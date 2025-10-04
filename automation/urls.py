"""
URL configuration for automation app.
"""

from django.urls import path
from . import views

app_name = 'automation'

urlpatterns = [
    # Threshold management
    path('ponds/<int:pond_id>/thresholds/', views.GetActiveThresholdsView.as_view(), name='get_active_thresholds'),
    path('ponds/<int:pond_id>/thresholds/create/', views.CreateThresholdView.as_view(), name='create_threshold'),
    path('thresholds/<int:threshold_id>/update/', views.UpdateThresholdView.as_view(), name='update_threshold'),
    path('thresholds/<int:threshold_id>/delete/', views.DeleteThresholdView.as_view(), name='delete_threshold'),
    
    # Automation schedules
    path('ponds/<int:pond_id>/schedules/', views.GetAutomationSchedulesView.as_view(), name='pond_automation_schedule_list'),
    path('ponds/<int:pond_id>/schedules/create/', views.CreateAutomationScheduleView.as_view(), name='create_automation_schedule'),
    path('ponds/<int:pond_id>/schedules/<int:schedule_id>/delete/', views.DeleteAutomationScheduleView.as_view(), name='pond_automation_schedule_delete'),
    path('ponds/<int:pond_id>/schedules/<int:schedule_id>/', views.UpdateAutomationScheduleView.as_view(), name='pond_automation_schedule_detail'),
    path('schedules/<int:schedule_id>/update/', views.UpdateAutomationScheduleFunctionView.as_view(), name='update_automation_schedule'),
    path('schedules/<int:schedule_id>/delete/', views.DeleteAutomationScheduleFunctionView.as_view(), name='delete_automation_schedule'),
    
    # Automation execution
    path('ponds/<int:pond_id>/execute/', views.ExecuteManualAutomationView.as_view(), name='execute_manual_automation'),
    path('ponds/<int:pond_id>/history/', views.GetAutomationHistoryView.as_view(), name='get_automation_history'),
    path('pending/', views.GetPendingAutomationsView.as_view(), name='get_pending_automations'),
    
    # Phase 5: System monitoring
    path('ponds/<int:pond_id>/status/', views.GetAutomationStatusView.as_view(), name='get_automation_status'),
    path('ponds/<int:pond_id>/conflicts/resolve/', views.ResolveAutomationConflictsView.as_view(), name='resolve_automation_conflicts'),
    path('ponds/<int:pond_id>/cleanup-stuck/', views.CleanupStuckAutomationsView.as_view(), name='cleanup_stuck_automations'),
    
    # Phase 5: Device Control Commands
    path('ponds/<int:pond_id>/control/feed/', views.ExecuteFeedCommandView.as_view(), name='execute_feed_command_view'),
    path('ponds/<int:pond_id>/control/water/', views.ExecuteWaterCommandView.as_view(), name='execute_water_command_view'),
    path('ponds/<int:pond_id>/control/threshold/', views.ExecuteThresholdCommandView.as_view(), name='execute_threshold_command_view'),
    path('ponds/<int:pond_id>/control/reboot/', views.ExecuteRebootCommandView.as_view(), name='execute_reboot_command_view'),
    path('ponds/<int:pond_id>/control/firmware/', views.ExecuteFirmwareCommandView.as_view(), name='execute_firmware_command_view'),
    
    # Phase 5: Device History & Monitoring
    path('ponds/<int:pond_id>/history/commands/', views.GetDeviceHistoryView.as_view(), name='get_device_history'),
    path('ponds/<int:pond_id>/history/automation/', views.GetAutomationHistoryView.as_view(), name='get_automation_history'),
    path('ponds/<int:pond_id>/history/alerts/', views.GetAlertsView.as_view(), name='get_alerts'),
    
    # Phase 5: Alert Management
    path('alerts/<int:alert_id>/acknowledge/', views.AcknowledgeAlertView.as_view(), name='acknowledge_alert'),
    path('alerts/<int:alert_id>/resolve/', views.ResolveAlertView.as_view(), name='resolve_alert'),
    
    # Phase 5: Threshold Configuration
    path('ponds/<int:pond_id>/thresholds/config/', views.GetThresholdConfigurationView.as_view(), name='get_threshold_configuration'),
    
    # Phase 5: Device Status
    path('ponds/<int:pond_id>/device/status/', views.GetDeviceStatusView.as_view(), name='get_device_status'),
    
    # SSE Status Streaming
    path('commands/<str:command_id>/stream/', views.CommandStatusStreamView.as_view(), name='command_status_stream'),
    path('commands/<str:command_id>/status/', views.CommandStatusView.as_view(), name='command_status'),
    path('commands/<str:command_id>/test-redis/', views.TestRedisView.as_view(), name='test_redis'),
    
    # Phase 6: Unified Dashboard Stream
    path('dashboard/<int:pond_id>/unified-stream/', views.UnifiedDashboardStreamView.as_view(), name='unified_dashboard_stream'),
    
    # Feed event logging
]
