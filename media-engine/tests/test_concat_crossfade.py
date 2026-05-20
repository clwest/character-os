"""SESSION 200 — ``/internal/clips/concat/`` crossfade_ms branch.

Closes the V-arc UX gap of hard shot transitions in
``storyboard_ad`` / ``storyboard_voiced``. When the body carries
``crossfade_ms > 0`` the endpoint switches from ffmpeg's concat
demuxer to a filter_complex chain built around ``xfade`` (video)
+ ``acrossfade`` (audio) with per-clip ffprobe duration detection.

Three real-mode shape tests:

* **Silent storyboard shape** — three silent clips + crossfade ⇒
  output exists, video stream present, no audio (matches input
  shape), duration shorter than naive sum by ``(n-1) * crossfade``.
* **Voiced shape** — three clips WITH audio + crossfade ⇒ output
  carries both video + audio streams (acrossfade chain wired
  through, not just xfade).
* **crossfade_ms=0 stays on the fast path** — the existing
  concat-demuxer ``-c copy`` branch fires when crossfade is off,
  so the SESSION 199 fast path doesn't regress.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


def _make_silent_clip(
    tmp_path: Path,
    name: str = "silent",
    w: int = 320,
    h: int = 240,
    color: str = "navy",
    duration_s: int = 5,
) -> Path:
    out = tmp_path / f"{name}-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={w}x{h}:r=30:d={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


def _make_clip_with_audio(
    tmp_path: Path,
    name: str = "voiced",
    w: int = 320,
    h: int = 240,
    color: str = "navy",
    duration_s: int = 5,
) -> Path:
    out = tmp_path / f"{name}-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r=30:d={duration_s}",
            "-f", "lavfi",
            "-i", (
                f"sine=frequency=440:duration={duration_s},"
                "aformat=channel_layouts=stereo"
            ),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


def _probe_codecs(path: Path) -> list[str]:
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(path),
        ],
        check=True, capture_output=True, text=True, timeout=10,
    )
    return [
        line.strip() for line in probe.stdout.splitlines() if line.strip()
    ]


def _probe_duration_seconds(path: Path) -> float:
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(path),
        ],
        check=True, capture_output=True, text=True, timeout=10,
    )
    return float(probe.stdout.strip())


@pytest.fixture
def real_mode_client(tmp_path: Path):
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="present",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


def test_concat_silent_clips_with_crossfade_shortens_total_duration(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Storyboard shape: three silent clips + 500ms crossfade. Naive
    sum is 15s; each of two xfades overlaps 0.5s so output is ~14s.
    Pre-fix this would 422 (crossfade_ms not in schema) or fall
    through to the concat-demuxer hard-cut path."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe not on PATH")

    clips = [
        _make_silent_clip(tmp_path, name=f"shot_{i}", color=c, duration_s=5)
        for i, c in enumerate(["navy", "darkred", "darkgreen"])
    ]

    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": [str(p) for p in clips],
            "reencode": False,
            "crossfade_ms": 500,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["output_url"].startswith("/data/_internal/concats/")

    output_path = tmp_path / body["output_url"][len("/data/"):]
    assert output_path.exists()

    # No audio in any input → no audio in output (xfade-only path).
    codecs = _probe_codecs(output_path)
    assert "video" in codecs
    assert "audio" not in codecs

    # Two transitions × 0.5s overlap = 1s shorter than naive 15s.
    duration = _probe_duration_seconds(output_path)
    assert 13.5 <= duration <= 14.5, duration


def test_concat_audio_clips_with_crossfade_keeps_both_streams(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Voiced shape: three clips WITH audio + 500ms crossfade. The
    acrossfade chain must fire so the output carries both video and
    audio (regression guard against an xfade-only filter graph that
    would drop the audio streams)."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe not on PATH")

    clips = [
        _make_clip_with_audio(tmp_path, name=f"shot_{i}", color=c, duration_s=5)
        for i, c in enumerate(["navy", "darkred", "darkgreen"])
    ]

    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": [str(p) for p in clips],
            "reencode": False,
            "crossfade_ms": 500,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    output_path = tmp_path / body["output_url"][len("/data/"):]
    codecs = _probe_codecs(output_path)
    assert "video" in codecs
    assert "audio" in codecs


def test_concat_with_zero_crossfade_uses_existing_fast_path(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Backwards-compat: crossfade_ms=0 (or omitted) keeps the
    SESSION 199 concat-demuxer + ``-c copy`` path. Duration is the
    exact naive sum — no overlap."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe not on PATH")

    clips = [
        _make_silent_clip(tmp_path, name=f"fast_{i}", color=c, duration_s=4)
        for i, c in enumerate(["navy", "darkred"])
    ]

    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": [str(p) for p in clips],
            "reencode": False,
            "crossfade_ms": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    output_path = tmp_path / body["output_url"][len("/data/"):]
    duration = _probe_duration_seconds(output_path)
    # Hard cuts → exact 8s sum (small tolerance for ffmpeg
    # container-level timing).
    assert 7.5 <= duration <= 8.5, duration


def test_concat_crossfade_ms_validation_rejects_negative(
    real_mode_client: TestClient,
) -> None:
    """The endpoint schema's Field(ge=0, le=5000) rejects negative
    crossfade. 422 from pydantic before any ffmpeg work."""
    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": ["/tmp/nope.mp4"],
            "crossfade_ms": -1,
        },
    )
    assert resp.status_code == 422


def test_concat_crossfade_ms_validation_caps_at_five_seconds(
    real_mode_client: TestClient,
) -> None:
    """Crossfade > 5s is almost always an operator mistake (clips
    are typically 5s themselves). Cap matches the primitive-level
    docstring contract."""
    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": ["/tmp/nope.mp4"],
            "crossfade_ms": 6000,
        },
    )
    assert resp.status_code == 422
