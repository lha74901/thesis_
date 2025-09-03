'''# employee_predictor/views.py
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
import pandas as pd
import logging
logger = logging.getLogger(__name__)
from . import forms
from .ml.predictor import PerformancePredictor
from .models import Employee, Attendance, Leave, Payroll
from .forms import (
    EmployeeForm, AttendanceForm, LeaveForm, PayrollForm,
    BulkAttendanceForm, EmployeeRegistrationForm
)
from .ml.feature_engineering import engineer_features'''
#from .ml.predictor import PerformancePredictor
import logging
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from django.contrib import messages
from datetime import timedelta
import pandas as pd

from . import forms
from .ml.enhanced_predictor import EnhancedPerformancePredictor  # CORRECT IMPORT
from .models import Employee, Attendance, Leave, Payroll
from .forms import (
    EmployeeForm, AttendanceForm, LeaveForm, PayrollForm,
    BulkAttendanceForm, EmployeeRegistrationForm
)

# Set up logging
logger = logging.getLogger(__name__)

# Mixins
class StaffRequiredMixin(UserPassesTestMixin):
    """Verify that the current user is staff."""

    def test_func(self):
        return self.request.user.is_staff


class EmployeeRequiredMixin(LoginRequiredMixin):
    """Verify that the current user is authenticated and is not staff."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_staff:
            messages.info(request, 'Staff members should use the admin dashboard.')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)


from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Avg, Q
from .models import Employee, Attendance

class EmployeePerformanceView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = 'employee_predictor/employee_portal/performance_detail.html'
    context_object_name = 'employee'

    def get_object(self):
        return Employee.objects.get(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Get attendance statistics for current month
        context['attendance_stats'] = Attendance.objects.filter(
            employee=self.object,
            date__gte=month_start,
            date__lte=today
        ).aggregate(
            present_days=Count('id', filter=Q(status='PRESENT')),
            late_days=Count('id', filter=Q(status='LATE')),
            absent_days=Count('id', filter=Q(status='ABSENT')),
            on_leave_days=Count('id', filter=Q(status='ON_LEAVE')),
            avg_hours=Avg('hours_worked')
        )

        return context


class AdminPerformanceListView(StaffRequiredMixin, ListView):
    model = Employee
    template_name = 'employee_predictor/performance_list.html'
    context_object_name = 'employees'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        # Search filter
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(emp_id__icontains=search_query)
            )

        # Department filter
        department = self.request.GET.get('department', '').strip()
        if department:
            queryset = queryset.filter(department=department)

        # Score range filter
        score_range = self.request.GET.get('score_range', '').strip()
        if score_range:
            if score_range == 'exceeds':
                queryset = queryset.filter(predicted_score=4.0)
            elif score_range == 'fully_meets':
                queryset = queryset.filter(predicted_score=3.0)

            elif score_range == 'needs_improvement':
                queryset = queryset.filter(predicted_score=2.0)

            elif score_range == 'improvement_plan':
                queryset = queryset.filter(predicted_score=1.0)
            elif score_range == 'pending':
                queryset = queryset.filter(predicted_score__isnull=True)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all employees for statistics (before pagination)
        all_employees = self.get_queryset()

        # Calculate summary statistics
        context.update({
            'avg_performance': all_employees.exclude(
                predicted_score__isnull=True
            ).aggregate(
                avg=Avg('predicted_score')
            )['avg'],
            'top_performers_count': all_employees.filter(
                predicted_score=4
            ).count(),
            'meets_expectations_count': all_employees.filter(
                predicted_score=3
            ).count(),
            'needs_improvement_count': all_employees.filter(
                predicted_score=2
            ).count(),
            'pip_count': all_employees.filter(
                predicted_score=1
            ).count(),
            'pending_reviews_count': all_employees.filter(
                predicted_score__isnull=True
            ).count(),
        })

        # Add filter parameters to context for form persistence
        context.update({
            'search_query': self.request.GET.get('search', ''),
            'selected_department': self.request.GET.get('department', ''),
            'selected_score_range': self.request.GET.get('score_range', ''),
        })

        return context

class AdminPerformanceView(StaffRequiredMixin, DetailView):
    model = Employee
    template_name = 'employee_predictor/performance_detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        current_month_start = today.replace(day=1)
        prev_month_end = current_month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        employee = self.object

        # Current month statistics
        current_month_stats = Attendance.objects.filter(
            employee=employee,
            date__range=[current_month_start, today]
        ).aggregate(
            present_days=Count('id', filter=Q(status='PRESENT')),
            late_days=Count('id', filter=Q(status='LATE')),
            absent_days=Count('id', filter=Q(status='ABSENT')),
            on_leave_days=Count('id', filter=Q(status='ON_LEAVE')),
            avg_hours=Avg('hours_worked')
        )

        # Calculate attendance rate
        working_days = (today - current_month_start).days + 1
        present_days = current_month_stats['present_days'] or 0
        current_month_stats['attendance_rate'] = (present_days / working_days) * 100 if working_days > 0 else 0

        # Previous month statistics
        prev_month_stats = Attendance.objects.filter(
            employee=employee,
            date__range=[prev_month_start, prev_month_end]
        ).aggregate(
            present_days=Count('id', filter=Q(status='PRESENT')),
            late_days=Count('id', filter=Q(status='LATE')),
            absent_days=Count('id', filter=Q(status='ABSENT')),
            on_leave_days=Count('id', filter=Q(status='ON_LEAVE')),
            avg_hours=Avg('hours_worked')
        )

        # Calculate previous month attendance rate
        prev_month_working_days = (prev_month_end - prev_month_start).days + 1
        prev_month_present_days = prev_month_stats['present_days'] or 0
        prev_month_stats['attendance_rate'] = (prev_month_present_days / prev_month_working_days) * 100 if prev_month_working_days > 0 else 0

        # Make sure all values exist to prevent template errors
        attendance_stats = {
            'present_days': current_month_stats['present_days'] or 0,
            'late_days': current_month_stats['late_days'] or 0,
            'absent_days': current_month_stats['absent_days'] or 0,
            'on_leave_days': current_month_stats['on_leave_days'] or 0,
        }

        context.update({
            'attendance_stats': attendance_stats,
            'current_month_stats': current_month_stats,
            'prev_month_stats': prev_month_stats,
        })

        return context

#Start OF CRUD for EMP in Admin
class EmployeeListView(StaffRequiredMixin, ListView):
    model = Employee
    template_name = 'employee_predictor/employee/list.html'
    context_object_name = 'employees'
    paginate_by = 10

    def get_queryset(self):
        queryset = Employee.objects.all()
        search = self.request.GET.get('search')
        department = self.request.GET.get('department')

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(emp_id__icontains=search) |
                Q(position__icontains=search)
            )
        if department:
            queryset = queryset.filter(department=department)

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Employee.objects.values_list('department', flat=True).distinct()
        return context


class EmployeeDetailView(StaffRequiredMixin, DetailView):
    model = Employee
    template_name = 'employee_predictor/employee/detail.html'
    context_object_name = 'employee'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object

        # Get recent attendance
        context['recent_attendance'] = Attendance.objects.filter(
            employee=employee
        ).order_by('-date')[:5]

        # Get leave history
        context['leaves'] = Leave.objects.filter(
            employee=employee
        ).order_by('-start_date')[:5]

        # Get payroll history
        context['payrolls'] = Payroll.objects.filter(
            employee=employee
        ).order_by('-period_end')[:5]

        return context


class EmployeeCreateView(StaffRequiredMixin, CreateView):
    model = Employee
    template_name = 'employee_predictor/employee/form.html'
    success_url = reverse_lazy('employee-list')
    fields = [
        'name', 'emp_id', 'department', 'position', 'date_of_hire',
        'salary', 'engagement_survey', 'emp_satisfaction',
        'special_projects_count', 'days_late_last_30', 'absences'
    ]

    def form_valid(self, form):
        messages.success(self.request, 'Employee created successfully.')
        return super().form_valid(form)


class EmployeeUpdateView(StaffRequiredMixin, UpdateView):
    model = Employee
    template_name = 'employee_predictor/employee/form.html'
    success_url = reverse_lazy('employee-list')
    fields = [
        'name', 'emp_id', 'department', 'position', 'date_of_hire',
        'salary', 'engagement_survey', 'emp_satisfaction',
        'special_projects_count', 'days_late_last_30', 'absences'
    ]

    def form_valid(self, form):
        messages.success(self.request, 'Employee updated successfully.')
        return super().form_valid(form)


class EmployeeDeleteView(StaffRequiredMixin, DeleteView):
    model = Employee
    template_name = 'employee_predictor/employee/confirm_delete.html'
    success_url = reverse_lazy('employee-list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Employee deleted successfully.')
        return super().delete(request, *args, **kwargs)

#end of CRUD for EMP in Admin

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'employee_predictor/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # Redirect employees to employee portal
        if not request.user.is_staff:
            return redirect('employee-portal')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Employee statistics
        context['total_employees'] = Employee.objects.count()
        context['departments'] = Employee.objects.values('department').annotate(
            count=Count('id'),
            avg_salary=Avg('salary')
        )

        # Today's attendance
        context['today_attendance'] = Attendance.objects.filter(date=today).aggregate(
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            late=Count('id', filter=Q(status='LATE')),
            on_leave=Count('id', filter=Q(status='ON_LEAVE'))
        )

        # Pending leaves
        context['pending_leaves'] = Leave.objects.filter(status='PENDING').count()
        context['active_leaves'] = Leave.objects.filter(
            status='APPROVED',
            start_date__lte=today,
            end_date__gte=today
        ).count()

        # Payroll statistics for current month
        context['payroll_stats'] = Payroll.objects.filter(
            period_start__month=today.month,
            period_start__year=today.year
        ).aggregate(
            total=Sum('net_salary'),
            count=Count('id')
        )

        return context
'''
# Admin/Manager Views
class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = 'employee_predictor/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Employee statistics
        context['total_employees'] = Employee.objects.count()
        context['departments'] = Employee.objects.values('department').annotate(
            count=Count('id'),
            avg_salary=Avg('salary')
        )

        # Today's attendance
        context['today_attendance'] = Attendance.objects.filter(date=today).aggregate(
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            late=Count('id', filter=Q(status='LATE')),
            on_leave=Count('id', filter=Q(status='ON_LEAVE'))
        )
        
        # Pending leaves
        context['pending_leaves'] = Leave.objects.filter(status='PENDING').count()

        # This month's payroll
        context['this_month_payroll'] = Payroll.objects.filter(
            period_start__month=today.month,
            period_start__year=today.year
        ).aggregate(
            total=Sum('net_salary'),
            count=Count('id')
        )

        return context


class EmployeeListView(StaffRequiredMixin, ListView):
    model = Employee
    template_name = 'employee_predictor/employee_list.html'
    context_object_name = 'employees'
    paginate_by = 10


class EmployeeDetailView(StaffRequiredMixin, DetailView):
    model = Employee
    template_name = 'employee_predictor/employee_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        today = timezone.now().date()
        month_start = today.replace(day=1)

        # Get attendance statistics
        context['attendance_stats'] = Attendance.objects.filter(
            employee=employee,
            date__gte=month_start
        ).aggregate(
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            late=Count('id', filter=Q(status='LATE')),
            on_leave=Count('id', filter=Q(status='ON_LEAVE'))
        )

        # Get recent attendance
        context['recent_attendance'] = Attendance.objects.filter(
            employee=employee
        ).order_by('-date')[:5]

        # Get leave history
        context['leaves'] = Leave.objects.filter(employee=employee).order_by('-start_date')[:5]

        return context
'''


class EmployeePredictionView(StaffRequiredMixin, UpdateView):
    model = Employee
    template_name = 'employee_predictor/prediction_form.html'
    form_class = EmployeeForm

    def form_valid(self, form):
        """Handle valid form submission and make prediction"""
        employee = form.save(commit=False)

        try:
            # Prepare data for prediction with proper error handling
            employee_data = self._prepare_employee_data(employee)

            # Make prediction using enhanced predictor
            predictor = EnhancedPerformancePredictor()
            prediction_results = predictor.predict_with_probability(employee_data)

            # Save prediction results
            self._save_prediction_results(employee, prediction_results)

            # Create success message with detailed information
            self._create_success_message(prediction_results)

            return redirect('employee-detail', pk=employee.pk)

        except Exception as e:
            logger.error(f"Error during prediction for employee {employee.emp_id}: {str(e)}")
            messages.error(
                self.request,
                f'Error making prediction: {str(e)}. The employee data has been saved, but prediction could not be completed.'
            )
            employee.save()  # Save employee data even if prediction fails
            return redirect('employee-detail', pk=employee.pk)

    def _prepare_employee_data(self, employee):
        """Prepare employee data for prediction"""
        try:
            # Convert employee object to dictionary for prediction
            employee_data = {
                'emp_id': employee.emp_id,
                'name': employee.name,
                'date_of_hire': employee.date_of_hire,
                'department': employee.department,
                'position': employee.position,
                'gender': employee.gender,
                'marital_status': employee.marital_status,
                'age': employee.age,
                'race': employee.race,
                'hispanic_latino': employee.hispanic_latino,
                'recruitment_source': employee.recruitment_source,
                'salary': float(employee.salary) if employee.salary else 0,
                'engagement_survey': float(employee.engagement_survey) if employee.engagement_survey else 3.0,
                'emp_satisfaction': int(employee.emp_satisfaction) if employee.emp_satisfaction else 3,
                'special_projects_count': int(
                    employee.special_projects_count) if employee.special_projects_count else 0,
                'days_late_last_30': int(employee.days_late_last_30) if employee.days_late_last_30 else 0,
                'absences': int(employee.absences) if employee.absences else 0,
                'employment_status': employee.employment_status
            }

            # Log the data being used for prediction (excluding sensitive info)
            logger.info(f"Preparing prediction for employee {employee.emp_id}")
            logger.debug(f"Key metrics - Engagement: {employee_data['engagement_survey']}, "
                         f"Satisfaction: {employee_data['emp_satisfaction']}, "
                         f"Absences: {employee_data['absences']}, "
                         f"Days Late: {employee_data['days_late_last_30']}")

            return employee_data

        except Exception as e:
            logger.error(f"Error preparing employee data: {str(e)}")
            raise Exception(f"Failed to prepare employee data for prediction: {str(e)}")

    def _save_prediction_results(self, employee, prediction_results):
        """Save prediction results to employee object"""
        try:
            if not prediction_results or 'prediction' not in prediction_results:
                raise Exception("Invalid prediction results received")

            # Save basic prediction info
            employee.predicted_score = prediction_results['prediction']
            employee.prediction_date = timezone.now()

            # Save confidence score if available
            probabilities = prediction_results.get('probabilities', {})
            if probabilities and employee.predicted_score in probabilities:
                employee.prediction_confidence = probabilities[employee.predicted_score]

            # Save detailed prediction information as JSON
            import json
            employee.prediction_details = json.dumps({
                'prediction_score': prediction_results['prediction'],
                'prediction_label': prediction_results.get('prediction_label', ''),
                'probabilities': probabilities,
                'key_factors': prediction_results.get('key_factors', []),
                'prediction_method': 'enhanced_predictor',
                'timestamp': timezone.now().isoformat()
            })

            # Map prediction score to performance_score field for database compatibility
            score_mapping = {
                1: 'PIP',
                2: 'Needs Improvement',
                3: 'Fully Meets',
                4: 'Exceeds'
            }

            if employee.predicted_score in score_mapping:
                employee.performance_score = score_mapping[employee.predicted_score]

            # Save the employee object
            employee.save()

            logger.info(f"Prediction saved for employee {employee.emp_id}: "
                        f"Score={employee.predicted_score}, "
                        f"Performance={employee.performance_score}")

        except Exception as e:
            logger.error(f"Error saving prediction results: {str(e)}")
            raise Exception(f"Failed to save prediction results: {str(e)}")

    def _create_success_message(self, prediction_results):
        """Create detailed success message for the user"""
        try:
            prediction_score = prediction_results.get('prediction', 0)
            prediction_label = prediction_results.get('prediction_label', 'Unknown')
            probabilities = prediction_results.get('probabilities', {})
            key_factors = prediction_results.get('key_factors', [])

            # Create main success message
            main_message = f"Performance prediction completed: {prediction_label} (Score: {prediction_score})"

            # Add probability information
            if probabilities:
                prob_strings = []
                for score in sorted(probabilities.keys()):
                    label_mapping = {1: "PIP", 2: "Needs Improvement", 3: "Fully Meets", 4: "Exceeds"}
                    label = label_mapping.get(score, f"Score {score}")
                    prob = probabilities[score] * 100
                    prob_strings.append(f"{label}: {prob:.1f}%")

                prob_message = "Probabilities: " + ", ".join(prob_strings)
            else:
                prob_message = "Probabilities not available"

            # Add key factors
            if key_factors:
                factors_message = "Key influencing factors: " + "; ".join(key_factors)
            else:
                factors_message = "Key factors analysis not available"

            # Create combined message
            full_message = f"{main_message}. {prob_message}. {factors_message}"

            messages.success(self.request, full_message)

            # Also add individual messages for better readability
            messages.info(self.request, prob_message)
            if key_factors:
                messages.info(self.request, factors_message)

        except Exception as e:
            logger.error(f"Error creating success message: {str(e)}")
            # Fallback to simple message
            messages.success(self.request, "Performance prediction completed successfully.")

    def get_context_data(self, **kwargs):
        """Add additional context for the template"""
        context = super().get_context_data(**kwargs)

        # Add information about the prediction process
        context['prediction_info'] = {
            'model_available': hasattr(self, '_check_model_availability') and self._check_model_availability(),
            'last_prediction': self.object.prediction_date,
            'current_score': self.object.predicted_score,
            'performance_mapping': {
                1: "PIP - Performance Improvement Plan",
                2: "Needs Improvement",
                3: "Fully Meets Expectations",
                4: "Exceeds Expectations"
            }
        }

        return context

    def _check_model_availability(self):
        """Check if ML model is available"""
        try:
            from .ml.enhanced_predictor import EnhancedPerformancePredictor
            predictor = EnhancedPerformancePredictor()
            return predictor.model is not None
        except:
            return False


# Employee Portal Views
class EmployeePortalView(EmployeeRequiredMixin, TemplateView):
    template_name = 'employee_predictor/employee_portal/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            employee = Employee.objects.get(user=self.request.user)
            today = timezone.now().date()
            month_start = today.replace(day=1)

            # Get attendance statistics
            context['attendance_stats'] = Attendance.objects.filter(
                employee=employee,
                date__range=[month_start, today]
            ).aggregate(
                present=Count('id', filter=Q(status='PRESENT')),
                absent=Count('id', filter=Q(status='ABSENT')),
                late=Count('id', filter=Q(status='LATE')),
                on_leave=Count('id', filter=Q(status='ON_LEAVE'))
            )

            # Get pending leave requests
            context['pending_leaves'] = Leave.objects.filter(
                employee=employee,
                status='PENDING'
            )

            # Get approved upcoming leaves
            context['upcoming_leaves'] = Leave.objects.filter(
                employee=employee,
                status='APPROVED',
                end_date__gte=today
            ).order_by('start_date')

            # Get recent payslips
            context['recent_payslips'] = Payroll.objects.filter(
                employee=employee,
                status__in=['APPROVED', 'PAID']
            ).order_by('-period_end')[:3]

            context['employee'] = employee
            context['month_name'] = today.strftime('%B %Y')

        except Employee.DoesNotExist:
            messages.error(self.request, 'No employee record found for your account.')

        return context


class EmployeeLeaveListView(EmployeeRequiredMixin, ListView):
    template_name = 'employee_predictor/employee_portal/leave_list.html'
    context_object_name = 'leaves'
    paginate_by = 10

    def get_queryset(self):
        try:
            employee = Employee.objects.get(user=self.request.user)
            return Leave.objects.filter(employee=employee).order_by('-start_date')
        except Employee.DoesNotExist:
            return Leave.objects.none()


'''class EmployeeLeaveCreateView(EmployeeRequiredMixin, CreateView):
    model = Leave
    form_class = LeaveForm
    template_name = 'employee_predictor/employee_portal/leave_form.html'
    success_url = reverse_lazy('employee-leaves')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        employee = Employee.objects.get(user=self.request.user)
        form.initial['employee'] = employee
        form.fields['employee'].widget = forms.HiddenInput()
        return form

    def form_valid(self, form):
        form.instance.employee = Employee.objects.get(user=self.request.user)
        form.instance.status = 'PENDING'
        messages.success(self.request, 'Leave request submitted successfully.')
        return super().form_valid(form)'''

class EmployeeLeaveCreateView(LoginRequiredMixin, CreateView):
    model = Leave
    form_class = LeaveForm
    template_name = 'employee_predictor/employee_portal/leave_form.html'
    success_url = reverse_lazy('employee-leaves')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        employee = Employee.objects.get(user=self.request.user)
        form.initial['employee'] = employee
        return form

    def form_valid(self, form):
        form.instance.employee = Employee.objects.get(user=self.request.user)
        form.instance.status = 'PENDING'
        messages.success(self.request, 'Leave request submitted successfully.')
        return super().form_valid(form)


class EmployeeAttendanceListView(EmployeeRequiredMixin, ListView):
    template_name = 'employee_predictor/employee_portal/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 31

    def get_queryset(self):
        try:
            employee = Employee.objects.get(user=self.request.user)
            queryset = Attendance.objects.filter(employee=employee)

            month = self.request.GET.get('month')
            year = self.request.GET.get('year')

            if month and year:
                queryset = queryset.filter(date__month=month, date__year=year)
            else:
                today = timezone.now()
                queryset = queryset.filter(date__month=today.month, date__year=today.year)

            return queryset.order_by('-date')
        except Employee.DoesNotExist:
            return Attendance.objects.none()


class EmployeePayslipListView(EmployeeRequiredMixin, ListView):
    template_name = 'employee_predictor/employee_portal/payslip_list.html'
    context_object_name = 'payslips'
    paginate_by = 12

    def get_queryset(self):
        try:
            employee = Employee.objects.get(user=self.request.user)
            return Payroll.objects.filter(
                employee=employee,
                status__in=['APPROVED', 'PAID']
            ).order_by('-period_end')
        except Employee.DoesNotExist:
            return Payroll.objects.none()


class EmployeePayslipDetailView(EmployeeRequiredMixin, DetailView):
    model = Payroll
    template_name = 'employee_predictor/employee_portal/payslip_detail.html'
    context_object_name = 'payslip'

    def get_queryset(self):
        try:
            employee = Employee.objects.get(user=self.request.user)
            return Payroll.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return Payroll.objects.none()


class EmployeeProfileView(EmployeeRequiredMixin, DetailView):
    template_name = 'employee_predictor/employee_portal/profile.html'
    context_object_name = 'employee'

    def get_object(self):
        return get_object_or_404(Employee, user=self.request.user)


# Admin Function-Based Views
@staff_member_required
def approve_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    action = request.GET.get('action')

    if action == 'approve':
        leave.status = 'APPROVED'
        leave.approved_by = request.user
        leave.save()

        # Create attendance records for approved leave
        current_date = leave.start_date
        while current_date <= leave.end_date:
            Attendance.objects.create(
                employee=leave.employee,
                date=current_date,
                status='ON_LEAVE',
                notes=f"On {leave.leave_type}"
            )
            current_date += timedelta(days=1)

        messages.success(request, 'Leave request approved successfully.')

    elif action == 'reject':
        leave.status = 'REJECTED'
        leave.approved_by = request.user
        leave.save()
        messages.success(request, 'Leave request rejected.')

    return redirect('leave-list')


@staff_member_required
def process_payroll(request, pk):
    payroll = get_object_or_404(Payroll, pk=pk)
    if payroll.status == 'DRAFT':
        payroll.status = 'APPROVED'
        payroll.payment_date = timezone.now().date()
        payroll.save()
        messages.success(request, 'Payroll processed successfully.')
    return redirect('payroll-detail', pk=payroll.pk)


@staff_member_required
def bulk_attendance_upload(request):
    if request.method == 'POST':
        form = BulkAttendanceForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                date = form.cleaned_data['date']
                df = pd.read_csv(request.FILES['csv_file'])
                success_count = 0
                error_count = 0

                for _, row in df.iterrows():
                    try:
                        employee = Employee.objects.get(emp_id=row['employee_id'])
                        Attendance.objects.update_or_create(
                            employee=employee,
                            date=date,
                            defaults={
                                'status': row['status'].upper(),
                                'check_in': row.get('check_in'),
                                'check_out': row.get('check_out'),
                                'notes': row.get('notes', '')
                            }
                        )
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        messages.error(request, f'Error processing record: {str(e)}')

                if success_count > 0:
                    messages.success(request, f'Successfully processed {success_count} attendance records.')
                if error_count > 0:
                    messages.warning(request, f'Failed to process {error_count} records.')

                return redirect('attendance-list')
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
    else:
        form = BulkAttendanceForm()

    return render(request, 'employee_predictor/bulk_attendance_upload.html', {'form': form})

# Then add to employee_predictor/views.py:
def employee_register(request):
    if request.method == 'POST':
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create user
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1']
                )

                # Link user to employee
                employee = Employee.objects.get(emp_id=form.cleaned_data['employee_id'])
                employee.user = user
                employee.save()

                messages.success(request, 'Registration successful! Please login.')
                return redirect('login')

            except Exception as e:
                messages.error(request, f'Error during registration: {str(e)}')
                return render(request, 'employee_predictor/registration/register.html', {'form': form})
    else:
        form = EmployeeRegistrationForm()

    return render(request, 'employee_predictor/registration/register.html', {'form': form})


# Leave Management Views
class LeaveListView(StaffRequiredMixin, ListView):
    model = Leave
    template_name = 'employee_predictor/leave_list.html'
    context_object_name = 'leaves'
    paginate_by = 10

    def get_queryset(self):
        queryset = Leave.objects.select_related('employee', 'approved_by').order_by('-start_date')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status.upper())
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = Leave.objects.filter(status='PENDING').count()
        return context


class LeaveCreateView(StaffRequiredMixin, CreateView):
    model = Leave
    form_class = LeaveForm
    template_name = 'employee_predictor/leave_form.html'
    success_url = reverse_lazy('leave-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Leave request created successfully.')
        return response


class LeaveUpdateView(StaffRequiredMixin, UpdateView):
    model = Leave
    form_class = LeaveForm
    template_name = 'employee_predictor/leave_form.html'
    success_url = reverse_lazy('leave-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Leave request updated successfully.')
        return response


# Attendance Management Views
class AttendanceListView(StaffRequiredMixin, ListView):
    model = Attendance
    template_name = 'employee_predictor/attendance_list.html'
    context_object_name = 'attendances'
    paginate_by = 20

    def get_queryset(self):
        queryset = Attendance.objects.select_related('employee').order_by('-date')
        date = self.request.GET.get('date')
        if date:
            queryset = queryset.filter(date=date)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        context['today_stats'] = Attendance.objects.filter(date=today).aggregate(
            present=Count('id', filter=Q(status='PRESENT')),
            absent=Count('id', filter=Q(status='ABSENT')),
            late=Count('id', filter=Q(status='LATE')),
            on_leave=Count('id', filter=Q(status='ON_LEAVE'))
        )
        return context


class AttendanceCreateView(StaffRequiredMixin, CreateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'employee_predictor/attendance_form.html'
    success_url = reverse_lazy('attendance-list')

    def form_valid(self, form):
        attendance = form.save(commit=False)
        if attendance.check_out and attendance.status == 'PRESENT':
            attendance.hours_worked = attendance.calculate_hours_worked()
        attendance.save()
        messages.success(self.request, 'Attendance record created successfully.')
        return super().form_valid(form)


class AttendanceUpdateView(StaffRequiredMixin, UpdateView):
    model = Attendance
    form_class = AttendanceForm
    template_name = 'employee_predictor/attendance_form.html'
    success_url = reverse_lazy('attendance-list')

    def form_valid(self, form):
        attendance = form.save(commit=False)
        if attendance.check_out and attendance.status == 'PRESENT':
            attendance.hours_worked = attendance.calculate_hours_worked()
        attendance.save()
        messages.success(self.request, 'Attendance record updated successfully.')
        return super().form_valid(form)


# Payroll Management Views
class PayrollListView(StaffRequiredMixin, ListView):
    model = Payroll
    template_name = 'employee_predictor/payroll_list.html'
    context_object_name = 'payrolls'
    paginate_by = 10

    def get_queryset(self):
        queryset = Payroll.objects.select_related('employee').order_by('-period_end')
        month = self.request.GET.get('month')
        year = self.request.GET.get('year')
        if month and year:
            queryset = queryset.filter(period_start__month=month, period_start__year=year)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_payroll'] = self.get_queryset().aggregate(
            total=Sum('net_salary'),
            count=Count('id')
        )
        return context


class PayrollCreateView(StaffRequiredMixin, CreateView):
    model = Payroll
    form_class = PayrollForm
    template_name = 'employee_predictor/payroll_form.html'
    success_url = reverse_lazy('payroll-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'employee' in self.request.GET:
            try:
                employee = Employee.objects.get(pk=self.request.GET['employee'])
                context['employee'] = employee
                # Calculate default values based on attendance
                today = timezone.now().date()
                month_start = today.replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                attendance = Attendance.objects.filter(
                    employee=employee,
                    date__range=[month_start, month_end],
                    status='PRESENT'
                )
                total_hours = attendance.aggregate(Sum('hours_worked'))['hours_worked__sum'] or 0
                regular_hours = attendance.count() * 8
                overtime_hours = max(0, total_hours - regular_hours)

                context['attendance_summary'] = {
                    'working_days': attendance.count(),
                    'total_hours': total_hours,
                    'overtime_hours': overtime_hours
                }
            except Employee.DoesNotExist:
                pass
        return context

    def form_valid(self, form):
        payroll = form.save(commit=False)
        payroll.net_salary = payroll.calculate_net_salary()
        payroll.save()
        messages.success(self.request, 'Payroll record created successfully.')
        return super().form_valid(form)


class PayrollDetailView(StaffRequiredMixin, DetailView):
    model = Payroll
    template_name = 'employee_predictor/payroll_detail.html'
    context_object_name = 'payroll'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payroll = self.get_object()

        # Get attendance records for payroll period
        context['attendance_records'] = Attendance.objects.filter(
            employee=payroll.employee,
            date__range=[payroll.period_start, payroll.period_end]
        ).order_by('date')

        # Calculate attendance statistics
        context['attendance_stats'] = context['attendance_records'].aggregate(
            present_days=Count('id', filter=Q(status='PRESENT')),
            absent_days=Count('id', filter=Q(status='ABSENT')),
            late_days=Count('id', filter=Q(status='LATE')),
            leave_days=Count('id', filter=Q(status='ON_LEAVE')),
            total_hours=Sum('hours_worked')
        )

        return context


class PayrollUpdateView(StaffRequiredMixin, UpdateView):
    model = Payroll
    form_class = PayrollForm
    template_name = 'employee_predictor/payroll_form.html'
    success_url = reverse_lazy('payroll-list')

    def dispatch(self, request, *args, **kwargs):
        payroll = self.get_object()
        if payroll.status != 'DRAFT':
            messages.error(request, 'Only draft payrolls can be edited.')
            return redirect('payroll-list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        payroll = form.save(commit=False)
        payroll.net_salary = payroll.calculate_net_salary()
        payroll.save()
        messages.success(self.request, 'Payroll record updated successfully.')
        return super().form_valid(form)

# In views.py
@staff_member_required
def approve_leave(request, pk):
    leave = get_object_or_404(Leave, pk=pk)
    action = request.GET.get('action')

    if action == 'approve' and leave.status != 'APPROVED':
        leave.status = 'APPROVED'
        leave.approved_by = request.user
        leave.save()

        # Create attendance records for approved leave
        current_date = leave.start_date
        while current_date <= leave.end_date:
            # Check if record already exists
            Attendance.objects.get_or_create(
                employee=leave.employee,
                date=current_date,
                defaults={
                    'status': 'ON_LEAVE',
                    'notes': f"On {leave.leave_type}"
                }
            )
            current_date += timedelta(days=1)

        messages.success(request, 'Leave request approved successfully.')

    elif action == 'reject':
        leave.status = 'REJECTED'
        leave.approved_by = request.user
        leave.save()
        messages.success(request, 'Leave request rejected.')

    return redirect('leave-list')