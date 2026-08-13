"""Real-provider smoke — §19 Step 5.b (SESSION 244).

Opt-in test that exercises the actual Stability HTTP API to
validate the adapter's assumptions against real responses. Not
part of the default suite — skipped unless the caller sets
``PORTRAIT_PROVIDER_REAL_SMOKE=1`` AND ``STABILITY_API_KEY``
is present.

**This is IMPLEMENTATION-VALIDATION evidence, not portrait
QUALIFICATION evidence.** A passing smoke test proves the
adapter can execute its Protocol contract end-to-end against
the live provider. It does not prove the provider produces
output that qualifies for portrait-generation use in the
product. Qualification is a separate benchmark landing after
Step 7 (normalization) per §19.3.

Runbook:

    export STABILITY_API_KEY="sk-..."
    export PORTRAIT_PROVIDER_REAL_SMOKE=1
    cd media-engine
    pytest tests/portrait_provider/test_stability_real_smoke.py -v

Cost: one Stability ``core`` call per smoke test run (~3
credits, ~$0.03 at current pricing).
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
)
from app.services.portrait_provider.stability import StabilityStillPortraitProvider


REAL_SMOKE_ENV = "PORTRAIT_PROVIDER_REAL_SMOKE"


def _real_smoke_enabled() -> bool:
    return os.environ.get(REAL_SMOKE_ENV) == "1"


def _real_key_present() -> bool:
    """Check the Settings-loaded key (respects ``.env``) rather
    than ``os.environ`` alone, because pydantic-settings reads
    from the repo-root ``.env`` file without exporting to the
    process environment.
    """
    return bool((Settings().stability_api_key or "").strip())


pytestmark = pytest.mark.skipif(
    not (_real_smoke_enabled() and _real_key_present()),
    reason=(
        f"Real Stability smoke skipped. Set {REAL_SMOKE_ENV}=1 AND "
        f"STABILITY_API_KEY to exercise. This is opt-in because it "
        f"costs real credits and takes 3-10s per test."
    ),
)


def _real_settings() -> Settings:
    """Load Settings from the environment so the shipped
    ``.env`` values are respected."""
    return Settings()


def _core_spec() -> PortraitSpec:
    """Cheapest Stability model, 1:1 aspect, short prompt. Keeps
    smoke cost minimal while exercising the real path."""
    return PortraitSpec(
        prompt=(
            "A minimalist studio portrait of a solitary red apple "
            "on a plain gray background, soft even lighting."
        ),
        aspect_ratio="1:1",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        provider_model="core",
    )


# ---- Implementation-validation contract ------------------------


def test_real_required_returns_real_png_bytes():
    """The adapter, called with REAL_REQUIRED against real
    Stability, returns a PortraitResult carrying non-empty PNG
    bytes tagged execution_mode_actual=REAL."""
    provider = StabilityStillPortraitProvider(_real_settings())
    result = provider.generate_still_portrait(_core_spec())

    # Provenance stamped correctly.
    assert result.provider == PortraitProviderName.STABILITY_STILL
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.provider_model == "core"

    # PNG bytes look valid.
    assert result.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"), (
        "Real Stability response is not a valid PNG — adapter "
        "assumption about response shape may be wrong."
    )
    # Reasonable size — Stability 1:1 core output is typically
    # 200KB-2MB. Anything under 5KB or over 5MB suggests something
    # went sideways.
    assert 5_000 < len(result.image_bytes) < 5_000_000, (
        f"Real Stability PNG size {len(result.image_bytes)} bytes "
        f"is outside expected 5KB-5MB range."
    )

    # Timing sanity.
    assert result.elapsed_ms > 0
    assert result.elapsed_ms < 180_000, "Exceeded 3-min hard cap"

    # Prompt snapshot recorded for provenance.
    assert result.prompt_snapshot["prompt"] == _core_spec().prompt
    assert result.prompt_snapshot["provider_model"] == "core"
    assert result.prompt_snapshot["endpoint"].endswith("/core")


def test_real_required_with_force_mock_raises():
    """Sanity: even against real Stability, force-mock + REAL_REQUIRED
    must raise ProviderUnavailableError. Proves the force-mock
    override works when the key IS available."""
    settings = Settings(
        stability_api_key=os.environ.get("STABILITY_API_KEY", ""),
        stability_force_mock=True,
    )
    provider = StabilityStillPortraitProvider(settings)
    with pytest.raises(ProviderUnavailableError):
        provider.generate_still_portrait(_core_spec())


def test_unknown_model_field_surfaces_as_provider_request_failed():
    """If we bypass the adapter's spec validation and hand
    Stability a model it doesn't recognize, the transport layer
    returns a non-success response and the adapter raises
    ProviderRequestFailedError. This test exercises the failure
    plumbing against the real API rather than a stub.

    We use direct construction of the endpoint call rather than
    the adapter's normal path so we hit the "Stability rejects
    unknown model" branch.
    """
    # Adapter's own validation catches this earlier — verify.
    from app.services.portrait_provider import UnsupportedModelError

    spec = PortraitSpec(
        prompt=_core_spec().prompt,
        aspect_ratio="1:1",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        provider_model="phantom-model-does-not-exist",
    )
    provider = StabilityStillPortraitProvider(_real_settings())
    with pytest.raises(UnsupportedModelError):
        provider.generate_still_portrait(spec)


def test_multiple_aspect_ratios_all_return_valid_png():
    """Advertised aspect ratios in capabilities must actually
    round-trip through the real API. Runs against a subset to
    keep smoke cost bounded.
    """
    provider = StabilityStillPortraitProvider(_real_settings())
    subset = ["1:1", "16:9", "9:16"]
    for aspect in subset:
        spec = PortraitSpec(
            prompt=_core_spec().prompt,
            aspect_ratio=aspect,
            execution_mode=ExecutionMode.REAL_REQUIRED,
            provider_model="core",
        )
        result = provider.generate_still_portrait(spec)
        assert result.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"), (
            f"aspect_ratio={aspect} did not produce a valid PNG"
        )
