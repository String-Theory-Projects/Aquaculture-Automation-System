from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.auth_views import *
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from dashboard.views.auth_views import (
    RegisterView,
    CustomTokenObtainPairView,
    LogoutView,
    RegisterPondView,
    UserProfileView,
    ChangePasswordView
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
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Pond registration
    path('auth/register-pond/', RegisterPondView.as_view(), name='register_pond')
]