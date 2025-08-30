"""
Django management command to start the MQTT client.

Usage:
    python manage.py start_mqtt_client [--config-file CONFIG_FILE] [--daemon]

This command initializes and starts the MQTT client for device communication.
"""

import time
import signal
import sys
import logging
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection

from mqtt_client.client import initialize_mqtt_client, shutdown_mqtt_client, MQTTConfig

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start the MQTT client for device communication'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config-file',
            type=str,
            help='Path to MQTT configuration file'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run in daemon mode (background)'
        )
        parser.add_argument(
            '--broker-host',
            type=str,
            help='MQTT broker host'
        )
        parser.add_argument(
            '--broker-port',
            type=int,
            help='MQTT broker port'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='MQTT username'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='MQTT password'
        )
        parser.add_argument(
            '--use-tls',
            action='store_true',
            help='Use TLS encryption'
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        try:
            self.stdout.write(
                self.style.SUCCESS('Starting MQTT client...')
            )
            
            # Load configuration
            config = self._load_config(options)
            
            # Initialize MQTT client
            client = initialize_mqtt_client(config)
            if not client:
                raise CommandError('Failed to initialize MQTT client')
            
            self.stdout.write(
                self.style.SUCCESS('MQTT client started successfully')
            )
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Main loop
            if options['daemon']:
                self._run_daemon_mode(client)
            else:
                self._run_interactive_mode(client)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nReceived interrupt signal')
            )
        except Exception as e:
            logger.error(f'Error in MQTT client command: {e}')
            raise CommandError(f'MQTT client error: {e}')
        finally:
            self._cleanup()
    
    def _load_config(self, options):
        """Load MQTT configuration from various sources"""
        config = MQTTConfig()
        
        # Override with command line arguments
        if options['broker_host']:
            config.broker_host = options['broker_host']
        if options['broker_port']:
            config.broker_port = options['broker_port']
        if options['username']:
            config.username = options['username']
        if options['password']:
            config.password = options['password']
        if options['use_tls']:
            config.use_tls = True
        
        # Override with settings if available
        if hasattr(settings, 'MQTT_BROKER_HOST'):
            config.broker_host = settings.MQTT_BROKER_HOST
        if hasattr(settings, 'MQTT_BROKER_PORT'):
            config.broker_port = settings.MQTT_BROKER_PORT
        if hasattr(settings, 'MQTT_USERNAME'):
            config.username = settings.MQTT_USERNAME
        if hasattr(settings, 'MQTT_PASSWORD'):
            config.password = settings.MQTT_PASSWORD
        if hasattr(settings, 'MQTT_USE_TLS'):
            config.use_tls = settings.MQTT_USE_TLS
        
        return config
    
    def _run_interactive_mode(self, client):
        """Run in interactive mode with status updates"""
        self.stdout.write(
            self.style.SUCCESS('MQTT client running in interactive mode')
        )
        self.stdout.write('Press Ctrl+C to stop')
        
        try:
            while True:
                # Check connection status
                if client.is_connected:
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Connected to {client.config.broker_host}:{client.config.broker_port}')
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Disconnected from {client.config.broker_host}:{client.config.broker_port}')
                    )
                
                # Show device status
                online_devices = len(client.device_heartbeats)
                pending_commands = len(client.pending_commands)
                
                self.stdout.write(
                    f'Online devices: {online_devices}, Pending commands: {pending_commands}'
                )
                
                time.sleep(5)  # Update every 5 seconds
                
        except KeyboardInterrupt:
            pass
    
    def _run_daemon_mode(self, client):
        """Run in daemon mode (background)"""
        self.stdout.write(
            self.style.SUCCESS('MQTT client running in daemon mode')
        )
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stdout.write(
            self.style.WARNING(f'\nReceived signal {signum}, shutting down...')
        )
        sys.exit(0)
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            self.stdout.write('Shutting down MQTT client...')
            shutdown_mqtt_client()
            
            # Close database connections
            connection.close()
            
            self.stdout.write(
                self.style.SUCCESS('MQTT client shutdown complete')
            )
            
        except Exception as e:
            logger.error(f'Error during cleanup: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error during cleanup: {e}')
            )

