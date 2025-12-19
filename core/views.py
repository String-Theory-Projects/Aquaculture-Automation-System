# Core app views
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
import psutil
import os
import json
import time
from typing import Dict, Any

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Enhanced health check endpoint for Railway deployment with service dependency checks"""
    overall_status = 'healthy'
    http_status = 200
    timestamp = timezone.now().isoformat()
    
    # Perform health checks with error handling
    checks = {
        'django': _check_django(),
        'database': _check_database(),
        'redis': _check_redis(),
        'services': {}
    }
    
    # Service checks - wrap in try/except to prevent one failure from breaking entire health check
    try:
        checks['services']['mqtt_client'] = _check_mqtt_client()
    except Exception as e:
        checks['services']['mqtt_client'] = {
            'status': 'unknown',
            'error': f'Check failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }
    
    try:
        checks['services']['mqtt_listener'] = _check_mqtt_listener()
    except Exception as e:
        checks['services']['mqtt_listener'] = {
            'status': 'unknown',
            'error': f'Check failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }
    
    try:
        checks['services']['celery_worker'] = _check_celery_worker()
    except Exception as e:
        checks['services']['celery_worker'] = {
            'status': 'unknown',
            'error': f'Check failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }
    
    try:
        checks['services']['celery_beat'] = _check_celery_beat()
    except Exception as e:
        checks['services']['celery_beat'] = {
            'status': 'unknown',
            'error': f'Check failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }
    
    # Determine overall status
    critical_failures = []
    degraded_services = []
    
    # Critical: Django, Database, Redis
    if checks['django']['status'] != 'healthy':
        critical_failures.append('django')
    if checks['database']['status'] != 'healthy':
        critical_failures.append('database')
    if checks['redis']['status'] != 'healthy':
        critical_failures.append('redis')
    
    # Check service health
    # Only mark as degraded if service is explicitly unhealthy, not if unknown/missing
    # This allows services to start up without causing health check failures
    for service_name, service_check in checks['services'].items():
        status = service_check.get('status', 'unknown')
        # Only mark as degraded if explicitly unhealthy, not if unknown (service may not have started yet)
        if status == 'unhealthy':
            degraded_services.append(service_name)
        # 'degraded' status from service check also counts as degraded
        elif status == 'degraded':
            degraded_services.append(service_name)
    
    # Set overall status
    if critical_failures:
        overall_status = 'unhealthy'
        http_status = 500
    elif degraded_services:
        overall_status = 'degraded'
        http_status = 503
    
    # Basic system info
    try:
        memory_usage = psutil.virtual_memory().percent if hasattr(psutil, 'virtual_memory') else 0
        cpu_usage = psutil.cpu_percent() if hasattr(psutil, 'cpu_percent') else 0
    except Exception:
        memory_usage = 0
        cpu_usage = 0
    
    response_data = {
        'status': overall_status,
        'timestamp': timestamp,
        'service': 'Future Fish Dashboard',
        'version': '1.0.0',
        'environment': os.environ.get('DJANGO_SETTINGS_MODULE', 'unknown'),
        'checks': checks,
        'system': {
            'memory_usage_percent': memory_usage,
            'cpu_usage_percent': cpu_usage,
        }
    }
    
    if critical_failures:
        response_data['critical_failures'] = critical_failures
    if degraded_services:
        response_data['degraded_services'] = degraded_services
    
    return JsonResponse(response_data, status=http_status)


def _check_django() -> Dict[str, Any]:
    """Check Django application health"""
    return {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat()
    }


def _check_database() -> Dict[str, Any]:
    """Check database connectivity with timeout protection"""
    from core.health_utils import check_health_with_timeout
    
    def check_db():
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {'status': 'healthy'}
    
    result = check_health_with_timeout(
        check_db,
        timeout_seconds=2.0,
        default_status='unknown'
    )
    
    if result.get('status') == 'healthy':
        return {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat()
        }
    elif result.get('timeout'):
        return {
            'status': 'degraded',
            'message': 'Database check timed out',
            'timestamp': timezone.now().isoformat()
        }
    else:
        return {
            'status': 'unhealthy',
            'error': result.get('error', 'Database check failed'),
            'timestamp': timezone.now().isoformat()
        }


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity with timeout protection"""
    from core.health_utils import check_health_with_timeout
    
    def check_redis_ping():
        from mqtt_client.bridge import get_redis_client
        redis_client = get_redis_client()
        redis_client.ping()
        return {'status': 'healthy'}
    
    result = check_health_with_timeout(
        check_redis_ping,
        timeout_seconds=2.0,
        default_status='unknown'
    )
    
    if result.get('status') == 'healthy':
        return {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat()
        }
    elif result.get('timeout'):
        return {
            'status': 'degraded',
            'message': 'Redis check timed out',
            'timestamp': timezone.now().isoformat()
        }
    else:
        return {
            'status': 'unhealthy',
            'error': result.get('error', 'Redis check failed'),
            'timestamp': timezone.now().isoformat()
        }


def _check_mqtt_client() -> Dict[str, Any]:
    """Check MQTT client service health via Redis heartbeat and subscriber count with timeout"""
    from core.health_utils import check_health_with_timeout
    
    def check_mqtt_client_status():
        from mqtt_client.bridge import get_redis_client, get_redis_status
        
        redis_client = get_redis_client()
        
        # Check Redis subscriber count
        redis_status = get_redis_status()
        outgoing_subscribers = redis_status.get('outgoing_subscribers', 0)
        
        # Check heartbeat from Redis
        heartbeat_key = 'health:mqtt_client'
        heartbeat_data = redis_client.get(heartbeat_key)
        
        heartbeat_status = None
        heartbeat_age_seconds = None
        
        if heartbeat_data:
            try:
                heartbeat = json.loads(heartbeat_data.decode('utf-8'))
                heartbeat_timestamp = heartbeat.get('timestamp')
                if heartbeat_timestamp:
                    from datetime import datetime
                    heartbeat_time = datetime.fromisoformat(heartbeat_timestamp.replace('Z', '+00:00'))
                    heartbeat_age_seconds = (timezone.now() - heartbeat_time.replace(tzinfo=timezone.utc)).total_seconds()
                    heartbeat_status = 'recent' if heartbeat_age_seconds < 60 else 'stale'
            except Exception:
                pass
        
        # Determine health status
        if outgoing_subscribers == 0:
            return {
                'status': 'unhealthy',
                'message': 'No Redis outgoing subscribers',
                'outgoing_subscribers': outgoing_subscribers,
                'heartbeat_status': heartbeat_status,
                'heartbeat_age_seconds': heartbeat_age_seconds
            }
        
        if heartbeat_status == 'stale' or heartbeat_age_seconds is None:
            return {
                'status': 'degraded',
                'message': 'Heartbeat stale or missing',
                'outgoing_subscribers': outgoing_subscribers,
                'heartbeat_status': heartbeat_status,
                'heartbeat_age_seconds': heartbeat_age_seconds
            }
        
        return {
            'status': 'healthy',
            'outgoing_subscribers': outgoing_subscribers,
            'heartbeat_status': heartbeat_status,
            'heartbeat_age_seconds': round(heartbeat_age_seconds, 2) if heartbeat_age_seconds else None
        }
    
    result = check_health_with_timeout(
        check_mqtt_client_status,
        timeout_seconds=2.0,
        default_status='unknown'
    )
    
    if result.get('timeout'):
        return {
            'status': 'unknown',
            'error': 'MQTT client check timed out',
            'timestamp': timezone.now().isoformat()
        }
    
    result['timestamp'] = timezone.now().isoformat()
    return result


def _check_mqtt_listener() -> Dict[str, Any]:
    """Check MQTT listener service health via Redis heartbeat and subscriber count with timeout"""
    from core.health_utils import check_health_with_timeout
    
    def check_mqtt_listener_status():
        from mqtt_client.bridge import get_redis_client, get_redis_status
        
        redis_client = get_redis_client()
        
        # Check Redis subscriber count
        redis_status = get_redis_status()
        incoming_subscribers = redis_status.get('incoming_subscribers', 0)
        
        # Check heartbeat from Redis
        heartbeat_key = 'health:mqtt_listener'
        heartbeat_data = redis_client.get(heartbeat_key)
        
        heartbeat_status = None
        heartbeat_age_seconds = None
        
        if heartbeat_data:
            try:
                heartbeat = json.loads(heartbeat_data.decode('utf-8'))
                heartbeat_timestamp = heartbeat.get('timestamp')
                if heartbeat_timestamp:
                    from datetime import datetime
                    heartbeat_time = datetime.fromisoformat(heartbeat_timestamp.replace('Z', '+00:00'))
                    heartbeat_age_seconds = (timezone.now() - heartbeat_time.replace(tzinfo=timezone.utc)).total_seconds()
                    heartbeat_status = 'recent' if heartbeat_age_seconds < 60 else 'stale'
            except Exception:
                pass
        
        # Determine health status
        if incoming_subscribers == 0:
            return {
                'status': 'unhealthy',
                'message': 'No Redis incoming subscribers',
                'incoming_subscribers': incoming_subscribers,
                'heartbeat_status': heartbeat_status,
                'heartbeat_age_seconds': heartbeat_age_seconds
            }
        
        if heartbeat_status == 'stale' or heartbeat_age_seconds is None:
            return {
                'status': 'degraded',
                'message': 'Heartbeat stale or missing',
                'incoming_subscribers': incoming_subscribers,
                'heartbeat_status': heartbeat_status,
                'heartbeat_age_seconds': heartbeat_age_seconds
            }
        
        return {
            'status': 'healthy',
            'incoming_subscribers': incoming_subscribers,
            'heartbeat_status': heartbeat_status,
            'heartbeat_age_seconds': round(heartbeat_age_seconds, 2) if heartbeat_age_seconds else None
        }
    
    result = check_health_with_timeout(
        check_mqtt_listener_status,
        timeout_seconds=2.0,
        default_status='unknown'
    )
    
    if result.get('timeout'):
        return {
            'status': 'unknown',
            'error': 'MQTT listener check timed out',
            'timestamp': timezone.now().isoformat()
        }
    
    result['timestamp'] = timezone.now().isoformat()
    return result


def _check_celery_worker() -> Dict[str, Any]:
    """Check Celery worker service health via Redis heartbeat with timeout"""
    from core.health_utils import check_health_with_timeout
    
    def check_worker_status():
        from mqtt_client.bridge import get_redis_client
        
        redis_client = get_redis_client()
        heartbeat_key = 'health:celery_worker'
        heartbeat_data = redis_client.get(heartbeat_key)
        
        if not heartbeat_data:
            return {
                'status': 'unknown',
                'message': 'No heartbeat found'
            }
        
        try:
            heartbeat = json.loads(heartbeat_data.decode('utf-8'))
            heartbeat_timestamp = heartbeat.get('timestamp')
            if heartbeat_timestamp:
                from datetime import datetime
                heartbeat_time = datetime.fromisoformat(heartbeat_timestamp.replace('Z', '+00:00'))
                heartbeat_age_seconds = (timezone.now() - heartbeat_time.replace(tzinfo=timezone.utc)).total_seconds()
                
                if heartbeat_age_seconds > 60:
                    return {
                        'status': 'unhealthy',
                        'message': 'Heartbeat stale',
                        'heartbeat_age_seconds': round(heartbeat_age_seconds, 2)
                    }
                
                return {
                    'status': 'healthy',
                    'heartbeat_age_seconds': round(heartbeat_age_seconds, 2),
                    'worker_id': heartbeat.get('worker_id')
                }
        except Exception as e:
            return {
                'status': 'unknown',
                'error': f'Failed to parse heartbeat: {str(e)}'
            }
        
        return {
            'status': 'unknown',
            'message': 'Heartbeat data invalid'
        }
    
    result = check_health_with_timeout(
        check_worker_status,
        timeout_seconds=2.0,
        default_status='unknown'
    )
    
    if result.get('timeout'):
        return {
            'status': 'unknown',
            'error': 'Celery worker check timed out',
            'timestamp': timezone.now().isoformat()
        }
    
    result['timestamp'] = timezone.now().isoformat()
    return result


def _check_celery_beat() -> Dict[str, Any]:
    """Check Celery beat service health via Redis heartbeat with timeout"""
    from core.health_utils import check_health_with_timeout
    
    def check_beat_status():
        from mqtt_client.bridge import get_redis_client
        
        redis_client = get_redis_client()
        heartbeat_key = 'health:celery_beat'
        heartbeat_data = redis_client.get(heartbeat_key)
        
        if not heartbeat_data:
            return {
                'status': 'unknown',
                'message': 'No heartbeat found'
            }
        
        try:
            heartbeat = json.loads(heartbeat_data.decode('utf-8'))
            heartbeat_timestamp = heartbeat.get('timestamp')
            if heartbeat_timestamp:
                from datetime import datetime
                heartbeat_time = datetime.fromisoformat(heartbeat_timestamp.replace('Z', '+00:00'))
                heartbeat_age_seconds = (timezone.now() - heartbeat_time.replace(tzinfo=timezone.utc)).total_seconds()
                
                if heartbeat_age_seconds > 60:
                    return {
                        'status': 'unhealthy',
                        'message': 'Heartbeat stale',
                        'heartbeat_age_seconds': round(heartbeat_age_seconds, 2)
                    }
                
                return {
                    'status': 'healthy',
                    'heartbeat_age_seconds': round(heartbeat_age_seconds, 2),
                    'scheduled_tasks_count': heartbeat.get('scheduled_tasks_count', 0)
                }
        except Exception as e:
            return {
                'status': 'unknown',
                'error': f'Failed to parse heartbeat: {str(e)}'
            }
        
        return {
            'status': 'unknown',
            'message': 'Heartbeat data invalid'
        }
    
    result = check_health_with_timeout(
        check_beat_status,
        timeout_seconds=2.0,
        default_status='unknown'
    )
    
    if result.get('timeout'):
        return {
            'status': 'unknown',
            'error': 'Celery beat check timed out',
            'timestamp': timezone.now().isoformat()
        }
    
    result['timestamp'] = timezone.now().isoformat()
    return result
