from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.realtime"

    def ready(self) -> None:
        # Import signal receivers so cross-workspace validation
        # fires at save time even outside `clean()` / form flows.
        from . import signals  # noqa: F401
