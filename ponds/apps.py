from django.apps import AppConfig


class PondsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ponds'
    verbose_name = 'Pond Management'
    
    def ready(self):
        """Initialize ponds app when Django starts"""
        try:
            import ponds.signals  # noqa
        except ImportError:
            pass
