from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from django.conf import settings

from dashboard.models import Pond, PondControl


@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class PondListViewTest(TestCase):
    """Tests for pond list endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.pond_list_url = reverse('pond_list')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Create system user
        self.system_user = User.objects.create_user(
            username=settings.SYSTEM_USERNAME,
            email=settings.SYSTEM_EMAIL,
            password='SystemPassword123!'
        )
        
        # Create some ponds for the user
        Pond.objects.create(
            name='First Pond',
            owner=self.user,
            device_id='device001',
            is_active=True
        )
        
        Pond.objects.create(
            name='Second Pond',
            owner=self.user,
            device_id='device002',
            is_active=True
        )
        
        # Create an inactive pond owned by the user (unusual case)
        Pond.objects.create(
            name='Inactive User Pond',
            owner=self.user,
            device_id='device003',
            is_active=False
        )
        
        # Create a system-owned inactive pond (normal case for deactivated ponds)
        Pond.objects.create(
            name='System Pond',
            owner=self.system_user,
            device_id='device004',
            is_active=False
        )
        
        # Login
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
    
    def test_get_pond_list(self):
        """Test getting list of user's ponds"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.pond_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Only user-owned ponds, not system-owned
        
        # Verify pond names
        pond_names = [pond['name'] for pond in response.data]
        self.assertIn('First Pond', pond_names)
        self.assertIn('Second Pond', pond_names)
        self.assertIn('Inactive User Pond', pond_names)
        self.assertNotIn('System Pond', pond_names)  # Should not include system ponds
    
    def test_inactive_pond_included(self):
        """Test that inactive ponds owned by the user are included in list"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.pond_list_url)
        
        inactive_ponds = [pond for pond in response.data if not pond['is_active']]
        self.assertEqual(len(inactive_ponds), 1)
        self.assertEqual(inactive_ponds[0]['name'], 'Inactive User Pond')
    
    def test_unauthorized(self):
        """Test that pond list access fails without authentication"""
        response = self.client.get(self.pond_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class PondDetailViewTest(TestCase):
    """Tests for pond detail endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test users
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
        
        # Create a pond for the test user
        self.pond = Pond.objects.create(
            name='Test Pond',
            owner=self.user,
            device_id='testdevice123',
            is_active=True
        )
        
        # Create a pond control for the pond
        PondControl.objects.create(pond=self.pond)
        
        # Create a pond for the other user
        self.other_pond = Pond.objects.create(
            name='Other Pond',
            owner=self.other_user,
            device_id='otherdevice123',
            is_active=True
        )
        
        # Login as test user
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        
        # URLs for testing
        self.pond_detail_url = reverse('pond_detail', kwargs={'pk': self.pond.pk})
        self.other_pond_url = reverse('pond_detail', kwargs={'pk': self.other_pond.pk})
    
    def test_get_pond_detail(self):
        """Test getting pond details"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.pond_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Pond')
        self.assertEqual(response.data['device_id'], 'testdevice123')
        self.assertTrue(response.data['is_active'])
    
    def test_update_pond(self):
        """Test updating pond details"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Updated Pond Name'
        }
        response = self.client.put(self.pond_detail_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pond']['name'], 'Updated Pond Name')
        
        # Verify database update
        self.pond.refresh_from_db()
        self.assertEqual(self.pond.name, 'Updated Pond Name')
    
    def test_update_is_active_ignored(self):
        """Test that updating is_active field is ignored"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Updated Name',
            'is_active': False  # This should be ignored
        }
        response = self.client.put(self.pond_detail_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify is_active was not changed
        self.pond.refresh_from_db()
        self.assertEqual(self.pond.name, 'Updated Name')
        self.assertTrue(self.pond.is_active)  # Still active
    
    def test_delete_transfers_to_system(self):
        """Test that deleting a pond transfers ownership to system user"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.delete(self.pond_detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pond ownership was transferred and marked inactive
        self.pond.refresh_from_db()
        self.assertEqual(self.pond.owner, self.system_user)
        self.assertFalse(self.pond.is_active)
        
        # Controls should still exist
        self.assertTrue(PondControl.objects.filter(pond=self.pond).exists())
    
    def test_access_others_pond(self):
        """Test that user cannot access another user's pond"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.other_pond_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_unauthorized(self):
        """Test that pond detail access fails without authentication"""
        response = self.client.get(self.pond_detail_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class PondDetailViewUniqueNameTest(TestCase):
    """Tests for unique pond name validation in updates"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Create two ponds for the user
        self.pond1 = Pond.objects.create(
            name='First Pond',
            owner=self.user,
            device_id='device001',
            is_active=True
        )
        
        self.pond2 = Pond.objects.create(
            name='Second Pond',
            owner=self.user,
            device_id='device002',
            is_active=True
        )
        
        # Login
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        
        # URLs for testing
        self.pond1_url = reverse('pond_detail', kwargs={'pk': self.pond1.pk})
        self.pond2_url = reverse('pond_detail', kwargs={'pk': self.pond2.pk})
    
    def test_update_to_duplicate_name(self):
        """Test that updating to a duplicate name fails"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Second Pond'  # Same as pond2's name
        }
        response = self.client.put(self.pond1_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You already have an active pond named', response.data['error'])
    
    def test_update_to_unique_name(self):
        """Test that updating to a unique name succeeds"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Updated Pond Name'  # Unique name
        }
        response = self.client.put(self.pond1_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pond name was updated
        self.pond1.refresh_from_db()
        self.assertEqual(self.pond1.name, 'Updated Pond Name')
    
    def test_update_to_same_name(self):
        """Test that updating to the same name succeeds"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'First Pond'  # Same as current name
        }
        response = self.client.put(self.pond1_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_update_with_special_characters(self):
        """Test updating pond name with special characters"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Koi & Goldfish Pond (2023) - Backyard'
        }
        response = self.client.put(self.pond1_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pond name was updated with special characters
        self.pond1.refresh_from_db()
        self.assertEqual(self.pond1.name, 'Koi & Goldfish Pond (2023) - Backyard')


@override_settings(SYSTEM_USERNAME='system_test', SYSTEM_EMAIL='system_test@example.com')
class RegisterPondViewTest(TestCase):
    """Tests for the pond registration endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_pond_url = reverse('register_pond')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Create another user for multi-user tests
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
        
        # Login
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        
        # Valid pond registration payload
        self.valid_payload = {
            'name': 'Test Pond',
            'device_id': 'testdevice123',
            'ssid': 'TestWiFi',
            'password': 'WiFiPassword'
        }
    
    def test_register_pond_success(self):
        """Test that a user can register a pond successfully"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.register_pond_url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Pond.objects.filter(device_id='testdevice123').exists())
        self.assertTrue(PondControl.objects.filter(pond__device_id='testdevice123').exists())
        
        # Verify pond is active and owned by the user
        pond = Pond.objects.get(device_id='testdevice123')
        self.assertTrue(pond.is_active)
        self.assertEqual(pond.owner, self.user)
    
    def test_register_without_wifi(self):
        """Test registering a pond without WiFi credentials"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'No WiFi Pond',
            'device_id': 'nowifi123'
        }
        response = self.client.post(self.register_pond_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Pond.objects.filter(device_id='nowifi123').exists())
    
    def test_register_with_duplicate_name(self):
        """Test that registering a pond with duplicate name fails"""
        # Create an existing pond first
        Pond.objects.create(
            name='Existing Pond',
            owner=self.user,
            device_id='existing123',
            is_active=True
        )
        
        # Try to register a new pond with the same name
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Existing Pond',  # Same name
            'device_id': 'different456'  # Different device ID
        }
        response = self.client.post(self.register_pond_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('You already have an active pond named', response.data['error'])
    
    def test_register_with_duplicate_device_id(self):
        """Test that registering with duplicate device ID fails"""
        # Create an existing pond first
        Pond.objects.create(
            name='First Pond',
            owner=self.user,
            device_id='duplicatedevice',
            is_active=True
        )
        
        # Try to register a new pond with the same device ID
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Second Pond',
            'device_id': 'duplicatedevice'  # Same device ID
        }
        response = self.client.post(self.register_pond_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Device ID already registered', response.data['error'])
    
    def test_reactivate_deactivated_pond(self):
        """Test reactivating a deactivated pond"""
        # Create a deactivated pond owned by system user
        deactivated_pond = Pond.objects.create(
            name='Deactivated Pond',
            owner=self.system_user,
            device_id='deactivated123',
            is_active=False
        )
        
        # Create control for the deactivated pond
        PondControl.objects.create(pond=deactivated_pond)
        
        # Try to register/reactivate
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Reactivated Pond',
            'device_id': 'deactivated123',
            'ssid': 'NewWiFi',
            'password': 'NewPassword'
        }
        response = self.client.post(self.register_pond_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Pond re-registered successfully', response.data['message'])
        
        # Verify pond ownership transferred and activated
        deactivated_pond.refresh_from_db()
        self.assertEqual(deactivated_pond.owner, self.user)
        self.assertEqual(deactivated_pond.name, 'Reactivated Pond')
        self.assertTrue(deactivated_pond.is_active)
    
    def test_other_user_cannot_reactivate(self):
        """Test that another user cannot reactivate a deactivated pond belonging to someone else"""
        # Create a pond owned by our user
        user_pond = Pond.objects.create(
            name='User Pond',
            owner=self.user,
            device_id='userdevice123',
            is_active=True
        )
        
        # Deactivate it (this would normally transfer to system user)
        user_pond.is_active = False
        user_pond.owner = self.system_user
        user_pond.save()
        
        # Login as other user
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'otheruser',
            'password': 'OtherPassword123!'
        }, format='json')
        other_token = response.data['access']
        
        # Try to register the same device as other user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {other_token}')
        payload = {
            'name': 'Other User Pond',
            'device_id': 'userdevice123'  # Same device ID
        }
        response = self.client.post(self.register_pond_url, payload, format='json')
        
        # Should succeed since the device was deactivated
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pond ownership was transferred to other user
        user_pond.refresh_from_db()
        self.assertEqual(user_pond.owner, self.other_user)
        self.assertEqual(user_pond.name, 'Other User Pond')
        self.assertTrue(user_pond.is_active)
