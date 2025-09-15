from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg, Sum, Count
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ponds.models import Pond, SensorData
from automation.models import DeviceCommand


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
    
    def get(self, request, *args, **kwargs):
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
        
        # Get feed commands for the period
        feed_commands = DeviceCommand.objects.filter(
            pond=pond,
            command_type='FEED',
            status='COMPLETED',
            success=True,
            completed_at__date__range=[start_date, end_date]
        )
        
        # Calculate statistics
        # Note: Can't aggregate JSON fields directly, so we'll calculate manually
        total_amount = 0.0
        command_count = 0
        
        for command in feed_commands:
            amount = command.parameters.get('amount', 0)
            if isinstance(amount, (int, float)):
                total_amount += amount
            command_count += 1
        
        # Get last feed timestamp
        last_feed = feed_commands.order_by('-completed_at').first()
        last_feed_time = last_feed.completed_at if last_feed else None
        
        return Response({
            'pond_id': pond_id,
            'period': period,
            'total_amount': total_amount,
            'command_count': command_count,
            'period_start': start_date,
            'period_end': end_date,
            'last_feed': last_feed_time
        })


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
    
    def get(self, request, *args, **kwargs):
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
        
        # Get feed commands for the period
        feed_commands = DeviceCommand.objects.filter(
            pond=pond,
            command_type='FEED',
            status='COMPLETED',
            success=True,
            completed_at__date__range=[start_date, end_date]
        )
        
        # Group by date and calculate daily stats
        history = []
        current_date = start_date
        
        while current_date <= end_date:
            daily_commands = feed_commands.filter(completed_at__date=current_date)
            
            # Calculate daily stats manually (can't aggregate JSON fields)
            daily_total_amount = 0.0
            daily_command_count = 0
            
            for command in daily_commands:
                amount = command.parameters.get('amount', 0)
                if isinstance(amount, (int, float)):
                    daily_total_amount += amount
                daily_command_count += 1
            
            history.append({
                'date': current_date,
                'total_amount': daily_total_amount,
                'command_count': daily_command_count
            })
            
            current_date += timedelta(days=1)
        
        return Response({
            'pond_id': pond_id,
            'period': period,
            'days': days,
            'history': history
        })