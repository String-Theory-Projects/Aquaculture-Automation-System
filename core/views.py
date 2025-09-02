# Core app views
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import psutil
import os

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for Railway deployment"""
    try:
        # Basic system info
        memory_usage = psutil.virtual_memory().percent if hasattr(psutil, 'virtual_memory') else 0
        cpu_usage = psutil.cpu_percent() if hasattr(psutil, 'cpu_percent') else 0
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'service': 'Future Fish Dashboard',
            'version': '1.0.0',
            'environment': os.environ.get('DJANGO_SETTINGS_MODULE', 'unknown'),
            'system': {
                'memory_usage_percent': memory_usage,
                'cpu_usage_percent': cpu_usage,
            }
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'timestamp': timezone.now().isoformat(),
            'error': str(e)
        }, status=500)
