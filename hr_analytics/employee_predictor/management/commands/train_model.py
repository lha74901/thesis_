# employee_predictor/management/commands/train_model.py
from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns
from imblearn.over_sampling import ADASYN
import joblib
import os
from django.conf import settings
import warnings

warnings.filterwarnings('ignore')

from employee_predictor.ml.feature_engineering import (
    MINMAX_FEATURES, ZSCORE_FEATURES, LABEL_FEATURES, ONEHOT_FEATURES,
    get_preprocessor, save_preprocessor, save_label_encoders
)


class Command(BaseCommand):
    help = 'Train and save the SVM model using advanced feature engineering and ADASYN resampling'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the HR dataset CSV file')
        parser.add_argument('--test_size', type=float, default=0.2, help='Proportion of data to use for testing')
        parser.add_argument('--random_state', type=int, default=42, help='Random seed for reproducibility')

    def handle(self, *args, **options):
        try:
            # Create models directory if it doesn't exist
            models_dir = os.path.join(settings.MEDIA_ROOT, 'models')
            os.makedirs(models_dir, exist_ok=True)

            # Path for plot output
            plots_dir = os.path.join(settings.MEDIA_ROOT, 'plots')
            os.makedirs(plots_dir, exist_ok=True)

            # Load the CSV data
            csv_file = options['csv_file']
            self.stdout.write(self.style.SUCCESS(f'Loading dataset from {csv_file}...'))

            try:
                df = pd.read_csv(csv_file)
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'Dataset file not found at {csv_file}'))
                return

            self.stdout.write(self.style.SUCCESS(f'Dataset loaded with {len(df)} records'))

            # Define required target variable
            if 'PerformanceScore_Encoded' not in df.columns:
                self.stdout.write(self.style.WARNING('PerformanceScore_Encoded not found, looking for alternatives...'))

                if 'PerfScoreID' in df.columns:
                    # Convert PerfScoreID to PerformanceScore_Encoded (1-4 scale)
                    df['PerformanceScore_Encoded'] = df['PerfScoreID'].clip(1, 4)
                    self.stdout.write(self.style.SUCCESS('Using PerfScoreID as target variable'))

                elif 'PerformanceScore' in df.columns and df['PerformanceScore'].dtype == 'object':
                    # Map text scores to numeric values
                    perf_map = {
                        'Exceeds': 4,
                        'Fully Meets': 3,
                        'Needs Improvement': 2,
                        'PIP': 1
                    }
                    df['PerformanceScore_Encoded'] = df['PerformanceScore'].map(perf_map)
                    self.stdout.write(self.style.SUCCESS('Using mapped PerformanceScore as target variable'))

                elif 'performance_score' in df.columns and df['performance_score'].dtype == 'object':
                    # Map performance_score to numeric values
                    perf_map = {
                        'Exceeds': 4,
                        'Fully Meets': 3,
                        'Needs Improvement': 2,
                        'PIP': 1
                    }
                    df['PerformanceScore_Encoded'] = df['performance_score'].map(perf_map)
                    self.stdout.write(self.style.SUCCESS('Using mapped performance_score as target variable'))
                else:
                    self.stdout.write(self.style.ERROR('No performance score column found!'))
                    return

            # Check if dataset has the required feature categories
            all_features = MINMAX_FEATURES + ZSCORE_FEATURES + LABEL_FEATURES + ONEHOT_FEATURES
            missing_features = [feat for feat in all_features if feat not in df.columns]

            if missing_features:
                self.stdout.write(self.style.WARNING(
                    f'Dataset missing required features: {missing_features}'))
                self.stdout.write(self.style.SUCCESS('Attempting to map missing features...'))

                # Map common column names
                column_mapping = {
                    'engagement_survey': 'EngagementSurvey',
                    'emp_satisfaction': 'EmpSatisfaction',
                    'days_late_last_30': 'DaysLateLast30',
                    'special_projects_count': 'SpecialProjectsCount',
                    'absences': 'Absences',
                    'salary': 'Salary',
                    'position': 'Position',
                    'department': 'Department',
                    'gender': 'Sex',
                    'marital_status': 'MaritalDesc',
                    'race': 'RaceDesc',
                    'recruitment_source': 'RecruitmentSource',
                    'employment_status': 'EmploymentStatus'
                }

                # Rename columns that exist in the DataFrame
                for old_name, new_name in column_mapping.items():
                    if old_name in df.columns and new_name not in df.columns:
                        df[new_name] = df[old_name]

                # Calculate tenure in years if needed
                if 'Tenure_Years' not in df.columns and 'date_of_hire' in df.columns:
                    df['DateofHire'] = pd.to_datetime(df['date_of_hire'])
                    df['Tenure_Years'] = (pd.Timestamp.now() - df['DateofHire']).dt.days / 365.25
                    self.stdout.write(self.style.SUCCESS('Calculated Tenure_Years from date_of_hire'))

                # Add Age if it's missing
                if 'Age' not in df.columns and 'age' in df.columns:
                    df['Age'] = df['age']
                    self.stdout.write(self.style.SUCCESS('Mapped age to Age'))

                # Check which features are still missing
                all_features = MINMAX_FEATURES + ZSCORE_FEATURES + LABEL_FEATURES + ONEHOT_FEATURES
                missing_features = [feat for feat in all_features if feat not in df.columns]

                if missing_features:
                    self.stdout.write(self.style.WARNING(
                        f'Still missing features after mapping: {missing_features}'))

                    # Add default values for essential missing features
                    for feature in missing_features:
                        if feature in MINMAX_FEATURES:
                            df[feature] = 0
                            self.stdout.write(self.style.SUCCESS(f'Added default value for {feature}'))
                        elif feature in ZSCORE_FEATURES:
                            if feature == 'EngagementSurvey':
                                df[feature] = 3.0
                            elif feature == 'EmpSatisfaction':
                                df[feature] = 3
                            elif feature == 'Salary':
                                df[feature] = 60000
                            elif feature == 'Tenure_Years':
                                df[feature] = 5
                            elif feature == 'Age':
                                df[feature] = 35
                            self.stdout.write(self.style.SUCCESS(f'Added default value for {feature}'))
                        elif feature in LABEL_FEATURES:
                            if feature == 'Sex':
                                df[feature] = 'M'
                            elif feature == 'EmploymentStatus':
                                df[feature] = 'Active'
                            self.stdout.write(self.style.SUCCESS(f'Added default value for {feature}'))
                        elif feature in ONEHOT_FEATURES:
                            df[feature] = 'Other'
                            self.stdout.write(self.style.SUCCESS(f'Added default value for {feature}'))

            # Clean the data - trim whitespace in string columns
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()

            # Define X (features) and y (target)
            X = df[MINMAX_FEATURES + ZSCORE_FEATURES + LABEL_FEATURES + ONEHOT_FEATURES]
            y = df['PerformanceScore_Encoded']

            # Display target distribution
            target_counts = y.value_counts().sort_index()
            self.stdout.write(self.style.SUCCESS("\nTarget variable distribution:"))
            for score, count in target_counts.items():
                self.stdout.write(self.style.SUCCESS(f"  Score {score}: {count} records"))

            # Pre-encode label features
            label_encoders = {}
            for feature in LABEL_FEATURES:
                if feature in X.columns:
                    le = LabelEncoder()
                    X[feature] = le.fit_transform(X[feature].astype(str))
                    label_encoders[feature] = le
                    self.stdout.write(self.style.SUCCESS(
                        f"Encoded {feature} values: {dict(zip(le.classes_, le.transform(le.classes_)))}"
                    ))

            # Save label encoders for later use
            save_label_encoders(label_encoders)
            self.stdout.write(self.style.SUCCESS("Label encoders saved for future use."))

            # Create preprocessing pipeline
            preprocessor = get_preprocessor()

            # Apply preprocessing to features
            self.stdout.write(self.style.SUCCESS("\nPreprocessing features..."))
            X_preprocessed = preprocessor.fit_transform(X)

            # Save the preprocessor for future use
            save_preprocessor(preprocessor)
            self.stdout.write(self.style.SUCCESS("Preprocessor saved for future use."))

            # Apply ADASYN to address class imbalance
            self.stdout.write(self.style.SUCCESS("\nApplying ADASYN to balance the dataset..."))
            self.stdout.write(self.style.SUCCESS(
                f"Original class distribution: {dict(zip(*np.unique(y, return_counts=True)))}"
            ))

            adasyn = ADASYN(random_state=options['random_state'])
            X_resampled, y_resampled = adasyn.fit_resample(X_preprocessed, y)

            self.stdout.write(self.style.SUCCESS(
                f"Balanced class distribution: {dict(zip(*np.unique(y_resampled, return_counts=True)))}"
            ))
            self.stdout.write(self.style.SUCCESS(
                f"Dataset size increased from {len(y)} to {len(y_resampled)} samples"
            ))

            # Split the balanced data into training and testing sets
            test_size = options['test_size']
            random_state = options['random_state']

            X_train, X_test, y_train, y_test = train_test_split(
                X_resampled, y_resampled, test_size=test_size,
                random_state=random_state, stratify=y_resampled
            )

            self.stdout.write(self.style.SUCCESS(f"\nTraining set size: {X_train.shape}"))
            self.stdout.write(self.style.SUCCESS(f"Testing set size: {X_test.shape}"))

            # Create SVM pipeline
            svm_pipeline = Pipeline([
                ('classifier', SVC(probability=True))
            ])

            # Grid search parameters for SVM
            param_grid = {
                'classifier__C': [0.1, 1, 10, 100],
                'classifier__gamma': ['scale', 'auto'],
                'classifier__kernel': ['rbf', 'linear', 'poly']
            }

            # Set up proper cross-validation with stratification
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)

            # Perform grid search
            self.stdout.write(self.style.SUCCESS("\nPerforming grid search to find optimal hyperparameters..."))
            grid_search = GridSearchCV(
                svm_pipeline,
                param_grid,
                cv=cv,
                scoring='balanced_accuracy',
                verbose=1,
                n_jobs=-1
            )

            # Fit to training data
            grid_search.fit(X_train, y_train)

            # Get best parameters
            self.stdout.write(self.style.SUCCESS(f"\nBest parameters: {grid_search.best_params_}"))
            self.stdout.write(self.style.SUCCESS(f"Best cross-validation score: {grid_search.best_score_:.4f}"))

            # Evaluate on test set
            best_model = grid_search.best_estimator_
            y_pred = best_model.predict(X_test)

            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred)
            self.stdout.write(self.style.SUCCESS(f"\nAccuracy on test set: {accuracy:.4f}"))

            # Classification report
            report = classification_report(y_test, y_pred)
            self.stdout.write(self.style.SUCCESS("\nClassification Report:"))
            self.stdout.write(self.style.SUCCESS(report))

            # Confusion matrix
            cm = confusion_matrix(y_test, y_pred)

            # Save confusion matrix visualization
            plt.figure(figsize=(10, 8))
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                        xticklabels=sorted(np.unique(y)),
                        yticklabels=sorted(np.unique(y)))
            plt.xlabel('Predicted')
            plt.ylabel('True')
            plt.title('Confusion Matrix')
            plt.tight_layout()

            confusion_matrix_path = os.path.join(plots_dir, 'confusion_matrix.png')
            plt.savefig(confusion_matrix_path)
            plt.close()

            self.stdout.write(self.style.SUCCESS(f"Confusion matrix saved to {confusion_matrix_path}"))

            # Save the model
            model_path = os.path.join(models_dir, 'hr_svm_model.pkl')
            joblib.dump(best_model, model_path)
            self.stdout.write(self.style.SUCCESS(f"\nModel saved to {model_path}"))

            # Performance score mapping for reference
            performance_mapping = {
                1: "PIP",
                2: "Needs Improvement",
                3: "Fully Meets",
                4: "Exceeds"
            }

            self.stdout.write(self.style.SUCCESS("\nPerformance score mapping:"))
            for code, description in performance_mapping.items():
                self.stdout.write(self.style.SUCCESS(f"{code}: {description}"))

            self.stdout.write(self.style.SUCCESS(
                "\nFinished training SVM model with advanced feature engineering and ADASYN balancing."
            ))

        except Exception as e:
            import traceback
            self.stdout.write(self.style.ERROR(f"Error training model: {str(e)}"))
            traceback.print_exc()