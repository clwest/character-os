"""Capabilities-factuality gate — §19 Step 5.a (SESSION 244).

Enforces §9.5: ``ProviderCapabilities`` describes what an
adapter CAN DO, not how WELL it does it. Aesthetic claims,
quality ratings, and identity-stability judgments are benchmark
outcomes, not capabilities.

The gate is a substring denylist against
``ProviderCapabilities.__dataclass_fields__``. If someone
proposes adding e.g. ``identity_stability_score`` to
capabilities to make the field "more useful," this test fails
immediately and forces the discussion back to §9.5 before the
field ships.

This is the concrete mechanism operator constraint 5 called
out — encoding the discipline in a test so drift is caught
mechanically, not by reviewer vigilance.
"""
from __future__ import annotations

import pytest

from app.config import Settings
from app.services.portrait_provider import (
    ExecutionMode,
    PortraitProviderName,
    ProviderCapabilities,
)
from app.services.portrait_provider.mock import MockStillPortraitProvider
from app.services.portrait_provider.runway import RunwayStillPortraitProvider
from app.services.portrait_provider.stability import StabilityStillPortraitProvider


def _all_provider_instances() -> list:
    """Every concrete adapter, instantiated. Constructor
    signatures differ (Mock takes no args; Stability + Runway
    take Settings), so tests use instances rather than classes
    for behavioral checks. Class-level checks (Protocol drift)
    live in ``test_protocol_drift.py``.
    """
    return [
        MockStillPortraitProvider(),
        StabilityStillPortraitProvider(Settings()),
        RunwayStillPortraitProvider(Settings()),
    ]


# Substring denylist. Case-insensitive. If a substring in this
# set appears anywhere in a capabilities field name, the field
# is presumed aesthetic and the test fails. This intentionally
# catches compound names like ``naturalistic_quality`` or
# ``identity_stability_index``. Extend cautiously — the
# discipline lives here.
AESTHETIC_JARGON_SUBSTRINGS: frozenset[str] = frozenset({
    "quality",
    "naturalistic",
    "cinematic",
    "painterly",
    "photographic",
    "illustration",
    "stylized",
    "aesthetic",
    "beauty",
    "beautiful",
    "polished",
    "professional",
    "expressive",
    "identity_stable",
    "identity_stability",
    "flattering",
    "attractive",
    "pleasing",
    "artistic",
})


def test_capabilities_field_names_have_no_aesthetic_jargon():
    """Every field name on ``ProviderCapabilities`` must be
    factual per §9.5. Substring check against the
    denylist above.
    """
    offenders: list[tuple[str, str]] = []
    for name in ProviderCapabilities.__dataclass_fields__:
        lowered = name.lower()
        for token in AESTHETIC_JARGON_SUBSTRINGS:
            if token in lowered:
                offenders.append((name, token))
    assert offenders == [], (
        f"ProviderCapabilities has aesthetic-jargon fields — §9.5 "
        f"violation. Aesthetic claims belong to benchmark evidence, "
        f"not capabilities. Offenders (field, matching_token):\n"
        f"  {offenders}\n"
        f"If you believe a field is legitimately factual despite "
        f"the substring match, surface the exception to the "
        f"operator and revisit §9.5 — do not silence this test."
    )


@pytest.mark.parametrize(
    "provider",
    _all_provider_instances(),
    ids=lambda p: type(p).__name__,
)
def test_capabilities_returns_the_exact_dataclass(provider):
    """Adapters must return ``ProviderCapabilities`` directly —
    not a subclass with additional fields, and not a duck-typed
    dict. Subclassing would let an adapter smuggle aesthetic
    fields past the denylist.
    """
    caps = provider.capabilities()
    assert type(caps) is ProviderCapabilities, (
        f"{type(provider).__name__}.capabilities() returned "
        f"{type(caps).__name__}, expected ProviderCapabilities. "
        f"Adapters must not subclass ProviderCapabilities to "
        f"add fields — the field-name denylist is the discipline "
        f"anchor and subclassing evades it."
    )


def test_capabilities_field_set_is_scope_locked():
    """The set of ``ProviderCapabilities`` fields is itself a
    scope-locked surface. Adding fields is a §17.9.a decision —
    it changes what adapters must advertise.

    This test pins the field set. Failure means someone added
    or removed a capability field; the test update is itself
    the audit event.
    """
    expected = {
        "provider_name",
        "provider_model",
        "supported_models",
        "supported_aspect_ratios",
        "max_prompt_length",
        "is_deterministic",
        "execution_modes_supported",
    }
    actual = set(ProviderCapabilities.__dataclass_fields__)
    assert actual == expected, (
        f"ProviderCapabilities field set drifted from the "
        f"SESSION 244 scope-lock.\n"
        f"  Actual:   {sorted(actual)}\n"
        f"  Expected: {sorted(expected)}\n"
        f"  Added:    {sorted(actual - expected)}\n"
        f"  Removed:  {sorted(expected - actual)}\n"
        f"Adding capabilities fields is a scope decision — "
        f"revisit §17.9.a and SESSION 244 constraint 5."
    )


@pytest.mark.parametrize(
    "provider",
    _all_provider_instances(),
    ids=lambda p: type(p).__name__,
)
def test_execution_modes_supported_is_frozenset_of_execution_mode(provider):
    """Adapters advertise which execution modes they accept.
    The type here matters — a frozenset of the ExecutionMode
    enum, not strings, so callers can pattern-match without
    string comparison.
    """
    caps = provider.capabilities()
    assert isinstance(caps.execution_modes_supported, frozenset)
    assert all(
        isinstance(mode, ExecutionMode)
        for mode in caps.execution_modes_supported
    ), (
        f"execution_modes_supported must be a frozenset of "
        f"ExecutionMode, got "
        f"{[type(m).__name__ for m in caps.execution_modes_supported]}"
    )


@pytest.mark.parametrize(
    "provider",
    _all_provider_instances(),
    ids=lambda p: type(p).__name__,
)
def test_capabilities_provider_name_matches_provider_name_method(provider):
    """A subtle discipline — ``capabilities().provider_name``
    must equal ``provider_name()``. If they diverge, provenance
    tooling that reads one will disagree with tooling that
    reads the other.

    Also enforces that each adapter reports a valid
    ``PortraitProviderName`` value.
    """
    assert provider.capabilities().provider_name == provider.provider_name()
    assert isinstance(provider.provider_name(), PortraitProviderName)
