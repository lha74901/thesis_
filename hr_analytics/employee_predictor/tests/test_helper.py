# employee_predictor/tests/test_helper.py
from django.test import RequestFactory
from django.contrib.auth import authenticate
from django.contrib.messages.storage.fallback import FallbackStorage
from datetime import date, timedelta
from decimal import Decimal
import random


def axes_login(client, username, password, **kwargs):
    """
    Login method that works with django-axes by providing a request object.

    Args:
        client: The test client
        username: The username to log in with
        password: The password to log in with
        **kwargs: Any additional parameters to pass to authenticate

    Returns:
        True if login was successful, False otherwise
    """
    request_factory = RequestFactory()
    request = request_factory.get('/')
    request.session = client.session

    # Include request in auth credentials
    auth_kwargs = {'request': request, 'username': username, 'password': password}
    auth_kwargs.update(kwargs)

    # Authenticate with request
    user = authenticate(**auth_kwargs)

    if user:
        # Manually log in without going through authenticate again
        client.force_login(user)
        return True
    return False


def add_message_middleware(request):
    """Add message middleware to a request factory request."""
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    return request


def generate_test_employee_data(unique_id=None):
    """Generate test employee data with optional unique identifier."""
    if unique_id is None:
        unique_id = random.randint(1000, 9999)

    return {
        'name': f'Test Employee {unique_id}',
        'emp_id': f'EMP{unique_id}',
        'department': 'IT',
        'position': 'Developer',
        'date_of_hire': date(2020, 1, 1),
        'gender': 'M',
        'marital_status': 'Single',
        'salary': Decimal('60000.00'),
        'engagement_survey': 4.0,
        'emp_satisfaction': 4,
        'special_projects_count': 2,
        'days_late_last_30': 1,
        'absences': 3,
        'hispanic_latino': 'No',
        'employment_status': 'Active'
    }