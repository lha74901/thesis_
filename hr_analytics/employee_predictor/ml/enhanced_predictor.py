# employee_predictor/ml/enhanced_predictor.py
import joblib
import pandas as pd
import numpy as np
import os
import logging
from django.conf import settings
from datetime import datetime, date

# Set up logging
logger = logging.getLogger(__name__)


class EnhancedPerformancePredictor:
    """
    Enhanced performance predictor with robust fallback mechanisms
    """

    def __init__(self):
        self.performance_mapping = {
            1: "PIP",
            2: "Needs Improvement",
            3: "Fully Meets",
            4: "Exceeds"
        }

        # Initialize model and related components
        self.model = None
        self.preprocessor_config = None
        self.encoding_maps = None
        self.sex_encoder = None

        # Load model components if available
        self._load_model_components()

    def _load_model_components(self):
        """Load ML model components with proper error handling"""
        try:
            # Define possible paths for model files
            models_dir = os.path.join(settings.MEDIA_ROOT, 'models')
            fallback_dir = os.path.join(settings.BASE_DIR, 'employee_predictor', 'ml', 'models')

            # Create directories if they don't exist
            os.makedirs(models_dir, exist_ok=True)
            os.makedirs(fallback_dir, exist_ok=True)

            # Try to load model
            model_files = [
                'hr_svm_model_enhanced.pkl',
                'hr_svm_model.pkl',
                'best_svm_model.pkl'
            ]

            for model_file in model_files:
                for base_dir in [models_dir, fallback_dir]:
                    model_path = os.path.join(base_dir, model_file)
                    if os.path.exists(model_path):
                        try:
                            self.model = joblib.load(model_path)
                            logger.info(f"Model loaded successfully from {model_path}")
                            break
                        except Exception as e:
                            logger.warning(f"Error loading model from {model_path}: {str(e)}")
                if self.model:
                    break

            # Load encoding maps with defaults
            self.encoding_maps = self._load_or_create_encoding_maps(models_dir, fallback_dir)

            # Load preprocessor config with defaults
            self.preprocessor_config = self._load_or_create_preprocessor_config(models_dir, fallback_dir)

            # Load sex encoder with defaults
            self.sex_encoder = self._load_or_create_sex_encoder(models_dir, fallback_dir)

        except Exception as e:
            logger.error(f"Error initializing predictor components: {str(e)}")
            # Set defaults
            self.encoding_maps = self._get_default_encoding_maps()
            self.preprocessor_config = self._get_default_preprocessor_config()

    def _load_or_create_encoding_maps(self, models_dir, fallback_dir):
        """Load or create default encoding maps"""
        for base_dir in [models_dir, fallback_dir]:
            encoding_path = os.path.join(base_dir, 'encoding_maps.pkl')
            if os.path.exists(encoding_path):
                try:
                    maps = joblib.load(encoding_path)
                    logger.info(f"Encoding maps loaded from {encoding_path}")
                    return maps
                except Exception as e:
                    logger.warning(f"Error loading encoding maps from {encoding_path}: {str(e)}")

        # Return defaults
        return self._get_default_encoding_maps()

    def _load_or_create_preprocessor_config(self, models_dir, fallback_dir):
        """Load or create default preprocessor config"""
        for base_dir in [models_dir, fallback_dir]:
            config_path = os.path.join(base_dir, 'preprocessor_config.pkl')
            if os.path.exists(config_path):
                try:
                    config = joblib.load(config_path)
                    logger.info(f"Preprocessor config loaded from {config_path}")
                    return config
                except Exception as e:
                    logger.warning(f"Error loading preprocessor config from {config_path}: {str(e)}")

        # Return defaults
        return self._get_default_preprocessor_config()

    def _load_or_create_sex_encoder(self, models_dir, fallback_dir):
        """Load or create default sex encoder"""
        for base_dir in [models_dir, fallback_dir]:
            encoder_path = os.path.join(base_dir, 'sex_label_encoder.pkl')
            if os.path.exists(encoder_path):
                try:
                    encoder = joblib.load(encoder_path)
                    logger.info(f"Sex encoder loaded from {encoder_path}")
                    return encoder
                except Exception as e:
                    logger.warning(f"Error loading sex encoder from {encoder_path}: {str(e)}")

        # Return None - will handle in feature preparation
        return None

    def _get_default_encoding_maps(self):
        """Get default encoding maps"""
        return {
            'position_encoding': {
                'Technical': 3.0,
                'Management': 3.2,
                'Administrative': 2.8,
                'Other': 2.5
            },
            'marital_encoding': {
                'Married': 3.0,
                'Single': 2.8,
                'Other': 2.9
            },
            'performance_mapping': {
                'PIP': 1,
                'Needs Improvement': 2,
                'Fully Meets': 3,
                'Exceeds': 4
            }
        }

    def _get_default_preprocessor_config(self):
        """Get default preprocessor configuration"""
        return {
            'z_score_features': ['Salary', 'Age'],
            'min_max_features': ['ServiceDuration', 'Absences', 'DaysLateLast30',
                                 'SpecialProjectsCount', 'MaritalDesc_Simple_Encoded',
                                 'Position_Group_Encoded', 'EngagementSurvey', 'EmpSatisfaction'],
            'remaining_features': ['Sex_Encoded'],
            'all_features': ['Absences', 'Age', 'DaysLateLast30', 'EmpSatisfaction',
                             'EngagementSurvey', 'Salary', 'ServiceDuration',
                             'SpecialProjectsCount', 'MaritalDesc_Simple_Encoded',
                             'Position_Group_Encoded', 'Sex_Encoded']
        }

    def categorize_position(self, position):
        """Categorize position into groups"""
        if not position or pd.isna(position):
            return "Other"

        position_lower = str(position).lower()

        # Technical roles
        if any(term in position_lower for term in ['technician', 'engineer', 'developer',
                                                   'analyst', 'dba', 'architect', 'database']):
            return "Technical"

        # Management roles
        if any(term in position_lower for term in ['manager', 'director', 'ceo',
                                                   'president', 'cio']):
            return "Management"

        # Administrative roles
        if any(term in position_lower for term in ['admin', 'accountant', 'support']):
            return "Administrative"

        return "Other"

    def simplify_marital_status(self, status):
        """Simplify marital status"""
        if not status or pd.isna(status):
            return "Other"

        status_str = str(status).strip()
        if status_str == "Married":
            return "Married"
        elif status_str == "Single":
            return "Single"
        else:
            return "Other"

    def calculate_tenure_years(self, date_of_hire):
        """Calculate tenure in years"""
        if not date_of_hire:
            return 0

        try:
            if isinstance(date_of_hire, str):
                hire_date = pd.to_datetime(date_of_hire).date()
            elif isinstance(date_of_hire, date):
                hire_date = date_of_hire
            else:
                hire_date = date_of_hire.date() if hasattr(date_of_hire, 'date') else date_of_hire

            today = date.today()
            tenure_days = (today - hire_date).days
            return max(0, tenure_days / 365.25)
        except:
            return 0

    def prepare_features(self, employee_data):
        """Prepare employee data for prediction"""
        try:
            # Handle case where values are lists
            processed_data = {}
            for key, value in employee_data.items():
                if isinstance(value, list) and len(value) > 0:
                    processed_data[key] = value[0]
                else:
                    processed_data[key] = value

            # Apply transformations
            # Position transformation
            if 'position' in processed_data:
                position_group = self.categorize_position(processed_data['position'])
                processed_data['Position_Group'] = position_group
                processed_data['Position_Group_Encoded'] = self.encoding_maps['position_encoding'].get(position_group,
                                                                                                       2.5)

            # Marital status transformation
            if 'marital_status' in processed_data:
                marital_simple = self.simplify_marital_status(processed_data['marital_status'])
                processed_data['MaritalDesc_Simple'] = marital_simple
                processed_data['MaritalDesc_Simple_Encoded'] = self.encoding_maps['marital_encoding'].get(
                    marital_simple, 2.9)

            # Sex encoding
            if 'gender' in processed_data:
                # Map gender to expected sex format
                gender_value = str(processed_data['gender']).upper()
                processed_data['Sex_Encoded'] = 1 if gender_value == 'F' else 0

            # Calculate tenure
            if 'date_of_hire' in processed_data:
                processed_data['ServiceDuration'] = self.calculate_tenure_years(processed_data['date_of_hire'])

            # Map field names to expected names
            field_mapping = {
                'engagement_survey': 'EngagementSurvey',
                'emp_satisfaction': 'EmpSatisfaction',
                'absences': 'Absences',
                'days_late_last_30': 'DaysLateLast30',
                'special_projects_count': 'SpecialProjectsCount',
                'salary': 'Salary',
                'age': 'Age'
            }

            for old_name, new_name in field_mapping.items():
                if old_name in processed_data:
                    processed_data[new_name] = processed_data[old_name]

            # Set defaults for missing values
            defaults = {
                'Absences': 0,
                'Age': 35,
                'DaysLateLast30': 0,
                'EmpSatisfaction': 3,
                'EngagementSurvey': 3.0,
                'Salary': 60000,
                'ServiceDuration': 5,
                'SpecialProjectsCount': 0,
                'MaritalDesc_Simple_Encoded': 2.9,
                'Position_Group_Encoded': 2.5,
                'Sex_Encoded': 0
            }

            for key, default_value in defaults.items():
                if key not in processed_data or processed_data[key] is None:
                    processed_data[key] = default_value

            # Convert to DataFrame
            df = pd.DataFrame([processed_data])

            # Select required features
            required_features = self.preprocessor_config['all_features']
            feature_data = {}

            for feature in required_features:
                if feature in df.columns:
                    feature_data[feature] = df[feature].iloc[0]
                else:
                    feature_data[feature] = defaults.get(feature, 0)

            df_features = pd.DataFrame([feature_data])

            return df_features, df_features.values

        except Exception as e:
            logger.error(f"Error preparing features: {str(e)}")
            # Return minimal default features
            defaults = {
                'Absences': 0, 'Age': 35, 'DaysLateLast30': 0, 'EmpSatisfaction': 3,
                'EngagementSurvey': 3.0, 'Salary': 60000, 'ServiceDuration': 5,
                'SpecialProjectsCount': 0, 'MaritalDesc_Simple_Encoded': 2.9,
                'Position_Group_Encoded': 2.5, 'Sex_Encoded': 0
            }
            df = pd.DataFrame([defaults])
            return df, df.values

    def detect_clear_performance_issues(self, df):
        """Detect clear performance issues"""
        try:
            # Get values safely
            engagement = df.get('EngagementSurvey', [3.0])[0] if isinstance(df.get('EngagementSurvey'),
                                                                            list) else df.get('EngagementSurvey', 3.0)
            satisfaction = df.get('EmpSatisfaction', [3])[0] if isinstance(df.get('EmpSatisfaction'), list) else df.get(
                'EmpSatisfaction', 3)
            absences = df.get('Absences', [0])[0] if isinstance(df.get('Absences'), list) else df.get('Absences', 0)
            days_late = df.get('DaysLateLast30', [0])[0] if isinstance(df.get('DaysLateLast30'), list) else df.get(
                'DaysLateLast30', 0)

            engagement = float(engagement)
            satisfaction = float(satisfaction)
            absences = float(absences)
            days_late = float(days_late)

            # Clear indicators for PIP (Class 1)
            if (engagement < 1.8 or satisfaction < 1.8 or absences > 12 or days_late > 8):
                return 1

            # Clear indicators for Needs Improvement (Class 2)
            if (engagement < 2.5 or satisfaction < 2.5 or absences > 7 or days_late > 5 or
                    (absences > 5 and days_late > 3)):
                return 2

            return None

        except Exception as e:
            logger.error(f"Error detecting performance issues: {str(e)}")
            return None

    def rules_based_prediction(self, employee_data):
        """Rules-based prediction fallback"""
        try:
            # Extract key metrics safely
            def safe_get(data, keys, default):
                for key in keys if isinstance(keys, list) else [keys]:
                    if key in data:
                        value = data[key]
                        if isinstance(value, list) and len(value) > 0:
                            value = value[0]
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            continue
                return default

            engagement = safe_get(employee_data, ['EngagementSurvey', 'engagement_survey'], 3.0)
            satisfaction = safe_get(employee_data, ['EmpSatisfaction', 'emp_satisfaction'], 3.0)
            absences = safe_get(employee_data, ['Absences', 'absences'], 0)
            days_late = safe_get(employee_data, ['DaysLateLast30', 'days_late_last_30'], 0)
            projects = safe_get(employee_data, ['SpecialProjectsCount', 'special_projects_count'], 0)

            # Calculate score
            score = 0

            # Engagement impact
            if engagement < 2.0:
                score -= 3.0
            elif engagement < 3.0:
                score -= 1.5
            elif engagement >= 4.5:
                score += 2.0
            elif engagement >= 3.5:
                score += 1.0

            # Satisfaction impact
            if satisfaction < 2.0:
                score -= 3.0
            elif satisfaction < 3.0:
                score -= 1.5
            elif satisfaction >= 4.5:
                score += 2.0
            elif satisfaction >= 3.5:
                score += 1.0

            # Absences impact
            if absences > 10:
                score -= 4.0
            elif absences > 7:
                score -= 3.0
            elif absences > 5:
                score -= 2.0
            elif absences > 3:
                score -= 1.0
            elif absences <= 1:
                score += 0.5

            # Days late impact
            if days_late > 7:
                score -= 3.0
            elif days_late > 5:
                score -= 2.0
            elif days_late > 3:
                score -= 1.0
            elif days_late > 1:
                score -= 0.5
            elif days_late == 0:
                score += 0.5

            # Projects impact
            score += projects * 0.4

            # Combined penalties
            if absences > 5 and days_late > 3:
                score -= 1.0
            if engagement < 3.0 and satisfaction < 3.0:
                score -= 1.0

            # Convert to 1-4 scale
            if score <= -3.0:
                return 1  # PIP
            elif score < 0:
                return 2  # Needs Improvement
            elif score < 2.5:
                return 3  # Fully Meets
            else:
                return 4  # Exceeds

        except Exception as e:
            logger.error(f"Error in rules-based prediction: {str(e)}")
            return 3  # Default to "Fully Meets"

    def predict(self, employee_data):
        """Make basic performance prediction"""
        try:
            df, X = self.prepare_features(employee_data)

            # Check for clear issues first
            clear_issue = self.detect_clear_performance_issues(df.iloc[0].to_dict())
            if clear_issue is not None:
                return clear_issue

            # Try model prediction if available
            if self.model is not None:
                try:
                    prediction = self.model.predict(X)
                    prediction_value = int(prediction[0])

                    # Validate prediction range
                    if 1 <= prediction_value <= 4:
                        return prediction_value
                except Exception as e:
                    logger.warning(f"Model prediction failed: {str(e)}")

            # Fallback to rules-based prediction
            return self.rules_based_prediction(df.iloc[0].to_dict())

        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            return 3  # Default

    def predict_with_probability(self, employee_data):
        """Make prediction with probability scores"""
        try:
            df, X = self.prepare_features(employee_data)

            # Check for clear issues first
            clear_issue = self.detect_clear_performance_issues(df.iloc[0].to_dict())
            if clear_issue is not None:
                probabilities = {1: 0.1, 2: 0.1, 3: 0.1, 4: 0.1}
                probabilities[clear_issue] = 0.7

                return {
                    'prediction': clear_issue,
                    'prediction_label': self.performance_mapping.get(clear_issue, "Unknown"),
                    'probabilities': probabilities,
                    'key_factors': self.identify_key_factors(df.iloc[0].to_dict(), clear_issue)
                }

            # Try model prediction if available
            if self.model is not None:
                try:
                    prediction = self.model.predict(X)[0]
                    prediction_value = int(prediction)

                    # Get probabilities if available
                    probabilities = {}
                    if hasattr(self.model, 'predict_proba'):
                        proba = self.model.predict_proba(X)[0]
                        classes = self.model.classes_
                        probabilities = {int(cls): float(prob) for cls, prob in zip(classes, proba)}

                    if 1 <= prediction_value <= 4:
                        return {
                            'prediction': prediction_value,
                            'prediction_label': self.performance_mapping.get(prediction_value, "Unknown"),
                            'probabilities': probabilities,
                            'key_factors': self.identify_key_factors(df.iloc[0].to_dict(), prediction_value)
                        }
                except Exception as e:
                    logger.warning(f"Model prediction with probability failed: {str(e)}")

            # Fallback to rules-based prediction
            basic_prediction = self.rules_based_prediction(df.iloc[0].to_dict())
            probabilities = {1: 0.1, 2: 0.2, 3: 0.4, 4: 0.3}
            probabilities[basic_prediction] = 0.7

            # Normalize probabilities
            total = sum(probabilities.values())
            probabilities = {k: v / total for k, v in probabilities.items()}

            return {
                'prediction': basic_prediction,
                'prediction_label': self.performance_mapping.get(basic_prediction, "Unknown"),
                'probabilities': probabilities,
                'key_factors': self.identify_key_factors(df.iloc[0].to_dict(), basic_prediction)
            }

        except Exception as e:
            logger.error(f"Error during prediction with probability: {str(e)}")
            return {
                'prediction': 3,
                'prediction_label': "Fully Meets",
                'probabilities': {3: 1.0},
                'key_factors': ["Unable to analyze factors"]
            }

    def identify_key_factors(self, employee_data, prediction):
        """Identify key factors that influenced the prediction"""
        try:
            key_factors = []

            # Safe value extraction
            def safe_get(data, keys, default):
                for key in keys if isinstance(keys, list) else [keys]:
                    if key in data:
                        value = data[key]
                        if isinstance(value, list) and len(value) > 0:
                            value = value[0]
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            continue
                return default

            engagement = safe_get(employee_data, ['EngagementSurvey', 'engagement_survey'], 3.0)
            satisfaction = safe_get(employee_data, ['EmpSatisfaction', 'emp_satisfaction'], 3.0)
            absences = safe_get(employee_data, ['Absences', 'absences'], 0)
            days_late = safe_get(employee_data, ['DaysLateLast30', 'days_late_last_30'], 0)
            projects = safe_get(employee_data, ['SpecialProjectsCount', 'special_projects_count'], 0)

            if prediction == 4:  # Exceeds
                if engagement >= 4.5:
                    key_factors.append("Very high engagement score")
                elif engagement >= 4.0:
                    key_factors.append("High engagement score")
                if satisfaction >= 4.5:
                    key_factors.append("Very high job satisfaction")
                elif satisfaction >= 4.0:
                    key_factors.append("High job satisfaction")
                if projects >= 3:
                    key_factors.append("High number of special projects")
                if absences <= 1 and days_late <= 1:
                    key_factors.append("Excellent attendance record")

            elif prediction == 3:  # Fully Meets
                if 3.5 <= engagement < 4.5:
                    key_factors.append("Good engagement score")
                if 1 <= projects < 3:
                    key_factors.append("Contributes to special projects")
                if 3 <= satisfaction < 4:
                    key_factors.append("Satisfactory job satisfaction")
                if absences <= 3 and days_late <= 3:
                    key_factors.append("Good attendance record")

            elif prediction == 2:  # Needs Improvement
                if engagement < 3:
                    key_factors.append("Below average engagement")
                if satisfaction < 3:
                    key_factors.append("Below average job satisfaction")
                if absences > 5:
                    key_factors.append("Higher than average absences")
                if days_late > 3:
                    key_factors.append("Punctuality issues")
                if projects < 1:
                    key_factors.append("Limited contribution to special projects")

            elif prediction == 1:  # PIP
                if engagement < 2:
                    key_factors.append("Very low engagement")
                if satisfaction < 2:
                    key_factors.append("Very low job satisfaction")
                if absences > 10:
                    key_factors.append("Excessive absences")
                if days_late > 5:
                    key_factors.append("Serious punctuality issues")
                if projects == 0:
                    key_factors.append("No participation in special projects")

            # Default message if no factors identified
            if not key_factors:
                if prediction >= 3:
                    key_factors.append("Multiple positive factors")
                else:
                    key_factors.append("Multiple areas needing improvement")

            return key_factors

        except Exception as e:
            logger.error(f"Error identifying key factors: {str(e)}")
            return ["Unable to identify key factors"]