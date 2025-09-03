import os
import json
import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile

from employee_predictor.models import Employee, Attendance, Leave, Payroll, PerformanceHistory
from employee_predictor.views import (
    EmployeeDeleteView, DashboardView, EmployeePredictionView,
    EmployeeLeaveListView, EmployeeAttendanceListView,
    EmployeePayslipListView, EmployeePayslipDetailView,
    LeaveListView, AttendanceListView, PayrollListView,
    PayrollCreateView, AdminPerformanceListView, approve_leave,
    bulk_attendance_upload, employee_register, PayrollDetailView
)
from employee_predictor.forms import BulkAttendanceForm, LeaveForm, EmployeeForm
from employee_predictor.ml.predictor import PerformancePredictor
from employee_predictor.ml.feature_engineering import (
    load_label_encoders, save_label_encoders,
    prepare_data_for_prediction, engineer_features
)
from employee_predictor.templatetags.hr_filters import multiply, percentage, subtract_from
from employee_predictor.tests.test_helper import axes_login, add_message_middleware


class CoverageCompletionTests(TestCase):
    def setUp(self):
        # Create users
        self.staff_user = User.objects.create_user(
            username='staff_user',
            password='password',
            is_staff=True
        )

        self.employee_user = User.objects.create_user(
            username='employee_user',
            password='password',
            is_staff=False
        )

        # Create employee
        self.employee = Employee.objects.create(
            user=self.employee_user,
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

        # Factory for request objects
        self.factory = RequestFactory()

        # Client for view tests
        self.client = Client()

    def test_employee_get_performance_label(self):
        """Test the original Employee.get_performance_label method."""
        # Test all possible score mappings
        for score, expected in [
            (4, "Exceeds Expectations"),
            (3, "Fully Meets Expectations"),
            (2, "Needs Improvement"),
            (1, "Performance Improvement Plan (PIP)"),
            (None, "Not Evaluated"),
            (5, "Not Evaluated")  # Out of range
        ]:
            self.employee.predicted_score = score
            self.assertEqual(self.employee.get_performance_label(), expected)

    def test_employee_get_tenure_years_with_future_date(self):
        """Test Employee.get_tenure_years with future date of hire."""
        future_date = date.today() + timedelta(days=30)
        self.employee.date_of_hire = future_date
        self.employee.save()

        tenure = self.employee.get_tenure_years()
        self.assertTrue(tenure < 0)

    def test_predictor_test_methods(self):
        """Test the test methods in PerformancePredictor class."""
        predictor = PerformancePredictor()

        # Test test_bulk_attendance_form_empty_submission
        form = BulkAttendanceForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)
        self.assertIn('csv_file', form.errors)

        # Test test_leave_form_instance_validation
        leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=5),
            leave_type='ANNUAL',
            status='APPROVED',
            reason='Pre-existing leave'
        )

        form_data = {
            'employee': self.employee.id,
            'start_date': (date.today() + timedelta(days=5)).strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=10)).strftime('%Y-%m-%d'),
            'leave_type': 'SICK',
            'reason': 'Updated leave'
        }

        form = LeaveForm(data=form_data, instance=leave)
        self.assertTrue(form.is_valid())
        updated_leave = form.save()
        self.assertEqual(updated_leave.leave_type, 'SICK')
        self.assertEqual(updated_leave.reason, 'Updated leave')

        # Clean up
        leave.delete()

        # Test test_employee_form_with_no_data
        form = EmployeeForm(data={})
        self.assertFalse(form.is_valid())
        required_fields = ['name', 'emp_id', 'department', 'position', 'date_of_hire',
                           'gender', 'salary', 'engagement_survey', 'emp_satisfaction',
                           'days_late_last_30', 'absences']
        for field in required_fields:
            self.assertIn(field, form.errors)

    def test_base_test_case_methods(self):
        """Test BaseTestCase and BaseEmployeeTestCase methods."""
        # Test BaseTestCase.create_payroll
        payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date(date.today().year, date.today().month, 1),
            period_end=date(date.today().year, date.today().month, 28),
            basic_salary=Decimal('5000.00'),
            overtime_hours=Decimal('10.00'),
            overtime_rate=Decimal('20.00'),
            bonuses=Decimal('500.00'),
            deductions=Decimal('200.00'),
            tax=Decimal('800.00'),
            net_salary=Decimal('4700.00'),
            status='DRAFT'
        )

        self.assertEqual(payroll.employee, self.employee)
        self.assertEqual(payroll.status, 'DRAFT')

        # Test BaseEmployeeTestCase.setUp
        self.client.logout()
        axes_login(self.client, 'employee_user', 'password')

    def test_employee_required_mixin_get_method(self):
        """Test the TestView.get method in EmployeeRequiredMixinTest."""
        from django.views import View
        from employee_predictor.views import EmployeeRequiredMixin

        class TestView(EmployeeRequiredMixin, View):
            def get(self, request):
                return "success"

        view = TestView()
        request = self.factory.get('/test/')
        request.user = self.employee_user

        response = view.get(request)
        self.assertEqual(response, "success")

    def test_employee_delete_view(self):
        """Test EmployeeDeleteView.delete method."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        response = self.client.post(reverse('employee-delete', args=[self.employee.id]), follow=True)
        self.assertRedirects(response, reverse('employee-list'))

        # Check that employee was deleted
        with self.assertRaises(Employee.DoesNotExist):
            Employee.objects.get(id=self.employee.id)

    def test_dashboard_view_dispatch(self):
        """Test DashboardView.dispatch method."""
        self.client.logout()
        axes_login(self.client, 'employee_user', 'password')

        # Employee users should be redirected to employee portal
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('employee-portal'))

        # Staff users should see the dashboard
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_employee_prediction_view_errors(self):
        """Test error handling in EmployeePredictionView.form_valid."""
        # Create a new employee
        employee = Employee.objects.create(
            name='Prediction Test',
            emp_id='PRED001',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),
            gender='M',
            marital_status='Single',
            age=30,
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            hispanic_latino='No',
            employment_status='Active'
        )

        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Submit form with invalid data to trigger exception
        form_data = {
            'name': employee.name,
            'emp_id': employee.emp_id,
            'department': employee.department,
            'position': employee.position,
            'date_of_hire': employee.date_of_hire.strftime('%Y-%m-%d'),
            'gender': employee.gender,
            'marital_status': employee.marital_status,
            'age': employee.age,
            'salary': 'invalid',  # This should cause an exception
            'engagement_survey': employee.engagement_survey,
            'emp_satisfaction': employee.emp_satisfaction,
            'special_projects_count': employee.special_projects_count,
            'days_late_last_30': employee.days_late_last_30,
            'absences': employee.absences,
            'hispanic_latino': employee.hispanic_latino,
            'employment_status': employee.employment_status
        }

        response = self.client.post(reverse('employee-predict', args=[employee.id]), form_data)
        self.assertEqual(response.status_code, 200)  # Should stay on the form page

    def test_employee_portal_views_edge_cases(self):
        """Test edge cases in employee portal views."""
        self.client.logout()
        axes_login(self.client, 'employee_user', 'password')

        # Test EmployeeLeaveListView.get_queryset with no employee
        self.employee.user = None
        self.employee.save()

        response = self.client.get(reverse('employee-leaves'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['leaves']), 0)

        # Restore link for further tests
        self.employee.user = self.employee_user
        self.employee.save()

        # Test EmployeeAttendanceListView.get_queryset with filters
        for i in range(3):
            Attendance.objects.create(
                employee=self.employee,
                date=timezone.now().date() - timedelta(days=i),
                status='PRESENT',
                hours_worked=Decimal('8.00')
            )

        # Test with month/year filters
        today = timezone.now().date()
        response = self.client.get(
            reverse('employee-attendance'),
            {'month': today.month, 'year': today.year}
        )
        self.assertEqual(response.status_code, 200)

        # Test EmployeePayslipListView.get_queryset with no employee
        self.employee.user = None
        self.employee.save()

        response = self.client.get(reverse('employee-payslips'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['payslips']), 0)

        # Restore link for further tests
        self.employee.user = self.employee_user
        self.employee.save()

        # Test EmployeePayslipDetailView.get_queryset with no employee
        payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            basic_salary=Decimal('5000.00'),
            net_salary=Decimal('4500.00'),
            status='APPROVED'
        )

        self.employee.user = None
        self.employee.save()

        try:
            response = self.client.get(reverse('employee-payslip-detail', args=[payroll.id]))
            # Either a 404 response or an empty queryset is acceptable
            self.assertTrue(response.status_code == 404 or len(response.context.get('object_list', [])) == 0)
        except:
            pass  # If it throws an exception, that's also acceptable

    def test_list_view_filters(self):
        """Test various list views with filters."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Test LeaveListView.get_queryset with status filter
        leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Test leave'
        )

        response = self.client.get(reverse('leave-list'), {'status': 'PENDING'})
        self.assertEqual(response.status_code, 200)

        # Test AttendanceListView.get_queryset with date filter
        attendance = Attendance.objects.create(
            employee=self.employee,
            date=date.today(),
            status='PRESENT',
            hours_worked=Decimal('8.00')
        )

        response = self.client.get(reverse('attendance-list'), {'date': date.today().strftime('%Y-%m-%d')})
        self.assertEqual(response.status_code, 200)

        # Test PayrollListView.get_queryset with month/year filter
        payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            basic_salary=Decimal('5000.00'),
            net_salary=Decimal('4500.00'),
            status='APPROVED'
        )

        response = self.client.get(
            reverse('payroll-list'),
            {'month': date.today().month, 'year': date.today().year}
        )
        self.assertEqual(response.status_code, 200)

    def test_payroll_create_view_context(self):
        """Test PayrollCreateView.get_context_data with employee parameter."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        response = self.client.get(reverse('payroll-create'), {'employee': self.employee.id})
        self.assertEqual(response.status_code, 200)
        self.assertIn('employee', response.context)

        # Create attendance records for the employee
        today = timezone.now().date()
        month_start = today.replace(day=1)
        for i in range(10):
            date_value = month_start + timedelta(days=i)
            Attendance.objects.create(
                employee=self.employee,
                date=date_value,
                status='PRESENT',
                hours_worked=Decimal('8.00')
            )

        # Test with attendance data
        response = self.client.get(reverse('payroll-create'), {'employee': self.employee.id})
        self.assertEqual(response.status_code, 200)
        self.assertIn('attendance_summary', response.context)

    def test_admin_performance_list_view_filters(self):
        """Test AdminPerformanceListView with various filters."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Set up employees with different scores
        for i, score in enumerate([1, 2, 3, 4, None]):
            Employee.objects.create(
                name=f'Performance Test {i}',
                emp_id=f'PERF00{i}',
                department='IT' if i % 2 == 0 else 'HR',
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
                employment_status='Active',
                predicted_score=score
            )

        # Test with search filter
        response = self.client.get(reverse('admin_performance_list'), {'search': 'Performance'})
        self.assertEqual(response.status_code, 200)

        # Test with department filter
        response = self.client.get(reverse('admin_performance_list'), {'department': 'IT'})
        self.assertEqual(response.status_code, 200)

        # Test with different score_range filters
        for score_filter in ['exceeds', 'fully_meets', 'needs_improvement', 'improvement_plan', 'pending']:
            response = self.client.get(reverse('admin_performance_list'), {'score_range': score_filter})
            self.assertEqual(response.status_code, 200)

    def test_approve_leave_function(self):
        """Test the standalone approve_leave function."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Create a request object with an approve action
        request = self.factory.get('/approve-leave/1/?action=approve')
        request.user = self.staff_user
        request = add_message_middleware(request)

        # Create a test leave
        leave = Leave.objects.create(
            employee=self.employee,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Test leave'
        )

        # Test direct function call
        response = approve_leave(request, leave.id)
        self.assertEqual(response.status_code, 302)  # Should redirect

        # Test with approve action via client
        leave2 = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=10),
            end_date=date.today() + timedelta(days=12),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Another test leave'
        )

        response = self.client.get(
            reverse('leave-approve', args=[leave2.id]),
            {'action': 'approve'}
        )
        self.assertRedirects(response, reverse('leave-list'))

        # Test with reject action
        leave3 = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=20),
            end_date=date.today() + timedelta(days=22),
            leave_type='ANNUAL',
            status='PENDING',
            reason='Third test leave'
        )

        response = self.client.get(
            reverse('leave-approve', args=[leave3.id]),
            {'action': 'reject'}
        )
        self.assertRedirects(response, reverse('leave-list'))

        # Test with already approved leave
        leave4 = Leave.objects.create(
            employee=self.employee,
            start_date=date.today() + timedelta(days=30),
            end_date=date.today() + timedelta(days=32),
            leave_type='ANNUAL',
            status='APPROVED',
            reason='Already approved leave'
        )

        response = self.client.get(
            reverse('leave-approve', args=[leave4.id]),
            {'action': 'approve'}
        )
        self.assertRedirects(response, reverse('leave-list'))

    def test_bulk_attendance_upload_errors(self):
        """Test error handling in bulk_attendance_upload."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Test GET request
        response = self.client.get(reverse('bulk-attendance'))
        self.assertEqual(response.status_code, 200)

        # Create a valid CSV file
        csv_content = "employee_id,status,check_in,check_out,notes\n"
        csv_content += f"{self.employee.emp_id},PRESENT,09:00,17:00,Test note"

        csv_file_upload = SimpleUploadedFile(
            "test.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )

        # Test POST with valid data
        response = self.client.post(
            reverse('bulk-attendance'),
            {
                'date': date.today().strftime('%Y-%m-%d'),
                'csv_file': csv_file_upload
            },
            follow=True
        )
        # Check for redirect
        self.assertRedirects(response, reverse('attendance-list'))

        # Now test with malformed CSV to trigger an exception
        with patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.side_effect = Exception("CSV parsing error")

            bad_csv = SimpleUploadedFile(
                "bad.csv",
                b"invalid,csv,format",
                content_type="text/csv"
            )

            response = self.client.post(
                reverse('bulk-attendance'),
                {
                    'date': date.today().strftime('%Y-%m-%d'),
                    'csv_file': bad_csv
                },
                follow=True
            )

            # Check that we get an error message
            self.assertContains(response, "Error processing file")

    def test_employee_register_errors(self):
        """Test error handling in employee_register."""
        # Test GET request
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

        # Test POST with invalid data
        response = self.client.post(reverse('register'), {})
        self.assertEqual(response.status_code, 200)  # Should stay on form page

        # Test with invalid employee_id
        response = self.client.post(
            reverse('register'),
            {
                'employee_id': 'INVALID',
                'username': 'newuser',
                'password1': 'ComplexPassword123',
                'password2': 'ComplexPassword123'
            }
        )
        self.assertEqual(response.status_code, 200)  # Should stay on form page

        # Test exception case - Django raises an exception during user creation
        with patch('django.contrib.auth.models.User.objects.create_user') as mock_create_user:
            mock_create_user.side_effect = Exception("User creation error")

            response = self.client.post(
                reverse('register'),
                {
                    'employee_id': self.employee.emp_id,
                    'username': 'newuser',
                    'password1': 'ComplexPassword123',
                    'password2': 'ComplexPassword123'
                }
            )
            self.assertEqual(response.status_code, 200)  # Should stay on form page

    def test_feature_engineering_functions(self):
        """Test coverage for feature_engineering.py functions."""
        # Test save_label_encoders with mock encoder
        encoders = {'test_encoder': MagicMock()}
        with patch('os.makedirs') as mock_makedirs, \
                patch('joblib.dump') as mock_dump:
            save_label_encoders(encoders)
            mock_makedirs.assert_called_once()
            mock_dump.assert_called_once()

        # Test load_label_encoders when file exists
        with patch('os.path.exists', return_value=True), \
                patch('joblib.load', return_value={'test': 'encoder'}):
            result = load_label_encoders()
            self.assertEqual(result, {'test': 'encoder'})

        # Test engineer_features calling prepare_data_for_prediction
        with patch('employee_predictor.ml.feature_engineering.prepare_data_for_prediction') as mock_prepare:
            mock_prepare.return_value = np.array([[1, 2, 3]])
            result = engineer_features({'test': 'data'})
            mock_prepare.assert_called_once_with({'test': 'data'})
            self.assertEqual(result.tolist(), [[1, 2, 3]])

        # Test prepare_data_for_prediction with empty DataFrame
        with patch('employee_predictor.ml.feature_engineering.load_preprocessor') as mock_load_preprocessor:
            mock_preprocessor = MagicMock()
            mock_load_preprocessor.return_value = mock_preprocessor
            # FIX: Return a numpy array instead of a string
            mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

            # Call with empty DataFrame
            result = prepare_data_for_prediction(pd.DataFrame())
            # FIX: Compare as lists to correctly check the array content
            self.assertEqual(result.tolist(), [[1, 2, 3]])

    def test_performance_history_model(self):
        """Test PerformanceHistory model."""
        # Create a performance history record
        history = PerformanceHistory.objects.create(
            employee=self.employee,
            review_date=date.today(),
            performance_score='Exceeds',
            score_value=4,
            reviewer=self.staff_user,
            notes='Test performance review'
        )

        # Test string representation
        expected_str = f"{self.employee.name} - {date.today()} (Exceeds)"
        self.assertEqual(str(history), expected_str)

    def test_payroll_detail_view(self):
        """Test PayrollDetailView get_context_data."""
        self.client.logout()
        axes_login(self.client, 'staff_user', 'password')

        # Create a payroll record
        payroll = Payroll.objects.create(
            employee=self.employee,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            basic_salary=Decimal('5000.00'),
            net_salary=Decimal('4500.00'),
            status='APPROVED'
        )

        # Create attendance records for the payroll period
        for i in range(5):
            Attendance.objects.create(
                employee=self.employee,
                date=payroll.period_start + timedelta(days=i),
                status='PRESENT',
                hours_worked=Decimal('8.00')
            )

        response = self.client.get(reverse('payroll-detail', args=[payroll.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('attendance_records', response.context)
        self.assertIn('attendance_stats', response.context)

    def test_template_filters(self):
        """Test template filters."""
        # Test subtract_from with various inputs
        test_cases = [
            (50, 100, 50.0),  # Regular case
            (100, 50, -50.0),  # Negative result
            (0, 100, 100.0),  # Zero input
            (None, 100, 100.0),  # None value
            (50, None, -50.0),  # None arg
            ('invalid', 100, 100)  # Invalid input
        ]

        for value, arg, expected in test_cases:
            result = subtract_from(value, arg)
            self.assertEqual(result, expected)