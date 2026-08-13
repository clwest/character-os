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
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.compositions.models import Composition, CompositionStatus

from .models import PublishBundle, PublishVariant

logger = logging.getLogger(__name__)


# B14.3 — composition statuses we treat as terminal for the
# variant flip. COMPLETED → variant COMPLETED; FAILED /
# PARTIAL → variant FAILED with the composition's
# error_message captured.
_TERMINAL_SUCCESS = {CompositionStatus.COMPLETED}
_TERMINAL_FAILURE = {
    CompositionStatus.FAILED,
    CompositionStatus.PARTIAL,
}


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


@receiver(post_save, sender=Composition)
def flip_variant_on_composition_completion(
    sender,
    instance: Composition,
    update_fields=None,
    created: bool = False,
    **kwargs,
) -> None:
    """B14.3 — when a publish_variant composition reaches a
    terminal status, flip the linked variant + roll up the
    bundle.

    Mirrors apps.campaigns.signals' equivalent receiver +
    apps.transcripts.signals'. Cheap filter (update_fields +
    status check) before the lookup query so vanilla
    composition saves don't pay.
    """
    if created:
        return

    if update_fields is not None and "status" not in update_fields:
        return

    is_success = instance.status in _TERMINAL_SUCCESS
    is_failure = instance.status in _TERMINAL_FAILURE
    if not (is_success or is_failure):
        return

    from .services import rollup_bundle_status

    variants = list(
        PublishVariant.objects
        .filter(produced_composition=instance)
        # Skip already-terminal rows — idempotent.
        .exclude(status__in=[
            PublishVariant.Status.COMPLETED,
            PublishVariant.Status.FAILED,
        ])
        .select_related("bundle")
    )
    if not variants:
        return

    new_status = (
        PublishVariant.Status.COMPLETED
        if is_success
        else PublishVariant.Status.FAILED
    )
    error_message = (
        "" if is_success else (instance.error_message or "")[:500]
    )

    seen_bundles = set()
    for variant in variants:
        variant.status = new_status
        if not is_success:
            variant.error_message = error_message
        variant.save(update_fields=[
            "status", "error_message", "updated_at",
        ])
        seen_bundles.add(variant.bundle_id)

    for bundle in PublishBundle.objects.filter(pk__in=seen_bundles):
        flipped = rollup_bundle_status(bundle)
        if flipped:
            logger.info(
                "publish_bundle %s rolled up to %s after "
                "composition %s terminal",
                bundle.pk, bundle.status, instance.pk,
            )
