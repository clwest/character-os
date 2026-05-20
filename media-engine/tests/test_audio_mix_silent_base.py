"""SESSION 196 slice 1 — ``/internal/audio/mix/`` silent-base regression.

SESSION 195 dogfood found that ``mix_audio``'s filtergraph references
``[0:a]`` (the base's audio stream) unconditionally. When the base is
silent (e.g. ``storyboard_voiced``'s concat of N silent visual clips,
or any ``gen4_turbo`` / ``gen4.5`` Runway output), ``[0:a]`` matches
no streams and ffmpeg exits rc=234.

V14 design assumed base had audio (``music_bed_pass`` shape: avatar
speech + music bed). V15.4's ``storyboard_voiced`` bonus added the
``audio_extract`` + ``mix_audio`` chain without realising the base
would be silent.

This test exercises the fix end-to-end:

* **Silent base** (silent storyboard concat shape) + audio overlay
  → the overlay becomes the only audio output. Was 500; now works.
* **Audio base** (music_bed_pass shape) + audio overlay → existing
  ``amix`` path. Regression guard that the fix didn't break the
  V14 happy path.
* **Silent overlay** → 422 (pathological — overlay must carry audio
  for mix to be meaningful).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


# ---- fixtures synthesized via ffmpeg lavfi -----------------------


def _make_silent_clip(
    tmp_path: Path,
    name: str = "silent",
    w: int = 320,
    h: int = 240,
    color: str = "navy",
    duration_s: int = 5,
) -> Path:
    """Silent video — no audio stream at all. Mirrors what
    ``generate_visual_clip`` / ``concat_clips`` produces when the
    upstream Runway model is gen4_turbo / gen4.5."""
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


def _make_audio_clip(
    tmp_path: Path,
    name: str = "audio",
    duration_s: int = 5,
    frequency: int = 440,
) -> Path:
    """Audio-only MP3 — what ``audio_extract`` produces. Sine tone
    keeps the file small + tests still meaningful."""
    out = tmp_path / f"{name}.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"sine=frequency={frequency}:duration={duration_s}",
            "-c:a", "libmp3lame", "-b:a", "128k",
            "-f", "mp3", str(out),
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
    """Video WITH audio — mirrors the ``avatar_speech`` /
    ``music_bed_pass`` base shape."""
    out = tmp_path / f"{name}-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r=30:d={duration_s}",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


@pytest.fixture
def real_mode_client(tmp_path: Path):
    """TestClient pinned to a tmp data_path with runway_mock OFF
    so the real ffmpeg pipeline runs."""

    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="present",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


# ---- silent-base path (the SESSION 195 bug) -----------------------


def test_audio_mix_silent_base_produces_video_plus_audio_output(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """The SESSION 195 trigger reproduction: silent base
    (storyboard concat shape) + audio overlay. Pre-fix this was a
    500 from ffmpeg rc=234. Post-fix the output exists + carries
    both video (from base) and audio (from overlay)."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    silent_base = _make_silent_clip(tmp_path, "silent_storyboard", duration_s=8)
    audio_overlay = _make_audio_clip(tmp_path, "narration", duration_s=5)

    resp = real_mode_client.post(
        "/internal/audio/mix/",
        json={
            "base_clip_url": str(silent_base),
            "audio_urls": [str(audio_overlay)],
            "mix_spec": {
                "fade_in_ms": 0,
                "fade_out_ms": 0,
                "music_gain_db": 0.0,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["output_url"].startswith("/data/_internal/mixes/")

    # Output must carry both streams. The video comes from the base
    # (8s); the audio comes from the overlay (5s). The container
    # carries both — duration tracks the longer (video).
    output_rel = body["output_url"][len("/data/"):]
    output_path = tmp_path / output_rel
    assert output_path.exists()

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(output_path),
        ],
        capture_output=True, text=True, timeout=10,
    )
    streams = set(line for line in probe.stdout.splitlines() if line)
    assert streams == {"video", "audio"}, (
        f"expected video+audio streams; got {streams}"
    )


# ---- music_bed_pass path (existing V14 happy path) ---------------


def test_audio_mix_audio_base_still_uses_amix_path(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Regression guard — the silent-base detection mustn't break
    the existing music_bed_pass / avatar_speech shape where the
    base already carries audio. amix path stays correct."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    audio_base = _make_clip_with_audio(tmp_path, "voiced_base", duration_s=5)
    music_overlay = _make_audio_clip(
        tmp_path, "music_bed", duration_s=5, frequency=220,
    )

    resp = real_mode_client.post(
        "/internal/audio/mix/",
        json={
            "base_clip_url": str(audio_base),
            "audio_urls": [str(music_overlay)],
            "mix_spec": {
                "fade_in_ms": 500,
                "fade_out_ms": 1000,
                "music_gain_db": -12.0,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    output_rel = resp.json()["output_url"][len("/data/"):]
    output_path = tmp_path / output_rel
    assert output_path.exists()

    # Both streams present, same as the silent-base case (the
    # mapping logic is the same; what differs is the filter_complex
    # source).
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(output_path),
        ],
        capture_output=True, text=True, timeout=10,
    )
    streams = set(line for line in probe.stdout.splitlines() if line)
    assert streams == {"video", "audio"}


# ---- pathological: silent overlay ---------------------------------


def test_audio_mix_silent_overlay_rejected_with_422(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Defense-in-depth: overlay must carry audio. A silent
    overlay would produce a silent output, which defeats the whole
    point of the endpoint. Refuse fast with 422."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    audio_base = _make_clip_with_audio(tmp_path, "voiced_base", duration_s=3)
    # Make a "silent overlay" by reusing the silent-video maker
    # (it has no audio stream).
    silent_overlay = _make_silent_clip(tmp_path, "silent_overlay", duration_s=3)

    resp = real_mode_client.post(
        "/internal/audio/mix/",
        json={
            "base_clip_url": str(audio_base),
            "audio_urls": [str(silent_overlay)],
            "mix_spec": {"music_gain_db": 0.0},
        },
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    msg = (body.get("error") or "").lower()
    assert "audio stream" in msg
    assert "overlay" in msg
