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
        'monitor-command-timeouts': {
            'task': 'mqtt_client.tasks.monitor_command_timeouts',
            'schedule': 10.0,  # Every 10 seconds
        },
        'update-device-offline-status': {
            'task': 'mqtt_client.tasks.update_device_offline_status',
            'schedule': 30.0,  # Every 30 seconds
        },
        'cleanup-old-mqtt-messages': {
            'task': 'mqtt_client.tasks.cleanup_old_mqtt_messages',
            'schedule': 3600.0,  # Every hour
        },
        'cleanup-old-device-logs': {
            'task': 'mqtt_client.tasks.cleanup_old_device_logs',
            'schedule': 3600.0,  # Every hour
        },
        'generate-system-health-report': {
            'task': 'mqtt_client.tasks.generate_system_health_report',
            'schedule': 300.0,  # Every 5 minutes
        },
        'retry-failed-commands': {
            'task': 'mqtt_client.tasks.retry_failed_commands',
            'schedule': 60.0,  # Every minute
        },
        'cleanup-completed-automations': {
            'task': 'mqtt_client.tasks.cleanup_completed_automations',
            'schedule': 3600.0,  # Every hour
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
