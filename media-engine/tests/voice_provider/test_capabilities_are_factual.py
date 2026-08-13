"""Capabilities-factuality gate — §19 Step 6.a (SESSION 245).

Enforces §9.5 / §17.4.a bullet 4: ``VoiceProviderCapabilities``
describes what an adapter CAN DO, not how WELL it does it.
Aesthetic claims, quality ratings, and voice-similarity
judgments are benchmark outcomes, not capabilities.

The gate is a substring denylist against
``VoiceProviderCapabilities.__dataclass_fields__``. If someone
proposes adding e.g. ``voice_similarity_score`` to capabilities
to make the field "more useful," this test fails immediately
and forces the discussion back to §17.4.a before the field
ships.

This is the concrete mechanism SESSION 245 ratification called
out — encoding the discipline in a test so drift is caught
mechanically, not by reviewer vigilance.
"""
from __future__ import annotations

import pytest

from app.config import Settings
from app.services.voice_provider import (
    ExecutionMode,
    VoiceProviderCapabilities,
    VoiceProviderName,
)
from app.services.voice_provider.mock import MockVoiceProvider
from app.services.voice_provider.runway import RunwayVoiceProvider


def _all_provider_instances() -> list:
    """Every concrete adapter, instantiated. v1 registry closes
    at Mock (6.a) + Runway (6.b). Class-level checks (Protocol
    drift) live in ``test_protocol_drift.py``.
    """
    return [
        MockVoiceProvider(),
        RunwayVoiceProvider(Settings()),
    ]


# Substring denylist. Case-insensitive. If a substring in this
# set appears anywhere in a capabilities field name, the field
# is presumed aesthetic and the test fails. This intentionally
# catches compound names like ``naturalistic_index`` or
# ``voice_similarity_score``. Extend cautiously — the discipline
# lives here.
#
# Additions vs. Step 5's portrait denylist: voice-specific
# aesthetic language (``natural``, ``clarity``, ``timbre``,
# ``similarity``, ``resemblance``, ``intonation``, ``prosody``
# — the last two are quality-of-synthesis language when used as
# capability claims, not domain concepts). ``identity_stable``
# / ``identity_stability`` retained from portrait since the same
# aesthetic pretension applies.
AESTHETIC_JARGON_SUBSTRINGS: frozenset[str] = frozenset({
    "quality",
    "natural",
    "expressive",
    "professional",
    "premium",
    "clarity",
    "timbre",
    "similarity",
    "resemblance",
    "intonation",
    "prosody",
    "beautiful",
    "beauty",
    "polished",
    "identity_stable",
    "identity_stability",
    "flattering",
    "attractive",
    "pleasing",
    "artistic",
    "aesthetic",
    "warm",
    "cold",
    "smooth",
    "silky",
    "crisp",
})


def test_capabilities_field_names_have_no_aesthetic_jargon():
    """Every field name on ``VoiceProviderCapabilities`` must be
    factual per §17.4.a bullet 4. Substring check against the
    denylist above.
    """
    offenders: list[tuple[str, str]] = []
    for name in VoiceProviderCapabilities.__dataclass_fields__:
        lowered = name.lower()
        for token in AESTHETIC_JARGON_SUBSTRINGS:
            if token in lowered:
                offenders.append((name, token))
    assert offenders == [], (
        f"VoiceProviderCapabilities has aesthetic-jargon fields — "
        f"§17.4.a bullet 4 violation. Aesthetic claims belong to "
        f"benchmark evidence, not capabilities. Offenders "
        f"(field, matching_token):\n"
        f"  {offenders}\n"
        f"If you believe a field is legitimately factual despite "
        f"the substring match, surface the exception to the "
        f"operator and revisit §17.4.a — do not silence this test."
    )


@pytest.mark.parametrize(
    "provider",
    _all_provider_instances(),
    ids=lambda p: type(p).__name__,
)
def test_capabilities_returns_the_exact_dataclass(provider):
    """Adapters must return ``VoiceProviderCapabilities``
    directly — not a subclass with additional fields, and not a
    duck-typed dict. Subclassing would let an adapter smuggle
    aesthetic fields past the denylist.
    """
    caps = provider.capabilities()
    assert type(caps) is VoiceProviderCapabilities, (
        f"{type(provider).__name__}.capabilities() returned "
        f"{type(caps).__name__}, expected VoiceProviderCapabilities. "
        f"Adapters must not subclass VoiceProviderCapabilities to "
        f"add fields — the field-name denylist is the discipline "
        f"anchor and subclassing evades it."
    )


def test_capabilities_field_set_is_scope_locked():
    """The set of ``VoiceProviderCapabilities`` fields is itself
    a scope-locked surface. Adding fields is a §17.4.a decision —
    it changes what adapters must advertise.

    This test pins the field set. Failure means someone added
    or removed a capability field; the test update is itself
    the audit event.
    """
    expected = {
        "provider_name",
        "supports_design",
        "supports_clone",
        "supported_design_models",
        "accepted_audio_mimes",
        "max_reference_bytes",
        "min_reference_seconds",
        "max_reference_seconds",
        "min_description_chars",
        "max_description_chars",
        "max_authoring_seconds",
        "is_synchronous",
        "execution_modes_supported",
    }
    actual = set(VoiceProviderCapabilities.__dataclass_fields__)
    assert actual == expected, (
        f"VoiceProviderCapabilities field set drifted from the "
        f"SESSION 245 scope-lock.\n"
        f"  Actual:   {sorted(actual)}\n"
        f"  Expected: {sorted(expected)}\n"
        f"  Added:    {sorted(actual - expected)}\n"
        f"  Removed:  {sorted(expected - actual)}\n"
        f"Adding capabilities fields is a scope decision — "
        f"revisit §17.4.a and SESSION 245 ratifications."
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
def test_capabilities_provider_name_is_valid_enum(provider):
    """Adapters must report a valid ``VoiceProviderName`` value
    on capabilities. Provenance tooling relies on the enum
    type, not raw strings.
    """
    caps = provider.capabilities()
    assert isinstance(caps.provider_name, VoiceProviderName)


@pytest.mark.parametrize(
    "provider",
    _all_provider_instances(),
    ids=lambda p: type(p).__name__,
)
def test_capability_shape_matches_declared_support(provider):
    """If ``supports_design=False`` then design-only fields
    (``supported_design_models``, ``min_description_chars``,
    ``max_description_chars``) must be empty / None. If
    ``supports_clone=False`` then clone-only fields
    (``accepted_audio_mimes``, ``max_reference_bytes``,
    ``min_reference_seconds``, ``max_reference_seconds``) must
    be empty / None. Advertising constraints for an operation
    the adapter doesn't actually support misleads callers.
    """
    caps = provider.capabilities()
    if not caps.supports_design:
        assert caps.supported_design_models == (), (
            f"{type(provider).__name__} advertises "
            f"supports_design=False but ships design models: "
            f"{caps.supported_design_models}. Empty the field."
        )
        assert caps.min_description_chars is None
        assert caps.max_description_chars is None
    if not caps.supports_clone:
        assert caps.accepted_audio_mimes == (), (
            f"{type(provider).__name__} advertises "
            f"supports_clone=False but ships audio mimes: "
            f"{caps.accepted_audio_mimes}. Empty the field."
        )
        assert caps.max_reference_bytes is None
        assert caps.min_reference_seconds is None
        assert caps.max_reference_seconds is None
