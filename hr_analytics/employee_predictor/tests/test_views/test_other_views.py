# employee_predictor/tests/test_views/test_other_views.py
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from employee_predictor.tests.test_helper import axes_login, add_message_middleware
from employee_predictor.models import Employee, Attendance, Leave, Payroll
from employee_predictor.views import (
    employee_register, LeaveUpdateView, AttendanceUpdateView, PayrollUpdateView
)


class EmployeeRegisterTest(TestCase):
    """Test employee_register view."""

    def setUp(self):
        self.client = Client()

        # Create employee record without user
        self.employee = Employee.objects.create(
            name='Test Employee',
            emp_id='EMP001',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),
            gender='M',
            marital_status='Single',
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            hispanic_latino='No',
            employment_status='Active',
            user=None
        )

    def test_employee_register_success(self):
        """Test employee_register with valid data."""
        data = {
            'employee_id': 'EMP001',
            'username': 'newuser',
            'password1': 'ComplexPassword123',
            'password2': 'ComplexPassword123'
        }

        response = self.client.post(reverse('register'), data, follow=True)

        # Check redirect to login
        self.assertRedirects(response, reverse('login'))

        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())

        # Check employee was linked to user
        self.employee.refresh_from_db()
        self.assertIsNotNone(self.employee.user)
        self.assertEqual(self.employee.user.username, 'newuser')

    def test_employee_register_error(self):
        """Test employee_register with invalid data."""
        data = {
            'employee_id': 'INVALID',  # Invalid employee ID
            'username': 'newuser',
            'password1': 'ComplexPassword123',
            'password2': 'ComplexPassword123'
        }

        response = self.client.post(reverse('register'), data)

        # Should stay on register page with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid Employee ID')

        # Check no user was created
        self.assertFalse(User.objects.filter(username='newuser').exists())


class UpdateViewsTest(TestCase):
    """Test various Update views."""

    def setUp(self):
        self.client = Client()

        # Create staff user
        self.staff = User.objects.create_user(
            username='staff',
            password='password',
            is_staff=True
        )

        # Create employee
        self.employee = Employee.objects.create(
            name='Test Employee',
            emp_id='EMP001',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),
            gender='M',
            marital_status='Single',
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            hispanic_latino='No',
            employment_status='Active'
        )

        # Create leave record
        self.leave = Leave.objects.create(
            employee=self.employee,
            start_date=timezone.now().date() + timedelta(days=5),
            end_date=timezone.now().date() + timedelta(days=7),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Vacation'
        )

        # Create attendance record
        self.attendance = Attendance.objects.create(
            employee=self.employee,
            date=timezone.now().date(),
            status='PRESENT',
            check_in=timezone.now().time(),
            check_out=None,
            hours_worked=Decimal('0.00')
        )

        # Create payroll record
        self.payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date(2023, 1, 1),
            period_end=date(2023, 1, 31),
            basic_salary=Decimal('5000.00'),
            net_salary=Decimal('5000.00'),
            status='DRAFT'
        )

        # Login as staff
        axes_login(self.client, 'staff', 'password')

    def test_leave_update_view(self):
        """Test LeaveUpdateView.form_valid."""
        factory = RequestFactory()
        request = factory.post('/leave/update/')
        request.user = self.staff
        request = add_message_middleware(request)

        view = LeaveUpdateView()
        view.request = request
        view.object = self.leave

        # Create form with updated data
        form_data = {
            'employee': self.employee.id,
            'start_date': (timezone.now().date() + timedelta(days=6)).strftime('%Y-%m-%d'),
            'end_date': (timezone.now().date() + timedelta(days=8)).strftime('%Y-%m-%d'),
            'leave_type': 'SICK',
            'reason': 'Updated reason'
        }

        # Update leave through the view
        response = self.client.post(
            reverse('leave-update', args=[self.leave.id]),
            form_data,
            follow=True
        )

        # Check redirect
        self.assertRedirects(response, reverse('leave-list'))

        # Check leave was updated
        self.leave.refresh_from_db()
        self.assertEqual(self.leave.leave_type, 'SICK')
        self.assertEqual(self.leave.reason, 'Updated reason')

    def test_attendance_update_view(self):
        """Test AttendanceUpdateView.form_valid."""
        # Update attendance through the view
        form_data = {
            'employee': self.employee.id,
            'date': timezone.now().date().strftime('%Y-%m-%d'),
            'status': 'PRESENT',
            'check_in': '09:00',
            'check_out': '17:00',
            'notes': 'Updated notes'
        }

        response = self.client.post(
            reverse('attendance-update', args=[self.attendance.id]),
            form_data,
            follow=True
        )

        # Check redirect
        self.assertRedirects(response, reverse('attendance-list'))

        # Check attendance was updated
        self.attendance.refresh_from_db()
        self.assertEqual(self.attendance.notes, 'Updated notes')
        self.assertIsNotNone(self.attendance.check_out)
        self.assertEqual(self.attendance.hours_worked, Decimal('8.00'))

    def test_payroll_update_view_dispatching(self):
        """Test PayrollUpdateView.dispatch with non-draft payroll."""
        # Change payroll status to non-draft
        self.payroll.status = 'APPROVED'
        self.payroll.save()

        # Try to access update view
        response = self.client.get(
            reverse('payroll-update', args=[self.payroll.id]),
            follow=True
        )

        # Should redirect to payroll list
        self.assertRedirects(response, reverse('payroll-list'))

        # Should show error message
        messages_list = list(response.context['messages'])
        self.assertTrue(any('Only draft payrolls can be edited' in str(m) for m in messages_list))

    def test_payroll_update_view(self):
        """Test PayrollUpdateView.form_valid."""
        # Update payroll through the view
        form_data = {
            'employee': self.employee.id,
            'period_start': '2023-01-01',
            'period_end': '2023-01-31',
            'basic_salary': '6000.00',  # Changed
            'overtime_hours': '10.00',
            'overtime_rate': '20.00',
            'bonuses': '500.00',
            'deductions': '200.00',
            'tax': '1000.00'
        }

        response = self.client.post(
            reverse('payroll-update', args=[self.payroll.id]),
            form_data,
            follow=True
        )

        # Check redirect
        self.assertRedirects(response, reverse('payroll-list'))

        # Check payroll was updated
        self.payroll.refresh_from_db()
        self.assertEqual(self.payroll.basic_salary, Decimal('6000.00'))

        # Check net salary recalculation
        expected_net = Decimal('6000.00') + (Decimal('10.00') * Decimal('20.00')) + Decimal('500.00') - Decimal(
            '200.00') - Decimal('1000.00')
        self.assertEqual(self.payroll.net_salary, expected_net)