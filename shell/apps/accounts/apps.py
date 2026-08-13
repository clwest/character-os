from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self) -> None:
        # Importing the signals module connects its @receiver handlers.
        from . import signals  # noqa: F401
