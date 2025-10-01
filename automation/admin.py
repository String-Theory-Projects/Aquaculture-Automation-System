from django.contrib import admin
from .models import AutomationExecution, DeviceCommand, AutomationSchedule


@admin.register(AutomationExecution)
class AutomationExecutionAdmin(admin.ModelAdmin):
    list_display = ['pond', 'execution_type', 'action', 'priority', 'status', 'scheduled_at', 'created_at']
    list_filter = ['status', 'execution_type', 'action', 'priority', 'success', 'pond__parent_pair']
    search_fields = ['pond__name', 'pond__parent_pair__name', 'result_message']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond', 'execution_type', 'action', 'priority', 'status')
        }),
        ('Execution Details', {
            'fields': ('scheduled_at', 'started_at', 'completed_at', 'parameters')
        }),
        ('Results', {
            'fields': ('success', 'result_message', 'error_details')
        }),
        ('Related Objects', {
            'fields': ('schedule', 'threshold', 'user'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DeviceCommand)
class DeviceCommandAdmin(admin.ModelAdmin):
    list_display = ['pond', 'command_type', 'status', 'command_id', 'retry_count', 'created_at']
    list_filter = ['status', 'command_type', 'success', 'pond__parent_pair', 'created_at']
    search_fields = ['pond__name', 'pond__parent_pair__name', 'command_id', 'result_message']
    readonly_fields = ['command_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond', 'command_type', 'status', 'command_id')
        }),
        ('Execution Tracking', {
            'fields': ('sent_at', 'acknowledged_at', 'completed_at', 'parameters')
        }),
        ('Retry Settings', {
            'fields': ('timeout_seconds', 'max_retries', 'retry_count')
        }),
        ('Results', {
            'fields': ('success', 'result_message', 'error_code', 'error_details')
        }),
        ('Related Objects', {
            'fields': ('automation_execution', 'user'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AutomationSchedule)
class AutomationScheduleAdmin(admin.ModelAdmin):
    list_display = ['pond', 'automation_type', 'action', 'time', 'days', 'is_active', 'priority', 'next_execution']
    list_filter = ['automation_type', 'action', 'is_active', 'priority', 'pond__parent_pair']
    search_fields = ['pond__name', 'pond__parent_pair__name', 'user__username']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('pond', 'automation_type', 'action', 'is_active', 'priority', 'user')
        }),
        ('Schedule Settings', {
            'fields': ('time', 'days')
        }),
        ('Automation Parameters', {
            'fields': ('feed_amount', 'drain_water_level', 'target_water_level')
        }),
        ('Execution Tracking', {
            'fields': ('last_execution', 'next_execution', 'execution_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


