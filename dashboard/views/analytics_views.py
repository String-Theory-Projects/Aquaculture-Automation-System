from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from django.db.models.functions import TruncHour, TruncDate
from dashboard.models import SensorData, Pond
from dashboard.serializers.analytics_serializers import (
    CurrentSensorDataSerializer,
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
            # Get latest sensor reading
            latest_reading = SensorData.objects.filter(
                pond_id=pond_id
            ).latest('timestamp')
            
            current_data = CurrentSensorDataSerializer(latest_reading).data
            
            return Response({
                "current_data": current_data,
            })
        except SensorData.DoesNotExist:
            return Response(
                {"error": "No sensor data available"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class HistoricalDataView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_aggregated_data(self, pond_id, start_time, interval='hour'):
        truncate_func = {
            'hour': TruncHour('timestamp'),
            'day': TruncDate('timestamp')
        }.get(interval, TruncHour('timestamp'))
        
        if not Pond.objects.filter(id=pond_id).exists():
            return None
            
        # Make sure start_time is timezone-aware
        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time)
            
        data = SensorData.objects.filter(
            pond_id=pond_id,
            timestamp__gte=start_time
        ).annotate(
            interval=truncate_func
        ).values('interval').annotate(
            temperature=Avg('temperature'),
            water_level=Avg('water_level'),
            turbidity=Avg('turbidity'),
            dissolved_oxygen=Avg('dissolved_oxygen'),
            ph=Avg('ph'),
            feed_level=Avg('feed_level')
        ).order_by('interval')
        
        # Debug print
        print(f"Query returned {data.count()} records")
        print(f"Start time: {start_time}")
        print(f"SQL Query: {data.query}")
        
        return data

    def get(self, request, *args, **kwargs):
        pond_id = request.query_params.get('pond_id')
        time_range = request.query_params.get('range', '24h')
        
        if not pond_id:
            return Response(
                {"error": "Pond ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate time_range
        valid_ranges = {'24h', '1w', '1m'}
        if time_range not in valid_ranges:
            time_range = '24h'
            
        now = timezone.now()
        
        ranges = {
            '24h': (now - timedelta(days=1), 'hour'),
            '1w': (now - timedelta(weeks=1), 'hour'),
            '1m': (now - timedelta(days=30), 'day')
        }
        
        start_time, interval = ranges[time_range]
        
        historical_data = self.get_aggregated_data(pond_id, start_time, interval)
        
        if historical_data is None:
            return Response(
                {"error": f"Pond with ID {pond_id} not found"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = HistoricalDataSerializer(historical_data, many=True)
        
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
