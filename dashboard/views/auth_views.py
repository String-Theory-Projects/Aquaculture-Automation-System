from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from dashboard.models import Pond
from dashboard.serializers.auth_serializers import UserSerializer, RegisterSerializer, PondRegistrationSerializer


class RegisterView(APIView):
    """
    API view for user registration
    """
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'User registered successfully'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token view that allows login with email or username and returns user data
    """
    def post(self, request, *args, **kwargs):
        # If username contains @, it's an email, find the corresponding username
        username = request.data.get('username')
        if username and '@' in username:
            try:
                user = User.objects.get(email=username)
                # Create a mutable copy of the request data
                mutable_data = request.data.copy()
                # Replace the email with the actual username for authentication
                mutable_data['username'] = user.username
                request._full_data = mutable_data
            except User.DoesNotExist:
                # If no user found with this email, continue with original data
                # (will result in authentication failure)
                pass
                
        # Proceed with standard token generation
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            # Get the authenticated user
            username = request.data.get('username')
            user = User.objects.get(username=username)
            
            response.data['user'] = UserSerializer(user).data
            
            # Add ponds information if available
            ponds = user.ponds.all()
            if ponds.exists():
                response.data['has_ponds'] = True
                response.data['ponds_count'] = ponds.count()
            else:
                response.data['has_ponds'] = False
                response.data['ponds_count'] = 0
                
        return response


class LogoutView(APIView):
    """
    API view for logging out (blacklisting the refresh token)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
            device_id = serializer.validated_data.get('device_id')
            if Pond.objects.filter(device_id=device_id).exists():
                return Response(
                    {'error': 'Device ID already registered'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create new pond
            pond = Pond.objects.create(
                name=serializer.validated_data.get('name'),
                owner=request.user,
                device_id=device_id,
                is_active=True
            )
            
            # Create default controls for the pond
            from dashboard.models import PondControl, WiFiConfig
            PondControl.objects.create(pond=pond)
            
            # Create default WiFi config if SSID and password are provided
            ssid = serializer.validated_data.get('ssid', None)
            password = serializer.validated_data.get('password', None)
            
            if ssid and password:
                WiFiConfig.objects.create(
                    pond=pond,
                    ssid=ssid,
                    password=password
                )
            
            return Response({
                'message': 'Pond registered successfully',
                'pond_id': pond.id,
                'name': pond.name
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    """
    API view for retrieving and updating user profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        data = serializer.data
        
        # Include ponds information if available
        ponds = request.user.ponds.all()
        if ponds.exists():
            data['has_ponds'] = True
            data['ponds'] = []
            for pond in ponds:
                data['ponds'].append({
                    'id': pond.id,
                    'name': pond.name,
                    'device_id': pond.device_id,
                    'is_active': pond.is_active
                })
        else:
            data['has_ponds'] = False
            
        return Response(data)
    
    def put(self, request):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Handle password change separately if provided
            password = request.data.get('password')
            if password:
                try:
                    validate_password(password, user)
                    user.set_password(password)
                    # We need to save separately since serializer.save() won't hash the password
                    user.save()
                    # Remove password from data to prevent double processing
                    serializer.validated_data.pop('password', None)
                except ValidationError as e:
                    return Response({'password': e.messages}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    API view for changing password
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old_password and new_password are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Verify old password
        if not user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate and set new password
        try:
            validate_password(new_password, user)
            user.set_password(new_password)
            user.save()
            
            # Generate new token since password change invalidates sessions
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Password changed successfully',
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            })
        except ValidationError as e:
            return Response({'error': e.messages}, status=status.HTTP_400_BAD_REQUEST)
