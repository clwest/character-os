from django.apps import AppConfig


class PublishConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publish"

    def ready(self) -> None:
        # Import signal receivers so cross-workspace validation
        # + the cross-app post_save Composition flip fire at
        # save time even outside `clean()` / form flows.
        from . import signals  # noqa: F401
