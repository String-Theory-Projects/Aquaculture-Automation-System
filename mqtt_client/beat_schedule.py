"""
Celery Beat Schedule for MQTT Bridge Tasks.

This module configures periodic tasks for the MQTT bridge system.
"""

from celery.schedules import crontab

# MQTT Bridge Task Schedule
mqtt_bridge_schedule = {
    # Process incoming MQTT messages from Redis every 10 seconds
    'process-mqtt-messages': {
        'task': 'mqtt_client.tasks.process_mqtt_messages_from_redis',
        'schedule': 10.0,  # Every 10 seconds
    },
    
    # Monitor bridge health every minute
    'monitor-bridge-health': {
        'task': 'mqtt_client.tasks.monitor_mqtt_bridge_health',
        'schedule': 60.0,  # Every minute
    },
    
    # Clean up old MQTT messages daily at 2 AM
    'cleanup-old-messages': {
        'task': 'mqtt_client.tasks.cleanup_old_mqtt_messages',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'args': (30,),  # Keep messages for 30 days
    },
    
    # Synchronize device status every 5 minutes
    'sync-device-status': {
        'task': 'mqtt_client.tasks.sync_device_status_from_mqtt',
        'schedule': 300.0,  # Every 5 minutes
    },
}

# Export the schedule for use in Celery configuration
CELERY_BEAT_SCHEDULE = mqtt_bridge_schedule
