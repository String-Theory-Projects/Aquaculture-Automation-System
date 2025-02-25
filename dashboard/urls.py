from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.auth_views import *
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from dashboard.views.auth_views import (
    RegisterView,
    CustomTokenObtainPairView,
    LogoutView,
    UserProfileView,
    ChangePasswordView
)

from dashboard.views.profile_views import (
    RegisterPondView,
    UpdateProfileView,
    PondDetailView,
    PondListView,
)

from dashboard.views.settings_views import (
    WiFiConfigView,
    AutomationScheduleView,
    AutomationScheduleDetailView
)

from dashboard.views.analytics_views import (
    DashboardDataView,
    HistoricalDataView,
    UserPondsDropdownView
)

from dashboard.views.control_views import (
    FeedDispenserView,
    WaterValveControlView,
    DeviceLogView,
    ExecuteAutomationView
)

# Get All Tables
router = DefaultRouter()


urlpatterns = [
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User profile
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('update-profile/', UpdateProfileView.as_view(), name='update_profile'),
    
    # Pond registration and management
    path('ponds/', PondListView.as_view(), name='pond_list'),
    path('ponds/register-pond/', RegisterPondView.as_view(), name='register_pond'),
    path('ponds/<int:pk>/', PondDetailView.as_view(), name='pond_detail'),

    # Settings 
    path('settings/<int:pond_id>/wifi/', WiFiConfigView.as_view(), name='wifi_config'),
    path('settings/<int:pond_id>/schedules/', AutomationScheduleView.as_view(), name='automation_schedules'),
    path('settings/schedules/<int:schedule_id>/', AutomationScheduleDetailView.as_view(), name='automation_schedule_detail'),

    # Dashboard
    path('dashboard/current-data/', DashboardDataView.as_view(), name='dashboard_current_data'),
    path('dashboard/historical-data/', HistoricalDataView.as_view(), name='dashboard_historical_data'),
    path('dashboard/user-ponds/', UserPondsDropdownView.as_view(), name='user_ponds_dropdown'),

    # Pond Control endpoints
    path('control/<int:pond_id>/feed/', FeedDispenserView.as_view(), name='feed_dispenser'),
    path('control/<int:pond_id>/water-valve/', WaterValveControlView.as_view(), name='water_valve_control'),
    path('control/<int:pond_id>/logs/', DeviceLogView.as_view(), name='device_logs'),
    path('control/automation/<int:schedule_id>/execute/', ExecuteAutomationView.as_view(), name='execute_automation'),
]
