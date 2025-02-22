from django.contrib.auth import get_user_model
from rest_framework import serializers
from dashboard.models import WiFiConfig, PondControl, AutomationSchedule, Pond


User = get_user_model()


class PondRegistrationSerializer(serializers.Serializer):
    """
    Serializer for pond registration (linking device to user)
    """
    name = serializers.CharField(max_length=100, required=True)
    device_id = serializers.CharField(max_length=100, required=True)
    
    # Optional WiFi config during registration
    ssid = serializers.CharField(max_length=32, required=False)
    password = serializers.CharField(max_length=64, required=False)

    def validate_device_id(self, value):
        # Here you could add additional validation for device ID format
        # For example, check if it matches a specific pattern
        if len(value) < 8:
            raise serializers.ValidationError("Device ID must be at least 8 characters")
        return value


class PondSerializer(serializers.ModelSerializer):
    """
    Serializer for the Pond model
    """
    owner_username = serializers.ReadOnlyField(source='owner.username')
    
    class Meta:
        model = Pond
        fields = ('id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 'is_active')
        read_only_fields = ('id', 'owner', 'owner_username', 'device_id', 'created_at')


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


class PondControlSerializer(serializers.ModelSerializer):
    """
    Serializer for pond controls
    """
    class Meta:
        model = PondControl
        fields = ('id', 'water_valve_state', 'last_feed_time', 'last_feed_amount')
        read_only_fields = ('id', 'last_feed_time', 'last_feed_amount')


class AutomationScheduleSerializer(serializers.ModelSerializer):
    """
    Serializer for automation schedules
    """
    class Meta:
        model = AutomationSchedule
        fields = ('id', 'automation_type', 'is_active', 'time', 'days',
                 'feed_amount', 'drain_water_level', 'target_water_level',
                 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        """
        Validate automation schedule fields based on automation type
        """
        automation_type = attrs.get('automation_type')
        
        if automation_type == 'FEED':
            # Feeding requires feed_amount
            if 'feed_amount' not in attrs or attrs['feed_amount'] is None:
                raise serializers.ValidationError(
                    {'feed_amount': 'Feed amount is required for feeding schedules'}
                )
            
            # Reset water change fields
            attrs['drain_water_level'] = None
            attrs['target_water_level'] = None
            
        elif automation_type == 'WATER':
            # Water change requires target water level
            if 'target_water_level' not in attrs or attrs['target_water_level'] is None:
                raise serializers.ValidationError(
                    {'target_water_level': 'Target water level is required for water change schedules'}
                )
            
            # Reset feeding fields
            attrs['feed_amount'] = None
        
        # Validate days format (comma-separated list of numbers 0-6)
        days = attrs.get('days')
        if days:
            try:
                day_list = [int(day.strip()) for day in days.split(',')]
                for day in day_list:
                    if day < 0 or day > 6:
                        raise ValueError
            except ValueError:
                raise serializers.ValidationError(
                    {'days': 'Days must be comma-separated numbers between 0-6 (Sunday-Saturday)'}
                )
        
        return attrs
