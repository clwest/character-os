"""End-to-end smoke test for the SESSION 110 voice clone pipeline.

Exercises:

    SpokespersonViewSet.clone_voice action
      → MediaEngineClient.clone_voice
      → POST /internal/voices/ on FastAPI media-engine
      → voice_clone_client.clone_voice_from_audio (mock-mode short-circuit)
      → returns voice_id + preview_url
      → Spokesperson.voice_id persisted

Auto-creates a spokesperson with a mock avatar if the workspace
doesn't have one (reuses the SESSION 108 path). Uses a tiny in-line
silent WAV payload so the test is hermetic.

Usage:
    python manage.py smoke_voice
    python manage.py smoke_voice --workspace-slug acme
    python manage.py smoke_voice --keep

Exit codes:
    0 — voice_id persisted, status ∈ {ready, mock}
    1 — anything else
"""
from __future__ import annotations

import base64
import struct
import sys
from typing import Any

from django.core.management.base import BaseCommand

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)


def _silent_wav_bytes(duration_seconds: float = 1.0) -> bytes:
    """Build a minimal RIFF/WAVE header + duration_seconds of silence.

    16-bit PCM, mono, 8 kHz — the smallest viable shape Runway's
    decoder will accept. Hermetic; no fixture file needed.
    """
    sample_rate = 8000
    num_samples = int(sample_rate * duration_seconds)
    data_bytes = num_samples * 2  # 16-bit mono
    riff_size = 36 + data_bytes

    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
    fmt_chunk = (
        b"fmt " + struct.pack("<I", 16)
        + struct.pack("<H", 1)         # PCM
        + struct.pack("<H", 1)         # mono
        + struct.pack("<I", sample_rate)
        + struct.pack("<I", sample_rate * 2)  # byte rate
        + struct.pack("<H", 2)         # block align
        + struct.pack("<H", 16)        # bits per sample
    )
    data_chunk = b"data" + struct.pack("<I", data_bytes) + b"\x00" * data_bytes
    return header + fmt_chunk + data_chunk


def _audio_data_uri() -> str:
    raw = _silent_wav_bytes()
    return "data:audio/wav;base64," + base64.b64encode(raw).decode("ascii")


class Command(BaseCommand):
    help = (
        "Smoke-test the SESSION 110 voice clone: clone_voice action → "
        "/internal/voices/ → Spokesperson.voice_id persisted."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--workspace-slug",
            default=None,
            help="Pick an existing workspace by slug. Defaults to first.",
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep the test spokesperson (default: revert voice_id).",
        )

    def handle(self, *_, **opts: Any) -> None:
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
            self.stdout.write(
                self.style.WARNING(
                    "  ! no spokesperson with avatar in this workspace — "
                    "creating one"
                )
            )
            spokesperson = self._auto_create_spokesperson(workspace)

        original_voice_id = spokesperson.voice_id
        self.stdout.write(
            f"  ✓ using spokesperson {spokesperson.name!r} "
            f"(initial voice_id={original_voice_id!r})"
        )

        # Drive the same code path the DRF action would — call
        # clone_voice directly with a stub request.
        from apps.spokespeople.views import SpokespersonViewSet

        owner = workspace.owner
        request = _StubRequest(
            owner,
            data={
                "audio_data_uri": _audio_data_uri(),
                "name": f"Smoke test voice — {spokesperson.name}",
            },
        )

        viewset = SpokespersonViewSet()
        viewset.request = request  # type: ignore[assignment]
        viewset.format_kwarg = None  # type: ignore[assignment]
        viewset.kwargs = {"pk": str(spokesperson.pk)}  # type: ignore[assignment]

        response = viewset.clone_voice(request, pk=str(spokesperson.pk))

        if response.status_code != 200:
            self.stderr.write(
                self.style.ERROR(
                    f"  ✗ clone_voice returned {response.status_code}: {response.data!r}"
                )
            )
            sys.exit(1)

        voice_block = response.data.get("voice") or {}
        self.stdout.write(
            f"  ✓ clone_voice response status={voice_block.get('status')!r} "
            f"voice_id={voice_block.get('voice_id')!r} "
            f"preview_url={voice_block.get('preview_url')!r}"
        )

        spokesperson.refresh_from_db()
        self.stdout.write(
            f"  ✓ Spokesperson row voice_id={spokesperson.voice_id!r}"
        )

        ok = (
            voice_block.get("voice_id")
            and voice_block.get("status") in {"ready", "mock"}
            and spokesperson.voice_id == voice_block.get("voice_id")
        )

        if not opts["keep"]:
            spokesperson.voice_id = original_voice_id
            spokesperson.save(update_fields=["voice_id", "updated_at"])
            self.stdout.write(f"  ✓ reverted voice_id to {original_voice_id!r}")
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  ! kept voice_id={spokesperson.voice_id!r}"
                )
            )

        if ok:
            self.stdout.write(self.style.SUCCESS("✓ smoke test PASSED"))
            return
        self.stderr.write(self.style.ERROR("✗ smoke test FAILED"))
        sys.exit(1)

    def _auto_create_spokesperson(self, workspace) -> Spokesperson:
        """Mirrors the smoke_video helper — creates a mock-mode
        spokesperson with an avatar so voice cloning has a target."""
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
                "name": "Voice Smoke Test Spokesperson",
                "business_brief": "Voice smoke test default brief.",
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

    @staticmethod
    def _pick_workspace(slug: str | None) -> Workspace | None:
        qs = Workspace.objects.all().order_by("created_at")
        if slug:
            return qs.filter(slug=slug).first()
        return qs.first()


class _StubRequest:
    """Minimal stand-in for a DRF Request. Carries an authenticated
    user, a data dict, and an HTTP method (the IsWorkspaceMember
    permission class reads ``request.method`` to decide read vs
    write)."""

    def __init__(
        self,
        user,
        data: dict | None = None,
        method: str = "POST",
    ) -> None:
        self.user = user
        self.data = data or {}
        self.method = method
        self.query_params: dict = {}
