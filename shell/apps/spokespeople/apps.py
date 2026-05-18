from django.apps import AppConfig


class SpokespeopleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.spokespeople"

    def ready(self):
        # Import for side effect — registers post_save signal
        # that syncs personality edits to Runway.
        from . import signals  # noqa: F401
