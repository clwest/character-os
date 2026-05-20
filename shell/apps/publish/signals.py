"""Cross-workspace validation for the D-arc / B-14 publish-bundle
arc.

B14.2 (SESSION 205). Mirrors apps.transcripts.signals +
apps.campaigns.signals. ``clean()`` catches form +
``full_clean()`` paths; this signal catches the raw
``.save()`` path that doesn't run clean() by default.

The leak shapes eliminated by construction:
* PublishBundle whose ``source_clip`` belongs to a different
  workspace.
* PublishVariant whose ``produced_composition`` belongs to a
  different workspace than its bundle.workspace.

B14.3 will add a post_save Composition receiver here that
flips variant status + rolls up the bundle.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import PublishBundle, PublishVariant

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PublishBundle)
def reject_cross_workspace_bundle_refs(
    sender,
    instance: PublishBundle,
    **kwargs,
) -> None:
    """Veto a bundle whose source_clip lives in another
    workspace.

    Skips state-only updates (status / launched_at /
    completed_at).
    """
    if not instance.workspace_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"workspace", "source_clip"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise


@receiver(pre_save, sender=PublishVariant)
def reject_cross_workspace_variant_refs(
    sender,
    instance: PublishVariant,
    **kwargs,
) -> None:
    """Veto a variant whose produced_composition lives in
    another workspace.

    Skips state-only updates (status / error_message).
    """
    if not instance.bundle_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"bundle", "produced_composition"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise
