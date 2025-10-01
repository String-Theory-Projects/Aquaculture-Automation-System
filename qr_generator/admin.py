from django.contrib import admin
from .models import QRCodeGeneration


@admin.register(QRCodeGeneration)
class QRCodeGenerationAdmin(admin.ModelAdmin):
    list_display = ['device_id', 'notes', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['device_id', 'notes']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    fields = ['device_id', 'notes', 'qr_code_image', 'created_at', 'updated_at']
