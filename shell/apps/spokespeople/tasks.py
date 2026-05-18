"""Spokespeople Celery tasks.

Currently houses one task — `sync_personality_to_runway` — fired
by the post-save signal in `signals.py` whenever
`Spokesperson.personality` (W11.y) is edited. Pushes the new
persona to Runway's avatar resource via the media-engine's
`change-personality` endpoint so non-session-create surfaces
(avatar_videos bakes, recipe renders, etc.) inherit the same
voice that the realtime session-create flow already overrides
per session.
"""
from __future__ import annotations

import logging

from celery import shared_task

from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .models import Spokesperson

logger = logging.getLogger(__name__)


@shared_task(
    name="spokespeople.sync_personality_to_runway",
    bind=True,
    max_retries=2,
)
def sync_personality_to_runway(self, spokesperson_id: str) -> dict:
    """Push the current `Spokesperson.personality` to Runway's
    avatar resource.

    Idempotent — Runway PATCH is overwrite semantics. Re-firing on
    the same row twice produces the same end state.

    Returns the structured result from the media-engine
    endpoint so the celery task log captures the outcome.
    Statuses:
    * ``applied`` — Runway PATCH returned 2xx.
    * ``mock_patched`` — running against mock or a mock avatar id;
      no HTTP made.
    * ``pending_avatar`` — spokesperson has no runway_avatar_id
      yet (the next avatar bake will read the personality field
      from the row).
    * ``failed`` — Runway PATCH returned non-2xx OR network error.
    * ``no_avatar`` — same shape as pending_avatar, surfaced from
      the task wrapper before we even call the media-engine.
    * ``empty`` — personality is blank; skip the upstream call.
    * ``not_found`` — spokesperson row vanished between signal
      and task execution.
    * ``upstream_error`` — MediaEngineError caught.
    """
    try:
        sp = Spokesperson.objects.get(pk=spokesperson_id)
    except Spokesperson.DoesNotExist:
        logger.warning(
            "sync_personality_to_runway: spokesperson %s not found",
            spokesperson_id,
        )
        return {"status": "not_found", "spokesperson_id": spokesperson_id}

    if not sp.runway_avatar_id:
        return {"status": "no_avatar", "spokesperson_id": spokesperson_id}

    personality = (sp.personality or "").strip()
    if not personality:
        return {"status": "empty", "spokesperson_id": spokesperson_id}

    try:
        with MediaEngineClient() as client:
            result = client.change_avatar_personality(
                avatar_id=sp.runway_avatar_id,
                personality=personality,
            )
    except MediaEngineError as exc:
        logger.warning(
            "sync_personality_to_runway: media-engine failed "
            "spokesperson=%s err=%s",
            sp.pk, exc,
        )
        # Retry only transient-looking errors.
        msg = str(exc).lower()
        retryable = any(
            tok in msg
            for tok in ("timeout", "ratelimit", "rate_limit",
                        "connection", "apiconnection")
        )
        if retryable and self.request.retries < self.max_retries:
            raise self.retry(
                exc=exc, countdown=2 ** self.request.retries,
            )
        return {
            "status": "upstream_error",
            "spokesperson_id": spokesperson_id,
            "error": str(exc)[:200],
        }

    logger.info(
        "sync_personality_to_runway: spokesperson=%s avatar=%s status=%s",
        sp.pk, sp.runway_avatar_id, result.get("status"),
    )
    return result
