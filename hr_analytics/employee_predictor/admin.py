# employee_predictor/admin.py
from django.contrib import admin
from .models import Employee, Attendance, Leave, Payroll

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'emp_id', 'department', 'position', 'predicted_score']
    search_fields = ['name', 'emp_id']
    list_filter = ['department', 'position']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'status', 'check_in', 'check_out']
    list_filter = ['status', 'date']
    search_fields = ['employee__name']

@admin.register(Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'leave_type']
    search_fields = ['employee__name']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['employee', 'period_start', 'period_end', 'net_salary', 'status']
    list_filter = ['status']
    search_fields = ['employee__name']