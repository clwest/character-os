"""Run identity — unique run ID + deterministic run fingerprint.

Every benchmark harness invocation produces one ``RunIdentity``:

* ``run_id`` — unique immutable execution identity. Bearer of
  a UTC timestamp. Two invocations of the same configuration
  produce different ``run_id``s.

* ``run_fingerprint`` — deterministic sha256 hex of the
  reproducibility-relevant configuration. Two invocations of the
  same configuration MUST produce the same fingerprint even
  months apart.

Per SESSION 247 operator discipline #5:

    Running the same configuration tomorrow should produce a
    different ``run_id`` but the same ``run_fingerprint``.

Load-bearing rules:

* Fingerprint inputs MUST NOT include timing, random UUIDs,
  filesystem paths, or environment values. Tests enforce this by
  running the fingerprint twice at different simulated wall
  times and asserting equality, and by feeding a different
  filesystem-path override and asserting no change.

* Fingerprint inputs MUST include everything that could
  legitimately alter the harness's produced evidence:

    - fixture set + fixture content hashes
    - direction set
    - reference-purpose set (per branch)
    - provider set
    - provider model overrides (if any caller pins them)
    - surface profile set + per-profile version numbers
    - background family schema hash
    - normalization pipeline_version (via a caller-supplied
      surface-profile-agnostic surrogate: the pipeline-version
      composition string produced by
      ``NormalizationPipeline.pipeline_version(profile, family)``
      for a representative profile is not stable across profiles,
      so the fingerprint contains a MAP of profile → pipeline
      version)
    - prompt_builder version
    - execution mode
    - harness schema version

* Fingerprint is a hex sha256 string (64 chars). The
  ``run_id`` embeds only the first 12 characters of the
  fingerprint alongside the timestamp, since a full 64-char
  fingerprint in a filesystem-visible directory name would be
  noisy without adding uniqueness beyond the timestamp.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .fixture_loader import LoadedFixture
from .matrix import MatrixAxes, axes_fingerprint_input


class RunIdentityError(Exception):
    """Raised on internal contradictions during identity
    minting — e.g., ``kind`` outside the accepted set.
    """


ALLOWED_RUN_KINDS: tuple[str, ...] = ("bootstrap", "round")
"""Accepted ``kind`` prefixes for a minted run_id.

* ``bootstrap`` — §19.3 Step 8 bootstrap runs. Every Step 8
  invocation uses this.
* ``round`` — reserved for §19.3 Step 10 regeneration runs. The
  round-number tag is passed as a separate ``round_number``
  argument at mint time (Step 10's concern; documented here so
  the ``kind`` space is closed rather than open-ended).
"""


ALLOWED_EXECUTION_MODES: tuple[str, ...] = (
    "forced_mock",
    "auto",
    "real_required",
)
"""Execution modes the harness accepts. ``unavailable`` is a
provider-side signal per ``PortraitSpec.execution_mode`` docs
and is never a caller-selected mode."""


@dataclass(frozen=True, slots=True)
class RunIdentity:
    """Unique-per-invocation identity + deterministic
    reproducibility fingerprint for one benchmark run.

    * ``run_id`` — bearer of the timestamp. Unique per
      invocation. Filesystem-safe (only ASCII + underscores +
      hyphens).
    * ``run_fingerprint`` — 64-char sha256 hex of the
      reproducibility inputs. Two invocations with the same
      configuration produce the same value.
    * ``run_kind`` — one of ``ALLOWED_RUN_KINDS``.
    * ``created_at_utc`` — timestamp captured at mint time,
      recorded verbatim in evidence. Not included in the
      fingerprint.
    """

    run_id: str
    run_fingerprint: str
    run_kind: str
    created_at_utc: datetime


# ---- Fingerprint composition ---------------------------------


def _stable_json(obj: object) -> str:
    # Mirror fixture_loader._stable_json: ``default=str`` handles
    # YAML-native date/datetime instances that survive into
    # fingerprint payloads.
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        default=str,
    )


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_run_fingerprint(
    *,
    fixtures: Iterable[LoadedFixture],
    axes: MatrixAxes,
    provider_models: Mapping[str, str] | None,
    surface_profile_versions: Mapping[str, int],
    background_family_schema_hash: str,
    pipeline_versions: Mapping[str, str],
    prompt_builder_version: str,
    execution_mode: str,
    harness_schema_version: int,
) -> str:
    """Compute the deterministic ``run_fingerprint`` from the
    reproducibility-relevant inputs.

    All inputs are pure data. No timestamps, no UUIDs, no
    filesystem paths — those live only on ``run_id`` /
    ``created_at_utc`` and are excluded here.

    Arguments:

    * ``fixtures`` — the fixtures the harness will exercise.
      Order-insensitive: the fingerprint sorts by
      ``fixture_id`` before hashing so two callers passing the
      same fixtures in different orders converge.
    * ``axes`` — the ``MatrixAxes`` shaped by the caller. All
      axis fields are recorded as sorted lists so tuple order
      does not shift the fingerprint.
    * ``provider_models`` — optional map from provider → model
      identifier. Absent providers imply "adapter default,"
      which is recorded as the empty string to keep the
      fingerprint honest.
    * ``surface_profile_versions`` — map from profile_id →
      integer version number. Loaded from the ratified profile
      YAMLs (whose ``version`` field bumps on any content
      change).
    * ``background_family_schema_hash`` — the background family
      YAML's stable schema hash (from
      ``normalization.config.load_background_family().schema_hash``).
    * ``pipeline_versions`` — map from profile_id → pipeline
      version string (from
      ``NormalizationPipeline.pipeline_version(profile, family)``
      for that profile). Included per-profile because the
      pipeline version encoding includes profile-specific
      elements.
    * ``prompt_builder_version`` — from ``PROMPT_BUILDER_VERSION``.
    * ``execution_mode`` — one of ``ALLOWED_EXECUTION_MODES``.
    * ``harness_schema_version`` — from ``HARNESS_SCHEMA_VERSION``.
    """
    if execution_mode not in ALLOWED_EXECUTION_MODES:
        raise RunIdentityError(
            f"execution_mode {execution_mode!r} is not in the accepted "
            f"set {ALLOWED_EXECUTION_MODES}"
        )

    fixtures_input = sorted(
        [
            {
                "fixture_id": fx.fixture_id,
                "branch": fx.branch.value,
                "fixture_version": fx.fixture_version,
                "content_hash": fx.content_hash,
            }
            for fx in fixtures
        ],
        key=lambda d: d["fixture_id"],
    )

    axes_input = axes_fingerprint_input(axes)
    # Sort every axis-list here in addition to the axes module's
    # own ordering so downstream mutability of MatrixAxes cannot
    # silently alter the fingerprint.
    for k, v in list(axes_input.items()):
        if isinstance(v, list):
            axes_input[k] = sorted(v)
        elif isinstance(v, dict):
            axes_input[k] = {
                bk: sorted(bv) if isinstance(bv, list) else bv
                for bk, bv in sorted(v.items())
            }

    provider_models_input = {
        p: str(provider_models.get(p, "") if provider_models else "")
        for p in axes.providers
    }

    surface_profile_versions_input = {
        p: int(surface_profile_versions.get(p, 0))
        for p in axes.surface_profiles
    }

    pipeline_versions_input = {
        p: str(pipeline_versions.get(p, ""))
        for p in axes.surface_profiles
    }

    payload = {
        "harness_schema_version": int(harness_schema_version),
        "prompt_builder_version": str(prompt_builder_version),
        "execution_mode": execution_mode,
        "fixtures": fixtures_input,
        "axes": axes_input,
        "provider_models": provider_models_input,
        "surface_profile_versions": surface_profile_versions_input,
        "background_family_schema_hash": str(background_family_schema_hash),
        "pipeline_versions": pipeline_versions_input,
    }

    return _sha256_hex(_stable_json(payload))


# ---- Run-id minting ------------------------------------------


def _iso_utc(dt: datetime) -> str:
    """Return an ISO-8601 UTC timestamp with second precision,
    filesystem-friendly: ``YYYYMMDDTHHMMSSZ``.
    """
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def mint_run_id(
    fingerprint: str,
    *,
    kind: str = "bootstrap",
    now: datetime | None = None,
    round_number: int | None = None,
) -> str:
    """Compose the human-readable, filesystem-safe ``run_id``.

    Shape:

    * ``bootstrap`` — ``bootstrap_<timestamp>_<fp12>``
    * ``round``     — ``round_<n>_<timestamp>_<fp12>``

    Uses only the first 12 characters of the fingerprint for
    readability. The full fingerprint is preserved on the
    ``RunIdentity`` dataclass and inside the evidence tree.
    """
    if kind not in ALLOWED_RUN_KINDS:
        raise RunIdentityError(
            f"run kind {kind!r} is not in {ALLOWED_RUN_KINDS}"
        )
    if kind == "round" and round_number is None:
        raise RunIdentityError("kind='round' requires round_number")
    if kind == "bootstrap" and round_number is not None:
        raise RunIdentityError("kind='bootstrap' cannot carry round_number")
    if not (isinstance(fingerprint, str) and len(fingerprint) == 64):
        raise RunIdentityError(
            "fingerprint must be a 64-char sha256 hex string"
        )
    ts = _iso_utc(now or datetime.now(timezone.utc))
    fp12 = fingerprint[:12]
    if kind == "bootstrap":
        return f"bootstrap_{ts}_{fp12}"
    assert round_number is not None  # narrows for typechecker; guarded above
    return f"round_{int(round_number)}_{ts}_{fp12}"


def mint_run_identity(
    *,
    kind: str = "bootstrap",
    fixtures: Iterable[LoadedFixture],
    axes: MatrixAxes,
    provider_models: Mapping[str, str] | None,
    surface_profile_versions: Mapping[str, int],
    background_family_schema_hash: str,
    pipeline_versions: Mapping[str, str],
    prompt_builder_version: str,
    execution_mode: str,
    harness_schema_version: int,
    now: datetime | None = None,
    round_number: int | None = None,
) -> RunIdentity:
    """One-call convenience: compute the fingerprint, mint the
    run_id, and return a populated ``RunIdentity`` dataclass.

    ``fixtures`` is consumed twice (once for fingerprint, once
    unused here) — the caller passes a list / tuple, not a
    single-use iterator. Documented explicitly because a caller
    passing a generator would silently produce an empty fixture
    set on the second pass and a garbage fingerprint.
    """
    fixtures_seq = tuple(fixtures)
    fingerprint = compute_run_fingerprint(
        fixtures=fixtures_seq,
        axes=axes,
        provider_models=provider_models,
        surface_profile_versions=surface_profile_versions,
        background_family_schema_hash=background_family_schema_hash,
        pipeline_versions=pipeline_versions,
        prompt_builder_version=prompt_builder_version,
        execution_mode=execution_mode,
        harness_schema_version=harness_schema_version,
    )
    created = now or datetime.now(timezone.utc)
    run_id = mint_run_id(
        fingerprint, kind=kind, now=created, round_number=round_number,
    )
    return RunIdentity(
        run_id=run_id,
        run_fingerprint=fingerprint,
        run_kind=kind,
        created_at_utc=created,
    )


__all__ = [
    "ALLOWED_EXECUTION_MODES",
    "ALLOWED_RUN_KINDS",
    "RunIdentity",
    "RunIdentityError",
    "compute_run_fingerprint",
    "mint_run_id",
    "mint_run_identity",
]
