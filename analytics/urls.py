from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('current-data/', views.dashboard_current_data, name='dashboard_current_data'),
    path('historical-data/', views.HistoricalDataView.as_view(), name='dashboard_historical_data'),
    path('user-ponds/', views.UserPondsDropdownView.as_view(), name='user_ponds_dropdown'),
    path('dashboard-data/', views.DashboardDataView.as_view(), name='dashboard_data'),
]
