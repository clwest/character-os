"""Text-to-speech provider abstraction — VO.1 (voiceover arc).

Single named adapter per the VO.0 scope-lock contract rule 9.
The media-engine exposes one Protocol; v1 ships two
implementations (Runway, ElevenLabs direct) + a deterministic
mock. The shell never imports a provider directly — it calls
``POST /internal/audio/tts/`` and the route dispatches.

Provider selection at runtime (Q-vo-2 resolution):

* ``provider="mock"`` (or settings.runway_mock /
  voiceover_tts_force_mock) → ``MockTtsProvider``.
* ``provider="elevenlabs"`` → ``ElevenLabsTtsProvider`` if
  ``ELEVENLABS_API_KEY`` is set; raises ``TtsUnavailableError``
  otherwise.
* ``provider="runway"`` → ``RunwayTtsProvider``; raises
  ``TtsUnavailableError`` if Runway returns the documented
  "voice.type gated" rejection from ``audio_client.py:19``.
* ``provider="auto"`` (default) → tries Runway first; on
  ``TtsUnavailableError`` falls through to ElevenLabs; if
  neither path works, raises ``TtsUnavailableError`` with
  both upstream messages.

Adding a third provider is exactly one new module + one
registry entry — same shape as ``realtime_provider``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ...config import Settings


# ---- Provider-shared dataclasses --------------------------------


@dataclass(slots=True)
class TtsSpec:
    """Resolved voice + text payload handed to a provider.

    The shell side handles the ``voice_spec`` discriminator
    (spokesperson / voice_id / voice_design) and passes a
    concrete ``voice_id`` down to the route. Providers do not
    interpret spokesperson ids."""

    text: str
    voice_id: str
    model: str = "eleven_multilingual_v2"


@dataclass(slots=True)
class TtsResult:
    """Result of ``synthesize``. ``audio_url`` is a media-engine-
    served path the shell persists on the Asset row."""

    audio_url: str
    voice_id: str
    duration_seconds: float
    size_bytes: int
    model: str
    provider: str  # 'runway' | 'elevenlabs' | 'mock'
    cost_micros: int
    mock_mode: bool


# ---- Protocol ---------------------------------------------------


@runtime_checkable
class TextToSpeechProvider(Protocol):
    """Single named adapter — contract rule 9.

    v1 surface is one method: synthesize. Future R-arc-style
    extensions (streaming, partial-poll, voice listing) drop
    in as additional Protocol methods + concrete-provider
    stubs."""

    name: str

    def synthesize(self, spec: TtsSpec) -> TtsResult:
        """Synthesize speech from text. Returns the cached
        audio asset path the shell stores as the AUDIO row's
        ``file_path``. Raises ``TtsUnavailableError`` for
        provider-gated paths so the dispatcher can fall
        through; raises ``TtsProviderError`` for everything
        else (network, 5xx, malformed payload)."""
        ...


# ---- Errors -----------------------------------------------------


class TtsProviderError(RuntimeError):
    """Wraps upstream / configuration failures. The route
    surfaces these as HTTP 502s; the shell turns these into
    ``PrimitiveError`` so the composition step is marked
    FAILED."""


class TtsUnavailableError(TtsProviderError):
    """Configuration says this provider can't synthesize right
    now (gated feature, missing API key, etc.). The dispatcher
    catches this and tries the next provider in the auto
    chain; explicit single-provider callers see HTTP 503."""


# ---- Registry ---------------------------------------------------


def get_provider(name: str, settings: Settings) -> TextToSpeechProvider:
    """Look up a provider by name. ``name`` is one of
    ``mock`` / ``runway`` / ``elevenlabs``. ``auto`` chaining
    is handled in the route, not here — this function returns
    one concrete provider, never a chain.

    Mock-mode short-circuit: if ``settings.voiceover_tts_force_mock``
    is True OR ``settings.runway_mock`` is True with no
    explicit ``elevenlabs`` request, returns ``MockTtsProvider``.
    Lets tests + local dev work without burning either
    upstream's credits.
    """
    if name == "mock" or settings.voiceover_tts_force_mock:
        from .mock import MockTtsProvider

        return MockTtsProvider()
    if name == "runway":
        if settings.runway_mock:
            from .mock import MockTtsProvider

            return MockTtsProvider()
        from .runway import RunwayTtsProvider

        return RunwayTtsProvider(settings)
    if name == "elevenlabs":
        from .elevenlabs import ElevenLabsTtsProvider

        return ElevenLabsTtsProvider(settings)
    raise TtsProviderError(
        f"unknown tts provider {name!r}. "
        f"Registered: ['runway', 'elevenlabs', 'mock']"
    )


__all__ = [
    "TextToSpeechProvider",
    "TtsProviderError",
    "TtsResult",
    "TtsSpec",
    "TtsUnavailableError",
    "get_provider",
]
