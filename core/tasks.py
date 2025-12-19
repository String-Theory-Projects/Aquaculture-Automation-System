"""
Core Celery tasks for system health monitoring.

This module provides periodic tasks for writing health check heartbeats
to Redis for Celery worker and beat services.
"""

import json
import logging
import socket
from celery import shared_task
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name='core.tasks.celery_worker_heartbeat', bind=False)
def celery_worker_heartbeat():
    """
    Write Celery worker heartbeat to Redis with retry logic.
    
    This task runs periodically (every 30 seconds) to indicate the worker is alive.
    """
    from core.health_utils import write_heartbeat_with_retry
    
    def write_func():
        from mqtt_client.bridge import get_redis_client
        
        redis_client = get_redis_client()
        
        # Get worker hostname/ID
        hostname = socket.gethostname()
        worker_id = f"celery@{hostname}"
        
        heartbeat_data = {
            'timestamp': timezone.now().isoformat(),
            'worker_id': worker_id,
            'hostname': hostname,
        }
        
        # Try to get active task count (optional, may not always be available)
        try:
            from celery import current_app
            inspect = current_app.control.inspect()
            active_tasks = inspect.active()
            if active_tasks:
                # Count active tasks for this worker
                total_active = sum(len(tasks) for tasks in active_tasks.values())
                heartbeat_data['active_tasks'] = total_active
        except Exception:
            pass
        
        # Write to Redis with TTL (90 seconds)
        redis_client.setex(
            'health:celery_worker',
            90,  # TTL in seconds
            json.dumps(heartbeat_data)
        )
        
        logger.debug(f'Celery worker heartbeat written: {worker_id}')
        return f'Heartbeat written for {worker_id}'
    
    # Use retry logic - don't crash if it fails
    success = write_heartbeat_with_retry(write_func, service_name='celery_worker')
    if success:
        return f'Heartbeat written successfully'
    else:
        return f'Heartbeat write failed after retries'


@shared_task(name='core.tasks.celery_beat_heartbeat', bind=False)
def celery_beat_heartbeat():
    """
    Write Celery beat heartbeat to Redis with retry logic.
    
    This task runs periodically (every 30 seconds) to indicate the beat scheduler is alive.
    """
    from core.health_utils import write_heartbeat_with_retry
    
    def write_func():
        from mqtt_client.bridge import get_redis_client
        
        redis_client = get_redis_client()
        
        heartbeat_data = {
            'timestamp': timezone.now().isoformat(),
            'scheduled_tasks_count': len(getattr(settings, 'CELERY_BEAT_SCHEDULE', {})),
        }
        
        # Write to Redis with TTL (90 seconds)
        redis_client.setex(
            'health:celery_beat',
            90,  # TTL in seconds
            json.dumps(heartbeat_data)
        )
        
        logger.debug('Celery beat heartbeat written')
        return 'Heartbeat written for Celery beat'
    
    # Use retry logic - don't crash if it fails
    success = write_heartbeat_with_retry(write_func, service_name='celery_beat')
    if success:
        return f'Heartbeat written successfully'
    else:
        return f'Heartbeat write failed after retries'

