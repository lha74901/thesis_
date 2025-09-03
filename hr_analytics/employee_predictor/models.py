# employee_predictor/models.py
from django.contrib.auth.models import User
from django.db import models
from datetime import datetime
from decimal import Decimal
import json
import logging
from django.utils import timezone as django_timezone
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


class Employee(models.Model):
    # Link to User model (for login functionality)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    # Basic employee information
    name = models.CharField(max_length=100)
    emp_id = models.CharField(max_length=20, unique=True)

    # Fields from HRDataset
    department = models.CharField(max_length=50)
    position = models.CharField(max_length=50)
    date_of_hire = models.DateField(null=True, blank=True)

    # Demographic information
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    MARITAL_STATUS_CHOICES = [
        ('Married', 'Married'),
        ('Single', 'Single'),
        ('Divorced', 'Divorced'),
        ('Separated', 'Separated'),
        ('Widowed', 'Widowed')
    ]
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS_CHOICES)

    age = models.IntegerField(null=True, blank=True)
    race = models.CharField(max_length=50, blank=True)

    HISPANIC_LATINO_CHOICES = [('Yes', 'Yes'), ('No', 'No')]
    hispanic_latino = models.CharField(max_length=3, choices=HISPANIC_LATINO_CHOICES, default='No')

    # Recruitment information
    recruitment_source = models.CharField(max_length=100, blank=True)

    # Performance metrics - key fields used in ML prediction
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    engagement_survey = models.FloatField(help_text="Score from 1-5")
    emp_satisfaction = models.IntegerField(help_text="Score from 1-5")
    special_projects_count = models.IntegerField(default=0)
    days_late_last_30 = models.IntegerField(default=0)
    absences = models.IntegerField(default=0)

    # Performance evaluation
    PERFORMANCE_SCORE_CHOICES = [
        ('Exceeds', 'Exceeds Expectations'),
        ('Fully Meets', 'Fully Meets Expectations'),
        ('Needs Improvement', 'Needs Improvement'),
        ('PIP', 'Performance Improvement Plan')
    ]
    performance_score = models.CharField(
        max_length=20,
        choices=PERFORMANCE_SCORE_CHOICES,
        null=True,
        blank=True
    )

    # ML prediction fields
    predicted_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Predicted score: 4=Exceeds, 3=Fully Meets, 2=Needs Improvement, 1=PIP"
    )
    prediction_date = models.DateTimeField(null=True, blank=True)
    prediction_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score for the prediction (0-1)"
    )
    prediction_details = models.TextField(
        null=True,
        blank=True,
        help_text="JSON string with detailed prediction info"
    )

    # Employment status
    EMPLOYMENT_STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Voluntarily Terminated', 'Voluntarily Terminated'),
        ('Terminated for Cause', 'Terminated for Cause')
    ]
    employment_status = models.CharField(
        max_length=50,
        choices=EMPLOYMENT_STATUS_CHOICES,
        default='Active'
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['emp_id']),
            models.Index(fields=['department']),
            models.Index(fields=['predicted_score']),
            models.Index(fields=['prediction_date']),
        ]

    def __str__(self):
        return f"{self.name} ({self.emp_id})"

    def clean(self):
        """Validate model data"""
        super().clean()

        # Validate engagement survey score
        if self.engagement_survey is not None:
            if not (1.0 <= self.engagement_survey <= 5.0):
                raise ValidationError({'engagement_survey': 'Must be between 1.0 and 5.0'})

        # Validate employee satisfaction
        if self.emp_satisfaction is not None:
            if not (1 <= self.emp_satisfaction <= 5):
                raise ValidationError({'emp_satisfaction': 'Must be between 1 and 5'})

        # Validate predicted score
        if self.predicted_score is not None:
            if not (1 <= self.predicted_score <= 4):
                raise ValidationError({'predicted_score': 'Must be between 1 and 4'})

        # Validate days late
        if self.days_late_last_30 is not None:
            if not (0 <= self.days_late_last_30 <= 30):
                raise ValidationError({'days_late_last_30': 'Must be between 0 and 30'})

    def save(self, *args, **kwargs):
        """Override save to ensure data consistency"""
        # Clean data before saving
        self.full_clean()

        # Ensure consistency between predicted_score and performance_score
        if self.predicted_score is not None:
            score_mapping = {
                4: 'Exceeds',
                3: 'Fully Meets',
                2: 'Needs Improvement',
                1: 'PIP'
            }
            if self.predicted_score in score_mapping:
                self.performance_score = score_mapping[self.predicted_score]

        super().save(*args, **kwargs)

    def salary_as_float(self):
        """Convert salary to float for calculations"""
        try:
            return float(self.salary) if self.salary else 0.0
        except (ValueError, TypeError):
            return 0.0

    def get_tenure_years(self):
        """Calculate employee's tenure in years"""
        if not self.date_of_hire:
            return 0

        try:
            today = datetime.now().date()
            tenure_days = (today - self.date_of_hire).days
            return max(0, tenure_days / 365.25)
        except Exception as e:
            logger.warning(f"Error calculating tenure for {self.emp_id}: {str(e)}")
            return 0

    def save_prediction_details(self, prediction_result):
        """
        Save detailed prediction results with robust error handling

        Args:
            prediction_result (dict): Dictionary containing prediction results
        """
        try:
            if not isinstance(prediction_result, dict):
                logger.error(f"Invalid prediction result type for {self.emp_id}: {type(prediction_result)}")
                return False

            # Extract prediction score with multiple possible keys
            prediction_score = None
            for key in ['prediction', 'prediction_score', 'predicted_score']:
                if key in prediction_result:
                    prediction_score = prediction_result[key]
                    break

            if prediction_score is None:
                logger.error(f"No prediction score found in results for {self.emp_id}")
                return False

            # Validate and set prediction score
            try:
                prediction_score = int(prediction_score)
                if 1 <= prediction_score <= 4:
                    self.predicted_score = prediction_score
                else:
                    logger.error(f"Invalid prediction score {prediction_score} for {self.emp_id}")
                    return False
            except (ValueError, TypeError):
                logger.error(f"Cannot convert prediction score to int for {self.emp_id}: {prediction_score}")
                return False

            # Map prediction score to performance category
            score_mapping = {
                4: 'Exceeds',
                3: 'Fully Meets',
                2: 'Needs Improvement',
                1: 'PIP'
            }

            if self.predicted_score in score_mapping:
                self.performance_score = score_mapping[self.predicted_score]

            # Save confidence score if available
            probabilities = prediction_result.get('probabilities', {})
            if probabilities and isinstance(probabilities, dict):
                if self.predicted_score in probabilities:
                    try:
                        confidence = float(probabilities[self.predicted_score])
                        self.prediction_confidence = max(0.0, min(1.0, confidence))
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid confidence value for {self.emp_id}")

            # Save detailed prediction information as JSON
            prediction_details = {
                'prediction_score': self.predicted_score,
                'prediction_label': prediction_result.get('prediction_label', ''),
                'probabilities': probabilities,
                'key_factors': prediction_result.get('key_factors', []),
                'prediction_method': prediction_result.get('prediction_method', 'enhanced_predictor'),
                'timestamp': django_timezone.now().isoformat(),
                'model_version': prediction_result.get('model_version', '1.0')
            }

            try:
                self.prediction_details = json.dumps(prediction_details, default=str)
            except Exception as e:
                logger.error(f"Error serializing prediction details for {self.emp_id}: {str(e)}")
                # Save minimal details
                self.prediction_details = json.dumps({
                    'prediction_score': self.predicted_score,
                    'timestamp': django_timezone.now().isoformat(),
                    'error': 'Failed to serialize full details'
                })

            # Set prediction date
            self.prediction_date = django_timezone.now()

            # Save the model instance
            self.save()

            logger.info(f"Prediction details saved for {self.emp_id}: score={self.predicted_score}")
            return True

        except Exception as e:
            logger.error(f"Error saving prediction details for {self.emp_id}: {str(e)}")
            return False

    def get_performance_label(self):
        """Get human-readable performance label"""
        if self.predicted_score is not None:
            score_mapping = {
                4: 'Exceeds Expectations',
                3: 'Fully Meets Expectations',
                2: 'Needs Improvement',
                1: 'Performance Improvement Plan (PIP)'
            }
            return score_mapping.get(self.predicted_score, "Unknown Score")
        elif self.performance_score:
            label_mapping = {
                'Exceeds': 'Exceeds Expectations',
                'Fully Meets': 'Fully Meets Expectations',
                'Needs Improvement': 'Needs Improvement',
                'PIP': 'Performance Improvement Plan (PIP)'
            }
            return label_mapping.get(self.performance_score, self.performance_score)
        else:
            return "Not Evaluated"

    def get_prediction_details(self):
        """Get parsed prediction details with error handling"""
        if not self.prediction_details:
            return None

        try:
            return json.loads(self.prediction_details)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing prediction details for {self.emp_id}: {str(e)}")
            return None

    def get_key_performance_factors(self):
        """Get key factors that influenced the prediction"""
        details = self.get_prediction_details()
        if details and 'key_factors' in details:
            return details['key_factors']
        return []

    def get_prediction_probabilities(self):
        """Get prediction probabilities"""
        details = self.get_prediction_details()
        if details and 'probabilities' in details:
            return details['probabilities']
        return {}

    def get_performance_color(self):
        """Get color code representing performance level for UI"""
        if self.predicted_score is not None:
            colors = {
                4: 'success',  # Green for Exceeds
                3: 'info',  # Blue for Fully Meets
                2: 'warning',  # Yellow for Needs Improvement
                1: 'danger'  # Red for PIP
            }
            return colors.get(self.predicted_score, 'secondary')
        return 'secondary'

    def get_performance_trend(self):
        """Get performance trend based on historical data"""
        # This could be expanded to compare with previous predictions
        if self.prediction_confidence is not None:
            if self.prediction_confidence >= 0.8:
                return 'stable'
            elif self.prediction_confidence >= 0.6:
                return 'moderate'
            else:
                return 'uncertain'
        return 'unknown'

    def is_high_performer(self):
        """Check if employee is a high performer"""
        return self.predicted_score is not None and self.predicted_score >= 4

    def needs_attention(self):
        """Check if employee needs attention"""
        return self.predicted_score is not None and self.predicted_score <= 2

    def get_risk_factors(self):
        """Get list of risk factors for employee"""
        risk_factors = []

        if self.engagement_survey and self.engagement_survey < 3.0:
            risk_factors.append("Low engagement score")

        if self.emp_satisfaction and self.emp_satisfaction < 3:
            risk_factors.append("Low job satisfaction")

        if self.absences and self.absences > 5:
            risk_factors.append("High absenteeism")

        if self.days_late_last_30 and self.days_late_last_30 > 3:
            risk_factors.append("Punctuality issues")

        if self.special_projects_count == 0:
            risk_factors.append("No special project participation")

        return risk_factors


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)

    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('HALF_DAY', 'Half Day'),
        ('ON_LEAVE', 'On Leave')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date', 'employee']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.date} ({self.status})"

    def clean(self):
        """Validate attendance data"""
        super().clean()

        # Validate hours worked
        if self.hours_worked is not None:
            if not (0 <= self.hours_worked <= 24):
                raise ValidationError({'hours_worked': 'Hours worked must be between 0 and 24'})

    def calculate_hours_worked(self):
        """Calculate hours worked based on check-in and check-out times"""
        if self.check_out and self.check_in and self.status in ['PRESENT', 'LATE']:
            try:
                check_in_dt = datetime.combine(self.date, self.check_in)
                check_out_dt = datetime.combine(self.date, self.check_out)

                # Handle case where check-out is next day
                if check_out_dt < check_in_dt:
                    from datetime import timedelta
                    check_out_dt += timedelta(days=1)

                duration = check_out_dt - check_in_dt
                hours = duration.total_seconds() / 3600
                return round(Decimal(str(hours)), 2)
            except Exception as e:
                logger.warning(f"Error calculating hours for attendance {self.id}: {str(e)}")

        return Decimal('0.00')

    def save(self, *args, **kwargs):
        """Override save to calculate hours worked"""
        # Clean data before saving
        self.full_clean()

        # Auto-calculate hours worked
        if self.status == 'ON_LEAVE':
            self.check_in = None
            self.check_out = None
            self.hours_worked = Decimal('0.00')
        elif self.check_out and self.check_in and self.status in ['PRESENT', 'LATE']:
            self.hours_worked = self.calculate_hours_worked()

        super().save(*args, **kwargs)


class Leave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()

    LEAVE_TYPE_CHOICES = [
        ('ANNUAL', 'Annual Leave'),
        ('SICK', 'Sick Leave'),
        ('UNPAID', 'Unpaid Leave'),
        ('MATERNITY', 'Maternity Leave'),
        ('PATERNITY', 'Paternity Leave'),
        ('OTHER', 'Other')
    ]
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES)

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    reason = models.TextField()
    approved_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    approval_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['status', 'start_date']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type} ({self.start_date} to {self.end_date})"

    def clean(self):
        """Validate leave data"""
        super().clean()

        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({'end_date': 'End date cannot be before start date'})

    def duration_days(self):
        """Calculate leave duration in days"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    def is_active(self):
        """Check if leave is currently active"""
        if self.status != 'APPROVED':
            return False

        today = datetime.now().date()
        return self.start_date <= today <= self.end_date

    def save(self, *args, **kwargs):
        """Override save to validate data"""
        self.full_clean()
        super().save(*args, **kwargs)


class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payroll_records')
    period_start = models.DateField()
    period_end = models.DateField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overtime_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    bonuses = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)

    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')

    payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_end', 'employee']
        indexes = [
            models.Index(fields=['employee', 'period_start']),
            models.Index(fields=['period_end', 'status']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.period_start} to {self.period_end}"

    def clean(self):
        """Validate payroll data"""
        super().clean()

        if self.period_start and self.period_end:
            if self.period_end < self.period_start:
                raise ValidationError({'period_end': 'End date cannot be before start date'})

    def calculate_gross_salary(self):
        """Calculate gross salary including overtime and bonuses"""
        overtime_pay = self.overtime_hours * self.overtime_rate
        return self.basic_salary + overtime_pay + self.bonuses

    def calculate_total_deductions(self):
        """Calculate total deductions including tax"""
        return self.deductions + self.tax

    def calculate_net_salary(self):
        """Calculate net salary after deductions"""
        gross_salary = self.calculate_gross_salary()
        total_deductions = self.calculate_total_deductions()
        return gross_salary - total_deductions

    def save(self, *args, **kwargs):
        """Override save to calculate net salary"""
        # Clean data before saving
        self.full_clean()

        # Auto-calculate net salary if not provided
        if not self.net_salary:
            self.net_salary = self.calculate_net_salary()

        super().save(*args, **kwargs)


class PerformanceHistory(models.Model):
    """Track performance history over time"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='performance_history')
    review_date = models.DateField()

    PERFORMANCE_SCORE_CHOICES = [
        ('Exceeds', 'Exceeds Expectations'),
        ('Fully Meets', 'Fully Meets Expectations'),
        ('Needs Improvement', 'Needs Improvement'),
        ('PIP', 'Performance Improvement Plan')
    ]
    performance_score = models.CharField(max_length=20, choices=PERFORMANCE_SCORE_CHOICES)

    score_value = models.IntegerField(help_text="Numeric value 1-4")
    reviewer = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(blank=True)
    goals_met = models.BooleanField(default=False)
    improvement_areas = models.TextField(blank=True)
    strengths = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-review_date', 'employee']
        verbose_name_plural = "Performance Histories"
        indexes = [
            models.Index(fields=['employee', 'review_date']),
            models.Index(fields=['performance_score', 'review_date']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.review_date} ({self.performance_score})"

    def clean(self):
        """Validate performance history data"""
        super().clean()

        if self.score_value is not None:
            if not (1 <= self.score_value <= 4):
                raise ValidationError({'score_value': 'Score value must be between 1 and 4'})

    def save(self, *args, **kwargs):
        """Override save to ensure consistency"""
        # Clean data before saving
        self.full_clean()

        # Ensure score_value matches performance_score
        score_mapping = {
            'PIP': 1,
            'Needs Improvement': 2,
            'Fully Meets': 3,
            'Exceeds': 4
        }

        if self.performance_score in score_mapping:
            self.score_value = score_mapping[self.performance_score]

        super().save(*args, **kwargs)