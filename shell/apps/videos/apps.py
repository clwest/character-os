from django.apps import AppConfig


class VideosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.videos"

    def ready(self) -> None:
        # V6 — wire the Composition→Video sync receiver. Same
        # import-as-side-effect pattern as apps.embeddings and
        # apps.compositions.
        from . import signals  # noqa: F401
