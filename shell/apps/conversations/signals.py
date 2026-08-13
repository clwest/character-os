"""Signal wiring for the conversation pipeline.

SESSION 145 / K8 — message create → embedding fire. When a
``ConversationMessage`` row is saved for the first time, kick
the K3-style embedding task asynchronously so subsequent
``retrieve_for_thread`` calls can pull this turn back into
context.

We only fire on **create**, not update — re-embedding on every
edit would burn tokens for no reason. If a message edit
arrives (post-v1) the caller can explicitly enqueue
``embed_message`` again; the task is idempotent (deletes prior
chunks before re-embedding).

The signal is intentionally fire-and-forget — Celery handles
retries on transient failures, permanent failures land in the
task's return shape for telemetry.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ConversationMessage
from .tasks import embed_message

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ConversationMessage)
def enqueue_message_embedding(sender, instance, created, raw, **kwargs):
    """Fire `embed_message` on ConversationMessage creation.

    Skips:
      * Loaded fixtures (``raw=True``) — same shape as the
        K1 / billing `raw=True` guards in `accounts.signals`.
      * Empty content — the task handles this safely too,
        but no point queueing work that'll no-op.
      * Updates (``created=False``) — embedding cost is paid
        once per message; edit-then-reembed is a v1.1
        concern.
    """
    if raw:
        return
    if not created:
        return
    if not (instance.content or "").strip():
        return
    try:
        embed_message.delay(str(instance.pk))
    except Exception as exc:
        # If the Celery broker is unreachable we don't want
        # message creation itself to 500. Log + continue —
        # retrieval will simply miss this turn until a
        # follow-up enqueue lands.
        logger.warning(
            "enqueue_message_embedding: broker enqueue failed msg=%s err=%s",
            instance.pk, exc,
        )
