# employee_predictor/ml/feature_transformations.py
import pandas as pd
import numpy as np
import joblib
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def categorize_position(position):
    """
    Categorizes positions into Technical, Management, Administrative, or Other
    """
    if not position or pd.isna(position):
        return "Other"

    position_lower = str(position).lower()

    # Technical roles
    technical_keywords = ['technician', 'engineer', 'developer', 'analyst',
                          'dba', 'architect', 'database', 'programmer', 'specialist']
    if any(keyword in position_lower for keyword in technical_keywords):
        return "Technical"

    # Management roles
    management_keywords = ['manager', 'director', 'ceo', 'president', 'cio',
                           'supervisor', 'lead', 'head', 'chief']
    if any(keyword in position_lower for keyword in management_keywords):
        return "Management"

    # Administrative roles
    admin_keywords = ['admin', 'accountant', 'support', 'assistant',
                      'coordinator', 'clerk', 'secretary']
    if any(keyword in position_lower for keyword in admin_keywords):
        return "Administrative"

    return "Other"


def simplify_marital_status(status):
    """
    Simplifies marital status to Married, Single, or Other
    """
    if not status or pd.isna(status):
        return "Other"

    status_str = str(status).strip().lower()

    if status_str in ['married']:
        return "Married"
    elif status_str in ['single']:
        return "Single"
    else:
        return "Other"  # For Divorced, Separated, Widowed


def load_encoding_maps():
    """
    Load the encoding maps used for target encoding with fallback defaults
    """
    try:
        # Try to load from multiple possible locations
        possible_paths = [
            os.path.join(settings.MEDIA_ROOT, 'models', 'encoding_maps.pkl'),
            os.path.join(settings.BASE_DIR, 'employee_predictor', 'ml', 'models', 'encoding_maps.pkl'),
            os.path.join(settings.BASE_DIR, 'employee_predictor', 'ml', 'encoding_maps.pkl')
        ]

        for path in possible_paths:
            if os.path.exists(path):
                try:
                    maps = joblib.load(path)
                    logger.info(f"Encoding maps loaded from {path}")
                    return maps
                except Exception as e:
                    logger.warning(f"Error loading encoding maps from {path}: {str(e)}")

    except Exception as e:
        logger.warning(f"Error in load_encoding_maps: {str(e)}")

    # Return default encoding maps
    logger.info("Using default encoding maps")
    return get_default_encoding_maps()


def get_default_encoding_maps():
    """
    Get default encoding maps based on typical HR data patterns
    """
    return {
        'position_encoding': {
            'Technical': 3.0,  # Technical roles often perform well
            'Management': 3.2,  # Management roles typically perform well
            'Administrative': 2.8,  # Administrative roles perform moderately
            'Other': 2.5  # Other roles - neutral
        },
        'marital_encoding': {
            'Married': 3.0,  # Married employees often more stable
            'Single': 2.8,  # Single employees
            'Other': 2.9  # Other marital status
        },
        'performance_mapping': {
            'PIP': 1,
            'Needs Improvement': 2,
            'Fully Meets': 3,
            'Exceeds': 4
        }
    }


def apply_transformations(employee_data):
    """
    Apply all transformations to employee data with robust error handling

    Args:
        employee_data (dict or DataFrame): Employee data

    Returns:
        dict or DataFrame: Transformed employee data
    """
    try:
        # Convert to DataFrame if dict
        if isinstance(employee_data, dict):
            df = pd.DataFrame([employee_data])
            was_dict = True
        else:
            df = employee_data.copy()
            was_dict = False

        # Load encoding maps
        encoding_maps = load_encoding_maps()
        position_encoding = encoding_maps.get('position_encoding', {})
        marital_encoding = encoding_maps.get('marital_encoding', {})

        # Apply position transformation
        position_columns = ['position', 'Position']
        for col in position_columns:
            if col in df.columns:
                try:
                    df['Position_Group'] = df[col].apply(categorize_position)
                    df['Position_Group_Encoded'] = df['Position_Group'].map(position_encoding)
                    df['Position_Group_Encoded'] = df['Position_Group_Encoded'].fillna(2.5)
                    logger.debug(f"Position transformation applied using column: {col}")
                    break
                except Exception as e:
                    logger.warning(f"Error applying position transformation to {col}: {str(e)}")

        # Apply marital status transformation
        marital_columns = ['marital_status', 'MaritalDesc', 'marital_desc']
        for col in marital_columns:
            if col in df.columns:
                try:
                    df['MaritalDesc_Simple'] = df[col].apply(simplify_marital_status)
                    df['MaritalDesc_Simple_Encoded'] = df['MaritalDesc_Simple'].map(marital_encoding)
                    df['MaritalDesc_Simple_Encoded'] = df['MaritalDesc_Simple_Encoded'].fillna(2.9)
                    logger.debug(f"Marital status transformation applied using column: {col}")
                    break
                except Exception as e:
                    logger.warning(f"Error applying marital transformation to {col}: {str(e)}")

        # Handle gender/sex encoding
        gender_columns = ['gender', 'sex', 'Gender', 'Sex']
        for col in gender_columns:
            if col in df.columns:
                try:
                    df['Sex_Encoded'] = df[col].apply(lambda x: 1 if str(x).upper().startswith('F') else 0)
                    logger.debug(f"Gender encoding applied using column: {col}")
                    break
                except Exception as e:
                    logger.warning(f"Error applying gender encoding to {col}: {str(e)}")

        # Ensure encoded columns exist with defaults
        if 'Position_Group_Encoded' not in df.columns:
            df['Position_Group_Encoded'] = 2.5  # Default for 'Other'
            logger.debug("Added default Position_Group_Encoded")

        if 'MaritalDesc_Simple_Encoded' not in df.columns:
            df['MaritalDesc_Simple_Encoded'] = 2.9  # Default for 'Other'
            logger.debug("Added default MaritalDesc_Simple_Encoded")

        if 'Sex_Encoded' not in df.columns:
            df['Sex_Encoded'] = 0  # Default to male
            logger.debug("Added default Sex_Encoded")

        # Return DataFrame or dict depending on input
        if was_dict:
            return df.iloc[0].to_dict()
        return df

    except Exception as e:
        logger.error(f"Error in apply_transformations: {str(e)}")

        # Return input data unchanged if transformation fails
        if isinstance(employee_data, dict):
            # Add basic encoded fields to dict
            result = employee_data.copy()
            result.update({
                'Position_Group_Encoded': 2.5,
                'MaritalDesc_Simple_Encoded': 2.9,
                'Sex_Encoded': 0
            })
            return result
        else:
            return employee_data


def create_and_save_encoding_maps(df, target_column='PerformanceScore'):
    """
    Create encoding maps from a dataset and save them
    This function can be used to generate encoding maps from training data

    Args:
        df (DataFrame): Training dataset
        target_column (str): Target column name for target encoding
    """
    try:
        encoding_maps = {}

        # Apply transformations first
        df_transformed = apply_transformations(df)

        # Create target encoding if target column exists
        if target_column in df_transformed.columns:
            # Handle categorical target
            if df_transformed[target_column].dtype == 'object':
                performance_mapping = {
                    'PIP': 1,
                    'Needs Improvement': 2,
                    'Fully Meets': 3,
                    'Exceeds': 4
                }
                df_transformed['target_numeric'] = df_transformed[target_column].map(performance_mapping)
                encoding_target = 'target_numeric'
            else:
                encoding_target = target_column

            # Position encoding
            if 'Position_Group' in df_transformed.columns:
                position_encoding = df_transformed.groupby('Position_Group')[encoding_target].mean().to_dict()
                encoding_maps['position_encoding'] = position_encoding

            # Marital encoding
            if 'MaritalDesc_Simple' in df_transformed.columns:
                marital_encoding = df_transformed.groupby('MaritalDesc_Simple')[encoding_target].mean().to_dict()
                encoding_maps['marital_encoding'] = marital_encoding
        else:
            # Use defaults if no target column
            encoding_maps = get_default_encoding_maps()

        # Save encoding maps
        models_dir = os.path.join(settings.MEDIA_ROOT, 'models')
        os.makedirs(models_dir, exist_ok=True)

        encoding_path = os.path.join(models_dir, 'encoding_maps.pkl')
        joblib.dump(encoding_maps, encoding_path)

        logger.info(f"Encoding maps created and saved to {encoding_path}")
        logger.info(f"Encoding maps: {encoding_maps}")

        return encoding_maps

    except Exception as e:
        logger.error(f"Error creating encoding maps: {str(e)}")
        return get_default_encoding_maps()


# Utility function for testing transformations
def test_transformations():
    """Test the transformation functions with sample data"""
    test_data = {
        'position': 'Software Engineer',
        'marital_status': 'Married',
        'gender': 'F',
        'age': 30,
        'salary': 75000
    }

    print("Original data:", test_data)
    transformed = apply_transformations(test_data)
    print("Transformed data:", transformed)

    return transformed


if __name__ == "__main__":
    # Run test if executed directly
    test_transformations()