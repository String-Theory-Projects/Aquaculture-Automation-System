"""
MQTT Bridge Service for Future Fish Dashboard.

This service replaces the direct MQTT client calls with Redis pub/sub communication.
It provides the same interface as the old MQTTService but uses the bridge pattern.
"""

import json
import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from django.db import transaction

from .bridge import publish_to_mqtt
from .models import MQTTMessage
from ponds.models import PondPair, Pond
from automation.models import DeviceCommand
from core.constants import MQTT_TOPICS
from core.choices import COMMAND_TYPES

logger = logging.getLogger(__name__)


class MQTTBridgeService:
    """
    MQTT service that uses Redis bridge for communication.
    
    This service provides the same interface as the old MQTTService but
    communicates with the MQTT broker through Redis channels instead of
    direct client calls.
    """
    
    def __init__(self):
        self.service_name = "MQTTBridgeService"
    
    def send_command(self, pond_pair: PondPair, command_type: str, 
                    parameters: Dict[str, Any] = None, pond: Pond = None) -> Optional[str]:
        """
        Send command to device using Redis bridge.
        
        Args:
            pond_pair: Pond pair containing the device
            command_type: Type of command to send
            parameters: Command parameters
            pond: Specific pond to target (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        try:
            # Create device command record
            if not pond:
                # Fallback to first pond if none specified
                pond = pond_pair.ponds.first()
            
            if not pond:
                logger.error(f"No ponds found for pond pair {pond_pair.id}")
                return None
            
            # Filter out non-serializable objects from parameters
            clean_parameters = self._clean_parameters_for_json(parameters or {})
                
            command = DeviceCommand.objects.create(
                pond=pond,
                command_type=command_type,
                status='PENDING',
                parameters=clean_parameters,
                timeout_seconds=10,
                max_retries=3
            )
            
            # Get pond position (1 or 2) for the device
            pond_position = pond.position
            
            # Prepare command message with pond position
            # Use simplified format for large commands to reduce message size
            if command_type in ['WATER_FLUSH', 'FIRMWARE_UPDATE', 'SET_THRESHOLD']:
                message = self._create_simplified_message(command.command_id.hex, command_type, pond_position, clean_parameters)
            else:
                message = {
                    'command_id': command.command_id.hex,
                    'command_type': command_type,
                    'pond_position': pond_position,  # Add pond position for device recognition
                    'parameters': clean_parameters,
                    'timestamp': timezone.now().isoformat()
                }
            
            # Publish command to Redis channel
            topic = MQTT_TOPICS['COMMANDS'].format(device_id=pond_pair.device_id)
            success = publish_to_mqtt(
                command_id=command.command_id.hex,
                device_id=pond_pair.device_id,
                topic=topic,
                payload=message,
                qos=2
            )
            
            if success:
                # Log MQTT message
                MQTTMessage.objects.create(
                    pond_pair=pond_pair,
                    topic=topic,
                    message_type='PUBLISH',
                    payload=message,
                    payload_size=len(json.dumps(message)),
                    success=True,
                    sent_at=timezone.now(),
                    correlation_id=command.command_id.hex
                )
                
                logger.info(f"Command {command.command_id} queued via Redis bridge for device {pond_pair.device_id}")
                return command.command_id.hex
            else:
                # Mark command as failed
                command.complete_command(False, "Failed to publish to Redis bridge")
                logger.error(f"Failed to publish command {command.command_id} to Redis bridge")
                return None
                
        except Exception as e:
            logger.error(f"Error sending command via bridge: {e}")
            return None
    
    def _create_simplified_message(self, command_id: str, command_type: str, pond_position: int, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create simplified message format for large commands to reduce message size.
        
        Args:
            command_id: Command ID
            command_type: Type of command
            pond_position: Pond position (1 or 2)
            parameters: Command parameters
            
        Returns:
            Simplified message dictionary
        """
        if command_type == 'WATER_FLUSH':
            return {
                'id': command_id,
                'type': 'FLUSH',
                'pos': pond_position,
                'd': parameters.get('drain_level', 0.0),  # drain level
                'f': parameters.get('fill_level', 80.0)   # fill level
            }
        elif command_type == 'FIRMWARE_UPDATE':
            return {
                'id': command_id,
                'type': 'FW',
                'pos': pond_position,
                'url': parameters.get('firmware_url', '')
            }
        elif command_type == 'SET_THRESHOLD':
            # Map parameter names to short versions
            param_mapping = {
                'temperature': 'temp',
                'dissolved_oxygen': 'do',
                'ph': 'ph'
            }
            param = parameters.get('parameter', '')
            short_param = param_mapping.get(param, param)
            
            return {
                'id': command_id,
                'type': 'THRESH',
                'pos': pond_position,
                'p': short_param,  # parameter
                'u': parameters.get('upper_threshold', 0.0),  # upper threshold
                'l': parameters.get('lower_threshold', 0.0)   # lower threshold
            }
        else:
            # Fallback to standard format
            return {
                'command_id': command_id,
                'command_type': command_type,
                'pond_position': pond_position,
                'parameters': parameters,
                'timestamp': timezone.now().isoformat()
            }

    def _clean_parameters_for_json(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean parameters dictionary to ensure JSON serialization.
        
        Args:
            parameters: Original parameters dictionary
            
        Returns:
            Cleaned parameters dictionary with only serializable values
        """
        if not parameters:
            return {}
        
        clean_params = {}
        for key, value in parameters.items():
            try:
                # Test if value is JSON serializable
                json.dumps(value)
                clean_params[key] = value
            except (TypeError, ValueError):
                # Skip non-serializable values, but log them
                if hasattr(value, '__class__'):
                    logger.debug(f"Skipping non-serializable parameter {key}: {value.__class__.__name__}")
                else:
                    logger.debug(f"Skipping non-serializable parameter {key}: {type(value)}")
        
        return clean_params
    
    def send_feed_command(self, pond_pair: PondPair, amount: int, pond: Pond = None, user=None) -> Optional[str]:
        """
        Send feed command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            amount: Amount of feed to dispense
            pond: Specific pond to target (optional)
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'amount': amount,
            'unit': 'grams'
        }
        
        # # Add user info if provided (but filter out non-serializable parts)
        # if user:
        #     parameters['user_id'] = user.id
        #     parameters['username'] = user.username
        
        return self.send_command(pond_pair, 'FEED', parameters, pond)
    
    def send_water_level_command(self, pond_pair: PondPair, target_level: float, 
                               pond: Pond = None, user=None) -> Optional[str]:
        """
        Send water level adjustment command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            target_level: Target water level
            pond: Specific pond to target (optional)
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'target_level': target_level,
            'unit': 'cm'
        }
        
        # Add user info if provided (but filter out non-serializable parts)
        # if user:
        #     parameters['user_id'] = user.id
        #     parameters['username'] = user.username
        
        return self.send_command(pond_pair, 'WATER_LEVEL', parameters, pond)
    
    def send_water_command(self, pond_pair: PondPair, action: str, level: float = None, 
                          pond: Pond = None, **kwargs) -> Optional[str]:
        """
        Send water control command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            action: Water action (WATER_DRAIN, WATER_FILL, WATER_FLUSH, etc.)
            level: Water level for the action
            pond: Specific pond to target (optional)
            **kwargs: Additional parameters
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'action': action,
            'level': level,
            **kwargs
        }
        
        return self.send_command(pond_pair, action, parameters, pond)
    
    def send_emergency_stop(self, pond_pair: PondPair, pond: Pond = None, user=None) -> Optional[str]:
        """
        Send emergency stop command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            pond: Specific pond to target (optional)
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'reason': 'Emergency stop requested',
            'timestamp': timezone.now().isoformat()
        }
        
        # Add user info if provided (but filter out non-serializable parts)
        # if user:
        #     parameters['user_id'] = user.id
        #     parameters['username'] = user.username
        
        return self.send_command(pond_pair, 'EMERGENCY_STOP', parameters, pond)
    
    def send_device_reboot(self, pond_pair: PondPair, user=None) -> Optional[str]:
        """
        Send device reboot command.
        
        Args:
            pond_pair: Pond pair containing the device
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        # parameters = {
        #     'reason': 'Device reboot requested',
        #     'timestamp': timezone.now().isoformat()
        # }
        
        # Add user info if provided (but filter out non-serializable parts)
        # if user:
        #     parameters['user_id'] = user.id
        #     parameters['username'] = user.username
        
        # return self.send_command(pond_pair, 'REBOOT', parameters)
        return self.send_command(pond_pair, 'REBOOT')
    
    def send_calibration_command(self, pond_pair: PondPair, sensor_type: str, 
                               calibration_value: float, pond: Pond = None, user=None) -> Optional[str]:
        """
        Send sensor calibration command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            sensor_type: Type of sensor to calibrate
            calibration_value: Calibration value
            pond: Specific pond to target (optional)
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'sensor_type': sensor_type,
            'calibration_value': calibration_value,
            'timestamp': timezone.now().isoformat()
        }
        
        # Add user info if provided (but filter out non-serializable parts)
        if user:
            parameters['user_id'] = user.id
            parameters['username'] = user.username
        
        return self.send_command(pond_pair, 'CALIBRATE', parameters, pond)
    
    def send_threshold_command(self, pond_pair: PondPair, parameter: str, 
                             upper_threshold: float, lower_threshold: float, 
                             pond: Pond = None, user=None) -> Optional[str]:
        """
        Send threshold configuration command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            parameter: Sensor parameter name (temperature, water_level, etc.)
            upper_threshold: Upper threshold value
            lower_threshold: Lower threshold value
            pond: Specific pond to target (optional)
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'parameter': parameter,
            'upper_threshold': upper_threshold,
            'lower_threshold': lower_threshold
        }
        
        # Add user info if provided (but filter out non-serializable parts)
        # if user:
        #     parameters['user_id'] = user.id
        #     parameters['username'] = user.username
        
        return self.send_command(pond_pair, 'SET_THRESHOLD', parameters, pond)
    
    def send_firmware_update(self, pond_pair: PondPair, firmware_url: str, pond: Pond = None, user=None) -> Optional[str]:
        """
        Send firmware update command to device.
        
        Args:
            pond_pair: Pond pair containing the device
            firmware_url: URL to download firmware from
            pond: Specific pond to target (optional)
            user: User executing the command (optional)
            
        Returns:
            Command ID if successful, None otherwise
        """
        parameters = {
            'firmware_url': firmware_url,
            'timestamp': timezone.now().isoformat()
        }
        
        # Add user info if provided (but filter out non-serializable parts)
        if user:
            parameters['user_id'] = user.id
            parameters['username'] = user.username
        
        return self.send_command(pond_pair, 'FIRMWARE_UPDATE', parameters, pond)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get the status of the MQTT bridge service"""
        try:
            from .bridge import get_redis_status
            
            redis_status = get_redis_status()
            
            return {
                'service_name': self.service_name,
                'status': 'active',
                'redis_status': redis_status,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'service_name': self.service_name,
                'status': 'error',
                'error': str(e),
                'timestamp': timezone.now().isoformat()
            }
    
    def test_connection(self) -> bool:
        """Test the Redis bridge connection"""
        try:
            from .bridge import get_redis_status
            
            status = get_redis_status()
            return status['status'] == 'connected'
            
        except Exception as e:
            logger.error(f"Error testing bridge connection: {e}")
            return False


# Global service instance
_mqtt_bridge_service = None


def get_mqtt_bridge_service() -> MQTTBridgeService:
    """Get or create global MQTT bridge service instance"""
    global _mqtt_bridge_service
    if _mqtt_bridge_service is None:
        _mqtt_bridge_service = MQTTBridgeService()
    return _mqtt_bridge_service
