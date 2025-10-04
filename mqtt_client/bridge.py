"""
MQTT Bridge for Future Fish Dashboard.

This module provides Redis pub/sub communication between Django and the MQTT service.
It handles:
- Outgoing commands from Django to MQTT broker
- Incoming messages from MQTT broker to Django
- Command status updates and acknowledgments
"""

import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from django.utils import timezone
import redis

logger = logging.getLogger(__name__)

# Redis channels
MQTT_OUTGOING_CHANNEL = 'mqtt_outgoing'
MQTT_INCOMING_CHANNEL = 'mqtt_incoming'
COMMAND_STATUS_CHANNEL = 'command_status_updates'

# Redis connection
_redis_client = None


def get_redis_client():
    """Get or create Redis client instance"""
    global _redis_client
    if _redis_client is None:
        try:
            # Parse Redis URL from Celery broker URL
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            _redis_client = redis.from_url(
                redis_url,
                socket_timeout=5,  # 5 second socket timeout
                socket_connect_timeout=5,  # 5 second connection timeout
                retry_on_timeout=True,  # Retry on timeout
                health_check_interval=30  # Health check every 30 seconds
            )
            logger.info("Redis client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            raise
    return _redis_client


def publish_to_mqtt(command_id: str, device_id: str, topic: str, payload: Dict[str, Any], qos: int = 2) -> bool:
    """
    Publish a command to the MQTT outgoing Redis channel.
    
    Args:
        command_id: Unique identifier for the command
        device_id: Target device ID
        topic: MQTT topic to publish to
        payload: Command payload
        qos: Quality of service level (0, 1, or 2)
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare message for MQTT service
        message = {
            'command_id': command_id,
            'device_id': device_id,
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'timestamp': timezone.now().isoformat(),
            'source': 'django'
        }
        
        # Publish to Redis channel
        result = redis_client.publish(MQTT_OUTGOING_CHANNEL, json.dumps(message))
        
        # Redis publish returns number of subscribers, not success/failure
        # A successful publish returns the number of subscribers (0 is valid)
        logger.info(f"Command {command_id} published to Redis channel {MQTT_OUTGOING_CHANNEL} (subscribers: {result})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing command {command_id} to Redis: {e}")
        return False


def publish_mqtt_message(topic: str, payload: Dict[str, Any], device_id: str = None, 
                        message_type: str = 'PUBLISH', timestamp: Optional[str] = None) -> bool:
    """
    Publish an incoming MQTT message to the Django Redis channel.
    
    Args:
        topic: MQTT topic the message was received on
        payload: Message payload
        device_id: Source device ID (if applicable)
        message_type: Type of message (PUBLISH, ACK, etc.)
        timestamp: Message timestamp (defaults to now)
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare message for Django
        message = {
            'topic': topic,
            'payload': payload,
            'device_id': device_id,
            'message_type': message_type,
            'timestamp': timestamp or timezone.now().isoformat(),
            'source': 'mqtt_service'
        }
        
        # Publish to Redis channel
        result = redis_client.publish(MQTT_INCOMING_CHANNEL, json.dumps(message))
        
        # Redis publish returns number of subscribers, not success/failure
        # A successful publish returns the number of subscribers (0 is valid)
        logger.debug(f"MQTT message published to Redis channel {MQTT_INCOMING_CHANNEL} (subscribers: {result})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing MQTT message to Redis: {e}")
        return False


def subscribe_to_mqtt_outgoing(callback):
    """
    Subscribe to MQTT outgoing channel for testing/debugging purposes.
    
    Args:
        callback: Function to call when messages are received
        
    Returns:
        Redis pubsub object
    """
    try:
        redis_client = get_redis_client()
        pubsub = redis_client.pubsub()
        pubsub.subscribe(MQTT_OUTGOING_CHANNEL)
        
        def message_handler(message):
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'].decode('utf-8'))
                    callback(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in Redis message: {e}")
        
        pubsub.message_handler = message_handler
        return pubsub
        
    except Exception as e:
        logger.error(f"Error subscribing to MQTT outgoing channel: {e}")
        return None


def subscribe_to_mqtt_incoming(callback):
    """
    Subscribe to MQTT incoming channel for testing/debugging purposes.
    
    Args:
        callback: Function to call when messages are received
        
    Returns:
        Redis pubsub object
    """
    try:
        redis_client = get_redis_client()
        pubsub = redis_client.pubsub()
        pubsub.subscribe(MQTT_INCOMING_CHANNEL)
        
        def message_handler(message):
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'].decode('utf-8'))
                    callback(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in Redis message: {e}")
        
        pubsub.message_handler = message_handler
        return pubsub
        
    except Exception as e:
        logger.error(f"Error subscribing to MQTT incoming channel: {e}")
        return None


def publish_command_status_update(command_id: str, status: str, message: str = '', command_type: str = '', pond_id: int = None, pond_name: str = '') -> bool:
    """
    Publish a command status update to the Redis channel for SSE streams.
    
    Args:
        command_id: Unique identifier for the command
        status: Current status (PENDING, SENT, ACKNOWLEDGED, COMPLETED, FAILED, TIMEOUT)
        message: Status message
        command_type: Type of command (FEED, WATER_DRAIN, etc.)
        pond_id: ID of the pond
        pond_name: Name of the pond
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare status update message
        status_data = {
            'command_id': str(command_id),
            'command_type': command_type,
            'status': status,
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'pond_id': pond_id,
            'pond_name': pond_name
        }
        
        # Publish to Redis channel
        result = redis_client.publish(COMMAND_STATUS_CHANNEL, json.dumps(status_data))
        
        # Also publish to command-specific channel for SSE streams
        command_channel = f'command_status_{command_id}'
        result2 = redis_client.publish(command_channel, json.dumps(status_data))
        
        logger.info(f"📢 Command status update published for {command_id}: {status} (subscribers: {result}, command-specific: {result2})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing command status update for {command_id}: {e}")
        return False


def publish_device_status_update(device_id: str, device_status: dict) -> bool:
    """
    Publish device status update to the unified dashboard stream.
    
    Args:
        device_id: ID of the device (pond pair)
        device_status: Device status data
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare device status update message
        status_data = {
            'device_status': device_status,
            'timestamp': timezone.now().isoformat(),
            'device_id': device_id
        }
        
        # Publish to device channel (one channel per device/pond pair)
        channel = f'device_status_{device_id}'
        result = redis_client.publish(channel, json.dumps(status_data))
        
        logger.info(f"📡 Device status update published for device {device_id} (subscribers: {result})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing device status update for device {device_id}: {e}")
        return False


def publish_sensor_data_update(device_id: str, sensor_data: dict) -> bool:
    """
    Publish sensor data update to the unified dashboard stream.
    
    Args:
        device_id: ID of the device (pond pair)
        sensor_data: Sensor data
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare sensor data update message
        data = {
            'sensor_data': sensor_data,
            'timestamp': timezone.now().isoformat(),
            'device_id': device_id
        }
        
        # Publish to device channel (one channel per device/pond pair)
        channel = f'sensor_data_{device_id}'
        result = redis_client.publish(channel, json.dumps(data))
        
        logger.info(f"📊 Sensor data update published for device {device_id} (subscribers: {result})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing sensor data update for device {device_id}: {e}")
        return False


def publish_unified_command_status_update(device_id: str, command_id: str, status: str, message: str = '', command_type: str = '', pond_name: str = '') -> bool:
    """
    Publish command status update to the unified dashboard stream.
    
    Args:
        device_id: ID of the device (pond pair)
        command_id: Unique identifier for the command
        status: Current status (PENDING, SENT, ACKNOWLEDGED, COMPLETED, FAILED, TIMEOUT)
        message: Status message
        command_type: Type of command (FEED, WATER_DRAIN, etc.)
        pond_name: Name of the pond
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare command status update message
        status_data = {
            'command_id': str(command_id),
            'command_type': command_type,
            'status': status,
            'message': message,
            'timestamp': timezone.now().isoformat(),
            'device_id': device_id,
            'pond_name': pond_name
        }
        
        # Publish to device channel (one channel per device/pond pair)
        channel = f'command_status_{device_id}'
        result = redis_client.publish(channel, json.dumps(status_data))
        
        logger.info(f"📢 Unified command status update published for device {device_id}, command {command_id}: {status} (subscribers: {result})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing unified command status update for device {device_id}, command {command_id}: {e}")
        return False


def publish_alert_notification(device_id: str, alert: dict) -> bool:
    """
    Publish alert notification to the unified dashboard stream.
    
    Args:
        device_id: ID of the device (pond pair)
        alert: Alert data
        
    Returns:
        True if successfully published to Redis, False otherwise
    """
    try:
        redis_client = get_redis_client()
        
        # Prepare alert notification message
        data = {
            'alert': alert,
            'timestamp': timezone.now().isoformat(),
            'device_id': device_id
        }
        
        # Publish to device channel (one channel per device/pond pair)
        channel = f'alerts_{device_id}'
        result = redis_client.publish(channel, json.dumps(data))
        
        logger.info(f"🚨 Alert notification published for device {device_id} (subscribers: {result})")
        return True
            
    except Exception as e:
        logger.error(f"Error publishing alert notification for device {device_id}: {e}")
        return False


def get_redis_status() -> Dict[str, Any]:
    """Get Redis connection status and channel information"""
    try:
        redis_client = get_redis_client()
        
        # Test connection
        redis_client.ping()
        
        # Get channel subscriber counts
        outgoing_subscribers = redis_client.pubsub_numsub(MQTT_OUTGOING_CHANNEL)[0][1]
        incoming_subscribers = redis_client.pubsub_numsub(MQTT_INCOMING_CHANNEL)[0][1]
        
        return {
            'status': 'connected',
            'outgoing_channel': MQTT_OUTGOING_CHANNEL,
            'incoming_channel': MQTT_INCOMING_CHANNEL,
            'outgoing_subscribers': outgoing_subscribers,
            'incoming_subscribers': incoming_subscribers,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }
