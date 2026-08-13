from django.apps import AppConfig


class ConversationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.conversations"

    def ready(self) -> None:
        # Import signal receivers so message-create
        # auto-enqueues the embedding pipeline (K8 completion).
        from . import signals  # noqa: F401
