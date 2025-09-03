# employee_predictor/utils.py
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Attendance, Leave


def calculate_payroll_details(employee, start_date, end_date):
    """Calculate payroll details for an employee within a date range"""

    # Get attendance records
    attendance_records = Attendance.objects.filter(
        employee=employee,
        date__range=[start_date, end_date]
    )

    # Calculate attendance statistics
    attendance_stats = attendance_records.aggregate(
        present_days=Count('id', filter=Q(status='PRESENT')),
        absent_days=Count('id', filter=Q(status='ABSENT')),
        late_days=Count('id', filter=Q(status='LATE')),
        total_hours=Sum('hours_worked')
    )

    # Convert None values to 0
    attendance_stats = {k: v or 0 for k, v in attendance_stats.items()}

    # Calculate overtime hours
    regular_hours = attendance_stats['present_days'] * 8  # 8 hours per working day
    total_hours = float(attendance_stats['total_hours'])
    overtime_hours = max(0, total_hours - regular_hours)

    # Calculate base overtime rate (1.5 times hourly rate)
    daily_rate = float(employee.salary) / 22  # Assuming 22 working days
    hourly_rate = daily_rate / 8
    overtime_rate = hourly_rate * 1.5

    # Calculate tax (simplified example - customize according to your tax rules)
    monthly_salary = float(employee.salary)
    tax_rate = 0.15 if monthly_salary > 5000 else 0.1  # Example tax brackets
    estimated_tax = monthly_salary * tax_rate

    return {
        'attendance_stats': attendance_stats,
        'overtime_hours': round(overtime_hours, 2),
        'overtime_rate': round(overtime_rate, 2),
        'estimated_tax': round(estimated_tax, 2),
    }