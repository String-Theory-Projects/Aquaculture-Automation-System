from django.db import models
from django.contrib.auth.models import User


class APIVersion(models.Model):
    """Model for tracking API versions and compatibility"""
    version = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    is_deprecated = models.BooleanField(default=False)
    deprecation_date = models.DateField(null=True, blank=True)
    sunset_date = models.DateField(null=True, blank=True)
    changelog = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-version']
        indexes = [
            models.Index(fields=['is_active', 'is_deprecated']),
        ]
    
    def __str__(self):
        return f"API Version {self.version}"


class APIEndpoint(models.Model):
    """Model for tracking API endpoints and their usage"""
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    version = models.ForeignKey(APIVersion, on_delete=models.CASCADE, related_name='endpoints')
    is_active = models.BooleanField(default=True)
    rate_limit = models.CharField(max_length=50, default='100/hour')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('path', 'method', 'version')
        indexes = [
            models.Index(fields=['path', 'method']),
            models.Index(fields=['version', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.path} (v{self.version.version})"


class APIUsage(models.Model):
    """Model for tracking API usage and analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_usage', null=True, blank=True)
    endpoint = models.ForeignKey(APIEndpoint, on_delete=models.CASCADE, related_name='usage')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    response_time = models.FloatField(null=True, blank=True)
    status_code = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['endpoint', 'created_at']),
            models.Index(fields=['status_code', 'created_at']),
        ]
    
    def __str__(self):
        return f"API usage by {self.user.username if self.user else 'anonymous'} at {self.created_at}"
