from django.urls import path
from . import views

app_name = 'ponds'

urlpatterns = [
    # Pond Pair registration and management
    path('', views.PondPairListView.as_view(), name='pond_pair_list'),
    path('summary/', views.PondPairSummaryListView.as_view(), name='pond_pair_summary_list'),
    path('<int:pk>/', views.PondPairDetailView.as_view(), name='pond_pair_detail'),
    path('<int:pk>/details/', views.PondPairWithDetailsView.as_view(), name='pond_pair_with_details'),
    path('<int:pond_pair_id>/add-pond/', views.PondPairAddPondView.as_view(), name='pond_pair_add_pond'),
    path('<int:pond_pair_id>/remove-pond/<int:pond_id>/', views.PondPairRemovePondView.as_view(), name='pond_pair_remove_pond'),
    path('device/<str:device_id>/', views.PondPairByDeviceView.as_view(), name='pond_pair_by_device'),
    
    # Pond management URLs
    path('ponds/', views.PondListView.as_view(), name='pond_list'),
    path('ponds/<int:pk>/', views.PondDetailView.as_view(), name='pond_detail'),
    path('ponds/register/', views.PondRegistrationView.as_view(), name='register_pond'),
    
    # Feed stats URL
    path('ponds/<int:pond_id>/feed-stats/', views.PondFeedStatsView.as_view(), name='pond_feed_stats'),
    
    # Deactivate pond pair
    path('deactivate/', views.PondPairDeactivateView.as_view(), name='pond_pair_deactivate'),
]
