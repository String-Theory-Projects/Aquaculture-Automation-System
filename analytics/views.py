from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Avg
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ponds.models import Pond, SensorData
from automation.models import DeviceCommand


class PondFeedMultiStatsView(APIView):
    """
    API view for retrieving feed statistics for multiple time periods in one call.
    
    This view provides feed statistics for daily, weekly, monthly, and yearly periods
    in a single optimized database query to avoid multiple API calls.
    
    URL Parameters:
    - pond_id (required): Integer ID of the pond to get data for
    
    Response Format:
    {
        'pond_id': 1,
        'periods': {
            'daily': {
                'total_amount': 2.5,
                'command_count': 3,
                'period_start': '2025-01-15',
                'period_end': '2025-01-15'
            },
            'weekly': { ... },
            'monthly': { ... },
            'yearly': { ... }
        }
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id):
        # Verify the pond exists and the user is the owner
        pond = get_object_or_404(Pond, id=pond_id)
        if request.user != pond.parent_pair.owner:
            return Response(
                {"detail": "You do not have permission to access this pond's data."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create cache key for this specific query
        cache_key = f"feed_multi_stats_{pond_id}"
        
        # Try to get from cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)
        
        now = timezone.now().date()
        
        # Calculate all time ranges - proper period calculations
        periods = {
            'daily': {
                'start_date': now,
                'end_date': now
            },
            'weekly': {
                'start_date': now - timedelta(days=now.weekday()),  # Start of current week (Monday)
                'end_date': now
            },
            'monthly': {
                'start_date': now.replace(day=1),  # First day of current month
                'end_date': now
            },
            'yearly': {
                'start_date': now.replace(month=1, day=1),  # First day of current year
                'end_date': now
            }
        }
        
        # Get all feed commands for the maximum range (yearly) in one query
        yearly_start = periods['yearly']['start_date']
        yearly_end = periods['yearly']['end_date']
        
        feed_commands = DeviceCommand.objects.filter(
            pond=pond,
            command_type='FEED',
            status='COMPLETED',
            success=True,
            completed_at__date__range=[yearly_start, yearly_end]
        ).only('parameters', 'completed_at')
        
        # Process all commands once and calculate for each period
        results = {}
        
        for period_name, period_data in periods.items():
            start_date = period_data['start_date']
            end_date = period_data['end_date']
            
            # Filter commands for this period
            period_commands = [
                cmd for cmd in feed_commands.iterator(chunk_size=1000)
                if cmd.completed_at and start_date <= cmd.completed_at.date() <= end_date
            ]
            
            # Calculate statistics for this period
            command_count = len(period_commands)
            total_amount = 0.0
            
            for command in period_commands:
                amount = command.parameters.get('amount', 0)
                if isinstance(amount, (int, float)):
                    total_amount += amount
            
            results[period_name] = {
                'total_amount': total_amount,
                'command_count': command_count,
                'period_start': start_date,
                'period_end': end_date,
                'debug_commands_found': len(period_commands)  # Debug info
            }
        
        # Prepare response
        result = {
            'pond_id': pond_id,
            'periods': results
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, result, 300)
        
        return Response(result)


class PondFeedStatsView(APIView):
    """
    API view for retrieving feed statistics for a specific pond.
    
    This view provides real-time feed statistics computed from DeviceCommand records
    for different time periods (daily, weekly, monthly, yearly).
    
    Query Parameters:
    - pond_id (required): Integer ID of the pond to get feed stats for
    - period (optional): Time period ('daily', 'weekly', 'monthly', 'yearly'). Defaults to 'daily'
    
    Response Format:
    {
        'pond_id': 1,
        'period': 'daily',
        'total_amount': 2.5,
        'command_count': 3,
        'period_start': '2025-01-15',
        'period_end': '2025-01-15',
        'last_feed': '2025-01-15T14:30:00Z'
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        pond_id = request.GET.get('pond_id')
        period = request.GET.get('period', 'daily')
        
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
        
        # Calculate time range based on period
        now = timezone.now().date()
        
        if period == 'daily':
            start_date = now
            end_date = now
        elif period == 'weekly':
            start_date = now - timedelta(days=now.weekday())  # Start of week (Monday)
            end_date = now
        elif period == 'monthly':
            start_date = now.replace(day=1)  # First day of month
            end_date = now
        elif period == 'yearly':
            start_date = now.replace(month=1, day=1)  # First day of year
            end_date = now
        else:
            return Response(
                {"detail": "Invalid period parameter. Use 'daily', 'weekly', 'monthly', or 'yearly'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create cache key for this specific query
        cache_key = f"feed_stats_{pond_id}_{period}_{start_date}_{end_date}"
        
        # Try to get from cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)
        
        # Use database-agnostic approach with ORM for better compatibility
        # Get feed commands for the period with optimized query
        feed_commands = DeviceCommand.objects.filter(
            pond=pond,
            command_type='FEED',
            status='COMPLETED',
            success=True,
            completed_at__date__range=[start_date, end_date]
        ).only('parameters', 'completed_at')
        
        # Calculate statistics efficiently
        command_count = feed_commands.count()
        total_amount = 0.0
        
        # Process in chunks to avoid memory issues with large datasets
        chunk_size = 1000
        for i in range(0, command_count, chunk_size):
            chunk = feed_commands[i:i + chunk_size]
            for command in chunk:
                amount = command.parameters.get('amount', 0)
                if isinstance(amount, (int, float)):
                    total_amount += amount
        
        # Get last feed timestamp efficiently
        last_feed = feed_commands.order_by('-completed_at').first()
        last_feed_time = last_feed.completed_at if last_feed else None
        
        # Prepare response
        result = {
            'pond_id': pond_id,
            'period': period,
            'total_amount': total_amount,
            'command_count': command_count,
            'period_start': start_date,
            'period_end': end_date,
            'last_feed': last_feed_time
        }
        
        # Cache for 5 minutes (300 seconds)
        cache.set(cache_key, result, 300)
        
        return Response(result)


class PondFeedHistoryView(APIView):
    """
    API view for retrieving historical feed statistics for a specific pond.
    
    This view provides historical feed data aggregated by time periods,
    showing feed amounts and command counts over time.
    
    Query Parameters:
    - pond_id (required): Integer ID of the pond to get feed history for
    - period (optional): Time period ('daily', 'weekly', 'monthly'). Defaults to 'daily'
    - days (optional): Number of days to look back. Defaults to 30
    
    Response Format:
    {
        'pond_id': 1,
        'period': 'daily',
        'days': 30,
        'history': [
            {
                'date': '2025-01-15',
                'total_amount': 2.5,
                'command_count': 3
            },
            ...
        ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        pond_id = request.GET.get('pond_id')
        period = request.GET.get('period', 'daily')
        
        try:
            days = int(request.GET.get('days', 30))
        except (ValueError, TypeError):
            return Response(
                {"detail": "days parameter must be a valid integer."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Create cache key for this specific query
        cache_key = f"feed_history_{pond_id}_{period}_{days}_{start_date}_{end_date}"
        
        # Try to get from cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)
        
        # Use database-agnostic approach with ORM for better compatibility
        # Get feed commands for the period with optimized query
        feed_commands = DeviceCommand.objects.filter(
            pond=pond,
            command_type='FEED',
            status='COMPLETED',
            success=True,
            completed_at__date__range=[start_date, end_date]
        ).only('parameters', 'completed_at')
        
        # Group by date efficiently using Python
        daily_data = {}
        for command in feed_commands.iterator(chunk_size=1000):
            if command.completed_at:
                feed_date = command.completed_at.date()
                if feed_date not in daily_data:
                    daily_data[feed_date] = {'command_count': 0, 'total_amount': 0.0}
                
                daily_data[feed_date]['command_count'] += 1
                amount = command.parameters.get('amount', 0)
                if isinstance(amount, (int, float)):
                    daily_data[feed_date]['total_amount'] += amount
        
        # Build history array with all dates, including those with no data
        history = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date in daily_data:
                history.append({
                    'date': current_date,
                    'total_amount': daily_data[current_date]['total_amount'],
                    'command_count': daily_data[current_date]['command_count']
                })
            else:
                history.append({
                    'date': current_date,
                    'total_amount': 0.0,
                    'command_count': 0
                })
            
            current_date += timedelta(days=1)
        
        # Prepare response
        result = {
            'pond_id': pond_id,
            'period': period,
            'days': days,
            'history': history
        }
        
        # Cache for 10 minutes (600 seconds) - longer cache for historical data
        cache.set(cache_key, result, 600)
        
        return Response(result)


class HistoricalDataView(APIView):
    """
    API view for retrieving historical sensor data with smart aggregation.
    
    This view provides aggregated sensor data for different time periods:
    - 24h: 24 hourly averages
    - 1w: 21 data points (3 per day × 7 days: morning, afternoon, night)
    - 1m: 90 data points (3 per day × 30 days: morning, afternoon, night)
    
    URL Parameters:
    - pond_id (required): Integer ID of the pond to get data for
    
    Query Parameters:
    - timeframe (required): Time period ('24h', '1w', '1m')
    
    Response Format:
    {
        'timeframe': '24h',
        'pond_id': 1,
        'data': [
            {
                'timestamp': '2024-01-15T00:00:00Z',
                'temperature': 25.5,
                'dissolved_oxygen': 6.2,
                'ph': 7.1,
                'water_level': 85.0
            },
            ...
        ]
    }
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pond_id, *args, **kwargs):
        timeframe = request.GET.get('timeframe')
        
        if not timeframe:
            return Response(
                {"error": "timeframe query parameter is required. Use '24h', '1w', or '1m'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if timeframe not in ['24h', '1w', '1m']:
            return Response(
                {"error": "Invalid timeframe. Use '24h', '1w', or '1m'."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the pond exists and the user is the owner
        pond = get_object_or_404(Pond, id=pond_id)
        if request.user != pond.parent_pair.owner:
            return Response(
                {"detail": "You do not have permission to access this pond's data."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Calculate time range based on timeframe
        now = timezone.now()
        data = []
        
        if timeframe == '24h':
            start_time = now - timedelta(hours=24)
            data = self._get_hourly_data(pond, start_time, now)
        elif timeframe == '1w':
            start_time = now - timedelta(days=7)
            data = self._get_daily_segments_data(pond, start_time, now, 7)
        elif timeframe == '1m':
            start_time = now - timedelta(days=30)
            data = self._get_daily_segments_data(pond, start_time, now, 30)
        
        return Response({
            'timeframe': timeframe,
            'pond_id': pond_id,
            'data': data
        })
    
    def _get_hourly_data(self, pond, start_time, end_time):
        """Get hourly aggregated data for 24h timeframe."""
        data = []
        
        # Get all sensor data for the pond in the time range
        sensor_data = SensorData.objects.filter(
            pond=pond,
            timestamp__range=[start_time, end_time]
        ).exclude(
            temperature__isnull=True,
            dissolved_oxygen__isnull=True,
            ph__isnull=True,
            water_level__isnull=True
        )
        
        # Group by hour and calculate averages
        current_time = start_time.replace(minute=0, second=0, microsecond=0)
        
        while current_time < end_time:
            next_hour = current_time + timedelta(hours=1)
            
            # Get data for this hour
            hour_data = sensor_data.filter(
                timestamp__gte=current_time,
                timestamp__lt=next_hour
            )
            
            if hour_data.exists():
                # Calculate averages for this hour
                avg_data = hour_data.aggregate(
                    temperature=Avg('temperature'),
                    dissolved_oxygen=Avg('dissolved_oxygen'),
                    ph=Avg('ph'),
                    water_level=Avg('water_level')
                )
                
                data.append({
                    'timestamp': current_time.isoformat(),
                    'temperature': round(avg_data['temperature'] or 0, 2),
                    'dissolved_oxygen': round(avg_data['dissolved_oxygen'] or 0, 2),
                    'ph': round(avg_data['ph'] or 0, 2),
                    'water_level': round(avg_data['water_level'] or 0, 2)
                })
            else:
                # No data for this hour, add null values
                data.append({
                    'timestamp': current_time.isoformat(),
                    'temperature': None,
                    'dissolved_oxygen': None,
                    'ph': None,
                    'water_level': None
                })
            
            current_time = next_hour
        
        return data
    
    def _get_daily_segments_data(self, pond, start_time, end_time, _days):
        """Get daily segment data (morning, afternoon, night) for weekly/monthly timeframes."""
        data = []
        
        # Get all sensor data for the pond in the time range
        sensor_data = SensorData.objects.filter(
            pond=pond,
            timestamp__range=[start_time, end_time]
        ).exclude(
            temperature__isnull=True,
            dissolved_oxygen__isnull=True,
            ph__isnull=True,
            water_level__isnull=True
        )
        
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            # Define 8-hour segments for the day
            segments = [
                ('morning', 0, 8),    # 00:00-08:00
                ('afternoon', 8, 16), # 08:00-16:00
                ('night', 16, 24)     # 16:00-24:00 (will be handled as 23:59:59)
            ]
            
            for segment_name, start_hour, end_hour in segments:
                # Create datetime objects for this segment
                segment_start = timezone.make_aware(
                    datetime.combine(current_date, datetime.min.time().replace(hour=start_hour))
                )
                
                # Handle the 24-hour case (night segment) properly
                if end_hour == 24:
                    # For the night segment, end at 23:59:59 of the same day
                    segment_end = timezone.make_aware(
                        datetime.combine(current_date, datetime.max.time().replace(microsecond=0))
                    )
                else:
                    segment_end = timezone.make_aware(
                        datetime.combine(current_date, datetime.min.time().replace(hour=end_hour))
                    )
                
                # Get data for this segment
                segment_data = sensor_data.filter(
                    timestamp__gte=segment_start,
                    timestamp__lt=segment_end
                )
                
                if segment_data.exists():
                    # Calculate averages for this segment
                    avg_data = segment_data.aggregate(
                        temperature=Avg('temperature'),
                        dissolved_oxygen=Avg('dissolved_oxygen'),
                        ph=Avg('ph'),
                        water_level=Avg('water_level')
                    )
                    
                    data.append({
                        'timestamp': segment_start.isoformat(),
                        'segment': segment_name,
                        'temperature': round(avg_data['temperature'] or 0, 2),
                        'dissolved_oxygen': round(avg_data['dissolved_oxygen'] or 0, 2),
                        'ph': round(avg_data['ph'] or 0, 2),
                        'water_level': round(avg_data['water_level'] or 0, 2)
                    })
                else:
                    # No data for this segment, add null values
                    data.append({
                        'timestamp': segment_start.isoformat(),
                        'segment': segment_name,
                        'temperature': None,
                        'dissolved_oxygen': None,
                        'ph': None,
                        'water_level': None
                    })
            
            current_date += timedelta(days=1)
        
        return data