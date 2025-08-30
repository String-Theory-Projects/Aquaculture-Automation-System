from django.apps import AppConfig
import threading
import logging

logger = logging.getLogger(__name__)


class MqttClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mqtt_client'
    verbose_name = 'MQTT Client'
    
    def ready(self):
        """Initialize MQTT client app when Django starts"""
        try:
            # Import signals to register them (if any)
            import mqtt_client.signals  # noqa
            
            # DISABLED: Old Django MQTT client - now using Redis bridge instead
            # self._start_django_mqtt_client()
            
        except ImportError:
            pass
    
    def _start_django_mqtt_client(self):
        """Start MQTT client in Django process for incoming message processing"""
        try:
            # Only start in main process (not in autoreload)
            import os
            if os.environ.get('RUN_MAIN') != 'true':
                return
            
            # Start MQTT client in background thread
            def start_mqtt_client():
                try:
                    from .client import get_mqtt_client
                    from django.conf import settings
                    
                    logger.info("Starting Django MQTT client for incoming messages...")
                    
                    # Get MQTT client instance
                    client = get_mqtt_client()
                    
                    # Connect to broker
                    if client.connect():
                        logger.info("Django MQTT client connected successfully for incoming messages")
                        
                        # Keep connection alive
                        import time
                        while True:
                            if not client.is_connected:
                                logger.warning("Django MQTT client disconnected, reconnecting...")
                                if not client.connect():
                                    logger.error("Failed to reconnect Django MQTT client")
                                    time.sleep(30)  # Wait before retry
                                    continue
                            
                            time.sleep(10)  # Check connection every 10 seconds
                    else:
                        logger.error("Failed to connect Django MQTT client")
                        
                except Exception as e:
                    logger.error(f"Error in Django MQTT client: {e}")
            
            # Start in background thread
            thread = threading.Thread(target=start_mqtt_client, daemon=True)
            thread.start()
            
            logger.info("Django MQTT client thread started")
            
        except Exception as e:
            logger.error(f"Error starting Django MQTT client: {e}")
