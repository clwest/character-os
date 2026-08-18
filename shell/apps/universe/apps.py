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

    def ready(self) -> None:
        """Import signals so ``m2m_changed pre_add`` on
        ``Episode.cast`` is wired at app startup. Mirrors the
        embeddings-app pattern for KnowledgeDocument.spokespeople.
        """
        # noqa: F401 — signals module registers receivers on import
        from . import signals  # noqa: F401
