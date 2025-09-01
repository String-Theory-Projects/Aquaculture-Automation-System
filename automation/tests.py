from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
import time
from .models import (
    AutomationExecution, DeviceCommand, AutomationSchedule, 
    FeedEvent, FeedStat, FeedStatHistory
)
from ponds.models import PondPair, Pond
from automation.services import AutomationService
from datetime import timedelta
from unittest.mock import patch


class AutomationExecutionModelTest(TestCase):
    """Tests for AutomationExecution model"""
    
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
    
    def test_automation_execution_creation(self):
        """Test creating an automation execution"""
        execution = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING'
        )
        
        self.assertEqual(execution.execution_type, 'FEED')
        self.assertEqual(execution.action, 'FEED')
        self.assertEqual(execution.priority, 'THRESHOLD')
        self.assertEqual(execution.status, 'PENDING')
        self.assertTrue(execution.success)
    
    def test_execution_lifecycle(self):
        """Test execution lifecycle methods"""
        execution = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING'
        )
        
        # Start execution
        execution.start_execution()
        self.assertEqual(execution.status, 'EXECUTING')
        self.assertIsNotNone(execution.started_at)
        
        # Complete execution
        execution.complete_execution(
            success=True, 
            message='Feed completed successfully'
        )
        self.assertEqual(execution.status, 'COMPLETED')
        self.assertTrue(execution.success)
        self.assertEqual(execution.result_message, 'Feed completed successfully')
        self.assertIsNotNone(execution.completed_at)
    
    def test_execution_cancellation(self):
        """Test execution cancellation"""
        execution = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING'
        )
        
        execution.cancel_execution()
        self.assertEqual(execution.status, 'CANCELLED')
        self.assertIsNotNone(execution.completed_at)
    
    def test_execution_executability(self):
        """Test execution executability check"""
        # Pending execution without scheduled time
        execution1 = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING'
        )
        # Should not be executable without scheduled time
        self.assertFalse(execution1.is_executable())
        
        # Pending execution with scheduled time in the past
        execution2 = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertTrue(execution2.is_executable())
        
        # Non-pending execution
        execution3 = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='COMPLETED'
        )
        self.assertFalse(execution3.is_executable())

    def test_automation_execution_failure_handling(self):
        """Test that automations are properly marked as failed when MQTT commands fail"""
        # Test automation that fails to send MQTT command
        with patch('automation.services.get_mqtt_bridge_service') as mock_mqtt:
            mock_mqtt.return_value.send_feed_command.return_value = None
            
            service = AutomationService()
            execution = service.execute_manual_automation(
                pond=self.pond,
                action='FEED',
                parameters={'feed_amount': 100},
                user=self.user
            )
            
            # Should be marked as failed immediately
            self.assertEqual(execution.status, 'FAILED')
            self.assertFalse(execution.success)
            self.assertIn('Failed to send MQTT command', execution.result_message)
            self.assertIsNotNone(execution.completed_at)
    
    def test_automation_execution_exception_handling(self):
        """Test that automations are properly marked as failed when exceptions occur"""
        # Test automation that throws an exception during MQTT command sending
        with patch('automation.services.get_mqtt_bridge_service') as mock_mqtt:
            mock_mqtt.return_value.send_feed_command.side_effect = Exception("MQTT connection failed")
            
            service = AutomationService()
            execution = service.execute_manual_automation(
                pond=self.pond,
                action='FEED',
                parameters={'feed_amount': 100},
                user=self.user
            )
            
            # Should be marked as failed immediately
            self.assertEqual(execution.status, 'FAILED')
            self.assertFalse(execution.success)
            self.assertIn('MQTT command error', execution.result_message)
            self.assertIn('MQTT connection failed', execution.error_details)
            self.assertIsNotNone(execution.completed_at)
    
    def test_automation_timeout_protection(self):
        """Test that automations are protected from getting stuck indefinitely"""
        # Create an automation that has been executing for too long
        execution = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='MANUAL_COMMAND',
            status='EXECUTING',
            started_at=timezone.now() - timedelta(hours=3),  # 3 hours ago
            scheduled_at=timezone.now() - timedelta(hours=3),
            user=self.user,
            parameters={'feed_amount': 100}
        )
        
        # The automation should be considered stuck
        execution_time = timezone.now() - execution.started_at
        self.assertGreater(execution_time.total_seconds(), 7200)  # 2 hours
        
        # Test that the cleanup task would mark this as failed
        from mqtt_client.tasks import cleanup_stuck_automations
        result = cleanup_stuck_automations.delay()
        
        # Wait for task completion
        result.get(timeout=10)
        
        # Refresh from database
        execution.refresh_from_db()
        
        # Should now be marked as failed
        self.assertEqual(execution.status, 'FAILED')
        self.assertFalse(execution.success)
        self.assertIn('cleanup task', execution.result_message.lower())
    
    def test_automation_status_filtering(self):
        """Test that stuck automations are filtered out from API responses"""
        # Create a stuck automation
        stuck_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='MANUAL_COMMAND',
            status='EXECUTING',
            started_at=timezone.now() - timedelta(hours=3),  # 3 hours ago
            scheduled_at=timezone.now() - timedelta(hours=3),
            user=self.user,
            parameters={'feed_amount': 100}
        )
        
        # Create a normal automation
        normal_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='MANUAL_COMMAND',
            status='COMPLETED',
            started_at=timezone.now() - timedelta(minutes=30),
            completed_at=timezone.now() - timedelta(minutes=25),
            scheduled_at=timezone.now() - timedelta(minutes=30),
            user=self.user,
            parameters={'feed_amount': 100},
            success=True,
            result_message='Feed completed successfully'
        )
        
        # Test that the API view filters out stuck automations
        from automation.views import GetDeviceStatusView
        from rest_framework.test import APIRequestFactory
        from rest_framework.test import force_authenticate
        
        factory = APIRequestFactory()
        request = factory.get(f'/automation/ponds/{self.pond.id}/device/status/')
        force_authenticate(request, user=self.user)
        
        view = GetDeviceStatusView.as_view()
        response = view(request, pond_id=self.pond.id)
        
        # Should only show the normal automation, not the stuck one
        execution_data = response.data['data']['recent_executions']
        execution_ids = [execution['id'] for execution in execution_data]
        
        self.assertIn(normal_automation.id, execution_ids)
        self.assertNotIn(stuck_automation.id, execution_ids)
    
    def test_manual_cleanup_endpoint(self):
        """Test the manual cleanup endpoint for stuck automations"""
        # Create a stuck automation
        stuck_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='MANUAL_COMMAND',
            status='EXECUTING',
            started_at=timezone.now() - timedelta(hours=2),  # 2 hours ago
            scheduled_at=timezone.now() - timedelta(hours=2),
            user=self.user,
            parameters={'feed_amount': 100}
        )
        
        # Test the cleanup endpoint
        from automation.views import CleanupStuckAutomationsView
        from rest_framework.test import APIRequestFactory
        from rest_framework.test import force_authenticate
        
        factory = APIRequestFactory()
        request = factory.post(f'/automation/ponds/{self.pond.id}/cleanup-stuck/', {
            'timeout_hours': 1
        })
        force_authenticate(request, user=self.user)
        
        view = CleanupStuckAutomationsView.as_view()
        response = view(request, pond_id=self.pond.id)
        
        # Should be successful
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        
        # Should have cleaned up the stuck automation
        self.assertEqual(response.data['data']['cleaned_count'], 1)
        self.assertEqual(response.data['data']['stuck_count'], 1)
        
        # Refresh from database
        stuck_automation.refresh_from_db()
        
        # Should now be marked as failed
        self.assertEqual(stuck_automation.status, 'FAILED')
        self.assertFalse(stuck_automation.success)
        self.assertIn('Manually marked as failed', stuck_automation.result_message)


class DeviceCommandModelTest(TestCase):
    """Tests for DeviceCommand model"""
    
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
    
    def test_device_command_creation(self):
        """Test creating a device command"""
        command = DeviceCommand.objects.create(
            pond=self.pond,
            command_type='FEED',
            status='PENDING',
            parameters={'amount': 100, 'duration': 30}
        )
        
        self.assertEqual(command.command_type, 'FEED')
        self.assertEqual(command.status, 'PENDING')
        self.assertEqual(command.parameters, {'amount': 100, 'duration': 30})
        self.assertIsNotNone(command.command_id)
        self.assertEqual(command.retry_count, 0)
        self.assertEqual(command.max_retries, 3)
    
    def test_command_lifecycle(self):
        """Test command lifecycle methods"""
        command = DeviceCommand.objects.create(
            pond=self.pond,
            command_type='FEED',
            status='PENDING'
        )
        
        # Send command
        command.send_command()
        self.assertEqual(command.status, 'SENT')
        self.assertIsNotNone(command.sent_at)
        
        # Acknowledge command
        command.acknowledge_command()
        self.assertEqual(command.status, 'ACKNOWLEDGED')
        self.assertIsNotNone(command.acknowledged_at)
        
        # Complete command
        command.complete_command(
            success=True, 
            message='Feed command completed'
        )
        self.assertEqual(command.status, 'COMPLETED')
        self.assertTrue(command.success)
        self.assertEqual(command.result_message, 'Feed command completed')
        self.assertIsNotNone(command.completed_at)
    
    def test_command_timeout(self):
        """Test command timeout"""
        command = DeviceCommand.objects.create(
            pond=self.pond,
            command_type='FEED',
            status='SENT',
            sent_at=timezone.now()
        )
        
        command.timeout_command()
        self.assertEqual(command.status, 'TIMEOUT')
        self.assertIsNotNone(command.completed_at)
    
    def test_command_retry(self):
        """Test command retry logic"""
        command = DeviceCommand.objects.create(
            pond=self.pond,
            command_type='FEED',
            status='FAILED',
            retry_count=1
        )
        
        # Should be able to retry
        self.assertTrue(command.is_retryable())
        self.assertTrue(command.retry_command())
        self.assertEqual(command.status, 'PENDING')
        self.assertEqual(command.retry_count, 2)
        self.assertIsNone(command.sent_at)
        self.assertIsNone(command.acknowledged_at)
        
        # Should not be able to retry after max attempts
        command.status = 'FAILED'
        command.retry_count = 3
        self.assertFalse(command.is_retryable())
        self.assertFalse(command.retry_command())
    
    def test_command_expiration(self):
        """Test command expiration check"""
        command = DeviceCommand.objects.create(
            pond=self.pond,
            command_type='FEED',
            status='SENT',
            sent_at=timezone.now() - timezone.timedelta(seconds=15),
            timeout_seconds=10
        )
        
        self.assertTrue(command.is_expired())
        
        # Non-expired command
        command.sent_at = timezone.now()
        self.assertFalse(command.is_expired())


class AutomationScheduleModelTest(TestCase):
    """Tests for AutomationSchedule model"""
    
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
    
    def test_schedule_creation(self):
        """Test creating an automation schedule"""
        schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            is_active=True,
            time=timezone.now().time(),
            days='0,1,2,3,4,5,6',
            feed_amount=100.0,
            priority=1,
            user=self.user
        )
        
        self.assertEqual(schedule.automation_type, 'FEED')
        self.assertTrue(schedule.is_active)
        self.assertEqual(schedule.feed_amount, 100.0)
        self.assertEqual(schedule.priority, 1)
        self.assertEqual(schedule.user, self.user)
    
    def test_schedule_validation(self):
        """Test schedule validation"""
        # Feed schedule without amount should fail
        with self.assertRaises(ValidationError):
            schedule = AutomationSchedule(
                pond=self.pond,
                automation_type='FEED',
                time=timezone.now().time(),
                days='0,1,2,3,4,5,6',
                user=self.user
            )
            schedule.full_clean()
        
        # Water schedule without parameters should fail
        with self.assertRaises(ValidationError):
            schedule = AutomationSchedule(
                pond=self.pond,
                automation_type='WATER',
                time=timezone.now().time(),
                days='0,1,2,3,4,5,6',
                user=self.user
            )
            schedule.full_clean()
    
    def test_next_execution_calculation(self):
        """Test next execution calculation"""
        schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            time=timezone.now().time(),
            days='0,1,2,3,4,5,6',
            feed_amount=100.0,
            user=self.user
        )
        
        next_exec = schedule.get_next_execution()
        self.assertIsNotNone(next_exec)
        self.assertGreater(next_exec, timezone.now())
    
    def test_execution_recording(self):
        """Test execution recording"""
        schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            time=timezone.now().time(),
            days='0,1,2,3,4,5,6',
            feed_amount=100.0,
            user=self.user
        )
        
        initial_count = schedule.execution_count
        schedule.record_execution()
        
        self.assertEqual(schedule.execution_count, initial_count + 1)
        self.assertIsNotNone(schedule.last_execution)
        self.assertIsNotNone(schedule.next_execution)


class FeedEventModelTest(TestCase):
    """Tests for FeedEvent model"""
    
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
    
    def test_feed_event_creation(self):
        """Test creating a feed event"""
        event = FeedEvent.objects.create(
            user=self.user,
            pond=self.pond,
            amount=150.0
        )
        
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.pond, self.pond)
        self.assertEqual(event.amount, 150.0)
        self.assertIsNotNone(event.timestamp)
    
    def test_feed_event_ordering(self):
        """Test feed event ordering"""
        event1 = FeedEvent.objects.create(
            user=self.user,
            pond=self.pond,
            amount=100.0
        )
        
        # Wait a moment
        time.sleep(0.001)
        
        event2 = FeedEvent.objects.create(
            user=self.user,
            pond=self.pond,
            amount=200.0
        )
        
        events = FeedEvent.objects.all()
        self.assertEqual(events[0], event2)  # Most recent first
        self.assertEqual(events[1], event1)


class FeedStatModelTest(TestCase):
    """Tests for FeedStat model"""
    
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
    
    def test_feed_stat_creation(self):
        """Test creating a feed stat"""
        stat = FeedStat.objects.create(
            user=self.user,
            pond=self.pond,
            stat_type='daily',
            amount=500.0,
            start_date=timezone.now().date()
        )
        
        self.assertEqual(stat.user, self.user)
        self.assertEqual(stat.pond, self.pond)
        self.assertEqual(stat.stat_type, 'daily')
        self.assertEqual(stat.amount, 500.0)
        self.assertIsNotNone(stat.start_date)
    
    def test_feed_stat_unique_constraint(self):
        """Test unique constraint"""
        start_date = timezone.now().date()
        
        FeedStat.objects.create(
            user=self.user,
            pond=self.pond,
            stat_type='daily',
            amount=500.0,
            start_date=start_date
        )
        
        # Same user, pond, type, and start_date should fail
        with self.assertRaises(IntegrityError):
            FeedStat.objects.create(
                user=self.user,
                pond=self.pond,
                stat_type='daily',
                amount=600.0,
                start_date=start_date
            )


class FeedStatHistoryModelTest(TestCase):
    """Tests for FeedStatHistory model"""
    
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
    
    def test_feed_stat_history_creation(self):
        """Test creating a feed stat history"""
        start_date = timezone.now().date()
        end_date = start_date + timezone.timedelta(days=7)
        
        history = FeedStatHistory.objects.create(
            user=self.user,
            pond=self.pond,
            stat_type='weekly',
            amount=3500.0,
            start_date=start_date,
            end_date=end_date
        )
        
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.pond, self.pond)
        self.assertEqual(history.stat_type, 'weekly')
        self.assertEqual(history.amount, 3500.0)
        self.assertEqual(history.start_date, start_date)
        self.assertEqual(history.end_date, end_date)
        self.assertIsNotNone(history.created_at)
    
    def test_feed_stat_history_ordering(self):
        """Test feed stat history ordering"""
        start_date = timezone.now().date()
        end_date = start_date + timezone.timedelta(days=7)
        
        history1 = FeedStatHistory.objects.create(
            user=self.user,
            pond=self.pond,
            stat_type='weekly',
            amount=3000.0,
            start_date=start_date,
            end_date=end_date
        )
        
        # Wait a moment
        time.sleep(0.001)
        
        history2 = FeedStatHistory.objects.create(
            user=self.user,
            pond=self.pond,
            stat_type='weekly',
            amount=4000.0,
            start_date=start_date + timezone.timedelta(days=7),
            end_date=end_date + timezone.timedelta(days=7)
        )
        
        histories = FeedStatHistory.objects.all()
        self.assertEqual(histories[0], history2)  # Most recent first
        self.assertEqual(histories[1], history1)

# ============================================================================
# CONTROL VIEW TESTS (moved from old testing)
# ============================================================================

from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta


class PondFeedStatsViewTest(TestCase):
    """Tests for the PondFeedStatsView"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='TestPassword123!'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='TestPassword123!'
        )
        
        # Create pond pairs
        self.pond_pair1 = PondPair.objects.create(
            name='Control Test Pair 1',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user1
        )
        self.pond_pair2 = PondPair.objects.create(
            name='Control Test Pair 2',
            device_id='BB:CC:DD:EE:FF:AA',
            owner=self.user2
        )
        
        # Create ponds
        self.pond1 = Pond.objects.create(
            name='User1 Pond',
            parent_pair=self.pond_pair1
        )
        self.pond2 = Pond.objects.create(
            name='User2 Pond',
            parent_pair=self.pond_pair2
        )
        
        # Create feed stats for pond1
        today = date.today()
        self.daily_stat = FeedStat.objects.create(
            user=self.user1,
            pond=self.pond1,
            stat_type='daily',
            amount=5.5,
            start_date=today
        )
        self.weekly_stat = FeedStat.objects.create(
            user=self.user1,
            pond=self.pond1,
            stat_type='weekly',
            amount=25.0,
            start_date=today - timedelta(days=today.weekday())
        )
        self.monthly_stat = FeedStat.objects.create(
            user=self.user1,
            pond=self.pond1,
            stat_type='monthly',
            amount=100.0,
            start_date=today.replace(day=1)
        )
        
        # Create feed stats for pond2
        self.pond2_daily_stat = FeedStat.objects.create(
            user=self.user2,
            pond=self.pond2,
            stat_type='daily',
            amount=3.0,
            start_date=today
        )
        
        # Test URLs
        self.feed_stats_url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond1.id})
        self.feed_stats_url2 = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond2.id})
        self.feed_stats_url_invalid = reverse('ponds:pond_feed_stats', kwargs={'pond_id': 999})
    
    def test_get_feed_stats_authenticated_owner(self):
        """Test that authenticated owner can get feed stats for their pond"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond1.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('feed_statistics', response.data)
        self.assertEqual(response.data['pond_id'], self.pond1.id)
        self.assertEqual(response.data['pond_name'], self.pond1.name)
    
    def test_get_feed_stats_unauthorized_pond(self):
        """Test that user cannot get feed stats for another user's pond"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond2.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_get_feed_stats_unauthenticated(self):
        """Test that unauthenticated user cannot get feed stats"""
        url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond1.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_feed_stats_nonexistent_pond(self):
        """Test getting feed stats for non-existent pond"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': 999})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_feed_stats_data_accuracy(self):
        """Test that feed stats data is accurate"""
        self.client.force_authenticate(user=self.user1)
        url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond1.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('feed_statistics', response.data)
        self.assertIn('total_records', response.data)
        
        # Test with specific stat type filter
        response = self.client.get(f"{url}?stat_type=daily")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test with invalid stat type
        response = self.client.get(f"{url}?stat_type=invalid")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_feed_stats_empty_pond(self):
        """Test feed stats for pond with no feed statistics"""
        # Create a new pond with no feed stats
        pond3 = Pond.objects.create(
            name='Empty Pond',
            parent_pair=self.pond_pair1
        )
        
        self.client.force_authenticate(user=self.user1)
        url = reverse('ponds:pond_feed_stats', kwargs={'pond_id': pond3.id})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('feed_statistics', response.data)
        self.assertEqual(response.data['total_records'], 0)
    
    def test_feed_stats_multiple_users(self):
        """Test that users can only see their own pond feed stats"""
        # User1 should see pond1 stats
        self.client.force_authenticate(user=self.user1)
        url1 = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond1.id})
        response1 = self.client.get(url1)
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data['pond_id'], self.pond1.id)
        
        # User2 should see pond2 stats
        self.client.force_authenticate(user=self.user2)
        url2 = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond2.id})
        response2 = self.client.get(url2)
        
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['pond_id'], self.pond2.id)
        
        # User2 should not see pond1 stats
        self.client.force_authenticate(user=self.user2)
        url3 = reverse('ponds:pond_feed_stats', kwargs={'pond_id': self.pond1.id})
        response3 = self.client.get(url3)
        
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)

# ============================================================================
# AUTOMATION SCHEDULE TESTS (moved from old testing)
# ============================================================================

import time
from datetime import time as time_class


class AutomationScheduleViewTest(TestCase):
    """Tests for automation schedule endpoints"""
    
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
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Login
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'TestPassword123!'
        }, format='json')
        
        self.access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        self.schedule_url = reverse('automation:create_automation_schedule', kwargs={'pond_id': self.pond.id})
        # print(f"DEBUG: schedule_url = {self.schedule_url}")
        # print(f"DEBUG: pond.id = {self.pond.id}")
    
    def tearDown(self):
        """Clean up after each test"""
        AutomationSchedule.objects.all().delete()
    
    def test_create_schedule(self):
        """Test creating a new automation schedule"""
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AutomationSchedule.objects.count(), 1)
        
        schedule = AutomationSchedule.objects.first()
        self.assertEqual(schedule.pond, self.pond)
        self.assertEqual(schedule.automation_type, 'FEED')
        self.assertEqual(schedule.action, 'FEED')
        self.assertEqual(schedule.feed_amount, 50.0)
    
    def test_invalid_schedule_data(self):
        """Test validation of schedule data"""
        # Test with invalid automation type
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'INVALID',
            'action': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'feed_amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('automation_type', response.data)
    
    def test_schedule_without_required_fields(self):
        """Test creating schedule without required fields"""
        # Test without automation_type
        data = {
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'feed_amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('automation_type', response.data)
        
        # Test without time
        data = {
            'automation_type': 'FEED',
            'action': 'FEED',
            'days': '0,1,2,3,4,5,6',
            'amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time', response.data)
        
        # Test without days
        data = {
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '08:00:00',
            'feed_amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('days', response.data)
        
        # Test without action
        data = {
            'automation_type': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'feed_amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('action', response.data)
    
    def test_schedule_time_validation(self):
        """Test schedule time validation"""
        # Test with invalid time format
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '25:00:00',  # Invalid hour
            'days': '0,1,2,3,4,5,6',
            'feed_amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time', response.data)
    
    def test_schedule_action_validation(self):
        """Test schedule action validation"""
        # Test with invalid action for FEED automation
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'FEED',
            'action': 'WATER_DRAIN',  # Invalid action for FEED
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'feed_amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('action', response.data)
        
        # Test with invalid action for WATER automation
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'WATER',
            'action': 'FEED',  # Invalid action for WATER
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'drain_level': 0.0,
            'target_level': 80.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('action', response.data)
    
    def test_schedule_days_validation(self):
        """Test schedule days validation"""
        # Test with invalid days format
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,7',  # Invalid day 7
            'amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('days', response.data)
    
    def test_schedule_feed_amount_validation(self):
        """Test schedule feed amount validation"""
        # Test with negative feed amount
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'amount': -10.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)
        
        # Test with zero feed amount
        data['amount'] = 0.0
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('amount', response.data)
    
    def test_schedule_unauthorized_pond(self):
        """Test that user cannot create schedule for another user's pond"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='OtherPassword123!'
        )
        
        other_pond_pair = PondPair.objects.create(
            device_id='BB:CC:DD:EE:FF:AA',
            owner=other_user
        )
        other_pond = Pond.objects.create(
            name='Other Pond',
            parent_pair=other_pond_pair
        )
        
        data = {
            'pond_id': other_pond.id,  # Use other_pond, not self.pond
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'amount': 50.0
        }
        
        # Construct URL for the other user's pond
        other_pond_url = reverse('automation:create_automation_schedule', kwargs={'pond_id': other_pond.id})
        
        response = self.client.post(other_pond_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('pond_id', response.data)
    
    def test_schedule_unauthenticated(self):
        """Test that unauthenticated user cannot create schedule"""
        self.client.credentials()  # Clear credentials
        
        data = {
            'pond_id': self.pond.id,
            'automation_type': 'FEED',
            'action': 'FEED',
            'time': '08:00:00',
            'days': '0,1,2,3,4,5,6',
            'amount': 50.0
        }
        
        response = self.client.post(self.schedule_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_get_schedule_list(self):
        """Test getting list of automation schedules"""
        # Clear any existing schedules for this test
        AutomationSchedule.objects.filter(pond=self.pond).delete()
        
        # Create some schedules
        AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            time=time_class(8, 0),
            days='0,1,2,3,4,5,6',
            feed_amount=50.0,
            user=self.user
        )
        AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            time=time_class(18, 0),
            days='1,3,5',
            feed_amount=75.0,
            user=self.user
        )
        
        list_url = reverse('automation:pond_automation_schedule_list', kwargs={'pond_id': self.pond.id})
        response = self.client.get(list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 2)
        
        # Check that schedules are returned
        self.assertEqual(len(response.data['data']), 2)
    
    def test_update_schedule(self):
        """Test updating an automation schedule"""
        schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            time=time_class(8, 0),
            days='0,1,2,3,4,5,6',
            feed_amount=50.0,
            user=self.user
        )
        
        update_data = {
            'time': '09:00:00',
            'feed_amount': 75.0
        }
        
        url = reverse('automation:pond_automation_schedule_detail', kwargs={'pond_id': self.pond.id, 'schedule_id': schedule.id})
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['schedule']['time'], '09:00:00')
        self.assertEqual(response.data['schedule']['feed_amount'], 75.0)
        
        # Verify in database
        schedule.refresh_from_db()
        self.assertEqual(schedule.time, time_class(9, 0))
        self.assertEqual(schedule.feed_amount, 75.0)
    
    def test_delete_schedule(self):
        """Test deleting an automation schedule"""
        schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            action='FEED',
            time=time_class(8, 0),
            days='0,1,2,3,4,5,6',
            feed_amount=50.0,
            user=self.user
        )
        
        url = reverse('automation:pond_automation_schedule_delete', kwargs={'pond_id': self.pond.id, 'schedule_id': schedule.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify deleted from database
        self.assertFalse(AutomationSchedule.objects.filter(id=schedule.id).exists())
