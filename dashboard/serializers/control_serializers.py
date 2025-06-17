from rest_framework import serializers

from dashboard.models import DeviceLog, MQTTMessage, PondControl


class PondControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = PondControl
        fields = ["water_valve_state", "last_feed_time", "last_feed_amount"]
        read_only_fields = ["last_feed_time", "last_feed_amount"]


class FeedDispenseSerializer(serializers.Serializer):
    feed_amount = serializers.FloatField(
        min_value=0.0, max_value=1000.0, help_text="Amount of feed to dispense in grams"
    )


class WaterValveSerializer(serializers.Serializer):
    valve_state = serializers.BooleanField(
        help_text="True to open valve, False to close"
    )


class DeviceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceLog
        fields = ["timestamp", "log_type", "message", "command_id", "retry_count"]
        read_only_fields = ["timestamp"]


class MQTTMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MQTTMessage
        fields = [
            "command_id",
            "topic",
            "payload",
            "message_type",
            "status",
            "timestamp",
            "retries",
        ]
        read_only_fields = ["command_id", "timestamp"]
