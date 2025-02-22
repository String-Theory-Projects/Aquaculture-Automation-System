from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from dashboard.models import Pond, WiFiConfig, AutomationSchedule


class BaseSettingsTest(TestCase):
    """Base test class with common setup"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Create another user for permission tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        
        # Create a test pond
        self.pond = Pond.objects.create(
            name='Test Pond',
            owner=self.user,
            device_id='TEST001',
            is_active=True
        )
        
        # Get authentication token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')


class WiFiConfigViewTest(BaseSettingsTest):
    """Tests for WiFi configuration endpoints"""
    
    def setUp(self):
        super().setUp()
        self.wifi_config_url = reverse('wifi_config', kwargs={'pond_id': self.pond.id})
    
    def test_create_wifi_config(self):
        """Test creating new WiFi configuration"""
        payload = {
            'ssid': 'TestNetwork',
            'password': 'TestPassword123'
        }
        response = self.client.post(self.wifi_config_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(WiFiConfig.objects.count(), 1)
        self.assertEqual(WiFiConfig.objects.get().ssid, 'TestNetwork')
    
    def test_get_wifi_config(self):
        """Test retrieving WiFi configuration"""
        # Create WiFi config
        WiFiConfig.objects.create(
            pond=self.pond,
            ssid='TestNetwork',
            password='TestPassword123'
        )
        
        response = self.client.get(self.wifi_config_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ssid'], 'TestNetwork')
        self.assertNotIn('password', response.data)  # Password should not be returned
    
    def test_update_wifi_config(self):
        """Test updating WiFi configuration"""
        wifi_config = WiFiConfig.objects.create(
            pond=self.pond,
            ssid='OldNetwork',
            password='OldPassword123'
        )
        
        payload = {
            'ssid': 'NewNetwork',
            'password': 'NewPassword123'
        }
        response = self.client.put(self.wifi_config_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        wifi_config.refresh_from_db()
        self.assertEqual(wifi_config.ssid, 'NewNetwork')
        self.assertFalse(wifi_config.is_config_synced)  # Should be marked as not synced
    
    def test_delete_wifi_config(self):
        """Test deleting WiFi configuration"""
        WiFiConfig.objects.create(
            pond=self.pond,
            ssid='TestNetwork',
            password='TestPassword123'
        )
        
        response = self.client.delete(self.wifi_config_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(WiFiConfig.objects.count(), 0)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to WiFi configuration"""
        self.client.credentials()  # Clear credentials
        response = self.client.get(self.wifi_config_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_wrong_user_access(self):
        """Test accessing WiFi config of another user's pond"""
        # Create pond owned by other user
        other_pond = Pond.objects.create(
            name='Other Pond',
            owner=self.other_user,
            device_id='TEST002',
            is_active=True
        )
        
        url = reverse('wifi_config', kwargs={'pond_id': other_pond.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AutomationScheduleViewTest(BaseSettingsTest):
    """Tests for automation schedule endpoints"""
    
    def setUp(self):
        super().setUp()
        self.schedules_url = reverse('automation_schedules', kwargs={'pond_id': self.pond.id})
    
    def test_create_feeding_schedule(self):
        """Test creating new feeding schedule"""
        payload = {
            'automation_type': 'FEED',
            'is_active': True,
            'time': '08:00:00',
            'days': '1,2,3,4,5',
            'feed_amount': 50.0
        }
        response = self.client.post(self.schedules_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AutomationSchedule.objects.count(), 1)
        schedule = AutomationSchedule.objects.first()
        self.assertEqual(schedule.automation_type, 'FEED')
        self.assertEqual(schedule.feed_amount, 50.0)
    
    def test_create_water_change_schedule(self):
        """Test creating new water change schedule"""
        payload = {
            'automation_type': 'WATER',
            'is_active': True,
            'time': '09:00:00',
            'days': '0,6',
            'target_water_level': 90.0
        }
        response = self.client.post(self.schedules_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        schedule = AutomationSchedule.objects.first()
        self.assertEqual(schedule.automation_type, 'WATER')
        self.assertEqual(schedule.target_water_level, 90.0)
    
    def test_get_schedules(self):
        """Test retrieving automation schedules"""
        # Create test schedules
        AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            time='08:00:00',
            days='1,2,3,4,5',
            feed_amount=50.0
        )
        AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='WATER',
            time='09:00:00',
            days='0,6',
            target_water_level=90.0
        )
        
        response = self.client.get(self.schedules_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_invalid_schedule_data(self):
        """Test validation of schedule data"""
        # Test missing feed amount
        payload = {
            'automation_type': 'FEED',
            'is_active': True,
            'time': '08:00:00',
            'days': '1,2,3,4,5'
        }
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test invalid days format
        payload = {
            'automation_type': 'FEED',
            'is_active': True,
            'time': '08:00:00',
            'days': '1,2,8',  # 8 is invalid day
            'feed_amount': 50.0
        }
        response = self.client.post(self.schedules_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AutomationScheduleDetailViewTest(BaseSettingsTest):
    """Tests for individual automation schedule endpoints"""
    
    def setUp(self):
        super().setUp()
        self.schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            time='08:00:00',
            days='1,2,3,4,5',
            feed_amount=50.0
        )
        self.detail_url = reverse('automation_schedule_detail', kwargs={'schedule_id': self.schedule.id})
    
    def test_get_schedule(self):
        """Test retrieving specific schedule"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['automation_type'], 'FEED')
        self.assertEqual(response.data['feed_amount'], 50.0)
    
    def test_update_schedule(self):
        """Test updating schedule"""
        payload = {
            'feed_amount': 75.0,
            'days': '1,2,3,4,5,6',
            'is_active': False
        }
        response = self.client.put(self.detail_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.schedule.refresh_from_db()
        self.assertEqual(self.schedule.feed_amount, 75.0)
        self.assertFalse(self.schedule.is_active)
    
    def test_delete_schedule(self):
        """Test deleting schedule"""
        response = self.client.delete(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AutomationSchedule.objects.count(), 0)
    
    def test_wrong_user_access(self):
        """Test accessing schedule of another user's pond"""
        # Create pond and schedule for other user
        other_pond = Pond.objects.create(
            name='Other Pond',
            owner=self.other_user,
            device_id='TEST002',
            is_active=True
        )
        other_schedule = AutomationSchedule.objects.create(
            pond=other_pond,
            automation_type='FEED',
            time='08:00:00',
            days='1,2,3,4,5',
            feed_amount=50.0
        )
        
        url = reverse('automation_schedule_detail', kwargs={'schedule_id': other_schedule.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
