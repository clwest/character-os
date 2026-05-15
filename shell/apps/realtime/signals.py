"""Cross-workspace validation for the realtime arc.

R1 (SESSION 146). Mirrors V1's signals.py pattern. The
``clean()`` methods on ``RealtimeSession`` and
``RealtimeToolInvocation`` catch the form / explicit
``full_clean()`` paths. These signals catch the raw
``.save()`` path which does not run ``clean()`` by default.
Together: defense in depth — every persistence path runs
the same workspace-isolation check.

The leak shape we eliminate by construction:
* A RealtimeSession whose spokesperson, thread, or
  transcript_asset belongs to a different workspace.
* A RealtimeToolInvocation whose produced_asset or
  produced_composition belongs to a different workspace.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import RealtimeSession, RealtimeToolInvocation

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=RealtimeSession)
def reject_cross_workspace_session_references(
    sender,
    instance: RealtimeSession,
    **kwargs,
) -> None:
    """Veto a RealtimeSession whose linked rows live in
    another workspace.

    Skips when an update touches none of the FK fields —
    state transitions (status / timestamps / cost) leave the
    reference shape unchanged.
    """
    if not instance.workspace_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"spokesperson", "thread", "transcript_asset"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        # Re-raise as-is — `clean()` carries the specific
        # field-level message.
        raise


@receiver(pre_save, sender=RealtimeToolInvocation)
def reject_cross_workspace_tool_invocation_references(
    sender,
    instance: RealtimeToolInvocation,
    **kwargs,
) -> None:
    """Veto a RealtimeToolInvocation whose produced asset or
    composition belongs to a different workspace.

    Skips state-only updates (status / error_message /
    completed_at).
    """
    if not instance.session_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"produced_asset", "produced_composition"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise
