from django.apps import AppConfig


class SpokespeopleConfig(AppConfig):
    # AppConfig class name matches the app label deliberately —
    # both are persistence identifiers preserved unchanged across
    # the Teammate → Teammate class rename (§17.1.b).
    # The Django app label ``spokespeople`` is derived from
    # ``name`` below and appears in every migration dependency
    # tuple (`("spokespeople", "0001_initial")`), the DB table
    # prefix (`spokespeople_spokesperson`), and content types.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.spokespeople"

    def ready(self):
        # Import for side effect — registers post_save signal
        # that syncs personality edits to Runway.
        from . import signals  # noqa: F401
