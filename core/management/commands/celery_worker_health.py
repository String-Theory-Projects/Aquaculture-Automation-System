"""
Django management command to run Celery worker with health check server.

This command starts a lightweight HTTP server for health checks while
the Celery worker runs. Railway can monitor the health endpoint.
"""

import json
import os
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from django.core.management.base import BaseCommand
from django.utils import timezone
from mqtt_client.bridge import get_redis_client, get_redis_status

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run Celery worker health check server'
    
    def __init__(self):
        super().__init__()
        self.health_server = None
        self.health_server_thread = None
    
    def handle(self, *args, **options):
        """Start the health check server"""
        self.stdout.write(
            self.style.SUCCESS('Starting Celery worker health server...')
        )
        
        try:
            self._start_health_server()
            
            self.stdout.write(
                self.style.SUCCESS('Health server started. Celery worker should be running separately.')
            )
            self.stdout.write('Press Ctrl+C to stop')
            
            # Keep the process alive
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write('\nShutting down health server...')
        except Exception as e:
            logger.error(f'Error running health server: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
            raise
        finally:
            self._cleanup()
    
    def _start_health_server(self):
        """Start HTTP health server in background thread"""
        try:
            # Get port from environment (Railway sets PORT for all services)
            health_port = int(os.environ.get('PORT', 8080))
            
            # Create health server handler with closure to access command instance
            command_instance = self
            
            class HealthHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/health/':
                        status = command_instance._check_health()
                        # Determine status code: 500 for critical failures, 503 for degraded
                        # Critical: redis_broker_connected=False or heartbeat_status != 'recent'
                        checks = status.get('checks', {})
                        critical_failure = (
                            not checks.get('redis_broker_connected', False) or
                            checks.get('heartbeat_status') != 'recent'
                        )
                        http_status = 200 if status['healthy'] else (500 if critical_failure else 503)
                        
                        self.send_response(http_status)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(status).encode('utf-8'))
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    # Suppress default HTTP server logging
                    pass
            
            self.health_server = HTTPServer(('0.0.0.0', health_port), HealthHandler)
            
            # Only start thread if not already started (for standalone mode)
            if not hasattr(self, 'health_server_thread') or not self.health_server_thread:
                self.health_server_thread = threading.Thread(
                    target=self.health_server.serve_forever,
                    daemon=True
                )
                self.health_server_thread.start()
            
            logger.info(f'Celery worker health server started on port {health_port}')
            if hasattr(self, 'stdout') and self.stdout:
                self.stdout.write(
                    self.style.SUCCESS(f'Health server started on port {health_port}')
                )
            
        except Exception as e:
            logger.error(f'Failed to start health server: {e}')
            if hasattr(self, 'stdout') and self.stdout:
                self.stdout.write(
                    self.style.ERROR(f'Failed to start health server: {e}')
                )
            raise
    
    def _check_health(self):
        """Check Celery worker health status with timeout protection"""
        from core.health_utils import check_health_with_timeout
        
        checks = {
            'redis_connected': False,
            'redis_broker_connected': False,
            'heartbeat_status': None,
            'heartbeat_age_seconds': None,
            'worker_id': None
        }
        
        # Check Redis connectivity with timeout
        def check_redis_status():
            redis_status = get_redis_status()
            return redis_status.get('status') == 'connected'
        
        redis_status_result = check_health_with_timeout(
            check_redis_status,
            timeout_seconds=2.0,
            default_status='unknown'
        )
        
        if redis_status_result.get('status') != 'unknown' and not redis_status_result.get('timeout'):
            checks['redis_connected'] = redis_status_result
        else:
            checks['redis_error'] = redis_status_result.get('error', 'Redis status check failed')
            if redis_status_result.get('timeout'):
                checks['redis_timeout'] = True
        
        # Check Redis broker connectivity with timeout
        def check_redis_broker():
            redis_client = get_redis_client()
            redis_client.ping()
            return True
        
        redis_broker_result = check_health_with_timeout(
            check_redis_broker,
            timeout_seconds=2.0,
            default_status='unknown'
        )
        
        if redis_broker_result.get('status') != 'unknown' and not redis_broker_result.get('timeout'):
            checks['redis_broker_connected'] = redis_broker_result
        else:
            checks['redis_broker_error'] = redis_broker_result.get('error', 'Redis broker check failed')
            if redis_broker_result.get('timeout'):
                checks['redis_broker_timeout'] = True
        
        # Check heartbeat from Redis with timeout
        def check_heartbeat():
            redis_client = get_redis_client()
            heartbeat_key = 'health:celery_worker'
            heartbeat_data = redis_client.get(heartbeat_key)
            
            if not heartbeat_data:
                return {'status': 'missing'}
            
            heartbeat = json.loads(heartbeat_data.decode('utf-8'))
            heartbeat_timestamp = heartbeat.get('timestamp')
            if heartbeat_timestamp:
                from datetime import datetime
                heartbeat_time = datetime.fromisoformat(heartbeat_timestamp.replace('Z', '+00:00'))
                heartbeat_age_seconds = (timezone.now() - heartbeat_time.replace(tzinfo=timezone.utc)).total_seconds()
                return {
                    'status': 'recent' if heartbeat_age_seconds < 60 else 'stale',
                    'age_seconds': round(heartbeat_age_seconds, 2),
                    'worker_id': heartbeat.get('worker_id')
                }
            return {'status': 'invalid'}
        
        heartbeat_result = check_health_with_timeout(
            check_heartbeat,
            timeout_seconds=2.0,
            default_status='unknown'
        )
        
        if heartbeat_result.get('status') != 'unknown' and not heartbeat_result.get('timeout'):
            checks['heartbeat_status'] = heartbeat_result.get('status')
            checks['heartbeat_age_seconds'] = heartbeat_result.get('age_seconds')
            checks['worker_id'] = heartbeat_result.get('worker_id')
        else:
            checks['heartbeat_error'] = heartbeat_result.get('error', 'Heartbeat check failed')
            if heartbeat_result.get('timeout'):
                checks['heartbeat_timeout'] = True
        
        # Determine overall health: critical checks are redis_broker_connected and heartbeat_status
        healthy = (
            checks['redis_connected'] and
            checks['redis_broker_connected'] and
            checks['heartbeat_status'] == 'recent'
        )
        
        return {
            'healthy': healthy,
            'timestamp': timezone.now().isoformat(),
            'checks': checks
        }
    
    def _cleanup(self):
        """Clean up resources"""
        if self.health_server:
            try:
                self.health_server.shutdown()
            except Exception as e:
                logger.warning(f'Error shutting down health server: {e}')

