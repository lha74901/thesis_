# employee_predictor/tests/test_ml/test_predictor.py
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import User

from employee_predictor.ml.predictor import PerformancePredictor
from employee_predictor.models import Employee


class PredictorTests(TestCase):
    """Tests for the PerformancePredictor class."""

    def setUp(self):
        """Set up test data."""
        # Create a test employee
        self.employee = Employee.objects.create(
            name='Test Employee',
            emp_id='EMP001',
            department='IT',
            position='Developer',
            date_of_hire=date(2020, 1, 1),
            gender='M',
            marital_status='Single',
            age=30,
            salary=Decimal('60000.00'),
            engagement_survey=4.0,
            emp_satisfaction=4,
            special_projects_count=2,
            days_late_last_30=1,
            absences=3,
            hispanic_latino='No',
            employment_status='Active'
        )

        # Sample employee data for predictions
        self.employee_data = {
            'engagement_survey': [4.0],
            'emp_satisfaction': [4],
            'days_late_last_30': [1],
            'absences': [3],
            'special_projects_count': [2]
        }

        # Create DataFrame from employee data
        self.employee_df = pd.DataFrame(self.employee_data)

        # Create predictor instance
        self.predictor = PerformancePredictor()

    def test_init_with_model_found(self):
        """Test initialization when model is found."""
        with patch('os.path.exists', return_value=True), \
                patch('joblib.load') as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            predictor = PerformancePredictor()

            # Check that model was loaded
            self.assertEqual(predictor.model, mock_model)
            mock_load.assert_called_once()

    def test_init_with_model_not_found(self):
        """Test initialization when model is not found."""
        with patch('os.path.exists', return_value=False):
            predictor = PerformancePredictor()

            # Check that model is None
            self.assertIsNone(predictor.model)

    def test_init_with_load_exception(self):
        """Test initialization when model loading raises an exception."""
        with patch('os.path.exists', return_value=True), \
                patch('joblib.load', side_effect=Exception("Test exception")):
            # This should not raise an exception
            predictor = PerformancePredictor()

            # Check that model is None
            self.assertIsNone(predictor.model)

    def test_predict_success(self):
        """Test successful prediction."""
        # Mock rules_based_prediction to return a fixed value
        with patch.object(self.predictor, 'rules_based_prediction', return_value=4):
            result = self.predictor.predict(self.employee_df)
            self.assertEqual(result, 4)

    def test_predict_exception(self):
        """Test predict method handles exceptions."""
        # Mock rules_based_prediction to raise an exception
        with patch.object(self.predictor, 'rules_based_prediction', side_effect=Exception("Test exception")):
            result = self.predictor.predict(self.employee_df)

            # Should return default score of 3
            self.assertEqual(result, 3)

    def test_rules_based_prediction_df_input(self):
        """Test rules_based_prediction with DataFrame input."""
        result = self.predictor.rules_based_prediction(self.employee_df)

        # With the given values, should return 4 (Exceeds)
        self.assertEqual(result, 4)

    def test_rules_based_prediction_alternative_column_names(self):
        """Test rules_based_prediction with alternative column names."""
        # Create data with alternative column names
        alt_data = {
            'EngagementSurvey': [4.0],
            'EmpSatisfaction': [4],
            'DaysLateLast30': [1],
            'Absences': [3],
            'SpecialProjectsCount': [2]
        }
        alt_df = pd.DataFrame(alt_data)

        result = self.predictor.rules_based_prediction(alt_df)

        # Should still return 4 (Exceeds)
        self.assertEqual(result, 4)

    def test_rules_based_prediction_low_scores(self):
        """Test rules_based_prediction with low scores."""
        # Create data with low scores
        low_data = {
            'engagement_survey': [1.0],
            'emp_satisfaction': [1],
            'days_late_last_30': [10],
            'absences': [15],
            'special_projects_count': [0]
        }
        low_df = pd.DataFrame(low_data)

        result = self.predictor.rules_based_prediction(low_df)

        # Should return 1 (PIP)
        self.assertEqual(result, 1)

    def test_rules_based_prediction_medium_scores(self):
        """Test rules_based_prediction with medium scores."""
        # Create data with medium scores
        med_data = {
            'engagement_survey': [3.0],
            'emp_satisfaction': [3],
            'days_late_last_30': [5],
            'absences': [5],
            'special_projects_count': [1]
        }
        med_df = pd.DataFrame(med_data)

        result = self.predictor.rules_based_prediction(med_df)

        # Calculation: (3.0-2.5) + (3.0-2.5) - (5*0.1) - (5*0.2) + (1*0.3) = 0.5 + 0.5 - 0.5 - 1.0 + 0.3 = -0.2
        # -0.2 is between -2 and 0, which maps to 2 (Needs Improvement)
        self.assertEqual(result, 2)

    def test_predict_with_probability(self):
        """Test predict_with_probability method."""
        # Mock predict to return a fixed value
        with patch.object(self.predictor, 'predict', return_value=4):
            result = self.predictor.predict_with_probability(self.employee_df)

            # Check structure of result
            self.assertIn('prediction', result)
            self.assertIn('prediction_label', result)
            self.assertIn('probabilities', result)

            # Check values
            self.assertEqual(result['prediction'], 4)
            self.assertEqual(result['prediction_label'], 'Exceeds')

            # Check probabilities sum to approximately 1
            probs_sum = sum(result['probabilities'].values())
            self.assertAlmostEqual(probs_sum, 1.0, places=1)

            # Check highest probability is for predicted class
            self.assertEqual(max(result['probabilities'].items(), key=lambda x: x[1])[0], 4)

    def test_predict_with_probability_missing_mapping(self):
        """Test predict_with_probability when prediction is not in mapping."""
        # Mock predict to return a value not in the mapping
        with patch.object(self.predictor, 'predict', return_value=None):
            result = self.predictor.predict_with_probability(self.employee_df)

            # Should still return valid structure with default values
            self.assertIn('prediction', result)
            self.assertIn('prediction_label', result)
            self.assertIn('probabilities', result)

            # Check that label is "Unknown" for missing mapping
            self.assertEqual(result['prediction_label'], "Unknown")

    def test_rules_based_prediction_with_none_values(self):
        """Test rules_based_prediction with None values in numeric fields."""
        # Create data with None values in numeric fields
        none_data = {
            'engagement_survey': [None],
            'emp_satisfaction': [None],
            'days_late_last_30': [None],
            'absences': [None],
            'special_projects_count': [None]
        }
        none_df = pd.DataFrame(none_data)

        # Should handle None values by using defaults
        result = self.predictor.rules_based_prediction(none_df)
        # Should return a value based on defaults (all 0s and 3.0)
        self.assertEqual(result, 3)  # Should use defaults and return "Fully Meets"

    def test_rules_based_prediction_with_string_values(self):
        """Test rules_based_prediction with string values that need conversion."""
        # Create data with string values
        string_data = {
            'engagement_survey': ['4.0'],
            'emp_satisfaction': ['4'],
            'days_late_last_30': ['1'],
            'absences': ['3'],
            'special_projects_count': ['2']
        }
        string_df = pd.DataFrame(string_data)

        # Should convert strings to numeric values
        result = self.predictor.rules_based_prediction(string_df)
        self.assertEqual(result, 4)  # Should still return "Exceeds"

    def test_rules_based_prediction_extreme_values(self):
        """Test rules_based_prediction with extreme values."""
        # Test with extremely high values
        high_data = pd.DataFrame({
            'engagement_survey': [5.0],
            'emp_satisfaction': [5],
            'days_late_last_30': [0],
            'absences': [0],
            'special_projects_count': [10]
        })

        high_result = self.predictor.predict(high_data)
        self.assertEqual(high_result, 4)  # Should be "Exceeds"

        # Test with extremely low values
        low_data = pd.DataFrame({
            'engagement_survey': [1.0],
            'emp_satisfaction': [1],
            'days_late_last_30': [30],
            'absences': [30],
            'special_projects_count': [0]
        })

        low_result = self.predictor.predict(low_data)
        self.assertEqual(low_result, 1)  # Should be "PIP"

    def test_predict_with_nonstandard_data_formats(self):
        """Test predict method with non-standard data formats."""
        # Dictionary with string values
        data_dict = {
            'engagement_survey': ['4.5'],
            'emp_satisfaction': ['4'],
            'days_late_last_30': ['1'],
            'absences': ['3'],
            'special_projects_count': ['2']
        }

        # Should handle string conversions
        result = self.predictor.predict(data_dict)
        self.assertIn(result, [1, 2, 3, 4])

        # Test with empty input
        result = self.predictor.predict({})
        self.assertIn(result, [1, 2, 3, 4])