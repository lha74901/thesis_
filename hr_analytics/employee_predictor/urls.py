'''# employee_predictor/urls.py
from django.urls import path
from . import views, api

urlpatterns = [
    # Existing URLs
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('employees/', views.EmployeeListView.as_view(), name='employee-list'),
    path('employee/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    path('employee/<int:pk>/predict/', views.EmployeePredictionView.as_view(), name='employee-predict'),

    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance-list'),
    path('attendance/create/', views.AttendanceCreateView.as_view(), name='attendance-create'),
    path('attendance/<int:pk>/update/', views.AttendanceUpdateView.as_view(), name='attendance-update'),
    path('attendance/bulk-upload/', views.bulk_attendance_upload, name='bulk-attendance'),

    # Leave URLs
    path('leaves/', views.LeaveListView.as_view(), name='leave-list'),
    path('leave/create/', views.LeaveCreateView.as_view(), name='leave-create'),
    path('leave/<int:pk>/update/', views.LeaveUpdateView.as_view(), name='leave-update'),
    path('leave/<int:pk>/approve/', views.approve_leave, name='leave-approve'),

    # Payroll URLs
    path('payroll/', views.PayrollListView.as_view(), name='payroll-list'),
    path('payroll/create/', views.PayrollCreateView.as_view(), name='payroll-create'),
    path('payroll/<int:pk>/', views.PayrollDetailView.as_view(), name='payroll-detail'),
    path('payroll/<int:pk>/update/', views.PayrollUpdateView.as_view(), name='payroll-update'),
    path('payroll/<int:pk>/process/', views.process_payroll, name='payroll-process'),

    # API URLs
    path('api/employee/<int:employee_id>/salary/', api.get_employee_salary_info, name='api-employee-salary'),

    # Employee Portal URLs
    path('portal/', views.EmployeePortalView.as_view(), name='employee-portal'),
    path('portal/leaves/', views.EmployeeLeaveListView.as_view(), name='employee-leaves'),
    path('portal/leaves/create/', views.EmployeeLeaveCreateView.as_view(), name='employee-leave-create'),
    path('portal/attendance/', views.EmployeeAttendanceListView.as_view(), name='employee-attendance'),
    path('portal/payslips/', views.EmployeePayslipListView.as_view(), name='employee-payslips'),
    path('portal/payslips/<int:pk>/', views.EmployeePayslipDetailView.as_view(), name='employee-payslip-detail'),
    path('portal/profile/', views.EmployeeProfileView.as_view(), name='employee-profile'),
]'''

# employee_predictor/urls.py
from django.urls import path
from . import views, api
from .views import AdminPerformanceListView, AdminPerformanceView

urlpatterns = [
    # Admin URLs
    # Employee Management
    path('employees/', views.EmployeeListView.as_view(), name='employee-list'),
    path('employee/add/', views.EmployeeCreateView.as_view(), name='employee-create'),
    path('employee/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee-detail'),
    path('employee/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee-update'),
    path('employee/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee-delete'),
    path('employee/<int:pk>/predict/', views.EmployeePredictionView.as_view(), name='employee-predict'),

    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    # Leave Management
    path('leaves/', views.LeaveListView.as_view(), name='leave-list'),
    path('leave/create/', views.LeaveCreateView.as_view(), name='leave-create'),
    path('leave/<int:pk>/update/', views.LeaveUpdateView.as_view(), name='leave-update'),
    path('leave/<int:pk>/approve/', views.approve_leave, name='leave-approve'),

    # Attendance Management
    path('attendance/', views.AttendanceListView.as_view(), name='attendance-list'),
    path('attendance/create/', views.AttendanceCreateView.as_view(), name='attendance-create'),
    path('attendance/<int:pk>/update/', views.AttendanceUpdateView.as_view(), name='attendance-update'),
    path('attendance/bulk-upload/', views.bulk_attendance_upload, name='bulk-attendance'),

    # Payroll Management
    path('payroll/', views.PayrollListView.as_view(), name='payroll-list'),
    path('payroll/create/', views.PayrollCreateView.as_view(), name='payroll-create'),
    path('payroll/<int:pk>/', views.PayrollDetailView.as_view(), name='payroll-detail'),
    path('payroll/<int:pk>/update/', views.PayrollUpdateView.as_view(), name='payroll-update'),
    path('payroll/<int:pk>/process/', views.process_payroll, name='payroll-process'),

    # Employee Portal URLs
    path('portal/', views.EmployeePortalView.as_view(), name='employee-portal'),
    path('portal/attendance/', views.EmployeeAttendanceListView.as_view(), name='employee-attendance'),
    path('portal/leaves/', views.EmployeeLeaveListView.as_view(), name='employee-leaves'),
    path('portal/leaves/create/', views.EmployeeLeaveCreateView.as_view(), name='employee-leave-create'),
    path('portal/profile/', views.EmployeeProfileView.as_view(), name='employee-profile'),

    # Fix: Change these URL patterns for payslips
    path('payroll/employee/', views.EmployeePayslipListView.as_view(), name='employee-payslips'),
    path('payroll/employee/<int:pk>/', views.EmployeePayslipDetailView.as_view(), name='employee-payslip-detail'),


    path('portal/performance/', views.EmployeePerformanceView.as_view(), name='employee-performance'),

    # Performance URLs

    path('performance/', AdminPerformanceListView.as_view(), name='admin_performance_list'),
    path('performance/<int:pk>/', AdminPerformanceView.as_view(), name='admin_performance_detail'),
# API URLs
    path('api/employee/<int:employee_id>/salary/', api.get_employee_salary_info, name='api-employee-salary')

]