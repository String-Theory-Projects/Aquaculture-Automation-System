"""
Celery tasks for automation system.

This module provides background tasks for:
- Threshold monitoring and automation triggers
- Scheduled automation execution
- Priority-based conflict resolution
- Automation execution engine
"""

import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from celery import shared_task
from datetime import timedelta
import json

from .models import (
    AutomationExecution, DeviceCommand, AutomationSchedule,
    FeedEvent, FeedStat, FeedStatHistory
)
from ponds.models import Pond, SensorData, SensorThreshold, Alert
from mqtt_client.bridge_service import get_mqtt_bridge_service
from core.constants import AUTOMATION_PRIORITIES, DEFAULT_THRESHOLD_TIMEOUT
from core.choices import AUTOMATION_TYPES, AUTOMATION_ACTIONS, COMMAND_TYPES

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_parameter_thresholds(self, pond_id: int, parameter: str, value: float):
    """
    Check if a sensor parameter violates thresholds and trigger automations.
    
    Args:
        pond_id: ID of the pond to check
        parameter: Sensor parameter name (e.g., 'temperature', 'water_level')
        value: Current sensor value
    """
    try:
        with transaction.atomic():
            # Get pond and active thresholds
            try:
                pond = Pond.objects.get(id=pond_id)
            except Pond.DoesNotExist:
                logger.error(f"Pond {pond_id} not found")
                return False
            
            thresholds = SensorThreshold.objects.filter(
                pond=pond,
                parameter=parameter,
                is_active=True
            )
            
            if not thresholds.exists():
                logger.debug(f"No active thresholds for {parameter} in pond {pond_id}")
                return True
            
            for threshold in thresholds:
                # Check if threshold is violated
                is_violated = (
                    value > threshold.upper_threshold or
                    value < threshold.lower_threshold
                )
                
                if is_violated:
                    logger.info(f"Threshold violation detected: {parameter}={value} "
                              f"(range: {threshold.lower_threshold}-{threshold.upper_threshold})")
                    
                    # Create or update alert
                    alert, created = Alert.objects.get_or_create(
                        pond=pond,
                        parameter=parameter,
                        status='active',
                        defaults={
                            'alert_level': threshold.alert_level,
                            'message': f"{parameter.title()} threshold violation: {value} "
                                      f"(range: {threshold.lower_threshold}-{threshold.upper_threshold})",
                            'threshold_value': threshold.upper_threshold if value > threshold.upper_threshold else threshold.lower_threshold,
                            'current_value': value,
                            'violation_count': 1,
                        }
                    )
                    
                    if not created:
                        # Update existing alert
                        alert.violation_count += 1
                        alert.last_violation_at = timezone.now()
                        alert.current_value = value
                        alert.save()
                    
                    # Check if we should trigger automation
                    if alert.violation_count >= threshold.max_violations:
                        # Create automation execution
                        automation = AutomationExecution.objects.create(
                            pond=pond,
                            execution_type='WATER' if 'water' in parameter else 'FEED',
                            action=threshold.automation_action,
                            priority='THRESHOLD',
                            status='PENDING',
                            scheduled_at=timezone.now() + timedelta(seconds=threshold.violation_timeout),
                            threshold=threshold,
                            parameters={
                                'parameter': parameter,
                                'current_value': value,
                                'upper_threshold': threshold.upper_threshold,
                                'lower_threshold': threshold.lower_threshold,
                                'threshold_id': threshold.id,
                                'alert_id': alert.id,
                                'violation_count': alert.violation_count,
                            }
                        )
                        
                        logger.info(f"Created automation execution {automation.id} for threshold violation")
                        
                        # Schedule the automation execution
                        execute_automation.apply_async(
                            args=[automation.id],
                            countdown=threshold.violation_timeout
                        )
                    
                else:
                    # Threshold not violated, resolve active alerts
                    Alert.objects.filter(
                        pond=pond,
                        parameter=parameter,
                        status='active'
                    ).update(
                        status='resolved',
                        resolved_at=timezone.now()
                    )
            
            return True
            
    except Exception as exc:
        logger.error(f"Error checking thresholds for pond {pond_id}, parameter {parameter}: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def execute_automation(self, automation_id: int):
    """
    Execute an automation action.
    
    Args:
        automation_id: ID of the automation execution to run
    """
    try:
        with transaction.atomic():
            # Get automation execution
            try:
                automation = AutomationExecution.objects.select_for_update().get(id=automation_id)
            except AutomationExecution.DoesNotExist:
                logger.error(f"Automation execution {automation_id} not found")
                return False
            
            # Check if automation can be executed
            if automation.status not in ['PENDING', 'EXECUTING']:
                logger.warning(f"Automation {automation_id} cannot be executed (status: {automation.status})")
                return False
            
            # Check for priority conflicts (only for pending automations)
            if automation.status == 'PENDING' and not _can_execute_automation(automation):
                logger.info(f"Automation {automation_id} blocked by higher priority execution")
                # Reschedule for later
                execute_automation.apply_async(
                    args=[automation_id],
                    countdown=60  # Try again in 1 minute
                )
                return False
            
            # For manual commands that already have MQTT commands sent, just monitor completion
            if automation.priority == 'MANUAL_COMMAND' and automation.status == 'EXECUTING':
                mqtt_command_id = automation.parameters.get('mqtt_command_id')
                if mqtt_command_id:
                    logger.info(f"Automation {automation_id} already has MQTT command {mqtt_command_id} sent, monitoring completion")
                    # The automation will be completed when the MQTT acknowledgment is received
                    # For now, just return success as the command was sent
                    return True
            
            # Check if automation has been executing too long (timeout protection)
            if automation.status == 'EXECUTING' and automation.started_at:
                execution_time = timezone.now() - automation.started_at
                max_execution_time = timedelta(hours=2)  # 2 hour timeout
                
                if execution_time > max_execution_time:
                    logger.warning(f"Automation {automation_id} has been executing for {execution_time.total_seconds()/3600:.1f}h, marking as failed")
                    automation.complete_execution(
                        False, 
                        f"Automation timed out after {execution_time.total_seconds()/3600:.1f}h",
                        f"Maximum execution time exceeded: {max_execution_time}"
                    )
                    return False
            
            # Mark as executing if not already
            if automation.status == 'PENDING':
                automation.start_execution()
            
            # Execute based on action type
            success = False
            message = ""
            error_details = ""
            
            try:
                if automation.action == 'FEED':
                    success, message, error_details = _execute_feed_automation(automation)
                elif automation.execution_type == 'WATER':
                    # Handle water-related automations
                    if automation.action in ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 
                                           'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                                           'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                        success, message, error_details = _execute_water_automation(automation)
                    else:
                        success, message, error_details = False, f"Unsupported water action: {automation.action}", f"Action {automation.action} not supported"
                elif automation.action == 'ALERT':
                    success, message, error_details = _execute_alert_automation(automation)
                elif automation.action == 'NOTIFICATION':
                    success, message, error_details = _execute_notification_automation(automation)
                elif automation.action == 'LOG':
                    success, message, error_details = _execute_log_automation(automation)
                else:
                    error_details = f"Unknown automation action: {automation.action}"
                    success = False
                
            except Exception as e:
                error_details = f"Error executing automation: {str(e)}"
                success = False
                logger.error(f"Error executing automation {automation_id}: {e}")
            
            # Complete automation execution
            automation.complete_execution(success, message, error_details)
            
            if success:
                logger.info(f"✅ Automation {automation_id} completed successfully: {message}")
            else:
                logger.warning(f"❌ Automation {automation_id} failed: {message}")
                if error_details:
                    logger.warning(f"   Error details: {error_details}")
            
            return success
            
    except Exception as e:
        logger.error(f"Error in execute_automation task for {automation_id}: {e}")
        
        # Try to mark automation as failed if we can access it
        try:
            automation = AutomationExecution.objects.get(id=automation_id)
            automation.complete_execution(False, f"Task execution error: {str(e)}", f"Exception: {type(e).__name__}: {str(e)}")
        except Exception as cleanup_error:
            logger.error(f"Could not mark automation {automation_id} as failed: {cleanup_error}")
        
        # Retry the task
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def check_scheduled_automations(self):
    """
    Check for scheduled automations that need to be executed.
    This task runs every minute to check schedules.
    """
    try:
        now = timezone.localtime(timezone.now())
        current_time = now.time()
        
        # Get active schedules that should run now
        active_schedules = AutomationSchedule.objects.filter(
            is_active=True,
            time__hour=current_time.hour,
            time__minute=current_time.minute
        )
        
        executed_count = 0
        for schedule in active_schedules:
            try:
                # Check if this schedule should run today
                if _should_run_schedule_today(schedule, now):
                    # Create automation execution
                    automation = AutomationExecution.objects.create(
                        pond=schedule.pond,
                        execution_type=schedule.automation_type,
                        action=_get_action_for_schedule_type(schedule.automation_type),
                        priority='SCHEDULED',
                        status='PENDING',
                        scheduled_at=now,
                        schedule=schedule,
                        parameters={
                            'schedule_id': schedule.id,
                            'feed_amount': schedule.feed_amount,
                            'drain_water_level': schedule.drain_water_level,
                            'target_water_level': schedule.target_water_level,
                        }
                    )
                    
                    # Execute immediately
                    execute_automation.apply_async(args=[automation.id])
                    
                    # Update schedule
                    schedule.record_execution()
                    executed_count += 1
                    
                    logger.info(f"Executed scheduled automation {automation.id} for {schedule.pond.name}")
                    
            except Exception as e:
                logger.error(f"Error executing scheduled automation for {schedule.pond.name}: {e}")
                continue
        
        if executed_count > 0:
            logger.info(f"Executed {executed_count} scheduled automations")
        
        return {
            'success': True,
            'executed_count': executed_count,
            'timestamp': timezone.localtime(now).isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error checking scheduled automations: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_threshold_violations(self):
    """
    Process pending threshold violations and trigger automations.
    This task runs every 30 seconds to check for violations.
    """
    try:
        # Get pending threshold automations
        pending_automations = AutomationExecution.objects.filter(
            execution_type__in=['WATER', 'FEED'],
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at__lte=timezone.now()
        )
        
        processed_count = 0
        for automation in pending_automations:
            try:
                # Execute the automation
                execute_automation.apply_async(args=[automation.id])
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing threshold automation {automation.id}: {e}")
                continue
        
        if processed_count > 0:
            logger.info(f"Processed {processed_count} threshold violations")
        
        return {
            'success': True,
            'processed_count': processed_count,
            'timestamp': timezone.localtime(timezone.now()).isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error processing threshold violations: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def retry_failed_automations(self):
    """
    Retry failed automation executions that can be retried.
    """
    try:
        # Get failed automations that can be retried
        failed_automations = AutomationExecution.objects.filter(
            status='FAILED',
            created_at__gte=timezone.now() - timedelta(hours=1)  # Only recent failures
        )
        
        retry_count = 0
        for automation in failed_automations:
            try:
                # Reset status and retry
                automation.status = 'PENDING'
                automation.save()
                
                # Execute again
                execute_automation.apply_async(args=[automation.id])
                retry_count += 1
                
            except Exception as e:
                logger.error(f"Error retrying automation {automation.id}: {e}")
                continue
        
        if retry_count > 0:
            logger.info(f"Retried {retry_count} failed automations")
        
        return {
            'success': True,
            'retry_count': retry_count,
            'timestamp': timezone.localtime(timezone.now()).isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Error retrying failed automations: {exc}")
        # Retry the task
        raise self.retry(exc=exc)


# Helper functions

def _can_execute_automation(automation: AutomationExecution) -> bool:
    """
    Check if an automation can be executed based on priority conflicts.
    
    Args:
        automation: The automation execution to check
        
    Returns:
        True if automation can execute, False if blocked
    """
    pond = automation.pond
    
    # Check for higher priority executions
    higher_priority_executions = AutomationExecution.objects.filter(
        pond=pond,
        status__in=['PENDING', 'EXECUTING'],
        priority__in=_get_higher_priorities(automation.priority)
    )
    
    if higher_priority_executions.exists():
        return False
    
    # Check for conflicting water operations
    if automation.action in ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 
                           'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                           'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
        conflicting_executions = AutomationExecution.objects.filter(
            pond=pond,
            status__in=['PENDING', 'EXECUTING'],
            action__in=['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 
                       'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                       'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']
        ).exclude(id=automation.id)  # Exclude current automation
        
        if conflicting_executions.exists():
            return False
    
    return True


def _get_higher_priorities(priority: str) -> List[str]:
    """Get priorities higher than the given priority."""
    try:
        priority_index = AUTOMATION_PRIORITIES.index(priority)
        return AUTOMATION_PRIORITIES[:priority_index]
    except ValueError:
        return []


def _should_run_schedule_today(schedule: AutomationSchedule, now: timezone.datetime) -> bool:
    """Check if a schedule should run today based on days of week."""
    if not schedule.days:
        return True
    
    try:
        # Parse days string (e.g., "0,1,3" for Sunday, Monday, Wednesday)
        days = [int(d) for d in schedule.days.split(',')]
        current_weekday = now.weekday()
        # Convert to Sunday=0 format
        current_weekday = (current_weekday + 1) % 7
        return current_weekday in days
    except (ValueError, AttributeError):
        # If days parsing fails, run every day
        return True


def _get_action_for_schedule_type(schedule_type: str) -> str:
    """Get the automation action for a schedule type."""
    if schedule_type == 'FEED':
        return 'FEED'
    elif schedule_type == 'WATER':
        return 'WATER_FLUSH'  # Default to drain
    else:
        return 'LOG'


def _execute_feed_automation(automation: AutomationExecution) -> tuple[bool, str, str]:
    """Execute a feed automation."""
    try:
        feed_amount = automation.parameters.get('feed_amount', 100)  # Default 100g
        
        # Create feed event - use system user if no user available
        user = automation.user or (automation.schedule.user if automation.schedule else None)
        if not user:
            # Use system user for threshold-based automations
            from django.contrib.auth.models import User
            user, _ = User.objects.get_or_create(
                username='system',
                defaults={'email': 'system@futurefishagro.com'}
            )
        
        FeedEvent.objects.create(
            user=user,
            pond=automation.pond,
            amount=feed_amount / 1000  # Convert to kg
        )
        
        # Send feed command to device
        mqtt_service = get_mqtt_bridge_service()
        success = mqtt_service.send_feed_command(
            automation.pond.parent_pair,
            feed_amount,
            pond=automation.pond
        )
        
        if success:
            return True, f"Feed automation executed: {feed_amount}g", ""
        else:
            return False, "Failed to send feed command", "MQTT command failed"
            
    except Exception as e:
        return False, "Feed automation failed", str(e)


def _execute_water_automation(automation: AutomationExecution) -> tuple[bool, str, str]:
    """Execute a water automation."""
    try:
        if automation.action == 'WATER_DRAIN':
            drain_level = automation.parameters.get('drain_water_level', 0)
            
            # Send drain command
            mqtt_service = get_mqtt_bridge_service()
            success = mqtt_service.send_water_command(
                automation.pond.parent_pair,
                'WATER_DRAIN',
                level=drain_level,
                pond=automation.pond
            )
            
            if success:
                return True, f"Water drain automation executed: target {drain_level}%", ""
            else:
                return False, "Failed to send drain command", "MQTT command failed"
                
        elif automation.action == 'WATER_FILL':
            target_level = automation.parameters.get('target_water_level', 80)
            
            # Send fill command
            mqtt_service = get_mqtt_bridge_service()
            success = mqtt_service.send_water_command(
                automation.pond.parent_pair,
                'WATER_FILL',
                level=target_level,
                pond=automation.pond
            )
            
            if success:
                return True, f"Water fill automation executed: target {target_level}%", ""
            else:
                return False, "Failed to send fill command", "MQTT command failed"
                
        elif automation.action == 'WATER_FLUSH':
            drain_level = automation.parameters.get('drain_water_level', 0)
            fill_level = automation.parameters.get('target_water_level', 80)
            
            # Send flush command
            mqtt_service = get_mqtt_bridge_service()
            success = mqtt_service.send_water_command(
                automation.pond.parent_pair,
                'WATER_FLUSH',
                pond=automation.pond,
                drain_level=drain_level,
                fill_level=fill_level
            )
            
            if success:
                return True, f"Water flush automation executed: drain to {drain_level}%, fill to {fill_level}%", ""
            else:
                return False, "Failed to send flush command", "MQTT command failed"
                
        elif automation.action in ['WATER_INLET_OPEN', 'WATER_INLET_CLOSE']:
            # Send inlet valve control command
            mqtt_service = get_mqtt_bridge_service()
            success = mqtt_service.send_water_command(
                automation.pond.parent_pair,
                automation.action,
                pond=automation.pond
            )
            
            if success:
                action_text = "opened" if automation.action == 'WATER_INLET_OPEN' else "closed"
                return True, f"Water inlet valve {action_text}", ""
            else:
                return False, f"Failed to {automation.action.lower().replace('_', ' ')}", "MQTT command failed"
                
        elif automation.action in ['WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
            # Send outlet valve control command
            mqtt_service = get_mqtt_bridge_service()
            success = mqtt_service.send_water_command(
                automation.pond.parent_pair,
                automation.action,
                pond=automation.pond
            )
            
            if success:
                action_text = "opened" if automation.action == 'WATER_OUTLET_OPEN' else "closed"
                return True, f"Water outlet valve {action_text}", ""
            else:
                return False, f"Failed to {automation.action.lower().replace('_', ' ')}", "MQTT command failed"
        
        return False, "Unknown water action", f"Action {automation.action} not supported"
        
    except Exception as e:
        return False, "Water automation failed", str(e)


def _execute_alert_automation(automation: AutomationExecution) -> tuple[bool, str, str]:
    """Execute an alert automation."""
    try:
        # This would integrate with notification system
        # For now, just log the alert
        logger.warning(f"Alert automation triggered for {automation.pond.name}: "
                      f"{automation.parameters.get('message', 'No message')}")
        
        return True, "Alert automation executed", ""
        
    except Exception as e:
        return False, "Alert automation failed", str(e)


def _execute_notification_automation(automation: AutomationExecution) -> tuple[bool, str, str]:
    """Execute a notification automation."""
    try:
        # This would integrate with notification system
        # For now, just log the notification
        logger.info(f"Notification automation triggered for {automation.pond.name}: "
                   f"{automation.parameters.get('message', 'No message')}")
        
        return True, "Notification automation executed", ""
        
    except Exception as e:
        return False, "Notification automation failed", str(e)


def _execute_log_automation(automation: AutomationExecution) -> tuple[bool, str, str]:
    """Execute a log automation."""
    try:
        # Log the automation event
        message = automation.parameters.get('message', f"Automation {automation.execution_type} executed")
        logger.info(f"Log automation for {automation.pond.name}: {message}")
        
        return True, "Log automation executed", ""
        
    except Exception as e:
        return False, "Log automation failed", str(e)
