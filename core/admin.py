from django.contrib import admin
from .models import SystemConfiguration, AuditLog, NotificationTemplate


@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'is_encrypted', 'created_at', 'updated_at')
    list_filter = ('is_encrypted',)
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('key',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'model_name', 'object_id', 'timestamp', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('action', 'user__username', 'model_name', 'message')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'notification_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('notification_type', 'is_active')
    search_fields = ('name', 'subject', 'body')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('name',)
