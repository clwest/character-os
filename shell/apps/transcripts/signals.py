"""Cross-workspace validation for the transcript miner arc.

B1.2 (SESSION 202). Mirrors ``apps.realtime.signals`` shape.
``clean()`` catches the form / ``full_clean()`` paths; this
signal catches the raw ``.save()`` path which doesn't run
``clean()`` by default. Together: defense in depth — every
persistence path runs the same isolation check.

The leak shape we eliminate by construction:
* A ``TranscriptHighlight`` whose ``source_transcript`` or
  ``produced_composition`` belongs to a different workspace
  than the highlight's own ``workspace`` FK.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.compositions.models import Composition

from .models import TranscriptHighlight

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=TranscriptHighlight)
def reject_cross_workspace_highlight_references(
    sender,
    instance: TranscriptHighlight,
    **kwargs,
) -> None:
    """Veto a TranscriptHighlight whose linked rows live in
    another workspace.

    Skips when an update touches none of the FK fields —
    state transitions (status / decided_at / rejection_reason)
    leave the reference shape unchanged.
    """
    if not instance.workspace_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {
            "workspace",
            "source_transcript",
            "produced_composition",
        }
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        # Re-raise as-is — ``clean()`` carries the specific
        # field-level message.
        raise


@receiver(post_save, sender=Composition)
def mark_highlight_rendered_on_composition_completion(
    sender,
    instance: Composition,
    update_fields=None,
    created: bool = False,
    **kwargs,
) -> None:
    """B1.4 — flip APPROVED highlights to RENDERED when their
    linked composition reaches the COMPLETED state.

    Cheap: filters update_fields first so we only run the
    lookup query on the specific save that transitions status.
    Idempotent: a composition that re-saves with status
    COMPLETED for any reason produces an
    ``update(...).update(status=RENDERED)`` that does nothing
    if the row is already RENDERED.
    """
    if created:
        # First save of a Composition is at status DRAFT —
        # never the completion transition.
        return

    # Filter by update_fields when present. The runner saves
    # the completion transition with
    # update_fields=["final_asset", "status", "updated_at"];
    # other state transitions (DRAFT → QUEUED → RUNNING) also
    # update status, so we additionally check the new value.
    if update_fields is not None and "status" not in update_fields:
        return

    if instance.status != "completed":
        return

    # Lazy reverse lookup — only the highlights that hold this
    # composition's id will match. The
    # ``produced_composition`` index isn't there in v1 but the
    # PK lookup is fast enough at the v1 row counts.
    updated = TranscriptHighlight.objects.filter(
        produced_composition=instance,
        status=TranscriptHighlight.Status.APPROVED,
    ).update(status=TranscriptHighlight.Status.RENDERED)
    if updated:
        logger.info(
            "transcript_highlights: marked %d highlight(s) RENDERED "
            "for composition=%s",
            updated, instance.pk,
        )
