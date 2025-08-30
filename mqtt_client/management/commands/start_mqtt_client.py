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
import json
import threading
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection

from mqtt_client.client import initialize_mqtt_client, shutdown_mqtt_client, MQTTConfig
from mqtt_client.bridge import get_redis_client, MQTT_OUTGOING_CHANNEL

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start the MQTT client for device communication'
    
    def __init__(self):
        super().__init__()
        self.redis_pubsub = None
        self.redis_thread = None
        self.should_stop = False
    
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
            
            # Start Redis bridge for outgoing commands
            self._start_redis_bridge(client)
            
            self.stdout.write(
                self.style.SUCCESS('MQTT client started successfully with Redis bridge')
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
                
                # Get Redis channel status
                try:
                    from mqtt_client.bridge import get_redis_status
                    redis_status = get_redis_status()
                    outgoing_subscribers = redis_status.get('outgoing_subscribers', 0)
                    incoming_subscribers = redis_status.get('incoming_subscribers', 0)
                except:
                    outgoing_subscribers = 0
                    incoming_subscribers = 0
                
                # Show comprehensive status
                self.stdout.write(
                    f'📊 Status Update:'
                )
                self.stdout.write(
                    f'  🔌 MQTT: Connected to {client.config.broker_host}:{client.config.broker_port}'
                )
                self.stdout.write(
                    f'  📡 Devices: {online_devices} online, {pending_commands} pending commands'
                )
                self.stdout.write(
                    f'  🔄 Redis: {outgoing_subscribers} outgoing, {incoming_subscribers} incoming subscribers'
                )
                self.stdout.write('')  # Empty line for readability
                
                time.sleep(10)  # Update every 10 seconds for less spam
                
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
    
    def _start_redis_bridge(self, client):
        """Start Redis bridge for handling outgoing commands"""
        try:
            redis_client = get_redis_client()
            self.redis_pubsub = redis_client.pubsub()
            self.redis_pubsub.subscribe(MQTT_OUTGOING_CHANNEL)
            
            # Start Redis listener thread
            self.redis_thread = threading.Thread(target=self._redis_listener, args=(client,), daemon=True)
            self.redis_thread.start()
            
            self.stdout.write(
                self.style.SUCCESS('Redis bridge started successfully')
            )
            
        except Exception as e:
            logger.error(f'Failed to start Redis bridge: {e}')
            self.stdout.write(
                self.style.ERROR(f'Failed to start Redis bridge: {e}')
            )
    
    def _redis_listener(self, client):
        """Listen for outgoing commands from Redis and publish to MQTT"""
        try:
            for message in self.redis_pubsub.listen():
                if self.should_stop:
                    break
                    
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'].decode('utf-8'))
                        self._handle_outgoing_command(client, data)
                    except json.JSONDecodeError as e:
                        logger.error(f'Invalid JSON in Redis message: {e}')
                    except Exception as e:
                        logger.error(f'Error handling outgoing command: {e}')
                        
        except Exception as e:
            logger.error(f'Redis listener error: {e}')
    
    def _handle_outgoing_command(self, client, data):
        """Handle outgoing command from Redis and publish to MQTT"""
        try:
            command_id = data.get('command_id')
            device_id = data.get('device_id')
            topic = data.get('topic')
            payload = data.get('payload', {})
            qos = data.get('qos', 2)
            
            if not all([command_id, device_id, topic, payload]):
                logger.error(f'Missing required fields in outgoing command: {data}')
                return
            
            # Publish to MQTT broker
            if client.is_connected:
                result, mid = client.client.publish(topic, json.dumps(payload), qos=qos)
                
                if result == 0:  # MQTT_ERR_SUCCESS
                    logger.info(f'Command {command_id} published to MQTT topic {topic}')
                    
                    # Update command status in database
                    self._update_command_status(command_id, 'SENT')
                else:
                    logger.error(f'Failed to publish command {command_id}: {result}')
                    self._update_command_status(command_id, 'FAILED', f'MQTT error: {result}')
            else:
                logger.error(f'MQTT client not connected, cannot publish command {command_id}')
                self._update_command_status(command_id, 'FAILED', 'MQTT client not connected')
                
        except Exception as e:
            logger.error(f'Error handling outgoing command: {e}')
    
    def _update_command_status(self, command_id, status, message=''):
        """Update command status in database"""
        try:
            from automation.models import DeviceCommand
            
            command = DeviceCommand.objects.get(command_id=command_id)
            if status == 'SENT':
                command.send_command()
            elif status == 'FAILED':
                command.complete_command(False, message)
                
        except DeviceCommand.DoesNotExist:
            logger.warning(f'Command {command_id} not found for status update')
        except Exception as e:
            logger.error(f'Error updating command status: {e}')
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            self.should_stop = True
            
            # Stop Redis bridge
            if self.redis_pubsub:
                self.redis_pubsub.close()
            if self.redis_thread and self.redis_thread.is_alive():
                self.redis_thread.join(timeout=5)
            
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

