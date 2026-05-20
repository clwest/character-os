"""SESSION 201 forward-defense — `_build_reencode_cmd` silent-base.

The post-SESSION 200 audit identified `_build_reencode_cmd` as the
last remaining ffmpeg endpoint that unconditionally referenced
``[N:a]`` from downloaded clips. Hit by ``concat_clips`` when the
caller passes ``reencode=True`` (operator-set on ``long_form_ad``).
Long-form ad always has avatar speech today, so silent-base was
never exercised — but the contract is the same fragile shape as
SESSION 196 mix_audio + SESSION 200 intro_outro.

Two tests:

* **All-silent inputs** — three silent clips + ``reencode=True``
  produces a video-only output (no audio stream).
* **Mixed audio + silent** — one with audio, one without; the
  uniform-shape simplification drops audio from both rather than
  synthesizing silence per-clip. Output is video-only.

The reencode path is reached via ``POST /internal/clips/concat/``
with ``reencode: true`` + ``crossfade_ms: 0``.
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


def test_concat_reencode_with_all_silent_inputs_emits_video_only(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Pre-fix, this would 500 with ``Error binding filtergraph
    inputs/outputs: Invalid argument`` because every
    ``[N:a]aresample`` reference matched no streams. Post-fix, the
    reencode branch detects all-silent inputs + drops the audio
    chain entirely. Output carries video only."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe not on PATH")

    clips = [
        _make_silent_clip(tmp_path, name=f"shot_{i}", color=c)
        for i, c in enumerate(["navy", "darkred", "darkgreen"])
    ]

    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": [str(p) for p in clips],
            "reencode": True,
            "crossfade_ms": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["output_url"].startswith("/data/_internal/concats/")

    output_path = tmp_path / body["output_url"][len("/data/"):]
    codecs = _probe_codecs(output_path)
    assert "video" in codecs
    assert "audio" not in codecs


def test_concat_reencode_with_mixed_audio_silent_inputs_drops_audio(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Mixed-shape inputs (some with audio, some without) fall
    through the same all-silent branch — the
    ``any(silent) → video-only`` simplification keeps concat
    semantics predictable. Audio is intentionally dropped from
    the audio-carrying input rather than synthesizing silence
    per-silent input. Mirrors ``_extend_concat``'s v1 contract."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe not on PATH")

    silent = _make_silent_clip(tmp_path, name="silent_shot")
    voiced = _make_clip_with_audio(tmp_path, name="voiced_shot")

    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": [str(silent), str(voiced)],
            "reencode": True,
            "crossfade_ms": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    codecs = _probe_codecs(output_path)
    assert "video" in codecs
    assert "audio" not in codecs


def test_concat_reencode_with_all_audio_inputs_preserves_audio(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Regression guard for the audio-preserving path. Uniform
    audio inputs + ``reencode=True`` continue to emit audio
    (the SESSION 199 baseline). Validates the silent-base branch
    didn't break the happy path."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg / ffprobe not on PATH")

    clips = [
        _make_clip_with_audio(tmp_path, name=f"voiced_{i}", color=c)
        for i, c in enumerate(["navy", "darkred"])
    ]

    resp = real_mode_client.post(
        "/internal/clips/concat/",
        json={
            "clip_urls": [str(p) for p in clips],
            "reencode": True,
            "crossfade_ms": 0,
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    codecs = _probe_codecs(output_path)
    assert "video" in codecs
    assert "audio" in codecs
