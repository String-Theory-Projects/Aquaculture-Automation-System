from django.contrib import admin
from .models import DeviceStatus, MQTTMessage


@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ['pond_pair', 'status', 'last_seen', 'firmware_version', 'ip_address', 'is_online']
    list_filter = ['status', 'firmware_version', 'pond_pair']
    search_fields = ['pond_pair__name', 'pond_pair__device_id', 'device_name']
    readonly_fields = ['created_at', 'updated_at', 'is_online']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond_pair', 'status', 'device_name')
        }),
        ('Connection Status', {
            'fields': ('last_seen', 'connection_uptime', 'is_online')
        }),
        ('Device Information', {
            'fields': ('firmware_version', 'hardware_version')
        }),
        ('Network Information', {
            'fields': ('ip_address', 'wifi_ssid', 'wifi_signal_strength')
        }),
        ('System Health', {
            'fields': ('free_heap', 'cpu_frequency'),
            'classes': ('collapse',)
        }),
        ('Error Tracking', {
            'fields': ('error_count', 'last_error', 'last_error_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MQTTMessage)
class MQTTMessageAdmin(admin.ModelAdmin):
    list_display = ['pond_pair', 'topic', 'message_type', 'success', 'payload_size', 'created_at']
    list_filter = ['message_type', 'success', 'pond_pair', 'created_at']
    search_fields = ['pond_pair__name', 'topic', 'message_id', 'correlation_id']
    readonly_fields = ['message_id', 'correlation_id', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond_pair', 'topic', 'message_type', 'message_id', 'correlation_id')
        }),
        ('Message Content', {
            'fields': ('payload', 'payload_size')
        }),
        ('Message Status', {
            'fields': ('success', 'error_message')
        }),
        ('Timing', {
            'fields': ('sent_at', 'received_at', 'processing_time')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
