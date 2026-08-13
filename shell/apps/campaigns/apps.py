from django.apps import AppConfig


class CampaignsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.campaigns"

    def ready(self) -> None:
        # Import signal receivers so cross-workspace validation
        # fires at save time even outside `clean()` / form flows.
        from . import signals  # noqa: F401
