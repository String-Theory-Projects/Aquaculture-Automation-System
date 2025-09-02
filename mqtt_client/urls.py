"""
URL patterns for MQTT Client API endpoints.
"""

from django.urls import path
from . import views

app_name = 'mqtt_client'

urlpatterns = [
    # Device Commands
    path('commands/feed/', views.send_feed_command, name='send_feed_command'),
    path('commands/water/', views.send_water_command, name='send_water_command'),
    path('commands/firmware/', views.send_firmware_update, name='send_firmware_update'),
    path('commands/restart/', views.send_restart_command, name='send_restart_command'),
    
    # Device Status & Monitoring
    path('devices/<int:pond_pair_id>/status/', views.get_device_status, name='get_device_status'),
    path('devices/<int:pond_pair_id>/commands/', views.get_device_commands, name='get_device_commands'),
    path('devices/<int:pond_pair_id>/messages/', views.get_mqtt_messages, name='get_mqtt_messages'),
    path('devices/<int:pond_pair_id>/connectivity/', views.check_device_connectivity, name='check_device_connectivity'),
    
    # System Overview
    path('devices/online/', views.get_online_devices, name='get_online_devices'),
    path('commands/pending/', views.get_pending_commands, name='get_pending_commands'),
    path('system/health/', views.get_system_health, name='get_system_health'),
    path('client/status/', views.get_mqtt_client_status, name='get_mqtt_client_status'),
]

