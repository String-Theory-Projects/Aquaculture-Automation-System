"""
Tests for automation tasks.

This module tests the Celery tasks for:
- Threshold monitoring and automation triggers
- Automation execution engine
- Priority-based conflict resolution
- Scheduled automation system
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    AutomationExecution, DeviceCommand, AutomationSchedule
)
from .tasks import (
    check_parameter_thresholds, execute_automation, check_scheduled_automations,
    process_threshold_violations, retry_failed_automations
)
from ponds.models import Pond, PondPair, SensorData, SensorThreshold, Alert
from core.constants import AUTOMATION_PRIORITIES
from core.choices import AUTOMATION_TYPES, AUTOMATION_ACTIONS


class AutomationTasksTestCase(TestCase):
    """Test case for automation tasks"""
    
    def setUp(self):
        """Set up test data"""
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test pond pair and pond
        self.pond_pair = PondPair.objects.create(
            name='Test Pond Pair',
            device_id='AA:BB:CC:DD:EE:FF',
            owner=self.user
        )
        
        self.pond = Pond.objects.create(
            name='Test Pond',
            parent_pair=self.pond_pair
        )
        
        # Create test sensor threshold
        self.threshold = SensorThreshold.objects.create(
            pond=self.pond,
            parameter='temperature',
            upper_threshold=30.0,
            lower_threshold=20.0,
            automation_action='ALERT',
            priority=1,
            alert_level='MEDIUM',
            violation_timeout=30,
            max_violations=2
        )
        
        # Create test automation schedule
        self.schedule = AutomationSchedule.objects.create(
            pond=self.pond,
            automation_type='FEED',
            time='08:00:00',
            days='0,1,2,3,4,5,6',  # Every day
            feed_amount=100.0,
            priority=3,
            user=self.user
        )
    
    def test_check_parameter_thresholds_no_violation(self):
        """Test threshold checking when no violation occurs"""
        # Test with value within threshold range
        result = check_parameter_thresholds(self.pond.id, 'temperature', 25.0)
        
        self.assertTrue(result)
        
        # Check that no alerts were created
        alerts = Alert.objects.filter(pond=self.pond, parameter='temperature')
        self.assertEqual(alerts.count(), 0)
    
    def test_check_parameter_thresholds_upper_violation(self):
        """Test threshold checking when upper threshold is violated"""
        # Test with value above upper threshold
        result = check_parameter_thresholds(self.pond.id, 'temperature', 35.0)
        
        self.assertTrue(result)
        
        # Check that alert was created
        alerts = Alert.objects.filter(pond=self.pond, parameter='temperature')
        self.assertEqual(alerts.count(), 1)
        
        alert = alerts.first()
        self.assertEqual(alert.status, 'active')
        self.assertEqual(alert.violation_count, 1)
        self.assertEqual(alert.current_value, 35.0)
    
    def test_check_parameter_thresholds_lower_violation(self):
        """Test threshold checking when lower threshold is violated"""
        # Test with value below lower threshold
        result = check_parameter_thresholds(self.pond.id, 'temperature', 15.0)
        
        self.assertTrue(result)
        
        # Check that alert was created
        alerts = Alert.objects.filter(pond=self.pond, parameter='temperature')
        self.assertEqual(alerts.count(), 1)
        
        alert = alerts.first()
        self.assertEqual(alert.status, 'active')
        self.assertEqual(alert.violation_count, 1)
        self.assertEqual(alert.current_value, 15.0)
    
    def test_check_parameter_thresholds_multiple_violations(self):
        """Test threshold checking with multiple violations"""
        # First violation
        check_parameter_thresholds(self.pond.id, 'temperature', 35.0)
        
        # Second violation with the same value (should increment violation count)
        result = check_parameter_thresholds(self.pond.id, 'temperature', 35.0)
        
        self.assertTrue(result)
        
        # Check that automation execution was created
        # Note: The automation is scheduled with a delay, so we check for PENDING status
        automations = AutomationExecution.objects.filter(
            pond=self.pond,
            execution_type='FEED',  # Temperature parameter defaults to FEED type
            priority='THRESHOLD',
            status='PENDING'
        )
        
        self.assertEqual(automations.count(), 1)
        
        automation = automations.first()
        self.assertEqual(automation.status, 'PENDING')
        self.assertEqual(automation.action, 'ALERT')
        
        # Verify the automation is linked to the threshold
        self.assertEqual(automation.threshold, self.threshold)
    
    def test_check_parameter_thresholds_resolve_alert(self):
        """Test that alerts are resolved when threshold is no longer violated"""
        # Create violation
        check_parameter_thresholds(self.pond.id, 'temperature', 35.0)
        
        # Check that alert exists
        alerts = Alert.objects.filter(pond=self.pond, parameter='temperature')
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().status, 'active')
        
        # Resolve violation
        check_parameter_thresholds(self.pond.id, 'temperature', 25.0)
        
        # Check that alert was resolved
        alerts = Alert.objects.filter(pond=self.pond, parameter='temperature')
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().status, 'resolved')
    
    @patch('automation.tasks.execute_automation.apply_async')
    def test_execute_automation_success(self, mock_apply_async):
        """Test successful automation execution"""
        # Create automation execution
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now(),
            parameters={'feed_amount': 100}
        )
        
        # Mock MQTT service
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_feed_command.return_value = True
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(automation.id)
            
            self.assertTrue(result)
            
            # Check that automation was completed
            automation.refresh_from_db()
            self.assertEqual(automation.status, 'COMPLETED')
            self.assertTrue(automation.success)
    
    @patch('automation.tasks.execute_automation.apply_async')
    def test_execute_automation_failure(self, mock_apply_async):
        """Test failed automation execution"""
        # Create automation execution
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now(),
            parameters={'feed_amount': 100}
        )
        
        # Mock MQTT service failure
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_feed_command.return_value = False
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(automation.id)
            
            self.assertFalse(result)
            
            # Check that automation was marked as failed
            automation.refresh_from_db()
            self.assertEqual(automation.status, 'FAILED')  # Status is FAILED when success is False
            self.assertFalse(automation.success)
            self.assertIn('MQTT command failed', automation.error_details)
    
    def test_execute_automation_priority_conflict(self):
        """Test automation execution with priority conflicts"""
        # Create higher priority automation
        high_priority_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='WATER_DRAIN',
            priority='EMERGENCY_WATER',
            status='EXECUTING',
            scheduled_at=timezone.now()
        )
        
        # Create lower priority automation
        low_priority_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now()
        )
        
        # Try to execute lower priority automation
        with patch('automation.tasks.execute_automation.apply_async') as mock_apply_async:
            result = execute_automation(low_priority_automation.id)
            
            self.assertFalse(result)
            
            # Check that automation was rescheduled
            mock_apply_async.assert_called_once()
    
    @patch('automation.tasks.execute_automation.apply_async')
    def test_check_scheduled_automations(self, mock_apply_async):
        """Test scheduled automation checking"""
        # Set schedule time to current time
        now = timezone.now()
        current_time = now.time()
        self.schedule.time = current_time
        self.schedule.save()
        
        # Check scheduled automations
        result = check_scheduled_automations()
        
        self.assertTrue(result['success'])
        self.assertEqual(result['executed_count'], 1)
        
        # Check that automation execution was created
        automations = AutomationExecution.objects.filter(
            pond=self.pond,
            schedule=self.schedule
        )
        self.assertEqual(automations.count(), 1)
        
        # Check that schedule was updated
        self.schedule.refresh_from_db()
        self.assertIsNotNone(self.schedule.last_execution)
        self.assertEqual(self.schedule.execution_count, 1)
    
    def test_process_threshold_violations(self):
        """Test processing of threshold violations"""
        # Create pending threshold automation
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='ALERT',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now() - timedelta(seconds=1)
        )
        
        # Process threshold violations
        with patch('automation.tasks.execute_automation.apply_async') as mock_apply_async:
            result = process_threshold_violations()
            
            self.assertTrue(result['success'])
            self.assertEqual(result['processed_count'], 1)
            
            # Check that automation was triggered
            mock_apply_async.assert_called_once_with(args=[automation.id])
    
    def test_retry_failed_automations(self):
        """Test retrying failed automations"""
        # Create failed automation
        failed_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='FAILED',
            created_at=timezone.now() - timedelta(minutes=30)
        )
        
        # Retry failed automations
        with patch('automation.tasks.execute_automation.apply_async') as mock_apply_async:
            result = retry_failed_automations()
            
            self.assertTrue(result['success'])
            self.assertEqual(result['retry_count'], 1)
            
            # Check that automation was reset and retried
            failed_automation.refresh_from_db()
            self.assertEqual(failed_automation.status, 'PENDING')
            
            # Check that retry was triggered
            mock_apply_async.assert_called_once_with(args=[failed_automation.id])
    
    def test_automation_priority_hierarchy(self):
        """Test automation priority hierarchy"""
        priorities = ['MANUAL_COMMAND', 'EMERGENCY_WATER', 'SCHEDULED', 'THRESHOLD']
        
        for i, priority in enumerate(priorities):
            # Create automation with this priority
            automation = AutomationExecution.objects.create(
                pond=self.pond,
                execution_type='FEED',
                action='FEED',
                priority=priority,
                status='PENDING',
                scheduled_at=timezone.now()
            )
            
            # Mock MQTT service to avoid connection issues
            with patch('automation.tasks.MQTTService') as mock_mqtt_service:
                mock_service = MagicMock()
                mock_service.send_feed_command.return_value = True
                mock_mqtt_service.return_value = mock_service
                
                # Check that automation can be executed
                result = execute_automation(automation.id)
                
                # All should succeed in isolation
                self.assertTrue(result)
    
    def test_water_operation_conflicts(self):
        """Test that water operations don't conflict"""
        # Create drain operation
        drain_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='WATER_DRAIN',
            priority='THRESHOLD',
            status='EXECUTING',
            scheduled_at=timezone.now()
        )
        
        # Try to create fill operation (should be blocked)
        fill_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='WATER_FILL',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now()
        )
        
        # Try to execute fill operation
        with patch('automation.tasks.execute_automation.apply_async') as mock_apply_async:
            result = execute_automation(fill_automation.id)
            
            self.assertFalse(result)
            
            # Check that automation was rescheduled
            mock_apply_async.assert_called_once()
    
    def test_feed_automation_execution(self):
        """Test feed automation execution"""
        # Create feed automation
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now(),
            parameters={'feed_amount': 150}
        )
        
        # Mock MQTT service
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_feed_command.return_value = True
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(automation.id)
            
            self.assertTrue(result)
            
            # FeedEvent model has been deprecated - feed tracking is now handled via DeviceCommand
            # Check that device command was created instead
            device_commands = DeviceCommand.objects.filter(pond=self.pond, command_type='FEED')
            self.assertEqual(device_commands.count(), 1)
            
            device_command = device_commands.first()
            self.assertEqual(device_command.parameters.get('feed_amount', 0), 150)  # Amount in grams
            self.assertEqual(device_command.user.username, 'system')  # System user for threshold automation
    
    def test_water_automation_execution(self):
        """Test water automation execution"""
        # Create water automation
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='WATER_DRAIN',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now(),
            parameters={'drain_water_level': 0}
        )
        
        # Mock MQTT service using the same pattern as other tests
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_water_command.return_value = True
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(automation.id)
            
            self.assertTrue(result)
            
            # Check that MQTT service was called correctly
            mock_service.send_water_command.assert_called_once_with(
                self.pond.parent_pair,
                'WATER_DRAIN',
                level=0,
                pond=self.pond
            )
    
    def test_water_flush_automation_execution(self):
        """Test water flush automation execution"""
        # Create water flush automation
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='WATER_FLUSH',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now(),
            parameters={'drain_water_level': 20, 'target_water_level': 80}
        )
        
        # Mock MQTT service
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_water_command.return_value = True
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(automation.id)
            
            self.assertTrue(result)
            
            # Check that MQTT service was called correctly
            mock_service.send_water_command.assert_called_once_with(
                self.pond.parent_pair,
                'WATER_FLUSH',
                pond=self.pond,
                drain_level=20,
                fill_level=80
            )
    
    def test_water_valve_automation_execution(self):
        """Test water valve control automation execution"""
        # Test inlet valve open
        inlet_open_automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='WATER',
            action='WATER_INLET_OPEN',
            priority='THRESHOLD',
            status='PENDING',
            scheduled_at=timezone.now(),
            parameters={}
        )
        
        # Mock MQTT service
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_water_command.return_value = True
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(inlet_open_automation.id)
            
            self.assertTrue(result)
            
            # Check that MQTT service was called correctly
            mock_service.send_water_command.assert_called_once_with(
                self.pond.parent_pair,
                'WATER_INLET_OPEN',
                pond=self.pond
            )
    
    def test_automation_with_schedule(self):
        """Test automation execution with linked schedule"""
        # Create automation with schedule
        automation = AutomationExecution.objects.create(
            pond=self.pond,
            execution_type='FEED',
            action='FEED',
            priority='SCHEDULED',
            status='PENDING',
            scheduled_at=timezone.now(),
            schedule=self.schedule,
            parameters={'feed_amount': 100}
        )
        
        # Mock MQTT service
        with patch('automation.tasks.MQTTService') as mock_mqtt_service:
            mock_service = MagicMock()
            mock_service.send_feed_command.return_value = True
            mock_mqtt_service.return_value = mock_service
            
            # Execute automation
            result = execute_automation(automation.id)
            
            self.assertTrue(result)
            
            # FeedEvent model has been deprecated - feed tracking is now handled via DeviceCommand
            # Check that device command was created with correct user
            device_commands = DeviceCommand.objects.filter(pond=self.pond, command_type='FEED')
            self.assertEqual(device_commands.count(), 1)
            
            device_command = device_commands.first()
            self.assertEqual(device_command.user, self.user)  # User from schedule
