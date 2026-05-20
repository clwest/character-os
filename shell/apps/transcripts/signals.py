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
from django.db.models.signals import pre_save
from django.dispatch import receiver

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
