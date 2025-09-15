from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import Http404
from django.contrib.auth import get_user_model
import logging
from django.conf import settings

from .models import PondPair, Pond
from .serializers import (
    PondPairListSerializer,
    PondPairDetailSerializer,
    PondPairCreateSerializer,
    PondPairUpdateSerializer,
    PondPairWithPondDetailsSerializer,
    PondPairSummarySerializer
)

logger = logging.getLogger(__name__)


class PondPairListView(generics.ListCreateAPIView):
    """
    API view for listing and creating pond pairs
    
    GET: List all pond pairs for the authenticated user
    POST: Create a new pond pair with initial ponds
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PondPairCreateSerializer
        return PondPairListSerializer
    
    def get_queryset(self):
        """Get pond pairs owned by the authenticated user with related data for detailed pond information"""
        return PondPair.objects.filter(owner=self.request.user).select_related(
            'device_status'
        ).prefetch_related(
            'ponds',
            'ponds__controls',
            'ponds__sensor_readings'
        )
    
    def perform_create(self, serializer):
        """Create pond pair with the authenticated user as owner"""
        serializer.save(owner=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create a new pond pair with validation"""
        try:
            device_id = request.data.get('device_id')
            name = request.data.get('name')
            pond_details = request.data.get('pond_details', [])
            
            # Validate that name is provided for new pond pairs
            if not name:
                return Response(
                    {'error': 'Pond pair name is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if this is a reactivation attempt
            existing_pair = PondPair.objects.filter(device_id=device_id).first()
            is_reactivation = existing_pair and existing_pair.owner.username == settings.SYSTEM_USERNAME
            
            if is_reactivation:
                # Handle reactivation: transfer ownership and update ponds
                with transaction.atomic():
                    # Transfer ownership
                    existing_pair.owner = request.user
                    existing_pair.save()
                    
                    # Update pond details if provided
                    if pond_details:
                        existing_ponds = list(existing_pair.ponds.all())
                        
                        # Update existing ponds or create new ones
                        for i, pond_detail in enumerate(pond_details):
                            if i < len(existing_ponds):
                                # Update existing pond
                                existing_ponds[i].name = pond_detail['name']
                                existing_ponds[i].sensor_height = pond_detail['sensor_height']
                                existing_ponds[i].tank_depth = pond_detail['tank_depth']
                                existing_ponds[i].is_active = True
                                existing_ponds[i].save()
                            else:
                                # Create new pond
                                Pond.objects.create(
                                    name=pond_detail['name'],
                                    parent_pair=existing_pair,
                                    sensor_height=pond_detail['sensor_height'],
                                    tank_depth=pond_detail['tank_depth'],
                                    is_active=True
                                )
                        
                        # Deactivate any extra ponds beyond the new count
                        for i in range(len(pond_details), len(existing_ponds)):
                            existing_ponds[i].is_active = False
                            existing_ponds[i].save()
                    
                    # Validate pond count after re-registration
                    try:
                        existing_pair.validate_pond_count()
                    except ValidationError as e:
                        # If validation fails, revert ownership and re-raise
                        existing_pair.owner = get_user_model().objects.get(username=settings.SYSTEM_USERNAME)
                        existing_pair.save()
                        raise e
                    
                    # Return success response
                    response_serializer = PondPairDetailSerializer(existing_pair)
                    return Response({
                        'message': 'Pond pair re-registered successfully',
                        'pond_pair': response_serializer.data
                    }, status=status.HTTP_200_OK)
            else:
                # Handle new registration: use normal serializer validation
                serializer = self.get_serializer(data=request.data)
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                with transaction.atomic():
                    pond_pair = serializer.save(owner=request.user)
                    response_serializer = PondPairDetailSerializer(pond_pair)
                    return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating pond pair: {str(e)}")
            return Response(
                {'error': 'An error occurred while creating the pond pair'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PondPairDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting a specific pond pair
    
    GET: Get detailed information about a pond pair
    PUT/PATCH: Update pond pair information
    DELETE: Delete a pond pair (and all its ponds)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PondPairDetailSerializer
    
    def get_queryset(self):
        """Get pond pairs owned by the authenticated user"""
        return PondPair.objects.filter(owner=self.request.user).prefetch_related('ponds')
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PondPairUpdateSerializer
        return PondPairDetailSerializer
    
    def update(self, request, *args, **kwargs):
        """Update pond pair with validation"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            # Return the updated pond pair with full details
            response_serializer = PondPairDetailSerializer(instance)
            return Response(response_serializer.data)
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Http404:
            # Let 404 errors propagate naturally
            raise
        except Exception as e:
            logger.error(f"Error updating pond pair: {str(e)}")
            return Response(
                {'error': 'An error occurred while updating the pond pair'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Delete pond pair and all its ponds"""
        try:
            with transaction.atomic():
                instance = self.get_object()
                pond_count = instance.pond_count
                
                # Delete the pond pair (this will cascade to ponds)
                self.perform_destroy(instance)
                
                return Response(status=status.HTTP_204_NO_CONTENT)
                
        except Http404:
            # Let 404 errors propagate naturally
            raise
        except Exception as e:
            logger.error(f"Error deleting pond pair: {str(e)}")
            return Response(
                {'error': 'An error occurred while deleting the pond pair'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PondPairWithDetailsView(generics.RetrieveAPIView):
    """
    API view for getting detailed pond pair information including controls and sensor data
    
    GET: Get comprehensive information about a pond pair
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PondPairWithPondDetailsSerializer
    
    def get_queryset(self):
        """Get pond pairs owned by the authenticated user with related data"""
        return PondPair.objects.filter(owner=self.request.user).prefetch_related(
            'ponds',
            'ponds__controls',
            'ponds__sensor_readings'
        )


class PondPairSummaryListView(generics.ListAPIView):
    """
    API view for getting a summary list of pond pairs
    
    GET: Get a lightweight summary of all pond pairs for the user
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PondPairSummarySerializer
    
    def get_queryset(self):
        """Get pond pairs owned by the authenticated user"""
        return PondPair.objects.filter(owner=self.request.user).prefetch_related('ponds')


class PondPairByDeviceView(generics.RetrieveAPIView):
    """
    API view for retrieving a pond pair by device ID
    
    GET: Get pond pair information by device ID
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PondPairDetailSerializer
    
    def get_queryset(self):
        """Get pond pairs owned by the authenticated user"""
        return PondPair.objects.filter(owner=self.request.user).prefetch_related('ponds')
    
    def get_object(self):
        """Get pond pair by device_id instead of pk"""
        device_id = self.kwargs.get('device_id')
        return get_object_or_404(self.get_queryset(), device_id=device_id)


class PondPairAddPondView(generics.GenericAPIView):
    """
    API view for adding a pond to an existing pond pair
    
    POST: Add a new pond to an existing pond pair
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PondPairDetailSerializer
    
    def get_queryset(self):
        """Get pond pairs owned by the authenticated user"""
        return PondPair.objects.filter(owner=self.request.user).prefetch_related('ponds')
    
    def post(self, request, pond_pair_id):
        """Add a pond to an existing pond pair"""
        try:
            with transaction.atomic():
                pond_pair = get_object_or_404(self.get_queryset(), id=pond_pair_id)
                
                # Check if pond pair can accept more ponds
                if pond_pair.pond_count >= 2:
                    return Response(
                        {'error': 'This pond pair already has 2 ponds and cannot accept more'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate request data
                pond_name = request.data.get('name')
                sensor_height = request.data.get('sensor_height')
                tank_depth = request.data.get('tank_depth')
                
                # Validate required fields
                if not pond_name:
                    return Response(
                        {'error': 'Pond name is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if sensor_height is None:
                    return Response(
                        {'error': 'sensor_height is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if tank_depth is None:
                    return Response(
                        {'error': 'tank_depth is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate field values
                try:
                    sensor_height = float(sensor_height)
                    if sensor_height < 0:
                        return Response(
                            {'error': 'sensor_height must be >= 0'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        {'error': 'sensor_height must be a valid number'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    tank_depth = float(tank_depth)
                    if tank_depth < 0:
                        return Response(
                            {'error': 'tank_depth must be >= 0'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    return Response(
                        {'error': 'tank_depth must be a valid number'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if user already has a pond with this name
                if Pond.objects.filter(
                    parent_pair__owner=request.user,
                    name=pond_name,
                    is_active=True
                ).exists():
                    return Response(
                        {'error': f'You already have an active pond named "{pond_name}"'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create the new pond
                pond_data = {
                    'name': pond_name,
                    'parent_pair': pond_pair,
                    'sensor_height': sensor_height,
                    'tank_depth': tank_depth
                }
                
                pond = Pond.objects.create(**pond_data)
                
                # Refresh the pond pair to get updated pond count
                pond_pair.refresh_from_db()
                
                # Return the updated pond pair
                serializer = self.get_serializer(pond_pair)
                return Response(serializer.data, status=status.HTTP_200_OK)
                
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error adding pond to pair {pond_pair_id}: {str(e)}")
            return Response(
                {'error': 'An error occurred while adding the pond'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 


class PondPairRemovePondView(generics.GenericAPIView):
    """
    API view for removing a pond from a pond pair
    
    POST: Remove a pond from the pond pair
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pond_pair_id, pond_id):
        """Remove a pond from the pond pair"""
        try:
            pond_pair = get_object_or_404(PondPair, id=pond_pair_id, owner=request.user)
            pond = get_object_or_404(Pond, id=pond_id, parent_pair=pond_pair)
            
            # Check if this is the last active pond
            active_ponds = pond_pair.ponds.filter(is_active=True)
            if active_ponds.count() <= 1:
                return Response(
                    {'error': 'Cannot remove the last active pond from a pair'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Deactivate the pond instead of deleting it
            pond.is_active = False
            pond.save()
            
            return Response(
                {'message': f'Pond {pond.name} removed from pair {pond_pair.name}'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Error removing pond {pond_id} from pair {pond_pair_id}: {str(e)}")
            return Response(
                {'error': 'Failed to remove pond from pair'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PondListView(generics.GenericAPIView):
    """
    API view for listing user's ponds
    
    GET: List all ponds owned by the authenticated user
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get ponds owned by the authenticated user"""
        try:
            # Check if user wants to include inactive ponds
            include_inactive = request.query_params.get('include_inactive', 'false').lower() == 'true'
            
            if include_inactive:
                ponds = Pond.objects.filter(parent_pair__owner=request.user).select_related('parent_pair')
            else:
                ponds = Pond.objects.filter(parent_pair__owner=request.user, is_active=True).select_related('parent_pair')
            
            # Serialize ponds manually
            pond_data = []
            for pond in ponds:
                pond_data.append({
                    'id': pond.id,
                    'name': pond.name,
                    'pond': pond.id,  # For test compatibility
                    'sensor_height': pond.sensor_height,
                    'tank_depth': pond.tank_depth,
                    'parent_pair': {
                        'id': pond.parent_pair.id,
                        'name': pond.parent_pair.name,
                        'device_id': pond.parent_pair.device_id,
                    },
                    'is_active': pond.is_active,
                    'created_at': pond.created_at.isoformat() if hasattr(pond, 'created_at') else None,
                })
            
            return Response(pond_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting ponds for user: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PondDetailView(generics.GenericAPIView):
    """
    API view for pond detail operations
    
    GET: Get pond details
    PUT/PATCH: Update pond details
    DELETE: Delete pond
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        """Get pond details"""
        try:
            pond = Pond.objects.filter(parent_pair__owner=request.user).get(id=pk)
            
            # Serialize pond manually to avoid serializer issues
            pond_data = {
                'id': pond.id,
                'name': pond.name,
                'sensor_height': pond.sensor_height,
                'tank_depth': pond.tank_depth,
                'parent_pair': pond.parent_pair.id,  # Just the ID, not the full object
                'is_active': pond.is_active,
                'created_at': pond.created_at.isoformat() if hasattr(pond, 'created_at') else None,
            }
            
            return Response(pond_data, status=status.HTTP_200_OK)
            
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting pond {pk}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, pk):
        """Update pond details"""
        try:
            pond = Pond.objects.filter(parent_pair__owner=request.user).get(id=pk)
            
            # Update allowed fields
            if 'name' in request.data:
                pond.name = request.data['name']
            
            if 'sensor_height' in request.data:
                pond.sensor_height = request.data['sensor_height']
            
            if 'tank_depth' in request.data:
                pond.tank_depth = request.data['tank_depth']
            
            if 'is_active' in request.data:
                pond.is_active = request.data['is_active']
            
            pond.full_clean()
            pond.save()
            
            # Return updated pond data
            pond_data = {
                'id': pond.id,
                'name': pond.name,
                'sensor_height': pond.sensor_height,
                'tank_depth': pond.tank_depth,
                'parent_pair': pond.parent_pair.id,  # Just the ID, not the full object
                'is_active': pond.is_active,
                'created_at': pond.created_at.isoformat() if hasattr(pond, 'created_at') else None,
            }
            
            return Response(pond_data, status=status.HTTP_200_OK)
            
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error updating pond {pk}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, pk):
        """Delete pond"""
        try:
            pond = Pond.objects.filter(parent_pair__owner=request.user).get(id=pk)
            
            # Check if this is the last pond in the pair
            if pond.parent_pair.pond_count <= 1:
                return Response(
                    {'error': 'Cannot delete the last pond from a pair'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            pond.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
            
        except Pond.DoesNotExist:
            return Response(
                {'error': 'Pond not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error deleting pond {pk}: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PondRegistrationView(generics.CreateAPIView):
    """
    API view for pond registration
    
    POST: Register a new pond
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PondPairCreateSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new pond with validation"""
        try:
            # Use the serializer for proper validation
            serializer = self.get_serializer(data=request.data, context={'request': request})
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Create the pond pair using the serializer
            pond_pair = serializer.save(owner=request.user)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
                
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in pond registration: {str(e)}")
            return Response(
                {'error': f'Failed to register pond: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Add PondFeedStatsView to ponds app


class PondPairDeactivateView(APIView):
    """
    Deactivate a pond pair by device_id
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Deactivate a pond pair and all its ponds"""
        try:
            device_id = request.data.get('device_id')
            
            if not device_id:
                return Response(
                    {'error': 'device_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Find the pond pair by device_id
            try:
                pond_pair = PondPair.objects.get(device_id=device_id, owner=request.user)
            except PondPair.DoesNotExist:
                return Response(
                    {'error': 'Pond pair with this device_id not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Delete all ponds in the pair
            deleted_ponds = []
            for pond in pond_pair.ponds.all():
                deleted_ponds.append(pond.name)
                pond.delete(force_delete=True)  # Force delete to bypass constraint
            
            # Deactivate the pond pair itself
            pond_pair.is_active = False
            pond_pair.save()
            
            return Response({
                'message': f'Pond pair "{pond_pair.name}" deactivated successfully - all ponds deleted and pair deactivated',
                'device_id': device_id,
                'deleted_ponds': deleted_ponds,
                'pond_count': len(deleted_ponds),
                'pond_pair_active': False
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error deactivating pond pair with device_id {device_id}: {str(e)}")
            return Response(
                {'error': 'An error occurred while deactivating the pond pair'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
