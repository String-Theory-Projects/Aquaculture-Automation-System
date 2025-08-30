from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from core.choices import DEVICE_STATUS, LOG_TYPES
from core.constants import MQTT_TOPICS
from ponds.models import PondPair
import uuid
from django.utils import timezone


class DeviceStatus(models.Model):
    """Model for tracking device connection status and health"""
    pond_pair = models.OneToOneField(PondPair, on_delete=models.CASCADE, related_name='device_status')
    
    # Connection status
    status = models.CharField(max_length=20, choices=DEVICE_STATUS, default='OFFLINE')
    last_seen = models.DateTimeField(null=True, blank=True)
    connection_uptime = models.DurationField(null=True, blank=True)
    
    # Device information
    firmware_version = models.CharField(max_length=20, null=True, blank=True)
    hardware_version = models.CharField(max_length=20, null=True, blank=True)
    device_name = models.CharField(max_length=50, null=True, blank=True)
    
    # Network information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    wifi_ssid = models.CharField(max_length=50, null=True, blank=True)
    wifi_signal_strength = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(-100), MaxValueValidator(0)],
        help_text="WiFi signal strength in dBm"
    )
    
    # System health
    free_heap = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Free heap memory in bytes"
    )
    cpu_frequency = models.IntegerField(
        null=True, 
        blank=True,
        help_text="CPU frequency in MHz"
    )
    
    # Error tracking
    error_count = models.IntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'last_seen']),
            models.Index(fields=['firmware_version']),
        ]
    
    def __str__(self):
        return f"Device status for {self.pond_pair.name} - {self.status}"
    
    def update_heartbeat(self):
        """Update device heartbeat"""
        now = timezone.now()
        if self.last_seen:
            self.connection_uptime = now - self.last_seen
        self.last_seen = now
        self.status = 'ONLINE'
        self.save()
    
    def mark_offline(self):
        """Mark device as offline"""
        self.status = 'OFFLINE'
        self.save()
    
    def record_error(self, error_message):
        """Record a device error"""
        self.error_count += 1
        self.last_error = error_message
        self.last_error_at = timezone.now()
        self.status = 'ERROR'
        self.save()
    
    def is_online(self):
        """Check if device is currently online"""
        if not self.last_seen:
            return False
        
        # Consider device offline if no heartbeat for more than 30 seconds
        offline_threshold = timezone.now() - timezone.timedelta(seconds=30)
        return self.last_seen > offline_threshold
    
    def get_uptime_percentage(self, hours=24):
        """Calculate device uptime percentage for the last N hours"""
        if not self.last_seen:
            return 0.0
        
        now = timezone.now()
        start_time = now - timezone.timedelta(hours=hours)
        
        # This is a simplified calculation
        # In production, you'd want to track actual connection/disconnection events
        if self.last_seen < start_time:
            return 0.0
        
        # Assume device was online for the time since last seen
        online_duration = min(self.last_seen - start_time, timezone.timedelta(hours=hours))
        total_duration = timezone.timedelta(hours=hours)
        
        return (online_duration.total_seconds() / total_duration.total_seconds()) * 100


class MQTTMessage(models.Model):
    """Model for logging MQTT messages for debugging and monitoring"""
    pond_pair = models.ForeignKey(PondPair, on_delete=models.CASCADE, related_name='mqtt_messages')
    
    # Message details
    topic = models.CharField(max_length=200)
    message_type = models.CharField(
        max_length=20,
        choices=[
            ('PUBLISH', 'Publish'),
            ('SUBSCRIBE', 'Subscribe'),
            ('ACKNOWLEDGE', 'Acknowledge'),
            ('ERROR', 'Error'),
        ]
    )
    
    # Message content
    payload = models.JSONField(default=dict, blank=True)
    payload_size = models.IntegerField(
        help_text="Size of payload in bytes"
    )
    
    # Message status
    success = models.BooleanField(default=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Timing
    sent_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    processing_time = models.DurationField(null=True, blank=True)
    
    # Message ID for tracking
    message_id = models.UUIDField(default=uuid.uuid4, unique=True)
    correlation_id = models.UUIDField(
        null=True, 
        blank=True,
        help_text="ID to correlate related messages"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['pond_pair', 'topic']),
            models.Index(fields=['message_type', 'success']),
            models.Index(fields=['created_at']),
            models.Index(fields=['message_id']),
            models.Index(fields=['correlation_id']),
        ]
    
    def __str__(self):
        return f"{self.message_type} message on {self.topic} - {self.created_at}"
    
    def record_sent(self):
        """Record when message was sent"""
        self.sent_at = timezone.now()
        self.save()
    
    def record_received(self):
        """Record when message was received"""
        self.received_at = timezone.now()
        if self.sent_at:
            self.processing_time = self.received_at - self.sent_at
        self.save()
    
    def record_error(self, error_message):
        """Record message error"""
        self.success = False
        self.error_message = error_message
        self.save()
    
    def is_processed(self):
        """Check if message has been processed"""
        return self.received_at is not None
    
    def get_processing_time_ms(self):
        """Get processing time in milliseconds"""
        if self.processing_time:
            return self.processing_time.total_seconds() * 1000
        return None
