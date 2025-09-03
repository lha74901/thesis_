# employee_predictor/management/commands/import_hr_dataset_v14.py
from django.core.management.base import BaseCommand
import pandas as pd
from datetime import datetime
from django.db import transaction
from employee_predictor.models import Employee
import logging
from django.conf import settings
import os

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import data from HRDataset_v14.csv into the Employee model'

    def add_arguments(self, parser):
        parser.add_argument('--csv_file', type=str, help='Path to the HRDataset_v14.csv file',
                            default='HRDataset_v14.csv')
        parser.add_argument('--update', action='store_true', help='Update existing records')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update_existing = options['update']

        # Try to find the file in different locations
        if not os.path.exists(csv_file):
            potential_paths = [
                os.path.join(settings.BASE_DIR, csv_file),
                os.path.join(settings.BASE_DIR, 'media', csv_file),
                os.path.join(settings.MEDIA_ROOT, csv_file)
            ]

            for path in potential_paths:
                if os.path.exists(path):
                    csv_file = path
                    break

        try:
            # Read CSV file
            self.stdout.write(self.style.SUCCESS(f'Reading from {csv_file}...'))
            df = pd.read_csv(csv_file)
            self.stdout.write(self.style.SUCCESS(f'Found {len(df)} records'))

            # Track progress
            records_created = 0
            records_updated = 0
            records_failed = 0

            # Start a transaction
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Process the row and create an employee record
                        employee_data = self._map_employee_data(row)

                        # Try to find existing employee by ID
                        emp_id = employee_data.get('emp_id')
                        try:
                            employee = Employee.objects.get(emp_id=emp_id)

                            # Update if requested
                            if update_existing:
                                for key, value in employee_data.items():
                                    setattr(employee, key, value)
                                employee.save()
                                records_updated += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f'Updated employee #{emp_id}: {employee_data["name"]}'))
                            else:
                                self.stdout.write(
                                    self.style.WARNING(f'Skipped existing employee #{emp_id}: {employee_data["name"]}'))

                        except Employee.DoesNotExist:
                            # Create new employee
                            employee = Employee.objects.create(**employee_data)
                            records_created += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Created employee #{emp_id}: {employee_data["name"]}'))

                    except Exception as e:
                        records_failed += 1
                        self.stdout.write(self.style.ERROR(f'Error processing record {index}: {str(e)}'))
                        logger.error(f'Error processing record {index}: {str(e)}')

            # Print summary
            self.stdout.write(self.style.SUCCESS(f'Import completed:'))
            self.stdout.write(self.style.SUCCESS(f'Created: {records_created}'))
            self.stdout.write(self.style.SUCCESS(f'Updated: {records_updated}'))
            self.stdout.write(self.style.SUCCESS(f'Failed: {records_failed}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import failed: {str(e)}'))
            logger.error(f'Import failed: {str(e)}', exc_info=True)

    def _map_employee_data(self, row):
        """Map CSV data to Employee model fields"""
        employee_data = {}

        # Basic employee information
        employee_data['name'] = row.get('Employee_Name', '')
        employee_data['emp_id'] = str(row.get('EmpID', ''))

        # Gender
        if 'Sex' in row and pd.notna(row['Sex']):
            employee_data['gender'] = row['Sex'][0].upper()  # Take first letter (M/F)

        # Date of birth
        if 'DOB' in row and pd.notna(row['DOB']):
            try:
                dob = self._parse_date(row['DOB'])
                if dob:
                    employee_data['date_of_birth'] = dob
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not parse DOB: {row['DOB']} - {str(e)}"))

        # Location
        if 'State' in row and pd.notna(row['State']):
            employee_data['state'] = row['State']

        if 'Zip' in row and pd.notna(row['Zip']):
            employee_data['zip_code'] = str(row['Zip'])

        # Marital status
        if 'MaritalDesc' in row and pd.notna(row['MaritalDesc']):
            employee_data['marital_status'] = row['MaritalDesc']

        # Citizenship & Diversity
        if 'CitizenDesc' in row and pd.notna(row['CitizenDesc']):
            employee_data['citizenship'] = row['CitizenDesc']

        if 'RaceDesc' in row and pd.notna(row['RaceDesc']):
            employee_data['race'] = row['RaceDesc']

        if 'HispanicLatino' in row and pd.notna(row['HispanicLatino']):
            employee_data['hispanic_latino'] = row['HispanicLatino']

        if 'FromDiversityJobFairID' in row and pd.notna(row['FromDiversityJobFairID']):
            employee_data['from_diversity_job_fair'] = bool(row['FromDiversityJobFairID'])

        # Employment Information
        if 'Department' in row and pd.notna(row['Department']):
            employee_data['department'] = row['Department']

        if 'Position' in row and pd.notna(row['Position']):
            employee_data['position'] = row['Position']

        if 'DateofHire' in row and pd.notna(row['DateofHire']):
            try:
                hire_date = self._parse_date(row['DateofHire'])
                if hire_date:
                    employee_data['date_of_hire'] = hire_date
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not parse DateofHire: {row['DateofHire']} - {str(e)}"))

        if 'RecruitmentSource' in row and pd.notna(row['RecruitmentSource']):
            employee_data['recruitment_source'] = row['RecruitmentSource']

        # Management
        if 'ManagerName' in row and pd.notna(row['ManagerName']):
            employee_data['manager_name'] = row['ManagerName']

        if 'ManagerID' in row and pd.notna(row['ManagerID']):
            employee_data['manager_id'] = str(row['ManagerID'])

        # Termination information
        if 'DateofTermination' in row and pd.notna(row['DateofTermination']):
            try:
                term_date = self._parse_date(row['DateofTermination'])
                if term_date:
                    employee_data['date_of_termination'] = term_date
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Could not parse DateofTermination: {row['DateofTermination']} - {str(e)}"))

        if 'TermReason' in row and pd.notna(row['TermReason']):
            employee_data['termination_reason'] = row['TermReason']

        if 'Termd' in row and pd.notna(row['Termd']):
            employee_data['is_terminated'] = bool(row['Termd'])

        # Employment status
        if 'EmploymentStatus' in row and pd.notna(row['EmploymentStatus']):
            status = row['EmploymentStatus']
            # Map to your model's choices
            if 'Active' in status:
                employee_data['employment_status'] = 'Active'
            elif 'Voluntarily' in status or 'Voluntary' in status:
                employee_data['employment_status'] = 'Voluntarily Terminated'
            elif 'Terminated' in status:
                employee_data['employment_status'] = 'Terminated for Cause'

        # Performance metrics
        if 'Salary' in row and pd.notna(row['Salary']):
            employee_data['salary'] = float(row['Salary'])

        if 'EngagementSurvey' in row and pd.notna(row['EngagementSurvey']):
            employee_data['engagement_survey'] = float(row['EngagementSurvey'])

        if 'EmpSatisfaction' in row and pd.notna(row['EmpSatisfaction']):
            employee_data['emp_satisfaction'] = int(row['EmpSatisfaction'])

        if 'SpecialProjectsCount' in row and pd.notna(row['SpecialProjectsCount']):
            employee_data['special_projects_count'] = int(row['SpecialProjectsCount'])

        if 'DaysLateLast30' in row and pd.notna(row['DaysLateLast30']):
            employee_data['days_late_last_30'] = int(row['DaysLateLast30'])

        if 'Absences' in row and pd.notna(row['Absences']):
            employee_data['absences'] = int(row['Absences'])

        if 'LastPerformanceReview_Date' in row and pd.notna(row['LastPerformanceReview_Date']):
            try:
                review_date = self._parse_date(row['LastPerformanceReview_Date'])
                if review_date:
                    employee_data['last_performance_review_date'] = review_date
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"Could not parse LastPerformanceReview_Date: {row['LastPerformanceReview_Date']} - {str(e)}"))

        # Performance score
        if 'PerformanceScore' in row and pd.notna(row['PerformanceScore']):
            score = row['PerformanceScore']

            # Map performance score text to model choices
            if 'Exceeds' in score:
                employee_data['performance_score'] = 'Exceeds'
            elif 'Fully' in score or 'Meets' in score:
                employee_data['performance_score'] = 'Fully Meets'
            elif 'Improvement' in score and not 'PIP' in score:
                employee_data['performance_score'] = 'Needs Improvement'
            elif 'PIP' in score:
                employee_data['performance_score'] = 'PIP'
        elif 'PerfScoreID' in row and pd.notna(row['PerfScoreID']):
            # Map numeric score to text
            score_id = int(row['PerfScoreID'])
            score_map = {
                4: 'Exceeds',
                3: 'Fully Meets',
                2: 'Needs Improvement',
                1: 'PIP'
            }
            employee_data['performance_score'] = score_map.get(score_id, None)

        return employee_data

    def _parse_date(self, date_string):
        """Parse date from string in multiple formats"""
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%m-%d-%Y',
            '%d-%m-%Y'
        ]

        # Try each format
        for fmt in date_formats:
            try:
                return datetime.strptime(str(date_string).strip(), fmt).date()
            except ValueError:
                continue

        # If none of the formats work, return None
        return None