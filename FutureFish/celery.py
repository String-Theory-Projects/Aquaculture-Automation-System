"""
Celery configuration for Future Fish Dashboard.

This module configures Celery for background task processing,
automation execution, and threshold monitoring.
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FutureFish.settings.dev')

# Create the Celery app
app = Celery('FutureFish')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure Celery settings - moved to settings.py to avoid import issues

@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery configuration"""
    print(f'Request: {self.request!r}')
    return f'Debug task executed at {self.request.id}'
