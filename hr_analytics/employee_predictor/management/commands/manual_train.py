# manual_train.py
# Place this script in your project root directory
# Run with: python manual_train.py

import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
import joblib
from decimal import Decimal

# Create models directory if it doesn't exist
os.makedirs('media/models', exist_ok=True)


# Sample data creation - replace this with your actual data loading
def create_sample_data(n_samples=100):
    np.random.seed(42)

    # Create a DataFrame with sample employee data
    data = {
        'engagement_survey': np.random.uniform(1, 5, n_samples),
        'emp_satisfaction': np.random.randint(1, 6, n_samples),
        'special_projects_count': np.random.randint(0, 5, n_samples),
        'days_late_last_30': np.random.randint(0, 10, n_samples),
        'absences': np.random.randint(0, 15, n_samples),
        'salary': np.random.uniform(30000, 120000, n_samples),
        'gender': np.random.choice(['M', 'F'], n_samples),
        'tenure': np.random.uniform(0, 15, n_samples)
    }

    df = pd.DataFrame(data)

    # Generate a target variable based on the features
    def generate_performance(row):
        score = 0
        score += (row['engagement_survey'] - 3) * 0.8
        score += (row['emp_satisfaction'] - 3) * 0.7
        score += row['special_projects_count'] * 0.3
        score -= row['days_late_last_30'] * 0.1
        score -= row['absences'] * 0.2

        if score < -2:
            return 1  # PIP
        elif score < 0:
            return 2  # Needs Improvement
        elif score < 2:
            return 3  # Fully Meets
        else:
            return 4  # Exceeds

    df['performance_score'] = df.apply(generate_performance, axis=1)

    return df


# Create sample data
print("Creating sample data...")
df = create_sample_data(500)
print(f"Created {len(df)} sample records")

# Preprocess data
print("Preprocessing data...")
X = df[['engagement_survey', 'emp_satisfaction', 'special_projects_count',
        'days_late_last_30', 'absences', 'salary', 'tenure']]
y = df['performance_score']

# Encode categorical variables
le = LabelEncoder()
df['gender_encoded'] = le.fit_transform(df['gender'])
X['gender'] = df['gender_encoded']

# Scale the data
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split the data
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# Train the model
print("Training SVM model...")
svm = SVC(C=10, kernel='rbf', gamma='scale', probability=True, random_state=42)
svm.fit(X_train, y_train)

# Evaluate the model
train_acc = svm.score(X_train, y_train)
test_acc = svm.score(X_test, y_test)
print(f"Train accuracy: {train_acc:.4f}")
print(f"Test accuracy: {test_acc:.4f}")

# Save the model
print("Saving model...")
joblib.dump(svm, 'media/models/hr_svm_model.pkl')
joblib.dump(scaler, 'media/models/scaler.pkl')
joblib.dump(le, 'media/models/label_encoders.pkl')

print("Done! Model saved to media/models/hr_svm_model.pkl")