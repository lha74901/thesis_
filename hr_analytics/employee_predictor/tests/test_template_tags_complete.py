# employee_predictor/tests/test_template_tags_complete.py

from django.test import TestCase
from decimal import Decimal
from employee_predictor.templatetags.hr_filters import multiply, percentage, subtract_from, abs_value

class HRFiltersTest(TestCase):
    def test_multiply_filter_all_cases(self):
        """Test multiply filter with all possible input types."""
        # Test cases
        test_cases = [
            # (value, multiplier, expected)
            (5, 2, 10.0),
            (5.5, 2, 11.0),
            (Decimal('5.5'), 2, 11.0),
            (None, 5, 0),
            (5, None, 0),
            ('5', 2, 10.0),
            ('abc', 2, 0),
            (0, 2, 0),
            (-5, 2, -10.0)
        ]

        for value, multiplier, expected in test_cases:
            self.assertEqual(multiply(value, multiplier), expected)
