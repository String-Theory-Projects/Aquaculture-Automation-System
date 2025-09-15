"""
Automation service layer for Future Fish Dashboard.

This module provides high-level services for:
- Threshold management and monitoring
- Automation execution and scheduling
- Priority conflict resolution
- System health monitoring
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.conf import settings
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


class AutomationService:
    """Service class for automation operations"""
    
    def __init__(self):
        self.mqtt_service = get_mqtt_bridge_service()
    
    def create_threshold(self, pond: Pond, parameter: str, upper_threshold: float, 
                        lower_threshold: float, automation_action: str, **kwargs) -> SensorThreshold:
        """
        Create a new sensor threshold for automation.
        
        Args:
            pond: The pond to create threshold for
            parameter: Sensor parameter name
            upper_threshold: Upper threshold value
            lower_threshold: Lower threshold value
            automation_action: Action to take when threshold is violated
            **kwargs: Additional threshold settings
            
        Returns:
            Created SensorThreshold instance
        """
        try:
            with transaction.atomic():
                threshold = SensorThreshold.objects.create(
                    pond=pond,
                    parameter=parameter,
                    upper_threshold=upper_threshold,
                    lower_threshold=lower_threshold,
                    automation_action=automation_action,
                    **kwargs
                )
                
                logger.info(f"Created threshold for {parameter} in {pond.name}: "
                          f"{lower_threshold}-{upper_threshold}")
                
                return threshold
                
        except Exception as e:
            logger.error(f"Error creating threshold for {pond.name}: {e}")
            raise
    
    def update_threshold(self, threshold_id: int, **kwargs) -> SensorThreshold:
        """
        Update an existing sensor threshold.
        
        Args:
            threshold_id: ID of threshold to update
            **kwargs: Fields to update
            
        Returns:
            Updated SensorThreshold instance
        """
        try:
            with transaction.atomic():
                threshold = SensorThreshold.objects.get(id=threshold_id)
                
                for field, value in kwargs.items():
                    if hasattr(threshold, field):
                        setattr(threshold, field, value)
                
                threshold.full_clean()
                threshold.save()
                
                logger.info(f"Updated threshold {threshold_id} for {threshold.pond.name}")
                
                return threshold
                
        except SensorThreshold.DoesNotExist:
            logger.error(f"Threshold {threshold_id} not found")
            raise
        except Exception as e:
            logger.error(f"Error updating threshold {threshold_id}: {e}")
            raise
    
    def delete_threshold(self, threshold_id: int) -> bool:
        """
        Delete a sensor threshold.
        
        Args:
            threshold_id: ID of threshold to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            threshold = SensorThreshold.objects.get(id=threshold_id)
            pond_name = threshold.pond.name
            threshold.delete()
            
            logger.info(f"Deleted threshold {threshold_id} for {pond_name}")
            return True
            
        except SensorThreshold.DoesNotExist:
            logger.error(f"Threshold {threshold_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting threshold {threshold_id}: {e}")
            return False
    
    def get_active_thresholds(self, pond: Pond) -> List[SensorThreshold]:
        """
        Get all active thresholds for a pond.
        
        Args:
            pond: The pond to get thresholds for
            
        Returns:
            List of active thresholds
        """
        return SensorThreshold.objects.filter(
            pond=pond,
            is_active=True
        ).order_by('priority', 'parameter')
    
    def check_threshold_violations(self, pond: Pond, parameter: str, value: float) -> List[Dict[str, Any]]:
        """
        Check if a sensor value violates any thresholds.
        
        Args:
            pond: The pond to check
            parameter: Sensor parameter name
            value: Current sensor value
            
        Returns:
            List of violation details
        """
        violations = []
        
        thresholds = self.get_active_thresholds(pond).filter(parameter=parameter)
        
        for threshold in thresholds:
            is_violated = (
                value > threshold.upper_threshold or
                value < threshold.lower_threshold
            )
            
            if is_violated:
                violations.append({
                    'threshold_id': threshold.id,
                    'parameter': parameter,
                    'current_value': value,
                    'upper_threshold': threshold.upper_threshold,
                    'lower_threshold': threshold.lower_threshold,
                    'automation_action': threshold.automation_action,
                    'priority': threshold.priority,
                    'alert_level': threshold.alert_level,
                })
        
        return violations
    
    def create_automation_schedule(self, pond: Pond, automation_type: str, action: str, time: str,
                                 days: str, **kwargs) -> AutomationSchedule:
        """
        Create a new automation schedule.
        
        Args:
            pond: The pond to schedule automation for
            automation_type: Type of automation (FEED, WATER)
            action: Specific action to perform (FEED, WATER_DRAIN, etc.)
            time: Time to run (HH:MM format)
            days: Days of week (comma-separated, e.g., "0,1,3")
            **kwargs: Additional schedule settings
            
        Returns:
            Created AutomationSchedule instance
        """
        try:
            with transaction.atomic():
                schedule = AutomationSchedule.objects.create(
                    pond=pond,
                    automation_type=automation_type,
                    action=action,
                    time=time,
                    days=days,
                    **kwargs
                )
                
                # Calculate next execution time
                schedule.update_next_execution()
                
                logger.info(f"Created {automation_type} schedule for {pond.name} at {time}")
                
                return schedule
                
        except Exception as e:
            logger.error(f"Error creating schedule for {pond.name}: {e}")
            raise
    
    def update_automation_schedule(self, schedule_id: int, **kwargs) -> AutomationSchedule:
        """
        Update an existing automation schedule.
        
        Args:
            schedule_id: ID of schedule to update
            **kwargs: Fields to update
            
        Returns:
            Updated AutomationSchedule instance
        """
        try:
            with transaction.atomic():
                schedule = AutomationSchedule.objects.get(id=schedule_id)
                
                for field, value in kwargs.items():
                    if hasattr(schedule, field):
                        setattr(schedule, field, value)
                
                schedule.full_clean()
                schedule.save()
                
                # Recalculate next execution time
                schedule.update_next_execution()
                
                logger.info(f"Updated schedule {schedule_id} for {schedule.pond.name}")
                
                return schedule
                
        except AutomationSchedule.DoesNotExist:
            logger.error(f"Schedule {schedule_id} not found")
            raise
        except Exception as e:
            logger.error(f"Error updating schedule {schedule_id}: {e}")
            raise
    
    def delete_automation_schedule(self, schedule_id: int) -> bool:
        """
        Delete an automation schedule.
        
        Args:
            schedule_id: ID of schedule to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            schedule = AutomationSchedule.objects.get(id=schedule_id)
            pond_name = schedule.pond.name
            schedule.delete()
            
            logger.info(f"Deleted schedule {schedule_id} for {pond_name}")
            return True
            
        except AutomationSchedule.DoesNotExist:
            logger.error(f"Schedule {schedule_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id}: {e}")
            return False
    
    def get_pending_automations(self, pond: Pond = None) -> List[AutomationExecution]:
        """
        Get all pending automation executions.
        
        Args:
            pond: Optional pond to filter by
            
        Returns:
            List of pending automations
        """
        queryset = AutomationExecution.objects.filter(
            status='PENDING',
            scheduled_at__lte=timezone.now()
        )
        
        if pond:
            queryset = queryset.filter(pond=pond)
        
        return queryset.order_by('priority', 'scheduled_at')
    
    def get_automation_history(self, pond: Pond = None, limit: int = 100) -> List[AutomationExecution]:
        """
        Get automation execution history.
        
        Args:
            pond: Optional pond to filter by
            limit: Maximum number of records to return
            
        Returns:
            List of automation executions
        """
        queryset = AutomationExecution.objects.filter(
            status__in=['COMPLETED', 'FAILED', 'CANCELLED']
        )
        
        if pond:
            queryset = queryset.filter(pond=pond)
        
        return queryset.order_by('-completed_at')[:limit]
    
    def execute_manual_automation(self, pond: Pond, action: str, parameters: Dict[str, Any],
                                user=None) -> AutomationExecution:
        """
        Execute a manual automation action.
        
        Args:
            pond: The pond to execute automation for
            action: Automation action to perform
            parameters: Action parameters
            user: User executing the automation
            
        Returns:
            Created AutomationExecution instance
        """
        try:
            with transaction.atomic():
                # Create automation execution with highest priority
                automation = AutomationExecution.objects.create(
                    pond=pond,
                    execution_type='WATER' if 'water' in action.lower() else 'FEED',
                    action=action.upper(),
                    priority='MANUAL_COMMAND',
                    status='EXECUTING',  # Start executing immediately
                    scheduled_at=timezone.now(),
                    started_at=timezone.now(),  # Mark as started
                    user=user,
                    parameters=parameters
                )
                
                logger.info(f"Created manual automation {automation.id} for {pond.name}: {action}")
                
                # Send MQTT command based on action type
                command_id = None
                try:
                    if action.upper() == 'FEED':
                        feed_amount = parameters.get('feed_amount', 100)
                        command_id = self.mqtt_service.send_feed_command(
                            pond_pair=pond.parent_pair,
                            amount=feed_amount,
                            pond=pond,  # Pass specific pond for position
                            user=user
                        )
                    elif action.upper() in ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 
                               'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                               'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                        # Handle water control commands
                        if action.upper() == 'WATER_DRAIN':
                            drain_level = parameters.get('drain_water_level', 
                                                       getattr(settings, 'AUTOMATION_MIN_WATER_LEVEL', 20))
                            command_id = self.mqtt_service.send_water_command(
                                pond_pair=pond.parent_pair,
                                action='WATER_DRAIN',
                                level=drain_level,
                                pond=pond,
                                user=user
                            )
                        elif action.upper() == 'WATER_FILL':
                            target_level = parameters.get('target_water_level', 
                                                        getattr(settings, 'AUTOMATION_DEFAULT_WATER_LEVEL', 80))
                            command_id = self.mqtt_service.send_water_command(
                                pond_pair=pond.parent_pair,
                                action='WATER_FILL',
                                level=target_level,
                                pond=pond,
                                user=user
                            )
                        elif action.upper() == 'WATER_FLUSH':
                            drain_level = parameters.get('drain_water_level', 
                                                       getattr(settings, 'AUTOMATION_MIN_WATER_LEVEL', 20))
                            fill_level = parameters.get('target_water_level', 
                                                      getattr(settings, 'AUTOMATION_DEFAULT_WATER_LEVEL', 80))
                            command_id = self.mqtt_service.send_water_command(
                                pond_pair=pond.parent_pair,
                                action='WATER_FLUSH',
                                pond=pond,
                                user=user,
                                drain_level=drain_level,
                                fill_level=fill_level
                            )
                        elif action.upper() in ['WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 
                                               'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                            command_id = self.mqtt_service.send_water_command(
                                pond_pair=pond.parent_pair,
                                action=action.upper(),
                                pond=pond,
                                user=user
                            )
                    elif action.upper() == 'FIRMWARE_UPDATE':
                        firmware_url = parameters.get('firmware_url')
                        command_id = self.mqtt_service.send_firmware_update(
                            pond_pair=pond.parent_pair,
                            firmware_url=firmware_url,
                            pond=pond,  # Pass specific pond for position
                            user=user
                        )
                    else:
                        logger.warning(f"Unknown action type: {action}")
                        automation.complete_execution(False, f"Unknown action type: {action}")
                        return automation
                    
                    if command_id:
                        logger.info(f"MQTT command {command_id} sent for automation {automation.id}")
                        # Update automation with command ID
                        automation.parameters['mqtt_command_id'] = command_id
                        automation.save()
                        
                        # Link the device command to this automation execution
                        try:
                            from automation.models import DeviceCommand
                            device_command = DeviceCommand.objects.get(command_id=command_id)
                            device_command.automation_execution = automation
                            device_command.save()
                            logger.info(f"Linked device command {command_id} to automation {automation.id}")
                        except DeviceCommand.DoesNotExist:
                            logger.warning(f"Device command {command_id} not found for linking")
                        
                        # Check if the MQTT service created a new automation execution
                        # If so, we should use that one and delete this duplicate
                        try:
                            mqtt_automation = AutomationExecution.objects.get(
                                parameters__mqtt_command_id=command_id
                            )
                            if mqtt_automation.id != automation.id:
                                logger.info(f"MQTT service created automation {mqtt_automation.id}, using that instead of {automation.id}")
                                automation.delete()
                                return mqtt_automation
                        except AutomationExecution.DoesNotExist:
                            # No automation created by MQTT service, continue with this one
                            pass
                    else:
                        logger.error(f"Failed to send MQTT command for automation {automation.id}")
                        # Immediately mark automation as failed since command couldn't be sent
                        automation.complete_execution(False, "Failed to send MQTT command", "MQTT service returned no command ID")
                        
                except Exception as e:
                    logger.error(f"Error sending MQTT command for automation {automation.id}: {e}")
                    # Immediately mark automation as failed due to exception
                    automation.complete_execution(False, f"MQTT command error: {str(e)}", f"Exception: {type(e).__name__}: {str(e)}")
                
                return automation
                
        except Exception as e:
            logger.error(f"Error creating manual automation for {pond.name}: {e}")
            raise
    
    def get_automation_status(self, pond: Pond) -> Dict[str, Any]:
        """
        Get comprehensive automation status for a pond.
        
        Args:
            pond: The pond to get status for
            
        Returns:
            Dictionary with automation status information
        """
        try:
            # Get active thresholds
            active_thresholds = self.get_active_thresholds(pond)
            
            # Get pending automations
            pending_automations = self.get_pending_automations(pond)
            
            # Get recent automation history
            recent_history = self.get_automation_history(pond, limit=10)
            
            # Get active schedules
            active_schedules = AutomationSchedule.objects.filter(
                pond=pond,
                is_active=True
            )
            
            # Calculate statistics
            total_automations = AutomationExecution.objects.filter(pond=pond).count()
            successful_automations = AutomationExecution.objects.filter(
                pond=pond,
                status='COMPLETED',
                success=True
            ).count()
            
            success_rate = (successful_automations / total_automations * 100) if total_automations > 0 else 0
            
            return {
                'pond_id': pond.id,
                'pond_name': pond.name,
                'active_thresholds_count': active_thresholds.count(),
                'pending_automations_count': pending_automations.count(),
                'active_schedules_count': active_schedules.count(),
                'total_automations': total_automations,
                'successful_automations': successful_automations,
                'success_rate': round(success_rate, 2),
                'last_automation': recent_history[0].completed_at if recent_history else None,
                'status': 'ACTIVE' if active_thresholds.exists() or active_schedules.exists() else 'INACTIVE'
            }
            
        except Exception as e:
            logger.error(f"Error getting automation status for {pond.name}: {e}")
            return {
                'pond_id': pond.id,
                'pond_name': pond.name,
                'error': str(e)
            }
    
    def resolve_automation_conflicts(self, pond: Pond) -> Dict[str, Any]:
        """
        Resolve automation conflicts for a pond.
        
        Args:
            pond: The pond to resolve conflicts for
            
        Returns:
            Dictionary with conflict resolution results
        """
        try:
            conflicts = []
            resolved = 0
            
            # Get all pending and executing automations
            active_automations = AutomationExecution.objects.filter(
                pond=pond,
                status__in=['PENDING', 'EXECUTING']
            ).order_by('priority', 'created_at')
            
            # Check for conflicts
            for automation in active_automations:
                if not self._can_execute_automation(automation):
                    conflicts.append({
                        'automation_id': automation.id,
                        'action': automation.action,
                        'priority': automation.priority,
                        'conflict_reason': 'Blocked by higher priority execution'
                    })
                    
                    # Reschedule for later
                    automation.scheduled_at = timezone.now() + timedelta(minutes=5)
                    automation.save()
                    resolved += 1
            
            return {
                'pond_id': pond.id,
                'pond_name': pond.name,
                'conflicts_found': len(conflicts),
                'conflicts_resolved': resolved,
                'conflict_details': conflicts
            }
            
        except Exception as e:
            logger.error(f"Error resolving conflicts for {pond.name}: {e}")
            return {
                'pond_id': pond.id,
                'pond_name': pond.name,
                'error': str(e)
            }
    
    def _can_execute_automation(self, automation: AutomationExecution) -> bool:
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
            priority__in=self._get_higher_priorities(automation.priority)
        )
        
        if higher_priority_executions.exists():
            return False
        
        # Check for water-related automations
        if automation.action in ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 
                               'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                               'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
            return 'WATER'  # Default to water
        
        return True
    
    def _get_higher_priorities(self, priority: str) -> List[str]:
        """Get priorities higher than the given priority."""
        try:
            priority_index = AUTOMATION_PRIORITIES.index(priority)
            return AUTOMATION_PRIORITIES[:priority_index]
        except ValueError:
            return []
