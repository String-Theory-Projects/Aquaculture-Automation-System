from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ponds.models import Pond, SensorData
from .serializers import (
    CurrentSensorDataSerializer,
    HistoricalDataSerializer, 
    PondDropdownSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_current_data(request):
    """
    Get current sensor data for a specific pond
    """
    pond_id = request.query_params.get('pond_id')
    
    if not pond_id:
        return Response(
            {"detail": "pond_id query parameter is required."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        pond_id = int(pond_id)
    except ValueError:
        return Response(
            {"detail": "pond_id must be a valid integer."},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify the pond exists and the user is the owner
    pond = get_object_or_404(Pond, id=pond_id)
    if request.user != pond.parent_pair.owner:
        return Response(
            {"detail": "You do not have permission to access this pond's data."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get the most recent sensor reading for this pond
    latest_data = SensorData.objects.filter(pond=pond).order_by('-timestamp').first()
    
    if not latest_data:
        return Response(
            {"detail": "No sensor data available for this pond."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = CurrentSensorDataSerializer(latest_data)
    return Response({
        'current_data': serializer.data
    })


class HistoricalDataView(APIView):
    """
    API view for retrieving historical sensor data aggregated by time intervals.
    
    This view provides time-series data for pond sensors by aggregating raw sensor readings
    into meaningful time intervals. It supports three time ranges: 24 hours, 1 week, and 1 month.
    
    Purpose:
    - Provides historical trend analysis for pond monitoring
    - Aggregates multiple sensor readings into time-based intervals
    - Enables data visualization and trend identification
    - Supports different granularity levels based on time range
    
    How it works:
    1. Validates user permissions and pond ownership
    2. Determines time range and aggregation interval based on 'range' parameter
    3. Fetches all SensorData records within the specified time window
    4. Groups data into time intervals and calculates averages for each sensor metric
    5. Returns aggregated data with timestamps for each interval
    
    Time Range Configurations:
    - '24h': 24 hourly intervals (1-hour granularity)
    - '1w': 28 intervals of 6 hours each (6-hour granularity) 
    - '1m': 30 daily intervals (24-hour granularity)
    
    Aggregation Logic:
    - Uses Django's Avg() aggregation function for each sensor metric
    - Only includes intervals that have at least one sensor reading
    - Returns averaged values for: temperature, water_level, turbidity, 
      dissolved_oxygen, ph, and feed_level
    
    Important Notes:
    - SensorData.timestamp uses auto_now_add=True, meaning timestamps are automatically
      set to the current time when records are created. This affects data grouping and
      should be considered when writing functions that need specific timestamps.
    - The view only returns intervals that contain sensor data (empty intervals are skipped)
    - All timestamps are returned in ISO format for frontend consumption
    
    Query Parameters:
    - pond_id (required): Integer ID of the pond to get data for
    - range (optional): Time range ('24h', '1w', '1m'). Defaults to '24h'
    
    Response Format:
    {
        'historical_data': [
            {
                'timestamp': '2025-01-15T10:00:00Z',
                'temperature': 25.5,
                'water_level': 80,
                'turbidity': 10.2,
                'dissolved_oxygen': 7.8,
                'ph': 7.2,
                'feed_level': 85
            },
            ...
        ],
        'time_range': '24h'
    }
    
    Error Responses:
    - 400: Missing or invalid pond_id, invalid range parameter
    - 403: User doesn't own the specified pond
    - 404: Pond not found or no sensor data available
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        pond_id = self.request.query_params.get('pond_id')
        time_range = str(self.request.query_params.get('range', '24h'))
        
        if not pond_id:
            return Response(
                {"error": "pond_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pond_id = int(pond_id)
        except ValueError:
            return Response(
                {"detail": "pond_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the pond exists and the user is the owner
        pond = get_object_or_404(Pond, id=pond_id)
        if request.user != pond.parent_pair.owner:
            return Response(
                {"detail": "You do not have permission to access this pond's data."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Determine time range parameters
        now = timezone.now()
        
        if time_range == '24h':
            start_time = now - timedelta(hours=24)
            interval_hours = 1
            interval_name = 'hour'
        elif time_range == '1w':
            start_time = now - timedelta(days=7)
            interval_hours = 6  # Every 6 hours for a week (28 data points)
            interval_name = 'day_hour'
        elif time_range == '1m':
            start_time = now - timedelta(days=30)
            interval_hours = 24  # Daily for a month (30 data points)
            interval_name = 'day'
        else:
            return Response(
                {"detail": "Invalid range parameter. Use '24h', '1w', or '1m'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all sensor data for the pond within the time range
        sensor_data = SensorData.objects.filter(
            pond=pond,
            timestamp__gte=start_time,
            timestamp__lte=now
        )
        
        if not sensor_data.exists():
            return Response(
                {"detail": "No sensor data available for the specified time range."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Aggregate data by the appropriate time interval
        aggregated_data = []
        
        # Calculate intervals based on time range
        current_interval = start_time
        while current_interval < now:
            next_interval = current_interval + timedelta(hours=interval_hours)
            
            # Get data for this interval
            interval_data = sensor_data.filter(
                timestamp__gte=current_interval,
                timestamp__lt=next_interval
            ).aggregate(
                temperature=Avg('temperature'),
                water_level=Avg('water_level'),
                turbidity=Avg('turbidity'),
                dissolved_oxygen=Avg('dissolved_oxygen'),
                ph=Avg('ph'),
                feed_level=Avg('feed_level')
            )
            
            # Only add data if we have readings for this interval
            if any(value is not None for value in interval_data.values()):
                # Add timestamp to the aggregated data
                interval_data['interval'] = current_interval
                aggregated_data.append(interval_data)
            
            # Move to next interval
            current_interval = next_interval
        
        # Serialize the aggregated data
        serializer = HistoricalDataSerializer(aggregated_data, many=True)
        
        # Return the response
        return Response({
            'historical_data': serializer.data,
            'time_range': time_range
        })


class DashboardDataView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Get aggregated dashboard data for a specific pond
        """
        pond_id = request.query_params.get('pond_id')
        
        if not pond_id:
            return Response(
                {"detail": "pond_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            pond_id = int(pond_id)
        except ValueError:
            return Response(
                {"detail": "pond_id must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the pond exists and the user is the owner
        pond = get_object_or_404(Pond, id=pond_id)
        if request.user != pond.parent_pair.owner:
            return Response(
                {"detail": "You do not have permission to access this pond's data."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get current data
        latest_data = SensorData.objects.filter(pond=pond).order_by('-timestamp').first()
        
        if not latest_data:
            return Response(
                {"detail": "No sensor data available for this pond."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get historical data for the last 24 hours
        now = timezone.now()
        start_time = now - timedelta(hours=24)
        
        historical_data = SensorData.objects.filter(
            pond=pond,
            timestamp__gte=start_time,
            timestamp__lte=now
        ).aggregate(
            avg_temperature=Avg('temperature'),
            avg_water_level=Avg('water_level'),
            avg_turbidity=Avg('turbidity'),
            avg_dissolved_oxygen=Avg('dissolved_oxygen'),
            avg_ph=Avg('ph'),
            avg_feed_level=Avg('feed_level')
        )
        
        # Combine current and historical data
        current_serializer = CurrentSensorDataSerializer(latest_data)
        
        return Response({
            'current_data': current_serializer.data,
            'historical_summary': historical_data,
            'pond_info': {
                'id': pond.id,
                'name': pond.name,
                'is_active': pond.is_active
            }
        })


class UserPondsDropdownView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PondDropdownSerializer
    
    def get_queryset(self):
        """Get all ponds owned by the authenticated user"""
        return Pond.objects.filter(
            parent_pair__owner=self.request.user,
            is_active=True
        ).select_related('parent_pair')
