#!/usr/bin/env python3
"""
Django management command to listen for incoming MQTT messages from Redis.

This command runs a Redis pub/sub listener on the mqtt_incoming channel
and processes incoming messages using the consumers module.
"""

import json
import logging
import time
from django.core.management.base import BaseCommand
from django.conf import settings

from mqtt_client.bridge import get_redis_client, MQTT_INCOMING_CHANNEL
from mqtt_client.consumers import process_mqtt_message

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Listen for incoming MQTT messages from Redis and process them'
    
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
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Listening on Redis channel: {MQTT_INCOMING_CHANNEL}')
            )
            
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
        
        try:
            message_count = 0
            while True:
                try:
                    # Get message with timeout
                    message = pubsub.get_message(timeout=timeout)
                    
                    if message and message['type'] == 'message':
                        message_count += 1
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

