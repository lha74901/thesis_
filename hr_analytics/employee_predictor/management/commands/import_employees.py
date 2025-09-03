# management/commands/import_employees.py
import csv
import os
from decimal import Decimal
from datetime import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from employee_predictor.models import Employee  # Adjust the app name as needed


class Command(BaseCommand):
    help = 'Import employees from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing employees if they exist',
        )

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        update_existing = options['update']

        if not os.path.exists(csv_file_path):
            self.stdout.write(
                self.style.ERROR(f'File {csv_file_path} does not exist')
            )
            return

        success_count = 0
        error_count = 0

        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Clean and prepare data
                    emp_data = self.clean_row_data(row)

                    # Check if employee exists
                    employee, created = Employee.objects.get_or_create(
                        emp_id=emp_data['emp_id'],
                        defaults=emp_data
                    )

                    if not created and update_existing:
                        # Update existing employee
                        for key, value in emp_data.items():
                            setattr(employee, key, value)
                        employee.save()
                        self.stdout.write(f"Updated employee: {employee.name}")
                    elif created:
                        self.stdout.write(f"Created employee: {employee.name}")
                    else:
                        self.stdout.write(f"Skipped existing employee: {emp_data['emp_id']}")

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Error on row {row_num}: {str(e)}')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Import completed. Success: {success_count}, Errors: {error_count}'
            )
        )

    def clean_row_data(self, row):
        """Clean and convert row data to appropriate types"""

        cleaned_data = {}

        # Basic information - Map CSV headers to Django model fields
        cleaned_data['name'] = row.get('name', '').strip()
        cleaned_data['emp_id'] = row.get('EmpID', '').strip()  # CSV uses 'EmpID'
        cleaned_data['department'] = row.get('Department', '').strip()  # CSV uses 'Department'
        cleaned_data['position'] = row.get('Position', '').strip()  # CSV uses 'Position'

        # Demographics - Fix gender mapping
        gender = row.get('Sex', '').strip().upper()  # CSV uses 'Sex'
        cleaned_data['gender'] = gender[:1] if gender in ['M', 'F'] else 'M'  # Default to M if invalid

        # Marital status mapping
        marital_desc = row.get('MaritalDesc', '').strip()  # CSV uses 'MaritalDesc'
        cleaned_data['marital_status'] = marital_desc if marital_desc else 'Single'

        # Convert age to integer
        try:
            age_val = row.get('Age', '')
            cleaned_data['age'] = int(age_val) if age_val and str(age_val).strip() else None
        except (ValueError, TypeError):
            cleaned_data['age'] = None

        # Handle missing required fields with defaults
        cleaned_data['race'] = row.get('race', '').strip() or 'Not Specified'

        # Hispanic/Latino - set default if empty
        hispanic_val = row.get('hispanic_latino', '').strip()
        cleaned_data['hispanic_latino'] = hispanic_val if hispanic_val in ['Yes', 'No'] else 'No'

        cleaned_data['recruitment_source'] = row.get('recruitment_source', '').strip() or 'Unknown'

        # Performance metrics - Map CSV headers
        try:
            salary_str = str(row.get('Salary', '0')).replace('$', '').replace(',', '').strip()  # CSV uses 'Salary'
            cleaned_data['salary'] = Decimal(salary_str) if salary_str else Decimal('0')
        except (ValueError, TypeError):
            cleaned_data['salary'] = Decimal('0')

        try:
            engagement_val = row.get('EngagementSurvey', '')  # CSV uses 'EngagementSurvey'
            engagement_float = float(engagement_val) if engagement_val else 3.0
            # Ensure it's between 1.0 and 5.0
            cleaned_data['engagement_survey'] = max(1.0, min(5.0, engagement_float))
        except (ValueError, TypeError):
            cleaned_data['engagement_survey'] = 3.0

        try:
            satisfaction_val = row.get('EmpSatisfaction', '')  # CSV uses 'EmpSatisfaction'
            satisfaction_int = int(satisfaction_val) if satisfaction_val else 3
            # Ensure it's between 1 and 5
            cleaned_data['emp_satisfaction'] = max(1, min(5, satisfaction_int))
        except (ValueError, TypeError):
            cleaned_data['emp_satisfaction'] = 3

        try:
            cleaned_data['special_projects_count'] = int(
                row.get('SpecialProjectsCount', 0))  # CSV uses 'SpecialProjectsCount'
        except (ValueError, TypeError):
            cleaned_data['special_projects_count'] = 0

        try:
            cleaned_data['days_late_last_30'] = int(row.get('DaysLateLast30', 0))  # CSV uses 'DaysLateLast30'
        except (ValueError, TypeError):
            cleaned_data['days_late_last_30'] = 0

        try:
            cleaned_data['absences'] = int(row.get('Absences', 0))  # CSV uses 'Absences'
        except (ValueError, TypeError):
            cleaned_data['absences'] = 0

        # Performance score
        perf_score = row.get('PerformanceScore', '').strip()  # CSV uses 'PerformanceScore'
        valid_scores = ['Exceeds', 'Fully Meets', 'Needs Improvement', 'PIP']
        cleaned_data['performance_score'] = perf_score if perf_score in valid_scores else ''

        # Employment status - set default if empty
        emp_status = row.get('employment_status', '').strip()
        cleaned_data['employment_status'] = emp_status if emp_status else 'Active'

        return cleaned_data