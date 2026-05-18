"""Spokesperson signal handlers.

Currently one handler — `_sync_personality_on_save` — fires the
`sync_personality_to_runway` Celery task when an existing
spokesperson's `personality` field changes. Captures the old
value in a `pre_save` hook so the `post_save` hook can detect
the change without an extra DB read.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Spokesperson

logger = logging.getLogger(__name__)

# Stashed on the instance during pre_save so post_save can
# compare. Underscore prefix keeps it out of any serializer that
# enumerates model fields.
_OLD_PERSONALITY_ATTR = "_old_personality_for_sync"


@receiver(pre_save, sender=Spokesperson)
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
        old = Spokesperson.objects.only("personality").get(pk=instance.pk)
        setattr(instance, _OLD_PERSONALITY_ATTR, old.personality or "")
    except Spokesperson.DoesNotExist:
        setattr(instance, _OLD_PERSONALITY_ATTR, "")


@receiver(post_save, sender=Spokesperson)
def _sync_personality_on_save(
    sender, instance, created, update_fields, **kwargs,
):
    """When an existing row's `personality` changes, enqueue the
    Runway-side push.

    Fires only when:
    * Row already existed (skip initial create — the next avatar
      bake will read personality from the row).
    * Spokesperson has a `runway_avatar_id` (otherwise the task
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

    sp_id = str(instance.pk)
    transaction.on_commit(
        lambda: sync_personality_to_runway.delay(sp_id)
    )
    logger.info(
        "spokesperson %s personality changed — enqueued runway sync",
        sp_id,
    )
