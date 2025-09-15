from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    UserSerializer, RegisterSerializer, PondSerializer, 
    PondRegistrationSerializer, PondPairRegistrationSerializer
)
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from ponds.models import Pond, PondPair

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    API view for user registration
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain pair view that includes user data and handles email/username login
    """
    def post(self, request, *args, **kwargs):
        # Handle email/username authentication
        username_or_email = request.data.get('username')
        password = request.data.get('password')
        
        if username_or_email and password:
            try:
                # Determine if input is email or username
                if '@' in username_or_email:
                    # It's an email, find user by email
                    user = User.objects.get(email=username_or_email)
                    # Update request data to use actual username for JWT authentication
                    request.data['username'] = user.username
                else:
                    # It's a username, use as is
                    user = User.objects.get(username=username_or_email)
                
                # Verify password
                if not user.check_password(password):
                    return Response(
                        {'error': 'Invalid credentials'}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
            except User.DoesNotExist:
                return Response(
                    {'error': 'Invalid credentials'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Proceed with normal JWT authentication
        response = super().post(request, *args, **kwargs)
        
        if response.status_code == 200:
            try:
                # Get the user from the token
                username = request.data.get('username')
                user = User.objects.get(username=username)
                
                response.data['user'] = UserSerializer(user).data
                
                # Add pond pairs information if available
                pond_pairs = user.pond_pairs.all()
                if pond_pairs.exists():
                    response.data['has_pond_pairs'] = True
                    response.data['pond_pairs_count'] = pond_pairs.count()
                    # Count total ponds across all pairs
                    total_ponds = sum(pair.pond_count for pair in pond_pairs)
                    response.data['total_ponds_count'] = total_ponds
                else:
                    response.data['has_pond_pairs'] = False
                    response.data['pond_pairs_count'] = 0
                    response.data['total_ponds_count'] = 0
                    
            except User.DoesNotExist:
                # User not found, but token was generated successfully
                # This shouldn't happen in normal flow, but handle gracefully
                pass
                
        return response


class UserProfileView(APIView):
    """
    View for getting user profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UpdateProfileView(APIView):
    """
    View for updating user profile
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Update user profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Partial update user profile"""
        return self.put(request)


class ChangePasswordView(APIView):
    """
    View for changing user password
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Change user password"""
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response({
                'error': 'Both current_password and new_password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify current password
        if not request.user.check_password(current_password):
            return Response({
                'error': 'Current password is incorrect'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        try:
            validate_password(new_password, request.user)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        request.user.set_password(new_password)
        request.user.save()
        
        return Response({
            'message': 'Password changed successfully'
        })


class TokenRefreshView(APIView):
    """
    View for refreshing access tokens
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Refresh access token using refresh token"""
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            token = RefreshToken(refresh_token)
            access_token = str(token.access_token)
            
            return Response({
                'access': access_token
            })
        except Exception as e:
            return Response(
                {'error': 'Invalid refresh token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutView(APIView):
    """
    View for user logout
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Logout user"""
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({
                'message': 'Logged out successfully'
            })
        except Exception as e:
            return Response({
                'error': 'Invalid refresh token'
            }, status=status.HTTP_400_BAD_REQUEST)


class PondDetailView(APIView):
    """
    API view for retrieving, updating, and deleting pond information
    """
    permission_classes = [IsAuthenticated]
    
    def get_pond(self, pk, user):
        """Helper method to get pond and verify ownership"""
        pond = get_object_or_404(Pond, pk=pk)
        if pond.parent_pair.owner != user:
            raise PermissionDenied("You don't have permission to access this pond")
        return pond
    
    def get(self, request, pk):
        """Retrieve pond details"""
        pond = self.get_pond(pk, request.user)
        serializer = PondSerializer(pond)
        return Response(serializer.data)
    
    def put(self, request, pk):
        """Update pond information"""
        pond = self.get_pond(pk, request.user)
        
        # Remove is_active from request data to prevent direct modification
        if 'is_active' in request.data:
            mutable_data = request.data.copy()
            mutable_data.pop('is_active')
            request._full_data = mutable_data
        
        # Check if name is being updated and would create a duplicate
        new_name = request.data.get('name')
        if new_name and new_name != pond.name:
            if Pond.objects.filter(parent_pair__owner=request.user, name=new_name, is_active=True).exclude(pk=pk).exists():
                return Response(
                    {'error': f'You already have an active pond named "{new_name}". Please use a different name.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = PondSerializer(pond, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request, pk):
        """Delete pond (transfer to system user and deactivate)"""
        pond = self.get_pond(pk, request.user)
        
        try:
            system_user = User.objects.get(username=settings.SYSTEM_USERNAME)
            
            # Transfer ownership to system user
            pond.parent_pair.owner = system_user
            pond.parent_pair.save()
            
            # Deactivate the pond
            pond.is_active = False
            pond.save()
            
            return Response({
                'message': 'Pond deleted successfully',
                'pond_id': pond.id
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'System user not found'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PondListView(APIView):
    """
    API view for listing all ponds for the authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get all ponds owned by the user"""
        ponds = Pond.objects.filter(
            parent_pair__owner=request.user
        ).select_related('parent_pair')
        
        serializer = PondSerializer(ponds, many=True)
        return Response(serializer.data)
