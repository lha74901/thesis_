# employee_predictor/management/commands/import_hr_dataset.py
from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
from django.db import transaction
from datetime import datetime
from .ml.employee_predictor.models import Employee
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import data from HRDataset.csv into the Employee model'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the HRDataset.csv file')
        parser.add_argument('--update', action='store_true', help='Update existing records')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update_existing = options['update']
        
        try:
            # Read CSV file
            self.stdout.write(self.style.SUCCESS(f'Reading from {csv_file}...'))
            df = pd.read_csv(csv_file)
            self.stdout.write(self.style.SUCCESS(f'Found {len(df)} records'))
            
            # Prepare data mapping
            records_created = 0
            records_updated = 0
            records_failed = 0
            
            # Start a transaction for bulk operations
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Map HRDataset fields to Employee model
                        emp_data = self.map_employee_data(row)
                        
                        # Create or update employee
                        employee, created = self.create_or_update_employee(emp_data, update_existing)
                        
                        if created:
                            records_created += 1
                        else:
                            records_updated += 1
                            
                    except Exception as e:
                        records_failed += 1
                        self.stdout.write(self.style.ERROR(f'Error processing record {index}: {str(e)}'))
                        logger.error(f'Error processing record {index}: {str(e)}')
                
            # Print results
            self.stdout.write(self.style.SUCCESS(f'Import completed:'))
            self.stdout.write(self.style.SUCCESS(f'Created: {records_created}'))
            self.stdout.write(self.style.SUCCESS(f'Updated: {records_updated}'))
            self.stdout.write(self.style.SUCCESS(f'Failed: {records_failed}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Import failed: {str(e)}'))
            logger.error(f'Import failed: {str(e)}', exc_info=True)
    
    def map_employee_data(self, row):
        """Map CSV row to Employee model fields"""
        # Common field mapping
        emp_data = {}
        
        # Extract name
        first_name = row.get('FirstName', '')
        last_name = row.get('LastName', '')
        name = f"{first_name} {last_name}".strip()
        if not name:
            name = "Employee " + str(row.get('EmpID', row.get('Employee_ID', index)))
        emp_data['name'] = name
        
        # Map employee ID
        emp_data['emp_id'] = str(row.get('EmpID', row.get('Employee_ID', '')))
        
        # Map department and position
        emp_data['department'] = row.get('Department', '')
        emp_data['position'] = row.get('Position', '')
        
        # Handle date fields
        if 'DateofHire' in row:
            try:
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        emp_data['date_of_hire'] = datetime.strptime(str(row['DateofHire']), fmt).date()
                        break
                    except ValueError:
                        continue
            except:
                # Fallback to current date
                emp_data['date_of_hire'] = datetime.now().date()
        
        # Map demographic data
        emp_data['gender'] = row.get('Sex', '').upper() if pd.notna(row.get('Sex', '')) else 'M'
        
        # Map marital status with fallback
        marital_status = row.get('MaritalDesc', '')
        if pd.isna(marital_status) or not marital_status:
            marital_status = 'Single'
        emp_data['marital_status'] = marital_status
        
        # Map age
        if 'Age' in row and pd.notna(row['Age']):
            emp_data['age'] = int(row['Age'])
        
        # Map race
        emp_data['race'] = row.get('RaceDesc', '')
        
        # Map Hispanic/Latino status
        hispanic_latino = row.get('HispanicLatino', '')
        if pd.isna(hispanic_latino) or not hispanic_latino:
            hispanic_latino = 'No'
        emp_data['hispanic_latino'] = hispanic_latino
        
        # Map recruitment source
        emp_data['recruitment_source'] = row.get('RecruitmentSource', '')
        
        # Map performance metrics
        emp_data['salary'] = float(row.get('Salary', 0))
        
        # Map engagement and satisfaction with defaults if missing
        engagement = row.get('EngagementSurvey', 0)
        emp_data['engagement_survey'] = float(engagement) if pd.notna(engagement) else 3.0
        
        satisfaction = row.get('EmpSatisfaction', 0)
        emp_data['emp_satisfaction'] = int(satisfaction) if pd.notna(satisfaction) else 3
        
        # Map special projects
        special_projects = row.get('SpecialProjectsCount', 0)
        emp_data['special_projects_count'] = int(special_projects) if pd.notna(special_projects) else 0
        
        # Map attendance metrics
        days_late = row.get('DaysLateLast30', 0)
        emp_data['days_late_last_30'] = int(days_late) if pd.notna(days_late) else 0
        
        absences = row.get('Absences', 0)
        emp_data['absences'] = int(absences) if pd.notna(absences) else 0
        
        # Map performance score - convert from numeric to categorical if needed
        if 'PerfScoreID' in row and pd.notna(row['PerfScoreID']):
            perf_id = int(row['PerfScoreID'])
            perf_map = {
                4: 'Exceeds',
                3: 'Fully Meets',
                2: 'Needs Improvement',
                1: 'PIP'
            }
            emp_data['performance_score'] = perf_map.get(perf_id, 'Fully Meets')
        elif 'PerformanceScore' in row and pd.notna(row['PerformanceScore']):
            emp_data['performance_score'] = row['PerformanceScore']
        
        # Map employment status
        if 'EmploymentStatus' in row and pd.notna(row['EmploymentStatus']):
            emp_data['employment_status'] = row['EmploymentStatus']
        else:
            # Default to 'Active'
            emp_data['employment_status'] = 'Active'
        
        return emp_data
    
    def create_or_update_employee(self, emp_data, update_existing):
        """Create or update Employee record"""
        emp_id = emp_data.get('emp_id')
        
        try:
            # Try to find existing employee
            employee = Employee.objects.get(emp_id=emp_id)
            
            # Update if requested
            if update_existing:
                for key, value in emp_data.items():
                    setattr(employee, key, value)
                employee.save()
                return employee, False
            else:
                return employee, False
                
        except Employee.DoesNotExist:
            # Create new employee
            employee = Employee.objects.create(**emp_data)
            return employee, True