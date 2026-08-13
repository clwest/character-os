"""Cell → PortraitProvider dispatch boundary.

Constructs a ``PortraitSpec`` from a ``CellKey`` + ``LoadedFixture``
+ run identity, calls the resolved provider adapter, and normalizes
every possible outcome into a stable ``CellProviderResult``.

Load-bearing rules:

* **Provider-neutral prompt.** The final prompt handed to the adapter
  comes from ``prompt_builder.build_prompt(fixture, direction,
  purpose)`` — no provider argument, no provider-specific patching.
  The adapter's ``prompt_snapshot`` output is the harness's proof
  that the provider actually received this prompt.

* **Deterministic mock bytes.** The ``deterministic_seed`` handed to
  ``PortraitSpec`` is computed from
  ``sha256(run_fingerprint + cell_id)`` so two runs with the same
  fingerprint produce byte-identical mock output for the same cell.
  This is what makes operator discipline #9's determinism test
  meaningful.

* **Every provider error becomes an outcome.** Callers never see a
  ``PortraitProviderError`` from this module — they see a
  ``CellProviderResult`` with an outcome from the stable failure
  taxonomy (operator discipline #9). The runner acts on the outcome;
  raw bytes / provenance are preserved when available.

* **Aspect ratio comes from the surface profile.** The runner passes
  the SurfaceProfile's ``crop.aspect_ratio`` (loaded from ratified
  YAML) into the spec. No harness-side aspect fabrication.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Callable

from ...config import Settings
from ..normalization import SurfaceProfile
from ..portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProvider,
    PortraitProviderError,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderCapabilities,
    ProviderRequestFailedError,
    ProviderUnavailableError,
    UnsupportedAspectRatioError,
    UnsupportedModelError,
    get_provider,
)

from .fixture_loader import LoadedFixture
from .matrix import CellKey
from .prompt_builder import build_prompt


# ---- Cell provider-outcome taxonomy (operator discipline #9) ----

# String literals mirror the operator's ratified failure taxonomy.
# Kept as module-level constants so tests and the runner reference
# the same strings.

CELL_OUTCOME_SUCCESS: str = "success"
CELL_OUTCOME_PROVIDER_UNAVAILABLE: str = "provider_unavailable"
CELL_OUTCOME_PROVIDER_REQUEST_FAILED: str = "provider_request_failed"
CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY: str = "unsupported_provider_capability"
CELL_OUTCOME_NORMALIZATION_FAILED: str = "normalization_failed"
CELL_OUTCOME_INVALID_FIXTURE: str = "invalid_fixture"
CELL_OUTCOME_HARNESS_ERROR: str = "harness_error"

# Provider-side outcomes only (normalization outcomes are decided
# later by the runner).
PROVIDER_STAGE_OUTCOMES: frozenset[str] = frozenset(
    {
        CELL_OUTCOME_SUCCESS,
        CELL_OUTCOME_PROVIDER_UNAVAILABLE,
        CELL_OUTCOME_PROVIDER_REQUEST_FAILED,
        CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY,
    }
)


# ---- Result dataclass ----------------------------------------


@dataclass(frozen=True, slots=True)
class CellProviderResult:
    """Outcome of the provider stage for one cell.

    * ``outcome`` — always one of ``PROVIDER_STAGE_OUTCOMES``.
      Normalization outcomes are decided later by the runner.
    * ``raw_image_bytes`` — the exact bytes the provider returned.
      ``None`` when the provider stage did not produce bytes
      (unavailable / unsupported / request failed).
    * ``provider_response`` — full ``PortraitResult`` on success;
      ``None`` on failure. Runner extracts prompt_snapshot,
      elapsed_ms, execution_mode_actual, provider_model from here.
    * ``capabilities_snapshot`` — provider capabilities recorded at
      dispatch time. Populated on every path where the adapter was
      reachable (even failed ones), so evidence can capture
      capability-side facts for Step 9.
    * ``error_class`` / ``error_message`` — populated on failure
      paths only. Message is the exception's ``str()``; class is
      the exception's ``__class__.__name__``.
    * ``final_prompt`` — the exact prompt handed to the adapter.
      Recorded here even on failure so cross-provider prompt
      equality can be proved from the runner-level tests.
    * ``deterministic_seed`` — the seed handed to the adapter.
      Present on every path so a failure record still shows what
      was requested.
    """

    outcome: str
    raw_image_bytes: bytes | None
    provider_response: PortraitResult | None
    capabilities_snapshot: ProviderCapabilities | None
    error_class: str | None
    error_message: str | None
    final_prompt: str
    deterministic_seed: str
    requested_execution_mode: str
    provider_model_override: str | None


# ---- Public API ----------------------------------------------


ProviderFactory = Callable[[str, Settings], PortraitProvider]
"""Signature of ``portrait_provider.get_provider``. Runner accepts
an optional override so tests can inject stub providers without
touching the real registry."""


def default_provider_factory(name: str, settings: Settings) -> PortraitProvider:
    """Default: delegate to the ratified registry."""
    return get_provider(name, settings)


def _seed_for_cell(run_fingerprint: str, cell_id: str) -> str:
    """Deterministic seed from run_fingerprint + cell_id.

    ``sha256(run_fingerprint + '|' + cell_id).hex()[:32]``.
    The 32-hex-char slice is passed as ``PortraitSpec.deterministic_seed``
    — plenty of entropy for the mock adapter's color hashing.

    Load-bearing for operator discipline #9's determinism test:
    two runs with identical fingerprints produce identical seeds
    per cell, so mock byte output is byte-identical.
    """
    digest = hashlib.sha256(
        (run_fingerprint + "|" + cell_id).encode("utf-8")
    ).hexdigest()
    return digest[:32]


def dispatch_cell(
    *,
    cell: CellKey,
    fixture: LoadedFixture,
    surface_profile: SurfaceProfile,
    run_fingerprint: str,
    cell_id: str,
    execution_mode: str,
    provider_model_override: str | None,
    settings: Settings,
    provider_factory: ProviderFactory = default_provider_factory,
) -> CellProviderResult:
    """Execute one cell's provider stage.

    Never raises ``PortraitProviderError`` — every failure lands
    as a stable outcome on the returned ``CellProviderResult``.

    ``HarnessError``-class conditions (adapter registry lookup
    fails, unexpected exception type) surface as
    ``CELL_OUTCOME_HARNESS_ERROR``. The runner treats these as
    per-cell failures (not fatal-run) unless the runner has
    reason to escalate.
    """
    # 1. Build the provider-neutral final prompt via 8.a.
    final_prompt = build_prompt(fixture, cell.direction, cell.reference_purpose)

    # 2. Deterministic mock seed derived from fingerprint + cell.
    seed = _seed_for_cell(run_fingerprint, cell_id)

    # 3. Map operator-level execution_mode string → enum.
    try:
        exec_mode_enum = ExecutionMode(execution_mode)
    except ValueError as exc:
        return CellProviderResult(
            outcome=CELL_OUTCOME_HARNESS_ERROR,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=None,
            error_class="ValueError",
            error_message=(
                f"unknown execution_mode {execution_mode!r}: {exc!s}"
            ),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )

    # 4. Resolve the adapter.
    try:
        adapter = provider_factory(cell.provider, settings)
    except Exception as exc:  # PortraitProviderError or any surprise
        return CellProviderResult(
            outcome=CELL_OUTCOME_HARNESS_ERROR,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=None,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )

    # 5. Capture capabilities (usable even on failure paths).
    capabilities: ProviderCapabilities | None
    try:
        capabilities = adapter.capabilities()
    except Exception as exc:  # capabilities() should never raise
        return CellProviderResult(
            outcome=CELL_OUTCOME_HARNESS_ERROR,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=None,
            error_class=type(exc).__name__,
            error_message=(
                f"adapter.capabilities() raised for {cell.provider!r}: {exc!s}"
            ),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )

    # 6. Construct the spec.
    aspect_ratio = surface_profile.crop.aspect_ratio
    spec = PortraitSpec(
        prompt=final_prompt,
        aspect_ratio=aspect_ratio,
        execution_mode=exec_mode_enum,
        provider_model=provider_model_override,
        deterministic_seed=seed,
    )

    # 7. Call the adapter. Every ``PortraitProviderError`` maps to
    #    a stable outcome. Unknown exceptions become HARNESS_ERROR.
    try:
        response = adapter.generate_still_portrait(spec)
    except ProviderUnavailableError as exc:
        return CellProviderResult(
            outcome=CELL_OUTCOME_PROVIDER_UNAVAILABLE,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=capabilities,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )
    except UnsupportedAspectRatioError as exc:
        return CellProviderResult(
            outcome=CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=capabilities,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )
    except UnsupportedModelError as exc:
        return CellProviderResult(
            outcome=CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=capabilities,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )
    except ProviderRequestFailedError as exc:
        return CellProviderResult(
            outcome=CELL_OUTCOME_PROVIDER_REQUEST_FAILED,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=capabilities,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )
    except PortraitProviderError as exc:
        return CellProviderResult(
            outcome=CELL_OUTCOME_PROVIDER_REQUEST_FAILED,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=capabilities,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )
    except Exception as exc:
        # Truly unexpected — harness-level defect surfaces as a
        # HARNESS_ERROR outcome for this cell. Runner may escalate.
        return CellProviderResult(
            outcome=CELL_OUTCOME_HARNESS_ERROR,
            raw_image_bytes=None,
            provider_response=None,
            capabilities_snapshot=capabilities,
            error_class=type(exc).__name__,
            error_message=str(exc),
            final_prompt=final_prompt,
            deterministic_seed=seed,
            requested_execution_mode=execution_mode,
            provider_model_override=provider_model_override,
        )

    return CellProviderResult(
        outcome=CELL_OUTCOME_SUCCESS,
        raw_image_bytes=response.image_bytes,
        provider_response=response,
        capabilities_snapshot=capabilities,
        error_class=None,
        error_message=None,
        final_prompt=final_prompt,
        deterministic_seed=seed,
        requested_execution_mode=execution_mode,
        provider_model_override=provider_model_override,
    )


# ---- Capability snapshot serialization ----------------------


def capabilities_to_dict(caps: ProviderCapabilities) -> dict:
    """Return a JSON-serializable snapshot of the adapter's
    ratified capability advertisement. Consumed by the runner
    to embed on candidate.json evidence."""
    return {
        "provider_name": caps.provider_name.value,
        "provider_model": caps.provider_model,
        "supported_models": list(caps.supported_models),
        "supported_aspect_ratios": list(caps.supported_aspect_ratios),
        "max_prompt_length": caps.max_prompt_length,
        "is_deterministic": caps.is_deterministic,
        "execution_modes_supported": sorted(
            m.value for m in caps.execution_modes_supported
        ),
    }


def execution_mode_actual_str(v: ExecutionModeActual) -> str:
    return v.value


def provider_name_str(v: PortraitProviderName) -> str:
    return v.value


__all__ = [
    "CELL_OUTCOME_HARNESS_ERROR",
    "CELL_OUTCOME_INVALID_FIXTURE",
    "CELL_OUTCOME_NORMALIZATION_FAILED",
    "CELL_OUTCOME_PROVIDER_REQUEST_FAILED",
    "CELL_OUTCOME_PROVIDER_UNAVAILABLE",
    "CELL_OUTCOME_SUCCESS",
    "CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY",
    "CellProviderResult",
    "PROVIDER_STAGE_OUTCOMES",
    "ProviderFactory",
    "capabilities_to_dict",
    "default_provider_factory",
    "dispatch_cell",
    "execution_mode_actual_str",
    "provider_name_str",
]
