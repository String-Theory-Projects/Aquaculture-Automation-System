from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

from dashboard.models import Pond, WiFiConfig, PondControl


class RegisterViewTest(TestCase):
    """Tests for the user registration endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.valid_payload = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
            'first_name': 'Test',
            'last_name': 'User'
        }
    
    def test_valid_registration(self):
        """Test that a user can register with valid credentials"""
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())
        self.assertIn('user', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
    
    def test_invalid_password_mismatch(self):
        """Test that registration fails if passwords don't match"""
        payload = self.valid_payload.copy()
        payload['password2'] = 'DifferentPassword123!'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
    
    def test_duplicate_username(self):
        """Test that registration fails with a duplicate username"""
        # Create a user first
        User.objects.create_user(
            username='testuser', 
            email='existing@example.com',
            password='ExistingPass123'
        )
        
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_duplicate_email(self):
        """Test that registration fails with a duplicate email"""
        # Create a user first
        User.objects.create_user(
            username='existinguser', 
            email='test@example.com',
            password='ExistingPass123'
        )
        
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_weak_password(self):
        """Test that registration fails with a weak password"""
        payload = self.valid_payload.copy()
        payload['password'] = 'weak'
        payload['password2'] = 'weak'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)


class CustomTokenObtainPairViewTest(TestCase):
    """Tests for the custom login endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('token_obtain_pair')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
    
    def test_login_with_username(self):
        """Test that a user can login with username"""
        payload = {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_login_with_email(self):
        """Test that a user can login with email"""
        payload = {
            'username': 'test@example.com',
            'password': 'TestPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_login_with_invalid_credentials(self):
        """Test that login fails with invalid credentials"""
        payload = {
            'username': 'testuser',
            'password': 'WrongPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_login_includes_pond_information(self):
        """Test that login response includes pond information when user has ponds"""
        # Create a pond for the user
        Pond.objects.create(
            name='Test Pond',
            owner=self.user,
            device_id='testdevice123'
        )
        
        payload = {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_ponds'])
        self.assertEqual(response.data['ponds_count'], 1)


class LogoutViewTest(TestCase):
    """Tests for the logout endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('token_obtain_pair')
        self.logout_url = reverse('logout')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Login and get refresh token
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.refresh_token = response.data['refresh']
        self.access_token = response.data['access']
        
    def test_logout_success(self):
        """Test that a user can successfully logout"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.logout_url, {'refresh': self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_logout_without_token(self):
        """Test that logout fails without a refresh token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.logout_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_logout_unauthorized(self):
        """Test that logout fails without authentication"""
        response = self.client.post(self.logout_url, {'refresh': self.refresh_token}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


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
        
        # Login and get token
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
        self.assertTrue(WiFiConfig.objects.filter(pond__device_id='testdevice123').exists())
    
    def test_register_pond_without_wifi(self):
        """Test that a pond can be registered without WiFi credentials"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Test Pond',
            'device_id': 'testdevice456'
        }
        response = self.client.post(self.register_pond_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Pond.objects.filter(device_id='testdevice456').exists())
        self.assertFalse(WiFiConfig.objects.filter(pond__device_id='testdevice456').exists())
    
    def test_register_duplicate_device_id(self):
        """Test that registering a pond with a duplicate device_id fails"""
        # Create a pond first
        Pond.objects.create(
            name='Existing Pond',
            owner=self.user,
            device_id='testdevice123'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.register_pond_url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_register_pond_unauthorized(self):
        """Test that pond registration fails without authentication"""
        response = self.client.post(self.register_pond_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileViewTest(TestCase):
    """Tests for the user profile endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.profile_url = reverse('user_profile')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        
        # Login and get token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
    
    def test_get_profile(self):
        """Test retrieving user profile information"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertFalse(response.data['has_ponds'])
    
    def test_get_profile_with_ponds(self):
        """Test retrieving profile with pond information"""
        # Create a pond for the user
        pond = Pond.objects.create(
            name='Test Pond',
            owner=self.user,
            device_id='testdevice123'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_ponds'])
        self.assertEqual(len(response.data['ponds']), 1)
        self.assertEqual(response.data['ponds'][0]['name'], 'Test Pond')
    
    def test_update_profile(self):
        """Test updating user profile information"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.put(self.profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
    
    def test_update_email(self):
        """Test updating user email"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'email': 'updated@example.com'
        }
        response = self.client.put(self.profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
    
    def test_profile_unauthorized(self):
        """Test that profile access fails without authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChangePasswordViewTest(TestCase):
    """Tests for the change password endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.change_password_url = reverse('change_password')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='OldPassword123!'
        )
        
        # Login and get token
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'OldPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
    
    def test_change_password_success(self):
        """Test successfully changing password"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'old_password': 'OldPassword123!',
            'new_password': 'NewPassword456!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
        
        # Verify new password works
        self.assertTrue(self.client.login(username='testuser', password='NewPassword456!'))
    
    def test_change_password_incorrect_old(self):
        """Test change password fails with incorrect old password"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'old_password': 'WrongOldPassword!',
            'new_password': 'NewPassword456!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_change_password_weak_new(self):
        """Test change password fails with weak new password"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'old_password': 'OldPassword123!',
            'new_password': 'weak'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_change_password_missing_fields(self):
        """Test change password fails with missing fields"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'old_password': 'OldPassword123!'
            # Missing new_password
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_change_password_unauthorized(self):
        """Test that password change fails without authentication"""
        payload = {
            'old_password': 'OldPassword123!',
            'new_password': 'NewPassword456!'
        }
        response = self.client.post(self.change_password_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
