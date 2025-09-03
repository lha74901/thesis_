# employee_predictor/tests/test_forms.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date, timedelta
from decimal import Decimal

from employee_predictor.models import Employee, Leave, Payroll
from employee_predictor.forms import (
    EmployeeForm, LeaveForm, AttendanceForm, PayrollForm,
    BulkAttendanceForm, EmployeeRegistrationForm
)


class EmployeeFormTest(TestCase):
    """Tests for EmployeeForm validation and functionality."""

    def test_valid_data(self):
        """Test form with valid data."""
        form_data = {
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
            'salary': Decimal('60000.00'),
            'engagement_survey': 4.0,
            'emp_satisfaction': 4,
            'special_projects_count': 2,
            'days_late_last_30': 1,
            'absences': 3,
            'performance_score': 'Exceeds',
            'employment_status': 'Active'
        }

        form = EmployeeForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_validation_errors(self):
        """Test various validation errors."""
        # Test engagement_survey out of bounds
        form_data = {
            'name': 'Test Employee',
            'emp_id': 'EMP002',
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
            'engagement_survey': 6.0,  # Invalid: should be between 1 and 5
            'emp_satisfaction': 4,
            'special_projects_count': 2,
            'days_late_last_30': 1,
            'absences': 3,
            'employment_status': 'Active'
        }

        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('engagement_survey', form.errors)
        self.assertIn('must be between 1 and 5', str(form.errors['engagement_survey']))

        # Test emp_satisfaction out of bounds
        form_data['engagement_survey'] = 4.0
        form_data['emp_satisfaction'] = 6  # Invalid: should be between 1 and 5
        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('emp_satisfaction', form.errors)
        self.assertIn('must be between 1 and 5', str(form.errors['emp_satisfaction']))

        # Test days_late_last_30 out of bounds
        form_data['emp_satisfaction'] = 4
        form_data['days_late_last_30'] = 31  # Invalid: should be between 0 and 30
        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('days_late_last_30', form.errors)
        self.assertIn('Days late must be between 0 and 30', str(form.errors['days_late_last_30']))

        # Test with negative days_late
        form_data['days_late_last_30'] = -5
        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('days_late_last_30', form.errors)
        self.assertIn('Days late must be between 0 and 30', str(form.errors['days_late_last_30']))

    def test_unicode_characters(self):
        """Test form with Unicode characters."""
        form_data = {
            'name': '你好世界',  # Unicode characters
            'emp_id': 'EMP123',
            'department': 'IT',
            'position': 'Developer',
            'date_of_hire': '2020-01-01',
            'gender': 'M',
            'marital_status': 'Single',
            'age': 30,
            'salary': '60000.00',
            'engagement_survey': 4.0,
            'emp_satisfaction': 4,
            'special_projects_count': 2,
            'days_late_last_30': 1,
            'absences': 3,
            'hispanic_latino': 'No',
            'employment_status': 'Active'
        }

        form = EmployeeForm(data=form_data)
        self.assertTrue(form.is_valid())


class LeaveFormTest(TestCase):
    """Tests for LeaveForm validation and functionality."""

    def setUp(self):
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

    def test_valid_leave_request(self):
        """Test valid leave request form."""
        form_data = {
            'employee': self.employee.id,
            'start_date': date.today() + timedelta(days=5),
            'end_date': date.today() + timedelta(days=10),
            'leave_type': 'ANNUAL',
            'reason': 'Family vacation'
        }

        form = LeaveForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_end_date_before_start_date(self):
        """Test validation for end date before start date."""
        form_data = {
            'employee': self.employee.id,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=5),  # End date before start date
            'leave_type': 'ANNUAL',
            'reason': 'Family vacation'
        }

        form = LeaveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('End date cannot be before start date', str(form.errors))

    def test_overlapping_leave(self):
        """Test validation for overlapping leave requests."""
        # Create an existing approved leave
        Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
            leave_type='ANNUAL',
            status='APPROVED',
            reason='Existing leave'
        )

        # Try to create an overlapping leave
        form_data = {
            'employee': self.employee.id,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=20),
            'leave_type': 'SICK',
            'reason': 'Overlapping leave'
        }

        form = LeaveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('already an active leave request', str(form.errors))

    def test_overlapping_with_pending_leave(self):
        """Test validation for overlapping with a PENDING leave."""
        # Create an existing pending leave
        Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
            leave_type='ANNUAL',
            status='PENDING',  # PENDING status
            reason='Existing pending leave'
        )

        # Try to create an overlapping leave
        form_data = {
            'employee': self.employee.id,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=20),
            'leave_type': 'SICK',
            'reason': 'Overlapping with pending leave'
        }

        form = LeaveForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('already an active leave request', str(form.errors))

    def test_update_existing_leave(self):
        """Test updating an existing leave without triggering overlap validation with itself."""
        # Create an existing leave
        existing_leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=5),
            end_date=date.today() + timedelta(days=15),
            leave_type='ANNUAL',
            status='APPROVED',
            reason='Existing leave'
        )

        # Now update the same leave with modified dates
        form_data = {
            'employee': self.employee.id,
            'start_date': (date.today() + timedelta(days=6)).strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=16)).strftime('%Y-%m-%d'),
            'leave_type': 'ANNUAL',
            'reason': 'Updated leave'
        }

        # Create form for updating existing leave
        form = LeaveForm(data=form_data, instance=existing_leave)
        self.assertTrue(form.is_valid())


class PayrollFormTest(TestCase):
    """Tests for PayrollForm validation and functionality."""

    def setUp(self):
        self.employee = Employee.objects.create(
            name='Payroll Test Employee',
            emp_id='EMP_PAY',
            department='Finance',
            position='Accountant',
            date_of_hire=date(2020, 1, 1),
            gender='F',
            marital_status='Single',
            salary=Decimal('55000.00'),
            engagement_survey=3.5,
            emp_satisfaction=3,
            special_projects_count=1,
            days_late_last_30=0,
            absences=1,
            hispanic_latino='No',
            employment_status='Active'
        )

    def test_valid_payroll(self):
        """Test valid payroll form."""
        form_data = {
            'employee': self.employee.id,
            'period_start': '2023-01-01',
            'period_end': '2023-01-31',
            'basic_salary': '4500.00',
            'overtime_hours': '10.00',
            'overtime_rate': '20.00',
            'bonuses': '500.00',
            'deductions': '200.00',
            'tax': '600.00'
        }

        form = PayrollForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_end_date_before_start_date(self):
        """Test validation for end date before start date."""
        form_data = {
            'employee': self.employee.id,
            'period_start': '2023-01-31',
            'period_end': '2023-01-01',  # Before start date
            'basic_salary': '4500.00',
            'overtime_hours': '10.00',
            'overtime_rate': '20.00',
            'bonuses': '500.00',
            'deductions': '200.00',
            'tax': '600.00'
        }

        form = PayrollForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('End date cannot be before start date', str(form.errors))

    def test_overlapping_payroll_periods(self):
        """Test validation for overlapping payroll periods."""
        # Create an existing payroll
        Payroll.objects.create(
            employee=self.employee,
            period_start=date(2023, 2, 1),
            period_end=date(2023, 2, 28),
            basic_salary=Decimal('4500.00'),
            net_salary=Decimal('4500.00')
        )

        # Try to create one that overlaps
        form_data = {
            'employee': self.employee.id,
            'period_start': '2023-02-15',
            'period_end': '2023-03-15',
            'basic_salary': '4500.00',
            'overtime_hours': '10.00',
            'overtime_rate': '20.00',
            'bonuses': '500.00',
            'deductions': '200.00',
            'tax': '600.00'
        }

        form = PayrollForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('already a payroll record', str(form.errors))

    def test_update_existing_payroll(self):
        """Test updating an existing payroll without triggering overlap validation."""
        # Create an existing payroll
        existing_payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date(2023, 3, 1),
            period_end=date(2023, 3, 31),
            basic_salary=Decimal('4500.00'),
            net_salary=Decimal('4500.00')
        )

        # Update existing payroll with new values
        form_data = {
            'employee': self.employee.id,
            'period_start': '2023-03-01',
            'period_end': '2023-03-31',
            'basic_salary': '5000.00',  # Changed value
            'overtime_hours': '15.00',
            'overtime_rate': '25.00',
            'bonuses': '600.00',
            'deductions': '250.00',
            'tax': '700.00'
        }

        form = PayrollForm(data=form_data, instance=existing_payroll)
        self.assertTrue(form.is_valid())


class BulkAttendanceFormTest(TestCase):
    """Tests for BulkAttendanceForm validation and functionality."""

    def test_valid_form(self):
        """Test valid bulk attendance form."""
        # Create CSV content
        csv_content = "employee_id,status,check_in,check_out,notes\nEMP001,PRESENT,09:00,17:00,Test"

        # Create file using SimpleUploadedFile
        csv_file = SimpleUploadedFile(
            name='test.csv',
            content=csv_content.encode('utf-8'),
            content_type='text/csv'
        )

        # Create form with the file
        form_data = {
            'date': date.today().strftime('%Y-%m-%d'),
        }
        form = BulkAttendanceForm(data=form_data, files={'csv_file': csv_file})

        self.assertTrue(form.is_valid())

    def test_missing_date(self):
        """Test form validation with missing date."""
        # Create CSV content
        csv_content = "employee_id,status,check_in,check_out,notes\nEMP001,PRESENT,09:00,17:00,Test"

        # Create file
        csv_file = SimpleUploadedFile(
            name='test.csv',
            content=csv_content.encode('utf-8'),
            content_type='text/csv'
        )

        # Form with missing date
        form_data = {}  # Missing date
        form = BulkAttendanceForm(data=form_data, files={'csv_file': csv_file})

        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_missing_file(self):
        """Test form validation with missing file."""
        form_data = {
            'date': date.today().strftime('%Y-%m-%d'),
        }
        form = BulkAttendanceForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn('csv_file', form.errors)


class EmployeeRegistrationFormTest(TestCase):
    """Tests for EmployeeRegistrationForm validation and functionality."""

    def setUp(self):
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

        self.user = User.objects.create_user(
            username='existinguser',
            password='password123'
        )

    def test_valid_registration(self):
        """Test valid registration form."""
        form_data = {
            'employee_id': 'EMP001',
            'username': 'newuser',
            'password1': 'ComplexPassword123',
            'password2': 'ComplexPassword123'
        }

        form = EmployeeRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_employee_id(self):
        """Test form with invalid employee ID."""
        form_data = {
            'employee_id': 'INVALID',
            'username': 'newuser',
            'password1': 'ComplexPassword123',
            'password2': 'ComplexPassword123'
        }

        form = EmployeeRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('employee_id', form.errors)
        # Update assertion to match actual error message
        self.assertIn('Invalid Employee ID', str(form.errors['employee_id']))

    def test_username_already_exists(self):
        """Test form with already existing username."""
        form_data = {
            'employee_id': 'EMP001',
            'username': 'existinguser',  # This username already exists
            'password1': 'ComplexPassword123',
            'password2': 'ComplexPassword123'
        }

        form = EmployeeRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('already taken', str(form.errors['username']))

    def test_passwords_dont_match(self):
        """Test form with non-matching passwords."""
        form_data = {
            'employee_id': 'EMP001',
            'username': 'newuser',
            'password1': 'ComplexPassword123',
            'password2': 'DifferentPassword123'
        }

        form = EmployeeRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('Passwords do not match', str(form.errors))

    def test_employee_with_user_already_registered(self):
        """Test validation when employee already has a user account."""
        # Link the employee to a user
        self.employee.user = self.user
        self.employee.save()

        form_data = {
            'employee_id': 'EMP001',
            'username': 'newuser',
            'password1': 'ComplexPassword123',
            'password2': 'ComplexPassword123'
        }

        form = EmployeeRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('employee_id', form.errors)
        self.assertIn('already registered', str(form.errors['employee_id']))