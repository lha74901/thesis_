# employee_predictor/tests/test_helper_complete.py
from django.test import TestCase, RequestFactory
from django.contrib.auth import authenticate
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.auth.models import User
from datetime import date
from decimal import Decimal
import random

from employee_predictor.tests.test_helper import (
    axes_login, add_message_middleware, generate_test_employee_data
)
from employee_predictor.models import Employee


class TestHelperTest(TestCase):
    """Test test_helper.py utilities."""

    def setUp(self):
        self.factory = RequestFactory()

        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

    def test_add_message_middleware(self):
        """Test add_message_middleware function."""
        request = self.factory.get('/')
        request = add_message_middleware(request)

        # Check that message attributes are set
        self.assertTrue(hasattr(request, 'session'))
        self.assertTrue(hasattr(request, '_messages'))
        self.assertIsInstance(request._messages, FallbackStorage)

    def test_generate_test_employee_data(self):
        """Test generate_test_employee_data function."""
        # Test with default ID
        data = generate_test_employee_data()
        self.assertIn('name', data)
        self.assertIn('emp_id', data)
        self.assertIn('department', data)
        self.assertIn('gender', data)
        self.assertIsInstance(data['salary'], Decimal)

        # Test with specified ID
        data = generate_test_employee_data(123)
        self.assertEqual(data['emp_id'], 'EMP123')
        self.assertIn('123', data['name'])