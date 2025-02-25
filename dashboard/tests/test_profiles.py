from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status


class UpdateProfileViewTest(TestCase):
    """Tests for profile update endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.update_profile_url = reverse('update_profile')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        
        # Create another user for uniqueness tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        
        # Login
        response = self.client.post(reverse('token_obtain_pair'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
    
    def test_update_profile_name(self):
        """Test successful profile name update"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['first_name'], 'Updated')
        self.assertEqual(response.data['user']['last_name'], 'Name')
        
        # Verify database update
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
    
    def test_update_email(self):
        """Test updating email address"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'email': 'updated@example.com'
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'updated@example.com')
        
        # Verify database update
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'updated@example.com')
        
        # Verify new tokens are provided
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
    
    def test_update_username(self):
        """Test updating username"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'username': 'newusername'
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'newusername')
        
        # Verify database update
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')
        
        # Verify new tokens are provided
        self.assertIn('refresh', response.data)
        self.assertIn('access', response.data)
    
    def test_update_multiple_fields(self):
        """Test updating multiple profile fields at once"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'username': 'updateduser',
            'email': 'new@example.com',
            'first_name': 'NewFirst',
            'last_name': 'NewLast'
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], 'updateduser')
        self.assertEqual(response.data['user']['email'], 'new@example.com')
        self.assertEqual(response.data['user']['first_name'], 'NewFirst')
        self.assertEqual(response.data['user']['last_name'], 'NewLast')
    
    def test_update_with_invalid_email(self):
        """Test updating with invalid email format"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'email': 'not-an-email'
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_update_with_duplicate_email(self):
        """Test updating with an email that already exists"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'email': 'other@example.com'  # Email of other_user
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_update_with_duplicate_username(self):
        """Test updating with a username that already exists"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'username': 'otheruser'  # Username of other_user
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)
    
    def test_update_with_special_characters(self):
        """Test updating with special characters in fields"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'first_name': 'José-María',
            'last_name': "O'Connor-Smith"
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['first_name'], 'José-María')
        self.assertEqual(response.data['user']['last_name'], "O'Connor-Smith")
    
    def test_update_unauthorized(self):
        """Test that profile update fails without authentication"""
        payload = {
            'first_name': 'Unauthorized'
        }
        response = self.client.put(self.update_profile_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
