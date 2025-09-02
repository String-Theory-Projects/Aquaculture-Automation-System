from django.contrib import admin
from .models import UserProfile, UserNotification


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'company_name', 'is_active')
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number', 'company_name')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('user__username',)
    date_hierarchy = 'created_at'


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'is_enabled', 'created_at', 'updated_at')
    list_filter = ('notification_type', 'is_enabled', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('user__username', 'notification_type')
