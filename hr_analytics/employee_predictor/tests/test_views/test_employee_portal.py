# employee_predictor/tests/test_views/test_employee_portal.py
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from employee_predictor.tests.test_helper import axes_login
from employee_predictor.models import Employee, Attendance, Leave, Payroll
from employee_predictor.views import (
    EmployeeLeaveCreateView, EmployeeAttendanceListView,
    EmployeePayslipDetailView, EmployeeProfileView
)


class EmployeePortalViewsTest(TestCase):
    """Test Employee Portal Views."""

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Create employee user
        self.user = User.objects.create_user(
            username='employee',
            password='password',
            is_staff=False
        )

        # Create employee record
        self.employee = Employee.objects.create(
            user=self.user,
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

        # Create attendance records
        for i in range(5):
            Attendance.objects.create(
                employee=self.employee,
                date=timezone.now().date() - timedelta(days=i),
                status='PRESENT',
                hours_worked=Decimal('8.00')
            )

        # Create leave records
        self.leave = Leave.objects.create(
            employee=self.employee,
            start_date=timezone.now().date() + timedelta(days=5),
            end_date=timezone.now().date() + timedelta(days=7),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Vacation'
        )

        # Create payroll record
        self.payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date(2023, 1, 1),
            period_end=date(2023, 1, 31),
            basic_salary=Decimal('5000.00'),
            net_salary=Decimal('5000.00'),
            status='APPROVED'
        )

        # Login
        axes_login(self.client, 'employee', 'password')

    def test_employee_leave_create_view(self):
        """Test EmployeeLeaveCreateView methods."""
        view = EmployeeLeaveCreateView()

        # Test get_form
        request = self.factory.get('/portal/leaves/create/')
        request.user = self.user
        view.request = request

        form = view.get_form()
        self.assertEqual(form.initial['employee'], self.employee)

        # Test form_valid
        leave_data = {
            'employee': self.employee.id,
            'start_date': (timezone.now().date() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'end_date': (timezone.now().date() + timedelta(days=12)).strftime('%Y-%m-%d'),
            'leave_type': 'SICK',
            'reason': 'Medical appointment'
        }

        response = self.client.post(reverse('employee-leave-create'), leave_data, follow=True)

        # Check redirect
        self.assertRedirects(response, reverse('employee-leaves'))

        # Check leave was created with PENDING status
        new_leave = Leave.objects.get(
            employee=self.employee,
            start_date=timezone.now().date() + timedelta(days=10)
        )
        self.assertEqual(new_leave.status, 'PENDING')
        self.assertEqual(new_leave.leave_type, 'SICK')

    def test_employee_attendance_list_view(self):
        """Test EmployeeAttendanceListView.get_queryset with filters."""
        # Create request with month and year filters
        today = timezone.now().date()

        view = EmployeeAttendanceListView()
        request = self.factory.get(f'/portal/attendance/?month={today.month}&year={today.year}')
        request.user = self.user
        view.request = request

        queryset = view.get_queryset()

        # All attendance should be for the current employee
        self.assertTrue(all(a.employee == self.employee for a in queryset))

        # All attendance should be for the specified month and year
        for attendance in queryset:
            self.assertEqual(attendance.date.month, today.month)
            self.assertEqual(attendance.date.year, today.year)

    def test_employee_payslip_detail_view(self):
        """Test EmployeePayslipDetailView.get_queryset."""
        view = EmployeePayslipDetailView()
        request = self.factory.get(f'/portal/payslips/{self.payroll.id}/')
        request.user = self.user
        view.request = request

        queryset = view.get_queryset()

        # Queryset should only include payrolls for the current employee
        self.assertTrue(all(p.employee == self.employee for p in queryset))

    def test_employee_profile_view(self):
        """Test EmployeeProfileView.get_object."""
        view = EmployeeProfileView()
        request = self.factory.get('/portal/profile/')
        request.user = self.user
        view.request = request

        profile = view.get_object()

        # Should return the employee associated with the current user
        self.assertEqual(profile, self.employee)