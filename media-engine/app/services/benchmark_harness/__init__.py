"""Benchmark harness — §19 Step 8 (SESSION 247).

Repository-first, file-based portrait-qualification bootstrap
harness. Consumes the canonical fixture set, the
``PortraitProvider`` abstraction, and the normalization pipeline
exclusively; produces immutable candidate evidence under the
ratified §17.8.a fixture-run directory tree; makes NO
qualification decision itself.

Central Step 8 question (per SESSION 247 operator framing):

    Can the benchmark harness produce immutable, reproducible,
    provider-neutral two-tier evidence from the ratified fixture
    matrix without making any qualification decision itself?

Load-bearing boundary discipline (operator-locked in
SESSION 247, F-8.1):

* Step 8 does NOT write ``CharacterIdentityVersion`` /
  ``GenerationRecord`` / ``NormalizationManifest`` rows to the
  Django substrate. Every candidate is preserved as file
  evidence shaped so Step 9 can promote selected candidates
  into canonical substrate records without reinterpretation.

* Step 8 does NOT populate ``bootstrap/references/`` — that is
  Step 9's job after human selection.

* Step 8 does NOT emit any scoring vocabulary — no trust score,
  no aesthetic score, no pass/fail qualification, no preferred
  provider, no selected candidate. Those are downstream.

* Step 8 does NOT special-case any provider. Runway's
  1280x720-only real-input constraint (surfaced in SESSION 246
  as a first-class Step 8/10 finding) emerges naturally from
  the normal cell runner: normalization raises
  ``input_smaller_than_output`` deterministically for
  portrait-oriented profiles, and the harness records that
  refusal as evidence. If the same failure occurs for another
  provider tomorrow, the same generic machinery describes it.

Sub-slice ledger:

* 8.a — fixture loader, vocabulary, prompt-builder v1, matrix
  axes, RunIdentity split of run_id/run_fingerprint.
* 8.b (this slice) — evidence paths + atomic evidence writer +
  provider dispatcher + runner + CLI. Executes the matrix
  through PortraitProvider + NormalizationPipeline and writes
  immutable two-tier evidence under the ratified §17.8.a
  layout. No qualification decisions.
* 8.c — executable-evidence + replay + guardrail suite;
  handoff; INVENTORY regen; Step 9 remains gated.
"""
from __future__ import annotations

from .evidence_paths import (
    EvidenceLayout,
    RATIFIED_ARTIFACT_BUCKETS,
    cell_id_for,
    is_ratified_artifact_bucket,
)
from .evidence_writer import (
    ArtifactConflictError,
    EvidenceWriteError,
    EvidenceWriter,
    RunIdConflictError,
    WrittenArtifact,
    canonical_json_bytes,
    sha256_hex,
)
from .fixture_loader import (
    FixtureError,
    FixtureNotFoundError,
    FixtureSchemaError,
    LoadedBranchSchema,
    LoadedFixture,
    default_fixtures_root,
    default_schemas_root,
    load_branch_schema,
    load_fixture,
    load_ratified_fixtures,
)
from .matrix import (
    BACKGROUND_IS_DERIVED_FROM_PROFILE,
    CellKey,
    MatrixAxes,
    axes_fingerprint_input,
    expand_matrix,
)
from .prompt_builder import (
    PROMPT_BUILDER_VERSION,
    PromptBuilderError,
    build_prompt,
)
from .provider_dispatcher import (
    CELL_OUTCOME_HARNESS_ERROR,
    CELL_OUTCOME_INVALID_FIXTURE,
    CELL_OUTCOME_NORMALIZATION_FAILED,
    CELL_OUTCOME_PROVIDER_REQUEST_FAILED,
    CELL_OUTCOME_PROVIDER_UNAVAILABLE,
    CELL_OUTCOME_SUCCESS,
    CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY,
    CellProviderResult,
    PROVIDER_STAGE_OUTCOMES,
    ProviderFactory,
    capabilities_to_dict,
    default_provider_factory,
    dispatch_cell,
)
from .replay import (
    ReplayCellResult,
    ReplayError,
    ReplayRunResult,
    SourceEvidenceMalformed,
    SourceRawHashMismatch,
    SourceRunNotFound,
    replay_same_raw_input,
)
from .runner import CellRunResult, RunResult, run_matrix
from .run_identity import (
    ALLOWED_EXECUTION_MODES,
    ALLOWED_RUN_KINDS,
    RunIdentity,
    RunIdentityError,
    compute_run_fingerprint,
    mint_run_id,
    mint_run_identity,
)
from .version import HARNESS_SCHEMA_VERSION
from .vocabulary import (
    BRANCH_TO_KIND,
    BRANCH_TO_PURPOSES,
    HumanPortraitReferencePurpose,
    IdentityBranch,
    NonHumanCanonicalReferencePurpose,
    PROVIDER_MOCK,
    PROVIDER_RUNWAY_STILL_PORTRAIT,
    PROVIDER_STABILITY_STILL,
    RATIFIED_FIXTURES,
    RATIFIED_PROVIDERS,
    RATIFIED_SURFACE_PROFILES,
    ReferenceKind,
    RenderingDirectionHypothesis,
    kind_for_branch,
    purposes_for_branch,
)

__all__ = [
    # version
    "HARNESS_SCHEMA_VERSION",
    # vocabulary
    "BRANCH_TO_KIND",
    "BRANCH_TO_PURPOSES",
    "HumanPortraitReferencePurpose",
    "IdentityBranch",
    "NonHumanCanonicalReferencePurpose",
    "PROVIDER_MOCK",
    "PROVIDER_RUNWAY_STILL_PORTRAIT",
    "PROVIDER_STABILITY_STILL",
    "RATIFIED_FIXTURES",
    "RATIFIED_PROVIDERS",
    "RATIFIED_SURFACE_PROFILES",
    "ReferenceKind",
    "RenderingDirectionHypothesis",
    "kind_for_branch",
    "purposes_for_branch",
    # fixture loader
    "FixtureError",
    "FixtureNotFoundError",
    "FixtureSchemaError",
    "LoadedBranchSchema",
    "LoadedFixture",
    "default_fixtures_root",
    "default_schemas_root",
    "load_branch_schema",
    "load_fixture",
    "load_ratified_fixtures",
    # matrix
    "BACKGROUND_IS_DERIVED_FROM_PROFILE",
    "CellKey",
    "MatrixAxes",
    "axes_fingerprint_input",
    "expand_matrix",
    # prompt builder
    "PROMPT_BUILDER_VERSION",
    "PromptBuilderError",
    "build_prompt",
    # run identity
    "ALLOWED_EXECUTION_MODES",
    "ALLOWED_RUN_KINDS",
    "RunIdentity",
    "RunIdentityError",
    "compute_run_fingerprint",
    "mint_run_id",
    "mint_run_identity",
    # evidence paths + writer (8.b)
    "EvidenceLayout",
    "RATIFIED_ARTIFACT_BUCKETS",
    "cell_id_for",
    "is_ratified_artifact_bucket",
    "ArtifactConflictError",
    "EvidenceWriteError",
    "EvidenceWriter",
    "RunIdConflictError",
    "WrittenArtifact",
    "canonical_json_bytes",
    "sha256_hex",
    # provider dispatcher (8.b)
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
    # runner (8.b)
    "CellRunResult",
    "RunResult",
    "run_matrix",
    # replay (8.c)
    "ReplayCellResult",
    "ReplayError",
    "ReplayRunResult",
    "SourceEvidenceMalformed",
    "SourceRawHashMismatch",
    "SourceRunNotFound",
    "replay_same_raw_input",
]
