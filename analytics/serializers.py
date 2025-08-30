# serializers.py
from rest_framework import serializers
from ponds.models import SensorData, Pond, PondControl

class CurrentSensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = ['temperature', 'water_level', 'turbidity', 
                 'dissolved_oxygen', 'ph', 'feed_level', 'timestamp']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Convert water_level and feed_level to integer
        if representation.get('water_level') is not None:
            representation['water_level'] = int(representation['water_level'])
        if representation.get('feed_level') is not None:
            representation['feed_level'] = int(representation['feed_level'])
        
        # Round other values to 2 decimal places
        decimal_fields = ['temperature', 'turbidity', 'dissolved_oxygen', 'ph']
        for field in decimal_fields:
            if representation.get(field) is not None:
                representation[field] = round(representation[field], 2)
        
        return representation

class PondControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = PondControl
        fields = ['last_feed_time', 'last_feed_amount', 'water_valve_state']

class PondDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['id', 'name']

class HistoricalDataSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField(source='interval')  # Map 'interval' to 'timestamp'
    
    # Round to 2 decimal places
    temperature = serializers.SerializerMethodField()
    water_level = serializers.SerializerMethodField()  # Will be converted to integer
    turbidity = serializers.SerializerMethodField()
    dissolved_oxygen = serializers.SerializerMethodField()
    ph = serializers.SerializerMethodField()
    feed_level = serializers.SerializerMethodField()
    
    def get_temperature(self, obj):
        if obj.get('temperature') is None:
            return None
        return round(obj.get('temperature'), 2)
    
    def get_water_level(self, obj):
        if obj.get('water_level') is None:
            return None
        return int(obj.get('water_level'))
    
    def get_turbidity(self, obj):
        if obj.get('turbidity') is None:
            return None
        return round(obj.get('turbidity'), 2)
    
    def get_dissolved_oxygen(self, obj):
        if obj.get('dissolved_oxygen') is None:
            return None
        return round(obj.get('dissolved_oxygen'), 2)
    
    def get_ph(self, obj):
        if obj.get('ph') is None:
            return None
        return round(obj.get('ph'), 2)
    
    def get_feed_level(self, obj):
        if obj.get('feed_level') is None:
            return None
        return round(obj.get('feed_level'), 2)
