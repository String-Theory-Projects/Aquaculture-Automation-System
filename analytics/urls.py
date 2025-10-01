from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('feed-stats/', views.PondFeedStatsView.as_view(), name='pond_feed_stats'),
    path('feed-history/', views.PondFeedHistoryView.as_view(), name='pond_feed_history'),
]
