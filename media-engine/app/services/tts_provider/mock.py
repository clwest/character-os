"""Deterministic mock TTS provider — VO.1.

Mirrors the realtime_provider/mock.py + V14 audio_extract
mock-mode pattern. Returns a deterministic stub MP3 path that
the FastAPI route can serve via the existing
``data/_internal/voiceovers/`` static surface (Settings
.data_path) without hitting any external API.

Used by:

* Tests (``runway_mock=True`` fixture or
  ``VOICEOVER_TTS_FORCE_MOCK=1``).
* Local dev workflows that don't want to burn ElevenLabs or
  Runway credits.
* The CI suite which uses deterministic outputs.

The mock writes a real silent MP3 (via ffmpeg ``anullsrc``)
so downstream primitives like ``overlay_audio_at_offset``
(VO.2) see a parseable file. Falls back to a zero-byte
placeholder if ffmpeg is unavailable — the route still
returns a 200 with the stub path so tests don't fail on a
missing binary.
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
from pathlib import Path

from . import TtsResult, TtsSpec

logger = logging.getLogger(__name__)


# Mock duration heuristic — roughly aligned with the
# ``_estimate_avatar_speech_seconds`` constant from the V8
# backdrop chain math (11 chars/sec at conversational pace).
# Same constant so VO.2's offset validation pre-flight maths
# work the same in mock and real modes.
_MOCK_CHARS_PER_SECOND = 11
_MOCK_DURATION_FLOOR_S = 1.0
_MOCK_DURATION_CEILING_S = 60.0
# Trivial flat cost so cost-tracking surfaces still write
# non-zero numbers even in mock mode. Aligns with the V14
# audio_extract floor (40 micros = ~$0.00004).
_MOCK_TTS_MICROS = 10  # ~$0.00001 — placeholder


def _silent_mp3(target: Path, duration_s: float) -> bool:
    """Generate a silent MP3 via ffmpeg ``anullsrc``. Returns
    True on success, False if ffmpeg is unavailable. Mirrors
    ``audio_client._ffmpeg_silent_mp3``."""
    if not shutil.which("ffmpeg"):
        return False
    tmp = target.with_suffix(target.suffix + ".tmp")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", (
            "anullsrc=channel_layout=stereo:sample_rate=44100:"
            f"duration={duration_s:.3f}"
        ),
        "-c:a", "libmp3lame", "-b:a", "96k",
        "-f", "mp3",
        str(tmp),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return False
    if result.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(target)
    return True


def _mock_duration_for(text: str) -> float:
    """Conservative estimate so VO.2 offset math + cost
    estimation are stable across mock and real modes."""
    if not text:
        return _MOCK_DURATION_FLOOR_S
    approx = len(text) / _MOCK_CHARS_PER_SECOND
    return max(_MOCK_DURATION_FLOOR_S, min(approx, _MOCK_DURATION_CEILING_S))


class MockTtsProvider:
    """Deterministic stub. Same key inputs → same outputs so
    tests can assert on cache-key round-trips."""

    name = "mock"

    def __init__(self, data_dir: Path | None = None) -> None:
        # Late-bound — the route hands us the resolved
        # data_path so we don't double-resolve from env.
        self._data_dir = data_dir

    def configure(self, data_dir: Path) -> None:
        """The route sets this before calling synthesize so
        the mock writes into the same cache surface as the
        real providers."""
        self._data_dir = data_dir

    def synthesize(self, spec: TtsSpec) -> TtsResult:
        duration = _mock_duration_for(spec.text)
        cache_seed = (
            f"{spec.voice_id}|{spec.model}|{spec.text}|mock"
        ).encode("utf-8")
        cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

        size_bytes = 1024 * 50  # ~50KB placeholder
        relative_url = f"/data/_internal/voiceovers/mock-{cache_key}.mp3"
        if self._data_dir is not None:
            target_dir = self._data_dir / "_internal" / "voiceovers"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"mock-{cache_key}.mp3"
            if not target.exists():
                ok = _silent_mp3(target, duration)
                if ok:
                    size_bytes = target.stat().st_size
                else:
                    # Best-effort empty file so the URL resolves.
                    target.write_bytes(b"")
                    size_bytes = 0
            else:
                size_bytes = target.stat().st_size
        logger.info(
            "mock tts voice=%s chars=%d duration=%.2fs cache=%s",
            spec.voice_id, len(spec.text), duration, cache_key,
        )
        return TtsResult(
            audio_url=relative_url,
            voice_id=spec.voice_id or f"mock_voice_{cache_key}",
            duration_seconds=duration,
            size_bytes=size_bytes,
            model=spec.model,
            provider="mock",
            cost_micros=_MOCK_TTS_MICROS,
            mock_mode=True,
        )
