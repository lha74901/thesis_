# employee_predictor/forms.py
from django import forms
from django.contrib.auth.models import User

from .models import Payroll, Employee, Attendance, Leave
from django.utils import timezone

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'name', 'emp_id', 'department', 'position', 'date_of_hire',
            'gender', 'marital_status', 'age', 'race', 'hispanic_latino',
            'recruitment_source', 'salary', 'engagement_survey', 'emp_satisfaction',
            'special_projects_count', 'days_late_last_30', 'absences', 
            'performance_score', 'employment_status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter employee name'
            }),
            'emp_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter employee ID'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter department'
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter position'
            }),
            'date_of_hire': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'marital_status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'age': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '18',
                'max': '100'
            }),
            'race': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'hispanic_latino': forms.Select(attrs={
                'class': 'form-control'
            }),
            'recruitment_source': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01'
            }),
            'engagement_survey': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5',
                'step': '0.1'
            }),
            'emp_satisfaction': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5'
            }),
            'special_projects_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'days_late_last_30': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '30'
            }),
            'absences': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'performance_score': forms.Select(attrs={
                'class': 'form-control'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'form-control'
            })
        }

    def clean_engagement_survey(self):
        value = self.cleaned_data['engagement_survey']
        if value < 1 or value > 5:
            raise forms.ValidationError('Engagement survey score must be between 1 and 5')
        return value

    def clean_emp_satisfaction(self):
        value = self.cleaned_data['emp_satisfaction']
        if value < 1 or value > 5:
            raise forms.ValidationError('Employee satisfaction must be between 1 and 5')
        return value

    def clean_days_late_last_30(self):
        value = self.cleaned_data['days_late_last_30']
        if value < 0 or value > 30:
            raise forms.ValidationError('Days late must be between 0 and 30')
        return value


class LeaveForm(forms.ModelForm):
    class Meta:
        model = Leave
        fields = ['employee', 'start_date', 'end_date', 'leave_type', 'reason']
        widgets = {
            'employee': forms.HiddenInput(),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'leave_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        employee = cleaned_data.get('employee')

        if start_date and end_date:
            if end_date < start_date:
                raise forms.ValidationError("End date cannot be before start date")

            # Check for overlapping leaves
            if employee:
                overlapping = Leave.objects.filter(
                    employee=employee,
                    start_date__lte=end_date,
                    end_date__gte=start_date,
                    status__in=['PENDING', 'APPROVED']
                )
                if self.instance.pk:
                    overlapping = overlapping.exclude(pk=self.instance.pk)
                if overlapping.exists():
                    raise forms.ValidationError(
                        "There is already an active leave request for this period"
                    )

        return cleaned_data


class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['employee', 'date', 'check_in', 'check_out', 'status', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_in': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'check_out': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class PayrollForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = [
            'employee',
            'period_start',
            'period_end',
            'basic_salary',
            'overtime_hours',
            'overtime_rate',
            'bonuses',
            'deductions',
            'tax'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'period_start': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'period_end': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'basic_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'overtime_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'overtime_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'bonuses': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'deductions': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'tax': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        employee = cleaned_data.get('employee')

        if period_start and period_end:
            if period_end < period_start:
                raise forms.ValidationError("End date cannot be before start date")

            # Check for overlapping payroll periods for the same employee
            if employee:
                overlapping = Payroll.objects.filter(
                    employee=employee,
                    period_start__lte=period_end,
                    period_end__gte=period_start
                )
                if self.instance.pk:
                    overlapping = overlapping.exclude(pk=self.instance.pk)
                if overlapping.exists():
                    raise forms.ValidationError(
                        "There is already a payroll record for this employee during the selected period"
                    )

        return cleaned_data


class BulkAttendanceForm(forms.Form):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    csv_file = forms.FileField(help_text='Upload CSV file with employee attendance data')


class EmployeeRegistrationForm(forms.Form):
    employee_id = forms.CharField(
        label='Employee ID',
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean_employee_id(self):
        employee_id = self.cleaned_data.get('employee_id')
        try:
            employee = Employee.objects.get(emp_id=employee_id)
            if employee.user is not None:
                raise forms.ValidationError('This Employee ID is already registered.')
            return employee_id
        except Employee.DoesNotExist:
            raise forms.ValidationError('Invalid Employee ID.')

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data