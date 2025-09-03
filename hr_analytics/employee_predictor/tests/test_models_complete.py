# employee_predictor/tests/test_models_complete.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from employee_predictor.models import Employee, Attendance, Leave, Payroll, PerformanceHistory


class ModelStrMethodsTest(TestCase):
    """Test __str__ methods for all models."""

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
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            hispanic_latino='No',
            employment_status='Active'
        )

        self.attendance = Attendance.objects.create(
            employee=self.employee,
            date=date.today(),
            status='PRESENT',
            hours_worked=Decimal('8.00')
        )

        self.leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today(),
            end_date=date.today(),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Test leave'
        )

        self.payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date(2023, 1, 1),
            period_end=date(2023, 1, 31),
            basic_salary=Decimal('5000.00'),
            net_salary=Decimal('5000.00'),
            status='DRAFT'
        )

    def test_employee_str(self):
        """Test Employee.__str__()"""
        expected = f"Test Employee (EMP001)"
        self.assertEqual(str(self.employee), expected)

    def test_attendance_str(self):
        """Test Attendance.__str__()"""
        expected = f"Test Employee - {date.today()} (PRESENT)"
        self.assertEqual(str(self.attendance), expected)

    def test_leave_str(self):
        """Test Leave.__str__()"""
        expected = f"Test Employee - ANNUAL ({date.today()} to {date.today()})"
        self.assertEqual(str(self.leave), expected)

    def test_payroll_str(self):
        """Test Payroll.__str__()"""
        expected = f"Test Employee - 2023-01-01 to 2023-01-31"
        self.assertEqual(str(self.payroll), expected)


    def test_calculate_hours_worked_edge_case(self):
        """Test calculate_hours_worked with NULL check-out time."""
        # Use a date far in the past to avoid conflicts
        test_date = date.today() - timedelta(days=30)
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=test_date,  # Use a specific date instead of today
            check_in=None,
            check_out=None,
            status='ABSENT',
            hours_worked=Decimal('0.00')
        )
        self.assertEqual(attendance.calculate_hours_worked(), Decimal('0.00'))