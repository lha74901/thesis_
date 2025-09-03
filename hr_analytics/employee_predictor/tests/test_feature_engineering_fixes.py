import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from django.test import TestCase

from employee_predictor.ml.feature_engineering import (
    load_preprocessor, save_preprocessor, load_label_encoders, save_label_encoders,
    prepare_data_for_prediction, engineer_features
)


class FeatureEngineeringCoverageTests(TestCase):
    """Additional tests to improve coverage for feature_engineering.py."""

    def test_load_preprocessor_file_exists(self):
        """Test load_preprocessor when file exists."""
        with patch('os.path.exists', return_value=True), \
                patch('joblib.load', return_value='loaded_preprocessor'):
            result = load_preprocessor()
            self.assertEqual(result, 'loaded_preprocessor')

    def test_load_label_encoders_file_exists(self):
        """Test load_label_encoders when file exists."""
        with patch('os.path.exists', return_value=True), \
                patch('joblib.load', return_value={'test': 'encoder'}):
            result = load_label_encoders()
            self.assertEqual(result, {'test': 'encoder'})

    def test_prepare_data_with_invalid_data(self):
        """Test prepare_data_for_prediction with invalid data."""
        # Create test data with 'invalid' values
        test_data = pd.DataFrame({
            'DaysLateLast30': ['invalid'] * 3,
            'Absences': ['invalid'] * 3,
            'Salary': ['invalid'] * 3
        })

        # Should raise ValueError
        with self.assertRaises(ValueError):
            prepare_data_for_prediction(test_data)

    def test_prepare_data_with_empty_dataframe(self):
        """Test prepare_data_for_prediction with empty DataFrame."""
        with patch('employee_predictor.ml.feature_engineering.load_preprocessor') as mock_load:
            mock_preprocessor = MagicMock()
            mock_load.return_value = mock_preprocessor
            mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

            # Test with empty DataFrame
            result = prepare_data_for_prediction(pd.DataFrame())

            # Check that default values were used
            self.assertTrue(mock_preprocessor.transform.called)

            # Check shape of result
            self.assertEqual(result.shape, (1, 3))

    def test_prepare_data_with_all_column_types(self):
        """Test prepare_data_for_prediction with all column types."""
        sample_data = {
            # MinMax features
            'DaysLateLast30': [5],
            'Absences': [2],
            'SpecialProjectsCount': [3],

            # ZScore features
            'EngagementSurvey': [4.0],
            'EmpSatisfaction': [4],
            'Salary': [60000],
            'Tenure_Years': [3],
            'Age': [30],

            # Label features
            'Sex': ['M'],
            'EmploymentStatus': ['Active'],

            # OneHot features
            'Position': ['Developer'],
            'RaceDesc': ['White'],
            'RecruitmentSource': ['LinkedIn'],
            'MaritalDesc': ['Single'],
            'Department': ['IT']
        }

        df = pd.DataFrame(sample_data)

        with patch('employee_predictor.ml.feature_engineering.load_preprocessor') as mock_load, \
                patch('employee_predictor.ml.feature_engineering.load_label_encoders', return_value={}):
            mock_preprocessor = MagicMock()
            mock_load.return_value = mock_preprocessor
            mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

            result = prepare_data_for_prediction(df)

            # Check that transformer was called
            mock_preprocessor.transform.assert_called_once()

            # Check result
            self.assertEqual(result.shape, (1, 3))

    def test_prepare_data_error_handling(self):
        """Test error handling in prepare_data_for_prediction."""
        test_data = pd.DataFrame({'emp_id': ['TEST001']})

        # Test when preprocessor is not found
        with patch('employee_predictor.ml.feature_engineering.load_preprocessor', return_value=None):
            with self.assertRaises(ValueError):
                prepare_data_for_prediction(test_data)

        # Test when preprocessor raises error during transform
        with patch('employee_predictor.ml.feature_engineering.load_preprocessor') as mock_load, \
                patch('employee_predictor.ml.feature_engineering.load_label_encoders', return_value={}):
            mock_preprocessor = MagicMock()
            mock_load.return_value = mock_preprocessor
            mock_preprocessor.transform.side_effect = ValueError("Transformation error")

            with self.assertRaises(ValueError):
                prepare_data_for_prediction(test_data)