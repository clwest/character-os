"""VO.2 tests — ``POST /internal/clips/overlay_audio/``.

Covers the contract rules from docs/design/VOICEOVER_V1.md:

* Rule 4 — video stream byte-identity. The route uses ``-c:v copy``
  so the output's video stream MD5 matches the base's exactly.
  Asserted with ffprobe ``stream_hash`` (proxied via per-frame
  packet hashing); see ``test_overlay_audio_video_stream_byte_identity``.
* Rule 5 — duck_db default -18; range [-60, 0] gated by Pydantic.
* Rule 6 — offset + vo_duration > base_duration rejected 422 with
  actionable message (ffprobe-based defense in depth).

Mock-mode short-circuits return deterministic stub URLs without
firing ffmpeg, mirroring the V14 ``audio_extract`` cache discipline.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


# ---- fixtures: synthesized ffmpeg sources --------------------------


def _make_clip_with_audio(
    tmp_path: Path,
    name: str = "base",
    *,
    w: int = 320,
    h: int = 240,
    color: str = "navy",
    duration_s: float = 10.0,
    audio_freq: int = 440,
) -> Path:
    """Video + audio MP4 (the talking_head shape). Audio is a sine
    so the duck/amix output is easy to reason about; video is a
    solid color so the byte-identity check is deterministic."""
    out = tmp_path / f"{name}-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"color=c={color}:s={w}x{h}:r=30:d={duration_s}",
            "-f", "lavfi",
            "-i", f"sine=frequency={audio_freq}:duration={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-movflags", "+faststart",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


def _make_silent_clip(
    tmp_path: Path,
    name: str = "silent",
    *,
    w: int = 320,
    h: int = 240,
    duration_s: float = 10.0,
) -> Path:
    """Video without an audio stream — used to validate the
    silent-base rejection (point operators at /audio/mix/)."""
    out = tmp_path / f"{name}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"color=c=black:s={w}x{h}:r=30:d={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


def _make_audio_clip(
    tmp_path: Path,
    name: str = "vo",
    *,
    duration_s: float = 3.0,
    frequency: int = 880,
) -> Path:
    """Audio-only MP3 — the synthesize_voiceover_audio output."""
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


def _video_stream_md5(path: Path) -> str:
    """ffprobe-based per-packet hash of the video stream only.
    Rule 4 byte-identity check — base.video_md5 == output.video_md5
    even after audio re-encode."""
    out = subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(path),
            "-map", "0:v", "-c:v", "copy",
            "-f", "md5", "-",
        ],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return hashlib.sha256(out.stdout.encode()).hexdigest()


# ---- TestClient fixtures -------------------------------------------


@pytest.fixture
def mock_client(tmp_path: Path):
    def _override() -> Settings:
        return Settings(
            runway_api_key="present",
            runway_force_mock=True,
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def real_mode_client(tmp_path: Path):
    def _override() -> Settings:
        return Settings(
            runway_api_key="present",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


# ---- Mock-mode ------------------------------------------------------


def test_overlay_audio_mock_mode_returns_stub_url(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": "/data/_internal/avatar_speech/base.mp4",
            "vo_url": "/data/_internal/voiceovers/vo.mp3",
            "offset_seconds": 5.0,
            "duck_db": -18.0,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is True
    assert body["output_url"].startswith("/data/_internal/overlays/mock-")
    assert body["duration_seconds"] > 0


def test_overlay_audio_mock_mode_is_idempotent(mock_client: TestClient):
    """Cache-key determinism — same (base, vo, offset, duck) →
    same stub URL across calls."""
    payload = {
        "base_url": "/data/_internal/avatar_speech/base.mp4",
        "vo_url": "/data/_internal/voiceovers/vo.mp3",
        "offset_seconds": 2.0,
    }
    r1 = mock_client.post("/internal/clips/overlay_audio/", json=payload)
    r2 = mock_client.post("/internal/clips/overlay_audio/", json=payload)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["output_url"] == r2.json()["output_url"]


def test_overlay_audio_mock_mode_different_offset_different_cache(
    mock_client: TestClient,
):
    """Different params → different cache keys."""
    base = {
        "base_url": "/data/_internal/avatar_speech/base.mp4",
        "vo_url": "/data/_internal/voiceovers/vo.mp3",
    }
    r1 = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={**base, "offset_seconds": 2.0},
    )
    r2 = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={**base, "offset_seconds": 5.0},
    )
    assert r1.json()["output_url"] != r2.json()["output_url"]


# ---- Pydantic validation -------------------------------------------


def test_overlay_audio_rejects_negative_offset(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": "/data/x.mp4", "vo_url": "/data/x.mp3",
            "offset_seconds": -1.0,
        },
    )
    assert resp.status_code in (400, 422)


def test_overlay_audio_rejects_duck_db_above_zero(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": "/data/x.mp4", "vo_url": "/data/x.mp3",
            "offset_seconds": 1.0, "duck_db": 3.0,
        },
    )
    assert resp.status_code in (400, 422)


def test_overlay_audio_rejects_duck_db_below_minus_60(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": "/data/x.mp4", "vo_url": "/data/x.mp3",
            "offset_seconds": 1.0, "duck_db": -90.0,
        },
    )
    assert resp.status_code in (400, 422)


def test_overlay_audio_rejects_blank_base_url(mock_client: TestClient):
    resp = mock_client.post(
        "/internal/clips/overlay_audio/",
        json={"base_url": "", "vo_url": "/data/x.mp3", "offset_seconds": 1.0},
    )
    assert resp.status_code in (400, 422)


# ---- Real-mode — rule 6 (offset + vo > base) -----------------------


def test_overlay_audio_real_mode_rule_6_overflow_returns_422(
    real_mode_client: TestClient, tmp_path: Path,
):
    """Rule 6 defense-in-depth — server ffprobes durations and
    returns 422 if VO would extend past base end."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    base = _make_clip_with_audio(tmp_path, "rule6base", duration_s=5.0)
    vo = _make_audio_clip(tmp_path, "rule6vo", duration_s=3.0)

    resp = real_mode_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": str(base), "vo_url": str(vo),
            "offset_seconds": 3.5,                 # 3.5 + 3.0 > 5.0
        },
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    msg = body.get("error") or body.get("detail", "")
    assert "past base clip end" in msg


# ---- Real-mode — silent-base rejection -----------------------------


def test_overlay_audio_real_mode_silent_base_returns_422(
    real_mode_client: TestClient, tmp_path: Path,
):
    """Silent base is the /audio/mix/ shape — refuse fast so the
    operator gets pointed at the right endpoint."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    base = _make_silent_clip(tmp_path, "silent_base", duration_s=10.0)
    vo = _make_audio_clip(tmp_path, "vo_pointed", duration_s=3.0)

    resp = real_mode_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": str(base), "vo_url": str(vo),
            "offset_seconds": 1.0,
        },
    )
    assert resp.status_code == 422, resp.text
    msg = resp.json().get("error", "")
    assert "no audio stream" in msg
    assert "/internal/audio/mix/" in msg


# ---- Real-mode — rule 4 (byte-identical video stream) -------------


def test_overlay_audio_video_stream_byte_identity(
    real_mode_client: TestClient, tmp_path: Path,
):
    """Rule 4 — the output's video stream is byte-for-byte the same
    as the base's. Asserted via ``ffmpeg -c:v copy -f md5 -`` on
    both, which hashes the encoded video packets without re-decoding.

    If a future change accidentally re-encoded video (e.g. switched
    ``-c:v copy`` to ``-c:v libx264``), this test fails immediately."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    base = _make_clip_with_audio(tmp_path, "byteid_base", duration_s=8.0)
    vo = _make_audio_clip(tmp_path, "byteid_vo", duration_s=2.0)

    base_video_hash = _video_stream_md5(base)

    resp = real_mode_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": str(base), "vo_url": str(vo),
            "offset_seconds": 5.0, "duck_db": -18.0,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    output_rel = body["output_url"][len("/data/"):]
    output_path = tmp_path / output_rel
    assert output_path.exists()

    output_video_hash = _video_stream_md5(output_path)
    assert base_video_hash == output_video_hash, (
        "rule 4 violated — output video stream differs from base. "
        "The overlay route must use `-c:v copy`."
    )


def test_overlay_audio_real_mode_produces_video_plus_audio(
    real_mode_client: TestClient, tmp_path: Path,
):
    """Sanity probe — the output carries both streams. Combined
    with the byte-identity check, this proves the overlay produced
    a valid composite without corrupting either side."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    base = _make_clip_with_audio(tmp_path, "sane_base", duration_s=6.0)
    vo = _make_audio_clip(tmp_path, "sane_vo", duration_s=2.0)

    resp = real_mode_client.post(
        "/internal/clips/overlay_audio/",
        json={
            "base_url": str(base), "vo_url": str(vo),
            "offset_seconds": 1.0,
        },
    )
    assert resp.status_code == 200, resp.text
    output_rel = resp.json()["output_url"][len("/data/"):]
    output_path = tmp_path / output_rel

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


def test_overlay_audio_real_mode_caches_output(
    real_mode_client: TestClient, tmp_path: Path,
):
    """Second call with the same inputs returns the same cached
    output without re-running ffmpeg. Mirrors V14 audio_extract."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    base = _make_clip_with_audio(tmp_path, "cache_base", duration_s=6.0)
    vo = _make_audio_clip(tmp_path, "cache_vo", duration_s=2.0)

    payload = {
        "base_url": str(base), "vo_url": str(vo),
        "offset_seconds": 1.0,
    }
    r1 = real_mode_client.post("/internal/clips/overlay_audio/", json=payload)
    r2 = real_mode_client.post("/internal/clips/overlay_audio/", json=payload)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["output_url"] == r2.json()["output_url"]
