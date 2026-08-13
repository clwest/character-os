from django.apps import AppConfig


class IdentityConfig(AppConfig):
    # Canonical Identity substrate app (SESSION 241 / §19 Step 2).
    # Distinct from the customer-facing "identity page" fields that
    # live on ``apps.spokespeople.Teammate`` — those capture the
    # operator's presentation-preference text; this app owns the
    # ratified internal substrate (``CharacterIdentity``,
    # ``CharacterIdentityVersion``, references, generation records,
    # approved-representation bundles) per
    # ``docs/design/visual/portrait_qualification/CANONICAL_IDENTITY_CONTRACT_V1.md``.
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"

    def ready(self):
        # Register the cross-workspace ``pre_save`` signals so raw
        # ``.save()`` paths run the same isolation check that
        # ``full_clean()`` runs (§7.5 defense in depth).
        from . import signals  # noqa: F401
