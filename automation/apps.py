from django.apps import AppConfig


class AutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'automation'
    verbose_name = 'Automation & Control'
    
    def ready(self):
        """Initialize automation app when Django starts"""
        try:
            import automation.signals  # noqa
        except ImportError:
            pass
