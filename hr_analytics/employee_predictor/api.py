# employee_predictor/api.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from datetime import datetime, date, timedelta
from django.http import Http404
from .models import Employee
from .utils import calculate_payroll_details


@login_required
@require_http_methods(["GET"])
def get_employee_salary_info(request, employee_id):
    """API endpoint to get employee salary information"""
    try:
        # Attempt to get the employee object
        try:
            employee = get_object_or_404(Employee, id=employee_id)
        except Http404:
            return JsonResponse({
                'error': f'Employee with ID {employee_id} not found'
            }, status=400)

        # Get date range from query parameters or use current month
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'error': 'Invalid date format. Please use YYYY-MM-DD.'
                }, status=400)
        else:
            today = date.today()
            start_date = date(today.year, today.month, 1)
            # Handle month rollover
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)

        # Calculate payroll details
        payroll_details = calculate_payroll_details(employee, start_date, end_date)

        # Return successful response
        return JsonResponse({
            'employee_id': employee.id,
            'name': employee.name,
            'salary': float(employee.salary),
            'department': employee.department,
            'overtime_rate': payroll_details['overtime_rate'],
            'overtime_hours': payroll_details['overtime_hours'],
            'estimated_tax': payroll_details['estimated_tax'],
            'attendance_stats': payroll_details['attendance_stats']
        })
    except Exception as e:
        # Catch any other exceptions and return 400 with error message
        return JsonResponse({'error': str(e)}, status=400)