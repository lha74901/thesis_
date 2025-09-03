# employee_predictor/tests/test_middleware.py

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse
from employee_predictor.tests.test_helper import axes_login


# First, check the actual name of the middleware in your middleware.py file
# Common alternatives might be StaffAccessMiddleware, EmployeePortalMiddleware, etc.
# Let's use a more generic approach that doesn't depend on the exact class name:

class MiddlewareTest(TestCase):
    def setUp(self):
        # Create users
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpassword',
            is_staff=True
        )
        self.employee_user = User.objects.create_user(
            username='employeeuser',
            password='employeepassword',
            is_staff=False
        )

        self.client = Client()

    def test_staff_access_to_admin_urls(self):
        """Test staff access to admin URLs."""
        # Login as staff
        axes_login(self.client, 'staffuser', 'staffpassword')

        # Access admin URLs
        admin_urls = [
            reverse('employee-list'),
            reverse('attendance-list'),
            reverse('leave-list'),
            reverse('payroll-list')
        ]

        for url in admin_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_employee_redirect_from_admin_urls(self):
        """Test that employees are redirected from admin URLs."""
        # Login as employee
        axes_login(self.client, 'employeeuser', 'employeepassword')

        # Access admin URLs
        admin_urls = [
            reverse('employee-list'),
            reverse('attendance-list'),
            reverse('leave-list'),
            reverse('payroll-list')
        ]

        for url in admin_urls:
            response = self.client.get(url)
            self.assertRedirects(response, reverse('employee-portal'))