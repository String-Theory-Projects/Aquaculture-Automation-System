from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Core System'
    
    def ready(self):
        """Initialize core app when Django starts"""
        try:
            import core.signals  # noqa
        except ImportError:
            pass
