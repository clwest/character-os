"""ElevenLabs direct TTS provider — VO.1 second leg in the
dispatch chain.

Activates when Runway's TTS path is gated (per ``runway.py``
``TtsUnavailableError``) and ``ELEVENLABS_API_KEY`` is set in
the media-engine env. The same voice_ids work — Runway voices
are ElevenLabs-backed (see ``audio_client._VOICE_DESIGN_MODEL =
"eleven_multilingual_ttv_v2"``), so a voice_id resolved via
``design_voice`` (V10) round-trips here without re-registering.

Endpoint:

* ``POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}``
* Headers: ``xi-api-key: {ELEVENLABS_API_KEY}``,
  ``Content-Type: application/json``, ``Accept: audio/mpeg``
* Body: ``{text, model_id, voice_settings: {stability, similarity_boost}}``
* Response: raw audio/mpeg bytes

The MP3 is written to ``data/_internal/voiceovers/<hash>.mp3``
keyed by ``hash(voice_id|model|text)`` so re-calls with the
same inputs are idempotent. Duration is computed via ffprobe
(matches the V14 audio_extract + audio_client.py
``_ffprobe_duration`` pattern).
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import httpx

from ...config import Settings
from . import TtsProviderError, TtsResult, TtsSpec, TtsUnavailableError

logger = logging.getLogger(__name__)


_ELEVENLABS_TTS_PATH_TPL = "/v1/text-to-speech/{voice_id}"
_ELEVENLABS_TTS_MICROS = 10_000  # ~$0.01 list-price placeholder
_ELEVENLABS_TTS_TIMEOUT_S = 90.0
_MAX_TTS_BYTES = 25 * 1024 * 1024  # cap any single TTS at 25 MB
_DEFAULT_MODEL = "eleven_multilingual_v2"


class ElevenLabsTtsProvider:
    """ElevenLabs-direct TTS. The fallback path when Runway's
    TTS surface is gated."""

    name = "elevenlabs"

    def __init__(self, settings: Settings, data_dir: Path | None = None) -> None:
        if not settings.elevenlabs_api_key.strip():
            raise TtsUnavailableError(
                "ElevenLabsTtsProvider requires ELEVENLABS_API_KEY. "
                "Set the env var or use the runway / mock provider."
            )
        self.settings = settings
        self._data_dir = data_dir

    def configure(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def synthesize(self, spec: TtsSpec) -> TtsResult:
        if not spec.text.strip():
            raise TtsProviderError("text is required and cannot be blank")
        if not spec.voice_id.strip():
            raise TtsProviderError("voice_id is required")

        model = (spec.model or "").strip() or _DEFAULT_MODEL
        cache_seed = (
            f"{spec.voice_id}|{model}|{spec.text}|elevenlabs"
        ).encode("utf-8")
        cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

        if self._data_dir is None:
            raise TtsProviderError(
                "ElevenLabsTtsProvider not configured with data_dir"
            )
        target_dir = self._data_dir / "_internal" / "voiceovers"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{cache_key}.mp3"
        relative_url = f"/data/_internal/voiceovers/{target.name}"

        if target.exists():
            # Idempotent cache hit.
            size_bytes = target.stat().st_size
            duration = _ffprobe_duration(target) or 0.0
            return TtsResult(
                audio_url=relative_url,
                voice_id=spec.voice_id,
                duration_seconds=duration,
                size_bytes=size_bytes,
                model=model,
                provider="elevenlabs",
                cost_micros=_ELEVENLABS_TTS_MICROS,
                mock_mode=False,
            )

        url = (
            f"{self.settings.elevenlabs_api_base}"
            f"{_ELEVENLABS_TTS_PATH_TPL.format(voice_id=spec.voice_id)}"
        )
        headers = {
            "xi-api-key": self.settings.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        body = {
            "text": spec.text,
            "model_id": model,
            "voice_settings": {
                "stability": 0.55,
                "similarity_boost": 0.8,
            },
        }

        tmp = target.with_suffix(target.suffix + ".tmp")
        try:
            with httpx.Client(timeout=_ELEVENLABS_TTS_TIMEOUT_S) as client:
                with client.stream(
                    "POST", url, headers=headers, json=body,
                ) as resp:
                    if resp.status_code == 401:
                        raise TtsProviderError(
                            "elevenlabs returned 401 — check ELEVENLABS_API_KEY"
                        )
                    if resp.status_code == 404:
                        raise TtsProviderError(
                            f"elevenlabs returned 404 — voice_id "
                            f"{spec.voice_id!r} not found"
                        )
                    if resp.status_code >= 400:
                        body_text = ""
                        try:
                            body_text = resp.read().decode("utf-8", errors="replace")
                        except Exception:
                            pass
                        raise TtsProviderError(
                            f"elevenlabs returned {resp.status_code}: "
                            f"{body_text[:300]}"
                        )
                    ctype = (resp.headers.get("content-type") or "").lower()
                    if not ctype.startswith("audio/"):
                        raise TtsProviderError(
                            f"elevenlabs returned unexpected content-type "
                            f"{ctype!r}"
                        )
                    size = 0
                    with open(tmp, "wb") as fh:
                        for chunk in resp.iter_bytes():
                            size += len(chunk)
                            if size > _MAX_TTS_BYTES:
                                fh.close()
                                tmp.unlink(missing_ok=True)
                                raise TtsProviderError(
                                    f"elevenlabs tts exceeded {_MAX_TTS_BYTES} byte cap"
                                )
                            fh.write(chunk)
            tmp.replace(target)
        except TtsProviderError:
            tmp.unlink(missing_ok=True)
            raise
        except httpx.HTTPError as exc:
            tmp.unlink(missing_ok=True)
            raise TtsProviderError(
                f"elevenlabs http error: {type(exc).__name__}"
            ) from exc

        duration = _ffprobe_duration(target) or 0.0
        size_bytes = target.stat().st_size
        logger.info(
            "elevenlabs tts voice=%s chars=%d duration=%.2fs cache=%s size=%d",
            spec.voice_id, len(spec.text), duration, cache_key, size_bytes,
        )
        return TtsResult(
            audio_url=relative_url,
            voice_id=spec.voice_id,
            duration_seconds=duration,
            size_bytes=size_bytes,
            model=model,
            provider="elevenlabs",
            cost_micros=_ELEVENLABS_TTS_MICROS,
            mock_mode=False,
        )


def _ffprobe_duration(path: Path) -> Optional[float]:
    """Best-effort MP3 duration extraction. Mirrors
    ``audio_client._ffprobe_duration``."""
    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True, capture_output=True, text=True, timeout=10,
        )
        return float(out.stdout.strip() or 0.0)
    except Exception:
        return None
