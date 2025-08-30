"""
API Views for MQTT Client operations.

This module provides REST API endpoints for:
- Device command execution
- Device status monitoring
- System health information
- MQTT message history
"""

import logging
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
import json

from .services import mqtt_service
from ponds.models import PondPair
from core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_feed_command(request):
    """Send feed command to device"""
    try:
        data = json.loads(request.body)
        pond_pair_id = data.get('pond_pair_id')
        amount = data.get('amount', 100)
        user = request.user
        
        if not pond_pair_id:
            return JsonResponse({
                'success': False,
                'error': 'pond_pair_id is required'
            }, status=400)
        
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        # Validate amount
        if not isinstance(amount, (int, float)) or amount <= 0:
            return JsonResponse({
                'success': False,
                'error': 'Amount must be a positive number'
            }, status=400)
        
        # Send command
        command_id = mqtt_service.send_feed_command(pond_pair, amount, user)
        
        if command_id:
            return JsonResponse({
                'success': True,
                'command_id': command_id,
                'message': f'Feed command sent to {pond_pair.name}',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to send feed command'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error sending feed command: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_water_command(request):
    """Send water control command to device"""
    try:
        data = json.loads(request.body)
        pond_pair_id = data.get('pond_pair_id')
        action = data.get('action')
        level = data.get('level')
        user = request.user
        
        if not pond_pair_id:
            return JsonResponse({
                'success': False,
                'error': 'pond_pair_id is required'
            }, status=400)
        
        # Validate action
        if not action or action not in [
            'WATER_DRAIN', 'WATER_FILL', 'WATER_FLUSH',
            'WATER_INLET_OPEN', 'WATER_INLET_CLOSE',
            'WATER_OUTLET_OPEN', 'WATER_OUTLET_CLOSE'
        ]:
            return JsonResponse({
                'success': False,
                'error': 'action must be one of: WATER_DRAIN, WATER_FILL, WATER_FLUSH, WATER_INLET_OPEN, WATER_INLET_CLOSE, WATER_OUTLET_OPEN, WATER_OUTLET_CLOSE'
            }, status=400)
        
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        # Validate level if provided
        if level is not None:
            if not isinstance(level, (int, float)) or level < 0 or level > 100:
                return JsonResponse({
                    'success': False,
                    'error': 'Level must be between 0 and 100'
                }, status=400)
        
        # Send command
        command_id = mqtt_service.send_water_command(pond_pair, action, level, user)
        
        if command_id:
            return JsonResponse({
                'success': True,
                'command_id': command_id,
                'message': f'Water command sent to {pond_pair.name}',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to send water command'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error sending water command: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_firmware_update(request):
    """Send firmware update command to device"""
    try:
        data = json.loads(request.body)
        pond_pair_id = data.get('pond_pair_id')
        firmware_url = data.get('firmware_url')
        user = request.user
        
        if not pond_pair_id:
            return JsonResponse({
                'success': False,
                'error': 'pond_pair_id is required'
            }, status=400)
        
        if not firmware_url:
            return JsonResponse({
                'success': False,
                'error': 'firmware_url is required'
            }, status=400)
        
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        # Send command
        command_id = mqtt_service.send_firmware_update(pond_pair, firmware_url, user)
        
        if command_id:
            return JsonResponse({
                'success': True,
                'command_id': command_id,
                'message': f'Firmware update command sent to {pond_pair.name}',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to send firmware update command'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error sending firmware update command: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_restart_command(request):
    """Send device restart command"""
    try:
        data = json.loads(request.body)
        pond_pair_id = data.get('pond_pair_id')
        user = request.user
        
        if not pond_pair_id:
            return JsonResponse({
                'success': False,
                'error': 'pond_pair_id is required'
            }, status=400)
        
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        # Send command
        command_id = mqtt_service.send_restart_command(pond_pair, user)
        
        if command_id:
            return JsonResponse({
                'success': True,
                'command_id': command_id,
                'message': f'Restart command sent to {pond_pair.name}',
                'timestamp': timezone.now().isoformat()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to send restart command'
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error sending restart command: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_device_status(request, pond_pair_id):
    """Get device status for a specific pond pair"""
    try:
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        device_status = mqtt_service.get_device_status(pond_pair)
        
        if device_status:
            return JsonResponse({
                'success': True,
                'data': device_status
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Device status not found'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error getting device status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_device_commands(request, pond_pair_id):
    """Get device commands for a specific pond pair"""
    try:
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        # Get pagination parameters
        page_size = min(
            int(request.GET.get('page_size', DEFAULT_PAGE_SIZE)),
            MAX_PAGE_SIZE
        )
        
        commands = mqtt_service.get_device_commands(pond_pair, page_size)
        
        return JsonResponse({
            'success': True,
            'data': commands,
            'count': len(commands),
            'page_size': page_size
        })
        
    except Exception as e:
        logger.error(f"Error getting device commands: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_mqtt_messages(request, pond_pair_id):
    """Get MQTT messages for a specific pond pair"""
    try:
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        # Get pagination parameters
        page_size = min(
            int(request.GET.get('page_size', DEFAULT_PAGE_SIZE)),
            MAX_PAGE_SIZE
        )
        
        messages = mqtt_service.get_mqtt_messages(pond_pair, page_size)
        
        return JsonResponse({
            'success': True,
            'data': messages,
            'count': len(messages),
            'page_size': page_size
        })
        
    except Exception as e:
        logger.error(f"Error getting MQTT messages: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_online_devices(request):
    """Get list of all online devices"""
    try:
        online_devices = mqtt_service.get_online_devices()
        
        return JsonResponse({
            'success': True,
            'data': online_devices,
            'count': len(online_devices)
        })
        
    except Exception as e:
        logger.error(f"Error getting online devices: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_pending_commands(request):
    """Get list of all pending commands"""
    try:
        pending_commands = mqtt_service.get_pending_commands()
        
        return JsonResponse({
            'success': True,
            'data': pending_commands,
            'count': len(pending_commands)
        })
        
    except Exception as e:
        logger.error(f"Error getting pending commands: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def check_device_connectivity(request, pond_pair_id):
    """Check device connectivity and health"""
    try:
        try:
            pond_pair = PondPair.objects.get(id=pond_pair_id)
        except PondPair.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Pond pair not found'
            }, status=404)
        
        connectivity = mqtt_service.check_device_connectivity(pond_pair)
        
        return JsonResponse({
            'success': True,
            'data': connectivity
        })
        
    except Exception as e:
        logger.error(f"Error checking device connectivity: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_system_health(request):
    """Get overall system health summary"""
    try:
        health_summary = mqtt_service.get_system_health_summary()
        
        return JsonResponse({
            'success': True,
            'data': health_summary
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def get_mqtt_client_status(request):
    """Get MQTT client connection status"""
    try:
        client = mqtt_service.client
        
        status = {
            'is_connected': client.is_connected,
            'broker_host': client.config.broker_host,
            'broker_port': client.config.broker_port,
            'reconnect_attempts': client.reconnect_attempts,
            'max_reconnect_attempts': client.max_reconnect_attempts,
            'online_devices': len(client.device_heartbeats),
            'pending_commands': len(client.pending_commands),
            'last_updated': timezone.now().isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'data': status
        })
        
    except Exception as e:
        logger.error(f"Error getting MQTT client status: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
