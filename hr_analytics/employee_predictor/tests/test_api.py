# employee_predictor/tests/test_api.py
from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, timedelta
from decimal import Decimal
import json
from unittest.mock import patch, MagicMock

from employee_predictor.models import Employee, Attendance
from employee_predictor.tests.test_base import BaseTestCase
from employee_predictor.tests.test_helper import axes_login
from employee_predictor.api import get_employee_salary_info


class EmployeeAPITest(BaseTestCase):
    """Test API endpoint functionality."""

    def setUp(self):
        super().setUp()

        # Create attendance records
        self.create_attendance(days=5)

        # Login as staff user
        axes_login(self.client, 'staffuser', 'staffpassword')

    def test_get_employee_salary_info_authenticated(self):
        """Test API returns salary info for authenticated users."""
        response = self.client.get(
            reverse('api-employee-salary', args=[self.employee.id])
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Validate response data
        self.assertEqual(data['employee_id'], self.employee.id)
        self.assertEqual(data['name'], 'Test Employee')
        self.assertEqual(float(data['salary']), 60000.00)
        self.assertIn('overtime_rate', data)
        self.assertIn('attendance_stats', data)

    def test_get_employee_salary_info_with_dates(self):
        """Test API with custom date parameters."""
        response = self.client.get(
            reverse('api-employee-salary', args=[self.employee.id]),
            {'start_date': '2023-01-01', 'end_date': '2023-01-31'}
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Validate response contains expected fields
        self.assertIn('employee_id', data)
        self.assertIn('attendance_stats', data)
        self.assertIn('overtime_rate', data)
        self.assertIn('estimated_tax', data)

    def test_get_employee_salary_info_invalid_employee(self):
        """Test API with invalid employee ID."""
        response = self.client.get(
            reverse('api-employee-salary', args=[9999])  # Non-existent ID
        )

        # Should return 400 status code
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        # Update assertion to match exact error message
        self.assertIn('Employee with ID 9999 not found', data['error'])

    def test_api_error_handling(self):
        """Test API error handling scenarios."""
        # Test with malformed date
        response = self.client.get(
            reverse('api-employee-salary', args=[self.employee.id]),
            {'start_date': 'invalid-date', 'end_date': '2023-01-31'}
        )

        # Should return 400 for invalid date format
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Invalid date format', data['error'])

    def test_unauthorized_access(self):
        """Test API access by unauthenticated user."""
        # Logout
        self.client.logout()

        # Try to access API
        response = self.client.get(
            reverse('api-employee-salary', args=[self.employee.id])
        )

        # Should redirect to login page or return 403
        self.assertIn(response.status_code, [302, 403])

    @patch('employee_predictor.api.date')
    def test_december_date_handling(self, mock_date):
        """Test API handles December date rollover correctly."""
        # Mock today's date to be in December
        mock_date.today.return_value = date(2023, 12, 15)
        # The actual date.today() is patched but we still need a real date instance for other operations
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        response = self.client.get(
            reverse('api-employee-salary', args=[self.employee.id])
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Verify data contains expected fields
        self.assertIn('employee_id', data)
        self.assertIn('attendance_stats', data)

    def test_general_exception_handling(self):
        """Test API handles unexpected errors gracefully."""
        # Mock calculate_payroll_details to raise an exception
        with patch('employee_predictor.api.calculate_payroll_details') as mock_calc:
            mock_calc.side_effect = Exception("Test exception")

            # Make API request
            response = self.client.get(
                reverse('api-employee-salary', args=[self.employee.id])
            )

            # Should return 400 with error message
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.content)
            self.assertIn('error', data)
            self.assertEqual(data['error'], "Test exception")


class APIDirectTest(TestCase):
    """Test API functions directly with RequestFactory."""

    def setUp(self):
        # Create user and employee
        self.staff_user = User.objects.create_user(
            username='apistaff',
            password='password',
            is_staff=True
        )

        self.employee = Employee.objects.create(
            name='API Test Employee',
            emp_id='API001',
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

        # Create attendances
        for i in range(5):
            Attendance.objects.create(
                employee=self.employee,
                date=date.today() - timedelta(days=i),
                status='PRESENT',
                hours_worked=Decimal('8.00')
            )

        # Create factory
        self.factory = RequestFactory()

    def test_get_employee_salary_info_direct(self):
        """Test get_employee_salary_info function directly."""
        # Create authenticated request
        request = self.factory.get(f'/api/employee/{self.employee.id}/salary/')
        request.user = self.staff_user

        # Call API function directly
        response = get_employee_salary_info(request, self.employee.id)

        # Check response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Validate response data
        self.assertEqual(data['employee_id'], self.employee.id)
        self.assertEqual(data['name'], 'API Test Employee')
        self.assertIn('attendance_stats', data)

    def test_get_employee_salary_info_with_invalid_date(self):
        """Test API with invalid date parameters."""
        request = self.factory.get(
            f'/api/employee/{self.employee.id}/salary/',
            {'start_date': 'invalid', 'end_date': '2023-01-31'}
        )
        request.user = self.staff_user

        response = get_employee_salary_info(request, self.employee.id)

        # Should return 400 status code
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('Invalid date format', data['error'])

    def test_get_employee_salary_info_nonexistent_employee(self):
        """Test API with non-existent employee ID."""
        request = self.factory.get(f'/api/employee/9999/salary/')
        request.user = self.staff_user

        response = get_employee_salary_info(request, 9999)

        # Should return 400 status code
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        # Update assertion to match exact error message
        self.assertIn('Employee with ID 9999 not found', data['error'])