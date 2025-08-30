from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import UserProfile, UserNotification


class UserProfileModelTest(TestCase):
    """Tests for UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        # Get the automatically created profile
        self.profile = self.user.profile
    
    def test_user_profile_creation_signal(self):
        """Test that user profile is created automatically via signal"""
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.role, 'OWNER')
        self.assertTrue(self.profile.is_active)
    
    def test_user_profile_defaults(self):
        """Test user profile default values"""
        self.assertEqual(self.profile.role, 'OWNER')
        self.assertTrue(self.profile.is_active)
        self.assertEqual(self.profile.phone_number, '')  # blank=True defaults to empty string
        self.assertEqual(self.profile.company_name, '')  # blank=True defaults to empty string
    
    def test_user_profile_one_to_one(self):
        """Test one-to-one relationship with User"""
        # Profile should already exist from signal
        self.assertEqual(UserProfile.objects.filter(user=self.user).count(), 1)
        
        # Should not be able to create another profile for same user
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserProfile.objects.create(user=self.user)
    
    def test_user_profile_str_representation(self):
        """Test string representation"""
        # String representation is just "Profile for {username}" regardless of company name
        self.assertEqual(str(self.profile), f"Profile for {self.user.username}")
        
        # Test that company name can be set and retrieved
        self.profile.company_name = 'Test Company'
        self.profile.save()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.company_name, 'Test Company')
    
    def test_user_profile_full_name(self):
        """Test full name property"""
        # User with first and last name
        self.user.first_name = 'Test'
        self.user.last_name = 'User'
        self.user.save()
        
        self.assertEqual(self.profile.full_name, 'Test User')
        
        # User without first and last name
        self.user.first_name = ''
        self.user.last_name = ''
        self.user.save()
        
        self.assertEqual(self.profile.full_name, 'testuser')
    
    def test_user_profile_update(self):
        """Test updating user profile"""
        self.profile.phone_number = '+1234567890'
        self.profile.company_name = 'Test Company'
        self.profile.role = 'ADMIN'
        self.profile.save()
        
        # Refresh from database
        self.profile.refresh_from_db()
        
        self.assertEqual(self.profile.phone_number, '+1234567890')
        self.assertEqual(self.profile.company_name, 'Test Company')
        self.assertEqual(self.profile.role, 'ADMIN')


class UserNotificationModelTest(TestCase):
    """Tests for UserNotification model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
    
    def test_user_notification_creation(self):
        """Test creating a user notification"""
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='EMAIL',
            is_enabled=True,
            settings={'frequency': 'daily', 'time': '09:00'}
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'EMAIL')
        self.assertTrue(notification.is_enabled)
        self.assertEqual(notification.settings, {'frequency': 'daily', 'time': '09:00'})
        self.assertIsNotNone(notification.created_at)
        self.assertIsNotNone(notification.updated_at)
    
    def test_user_notification_defaults(self):
        """Test user notification default values"""
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='SMS'
        )
        
        self.assertTrue(notification.is_enabled)
        self.assertEqual(notification.settings, {})
    
    def test_user_notification_unique_constraint(self):
        """Test unique constraint per user and notification type"""
        UserNotification.objects.create(
            user=self.user,
            notification_type='EMAIL'
        )
        
        # Same user and notification type should fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserNotification.objects.create(
                    user=self.user,
                    notification_type='EMAIL'
                )
        
        # Different notification type should work
        UserNotification.objects.create(
            user=self.user,
            notification_type='SMS'
        )
    
    def test_user_notification_str_representation(self):
        """Test string representation"""
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='PUSH'
        )
        
        self.assertIn(self.user.username, str(notification))
        self.assertIn('PUSH', str(notification))


class UserModelIntegrationTest(TestCase):
    """Tests for User model integration with custom models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_user_profile_creation_signal(self):
        """Test that user profile is created automatically"""
        # Profile should be created automatically via signal
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsNotNone(self.user.profile)
        self.assertEqual(self.user.profile.user, self.user)
    
    def test_user_notification_management(self):
        """Test user notification management"""
        # Create notification
        notification = UserNotification.objects.create(
            user=self.user,
            notification_type='EMAIL'
        )
        
        # Check notification exists
        self.assertTrue(UserNotification.objects.filter(
            user=self.user,
            notification_type='EMAIL'
        ).exists())
        
        # Check notification is enabled
        self.assertTrue(notification.is_enabled)
    
    def test_user_deletion_cascade(self):
        """Test that user deletion cascades properly"""
        # Create related objects
        UserNotification.objects.create(
            user=self.user,
            notification_type='EMAIL'
        )
        
        # Delete user
        self.user.delete()
        
        # Check related objects are deleted
        self.assertEqual(UserNotification.objects.count(), 0)
        self.assertEqual(UserProfile.objects.count(), 0)


class UserValidationTest(TestCase):
    """Tests for user validation and business rules"""
    
    def test_user_email_uniqueness(self):
        """Test user email uniqueness"""
        User.objects.create_user(
            username='user1',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Django doesn't enforce email uniqueness by default for the User model
        # So this should actually succeed
        user2 = User.objects.create_user(
            username='user2',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Both users should exist with the same email
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 2)
        self.assertEqual(user2.email, 'test@example.com')
    
    def test_user_username_uniqueness(self):
        """Test user username uniqueness"""
        User.objects.create_user(
            username='testuser',
            email='user1@example.com',
            password='TestPassword123!'
        )
        
        # Same username should fail
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    username='testuser',
                    email='user2@example.com',
                    password='TestPassword123!'
                )
    
    def test_user_password_validation(self):
        """Test user password validation"""
        # Valid password should work
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='StrongPassword123!'
        )
        
        # Check password is hashed
        self.assertNotEqual(user.password, 'StrongPassword123!')
        
        # Check password verification works
        self.assertTrue(user.check_password('StrongPassword123!'))
        self.assertFalse(user.check_password('WrongPassword'))

# ============================================================================
# AUTHENTICATION TESTS (moved from old testing)
# ============================================================================

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from ponds.models import Pond, PondPair


class RegisterViewTest(TestCase):
    """Tests for the user registration endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('users:register')
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
        payload['password'] = 'Password'
        payload['password2'] = 'Password'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)


class CustomTokenObtainPairViewTest(TestCase):
    """Tests for the custom token obtain pair view"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('users:login')
        self.logout_url = reverse('users:logout')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Login and get tokens
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.refresh_token = response.data['refresh']
    
    def test_successful_login(self):
        """Test successful login with valid credentials"""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        
        # Check user data
        user_data = response.data['user']
        self.assertEqual(user_data['username'], 'testuser')
        self.assertEqual(user_data['email'], 'test@example.com')
    
    def test_failed_login_invalid_username(self):
        """Test login failure with invalid username"""
        response = self.client.post(self.login_url, {
            'username': 'nonexistentuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_failed_login_invalid_password(self):
        """Test login failure with invalid password"""
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'WrongPassword123!'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_failed_login_missing_credentials(self):
        """Test login failure with missing credentials"""
        response = self.client.post(self.login_url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
        self.assertIn('password', response.data)
    
    def test_logout_success(self):
        """Test successful logout"""
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_logout_unauthenticated(self):
        """Test logout without authentication"""
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh(self):
        """Test token refresh functionality"""
        refresh_url = reverse('users:token_refresh')
        
        response = self.client.post(refresh_url, {
            'refresh': self.refresh_token
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # New access token should be different
        new_access_token = response.data['access']
        self.assertNotEqual(new_access_token, self.access_token)
    
    def test_token_refresh_invalid(self):
        """Test token refresh with invalid refresh token"""
        refresh_url = reverse('users:token_refresh')
        
        response = self.client.post(refresh_url, {
            'refresh': 'invalid_refresh_token'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_protected_endpoint_access(self):
        """Test access to protected endpoints with valid token"""
        # Create a test pond pair to test protected endpoint
        pond_pair = PondPair.objects.create(
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Try to access a protected endpoint (pond list)
        url = reverse('users:pond_list')
        response = self.client.get(url)
        
        # Should succeed with valid token
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_protected_endpoint_no_token(self):
        """Test access to protected endpoints without token"""
        # Try to access a protected endpoint without token
        url = reverse('users:pond_list')
        response = self.client.get(url)
        
        # Should fail without token
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_invalid_token(self):
        """Test access to protected endpoints with invalid token"""
        # Set invalid authentication header
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        # Try to access a protected endpoint
        url = reverse('users:pond_list')
        response = self.client.get(url)
        
        # Should fail with invalid token
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# ============================================================================
# PROFILE TESTS (moved from old testing)
# ============================================================================

class UpdateProfileViewTest(TestCase):
    """Tests for profile update endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!'
        )
        
        # Login and get token
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # URLs
        self.update_profile_url = reverse('users:update_profile')
        
        # Create another user for uniqueness tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
    
    def test_update_profile_name(self):
        """Test successful profile name update"""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['first_name'], 'Updated')
        self.assertEqual(response.data['user']['last_name'], 'Name')
    
    def test_update_email(self):
        """Test updating email address"""
        data = {'email': 'updated@example.com'}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'updated@example.com')
    
    def test_update_username(self):
        """Test updating username"""
        data = {'username': 'newusername'}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'newusername')
    
    def test_update_multiple_fields(self):
        """Test updating multiple profile fields at once"""
        data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'first_name': 'Updated',
            'last_name': 'User'
        }
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'updateduser')
        self.assertEqual(response.data['user']['email'], 'updated@example.com')
        self.assertEqual(response.data['user']['first_name'], 'Updated')
        self.assertEqual(response.data['user']['last_name'], 'User')
    
    def test_update_with_special_characters(self):
        """Test updating with special characters in fields"""
        data = {
            'first_name': 'José-María',
            'last_name': 'O\'Connor'
        }
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['first_name'], 'José-María')
        self.assertEqual(response.data['user']['last_name'], 'O\'Connor')
    
    def test_update_username_duplicate(self):
        """Test that updating to duplicate username fails"""
        # Create another user with the username we want to use
        User.objects.create_user(
            username='duplicateuser',
            email='duplicate@example.com',
            password='DuplicatePass123!'
        )
        
        data = {'username': 'duplicateuser'}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_update_email_duplicate(self):
        """Test that updating to duplicate email fails"""
        # Create another user with the email we want to use
        User.objects.create_user(
            username='duplicateuser',
            email='duplicate@example.com',
            password='DuplicatePass123!'
        )
        
        data = {'email': 'duplicate@example.com'}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_update_profile_unauthenticated(self):
        """Test that unauthenticated user cannot update profile"""
        self.client.credentials()  # Clear credentials
        
        data = {'first_name': 'Updated'}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_profile_partial(self):
        """Test partial profile updates"""
        # Update only first name
        data = {'first_name': 'Partial'}
        
        response = self.client.patch(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['first_name'], 'Partial')
        
        # Other fields should remain unchanged
        self.assertEqual(response.data['user']['last_name'], '')
        self.assertEqual(response.data['user']['email'], 'test@example.com')
    
    def test_update_profile_validation(self):
        """Test profile update validation"""
        # Test with invalid email format
        data = {'email': 'invalid-email'}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        
        # Test with empty username
        data = {'username': ''}
        
        response = self.client.put(self.update_profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_get_profile(self):
        """Test getting user profile"""
        response = self.client.get(self.update_profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['first_name'], '')
        self.assertEqual(response.data['last_name'], '')
    
    def test_get_profile_unauthenticated(self):
        """Test that unauthenticated user cannot get profile"""
        self.client.credentials()  # Clear credentials
        
        response = self.client.get(self.update_profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
