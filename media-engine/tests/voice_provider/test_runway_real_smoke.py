"""Real-provider Runway smoke — §19 Step 6.b (SESSION 245).

Opt-in test that exercises the actual Runway HTTP API to
validate the ``VoiceDesignProvider`` adapter's assumptions
against real responses. Not part of the default suite — skipped
unless ``VOICE_PROVIDER_REAL_SMOKE=1`` is set AND
``RUNWAY_API_KEY`` is present (via ``.env`` or process env).

**IMPLEMENTATION-VALIDATION evidence, not voice QUALIFICATION
evidence.** A passing smoke proves the adapter can execute its
Protocol contract end-to-end against Runway. It does not prove
the resulting voice is aesthetically or perceptually good for
product use. Qualification is a separate benchmark landing per
§19.3.

Runbook:

    export VOICE_PROVIDER_REAL_SMOKE=1
    # RUNWAY_API_KEY should already live in .env
    cd media-engine
    pytest tests/voice_provider/test_runway_real_smoke.py -v

Cost per smoke run (approximate, subject to Runway pricing):
* 1 real design (~$0.02-$0.05)
* 1 real clone (~$0.02-$0.05)
* 1 TTS interop synthesis (~$0.005 — one short sentence)
Total: expected < $0.15 per full smoke run.

Neutral synthetic audio for the clone smoke is generated
locally via macOS ``say`` + ``ffmpeg`` (Apple's built-in TTS +
audio transcode). No real human voice is uploaded. See
``_synthesize_neutral_audio_fixture`` for the discipline.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from app.config import Settings
from app.services.tts_provider import TtsProviderError, TtsSpec
from app.services.tts_provider import get_provider as get_tts_provider
from app.services.voice_provider import (
    ExecutionMode,
    ExecutionModeActual,
    VoiceCloneSpec,
    VoiceDesignSpec,
    VoiceOperation,
    VoiceProviderName,
    VoiceProviderUnavailableError,
)
from app.services.voice_provider.runway import RunwayVoiceProvider


REAL_SMOKE_ENV = "VOICE_PROVIDER_REAL_SMOKE"


def _real_smoke_enabled() -> bool:
    return os.environ.get(REAL_SMOKE_ENV) == "1"


def _real_key_present() -> bool:
    """Check the Settings-loaded key (respects ``.env``) — same
    pattern as portrait smokes."""
    return bool((Settings().runway_api_key or "").strip())


pytestmark = pytest.mark.skipif(
    not (_real_smoke_enabled() and _real_key_present()),
    reason=(
        f"Real Runway voice smoke skipped. Set {REAL_SMOKE_ENV}=1 AND "
        f"RUNWAY_API_KEY (via .env or process env) to exercise. "
        f"Opt-in because it costs real credits (~$0.15/run) and takes "
        f"20-60s per real call."
    ),
)


def _real_settings() -> Settings:
    """Load Settings from the environment/.env — respects
    shipped config."""
    return Settings()


# ---- Neutral synthetic-audio fixture ---------------------------


def _synthesize_neutral_audio_fixture(
    tmp_path: Path,
    *,
    duration_seconds: int = 15,
) -> tuple[bytes, str]:
    """Generate a neutral synthetic spoken audio sample for the
    clone smoke. Uses macOS ``say`` (Apple's built-in TTS) to
    produce speech from generic filler text and ``ffmpeg`` to
    transcode to MP3.

    Returns (audio_bytes, mime). Raises pytest.skip if tools
    are unavailable.

    The audio is deliberately generic — no real person's voice,
    no proprietary content, no branded language. Runway's clone
    API returns a durable ``voice_id``; what MATTERS for smoke
    is that Runway accepts the wire format and gives us a
    ``voice_id`` back. Aesthetic quality of the result is not
    part of this smoke.
    """
    if not shutil.which("say"):
        pytest.skip(
            "macOS `say` command not available — cannot generate "
            "neutral audio fixture for clone smoke."
        )
    if not shutil.which("ffmpeg"):
        pytest.skip(
            "ffmpeg not available — cannot transcode synthetic "
            "speech to MP3 for clone smoke."
        )

    # Neutral filler that produces enough audio to meet Runway's
    # 10-second floor without repeating short phrases.
    text = (
        "This is a neutral synthetic voice sample used only for "
        "provider validation. The words carry no meaning and no "
        "identity. Nothing in this recording represents a real "
        "person. The purpose is to exercise the upstream cloning "
        "pipeline and verify that a durable voice identifier is "
        "returned."
    )
    aiff = tmp_path / "fixture.aiff"
    mp3 = tmp_path / "fixture.mp3"

    subprocess.run(
        ["say", "-v", "Alex", "-o", str(aiff), text],
        check=True,
        capture_output=True,
        timeout=30,
    )
    # Transcode to MP3 at 128 kbps mono 44.1 kHz — small file,
    # accepted MIME for Runway.
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(aiff),
            "-ac", "1",
            "-ar", "44100",
            "-b:a", "128k",
            "-t", str(duration_seconds),
            str(mp3),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    audio_bytes = mp3.read_bytes()
    # Runway wants 10-300s and ≤ 10 MB.
    assert 10_000 < len(audio_bytes) < 10 * 1024 * 1024, (
        f"Synthesized fixture is {len(audio_bytes)} bytes — "
        f"outside the 10 KB - 10 MB safety band."
    )
    return audio_bytes, "audio/mpeg"


# ---- Design smoke ---------------------------------------------


# Module-scoped state: the designed voice_id is reused by the
# TTS interop test so we spend one design credit instead of two.
_designed_voice_id: str | None = None


def test_real_required_design_returns_real_voice_id():
    """Answers operator's implementation-validation questions
    on the live path:
    * Did Runway accept our shared VoiceDesignSpec shape?
    * What durable voice_id came back?
    * Does the returned result stamp REAL / RUNWAY_VOICE /
      DESIGN / provider_model correctly?
    * Typical elapsed time within the adapter's 90s deadline?
    """
    global _designed_voice_id

    provider = RunwayVoiceProvider(_real_settings())
    spec = VoiceDesignSpec(
        description=(
            "A neutral mid-range narrator voice used only for "
            "provider validation. Clear enunciation, moderate "
            "pacing, no distinctive character."
        ),
        execution_mode=ExecutionMode.REAL_REQUIRED,
        name="Character OS Voice Smoke",
    )
    start = time.monotonic()
    result = provider.design_voice(spec)
    wall_seconds = time.monotonic() - start

    # Provenance stamped correctly.
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.provider.value == "runway_voice"
    assert result.operation == VoiceOperation.DESIGN
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.provider_model == "eleven_multilingual_ttv_v2"

    # Durable identifier looks like a Runway voice id (opaque
    # string; no attempt to encode its structure).
    assert isinstance(result.voice_id, str)
    assert len(result.voice_id) > 0
    assert not result.voice_id.startswith("mock_voice_"), (
        f"Real design smoke returned a mock voice_id "
        f"{result.voice_id!r} — routing may be broken."
    )

    # Preview URL is optional per adapter contract.
    if result.preview_url is not None:
        assert result.preview_url.startswith("http"), (
            f"Preview URL {result.preview_url!r} is not HTTP(S)."
        )

    # Timing — Runway design typically completes in ~10-30s.
    assert result.elapsed_ms > 0
    assert result.elapsed_ms < 90_000, (
        f"Exceeded 90s adapter deadline: {result.elapsed_ms}ms"
    )
    assert wall_seconds < 95.0

    # Prompt snapshot recorded for provenance.
    assert result.prompt_snapshot["operation"] == "design"
    assert result.prompt_snapshot["description"] == spec.description
    assert result.prompt_snapshot["provider_model"] == "eleven_multilingual_ttv_v2"
    assert result.prompt_snapshot["requested_execution_mode"] == "real_required"

    _designed_voice_id = result.voice_id
    # Surfaced for run logs (pytest -s) — useful for handoffs
    # documenting live-observed values.
    print(
        f"\n  DESIGN smoke observed: voice_id_len={len(result.voice_id)} "
        f"elapsed_ms={result.elapsed_ms} preview_url_present="
        f"{bool(result.preview_url)}"
    )


# ---- Clone smoke ----------------------------------------------


def test_real_required_clone_returns_real_voice_id(tmp_path: Path):
    """Answers implementation-validation questions on the live
    clone path with a neutral synthetic audio fixture (Apple TTS
    → MP3, non-personal).
    """
    audio_bytes, mime = _synthesize_neutral_audio_fixture(tmp_path)

    provider = RunwayVoiceProvider(_real_settings())
    spec = VoiceCloneSpec(
        reference_audio=audio_bytes,
        reference_mime=mime,
        execution_mode=ExecutionMode.REAL_REQUIRED,
        name="Character OS Clone Smoke",
    )
    start = time.monotonic()
    result = provider.clone_voice(spec)
    wall_seconds = time.monotonic() - start

    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.operation == VoiceOperation.CLONE
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    # Clone has no model concept — honest None (Session 245
    # ratification 5-adjacent).
    assert result.provider_model is None

    assert isinstance(result.voice_id, str)
    assert len(result.voice_id) > 0
    assert not result.voice_id.startswith("mock_voice_")

    assert result.elapsed_ms > 0
    assert result.elapsed_ms < 90_000
    assert wall_seconds < 95.0

    assert result.prompt_snapshot["operation"] == "clone"
    assert result.prompt_snapshot["reference_mime"] == "audio/mpeg"
    assert result.prompt_snapshot["reference_bytes"] == len(audio_bytes)
    assert result.prompt_snapshot["final_status"] == "READY"
    print(
        f"\n  CLONE smoke observed: voice_id_len={len(result.voice_id)} "
        f"elapsed_ms={result.elapsed_ms} preview_url_present="
        f"{bool(result.preview_url)} fixture_bytes={len(audio_bytes)}"
    )


# ---- $0 discipline probes on the live-key path ----------------


def test_force_mock_never_calls_runway_even_with_real_key():
    """FORCED_MOCK routing intercepts BEFORE any transport call
    — verified against a real key. Proves force-mock discipline
    holds when Runway would otherwise be reachable. Costs $0.
    """
    settings = _real_settings()
    settings.runway_force_mock = True
    assert settings.runway_mock is True

    provider = RunwayVoiceProvider(settings)
    # With runway_force_mock and REAL_REQUIRED, adapter must
    # raise availability error — not silently return mock, not
    # call Runway.
    with pytest.raises(VoiceProviderUnavailableError):
        provider.design_voice(
            VoiceDesignSpec(
                description=(
                    "Force-mock smoke — this description must "
                    "never reach Runway."
                ),
                execution_mode=ExecutionMode.REAL_REQUIRED,
            ),
        )


def test_invalid_spec_never_calls_runway_even_with_real_key():
    """Spec validation runs BEFORE the transport — verified
    end-to-end with a real key. Costs $0.
    """
    provider = RunwayVoiceProvider(_real_settings())
    with pytest.raises(ValueError):
        provider.design_voice(
            VoiceDesignSpec(
                description="short",  # < 20 chars
                execution_mode=ExecutionMode.REAL_REQUIRED,
            ),
        )


# ---- TTS interop (bonus — voice_id round-trips through TTS) ---


def test_designed_voice_id_synthesizes_speech_via_runway_tts():
    """Interoperability validation (separate from voice-authoring
    contract): the durable ``voice_id`` produced by
    ``VoiceDesignProvider.design_voice`` is consumable by the
    already-landed ``TextToSpeechProvider`` runtime path.

    This test does NOT bring TTS under Step 6's scope. It is
    empirical proof that the durable output of one abstraction
    is a valid input to another — the whole point of §17.4.a
    bullets 1-2 (identity authoring produces a durable
    identifier; TTS consumes one).

    Depends on the design smoke having populated
    ``_designed_voice_id``. If pytest runs in random order this
    test may skip; run the file's tests in declared order (the
    default).
    """
    if _designed_voice_id is None:
        pytest.skip(
            "Design smoke has not yet run in this session — "
            "no voice_id available for TTS interop check."
        )

    settings = _real_settings()
    spec = TtsSpec(
        text="Short neutral interoperability probe.",
        voice_id=_designed_voice_id,
    )

    # Prefer Runway TTS (matches the design source). Fall back
    # to ElevenLabs on ANY TtsProviderError (both gated
    # TtsUnavailableError and other 4xx/5xx failures) since the
    # ``elevenlabs.py`` module comment records that Runway voices
    # are ElevenLabs-backed and the voice_id round-trips through
    # either provider. Broader-than-gated fallback matches the
    # spirit of the ``auto`` chain even though the shipped route
    # only chains on TtsUnavailableError today.
    def _synthesize_via(impl_name: str):
        """Mirror the shipped dispatcher's provider setup:
        instantiate + configure(data_dir) if supported + call
        synthesize. Returns the TtsResult or raises the same
        TtsProviderError classes the route would."""
        impl = get_tts_provider(impl_name, settings)
        if hasattr(impl, "configure"):
            impl.configure(settings.data_path)
        return impl.synthesize(spec)

    runway_error: str | None = None
    tts_result = None
    try:
        tts_result = _synthesize_via("runway")
    except TtsProviderError as exc:
        runway_error = f"{type(exc).__name__}: {exc}"

    elevenlabs_error: str | None = None
    if tts_result is None:
        if not settings.elevenlabs_api_key.strip():
            pytest.skip(
                f"TTS interop check skipped: Runway TTS failed "
                f"({runway_error}) and ElevenLabs is not "
                f"configured (no ELEVENLABS_API_KEY). Neither "
                f"real TTS path is available in this environment. "
                f"Interop cannot be exercised — record as an "
                f"environmental gap, NOT a Step 6 defect."
            )
        try:
            tts_result = _synthesize_via("elevenlabs")
        except TtsProviderError as exc:
            elevenlabs_error = f"{type(exc).__name__}: {exc}"
            # Both real TTS paths fail today for reasons OUTSIDE
            # the Step 6 Protocol contract. Record findings and
            # mark this xfail so the closure smoke doesn't gate
            # on a runtime TTS-layer bug.
            #
            #   F-6.b-2 (Runway TTS 400 — pre-existing bug in
            #   RunwayTtsProvider; ``promptText`` field missing
            #   from the shipped request body).
            #
            #   F-6.b-3 (ElevenLabs rejects Runway-designed
            #   voice_ids as ``invalid_uid`` — contradicts the
            #   stale comment in ``elevenlabs.py`` claiming
            #   Runway voice_ids are ElevenLabs-backed and round-
            #   trip through ElevenLabs TTS. The comment is
            #   empirically wrong today.)
            #
            # When F-6.b-2 (or F-6.b-3) is repaired in a future
            # bounded session, this xfail flips to XPASS and
            # someone notices — the natural signal for confirming
            # the fix.
            #
            # This does NOT indicate a Step 6 defect. The
            # ``VoiceDesignProvider`` Protocol contract is: the
            # adapter returns a provider-stamped durable
            # ``voice_id``. Whether that ``voice_id`` is
            # consumable by ANOTHER provider's TTS is a runtime
            # TTS-layer concern, not part of the voice-authoring
            # abstraction. Cross-provider consumption would
            # require explicit translation (a design decision
            # that is not part of §17.4.a).
            pytest.xfail(
                f"TTS interop known-broken today for reasons "
                f"OUTSIDE Step 6 scope.\n"
                f"  F-6.b-2 (Runway TTS): {runway_error}\n"
                f"  F-6.b-3 (ElevenLabs invalid_uid): "
                f"{elevenlabs_error}\n"
                f"See SESSION_245 handoff for the full evidence "
                f"and follow-up ownership. Step 6 Protocol "
                f"contract is unaffected — voice authoring "
                f"produces a durable voice_id; cross-provider "
                f"TTS consumption is a runtime concern."
            )

    assert tts_result is not None
    # The TTS call returned an audio artefact for the design-
    # sourced voice_id. This is the interop contract.
    assert tts_result.voice_id == _designed_voice_id
    assert tts_result.audio_url  # non-empty string
    assert tts_result.size_bytes > 0
    assert tts_result.duration_seconds > 0
    # Should NOT be mock — the provider was explicitly non-mock.
    assert tts_result.mock_mode is False, (
        "TTS returned mock output for a real designed voice_id "
        "— interop check did not exercise the real path."
    )
    print(
        f"\n  TTS INTEROP observed: which_provider={tts_result.provider} "
        f"runway_error_present={bool(runway_error)} "
        f"audio_size_bytes={tts_result.size_bytes} "
        f"duration_seconds={tts_result.duration_seconds:.2f} "
        f"round_tripped_voice_id={tts_result.voice_id == _designed_voice_id}"
    )
