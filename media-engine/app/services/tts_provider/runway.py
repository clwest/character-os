"""Runway TTS provider — VO.1 first impl in the dispatch chain.

Targets Runway's ``/v1/text_to_speech`` endpoint per the
``audio_client.py:19`` SESSION 158-ish deferral note: at that
time the ``voice.type`` discriminator was gated by Runway and
the surface couldn't be unlocked via probing. The Q-vo-2 lock
resolution (VOICEOVER_V1.md) is to try Runway again here and
fall through to ElevenLabs direct if the gating is still in
place. If Runway has opened TTS up since then, this provider
just works.

The shape this provider tries:

* ``POST {runway_api_base}/v1/text_to_speech``
* Body: ``{model, voiceId, text}`` (the ``eleven_multilingual_v2``
  family is what design + dub use; this is the same family).
* Response: ``{previewUrl, voiceId, durationSeconds?}`` is the
  documented shape; defensive parsing handles fall-back keys.

Gated-feature surface: when Runway rejects with a documented
"voice.type" / "not enabled" / "feature gated" body, this
provider raises ``TtsUnavailableError`` so the dispatcher
falls through to ElevenLabs.

Cost: ~$0.01 per call (matches ElevenLabs eleven_multilingual_v2
list price). Refine post-VO.6 dogfood.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ...config import Settings
from . import TtsProviderError, TtsResult, TtsSpec, TtsUnavailableError

logger = logging.getLogger(__name__)


_RUNWAY_TTS_PATH = "/v1/text_to_speech"
_RUNWAY_TTS_MICROS = 10_000  # ~$0.01 — placeholder
_RUNWAY_TTS_TIMEOUT_S = 60.0
# Substrings in the Runway error body that signal the feature
# is still gated. When matched, we raise TtsUnavailableError
# (not TtsProviderError) so the dispatcher tries ElevenLabs
# next. Defensive — if Runway adds new gating messages later,
# extend the list rather than letting the dispatch break.
_RUNWAY_GATED_MARKERS = (
    "voice.type",
    "not enabled",
    "feature gated",
    "tts is not available",
    "text_to_speech is not enabled",
    "endpoint not found",  # 404 on a path Runway hasn't shipped
)


class RunwayTtsProvider:
    """Runway-backed TTS. Tries the documented endpoint and
    raises TtsUnavailableError on the gated-feature path so
    the dispatcher falls through to ElevenLabs."""

    name = "runway"

    def __init__(self, settings: Settings, data_dir: Path | None = None) -> None:
        if not settings.runway_api_key:
            raise TtsUnavailableError(
                "RunwayTtsProvider requires RUNWAY_API_KEY. Set the env "
                "var or use the mock / elevenlabs provider."
            )
        self.settings = settings
        self._data_dir = data_dir

    def configure(self, data_dir: Path) -> None:
        """The route sets this so the provider writes its
        cached MP3 into the data path."""
        self._data_dir = data_dir

    def synthesize(self, spec: TtsSpec) -> TtsResult:
        if not spec.text.strip():
            raise TtsProviderError("text is required and cannot be blank")
        if not spec.voice_id.strip():
            raise TtsProviderError("voice_id is required")

        url = f"{self.settings.runway_api_base}{_RUNWAY_TTS_PATH}"
        body: dict = {
            "model": spec.model,
            "voiceId": spec.voice_id,
            "text": spec.text,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.runway_api_key}",
            "X-Runway-Version": self.settings.runway_api_version,
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=_RUNWAY_TTS_TIMEOUT_S) as client:
                resp = client.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise TtsProviderError(
                f"runway POST {_RUNWAY_TTS_PATH} failed: "
                f"{type(exc).__name__}"
            ) from exc

        if resp.status_code == 404:
            # Endpoint absent — Runway has not shipped TTS yet.
            raise TtsUnavailableError(
                "runway returned 404 on /v1/text_to_speech — "
                "endpoint not shipped"
            )
        if resp.status_code in (401, 403):
            body_lower = (resp.text or "").lower()
            if any(m in body_lower for m in _RUNWAY_GATED_MARKERS):
                raise TtsUnavailableError(
                    f"runway tts gated: {resp.status_code} "
                    f"{resp.text[:200]}"
                )
            raise TtsProviderError(
                f"runway returned {resp.status_code} on tts: "
                f"{resp.text[:200]}"
            )
        if resp.status_code >= 400:
            body_lower = (resp.text or "").lower()
            if any(m in body_lower for m in _RUNWAY_GATED_MARKERS):
                raise TtsUnavailableError(
                    f"runway tts gated (rc={resp.status_code}): "
                    f"{resp.text[:200]}"
                )
            raise TtsProviderError(
                f"runway returned {resp.status_code} on tts: "
                f"{resp.text[:200]}"
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise TtsProviderError(
                f"runway tts returned non-json: {exc!s}"[:200]
            ) from exc

        preview_url = (
            payload.get("previewUrl")
            or payload.get("preview_url")
            or payload.get("audioUrl")
            or payload.get("url")
            or ""
        )
        if not preview_url:
            raise TtsProviderError(
                "runway tts payload missing preview/audio url"
            )

        duration_raw = (
            payload.get("durationSeconds")
            or payload.get("duration_seconds")
            or payload.get("duration")
            or 0
        )
        try:
            duration = float(duration_raw)
        except (TypeError, ValueError):
            duration = 0.0

        size_bytes_raw = payload.get("sizeBytes") or payload.get("size_bytes") or 0
        try:
            size_bytes = int(size_bytes_raw)
        except (TypeError, ValueError):
            size_bytes = 0

        logger.info(
            "runway tts voice=%s chars=%d duration=%.2fs",
            spec.voice_id, len(spec.text), duration,
        )

        return TtsResult(
            audio_url=preview_url,
            voice_id=payload.get("voiceId") or spec.voice_id,
            duration_seconds=duration,
            size_bytes=size_bytes,
            model=spec.model,
            provider="runway",
            cost_micros=_RUNWAY_TTS_MICROS,
            mock_mode=False,
        )
