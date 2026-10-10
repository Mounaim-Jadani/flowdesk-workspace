from django.apps import AppConfig


class KarmaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'karma'

    def ready(self):
        # Importing rules registers the scoring handlers on the event bus.
        from . import rules  # noqa: F401
