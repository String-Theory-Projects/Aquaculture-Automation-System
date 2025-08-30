"""
URL configuration for automation app.
"""

from django.urls import path
from . import views

app_name = 'automation'

urlpatterns = [
    # Threshold management
    path('ponds/<int:pond_id>/thresholds/', views.get_active_thresholds, name='get_active_thresholds'),
    path('ponds/<int:pond_id>/thresholds/create/', views.create_threshold, name='create_threshold'),
    path('thresholds/<int:threshold_id>/update/', views.update_threshold, name='update_threshold'),
    path('thresholds/<int:threshold_id>/delete/', views.delete_threshold, name='delete_threshold'),
    
    # Automation schedules
    path('ponds/<int:pond_id>/schedules/', views.ListAutomationSchedulesView.as_view(), name='pond_automation_schedule_list'),
    path('ponds/<int:pond_id>/schedules/create/', views.CreateAutomationScheduleView.as_view(), name='create_automation_schedule'),
    path('ponds/<int:pond_id>/schedules/<int:schedule_id>/delete/', views.DeleteAutomationScheduleView.as_view(), name='pond_automation_schedule_delete'),
    path('ponds/<int:pond_id>/schedules/<int:schedule_id>/', views.UpdateAutomationScheduleView.as_view(), name='pond_automation_schedule_detail'),
    path('schedules/<int:schedule_id>/update/', views.update_automation_schedule, name='update_automation_schedule'),
    path('schedules/<int:schedule_id>/delete/', views.delete_automation_schedule, name='delete_automation_schedule'),
    
    # Automation execution
    path('ponds/<int:pond_id>/execute/', views.execute_manual_automation, name='execute_manual_automation'),
    path('ponds/<int:pond_id>/history/', views.get_automation_history, name='get_automation_history'),
    path('pending/', views.get_pending_automations, name='get_pending_automations'),
    
    # System monitoring
    path('ponds/<int:pond_id>/status/', views.get_automation_status, name='get_automation_status'),
    path('ponds/<int:pond_id>/conflicts/resolve/', views.resolve_automation_conflicts, name='resolve_automation_conflicts'),
    
    # Phase 5: Device Control Commands
    path('ponds/<int:pond_id>/control/feed/', views.ExecuteFeedCommandView.as_view(), name='execute_feed_command_view'),
    path('ponds/<int:pond_id>/control/water/', views.ExecuteWaterCommandView.as_view(), name='execute_water_command_view'),
    path('ponds/<int:pond_id>/control/firmware/', views.execute_firmware_command, name='execute_firmware_command'),
    
    # Phase 5: Device History & Monitoring
    path('ponds/<int:pond_id>/history/commands/', views.get_device_history, name='get_device_history'),
    path('ponds/<int:pond_id>/history/automation/', views.get_automation_history, name='get_automation_history'),
    path('ponds/<int:pond_id>/history/alerts/', views.get_alerts, name='get_alerts'),
    
    # Phase 5: Alert Management
    path('alerts/<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('alerts/<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Phase 5: Threshold Configuration
    path('ponds/<int:pond_id>/thresholds/config/', views.get_threshold_configuration, name='get_threshold_configuration'),
    
    # Phase 5: Device Status
    path('ponds/<int:pond_id>/device/status/', views.get_device_status, name='get_device_status'),
    
    # Feed event logging
    path('feed/log-event/', views.log_feed_event, name='log_feed_event'),
]
