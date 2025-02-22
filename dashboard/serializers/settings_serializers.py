from rest_framework import serializers
from dashboard.models import WiFiConfig, AutomationSchedule


class WiFiConfigSerializer(serializers.ModelSerializer):
    """
    Serializer for WiFi configuration
    """
    class Meta:
        model = WiFiConfig
        fields = ('id', 'ssid', 'password', 'is_connected', 'last_connected', 
                 'last_updated', 'is_config_synced')
        read_only_fields = ('id', 'is_connected', 'last_connected', 'last_updated', 'is_config_synced')
        extra_kwargs = {
            'password': {'write_only': True}  # Don't expose password in responses
        }

class AutomationScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for automation schedules
    """
    class Meta:
        model = AutomationSchedule
        fields = (
            'id', 'automation_type', 'is_active', 'time', 'days',
            'feed_amount', 'drain_water_level', 'target_water_level',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate automation schedule fields based on type"""
        automation_type = data.get('automation_type')
        
        if automation_type == 'FEED':
            if not data.get('feed_amount'):
                raise serializers.ValidationError(
                    {'feed_amount': 'Feed amount is required for feeding schedules'}
                )
            # Clear water change fields
            data['drain_water_level'] = None
            data['target_water_level'] = None
            
        elif automation_type == 'WATER':
            if not data.get('target_water_level'):
                raise serializers.ValidationError(
                    {'target_water_level': 'Target water level is required for water change schedules'}
                )
            # Clear feeding fields
            data['feed_amount'] = None

        # Validate days format
        days = data.get('days', '')
        try:
            day_list = [int(d.strip()) for d in days.split(',')]
            if not all(0 <= d <= 6 for d in day_list):
                raise ValueError
        except ValueError:
            raise serializers.ValidationError(
                {'days': 'Days must be comma-separated numbers between 0-6'}
            )

        return data
