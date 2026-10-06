from django.apps import AppConfig

class DigestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'digest'

    def ready(self):
        import digest.signals  # noqa: F401
