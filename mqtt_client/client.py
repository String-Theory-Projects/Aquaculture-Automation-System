"""
MQTT Client for Future Fish Dashboard IoT automation system.

This module implements a robust MQTT client that handles:
- Device communication and heartbeat tracking
- Sensor data processing and threshold checking
- Command acknowledgment and retry logic
- Error handling and connection management
"""

import json
import ssl
import uuid
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

import paho.mqtt.client as mqtt
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from .models import DeviceStatus, MQTTMessage
from ponds.models import PondPair, SensorData, SensorThreshold, Pond
from automation.models import DeviceCommand, AutomationExecution
from core.constants import MQTT_TOPICS, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD, MQTT_KEEPALIVE, MQTT_TIMEOUT
from core.choices import COMMAND_TYPES, COMMAND_STATUS, LOG_TYPES

logger = logging.getLogger(__name__)


@dataclass
class MQTTConfig:
    """Configuration for MQTT client"""
    broker_host: str = MQTT_BROKER_HOST
    broker_port: int = MQTT_BROKER_PORT
    keepalive: int = MQTT_KEEPALIVE
    timeout: int = MQTT_TIMEOUT
    username: str = MQTT_USERNAME
    password: str = MQTT_PASSWORD
    use_tls: bool = False
    ca_certs: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None


class MQTTClient:
    """
    Robust MQTT client for device communication.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Device heartbeat tracking (application-level)
    - Sensor data processing and threshold checking
    - Command acknowledgment system with retry logic
    - Comprehensive error handling and logging
    """
    
    def __init__(self, config: MQTTConfig = None):
        self.config = config or MQTTConfig()
        self.client = None
        self.is_connected = False
        self.connection_lock = threading.Lock()
        self.pending_commands: Dict[str, DeviceCommand] = {}
        self.command_timeouts: Dict[str, float] = {}
        self.device_heartbeats: Dict[str, datetime] = {}
        self.device_commands: Dict[str, List[Dict[str, Any]]] = {}
        self.executor = ThreadPoolExecutor(max_workers=getattr(settings, 'THREAD_POOL_MAX_WORKERS', 4))
        
        # Connection state
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = getattr(settings, 'MQTT_MAX_RECONNECT_ATTEMPTS', 10)
        self.reconnect_delay = getattr(settings, 'MQTT_RECONNECT_DELAY', 1)  # Start with 1 second
        
        # Callbacks
        self.on_sensor_data: Optional[Callable] = None
        self.on_device_status: Optional[Callable] = None
        self.on_command_ack: Optional[Callable] = None
        
        # Initialize client
        self._setup_client()
    
    def _setup_client(self):
        """Initialize MQTT client with proper configuration"""
        try:
            self.client = mqtt.Client(
                client_id=f"futurefish_backend_{uuid.uuid4().hex[:8]}",
                clean_session=True,
                protocol=mqtt.MQTTv311
            )
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            self.client.on_subscribe = self._on_subscribe
            
            # Set authentication credentials
            self.client.username_pw_set(self.config.username, self.config.password)
            
            # Set TLS if enabled
            if self.config.use_tls:
                self.client.tls_set(
                    ca_certs=self.config.ca_certs,
                    certfile=self.config.certfile,
                    keyfile=self.config.keyfile,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLSv1_2
                )
            
            # Set connection parameters
            self.client.keepalive = self.config.keepalive
            self.client.reconnect_delay_set(
                min_delay=getattr(settings, 'MQTT_MIN_DELAY', 1), 
                max_delay=getattr(settings, 'MQTT_MAX_DELAY', 120)
            )
            
            logger.info("MQTT client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            raise
    
    def connect(self) -> bool:
        """Connect to MQTT broker with retry logic"""
        with self.connection_lock:
            if self.is_connected:
                logger.info("Already connected to MQTT broker")
                return True
            
            try:
                logger.info(f"Connecting to MQTT broker at {self.config.broker_host}:{self.config.broker_port}")
                
                # Connect to broker
                result = self.client.connect(
                    self.config.broker_host,
                    self.config.broker_port,
                    keepalive=self.config.keepalive
                )
                
                if result == mqtt.MQTT_ERR_SUCCESS:
                    # Start the loop in a separate thread
                    self.client.loop_start()
                    
                    # Wait for connection callback
                    timeout = time.time() + self.config.timeout
                    while not self.is_connected and time.time() < timeout:
                        time.sleep(0.1)
                    
                    if self.is_connected:
                        logger.info("Successfully connected to MQTT broker")
                        self.reconnect_attempts = 0
                        self.reconnect_delay = 1
                        return True
                    else:
                        logger.error("Connection timeout")
                        return False
                else:
                    logger.error(f"Failed to connect: {result}")
                    return False
                    
            except Exception as e:
                logger.error(f"Connection error: {e}")
                return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        with self.connection_lock:
            if not self.is_connected:
                return
            
            try:
                logger.info("Disconnecting from MQTT broker")
                self.client.loop_stop()
                self.client.disconnect()
                self.is_connected = False
                logger.info("Disconnected from MQTT broker")
                
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection events"""
        if rc == 0:
            logger.info(f"🔌 Connected to MQTT broker {self.config.broker_host}:{self.config.broker_port}")
            self.is_connected = True
            
            # Subscribe to all required topics
            logger.info("📡 Setting up topic subscriptions...")
            self._subscribe_to_topics()
            
            # Start heartbeat monitoring
            logger.info("💓 Starting heartbeat monitoring...")
            self._start_heartbeat_monitoring()
            
        else:
            error_messages = {
                1: "Incorrect protocol version",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            error_msg = error_messages.get(rc, f"Unknown error code: {rc}")
            logger.error(f"Failed to connect to MQTT broker: {error_msg}")
            self.is_connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Handle MQTT disconnection events"""
        logger.warning(f"Disconnected from MQTT broker (rc: {rc})")
        self.is_connected = False
        
        # Attempt reconnection if not intentional
        if rc != 0:
            self._schedule_reconnect()
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"📥 MQTT message received on topic {topic}: {payload[:100]}...")
            
            # Parse message
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON payload on topic {topic}")
                return
            
            # Extract device ID from topic
            device_id = None
            if '/' in topic:
                device_id = topic.split('/')[1]
            
            # Publish to Redis channel for Django to process
            try:
                from .bridge import publish_mqtt_message
                success = publish_mqtt_message(topic, data, device_id, 'PUBLISH')
                if success:
                    logger.info(f"📨 Message published to Redis: {topic} from device {device_id}")
                else:
                    logger.warning(f"⚠️ Failed to publish message to Redis: {topic}")
                    # Fallback to local processing if Redis fails
                    self._process_message_locally(topic, data, device_id)
            except ImportError:
                logger.warning("Bridge module not available, processing locally")
                self._process_message_locally(topic, data, device_id)
                
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Handle successful message publishing"""
        logger.debug(f"Message published successfully (mid: {mid})")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Handle successful topic subscription"""
        logger.info(f"Subscribed to topics with QoS: {granted_qos}")
    
    def _subscribe_to_topics(self):
        """Subscribe to all required MQTT topics"""
        try:
            # Subscribe to device data topics
            topics = [
                ('ff/+/heartbeat', 1),
                ('ff/+/startup', 1),
                ('ff/+/sensors', 1),
                ('ff/+/ack', 1),
                ('ff/+/threshold', 1),
                ('ff/+/commands', 1),  # Subscribe to commands topic
                ('ff/+/status', 1)      # Subscribe to device status topic
            ]
            
            for topic, qos in topics:
                result, mid = self.client.subscribe(topic, qos)
                if result == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"✅ Subscribed to {topic} with QoS {qos}")
                else:
                    logger.error(f"❌ Failed to subscribe to {topic}")
                    
            logger.info(f"📡 MQTT client subscribed to {len(topics)} topics")
                    
        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")
    
    def _process_message_locally(self, topic: str, data: Dict[str, Any], device_id: str):
        """Process message locally when Redis bridge is not available"""
        try:
            if 'heartbeat' in topic:
                self._process_heartbeat(topic, data)
            elif 'sensors' in topic:
                self._process_sensor_data(topic, data)
            elif 'ack' in topic:
                self._process_command_ack(topic, data)
            elif 'startup' in topic:
                self._process_startup_message(topic, data)
            elif 'commands' in topic:
                self._process_command_message(topic, data, device_id)
            elif 'status' in topic:
                self._process_status_message(topic, data, device_id)
            else:
                logger.debug(f"Unhandled topic: {topic}")
        except Exception as e:
            logger.error(f"Error in local message processing: {e}")

    def _process_heartbeat(self, topic: str, data: Dict[str, Any]):
        """Process device heartbeat message"""
        try:
            # Extract device ID from topic
            device_id = topic.split('/')[1]
            
            # Update device heartbeat
            self.device_heartbeats[device_id] = timezone.now()
            
            # Update device status in database
            self._update_device_status(device_id, data)
            
            logger.debug(f"Processed heartbeat from device {device_id}")
            
        except Exception as e:
            logger.error(f"Error processing heartbeat: {e}")
    
    def _process_sensor_data(self, topic: str, data: Dict[str, Any]):
        """Process sensor data message"""
        try:
            # Extract device ID from topic
            device_id = topic.split('/')[1]
            
            # Process sensor data asynchronously
            self.executor.submit(self._process_sensor_data_async, device_id, data)
            
        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
    
    def _process_sensor_data_async(self, device_id: str, data: Dict[str, Any]):
        """Process sensor data asynchronously to avoid blocking MQTT loop"""
        try:
            with transaction.atomic():
                # Find pond pair by device ID
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                except PondPair.DoesNotExist:
                    logger.warning(f"Pond pair not found for device {device_id}")
                    return
                
                # Create sensor data record
                pond = pond_pair.ponds.first()
                if not pond:
                    logger.warning(f"No ponds found for pond pair {pond_pair.id}")
                    return
                
                sensor_data = SensorData.objects.create(
                    pond=pond,
                    temperature=data.get('temperature'),
                    water_level=data.get('water_level'),
                    water_level2=data.get('water_level2'),
                    feed_level=data.get('feed_level'),
                    feed_level2=data.get('feed_level2'),
                    dissolved_oxygen=data.get('dissolved_oxygen'),
                    ph=data.get('ph'),
                    battery=data.get('battery'),
                    signal_strength=data.get('signal_strength'),
                    device_timestamp=data.get('timestamp'),
                    timestamp=timezone.now()
                )
                
                # Log MQTT message
                MQTTMessage.objects.create(
                    pond_pair=pond_pair,
                    topic=f"devices/{device_id}/sensors",
                    message_type='PUBLISH',
                    payload=data,
                    payload_size=len(json.dumps(data)),
                    success=True,
                    received_at=timezone.now()
                )
                
                # Check thresholds and trigger automations using Celery tasks
                self._trigger_threshold_checks(pond_pair, sensor_data)
                
                logger.info(f"Processed sensor data for device {device_id}")
                
        except Exception as e:
            logger.error(f"Error processing sensor data asynchronously: {e}")
    
    def _process_command_ack(self, topic: str, data: Dict[str, Any]):
        """Process command acknowledgment message"""
        try:
            # Extract device ID from topic
            device_id = topic.split('/')[1]
            
            # Process acknowledgment asynchronously
            self.executor.submit(self._process_command_ack_async, device_id, data)
            
        except Exception as e:
            logger.error(f"Error processing command acknowledgment: {e}")
    
    def _process_command_ack_async(self, device_id: str, data: Dict[str, Any]):
        """Process command acknowledgment asynchronously"""
        try:
            command_id = data.get('command_id')
            success = data.get('success', True)
            message = data.get('message', '')
            error_code = data.get('error_code')
            error_details = data.get('error_details')
            
            if not command_id:
                logger.warning(f"Command acknowledgment missing command_id from device {device_id}")
                return
            
            # Find and update device command
            try:
                command = DeviceCommand.objects.get(command_id=command_id)
                
                if success:
                    command.acknowledge_command()
                    command.complete_command(True, message)
                    logger.info(f"Command {command_id} acknowledged successfully")
                else:
                    command.complete_command(False, message, error_code, error_details)
                    logger.warning(f"Command {command_id} failed: {message}")
                
                # Remove from pending commands
                if command_id in self.pending_commands:
                    del self.pending_commands[command_id]
                if command_id in self.command_timeouts:
                    del self.command_timeouts[command_id]
                
                # Complete automation execution if this command was part of one
                if command.automation_execution:
                    automation = command.automation_execution
                    if success:
                        automation.complete_execution(True, f"Command completed: {message}")
                        logger.info(f"Automation {automation.id} completed successfully via command {command_id}")
                    else:
                        automation.complete_execution(False, f"Command failed: {message}", error_details)
                        logger.warning(f"Automation {automation.id} failed via command {command_id}: {message}")
                    
            except DeviceCommand.DoesNotExist:
                logger.warning(f"Command {command_id} not found for acknowledgment")
                
        except Exception as e:
            logger.error(f"Error processing command acknowledgment: {e}")
    
    def _process_startup_message(self, topic: str, data: Dict[str, Any]):
        """Process device startup message"""
        try:
            # Extract device ID from topic
            device_id = topic.split('/')[1]
            
            # Update device status with startup information
            self._update_device_status(device_id, data)
            
            logger.info(f"Processed startup message from device {device_id}")
            
        except Exception as e:
            logger.error(f"Error processing startup message: {e}")
    
    def _process_command_message(self, topic: str, data: Dict[str, Any], device_id: str):
        """Process incoming command message from device"""
        try:
            logger.info(f"📥 Received command message from device {device_id}: {data}")
            # Store command data for local processing if needed
            if device_id not in self.device_commands:
                self.device_commands[device_id] = []
            self.device_commands[device_id].append({
                'topic': topic,
                'data': data,
                'timestamp': timezone.now()
            })
        except Exception as e:
            logger.error(f"Error processing command message: {e}")
    
    def _process_status_message(self, topic: str, data: Dict[str, Any], device_id: str):
        """Process device status message"""
        try:
            logger.info(f"📊 Received status message from device {device_id}: {data}")
            # Update device status
            if device_id in self.device_heartbeats:
                self.device_heartbeats[device_id] = timezone.now()
        except Exception as e:
            logger.error(f"Error processing status message: {e}")
    
    def _update_device_status(self, device_id: str, data: Dict[str, Any]):
        """Update device status in database"""
        try:
            with transaction.atomic():
                # Find pond pair by device ID
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                except PondPair.DoesNotExist:
                    logger.warning(f"Pond pair not found for device {device_id}")
                    return
                
                # Get or create device status
                device_status, created = DeviceStatus.objects.get_or_create(
                    pond_pair=pond_pair,
                    defaults={
                        'status': 'ONLINE',
                        'last_seen': timezone.now(),
                        'firmware_version': data.get('firmware_version'),
                        'hardware_version': data.get('hardware_version'),
                        'device_name': data.get('device_name'),
                        'ip_address': data.get('ip_address'),
                        'wifi_ssid': data.get('wifi_ssid'),
                        'wifi_signal_strength': data.get('wifi_signal_strength'),
                        'free_heap': data.get('free_heap'),
                        'cpu_frequency': data.get('cpu_frequency')
                    }
                )
                
                if not created:
                    # Update existing status
                    device_status.update_heartbeat()
                    if data.get('firmware_version'):
                        device_status.firmware_version = data['firmware_version']
                    if data.get('hardware_version'):
                        device_status.hardware_version = data['hardware_version']
                    if data.get('device_name'):
                        device_status.device_name = data['device_name']
                    if data.get('ip_address'):
                        device_status.ip_address = data['ip_address']
                    if data.get('wifi_ssid'):
                        device_status.wifi_ssid = data['wifi_ssid']
                    if data.get('wifi_signal_strength'):
                        device_status.wifi_signal_strength = data['wifi_signal_strength']
                    if data.get('free_heap'):
                        device_status.free_heap = data['free_heap']
                    if data.get('cpu_frequency'):
                        device_status.cpu_frequency = data['cpu_frequency']
                    device_status.save()
                
        except Exception as e:
            logger.error(f"Error updating device status: {e}")
    
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
                'dissolved_oxygen', 'ph', 'battery'
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
    
    def send_command(self, pond_pair: PondPair, command_type: str, parameters: Dict[str, Any] = None, pond: Pond = None) -> Optional[str]:
        """Send command to device and track acknowledgment"""
        try:
            if not self.is_connected:
                logger.error("MQTT client not connected")
                return None
            
            # Create device command record
            if not pond:
                # Fallback to first pond if none specified
                pond = pond_pair.ponds.first()
            
            if not pond:
                logger.error(f"No ponds found for pond pair {pond_pair.id}")
                return None
                
            command = DeviceCommand.objects.create(
                pond=pond,
                command_type=command_type,
                status='PENDING',
                parameters=parameters or {},
                timeout_seconds=getattr(settings, 'DEVICE_COMMAND_TIMEOUT_SECONDS', 10),
                max_retries=getattr(settings, 'DEVICE_COMMAND_MAX_RETRIES', 3)
            )
            
            # Get pond position (1 or 2) for the device
            pond_position = pond.position
            
            # Prepare command message with pond position
            message = {
                'command_id': str(command.command_id),
                'command_type': command_type,
                'pond_position': pond_position,  # Add pond position for device recognition
                'parameters': parameters or {},
                'timestamp': timezone.now().isoformat()
            }
            
            # Publish command
            topic = MQTT_TOPICS['COMMANDS'].format(device_id=pond_pair.device_id)
            result, mid = self.client.publish(
                topic,
                json.dumps(message),
                qos=2,  # Exactly once delivery
                retain=False
            )
            
            if result == mqtt.MQTT_ERR_SUCCESS:
                # Mark command as sent
                command.send_command()
                
                # Track pending command
                self.pending_commands[str(command.command_id)] = command
                self.command_timeouts[str(command.command_id)] = time.time() + command.timeout_seconds
                
                # Log MQTT message
                MQTTMessage.objects.create(
                    pond_pair=pond_pair,
                    topic=topic,
                    message_type='PUBLISH',
                    payload=message,
                    payload_size=len(json.dumps(message)),
                    success=True,
                    sent_at=timezone.now(),
                    correlation_id=command.command_id
                )
                
                logger.info(f"Command {command.command_id} sent to device {pond_pair.device_id} for pond {pond_position}")
                return str(command.command_id)
            else:
                # Mark command as failed
                command.complete_command(False, f"Failed to publish: {result}")
                logger.error(f"Failed to publish command {command.command_id}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    def _start_heartbeat_monitoring(self):
        """Start monitoring device heartbeats and marking offline devices"""
        def monitor_heartbeats():
            logger.info("💓 Heartbeat monitoring started")
            while self.is_connected:
                try:
                    now = timezone.now()
                    offline_threshold = now - timedelta(seconds=getattr(settings, 'DEVICE_HEARTBEAT_OFFLINE_THRESHOLD', 30))
                    
                    # Check all known devices
                    for device_id, last_heartbeat in self.device_heartbeats.items():
                        if last_heartbeat < offline_threshold:
                            # Device is offline
                            logger.info(f"📴 Device {device_id} marked as offline (no heartbeat)")
                            self._mark_device_offline(device_id)
                    
                    time.sleep(getattr(settings, 'DEVICE_HEARTBEAT_CHECK_INTERVAL', 10))  # Check every 10 seconds
                    
                except Exception as e:
                    logger.error(f"Error in heartbeat monitoring: {e}")
                    time.sleep(10)
        
        # Start monitoring in background thread
        threading.Thread(target=monitor_heartbeats, daemon=True).start()
    
    def _mark_device_offline(self, device_id: str):
        """Mark device as offline in database"""
        try:
            with transaction.atomic():
                # Find pond pair by device ID
                try:
                    pond_pair = PondPair.objects.get(device_id=device_id)
                except PondPair.DoesNotExist:
                    return
                
                # Update device status
                try:
                    device_status = DeviceStatus.objects.get(pond_pair=pond_pair)
                    device_status.mark_offline()
                except DeviceStatus.DoesNotExist:
                    pass
                
                # Remove from heartbeat tracking
                if device_id in self.device_heartbeats:
                    del self.device_heartbeats[device_id]
                    
        except Exception as e:
            logger.error(f"Error marking device offline: {e}")
    
    def _schedule_reconnect(self):
        """Schedule reconnection with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            return
        
        self.reconnect_attempts += 1
        delay = min(self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)), getattr(settings, 'MQTT_MAX_DELAY', 120))
        
        logger.info(f"Scheduling reconnection attempt {self.reconnect_attempts} in {delay} seconds")
        
        def delayed_reconnect():
            time.sleep(delay)
            if not self.is_connected:
                self.connect()
        
        threading.Thread(target=delayed_reconnect, daemon=True).start()
    
    def cleanup(self):
        """Clean up resources"""
        try:
            self.disconnect()
            if self.executor:
                self.executor.shutdown(wait=True)
            logger.info("MQTT client cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global MQTT client instance
_mqtt_client = None


def get_mqtt_client() -> MQTTClient:
    """Get or create global MQTT client instance"""
    global _mqtt_client
    if _mqtt_client is None:
        _mqtt_client = MQTTClient()
    return _mqtt_client


def initialize_mqtt_client(config: MQTTConfig = None) -> MQTTClient:
    """Initialize and connect MQTT client"""
    client = get_mqtt_client()
    if config:
        client.config = config
    
    if client.connect():
        logger.info("🚀 MQTT client initialized and connected successfully")
        return client
    else:
        logger.error("❌ Failed to initialize MQTT client")
        return None


def shutdown_mqtt_client():
    """Shutdown global MQTT client"""
    global _mqtt_client
    if _mqtt_client:
        _mqtt_client.cleanup()
        _mqtt_client = None

