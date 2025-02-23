from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta
from unittest.mock import patch
from dashboard.models import Pond, SensorData

class AnalyticsViewsTest(APITestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test pond
        self.pond = Pond.objects.create(
            name='Test Pond',
            owner=self.user,
            device_id='TEST001'
        )
        
        # Setup client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create sample data
        self.now = timezone.now()
        self.create_sample_data()

    def create_sample_data(self):
        """Create 24 hours of test data with hourly intervals, overriding auto_now_add timestamps."""
        # Clear any existing data
        SensorData.objects.all().delete()
        
        # Start from the beginning of the current hour (rounded down)
        start_time = self.now.replace(minute=0, second=0, microsecond=0)
        
        # Create data for exactly 24 hours, including the current hour
        for hour in range(24):
            hour_time = start_time - timedelta(hours=hour)
            
            # Create three readings per hour
            for minute in [0, 20, 40]:
                # Create the record, which will get the auto_now_add timestamp
                sensor = SensorData.objects.create(
                    pond=self.pond,
                    temperature=25.0,
                    water_level=80.0,
                    turbidity=10.0,
                    dissolved_oxygen=7.0,
                    ph=7.2,
                    feed_level=90.0,
                )
                # Override the auto-added timestamp with the desired value
                sensor.timestamp = hour_time + timedelta(minutes=minute)
                sensor.save(update_fields=['timestamp'])

    def test_current_data_authenticated(self):
        """Test current data endpoint with authentication"""
        url = reverse('dashboard_current_data')
        response = self.client.get(f'{url}?pond_id={self.pond.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_data', response.data)
        self.assertEqual(len(response.data['current_data']), 7)  # All sensor fields

    def test_current_data_unauthenticated(self):
        """Test current data endpoint without authentication"""
        self.client.force_authenticate(user=None)
        url = reverse('dashboard_current_data')
        response = self.client.get(f'{url}?pond_id={self.pond.id}')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_historical_data_24h(self):
        """Test historical data endpoint with 24h range"""
        url = reverse('dashboard_historical_data')
        response = self.client.get(f'{url}?pond_id={self.pond.id}&range=24h')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('historical_data', response.data)
        self.assertIn('time_range', response.data)
        self.assertEqual(response.data['time_range'], '24h')
        
        print(f"Number of data points: {len(response.data['historical_data'])}")
        print(f"First data point: {response.data['historical_data'][0]}")
        
        # Should have 24 hourly data points
        self.assertEqual(len(response.data['historical_data']), 24)

    def test_historical_data_invalid_range(self):
        """Test historical data endpoint with invalid range"""
        url = reverse('dashboard_historical_data')
        response = self.client.get(f'{url}?pond_id={self.pond.id}&range=invalid')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Falls back to 24h
        self.assertEqual(response.data['time_range'], '24h')

    def test_historical_data_missing_pond(self):
        """Test historical data endpoint with missing pond_id"""
        url = reverse('dashboard_historical_data')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_historical_data_invalid_pond(self):
        """Test historical data endpoint with invalid pond_id"""
        url = reverse('dashboard_historical_data')
        response = self.client.get(f'{url}?pond_id=999')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_ponds_dropdown(self):
        """Test user ponds dropdown endpoint"""
        url = reverse('user_ponds_dropdown')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # One test pond
        self.assertEqual(response.data[0]['id'], self.pond.id)

    def test_aggregation_accuracy(self):
        """Test accuracy of data aggregation"""
        # Clear existing data
        SensorData.objects.all().delete()
        
        # Create test data for a specific hour
        test_hour = self.now.replace(minute=0, second=0, microsecond=0)
        values = [25.0, 26.0, 27.0]
        expected_avg = sum(values) / len(values)
        
        # Create readings within the same hour
        for i, value in enumerate(values):
            SensorData.objects.create(
                pond=self.pond,
                timestamp=test_hour + timedelta(minutes=i*20),
                temperature=value,
                water_level=80.0,
                turbidity=10.0,
                dissolved_oxygen=7.0,
                ph=7.2,
                feed_level=90.0
            )

        url = reverse('dashboard_historical_data')
        response = self.client.get(f'{url}?pond_id={self.pond.id}&range=24h')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Debug print
        print(f"Response data: {response.data}")
        print(f"Looking for hour: {test_hour.isoformat()[:13]}")
        
        # Find the relevant hour in response
        test_data = next(
            (d for d in response.data['historical_data'] 
             if d['timestamp'].startswith(test_hour.isoformat()[:13])),
            None
        )
        
        self.assertIsNotNone(test_data, "Could not find test hour in response data")
        self.assertAlmostEqual(test_data['temperature'], expected_avg, places=2)

    def test_data_format(self):
        """Test response data format"""
        url = reverse('dashboard_historical_data')
        response = self.client.get(f'{url}?pond_id={self.pond.id}&range=24h')
        
        # Check first data point structure
        data_point = response.data['historical_data'][0]
        expected_fields = {
            'timestamp', 'temperature', 'water_level', 'turbidity',
            'dissolved_oxygen', 'ph', 'feed_level'
        }
        
        self.assertEqual(set(data_point.keys()), expected_fields)
