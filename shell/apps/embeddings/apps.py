from django.apps import AppConfig


class EmbeddingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.embeddings"

    def ready(self) -> None:
        # Wire the cross-workspace M2M validator. Import-as-side-
        # effect is the standard Django pattern for signals.
        from . import signals  # noqa: F401
