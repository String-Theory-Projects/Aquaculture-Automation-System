from rest_framework import serializers
from .models import PondPair, Pond
from automation.models import FeedStat
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model


class PondSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for pond summary information
    """
    class Meta:
        model = Pond
        fields = ('id', 'name', 'is_active', 'created_at')


class PondPairSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for pond pair summary information
    """
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    
    class Meta:
        model = PondPair
        fields = ('id', 'name', 'device_id', 'pond_count', 'is_complete', 'created_at')


class PondPairListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing pond pairs with basic pond information
    """
    ponds = PondSummarySerializer(many=True, read_only=True)
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    owner_username = serializers.ReadOnlyField(source='owner.username')
    
    class Meta:
        model = PondPair
        fields = ('id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 'ponds', 'pond_count', 'is_complete')


class PondPairDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for pond pair including full pond information
    """
    ponds = serializers.SerializerMethodField()
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    has_minimum_ponds = serializers.ReadOnlyField()
    owner_username = serializers.ReadOnlyField(source='owner.username')
    
    class Meta:
        model = PondPair
        fields = ('id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 'ponds', 'pond_count', 'is_complete', 'has_minimum_ponds')
        read_only_fields = ('id', 'owner', 'owner_username', 'created_at', 'ponds', 'pond_count', 'is_complete', 'has_minimum_ponds')
    
    def get_ponds(self, obj):
        """Get serialized ponds with full details"""
        from users.serializers import PondSerializer
        return PondSerializer(obj.ponds.all(), many=True).data


class PondPairCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new pond pair with initial ponds
    """
    name = serializers.CharField(max_length=30, required=True, help_text="Name for this pond pair (unique per user)")
    pond_names = serializers.ListField(
        child=serializers.CharField(max_length=15),
        write_only=True,
        required=False,
        help_text="List of pond names to create with this pair (1-2 ponds)"
    )
    owner_username = serializers.ReadOnlyField(source='owner.username')
    ponds = PondSummarySerializer(many=True, read_only=True)
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    
    class Meta:
        model = PondPair
        fields = ('id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 'pond_names', 'ponds', 'pond_count', 'is_complete')
        read_only_fields = ('id', 'owner', 'owner_username', 'created_at', 'ponds', 'pond_count', 'is_complete')
    
    def validate_name(self, value):
        """Validate that the name is unique for this user"""
        user = self.context['request'].user
        if PondPair.objects.filter(owner=user, name=value).exists():
            raise serializers.ValidationError("A pond pair with this name already exists for your account.")
        return value
    
    def validate_pond_names(self, value):
        """Validate that 1-2 pond names are provided"""
        if len(value) == 0:
            raise serializers.ValidationError("At least one pond name must be provided")
        if len(value) > 2:
            raise serializers.ValidationError("A PondPair can have at most 2 ponds")
        return value
    
    def validate_device_id(self, value):
        """Validate device ID format and check for duplicates"""
        import re
        
        # Validate MAC address format (XX:XX:XX:XX:XX:XX)
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        if not mac_pattern.match(value):
            raise serializers.ValidationError("Device ID must be a valid MAC address in format XX:XX:XX:XX:XX:XX")
        
        # Check for existing pond pair with this device ID
        if PondPair.objects.filter(device_id=value).exists():
            raise serializers.ValidationError("A pond pair with this device ID already exists")
        
        return value
    
    def validate(self, data):
        """Validate the entire data set"""
        # Check if this is a reactivation attempt
        device_id = data.get('device_id')
        existing_pair = PondPair.objects.filter(device_id=device_id).first()
        
        if existing_pair and existing_pair.owner.username == settings.SYSTEM_USERNAME:
            # This is a reactivation, so we don't need to validate name uniqueness
            # since we'll be updating the existing pair
            pass
        else:
            # For new pairs, validate pond names uniqueness within the pair
            pond_names = data.get('pond_names', [])
            if len(pond_names) != len(set(pond_names)):
                raise serializers.ValidationError("Pond names within a pair must be unique")
            
            # Validate that pond names don't conflict with existing active ponds for this user
            user = self.context['request'].user
            for pond_name in pond_names:
                if Pond.objects.filter(parent_pair__owner=user, name=pond_name, is_active=True).exists():
                    raise serializers.ValidationError(f'You already have an active pond named "{pond_name}". Please use a different name.')
        
        return data
    
    def create(self, validated_data):
        """Create a new pond pair with ponds"""
        pond_names = validated_data.pop('pond_names', [])
        
        # Check if this is a reactivation attempt
        device_id = validated_data.get('device_id')
        existing_pair = PondPair.objects.filter(device_id=device_id).first()
        
        if existing_pair and existing_pair.owner.username == settings.SYSTEM_USERNAME:
            # Handle reactivation
            existing_pair.name = validated_data.get('name')
            existing_pair.owner = validated_data.get('owner')
            existing_pair.save()
            
            # Update ponds
            existing_ponds = list(existing_pair.ponds.all())
            
            # Update existing ponds or create new ones
            for i, pond_name in enumerate(pond_names):
                if i < len(existing_ponds):
                    # Update existing pond
                    existing_ponds[i].name = pond_name
                    existing_ponds[i].is_active = True
                    existing_ponds[i].save()
                else:
                    # Create new pond
                    Pond.objects.create(
                        name=pond_name,
                        parent_pair=existing_pair,
                        is_active=True
                    )
            
            # Deactivate any extra ponds beyond the new count
            for i in range(len(pond_names), len(existing_ponds)):
                existing_ponds[i].is_active = False
                existing_ponds[i].save()
            
            return existing_pair
        else:
            # Create new pond pair
            pond_pair = PondPair.objects.create(**validated_data)
            
            # Create ponds with automatic naming if needed
            for i, pond_name in enumerate(pond_names):
                if not pond_name:
                    # Auto-generate name if not provided
                    pond_name = f"Pond {i + 1}"
                
                Pond.objects.create(
                    name=pond_name,
                    parent_pair=pond_pair,
                    is_active=True
                )
            
            return pond_pair


class PondPairUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating pond pair information
    """
    class Meta:
        model = PondPair
        fields = ('name', 'device_id')
    
    def validate_name(self, value):
        """Validate that the name is unique for this user"""
        user = self.context['request'].user
        instance = self.instance
        
        # Check if another pond pair with this name exists for the same user
        if instance and PondPair.objects.filter(owner=user, name=value).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError("A pond pair with this name already exists for your account.")
        elif not instance and PondPair.objects.filter(owner=user, name=value).exists():
            raise serializers.ValidationError("A pond pair with this name already exists for your account.")
        return value
    
    def validate_device_id(self, value):
        """Validate device ID format and check for duplicates"""
        import re
        
        # Validate MAC address format (XX:XX:XX:XX:XX:XX)
        mac_pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        if not mac_pattern.match(value):
            raise serializers.ValidationError("Device ID must be a valid MAC address in format XX:XX:XX:XX:XX:XX")
        
        # Check for existing pond pair with this device ID (excluding current instance)
        instance = self.instance
        if PondPair.objects.filter(device_id=value).exclude(pk=instance.pk).exists():
            raise serializers.ValidationError("A pond pair with this device ID already exists")
        
        return value


class PondPairWithPondDetailsSerializer(serializers.ModelSerializer):
    """
    Serializer that includes pond details and additional metadata
    """
    ponds = serializers.SerializerMethodField()
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    owner_username = serializers.ReadOnlyField(source='owner.username')
    total_feed_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = PondPair
        fields = (
            'id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 
            'ponds', 'pond_count', 'is_complete', 'total_feed_amount'
        )
        read_only_fields = ('id', 'owner', 'owner_username', 'created_at', 'ponds', 'pond_count', 'is_complete', 'total_feed_amount')
    
    def get_ponds(self, obj):
        """Get serialized ponds with full details including controls and recent sensor data"""
        from users.serializers import PondSerializer
        
        ponds = obj.ponds.all()
        pond_data = []
        
        for pond in ponds:
            pond_serializer = PondSerializer(pond)
            pond_info = pond_serializer.data
            
            # Add control information
            try:
                control = pond.controls
                pond_info['control'] = {
                    'water_valve_state': control.water_valve_state,
                    'last_feed_time': control.last_feed_time,
                    'last_feed_amount': control.last_feed_amount
                }
            except Pond.controls.RelatedObjectDoesNotExist:
                pond_info['control'] = None
            
            # Add recent sensor data
            recent_sensor_data = pond.sensor_readings.first()
            if recent_sensor_data:
                pond_info['latest_sensor_data'] = {
                    'timestamp': recent_sensor_data.timestamp,
                    'temperature': recent_sensor_data.temperature,
                    'water_level': recent_sensor_data.water_level,
                    'feed_level': recent_sensor_data.feed_level,
                    'turbidity': recent_sensor_data.turbidity,
                    'dissolved_oxygen': recent_sensor_data.dissolved_oxygen,
                    'ph': recent_sensor_data.ph
                }
            else:
                pond_info['latest_sensor_data'] = None
            
            pond_data.append(pond_info)
        
        return pond_data
    
    def get_total_feed_amount(self, obj):
        """Calculate total feed amount across all ponds in the pair"""
        total = 0
        for pond in obj.ponds.all():
            # Get the most recent feed stat for this pond
            latest_stat = FeedStat.objects.filter(
                user=obj.owner,
                pond=pond
            ).order_by('-updated_at').first()
            
            if latest_stat:
                total += latest_stat.amount
        
        return total
