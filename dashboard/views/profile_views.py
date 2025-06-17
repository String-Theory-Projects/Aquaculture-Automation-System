from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from dashboard.models import Pond, PondControl, WiFiConfig
from dashboard.serializers.auth_serializers import UserSerializer
from dashboard.serializers.profile_serializers import (
    PondRegistrationSerializer, PondSerializer, WiFiConfigSerializer)

User = get_user_model()


class UpdateProfileView(APIView):
    """
    API view for updating user profile information
    """

    permission_classes = [IsAuthenticated]

    def put(self, request):
        """Update user profile information including username, email, first_name, last_name"""
        user = request.user

        # Store original values for comparison
        original_username = user.username
        original_email = user.email

        # Check for username change
        new_username = request.data.get("username")
        if new_username and new_username != original_username:
            # Validate username uniqueness
            if User.objects.filter(username=new_username).exists():
                return Response(
                    {"username": ["A user with this username already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Check for email change
        new_email = request.data.get("email")
        if new_email and new_email != original_email:
            # Validate email uniqueness
            if User.objects.filter(email=new_email).exists():
                return Response(
                    {"email": ["A user with this email already exists."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = UserSerializer(user, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            # If username or email was changed, generate new tokens
            username_changed = new_username and new_username != original_username
            email_changed = new_email and new_email != original_email

            if username_changed or email_changed:
                # Generate new tokens
                from rest_framework_simplejwt.tokens import RefreshToken

                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        "message": "Profile updated successfully. Please use your new credentials for future logins.",
                        "user": serializer.data,
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"message": "Profile updated successfully", "user": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterPondView(APIView):
    """
    API view for registering a pond to a user account
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = PondRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Check if device_id already exists
            device_id = serializer.validated_data.get("device_id")
            pond_name = serializer.validated_data.get("name")

            # Check if the user already has a pond with this name
            if Pond.objects.filter(
                owner=request.user, name=pond_name, is_active=True
            ).exists():
                return Response(
                    {
                        "error": f'You already have an active pond named "{pond_name}". Please use a different name.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                # Check if pond exists but is deactivated (owned by system user)
                system_user = User.objects.get(username=settings.SYSTEM_USERNAME)
                existing_pond = Pond.objects.get(
                    device_id=device_id, owner=system_user, is_active=False
                )

                # Check if reactivating would create a duplicate name
                if Pond.objects.filter(
                    owner=request.user, name=pond_name, is_active=True
                ).exists():
                    return Response(
                        {
                            "error": f'You already have an active pond named "{pond_name}". Please use a different name.'
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # If found, transfer ownership back to the user
                existing_pond.owner = request.user
                existing_pond.name = pond_name
                existing_pond.is_active = True
                existing_pond.save()

                # Update WiFi config if provided
                ssid = serializer.validated_data.get("ssid", None)
                password = serializer.validated_data.get("password", None)

                if ssid and password:
                    try:
                        # Update existing WiFi config if it exists
                        wifi_config = existing_pond.wifi_config
                        wifi_config.ssid = ssid
                        wifi_config.password = password
                        wifi_config.is_config_synced = False
                        wifi_config.save()
                    except WiFiConfig.DoesNotExist:
                        # Create new WiFi config if it doesn't exist
                        WiFiConfig.objects.create(
                            pond=existing_pond, ssid=ssid, password=password
                        )

                return Response(
                    {
                        "message": "Pond re-registered successfully",
                        "pond_id": existing_pond.id,
                        "name": existing_pond.name,
                    },
                    status=status.HTTP_200_OK,
                )

            except (Pond.DoesNotExist, User.DoesNotExist):
                # Check if device is registered to another active user
                if Pond.objects.filter(device_id=device_id, is_active=True).exists():
                    return Response(
                        {"error": "Device ID already registered to an active user"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create new pond
                pond = Pond.objects.create(
                    name=pond_name,
                    owner=request.user,
                    device_id=device_id,
                    is_active=True,
                )

                PondControl.objects.create(pond=pond)

                # Create default WiFi config if SSID and password are provided
                ssid = serializer.validated_data.get("ssid", None)
                password = serializer.validated_data.get("password", None)

                if ssid and password:
                    WiFiConfig.objects.create(pond=pond, ssid=ssid, password=password)

                return Response(
                    {
                        "message": "Pond registered successfully",
                        "pond_id": pond.id,
                        "name": pond.name,
                    },
                    status=status.HTTP_201_CREATED,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PondDetailView(APIView):
    """
    API view for retrieving, updating, and deleting pond information
    """

    permission_classes = [IsAuthenticated]

    def get_pond(self, pk, user):
        """Helper method to get pond and verify ownership"""
        pond = get_object_or_404(Pond, pk=pk)
        if pond.owner != user:
            raise PermissionDenied("You don't have permission to access this pond")
        return pond

    def get(self, request, pk):
        """Retrieve pond details"""
        pond = self.get_pond(pk, request.user)
        serializer = PondSerializer(pond)

        # Include WiFi config if it exists
        try:
            wifi_config = pond.wifi_config
            wifi_serializer = WiFiConfigSerializer(wifi_config)
            data = serializer.data
            data["wifi_config"] = wifi_serializer.data
            return Response(data)
        except WiFiConfig.DoesNotExist:
            return Response(serializer.data)

    def put(self, request, pk):
        """Update pond information"""
        pond = self.get_pond(pk, request.user)

        # Remove is_active from request data to prevent direct modification
        if "is_active" in request.data:
            mutable_data = request.data.copy()
            mutable_data.pop("is_active")
            request._full_data = mutable_data

        # Check if name is being updated and would create a duplicate
        new_name = request.data.get("name")
        if new_name and new_name != pond.name:
            # Check if user already has a pond with this name
            if (
                Pond.objects.filter(owner=request.user, name=new_name, is_active=True)
                .exclude(pk=pond.pk)
                .exists()
            ):
                return Response(
                    {
                        "error": f'You already have an active pond named "{new_name}". Please use a different name.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = PondSerializer(pond, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            # Update WiFi config if provided
            wifi_data = request.data.get("wifi_config")
            if wifi_data:
                try:
                    wifi_config = pond.wifi_config
                    wifi_serializer = WiFiConfigSerializer(
                        wifi_config, data=wifi_data, partial=True
                    )
                except WiFiConfig.DoesNotExist:
                    # Create new WiFi config if it doesn't exist
                    wifi_serializer = WiFiConfigSerializer(data=wifi_data)

                if wifi_serializer.is_valid():
                    wifi_config = wifi_serializer.save(pond=pond)

                    # Mark as not synced if SSID or password changed
                    if "ssid" in wifi_data or "password" in wifi_data:
                        wifi_config.is_config_synced = False
                        wifi_config.save()
                else:
                    return Response(
                        wifi_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

            return Response(
                {"message": "Pond updated successfully", "pond": serializer.data}
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, pk):
        """Transfer pond ownership to system user (soft delete)"""
        pond = self.get_pond(pk, request.user)

        try:
            # Get or create system user
            system_user, created = User.objects.get_or_create(
                username=settings.SYSTEM_USERNAME,
                defaults={
                    "email": settings.SYSTEM_EMAIL,
                    "is_active": True,
                    "is_staff": False,
                },
            )

            # Transfer ownership and mark as inactive
            pond.owner = system_user
            pond.is_active = False
            pond.save()

            return Response(
                {"message": "Pond deactivated successfully"}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"Failed to deactivate pond: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PondListView(APIView):
    """
    API view for listing all ponds for the authenticated user
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all ponds for the current user"""
        ponds = Pond.objects.filter(owner=request.user)
        serializer = PondSerializer(ponds, many=True)
        return Response(serializer.data)
