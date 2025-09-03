from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, timedelta
import json

from employee_predictor.models import Employee, PerformanceHistory


class ModelsCoverageFixTests(TestCase):
    """Tests to complete coverage for models.py."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

        self.employee = Employee.objects.create(
            name='Test Employee',
            emp_id='EMP001',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),
            gender='M',
            marital_status='Single',
            age=30,
            race='White',
            hispanic_latino='No',
            recruitment_source='LinkedIn',
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            employment_status='Active'
        )

    def test_get_performance_label_complete(self):
        """Test get_performance_label methods with all possible values."""
        # Test original method (lines 127-135)
        for score, expected in [
            (4, "Exceeds Expectations"),
            (3, "Fully Meets Expectations"),
            (2, "Needs Improvement"),
            (1, "Performance Improvement Plan (PIP)"),
            (None, "Not Evaluated"),
            (5, "Not Evaluated")  # Invalid score
        ]:
            self.employee.predicted_score = score
            self.assertEqual(self.employee.get_performance_label(), expected)

        # Test that when date_of_hire is None in get_tenure_years (line 86)
        # FIX: Create with a valid date, then modify the field for the test
        employee = Employee.objects.create(
            name='No Hire Date Employee',
            emp_id='EMP002',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),  # Valid date for database storage
            gender='M',
            marital_status='Single',
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            employment_status='Active'
        )

        # Now modify the date_of_hire after creation for testing
        # This only changes it in memory, not in the database
        employee.date_of_hire = None

        # Should return 0 if date_of_hire is None
        self.assertEqual(employee.get_tenure_years(), 0)