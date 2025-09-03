# employee_predictor/middleware.py
from django.shortcuts import redirect
from django.urls import resolve, reverse
from django.contrib import messages


class EmployeePortalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_staff:
            current_url = resolve(request.path_info).url_name
            admin_urls = ['employee-list', 'employee-detail', 'employee-predict',
                          'attendance-list', 'attendance-create', 'attendance-update',
                          'leave-list', 'leave-create', 'leave-update', 'leave-approve',
                          'payroll-list', 'payroll-create', 'payroll-detail', 'payroll-update']

            # If employee tries to access admin URLs, redirect to employee portal
            if current_url in admin_urls:
                messages.warning(request, 'Access denied. Redirecting to employee portal.')
                return redirect('employee-portal')

        response = self.get_response(request)
        return response