# employee_predictor/tests/test_ml/test_feature_engineering_complete.py
import os
import pandas as pd
import numpy as np
from django.test import TestCase
from unittest.mock import patch, MagicMock, mock_open
import joblib
from django.conf import settings

from employee_predictor.ml.feature_engineering import (
    get_preprocessor, load_preprocessor, save_preprocessor,
    load_label_encoders, save_label_encoders, engineer_features,
    prepare_data_for_prediction
)


class FeatureEngineeringCompleteTest(TestCase):
    def setUp(self):
        self.test_data = {
            'emp_id': ['EMP001'],
            'name': ['Test Employee'],
            'date_of_hire': [pd.Timestamp('2020-01-01')],
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

    def test_get_preprocessor(self):
        """Test get_preprocessor returns correct transformer."""
        preprocessor = get_preprocessor()
        self.assertIsNotNone(preprocessor)
        self.assertTrue(hasattr(preprocessor, 'transformers'))

    @patch('os.path.exists')
    @patch('joblib.load')
    def test_load_preprocessor(self, mock_load, mock_exists):
        """Test load_preprocessor function."""
        # Test when file exists
        mock_exists.return_value = True
        mock_preprocessor = MagicMock()
        mock_load.return_value = mock_preprocessor

        result = load_preprocessor()
        self.assertEqual(result, mock_preprocessor)

        # Test when file doesn't exist
        mock_exists.return_value = False
        result = load_preprocessor()
        self.assertIsNone(result)

    @patch('os.makedirs')
    @patch('joblib.dump')
    def test_save_preprocessor(self, mock_dump, mock_makedirs):
        """Test save_preprocessor function."""
        mock_preprocessor = MagicMock()

        save_preprocessor(mock_preprocessor)

        mock_makedirs.assert_called_once()
        mock_dump.assert_called_once()

    @patch('os.path.exists')
    def test_load_label_encoders_file_not_found(self, mock_exists):
        """Test load_label_encoders when file doesn't exist."""
        mock_exists.return_value = False
        result = load_label_encoders()
        self.assertEqual(result, {})

    @patch('os.makedirs')
    @patch('joblib.dump')
    def test_save_label_encoders(self, mock_dump, mock_makedirs):
        """Test save_label_encoders function."""
        test_encoders = {'Sex': MagicMock(), 'EmploymentStatus': MagicMock()}

        save_label_encoders(test_encoders)

        mock_makedirs.assert_called_once()
        mock_dump.assert_called_once()

    def test_engineer_features(self):
        """Test engineer_features calls prepare_data_for_prediction."""
        with patch('employee_predictor.ml.feature_engineering.prepare_data_for_prediction') as mock_prepare:
            mock_prepare.return_value = np.array([[1, 2, 3]])

            result = engineer_features(self.df)

            mock_prepare.assert_called_once_with(self.df)
            self.assertEqual(result.tolist(), [[1, 2, 3]])

    # Add to test_feature_engineering_complete.py
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('joblib.dump')
    def test_save_preprocessor_and_encoders(self, mock_dump, mock_makedirs, mock_exists):
        """Test both save_preprocessor and save_label_encoders functions."""
        mock_exists.return_value = True

        # Test preprocessor saving
        mock_preprocessor = MagicMock()
        save_preprocessor(mock_preprocessor)
        mock_makedirs.assert_called()
        mock_dump.assert_called()

        # Test label encoders saving
        test_encoders = {'Sex': MagicMock(), 'EmploymentStatus': MagicMock()}
        save_label_encoders(test_encoders)
        mock_makedirs.assert_called()
        mock_dump.assert_called()

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_prepare_data_for_prediction_error_handling(self, mock_load_preprocessor):
        """Test error handling in prepare_data_for_prediction."""
        # Test when preprocessor raises an error
        mock_load_preprocessor.return_value = MagicMock()
        mock_load_preprocessor.return_value.transform.side_effect = ValueError("Test error")

        with self.assertRaises(ValueError):
            prepare_data_for_prediction({'emp_id': ['TEST001']})


import pandas as pd
import numpy as np
from django.test import TestCase
from unittest.mock import patch, MagicMock

from employee_predictor.ml.feature_engineering import (
    prepare_data_for_prediction, load_preprocessor,
    LABEL_FEATURES, MINMAX_FEATURES, ZSCORE_FEATURES
)


class FeatureEngineeringLabelEncodingTest(TestCase):
    """Test label encoding and feature conversion in feature_engineering.py."""

    def setUp(self):
        # Create test data with mixed types to trigger different code paths
        self.test_data = pd.DataFrame({
            # Standard cases that should convert directly
            'Sex': ['M', 'F', 'M', 'F'],
            'EmploymentStatus': ['Active', 'Voluntarily Terminated', 'Terminated for Cause', 'Active'],

            # Case that will trigger ValueError in conversion to int
            'OtherLabel': ['Category1', 'Category2', 'Category3', 'Category1'],

            # Numeric features
            'DaysLateLast30': [5, 10, 0, 3],
            'Absences': [2, 5, 1, 0],

            # String features that should remain strings
            'Position': ['Developer', 'Manager', 'Analyst', 'Developer'],
            'Department': ['IT', 'HR', 'Finance', 'IT']
        })

    @patch('employee_predictor.ml.feature_engineering.LABEL_ENCODERS', {})
    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_label_features_conversion_with_exceptions(self, mock_load_preprocessor):
        """Test conversion of label features including exception handling path."""
        # Setup mock preprocessor
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Add OtherLabel to LABEL_FEATURES for this test
        original_label_features = LABEL_FEATURES.copy()
        try:
            # Temporarily modify LABEL_FEATURES
            LABEL_FEATURES.append('OtherLabel')

            # Call function to test
            result = prepare_data_for_prediction(self.test_data)

            # Check that prepare_data_for_prediction was called correctly
            mock_load_preprocessor.assert_called_once()
            mock_preprocessor.transform.assert_called_once()

            # Check call to transform
            args, _ = mock_preprocessor.transform.call_args
            transformed_df = args[0]

            # Check Sex was converted correctly to 0,1
            sex_values = transformed_df['Sex'].tolist()
            self.assertEqual(sex_values, [0, 1, 0, 1])
            self.assertEqual(transformed_df['Sex'].dtype, np.int64)

            # Check EmploymentStatus was converted correctly to 0,1,2
            status_values = transformed_df['EmploymentStatus'].tolist()
            self.assertEqual(status_values, [0, 1, 2, 0])
            self.assertEqual(transformed_df['EmploymentStatus'].dtype, np.int64)

            # Check OtherLabel went through the exception path and created a mapping
            # It should map 'Category1' to 0, 'Category2' to 1, 'Category3' to 2
            other_label_values = transformed_df['OtherLabel'].tolist()
            self.assertEqual(sorted(set(other_label_values)), [0, 1, 2])
            self.assertEqual(transformed_df['OtherLabel'].dtype, np.int64)

            # Verify first value equals last value (both are 'Category1')
            self.assertEqual(other_label_values[0], other_label_values[3])
        finally:
            # Restore original LABEL_FEATURES
            while 'OtherLabel' in LABEL_FEATURES:
                LABEL_FEATURES.remove('OtherLabel')

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_minmax_zscore_features_conversion(self, mock_load_preprocessor):
        """Test conversion of minmax and zscore features."""
        # Setup mock preprocessor
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Add test columns to MINMAX_FEATURES and ZSCORE_FEATURES
        original_minmax = MINMAX_FEATURES.copy()
        original_zscore = ZSCORE_FEATURES.copy()

        try:
            # Modify features lists for testing
            if 'DaysLateLast30' not in MINMAX_FEATURES:
                MINMAX_FEATURES.append('DaysLateLast30')
            if 'Absences' not in MINMAX_FEATURES:
                MINMAX_FEATURES.append('Absences')

            # Call function to test
            result = prepare_data_for_prediction(self.test_data)

            # Check the call to transform
            args, _ = mock_preprocessor.transform.call_args
            transformed_df = args[0]

            # Verify numeric features were converted to float
            self.assertEqual(transformed_df['DaysLateLast30'].dtype, np.float64)
            self.assertEqual(transformed_df['Absences'].dtype, np.float64)

            # Verify string features remained strings
            self.assertEqual(transformed_df['Position'].dtype, np.dtype('O'))
            self.assertEqual(transformed_df['Department'].dtype, np.dtype('O'))
        finally:
            # Restore original feature lists
            MINMAX_FEATURES.clear()
            MINMAX_FEATURES.extend(original_minmax)
            ZSCORE_FEATURES.clear()
            ZSCORE_FEATURES.extend(original_zscore)

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_mixed_type_data_conversion(self, mock_load_preprocessor):
        """Test handling of mixed type data and complex conversions."""
        # Setup mock preprocessor
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Create data with mixed types that will trigger various conversion paths
        mixed_data = pd.DataFrame({
            # Label feature with mixed types including None and string types
            'Sex': ['M', None, 'F', 'Unknown'],

            # Numeric fields with strings and None values
            'DaysLateLast30': [5, '10', None, 'invalid'],
            'Absences': [2, None, '1', 'five'],

            # Non-label feature containing mix of types
            'MixedFeature': ['A', 1, 2.5, None]
        })

        # Add test columns to appropriate feature lists
        original_label = LABEL_FEATURES.copy()
        original_minmax = MINMAX_FEATURES.copy()

        try:
            # Modify features lists
            if 'DaysLateLast30' not in MINMAX_FEATURES:
                MINMAX_FEATURES.append('DaysLateLast30')
            if 'Absences' not in MINMAX_FEATURES:
                MINMAX_FEATURES.append('Absences')

            # Call function to test
            result = prepare_data_for_prediction(mixed_data)

            # Verify the preprocessing step
            args, _ = mock_preprocessor.transform.call_args
            transformed_df = args[0]

            # Check that Sex was converted and default values were applied
            self.assertEqual(transformed_df['Sex'].dtype, np.int64)
            self.assertTrue(all(isinstance(val, (int, np.integer)) for val in transformed_df['Sex']))

            # Check numeric columns were converted to float with defaults for invalid/None values
            self.assertEqual(transformed_df['DaysLateLast30'].dtype, np.float64)
            self.assertEqual(transformed_df['Absences'].dtype, np.float64)

            # Check for no NaN values
            self.assertFalse(transformed_df['DaysLateLast30'].isnull().any())
            self.assertFalse(transformed_df['Absences'].isnull().any())

            # MixedFeature should be converted to string as it's not in any feature list
            if 'MixedFeature' in transformed_df.columns:
                self.assertEqual(transformed_df['MixedFeature'].dtype, np.dtype('O'))
        finally:
            # Restore original feature lists
            LABEL_FEATURES.clear()
            LABEL_FEATURES.extend(original_label)
            MINMAX_FEATURES.clear()
            MINMAX_FEATURES.extend(original_minmax)


import pandas as pd
import numpy as np
from django.test import TestCase
from unittest.mock import patch, MagicMock

from employee_predictor.ml.feature_engineering import (
    prepare_data_for_prediction, load_preprocessor,
    LABEL_FEATURES, MINMAX_FEATURES, ZSCORE_FEATURES, ONEHOT_FEATURES,
    load_label_encoders
)


class PrepareDataForPredictionCoverageTest(TestCase):
    """Targeted test to increase coverage for the prepare_data_for_prediction function."""

    def setUp(self):
        """Set up test data that will trigger different code paths."""
        # Test data that will trigger multiple conversion paths
        self.test_data = pd.DataFrame({
            # Empty DataFrame case will be tested separately

            # String value needing conversion with missing values
            'DaysLateLast30': ['invalid', '5', None, '10'],
            'Absences': [None, '3', 'invalid', '2'],
            'SpecialProjectsCount': ['1', '2', None, 'invalid'],

            # Columns with pre-existing mappings
            'Sex': ['M', 'F', None, 'Unknown'],
            'EmploymentStatus': ['Active', None, 'Voluntarily Terminated', 'Terminated for Cause'],

            # Date field to test date conversion and tenure calculation
            'date_of_hire': [pd.Timestamp('2020-01-01'), None, pd.Timestamp('2019-05-15'), pd.Timestamp('2022-03-10')],

            # Age field with mixed types
            'age': [30, None, '45', 'invalid'],

            # Extra fields that might not be in standard mappings
            'custom_field': ['value1', 'value2', None, 'value3'],

            # Fields that should trigger OneHot encoding
            'Position': ['Developer', None, 'Manager', 'Analyst'],
            'MaritalDesc': ['Single', 'Married', None, 'Divorced'],
            'Department': [None, 'IT', 'HR', 'Finance']
        })

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    @patch('employee_predictor.ml.feature_engineering.load_label_encoders')
    def test_prepare_data_with_invalid_values(self, mock_load_encoders, mock_load_preprocessor):
        """Test with invalid values that will trigger exception handling."""
        # Setup mocks
        mock_encoders = {
            'Sex': MagicMock(),
            'EmploymentStatus': MagicMock()
        }
        mock_load_encoders.return_value = mock_encoders

        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Call the function
        result = prepare_data_for_prediction(self.test_data)

        # Verify the function made appropriate calls
        mock_load_encoders.assert_called_once()
        mock_load_preprocessor.assert_called_once()

        # Get the DataFrame that was passed to transform
        call_args = mock_preprocessor.transform.call_args
        df_passed = call_args[0][0]

        # Verify all numeric fields were handled properly
        for field in MINMAX_FEATURES + ZSCORE_FEATURES:
            if field in df_passed:
                self.assertEqual(df_passed[field].dtype, np.float64)
                # Check that invalid values were converted to defaults (not NaN)
                self.assertEqual(df_passed[field].isnull().sum(), 0)

        # Verify categorical fields were processed
        for field in ONEHOT_FEATURES:
            if field in df_passed:
                self.assertEqual(df_passed[field].dtype, np.dtype('O'))
                # Check that None values were handled
                self.assertEqual(df_passed[field].isnull().sum(), 0)

        # Verify label features were encoded
        for field in LABEL_FEATURES:
            if field in df_passed:
                self.assertEqual(df_passed[field].dtype, np.int64)

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_prepare_data_with_empty_dataframe(self, mock_load_preprocessor):
        """Test with empty DataFrame to hit that edge case."""
        # Setup mock
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Call with empty DataFrame
        result = prepare_data_for_prediction(pd.DataFrame())

        # Verify that the default values were created and used
        mock_load_preprocessor.assert_called_once()
        mock_preprocessor.transform.assert_called_once()

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_with_preprocessor_none(self, mock_load_preprocessor):
        """Test when preprocessor is None to hit ValueError path."""
        # Setup mock to return None
        mock_load_preprocessor.return_value = None

        # Expect ValueError
        with self.assertRaises(ValueError):
            prepare_data_for_prediction(self.test_data)

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_with_transform_error(self, mock_load_preprocessor):
        """Test when transform raises an error."""
        # Setup mock to raise exception
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.side_effect = ValueError("Test transform error")

        # Expect ValueError with specific message about preprocessing
        with self.assertRaises(ValueError) as context:
            prepare_data_for_prediction(self.test_data)

        # Verify error message
        self.assertIn("Failed to preprocess features", str(context.exception))

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_with_dictionary_input(self, mock_load_preprocessor):
        """Test with dictionary input instead of DataFrame."""
        # Setup mock
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Test data as dictionary
        dict_data = {
            'DaysLateLast30': [5],
            'Absences': [3],
            'Sex': ['M'],
            'Department': ['IT']
        }

        # Call function
        result = prepare_data_for_prediction(dict_data)

        # Verify conversion to DataFrame
        mock_preprocessor.transform.assert_called_once()
        # Verify result
        self.assertIsInstance(result, np.ndarray)

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_tenure_calculation(self, mock_load_preprocessor):
        """Test tenure calculation logic."""
        # Setup mock
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Create data with date_of_hire
        data = pd.DataFrame({
            'date_of_hire': [pd.Timestamp('2020-01-01')],
            'DateofHire': [None]  # Alternative column name
        })

        # Call function
        result = prepare_data_for_prediction(data)

        # Verify transform was called
        mock_preprocessor.transform.assert_called_once()
        # Get DataFrame passed to transform
        df_passed = mock_preprocessor.transform.call_args[0][0]
        # Check that Tenure_Years was calculated
        self.assertIn('Tenure_Years', df_passed.columns)
        # Should be a float with years since 2020-01-01
        self.assertGreaterEqual(df_passed['Tenure_Years'].iloc[0], 4.0)  # At least 4 years since 2020

    @patch('employee_predictor.ml.feature_engineering.load_preprocessor')
    def test_all_numeric_feature_types(self, mock_load_preprocessor):
        """Test all numeric feature conversion edge cases."""
        # Setup mock
        mock_preprocessor = MagicMock()
        mock_load_preprocessor.return_value = mock_preprocessor
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3]])

        # Create data with edge cases for all numeric features
        numeric_edge_cases = {}

        # Add all MINMAX_FEATURES with edge cases
        for feature in MINMAX_FEATURES:
            numeric_edge_cases[feature] = ['invalid', None, '5.5', 10]

        # Add all ZSCORE_FEATURES with edge cases
        for feature in ZSCORE_FEATURES:
            numeric_edge_cases[feature] = [None, 'invalid', '3.14', -2.5]

        # Create DataFrame
        data = pd.DataFrame(numeric_edge_cases)

        # Call function
        result = prepare_data_for_prediction(data)

        # Verify transform was called
        mock_preprocessor.transform.assert_called_once()
        # Get DataFrame passed to transform
        df_passed = mock_preprocessor.transform.call_args[0][0]

        # Check all numeric features were processed correctly
        for feature in MINMAX_FEATURES + ZSCORE_FEATURES:
            if feature in df_passed:
                self.assertEqual(df_passed[feature].dtype, np.float64)
                # Check no NaN values
                self.assertEqual(df_passed[feature].isnull().sum(), 0)
                # Check valid conversions
                self.assertTrue(df_passed[feature].iloc[2] > 3)  # '5.5' or '3.14'
                self.assertTrue(isinstance(df_passed[feature].iloc[3], float))  # 10 or -2.5


