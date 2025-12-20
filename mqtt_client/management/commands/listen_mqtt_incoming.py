#!/usr/bin/env python3
"""
Django management command to listen for incoming MQTT messages from Redis.

This command runs a Redis pub/sub listener on the mqtt_incoming channel
and processes incoming messages using the consumers module.
"""

import json
import logging
import time
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from mqtt_client.bridge import get_redis_client, MQTT_INCOMING_CHANNEL, get_redis_status
from mqtt_client.consumers import process_mqtt_message

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Listen for incoming MQTT messages from Redis and process them'
    
    def __init__(self):
        super().__init__()
        self.health_server = None
        self.health_server_thread = None
        self.last_heartbeat_time = None
        self.last_message_time = None
        self.pubsub = None
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run in daemon mode (continuous listening)',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=1,
            help='Timeout for Redis pubsub listen (default: 1 second)',
        )
    
    def handle(self, *args, **options):
        """Handle the command"""
        self.stdout.write(
            self.style.SUCCESS('Starting MQTT incoming message listener...')
        )
        
        try:
            # Get Redis client
            redis_client = get_redis_client()
            pubsub = redis_client.pubsub()
            pubsub.subscribe(MQTT_INCOMING_CHANNEL)
            self.pubsub = pubsub  # Store reference for health checks
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Listening on Redis channel: {MQTT_INCOMING_CHANNEL}')
            )
            
            # Start health server
            self._start_health_server()
            
            if options['daemon']:
                self._run_daemon_mode(pubsub, options['timeout'])
            else:
                self._run_single_listen(pubsub, options['timeout'])
                
        except Exception as e:
            logger.error(f'Failed to start MQTT incoming listener: {e}')
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to start listener: {e}')
            )
            raise
    
    def _run_daemon_mode(self, pubsub, timeout):
        """Run in continuous listening mode"""
        self.stdout.write(
            self.style.SUCCESS('🔄 Running in daemon mode (continuous listening)')
        )
        
        # Write initial heartbeat immediately
        self._write_heartbeat()
        logger.info('Initial MQTT listener heartbeat written')
        
        # Track last heartbeat time for time-based writes
        last_heartbeat_time = time.time()
        
        try:
            message_count = 0
            while True:
                try:
                    # Get message with timeout
                    message = pubsub.get_message(timeout=timeout)
                    
                    if message and message['type'] == 'message':
                        message_count += 1
                        self.last_message_time = timezone.now()
                        self.stdout.write(
                            f'📥 Received message #{message_count}'
                        )
                        
                        # Process the message
                        try:
                            data = json.loads(message['data'].decode('utf-8'))
                            success = process_mqtt_message(data)
                            
                            if success:
                                self.stdout.write(
                                    self.style.SUCCESS(f'✅ Message #{message_count} processed successfully')
                                )
                            else:
                                self.stdout.write(
                                    self.style.WARNING(f'⚠️ Message #{message_count} processing failed')
                                )
                                
                        except json.JSONDecodeError as e:
                            logger.error(f'Invalid JSON in message #{message_count}: {e}')
                            self.stdout.write(
                                self.style.ERROR(f'❌ Invalid JSON in message #{message_count}')
                            )
                        except Exception as e:
                            logger.error(f'Error processing message #{message_count}: {e}')
                            self.stdout.write(
                                self.style.ERROR(f'❌ Error processing message #{message_count}: {e}')
                            )
                    
                    # Write heartbeat every 30 seconds (based on actual wall time, not loop iterations)
                    current_time = time.time()
                    if current_time - last_heartbeat_time >= 30:
                        self._write_heartbeat()
                        last_heartbeat_time = current_time
                        logger.debug('MQTT listener heartbeat written')
                    
                    # Show status every 10 messages
                    if message_count > 0 and message_count % 10 == 0:
                        self.stdout.write(
                            f'📊 Processed {message_count} messages so far...'
                        )
                        
                except KeyboardInterrupt:
                    self.stdout.write('\n🛑 Received interrupt signal, shutting down...')
                    break
                except Exception as e:
                    logger.error(f'Error in daemon mode: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'❌ Error in daemon mode: {e}')
                    )
                    time.sleep(5)  # Wait before retrying
                    
        finally:
            # Cleanup
            if self.health_server:
                try:
                    self.health_server.shutdown()
                except Exception as e:
                    logger.warning(f'Error shutting down health server: {e}')
            
            if self.health_server_thread and self.health_server_thread.is_alive():
                self.health_server_thread.join(timeout=2)
            
            pubsub.close()
            self.stdout.write(
                self.style.SUCCESS(f'✅ Listener stopped. Total messages processed: {message_count}')
            )
    
    def _run_single_listen(self, pubsub, timeout):
        """Run single listen operation"""
        self.stdout.write(
            self.style.SUCCESS('🔍 Running single listen operation')
        )
        
        try:
            # Wait for a message
            message = pubsub.get_message(timeout=timeout)
            
            if message and message['type'] == 'message':
                self.stdout.write('📥 Received message')
                
                try:
                    data = json.loads(message['data'].decode('utf-8'))
                    self.stdout.write(f'📋 Message data: {data}')
                    
                    # Process the message
                    success = process_mqtt_message(data)
                    
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS('✅ Message processed successfully')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING('⚠️ Message processing failed')
                        )
                        
                except json.JSONDecodeError as e:
                    logger.error(f'Invalid JSON in message: {e}')
                    self.stdout.write(
                        self.style.ERROR('❌ Invalid JSON in message')
                    )
                except Exception as e:
                    logger.error(f'Error processing message: {e}')
                    self.stdout.write(
                        self.style.ERROR(f'❌ Error processing message: {e}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⏰ No message received within {timeout} second timeout')
                )
                
        finally:
            pubsub.close()
            self.stdout.write('✅ Single listen operation completed')
    
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
                        # Critical: redis_subscriber_count=0
                        checks = status.get('checks', {})
                        critical_failure = checks.get('redis_subscriber_count', 0) == 0
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
        """Check MQTT listener health status with timeout protection"""
        from core.health_utils import check_health_with_timeout
        
        checks = {
            'redis_connected': False,
            'redis_subscriber_count': 0,
            'last_heartbeat': None,
            'last_message_time': None
        }
        
        # Check Redis with timeout protection
        def check_redis():
            redis_status = get_redis_status()
            return {
                'redis_connected': redis_status.get('status') == 'connected',
                'redis_subscriber_count': redis_status.get('incoming_subscribers', 0)
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
        
        # Check last message time (fast, no timeout needed)
        if self.last_message_time:
            checks['last_message_time'] = self.last_message_time.isoformat()
        
        # Determine overall health: critical check is redis_subscriber_count
        healthy = (
            checks['redis_connected'] and
            checks['redis_subscriber_count'] > 0
        )
        
        return {
            'healthy': healthy,
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        }
    
    def _write_heartbeat(self):
        """Write heartbeat to Redis with retry logic"""
        from core.health_utils import write_heartbeat_with_retry
        
        def write_func():
            redis_client = get_redis_client()
            
            heartbeat_data = {
                'timestamp': timezone.now().isoformat(),
                'redis_subscriber_count': 0,
                'last_message_time': self.last_message_time.isoformat() if self.last_message_time else None
            }
            
            # Get subscriber count (non-blocking, don't fail if this errors)
            try:
                redis_status = get_redis_status()
                heartbeat_data['redis_subscriber_count'] = redis_status.get('incoming_subscribers', 0)
            except Exception:
                pass
            
            # Write to Redis with TTL (90 seconds)
            redis_client.setex(
                'health:mqtt_listener',
                90,  # TTL in seconds
                json.dumps(heartbeat_data)
            )
            
            self.last_heartbeat_time = timezone.now()
        
        # Use retry logic - don't crash if it fails
        write_heartbeat_with_retry(write_func, service_name='mqtt_listener')

