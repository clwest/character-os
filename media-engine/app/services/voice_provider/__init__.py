"""VoiceDesignProvider abstraction — §19 Step 6 (SESSION 245).

Single Protocol per §17.4.a for voice-identity authoring. Step
6.a lands the Protocol + Mock adapter + drift verifier. The
Runway adapter (Step 6.b) wraps the reusable transport
functions ``runway_design_voice_transport`` (``audio_client.py``)
and ``runway_clone_voice_transport``
(``voice_clone_client.py``) — NOT the frozen
``/internal/voices/design/`` route handler, NOT the
``design_brand_voice()`` composition service. The lower-level
transport functions are the correct wrap point per the Step 5
finding that provider abstractions sit BELOW composition and
ABOVE transport.

SESSION 245 ratification anchors:

* The Protocol is narrow — three methods (``design_voice``,
  ``clone_voice``, ``capabilities``). Extending the Protocol
  requires re-ratification against §17.4.a.

* Two typed methods, not one discriminated union. Voice design
  (from text description) and voice cloning (from reference
  audio) share one lifecycle — authoring a durable voice
  identity — but the caller intent and required inputs are
  genuinely different. Two methods preserve that distinction
  without creating two separate Protocols.

* Provider-independence is mandatory (§17.4.a bullet 6). The
  orchestration layer never branches on provider name;
  capability inspection determines behavior.
  ``supports_design`` and ``supports_clone`` are separate
  capability flags so a future provider that supports only one
  operation reports its truth honestly.

* Capabilities are factual per §9.5 / §17.4.a bullet 4.
  Aesthetic claims ("natural", "expressive", "professional")
  do not belong on capabilities; a test file
  (``test_capabilities_are_factual.py``) enforces this via a
  field-name substring denylist.

* Adapter identity is preserved across mock/real routing (same
  discipline as PortraitProvider). Runway stays Runway even in
  force-mock; the routing decision lives INSIDE the adapter and
  is stamped as ``execution_mode_actual``. This preserves
  provider provenance on every ``GenerationRecord``.

* Mock is qualification plumbing, never qualification evidence.
  Records with ``provider=MOCK`` (from the Mock adapter) AND
  records with ``execution_mode_actual=MOCK`` (from a real
  adapter routing to mock) are BOTH non-qualifying. Two
  orthogonal filters — both must be applied to isolate
  qualification-quality evidence. Tests enforce this.

* ``AUTO`` never silently falls back to mock after a real
  request has begun and failed. Mock is an availability-routing
  decision, not an error-hiding strategy (SESSION 245
  ratification 4). Real failures raise
  ``VoiceProviderRequestFailedError``; the caller decides
  whether to retry, log, or degrade.

* Hard boundary to ``TextToSpeechProvider`` (§17.4.a bullets
  1–2). ``VoiceDesignProvider`` owns identity creation only —
  its responsibility ends once it returns a durable
  ``voice_id``. It NEVER synthesizes speech. The
  ``test_tts_boundary.py`` test proves the two packages have
  no import-graph coupling.

Frozen direct-call paths remain the Step 6 co-existence surface
(§17.9.a strangler discipline, applied to voice authoring):

* Media-engine routes: ``/internal/voices/design/``,
  ``/internal/voices/``, ``/api/characters/{id}/clone-voice``,
  ``/api/characters/{id}/apply-voice``,
  ``/api/characters/{id}/refresh-avatar-voice``,
  ``/api/characters/{id}/refresh-voice-preview``.
* Composition services: ``design_brand_voice()`` (audio_client),
  ``dub_*`` (audio_client).
* Django broker: ``MediaEngineClient.design_voice()``,
  ``.clone_voice()``, ``.change_avatar_voice()``.
* Django DRF endpoints on ``TeammateViewSet``: clone_voice,
  change_voice, create + perform_create_avatar,
  voice_presets.
* Composition primitives: ``DesignVoicePrimitive``,
  ``SynthesizeVoiceoverAudioPrimitive._resolve_voice_design_path``,
  ``starters.voice_design``.
* SPA: wizard Step 2 (VoiceCapture), teammate edit/rebake
  modals.
* Model: ``Teammate.voice_id``.

These consumers receive no new consumers and no new
provider-specific behavior during the Step 6 growth window.
Delegation of the frozen endpoints through this abstraction is
deferred to Step 11. A cleanup pass at that time will also
consolidate the transport-duplication currently present in the
``/internal/voices/design/`` route handler (which inlines the
same Runway POST + poll logic that
``runway_design_voice_transport`` already provides).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from ...config import Settings


# ---- Enums mirroring the Django substrate's TextChoices ---------
# String values MUST match ``GenerationProvider`` / ``ExecutionMode``
# / ``ExecutionModeActual`` in ``shell/apps/identity/models.py`` so a
# Django-side consumer can map a ``VoiceAuthoringResult`` field into
# the canonical enum by string equality. This is a duplicate-string
# discipline, not a shared module — media-engine is not permitted to
# import from ``shell`` per monorepo boundary conventions
# (CLAUDE.md).


class VoiceProviderName(str, Enum):
    """Media-engine mirror of the subset of ``GenerationProvider``
    values a VoiceDesignProvider adapter may stamp on its output.

    One Runway value spans both design and clone — see the pre-6.a
    migration docstring
    (``0008_step6_runway_voice_provider.py``) for the rationale.
    """

    RUNWAY_VOICE = "runway_voice"
    MOCK = "mock"


class ExecutionMode(str, Enum):
    """Mirror of ``ExecutionMode`` in the substrate. Set by the
    caller on ``VoiceDesignSpec`` / ``VoiceCloneSpec``.

    Same value set as ``portrait_provider.ExecutionMode`` — a
    duplicate for import-graph cleanliness, not a divergent
    concept. Both must match the Django enum by string equality.
    """

    FORCED_MOCK = "forced_mock"
    AUTO = "auto"
    REAL_REQUIRED = "real_required"
    UNAVAILABLE = "unavailable"


class ExecutionModeActual(str, Enum):
    """Mirror of ``ExecutionModeActual`` in the substrate. Set by
    the adapter on ``VoiceAuthoringResult``.

    Step 6 adapters emit ``REAL`` or ``MOCK`` only.
    ``MOCK_FALLBACK`` is reserved for a future explicit fallback
    opt-in; current adapters never emit it because
    ``REAL_REQUIRED`` raises rather than silently degrading, and
    ``AUTO`` never silently degrades on real failure (SESSION 245
    ratification 4).
    """

    REAL = "real"
    MOCK = "mock"
    MOCK_FALLBACK = "mock_fallback"


class VoiceOperation(str, Enum):
    """Which authoring lifecycle the caller invoked. Recorded on
    ``VoiceAuthoringResult.operation`` for downstream provenance
    filtering — the provider stamp alone (``RUNWAY_VOICE``) does
    not distinguish because Runway models both as one endpoint.
    """

    DESIGN = "design"
    CLONE = "clone"


# ---- Provider-shared dataclasses --------------------------------


@dataclass(frozen=True, slots=True)
class VoiceDesignSpec:
    """Shared voice-design request (parameter-based authoring).

    Every field represents a shared domain concept across the
    candidate provider space. Vendor-specific knobs stay out of
    the spec per §17.4.a bullet 6 and §17.9.a discipline.
    """

    description: str
    execution_mode: ExecutionMode
    name: str | None = None
    # Optional provider-model override. Adapter validates against
    # ``capabilities().supported_design_models`` and raises
    # ``UnsupportedModelError`` if unknown — never silently
    # replaced with the default (mirrors Step 5 constraint 6).
    provider_model: str | None = None
    # Mock-only. Real adapter paths IGNORE this. Mock code paths
    # (both the Mock adapter and real adapters routing to mock)
    # fold it into deterministic synthesis so tests can pin
    # reproducible voice_ids for identical specs.
    deterministic_seed: str | None = None


@dataclass(frozen=True, slots=True)
class VoiceCloneSpec:
    """Shared voice-clone request (reference-audio-based
    authoring).

    ``reference_audio`` is raw bytes; adapters validate MIME +
    size against their capabilities. Wizard context, teammate FK,
    workspace FK, and campaign FK stay OUT of the spec — the
    caller resolves those and is responsible for its own
    persistence.
    """

    reference_audio: bytes
    reference_mime: str
    execution_mode: ExecutionMode
    name: str | None = None
    # Mock-only. See VoiceDesignSpec.deterministic_seed.
    deterministic_seed: str | None = None


@dataclass(frozen=True, slots=True)
class VoiceProviderCapabilities:
    """Factual capability advertisement per §9.5 / §17.4.a bullet
    4.

    Adapter authors: add fields that describe *what the adapter
    can do*, not *how well it does it*. Aesthetic claims,
    quality ratings, and voice-similarity judgments are not
    capabilities — they are benchmark outcomes. A test in this
    package enforces the boundary via a field-name substring
    denylist.

    Design fields (``supported_design_models``,
    ``min_description_chars``, ``max_description_chars``) are
    empty / ``None`` if ``supports_design`` is False.
    Clone fields (``accepted_audio_mimes``,
    ``max_reference_bytes``, ``min_reference_seconds``,
    ``max_reference_seconds``) are empty / ``None`` if
    ``supports_clone`` is False.
    """

    provider_name: VoiceProviderName
    supports_design: bool
    supports_clone: bool
    supported_design_models: tuple[str, ...]
    accepted_audio_mimes: tuple[str, ...]
    max_reference_bytes: int | None
    min_reference_seconds: float | None
    max_reference_seconds: float | None
    min_description_chars: int | None
    max_description_chars: int | None
    max_authoring_seconds: int
    is_synchronous: bool
    execution_modes_supported: frozenset[ExecutionMode]


@dataclass(frozen=True, slots=True)
class VoiceAuthoringResult:
    """Adapter output for one voice-authoring call (design OR
    clone).

    Unified result type covers both operations — the durable
    output is the ``voice_id`` string in either case. Adapter
    emits the identifier + provenance evidence. Consumers own
    persistence (``CanonicalVoiceReference`` rows,
    ``GenerationRecord`` rows). This Protocol does not.

    ``provider_model`` is ``None`` for operations that have no
    model concept on the provider side (e.g. Runway clone does
    not accept or return a model). For design, it is the actual
    model the provider used (e.g.
    ``"eleven_multilingual_ttv_v2"`` for Runway design).
    """

    voice_id: str
    provider: VoiceProviderName
    operation: VoiceOperation
    execution_mode_actual: ExecutionModeActual
    provider_model: str | None = None
    preview_url: str | None = None
    # Snapshot of the request evidence shaped for direct use as
    # ``GenerationRecord.prompt_snapshot``. Adapter chooses what
    # to include; must be JSON-serializable. Provider-specific
    # response details live ONLY here — never as top-level
    # fields (§17.4.a bullet 3).
    prompt_snapshot: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: int = 0


# ---- Protocol ---------------------------------------------------


@runtime_checkable
class VoiceDesignProvider(Protocol):
    """Provider adapter for voice-identity authoring.

    Three methods, no more. Extending this Protocol requires
    re-ratification against §17.4.a and SESSION 245 scope-lock.

    Providers that do not support one operation raise
    ``VoiceOperationUnsupportedError`` AND declare
    ``supports_design=False`` or ``supports_clone=False`` in
    ``capabilities()``. Callers should check capabilities before
    dispatch. The mock adapter supports both (satisfies
    §17.4.a bullet 7); the Runway adapter (6.b) supports both.
    """

    def design_voice(self, spec: VoiceDesignSpec) -> VoiceAuthoringResult:
        """Author a voice identity from a text description.

        Adapter validates the spec (description length,
        provider_model if supplied) and raises loudly on
        mismatch, then branches on ``spec.execution_mode``:

        * ``FORCED_MOCK`` — always run the adapter's mock code
          path; emit ``execution_mode_actual=MOCK``.
        * ``AUTO`` — run real if the adapter is available (API
          key present, no force-mock override); otherwise run
          mock. Emit ``REAL`` or ``MOCK`` accordingly.
        * ``REAL_REQUIRED`` — run real if available; otherwise
          raise ``VoiceProviderUnavailableError``. Adapters
          never silently emit ``MOCK`` in this mode.
        * ``UNAVAILABLE`` — invalid on input; raises
          ``ValueError``.

        Adapters that do not support design raise
        ``VoiceOperationUnsupportedError`` regardless of
        execution mode.
        """
        ...

    def clone_voice(self, spec: VoiceCloneSpec) -> VoiceAuthoringResult:
        """Author a voice identity from a reference audio
        sample.

        Adapter validates the spec (MIME acceptance, byte size
        cap) and raises loudly on mismatch. Execution-mode
        semantics are identical to ``design_voice``.

        Adapters that do not support clone raise
        ``VoiceOperationUnsupportedError`` regardless of
        execution mode.
        """
        ...

    def capabilities(self) -> VoiceProviderCapabilities:
        """Factual capability introspection per §9.5. Called
        pre-request to check spec compatibility, and
        post-response as evidence.

        Adapters MUST NOT include aesthetic claims. A drift
        test in this package enforces the boundary.
        """
        ...


# ---- Errors -----------------------------------------------------


class VoiceProviderError(RuntimeError):
    """Base for voice provider errors."""


class VoiceProviderUnavailableError(VoiceProviderError):
    """Adapter cannot run the real provider (force-mock env,
    missing API key, etc.) and the caller specified
    ``REAL_REQUIRED``. Callers may retry with ``AUTO`` or
    ``FORCED_MOCK`` if degradation is acceptable.
    """


class VoiceOperationUnsupportedError(VoiceProviderError):
    """Adapter does not support the requested operation (design
    or clone). Callers should check ``capabilities()`` first —
    ``supports_design`` and ``supports_clone`` are advertised for
    exactly this reason.
    """


class UnsupportedModelError(VoiceProviderError):
    """``spec.provider_model`` is not in
    ``capabilities().supported_design_models``. Adapters raise
    rather than silently substituting the default (mirrors
    Step 5 constraint 6).
    """


class UnsupportedAudioFormatError(VoiceProviderError):
    """``spec.reference_mime`` is not in
    ``capabilities().accepted_audio_mimes``. Adapters raise
    rather than silently converting.
    """


class ReferenceAudioTooLargeError(VoiceProviderError):
    """``len(spec.reference_audio) > capabilities().max_reference_bytes``.
    Adapters raise rather than silently truncating.
    """


class VoiceProviderRequestFailedError(VoiceProviderError):
    """The real provider call returned a non-success response
    after retries. Carries the upstream error message and the
    HTTP status code (or ``None`` when the failure was a
    transport-layer exception like a timeout).

    Adapters raise this on real-provider failure. Callers may
    catch to log, retry with backoff, or degrade to mock — the
    Protocol takes no stance on retry policy above the transport
    layer. Adapters themselves NEVER silently degrade to mock
    after a real request has begun (SESSION 245 ratification 4).
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


# ---- Registry ---------------------------------------------------


def _registered_provider_names() -> tuple[str, ...]:
    """Names known to ``get_provider``. Full v1 registry after
    6.b (SESSION 245). Kept close to ``get_provider`` so the
    drift test can reason over it.
    """
    return (
        VoiceProviderName.MOCK.value,
        VoiceProviderName.RUNWAY_VOICE.value,
    )


def get_provider(name: str, settings: Settings) -> VoiceDesignProvider:
    """Look up a voice-authoring provider by name.

    Step 6.a shipped Mock; 6.b adds Runway. The v1 registry
    closes at these two adapters. Unknown names raise
    ``VoiceProviderError``.
    """
    if name == VoiceProviderName.MOCK.value:
        from .mock import MockVoiceProvider

        return MockVoiceProvider()
    if name == VoiceProviderName.RUNWAY_VOICE.value:
        from .runway import RunwayVoiceProvider

        return RunwayVoiceProvider(settings)
    raise VoiceProviderError(
        f"unknown voice provider {name!r}. "
        f"Registered: {list(_registered_provider_names())}"
    )


__all__ = [
    "ExecutionMode",
    "ExecutionModeActual",
    "ReferenceAudioTooLargeError",
    "UnsupportedAudioFormatError",
    "UnsupportedModelError",
    "VoiceAuthoringResult",
    "VoiceCloneSpec",
    "VoiceDesignProvider",
    "VoiceDesignSpec",
    "VoiceOperation",
    "VoiceOperationUnsupportedError",
    "VoiceProviderCapabilities",
    "VoiceProviderError",
    "VoiceProviderName",
    "VoiceProviderRequestFailedError",
    "VoiceProviderUnavailableError",
    "get_provider",
]
