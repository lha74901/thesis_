# employee_predictor/tests/test_views/test_admin_views.py

from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User
from decimal import Decimal  # Add this import
from unittest.mock import patch, MagicMock

from employee_predictor.tests.test_base import BaseStaffTestCase
from employee_predictor.models import Employee, Attendance, Leave



class DashboardViewTests(BaseStaffTestCase):
    """Test DashboardView thoroughly."""

    def test_dashboard_staff_access(self):
        """Test staff access to dashboard."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employee_predictor/dashboard.html')

        # Check context data
        self.assertIn('total_employees', response.context)
        self.assertIn('departments', response.context)
        self.assertIn('today_attendance', response.context)
        self.assertIn('pending_leaves', response.context)


class EmployeeListViewTests(BaseStaffTestCase):
    """Test EmployeeListView thoroughly."""

    def setUp(self):
        super().setUp()
        # Create additional employees for list testing
        for i in range(2, 5):
            Employee.objects.create(
                name=f'Test Employee {i}',
                emp_id=f'EMP00{i}',
                department='IT' if i % 2 == 0 else 'HR',
                position='Developer' if i % 2 == 0 else 'Manager',
                date_of_hire='2020-01-01',
                gender='M' if i % 2 == 0 else 'F',
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

    def test_employee_list_view(self):
        """Test employee list view displays all employees."""
        response = self.client.get(reverse('employee-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employee_predictor/employee/list.html')

        # Should contain all employees
        self.assertEqual(len(response.context['employees']), 4)

    def test_employee_list_view_search_filter(self):
        """Test search filter functionality."""
        # Search for specific employee
        response = self.client.get(
            reverse('employee-list'),
            {'search': 'Test Employee 3'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['employees']), 1)
        self.assertEqual(response.context['employees'][0].name, 'Test Employee 3')

    def test_employee_list_view_department_filter(self):
        """Test department filter functionality."""
        # Filter by department
        response = self.client.get(
            reverse('employee-list'),
            {'department': 'HR'}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(e.department == 'HR' for e in response.context['employees']))


class LeaveApprovalTests(BaseStaffTestCase):
    """Test leave approval functionality."""

    def setUp(self):
        super().setUp()
        self.leave = self.create_leave(status='PENDING')

    def test_approve_leave_request(self):
        """Test approving a leave request."""
        response = self.client.get(
            reverse('leave-approve', args=[self.leave.id]),
            {'action': 'approve'}
        )

        # Should redirect to leave list
        self.assertRedirects(response, reverse('leave-list'))

        # Refresh leave from database
        self.leave.refresh_from_db()
        self.assertEqual(self.leave.status, 'APPROVED')

        # Check attendance records were created
        attendance_count = Attendance.objects.filter(
            employee=self.employee,
            status='ON_LEAVE'
        ).count()

        self.assertEqual(attendance_count, 6)  # 6 days including start and end

    def test_reject_leave_request(self):
        """Test rejecting a leave request."""
        response = self.client.get(
            reverse('leave-approve', args=[self.leave.id]),
            {'action': 'reject'}
        )

        # Should redirect to leave list
        self.assertRedirects(response, reverse('leave-list'))

        # Refresh leave from database
        self.leave.refresh_from_db()
        self.assertEqual(self.leave.status, 'REJECTED')

        # Check no attendance records were created
        attendance_count = Attendance.objects.filter(
            employee=self.employee,
            status='ON_LEAVE'
        ).count()

        self.assertEqual(attendance_count, 0)

    def test_approve_leave_invalid_action(self):
        """Test approve_leave with invalid action."""
        response = self.client.get(
            reverse('leave-approve', args=[self.leave.id]),
            {'action': 'invalid'}
        )

        # Should redirect to leave list
        self.assertRedirects(response, reverse('leave-list'))

        # Leave status should remain pending
        self.leave.refresh_from_db()
        self.assertEqual(self.leave.status, 'PENDING')


class EmployeePredictionViewTests(BaseStaffTestCase):
    """Test EmployeePredictionView thoroughly."""

    @patch('employee_predictor.views.PerformancePredictor')
    def test_prediction_success(self, mock_predictor_class):
        """Test successful prediction."""
        # Mock the predictor instance
        mock_predictor = MagicMock()
        mock_predictor_class.return_value = mock_predictor

        # Mock prediction result
        mock_predictor.predict_with_probability.return_value = {
            'prediction': 4,
            'prediction_label': 'Exceeds',
            'probabilities': {1: 0.05, 2: 0.1, 3: 0.15, 4: 0.7}
        }

        # Form data
        data = {
            'name': 'Test Employee',
            'emp_id': 'EMP001',
            'department': 'IT',
            'position': 'Developer',
            'date_of_hire': '2020-01-01',
            'gender': 'M',
            'marital_status': 'Single',
            'age': 30,
            'race': 'White',
            'hispanic_latino': 'No',
            'recruitment_source': 'LinkedIn',
            'salary': '60000.00',
            'engagement_survey': 4.0,
            'emp_satisfaction': 4,
            'special_projects_count': 2,
            'days_late_last_30': 1,
            'absences': 3,
            'employment_status': 'Active'
        }

        # Make prediction
        response = self.client.post(
            reverse('employee-predict', args=[self.employee.id]),
            data=data,
            follow=True
        )

        # Check redirect and success message
        self.assertRedirects(response, reverse('employee-detail', args=[self.employee.id]))
        self.assertTrue(any(m.level == messages.SUCCESS for m in response.context['messages']))

        # Check employee was updated
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.predicted_score, 4)
        self.assertIsNotNone(self.employee.prediction_date)