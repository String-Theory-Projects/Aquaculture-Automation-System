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
    Serializer for listing pond pairs with detailed pond information
    """
    ponds = serializers.SerializerMethodField()
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    owner_username = serializers.ReadOnlyField(source='owner.username')
    battery_level = serializers.SerializerMethodField()
    device_status = serializers.SerializerMethodField()
    
    class Meta:
        model = PondPair
        fields = ('id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 'ponds', 'pond_count', 'is_complete', 'battery_level', 'device_status')
    
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
            
            # Add recent sensor data with last non-zero values
            latest_sensor_data = self._get_latest_non_zero_sensor_data(pond)
            if latest_sensor_data:
                pond_info['latest_sensor_data'] = latest_sensor_data
            else:
                pond_info['latest_sensor_data'] = None
            
            pond_data.append(pond_info)
        
        return pond_data
    
    def _get_latest_non_zero_sensor_data(self, pond):
        """
        Get the latest non-zero sensor data for a pond.
        Returns a dictionary with the last non-zero value for each sensor type.
        """
        from django.db.models import Q
        
        # Get all sensor readings for this pond, ordered by timestamp
        sensor_readings = pond.sensor_readings.all().order_by('-timestamp')
        
        if not sensor_readings.exists():
            return None
        
        # Initialize result with None values
        latest_data = {
            'timestamp': None,
            'temperature': None,
            'water_level': None,
            'feed_level': None,
            'turbidity': None,
            'dissolved_oxygen': None,
            'ph': None,
            'ammonia': None,
            'battery': None,
            'device_timestamp': None,
            'signal_strength': None
        }
        
        # Find the latest non-zero value for each sensor
        for reading in sensor_readings:
            # Update timestamp to the most recent reading
            if latest_data['timestamp'] is None:
                latest_data['timestamp'] = reading.timestamp
            
            # Update device timestamp to the most recent reading
            if latest_data['device_timestamp'] is None and reading.device_timestamp:
                latest_data['device_timestamp'] = reading.device_timestamp
            
            # Update signal strength to the most recent reading
            if latest_data['signal_strength'] is None and reading.signal_strength is not None:
                latest_data['signal_strength'] = reading.signal_strength
            
            # For each sensor value, find the last non-zero value
            if latest_data['temperature'] is None and reading.temperature and reading.temperature > 0:
                latest_data['temperature'] = reading.temperature
            
            if latest_data['water_level'] is None and reading.water_level and reading.water_level > 0:
                latest_data['water_level'] = reading.water_level
            
            if latest_data['feed_level'] is None and reading.feed_level and reading.feed_level > 0:
                latest_data['feed_level'] = reading.feed_level
            
            if latest_data['turbidity'] is None and reading.turbidity and reading.turbidity > 0:
                latest_data['turbidity'] = reading.turbidity
            
            if latest_data['dissolved_oxygen'] is None and reading.dissolved_oxygen and reading.dissolved_oxygen > 0:
                latest_data['dissolved_oxygen'] = reading.dissolved_oxygen
            
            if latest_data['ph'] is None and reading.ph and reading.ph > 0:
                latest_data['ph'] = reading.ph
            
            if latest_data['ammonia'] is None and reading.ammonia and reading.ammonia > 0:
                latest_data['ammonia'] = reading.ammonia
            
            if latest_data['battery'] is None and reading.battery and reading.battery > 0:
                latest_data['battery'] = reading.battery
            
            # If we have all sensor values, we can break early
            if all(v is not None for v in [
                latest_data['temperature'], latest_data['water_level'], 
                latest_data['feed_level'], latest_data['turbidity'],
                latest_data['dissolved_oxygen'], latest_data['ph'],
                latest_data['ammonia'], latest_data['battery']
            ]):
                break
        
        # Only return data if we have at least some sensor readings
        has_sensor_data = any(v is not None for v in [
            latest_data['temperature'], latest_data['water_level'], 
            latest_data['feed_level'], latest_data['turbidity'],
            latest_data['dissolved_oxygen'], latest_data['ph'],
            latest_data['ammonia'], latest_data['battery']
        ])
        
        if has_sensor_data:
            # Remove None values for cleaner output
            return {k: v for k, v in latest_data.items() if v is not None}
        
        return None
    
    def get_battery_level(self, obj):
        """
        Get the last non-zero battery level from any pond in this pair
        """
        from django.db.models import Max
        
        # Get the latest non-zero battery reading from any pond in this pair
        latest_battery = obj.ponds.aggregate(
            latest_battery=Max('sensor_readings__battery')
        )['latest_battery']
        
        # If no battery reading found, return None
        if latest_battery is None or latest_battery <= 0:
            return None
        
        return latest_battery
    
    def get_device_status(self, obj):
        """
        Get the device status for this pond pair
        """
        try:
            device_status = obj.device_status
            return {
                'status': device_status.status,
                'last_seen': device_status.last_seen,
                'is_online': device_status.is_online(),
                'firmware_version': device_status.firmware_version,
                'hardware_version': device_status.hardware_version,
                'device_name': device_status.device_name,
                'ip_address': device_status.ip_address,
                'wifi_ssid': device_status.wifi_ssid,
                'wifi_signal_strength': device_status.wifi_signal_strength,
                'free_heap': device_status.free_heap,
                'cpu_frequency': device_status.cpu_frequency,
                'error_count': device_status.error_count,
                'last_error': device_status.last_error,
                'last_error_at': device_status.last_error_at,
                'uptime_percentage_24h': device_status.get_uptime_percentage(24)
            }
        except obj.device_status.RelatedObjectDoesNotExist:
            return None


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
    pond_details = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        help_text="List of pond details including name, sensor_height, and tank_depth (1-2 ponds)"
    )
    owner_username = serializers.ReadOnlyField(source='owner.username')
    ponds = PondSummarySerializer(many=True, read_only=True)
    pond_count = serializers.ReadOnlyField(source='ponds.count')
    is_complete = serializers.ReadOnlyField()
    
    class Meta:
        model = PondPair
        fields = ('id', 'name', 'device_id', 'owner', 'owner_username', 'created_at', 'pond_names', 'pond_details', 'ponds', 'pond_count', 'is_complete')
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
    
    def validate_pond_details(self, value):
        """Validate pond details structure"""
        if len(value) == 0:
            raise serializers.ValidationError("At least one pond detail must be provided")
        if len(value) > 2:
            raise serializers.ValidationError("A PondPair can have at most 2 ponds")
        
        for i, pond_detail in enumerate(value):
            if 'name' not in pond_detail:
                raise serializers.ValidationError(f"Pond {i+1} must have a 'name' field")
            
            # Validate sensor_height if provided
            if 'sensor_height' in pond_detail:
                try:
                    sensor_height = float(pond_detail['sensor_height'])
                    if sensor_height < 0:
                        raise serializers.ValidationError(f"Pond {i+1} sensor_height must be >= 0")
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"Pond {i+1} sensor_height must be a valid number")
            
            # Validate tank_depth if provided
            if 'tank_depth' in pond_detail:
                try:
                    tank_depth = float(pond_detail['tank_depth'])
                    if tank_depth < 0:
                        raise serializers.ValidationError(f"Pond {i+1} tank_depth must be >= 0")
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"Pond {i+1} tank_depth must be a valid number")
        
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
            pond_details = data.get('pond_details', [])
            
            # Ensure either pond_names or pond_details is provided, but not both
            if pond_names and pond_details:
                raise serializers.ValidationError("Provide either 'pond_names' or 'pond_details', not both")
            if not pond_names and not pond_details:
                raise serializers.ValidationError("Either 'pond_names' or 'pond_details' must be provided")
            
            # Extract names from pond_details if provided
            if pond_details:
                pond_names = [detail.get('name') for detail in pond_details if detail.get('name')]
            
            if len(pond_names) != len(set(pond_names)):
                raise serializers.ValidationError("Pond names within a pair must be unique")
            
            # Validate that pond names don't conflict with existing active ponds for this user
            user = self.context['request'].user
            for pond_name in pond_names:
                if Pond.objects.filter(parent_pair__owner=user, name=pond_name, is_active=True).exists():
                    raise serializers.ValidationError(f'You already have an active pond named "{pond_name}". Please use a different name.')
        
        return data
    
    def _process_pond_data(self, pond_names, pond_details):
        """Process pond data from either pond_names or pond_details format"""
        if pond_details:
            # Use pond_details format
            return pond_details
        else:
            # Convert pond_names to pond_details format
            return [{'name': name} for name in pond_names]
    
    def create(self, validated_data):
        """Create a new pond pair with ponds"""
        pond_names = validated_data.pop('pond_names', [])
        pond_details = validated_data.pop('pond_details', [])
        
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
            pond_data_list = self._process_pond_data(pond_names, pond_details)
            
            # Update existing ponds or create new ones
            for i, pond_data in enumerate(pond_data_list):
                if i < len(existing_ponds):
                    # Update existing pond
                    existing_ponds[i].name = pond_data['name']
                    existing_ponds[i].is_active = True
                    if 'sensor_height' in pond_data:
                        existing_ponds[i].sensor_height = pond_data['sensor_height']
                    if 'tank_depth' in pond_data:
                        existing_ponds[i].tank_depth = pond_data['tank_depth']
                    existing_ponds[i].save()
                else:
                    # Create new pond
                    pond_create_data = {
                        'name': pond_data['name'],
                        'parent_pair': existing_pair,
                        'is_active': True
                    }
                    if 'sensor_height' in pond_data:
                        pond_create_data['sensor_height'] = pond_data['sensor_height']
                    if 'tank_depth' in pond_data:
                        pond_create_data['tank_depth'] = pond_data['tank_depth']
                    Pond.objects.create(**pond_create_data)
            
            # Deactivate any extra ponds beyond the new count
            for i in range(len(pond_data_list), len(existing_ponds)):
                existing_ponds[i].is_active = False
                existing_ponds[i].save()
            
            return existing_pair
        else:
            # Create new pond pair
            pond_pair = PondPair.objects.create(**validated_data)
            
            # Create ponds with automatic naming if needed
            pond_data_list = self._process_pond_data(pond_names, pond_details)
            for i, pond_data in enumerate(pond_data_list):
                if not pond_data.get('name'):
                    # Auto-generate name if not provided
                    pond_data['name'] = f"Pond {i + 1}"
                
                pond_create_data = {
                    'name': pond_data['name'],
                    'parent_pair': pond_pair,
                    'is_active': True
                }
                if 'sensor_height' in pond_data:
                    pond_create_data['sensor_height'] = pond_data['sensor_height']
                if 'tank_depth' in pond_data:
                    pond_create_data['tank_depth'] = pond_data['tank_depth']
                
                Pond.objects.create(**pond_create_data)
            
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
            
            # Add recent sensor data with last non-zero values
            latest_sensor_data = self._get_latest_non_zero_sensor_data(pond)
            if latest_sensor_data:
                pond_info['latest_sensor_data'] = latest_sensor_data
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
    
    def _get_latest_non_zero_sensor_data(self, pond):
        """
        Get the latest non-zero sensor data for a pond.
        Returns a dictionary with the last non-zero value for each sensor type.
        """
        from django.db.models import Q
        
        # Get all sensor readings for this pond, ordered by timestamp
        sensor_readings = pond.sensor_readings.all().order_by('-timestamp')
        
        if not sensor_readings.exists():
            return None
        
        # Initialize result with None values
        latest_data = {
            'timestamp': None,
            'temperature': None,
            'water_level': None,
            'feed_level': None,
            'turbidity': None,
            'dissolved_oxygen': None,
            'ph': None,
            'ammonia': None,
            'battery': None,
            'device_timestamp': None,
            'signal_strength': None
        }
        
        # Find the latest non-zero value for each sensor
        for reading in sensor_readings:
            # Update timestamp to the most recent reading
            if latest_data['timestamp'] is None:
                latest_data['timestamp'] = reading.timestamp
            
            # Update device timestamp to the most recent reading
            if latest_data['device_timestamp'] is None and reading.device_timestamp:
                latest_data['device_timestamp'] = reading.device_timestamp
            
            # Update signal strength to the most recent reading
            if latest_data['signal_strength'] is None and reading.signal_strength is not None:
                latest_data['signal_strength'] = reading.signal_strength
            
            # For each sensor value, find the last non-zero value
            if latest_data['temperature'] is None and reading.temperature and reading.temperature > 0:
                latest_data['temperature'] = reading.temperature
            
            if latest_data['water_level'] is None and reading.water_level and reading.water_level > 0:
                latest_data['water_level'] = reading.water_level
            
            if latest_data['feed_level'] is None and reading.feed_level and reading.feed_level > 0:
                latest_data['feed_level'] = reading.feed_level
            
            if latest_data['turbidity'] is None and reading.turbidity and reading.turbidity > 0:
                latest_data['turbidity'] = reading.turbidity
            
            if latest_data['dissolved_oxygen'] is None and reading.dissolved_oxygen and reading.dissolved_oxygen > 0:
                latest_data['dissolved_oxygen'] = reading.dissolved_oxygen
            
            if latest_data['ph'] is None and reading.ph and reading.ph > 0:
                latest_data['ph'] = reading.ph
            
            if latest_data['ammonia'] is None and reading.ammonia and reading.ammonia > 0:
                latest_data['ammonia'] = reading.ammonia
            
            if latest_data['battery'] is None and reading.battery and reading.battery > 0:
                latest_data['battery'] = reading.battery
            
            # If we have all sensor values, we can break early
            if all(v is not None for v in [
                latest_data['temperature'], latest_data['water_level'], 
                latest_data['feed_level'], latest_data['turbidity'],
                latest_data['dissolved_oxygen'], latest_data['ph'],
                latest_data['ammonia'], latest_data['battery']
            ]):
                break
        
        # Only return data if we have at least some sensor readings
        has_sensor_data = any(v is not None for v in [
            latest_data['temperature'], latest_data['water_level'], 
            latest_data['feed_level'], latest_data['turbidity'],
            latest_data['dissolved_oxygen'], latest_data['ph'],
            latest_data['ammonia'], latest_data['battery']
        ])
        
        if has_sensor_data:
            # Remove None values for cleaner output
            return {k: v for k, v in latest_data.items() if v is not None}
        
        return None
