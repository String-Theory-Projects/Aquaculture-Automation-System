from django import forms
from django.core.validators import MaxLengthValidator
from .models import QRCodeGeneration


class QRCodeGenerationForm(forms.ModelForm):
    """
    Form for QR code generation with Device ID and optional Notes
    """
    device_id = forms.CharField(
        max_length=17,
        validators=[MaxLengthValidator(17)],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Device ID (max 17 characters)',
            'maxlength': '17'
        }),
        help_text="Enter the Device ID (maximum 17 characters)"
    )
    
    notes = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Enter optional notes about this QR code (max 500 characters)',
            'rows': 3,
            'maxlength': '500'
        }),
        help_text="Optional notes about this QR code (maximum 500 characters)"
    )
    
    class Meta:
        model = QRCodeGeneration
        fields = ['device_id', 'notes']
    
    def clean_device_id(self):
        device_id = self.cleaned_data.get('device_id')
        if device_id:
            device_id = device_id.strip()
            if len(device_id) == 0:
                raise forms.ValidationError("Device ID cannot be empty.")
            if len(device_id) > 17:
                raise forms.ValidationError("Device ID cannot exceed 17 characters.")
        return device_id
    
    def clean_notes(self):
        notes = self.cleaned_data.get('notes')
        if notes:
            notes = notes.strip()
            if len(notes) > 500:
                raise forms.ValidationError("Notes cannot exceed 500 characters.")
        return notes
