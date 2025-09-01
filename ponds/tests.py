from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from .models import PondPair, Pond, SensorData, SensorThreshold, Alert, DeviceLog, PondControl
from core.constants import SENSOR_RANGES
from django.db import transaction


class PondPairModelTest(TestCase):
    """Tests for PondPair model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
    
    def test_pond_pair_creation(self):
        """Test creating a pond pair"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        
        self.assertEqual(pond_pair.name, 'Test Pair')
        self.assertEqual(pond_pair.device_id, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(pond_pair.owner, self.user)
        self.assertEqual(pond_pair.pond_count, 0)
        self.assertFalse(pond_pair.is_complete)
        self.assertFalse(pond_pair.has_minimum_ponds)
    
    def test_pond_pair_with_ponds(self):
        """Test pond pair with ponds"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        
        pond1 = Pond.objects.create(name='Pond 1', parent_pair=pond_pair)
        pond2 = Pond.objects.create(name='Pond 2', parent_pair=pond_pair)
        
        self.assertEqual(pond_pair.pond_count, 2)
        self.assertTrue(pond_pair.is_complete)
        self.assertTrue(pond_pair.has_minimum_ponds)
        
        # Check that ponds are accessible through the related name
        ponds = list(pond_pair.ponds.all())
        self.assertIn(pond1, ponds)
        self.assertIn(pond2, ponds)
    
    def test_unique_constraints(self):
        """Test unique constraints"""
        PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        
        # Same name, different owner should work
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        PondPair.objects.create(
            name='Test Pair',
            device_id='BB:CC:DD:EE:FF:AA',
            owner=other_user
        )
        
        # Same device_id should fail
        with self.assertRaises(IntegrityError):
            PondPair.objects.create(
                name='Different Name',
                device_id='AA:BB:CC:DD:EE:FF',
                owner=other_user
            )


class PondModelTest(TestCase):
    """Tests for Pond model"""
    
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
    
    def test_pond_creation(self):
        """Test creating a pond"""
        pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        self.assertEqual(pond.name, 'Test Pond')
        self.assertEqual(pond.parent_pair, self.pond_pair)
        self.assertEqual(pond.owner, self.user)
        self.assertTrue(pond.is_active)
    
    def test_pond_unique_constraints(self):
        """Test unique constraints"""
        # Create first pond
        Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Same name in same pair should fail at database level
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Pond.objects.create(
                    name='Test Pond',
                    parent_pair=self.pond_pair
                )
        
        # Same name in different pair should work
        other_pair = PondPair.objects.create(
            name='Other Pair',
            device_id='BB:CC:DD:EE:FF:AA',
            owner=self.user
        )
        Pond.objects.create(
            name='Test Pond',
            parent_pair=other_pair
        )
    
    def test_pond_deletion_validation(self):
        """Test pond deletion validation"""
        pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Should not be able to delete the last pond
        with self.assertRaises(ValidationError):
            pond.delete()
        
        # Should be able to force delete
        pond.delete(force_delete=True)
        self.assertEqual(self.pond_pair.pond_count, 0)


class SensorDataModelTest(TestCase):
    """Tests for SensorData model"""
    
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
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    def test_sensor_data_creation(self):
        """Test creating sensor data"""
        sensor_data = SensorData.objects.create(
            pond=self.pond,
            temperature=25.5,
            water_level=80.0,
            feed_level=90.0,
            turbidity=15.0,
            dissolved_oxygen=7.5,
            ph=7.2,
            ammonia=5.0,
            battery=85.0,
            signal_strength=-45
        )
        
        self.assertEqual(sensor_data.temperature, 25.5)
        self.assertEqual(sensor_data.water_level, 80.0)
        self.assertEqual(sensor_data.ammonia, 5.0)
        self.assertEqual(sensor_data.battery, 85.0)
        self.assertEqual(sensor_data.signal_strength, -45)
    
    def test_sensor_data_validation(self):
        """Test sensor data validation"""
        # Valid data should work
        SensorData.objects.create(
            pond=self.pond,
            temperature=25.0,
            water_level=80.0,
            feed_level=90.0,
            turbidity=15.0,
            dissolved_oxygen=7.5,
            ph=7.2
        )
        
        # Invalid temperature should fail
        with self.assertRaises(ValidationError):
            sensor_data = SensorData(
                pond=self.pond,
                temperature=60.0,  # Above max
                water_level=80.0,
                feed_level=90.0,
                turbidity=15.0,
                dissolved_oxygen=7.5,
                ph=7.2
            )
            sensor_data.full_clean()
    
    def test_sensor_data_indexes(self):
        """Test that sensor data has proper indexes"""
        # This test ensures the model meta is correct
        meta = SensorData._meta
        self.assertIn('pond', [field.name for field in meta.fields])
        self.assertIn('timestamp', [field.name for field in meta.fields])


class SensorThresholdModelTest(TestCase):
    """Tests for SensorThreshold model"""
    
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
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    def test_threshold_creation(self):
        """Test creating a threshold"""
        threshold = SensorThreshold.objects.create(
            pond=self.pond,
            parameter='temperature',
            upper_threshold=30.0,
            lower_threshold=20.0,
            automation_action='ALERT',
            priority=1,
            alert_level='HIGH'
        )
        
        self.assertEqual(threshold.parameter, 'temperature')
        self.assertEqual(threshold.upper_threshold, 30.0)
        self.assertEqual(threshold.lower_threshold, 20.0)
        self.assertEqual(threshold.automation_action, 'ALERT')
        self.assertEqual(threshold.priority, 1)
        self.assertTrue(threshold.is_active)
    
    def test_threshold_validation(self):
        """Test threshold validation"""
        # Upper must be greater than lower
        with self.assertRaises(ValidationError):
            threshold = SensorThreshold(
                pond=self.pond,
                parameter='temperature',
                upper_threshold=20.0,
                lower_threshold=30.0,
                automation_action='ALERT'
            )
            threshold.full_clean()
        
        # Values must be within sensor ranges
        with self.assertRaises(ValidationError):
            threshold = SensorThreshold(
                pond=self.pond,
                parameter='temperature',
                upper_threshold=60.0,  # Above max
                lower_threshold=20.0,
                automation_action='ALERT'
            )
            threshold.full_clean()
    
    def test_threshold_unique_constraint(self):
        """Test unique constraint per pond and parameter"""
        SensorThreshold.objects.create(
            pond=self.pond,
            parameter='temperature',
            upper_threshold=30.0,
            lower_threshold=20.0,
            automation_action='ALERT'
        )
        
        # Same parameter for same pond should fail
        with self.assertRaises(IntegrityError):
            SensorThreshold.objects.create(
                pond=self.pond,
                parameter='temperature',
                upper_threshold=35.0,
                lower_threshold=25.0,
                automation_action='FEED'
            )


class AlertModelTest(TestCase):
    """Tests for Alert model"""
    
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
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    def test_alert_creation(self):
        """Test creating an alert"""
        alert = Alert.objects.create(
            pond=self.pond,
            parameter='temperature',
            alert_level='HIGH',
            status='active',
            message='Temperature too high',
            threshold_value=30.0,
            current_value=35.0
        )
        
        self.assertEqual(alert.parameter, 'temperature')
        self.assertEqual(alert.alert_level, 'HIGH')
        self.assertEqual(alert.status, 'active')
        self.assertEqual(alert.threshold_value, 30.0)
        self.assertEqual(alert.current_value, 35.0)
        self.assertEqual(alert.violation_count, 1)
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment"""
        alert = Alert.objects.create(
            pond=self.pond,
            parameter='temperature',
            alert_level='HIGH',
            status='active',
            message='Temperature too high',
            threshold_value=30.0,
            current_value=35.0
        )
        
        alert.acknowledge(self.user)
        self.assertEqual(alert.status, 'acknowledged')
        self.assertEqual(alert.acknowledged_by, self.user)
        self.assertIsNotNone(alert.acknowledged_at)
    
    def test_alert_resolution(self):
        """Test alert resolution"""
        alert = Alert.objects.create(
            pond=self.pond,
            parameter='temperature',
            alert_level='HIGH',
            status='active',
            message='Temperature too high',
            threshold_value=30.0,
            current_value=35.0
        )
        
        alert.resolve(self.user)
        self.assertEqual(alert.status, 'resolved')
        self.assertEqual(alert.resolved_by, self.user)
        self.assertIsNotNone(alert.resolved_at)


class DeviceLogModelTest(TestCase):
    """Tests for DeviceLog model"""
    
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
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    def test_device_log_creation(self):
        """Test creating a device log"""
        log = DeviceLog.objects.create(
            pond=self.pond,
            log_type='COMMAND',
            message='Feed command sent',
            success=True,
            command_type='FEED',
            user=self.user
        )
        
        self.assertEqual(log.log_type, 'COMMAND')
        self.assertEqual(log.message, 'Feed command sent')
        self.assertTrue(log.success)
        self.assertEqual(log.command_type, 'FEED')
        self.assertEqual(log.user, self.user)
        # command_id is optional, so it can be None
        self.assertIsNone(log.command_id)
    
    def test_device_log_with_metadata(self):
        """Test device log with metadata"""
        metadata = {
            'command_amount': 100,
            'device_response': 'success',
            'execution_time': 2.5
        }
        
        log = DeviceLog.objects.create(
            pond=self.pond,
            log_type='COMMAND',
            message='Feed command executed',
            success=True,
            metadata=metadata
        )
        
        self.assertEqual(log.metadata, metadata)
        self.assertEqual(log.metadata['command_amount'], 100)


class PondControlModelTest(TestCase):
    """Tests for PondControl model"""
    
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
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    def test_pond_control_creation(self):
        """Test creating pond control"""
        control = PondControl.objects.create(
            pond=self.pond,
            water_valve_state=True,
            last_feed_time=timezone.now(),
            last_feed_amount=100.0
        )
        
        self.assertTrue(control.water_valve_state)
        self.assertIsNotNone(control.last_feed_time)
        self.assertEqual(control.last_feed_amount, 100.0)
    
    def test_pond_control_one_to_one(self):
        """Test one-to-one relationship"""
        control1 = PondControl.objects.create(
            pond=self.pond,
            water_valve_state=False
        )
        
        # Should not be able to create another control for same pond
        with self.assertRaises(IntegrityError):
            PondControl.objects.create(
                pond=self.pond,
                water_valve_state=True
            )

# ============================================================================
# POND PAIR VIEW TESTS (moved from old testing)
# ============================================================================

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.test.utils import override_settings
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


class PondPairViewTest(TestCase):
    """Tests for PondPair views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )

        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='TestPassword123!'
        )
        
        # Login and get token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_pond_pair_creation(self):
        """Test creating a basic PondPair"""
        data = {
            'name': 'Test Pond Pair',
            'device_id': 'AA:BB:CC:DD:EE:12'
        }
        
        url = reverse('ponds:pond_pair_list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Pond Pair')
        self.assertEqual(response.data['device_id'], 'AA:BB:CC:DD:EE:12')
        self.assertEqual(response.data['owner'], self.user.id)
        self.assertEqual(response.data['pond_count'], 0)
        self.assertFalse(response.data['is_complete'])
    
    def test_pond_pair_with_ponds(self):
        """Test creating a PondPair with ponds"""
        data = {
            'name': 'Test Pond Pair 2',
            'device_id': 'BB:CC:DD:EE:FF:AA'
        }
        
        url = reverse('ponds:pond_pair_list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Pond Pair 2')
        self.assertEqual(response.data['device_id'], 'BB:CC:DD:EE:FF:AA')
        self.assertEqual(response.data['owner'], self.user.id)
        self.assertEqual(response.data['pond_count'], 0)
        self.assertFalse(response.data['is_complete'])
    
    def test_pond_pair_device_id_uniqueness(self):
        """Test that device_id must be unique"""
        # Create first pond pair
        data1 = {
            'name': 'Test Pond Pair 1',
            'device_id': 'AA:BB:CC:DD:EE:14'
        }
        
        url = reverse('ponds:pond_pair_list')
        response1 = self.client.post(url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Try to create another PondPair with the same device_id
        data2 = {
            'name': 'Test Pond Pair 2',
            'device_id': 'AA:BB:CC:DD:EE:14'
        }
        
        response2 = self.client.post(url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_pond_pair_owner_relationship(self):
        """Test that PondPair is properly linked to its owner"""
        data = {
            'name': 'Test Pond Pair',
            'device_id': 'BB:CC:DD:EE:FF:AA'
        }
        
        url = reverse('ponds:pond_pair_list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner'], self.user.id)
        
        # Verify the pond pair was created in the database
        pond_pair = PondPair.objects.get(id=response.data['id'])
        self.assertEqual(pond_pair.owner, self.user)
    
    def test_pond_pair_list_authenticated(self):
        """Test that authenticated user can list their pond pairs"""
        # Create some pond pairs
        pond_pair1 = PondPair.objects.create(
            name='Test Pair 1',
            device_id='AA:BB:CC:DD:EE:15',
            owner=self.user
        )
        pond_pair2 = PondPair.objects.create(
            name='Test Pair 2',
            device_id='BB:CC:DD:EE:FF:BB',
            owner=self.user
        )
        
        url = reverse('ponds:pond_pair_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the created pond pairs are in the response
        response_ids = [pair['id'] for pair in response.data['results']]
        
        self.assertIn(pond_pair1.id, response_ids)
        self.assertIn(pond_pair2.id, response_ids)
        
        # Check that only user's pond pairs are returned
        for pair in response.data['results']:
            self.assertEqual(pair['owner'], self.user.id)
    
    def test_pond_pair_list_unauthenticated(self):
        """Test that unauthenticated user cannot list pond pairs"""
        self.client.credentials()  # Clear credentials
        
        url = reverse('ponds:pond_pair_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_pond_pair_detail_authenticated_owner(self):
        """Test that authenticated owner can view pond pair details"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:16',
            owner=self.user
        )
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], pond_pair.id)
        self.assertEqual(response.data['name'], 'Test Pair')
        self.assertEqual(response.data['device_id'], 'AA:BB:CC:DD:EE:16')
    
    def test_pond_pair_detail_unauthenticated(self):
        """Test that unauthenticated user cannot view pond pair details"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:17',
            owner=self.user
        )
        
        self.client.credentials()  # Clear credentials
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_pond_pair_detail_unauthorized(self):
        """Test that user cannot view another user's pond pair"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:18',
            owner=self.user2
        )
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_pond_pair_update_authenticated_owner(self):
        """Test that authenticated owner can update pond pair"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:19',
            owner=self.user
        )
        
        update_data = {
            'name': 'Updated Pair Name'
        }
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Pair Name')
        
        # Verify in database
        pond_pair.refresh_from_db()
        self.assertEqual(pond_pair.name, 'Updated Pair Name')
    
    def test_pond_pair_update_unauthorized(self):
        """Test that user cannot update another user's pond pair"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:20',
            owner=self.user2
        )
        
        update_data = {
            'name': 'Updated Pair Name'
        }
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify no changes in database
        pond_pair.refresh_from_db()
        self.assertEqual(pond_pair.name, 'Test Pair')
    
    def test_pond_pair_delete_authenticated_owner(self):
        """Test that authenticated owner can delete pond pair"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:21',
            owner=self.user
        )
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deleted from database
        self.assertFalse(PondPair.objects.filter(id=pond_pair.id).exists())
    
    def test_pond_pair_delete_unauthorized(self):
        """Test that user cannot delete another user's pond pair"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:22',
            owner=self.user2
        )
        
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify not deleted from database
        self.assertTrue(PondPair.objects.filter(id=pond_pair.id).exists())
    
    def test_pond_pair_validation(self):
        """Test pond pair validation"""
        # Test invalid device_id format
        data = {
            'name': 'Test Pair',
            'device_id': 'invalid-device-id'
        }
        
        url = reverse('ponds:pond_pair_list')
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('device_id', response.data)
    
    def test_pond_pair_with_ponds_relationship(self):
        """Test pond pair relationship with ponds"""
        pond_pair = PondPair.objects.create(
            name='Test Pair',
            device_id='AA:BB:CC:DD:EE:23',
            owner=self.user
        )
        
        # Create ponds
        pond1 = Pond.objects.create(
            name='Pond 1',
            parent_pair=pond_pair
        )
        pond2 = Pond.objects.create(
            name='Pond 2',
            parent_pair=pond_pair
        )
        
        # Refresh pond pair to get updated pond_count
        pond_pair.refresh_from_db()
        
        self.assertEqual(pond_pair.pond_count, 2)
        self.assertTrue(pond_pair.is_complete)
        self.assertTrue(pond_pair.has_minimum_ponds)
        
        # Test pond pair detail includes pond information
        url = reverse('ponds:pond_pair_detail', kwargs={'pk': pond_pair.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pond_count'], 2)
        self.assertTrue(response.data['is_complete'])
        self.assertTrue(response.data['has_minimum_ponds'])

# ============================================================================
# POND VIEW TESTS (moved from old testing)
# ============================================================================

@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class PondListViewTest(TestCase):
    """Tests for pond list endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Create test pond pair and pond
        self.pond_pair = PondPair.objects.create(
            name='Pond List Test Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Login and get token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # URLs
        self.pond_list_url = reverse('ponds:pond_list')
    
    def test_get_pond_list(self):
        """Test getting list of user's Ponds"""
        response = self.client.get(self.pond_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Only user-owned ponds
        
        # Verify pond name
        self.assertEqual(response.data[0]['name'], 'Test Pond')
    
    def test_inactive_pond_included(self):
        """Test that inactive Ponds owned by the user are included in list"""
        # Deactivate a pond
        self.pond.is_active = False
        self.pond.save()
        
        # Get ponds including inactive ones
        response = self.client.get(f"{self.pond_list_url}?include_inactive=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ponds = response.data
        inactive_ponds = [p for p in ponds if not p['is_active']]
        self.assertEqual(len(inactive_ponds), 1)
    
    def test_unauthorized(self):
        """Test that Pond list access fails without authentication"""
        self.client.credentials() # Clear credentials
        response = self.client.get(self.pond_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class PondDetailViewTest(TestCase):
    """Tests for Pond detail endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        
        # Create system user
        self.system_user = User.objects.create_user(
            username=settings.SYSTEM_USERNAME,
            email=settings.SYSTEM_EMAIL,
            password='SystemPassword123!'
        )
        
        # Create test pond pair and pond
        self.pond_pair = PondPair.objects.create(
            name='Pond Detail Test Pair',
            device_id='BB:CC:DD:EE:FF:AA',
            owner=self.user
        )
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Login and get token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # URLs
        self.pond_detail_url = reverse('ponds:pond_detail', kwargs={'pk': self.pond.id})
    
    def test_get_pond_detail(self):
        """Test getting pond detail"""
        response = self.client.get(self.pond_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Pond')
        self.assertEqual(response.data['parent_pair'], self.pond_pair.id)
        self.assertTrue(response.data['is_active'])
    
    def test_get_pond_detail_unauthorized(self):
        """Test that user cannot access another user's pond"""
        other_pond_pair = PondPair.objects.create(
            name='Other User Pair',
            device_id='CC:DD:EE:FF:AA:BB',
            owner=self.other_user
        )
        other_pond = Pond.objects.create(
            name='Other User Pond',
            parent_pair=other_pond_pair
        )
        
        url = reverse('ponds:pond_detail', kwargs={'pk': other_pond.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_pond_detail_unauthenticated(self):
        """Test that unauthenticated user cannot access pond detail"""
        self.client.credentials()  # Clear credentials
        
        response = self.client.get(self.pond_detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_pond_detail(self):
        """Test updating pond detail"""
        update_data = {
            'name': 'Updated Pond',  # 12 characters, within 15 limit
            'is_active': False
        }
        
        response = self.client.patch(self.pond_detail_url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Pond')
        self.assertFalse(response.data['is_active'])
        
        # Verify in database
        self.pond.refresh_from_db()
        self.assertEqual(self.pond.name, 'Updated Pond')
        self.assertFalse(self.pond.is_active)
    
    def test_update_pond_detail_unauthorized(self):
        """Test that user cannot update another user's pond"""
        other_pond_pair = PondPair.objects.create(
            name='Other User Pair',
            device_id='DD:EE:FF:AA:BB:CC',
            owner=self.other_user
        )
        other_pond = Pond.objects.create(
            name='Other User Pond',
            parent_pair=other_pond_pair
        )
        
        url = reverse('ponds:pond_detail', kwargs={'pk': other_pond.id})
        update_data = {'name': 'Hacked Pond Name'}
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify no changes in database
        other_pond.refresh_from_db()
        self.assertEqual(other_pond.name, 'Other User Pond')
    
    def test_delete_pond(self):
        """Test deleting pond"""
        # Create a second pond in the same pair to allow deletion
        second_pond = Pond.objects.create(
            name='Second Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Now we can delete the first pond since there are 2 ponds in the pair
        response = self.client.delete(self.pond_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deleted from database
        self.assertFalse(Pond.objects.filter(id=self.pond.id).exists())
        
        # Verify second pond still exists
        self.assertTrue(Pond.objects.filter(id=second_pond.id).exists())
    
    def test_delete_pond_unauthorized(self):
        """Test that user cannot delete another user's pond"""
        other_pond_pair = PondPair.objects.create(
            name='Other User Pair',
            device_id='EE:FF:AA:BB:CC:DD',
            owner=self.other_user
        )
        other_pond = Pond.objects.create(
            name='Other User Pond',
            parent_pair=other_pond_pair
        )
        
        url = reverse('ponds:pond_detail', kwargs={'pk': other_pond.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify not deleted from database
        self.assertTrue(Pond.objects.filter(id=other_pond.id).exists())


@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class PondRegistrationTest(TestCase):
    """Tests for pond registration endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Create test pond pair
        self.pond_pair = PondPair.objects.create(
            name='Pond Registration Test Pair',
            device_id='FF:AA:BB:CC:DD:EE',
            owner=self.user
        )
        
        # Login and get token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # URLs
        self.register_pond_url = reverse('ponds:register_pond')
    
    def test_register_pond_success(self):
        """Test successful pond registration"""
        data = {
            'name': 'New Test Pair',  # This is the pond pair name
            'device_id': 'AA:BB:CC:DD:EE:FF',  # New device ID
            'pond_names': ['Pond 1', 'Pond 2']  # Names for the ponds
        }
        
        response = self.client.post(self.register_pond_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('pond_pair', response.data)
        self.assertEqual(response.data['pond_pair']['name'], 'New Test Pair')
        self.assertEqual(response.data['pond_pair']['device_id'], 'AA:BB:CC:DD:EE:FF')
        
        # Verify created in database
        pond_pair = PondPair.objects.get(device_id='AA:BB:CC:DD:EE:FF')
        self.assertEqual(pond_pair.name, 'New Test Pair')
        self.assertEqual(pond_pair.owner, self.user)
        self.assertEqual(pond_pair.pond_count, 2)
    
    def test_register_pond_invalid_data(self):
        """Test pond registration with invalid data"""
        # Test without required fields
        data = {}
        
        response = self.client.post(self.register_pond_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Check that at least one validation error is present
        self.assertTrue(len(response.data) > 0)
        # Check that device_id error is present (this will be the first validation error)
        self.assertIn('device_id', response.data)
    
    def test_register_pond_unauthorized_pair(self):
        """Test that user cannot register pond with another user's device"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        
        # Create a pond pair with a device that another user owns
        other_pair = PondPair.objects.create(
            name='Other User Pair',
            device_id='AA:BB:CC:DD:EE:11',
            owner=other_user
        )
        
        data = {
            'name': 'New Test Pair',
            'device_id': 'AA:BB:CC:DD:EE:11',  # Try to use device owned by another user
            'pond_names': ['Pond 1']
        }
        
        response = self.client.post(self.register_pond_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('device_id', response.data)
    
    def test_register_pond_unauthenticated(self):
        """Test that unauthenticated user cannot register pond"""
        self.client.credentials()  # Clear credentials
        
        data = {
            'name': 'New Test Pair',
            'device_id': 'AA:BB:CC:DD:EE:FF',
            'pond_names': ['Pond 1']
        }
        
        response = self.client.post(self.register_pond_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SensorDataSerializerTest(TestCase):
    """Tests for sensor data handling in PondPairWithPondDetailsSerializer"""
    
    def setUp(self):
        """Set up test data"""
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
        
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
    
    def test_get_latest_non_zero_sensor_data(self):
        """Test that the serializer returns the latest non-zero sensor values"""
        from .serializers import PondPairWithPondDetailsSerializer
        
        # Create sensor data with some zero values and some non-zero values
        SensorData.objects.create(
            pond=self.pond,
            temperature=0.0,  # Zero value
            water_level=0.0,  # Zero value
            feed_level=50.0,  # Non-zero value
            turbidity=0.0,    # Zero value
            dissolved_oxygen=8.5,  # Non-zero value
            ph=7.2,           # Non-zero value
            ammonia=0.0,      # Zero value
            battery=90.0,     # Non-zero value
            timestamp=timezone.now() - timezone.timedelta(hours=2)
        )
        
        # Create more recent sensor data with some non-zero values
        SensorData.objects.create(
            pond=self.pond,
            temperature=25.5,  # Non-zero value
            water_level=0.0,   # Still zero
            feed_level=0.0,    # Now zero
            turbidity=15.0,    # Non-zero value
            dissolved_oxygen=0.0,  # Now zero
            ph=0.0,            # Now zero
            ammonia=2.5,       # Non-zero value
            battery=0.0,       # Now zero
            timestamp=timezone.now() - timezone.timedelta(hours=1)
        )
        
        # Create most recent sensor data
        SensorData.objects.create(
            pond=self.pond,
            temperature=0.0,   # Zero again
            water_level=85.0,  # Non-zero value
            feed_level=0.0,    # Still zero
            turbidity=0.0,     # Zero again
            dissolved_oxygen=0.0,  # Still zero
            ph=0.0,            # Still zero
            ammonia=0.0,       # Zero again
            battery=0.0,       # Still zero
            timestamp=timezone.now()
        )
        
        # Serialize the pond pair
        serializer = PondPairWithPondDetailsSerializer(self.pond_pair)
        data = serializer.data
        
        # Check that ponds data exists
        self.assertIn('ponds', data)
        self.assertEqual(len(data['ponds']), 1)
        
        pond_data = data['ponds'][0]
        self.assertIn('latest_sensor_data', pond_data)
        
        sensor_data = pond_data['latest_sensor_data']
        self.assertIsNotNone(sensor_data)
        
        # Check that we get the latest non-zero values for each sensor
        # Temperature: should be 25.5 (from second reading)
        self.assertEqual(sensor_data['temperature'], 25.5)
        
        # Water level: should be 85.0 (from third reading)
        self.assertEqual(sensor_data['water_level'], 85.0)
        
        # Feed level: should be 50.0 (from first reading)
        self.assertEqual(sensor_data['feed_level'], 50.0)
        
        # Turbidity: should be 15.0 (from second reading)
        self.assertEqual(sensor_data['turbidity'], 15.0)
        
        # Dissolved oxygen: should be 8.5 (from first reading)
        self.assertEqual(sensor_data['dissolved_oxygen'], 8.5)
        
        # pH: should be 7.2 (from first reading)
        self.assertEqual(sensor_data['ph'], 7.2)
        
        # Ammonia: should be 2.5 (from second reading)
        self.assertEqual(sensor_data['ammonia'], 2.5)
        
        # Battery: should be 90.0 (from first reading)
        self.assertEqual(sensor_data['battery'], 90.0)
        
        # Check that timestamp is the most recent
        self.assertEqual(sensor_data['timestamp'], self.pond.sensor_readings.first().timestamp)
    
    def test_get_latest_non_zero_sensor_data_no_readings(self):
        """Test that the serializer handles ponds with no sensor readings"""
        from .serializers import PondPairWithPondDetailsSerializer
        
        # Serialize the pond pair (no sensor data created)
        serializer = PondPairWithPondDetailsSerializer(self.pond_pair)
        data = serializer.data
        
        pond_data = data['ponds'][0]
        self.assertIn('latest_sensor_data', pond_data)
        self.assertIsNone(pond_data['latest_sensor_data'])
    
    def test_get_latest_non_zero_sensor_data_all_zero_values(self):
        """Test that the serializer handles cases where all sensor values are zero"""
        from .serializers import PondPairWithPondDetailsSerializer
        
        # Create sensor data with all zero values
        SensorData.objects.create(
            pond=self.pond,
            temperature=0.0,
            water_level=0.0,
            feed_level=0.0,
            turbidity=0.0,
            dissolved_oxygen=0.0,
            ph=0.0,
            ammonia=0.0,
            battery=0.0,
            timestamp=timezone.now()
        )
        
        # Serialize the pond pair
        serializer = PondPairWithPondDetailsSerializer(self.pond_pair)
        data = serializer.data
        
        pond_data = data['ponds'][0]
        self.assertIn('latest_sensor_data', pond_data)
        
        # Should return None since all values are zero
        self.assertIsNone(pond_data['latest_sensor_data'])


class PondPairListSerializerTest(TestCase):
    """Tests for PondPairListSerializer detailed pond information"""
    
    def setUp(self):
        """Set up test data"""
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
        
        self.pond1 = Pond.objects.create(
            name='Test Pond 1',
            parent_pair=self.pond_pair
        )
        
        self.pond2 = Pond.objects.create(
            name='Test Pond 2',
            parent_pair=self.pond_pair
        )
    
    def test_pond_pair_list_returns_detailed_pond_info(self):
        """Test that PondPairListSerializer returns detailed pond information"""
        from .serializers import PondPairListSerializer
        
        # Create some sensor data
        SensorData.objects.create(
            pond=self.pond1,
            temperature=25.5,
            water_level=85.0,
            feed_level=50.0,
            turbidity=15.0,
            dissolved_oxygen=8.5,
            ph=7.2,
            ammonia=2.5,
            battery=90.0,
            timestamp=timezone.now()
        )
        
        # Create control data
        PondControl.objects.create(
            pond=self.pond1,
            water_valve_state=True,  # True for open, False for closed
            last_feed_time=timezone.now(),
            last_feed_amount=150.0
        )
        
        # Create device status
        from mqtt_client.models import DeviceStatus
        DeviceStatus.objects.create(
            pond_pair=self.pond_pair,
            status='ONLINE',
            last_seen=timezone.now(),
            firmware_version='1.2.3',
            hardware_version='ESP32-V1',
            device_name='Test Device',
            ip_address='192.168.1.100',
            wifi_ssid='TestWiFi',
            wifi_signal_strength=-45,
            free_heap=100000,
            cpu_frequency=240,
            error_count=0
        )
        
        # Serialize the pond pair
        serializer = PondPairListSerializer(self.pond_pair)
        data = serializer.data
        
        # Check that ponds data exists and has detailed information
        self.assertIn('ponds', data)
        self.assertEqual(len(data['ponds']), 2)
        
        # Check the first pond (the one with sensor and control data)
        pond_data = data['ponds'][0]
        
        # Check that we have the basic pond fields
        self.assertIn('id', pond_data)
        self.assertIn('name', pond_data)
        self.assertIn('is_active', pond_data)
        self.assertIn('created_at', pond_data)
        
        # Check that we have control information
        self.assertIn('control', pond_data)
        self.assertIsNotNone(pond_data['control'])
        self.assertEqual(pond_data['control']['water_valve_state'], True)
        self.assertIn('last_feed_time', pond_data['control'])
        self.assertIn('last_feed_amount', pond_data['control'])
        
        # Check that we have sensor data
        self.assertIn('latest_sensor_data', pond_data)
        self.assertIsNotNone(pond_data['latest_sensor_data'])
        
        sensor_data = pond_data['latest_sensor_data']
        self.assertEqual(sensor_data['temperature'], 25.5)
        self.assertEqual(sensor_data['water_level'], 85.0)
        self.assertEqual(sensor_data['feed_level'], 50.0)
        self.assertEqual(sensor_data['turbidity'], 15.0)
        self.assertEqual(sensor_data['dissolved_oxygen'], 8.5)
        self.assertEqual(sensor_data['ph'], 7.2)
        self.assertEqual(sensor_data['ammonia'], 2.5)
        self.assertEqual(sensor_data['battery'], 90.0)
        
        # Check that summary fields are still present
        self.assertIn('pond_count', data)
        self.assertIn('is_complete', data)
        self.assertEqual(data['pond_count'], 2)
        self.assertTrue(data['is_complete'])
        
        # Check that new fields are present
        self.assertIn('battery_level', data)
        self.assertIn('device_status', data)
        
        # Check battery level
        self.assertEqual(data['battery_level'], 90.0)
        
        # Check device status
        self.assertIsNotNone(data['device_status'])
        device_status = data['device_status']
        self.assertEqual(device_status['status'], 'ONLINE')
        self.assertTrue(device_status['is_online'])
        self.assertEqual(device_status['firmware_version'], '1.2.3')
        self.assertEqual(device_status['hardware_version'], 'ESP32-V1')
        self.assertEqual(device_status['device_name'], 'Test Device')
        self.assertEqual(device_status['ip_address'], '192.168.1.100')
        self.assertEqual(device_status['wifi_ssid'], 'TestWiFi')
        self.assertEqual(device_status['wifi_signal_strength'], -45)
        self.assertEqual(device_status['error_count'], 0)
        self.assertIn('uptime_percentage_24h', device_status)
