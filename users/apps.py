from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'User Management'
    
    def ready(self):
        """Initialize users app when Django starts"""
        try:
            import users.signals  # noqa
        except ImportError:
            pass
