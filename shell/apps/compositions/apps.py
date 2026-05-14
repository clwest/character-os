from django.apps import AppConfig


class CompositionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.compositions"

    def ready(self) -> None:
        # Wire the cross-workspace validator. Import-as-side-effect
        # is the standard Django pattern for signals.
        from . import signals  # noqa: F401
