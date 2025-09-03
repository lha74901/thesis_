# employee_predictor/tests/test_template_tags.py
from django.test import TestCase
from decimal import Decimal
from employee_predictor.templatetags.hr_filters import percentage, subtract_from, abs_value

class HRFiltersCompleteTest(TestCase):
    def test_percentage_filter(self):
        """Test percentage filter with all possible input types."""
        # Test cases: (value, total, expected)
        test_cases = [
            (50, 100, 50.0),
            (25, 50, 50.0),
            (10, 0, 0),  # Division by zero
            (None, 100, 0),
            (50, None, 0),
            ('50', '100', 50.0),
            ('invalid', 100, 0),
            (0, 100, 0),
            (100, 100, 100.0)
        ]

        for value, total, expected in test_cases:
            self.assertEqual(percentage(value, total), expected)

    # In test_template_tags.py
    def test_subtract_from_filter(self):
        """Test subtract_from filter with all possible input types."""
        # Test cases: (value, arg, expected)
        test_cases = [
            (50, 100, 50.0),
            (100, 50, -50.0),
            (0, 100, 100.0),  # ← FIXED: Changed expected value from 0 to 100.0
            (None, 100, 100.0),
            (50, None, -50.0),
            ('50', '100', 50.0),
            ('invalid', 100, 100),  # ← FIXED: Changed from 0 to 100
            (Decimal('50.5'), 100, 49.5)
        ]

        for value, arg, expected in test_cases:
            self.assertEqual(subtract_from(value, arg), expected)

    def test_abs_value_filter(self):
        """Test abs_value filter."""
        # Test cases: (value, expected)
        test_cases = [
            (50, 50),
            (-50, 50),
            (0, 0),
            (None, None),  # Should return value as is for non-numeric
            ('50', 50.0),
            ('-50', 50.0),
            ('invalid', 'invalid'),  # Should return value as is
            (Decimal('-50.5'), 50.5)
        ]

        for value, expected in test_cases:
            result = abs_value(value)
            if isinstance(expected, (int, float, Decimal)):
                self.assertEqual(result, expected)
            else:
                self.assertIs(result, value)