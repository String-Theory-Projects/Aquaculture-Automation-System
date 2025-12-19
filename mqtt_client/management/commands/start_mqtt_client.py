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
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db import connection
from django.utils import timezone
from redis.exceptions import TimeoutError as RedisTimeoutError, ConnectionError as RedisConnectionError, RedisError

from mqtt_client.client import initialize_mqtt_client, shutdown_mqtt_client, MQTTConfig
from mqtt_client.bridge import get_redis_client, MQTT_OUTGOING_CHANNEL, get_redis_status

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start the MQTT client for device communication'
    
    def __init__(self):
        super().__init__()
        self.redis_pubsub = None
        self.redis_thread = None
        self.should_stop = False
        self.redis_client = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 60  # Max 60 seconds
        self.mqtt_client = None  # Store MQTT client reference for health checks
        self.health_server = None
        self.health_server_thread = None
        self.last_heartbeat_time = None
    
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
            
            self.mqtt_client = client  # Store reference for health checks
            
            # Start Redis bridge for outgoing commands
            self._start_redis_bridge(client)
            
            # Start health server
            self._start_health_server()
            
            self.stdout.write(
                self.style.SUCCESS('MQTT client started successfully with Redis bridge and health server')
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
                
                # Write heartbeat to Redis
                self._write_heartbeat(client)
                
                time.sleep(10)  # Update every 10 seconds for less spam
                
        except KeyboardInterrupt:
            pass
    
    def _run_daemon_mode(self, client):
        """Run in daemon mode (background)"""
        self.stdout.write(
            self.style.SUCCESS('MQTT client running in daemon mode')
        )
        
        heartbeat_counter = 0
        try:
            while True:
                time.sleep(1)
                heartbeat_counter += 1
                
                # Write heartbeat every 30 seconds
                if heartbeat_counter >= 30:
                    self._write_heartbeat(client)
                    heartbeat_counter = 0
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
            self.redis_client = get_redis_client()
            self._create_pubsub_connection()
            
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
    
    def _create_pubsub_connection(self):
        """Create and subscribe to Redis pubsub channel"""
        try:
            if self.redis_pubsub:
                try:
                    self.redis_pubsub.close()
                except:
                    pass
            
            # Get fresh Redis client to ensure connection is valid
            self.redis_client = get_redis_client()
            self.redis_pubsub = self.redis_client.pubsub()
            self.redis_pubsub.subscribe(MQTT_OUTGOING_CHANNEL)
            
            logger.info(f'Successfully subscribed to Redis channel: {MQTT_OUTGOING_CHANNEL}')
            
        except Exception as e:
            logger.error(f'Failed to create pubsub connection: {e}')
            raise
    
    def _redis_listener(self, client):
        """Listen for outgoing commands from Redis and publish to MQTT with automatic reconnection"""
        logger.info('Redis listener thread started')
        
        while not self.should_stop:
            try:
                # Use get_message with timeout instead of listen() for better error handling
                # This allows us to check should_stop periodically and handle timeouts gracefully
                message = self.redis_pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'].decode('utf-8'))
                        self._handle_outgoing_command(client, data)
                        # Reset reconnect attempts on successful message processing
                        self.reconnect_attempts = 0
                    except json.JSONDecodeError as e:
                        logger.error(f'Invalid JSON in Redis message: {e}')
                    except Exception as e:
                        logger.error(f'Error handling outgoing command: {e}')
                
                # Check for subscription confirmation messages
                if message and message['type'] == 'subscribe':
                    logger.info(f'Successfully subscribed to channel: {message.get("channel", "unknown")}')
                    self.reconnect_attempts = 0
                        
            except (RedisTimeoutError, RedisConnectionError, RedisError) as e:
                # Redis connection/timeout errors - attempt reconnection
                logger.warning(f'Redis connection error in listener: {e}')
                self._reconnect_redis_bridge(client)
                
            except Exception as e:
                # Other unexpected errors - log and attempt reconnection
                logger.error(f'Unexpected error in Redis listener: {e}', exc_info=True)
                self._reconnect_redis_bridge(client)
        
        logger.info('Redis listener thread stopped')
    
    def _reconnect_redis_bridge(self, client):
        """Reconnect to Redis with exponential backoff"""
        if self.should_stop:
            return
        
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f'Max reconnection attempts ({self.max_reconnect_attempts}) reached. Stopping Redis listener.')
            return
        
        self.reconnect_attempts += 1
        
        # Calculate exponential backoff delay
        delay = min(
            self.base_reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay
        )
        
        logger.warning(
            f'Attempting to reconnect Redis bridge (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}) '
            f'after {delay} seconds...'
        )
        
        time.sleep(delay)
        
        try:
            # Recreate pubsub connection
            self._create_pubsub_connection()
            logger.info(f'Successfully reconnected to Redis after {self.reconnect_attempts} attempt(s)')
            self.reconnect_attempts = 0  # Reset on successful reconnection
            
        except Exception as e:
            logger.error(f'Failed to reconnect Redis bridge: {e}')
            # Will retry on next iteration of the listener loop
    
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
                    
                    # Add small delay to avoid race condition with database
                    import time
                    time.sleep(0.1)
                    
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
        """Update command status in database with retry logic"""
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                from automation.models import DeviceCommand
                
                command = DeviceCommand.objects.get(command_id=command_id)
                if status == 'SENT':
                    command.send_command()
                    
                    # Publish status update for SSE
                    from mqtt_client.bridge import publish_command_status_update, publish_unified_command_status_update
                    publish_command_status_update(
                        command_id=str(command.command_id),
                        status='SENT',
                        message=message or 'Command sent to device',
                        command_type=command.command_type,
                        pond_id=command.pond.id,
                        pond_name=command.pond.name
                    )
                    
                    # Also publish to unified dashboard stream
                    publish_unified_command_status_update(
                        device_id=command.pond.parent_pair.device_id,
                        command_id=str(command.command_id),
                        status='SENT',
                        message=message or 'Command sent to device',
                        command_type=command.command_type,
                        pond_name=command.pond.name
                    )
                elif status == 'FAILED':
                    command.complete_command(False, message)
                    
                    # Publish status update for SSE
                    from mqtt_client.bridge import publish_command_status_update, publish_unified_command_status_update
                    publish_command_status_update(
                        command_id=str(command.command_id),
                        status='FAILED',
                        message=message or 'Command failed to send',
                        command_type=command.command_type,
                        pond_id=command.pond.id,
                        pond_name=command.pond.name
                    )
                    
                    # Also publish to unified dashboard stream
                    publish_unified_command_status_update(
                        device_id=command.pond.parent_pair.device_id,
                        command_id=str(command.command_id),
                        status='FAILED',
                        message=message or 'Command failed to send',
                        command_type=command.command_type,
                        pond_name=command.pond.name
                    )
                
                # Success - break out of retry loop
                break
                
            except DeviceCommand.DoesNotExist:
                if attempt < max_retries - 1:
                    logger.warning(f'Command {command_id} not found for status update (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...')
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.warning(f'Command {command_id} not found for status update after {max_retries} attempts')
            except Exception as e:
                logger.error(f'Error updating command status: {e}')
                break
    
    def _start_health_server(self):
        """Start HTTP health server in background thread"""
        try:
            # Get port from environment (Railway sets PORT for all services)
            # Use PORT if available, otherwise use default 8080
            health_port = int(os.environ.get('PORT', 8080))
            
            # Create health server handler with closure to access command instance
            command_instance = self
            
            class HealthHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/health/':
                        status = command_instance._check_health()
                        # Determine status code: 500 for critical failures, 503 for degraded
                        # Critical: mqtt_connected=False or redis_subscriber_count=0
                        checks = status.get('checks', {})
                        critical_failure = (
                            not checks.get('mqtt_connected', False) or
                            checks.get('redis_subscriber_count', 0) == 0
                        )
                        http_status = 200 if status['healthy'] else (500 if critical_failure else 503)
                        
                        self.send_response(http_status)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(status).encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    # Suppress default HTTP server logging
                    pass
            
            self.health_server = HTTPServer(('0.0.0.0', health_port), HealthHandler)
            
            # Start server in background thread
            self.health_server_thread = threading.Thread(
                target=self.health_server.serve_forever,
                daemon=True
            )
            self.health_server_thread.start()
            
            logger.info(f'Health server started on port {health_port}')
            self.stdout.write(
                self.style.SUCCESS(f'Health server started on port {health_port}')
            )
            
        except Exception as e:
            logger.error(f'Failed to start health server: {e}')
            self.stdout.write(
                self.style.WARNING(f'Failed to start health server: {e}')
            )
    
    def _check_health(self):
        """Check MQTT client health status"""
        checks = {
            'mqtt_connected': False,
            'redis_connected': False,
            'redis_subscriber_count': 0,
            'last_heartbeat': None
        }
        
        # Check MQTT connection
        if self.mqtt_client:
            checks['mqtt_connected'] = self.mqtt_client.is_connected
        
        # Check Redis with timeout protection
        from core.health_utils import check_health_with_timeout
        
        def check_redis():
            redis_status = get_redis_status()
            return {
                'redis_connected': redis_status.get('status') == 'connected',
                'redis_subscriber_count': redis_status.get('outgoing_subscribers', 0)
            }
        
        redis_result = check_health_with_timeout(
            check_redis,
            timeout_seconds=2.0,
            default_status='unknown'
        )
        
        if redis_result.get('status') != 'unknown' and not redis_result.get('timeout'):
            checks['redis_connected'] = redis_result.get('redis_connected', False)
            checks['redis_subscriber_count'] = redis_result.get('redis_subscriber_count', 0)
        else:
            checks['redis_error'] = redis_result.get('error', 'Redis check failed')
            if redis_result.get('timeout'):
                checks['redis_timeout'] = True
        
        # Check last heartbeat (fast, no timeout needed)
        if self.last_heartbeat_time:
            checks['last_heartbeat'] = self.last_heartbeat_time.isoformat()
        
        # Determine overall health: critical checks are mqtt_connected and redis_subscriber_count
        healthy = (
            checks['mqtt_connected'] and
            checks['redis_connected'] and
            checks['redis_subscriber_count'] > 0
        )
        
        return {
            'healthy': healthy,
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        }
    
    def _write_heartbeat(self, client):
        """Write heartbeat to Redis with retry logic"""
        from core.health_utils import write_heartbeat_with_retry
        
        def write_func():
            redis_client = get_redis_client()
            
            heartbeat_data = {
                'timestamp': timezone.now().isoformat(),
                'mqtt_connected': client.is_connected if client else False,
                'redis_subscriber_count': 0,
                'last_command_time': None
            }
            
            # Get subscriber count (non-blocking, don't fail if this errors)
            try:
                redis_status = get_redis_status()
                heartbeat_data['redis_subscriber_count'] = redis_status.get('outgoing_subscribers', 0)
            except Exception:
                pass
            
            # Write to Redis with TTL (90 seconds)
            redis_client.setex(
                'health:mqtt_client',
                90,  # TTL in seconds
                json.dumps(heartbeat_data)
            )
            
            self.last_heartbeat_time = timezone.now()
        
        # Use retry logic - don't crash if it fails
        write_heartbeat_with_retry(write_func, service_name='mqtt_client')
    
    def _cleanup(self):
        """Clean up resources"""
        try:
            self.should_stop = True
            
            # Stop health server
            if self.health_server:
                try:
                    self.health_server.shutdown()
                except Exception as e:
                    logger.warning(f'Error shutting down health server: {e}')
            
            if self.health_server_thread and self.health_server_thread.is_alive():
                self.health_server_thread.join(timeout=2)
            
            # Stop Redis bridge
            if self.redis_pubsub:
                try:
                    self.redis_pubsub.close()
                except Exception as e:
                    logger.warning(f'Error closing Redis pubsub: {e}')
            
            if self.redis_thread and self.redis_thread.is_alive():
                self.redis_thread.join(timeout=5)
                if self.redis_thread.is_alive():
                    logger.warning('Redis listener thread did not stop within timeout')
            
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

