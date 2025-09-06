from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from core.choices import (
    PARAMETER_CHOICES, AUTOMATION_ACTIONS, ALERT_LEVELS, 
    ALERT_STATUS, LOG_TYPES, COMMAND_TYPES, COMMAND_STATUS
)
from core.constants import SENSOR_RANGES
import uuid
from django.utils import timezone


class PondPair(models.Model):
    """Model representing a pair of ponds"""
    name = models.CharField(
        max_length=30,
        help_text="Name for this pond pair (unique per user)"
    )
    device_id = models.CharField(
        max_length=settings.DEVICE_ID_MIN_LENGTH,  # MAC address format: XX:XX:XX:XX:XX:XX
        validators=[MinLengthValidator(settings.DEVICE_ID_MIN_LENGTH)],
        unique=True,
        help_text="MAC address of the ESP32 device in format XX:XX:XX:XX:XX:XX"
    )  # ESP32 unique identifier for the pair
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pond_pairs')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('owner', 'name')
    
    def __str__(self):
        return f"{self.name} ({self.device_id}) - {self.owner.username}"
    
    @property
    def pond_count(self):
        """Get the number of ponds in this pair"""
        return self.ponds.count()
    
    @property
    def is_complete(self):
        """Check if the pair has exactly 2 ponds"""
        return self.pond_count == 2
    
    @property
    def has_minimum_ponds(self):
        """Check if the pair has at least one pond"""
        return self.pond_count >= 1
    
    def clean(self):
        """Validate that a PondPair has at most 2 ponds"""
        # Check for existing instances
        if self.pk:
            pond_count = self.ponds.count()
            if pond_count > 2:
                raise ValidationError(f'A PondPair can have at most 2 ponds. This pair has {pond_count} ponds.')
        # For new instances, we can't validate pond count yet since ponds aren't created
        # The validation will happen when ponds are added to the pair
    
    def save(self, *args, **kwargs):
        """Override save to validate pond count"""
        if self.pk:  # Only validate existing instances
            self.clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to ensure we don't leave orphaned PondPairs"""
        # Check if this would leave any ponds without a parent
        ponds = self.ponds.all()
        if ponds.exists():
            # Delete all ponds first (using force_delete to bypass validation)
            for pond in ponds:
                pond.delete(force_delete=True)
        super().delete(*args, **kwargs)
    
    def validate_pond_count(self):
        """Validate pond count after ponds have been added/removed"""
        pond_count = self.ponds.count()
        if pond_count < 1:
            raise ValidationError(f'A PondPair must have at least 1 pond. This pair has {pond_count} ponds.')
        if pond_count > 2:
            raise ValidationError(f'A PondPair can have at most 2 ponds. This pair has {pond_count} ponds.')
    
    def get_pond_by_position(self, position: int):
        """Get pond by position (1 or 2) within the pair"""
        if position not in [1, 2]:
            raise ValueError("Position must be 1 or 2")
        
        # Get ponds ordered by ID for consistent positioning
        ponds = list(self.ponds.order_by('id'))
        
        if position <= len(ponds):
            return ponds[position - 1]  # Convert to 0-based index
        return None
    
    def get_pond_positions(self):
        """Get a mapping of pond positions to pond objects"""
        ponds = list(self.ponds.order_by('id'))
        positions = {}
        
        for i, pond in enumerate(ponds, 1):
            positions[i] = pond
        
        return positions


class Pond(models.Model):
    """Model representing a smart fish pond"""
    name = models.CharField(max_length=15)
    parent_pair = models.ForeignKey(PondPair, on_delete=models.CASCADE, related_name='ponds')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('parent_pair', 'name')
        ordering = ['id']  # Ensure consistent ordering for position calculation
    
    def __str__(self):
        return f"{self.name} - {self.parent_pair.owner.username}"
    
    @property
    def position(self):
        """Get the position of this pond within the pond pair (1 or 2)"""
        # Get all ponds in this pair, ordered by ID for consistency
        ponds_in_pair = self.parent_pair.ponds.order_by('id')
        try:
            # Find the index of this pond (0-based) and add 1 for 1-based position
            return list(ponds_in_pair).index(self) + 1
        except ValueError:
            # Fallback if pond not found in the list
            return 1
    
    def get_position(self):
        """Alternative method to get pond position"""
        return self.position
    
    @property
    def owner(self):
        """Get the owner from the parent pair"""
        return self.parent_pair.owner
    
    def clean(self):
        """Validate that the parent pair doesn't exceed 2 ponds and won't be left empty"""
        if self.parent_pair:
            existing_ponds = self.parent_pair.ponds.exclude(pk=self.pk)
            if existing_ponds.count() >= 2:
                raise ValidationError('This PondPair already has 2 ponds. A PondPair can have at most 2 ponds.')
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Override delete to prevent removing the last pond from a PondPair"""
        force_delete = kwargs.pop('force_delete', False)
        if not force_delete and self.parent_pair and self.parent_pair.pond_count <= 1:
            raise ValidationError('Cannot delete the last pond from a PondPair. A PondPair must have at least one pond.')
        super().delete(*args, **kwargs)


class SensorData(models.Model):
    """Enhanced model for storing sensor readings from the pond"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='sensor_readings')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Core sensor readings
    temperature = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    water_level = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )  # Percentage
    feed_level = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Percentage of feed remaining"
    )  # Percentage
    water_level2 = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True,
        help_text="Second water level sensor reading in percentage"
    )
    feed_level2 = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True,
        help_text="Second feed level sensor reading in percentage"
    )
    dissolved_oxygen = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )  # mg/L
    ph = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(14)]
    )
    battery = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True,
        help_text="Battery level percentage"
    )
    
    # Device metadata
    device_timestamp = models.DateTimeField(
        null=True, blank=True,
        help_text="Timestamp from the device when reading was taken"
    )
    signal_strength = models.IntegerField(
        null=True, blank=True,
        help_text="WiFi signal strength in dBm"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['pond', '-timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['device_timestamp']),
        ]
    
    def clean(self):
        """Validate sensor values against defined ranges"""
        super().clean()
        
        # Validate temperature
        if self.temperature is not None:
            temp_range = SENSOR_RANGES['temperature']
            if not (temp_range['min'] <= self.temperature <= temp_range['max']):
                raise ValidationError(f'Temperature must be between {temp_range["min"]} and {temp_range["max"]}°C')
        
        # Validate water level
        if self.water_level is not None:
            water_range = SENSOR_RANGES['water_level']
            if not (water_range['min'] <= self.water_level <= water_range['max']):
                raise ValidationError(f'Water level must be between {water_range["min"]} and {water_range["max"]}%')
        
        # Validate feed level
        if self.feed_level is not None:
            feed_range = SENSOR_RANGES['feed_level']
            if not (feed_range['min'] <= self.feed_level <= feed_range['max']):
                raise ValidationError(f'Feed level must be between {feed_range["min"]} and {feed_range["max"]}%')
        
        # Validate water_level2
        if self.water_level2 is not None:
            water_range = SENSOR_RANGES['water_level']
            if not (water_range['min'] <= self.water_level2 <= water_range['max']):
                raise ValidationError(f'Water level 2 must be between {water_range["min"]} and {water_range["max"]}%')
        
        # Validate feed_level2
        if self.feed_level2 is not None:
            feed_range = SENSOR_RANGES['feed_level']
            if not (feed_range['min'] <= self.feed_level2 <= feed_range['max']):
                raise ValidationError(f'Feed level 2 must be between {feed_range["min"]} and {feed_range["max"]}%')
        
        # Validate dissolved oxygen
        if self.dissolved_oxygen is not None:
            do_range = SENSOR_RANGES['dissolved_oxygen']
            if not (do_range['min'] <= self.dissolved_oxygen <= do_range['max']):
                raise ValidationError(f'Dissolved oxygen must be between {do_range["min"]} and {do_range["max"]} mg/L')
        
        # Validate pH
        if self.ph is not None:
            ph_range = SENSOR_RANGES['ph']
            if not (ph_range['min'] <= self.ph <= ph_range['max']):
                raise ValidationError(f'pH must be between {ph_range["min"]} and {ph_range["max"]}')
        
        
        # Validate battery
        if self.battery is not None:
            battery_range = SENSOR_RANGES['battery']
            if not (battery_range['min'] <= self.battery <= battery_range['max']):
                raise ValidationError(f'Battery must be between {battery_range["min"]} and {battery_range["max"]}%')


class SensorThreshold(models.Model):
    """Model for managing sensor thresholds and automation triggers"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='thresholds')
    parameter = models.CharField(max_length=20, choices=PARAMETER_CHOICES)
    
    # Threshold values
    upper_threshold = models.FloatField(
        help_text="Upper threshold value for this parameter"
    )
    lower_threshold = models.FloatField(
        help_text="Lower threshold value for this parameter"
    )
    
    # Automation settings
    automation_action = models.CharField(
        max_length=20, 
        choices=AUTOMATION_ACTIONS,
        help_text="Action to take when threshold is violated"
    )
    
    # Threshold configuration
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(
        default=1,
        help_text="Priority level (1=highest, 5=lowest)"
    )
    
    # Notification settings
    send_alert = models.BooleanField(default=True)
    alert_level = models.CharField(
        max_length=20,
        choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High'), ('CRITICAL', 'Critical')],
        default='MEDIUM'
    )
    
    # Timing settings
    violation_timeout = models.IntegerField(
        default=30,
        help_text="Seconds to wait before triggering action after threshold violation"
    )
    max_violations = models.IntegerField(
        default=3,
        help_text="Maximum violations before triggering action"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('pond', 'parameter')
        ordering = ['priority', 'parameter']
        indexes = [
            models.Index(fields=['pond', 'parameter']),
            models.Index(fields=['is_active', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.parameter} threshold for {self.pond.name}"
    
    def clean(self):
        """Validate threshold values"""
        super().clean()
        
        if self.upper_threshold <= self.lower_threshold:
            raise ValidationError('Upper threshold must be greater than lower threshold')
        
        # Validate against sensor ranges
        if self.parameter in SENSOR_RANGES:
            param_range = SENSOR_RANGES[self.parameter]
            if self.upper_threshold > param_range['max']:
                raise ValidationError(f'Upper threshold cannot exceed maximum value of {param_range["max"]}')
            if self.lower_threshold < param_range['min']:
                raise ValidationError(f'Lower threshold cannot be below minimum value of {param_range["min"]}')


class Alert(models.Model):
    """Model for managing system alerts and notifications"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='alerts')
    parameter = models.CharField(max_length=20, choices=PARAMETER_CHOICES)
    alert_level = models.CharField(max_length=20, choices=ALERT_LEVELS)
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='active')
    
    # Alert details
    message = models.TextField()
    threshold_value = models.FloatField()
    current_value = models.FloatField()
    
    # Threshold violation details
    violation_count = models.IntegerField(default=1)
    first_violation_at = models.DateTimeField(auto_now_add=True)
    last_violation_at = models.DateTimeField(auto_now=True)
    
    # Resolution tracking
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pond', 'status']),
            models.Index(fields=['alert_level', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.alert_level} alert for {self.parameter} on {self.pond.name}"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save()
    
    def resolve(self, user):
        """Mark alert as resolved"""
        self.status = 'resolved'
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.save()
    
    def is_active(self):
        """Check if alert is currently active"""
        return self.status == 'active'
    
    def is_acknowledged(self):
        """Check if alert has been acknowledged"""
        return self.status == 'acknowledged'
    
    def is_resolved(self):
        """Check if alert has been resolved"""
        return self.status == 'resolved'


class DeviceLog(models.Model):
    """Model for comprehensive device and system logging"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='device_logs')
    log_type = models.CharField(max_length=20, choices=LOG_TYPES)
    message = models.TextField()
    success = models.BooleanField(default=True)
    
    # Command details (for command logs)
    command_type = models.CharField(
        max_length=20, 
        choices=COMMAND_TYPES,
        null=True, 
        blank=True
    )
    command_id = models.UUIDField(
        null=True, 
        blank=True,
        help_text="Unique identifier for the command"
    )
    
    # Error details (for error logs)
    error_code = models.CharField(max_length=50, null=True, blank=True)
    error_details = models.TextField(null=True, blank=True)
    
    # Device metadata
    device_timestamp = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp from the device"
    )
    firmware_version = models.CharField(
        max_length=20, 
        null=True, 
        blank=True
    )
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # User tracking
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='device_logs'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pond', 'log_type']),
            models.Index(fields=['log_type', 'success']),
            models.Index(fields=['created_at']),
            models.Index(fields=['command_id']),
        ]
    
    def __str__(self):
        return f"{self.log_type} log for {self.pond.name} at {self.created_at}"


class PondControl(models.Model):
    """Model for controlling pond devices (valves, feeders)"""
    pond = models.OneToOneField(Pond, on_delete=models.CASCADE, related_name='controls')
    water_valve_state = models.BooleanField(default=False)
    last_feed_time = models.DateTimeField(null=True, blank=True)
    last_feed_amount = models.FloatField(null=True, blank=True)  # in grams
    
    def __str__(self):
        return f"Controls for {self.pond.name}"
