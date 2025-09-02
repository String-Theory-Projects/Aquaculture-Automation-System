from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # User profile
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('update-profile/', views.UpdateProfileView.as_view(), name='update_profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Pond management
    path('ponds/', views.PondListView.as_view(), name='pond_list'),
    path('ponds/<int:pk>/', views.PondDetailView.as_view(), name='pond_detail'),
]
