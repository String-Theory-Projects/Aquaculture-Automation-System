"""
Django management command to generate lifelong JWT tokens for camera devices.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import AccessToken
from datetime import timedelta
from ponds.models import PondPair
from mqtt_client.models import MQTTMessage
from django.utils import timezone


class Command(BaseCommand):
    help = 'Generate lifelong JWT tokens for camera devices'

    def handle(self, *args, **options):
        # Get admin user
        admin_user = User.objects.get(username='admin')
        
        # Find camera devices from recent MQTT messages
        recent_cutoff = timezone.now() - timedelta(days=7)
        recent_messages = MQTTMessage.objects.filter(
            topic__contains='heartbeat',
            created_at__gte=recent_cutoff
        ) | MQTTMessage.objects.filter(
            topic__contains='startup',
            created_at__gte=recent_cutoff
        )
        
        camera_device_ids = set()
        for message in recent_messages:
            payload = message.payload
            if isinstance(payload, dict) and payload.get('device_type') == 'camera':
                camera_device_ids.add(message.pond_pair.device_id)
        
        if not camera_device_ids:
            # Fallback: all active devices
            devices = PondPair.objects.filter(is_active=True)
            self.stdout.write('⚠ No camera devices found in recent messages. Generating for all devices:\n')
        else:
            devices = PondPair.objects.filter(device_id__in=camera_device_ids, is_active=True)
            self.stdout.write(f'✓ Found {devices.count()} camera device(s):\n')
        
        # Generate and display tokens
        for device in devices:
            token = AccessToken.for_user(admin_user)
            token.set_exp(from_time=timezone.now(), lifetime=timedelta(days=36500))
            
            self.stdout.write(f'\nDevice: {device.device_id} ({device.name})')
            self.stdout.write(f'Token: {str(token)}\n')
            self.stdout.write('-' * 80)
