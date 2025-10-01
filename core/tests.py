from django.test import TestCase
from .constants import (
    DEVICE_ID_MIN_LENGTH, SYSTEM_USERNAME, SYSTEM_EMAIL,
    MQTT_TOPICS, MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USERNAME, MQTT_PASSWORD,
    WEBSOCKET_UPDATE_INTERVAL, MAX_CONCURRENT_CONNECTIONS_PER_USER,
    AUTOMATION_PRIORITIES, DEFAULT_THRESHOLD_TIMEOUT, MAX_THRESHOLD_VIOLATIONS,
    DEFAULT_FEED_AMOUNT, MAX_FEED_AMOUNT, MIN_FEED_AMOUNT,
    DEFAULT_WATER_LEVEL, MIN_WATER_LEVEL, MAX_WATER_LEVEL,
    SENSOR_RANGES, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE,
    CACHE_TIMEOUT, CACHE_KEY_PREFIX, API_VERSION, API_RATE_LIMIT,
    LOG_LEVEL, LOG_FORMAT, LOG_MAX_SIZE, LOG_BACKUP_COUNT,
    JWT_ACCESS_TOKEN_LIFETIME_DAYS, JWT_REFRESH_TOKEN_LIFETIME_DAYS,
    PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH,
    DB_CONNECTION_TIMEOUT, DB_QUERY_TIMEOUT,
    CELERY_TASK_TIMEOUT, CELERY_MAX_RETRIES, CELERY_RETRY_DELAY
)
from .choices import (
    AUTOMATION_TYPES, FEED_STAT_TYPES, ALERT_LEVELS, ALERT_STATUS,
    LOG_TYPES, PARAMETER_CHOICES, AUTOMATION_ACTIONS, COMMAND_TYPES,
    COMMAND_STATUS, DEVICE_STATUS, USER_ROLES, NOTIFICATION_TYPES,
    THRESHOLD_OPERATORS, EXPORT_FORMATS, TIME_INTERVALS
)


class CoreConstantsTest(TestCase):
    """Tests for core constants"""
    
    def test_device_id_settings(self):
        """Test device ID settings"""
        self.assertEqual(DEVICE_ID_MIN_LENGTH, 17)
        self.assertIsInstance(DEVICE_ID_MIN_LENGTH, int)
    
    def test_system_user_settings(self):
        """Test system user settings"""
        self.assertEqual(SYSTEM_USERNAME, 'system')
        self.assertEqual(SYSTEM_EMAIL, 'system@futurefishagro.com')
        self.assertIsInstance(SYSTEM_USERNAME, str)
        self.assertIsInstance(SYSTEM_EMAIL, str)
    
    def test_mqtt_settings(self):
        """Test MQTT settings"""
        self.assertEqual(MQTT_BROKER_HOST, 'broker.emqx.io')
        self.assertEqual(MQTT_BROKER_PORT, 1883)
        self.assertEqual(MQTT_USERNAME, 'futurefish_backend')
        self.assertEqual(MQTT_PASSWORD, '7-33@98:epY}')
        self.assertIsInstance(MQTT_BROKER_HOST, str)
        self.assertIsInstance(MQTT_BROKER_PORT, int)
        self.assertIsInstance(MQTT_USERNAME, str)
        self.assertIsInstance(MQTT_PASSWORD, str)
    
    def test_mqtt_topics(self):
        """Test MQTT topic structure"""
        self.assertIn('HEARTBEAT', MQTT_TOPICS)
        self.assertIn('STARTUP', MQTT_TOPICS)
        self.assertIn('SENSORS', MQTT_TOPICS)
        self.assertIn('COMMANDS', MQTT_TOPICS)
        self.assertIn('ACK', MQTT_TOPICS)
        self.assertIn('THRESHOLD', MQTT_TOPICS)
        
        # Check topic format
        for topic_name, topic_format in MQTT_TOPICS.items():
            self.assertIn('{device_id}', topic_format)
            self.assertIsInstance(topic_format, str)
    
    def test_websocket_settings(self):
        """Test WebSocket settings"""
        self.assertEqual(WEBSOCKET_UPDATE_INTERVAL, 5)
        self.assertEqual(MAX_CONCURRENT_CONNECTIONS_PER_USER, 10)
        self.assertIsInstance(WEBSOCKET_UPDATE_INTERVAL, int)
        self.assertIsInstance(MAX_CONCURRENT_CONNECTIONS_PER_USER, int)
    
    def test_automation_settings(self):
        """Test automation settings"""
        self.assertIn('MANUAL_COMMAND', AUTOMATION_PRIORITIES)
        self.assertIn('EMERGENCY_WATER', AUTOMATION_PRIORITIES)
        self.assertIn('SCHEDULED', AUTOMATION_PRIORITIES)
        self.assertIn('THRESHOLD', AUTOMATION_PRIORITIES)
        
        self.assertEqual(DEFAULT_THRESHOLD_TIMEOUT, 30)
        self.assertEqual(MAX_THRESHOLD_VIOLATIONS, 3)
    
    def test_feed_settings(self):
        """Test feed settings"""
        self.assertEqual(DEFAULT_FEED_AMOUNT, 100)
        self.assertEqual(MAX_FEED_AMOUNT, 1000)
        self.assertEqual(MIN_FEED_AMOUNT, 10)
        
        # Validate feed amount logic
        self.assertGreater(MAX_FEED_AMOUNT, DEFAULT_FEED_AMOUNT)
        self.assertGreater(DEFAULT_FEED_AMOUNT, MIN_FEED_AMOUNT)
        self.assertGreater(MIN_FEED_AMOUNT, 0)
    
    def test_water_settings(self):
        """Test water settings"""
        self.assertEqual(DEFAULT_WATER_LEVEL, 80)
        self.assertEqual(MIN_WATER_LEVEL, 20)
        self.assertEqual(MAX_WATER_LEVEL, 100)
        
        # Validate water level logic
        self.assertGreater(MAX_WATER_LEVEL, DEFAULT_WATER_LEVEL)
        self.assertGreater(DEFAULT_WATER_LEVEL, MIN_WATER_LEVEL)
        self.assertGreater(MIN_WATER_LEVEL, 0)
        self.assertLessEqual(MAX_WATER_LEVEL, 100)
    
    def test_sensor_ranges(self):
        """Test sensor validation ranges"""
        required_sensors = [
            'temperature', 'water_level', 'feed_level', 'turbidity',
            'dissolved_oxygen', 'ph', 'ammonia', 'battery'
        ]
        
        for sensor in required_sensors:
            self.assertIn(sensor, SENSOR_RANGES)
            sensor_range = SENSOR_RANGES[sensor]
            self.assertIn('min', sensor_range)
            self.assertIn('max', sensor_range)
            self.assertIsInstance(sensor_range['min'], (int, float))
            self.assertIsInstance(sensor_range['max'], (int, float))
            self.assertLess(sensor_range['min'], sensor_range['max'])
    
    def test_pagination_settings(self):
        """Test pagination settings"""
        self.assertEqual(DEFAULT_PAGE_SIZE, 50)
        self.assertEqual(MAX_PAGE_SIZE, 200)
        self.assertLess(DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)
        self.assertGreater(DEFAULT_PAGE_SIZE, 0)
    
    def test_cache_settings(self):
        """Test cache settings"""
        self.assertEqual(CACHE_TIMEOUT, 300)
        self.assertEqual(CACHE_KEY_PREFIX, 'futurefish')
        self.assertIsInstance(CACHE_TIMEOUT, int)
        self.assertIsInstance(CACHE_KEY_PREFIX, str)
    
    def test_api_settings(self):
        """Test API settings"""
        self.assertEqual(API_VERSION, 'v1')
        self.assertEqual(API_RATE_LIMIT, '100/hour')
        self.assertIsInstance(API_VERSION, str)
        self.assertIsInstance(API_RATE_LIMIT, str)
    
    def test_logging_settings(self):
        """Test logging settings"""
        self.assertEqual(LOG_LEVEL, 'INFO')
        self.assertIn(LOG_LEVEL, ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])
        self.assertIsInstance(LOG_FORMAT, str)
        self.assertEqual(LOG_MAX_SIZE, 10 * 1024 * 1024)  # 10MB
        self.assertEqual(LOG_BACKUP_COUNT, 5)
    
    def test_security_settings(self):
        """Test security settings"""
        self.assertEqual(JWT_ACCESS_TOKEN_LIFETIME_DAYS, 60)
        self.assertEqual(JWT_REFRESH_TOKEN_LIFETIME_DAYS, 14)
        self.assertEqual(PASSWORD_MIN_LENGTH, 8)
        self.assertEqual(PASSWORD_MAX_LENGTH, 128)
        
        # Validate JWT token logic
        self.assertGreater(JWT_ACCESS_TOKEN_LIFETIME_DAYS, JWT_REFRESH_TOKEN_LIFETIME_DAYS)
        
        # Validate password length logic
        self.assertGreater(PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH)
        self.assertGreater(PASSWORD_MIN_LENGTH, 0)
    
    def test_database_settings(self):
        """Test database settings"""
        self.assertEqual(DB_CONNECTION_TIMEOUT, 30)
        self.assertEqual(DB_QUERY_TIMEOUT, 60)
        self.assertIsInstance(DB_CONNECTION_TIMEOUT, int)
        self.assertIsInstance(DB_QUERY_TIMEOUT, int)
        self.assertGreater(DB_QUERY_TIMEOUT, DB_CONNECTION_TIMEOUT)
    
    def test_celery_settings(self):
        """Test Celery settings"""
        self.assertEqual(CELERY_TASK_TIMEOUT, 300)
        self.assertEqual(CELERY_MAX_RETRIES, 3)
        self.assertEqual(CELERY_RETRY_DELAY, 60)
        self.assertIsInstance(CELERY_TASK_TIMEOUT, int)
        self.assertIsInstance(CELERY_MAX_RETRIES, int)
        self.assertIsInstance(CELERY_RETRY_DELAY, int)


class CoreChoicesTest(TestCase):
    """Tests for core choices"""
    
    def test_automation_types(self):
        """Test automation type choices"""
        self.assertIn(('FEED', 'Feeding'), AUTOMATION_TYPES)
        self.assertIn(('WATER', 'Water Change'), AUTOMATION_TYPES)
        
        # Check format: (value, display_name)
        for choice in AUTOMATION_TYPES:
            self.assertIsInstance(choice, tuple)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)
            self.assertIsInstance(choice[1], str)
    
    def test_feed_stat_types(self):
        """Test feed stat type choices"""
        expected_types = ['daily', 'weekly', 'monthly', 'yearly']
        for stat_type in expected_types:
            self.assertIn((stat_type, stat_type.title()), FEED_STAT_TYPES)
    
    def test_alert_levels(self):
        """Test alert level choices"""
        expected_levels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        for level in expected_levels:
            self.assertIn((level, level.title()), ALERT_LEVELS)
    
    def test_alert_status(self):
        """Test alert status choices"""
        expected_statuses = ['active', 'acknowledged', 'resolved', 'dismissed']
        for status in expected_statuses:
            self.assertIn((status, status.title()), ALERT_STATUS)
    
    def test_log_types(self):
        """Test log type choices"""
        expected_types = ['COMMAND', 'SENSOR', 'THRESHOLD', 'AUTOMATION', 'ERROR', 'INFO', 'WARNING']
        for log_type in expected_types:
            if log_type == 'SENSOR':
                self.assertIn((log_type, 'Sensor Data'), LOG_TYPES)
            elif log_type == 'THRESHOLD':
                self.assertIn((log_type, 'Threshold Violation'), LOG_TYPES)
            elif log_type == 'INFO':
                self.assertIn((log_type, 'Information'), LOG_TYPES)
            else:
                self.assertIn((log_type, log_type.replace('_', ' ').title()), LOG_TYPES)
    
    def test_parameter_choices(self):
        """Test parameter choices"""
        expected_parameters = [
            'temperature', 'water_level', 'feed_level', 'turbidity',
            'dissolved_oxygen', 'ph', 'ammonia', 'battery'
        ]
        for param in expected_parameters:
            if param == 'ph':
                self.assertIn((param, 'pH'), PARAMETER_CHOICES)
            else:
                self.assertIn((param, param.replace('_', ' ').title()), PARAMETER_CHOICES)
    
    def test_automation_actions(self):
        """Test automation action choices"""
        expected_actions = [
            'FEED', 'WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH',
            'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
            'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE',
            'ALERT', 'NOTIFICATION', 'LOG'
        ]
        for action in expected_actions:
            if action == 'WATER_DRAIN':
                self.assertIn((action, 'Drain Water'), AUTOMATION_ACTIONS)
            elif action == 'WATER_FILL':
                self.assertIn((action, 'Fill Water'), AUTOMATION_ACTIONS)
            elif action == 'WATER_FLUSH':
                self.assertIn((action, 'Flush Water'), AUTOMATION_ACTIONS)
            elif action == 'WATER_INLET_OPEN':
                self.assertIn((action, 'Open Water Inlet'), AUTOMATION_ACTIONS)
            elif action == 'WATER_INLET_CLOSE':
                self.assertIn((action, 'Close Water Inlet'), AUTOMATION_ACTIONS)
            elif action == 'WATER_OUTLET_OPEN':
                self.assertIn((action, 'Open Water Outlet'), AUTOMATION_ACTIONS)
            elif action == 'WATER_OUTLET_CLOSE':
                self.assertIn((action, 'Close Water Outlet'), AUTOMATION_ACTIONS)
            elif action == 'ALERT':
                self.assertIn((action, 'Send Alert'), AUTOMATION_ACTIONS)
            elif action == 'NOTIFICATION':
                self.assertIn((action, 'Send Notification'), AUTOMATION_ACTIONS)
            elif action == 'LOG':
                self.assertIn((action, 'Log Event'), AUTOMATION_ACTIONS)
            else:
                self.assertIn((action, action.replace('_', ' ').title()), AUTOMATION_ACTIONS)
    
    def test_command_types(self):
        """Test command type choices"""
        expected_commands = [
            'FEED', 'WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH',
            'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
            'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE',
            'FIRMWARE_UPDATE', 'RESTART', 'CONFIG_UPDATE'
        ]
        for command in expected_commands:
            if command == 'FEED':
                self.assertIn((command, 'Feed Command'), COMMAND_TYPES)
            elif command == 'WATER_DRAIN':
                self.assertIn((command, 'Drain Water'), COMMAND_TYPES)
            elif command == 'WATER_FILL':
                self.assertIn((command, 'Fill Water'), COMMAND_TYPES)
            elif command == 'WATER_FLUSH':
                self.assertIn((command, 'Flush Water'), COMMAND_TYPES)
            elif command == 'WATER_INLET_OPEN':
                self.assertIn((command, 'Open Water Inlet'), COMMAND_TYPES)
            elif command == 'WATER_INLET_CLOSE':
                self.assertIn((command, 'Close Water Inlet'), COMMAND_TYPES)
            elif command == 'WATER_OUTLET_OPEN':
                self.assertIn((command, 'Open Water Outlet'), COMMAND_TYPES)
            elif command == 'WATER_OUTLET_CLOSE':
                self.assertIn((command, 'Close Water Outlet'), COMMAND_TYPES)
            elif command == 'FIRMWARE_UPDATE':
                self.assertIn((command, 'Firmware Update'), COMMAND_TYPES)
            elif command == 'RESTART':
                self.assertIn((command, 'Device Restart'), COMMAND_TYPES)
            elif command == 'CONFIG_UPDATE':
                self.assertIn((command, 'Configuration Update'), COMMAND_TYPES)
            else:
                self.assertIn((command, command.replace('_', ' ').title()), COMMAND_TYPES)
    
    def test_command_status(self):
        """Test command status choices"""
        expected_statuses = [
            'PENDING', 'SENT', 'ACKNOWLEDGED', 'COMPLETED', 'FAILED', 'TIMEOUT'
        ]
        for status in expected_statuses:
            self.assertIn((status, status.title()), COMMAND_STATUS)
    
    def test_device_status(self):
        """Test device status choices"""
        expected_statuses = ['ONLINE', 'OFFLINE', 'ERROR', 'MAINTENANCE']
        for status in expected_statuses:
            self.assertIn((status, status.title()), DEVICE_STATUS)
    
    def test_user_roles(self):
        """Test user role choices"""
        expected_roles = ['OWNER', 'ADMIN', 'OPERATOR', 'VIEWER']
        for role in expected_roles:
            if role == 'ADMIN':
                self.assertIn((role, 'Administrator'), USER_ROLES)
            else:
                self.assertIn((role, role.title()), USER_ROLES)
    
    def test_notification_types(self):
        """Test notification type choices"""
        expected_types = ['EMAIL', 'SMS', 'PUSH', 'WEBHOOK']
        for notif_type in expected_types:
            if notif_type == 'SMS':
                self.assertIn((notif_type, 'SMS'), NOTIFICATION_TYPES)
            elif notif_type == 'PUSH':
                self.assertIn((notif_type, 'Push Notification'), NOTIFICATION_TYPES)
            elif notif_type == 'WEBHOOK':
                self.assertIn((notif_type, 'Webhook'), NOTIFICATION_TYPES)
            else:
                self.assertIn((notif_type, notif_type.title()), NOTIFICATION_TYPES)
    
    def test_threshold_operators(self):
        """Test threshold operator choices"""
        expected_operators = ['GT', 'LT', 'GTE', 'LTE', 'EQ', 'NE']
        operator_display_names = [
            'Greater Than', 'Less Than', 'Greater Than or Equal',
            'Less Than or Equal', 'Equal', 'Not Equal'
        ]
        
        for i, operator in enumerate(expected_operators):
            self.assertIn((operator, operator_display_names[i]), THRESHOLD_OPERATORS)
    
    def test_export_formats(self):
        """Test export format choices"""
        expected_formats = ['CSV', 'JSON', 'EXCEL', 'PDF']
        for format_type in expected_formats:
            if format_type == 'EXCEL':
                self.assertIn((format_type, 'Excel'), EXPORT_FORMATS)
            else:
                self.assertIn((format_type, format_type), EXPORT_FORMATS)
    
    def test_time_intervals(self):
        """Test time interval choices"""
        expected_intervals = [
            '1m', '5m', '15m', '30m', '1h', '6h', '12h', '1d', '1w', '1M'
        ]
        interval_display_names = [
            '1 Minute', '5 Minutes', '15 Minutes', '30 Minutes',
            '1 Hour', '6 Hours', '12 Hours', '1 Day', '1 Week', '1 Month'
        ]
        
        for i, interval in enumerate(expected_intervals):
            self.assertIn((interval, interval_display_names[i]), TIME_INTERVALS)
    
    def test_choice_consistency(self):
        """Test that all choices follow consistent format"""
        all_choices = [
            AUTOMATION_TYPES, FEED_STAT_TYPES, ALERT_LEVELS, ALERT_STATUS,
            LOG_TYPES, PARAMETER_CHOICES, AUTOMATION_ACTIONS, COMMAND_TYPES,
            COMMAND_STATUS, DEVICE_STATUS, USER_ROLES, NOTIFICATION_TYPES,
            THRESHOLD_OPERATORS, EXPORT_FORMATS, TIME_INTERVALS
        ]
        
        for choice_list in all_choices:
            self.assertIsInstance(choice_list, list)
            self.assertGreater(len(choice_list), 0)
            
            for choice in choice_list:
                self.assertIsInstance(choice, tuple)
                self.assertEqual(len(choice), 2)
                self.assertIsInstance(choice[0], str)
                self.assertIsInstance(choice[1], str)
                self.assertNotEqual(choice[0], '')
                self.assertNotEqual(choice[1], '')

# ============================================================================
# COMMON TEST UTILITIES (moved from old testing)
# ============================================================================

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.conf import settings
from rest_framework import status
from ponds.models import Pond, PondPair


class DashboardTestCase(TestCase):
    """
    Base test case with common setup for dashboard tests
    """
    
    @classmethod
    @override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
    def setUpTestData(cls):
        """Set up data for the whole TestCase"""
        super().setUpTestData()
        
        # Define common URLs
        cls.login_url = reverse('token_obtain_pair')
        cls.register_url = reverse('register')
        cls.profile_url = reverse('user_profile')
        cls.update_profile_url = reverse('update_profile')
        cls.pond_list_url = reverse('ponds:pond_list')
        cls.register_pond_url = reverse('ponds:register_pond')
        
        # Create test users
        cls.test_password = 'TestPassword123!'
        
        cls.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password=cls.test_password,
            first_name='Test',
            last_name='User'
        )
        
        cls.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password=cls.test_password,
            first_name='Other',
            last_name='User'
        )
        
        # Create system user
        cls.system_user = User.objects.create_user(
            username=settings.SYSTEM_USERNAME,
            email=settings.SYSTEM_EMAIL,
            password='SystemPassword123!',
            first_name='System',
            last_name='User'
        )
    
    def setUp(self):
        """Set up before each test method"""
        self.client = APIClient()
        
        # Default to being logged in as test_user
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': self.test_password
        }, format='json')
        
        self.access_token = response.data['access']
        self.refresh_token = response.data['refresh']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')


class PondTestUtils:
    """
    Utility methods for pond-related tests
    """
    
    @staticmethod
    def create_test_pond(owner, name, device_id, is_active=True, with_wifi=False, with_control=True):
        """
        Helper function to create a test pond with associated pond pair
        
        Args:
            owner: User who owns the pond
            name: Name of the pond
            device_id: Unique device ID (MAC address format)
            is_active: Whether the pond is active
            with_wifi: Whether to create WiFi config (deprecated)
            with_control: Whether to create pond control
        """
        # Create pond pair first
        pond_pair = PondPair.objects.create(
            device_id=device_id,
            owner=owner
        )
        
        # Create pond with parent pair
        pond = Pond.objects.create(
            name=name,
            parent_pair=pond_pair,
            is_active=is_active
        )
        
        # Pond control functionality removed - models deprecated
        
        return pond, pond_pair
    
    @staticmethod
    def create_test_pond_pair(owner, device_id, name=None):
        """
        Helper function to create a test pond pair
        
        Args:
            owner: User who owns the pond pair
            device_id: Unique device ID (MAC address format)
            name: Optional name for the pond pair
        """
        if name is None:
            name = f'Test Pair {device_id[-6:]}'
        
        return PondPair.objects.create(
            name=name,
            device_id=device_id,
            owner=owner
        )
    
    @staticmethod
    def create_test_user(username='testuser', email='test@example.com', password='TestPassword123!'):
        """
        Helper function to create a test user
        
        Args:
            username: Username for the test user
            email: Email for the test user
            password: Password for the test user
        """
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name='Test',
            last_name='User'
        )
    
    @staticmethod
    def authenticate_client(client, user, password='TestPassword123!'):
        """
        Helper function to authenticate a test client
        
        Args:
            client: APIClient instance
            user: User to authenticate as
            password: Password for the user
        """
        response = client.post(reverse('token_obtain_pair'), {
            'username': user.username,
            'password': password
        }, format='json')
        
        access_token = response.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        return access_token


class CommonTestMixin:
    """
    Mixin providing common test functionality
    """
    
    def assert_response_structure(self, response_data, expected_fields):
        """
        Assert that response data contains expected fields
        
        Args:
            response_data: Response data to check
            expected_fields: List of expected field names
        """
        for field in expected_fields:
            self.assertIn(field, response_data, f"Field '{field}' not found in response")
    
    def assert_pagination_structure(self, response_data):
        """
        Assert that response data has proper pagination structure
        
        Args:
            response_data: Response data to check
        """
        expected_pagination_fields = ['count', 'next', 'previous', 'results']
        self.assert_response_structure(response_data, expected_pagination_fields)
        
        # Check that results is a list
        self.assertIsInstance(response_data['results'], list)
        
        # Check that count is a positive integer
        self.assertIsInstance(response_data['count'], int)
        self.assertGreaterEqual(response_data['count'], 0)
    
    def assert_error_response(self, response, expected_status_code, expected_error_fields=None):
        """
        Assert that response is an error response with expected structure
        
        Args:
            response: Response to check
            expected_status_code: Expected HTTP status code
            expected_error_fields: List of expected error field names
        """
        self.assertEqual(response.status_code, expected_status_code)
        
        if expected_error_fields:
            for field in expected_error_fields:
                self.assertIn(field, response.data, f"Error field '{field}' not found in response")
    
    def assert_success_response(self, response, expected_status_code=200):
        """
        Assert that response is a successful response
        
        Args:
            response: Response to check
            expected_status_code: Expected HTTP status code
        """
        self.assertEqual(response.status_code, expected_status_code)
        self.assertNotIn('error', response.data)
        self.assertNotIn('detail', response.data)
    
    def assert_user_ownership(self, response_data, user):
        """
        Assert that response data belongs to the specified user
        
        Args:
            response_data: Response data to check
            user: User who should own the data
        """
        if 'owner' in response_data:
            self.assertEqual(response_data['owner'], user.id)
        elif 'user' in response_data:
            self.assertEqual(response_data['user'], user.id)
    
    def assert_data_integrity(self, model_class, **filters):
        """
        Assert that data exists in database with specified filters
        
        Args:
            model_class: Django model class to check
            **filters: Filters to apply to the query
        """
        self.assertTrue(model_class.objects.filter(**filters).exists())
    
    def assert_data_not_exists(self, model_class, **filters):
        """
        Assert that data does not exist in database with specified filters
        
        Args:
            model_class: Django model class to check
            **filters: Filters to apply to the query
        """
        self.assertFalse(model_class.objects.filter(**filters).exists())
