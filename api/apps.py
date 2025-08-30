from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    verbose_name = 'API Management'
    
    def ready(self):
        """Initialize API app when Django starts"""
        try:
            import api.signals  # noqa
        except ImportError:
            pass
