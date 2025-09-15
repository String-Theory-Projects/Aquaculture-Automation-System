from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from ponds.models import Pond, PondControl
from automation.models import AutomationSchedule


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model - used for profile viewing/editing
    """
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)
        
    def validate_email(self, value):
        """
        Validate email is unique except for the current user
        """
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
        
    def validate_username(self, value):
        """
        Validate username is unique except for the current user
        """
        user = self.instance
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        
        user.set_password(validated_data['password'])
        user.save()
        
        return user


class PondRegistrationSerializer(serializers.Serializer):
    """
    Serializer for pond registration (linking device to user)
    """
    name = serializers.CharField(max_length=100, required=True)
    device_id = serializers.CharField(max_length=100, required=True)

    def validate_device_id(self, value):
        """Validate device ID format"""
        import re
        
        # Validate MAC address format (XX:XX:XX:XX:XX:XX)
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        if not mac_pattern.match(value):
            raise serializers.ValidationError("Device ID must be a valid MAC address in format XX:XX:XX:XX:XX:XX")
        
        return value


class PondPairRegistrationSerializer(serializers.Serializer):
    """
    Serializer for pond pair registration (linking device to user)
    """
    device_id = serializers.CharField(max_length=100, required=True)
    pond_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        min_length=1,
        max_length=2,
        help_text="List of 1-2 pond names to create with this pair"
    )

    def validate_device_id(self, value):
        """Validate device ID format"""
        import re
        
        # Validate MAC address format (XX:XX:XX:XX:XX:XX)
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        if not mac_pattern.match(value):
            raise serializers.ValidationError("Device ID must be a valid MAC address in format XX:XX:XX:XX:XX:XX")
        
        return value
    
    def validate_pond_names(self, value):
        """Validate pond names"""
        if len(value) == 0:
            raise serializers.ValidationError("At least one pond name must be provided")
        if len(value) > 2:
            raise serializers.ValidationError("A PondPair can have at most 2 ponds")
        return value


class PondSerializer(serializers.ModelSerializer):
    """
    Serializer for the Pond model
    """
    owner_username = serializers.ReadOnlyField(source='owner.username')
    parent_pair_device_id = serializers.ReadOnlyField(source='parent_pair.device_id')
    name = serializers.CharField(max_length=15)
    sensor_height = serializers.FloatField(required=True, min_value=0)
    tank_depth = serializers.FloatField(required=True, min_value=0)

    class Meta:
        model = Pond
        fields = ('id', 'name', 'parent_pair', 'parent_pair_device_id', 'owner_username', 'sensor_height', 'tank_depth', 'created_at', 'is_active')
        read_only_fields = ('id', 'owner_username', 'parent_pair_device_id', 'created_at')


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
        fields = ('id', 'pond', 'automation_type', 'action', 'is_active', 'time', 'days',
                 'feed_amount', 'drain_water_level', 'target_water_level',
                 'priority', 'last_execution', 'next_execution', 'execution_count',
                 'created_at', 'updated_at')
        read_only_fields = ('id', 'pond', 'last_execution', 'next_execution', 'execution_count', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        """
        Validate automation schedule fields based on automation type
        """
        automation_type = attrs.get('automation_type')
        action = attrs.get('action')
        
        if automation_type == 'FEED':
            # Feeding requires FEED action
            if action != 'FEED':
                raise serializers.ValidationError(
                    {'action': 'FEED automation type can only use FEED action'}
                )
            
            # Feeding requires feed_amount
            if 'feed_amount' not in attrs or attrs['feed_amount'] is None:
                raise serializers.ValidationError(
                    {'feed_amount': 'Feed amount is required for feeding schedules'}
                )
            
            # Reset water change fields
            attrs['drain_water_level'] = None
            attrs['target_water_level'] = None
            
        elif automation_type == 'WATER':
            # Water automation requires water-related actions
            valid_water_actions = ['WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH', 'WATER_INLET_OPEN', 'WATER_INLET_CLOSE', 'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE']
            if action not in valid_water_actions:
                raise serializers.ValidationError(
                    {'action': f'Invalid action for WATER automation. Must be one of: {", ".join(valid_water_actions)}'}
                )
            
            # Water change requires target water level
            if 'target_water_level' not in attrs or attrs['target_water_level'] is None:
                raise serializers.ValidationError(
                    {'target_water_level': 'Target water level is required for water change schedules'}
                )
            
            # Reset feeding fields
            attrs['feed_amount'] = None
            
        return attrs
