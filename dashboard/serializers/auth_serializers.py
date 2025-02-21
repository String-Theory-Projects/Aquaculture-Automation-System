from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from dashboard.models import Pond


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model - used for profile viewing/editing
    """
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


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
