"""Cross-app sync from Composition → legacy Video.

SESSION 143 / V6. The backwards-compat shim that keeps the
legacy ``/api/videos/`` surface stable while the underlying
work runs through the V0+ composition arc.

When ``apps.compositions.tasks.execute_composition`` transitions
a Composition to a terminal status (COMPLETED / FAILED /
PARTIAL), this signal copies the relevant fields back to the
linked ``Video`` row:

* COMPLETED → ``Video.status='ready'``, ``output_path``,
  ``duration_seconds``, ``completed_at``, ``knowledge_chunk_ids``
  (when the underlying primitive recorded any).
* FAILED → ``Video.status='failed'`` + composition's
  ``error_message`` truncated.
* PARTIAL → ``Video.status='failed'`` with a
  ``partial completion`` marker prefix. The legacy enum has
  no half-success state, so we collapse to failed for the
  SPA's purposes; the Composition row preserves the full
  partial-success trail.

The signal is idempotent — a second post_save on an
already-terminal Composition is a no-op once the linked Video
is already at the same status.

### Why a signal, not a Celery callback

The V2 runtime is intentionally unaware of legacy callers. Adding
a `video_set` lookup inside ``execute_composition`` would make
the runtime know about the videos app — backward dependency we
want to avoid. The signal pattern keeps the dependency one-way
(videos depends on compositions, never the reverse).
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.compositions.models import Composition, CompositionStatus

from .models import Video

logger = logging.getLogger(__name__)


# Composition statuses that should trigger a Video sync.
_TERMINAL_COMP_STATUSES = {
    CompositionStatus.COMPLETED,
    CompositionStatus.FAILED,
    CompositionStatus.PARTIAL,
}


@receiver(post_save, sender=Composition)
def sync_video_from_composition(
    sender,
    instance: Composition,
    **kwargs,
) -> None:
    """Sync the legacy ``Video`` row from its parent
    ``Composition`` whenever the composition reaches a terminal
    state.

    The cheap branches:
      * Non-terminal composition → return early (most saves are
        intermediate state-machine updates).
      * Composition with no linked Video → return early (V6
        only wraps SPOKESPERSON_AD; other kinds fly free).
      * Video already at the right terminal status → return
        (idempotent — re-runs of the signal don't double-write).
    """
    if instance.status not in _TERMINAL_COMP_STATUSES:
        return

    video = (
        Video.objects.filter(composition=instance)
        .select_related("composition")
        .first()
    )
    if video is None:
        return

    # Aggregate the knowledge chunk ids from the speech primitive's
    # output asset source_spec — preserves K6's audit semantics on
    # the Video row even though the synthesis ran inside V3's
    # GenerateAvatarSpeechPrimitive rather than in views.py.
    chunk_ids: list[str] = []
    for step in instance.steps.all().order_by("position"):
        asset = step.output_asset
        if asset is None:
            continue
        spec_chunk_ids = asset.source_spec.get("knowledge_chunk_ids")
        if isinstance(spec_chunk_ids, list):
            chunk_ids.extend(str(c) for c in spec_chunk_ids)

    update_fields: list[str] = []

    if instance.status == CompositionStatus.COMPLETED:
        if video.status == Video.Status.READY:
            return  # already synced
        if instance.final_asset is not None:
            video.output_path = instance.final_asset.file_path or ""
            if instance.final_asset.duration_ms is not None:
                video.duration_seconds = instance.final_asset.duration_ms / 1000.0
                update_fields.append("duration_seconds")
            update_fields.append("output_path")
        video.status = Video.Status.READY
        video.error_message = ""
        video.completed_at = timezone.now()
        update_fields.extend(["status", "error_message", "completed_at"])

    elif instance.status == CompositionStatus.FAILED:
        if video.status == Video.Status.FAILED and video.error_message:
            return  # already synced
        video.status = Video.Status.FAILED
        video.error_message = (instance.error_message or "composition failed")[:500]
        video.completed_at = timezone.now()
        update_fields.extend(["status", "error_message", "completed_at"])

    elif instance.status == CompositionStatus.PARTIAL:
        if video.status == Video.Status.FAILED and "partial completion" in video.error_message:
            return  # already synced
        video.status = Video.Status.FAILED  # legacy has no PARTIAL
        video.error_message = (
            f"partial completion: {instance.error_message or 'one or more steps failed'}"
        )[:500]
        video.completed_at = timezone.now()
        update_fields.extend(["status", "error_message", "completed_at"])

    if chunk_ids and video.knowledge_chunk_ids != chunk_ids:
        video.knowledge_chunk_ids = chunk_ids
        update_fields.append("knowledge_chunk_ids")

    if update_fields:
        update_fields.append("updated_at")
        video.save(update_fields=update_fields)
        logger.info(
            "v6 sync video=%s composition=%s -> status=%s",
            video.pk, instance.pk, video.status,
        )
