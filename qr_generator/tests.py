from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import QRCodeGeneration
import tempfile
import os


class QRGeneratorTestCase(TestCase):
    def setUp(self):
        # Create a superuser for testing
        self.user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client = Client()
        
        # Create a test image
        self.test_image = SimpleUploadedFile(
            "test_image.jpg",
            b"fake image content",
            content_type="image/jpeg"
        )
    
    def test_qr_generator_requires_admin(self):
        """Test that QR generator requires admin authentication"""
        response = self.client.get(reverse('qr_generator:qr_generator'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_qr_generator_admin_access(self):
        """Test that admin users can access QR generator"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('qr_generator:qr_generator'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'QR Code Generator')
    
    def test_qr_generation_form_valid(self):
        """Test QR generation with valid data"""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'device_id': 'TEST1234567890123',
            'notes': 'Test QR code for device'
        }
        
        response = self.client.post(reverse('qr_generator:qr_generator'), data)
        
        # Should redirect to result page
        self.assertEqual(response.status_code, 302)
        
        # Check that QRCodeGeneration instance was created
        qr_instance = QRCodeGeneration.objects.filter(device_id='TEST1234567890123').first()
        self.assertTrue(qr_instance)
        self.assertEqual(qr_instance.notes, 'Test QR code for device')
    
    def test_qr_generation_form_invalid_device_id(self):
        """Test QR generation with invalid device ID"""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'device_id': 'TOOLONGDEVICEID123456789',  # Too long
            'notes': 'Test notes'
        }
        
        response = self.client.post(reverse('qr_generator:qr_generator'), data)
        
        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        # Check that form is not valid (should not redirect)
        self.assertNotEqual(response.status_code, 302)
    
    def test_qr_generation_form_empty_device_id(self):
        """Test QR generation with empty device ID"""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'device_id': '',
            'notes': 'Test notes'
        }
        
        response = self.client.post(reverse('qr_generator:qr_generator'), data)
        
        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required')
    
    def test_qr_generation_form_notes_too_long(self):
        """Test QR generation with notes that are too long"""
        self.client.login(username='admin', password='testpass123')
        
        data = {
            'device_id': 'TEST1234567890123',
            'notes': 'A' * 501  # Too long
        }
        
        response = self.client.post(reverse('qr_generator:qr_generator'), data)
        
        # Should stay on form page with errors
        self.assertEqual(response.status_code, 200)
        # Check that form is not valid (should not redirect)
        self.assertNotEqual(response.status_code, 302)
    
    def test_qr_result_view(self):
        """Test QR result view"""
        self.client.login(username='admin', password='testpass123')
        
        # Create a QR instance
        qr_instance = QRCodeGeneration.objects.create(
            device_id='TEST1234567890123',
            notes='Test QR code with notes'
        )
        
        response = self.client.get(reverse('qr_generator:qr_result', args=[qr_instance.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, qr_instance.device_id)
        self.assertContains(response, qr_instance.notes)
    
    def test_qr_download_view(self):
        """Test QR download view"""
        self.client.login(username='admin', password='testpass123')
        
        # Create a QR instance
        qr_instance = QRCodeGeneration.objects.create(
            device_id='TEST1234567890123',
            notes='Test QR code for download'
        )
        
        response = self.client.get(reverse('qr_generator:qr_download', args=[qr_instance.id]))
        # Should return 200 or redirect depending on QR code generation
        self.assertIn(response.status_code, [200, 302])
