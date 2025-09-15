"""
MQTT Message Consumer for Future Fish Dashboard.

This module handles incoming MQTT messages from the Redis channel and processes them
to update device commands, sensor data, and trigger automations.
"""

import json
import logging
import uuid
from typing import Dict, Any
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import MQTTMessage
from ponds.models import PondPair, SensorData, SensorThreshold, Alert
from automation.models import DeviceCommand, AutomationExecution
from core.choices import COMMAND_STATUS, LOG_TYPES

logger = logging.getLogger(__name__)


class MQTTMessageConsumer:
    """
    Consumer for MQTT messages from Redis channel.
    
    This class processes incoming MQTT messages and updates the appropriate
    Django models and triggers automations.
    """
    
    def __init__(self):
        self.processors = {
            'ack': self._process_command_ack,
            'complete': self._process_command_complete,
            'sensors': self._process_sensor_data,
            'heartbeat': self._process_heartbeat,
            'startup': self._process_startup_message,
            'threshold': self._process_threshold_violation
        }
    
    def process_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Process an incoming MQTT message.
        
        Args:
            message_data: Parsed message data from Redis
            
        Returns:
            True if message was processed successfully, False otherwise
        """
        try:
            topic = message_data.get('topic', '')
            payload = message_data.get('payload', {})
            device_id = message_data.get('device_id')
            message_type = message_data.get('message_type', 'PUBLISH')
            timestamp = message_data.get('timestamp')
            
            logger.info(f"📥 Processing MQTT message: {topic} from {device_id} (type: {message_type})")
            
            # Determine message type from topic
            if 'ack' in topic:
                logger.info(f"🔄 Processing command acknowledgment for device {device_id}")
                return self._process_command_ack(payload, device_id)
            elif 'complete' in topic:
                logger.info(f"✅ Processing command completion for device {device_id}")
                return self._process_command_complete(payload, device_id)
            elif 'sensors' in topic:
                logger.info(f"📊 Processing sensor data for device {device_id}")
                return self._process_sensor_data(payload, device_id, timestamp)
            elif 'heartbeat' in topic:
                logger.info(f"💓 Processing heartbeat for device {device_id}")
                return self._process_heartbeat(payload, device_id)
            elif 'startup' in topic:
                logger.info(f"🚀 Processing startup message for device {device_id}")
                return self._process_startup_message(payload, device_id)
            elif 'threshold' in topic:
                logger.info(f"⚠️ Processing threshold violation for device {device_id}")
                return self._process_threshold_violation(payload, device_id)
            elif 'commands' in topic:
                logger.info(f"📥 Processing incoming command message for device {device_id}")
                return self._process_incoming_command(payload, device_id)
            else:
                logger.warning(f"❓ Unknown message topic: {topic}")
                return False
                
        except Exception as e:
            logger.error(f"💥 Error processing MQTT message: {e}")
            return False
    
    def _process_command_ack(self, payload: Dict[str, Any], device_id: str) -> bool:
        """Process command acknowledgment message"""
        try:
            command_id = payload.get('command_id')
            success = payload.get('success', True)
            message = payload.get('message', '')
            error_code = payload.get('error_code')
            error_details = payload.get('error_details')
            
            if not command_id:
                logger.warning(f"Command acknowledgment missing command_id from device {device_id}")
                return False
            
            logger.info(f"Processing command ACK for {command_id} from device {device_id}: success={success}, message='{message}'")
            
            with transaction.atomic():
                # Find and update device command
                try:
                    command = DeviceCommand.objects.get(command_id=command_id)
                    logger.info(f"Found DeviceCommand {command.id} for command_id {command_id}")
                    
                    if success:
                        # Only acknowledge the command, don't complete it yet
                        command.acknowledge_command()
                        logger.info(f"✅ Command {command_id} acknowledged successfully")
                    else:
                        # For failed commands, acknowledge receipt and mark as failed
                        command.acknowledge_command()
                        logger.info(f"⚠️ Command {command_id} acknowledged but failed: {message}")
                        
                        command.complete_command(False, message, error_code, error_details)
                        logger.warning(f"❌ Command {command_id} failed: {message}")
                        
                        # Complete automation execution for failed commands
                        if command.automation_execution:
                            automation = command.automation_execution
                            logger.info(f"Completing automation {automation.id} via failed command {command_id}")
                            automation.complete_execution(False, f"Command failed: {message}", error_details)
                            logger.warning(f"💥 Automation {automation.id} failed via command {command_id}: {message}")
                    
                    # Note: pending_commands and command_timeouts are managed by MQTTClient
                    # They will be cleaned up when the command is processed
                    
                    # Log MQTT message for tracking
                    try:
                        from .models import MQTTMessage
                        from ponds.models import PondPair
                        
                        # Find pond pair by device ID
                        pond_pair = PondPair.objects.get(device_id=device_id)
                        
                        MQTTMessage.objects.create(
                            pond_pair=pond_pair,
                            topic=f"ff/{device_id}/ack",
                            message_type='ACK',
                            payload=payload,
                            payload_size=len(json.dumps(payload)),
                            success=True,
                            received_at=timezone.now(),
                            correlation_id=command_id
                        )
                        logger.debug(f"Logged MQTT ACK message for command {command_id}")
                    except Exception as e:
                        logger.warning(f"Could not log MQTT message: {e}")
                    
                    return True
                    
                except DeviceCommand.DoesNotExist:
                    logger.warning(f"⚠️ Command {command_id} not found for acknowledgment - may be from test or different system")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing command acknowledgment: {e}")
            return False
    
    def _process_command_complete(self, payload: Dict[str, Any], device_id: str) -> bool:
        """Process command completion message from device"""
        try:
            command_id = payload.get('command_id')
            success = payload.get('success', True)
            message = payload.get('message', '')
            error_code = payload.get('error_code')
            error_details = payload.get('error_details')
            
            if not command_id:
                logger.error(f"No command_id in COMPLETE payload from device {device_id}")
                return False
            
            logger.info(f"Processing command COMPLETE for {command_id} from device {device_id}: success={success}, message='{message}'")
            
            with transaction.atomic():
                # Find and update device command
                try:
                    command = DeviceCommand.objects.get(command_id=command_id)
                    logger.info(f"Found DeviceCommand {command.id} for command_id {command_id}")
                    
                    # Complete the command
                    command.complete_command(success, message, error_code, error_details)
                    logger.info(f"✅ Command {command_id} completed with status: {command.status}")
                    
                    # Complete automation execution if this command was part of one
                    if command.automation_execution:
                        automation = command.automation_execution
                        logger.info(f"Completing automation {automation.id} via command {command_id}")
                        
                        if success:
                            automation.complete_execution(True, f"Command completed: {message}")
                            logger.info(f"🎉 Automation {automation.id} completed successfully via command {command_id}")
                        else:
                            automation.complete_execution(False, f"Command failed: {message}", error_details)
                            logger.warning(f"💥 Automation {automation.id} failed via command {command_id}: {message}")
                    else:
                        logger.info(f"Command {command_id} has no linked automation execution")
                    
                    # Log MQTT message for tracking
                    try:
                        from .models import MQTTMessage
                        from ponds.models import PondPair
                        
                        # Find pond pair by device ID
                        pond_pair = PondPair.objects.get(device_id=device_id)
                        
                        MQTTMessage.objects.create(
                            pond_pair=pond_pair,
                            topic=f"ff/{device_id}/complete",
                            message_type='COMPLETE',
                            payload=payload,
                            payload_size=len(json.dumps(payload)),
                            success=True,
                            received_at=timezone.now(),
                            correlation_id=command_id
                        )
                        logger.debug(f"Logged MQTT COMPLETE message for command {command_id}")
                    except Exception as e:
                        logger.warning(f"Could not log MQTT message: {e}")
                    
                    return True
                    
                except DeviceCommand.DoesNotExist:
                    logger.error(f"DeviceCommand with command_id {command_id} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing command COMPLETE: {e}")
            return False
    
    def _process_sensor_data(self, payload: Dict[str, Any], device_id: str, timestamp: str = None) -> bool:
        """Process sensor data message"""
        try:
            with transaction.atomic():
                # Find pond pair by device ID
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                except PondPair.DoesNotExist:
                    logger.warning(f"Pond pair not found for device {device_id}")
                    return False
                
                # Create sensor data record
                pond = pond_pair.ponds.first()
                if not pond:
                    logger.warning(f"No ponds found for pond pair {pond_pair.id}")
                    return False
                    
                # Parse timestamp if provided
                device_timestamp = None
                if timestamp:
                    try:
                        device_timestamp = timezone.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except ValueError:
                        device_timestamp = timezone.now()
                
                # Extract sensor data from nested 'data' object or directly from payload
                sensor_data_dict = payload.get('data', payload)
                metadata = payload.get('metadata', {})
                
                # Validate that we have at least one sensor reading
                if not sensor_data_dict or not isinstance(sensor_data_dict, dict):
                    logger.warning(f"No valid sensor data found in payload for device {device_id}")
                    return False
                
                # Create sensor data record with proper validation
                try:
                    sensor_data = SensorData.objects.create(
                        pond=pond,
                        temperature=sensor_data_dict.get('temperature', 0.0),
                        water_level=sensor_data_dict.get('water1', 0.0),
                        water_level2=sensor_data_dict.get('water2', 0.0),
                        feed_level=sensor_data_dict.get('feed1', 0.0),
                        feed_level2=sensor_data_dict.get('feed2', 0.0),
                        turbidity=sensor_data_dict.get('turbidity', 0.0),
                        dissolved_oxygen=sensor_data_dict.get('dissolved_oxygen', 0.0),
                        ph=sensor_data_dict.get('ph', 7.0),
                        ammonia=sensor_data_dict.get('ammonia', 0.0),
                        battery=sensor_data_dict.get('battery', 100.0),
                        signal_strength=metadata.get('signal'),
                        device_timestamp=device_timestamp,
                        timestamp=timezone.now()
                    )
                except Exception as e:
                    logger.error(f"Error creating SensorData record: {e}")
                    logger.error(f"Payload data: {sensor_data_dict}")
                    return False
                
                # Log MQTT message
                MQTTMessage.objects.create(
                    pond_pair=pond_pair,
                    topic=f"ff/{device_id}/sensors",
                    message_type='PUBLISH',
                    payload=payload,
                    payload_size=len(json.dumps(payload)),
                    success=True,
                    received_at=timezone.now(),
                    correlation_id=str(uuid.uuid4())
                )
                
                # Check thresholds and trigger automations using Celery tasks
                self._trigger_threshold_checks(pond_pair, sensor_data)
                
                logger.info(f"✅ Processed sensor data for device {device_id}: {len(sensor_data_dict)} parameters")
                return True
                
        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
            return False
    
    def _process_heartbeat(self, payload: Dict[str, Any], device_id: str) -> bool:
        """Process device heartbeat message"""
        try:
            with transaction.atomic():
                # Find pond pair by device ID
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                except PondPair.DoesNotExist:
                    logger.warning(f"Pond pair not found for device {device_id}")
                    return False
                
                # Update device status
                from .models import DeviceStatus
                
                device_status, created = DeviceStatus.objects.get_or_create(
                    pond_pair=pond_pair,
                    defaults={
                        'status': 'ONLINE',
                        'last_seen': timezone.now(),
                        'firmware_version': payload.get('firmware_version'),
                        'hardware_version': payload.get('hardware_version'),
                        'device_name': payload.get('device_name'),
                        'ip_address': payload.get('ip_address'),
                        'wifi_ssid': payload.get('wifi_ssid'),
                        'wifi_signal_strength': payload.get('wifi_signal_strength'),
                        'free_heap': payload.get('free_heap'),
                        'cpu_frequency': payload.get('cpu_frequency')
                    }
                )
                
                if not created:
                    # Update existing status
                    device_status.update_heartbeat()
                    if payload.get('firmware_version'):
                        device_status.firmware_version = payload['firmware_version']
                    if payload.get('hardware_version'):
                        device_status.hardware_version = payload['hardware_version']
                    if payload.get('device_name'):
                        device_status.device_name = payload['device_name']
                    if payload.get('ip_address'):
                        device_status.ip_address = payload['ip_address']
                    if payload.get('wifi_ssid'):
                        device_status.wifi_ssid = payload['wifi_ssid']
                    if payload.get('wifi_signal_strength'):
                        device_status.wifi_signal_strength = payload['wifi_signal_strength']
                    if payload.get('free_heap'):
                        device_status.free_heap = payload['free_heap']
                    if payload.get('cpu_frequency'):
                        device_status.cpu_frequency = payload['cpu_frequency']
                    device_status.save()
                
                # Log MQTT message for tracking
                try:
                    MQTTMessage.objects.create(
                        pond_pair=pond_pair,
                        topic=f"ff/{device_id}/heartbeat",
                        message_type='PUBLISH',
                        payload=payload,
                        payload_size=len(json.dumps(payload)),
                        success=True,
                        received_at=timezone.now(),
                        correlation_id=str(uuid.uuid4())
                    )
                    logger.debug(f"Logged MQTT heartbeat message for device {device_id}")
                except Exception as e:
                    logger.warning(f"Could not log MQTT heartbeat message: {e}")
                
                logger.debug(f"Processed heartbeat from device {device_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing heartbeat: {e}")
            return False
    
    def _process_startup_message(self, payload: Dict[str, Any], device_id: str) -> bool:
        """Process device startup message"""
        try:
            logger.info(f"Processing startup message from device {device_id}")
            
            # Update device status with startup information
            success = self._process_heartbeat(payload, device_id)
            
            if success:
                # Log MQTT message for tracking
                try:
                    from .models import MQTTMessage
                    from ponds.models import PondPair
                    
                    # Find pond pair by device ID
                    pond_pair = PondPair.objects.get(device_id=device_id)
                    
                    MQTTMessage.objects.create(
                        pond_pair=pond_pair,
                        topic=f"ff/{device_id}/startup",
                        message_type='PUBLISH',
                        payload=payload,
                        payload_size=len(json.dumps(payload)),
                        success=True,
                        received_at=timezone.now(),
                        correlation_id=str(uuid.uuid4())
                    )
                    logger.debug(f"Logged MQTT startup message for device {device_id}")
                except Exception as e:
                    logger.warning(f"Could not log MQTT startup message: {e}")
                
                logger.info(f"✅ Processed startup message from device {device_id}")
                return True
            else:
                logger.warning(f"Failed to process startup message from device {device_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing startup message: {e}")
            return False
    
    def _process_threshold_violation(self, payload: Dict[str, Any], device_id: str) -> bool:
        """Process threshold violation message"""
        try:
            with transaction.atomic():
                # Find pond pair by device ID
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                except PondPair.DoesNotExist:
                    logger.warning(f"Pond pair not found for device {device_id}")
                    return False
                
                # Create alert
                pond = pond_pair.ponds.first()
                if not pond:
                    logger.warning(f"No ponds found for pond pair {pond_pair.id}")
                    return False
                
                alert = Alert.objects.create(
                    pond=pond,
                    alert_type='THRESHOLD_VIOLATION',
                    severity=payload.get('severity', 'WARNING'),
                    message=payload.get('message', 'Threshold violation detected'),
                    parameter=payload.get('parameter'),
                    value=payload.get('value'),
                    threshold=payload.get('threshold'),
                    timestamp=timezone.now()
                )
                
                # Log MQTT message for tracking
                try:
                    MQTTMessage.objects.create(
                        pond_pair=pond_pair,
                        topic=f"devices/{device_id}/threshold",
                        message_type='PUBLISH',
                        payload=payload,
                        payload_size=len(json.dumps(payload)),
                        success=True,
                        received_at=timezone.now(),
                        correlation_id=str(uuid.uuid4())
                    )
                    logger.debug(f"Logged MQTT threshold message for device {device_id}")
                except Exception as e:
                    logger.warning(f"Could not log MQTT threshold message: {e}")
                
                logger.info(f"⚠️ Created threshold violation alert for {pond.name}: {alert.message}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing threshold violation: {e}")
            return False
    
    def _process_incoming_command(self, payload: Dict[str, Any], device_id: str) -> bool:
        """Process incoming command message from device"""
        try:
            logger.info(f"Processing incoming command from device {device_id}: {payload}")
            
            # Log MQTT message for tracking
            try:
                from .models import MQTTMessage
                from ponds.models import PondPair
                
                # Find pond pair by device ID
                pond_pair = PondPair.objects.get(device_id=device_id)
                
                MQTTMessage.objects.create(
                    pond_pair=pond_pair,
                    topic=f"ff/{device_id}/commands",
                    message_type='PUBLISH',
                    payload=payload,
                    payload_size=len(json.dumps(payload)),
                    success=True,
                    received_at=timezone.now(),
                    correlation_id=str(uuid.uuid4())
                )
                logger.debug(f"Logged MQTT incoming command message for device {device_id}")
            except Exception as e:
                logger.warning(f"Could not log MQTT incoming command message: {e}")
            
            # For now, just log the command - this could be extended to handle
            # device-initiated commands or status updates
            logger.info(f"📥 Incoming command from device {device_id} logged successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error processing incoming command: {e}")
            return False
    
    def _trigger_threshold_checks(self, pond_pair: PondPair, sensor_data: SensorData):
        """Trigger Celery tasks to check sensor thresholds and trigger automations"""
        try:
            # Get pond from pond pair
            pond = pond_pair.ponds.first()
            if not pond:
                logger.warning(f"No ponds found for pond pair {pond_pair.id}")
                return
            
            # Import here to avoid circular imports
            from automation.tasks import check_parameter_thresholds
            
            # Check each sensor parameter that has data
            sensor_parameters = [
                'temperature', 'water_level', 'water_level2', 'feed_level', 'feed_level2',
                'turbidity', 'dissolved_oxygen', 'ph', 'ammonia', 'battery'
            ]
            
            for param in sensor_parameters:
                value = getattr(sensor_data, param, None)
                if value is not None:
                    # Trigger Celery task for threshold checking
                    check_parameter_thresholds.apply_async(
                        args=[pond.id, param, value],
                        countdown=1  # Small delay to ensure sensor data is saved
                    )
                    
            logger.info(f"Triggered threshold checks for {pond.name} in {pond_pair.name}")
                    
        except Exception as e:
            logger.error(f"Error triggering threshold checks: {e}")


# Global consumer instance
_mqtt_consumer = None


def get_mqtt_consumer() -> MQTTMessageConsumer:
    """Get or create global MQTT consumer instance"""
    global _mqtt_consumer
    if _mqtt_consumer is None:
        _mqtt_consumer = MQTTMessageConsumer()
    return _mqtt_consumer


def process_mqtt_message(message_data: Dict[str, Any]) -> bool:
    """Process an MQTT message using the global consumer"""
    consumer = get_mqtt_consumer()
    return consumer.process_message(message_data)
