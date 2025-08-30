"""
Background tasks for MQTT Client operations.

This module provides Celery tasks for:
- Command timeout monitoring
- Device status cleanup
- MQTT message cleanup
- System health monitoring
"""

import logging
from typing import List, Dict, Any
from django.utils import timezone
from django.db import transaction
from celery import shared_task
from datetime import timedelta

from .models import DeviceStatus, MQTTMessage
from automation.models import DeviceCommand
from ponds.models import PondPair

logger = logging.getLogger(__name__)


@shared_task
def monitor_command_timeouts():
    """Monitor and handle command timeouts"""
    try:
        now = timezone.now()
        timeout_threshold = now - timedelta(seconds=10)  # 10 second timeout
        
        # Find timed out commands
        timed_out_commands = DeviceCommand.objects.filter(
            status='SENT',
            sent_at__lt=timeout_threshold
        )
        
        timeout_count = 0
        for command in timed_out_commands:
            try:
                with transaction.atomic():
                    if command.retry_command():
                        logger.info(f"Command {command.command_id} retried (attempt {command.retry_count})")
                        timeout_count += 1
                    else:
                        # Max retries reached, mark as timed out
                        command.timeout_command()
                        logger.warning(f"Command {command.command_id} timed out after max retries")
                        
                        # Update automation execution if linked
                        if command.automation_execution:
                            command.automation_execution.complete_execution(
                                success=False,
                                message=f"Command timed out after {command.max_retries} retries",
                                error_details="Maximum retry attempts reached"
                            )
                        
                        timeout_count += 1
                        
            except Exception as e:
                logger.error(f"Error handling timeout for command {command.command_id}: {e}")
                continue
        
        if timeout_count > 0:
            logger.info(f"Processed {timeout_count} timed out commands")
            
        return {
            'success': True,
            'timeout_count': timeout_count,
            'timestamp': now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in monitor_command_timeouts task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def cleanup_old_mqtt_messages():
    """Clean up old MQTT messages to prevent database bloat"""
    try:
        # Keep messages for 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Count messages to be deleted
        old_messages = MQTTMessage.objects.filter(
            created_at__lt=cutoff_date
        )
        delete_count = old_messages.count()
        
        # Delete old messages
        old_messages.delete()
        
        logger.info(f"Cleaned up {delete_count} old MQTT messages")
        
        return {
            'success': True,
            'deleted_count': delete_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_mqtt_messages task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def cleanup_old_device_logs():
    """Clean up old device logs to prevent database bloat"""
    try:
        # Keep logs for 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        
        # Count logs to be deleted
        old_logs = DeviceStatus.objects.filter(
            last_error_at__lt=cutoff_date,
            error_count__gt=0
        )
        delete_count = old_logs.count()
        
        # Reset error counts for old logs
        old_logs.update(
            error_count=0,
            last_error=None,
            last_error_at=None
        )
        
        logger.info(f"Cleaned up {delete_count} old device error logs")
        
        return {
            'success': True,
            'cleaned_count': delete_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_device_logs task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def update_device_offline_status():
    """Update device offline status based on heartbeat timeout"""
    try:
        # Consider device offline if no heartbeat for 30 seconds
        offline_threshold = timezone.now() - timedelta(seconds=30)
        
        # Find devices that should be marked offline
        offline_devices = DeviceStatus.objects.filter(
            status='ONLINE',
            last_seen__lt=offline_threshold
        )
        
        offline_count = 0
        for device_status in offline_devices:
            try:
                device_status.mark_offline()
                offline_count += 1
                logger.info(f"Marked device {device_status.pond_pair.name} as offline")
            except Exception as e:
                logger.error(f"Error marking device {device_status.pond_pair.name} offline: {e}")
                continue
        
        if offline_count > 0:
            logger.info(f"Updated {offline_count} devices to offline status")
        
        return {
            'success': True,
            'offline_count': offline_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in update_device_offline_status task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def generate_system_health_report():
    """Generate comprehensive system health report"""
    try:
        now = timezone.now()
        
        # Get system statistics
        total_devices = PondPair.objects.count()
        online_devices = DeviceStatus.objects.filter(status='ONLINE').count()
        offline_devices = DeviceStatus.objects.filter(status='OFFLINE').count()
        error_devices = DeviceStatus.objects.filter(status='ERROR').count()
        
        # Get command statistics
        total_commands = DeviceCommand.objects.count()
        pending_commands = DeviceCommand.objects.filter(status='PENDING').count()
        sent_commands = DeviceCommand.objects.filter(status='SENT').count()
        completed_commands = DeviceCommand.objects.filter(status='COMPLETED').count()
        failed_commands = DeviceCommand.objects.filter(status='FAILED').count()
        timeout_commands = DeviceCommand.objects.filter(status='TIMEOUT').count()
        
        # Get MQTT message statistics
        total_messages = MQTTMessage.objects.count()
        recent_messages = MQTTMessage.objects.filter(
            created_at__gte=now - timedelta(hours=1)
        ).count()
        error_messages = MQTTMessage.objects.filter(success=False).count()
        
        # Calculate success rates
        command_success_rate = (
            (completed_commands / total_commands * 100) if total_commands > 0 else 0
        )
        message_success_rate = (
            ((total_messages - error_messages) / total_messages * 100) if total_messages > 0 else 0
        )
        
        # Generate report
        report = {
            'timestamp': now.isoformat(),
            'device_status': {
                'total': total_devices,
                'online': online_devices,
                'offline': offline_devices,
                'error': error_devices,
                'connectivity_percentage': round((online_devices / total_devices * 100) if total_devices > 0 else 0, 2)
            },
            'command_status': {
                'total': total_commands,
                'pending': pending_commands,
                'sent': sent_commands,
                'completed': completed_commands,
                'failed': failed_commands,
                'timeout': timeout_commands,
                'success_rate': round(command_success_rate, 2)
            },
            'mqtt_status': {
                'total_messages': total_messages,
                'recent_messages': recent_messages,
                'error_messages': error_messages,
                'success_rate': round(message_success_rate, 2)
            },
            'system_health': {
                'overall_score': round((command_success_rate + message_success_rate) / 2, 2),
                'status': 'HEALTHY' if command_success_rate > 90 and message_success_rate > 95 else 'DEGRADED'
            }
        }
        
        logger.info(f"Generated system health report: {report['system_health']['status']}")
        
        return {
            'success': True,
            'report': report
        }
        
    except Exception as e:
        logger.error(f"Error in generate_system_health_report task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def retry_failed_commands():
    """Retry failed commands that can be retried"""
    try:
        # Find failed commands that can be retried
        retryable_commands = DeviceCommand.objects.filter(
            status='FAILED',
            retry_count__lt=3  # Max 3 retries
        )
        
        retry_count = 0
        for command in retryable_commands:
            try:
                with transaction.atomic():
                    if command.retry_command():
                        logger.info(f"Retrying failed command {command.command_id}")
                        retry_count += 1
                        
                        # Update automation execution if linked
                        if command.automation_execution:
                            command.automation_execution.status = 'EXECUTING'
                            command.automation_execution.save()
                            
            except Exception as e:
                logger.error(f"Error retrying command {command.command_id}: {e}")
                continue
        
        if retry_count > 0:
            logger.info(f"Retried {retry_count} failed commands")
        
        return {
            'success': True,
            'retry_count': retry_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in retry_failed_commands task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def cleanup_completed_automations():
    """Clean up old completed automation executions"""
    try:
        # Keep completed automations for 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Count automations to be cleaned up
        old_automations = DeviceCommand.objects.filter(
            status__in=['COMPLETED', 'FAILED', 'TIMEOUT'],
            completed_at__lt=cutoff_date
        )
        cleanup_count = old_automations.count()
        
        # Archive old automations (you might want to move them to a separate table)
        # For now, we'll just log them
        for automation in old_automations:
            logger.debug(f"Old automation execution: {automation.id} - {automation.status}")
        
        logger.info(f"Identified {cleanup_count} old automation executions for cleanup")
        
        return {
            'success': True,
            'cleanup_count': cleanup_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in cleanup_completed_automations task: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }

