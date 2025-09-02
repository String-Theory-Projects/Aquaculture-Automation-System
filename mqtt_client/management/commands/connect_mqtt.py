"""
Django management command to connect the existing global MQTT client.

Usage:
    python manage.py connect_mqtt

This command connects the global MQTT client instance that Django uses.
"""

import logging
from django.core.management.base import BaseCommand
from mqtt_client.client import get_mqtt_client

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Connect the existing global MQTT client instance'
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            self.stdout.write(
                self.style.SUCCESS('Connecting global MQTT client...')
            )
            
            # Get the global MQTT client instance
            client = get_mqtt_client()
            
            # Connect it
            if client.connect():
                self.stdout.write(
                    self.style.SUCCESS('Global MQTT client connected successfully!')
                )
                logger.info("Global MQTT client connected successfully")
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to connect global MQTT client')
                )
                logger.error("Failed to connect global MQTT client")
                
        except Exception as e:
            logger.error(f'Error connecting MQTT client: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
