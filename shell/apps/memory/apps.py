from django.apps import AppConfig


class MemoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.memory"

    def ready(self) -> None:
        # SESSION 264 Slice 1 — wire the witnessed_by pre_add guard.
        from . import signals  # noqa: F401
