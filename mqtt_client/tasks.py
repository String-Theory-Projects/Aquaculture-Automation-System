"""
MQTT Client Tasks for Future Fish Dashboard.

This module provides Celery tasks for:
- Processing incoming MQTT messages from Redis
- Handling device status updates
- Managing MQTT bridge operations
"""

import json
import logging
from typing import Dict, Any
from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .bridge import get_redis_client, MQTT_INCOMING_CHANNEL
from .consumers import process_mqtt_message

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_mqtt_messages_from_redis(self):
    """
    Process incoming MQTT messages from Redis channel.
    
    This task runs periodically to check for new messages and process them.
    """
    try:
        redis_client = get_redis_client()
        
        # Get messages from Redis channel (non-blocking)
        messages = redis_client.pubsub().get_message(timeout=1)
        
        if messages:
            for message in messages:
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'].decode('utf-8'))
                        success = process_mqtt_message(data)
                        
                        if not success:
                            logger.warning(f"Failed to process MQTT message: {data}")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in Redis message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing MQTT message: {e}")
                        
        return f"Processed MQTT messages from Redis"
        
    except Exception as e:
        logger.error(f"Error in process_mqtt_messages_from_redis task: {e}")
        
        # Retry the task
        try:
            self.retry(countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for process_mqtt_messages_from_redis task")
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def monitor_mqtt_bridge_health(self):
    """
    Monitor the health of the MQTT bridge and Redis connection.
    
    This task runs periodically to ensure the bridge is functioning correctly.
    """
    try:
        from .bridge import get_redis_status
        
        status = get_redis_status()
        
        if status['status'] == 'error':
            logger.error(f"MQTT bridge health check failed: {status['error']}")
            
            # Retry the task
            try:
                self.retry(countdown=60, max_retries=3)
            except self.MaxRetriesExceededError:
                logger.error(f"Max retries exceeded for monitor_mqtt_bridge_health task")
                raise
        else:
            logger.debug(f"MQTT bridge health check passed: {status}")
            
        return status
        
    except Exception as e:
        logger.error(f"Error in monitor_mqtt_bridge_health task: {e}")
        
        # Retry the task
        try:
            self.retry(countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for monitor_mqtt_bridge_health task")
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_old_mqtt_messages(self):
    """
    Clean up old MQTT messages from the database.
    
    This task runs periodically to remove old messages and free up space.
    """
    try:
        from .models import MQTTMessage
        from django.utils import timezone
        from datetime import timedelta
        
        # Delete messages older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count, _ = MQTTMessage.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old MQTT messages")
        
        return f"Cleaned up {deleted_count} old MQTT messages"
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_mqtt_messages task: {e}")
        
        # Retry the task
        try:
            self.retry(countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for cleanup_old_mqtt_messages task")
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_device_status_from_mqtt(self):
    """
    Sync device status from MQTT messages.
    
    This task runs periodically to update device status based on recent MQTT activity.
    """
    try:
        from ponds.models import PondPair
        from django.utils import timezone
        from datetime import timedelta
        
        # Update device status based on recent MQTT activity
        cutoff_time = timezone.now() - timedelta(minutes=5)
        
        # Find devices with recent MQTT activity
        active_devices = PondPair.objects.filter(
            mqtt_messages__received_at__gte=cutoff_time
        ).distinct()
        
        for device in active_devices:
            # Update device status to ONLINE if recent activity
            if device.status != 'ONLINE':
                device.status = 'ONLINE'
                device.last_seen = timezone.now()
                device.save()
                logger.info(f"Updated device {device.device_id} status to ONLINE")
        
        # Find devices with no recent activity (mark as OFFLINE)
        inactive_devices = PondPair.objects.filter(
            mqtt_messages__received_at__lt=cutoff_time
        ).distinct()
        
        for device in inactive_devices:
            if device.status == 'ONLINE':
                device.status = 'OFFLINE'
                device.save()
                logger.info(f"Updated device {device.device_id} status to OFFLINE")
        
        return f"Synced status for {active_devices.count()} active and {inactive_devices.count()} inactive devices"
        
    except Exception as e:
        logger.error(f"Error in sync_device_status_from_mqtt task: {e}")
        
        # Retry the task
        try:
            self.retry(countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for sync_device_status_from_mqtt task")
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def handle_command_timeouts(self):
    """
    Handle command timeouts automatically.
    
    This task runs periodically to check for commands that have exceeded their timeout
    and mark them as timed out.
    """
    try:
        from automation.models import DeviceCommand
        from django.utils import timezone
        from datetime import timedelta
        
        # Find commands that have been SENT but not acknowledged within timeout
        now = timezone.now()
        timed_out_commands = []
        
        # Get all SENT commands
        sent_commands = DeviceCommand.objects.filter(status='SENT')
        
        for command in sent_commands:
            if command.sent_at:
                # Check if command has exceeded timeout
                time_since_sent = (now - command.sent_at).total_seconds()
                
                if time_since_sent > command.timeout_seconds:
                    logger.warning(f"Command {command.command_id} has timed out after {time_since_sent}s (limit: {command.timeout_seconds}s)")
                    
                    # Mark command as timed out
                    command.timeout_command()
                    timed_out_commands.append(command.command_id)
                    
                    # Update linked automation execution if exists
                    if command.automation_execution:
                        automation = command.automation_execution
                        automation.complete_execution(False, f"Command timed out after {command.timeout_seconds}s")
                        logger.warning(f"Automation {automation.id} marked as failed due to command timeout")
        
        if timed_out_commands:
            logger.info(f"Handled {len(timed_out_commands)} timed out commands: {timed_out_commands}")
            return f"Handled {len(timed_out_commands)} timed out commands"
        else:
            logger.debug("No commands timed out in this cycle")
            return "No commands timed out"
        
    except Exception as e:
        logger.error(f"Error in handle_command_timeouts task: {e}")
        
        # Retry the task
        try:
            self.retry(countdown=60, max_retries=3)
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for handle_command_timeouts task")
            raise


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def cleanup_stuck_automations(self):
    """
    Clean up automations stuck in EXECUTING status.
    
    This task runs periodically to check for automation executions that have been
    stuck in EXECUTING status for too long and mark them as failed.
    """
    try:
        from automation.models import AutomationExecution
        from django.utils import timezone
        from datetime import timedelta
        
        # Find automations stuck in EXECUTING status for more than 1 hour
        cutoff_time = timezone.now() - timedelta(hours=1)
        stuck_automations = AutomationExecution.objects.filter(
            status='EXECUTING',
            started_at__lt=cutoff_time
        ).order_by('started_at')
        
        if not stuck_automations.exists():
            logger.debug("No stuck automations found")
            return "No stuck automations found"
        
        logger.warning(f"Found {stuck_automations.count()} automations stuck in EXECUTING status")
        cleaned_up_count = 0
        
        for automation in stuck_automations:
            try:
                # Check if linked commands exist and their status
                linked_commands = automation.device_commands.all()
                
                if linked_commands.exists():
                    # Get the most recent command status
                    latest_command = linked_commands.order_by('-updated_at').first()
                    command_statuses = [cmd.status for cmd in linked_commands]
                    
                    logger.info(f"Automation {automation.id} has linked commands: {command_statuses}")
                    
                    # If any command is completed/failed, sync the automation status
                    if latest_command.status == 'COMPLETED':
                        automation.complete_execution(True, "Auto-synced from completed command (cleanup task)")
                        logger.info(f"Synced automation {automation.id} to COMPLETED from command {latest_command.command_id}")
                        cleaned_up_count += 1
                        
                    elif latest_command.status in ['FAILED', 'TIMEOUT']:
                        automation.complete_execution(False, f"Auto-synced from {latest_command.status.lower()} command (cleanup task)")
                        logger.info(f"Synced automation {automation.id} to FAILED from command {latest_command.command_id}")
                        cleaned_up_count += 1
                        
                    elif latest_command.status in ['PENDING', 'SENT', 'ACKNOWLEDGED']:
                        # Commands are still in progress but automation has been executing too long
                        # Mark as failed due to timeout
                        hours_stuck = (timezone.now() - automation.started_at).total_seconds() / 3600
                        automation.complete_execution(
                            False, 
                            f"Automation timed out after {hours_stuck:.1f}h (cleanup task)",
                            f"Linked commands still in progress: {command_statuses}"
                        )
                        logger.warning(f"Marked automation {automation.id} as failed due to timeout (cleanup task)")
                        cleaned_up_count += 1
                        
                else:
                    # No linked commands - mark as failed
                    hours_stuck = (timezone.now() - automation.started_at).total_seconds() / 3600
                    automation.complete_execution(
                        False, 
                        f"No linked commands found - marked as failed (cleanup task)",
                        f"Automation stuck for {hours_stuck:.1f}h with no device commands"
                    )
                    logger.warning(f"Marked automation {automation.id} as failed - no linked commands (cleanup task)")
                    cleaned_up_count += 1
                    
            except Exception as e:
                logger.error(f"Error cleaning up automation {automation.id}: {e}")
                # Try to mark as failed with error details
                try:
                    automation.complete_execution(
                        False, 
                        f"Cleanup task error - marked as failed",
                        f"Error during cleanup: {str(e)}"
                    )
                    cleaned_up_count += 1
                except Exception as cleanup_error:
                    logger.error(f"Failed to mark automation {automation.id} as failed during cleanup: {cleanup_error}")
        
        if cleaned_up_count > 0:
            logger.info(f"Cleanup task completed: {cleaned_up_count} stuck automations processed")
            return f"Cleaned up {cleaned_up_count} stuck automations"
        else:
            return "No automations were cleaned up"
            
    except Exception as e:
        logger.error(f"Error in cleanup_stuck_automations task: {e}")
        
        # Retry the task
        try:
            self.retry(countdown=300, max_retries=3)  # Retry after 5 minutes
        except self.MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for cleanup_stuck_automations task")
            raise

