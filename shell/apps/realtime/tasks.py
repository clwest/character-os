"""Celery tasks for the realtime arc.

SESSION 146 / R5 — `fetch_transcript_for_session`. Fires
after a `RealtimeSession` ends:
1. Pulls the transcript from media-engine via
   `realtime_session_fetch_transcript`.
2. Persists the text + segments as an
   ``Asset(asset_type=TRANSCRIPT)`` row in the session's
   workspace.
3. Wires the Asset to ``RealtimeSession.transcript_asset``.

Best-effort. Failures log + leave the session.transcript_asset
unset; operator can re-trigger via admin or wait for the
empty-transcript case to clear when Runway records the
conversation.

Idempotent: re-running on a session that already has a
transcript_asset re-uses the existing one (deletes the old
asset + creates a fresh one with the latest content).
"""
from __future__ import annotations

import json
import logging

from celery import shared_task
from django.utils import timezone

from apps.compositions.models import Asset, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .models import RealtimeSession

logger = logging.getLogger(__name__)


@shared_task(
    name="realtime.fetch_transcript_for_session",
    bind=True,
    max_retries=2,
)
def fetch_transcript_for_session(
    self,
    session_id: str,
) -> dict:
    """Pull the transcript from media-engine and persist
    it as an Asset(TRANSCRIPT) on the session.

    Args:
        session_id: ``RealtimeSession.pk``.

    Returns:
        ``{session_id, asset_id?, status, chars}`` —
        useful for telemetry. ``status`` is one of:
        ``persisted`` | ``empty`` | ``not_found`` |
        ``upstream_error``.
    """
    try:
        session = RealtimeSession.objects.select_related(
            "workspace",
        ).get(pk=session_id)
    except RealtimeSession.DoesNotExist:
        logger.warning(
            "fetch_transcript_for_session: session=%s not found",
            session_id,
        )
        return {
            "session_id": session_id,
            "asset_id": None,
            "status": "not_found",
            "chars": 0,
        }

    if not session.provider_session_id:
        logger.info(
            "fetch_transcript_for_session: session=%s has no "
            "provider_session_id — skipping",
            session.id,
        )
        return {
            "session_id": str(session.id),
            "asset_id": None,
            "status": "empty",
            "chars": 0,
        }

    try:
        with MediaEngineClient() as client:
            result = client.realtime_session_fetch_transcript(
                session.provider_session_id, provider=session.provider,
            )
    except MediaEngineError as exc:
        logger.warning(
            "fetch_transcript_for_session: media-engine failed "
            "session=%s: %s",
            session.id, exc,
        )
        if (
            self.request.retries < self.max_retries
            and _is_retryable(exc)
        ):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        return {
            "session_id": str(session.id),
            "asset_id": None,
            "status": "upstream_error",
            "chars": 0,
            "error": str(exc)[:200],
        }

    if not result.text.strip():
        logger.info(
            "fetch_transcript_for_session: empty transcript "
            "session=%s (runway hasn't recorded yet?)",
            session.id,
        )
        return {
            "session_id": str(session.id),
            "asset_id": None,
            "status": "empty",
            "chars": 0,
        }

    # Idempotency — if the session already has a
    # transcript_asset, replace it with the fresh one. The
    # old asset gets dropped (transcript Assets aren't
    # referenced by Compositions; safe to delete).
    if session.transcript_asset_id:
        try:
            Asset.objects.filter(pk=session.transcript_asset_id).delete()
        except Exception:  # pragma: no cover — defensive
            logger.exception(
                "fetch_transcript_for_session: stale-asset cleanup "
                "failed session=%s asset=%s",
                session.id, session.transcript_asset_id,
            )

    inline_content = result.text
    # Stash segments in source_spec for provenance (the
    # structured per-turn shape is useful for downstream
    # tooling — R6 summary, R8 SPA playback).
    source_spec = {
        "primitive_kind": "realtime_transcript",
        "session_id": str(session.id),
        "provider_session_id": session.provider_session_id,
        "provider": session.provider,
        "segments": result.segments,
        "fetched_at": timezone.now().isoformat(),
        "mock_mode": result.mock_mode,
    }

    asset = Asset.objects.create(
        workspace=session.workspace,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content=inline_content,
        source_spec=source_spec,
        mime_type="text/plain",
        size_bytes=len(inline_content.encode("utf-8")),
    )
    session.transcript_asset = asset
    session.save(update_fields=["transcript_asset", "updated_at"])

    logger.info(
        "fetch_transcript_for_session: persisted session=%s "
        "asset=%s chars=%d turns=%d",
        session.id, asset.id, len(inline_content), len(result.segments),
    )
    return {
        "session_id": str(session.id),
        "asset_id": str(asset.id),
        "status": "persisted",
        "chars": len(inline_content),
    }


def _is_retryable(exc: MediaEngineError) -> bool:
    """Same shape as embed_document's retry filter — only
    network-y errors get retried, not 4xx config bugs."""
    msg = str(exc).lower()
    return any(token in msg for token in (
        "timeout", "ratelimit", "rate_limit", "connection", "apiconnection",
    ))
