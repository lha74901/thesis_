from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from employee_predictor.models import Employee, Attendance, Leave, Payroll
from employee_predictor.views import (
    EmployeeLeaveListView, EmployeeAttendanceListView,
    EmployeePayslipListView, EmployeePayslipDetailView,
    LeaveListView, AttendanceListView, PayrollListView,
    PayrollCreateView, AdminPerformanceListView, approve_leave
)
from employee_predictor.tests.test_helper import axes_login, add_message_middleware


class ViewsCoverageTests(TestCase):
    """Tests to complete coverage for views.py."""

    def setUp(self):
        # Create users
        self.staff_user = User.objects.create_user(
            username='staff_user',
            password='password',
            is_staff=True
        )

        self.employee_user = User.objects.create_user(
            username='employee_user',
            password='password',
            is_staff=False
        )

        # Create employee
        self.employee = Employee.objects.create(
            user=self.employee_user,
            name='Test Employee',
            emp_id='EMP001',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),
            gender='M',
            marital_status='Single',
            age=30,
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            hispanic_latino='No',
            employment_status='Active'
        )

        # Factory for request objects
        self.factory = RequestFactory()

        # Client for view tests
        self.client = Client()

    def test_admin_performance_list_view_all_filters(self):
        """Test AdminPerformanceListView with all score range filters."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Create employees with different performance scores
        for i, score in enumerate([1, 2, 3, 4, None]):
            Employee.objects.create(
                name=f'Performance Test {i}',
                emp_id=f'PERF00{i}',
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
                predicted_score=score
            )

        # Test each score_range filter
        # The view logic checks for these specific strings
        for score_range in ['exceeds', 'fully_meets', 'needs_improvement', 'improvement_plan', 'pending']:
            response = self.client.get(reverse('admin_performance_list'), {'score_range': score_range})
            self.assertEqual(response.status_code, 200)

            # Employees should be filtered according to score_range
            if score_range == 'exceeds':
                self.assertTrue(all(e.predicted_score == 4 for e in response.context['employees']))
            elif score_range == 'fully_meets':
                self.assertTrue(all(e.predicted_score == 3 for e in response.context['employees']))
            elif score_range == 'needs_improvement':
                self.assertTrue(all(e.predicted_score == 2 for e in response.context['employees']))
            elif score_range == 'improvement_plan':
                self.assertTrue(all(e.predicted_score == 1 for e in response.context['employees']))
            elif score_range == 'pending':
                self.assertTrue(all(e.predicted_score is None for e in response.context['employees']))

    def test_leave_approve_function(self):
        """Test approve_leave function with all branches."""
        # Create a leave request
        leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Test leave'
        )

        # Create request with approval action
        request = self.factory.get(f'/leave/{leave.id}/approve/?action=approve')
        request.user = self.staff_user
        request = add_message_middleware(request)

        # Call function directly
        response = approve_leave(request, leave.id)
        self.assertEqual(response.status_code, 302)  # Should redirect

        # Verify leave was approved
        leave.refresh_from_db()
        self.assertEqual(leave.status, 'APPROVED')
        self.assertEqual(leave.approved_by, self.staff_user)

        # Check that attendance records were created
        attendance_count = Attendance.objects.filter(
            employee=self.employee,
            status='ON_LEAVE',
            date__range=[leave.start_date, leave.end_date]
        ).count()
        self.assertEqual(attendance_count, 3)  # 3 days including start and end

        # Test with already approved leave
        leave2 = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            leave_type='ANNUAL',
            status='APPROVED',  # Already approved
            reason='Already approved leave'
        )

        request = self.factory.get(f'/leave/{leave2.id}/approve/?action=approve')
        request.user = self.staff_user
        request = add_message_middleware(request)

        response = approve_leave(request, leave2.id)
        self.assertEqual(response.status_code, 302)  # Should still redirect

        # Test with reject action
        leave3 = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=20),
            end_date=date.today() + timedelta(days=22),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Leave to reject'
        )

        request = self.factory.get(f'/leave/{leave3.id}/approve/?action=reject')
        request.user = self.staff_user
        request = add_message_middleware(request)

        response = approve_leave(request, leave3.id)
        self.assertEqual(response.status_code, 302)  # Should redirect

        # Verify leave was rejected
        leave3.refresh_from_db()
        self.assertEqual(leave3.status, 'REJECTED')
        self.assertEqual(leave3.approved_by, self.staff_user)

        # Test with no action parameter
        leave4 = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Leave with no action'
        )

        request = self.factory.get(f'/leave/{leave4.id}/approve/')  # No action param
        request.user = self.staff_user
        request = add_message_middleware(request)

        response = approve_leave(request, leave4.id)
        self.assertEqual(response.status_code, 302)  # Should still redirect

        # Status should remain PENDING since no action was specified
        leave4.refresh_from_db()
        self.assertEqual(leave4.status, 'PENDING')

    def test_employee_portal_views_corner_cases(self):
        """Test EmployeePortalView subclass methods with edge cases."""
        # Test EmployeeLeaveListView.get_queryset with employee that has no user
        view = EmployeeLeaveListView()
        view.request = self.factory.get('/portal/leaves/')
        view.request.user = User.objects.create_user(
            username='no_employee_user',
            password='password',
            is_staff=False
        )

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 0)

        # Test EmployeeAttendanceListView.get_queryset with employee that has no user
        # and with no month/year filter
        view = EmployeeAttendanceListView()
        view.request = self.factory.get('/portal/attendance/')
        view.request.user = User.objects.create_user(
            username='no_employee_user2',
            password='password',
            is_staff=False
        )

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 0)

        # Test EmployeePayslipListView.get_queryset with employee that has no user
        view = EmployeePayslipListView()
        view.request = self.factory.get('/portal/payslips/')
        view.request.user = User.objects.create_user(
            username='no_employee_user3',
            password='password',
            is_staff=False
        )

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 0)

        # Test EmployeePayslipDetailView.get_queryset with employee that has no user
        view = EmployeePayslipDetailView()
        view.request = self.factory.get('/portal/payslips/1/')
        view.request.user = User.objects.create_user(
            username='no_employee_user4',
            password='password',
            is_staff=False
        )

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 0)