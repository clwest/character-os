from django.apps import AppConfig


class ScriptsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.scripts"

    def ready(self) -> None:
        # Import signal receivers so cross-workspace validation
        # fires at save time even outside `clean()` / form flows.
        # Mirrors apps.publish.apps + apps.campaigns.apps.
        from . import signals  # noqa: F401
