"""
Future Fish Dashboard - IoT Automation System

This is the main Django project for the Future Fish Dashboard,
an intelligent IoT automation system for fish farming.
"""

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ('celery_app',)
