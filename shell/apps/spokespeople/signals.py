"""Teammate signal handlers.

Two handlers today:

* ``_sync_personality_on_save`` — fires the
  ``sync_personality_to_runway`` Celery task when an existing
  teammate's ``personality`` field changes. Captures the old
  value in a ``pre_save`` hook so the ``post_save`` hook can detect
  the change without an extra DB read.

* SESSION 275 — ``_archive_orphaned_kds_on_teammate_delete`` —
  fires on ``pre_delete`` and archives any ``KnowledgeDocument``
  where this teammate is the sole spokesperson, so that Django's
  CASCADE on the ``KnowledgeDocumentSpokesperson`` through-row does
  not silently promote the surviving KD from character-specific
  to workspace- or Universe-broadcast. Load-bearing invariant:
  ``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md``
  §23 (no removal action may broaden the audience of surviving
  knowledge).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Count
from django.db.models.signals import post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Teammate

logger = logging.getLogger(__name__)

# Stashed on the instance during pre_save so post_save can
# compare. Underscore prefix keeps it out of any serializer that
# enumerates model fields.
_OLD_PERSONALITY_ATTR = "_old_personality_for_sync"


@receiver(pre_save, sender=Teammate)
def _capture_old_personality(sender, instance, **kwargs):
    """Stash the pre-save personality value on the instance so the
    post_save handler can detect a real change without a separate
    DB read."""
    if instance.pk is None:
        # New row — nothing to compare against; post_save will
        # skip (created=True branch).
        setattr(instance, _OLD_PERSONALITY_ATTR, "")
        return
    try:
        old = Teammate.objects.only("personality").get(pk=instance.pk)
        setattr(instance, _OLD_PERSONALITY_ATTR, old.personality or "")
    except Teammate.DoesNotExist:
        setattr(instance, _OLD_PERSONALITY_ATTR, "")


@receiver(post_save, sender=Teammate)
def _sync_personality_on_save(
    sender, instance, created, update_fields, **kwargs,
):
    """When an existing row's `personality` changes, enqueue the
    Runway-side push.

    Fires only when:
    * Row already existed (skip initial create — the next avatar
      bake will read personality from the row).
    * Teammate has a `runway_avatar_id` (otherwise the task
      would short-circuit anyway, but skip the enqueue for log
      hygiene).
    * The new personality differs from the captured pre-save
      value AND is non-empty.
    * `update_fields` either includes `personality` or is None
      (full save).

    The task is enqueued via `transaction.on_commit` so the
    Celery worker doesn't read a half-committed row.
    """
    if created:
        return
    if not instance.runway_avatar_id:
        return
    new = (instance.personality or "").strip()
    if not new:
        return
    if update_fields is not None and "personality" not in update_fields:
        return
    old = getattr(instance, _OLD_PERSONALITY_ATTR, "")
    if (old or "").strip() == new:
        return

    # Lazy import — avoids tasks.py loading at app-import time
    # which would pull MediaEngineClient + httpx into the
    # spokespeople boot path.
    from .tasks import sync_personality_to_runway

    tm_id = str(instance.pk)
    transaction.on_commit(
        lambda: sync_personality_to_runway.delay(tm_id)
    )
    logger.info(
        "teammate %s personality changed — enqueued runway sync",
        tm_id,
    )


# SESSION 275 — orphan-archive coordination attribute name.
# Set on the Teammate instance by pre_delete (which can still see
# the M2M through-rows) and read by post_delete (which runs after
# the CASCADE dropped them). Underscore-prefixed so no serializer
# accidentally enumerates it.
_ORPHAN_CANDIDATE_ATTR = "_session275_orphan_candidate_kd_ids"


@receiver(pre_delete, sender=Teammate)
def _stash_kd_membership_for_orphan_check(sender, instance, **kwargs):
    """SESSION 275 — half 1 of the audience-invariant enforcement.

    Before Django's cascade removes the ``KnowledgeDocumentSpokesperson``
    through-row(s) referencing this teammate, snapshot the list of
    KnowledgeDocuments this teammate is currently a spokesperson of.
    ``post_delete`` (below) uses that snapshot to identify which KDs
    became orphaned by this delete AND archive them.

    We can't do the archive here because of the bulk-delete case: when
    ``QuerySet.delete()`` removes multiple teammates in one go, Django
    fires all pre_delete signals BEFORE any DELETE SQL runs. At
    pre_delete time each teammate's M2M state still counts the OTHER
    doomed teammates as spokespeople — a KD with ``spokespeople=
    {A, B}`` where both are being deleted looks "still has 2 members"
    to A's pre_delete AND to B's pre_delete. Only after the SQL
    executes does the true post-cascade M2M state become observable.

    Load-bearing distinction (§26-§27): we snapshot only KDs where
    THIS teammate is currently in the M2M. Intentionally born-empty
    KDs (Class A / Class C canon) — where this teammate was never a
    spokesperson — are never in the snapshot, and post_delete never
    touches them.

    Fires for both single ``instance.delete()`` and ``QuerySet.delete()``
    paths (Django's Collector fires pre_delete per row in both). Raw
    SQL bypasses; accepted trade-off since admin + management + tests
    all go through the ORM.
    """
    # Lazy import — mirror the pattern used above to avoid pulling
    # embeddings into the spokespeople boot path.
    from apps.embeddings.models import KnowledgeDocumentSpokesperson

    kd_ids = list(
        KnowledgeDocumentSpokesperson.objects.filter(
            teammate=instance,
        ).values_list("knowledgedocument_id", flat=True)
    )
    setattr(instance, _ORPHAN_CANDIDATE_ATTR, kd_ids)


@receiver(post_delete, sender=Teammate)
def _archive_orphaned_kds_on_teammate_delete(sender, instance, **kwargs):
    """SESSION 275 — half 2 of the audience-invariant enforcement.

    After Django's cascade has dropped the through-rows, check each
    KD from the pre_delete snapshot: any KD whose spokespeople M2M
    is now empty AND is_active is still True is an orphan produced
    by this delete (single- or bulk-) — archive it.

    The is_active=True filter is load-bearing for the bulk-delete
    case: when two teammates share a KD and are both deleted, both
    post_delete handlers see the KD as empty. The first sets
    is_active=False; the second skips (already inactive), preventing
    duplicate stamps and preserving the first handler's reason
    stamp.

    The bulk ``update()`` runs inside the same transaction as the
    teammate delete (Django wraps ``Collector.delete()`` in
    ``mark_for_rollback_on_error``) — a raise here rolls the whole
    delete back. Test 9 in ``test_delete_orphan_archive.py`` locks
    the atomicity contract.
    """
    kd_ids = getattr(instance, _ORPHAN_CANDIDATE_ATTR, None)
    if not kd_ids:
        return

    # Lazy imports — same reason as pre_delete stash.
    from apps.embeddings.models import DeactivationReason, KnowledgeDocument

    orphan_ids = list(
        KnowledgeDocument.objects
        .filter(pk__in=kd_ids, is_active=True)
        .annotate(sp_count=Count("spokespeople"))
        .filter(sp_count=0)
        .values_list("pk", flat=True)
    )
    if not orphan_ids:
        return

    KnowledgeDocument.objects.filter(pk__in=orphan_ids).update(
        is_active=False,
        deactivated_reason=DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE,
        updated_at=timezone.now(),
    )
    logger.info(
        "session-275: teammate=%s archived %d orphan KD(s): %s",
        instance.pk,
        len(orphan_ids),
        [str(pk) for pk in orphan_ids],
    )
