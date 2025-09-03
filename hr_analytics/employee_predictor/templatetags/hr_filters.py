# employee_predictor/templatetags/hr_filters.py

from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        if value is None:
            value = 0
        if arg is None:
            arg = 0
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if value is None:
            value = 0
        if total is None or float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def subtract_from(value, arg):
    """Subtract value from argument"""
    try:
        if value is None:
            value = 0
        if arg is None:
            arg = 0
        return float(arg) - float(value)
    except (ValueError, TypeError):
        return arg  # Return arg instead of 0 for invalid values

@register.filter
def abs_value(value):
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value