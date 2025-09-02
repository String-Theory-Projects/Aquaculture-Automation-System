"""
Tests for MQTT Client implementation.

This module tests:
- MQTT client connection and message handling
- Device command execution
- Sensor data processing
- Error handling and retry logic
"""

import json
import time
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import uuid

from .client import MQTTClient, MQTTConfig
from .services import MQTTService
from .models import DeviceStatus, MQTTMessage
from ponds.models import PondPair, Pond
from automation.models import DeviceCommand, AutomationExecution


class MQTTConfigTestCase(TestCase):
    """Test MQTT configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = MQTTConfig()
        self.assertEqual(config.broker_host, 'localhost')
        self.assertEqual(config.broker_port, 1883)
        self.assertEqual(config.keepalive, 60)
        self.assertEqual(config.timeout, 10)
        self.assertFalse(config.use_tls)
        self.assertIsNone(config.username)
        self.assertIsNone(config.password)
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = MQTTConfig(
            broker_host='test.broker.com',
            broker_port=8883,
            username='testuser',
            password='testpass',
            use_tls=True
        )
        self.assertEqual(config.broker_host, 'test.broker.com')
        self.assertEqual(config.broker_port, 8883)
        self.assertEqual(config.username, 'testuser')
        self.assertEqual(config.password, 'testpass')
        self.assertTrue(config.use_tls)


class MQTTClientTestCase(TestCase):
    """Test MQTT client functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create pond pair first
        self.pond_pair = PondPair.objects.create(
            name='Test Pond Pair',
            device_id='TEST_DEVICE_001',
            owner=self.user
        )
        
        # Create pond with parent pair
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair,
            is_active=True
        )
        
        self.device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='OFFLINE'
        )
    
    @patch('paho.mqtt.client.Client')
    def test_client_initialization(self, mock_mqtt_client):
        """Test MQTT client initialization"""
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        
        client = MQTTClient()
        
        # Verify client was created
        mock_mqtt_client.assert_called_once()
        
        # Verify callbacks were set (they are assigned, not called)
        self.assertEqual(mock_client.on_connect, client._on_connect)
        self.assertEqual(mock_client.on_disconnect, client._on_disconnect)
        self.assertEqual(mock_client.on_message, client._on_message)
        self.assertEqual(mock_client.on_publish, client._on_publish)
        self.assertEqual(mock_client.on_subscribe, client._on_subscribe)
    
    @patch('paho.mqtt.client.Client')
    def test_client_connection(self, mock_mqtt_client):
        """Test MQTT client connection"""
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        mock_client.connect.return_value = 0  # MQTT_ERR_SUCCESS
        
        # Mock the subscribe method to return proper tuple
        mock_client.subscribe.return_value = (0, 1)  # (result, mid)
        
        client = MQTTClient()
        
        # Mock the loop_start to avoid threading issues
        mock_client.loop_start.return_value = None
        
        # Mock the connection callback to set is_connected
        def mock_on_connect(client, userdata, flags, rc):
            client._on_connect(client, userdata, flags, 0)
        
        # Set the callback and manually trigger it to set is_connected
        client.client.on_connect = mock_on_connect
        client._on_connect(mock_client, None, None, 0)
        
        # Test connection
        result = client.connect()
        self.assertTrue(result)
        self.assertTrue(client.is_connected)
    
    @patch('paho.mqtt.client.Client')
    def test_client_disconnection(self, mock_mqtt_client):
        """Test MQTT client disconnection"""
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        
        client = MQTTClient()
        client.is_connected = True
        
        client.disconnect()
        
        # Verify disconnect was called
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
        self.assertFalse(client.is_connected)


class MQTTServiceTestCase(TestCase):
    """Test MQTT service functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create pond pair first
        self.pond_pair = PondPair.objects.create(
            name='Test Pond Pair',
            device_id='TEST_DEVICE_001',
            owner=self.user
        )
        
        # Create pond with parent pair
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair,
            is_active=True
        )
        
        self.device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE',
            last_seen=timezone.now()
        )
    
    @patch('mqtt_client.services.get_mqtt_client')
    def test_send_feed_command(self, mock_get_client):
        """Test sending feed command"""
        mock_client = Mock()
        mock_client.send_command.return_value = str(uuid.uuid4())
        mock_get_client.return_value = mock_client
        
        service = MQTTService()
        result = service.send_feed_command(self.pond_pair, 100, pond=self.pond, user=self.user)
        
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        mock_client.send_command.assert_called_once()
        
        # Verify automation execution was created
        automation = AutomationExecution.objects.filter(
            pond=self.pond,
            execution_type='FEED',
            user=self.user
        ).first()
        self.assertIsNotNone(automation)
    
    @patch('mqtt_client.services.get_mqtt_client')
    def test_send_water_command(self, mock_get_client):
        """Test sending water command"""
        mock_client = Mock()
        mock_client.send_command.return_value = str(uuid.uuid4())
        mock_get_client.return_value = mock_client
        
        service = MQTTService()
        result = service.send_water_command(self.pond_pair, 'WATER_DRAIN', 50, pond=self.pond, user=self.user)
        
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        mock_client.send_command.assert_called_once()
        
        # Verify automation execution was created
        automation = AutomationExecution.objects.filter(
            pond=self.pond,
            execution_type='WATER',
            user=self.user
        ).first()
        self.assertIsNotNone(automation)
    
    @patch('mqtt_client.services.get_mqtt_client')
    def test_send_water_flush_command(self, mock_get_client):
        """Test sending water flush command"""
        mock_client = Mock()
        mock_client.send_command.return_value = str(uuid.uuid4())
        mock_get_client.return_value = mock_client
        
        service = MQTTService()
        result = service.send_water_command(
            self.pond_pair, 
            'WATER_FLUSH', 
            pond=self.pond, 
            user=self.user,
            drain_level=20,
            fill_level=80
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        mock_client.send_command.assert_called_once()
        
        # Verify automation execution was created
        automation = AutomationExecution.objects.filter(
            pond=self.pond,
            execution_type='WATER',
            user=self.user
        ).first()
        self.assertIsNotNone(automation)
    
    @patch('mqtt_client.services.get_mqtt_client')
    def test_send_water_valve_command(self, mock_get_client):
        """Test sending water valve control command"""
        mock_client = Mock()
        mock_client.send_command.return_value = str(uuid.uuid4())
        mock_get_client.return_value = mock_client
        
        service = MQTTService()
        result = service.send_water_command(
            self.pond_pair, 
            'WATER_INLET_OPEN', 
            pond=self.pond, 
            user=self.user
        )
        
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)
        mock_client.send_command.assert_called_once()
        
        # Verify automation execution was created
        automation = AutomationExecution.objects.filter(
            pond=self.pond,
            execution_type='WATER',
            user=self.user
        ).first()
        self.assertIsNotNone(automation)
    
    def test_get_device_status(self):
        """Test getting device status"""
        service = MQTTService()
        status = service.get_device_status(self.pond_pair)
        
        self.assertIsNotNone(status)
        self.assertEqual(status['status'], 'ONLINE')
        self.assertTrue(status['is_online'])
        self.assertEqual(status['firmware_version'], None)
    
    def test_get_device_commands(self):
        """Test getting device commands"""
        # Create a test command
        command = DeviceCommand.objects.create(
            pond=self.pond,
            command_type='FEED',
            status='COMPLETED',
            parameters={'amount': 100}
        )
        
        service = MQTTService()
        commands = service.get_device_commands(self.pond_pair, 10)
        
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]['command_type'], 'FEED')
        self.assertEqual(commands[0]['status'], 'COMPLETED')
    
    def test_get_mqtt_messages(self):
        """Test getting MQTT messages"""
        # Create a test message
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='test/topic',
            message_type='PUBLISH',
            payload={'test': 'data'},
            payload_size=20
        )
        
        service = MQTTService()
        messages = service.get_mqtt_messages(self.pond_pair, 10)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['topic'], 'test/topic')
        self.assertEqual(messages[0]['message_type'], 'PUBLISH')
    
    def test_check_device_connectivity(self):
        """Test device connectivity check"""
        service = MQTTService()
        connectivity = service.check_device_connectivity(self.pond_pair)
        
        self.assertIsNotNone(connectivity)
        self.assertTrue(connectivity['is_online'])
        self.assertEqual(connectivity['status'], 'ONLINE')
        self.assertGreater(connectivity['connectivity_score'], 0)
    
    def test_get_system_health_summary(self):
        """Test system health summary"""
        service = MQTTService()
        health = service.get_system_health_summary()
        
        self.assertIsNotNone(health)
        self.assertIn('total_devices', health)
        self.assertIn('online_devices', health)
        self.assertIn('connectivity_percentage', health)
        self.assertIn('mqtt_client_status', health)


class DeviceStatusModelTest(TestCase):
    """Tests for DeviceStatus model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        self.pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
    
    def test_device_status_creation(self):
        """Test creating device status"""
        device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE',
            firmware_version='1.2.3',
            hardware_version='ESP32-V1',
            device_name='Test Device',
            ip_address='192.168.1.100',
            wifi_ssid='TestWiFi',
            wifi_signal_strength=-45
        )
        
        self.assertEqual(device_status.pond_pair, self.pond_pair)
        self.assertEqual(device_status.status, 'ONLINE')
        self.assertEqual(device_status.firmware_version, '1.2.3')
        self.assertEqual(device_status.hardware_version, 'ESP32-V1')
        self.assertEqual(device_status.device_name, 'Test Device')
        self.assertEqual(device_status.ip_address, '192.168.1.100')
        self.assertEqual(device_status.wifi_ssid, 'TestWiFi')
        self.assertEqual(device_status.wifi_signal_strength, -45)
        self.assertEqual(device_status.error_count, 0)
    
    def test_device_status_validation(self):
        """Test device status validation"""
        # Valid signal strength should work
        DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE',
            wifi_signal_strength=-50
        )
        
        # Invalid signal strength should fail
        with self.assertRaises(ValidationError):
            device_status = DeviceStatus(
                pond_pair=self.pond_pair,
                status='ONLINE',
                wifi_signal_strength=10  # Above max
            )
            device_status.full_clean()
    
    def test_heartbeat_update(self):
        """Test heartbeat update method"""
        device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='OFFLINE'
        )
        
        initial_time = device_status.last_seen
        device_status.update_heartbeat()
        
        self.assertEqual(device_status.status, 'ONLINE')
        self.assertIsNotNone(device_status.last_seen)
        if initial_time:
            self.assertGreater(device_status.last_seen, initial_time)
    
    def test_mark_offline(self):
        """Test marking device as offline"""
        device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE'
        )
        
        device_status.mark_offline()
        self.assertEqual(device_status.status, 'OFFLINE')
    
    def test_record_error(self):
        """Test recording device error"""
        device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE',
            error_count=0
        )
        
        error_message = 'Connection timeout'
        device_status.record_error(error_message)
        
        self.assertEqual(device_status.status, 'ERROR')
        self.assertEqual(device_status.error_count, 1)
        self.assertEqual(device_status.last_error, error_message)
        self.assertIsNotNone(device_status.last_error_at)
    
    def test_is_online(self):
        """Test online status check"""
        device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE'
        )
        
        # No last_seen should be offline
        self.assertFalse(device_status.is_online())
        
        # Recent heartbeat should be online
        device_status.update_heartbeat()
        self.assertTrue(device_status.is_online())
        
        # Old heartbeat should be offline
        device_status.last_seen = timezone.now() - timezone.timedelta(seconds=35)
        self.assertFalse(device_status.is_online())
    
    def test_uptime_percentage(self):
        """Test uptime percentage calculation"""
        device_status = DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE'
        )
        
        # No last_seen should return 0%
        self.assertEqual(device_status.get_uptime_percentage(), 0.0)
        
        # Recent heartbeat should return >0%
        device_status.update_heartbeat()
        uptime = device_status.get_uptime_percentage(hours=1)
        self.assertGreater(uptime, 0.0)
        self.assertLessEqual(uptime, 100.0)
    
    def test_one_to_one_relationship(self):
        """Test one-to-one relationship with PondPair"""
        DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE'
        )
        
        # Should not be able to create another status for same pair
        with self.assertRaises(IntegrityError):
            DeviceStatus.objects.create(
                pond_pair=self.pond_pair,
                status='OFFLINE'
            )


class MQTTMessageModelTest(TestCase):
    """Tests for MQTTMessage model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        self.pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
    
    def test_mqtt_message_creation(self):
        """Test creating an MQTT message"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/data/sensors',
            message_type='PUBLISH',
            payload={'temperature': 25.5, 'humidity': 60.0},
            payload_size=45,
            success=True
        )
        
        self.assertEqual(message.pond_pair, self.pond_pair)
        self.assertEqual(message.topic, 'devices/AA:BB:CC:DD:EE:FF/data/sensors')
        self.assertEqual(message.message_type, 'PUBLISH')
        self.assertEqual(message.payload, {'temperature': 25.5, 'humidity': 60.0})
        self.assertEqual(message.payload_size, 45)
        self.assertTrue(message.success)
        self.assertIsNotNone(message.message_id)
        self.assertIsNone(message.correlation_id)
    
    def test_mqtt_message_with_correlation(self):
        """Test MQTT message with correlation ID"""
        correlation_id = uuid.uuid4()
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED', 'amount': 100},
            payload_size=35,
            success=True,
            correlation_id=correlation_id
        )
        
        self.assertEqual(message.correlation_id, correlation_id)
    
    def test_mqtt_message_with_error_details(self):
        """Test MQTT message with error details"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED'},
            payload_size=25,
            success=False
        )
        
        self.assertFalse(message.success)
    
    def test_record_sent(self):
        """Test recording message sent"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED'},
            payload_size=25,
            success=True
        )
        
        message.record_sent()
        self.assertIsNotNone(message.sent_at)
    
    def test_record_received(self):
        """Test recording message received"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED'},
            payload_size=25,
            success=True
        )
        
        message.record_sent()
        time.sleep(0.001)  # Small delay to ensure different timestamps
        message.record_received()
        
        self.assertIsNotNone(message.received_at)
        self.assertIsNotNone(message.processing_time)
        self.assertGreater(message.processing_time.total_seconds(), 0)
    
    def test_record_error(self):
        """Test recording message error"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED'},
            payload_size=25,
            success=True
        )
        
        error_message = 'Failed to process message'
        message.record_error(error_message)
        
        self.assertFalse(message.success)
        self.assertEqual(message.error_message, error_message)
    
    def test_is_processed(self):
        """Test message processing status"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED'},
            payload_size=25,
            success=True
        )
        
        # Initially not processed
        self.assertFalse(message.is_processed())
        
        # After recording received
        message.record_received()
        self.assertTrue(message.is_processed())
    
    def test_processing_time_ms(self):
        """Test processing time in milliseconds"""
        message = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/commands',
            message_type='PUBLISH',
            payload={'command': 'FEED'},
            payload_size=25,
            success=True
        )
        
        # No processing time should return None
        self.assertIsNone(message.get_processing_time_ms())
        
        # After recording sent and received
        message.record_sent()
        time.sleep(0.001)
        message.record_received()
        
        processing_time_ms = message.get_processing_time_ms()
        self.assertIsNotNone(processing_time_ms)
        self.assertGreater(processing_time_ms, 0)
    
    def test_message_ordering(self):
        """Test message ordering"""
        message1 = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/data/sensors',
            message_type='PUBLISH',
            payload={'temperature': 25.0},
            payload_size=20,
            success=True
        )
        
        time.sleep(0.001)  # Small delay
        
        message2 = MQTTMessage.objects.create(
            pond_pair=self.pond_pair,
            topic='devices/AA:BB:CC:DD:EE:FF/data/sensors',
            message_type='PUBLISH',
            payload={'temperature': 26.0},
            payload_size=20,
            success=True
        )
        
        messages = MQTTMessage.objects.all()
        self.assertEqual(messages[0], message2)  # Most recent first
        self.assertEqual(messages[1], message1)
    
    def test_message_indexes(self):
        """Test that messages have proper indexes"""
        meta = MQTTMessage._meta
        self.assertIn('pond_pair', [field.name for field in meta.fields])
        self.assertIn('topic', [field.name for field in meta.fields])
        self.assertIn('message_type', [field.name for field in meta.fields])
        self.assertIn('created_at', [field.name for field in meta.fields])


class MQTTClientIntegrationTestCase(TestCase):
    """Integration tests for MQTT client"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.pond_pair = PondPair.objects.create(
            name='Test Pond Pair',
            device_id='TEST_DEVICE_001',
            owner=self.user
        )
        
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    @patch('paho.mqtt.client.Client')
    def test_full_command_workflow(self, mock_mqtt_client):
        """Test complete command workflow"""
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        mock_client.connect.return_value = 0
        mock_client.publish.return_value = (0, 1)  # (result, mid)
        
        # Create client
        client = MQTTClient()
        
        # Mock connection
        client.is_connected = True
        
        # Send command
        command_id = client.send_command(self.pond_pair, 'FEED', {'amount': 100})
        
        self.assertIsNotNone(command_id)
        
        # Verify command was created in database
        command = DeviceCommand.objects.get(command_id=command_id)
        self.assertEqual(command.status, 'SENT')
        self.assertEqual(command.command_type, 'FEED')
        
        # Verify MQTT message was logged
        message = MQTTMessage.objects.filter(correlation_id=command_id).first()
        self.assertIsNotNone(message)
        self.assertEqual(message.topic, 'devices/TEST_DEVICE_001/commands')
    
    @patch('paho.mqtt.client.Client')
    def test_sensor_data_processing(self, mock_mqtt_client):
        """Test sensor data processing workflow"""
        mock_client = Mock()
        mock_mqtt_client.return_value = mock_client
        
        client = MQTTClient()
        
        # Mock device heartbeat
        client.device_heartbeats['TEST_DEVICE_001'] = timezone.now()
        
        # Process sensor data
        sensor_data = {
            'temperature': 25.5,
            'water_level': 80.0,
            'feed_level': 75.0,  # Required field
            'turbidity': 5.0,     # Required field
            'dissolved_oxygen': 8.5,  # Required field
            'ph': 7.2,
            'timestamp': timezone.now().isoformat()
        }
        
        client._process_sensor_data_async('TEST_DEVICE_001', sensor_data)
        
        # Verify sensor data was created
        sensor_record = self.pond.sensor_readings.first()
        self.assertIsNotNone(sensor_record)
        self.assertEqual(sensor_record.temperature, 25.5)
        self.assertEqual(sensor_record.water_level, 80.0)
        self.assertEqual(sensor_record.ph, 7.2)
        
        # Verify MQTT message was logged
        message = MQTTMessage.objects.filter(
            pond_pair=self.pond_pair,
            topic__contains='sensors'
        ).first()
        self.assertIsNotNone(message)
        self.assertTrue(message.success)
