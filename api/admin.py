from django.contrib import admin
from .models import APIVersion, APIEndpoint, APIUsage


@admin.register(APIVersion)
class APIVersionAdmin(admin.ModelAdmin):
    list_display = ('version', 'is_active', 'is_deprecated', 'deprecation_date', 'sunset_date')
    list_filter = ('is_active', 'is_deprecated', 'created_at')
    search_fields = ('version', 'changelog')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-version',)
    date_hierarchy = 'created_at'


@admin.register(APIEndpoint)
class APIEndpointAdmin(admin.ModelAdmin):
    list_display = ('path', 'method', 'version', 'is_active', 'rate_limit')
    list_filter = ('method', 'version', 'is_active', 'created_at')
    search_fields = ('path', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('version', 'path', 'method')
    date_hierarchy = 'created_at'


@admin.register(APIUsage)
class APIUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'endpoint', 'ip_address', 'status_code', 'response_time', 'created_at')
    list_filter = ('status_code', 'endpoint__method', 'created_at')
    search_fields = ('user__username', 'endpoint__path', 'ip_address')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
