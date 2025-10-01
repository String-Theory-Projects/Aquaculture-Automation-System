import qrcode
from io import BytesIO
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
import os
from PIL import Image
from .forms import QRCodeGenerationForm
from .models import QRCodeGeneration


@staff_member_required
def qr_generator_view(request):
    """
    QR Generator view - accessible only by admin users
    """
    if request.method == 'POST':
        form = QRCodeGenerationForm(request.POST)
        if form.is_valid():
            # Save the form data
            qr_instance = form.save()
            
            try:
                # Generate QR code
                qr_code = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr_code.add_data(qr_instance.device_id)
                qr_code.make(fit=True)
                
                # Create QR code image
                qr_img = qr_code.make_image(fill_color="black", back_color="white")
                
                # Save QR code to model
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                
                # Save the QR code image with URL-safe filename
                safe_device_id = qr_instance.device_id.replace(':', '-')
                qr_filename = f"qr_{safe_device_id}_{qr_instance.id}.png"
                qr_path = os.path.join(settings.MEDIA_ROOT, 'qr_generator', 'qr_codes', qr_filename)
                os.makedirs(os.path.dirname(qr_path), exist_ok=True)
                
                with open(qr_path, 'wb') as f:
                    f.write(qr_buffer.getvalue())
                
                # Update the model with QR code path
                qr_instance.qr_code_image.name = f'qr_generator/qr_codes/{qr_filename}'
                qr_instance.save()
                
                messages.success(request, f'QR code generated successfully for Device ID: {qr_instance.device_id}')
                return redirect('qr_generator:qr_result', qr_id=qr_instance.id)
                
            except Exception as e:
                messages.error(request, f'Error generating QR code: {str(e)}')
                qr_instance.delete()  # Clean up the instance if QR generation fails
    else:
        form = QRCodeGenerationForm()
    
    return render(request, 'qr_generator/qr_generator.html', {'form': form})


@staff_member_required
def qr_result_view(request, qr_id):
    """
    Display the generated QR code with download option
    """
    try:
        qr_instance = QRCodeGeneration.objects.get(id=qr_id)
        return render(request, 'qr_generator/qr_result.html', {'qr_instance': qr_instance})
    except QRCodeGeneration.DoesNotExist:
        messages.error(request, 'QR code not found.')
        return redirect('qr_generator:qr_generator')


@staff_member_required
def qr_download_view(request, qr_id):
    """
    Download the generated QR code
    """
    try:
        qr_instance = QRCodeGeneration.objects.get(id=qr_id)
        if qr_instance.qr_code_image:
            qr_path = os.path.join(settings.MEDIA_ROOT, qr_instance.qr_code_image.name)
            if os.path.exists(qr_path):
                with open(qr_path, 'rb') as f:
                    response = HttpResponse(f.read(), content_type='image/png')
                    safe_device_id = qr_instance.device_id.replace(':', '-')
                    response['Content-Disposition'] = f'attachment; filename="qr_{safe_device_id}.png"'
                    return response
        
        messages.error(request, 'QR code file not found.')
        return redirect('qr_generator:qr_result', qr_id=qr_id)
    except QRCodeGeneration.DoesNotExist:
        messages.error(request, 'QR code not found.')
        return redirect('qr_generator:qr_generator')
