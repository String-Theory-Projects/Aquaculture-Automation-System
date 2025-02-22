from django.core.exceptions import ValidationError, PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from django.db import transaction

from dashboard.models import Pond, WiFiConfig, AutomationSchedule
from dashboard.serializers.settings_serializers import AutomationScheduleSerializer, WiFiConfigSerializer


User = get_user_model()


class WiFiConfigView(APIView):
    """
    API view for managing WiFi configuration for a pond
    """
    permission_classes = [IsAuthenticated]
    
    def get_pond(self, pk, user):
        """Helper method to get pond and verify ownership"""
        pond = get_object_or_404(Pond, pk=pk)
        if pond.owner != user:
            raise PermissionDenied("You don't have permission to access this pond")
        return pond
    
    def get(self, request, pond_id):
        """Get WiFi configuration for a pond"""
        pond = self.get_pond(pond_id, request.user)
        
        try:
            wifi_config = pond.wifi_config
            serializer = WiFiConfigSerializer(wifi_config)
            return Response(serializer.data)
        except WiFiConfig.DoesNotExist:
            return Response({
                'message': 'No WiFi configuration exists for this pond'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def post(self, request, pond_id):
        """Create WiFi configuration for a pond"""
        pond = self.get_pond(pond_id, request.user)
        
        # Check if WiFi config already exists
        try:
            pond.wifi_config
            return Response({
                'message': 'WiFi configuration already exists. Use PUT to update.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except WiFiConfig.DoesNotExist:
            pass
        
        serializer = WiFiConfigSerializer(data=request.data)
        if serializer.is_valid():
            wifi_config = serializer.save(pond=pond)
            return Response({
                'message': 'WiFi configuration created successfully',
                'wifi_config': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pond_id):
        """Update WiFi configuration for a pond"""
        pond = self.get_pond(pond_id, request.user)
        
        try:
            wifi_config = pond.wifi_config
            serializer = WiFiConfigSerializer(wifi_config, data=request.data, partial=True)
            
            if serializer.is_valid():
                # Mark as not synced if SSID or password changed
                if 'ssid' in request.data or 'password' in request.data:
                    serializer.save(is_config_synced=False)
                else:
                    serializer.save()
                
                return Response({
                    'message': 'WiFi configuration updated successfully',
                    'wifi_config': serializer.data
                })
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except WiFiConfig.DoesNotExist:
            return Response({
                'message': 'No WiFi configuration exists for this pond. Use POST to create.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def delete(self, request, pond_id):
        """Delete WiFi configuration for a pond"""
        pond = self.get_pond(pond_id, request.user)
        
        try:
            wifi_config = pond.wifi_config
            wifi_config.delete()
            return Response({
                'message': 'WiFi configuration deleted successfully'
            }, status=status.HTTP_200_OK)
        except WiFiConfig.DoesNotExist:
            return Response({
                'message': 'No WiFi configuration exists for this pond'
            }, status=status.HTTP_404_NOT_FOUND)


class AutomationScheduleView(APIView):
    """
    API view for managing automation schedules for a pond
    """
    permission_classes = [IsAuthenticated]
    
    def get_pond(self, pk, user):
        """Helper method to get pond and verify ownership"""
        pond = get_object_or_404(Pond, pk=pk)
        if pond.owner != user:
            raise PermissionDenied("You don't have permission to access this pond")
        return pond
    
    def get(self, request, pond_id):
        """Get all automation schedules for a pond"""
        pond = self.get_pond(pond_id, request.user)
        schedules = AutomationSchedule.objects.filter(pond=pond)
        serializer = AutomationScheduleSerializer(schedules, many=True)
        return Response(serializer.data)
    
    def post(self, request, pond_id):
        """Create a new automation schedule"""
        pond = self.get_pond(pond_id, request.user)
        
        serializer = AutomationScheduleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(pond=pond)
            return Response({
                'message': 'Automation schedule created successfully',
                'schedule': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AutomationScheduleDetailView(APIView):
    """
    API view for managing individual automation schedules
    """
    permission_classes = [IsAuthenticated]
    
    def get_schedule(self, pk, user):
        """Helper method to get schedule and verify ownership"""
        schedule = get_object_or_404(AutomationSchedule, pk=pk)
        if schedule.pond.owner != user:
            raise PermissionDenied("You don't have permission to access this schedule")
        return schedule
    
    def get(self, request, schedule_id):
        """Get a specific automation schedule"""
        schedule = self.get_schedule(schedule_id, request.user)
        serializer = AutomationScheduleSerializer(schedule)
        return Response(serializer.data)
    
    def put(self, request, schedule_id):
        """Update an automation schedule"""
        schedule = self.get_schedule(schedule_id, request.user)
        
        serializer = AutomationScheduleSerializer(
            schedule, 
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Automation schedule updated successfully',
                'schedule': serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, schedule_id):
        """Delete an automation schedule"""
        schedule = self.get_schedule(schedule_id, request.user)
        schedule.delete()
        return Response({
            'message': 'Automation schedule deleted successfully'
        }, status=status.HTTP_200_OK)