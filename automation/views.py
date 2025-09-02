"""
API views for automation system.

This module provides REST API endpoints for:
- Threshold management
- Automation execution
- Schedule management
- System monitoring
"""

import logging
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
import json
from django.utils import timezone
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import time, datetime, timedelta
from django.utils.dateparse import parse_time
from django.contrib.auth import get_user_model

from .models import (
    AutomationExecution, DeviceCommand, AutomationSchedule,
    FeedEvent, FeedStat, FeedStatHistory
)
from .services import AutomationService
from ponds.models import Pond, PondPair, SensorThreshold, Alert, SensorData
from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, AUTOMATION_PRIORITIES
from mqtt_client.bridge_service import get_mqtt_bridge_service

logger = logging.getLogger(__name__)
User = get_user_model()


class GetAutomationStatusView(APIView):
    """Get automation status for a specific pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            service = AutomationService()
            status_data = service.get_automation_status(pond)
            
            return Response({
                'success': True,
                'data': status_data
            })
            
        except Exception as e:
            logger.error(f"Error getting automation status for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetActiveThresholdsView(APIView):
    """Get all active thresholds for a pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            service = AutomationService()
            thresholds = service.get_active_thresholds(pond)
            
            # Serialize thresholds
            threshold_data = []
            for threshold in thresholds:
                threshold_data.append({
                    'id': threshold.id,
                    'parameter': threshold.parameter,
                    'upper_threshold': threshold.upper_threshold,
                    'lower_threshold': threshold.lower_threshold,
                    'automation_action': threshold.automation_action,
                    'priority': threshold.priority,
                    'alert_level': threshold.alert_level,
                    'is_active': threshold.is_active,
                    'violation_timeout': threshold.violation_timeout,
                    'max_violations': threshold.max_violations,
                    'created_at': threshold.created_at.isoformat(),
                    'updated_at': threshold.updated_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'data': threshold_data,
                'count': len(threshold_data)
            })
            
        except Exception as e:
            logger.error(f"Error getting thresholds for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateThresholdView(APIView):
    """Create a new sensor threshold."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Parse request data
            data = request.data
            
            required_fields = ['parameter', 'upper_threshold', 'lower_threshold', 'automation_action']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            service = AutomationService()
            threshold = service.create_threshold(
                pond=pond,
                parameter=data['parameter'],
                upper_threshold=float(data['upper_threshold']),
                lower_threshold=float(data['lower_threshold']),
                automation_action=data['automation_action'],
                priority=data.get('priority', 1),
                alert_level=data.get('alert_level', 'MEDIUM'),
                violation_timeout=data.get('violation_timeout', getattr(settings, 'AUTOMATION_DEFAULT_THRESHOLD_TIMEOUT', 30)),
                max_violations=data.get('max_violations', getattr(settings, 'AUTOMATION_MAX_THRESHOLD_VIOLATIONS', 3)),
                send_alert=data.get('send_alert', True)
            )
            
            return Response({
                'success': True,
                'data': {
                    'id': threshold.id,
                    'message': f'Threshold created successfully for {threshold.parameter}'
                }
            })
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': f'Invalid numeric value: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creating threshold for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateThresholdView(APIView):
    """Update an existing sensor threshold."""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, threshold_id):
        try:
            threshold = get_object_or_404(SensorThreshold, id=threshold_id)
            
            # Check if user has access to this threshold
            if threshold.pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Parse request data
            data = request.data
            
            service = AutomationService()
            updated_threshold = service.update_threshold(threshold_id, **data)
            
            return Response({
                'success': True,
                'data': {
                    'id': updated_threshold.id,
                    'message': f'Threshold updated successfully for {updated_threshold.parameter}'
                }
            })
            
        except Exception as e:
            logger.error(f"Error updating threshold {threshold_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteThresholdView(APIView):
    """Delete a sensor threshold."""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, threshold_id):
        try:
            threshold = get_object_or_404(SensorThreshold, id=threshold_id)
            
            # Check if user has access to this threshold
            if threshold.pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            service = AutomationService()
            success = service.delete_threshold(threshold_id)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Threshold deleted successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to delete threshold'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Error deleting threshold {threshold_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAutomationSchedulesView(APIView):
    """Get automation schedules for a pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            schedules = AutomationSchedule.objects.filter(pond=pond).order_by('priority', 'time')
            
            # Serialize schedules
            schedule_data = []
            for schedule in schedules:
                schedule_data.append({
                    'id': schedule.id,
                    'automation_type': schedule.automation_type,
                    'action': schedule.action,
                    'time': schedule.time.strftime('%H:%M'),
                    'days': schedule.days,
                    'is_active': schedule.is_active,
                    'priority': schedule.priority,
                    'feed_amount': schedule.feed_amount,
                    'drain_water_level': schedule.drain_water_level,
                    'target_water_level': schedule.target_water_level,
                    'last_execution': schedule.last_execution.isoformat() if schedule.last_execution else None,
                    'next_execution': schedule.next_execution.isoformat() if schedule.next_execution else None,
                    'execution_count': schedule.execution_count,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'data': schedule_data,
                'count': len(schedule_data)
            })
            
        except Exception as e:
            logger.error(f"Error getting schedules for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListAutomationSchedulesView(generics.GenericAPIView):
    """
    DRF view for listing automation schedules
    
    GET: List all automation schedules for a pond
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        """Get automation schedules for a pond"""
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            schedules = AutomationSchedule.objects.filter(pond=pond).order_by('priority', 'time')
            
            # Serialize schedules
            schedule_data = []
            for schedule in schedules:
                schedule_data.append({
                    'id': schedule.id,
                    'pond': schedule.pond.id,
                    'automation_type': schedule.automation_type,
                    'action': schedule.action,
                    'time': schedule.time.strftime('%H:%M'),
                    'days': schedule.days,
                    'is_active': schedule.is_active,
                    'priority': schedule.priority,
                    'feed_amount': schedule.feed_amount,
                    'drain_water_level': schedule.drain_water_level,
                    'target_water_level': schedule.target_water_level,
                    'last_execution': schedule.last_execution.isoformat() if schedule.last_execution else None,
                    'next_execution': schedule.next_execution.isoformat() if schedule.next_execution else None,
                    'execution_count': schedule.execution_count,
                    'created_at': schedule.created_at.isoformat(),
                    'updated_at': schedule.updated_at.isoformat(),
                })
            
            return Response(schedule_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting schedules for pond {pond_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateAutomationScheduleView(generics.GenericAPIView):
    """
    DRF view for updating automation schedules
    
    GET: Retrieve a specific automation schedule
    PUT: Update an automation schedule (full update)
    PATCH: Update an automation schedule (partial update)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id, schedule_id):
        """Retrieve a specific automation schedule"""
        try:
            schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
            
            # Check if user has access to this schedule
            if schedule.pond.parent_pair.owner != request.user:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Serialize the schedule
            schedule_data = {
                'id': schedule.id,
                'pond': schedule.pond.id,
                'automation_type': schedule.automation_type,
                'action': schedule.action,
                'time': schedule.time.strftime('%H:%M:%S'),
                'days': schedule.days,
                'is_active': schedule.is_active,
                'priority': schedule.priority,
                'feed_amount': schedule.feed_amount,
                'drain_water_level': schedule.drain_water_level,
                'target_water_level': schedule.target_water_level,
                'last_execution': schedule.last_execution.isoformat() if schedule.last_execution else None,
                'next_execution': schedule.next_execution.isoformat() if schedule.next_execution else None,
                'execution_count': schedule.execution_count,
                'created_at': schedule.created_at.isoformat(),
                'updated_at': schedule.updated_at.isoformat(),
            }
            
            return Response(schedule_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting schedule {schedule_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, pond_id, schedule_id):
        """Update an automation schedule (full update)"""
        try:
            schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
            
            # Check if user has access to this schedule
            if schedule.pond.parent_pair.owner != request.user:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create a copy of the data for processing
            update_data = request.data.copy()
            
            # Convert time string to time object if provided
            if 'time' in update_data:
                time_str = update_data['time']
                try:
                    # Handle different time formats
                    if ':' in time_str:
                        parts = time_str.split(':')
                        if len(parts) == 2:
                            # HH:MM format - add seconds
                            time_str = time_str + ':00'
                        elif len(parts) == 3:
                            # HH:MM:SS format - use as is
                            pass
                        else:
                            raise ValueError("Invalid time format")
                    
                    time_obj = parse_time(time_str)
                    if time_obj is None:
                        return Response(
                            {'time': ['Invalid time format. Use HH:MM or HH:MM:SS']},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    # Update the data with the time object
                    update_data['time'] = time_obj
                except (ValueError, AttributeError):
                    return Response(
                        {'time': ['Invalid time format. Use HH:MM or HH:MM:SS']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            service = AutomationService()
            updated_schedule = service.update_automation_schedule(schedule_id, **update_data)
            
            return Response(
                {
                    'schedule': {
                        'id': updated_schedule.id,
                        'time': updated_schedule.time.strftime('%H:%M:%S'),
                        'feed_amount': updated_schedule.feed_amount,
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error updating schedule {schedule_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pond_id, schedule_id):
        """Update an automation schedule"""
        try:
            schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
            
            # Check if user has access to this schedule
            if schedule.pond.parent_pair.owner != request.user:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create a copy of the data for processing
            update_data = request.data.copy()
            
            # Convert time string to time object if provided
            if 'time' in update_data:
                time_str = update_data['time']
                try:
                    # Handle different time formats
                    if ':' in time_str:
                        parts = time_str.split(':')
                        if len(parts) == 2:
                            # HH:MM format - add seconds
                            time_str = time_str + ':00'
                        elif len(parts) == 3:
                            # HH:MM:SS format - use as is
                            pass
                        else:
                            raise ValueError("Invalid time format")
                    
                    time_obj = parse_time(time_str)
                    if time_obj is None:
                        return Response(
                            {'time': ['Invalid time format. Use HH:MM or HH:MM:SS']},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    # Update the data with the time object
                    update_data['time'] = time_obj
                except (ValueError, AttributeError):
                    return Response(
                        {'time': ['Invalid time format. Use HH:MM or HH:MM:SS']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            service = AutomationService()
            updated_schedule = service.update_automation_schedule(schedule_id, **update_data)
            
            return Response(
                {
                    'schedule': {
                        'id': updated_schedule.id,
                        'time': updated_schedule.time.strftime('%H:%M:%S'),
                        'feed_amount': updated_schedule.feed_amount,
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error updating schedule {schedule_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAutomationScheduleView(generics.DestroyAPIView):
    """
    DRF view for deleting automation schedules
    
    DELETE: Delete an automation schedule
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, pond_id, schedule_id):
        """Delete an automation schedule"""
        try:
            schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
            
            # Check if user has access to this schedule
            if schedule.pond.parent_pair.owner != request.user:
                return Response(
                    {'error': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            schedule.delete()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CreateAutomationScheduleView(generics.CreateAPIView):
    """
    DRF view for creating automation schedules
    
    POST: Create a new automation schedule
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request, pond_id):
        """Create a new automation schedule"""
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response(
                    {'pond_id': ['You do not have permission to create schedules for this pond']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate required fields
            required_fields = ['automation_type', 'action', 'time', 'days']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        {field: [f'Missing required field: {field}']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate automation_type
            automation_type = request.data['automation_type']
            if automation_type not in ['FEED', 'WATER']:
                return Response(
                    {'automation_type': ['Invalid automation_type. Must be FEED or WATER']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate action
            action = request.data['action']
            if automation_type == 'FEED':
                if action != 'FEED':
                    return Response(
                        {'action': ['FEED automation type can only use FEED action']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif automation_type == 'WATER':
                valid_water_actions = ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 'WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']
                if action not in valid_water_actions:
                    return Response(
                        {'action': [f'Invalid action for WATER automation. Must be one of: {", ".join(valid_water_actions)}']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate time format
            time_str = request.data['time']
            try:
                # Handle different time formats
                if ':' in time_str:
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        # HH:MM format - add seconds
                        time_str = time_str + ':00'
                    elif len(parts) == 3:
                        # HH:MM:SS format - use as is
                        pass
                    else:
                        raise ValueError("Invalid time format")
                
                time_obj = parse_time(time_str)
                if time_obj is None:
                    return Response(
                        {'time': ['Invalid time format. Use HH:MM or HH:MM:SS']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except (ValueError, AttributeError) as e:
                return Response(
                    {'time': ['Invalid time format. Use HH:MM or HH:MM:SS']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate days format
            days = request.data['days']
            if not days or not isinstance(days, str):
                return Response(
                    {'days': ['Days must be a comma-separated string of day numbers (0-6)']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate individual day numbers
            try:
                day_numbers = [int(day.strip()) for day in days.split(',')]
                for day_num in day_numbers:
                    if day_num < 0 or day_num > 6:
                        return Response(
                            {'days': ['Day numbers must be between 0 and 6 (0=Sunday, 6=Saturday)']},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            except ValueError:
                return Response(
                    {'days': ['Days must be a comma-separated string of valid day numbers (0-6)']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate amount for FEED automation
            if automation_type == 'FEED':
                amount = request.data.get('amount')
                if not amount or float(amount) <= 0:
                    return Response(
                        {'amount': ['Amount is required and must be greater than 0 for feeding automation']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Validate water levels for WATER automation
            if automation_type == 'WATER':
                drain_level = request.data.get('drain_level')
                target_level = request.data.get('target_level')
                if not drain_level and not target_level:
                    return Response(
                        {'water_levels': ['Either drain_level or target_level must be specified for water automation']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            service = AutomationService()
            schedule = service.create_automation_schedule(
                pond=pond,
                automation_type=automation_type,
                action=action,
                time=time_obj,
                days=days,
                priority=request.data.get('priority', 3),
                feed_amount=request.data.get('amount'),
                drain_water_level=request.data.get('drain_level'),
                target_water_level=request.data.get('target_level'),
                user=request.user
            )
            
            return Response(
                {
                'id': schedule.id,
                'message': f'{schedule.automation_type} schedule created successfully'
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error creating schedule for pond {pond_id}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateAutomationScheduleFunctionView(APIView):
    """Update an existing automation schedule."""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, schedule_id):
        try:
            schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
            
            # Check if user has access to this schedule
            if schedule.pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Parse request data
            data = request.data
            
            service = AutomationService()
            updated_schedule = service.update_automation_schedule(schedule_id, **data)
            
            return Response({
                'success': True,
                'data': {
                    'id': updated_schedule.id,
                    'message': f'Schedule updated successfully'
                }
            })
            
        except Exception as e:
            logger.error(f"Error updating schedule {schedule_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAutomationScheduleFunctionView(APIView):
    """Delete an automation schedule."""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, schedule_id):
        try:
            schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
            
            # Check if user has access to this schedule
            if schedule.pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            service = AutomationService()
            success = service.delete_automation_schedule(schedule_id)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Schedule deleted successfully'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to delete schedule'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            logger.error(f"Error deleting schedule {schedule_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAutomationHistoryView(APIView):
    """Get automation execution history for a pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            
            # Get status filter
            status_filter = request.GET.get('status', '')
            
            # Build queryset
            queryset = AutomationExecution.objects.filter(pond=pond)
            if status_filter:
                queryset = queryset.filter(status=status_filter.upper())
            
            # Order by creation date (newest first)
            queryset = queryset.order_by('-created_at')
            
            # Paginate results
            paginator = Paginator(queryset, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize automations
            automation_data = []
            for automation in page_obj:
                automation_data.append({
                    'id': automation.id,
                    'execution_type': automation.execution_type,
                    'action': automation.action,
                    'priority': automation.priority,
                    'status': automation.status,
                    'scheduled_at': automation.scheduled_at.isoformat() if automation.scheduled_at else None,
                    'started_at': automation.started_at.isoformat() if automation.started_at else None,
                    'completed_at': automation.completed_at.isoformat() if automation.completed_at else None,
                    'success': automation.success,
                    'result_message': automation.result_message,
                    'error_details': automation.error_details,
                    'parameters': automation.parameters,
                    'created_at': automation.created_at.isoformat(),
                    'updated_at': automation.updated_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'data': automation_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting automation history for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExecuteManualAutomationView(APIView):
    """Execute a manual automation action."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Parse request data
            data = request.data
            
            required_fields = ['action']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            service = AutomationService()
            automation = service.execute_manual_automation(
                pond=pond,
                action=data['action'],
                parameters=data.get('parameters', {}),
                user=request.user
            )
            
            return Response({
                'success': True,
                'data': {
                    'id': automation.id,
                    'message': f'Manual automation {automation.action} initiated successfully'
                }
            })
            
        except Exception as e:
            logger.error(f"Error executing manual automation for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetPendingAutomationsView(APIView):
    """Get all pending automation executions for the user's ponds."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get user's ponds
            user_ponds = Pond.objects.filter(parent_pair__owner=request.user)
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            
            # Get pending automations
            service = AutomationService()
            pending_automations = []
            
            for pond in user_ponds:
                pond_pending = service.get_pending_automations(pond)
                pending_automations.extend(pond_pending)
            
            # Sort by priority and scheduled time
            pending_automations.sort(key=lambda x: (AUTOMATION_PRIORITIES.index(x.priority), x.scheduled_at))
            
            # Paginate results
            paginator = Paginator(pending_automations, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize automations
            automation_data = []
            for automation in page_obj:
                automation_data.append({
                    'id': automation.id,
                    'pond_name': automation.pond.name,
                    'execution_type': automation.execution_type,
                    'action': automation.action,
                    'priority': automation.priority,
                    'status': automation.status,
                    'scheduled_at': automation.scheduled_at.isoformat() if automation.scheduled_at else None,
                    'parameters': automation.parameters,
                    'created_at': automation.created_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'data': automation_data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous(),
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting pending automations: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResolveAutomationConflictsView(APIView):
    """Resolve automation conflicts for a pond."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            service = AutomationService()
            result = service.resolve_automation_conflicts(pond)
            
            return Response({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            logger.error(f"Error resolving conflicts for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExecuteFeedCommandView(generics.GenericAPIView):
    """Execute a manual feed command for a specific pond."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            # Debug logging
            logger.info(f"=== FEED COMMAND DEBUG ===")
            logger.info(f"Request user: {request.user.username} (ID: {request.user.id})")
            logger.info(f"Request user is authenticated: {request.user.is_authenticated}")
            logger.info(f"Request user is active: {request.user.is_active}")
            logger.info(f"Pond ID requested: {pond_id}")
            logger.info(f"Request method: {request.method}")
            logger.info(f"Request path: {request.path}")
            logger.info(f"Authorization header: {request.headers.get('Authorization', 'None')}")
            
            pond = get_object_or_404(Pond, id=pond_id)
            logger.info(f"Pond found: {pond.name} (ID: {pond.id})")
            logger.info(f"Pond parent pair: {pond.parent_pair.name} (ID: {pond.parent_pair.id})")
            logger.info(f"Pond pair owner: {pond.parent_pair.owner.username} (ID: {pond.parent_pair.owner.id})")
            logger.info(f"Ownership check: {pond.parent_pair.owner == request.user}")
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                logger.error(f"ACCESS DENIED: User {request.user.username} (ID: {request.user.id}) does not own pond {pond.name}")
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Parse request data
            try:
                data = request.data
                amount = float(data.get('amount', 100))
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'Invalid amount parameter'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate amount
            if amount <= 0:
                return Response({
                    'success': False,
                    'error': 'Amount must be positive'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Execute feed command
            service = AutomationService()
            execution = service.execute_manual_automation(
                pond=pond,
                action='FEED',
                parameters={'feed_amount': amount},
                user=request.user
            )
            
            return Response({
                'success': True,
                'data': {
                    'execution_id': execution.id,
                    'message': f'Feed command executed successfully for {pond.name}',
                    'feed_amount': amount
                }
            })
            
        except Exception as e:
            logger.error(f"Error executing feed command for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExecuteWaterCommandView(generics.GenericAPIView):
    """Execute water control command for a specific pond"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            if pond.parent_pair.owner != request.user:
                return Response({'success': False, 'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)
            
            data = request.data
            action = data.get('command_type', '').upper()
            
            # Validate water action
            valid_actions = [
                'WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH',
                'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
                'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE'
            ]
            
            if action not in valid_actions:
                return Response({
                    'success': False,
                    'error': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate parameters based on action type
            parameters = {}
            
            if action == 'WATER_DRAIN':
                drain_level = data.get('drain_level')
                if drain_level is None or not 0 <= drain_level <= 100:
                    return Response({
                        'success': False, 
                        'error': 'drain_level must be between 0 and 100'
                    }, status=status.HTTP_400_BAD_REQUEST)
                parameters['drain_level'] = drain_level
                
            elif action == 'WATER_FILL':
                target_level = data.get('target_level')
                if target_level is None or not 0 <= target_level <= 100:
                    return Response({
                        'success': False, 
                        'error': 'target_level must be between 0 and 100'
                    }, status=status.HTTP_400_BAD_REQUEST)
                parameters['target_level'] = target_level
                
            elif action == 'WATER_FLUSH':
                drain_level = data.get('drain_level')
                fill_level = data.get('target_level')
                if drain_level is None or not 0 <= drain_level <= 100:
                    return Response({
                        'success': False, 
                        'error': 'drain_level must be between 0 and 100'
                    }, status=status.HTTP_400_BAD_REQUEST)
                if fill_level is None or not 0 <= fill_level <= 100:
                    return Response({
                        'success': False, 
                        'error': 'target_level must be between 0 and 100'
                    }, status=status.HTTP_400_BAD_REQUEST)
                parameters['drain_level'] = drain_level
                parameters['target_level'] = fill_level
                
            elif action in ['WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']:
                # Valve control actions don't need additional parameters
                pass
            
            service = AutomationService()
            execution = service.execute_manual_automation(
                pond=pond, action=action, parameters=parameters, user=request.user
            )
            
            return Response({
                'success': True,
                'data': {
                    'execution_id': execution.id,
                    'message': f'{action.replace("_", " ").title()} command executed successfully for {pond.name}',
                    'action': action,
                    'parameters': parameters
                }
            })
            
        except Exception as e:
            logger.error(f"Error executing water command for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExecuteFirmwareCommandView(APIView):
    """Execute firmware-related commands on device."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            # Parse request data
            data = request.data
            command_type = data.get('command_type')
            
            if not command_type:
                return Response({
                    'success': False,
                    'error': 'command_type is required'
                }, status=400)
            
            # Validate command type
            valid_firmware_commands = ['FIRMWARE_UPDATE', 'RESTART', 'CONFIG_UPDATE']
            if command_type not in valid_firmware_commands:
                return Response({
                    'success': False,
                    'error': f'command_type must be one of: {", ".join(valid_firmware_commands)}'
                }, status=400)
            
            # Get MQTT service and send command
            mqtt_service = get_mqtt_bridge_service()
            
            if command_type == 'FIRMWARE_UPDATE':
                firmware_url = data.get('parameters', {}).get('firmware_url')
                if not firmware_url:
                    return Response({
                        'success': False,
                        'error': 'firmware_url is required for FIRMWARE_UPDATE command'
                    }, status=400)
                
                command_id = mqtt_service.send_firmware_update(
                    pond_pair=pond.parent_pair,
                    firmware_url=firmware_url,
                    pond=pond,
                    user=request.user
                )
            elif command_type == 'RESTART':
                command_id = mqtt_service.send_device_reboot(
                    pond_pair=pond.parent_pair,
                    user=request.user
                )
            else:  # CONFIG_UPDATE
                config_data = data.get('parameters', {}).get('config_data', {})
                command_id = mqtt_service.send_command(
                    pond_pair=pond.parent_pair,
                    command_type=command_type,
                    parameters={'config_data': config_data},
                    pond=pond
                )
            
            if command_id:
                return Response({
                    'success': True,
                    'data': {
                        'command_id': command_id,
                        'message': f'{command_type} command sent successfully'
                    }
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send command'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error executing firmware command for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)

class ExecuteRebootCommandView(APIView):
    """Execute device reboot command."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            # Get MQTT service and send reboot command
            mqtt_service = get_mqtt_bridge_service()
            command_id = mqtt_service.send_device_reboot(
                pond_pair=pond.parent_pair,
                user=request.user
            )
            
            if command_id:
                return Response({
                    'success': True,
                    'data': {
                        'command_id': command_id,
                        'message': 'Reboot command sent successfully'
                    }
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send reboot command'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error executing reboot command for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)


class ExecuteThresholdCommandView(APIView):
    """Execute threshold configuration command on device."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            # Parse request data
            data = request.data
            
            # Validate required fields
            required_fields = ['parameter', 'upper_threshold', 'lower_threshold']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }, status=400)
            
            parameter = data['parameter']
            upper_threshold = data['upper_threshold']
            lower_threshold = data['lower_threshold']
            
            # Validate parameter
            valid_parameters = [
                'temperature', 'water_level', 'feed_level', 'turbidity', 
                'dissolved_oxygen', 'ph', 'ammonia', 'battery'
            ]
            if parameter not in valid_parameters:
                return Response({
                    'success': False,
                    'error': f'parameter must be one of: {", ".join(valid_parameters)}'
                }, status=400)
            
            # Validate threshold values
            try:
                upper_threshold = float(upper_threshold)
                lower_threshold = float(lower_threshold)
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'error': 'upper_threshold and lower_threshold must be valid numbers'
                }, status=400)
            
            if lower_threshold >= upper_threshold:
                return Response({
                    'success': False,
                    'error': 'lower_threshold must be less than upper_threshold'
                }, status=400)
            
            # Get MQTT service and send threshold command
            mqtt_service = get_mqtt_bridge_service()
            command_id = mqtt_service.send_threshold_command(
                pond_pair=pond.parent_pair,
                parameter=parameter,
                upper_threshold=upper_threshold,
                lower_threshold=lower_threshold,
                pond=pond,
                user=request.user
            )
            
            if command_id:
                # Also create/update the threshold in the database
                from .services import AutomationService
                automation_service = AutomationService()
                
                # Check if threshold already exists
                existing_threshold = SensorThreshold.objects.filter(
                    pond=pond, 
                    parameter=parameter
                ).first()
                
                if existing_threshold:
                    # Update existing threshold
                    existing_threshold.upper_threshold = upper_threshold
                    existing_threshold.lower_threshold = lower_threshold
                    existing_threshold.save()
                    threshold_id = existing_threshold.id
                    action = 'updated'
                else:
                    # Create new threshold
                    threshold = automation_service.create_threshold(
                        pond=pond,
                        parameter=parameter,
                        upper_threshold=upper_threshold,
                        lower_threshold=lower_threshold,
                        automation_action='ALERT',  # Default action
                        priority=3,  # Default priority
                        alert_level='MEDIUM',  # Default alert level
                        violation_timeout=getattr(settings, 'AUTOMATION_DEFAULT_THRESHOLD_TIMEOUT', 30),
                        max_violations=getattr(settings, 'AUTOMATION_MAX_THRESHOLD_VIOLATIONS', 3),
                        send_alert=True
                    )
                    threshold_id = threshold.id
                    action = 'created'
                
                return Response({
                    'success': True,
                    'data': {
                        'command_id': command_id,
                        'threshold_id': threshold_id,
                        'message': f'Threshold {action} and command sent successfully'
                    }
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to send threshold command'
                }, status=500)
                
        except Exception as e:
            logger.error(f"Error executing threshold command for pond {pond_id}: {e}")
            return Response({
            'success': False,
            'error': str(e)
        }, status=500)


class GetDeviceHistoryView(APIView):
    """Get device command history for a specific pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            
            # Get filter parameters
            command_type = request.GET.get('command_type')
            status = request.GET.get('status')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            
            # Build queryset
            commands = DeviceCommand.objects.filter(pond=pond)
            
            # Apply filters
            if command_type:
                commands = commands.filter(command_type=command_type)
            if status:
                commands = commands.filter(status=status)
            if date_from:
                commands = commands.filter(created_at__gte=date_from)
            if date_to:
                commands = commands.filter(created_at__lte=date_to)
            
            # Order by creation date (newest first)
            commands = commands.order_by('-created_at')
            
            # Paginate results
            paginator = Paginator(commands, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize commands
            command_data = []
            for command in page_obj:
                command_data.append({
                    'id': command.id,
                    'command_id': command.command_id.hex,
                    'command_type': command.command_type,
                    'status': command.status,
                    'parameters': command.parameters,
                    'sent_at': command.sent_at.isoformat() if command.sent_at else None,
                    'acknowledged_at': command.acknowledged_at.isoformat() if command.acknowledged_at else None,
                    'completed_at': command.completed_at.isoformat() if command.completed_at else None,
                    'success': command.success,
                    'result_message': command.result_message,
                    'error_code': command.error_code,
                    'error_details': command.error_details,
                    'retry_count': command.retry_count,
                    'created_at': command.created_at.isoformat(),
                    'user': command.user.username if command.user else None,
                })
            
            return Response({
                'success': True,
                'data': {
                    'commands': command_data,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_pages': paginator.num_pages,
                        'total_count': paginator.count,
                        'has_next': page_obj.has_next(),
                        'has_previous': page_obj.has_previous(),
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting device history for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAlertsView(APIView):
    """Get alerts for a specific pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get pagination parameters
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', DEFAULT_PAGE_SIZE)), MAX_PAGE_SIZE)
            
            # Get filter parameters
            parameter = request.GET.get('parameter')
            alert_level = request.GET.get('alert_level')
            status = request.GET.get('status')
            date_from = request.GET.get('date_from')
            date_to = request.GET.get('date_to')
            
            # Build queryset
            alerts = Alert.objects.filter(pond=pond)
            
            # Apply filters
            if parameter:
                alerts = alerts.filter(parameter=parameter)
            if alert_level:
                alerts = alerts.filter(alert_level=alert_level)
            if status:
                alerts = alerts.filter(status=status)
            if date_from:
                alerts = alerts.filter(created_at__gte=date_from)
            if date_to:
                alerts = alerts.filter(created_at__lte=date_to)
            
            # Order by creation date (newest first)
            alerts = alerts.order_by('-created_at')
            
            # Paginate results
            paginator = Paginator(alerts, page_size)
            page_obj = paginator.get_page(page)
            
            # Serialize alerts
            alert_data = []
            for alert in page_obj:
                alert_data.append({
                    'id': alert.id,
                    'parameter': alert.parameter,
                    'alert_level': alert.alert_level,
                    'status': alert.status,
                    'message': alert.message,
                    'threshold_value': alert.threshold_value,
                    'current_value': alert.current_value,
                    'created_at': alert.created_at.isoformat(),
                    'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                })
            
            return Response({
                'success': True,
                'data': {
                    'alerts': alert_data,
                    'pagination': {
                        'page': page,
                        'page_size': page_size,
                        'total_pages': paginator.num_pages,
                        'total_count': paginator.count,
                        'has_next': page_obj.has_next(),
                        'has_previous': page_obj.has_previous(),
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting alerts for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AcknowledgeAlertView(APIView):
    """Acknowledge an alert."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, alert_id):
        try:
            alert = get_object_or_404(Alert, id=alert_id)
            
            # Check if user has access to this alert
            if alert.pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Acknowledge the alert
            alert.status = 'acknowledged'
            alert.save()
            
            return Response({
                'success': True,
                'data': {
                    'alert_id': alert.id,
                    'message': 'Alert acknowledged successfully'
                }
            })
            
        except Exception as e:
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ResolveAlertView(APIView):
    """Resolve an alert."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, alert_id):
        try:
            alert = get_object_or_404(Alert, id=alert_id)
            
            # Check if user has access to this alert
            if alert.pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Resolve the alert
            alert.status = 'resolved'
            alert.resolved_at = timezone.now()
            alert.save()
            
            return Response({
                'success': True,
                'data': {
                    'alert_id': alert.id,
                    'message': 'Alert resolved successfully',
                    'resolved_at': alert.resolved_at.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error resolving alert {alert_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetThresholdConfigurationView(APIView):
    """Get comprehensive threshold configuration for a pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get active thresholds
            thresholds = SensorThreshold.objects.filter(pond=pond, is_active=True)
            
            # Serialize thresholds with current status
            threshold_data = []
            for threshold in thresholds:
                # Get current sensor value for this parameter
                latest_sensor_data = SensorData.objects.filter(
                    pond=pond,
                    parameter=threshold.parameter
                ).order_by('-timestamp').first()
                
                current_value = latest_sensor_data.value if latest_sensor_data else None
                
                # Determine threshold status
                if current_value is not None:
                    if current_value > threshold.upper_threshold:
                        status = 'UPPER_VIOLATION'
                    elif current_value < threshold.lower_threshold:
                        status = 'LOWER_VIOLATION'
                    else:
                        status = 'NORMAL'
                else:
                    status = 'NO_DATA'
                
                threshold_data.append({
                    'id': threshold.id,
                    'parameter': threshold.parameter,
                    'upper_threshold': threshold.upper_threshold,
                    'lower_threshold': threshold.lower_threshold,
                    'automation_action': threshold.automation_action,
                    'priority': threshold.priority,
                    'alert_level': threshold.alert_level,
                    'is_active': threshold.is_active,
                    'violation_timeout': threshold.violation_timeout,
                    'max_violations': threshold.max_violations,
                    'created_at': threshold.created_at.isoformat(),
                    'updated_at': threshold.updated_at.isoformat(),
                    'current_value': current_value,
                    'status': status
                })
            
            # Get available parameters and actions
            from core.choices import PARAMETER_CHOICES, AUTOMATION_ACTIONS, ALERT_LEVELS
            
            return Response({
                'success': True,
                'data': {
                    'pond_id': pond.id,
                    'pond_name': pond.name,
                    'thresholds': threshold_data,
                    'count': len(threshold_data),
                    'available_parameters': [choice[0] for choice in PARAMETER_CHOICES],
                    'available_actions': [choice[0] for choice in AUTOMATION_ACTIONS],
                    'available_alert_levels': [choice[0] for choice in ALERT_LEVELS]
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting threshold configuration for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetDeviceStatusView(APIView):
    """Get comprehensive device and automation status for a pond."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get device status
            from mqtt_client.models import DeviceStatus
            try:
                device_status = DeviceStatus.objects.get(pond_pair=pond.parent_pair)
                device_info = {
                    'device_id': device_status.pond_pair.device_id,
                    'status': device_status.status,
                    'last_seen': device_status.last_seen.isoformat() if device_status.last_seen else None,
                    'is_online': device_status.is_online(),
                    'firmware_version': device_status.firmware_version,
                    'hardware_version': device_status.hardware_version,
                    'device_name': device_status.device_name,
                    'ip_address': device_status.ip_address,
                    'wifi_ssid': device_status.wifi_ssid,
                    'wifi_signal_strength': device_status.wifi_signal_strength,
                    'free_heap': device_status.free_heap,
                    'cpu_frequency': device_status.cpu_frequency,
                    'error_count': device_status.error_count,
                    'last_error': device_status.last_error,
                    'last_error_at': device_status.last_error_at.isoformat() if device_status.last_error_at else None,
                    'uptime_percentage_24h': device_status.get_uptime_percentage(24)
                }
            except DeviceStatus.DoesNotExist:
                device_info = {
                    'device_id': pond.parent_pair.device_id,
                    'status': 'UNKNOWN',
                    'last_seen': None,
                    'is_online': False,
                    'firmware_version': None,
                    'hardware_version': None,
                    'device_name': None,
                    'ip_address': None,
                    'wifi_ssid': None,
                    'wifi_signal_strength': None,
                    'free_heap': None,
                    'cpu_frequency': None,
                    'error_count': 0,
                    'last_error': None,
                    'last_error_at': None,
                    'uptime_percentage_24h': 0
                }
            
            # Get pending and failed commands
            pending_commands = DeviceCommand.objects.filter(
                pond=pond,
                status__in=['PENDING', 'SENT', 'ACKNOWLEDGED']
            ).count()
            
            failed_commands = DeviceCommand.objects.filter(
                pond=pond,
                status='FAILED'
            ).count()
            
            # Get recent automation executions
            recent_executions = AutomationExecution.objects.filter(
                pond=pond
            ).exclude(
                # Filter out automations stuck in EXECUTING status for more than 2 hours
                status='EXECUTING',
                started_at__lt=timezone.now() - timedelta(hours=2)
            ).order_by('-created_at')[:5]
            
            execution_data = []
            for execution in recent_executions:
                execution_data.append({
                    'id': execution.id,
                    'type': execution.execution_type,
                    'action': execution.action,
                    'status': execution.status,
                    'priority': execution.priority,
                    'created_at': execution.created_at.isoformat(),
                    'success': execution.success
                })
            
            # Get automation and threshold status
            service = AutomationService()
            automation_status = service.get_automation_status(pond)
            active_thresholds = service.get_active_thresholds(pond)
            
            return Response({
                'success': True,
                'data': {
                    'pond_id': pond.id,
                    'pond_name': pond.name,
                    'device_id': pond.parent_pair.device_id,
                    'device_status': device_info,
                    'pending_commands': pending_commands,
                    'failed_commands': failed_commands,
                    'recent_executions': execution_data,
                    'automation_status': automation_status,
                    'threshold_status': {
                        'active_count': active_thresholds.count(),
                        'thresholds': [{
                            'parameter': t.parameter,
                            'upper': t.upper_threshold,
                            'lower': t.lower_threshold,
                            'action': t.automation_action
                        } for t in active_thresholds]
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting device status for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CleanupStuckAutomationsView(APIView):
    """Manually trigger cleanup of stuck automation executions."""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_id):
        try:
            pond = get_object_or_404(Pond, id=pond_id)
            
            # Check if user has access to this pond
            if pond.parent_pair.owner != request.user:
                return Response({
                    'success': False,
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Get timeout parameter (default 1 hour)
            timeout_hours = int(request.data.get('timeout_hours', getattr(settings, 'AUTOMATION_CLEANUP_HOURS', 1)))
            
            # Find stuck automations
            cutoff_time = timezone.now() - timedelta(hours=timeout_hours)
            stuck_automations = AutomationExecution.objects.filter(
                pond=pond,
                status='EXECUTING',
                started_at__lt=cutoff_time
            ).order_by('started_at')
            
            if not stuck_automations.exists():
                return Response({
                    'success': True,
                    'message': 'No stuck automations found',
                    'data': {
                        'cleaned_count': 0,
                        'stuck_count': 0
                    }
                })
            
            cleaned_count = 0
            stuck_count = stuck_automations.count()
            
            for automation in stuck_automations:
                try:
                    # Check linked commands
                    linked_commands = automation.device_commands.all()
                    
                    if linked_commands.exists():
                        latest_command = linked_commands.order_by('-updated_at').first()
                        
                        if latest_command.status == 'COMPLETED':
                            automation.complete_execution(True, "Manually synced from completed command")
                            cleaned_count += 1
                        elif latest_command.status in ['FAILED', 'TIMEOUT']:
                            automation.complete_execution(False, f"Manually synced from {latest_command.status.lower()} command")
                            cleaned_count += 1
                        else:
                            # Mark as failed due to timeout
                            hours_stuck = (timezone.now() - automation.started_at).total_seconds() / 3600
                            automation.complete_execution(
                                False, 
                                f"Manually marked as failed after {hours_stuck:.1f}h",
                                f"Linked commands still in progress: {[cmd.status for cmd in linked_commands]}"
                            )
                            cleaned_count += 1
                    else:
                        # No linked commands - mark as failed
                        hours_stuck = (timezone.now() - automation.started_at).total_seconds() / 3600
                        automation.complete_execution(
                            False, 
                            f"Manually marked as failed - no linked commands",
                            f"Automation stuck for {hours_stuck:.1f}h with no device commands"
                        )
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.error(f"Error cleaning up automation {automation.id}: {e}")
                    # Try to mark as failed
                    try:
                        automation.complete_execution(False, f"Manual cleanup error - marked as failed", str(e))
                        cleaned_count += 1
                    except Exception as cleanup_error:
                        logger.error(f"Failed to mark automation {automation.id} as failed during manual cleanup: {cleanup_error}")
            
            return Response({
                'success': True,
                'message': f'Cleanup completed: {cleaned_count} automations processed',
                'data': {
                    'cleaned_count': cleaned_count,
                    'stuck_count': stuck_count,
                    'timeout_hours': timeout_hours
                }
            })
            
        except Exception as e:
            logger.error(f"Error in manual cleanup for pond {pond_id}: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogFeedEventView(APIView):
    """
    Called by Lambda to record a feed event
    Expected payload: { "user_id": 123, "pond_id": 321, "amount": 7.5 }
    """
    permission_classes = [AllowAny]  # This is called by Lambda, not user
    
    def post(self, request):
        try:
            user = User.objects.get(id=request.data['user_id'])
            pond = Pond.objects.get(id=request.data['pond_id'])
            amount = float(request.data['amount'])
        except (KeyError, User.DoesNotExist, ValueError):
            return Response({"error": "Invalid data"}, status=status.HTTP_400_BAD_REQUEST)

        now = datetime.now().date()
        weekday_start = now - timedelta(days=now.weekday())  # Monday
        month_start = now.replace(day=1)
        year_start = now.replace(month=1, day=1)

        # Log event
        FeedEvent.objects.create(user=user, pond=pond, amount=amount)

        # Update stats
        for stat_type, start in [
            ('daily', now),
            ('weekly', weekday_start),
            ('monthly', month_start),
            ('yearly', year_start),
        ]:
            stat, _ = FeedStat.objects.get_or_create(user=user, pond=pond, stat_type=stat_type, start_date=start)
            stat.amount += amount
            stat.save()

        return Response({"status": "logged"})



