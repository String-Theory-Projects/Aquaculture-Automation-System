"""
Django management command to start Celery beat with health check server.

This command runs both the Celery beat scheduler and a health check HTTP server.
The health server runs in a background thread, and Celery beat runs in the main thread.
"""

import os
import sys
import subprocess
import threading
import signal
import logging
from django.core.management.base import BaseCommand
from core.management.commands.celery_beat_health import Command as HealthCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start Celery beat with health check server'
    
    def __init__(self):
        super().__init__()
        self.celery_process = None
        self.health_command = None
        self.health_thread = None
        self.should_stop = False
    
    def handle(self, *args, **options):
        """Start Celery beat and health server"""
        self.stdout.write(
            self.style.SUCCESS('Starting Celery beat with health server...')
        )
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Start health server in background thread
        self._start_health_server()
        
        # Start Celery beat in foreground (blocking)
        self._start_celery_beat()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stdout.write(f'\nReceived signal {signum}, shutting down...')
        self.should_stop = True
        self._cleanup()
        sys.exit(0)
    
    def _start_health_server(self):
        """Start health server in background thread"""
        try:
            # Create health command instance
            self.health_command = HealthCommand()
            self.health_command.stdout = self.stdout  # Share stdout
            
            # Start health server in background thread
            def run_health_server():
                try:
                    self.health_command._start_health_server()
                    # Keep thread alive
                    if self.health_command.health_server:
                        self.health_command.health_server.serve_forever()
                except Exception as e:
                    logger.error(f'Health server error: {e}')
            
            self.health_thread = threading.Thread(
                target=run_health_server,
                daemon=True
            )
            self.health_thread.start()
            
            # Give it a moment to start
            import time
            time.sleep(0.5)
            
            self.stdout.write(
                self.style.SUCCESS('Health server started in background thread')
            )
        except Exception as e:
            logger.error(f'Failed to start health server: {e}')
            self.stdout.write(
                self.style.WARNING(f'Failed to start health server: {e}')
            )
    
    def _start_celery_beat(self):
        """Start Celery beat"""
        try:
            # Get Celery beat command from environment or use default
            beat_command = os.environ.get(
                'CELERY_BEAT_COMMAND',
                'celery -A FutureFish beat -l warning'
            )
            
            # Split command into parts
            cmd_parts = beat_command.split()
            
            self.stdout.write(
                self.style.SUCCESS(f'Starting Celery beat: {" ".join(cmd_parts)}')
            )
            
            # Start Celery beat (blocking)
            self.celery_process = subprocess.Popen(
                cmd_parts,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            # Wait for Celery beat to finish
            self.celery_process.wait()
            
        except KeyboardInterrupt:
            self.stdout.write('\nReceived interrupt signal, shutting down...')
        except Exception as e:
            logger.error(f'Error running Celery beat: {e}')
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up processes"""
        if self.celery_process:
            try:
                self.celery_process.terminate()
                self.celery_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f'Error terminating Celery beat: {e}')
                try:
                    self.celery_process.kill()
                except Exception:
                    pass
        
        if self.health_command and self.health_command.health_server:
            try:
                self.health_command.health_server.shutdown()
            except Exception as e:
                logger.warning(f'Error shutting down health server: {e}')

