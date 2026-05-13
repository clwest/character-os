"""End-to-end smoke test for the SESSION 109 video pipeline.

Exercises the full fire-then-poll path:

    VideoViewSet.perform_create
      → MediaEngineClient.create_video
      → POST /internal/videos/ on FastAPI media-engine
      → runway_client.create_task (mock-mode short-circuit)
      → returns task_id immediately
      → Celery: poll_video_until_terminal.delay(video_id)
      → worker polls GET /internal/videos/{task_id}/
      → mock task resolves after ~12 s
      → worker writes status=ready + output_path back to Video row

Requires three processes running:
    1. Redis (infra/docker-compose.yml — port 6381)
    2. media-engine on :8001 (mock mode is fine; preferred)
    3. Celery worker: `celery -A character_os worker --pool=solo`

Usage:
    python manage.py smoke_video
    python manage.py smoke_video --workspace-slug acme
    python manage.py smoke_video --wait 25     # extend the poll wait
    python manage.py smoke_video --keep        # don't delete the row

Exit codes:
    0 — Video reached status=ready with a populated output_path
    1 — anything else (broker / media-engine unreachable, no
        spokesperson with avatar, polling timed out)
"""
from __future__ import annotations

import sys
import time
from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson
from apps.videos.models import Video
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)


class Command(BaseCommand):
    help = (
        "Smoke-test the SESSION 109 video pipeline: VideoViewSet → "
        "create_video → Celery poll → Video.status=ready."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--workspace-slug",
            default=None,
            help="Pick an existing workspace by slug. Defaults to first.",
        )
        parser.add_argument(
            "--wait",
            type=float,
            default=25.0,
            help=(
                "Seconds to wait for the Celery worker to mark the row "
                "terminal. Mock-mode tasks resolve in ~12 s; default 25 "
                "is comfortable."
            ),
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep the created Video row (default: delete on exit).",
        )

    def handle(self, *_, **opts: Any) -> None:
        # 1 — media-engine reachable?
        try:
            with MediaEngineClient() as client:
                health = client.health_check()
        except MediaEngineError as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"media engine unreachable — start it on :8001 first ({exc})"
                )
            )
            sys.exit(1)
        self.stdout.write(
            f"  ✓ media engine reachable (runway_mock={health.runway_mock})"
        )

        # 2 — pick a workspace + a spokesperson with an avatar id.
        workspace = self._pick_workspace(opts["workspace_slug"])
        if workspace is None:
            self.stderr.write(self.style.ERROR("no Workspace rows in the DB."))
            sys.exit(1)

        spokesperson = (
            Spokesperson.objects
            .filter(workspace=workspace)
            .exclude(runway_avatar_id="")
            .first()
        )
        if spokesperson is None:
            # Auto-create one in mock mode so the smoke test is hermetic
            # against a fresh DB. Reuses the same code path the avatar
            # smoke test exercises.
            self.stdout.write(
                self.style.WARNING(
                    "  ! no spokesperson with avatar in this workspace — "
                    "creating one"
                )
            )
            spokesperson = self._auto_create_spokesperson(workspace)

        self.stdout.write(
            f"  ✓ using spokesperson {spokesperson.name!r} "
            f"(avatar_id={spokesperson.runway_avatar_id})"
        )

        # 3 — POST the video via the viewset's perform_create path
        #     (same code path the SPA hits, minus the HTTP layer).
        from apps.videos.serializers import VideoSerializer
        from apps.videos.views import VideoViewSet

        owner = workspace.owner
        request = _StubRequest(owner)
        serializer = VideoSerializer(
            data={
                "spokesperson": str(spokesperson.pk),
                "title": "Smoke test",
                "brief": "Smoke test brief — Black Friday 30 % off.",
                "kind": "spokesperson_ad",
            },
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        viewset = VideoViewSet()
        viewset.request = request  # type: ignore[assignment]

        viewset.perform_create(serializer)
        video: Video = serializer.instance  # type: ignore[assignment]
        video_id = video.pk

        self.stdout.write(
            f"  ✓ video row id={video_id} status={video.status!r} "
            f"task_id={video.media_engine_task_id!r}"
        )

        if not video.media_engine_task_id:
            self.stderr.write(
                self.style.ERROR(
                    f"  ✗ no media_engine_task_id — perform_create failed "
                    f"(error={video.error_message!r})"
                )
            )
            self._cleanup(video_id, opts["keep"])
            sys.exit(1)

        # 4 — wait for the Celery worker to write terminal state back.
        deadline = time.time() + float(opts["wait"])
        last_status = video.status
        while time.time() < deadline:
            video.refresh_from_db()
            if video.status != last_status:
                self.stdout.write(
                    f"    status → {video.status!r} "
                    f"(t+{time.time() - (deadline - opts['wait']):.1f}s)"
                )
                last_status = video.status
            if video.status in {Video.Status.READY, Video.Status.FAILED}:
                break
            time.sleep(1.0)

        self.stdout.write(
            f"  → final status={video.status!r} output_path={video.output_path!r} "
            f"error={video.error_message!r}"
        )

        ok = (
            video.status == Video.Status.READY
            and bool(video.output_path)
        )

        self._cleanup(video_id, opts["keep"])

        if ok:
            self.stdout.write(self.style.SUCCESS("✓ smoke test PASSED"))
            return
        self.stderr.write(
            self.style.ERROR(
                "✗ smoke test FAILED — see status / error above. Is the "
                "Celery worker running? `celery -A character_os worker "
                "--pool=solo`"
            )
        )
        sys.exit(1)

    def _auto_create_spokesperson(self, workspace) -> Spokesperson:
        """Create a mock-mode spokesperson with an avatar so the smoke
        test has something to render against."""
        from apps.spokespeople.serializers import SpokespersonSerializer
        from apps.spokespeople.views import SpokespersonViewSet

        portrait_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        portrait_uri = "data:image/png;base64," + portrait_b64

        owner = workspace.owner
        request = _StubRequest(owner)
        ser = SpokespersonSerializer(
            data={
                "workspace": str(workspace.pk),
                "name": "Smoke Test Spokesperson",
                "business_brief": "Smoke test default brief.",
                "portrait_data_uri": portrait_uri,
                "voice_preset": "vincent",
            },
            context={"request": request},
        )
        ser.is_valid(raise_exception=True)
        viewset = SpokespersonViewSet()
        viewset.request = request  # type: ignore[assignment]
        viewset.perform_create(ser)
        return ser.instance  # type: ignore[return-value]

    def _cleanup(self, video_id, keep: bool) -> None:
        if keep:
            self.stdout.write(
                self.style.WARNING(f"  ! keeping Video row id={video_id}")
            )
            return
        with transaction.atomic():
            Video.objects.filter(pk=video_id).delete()
        self.stdout.write(f"  ✓ cleaned up Video row id={video_id}")

    @staticmethod
    def _pick_workspace(slug: str | None) -> Workspace | None:
        qs = Workspace.objects.all().order_by("created_at")
        if slug:
            return qs.filter(slug=slug).first()
        return qs.first()


class _StubRequest:
    """Minimal stand-in for a DRF Request. Carries an authenticated
    user — that's all the serializer / viewset code path actually
    reads."""

    def __init__(self, user) -> None:
        self.user = user
