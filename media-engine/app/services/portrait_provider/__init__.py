"""PortraitProvider abstraction — §19 Step 5 (SESSION 244).

Single Protocol per §17.9.a for still-portrait generation. Step
5.a lands the Protocol + Mock adapter + drift verifier. Stability
(Step 5.b) and Runway (Step 5.c) adapters land in subsequent
sub-slices under the same scope-lock.

SESSION 244 ratification anchors:

* The Protocol is intentionally narrow — three methods
  (``generate_still_portrait``, ``capabilities``,
  ``provider_name``). Provider health, pricing, normalization,
  persistence, qualification scoring, prompt construction, and
  benchmark concepts are OUT of scope. Extending the Protocol
  requires re-ratification.

* ``PortraitSpec`` describes the shared portrait-generation
  domain request, not a union of vendor-specific knobs. Fields
  excluded from Step 5 on defensibility grounds:
  ``reference_image_bytes`` (not used by the currently-shipped
  Runway ``gen4_image`` path or the Stability service function)
  and ``negative_prompt`` (Stability-only concept currently
  computed as a purpose-derived default; caller override not
  needed until a second provider exposes it). If future
  benchmark evidence justifies either field, it is added from
  evidence, not anticipation.

* ``ProviderCapabilities`` is factual per §9.5. Aesthetic
  claims ("cinematic naturalistic", "identity stable",
  "quality", "expressive") do not belong on capabilities; a
  test file (``test_capabilities_are_factual.py``) enforces
  this via a field-name substring denylist.

* Adapter identity is preserved across mock/real routing.
  Unlike the realtime ``get_provider`` (which returns the Mock
  provider when ``settings.runway_mock`` is True), portrait
  adapters retain their identity — Stability stays Stability
  even in force-mock. The routing decision lives INSIDE the
  adapter and is stamped as ``execution_mode_actual``. This
  preserves provider provenance in every ``GenerationRecord``.

* Mock is qualification plumbing, never qualification evidence.
  Records with ``provider=MOCK`` (from the Mock adapter) AND
  records with ``execution_mode_actual=MOCK`` (from a real
  adapter routing to mock) are BOTH non-qualifying. Two
  orthogonal filters — both must be applied to isolate
  qualification-quality evidence. Tests enforce this.

Frozen direct-call paths remain the Step 5 co-existence
surface: ``/internal/portrait/``, ``/internal/image_stability/``,
and ``MediaEngineClient.create_portrait`` are unchanged and
receive no new consumers per §17.9.a's freeze rule. Delegation
of those endpoints through this abstraction is deferred to
Step 11.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from ...config import Settings


# ---- Enums mirroring the Django substrate's TextChoices ---------
# String values MUST match ``GenerationProvider`` / ``ExecutionMode``
# / ``ExecutionModeActual`` in ``shell/apps/identity/models.py`` so a
# Django-side consumer can map a ``PortraitResult`` field into the
# canonical enum by string equality. This is a duplicate-string
# discipline, not a shared module — media-engine is not permitted to
# import from ``shell`` per monorepo boundary conventions
# (CLAUDE.md).


class PortraitProviderName(str, Enum):
    """Media-engine mirror of the subset of ``GenerationProvider``
    values a PortraitProvider adapter may stamp on its output.
    """

    RUNWAY_STILL_PORTRAIT = "runway_still_portrait"
    STABILITY_STILL = "stability_still"
    MOCK = "mock"


class ExecutionMode(str, Enum):
    """Mirror of ``ExecutionMode`` in the substrate. Set by the
    caller on ``PortraitSpec``.
    """

    FORCED_MOCK = "forced_mock"
    AUTO = "auto"
    REAL_REQUIRED = "real_required"
    UNAVAILABLE = "unavailable"


class ExecutionModeActual(str, Enum):
    """Mirror of ``ExecutionModeActual`` in the substrate. Set by
    the adapter on ``PortraitResult``.

    Step 5 adapters emit ``REAL`` or ``MOCK`` only.
    ``MOCK_FALLBACK`` is reserved for a future explicit fallback
    opt-in; current adapters never emit it because
    ``REAL_REQUIRED`` raises rather than silently degrading
    (SESSION 244 ratification constraint 3).
    """

    REAL = "real"
    MOCK = "mock"
    MOCK_FALLBACK = "mock_fallback"


# ---- Provider-shared dataclasses --------------------------------


@dataclass(frozen=True, slots=True)
class PortraitSpec:
    """Shared portrait-generation request.

    Every field represents a shared domain concept across the
    candidate provider space. Vendor-specific knobs stay out of
    the spec per §17.9.a discipline and SESSION 244 ratification
    constraint 5.
    """

    prompt: str
    aspect_ratio: str
    execution_mode: ExecutionMode
    # Optional provider-model override. Adapter validates against
    # ``capabilities().supported_models`` and raises
    # ``UnsupportedModelError`` if unknown — never silently
    # replaced with the default (SESSION 244 constraint 6).
    provider_model: str | None = None
    # Mock-only. Real adapter paths IGNORE this. Mock code paths
    # (both the Mock adapter and real adapters routing to mock)
    # fold it into the deterministic synthesis so tests can pin
    # reproducible bytes for identical seeds.
    deterministic_seed: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Factual capability advertisement per §9.5.

    Adapter authors: add fields that describe *what the adapter
    can do*, not *how well it does it*. Aesthetic claims,
    quality ratings, and identity-stability judgments are not
    capabilities — they are benchmark outcomes. A test in this
    package enforces the boundary via a field-name substring
    denylist.
    """

    provider_name: PortraitProviderName
    provider_model: str
    supported_models: tuple[str, ...]
    supported_aspect_ratios: tuple[str, ...]
    max_prompt_length: int | None
    is_deterministic: bool
    execution_modes_supported: frozenset[ExecutionMode]


@dataclass(frozen=True, slots=True)
class PortraitResult:
    """Adapter output for one still-portrait generation call.

    Adapter emits bytes + provenance evidence. Consumers own
    persistence (asset writes, ``GenerationRecord`` rows,
    ``NormalizationManifest`` rows). This Protocol does not.
    """

    image_bytes: bytes
    provider: PortraitProviderName
    provider_model: str
    execution_mode_actual: ExecutionModeActual
    # Snapshot of the request evidence shaped for direct use as
    # ``GenerationRecord.prompt_snapshot``. Adapter chooses what
    # to include; must be JSON-serializable.
    prompt_snapshot: dict = field(default_factory=dict)
    elapsed_ms: int = 0


# ---- Protocol ---------------------------------------------------


@runtime_checkable
class PortraitProvider(Protocol):
    """Provider adapter for still-portrait generation.

    Three methods, no more. Extending this Protocol requires
    re-ratification against §17.9.a and SESSION 244 scope-lock.
    """

    def generate_still_portrait(self, spec: PortraitSpec) -> PortraitResult:
        """Execute one still-portrait generation request.

        Adapter validates the spec first (aspect ratio,
        provider_model if supplied) and raises loudly on
        mismatch, then branches on ``spec.execution_mode``:

        * ``FORCED_MOCK`` — always run the adapter's mock code
          path; emit ``execution_mode_actual=MOCK``.
        * ``AUTO`` — run real if the adapter is available (API
          key present, no force-mock override); otherwise run
          mock. Emit ``REAL`` or ``MOCK`` accordingly.
        * ``REAL_REQUIRED`` — run real if available; otherwise
          raise ``ProviderUnavailableError``. Adapters never
          silently emit ``MOCK`` in this mode.
        * ``UNAVAILABLE`` — invalid on input; raises
          ``ValueError``.
        """
        ...

    def capabilities(self) -> ProviderCapabilities:
        """Factual capability introspection per §9.5. Called
        pre-request to check spec compatibility, and
        post-response as evidence.

        Adapters MUST NOT include aesthetic claims. A drift
        test in this package enforces the boundary.
        """
        ...

    def provider_name(self) -> PortraitProviderName:
        """The provenance value the adapter stamps on its
        results. Constant per adapter. Consumers use this to
        write ``GenerationRecord.provider``.
        """
        ...


# ---- Errors -----------------------------------------------------


class PortraitProviderError(RuntimeError):
    """Base for portrait provider errors."""


class ProviderUnavailableError(PortraitProviderError):
    """Adapter cannot run the real provider (force-mock env,
    missing API key, etc.) and the caller specified
    ``REAL_REQUIRED``. Callers may retry with ``AUTO`` or
    ``FORCED_MOCK`` if degradation is acceptable.
    """


class UnsupportedModelError(PortraitProviderError):
    """``spec.provider_model`` is not in
    ``capabilities().supported_models``. Adapters raise rather
    than silently substituting the default (SESSION 244
    constraint 6).
    """


class UnsupportedAspectRatioError(PortraitProviderError):
    """``spec.aspect_ratio`` is not in
    ``capabilities().supported_aspect_ratios``. Adapters raise
    rather than silently substituting.
    """


class ProviderRequestFailedError(PortraitProviderError):
    """The real provider call returned a non-success response
    after retries. Carries the upstream error message and the
    HTTP status code (or ``None`` when the failure was a
    transport-layer exception like a timeout).

    Adapters raise this on real-provider failure. Callers may
    catch to log, retry with backoff, or degrade to mock — the
    Protocol takes no stance on retry policy above the
    transport layer.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---- Registry ---------------------------------------------------


def _registered_provider_names() -> tuple[str, ...]:
    """Names known to ``get_provider``. Full v1 registry after
    5.c. Kept close to ``get_provider`` so the drift test in
    5.d can reason over it.
    """
    return (
        PortraitProviderName.MOCK.value,
        PortraitProviderName.STABILITY_STILL.value,
        PortraitProviderName.RUNWAY_STILL_PORTRAIT.value,
    )


def get_provider(name: str, settings: Settings) -> PortraitProvider:
    """Look up a portrait provider by name.

    Step 5.a shipped Mock; 5.b added Stability; 5.c adds Runway
    still-portrait. The v1 registry closes at these three
    adapters. Unknown names raise ``PortraitProviderError``.
    """
    if name == PortraitProviderName.MOCK.value:
        from .mock import MockStillPortraitProvider

        return MockStillPortraitProvider()
    if name == PortraitProviderName.STABILITY_STILL.value:
        from .stability import StabilityStillPortraitProvider

        return StabilityStillPortraitProvider(settings)
    if name == PortraitProviderName.RUNWAY_STILL_PORTRAIT.value:
        from .runway import RunwayStillPortraitProvider

        return RunwayStillPortraitProvider(settings)
    raise PortraitProviderError(
        f"unknown portrait provider {name!r}. "
        f"Registered: {list(_registered_provider_names())}"
    )


__all__ = [
    "ExecutionMode",
    "ExecutionModeActual",
    "PortraitProvider",
    "PortraitProviderError",
    "PortraitProviderName",
    "PortraitResult",
    "PortraitSpec",
    "ProviderCapabilities",
    "ProviderRequestFailedError",
    "ProviderUnavailableError",
    "UnsupportedAspectRatioError",
    "UnsupportedModelError",
    "get_provider",
]
