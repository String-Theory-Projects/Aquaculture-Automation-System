from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator


class Pond(models.Model):
    """Model representing a smart fish pond"""
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ponds')
    device_id = models.CharField(max_length=100, unique=True)  # ESP32 unique identifier
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.owner.username}"


class WiFiConfig(models.Model):
    """Model for storing and managing ESP32 WiFi configuration"""
    pond = models.OneToOneField(Pond, on_delete=models.CASCADE, related_name='wifi_config')
    ssid = models.CharField(max_length=32, help_text="WiFi network name")
    password = models.CharField(max_length=64, help_text="WiFi password")
    is_connected = models.BooleanField(default=False)
    last_connected = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    is_config_synced = models.BooleanField(default=False, help_text="Whether config has been synced to device")
    
    # # Advanced WiFi settings (optional)
    # static_ip = models.GenericIPAddressField(null=True, blank=True, protocol='IPv4')
    # subnet_mask = models.GenericIPAddressField(null=True, blank=True, protocol='IPv4')
    # gateway = models.GenericIPAddressField(null=True, blank=True, protocol='IPv4')
    # dns = models.GenericIPAddressField(null=True, blank=True, protocol='IPv4')
    
    def __str__(self):
        return f"WiFi Config for {self.pond.name} - {self.ssid}"
    
    class Meta:
        verbose_name = "WiFi Configuration"
        verbose_name_plural = "WiFi Configurations"


class SensorData(models.Model):
    """Model for storing sensor readings from the pond"""
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='sensor_readings')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Sensor readings
    temperature = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    water_level = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )  # Percentage
    turbidity = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )  # NTU
    dissolved_oxygen = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )  # mg/L
    ph = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(14)]
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['pond', '-timestamp']),
        ]


class PondControl(models.Model):
    """Model for controlling pond devices (valves, feeders)"""
    pond = models.OneToOneField(Pond, on_delete=models.CASCADE, related_name='controls')
    water_valve_state = models.BooleanField(default=False)
    last_feed_time = models.DateTimeField(null=True, blank=True)
    last_feed_amount = models.FloatField(null=True, blank=True)  # in grams
    
    def __str__(self):
        return f"Controls for {self.pond.name}"


class AutomationSchedule(models.Model):
    """Model for automation schedules"""
    AUTOMATION_TYPES = [
        ('FEED', 'Feeding'),
        ('WATER', 'Water Change'),
    ]
    
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='automation_schedules')
    automation_type = models.CharField(max_length=5, choices=AUTOMATION_TYPES)
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
        help_text="Water level to drain to (currently hardcoded to 0%)"
    )
    target_water_level = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Target water level percentage to refill to"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['time']
        indexes = [
            models.Index(fields=['pond', 'automation_type']),
        ]
    
    def __str__(self):
        return f"{self.get_automation_type_display()} - {self.pond.name}"


class DeviceLog(models.Model):
    """Model for logging device actions and errors"""
    LOG_TYPES = [
        ('INFO', 'Information'),
        ('ERROR', 'Error'),
        ('ACTION', 'Action'),
        ('WIFI', 'WiFi'),
    ]
    
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    log_type = models.CharField(max_length=6, choices=LOG_TYPES)
    message = models.TextField()
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['pond', '-timestamp', 'log_type']),
        ]
    
    def __str__(self):
        return f"{self.log_type} - {self.pond.name} - {self.timestamp}"