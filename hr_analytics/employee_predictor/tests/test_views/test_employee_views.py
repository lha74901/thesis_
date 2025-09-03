# employee_predictor/tests/test_views/test_employee_views.py
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
from django.views import View
from employee_predictor.tests.test_helper import axes_login
from employee_predictor.models import Employee, Attendance, Leave, Payroll
from employee_predictor.views import (
    EmployeeRequiredMixin, EmployeePerformanceView, AdminPerformanceView,
    EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView, EmployeeLeaveCreateView,
    EmployeeAttendanceListView, EmployeePayslipDetailView, EmployeeProfileView,
    PayrollUpdateView, LeaveUpdateView, AttendanceUpdateView
)


class EmployeeRequiredMixinTest(TestCase):
    """Test EmployeeRequiredMixin."""

    def setUp(self):
        self.factory = RequestFactory()

        # Create users
        self.staff_user = User.objects.create_user(
            username='staff',
            password='password',
            is_staff=True
        )

        self.employee_user = User.objects.create_user(
            username='employee',
            password='password',
            is_staff=False
        )

        # Create a test mixin instance
        class TestView(EmployeeRequiredMixin):
            def get(self, request):
                return "success"

        self.test_view = TestView()

    def test_dispatch_staff_user(self):
        """Test dispatch redirects staff users."""
        request = self.factory.get('/test/')
        request.user = self.staff_user

        # Add message storage to request
        setattr(request, '_messages', MagicMock())

        response = self.test_view.dispatch(request)

        # Should redirect to dashboard
        self.assertEqual(response.url, reverse('dashboard'))

    def test_dispatch_employee_user(self):
        """Test dispatch allows employee users."""
        request = self.factory.get('/test/')
        request.user = self.employee_user

        # Create a proper view class with View as a base
        class TestView(EmployeeRequiredMixin, View):
            def get(self, request):
                return "success"

        self.test_view = TestView()

        response = self.test_view.dispatch(request)

        # Should return "success" from the get method
        self.assertEqual(response, "success")


class EmployeePerformanceViewTest(TestCase):
    """Test EmployeePerformanceView."""

    def setUp(self):
        self.client = Client()

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
                date=timezone.now().date() - timezone.timedelta(days=i),
                status='PRESENT' if i % 2 == 0 else 'LATE',
                hours_worked=Decimal('8.00')
            )

        # Login
        axes_login(self.client, 'employee', 'password')

    def test_get_object(self):
        """Test get_object returns employee for current user."""
        view = EmployeePerformanceView()
        view.request = MagicMock()
        view.request.user = self.user

        obj = view.get_object()

        self.assertEqual(obj, self.employee)

    def test_get_context_data(self):
        """Test get_context_data includes attendance stats."""
        # Create factory and request
        factory = RequestFactory()
        request = factory.get('/performance/')
        request.user = self.user

        # Create view instance and set request
        view = EmployeePerformanceView()
        view.request = request
        view.object = self.employee

        # Get context
        context = view.get_context_data()

        # Check if attendance_stats is in context
        self.assertIn('attendance_stats', context)
        self.assertIn('present_days', context['attendance_stats'])
        self.assertIn('late_days', context['attendance_stats'])
        self.assertIn('avg_hours', context['attendance_stats'])


class AdminPerformanceViewTest(TestCase):
    """Test AdminPerformanceView and AdminPerformanceListView."""

    def setUp(self):
        self.client = Client()

        # Create staff user
        self.user = User.objects.create_user(
            username='staff',
            password='password',
            is_staff=True
        )

        # Create employee records
        self.employees = []
        for i in range(5):
            emp = Employee.objects.create(
                name=f'Test Employee {i}',
                emp_id=f'EMP00{i}',
                department='IT' if i % 2 == 0 else 'HR',
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
                predicted_score=i % 4 + 1  # Values 1-4
            )
            self.employees.append(emp)

            # Create attendance records
            for j in range(3):
                Attendance.objects.create(
                    employee=emp,
                    date=timezone.now().date() - timezone.timedelta(days=j),
                    status='PRESENT',
                    hours_worked=Decimal('8.00')
                )

        # Login
        axes_login(self.client, 'staff', 'password')

    def test_admin_performance_list_view_queryset(self):
        """Test AdminPerformanceListView.get_queryset with filters."""
        response = self.client.get(reverse('admin_performance_list'))
        self.assertEqual(response.status_code, 200)

        # Test with search filter
        response = self.client.get(reverse('admin_performance_list'), {'search': 'Employee 1'})
        self.assertEqual(len(response.context['employees']), 1)

        # Test with department filter
        response = self.client.get(reverse('admin_performance_list'), {'department': 'IT'})
        self.assertTrue(all(e.department == 'IT' for e in response.context['employees']))

        # Test with score range filter
        response = self.client.get(reverse('admin_performance_list'), {'score_range': 'exceeds'})
        self.assertTrue(all(e.predicted_score == 4 for e in response.context['employees']))

    def test_admin_performance_list_view_context(self):
        """Test AdminPerformanceListView.get_context_data."""
        response = self.client.get(reverse('admin_performance_list'))

        # Check that summary statistics are in context
        self.assertIn('avg_performance', response.context)
        self.assertIn('top_performers_count', response.context)
        self.assertIn('meets_expectations_count', response.context)
        self.assertIn('needs_improvement_count', response.context)
        self.assertIn('pip_count', response.context)

    def test_admin_performance_detail_view(self):
        """Test AdminPerformanceView.get_context_data."""
        employee = self.employees[0]
        response = self.client.get(reverse('admin_performance_detail', args=[employee.pk]))

        # Check that attendance stats are in context
        self.assertIn('attendance_stats', response.context)
        self.assertIn('current_month_stats', response.context)
        self.assertIn('prev_month_stats', response.context)

        # Check attendance rate calculation
        self.assertIn('attendance_rate', response.context['current_month_stats'])