from django.apps import AppConfig


class UniverseConfig(AppConfig):
    """AppConfig for the Universe substrate.

    App label ``universe`` becomes the FK target string
    ``"universe.Universe"`` on ``Teammate.universe`` and
    ``KnowledgeDocument.universe``. See SESSION 261 /
    ``docs/design/UNIVERSE_SCHEMA_V1.md``.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.universe"
    label = "universe"
    verbose_name = "Universe substrate"
