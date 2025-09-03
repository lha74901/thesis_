# employee_predictor/tests/test_base.py
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from datetime import date, timedelta

from employee_predictor.models import Employee, Attendance, Leave, Payroll
from employee_predictor.tests.test_helper import axes_login


class BaseTestCase(TestCase):
    """Base test case with common setup for all tests."""

    def setUp(self):
        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpassword',
            is_staff=True
        )

        # Create employee user
        self.employee_user = User.objects.create_user(
            username='employeeuser',
            password='employeepassword'
        )

        # Create employee record
        self.employee = Employee.objects.create(
            user=self.employee_user,
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

        # Create client and factory
        self.client = Client()
        self.factory = RequestFactory()

    def create_attendance(self, employee=None, days=5, status='PRESENT'):
        """Helper to create attendance records for a given employee."""
        if employee is None:
            employee = self.employee

        today = date.today()
        attendances = []

        for day in range(days):
            attendance = Attendance.objects.create(
                employee=employee,
                date=today - timedelta(days=day),
                status=status,
                hours_worked=Decimal('8.00') if status in ['PRESENT', 'LATE'] else Decimal('0.00')
            )
            attendances.append(attendance)

        return attendances

    def create_leave(self, employee=None, status='PENDING'):
        """Helper to create a leave request."""
        if employee is None:
            employee = self.employee

        return Leave.objects.create(
            employee=employee,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=10),
            leave_type='ANNUAL',
            status=status,
            reason='Test leave request'
        )

    def create_payroll(self, employee=None, status='DRAFT'):
        """Helper to create a payroll record."""
        if employee is None:
            employee = self.employee

        return Payroll.objects.create(
            employee=employee,
            period_start=date(date.today().year, date.today().month, 1),
            period_end=date(date.today().year, date.today().month, 28),
            basic_salary=Decimal('5000.00'),
            overtime_hours=Decimal('10.00'),
            overtime_rate=Decimal('20.00'),
            bonuses=Decimal('500.00'),
            deductions=Decimal('200.00'),
            tax=Decimal('800.00'),
            net_salary=Decimal('4700.00'),
            status=status
        )


class BaseStaffTestCase(BaseTestCase):
    """Base test case for staff-level functionality."""

    def setUp(self):
        super().setUp()
        axes_login(self.client, 'staffuser', 'staffpassword')


class BaseEmployeeTestCase(BaseTestCase):
    """Base test case for employee-level functionality."""

    def setUp(self):
        super().setUp()
        axes_login(self.client, 'employeeuser', 'employeepassword')