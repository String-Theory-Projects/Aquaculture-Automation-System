# serializers.py
from rest_framework import serializers
from dashboard.models import SensorData, Pond, PondControl

class CurrentSensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = ['temperature', 'water_level', 'turbidity', 
                 'dissolved_oxygen', 'ph', 'feed_level', 'timestamp']

class PondDropdownSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pond
        fields = ['id', 'name']

class HistoricalDataSerializer(serializers.Serializer):
    timestamp = serializers.DateTimeField(source='interval')  # Map 'interval' to 'timestamp'
    temperature = serializers.FloatField()
    water_level = serializers.FloatField()
    turbidity = serializers.FloatField()
    dissolved_oxygen = serializers.FloatField()
    ph = serializers.FloatField()
    feed_level = serializers.FloatField()
