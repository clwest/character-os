"""Celery tasks for the videos app.

Just one task today — ``poll_video_until_terminal`` — which drives
the fire-then-poll pattern documented in
``docs/design/MEDIA_ENGINE_INTERNAL_API.md`` §"Django-side polling
pattern".

The task is idempotent: re-running it against an already-terminal
``Video`` row is a no-op. Stuck rows (worker died mid-poll) stay in
``rendering`` until either a janitor task re-enqueues them (Phase 3
scope) or the operator retries from the SPA.
"""
from __future__ import annotations

import logging
import time

from celery import shared_task
from django.utils import timezone

from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .models import Video

logger = logging.getLogger(__name__)


# Poll cadence. Mock-mode Runway tasks finish in ~12 s; real-mode
# video generation runs 60-120 s. A 2-second interval is fast enough
# to feel live on the SPA without hammering Runway's task endpoint.
_POLL_INTERVAL_S = 2.0

# Wall-clock deadline. Anything longer than 10 minutes is either a
# Runway outage or a runaway task — give up and persist `failed`.
# Matches Celery's hard time limit minus a safety margin.
_POLL_DEADLINE_S = 10 * 60


@shared_task(
    bind=True,
    name="apps.videos.tasks.poll_video_until_terminal",
    autoretry_for=(MediaEngineError,),
    retry_backoff=True,
    retry_backoff_max=30,
    retry_kwargs={"max_retries": 5},
)
def poll_video_until_terminal(self, video_id: str) -> dict:
    """Poll the media-engine for this video's task until terminal,
    then write the final state back to the ``Video`` row.

    Returns a small status dict for Celery's result backend so
    `celery -A character_os inspect` shows useful summaries; the
    real artefacts (output path, error message, etc.) live on the
    Video row.

    Idempotent — if the row is already terminal we return
    immediately without polling.
    """
    try:
        video = Video.objects.select_related("spokesperson").get(pk=video_id)
    except Video.DoesNotExist:
        logger.warning("poll_video_until_terminal: no Video row id=%s", video_id)
        return {"video_id": video_id, "status": "missing"}

    if video.status in {Video.Status.READY, Video.Status.FAILED}:
        logger.info(
            "poll_video_until_terminal: video=%s already terminal status=%s",
            video_id, video.status,
        )
        return {"video_id": video_id, "status": video.status, "noop": True}

    task_id = video.media_engine_task_id
    if not task_id:
        logger.warning(
            "poll_video_until_terminal: video=%s missing media_engine_task_id; "
            "marking failed",
            video_id,
        )
        _persist_terminal(
            video,
            status=Video.Status.FAILED,
            error_message="no media_engine_task_id set",
        )
        return {"video_id": video_id, "status": "failed", "reason": "no_task_id"}

    deadline = time.time() + _POLL_DEADLINE_S
    last_status = video.status
    last_progress: float | None = None

    with MediaEngineClient() as client:
        while time.time() < deadline:
            poll = client.poll_video(task_id)

            # Surface in-progress updates so the SPA can render a
            # progress bar without each request hitting the media-
            # engine. We only write on transitions (status change or
            # a meaningful progress jump) to keep DB chatter down.
            if (
                poll.status != last_status
                or _progress_moved(last_progress, poll.progress)
            ):
                if poll.status == "rendering" and video.status != Video.Status.RENDERING:
                    video.status = Video.Status.RENDERING
                    video.save(update_fields=["status", "updated_at"])
                last_status = poll.status
                last_progress = poll.progress

            if poll.terminal:
                if poll.succeeded:
                    _persist_terminal(
                        video,
                        status=Video.Status.READY,
                        output_path=poll.output_url or "",
                        duration_seconds=poll.duration_seconds,
                    )
                    logger.info(
                        "poll_video_until_terminal: video=%s READY output=%s",
                        video_id, poll.output_url,
                    )
                    return {
                        "video_id": video_id,
                        "status": "ready",
                        "output_url": poll.output_url,
                        "task_id": task_id,
                    }
                _persist_terminal(
                    video,
                    status=Video.Status.FAILED,
                    error_message=poll.error or f"runway failed: {poll.failure_code or 'unknown'}",
                )
                logger.warning(
                    "poll_video_until_terminal: video=%s FAILED err=%s",
                    video_id, poll.error,
                )
                return {
                    "video_id": video_id,
                    "status": "failed",
                    "error": poll.error,
                    "task_id": task_id,
                }

            time.sleep(_POLL_INTERVAL_S)

    # Deadline tripped without a terminal state — persist failed so
    # the SPA can surface a useful message rather than spinning
    # forever.
    _persist_terminal(
        video,
        status=Video.Status.FAILED,
        error_message=f"polling timed out after {_POLL_DEADLINE_S}s",
    )
    logger.warning(
        "poll_video_until_terminal: video=%s TIMEOUT task=%s",
        video_id, task_id,
    )
    return {
        "video_id": video_id,
        "status": "failed",
        "reason": "timeout",
        "task_id": task_id,
    }


def _progress_moved(prev: float | None, current: float | None) -> bool:
    """Return True iff the progress shifted enough to justify a row
    write. Threshold of 10 % keeps DB load proportional to actual
    progress, not poll cadence."""
    if current is None:
        return False
    if prev is None:
        return True
    return abs(current - prev) >= 0.1


def _persist_terminal(
    video: Video,
    *,
    status: str,
    output_path: str = "",
    duration_seconds: float | None = None,
    error_message: str = "",
) -> None:
    """Single point of persistence for terminal state. Sets
    ``completed_at`` so the SPA can render "rendered N seconds ago"
    captions."""
    video.status = status
    if output_path:
        video.output_path = output_path
    if duration_seconds is not None:
        video.duration_seconds = duration_seconds
    if error_message:
        video.error_message = error_message
    video.completed_at = timezone.now()
    video.save(
        update_fields=[
            "status",
            "output_path",
            "duration_seconds",
            "error_message",
            "completed_at",
            "updated_at",
        ]
    )
