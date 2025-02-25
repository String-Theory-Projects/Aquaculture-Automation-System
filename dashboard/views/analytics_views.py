from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from django.db.models.functions import TruncHour, TruncDate
from dashboard.models import SensorData, Pond, PondControl
from dashboard.serializers.analytics_serializers import (
    CurrentSensorDataSerializer,
    PondControlSerializer,
    PondDropdownSerializer,
    HistoricalDataSerializer
)

class DashboardDataView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        pond_id = request.query_params.get('pond_id')
        if not pond_id:
            return Response(
                {"error": "Pond ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Get latest sensor and pond reading
            latest_sensor_reading = SensorData.objects.filter(
                pond_id=pond_id
            ).latest('timestamp')

            latest_pond_reading = PondControl.objects.filter(
                pond_id=pond_id
            ).last()
            
            current_data = CurrentSensorDataSerializer(latest_sensor_reading).data
            pond_state = PondControlSerializer(latest_pond_reading).data
            
            return Response({
                "current_data": current_data,
                "pond_state": pond_state,
            })
        
        except SensorData.DoesNotExist:
            return Response(
                {"error": "No sensor data available"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class HistoricalDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        pond_id = int(self.request.query_params.get('pond_id'))
        time_range = str(self.request.query_params.get('range', '24h'))
        
        if not pond_id:
            return Response(
                {"detail": "pond_id query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the pond exists and the user is the owner
        pond = get_object_or_404(Pond, id=pond_id)
        if request.user != pond.owner:
            return Response(
                {"detail": "You do not have permission to access this pond's data."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Determine time range parameters
        now = timezone.now()
        
        if time_range == '24h':
            # start_time = now - timedelta(hours=24)
            start_time = now - timedelta(hours=30*24)
            now = now - timedelta(hours=29*24)
            interval_hours = 1
            interval_name = 'hour'
        elif time_range == '1w':
            # start_time = now - timedelta(days=7)
            start_time = now - timedelta(days=5*7)
            now = now - timedelta(days=4*7)
            interval_hours = 6  # Every 6 hours for a week (28 data points)
            interval_name = 'day_hour'
        elif time_range == '1m':
            # start_time = now - timedelta(days=30)
            start_time = now - timedelta(days=2*30)
            now = now - timedelta(days=1*30)
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
            "historical_data": serializer.data,
            "time_range": time_range
        })


class UserPondsDropdownView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PondDropdownSerializer
    
    def get_queryset(self):
        return Pond.objects.filter(
            owner=self.request.user,
            is_active=True
        )
