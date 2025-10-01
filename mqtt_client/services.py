"""
MQTT Client Services for Future Fish Dashboard.

This module provides high-level services for MQTT operations including:
- Device command execution
- Device status monitoring
- Sensor data retrieval
- Threshold management
"""

import logging
from typing import Dict, Any, Optional, List
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from .client import get_mqtt_client, MQTTConfig
from .models import DeviceStatus, MQTTMessage
from ponds.models import PondPair, SensorData, SensorThreshold, Pond
from automation.models import DeviceCommand, AutomationExecution
from core.choices import COMMAND_TYPES, COMMAND_STATUS

logger = logging.getLogger(__name__)


class MQTTService:
    """Service class for MQTT operations"""
    
    def __init__(self):
        self.client = get_mqtt_client()
    
    def send_feed_command(self, pond_pair: PondPair, amount: float, pond: Pond = None, user=None) -> Optional[str]:
        """Send feed command to device"""
        try:
            parameters = {
                'action': 'feed',
                'amount': amount,
                'timestamp': timezone.now().isoformat()
            }
            
            command_id = self.client.send_command(
                pond_pair=pond_pair,
                command_type='FEED',
                parameters=parameters,
                pond=pond
            )
            
            if command_id:
                # Create automation execution if user is provided
                if user:
                    with transaction.atomic():
                        # Use specified pond or fallback to first pond
                        target_pond = pond or pond_pair.ponds.first()
                        if target_pond:
                            automation = AutomationExecution.objects.create(
                                pond=target_pond,
                                execution_type='FEED',
                                action='FEED',
                                priority='MANUAL_COMMAND',
                                status='EXECUTING',
                                user=user,
                                parameters=parameters
                            )
                            
                            # Link command to automation
                            DeviceCommand.objects.filter(command_id=command_id).update(
                                automation_execution=automation
                            )
                
                logger.info(f"Feed command {command_id} sent to {pond_pair.name}")
                return command_id
            else:
                logger.error(f"Failed to send feed command to {pond_pair.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending feed command: {e}")
            return None
    
    def send_water_command(self, pond_pair: PondPair, action: str, level: float = None, pond: Pond = None, user=None, **kwargs) -> Optional[str]:
        """Send water control command to device"""
        try:
            valid_actions = [
                'WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH',
                'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE'
            ]
            
            if action not in valid_actions:
                raise ValueError(f"Invalid water action: {action}")
            
            parameters = {
                'action': action.lower().replace('_', ' '),
                'timestamp': timezone.now().isoformat()
            }
            
            # Handle different water actions with their specific parameters
            if action == 'WATER_DRAIN' and level is not None:
                parameters['drain_level'] = level
            elif action == 'WATER_FILL' and level is not None:
                parameters['target_level'] = level
            elif action == 'WATER_FLUSH':
                # WATER_FLUSH requires both drain and fill levels
                drain_level = kwargs.get('drain_level')
                fill_level = kwargs.get('fill_level')
                if drain_level is not None:
                    parameters['drain_level'] = drain_level
                if fill_level is not None:
                    parameters['fill_level'] = fill_level
            elif action in ['WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                # Valve control actions don't need level parameters
                pass
            elif level is not None:
                # Fallback for other actions that might use level
                parameters['level'] = level
            
            command_id = self.client.send_command(
                pond_pair=pond_pair,
                command_type=action,
                parameters=parameters,
                pond=pond
            )
            
            if command_id:
                # Create automation execution if user is provided
                if user:
                    with transaction.atomic():
                        # Use specified pond or fallback to first pond
                        target_pond = pond or pond_pair.ponds.first()
                        if target_pond:
                            automation = AutomationExecution.objects.create(
                                pond=target_pond,
                                execution_type='WATER',
                                action=action,
                                priority='MANUAL_COMMAND',
                                status='EXECUTING',
                                user=user,
                                parameters=parameters
                            )
                            
                            # Link command to automation
                            DeviceCommand.objects.filter(command_id=command_id).update(
                                automation_execution=automation
                            )
                
                logger.info(f"Water command {command_id} sent to {pond_pair.name}")
                return command_id
            else:
                logger.error(f"Failed to send water command to {pond_pair.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending water command: {e}")
            return None
    
    def send_firmware_update(self, pond_pair: PondPair, firmware_url: str, pond: Pond = None, user=None) -> Optional[str]:
        """Send firmware update command to device"""
        try:
            parameters = {
                'firmware_url': firmware_url,
                'timestamp': timezone.now().isoformat()
            }
            
            command_id = self.client.send_command(
                pond_pair=pond_pair,
                command_type='FIRMWARE_UPDATE',
                parameters=parameters,
                pond=pond
            )
            
            if command_id:
                logger.info(f"Firmware update command {command_id} sent to {pond_pair.name}")
                return command_id
            else:
                logger.error(f"Failed to send firmware update command to {pond_pair.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending firmware update command: {e}")
            return None
    
    def send_restart_command(self, pond_pair: PondPair, pond: Pond = None, user=None) -> Optional[str]:
        """Send device restart command"""
        try:
            parameters = {
                'timestamp': timezone.now().isoformat()
            }
            
            command_id = self.client.send_command(
                pond_pair=pond_pair,
                command_type='RESTART',
                parameters=parameters,
                pond=pond
            )
            
            if command_id:
                logger.info(f"Restart command {command_id} sent to {pond_pair.name}")
                return command_id
            else:
                logger.error(f"Failed to send restart command to {pond_pair.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending restart command: {e}")
            return None
    
    def get_device_status(self, pond_pair: PondPair) -> Optional[Dict[str, Any]]:
        """Get current device status"""
        try:
            device_status = DeviceStatus.objects.get(pond_pair=pond_pair)
            
            return {
                'status': device_status.status,
                'last_seen': device_status.last_seen,
                'is_online': device_status.is_online(),
                'firmware_version': device_status.firmware_version,
                'hardware_version': device_status.hardware_version,
                'device_name': device_status.device_name,
                'ip_address': device_status.ip_address,
                'wifi_ssid': device_status.wifi_ssid,
                'wifi_signal_strength': device_status.wifi_signal_strength,
                'free_heap': device_status.free_heap,
                'cpu_frequency': device_status.cpu_frequency,
                'error_count': device_status.error_count,
                'last_error': device_status.last_error,
                'last_error_at': device_status.last_error_at,
                'uptime_percentage_24h': device_status.get_uptime_percentage(24)
            }
            
        except DeviceStatus.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return None
    
    def get_device_commands(self, pond_pair: PondPair, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent device commands for a pond pair"""
        try:
            # Get the first pond from the pair
            pond = pond_pair.ponds.first()
            if not pond:
                return []
            
            commands = DeviceCommand.objects.filter(
                pond=pond
            ).order_by('-created_at')[:limit]
            
            return [
                {
                    'command_id': str(cmd.command_id),
                    'command_type': cmd.command_type,
                    'status': cmd.status,
                    'parameters': cmd.parameters,
                    'sent_at': cmd.sent_at,
                    'acknowledged_at': cmd.acknowledged_at,
                    'completed_at': cmd.completed_at,
                    'success': cmd.success,
                    'result_message': cmd.result_message,
                    'error_code': cmd.error_code,
                    'error_details': cmd.error_details,
                    'retry_count': cmd.retry_count,
                    'created_at': cmd.created_at,
                    'user': cmd.user.username if cmd.user else None
                }
                for cmd in commands
            ]
            
        except Exception as e:
            logger.error(f"Error getting device commands: {e}")
            return []
    
    def get_mqtt_messages(self, pond_pair: PondPair, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent MQTT messages for a pond pair"""
        try:
            messages = MQTTMessage.objects.filter(
                pond_pair=pond_pair
            ).order_by('-created_at')[:limit]
            
            return [
                {
                    'message_id': str(msg.message_id),
                    'topic': msg.topic,
                    'message_type': msg.message_type,
                    'payload': msg.payload,
                    'payload_size': msg.payload_size,
                    'success': msg.success,
                    'error_message': msg.error_message,
                    'sent_at': msg.sent_at,
                    'received_at': msg.received_at,
                    'processing_time_ms': msg.get_processing_time_ms(),
                    'correlation_id': str(msg.correlation_id) if msg.correlation_id else None,
                    'created_at': msg.created_at
                }
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Error getting MQTT messages: {e}")
            return []
    
    def get_online_devices(self) -> List[Dict[str, Any]]:
        """Get list of all online devices"""
        try:
            online_devices = []
            
            for device_id, last_heartbeat in self.client.device_heartbeats.items():
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                    device_status = self.get_device_status(pond_pair)
                    
                    if device_status and device_status['is_online']:
                        online_devices.append({
                            'device_id': device_id,
                            'pond_pair_name': pond_pair.name,
                            'pond_pair_id': pond_pair.id,
                            'last_heartbeat': last_heartbeat,
                            'status': device_status
                        })
                        
                except PondPair.DoesNotExist:
                    logger.warning(f"Pond pair not found for device {device_id}")
                    continue
            
            return online_devices
            
        except Exception as e:
            logger.error(f"Error getting online devices: {e}")
            return []
    
    def get_pending_commands(self) -> List[Dict[str, Any]]:
        """Get list of all pending commands"""
        try:
            pending_commands = []
            
            for command_id, command in self.client.pending_commands.items():
                try:
                    # Get the pond from the command
                    pond = command.pond
                    pond_pair = pond.parent_pair
                    pending_commands.append({
                        'command_id': command_id,
                        'pond_pair_name': pond_pair.name,
                        'pond_pair_id': pond_pair.id,
                        'command_type': command.command_type,
                        'parameters': command.parameters,
                        'sent_at': command.sent_at,
                        'timeout_seconds': command.timeout_seconds,
                        'retry_count': command.retry_count,
                        'created_at': command.created_at
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing pending command {command_id}: {e}")
                    continue
            
            return pending_commands
            
        except Exception as e:
            logger.error(f"Error getting pending commands: {e}")
            return []
    
    def check_device_connectivity(self, pond_pair: PondPair) -> Dict[str, Any]:
        """Check device connectivity and health"""
        try:
            device_status = self.get_device_status(pond_pair)
            if not device_status:
                return {
                    'is_online': False,
                    'status': 'UNKNOWN',
                    'last_seen': None,
                    'connectivity_score': 0,
                    'issues': ['Device status not found']
                }
            
            issues = []
            connectivity_score = 100
            
            # Check if device is online
            if not device_status['is_online']:
                issues.append('Device offline')
                connectivity_score -= 50
            
            # Check last seen time
            if device_status['last_seen']:
                time_since_last_seen = timezone.now() - device_status['last_seen']
                if time_since_last_seen.total_seconds() > 300:  # 5 minutes
                    issues.append('No recent heartbeat')
                    connectivity_score -= 20
            
            # Check error count
            if device_status['error_count'] > 0:
                issues.append(f'Device has {device_status["error_count"]} errors')
                connectivity_score -= 10
            
            # Check WiFi signal strength
            if device_status['wifi_signal_strength']:
                if device_status['wifi_signal_strength'] < -70:
                    issues.append('Weak WiFi signal')
                    connectivity_score -= 15
            
            # Check free heap memory
            if device_status['free_heap']:
                if device_status['free_heap'] < 10000:  # Less than 10KB
                    issues.append('Low memory')
                    connectivity_score -= 10
            
            return {
                'is_online': device_status['is_online'],
                'status': device_status['status'],
                'last_seen': device_status['last_seen'],
                'connectivity_score': max(0, connectivity_score),
                'issues': issues,
                'uptime_percentage_24h': device_status['uptime_percentage_24h']
            }
            
        except Exception as e:
            logger.error(f"Error checking device connectivity: {e}")
            return {
                'is_online': False,
                'status': 'ERROR',
                'last_seen': None,
                'connectivity_score': 0,
                'issues': [f'Error checking connectivity: {str(e)}']
            }
    
    def send_threshold_command(self, pond_pair: PondPair, parameter: str, 
                              upper_threshold: float, lower_threshold: float, 
                              pond: Pond = None, user=None, threshold_id: int = None, **threshold_kwargs) -> Optional[str]:
        """Send threshold configuration command to device"""
        try:
            parameters = {
                'parameter': parameter,
                'upper': upper_threshold,
                'lower': lower_threshold,
                'automation': threshold_kwargs.get('automation_action', 'ALERT'),
                'timestamp': timezone.now().isoformat()
            }
            
            # Include threshold_id for updates
            if threshold_id:
                parameters['threshold_id'] = threshold_id
            
            command_id = self.client.send_command(
                pond_pair=pond_pair,
                command_type='SET_THRESHOLD',
                parameters=parameters,
                pond=pond
            )
            
            if command_id:
                logger.info(f"Sent threshold command for {parameter} to device {pond_pair.device_id}: "
                          f"{lower_threshold}-{upper_threshold}")
                
                # Create automation execution if user is provided
                if user and pond:
                    from automation.models import AutomationExecution
                    AutomationExecution.objects.create(
                        pond=pond,
                        execution_type='WATER' if 'water' in parameter else 'FEED',
                        action='SET_THRESHOLD',
                        priority='MANUAL_COMMAND',
                        status='PENDING',
                        scheduled_at=timezone.now(),
                        parameters=parameters,
                        user=user
                    )
            
            return command_id
            
        except Exception as e:
            logger.error(f"Error sending threshold command for {parameter}: {e}")
            return None

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        try:
            total_devices = PondPair.objects.count()
            online_devices = len(self.client.device_heartbeats)
            pending_commands = len(self.client.pending_commands)
            
            # Calculate connectivity percentage
            connectivity_percentage = (online_devices / total_devices * 100) if total_devices > 0 else 0
            
            # Get recent errors
            recent_errors = DeviceStatus.objects.filter(
                error_count__gt=0,
                last_error_at__gte=timezone.now() - timezone.timedelta(hours=24)
            ).count()
            
            # Get recent MQTT messages
            recent_messages = MQTTMessage.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            
            return {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': total_devices - online_devices,
                'connectivity_percentage': round(connectivity_percentage, 2),
                'pending_commands': pending_commands,
                'recent_errors': recent_errors,
                'recent_messages': recent_messages,
                'mqtt_client_status': 'Connected' if self.client.is_connected else 'Disconnected',
                'last_updated': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting system health summary: {e}")
            return {
                'error': str(e),
                'last_updated': timezone.now()
            }


# Global service instance
mqtt_service = MQTTService()
