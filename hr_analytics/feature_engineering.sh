#!/bin/bash

# Backup the original file
cp employee_predictor/ml/feature_engineering.py employee_predictor/ml/feature_engineering.py.bak

# Create the fixed feature_engineering.py file
cat > employee_predictor/ml/feature_engineering.py << 'EOL'
# employee_predictor/ml/feature_engineering.py
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
import os
import joblib
from django.conf import settings

# Define feature categories for preprocessing
MINMAX_FEATURES = ['DaysLateLast30', 'Absences', 'SpecialProjectsCount']
ZSCORE_FEATURES = ['EngagementSurvey', 'EmpSatisfaction', 'Salary', 'Tenure_Years', 'Age']
LABEL_FEATURES = ['Sex', 'EmploymentStatus']
ONEHOT_FEATURES = ['Position', 'RaceDesc', 'RecruitmentSource', 'MaritalDesc', 'Department']

# Store encoders for reuse
LABEL_ENCODERS = {}


def get_preprocessor():
    """Returns the column transformer for preprocessing features"""
    return ColumnTransformer(
        transformers=[
            ('minmax', MinMaxScaler(), MINMAX_FEATURES),
            ('zscore', StandardScaler(), ZSCORE_FEATURES),
            ('onehot', OneHotEncoder(drop='first', sparse_output=False, handle_unknown='ignore'), ONEHOT_FEATURES)
        ],
        remainder='passthrough'
    )