from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics & Reporting'
    
    def ready(self):
        """Initialize analytics app when Django starts"""
        try:
            import analytics.signals  # noqa
        except ImportError:
            pass
