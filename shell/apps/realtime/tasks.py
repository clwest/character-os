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


def capture_transcript(session: RealtimeSession) -> dict:
    """Fetch the transcript snapshot for ``session`` and
    persist it as an ``Asset(TRANSCRIPT)`` row.

    Shared helper extracted from R5's Celery task body in
    SESSION 152 (R7.3) so the same code path serves both:

    * **R5's `fetch_transcript_for_session`** — fired on
      session-end via the broker's `_end_session`. Captures
      the final transcript when the session terminates
      naturally.
    * **R7.3's `attach_memory`** — fired mid-session by the
      avatar's LLM. Captures a partial transcript snapshot
      while the session is still live, so the next
      session's R6 memory projection can reference it.

    Idempotent: re-running on a session that already has a
    `transcript_asset` deletes the old one + creates a fresh
    one with the latest content. The shape is what makes
    Q-r-8 (cross-session tool side effects) safe — last-
    write-wins, no merge logic, no race conditions beyond
    the standard "media-engine fetched stale data" risk.

    Args:
        session: the `RealtimeSession` to capture. Any
            status — R5 calls on ENDED, R7.3 calls on READY.

    Returns:
        ``{session_id, asset_id?, status, chars}`` where
        ``status`` is one of:
        ``persisted`` | ``empty`` | ``upstream_error``.

    Raises:
        Never. ``MediaEngineError`` is caught + returned as
        ``upstream_error`` status; callers (R5's Celery
        wrapper handles its own retry) decide what to do.
    """
    if not session.provider_session_id:
        logger.info(
            "capture_transcript: session=%s has no "
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
            "capture_transcript: media-engine failed session=%s: %s",
            session.id, exc,
        )
        return {
            "session_id": str(session.id),
            "asset_id": None,
            "status": "upstream_error",
            "chars": 0,
            "error": str(exc)[:200],
            "_retryable": _is_retryable(exc),  # caller can use
        }

    if not result.text.strip():
        logger.info(
            "capture_transcript: empty transcript session=%s "
            "(runway hasn't recorded yet?)",
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
                "capture_transcript: stale-asset cleanup failed "
                "session=%s asset=%s",
                session.id, session.transcript_asset_id,
            )

    inline_content = result.text
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
        "capture_transcript: persisted session=%s asset=%s "
        "chars=%d turns=%d",
        session.id, asset.id, len(inline_content), len(result.segments),
    )
    return {
        "session_id": str(session.id),
        "asset_id": str(asset.id),
        "status": "persisted",
        "chars": len(inline_content),
    }


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

    Celery task wrapper around `capture_transcript`. Adds
    session-row resolution + retry logic for transient
    upstream errors.

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

    result = capture_transcript(session)
    # Honor the retry signal extracted from the helper —
    # only the Celery wrapper has retry context, so the
    # helper just reports retryability.
    if (
        result["status"] == "upstream_error"
        and result.pop("_retryable", False)
        and self.request.retries < self.max_retries
    ):
        raise self.retry(
            exc=MediaEngineError(result.get("error", "upstream error")),
            countdown=2 ** self.request.retries,
        )
    # Strip the internal flag if it survived (non-retryable
    # path or retries exhausted).
    result.pop("_retryable", None)
    return result


def _is_retryable(exc: MediaEngineError) -> bool:
    """Same shape as embed_document's retry filter — only
    network-y errors get retried, not 4xx config bugs."""
    msg = str(exc).lower()
    return any(token in msg for token in (
        "timeout", "ratelimit", "rate_limit", "connection", "apiconnection",
    ))


# ---- R7.2 — async tool execution -------------------------------


@shared_task(
    name="realtime.execute_tool_invocation",
    bind=True,
    max_retries=0,  # tool executors handle their own retries
)
def execute_tool_invocation(self, invocation_id: str) -> dict:
    """Generic Celery task that runs an async tool's executor.

    R7.2 — the dispatcher enqueues this task for any tool
    registered with ``is_async=True``. The task:

    1. Resolves the ``RealtimeToolInvocation`` row + the
       tool spec from the registry.
    2. Calls the executor with ``(session, args)``.
    3. Updates the audit row to SUCCEEDED (linking any
       ``composition_id`` / ``asset_id`` the executor
       returned) or FAILED with the error message.

    Idempotent on terminal rows: re-running on an already-
    succeeded / failed / rejected invocation no-ops and
    returns the current state.

    The task does NOT raise — exceptions are caught and
    recorded on the audit row so the SPA can render the
    failure cleanly.

    Args:
        invocation_id: ``RealtimeToolInvocation.pk``.

    Returns:
        ``{invocation_id, status, ...}`` — telemetry shape.
    """
    # Lazy imports — keep this module free of the realtime
    # tools package at import time.
    from .models import RealtimeToolInvocation
    from .tools import get_tool

    try:
        invocation = (
            RealtimeToolInvocation.objects
            .select_related("session", "session__workspace", "session__spokesperson")
            .get(pk=invocation_id)
        )
    except RealtimeToolInvocation.DoesNotExist:
        logger.warning(
            "execute_tool_invocation: invocation=%s not found",
            invocation_id,
        )
        return {
            "invocation_id": invocation_id,
            "status": "not_found",
        }

    # Idempotency — terminal states stay put.
    if invocation.status in (
        RealtimeToolInvocation.Status.SUCCEEDED,
        RealtimeToolInvocation.Status.FAILED,
        RealtimeToolInvocation.Status.REJECTED,
    ):
        return {
            "invocation_id": str(invocation.id),
            "status": invocation.status,
            "note": "already terminal",
        }

    try:
        spec = get_tool(invocation.tool_name)
    except KeyError:
        # Tool was de-registered between dispatch and
        # execution. Record FAILED.
        _mark_failed(
            invocation,
            f"tool {invocation.tool_name!r} no longer registered",
        )
        return {
            "invocation_id": str(invocation.id),
            "status": "failed",
            "reason": "unknown_tool",
        }

    try:
        result = spec.executor(invocation.session, invocation.args or {})
    except Exception as exc:
        logger.exception(
            "execute_tool_invocation: executor raised tool=%s "
            "invocation=%s",
            spec.name, invocation.id,
        )
        _mark_failed(invocation, str(exc)[:500])
        return {
            "invocation_id": str(invocation.id),
            "status": "failed",
            "error": str(exc)[:200],
        }

    # Link produced_composition / produced_asset if the
    # executor returned ids. Cross-workspace refs are
    # rejected by the model's clean() guard (existing R1).
    update_fields = ["status", "completed_at"]
    if isinstance(result, dict):
        comp_id = result.get("composition_id")
        if comp_id:
            try:
                from apps.compositions.models import Composition

                invocation.produced_composition = Composition.objects.get(
                    pk=comp_id,
                )
                update_fields.append("produced_composition")
            except Composition.DoesNotExist:
                pass
        asset_id = result.get("asset_id")
        if asset_id:
            try:
                from apps.compositions.models import Asset

                invocation.produced_asset = Asset.objects.get(pk=asset_id)
                update_fields.append("produced_asset")
            except Asset.DoesNotExist:
                pass

    invocation.status = RealtimeToolInvocation.Status.SUCCEEDED
    invocation.completed_at = timezone.now()
    invocation.save(update_fields=update_fields)

    logger.info(
        "execute_tool_invocation: succeeded tool=%s invocation=%s",
        spec.name, invocation.id,
    )
    return {
        "invocation_id": str(invocation.id),
        "status": "succeeded",
        "result": result if isinstance(result, dict) else {},
    }


def _mark_failed(invocation, message: str) -> None:
    """Helper — flip an invocation to FAILED with the given
    error message + completed_at stamp."""
    invocation.status = invocation.Status.FAILED
    invocation.error_message = message
    invocation.completed_at = timezone.now()
    invocation.save(update_fields=[
        "status", "error_message", "completed_at",
    ])
