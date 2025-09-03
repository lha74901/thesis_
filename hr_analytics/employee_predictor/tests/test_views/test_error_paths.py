# employee_predictor/tests/test_views/test_error_paths.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch, MagicMock
from employee_predictor.tests.test_helper import axes_login
from employee_predictor.models import Employee, Leave, Payroll


class ViewErrorPathsTest(TestCase):
    def setUp(self):
        # Create users and test data
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpassword',
            is_staff=True
        )
        self.client = Client()
        axes_login(self.client, 'staffuser', 'staffpassword')

    def test_employee_create_view_validation_error(self):
        """Test EmployeeCreateView with validation errors."""
        # Submit with missing required fields
        response = self.client.post(
            reverse('employee-create'),
            {'name': 'Test Employee'},  # Missing other required fields
            follow=True
        )

        # Should return form with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
