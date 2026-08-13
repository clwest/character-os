"""Real-provider Runway smoke — §19 Step 5.c (SESSION 244).

Opt-in test that exercises the actual Runway HTTP API to
validate the adapter's assumptions against real responses. Not
part of the default suite — skipped unless
``PORTRAIT_PROVIDER_REAL_SMOKE=1`` is set AND ``RUNWAY_API_KEY``
is present (via ``.env`` or process env).

**IMPLEMENTATION-VALIDATION evidence, not portrait QUALIFICATION
evidence.** A passing smoke proves the adapter can execute its
Protocol contract end-to-end against Runway. It does not prove
Runway produces output that qualifies for portrait-generation
use in the product. Qualification is a separate benchmark
landing after Step 7 (normalization) per §19.3.

Runbook:

    export PORTRAIT_PROVIDER_REAL_SMOKE=1
    # RUNWAY_API_KEY should already live in .env
    cd media-engine
    pytest tests/portrait_provider/test_runway_real_smoke.py -v

Cost: Runway ``gen4_image`` at 1280:720 is currently billed as
image credits per generation. Real-provider smoke intentionally
runs a minimal set — one full generation for the primary
contract, two probes that fail before any credit spend
(force-mock override and unsupported model). Expected wall
time: 20-60 seconds per real call.
"""
from __future__ import annotations

import os

import pytest

from app.config import Settings
from app.services.portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitSpec,
    ProviderUnavailableError,
    UnsupportedModelError,
)
from app.services.portrait_provider.runway import RunwayStillPortraitProvider


REAL_SMOKE_ENV = "PORTRAIT_PROVIDER_REAL_SMOKE"


def _real_smoke_enabled() -> bool:
    return os.environ.get(REAL_SMOKE_ENV) == "1"


def _real_key_present() -> bool:
    """Check the Settings-loaded key (respects ``.env``) — same
    pattern as the Stability smoke.
    """
    return bool((Settings().runway_api_key or "").strip())


pytestmark = pytest.mark.skipif(
    not (_real_smoke_enabled() and _real_key_present()),
    reason=(
        f"Real Runway smoke skipped. Set {REAL_SMOKE_ENV}=1 AND "
        f"RUNWAY_API_KEY (via .env or process env) to exercise. "
        f"Opt-in because it costs real credits and takes 20-60s "
        f"per real call."
    ),
)


def _real_settings() -> Settings:
    """Load Settings from the environment/.env — respects
    shipped config."""
    return Settings()


def _minimal_spec() -> PortraitSpec:
    """Small, unambiguous prompt at Runway's shipped ratio.
    Keeps the smoke bounded in wall time + spend.
    """
    return PortraitSpec(
        prompt=(
            "A minimalist studio still-life photograph of a single "
            "green apple on a plain gray tabletop, soft overhead "
            "lighting, neutral background."
        ),
        aspect_ratio="1280:720",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        provider_model="gen4_image",
    )


# ---- Implementation-validation contract ------------------------


def test_real_required_returns_real_png_bytes():
    """The adapter, called with REAL_REQUIRED against real
    Runway, returns a PortraitResult with non-empty PNG bytes
    tagged execution_mode_actual=REAL. Answers the operator's
    implementation-validation questions on the live path."""
    provider = RunwayStillPortraitProvider(_real_settings())
    result = provider.generate_still_portrait(_minimal_spec())

    # Provenance stamped correctly.
    assert result.provider == PortraitProviderName.RUNWAY_STILL_PORTRAIT
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.provider_model == "gen4_image"
    # Never RUNWAY_AVATAR — the pre-5.a enum split enforces this
    # even in the live path.
    assert result.provider.value == "runway_still_portrait"

    # PNG bytes look valid.
    assert result.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"), (
        "Real Runway response is not a valid PNG — adapter "
        "assumption about download response may be wrong."
    )
    # Runway gen4_image 1280:720 output is typically 200KB-3MB.
    # Adapter enforces a 16MB hard cap via ``_MAX_IMAGE_BYTES``.
    assert 5_000 < len(result.image_bytes) < 16 * 1024 * 1024, (
        f"Real Runway PNG size {len(result.image_bytes)} bytes is "
        f"outside expected 5KB-16MB range."
    )

    # Timing sanity — Runway task API polls with a 180s deadline
    # per ``_portrait_task_attempt``.
    assert result.elapsed_ms > 0
    assert result.elapsed_ms < 240_000, "Exceeded 4-min soft cap"

    # Prompt snapshot recorded for provenance.
    assert result.prompt_snapshot["prompt"] == _minimal_spec().prompt
    assert result.prompt_snapshot["provider_model"] == "gen4_image"
    # ``task_id`` from Runway's task payload is threaded through
    # for GenerationRecord traceability.
    assert result.prompt_snapshot["task_id"], (
        "task_id missing from prompt_snapshot — Runway's response "
        "shape may have changed."
    )


def test_real_required_with_force_mock_raises_without_calling_runway():
    """Force-mock override intercepts BEFORE the transport is
    called — verified against a real key. Proves force-mock
    discipline works when Runway would otherwise be reachable.
    Costs $0 (no real call).
    """
    settings = Settings(
        runway_api_key=os.environ.get("RUNWAY_API_KEY", "")
        or _real_settings().runway_api_key,
        runway_force_mock=True,
    )
    provider = RunwayStillPortraitProvider(settings)
    with pytest.raises(ProviderUnavailableError):
        provider.generate_still_portrait(_minimal_spec())


def test_unsupported_model_raises_before_any_runway_call():
    """Spec validation runs before transport — verified end-to-
    end with a real key. Costs $0.
    """
    spec = PortraitSpec(
        prompt=_minimal_spec().prompt,
        aspect_ratio="1280:720",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        provider_model="gen4_image_turbo",  # documented but not shipped
    )
    provider = RunwayStillPortraitProvider(_real_settings())
    with pytest.raises(UnsupportedModelError):
        provider.generate_still_portrait(spec)
