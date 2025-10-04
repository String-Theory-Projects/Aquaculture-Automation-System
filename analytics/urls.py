from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('feed-stats/', views.PondFeedStatsView.as_view(), name='pond_feed_stats'),
    path('feed-history/', views.PondFeedHistoryView.as_view(), name='pond_feed_history'),
    path('ponds/<int:pond_id>/feed-multi-stats/', views.PondFeedMultiStatsView.as_view(), name='pond_feed_multi_stats'),
    path('ponds/<int:pond_id>/historical-data/', views.HistoricalDataView.as_view(), name='historical_data'),
]
