# employee_predictor/tests/test_ml/test_feature_engineering.py

import pandas as pd
import numpy as np
from django.test import TestCase
from unittest.mock import patch, MagicMock
from datetime import date
from employee_predictor.ml.feature_engineering import (
    prepare_data_for_prediction, engineer_features,
    get_preprocessor, load_preprocessor, save_preprocessor,
    load_label_encoders, save_label_encoders
)


class FeatureEngineeringTest(TestCase):
    def setUp(self):
        # Sample data for testing
        self.test_data = {
            'emp_id': ['EMP001'],
            'name': ['Test Employee'],
            'date_of_hire': [date(2020, 1, 1)],
            'department': ['IT'],
            'position': ['Developer'],
            'gender': ['M'],
            'marital_status': ['Single'],
            'age': [30],
            'salary': [60000.00],
            'engagement_survey': [4.0],
            'emp_satisfaction': [4],
            'special_projects_count': [2],
            'days_late_last_30': [1],
            'absences': [3]
        }
        self.df = pd.DataFrame(self.test_data)

    def test_prepare_data_with_minimal_input(self):
        """Test prepare_data_for_prediction with minimal input."""
        minimal_data = {'emp_id': ['TEST001']}
        with patch('employee_predictor.ml.feature_engineering.load_preprocessor') as mock_load:
            # Setup mock preprocessor
            mock_preprocessor = MagicMock()
            mock_load.return_value = mock_preprocessor
            mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

            # Call function
            result = prepare_data_for_prediction(minimal_data)

            # Check result
            self.assertIsInstance(result, np.ndarray)

    def test_prepare_data_with_missing_values(self):
        """Test prepare_data_for_prediction with missing values."""
        # Data with missing values
        data_with_nans = self.test_data.copy()
        data_with_nans['age'] = [None]
        data_with_nans['salary'] = [np.nan]

        with patch('employee_predictor.ml.feature_engineering.load_preprocessor') as mock_load:
            mock_preprocessor = MagicMock()
            mock_load.return_value = mock_preprocessor
            mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

            # Should handle missing values gracefully
            result = prepare_data_for_prediction(data_with_nans)
            self.assertIsInstance(result, np.ndarray)
