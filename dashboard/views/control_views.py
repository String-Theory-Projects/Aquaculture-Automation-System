# dashboard/views/control_views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from asgiref.sync import sync_to_async, async_to_sync
import asyncio
import logging
from django.utils import timezone

from dashboard.models import Pond, DeviceLog, PondControl, MQTTMessage
from dashboard.serializers.control_serializers import (
    DeviceLogSerializer,
    FeedDispenseSerializer,
    WaterValveSerializer,
    PondControlSerializer
)
# from dashboard.mqtt.client import get_mqtt_client

logger = logging.getLogger(__name__)

# Custom pagination for device logs
class DeviceLogPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

# Filter set for device logs    
class DeviceLogFilter(filters.FilterSet):
    log_type = filters.ChoiceFilter(choices=DeviceLog.LOG_TYPES)
    start_date = filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    end_date = filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')
    
    class Meta:
        model = DeviceLog
        fields = ['log_type', 'start_date', 'end_date']

class DeviceLogView(generics.ListAPIView):
    """
    API view for retrieving device logs for a specific pond
    
    Filters:
    - log_type: Filter by log type (INFO, ERROR, ACTION, WIFI)
    - start_date: Filter logs after this date (YYYY-MM-DDThh:mm:ss)
    - end_date: Filter logs before this date (YYYY-MM-DDThh:mm:ss)
    
    Pagination:
    - page: Page number
    - page_size: Number of logs per page (default 25, max 100)
    """
    serializer_class = DeviceLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = DeviceLogPagination
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = DeviceLogFilter
    
    def get_queryset(self):
        # Get pond_id from URL path
        pond_id = self.kwargs.get('pond_id')
        
        # Check if pond exists and user has access
        pond = get_object_or_404(Pond, id=pond_id, owner=self.request.user)
        
        # Return queryset filtered by pond
        return DeviceLog.objects.filter(pond=pond).order_by('-timestamp')
    

class FeedDispenserView(generics.CreateAPIView):
    """
    API view for sending feed dispenser commands to a pond
    
    Requires:
    - feed_amount: Amount of feed to dispense in grams (0-1000)
    
    Returns:
    - Command status and details
    
    Note: This operation is performed asynchronously with a timeout
    """
    serializer_class = FeedDispenseSerializer
    permission_classes = [IsAuthenticated]
    
    # TODO


class WaterValveControlView(generics.CreateAPIView):
    """
    API view for controlling the water valve of a pond
    
    Requires:
    - valve_state: Boolean indicating whether to open (True) or close (False) the valve
    
    Returns:
    - Command status and details
    
    Note: This operation is performed asynchronously with a timeout
    """
    serializer_class = WaterValveSerializer
    permission_classes = [IsAuthenticated]
    
    # TODO

    # For aethetic functionality (only changes valve_state in pond model)
    def post(self, request, pond_id):
        # 1. Validate the incoming payload
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        valve_state = serializer.validated_data['valve_state']

        # 2. Lookup the existing PondControl for this pond
        pond_control = get_object_or_404(PondControl, pond__id=pond_id)

        # 3. Update and save
        pond_control.water_valve_state = valve_state
        pond_control.save()

        # 4. Return the full PondControl representation
        output = PondControlSerializer(pond_control)
        return Response(output.data, status=status.HTTP_200_OK)


class ExecuteAutomationView(generics.GenericAPIView):
    """
    API view for manually executing an automation schedule
    
    This allows testing of automation schedules without waiting for their scheduled time
    
    Permissions:
    - User must be authenticated
    - User must own the associated pond
    """
    permission_classes = [IsAuthenticated]
    
    # TODO
    