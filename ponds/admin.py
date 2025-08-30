from django.contrib import admin
from .models import (
    PondPair, Pond, SensorData, SensorThreshold, Alert, 
    DeviceLog, PondControl
)


@admin.register(PondPair)
class PondPairAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_id', 'owner', 'pond_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'device_id', 'owner__username']
    readonly_fields = ['pond_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'device_id', 'owner')
        }),
        ('Status', {
            'fields': ('pond_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Pond)
class PondAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent_pair', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'parent_pair']
    search_fields = ['name', 'parent_pair__name', 'parent_pair__owner__username']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'parent_pair', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ['pond', 'timestamp', 'temperature', 'water_level', 'feed_level', 'ph']
    list_filter = ['timestamp', 'pond', 'pond__parent_pair']
    search_fields = ['pond__name', 'pond__parent_pair__name']
    readonly_fields = ['timestamp', 'device_timestamp']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond', 'timestamp', 'device_timestamp')
        }),
        ('Core Sensors', {
            'fields': ('temperature', 'water_level', 'feed_level', 'turbidity', 'dissolved_oxygen', 'ph')
        }),
        ('Extended Sensors', {
            'fields': ('ammonia', 'battery'),
            'classes': ('collapse',)
        }),
        ('Device Metadata', {
            'fields': ('signal_strength',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SensorThreshold)
class SensorThresholdAdmin(admin.ModelAdmin):
    list_display = ['pond', 'parameter', 'upper_threshold', 'lower_threshold', 'automation_action', 'is_active', 'priority']
    list_filter = ['is_active', 'parameter', 'automation_action', 'priority', 'pond__parent_pair']
    search_fields = ['pond__name', 'pond__parent_pair__name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond', 'parameter', 'is_active')
        }),
        ('Threshold Values', {
            'fields': ('upper_threshold', 'lower_threshold')
        }),
        ('Automation Settings', {
            'fields': ('automation_action', 'priority', 'send_alert', 'alert_level')
        }),
        ('Timing Settings', {
            'fields': ('violation_timeout', 'max_violations'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['pond', 'parameter', 'alert_level', 'status', 'current_value', 'threshold_value', 'created_at']
    list_filter = ['status', 'alert_level', 'parameter', 'created_at', 'pond__parent_pair']
    search_fields = ['pond__name', 'pond__parent_pair__name', 'message']
    readonly_fields = ['created_at', 'first_violation_at', 'last_violation_at']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('pond', 'parameter', 'alert_level', 'status', 'message')
        }),
        ('Values', {
            'fields': ('threshold_value', 'current_value', 'violation_count')
        }),
        ('Timing', {
            'fields': ('first_violation_at', 'last_violation_at', 'acknowledged_at', 'resolved_at'),
            'classes': ('collapse',)
        }),
        ('User Actions', {
            'fields': ('acknowledged_by', 'resolved_by'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ['pond', 'log_type', 'success', 'command_type', 'user', 'created_at']
    list_filter = ['log_type', 'success', 'command_type', 'created_at', 'pond__parent_pair']
    search_fields = ['pond__name', 'pond__parent_pair__name', 'message']
    readonly_fields = ['created_at', 'command_id']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond', 'log_type', 'message', 'success')
        }),
        ('Command Details', {
            'fields': ('command_type', 'command_id', 'error_code', 'error_details'),
            'classes': ('collapse',)
        }),
        ('Device Metadata', {
            'fields': ('device_timestamp', 'firmware_version', 'metadata'),
            'classes': ('collapse',)
        }),
        ('User Information', {
            'fields': ('user',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(PondControl)
class PondControlAdmin(admin.ModelAdmin):
    list_display = ['pond', 'water_valve_state', 'last_feed_time', 'last_feed_amount']
    list_filter = ['water_valve_state', 'last_feed_time']
    search_fields = ['pond__name', 'pond__parent_pair__name']
