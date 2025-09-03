# employee_predictor/tests/test_ml/test_predictor_more.py
from django.test import TestCase
from employee_predictor.ml.predictor import PerformancePredictor
from employee_predictor.forms import BulkAttendanceForm, LeaveForm, EmployeeForm
from django.core.files.uploadedfile import SimpleUploadedFile
from employee_predictor.models import Employee, Leave
from datetime import date, timedelta
from decimal import Decimal


class PerformancePredictorMethodsTest(TestCase):
    """Test the test methods in PerformancePredictor"""

    def setUp(self):
        """Set up test data and instance."""
        self.predictor = PerformancePredictor()

        # Create employee for leave test
        self.employee = Employee.objects.create(
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

    def test_bulk_attendance_form_empty_submission(self):
        """Test BulkAttendanceForm with completely empty data as implemented in predictor.py"""
        # Note: This is a bit unusual to have this test in the predictor class,
        # but we're testing it as implemented

        # Submit form with no data
        form = BulkAttendanceForm(data={}, files={})

        # Verify it's invalid
        self.assertFalse(form.is_valid())

        # Check both required fields have errors
        self.assertIn('date', form.errors)
        self.assertIn('csv_file', form.errors)

    def test_leave_form_instance_validation(self):
        """Test LeaveForm validation when updating an existing instance."""
        # First create a leave record
        leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=5),
            leave_type='ANNUAL',
            status='APPROVED',
            reason='Pre-existing leave'
        )

        # Now create a form with this instance
        form_data = {
            'employee': self.employee.id,
            'start_date': (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'leave_type': 'SICK',
            'reason': 'Updated leave'
        }

        # Create form with an instance to test that branch in clean() method
        form = LeaveForm(data=form_data, instance=leave)
        self.assertTrue(form.is_valid())

        # Save and verify
        updated_leave = form.save()
        self.assertEqual(updated_leave.leave_type, 'SICK')
        self.assertEqual(updated_leave.reason, 'Updated leave')

        # Clean up
        updated_leave.delete()

    def test_employee_form_with_no_data(self):
        """Test EmployeeForm with no data submission."""
        form = EmployeeForm(data={})
        self.assertFalse(form.is_valid())

        # Verify required fields are marked as errors
        required_fields = ['name', 'emp_id', 'department', 'position', 'date_of_hire',
                           'gender', 'salary', 'engagement_survey', 'emp_satisfaction',
                           'days_late_last_30', 'absences']
        for field in required_fields:
            self.assertIn(field, form.errors)