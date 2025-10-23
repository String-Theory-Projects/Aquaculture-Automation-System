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
            success_raw = payload.get('success', True)
            message = payload.get('message', '')
            error_code = payload.get('error_code')
            error_details = payload.get('error_details')
            
            # Convert string boolean to actual boolean
            if isinstance(success_raw, str):
                success = success_raw.lower() in ('true', '1', 'yes', 'on')
            else:
                success = bool(success_raw)
            
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
                        
                        # Publish ACKNOWLEDGED status update for SSE
                        from .bridge import publish_command_status_update, publish_unified_command_status_update
                        publish_command_status_update(
                            command_id=str(command.command_id),
                            status='ACKNOWLEDGED',
                            message=message or 'Command acknowledged by device',
                            command_type=command.command_type,
                            pond_id=command.pond.id,
                            pond_name=command.pond.name
                        )
                        
                        # Also publish to unified dashboard stream
                        publish_unified_command_status_update(
                            device_id=device_id,
                            command_id=str(command.command_id),
                            status='ACKNOWLEDGED',
                            message=message or 'Command acknowledged by device',
                            command_type=command.command_type,
                            pond_name=command.pond.name
                        )
                        
                        # Simulate EXECUTING status after a short delay
                        import threading
                        import time
                        
                        def simulate_executing():
                            time.sleep(1)  # 1 second delay
                            try:
                                # Check if command still exists and is not completed
                                command_check = DeviceCommand.objects.get(command_id=command_id)
                                if command_check.status == 'ACKNOWLEDGED' and not command_check.completed_at:
                                    publish_command_status_update(
                                        command_id=str(command_check.command_id),
                                        status='EXECUTING',
                                        message='Command is being executed by device',
                                        command_type=command_check.command_type,
                                        pond_id=command_check.pond.id,
                                        pond_name=command_check.pond.name
                                    )
                                    
                                    # Also publish to unified dashboard stream
                                    publish_unified_command_status_update(
                                        device_id=device_id,
                                        command_id=str(command_check.command_id),
                                        status='EXECUTING',
                                        message='Command is being executed by device',
                                        command_type=command_check.command_type,
                                        pond_name=command_check.pond.name
                                    )
                                    logger.info(f"🔄 Command {command_id} status updated to EXECUTING")
                            except DeviceCommand.DoesNotExist:
                                logger.warning(f"Command {command_id} no longer exists for EXECUTING simulation")
                            except Exception as e:
                                logger.error(f"Error simulating EXECUTING status for {command_id}: {e}")
                        
                        # Start simulation in background thread
                        threading.Thread(target=simulate_executing, daemon=True).start()
                    else:
                        # For failed commands, acknowledge receipt and mark as failed
                        command.acknowledge_command()
                        logger.info(f"⚠️ Command {command_id} acknowledged but failed: {message}")
                        
                        command.complete_command(False, message, error_code, error_details)
                        logger.warning(f"❌ Command {command_id} failed: {message}")
                        
                        # Publish status update for SSE
                        from .bridge import publish_command_status_update, publish_unified_command_status_update
                        publish_command_status_update(
                            command_id=str(command.command_id),
                            status='FAILED',
                            message=message or 'Command failed',
                            command_type=command.command_type,
                            pond_id=command.pond.id,
                            pond_name=command.pond.name
                        )
                        
                        # Also publish to unified dashboard stream
                        publish_unified_command_status_update(
                            device_id=device_id,
                            command_id=str(command.command_id),
                            status='FAILED',
                            message=message or 'Command failed',
                            command_type=command.command_type,
                            pond_name=command.pond.name
                        )
                        
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
            success_raw = payload.get('success', True)
            message = payload.get('message', '')
            error_code = payload.get('error_code')
            error_details = payload.get('error_details')
            
            # Convert string boolean to actual boolean
            if isinstance(success_raw, str):
                success = success_raw.lower() in ('true', '1', 'yes', 'on')
            else:
                success = bool(success_raw)
            
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
                    
                    # Publish status update for SSE
                    from .bridge import publish_command_status_update, publish_unified_command_status_update
                    publish_command_status_update(
                        command_id=str(command.command_id),
                        status='COMPLETED' if success else 'FAILED',
                        message=message or ('Command completed successfully' if success else 'Command failed'),
                        command_type=command.command_type,
                        pond_id=command.pond.id,
                        pond_name=command.pond.name
                    )
                    
                    # Also publish to unified dashboard stream
                    publish_unified_command_status_update(
                        device_id=device_id,
                        command_id=str(command.command_id),
                        status='COMPLETED' if success else 'FAILED',
                        message=message or ('Command completed successfully' if success else 'Command failed'),
                        command_type=command.command_type,
                        pond_name=command.pond.name
                    )
                    
                    # Handle special command types that need post-completion processing
                    if command.command_type == 'SET_THRESHOLD' and success:
                        # Process threshold completion outside the main transaction
                        try:
                            self._process_threshold_completion(command, payload)
                        except Exception as threshold_error:
                            logger.error(f"Error processing threshold completion: {threshold_error}")
                    
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
    
    def _process_threshold_completion(self, command, payload: Dict[str, Any]) -> bool:
        """Process threshold command completion by creating/updating threshold in database"""
        try:
            from ponds.models import SensorThreshold
            
            parameters = command.parameters
            parameter = parameters.get('parameter')
            upper_threshold = parameters.get('upper')
            lower_threshold = parameters.get('lower')
            
            if not all([parameter, upper_threshold is not None, lower_threshold is not None]):
                logger.error(f"Missing threshold parameters in command {command.command_id}")
                return False
            
            # Check if this is an update (command has threshold_id) or create
            threshold_id = parameters.get('threshold_id')
            
            if threshold_id:
                # Update existing threshold
                try:
                    threshold = SensorThreshold.objects.get(id=threshold_id)
                    
                    # Update threshold values from command parameters
                    threshold.upper_threshold = upper_threshold
                    threshold.lower_threshold = lower_threshold
                    
                    # Update other fields if they were modified in the command
                    if 'automation' in parameters:
                        threshold.automation_action = parameters['automation']
                    
                    # Save the updated threshold
                    threshold.save()
                    logger.info(f"✅ Updated threshold {threshold_id} for {parameter} after device completion")
                    return True
                except SensorThreshold.DoesNotExist:
                    logger.error(f"Threshold {threshold_id} not found for update")
                    return False
            else:
                # Create new threshold
                try:
                    # Get additional parameters from command
                    automation_action = parameters.get('automation', 'ALERT')
                    # Use default values for other parameters since they're not in simplified format
                    priority = 1
                    alert_level = 'MEDIUM'
                    violation_timeout = 30
                    max_violations = 3
                    send_alert = True
                    
                    threshold = SensorThreshold.objects.create(
                        pond=command.pond,
                        parameter=parameter,
                        upper_threshold=upper_threshold,
                        lower_threshold=lower_threshold,
                        automation_action=automation_action,
                        priority=priority,
                        alert_level=alert_level,
                        violation_timeout=violation_timeout,
                        max_violations=max_violations,
                        send_alert=send_alert
                    )
                    logger.info(f"✅ Created threshold {threshold.id} for {parameter} after device completion")
                    return True
                except Exception as e:
                    logger.error(f"Error creating threshold after device completion: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error processing threshold completion: {e}")
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
                    # Convert sensor distances to percentages for water levels
                    water1_distance = sensor_data_dict.get('water1')
                    water2_distance = sensor_data_dict.get('water2')
                    
                    # Convert distances to percentages if pond dimensions are available
                    water1_percentage = None
                    water2_percentage = None
                    
                    if water1_distance is not None and pond.sensor_height > 0 and pond.tank_depth > 0:
                        try:
                            water1_percentage = pond.sensor_distance_to_percentage(water1_distance)
                        except (ValueError, ZeroDivisionError):
                            logger.warning(f"Invalid conversion for water1_distance: {water1_distance}")
                    
                    if water2_distance is not None and pond.sensor_height > 0 and pond.tank_depth > 0:
                        try:
                            water2_percentage = pond.sensor_distance_to_percentage(water2_distance)
                        except (ValueError, ZeroDivisionError):
                            logger.warning(f"Invalid conversion for water2_distance: {water2_distance}")
                    
                    sensor_data = SensorData.objects.create(
                        pond=pond,
                        pond_pair=pond_pair,  # Add the missing pond_pair field
                        temperature=sensor_data_dict.get('temperature'),
                        water_level=water1_percentage,
                        water_level2=water2_percentage,
                        feed_level=sensor_data_dict.get('feed1'),
                        feed_level2=sensor_data_dict.get('feed2'),
                        turbidity=sensor_data_dict.get('turbidity'),
                        dissolved_oxygen=sensor_data_dict.get('dissolved_oxygen'),
                        ph=sensor_data_dict.get('ph'),
                        ammonia=sensor_data_dict.get('ammonia'),
                        battery=sensor_data_dict.get('battery'),
                        signal_strength=metadata.get('signal'),
                        device_timestamp=device_timestamp,
                        timestamp=timezone.now(),
                        # Store raw sensor distances for data integrity
                        sensor_distance=water1_distance,
                        sensor_distance2=water2_distance
                    )
                    
                    # Log each parameter that was processed
                    logger.info(f"📊 Created new sensor data record for device {device_id}")
                    if 'temperature' in sensor_data_dict:
                        logger.info(f"🌡️ Recorded temperature: {sensor_data.temperature}")
                    if 'dissolved_oxygen' in sensor_data_dict:
                        logger.info(f"🫁 Recorded dissolved_oxygen: {sensor_data.dissolved_oxygen}")
                    if 'ph' in sensor_data_dict:
                        logger.info(f"🧪 Recorded ph: {sensor_data.ph}")
                    if 'turbidity' in sensor_data_dict:
                        logger.info(f"🌫️ Recorded turbidity: {sensor_data.turbidity}")
                    if 'ammonia' in sensor_data_dict:
                        logger.info(f"☠️ Recorded ammonia: {sensor_data.ammonia}")
                    if 'battery' in sensor_data_dict:
                        logger.info(f"🔋 Recorded battery: {sensor_data.battery}")
                    if 'signal' in metadata:
                        logger.info(f"📶 Recorded signal_strength: {sensor_data.signal_strength}")
                    if 'water1' in sensor_data_dict:
                        logger.info(f"🌊 Recorded water_level (pond 1): {sensor_data.water_level}")
                    if 'water2' in sensor_data_dict:
                        logger.info(f"🌊 Recorded water_level (pond 2): {sensor_data.water_level2}")
                    if 'feed1' in sensor_data_dict:
                        logger.info(f"🍽️ Recorded feed_level (pond 1): {sensor_data.feed_level}")
                    if 'feed2' in sensor_data_dict:
                        logger.info(f"🍽️ Recorded feed_level (pond 2): {sensor_data.feed_level2}")
                    
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
                
                # Publish sensor data to device channel with all pond-specific data
                from .bridge import publish_sensor_data_update
                
                # Get all ponds in the pond pair for reference
                all_ponds = list(pond_pair.ponds.all())
                
                # Get or create cached comprehensive data for this device
                if not hasattr(self, '_sensor_data_cache'):
                    self._sensor_data_cache = {}
                
                # Initialize or get existing cached data for this device
                if device_id not in self._sensor_data_cache:
                    self._sensor_data_cache[device_id] = {
                        'device_id': device_id,
                        'pond_pair_id': pond_pair.id,
                        'pond_1': {'pond_id': all_ponds[0].id, 'pond_name': all_ponds[0].name} if len(all_ponds) > 0 else {},
                        'pond_2': {'pond_id': all_ponds[1].id, 'pond_name': all_ponds[1].name} if len(all_ponds) > 1 else {}
                    }
                
                # Get the cached data for this device
                comprehensive_data = self._sensor_data_cache[device_id]
                
                # Update timestamp
                comprehensive_data['timestamp'] = sensor_data.timestamp.isoformat()
                
                # Device-level fields are now added to each pond individually below
                if 'battery' in sensor_data_dict:
                    comprehensive_data['battery'] = sensor_data.battery
                    logger.info(f"🔋 Updated device battery: {sensor_data.battery}")
                if 'signal' in metadata:
                    comprehensive_data['signal_strength'] = sensor_data.signal_strength
                    logger.info(f"📶 Updated device signal_strength: {sensor_data.signal_strength}")
                if sensor_data.device_timestamp:
                    comprehensive_data['device_timestamp'] = sensor_data.device_timestamp.isoformat()
                    logger.info(f"⏰ Updated device_timestamp: {sensor_data.device_timestamp.isoformat()}")
                
                # Add/update pond-specific readings if present in the original payload
                for i, pond in enumerate(all_ponds):
                    pond_number = i + 1
                    pond_key = f'pond_{pond_number}'
                    
                    # Add device-level data to each pond (same values for both ponds)
                    if 'temperature' in sensor_data_dict:
                        comprehensive_data[pond_key]['temperature'] = sensor_data.temperature
                        logger.info(f"🌡️ Updated {pond_key} temperature: {sensor_data.temperature}")
                    if 'dissolved_oxygen' in sensor_data_dict:
                        comprehensive_data[pond_key]['dissolved_oxygen'] = sensor_data.dissolved_oxygen
                        logger.info(f"🫁 Updated {pond_key} dissolved_oxygen: {sensor_data.dissolved_oxygen}")
                    if 'ph' in sensor_data_dict:
                        comprehensive_data[pond_key]['ph'] = sensor_data.ph
                        logger.info(f"🧪 Updated {pond_key} ph: {sensor_data.ph}")
                    if 'turbidity' in sensor_data_dict:
                        comprehensive_data[pond_key]['turbidity'] = sensor_data.turbidity
                        logger.info(f"🌫️ Updated {pond_key} turbidity: {sensor_data.turbidity}")
                    if 'ammonia' in sensor_data_dict:
                        comprehensive_data[pond_key]['ammonia'] = sensor_data.ammonia
                        logger.info(f"☠️ Updated {pond_key} ammonia: {sensor_data.ammonia}")
                    
                    # Add pond-specific readings if present in the original payload
                    if f'water{pond_number}' in sensor_data_dict:
                        water_value = sensor_data.water_level if pond_number == 1 else sensor_data.water_level2
                        comprehensive_data[pond_key]['water_level'] = water_value
                        logger.info(f"🌊 Updated {pond_key} water_level: {water_value}")
                    if f'feed{pond_number}' in sensor_data_dict:
                        feed_value = sensor_data.feed_level if pond_number == 1 else sensor_data.feed_level2
                        comprehensive_data[pond_key]['feed_level'] = feed_value
                        logger.info(f"🍽️ Updated {pond_key} feed_level: {feed_value}")
                
                # Publish to device channel (one channel per device/pond pair)
                publish_sensor_data_update(device_id, comprehensive_data)
                
                # Count the actual parameters that were processed
                processed_params = []
                if 'temperature' in sensor_data_dict:
                    processed_params.append('temperature')
                if 'dissolved_oxygen' in sensor_data_dict:
                    processed_params.append('dissolved_oxygen')
                if 'ph' in sensor_data_dict:
                    processed_params.append('ph')
                if 'turbidity' in sensor_data_dict:
                    processed_params.append('turbidity')
                if 'ammonia' in sensor_data_dict:
                    processed_params.append('ammonia')
                if 'battery' in sensor_data_dict:
                    processed_params.append('battery')
                if 'signal' in metadata:
                    processed_params.append('signal_strength')
                if 'water1' in sensor_data_dict:
                    processed_params.append('water1')
                if 'water2' in sensor_data_dict:
                    processed_params.append('water2')
                if 'feed1' in sensor_data_dict:
                    processed_params.append('feed1')
                if 'feed2' in sensor_data_dict:
                    processed_params.append('feed2')
                
                logger.info(f"✅ Processed sensor data for device {device_id}: {len(processed_params)} parameters ({', '.join(processed_params)})")
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
                
                # Publish device status update to unified dashboard
                from .bridge import publish_device_status_update
                try:
                    # Get latest sensor data for battery and signal strength
                    latest_sensor_data = SensorData.objects.filter(pond_pair=pond_pair).order_by('-timestamp').first()
                    
                    device_status_data = {
                        'is_online': device_status.is_online(),
                        'last_seen': device_status.last_seen.isoformat() if device_status.last_seen else None,
                        'status': device_status.status,
                        'firmware_version': device_status.firmware_version,
                        'hardware_version': device_status.hardware_version,
                        'ip_address': device_status.ip_address,
                        'wifi_ssid': device_status.wifi_ssid,
                        'wifi_signal_strength': device_status.wifi_signal_strength,
                        'free_heap': device_status.free_heap,
                        'cpu_frequency': device_status.cpu_frequency,
                        'error_count': device_status.error_count,
                        'uptime_percentage_24h': float(device_status.get_uptime_percentage(24)),
                        'last_error': device_status.last_error,
                        'last_error_at': device_status.last_error_at.isoformat() if device_status.last_error_at else None
                    }
                    
                    # Add battery and signal strength from latest sensor data if available
                    if latest_sensor_data:
                        if latest_sensor_data.battery is not None:
                            device_status_data['battery'] = latest_sensor_data.battery
                        if latest_sensor_data.signal_strength is not None:
                            device_status_data['signal_strength'] = latest_sensor_data.signal_strength
                    
                    publish_device_status_update(device_id, device_status_data)
                except Exception as e:
                    logger.error(f"Error preparing device status data for publishing: {e}")
                    # Publish minimal data if there's an error
                    minimal_data = {
                        'is_online': device_status.is_online(),
                        'last_seen': device_status.last_seen.isoformat() if device_status.last_seen else None,
                        'status': device_status.status
                    }
                    publish_device_status_update(device_id, minimal_data)
                
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
                
                # Publish alert notification to unified dashboard
                from .bridge import publish_alert_notification
                alert_data = {
                    'id': alert.id,
                    'parameter': alert.parameter,
                    'alert_level': alert.alert_level,
                    'status': alert.status,
                    'message': alert.message,
                    'threshold_value': alert.threshold_value,
                    'current_value': alert.current_value,
                    'violation_count': alert.violation_count,
                    'first_violation_at': alert.first_violation_at.isoformat(),
                    'last_violation_at': alert.last_violation_at.isoformat(),
                    'created_at': alert.created_at.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None
                }
                publish_alert_notification(pond.id, alert_data)
                
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
