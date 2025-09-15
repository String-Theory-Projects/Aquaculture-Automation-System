from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from core.choices import (
    AUTOMATION_TYPES, AUTOMATION_ACTIONS, COMMAND_TYPES, 
    COMMAND_STATUS, LOG_TYPES
)
from core.constants import AUTOMATION_PRIORITIES
from ponds.models import Pond, PondPair
import uuid
from django.utils import timezone
from datetime import time


class AutomationExecution(models.Model):
    """Model for tracking automation executions"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='automation_executions')
    
    # Execution details
    execution_type = models.CharField(max_length=20, choices=AUTOMATION_TYPES)
    action = models.CharField(max_length=20, choices=AUTOMATION_ACTIONS)
    priority = models.CharField(
        max_length=20,
        choices=[(priority, priority.replace('_', ' ').title()) for priority in AUTOMATION_PRIORITIES],
        default='THRESHOLD'
    )
    
    # Execution status
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('EXECUTING', 'Executing'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING'
    )
    
    # Execution details
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Parameters
    parameters = models.JSONField(default=dict, blank=True)
    
    # Results
    success = models.BooleanField(default=True)
    result_message = models.TextField(null=True, blank=True)
    error_details = models.TextField(null=True, blank=True)
    
    # Related objects
    schedule = models.ForeignKey(
        'AutomationSchedule', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='executions'
    )
    threshold = models.ForeignKey(
        'ponds.SensorThreshold', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='automation_executions'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='automation_executions_v2'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pond', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['execution_type', 'status']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.execution_type} execution for {self.pond.name} - {self.status}"
    
    def start_execution(self):
        """Mark execution as started"""
        self.status = 'EXECUTING'
        self.started_at = timezone.now()
        self.save()
    
    def complete_execution(self, success=True, message=None, error_details=None):
        """Mark execution as completed"""
        self.status = 'COMPLETED' if success else 'FAILED'
        self.success = success
        self.completed_at = timezone.now()
        self.result_message = message
        self.error_details = error_details
        self.save()
    
    def cancel_execution(self):
        """Cancel the execution"""
        if self.status in ['PENDING', 'EXECUTING']:
            self.status = 'CANCELLED'
            self.completed_at = timezone.now()
            self.save()
    
    def is_executable(self):
        """Check if execution can be started"""
        if not self.scheduled_at:
            return False
        return self.status == 'PENDING' and self.scheduled_at <= timezone.now()


class DeviceCommand(models.Model):
    """Model for managing device commands and their execution"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='device_commands')
    command_type = models.CharField(max_length=20, choices=COMMAND_TYPES)
    status = models.CharField(max_length=20, choices=COMMAND_STATUS, default='PENDING')
    
    # Command details
    command_id = models.UUIDField(default=uuid.uuid4, unique=True)
    parameters = models.JSONField(default=dict, blank=True)
    
    # Execution tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Timeout and retry settings
    timeout_seconds = models.IntegerField(default=settings.DEVICE_COMMAND_TIMEOUT_SECONDS)
    max_retries = models.IntegerField(default=settings.DEVICE_COMMAND_MAX_RETRIES)
    retry_count = models.IntegerField(default=0)
    
    # Results
    success = models.BooleanField(default=True)
    result_message = models.TextField(null=True, blank=True)
    error_code = models.CharField(max_length=50, null=True, blank=True)
    error_details = models.TextField(null=True, blank=True)
    
    # Related objects
    automation_execution = models.ForeignKey(
        AutomationExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_commands'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_commands_v2'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pond', 'status']),
            models.Index(fields=['command_type', 'status']),
            models.Index(fields=['command_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.command_type} command for {self.pond.name} - {self.status}"
    
    def send_command(self):
        """Mark command as sent"""
        self.status = 'SENT'
        self.sent_at = timezone.now()
        self.save()
    
    def acknowledge_command(self):
        """Mark command as acknowledged"""
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_at = timezone.now()
        self.save()
    
    def complete_command(self, success=True, message=None, error_code=None, error_details=None):
        """Mark command as completed"""
        self.status = 'COMPLETED' if success else 'FAILED'
        self.success = success
        self.completed_at = timezone.now()
        self.result_message = message
        self.error_code = error_code
        self.error_details = error_details
        self.save()
    
    def timeout_command(self):
        """Mark command as timed out"""
        self.status = 'TIMEOUT'
        self.completed_at = timezone.now()
        self.save()
    
    def retry_command(self):
        """Increment retry count and reset status"""
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.status = 'PENDING'
            self.sent_at = None
            self.acknowledged_at = None
            self.save()
            return True
        return False
    
    def is_retryable(self):
        """Check if command can be retried"""
        return self.retry_count < self.max_retries and self.status in ['FAILED', 'TIMEOUT']
    
    def is_expired(self):
        """Check if command has exceeded timeout"""
        if self.sent_at and self.status in ['SENT', 'ACKNOWLEDGED']:
            return (timezone.now() - self.sent_at).total_seconds() > self.timeout_seconds
        return False


class AutomationSchedule(models.Model):
    """Enhanced model for automation schedules"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='automation_schedules')
    automation_type = models.CharField(max_length=5, choices=AUTOMATION_TYPES)
    action = models.CharField(
        max_length=20, 
        choices=AUTOMATION_ACTIONS,
        help_text="Specific action to perform when this schedule executes"
    )
    is_active = models.BooleanField(default=True)
    
    # Time settings
    time = models.TimeField()
    
    # Days of week (stored as comma-separated string of day numbers, e.g., "0,1,3")
    days = models.CharField(max_length=13)
    
    # Automation-specific settings
    feed_amount = models.FloatField(
        null=True, 
        blank=True,
        help_text="Feed amount in grams"
    )
    drain_water_level = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Water level to drain to"
    )
    target_water_level = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Target water level percentage to refill to"
    )
    
    # Priority and execution settings
    priority = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Priority level (1=highest, 5=lowest)"
    )
    
    # Schedule metadata
    last_execution = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)
    execution_count = models.IntegerField(default=0)
    
    # User settings
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='automation_schedules_v2'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['priority', 'time']
        indexes = [
            models.Index(fields=['pond', 'automation_type']),
            models.Index(fields=['is_active', 'next_execution']),
            models.Index(fields=['priority', 'next_execution']),
        ]
    
    def __str__(self):
        return f"{self.get_automation_type_display()} - {self.pond.name}"
    
    def clean(self):
        """Validate schedule settings"""
        super().clean()
        
        # Validate time field
        if self.time:
            # Ensure time is a valid time object
            if not isinstance(self.time, time):
                raise ValidationError('Time must be a valid time object')
        
        # Validate action based on automation type
        if self.automation_type == 'FEED':
            if self.action not in ['FEED']:
                raise ValidationError('FEED automation type can only use FEED action')
            if not self.feed_amount:
                raise ValidationError('Feed amount is required for feeding automation')
        
        elif self.automation_type == 'WATER':
            if self.action not in ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 'WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                raise ValidationError('WATER automation type can only use water-related actions')
            
            # Action-specific parameter validation
            if self.action == 'WATER_DRAIN':
                if not self.drain_water_level:
                    raise ValidationError('drain_water_level is required for WATER_DRAIN action')
                if not (0 <= self.drain_water_level <= 100):
                    raise ValidationError('drain_water_level must be between 0 and 100')
            
            elif self.action == 'WATER_FILL':
                if not self.target_water_level:
                    raise ValidationError('target_water_level is required for WATER_FILL action')
                if not (0 <= self.target_water_level <= 100):
                    raise ValidationError('target_water_level must be between 0 and 100')
            
            elif self.action == 'WATER_FLUSH':
                if not self.drain_water_level:
                    raise ValidationError('drain_water_level is required for WATER_FLUSH action')
                if not self.target_water_level:
                    raise ValidationError('target_water_level is required for WATER_FLUSH action')
                if not (0 <= self.drain_water_level <= 100):
                    raise ValidationError('drain_water_level must be between 0 and 100')
                if not (0 <= self.target_water_level <= 100):
                    raise ValidationError('target_water_level must be between 0 and 100')
            
            elif self.action in ['WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                # Valve control actions don't require additional parameters
                pass
            
            else:
                # Fallback validation for any other water actions
                if not self.drain_water_level and not self.target_water_level:
                    raise ValidationError('Either drain water level or target water level must be specified for water automation')
    
    def get_next_execution(self):
        """Calculate next execution time based on schedule"""
        # This is a simplified implementation
        # In production, this would use a proper scheduling library
        now = timezone.now()
        current_time = now.time()
        
        if current_time < self.time:
            # Today
            next_exec = timezone.make_aware(
                timezone.datetime.combine(now.date(), self.time)
            )
        else:
            # Tomorrow
            tomorrow = now.date() + timezone.timedelta(days=1)
            next_exec = timezone.make_aware(
                timezone.datetime.combine(tomorrow, self.time)
            )
        
        return next_exec
    
    def update_next_execution(self):
        """Update the next execution time"""
        self.next_execution = self.get_next_execution()
        self.save()
    
    def record_execution(self):
        """Record that this schedule was executed"""
        self.last_execution = timezone.now()
        self.execution_count += 1
        self.update_next_execution()
        self.save()


