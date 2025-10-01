from django.db import models
from django.core.validators import MaxLengthValidator


class QRCodeGeneration(models.Model):
    """
    Model to store QR code generation requests and results
    """
    device_id = models.CharField(
        max_length=17,
        validators=[MaxLengthValidator(17)],
        help_text="Device ID (maximum 17 characters)"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        max_length=500,
        help_text="Optional notes about this QR code (maximum 500 characters)"
    )
    qr_code_image = models.ImageField(
        upload_to='qr_generator/qr_codes/',
        blank=True,
        null=True,
        help_text="Generated QR code image"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "QR Code Generation"
        verbose_name_plural = "QR Code Generations"
    
    def __str__(self):
        return f"QR Code for Device: {self.device_id}"
