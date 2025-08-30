"""
Celery configuration for Future Fish Dashboard.

This module configures Celery for background task processing,
automation execution, and threshold monitoring.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FutureFish.settings.dev')

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
            'schedule': 30.0,  # Every 30 seconds
        },
        'sync-device-status-from-mqtt': {
            'task': 'mqtt_client.tasks.sync_device_status_from_mqtt',
            'schedule': 60.0,  # Every minute
        },
        'cleanup-old-mqtt-messages': {
            'task': 'mqtt_client.tasks.cleanup_old_mqtt_messages',
            'schedule': 3600.0,  # Every hour
        },
        'monitor-mqtt-bridge-health': {
            'task': 'mqtt_client.tasks.monitor_mqtt_bridge_health',
            'schedule': 300.0,  # Every 5 minutes
        },
        'check-scheduled-automations': {
            'task': 'automation.tasks.check_scheduled_automations',
            'schedule': 60.0,  # Every minute
        },
        'process-threshold-violations': {
            'task': 'automation.tasks.process_threshold_violations',
            'schedule': 30.0,  # Every 30 seconds
        },
    },
)

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration"""
    print(f'Request: {self.request!r}')
    return f'Debug task executed at {self.request.id}'
