"""
Celery configuration for Future Fish Dashboard.

This module configures Celery for background task processing,
automation execution, and threshold monitoring.
"""

import os
from celery import Celery
from django.conf import settings

# Create the Celery app
app = Celery('FutureFish')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Configure Celery settings
app.conf.update(
    # Task routing
    task_routes={
        'automation.tasks.*': {'queue': 'automation'},
        'mqtt_client.tasks.*': {'queue': 'mqtt'},
        'analytics.tasks.*': {'queue': 'analytics'},
    },
    
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone=settings.TIME_ZONE,
    enable_utc=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Task settings
    task_always_eager=False,  # Set to True for testing
    task_eager_propagates=True,
    
    # Result backend settings
    result_backend=settings.CELERY_RESULT_BACKEND,
    result_expires=3600,  # 1 hour
    
    # Beat settings for periodic tasks
    beat_schedule={
        'handle-command-timeouts': {
            'task': 'mqtt_client.tasks.handle_command_timeouts',
            'schedule': settings.CELERY_HANDLE_COMMAND_TIMEOUTS_INTERVAL,
        },
        'sync-device-status-from-mqtt': {
            'task': 'mqtt_client.tasks.sync_device_status_from_mqtt',
            'schedule': settings.CELERY_SYNC_DEVICE_STATUS_INTERVAL,
        },
        'cleanup-old-mqtt-messages': {
            'task': 'mqtt_client.tasks.cleanup_old_mqtt_messages',
            'schedule': settings.CELERY_CLEANUP_OLD_MQTT_MESSAGES_INTERVAL,
        },
        'monitor-mqtt-bridge-health': {
            'task': 'mqtt_client.tasks.monitor_mqtt_bridge_health',
            'schedule': settings.CELERY_MONITOR_MQTT_BRIDGE_HEALTH_INTERVAL,
        },
        'cleanup-stuck-automations': {
            'task': 'mqtt_client.tasks.cleanup_stuck_automations',
            'schedule': settings.CELERY_CLEANUP_STUCK_AUTOMATIONS_INTERVAL,
        },
        'check-scheduled-automations': {
            'task': 'automation.tasks.check_scheduled_automations',
            'schedule': settings.CELERY_CHECK_SCHEDULED_AUTOMATIONS_INTERVAL,
        },
        'process-threshold-violations': {
            'task': 'automation.tasks.process_threshold_violations',
            'schedule': settings.CELERY_PROCESS_THRESHOLD_VIOLATIONS_INTERVAL,
        },
    },
)

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration"""
    print(f'Request: {self.request!r}')
    return f'Debug task executed at {self.request.id}'
