"""NormalizationPipeline — composer, entry point, manifest assembler.

The pipeline takes a ``NormalizationSpec`` (raw provider bytes +
surface_profile_id + optional background_id override), threads
its ordered ``Stage`` list against a ``StageContext`` derived
from the ratified YAML config, and returns a
``NormalizationResult`` — the normalized PNG bytes + a
JSON-serializable manifest dict shaped for direct kwargs into
Django's ``record_normalization_manifest`` service.

Load-bearing invariants (§10.6, §17.6.a):

* **Deterministic.** Given identical spec + identical stage list
  + identical ratified YAMLs, ``run`` produces byte-for-byte
  identical ``normalized_bytes`` and a manifest with identical
  fields (execution_duration_ms excluded — the timing field is
  environmental).

* **Raw bytes preserved.** ``spec.raw_bytes`` is never mutated.
  A caller can persist ``spec.raw_bytes`` and
  ``result.normalized_bytes`` as two independent Assets on the
  Django side; the raw remains canonical evidence per §10.3.

* **Manifest completeness.** Every §10.6 field is populated on
  every run — even deferred stages record ``not_applied`` so
  Step 8/10 evidence can distinguish "the pipeline ran and did
  not include this stage yet" from "the pipeline crashed."

* **Honest failure.** A ``Stage`` that raises ``StageError`` is
  lifted into ``PipelineStageError`` — the pipeline never
  silently swallows a stage error and returns the input
  unchanged. If a stage decides not to run, it must say so
  explicitly (``status='skipped'`` with a reason).

Boundary discipline:

* This module owns bytes-in → stages → bytes-out + manifest
  payload.
* Django / shell owns ``Asset`` writes, ``GenerationRecord``
  linkage, and ``NormalizationManifest`` persistence via
  ``apps.identity.services.record_normalization_manifest``.
* This module never touches the filesystem, never talks to a
  provider, never emits log lines beyond DEBUG.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .config import (
    BackgroundFamily,
    SurfaceProfile,
    UnknownBackgroundIdError,
    get_background,
    load_background_family,
    load_surface_profile,
    resolve_background_for_profile,
)
from .png import BadPngError, dimensions_of
from .stages import Stage, StageContext, StageError, StageExecution


# ---- Errors -----------------------------------------------------


class PipelineError(Exception):
    """Base for pipeline-boundary errors."""


class PipelineInputError(PipelineError):
    """The spec was malformed — empty raw bytes, undecodable
    input, unknown profile_id or background_id.
    """


class PipelineStageError(PipelineError):
    """A stage raised ``StageError`` during execution. Carries
    the offending stage name for diagnosis. The pipeline lifts
    stage errors into this class so callers see one exception
    class at the pipeline boundary.
    """

    def __init__(self, message: str, *, stage_name: str) -> None:
        super().__init__(message)
        self.stage_name = stage_name


# ---- Spec + Result ----------------------------------------------


@dataclass(frozen=True, slots=True)
class NormalizationSpec:
    """One normalization request.

    ``raw_bytes`` is the provider's PNG output byte-for-byte.
    ``surface_profile_id`` names one of the ratified profiles
    (``compact``, ``presence``, ``studio``, ``conversation``,
    ``team_card``); the pipeline loads the YAML at run time.
    ``background_id_override`` lets a benchmark run pin a
    specific background rather than the profile default —
    recorded on the manifest verbatim per
    ``background_family_v1.yaml``'s ``reviewer_override``
    scope.

    ``schemas_root`` / ``background_family_path`` are test-only
    override hooks. Production callers leave them ``None`` and
    the loaders resolve to the ratified YAML locations.
    """

    raw_bytes: bytes
    surface_profile_id: str
    background_id_override: str | None = None
    schemas_root: Path | None = None
    background_family_path: Path | None = None


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    """Return shape of ``NormalizationPipeline.run``.

    ``normalized_bytes`` is the pipeline's output PNG —
    byte-for-byte identical for identical spec + pipeline.

    ``manifest`` is a JSON-serializable dict shaped for
    ``record_normalization_manifest(gen_record, **manifest)`` on
    the Django side. Contains every §10.6 field:

    * ``pipeline_version`` (str)
    * ``surface_profile_id`` (str)
    * ``surface_profile_version`` (int)
    * ``background_id`` (str)
    * ``stages_executed`` (list[dict])
    * ``stages_skipped`` (list[dict])
    * ``eye_line_adjustments`` (dict)
    * ``crop_metadata`` (dict)
    * ``execution_duration_ms`` (int)
    """

    normalized_bytes: bytes
    manifest: dict = field(default_factory=dict)


# ---- Pipeline ---------------------------------------------------


class NormalizationPipeline:
    """Ordered composition of ``Stage`` implementations.

    Instantiate with an explicit stage tuple; use
    ``build_default_v1_pipeline()`` for the canonical round-one
    order (defined at 7.c close). Tests instantiate with narrower
    tuples for isolation.
    """

    def __init__(self, stages: Sequence[Stage]) -> None:
        stages_tuple = tuple(stages)
        # Guard against accidental empty pipelines — a caller
        # composing dynamically and passing [] would produce a
        # result that superficially looks like a pass-through,
        # masking the mistake.
        if not stages_tuple:
            raise PipelineError(
                "NormalizationPipeline requires at least one stage; "
                "got an empty stage tuple. Use NoOpStage() explicitly "
                "if a pass-through pipeline is intended."
            )
        self._stages: tuple[Stage, ...] = stages_tuple

    @property
    def stages(self) -> tuple[Stage, ...]:
        return self._stages

    def pipeline_version(
        self,
        profile: SurfaceProfile,
        family: BackgroundFamily,
    ) -> str:
        """Compose the manifest's ``pipeline_version`` string.

        Format:
            ``pipeline_v1:<stage@version>|<stage@version>|...``
            ``|profile:<id>@<version>:<hash12>``
            ``|bg_family:v<version>:<hash12>``

        Load-bearing: the string reflects every input that could
        alter output bytes — stage list + profile identity +
        background family identity + short schema-hash prefix so
        an out-of-band YAML edit that forgets to bump ``version``
        still leaves a signal in evidence.
        """
        stage_parts = "|".join(
            f"{s.stage_name}@{s.stage_version}" for s in self._stages
        )
        return (
            f"pipeline_v1:{stage_parts}"
            f"|profile:{profile.profile_id}@{profile.version}:{profile.schema_hash[:12]}"
            f"|bg_family:v{family.schema_version}:{family.schema_hash[:12]}"
        )

    def run(self, spec: NormalizationSpec) -> NormalizationResult:
        """Execute the pipeline against ``spec``.

        Steps:

        1. Validate + decode input dimensions (raises
           ``PipelineInputError`` on empty / undecodable bytes).
        2. Load the surface profile + background family
           (raises ``PipelineInputError`` on unknown ids).
        3. Resolve the background from the profile or the
           spec's override.
        4. Build the initial ``StageContext``.
        5. Chain each stage; lift ``StageError`` into
           ``PipelineStageError`` with the offending stage name.
        6. Assemble the manifest dict; extract per-stage
           ``details`` into ``crop_metadata`` /
           ``eye_line_adjustments`` when those stages are
           present (7.b / 7.c populate these keys).
        7. Return ``NormalizationResult``.
        """
        # 1. Input validation (dimensions_of does the PNG-decode
        # check; empty bytes fail cleanly).
        if not spec.raw_bytes:
            raise PipelineInputError("spec.raw_bytes is empty")
        try:
            width_px, height_px = dimensions_of(spec.raw_bytes)
        except BadPngError as exc:
            raise PipelineInputError(f"raw_bytes is not a valid PNG: {exc!s}") from exc

        # 2. Load ratified config.
        try:
            profile = load_surface_profile(
                spec.surface_profile_id,
                schemas_root=spec.schemas_root,
            )
        except Exception as exc:
            raise PipelineInputError(
                f"cannot load surface profile {spec.surface_profile_id!r}: {exc!s}"
            ) from exc
        try:
            family = load_background_family(path=spec.background_family_path)
        except Exception as exc:
            raise PipelineInputError(
                f"cannot load background family: {exc!s}"
            ) from exc

        # 3. Resolve background.
        try:
            if spec.background_id_override is not None:
                background = get_background(family, spec.background_id_override)
            else:
                background = resolve_background_for_profile(family, profile)
        except UnknownBackgroundIdError as exc:
            raise PipelineInputError(str(exc)) from exc

        # 4. Initial context.
        ctx = StageContext(
            image_bytes=spec.raw_bytes,
            width_px=width_px,
            height_px=height_px,
            surface_profile=profile,
            background=background,
        )

        # 5. Chain stages.
        started = time.perf_counter()
        executions: list[StageExecution] = []
        for stage in self._stages:
            try:
                output = stage.apply(ctx)
            except StageError as exc:
                raise PipelineStageError(
                    f"stage {stage.stage_name!r} failed: {exc!s}",
                    stage_name=stage.stage_name,
                ) from exc
            executions.append(output.execution)
            ctx = output.new_context
        duration_ms = int((time.perf_counter() - started) * 1000)

        # 6. Manifest assembly.
        manifest = self._assemble_manifest(
            profile=profile,
            family=family,
            background_id=background.background_id,
            executions=executions,
            duration_ms=duration_ms,
        )

        # 7. Return.
        return NormalizationResult(
            normalized_bytes=ctx.image_bytes,
            manifest=manifest,
        )

    def _assemble_manifest(
        self,
        *,
        profile: SurfaceProfile,
        family: BackgroundFamily,
        background_id: str,
        executions: Sequence[StageExecution],
        duration_ms: int,
    ) -> dict:
        """Turn the pipeline's outputs into the manifest dict the
        Django ``record_normalization_manifest`` service consumes
        as kwargs. Every §10.6 field populated on every run.

        ``crop_metadata`` and ``eye_line_adjustments`` are hoisted
        from the corresponding stages' ``details`` when those
        stages are present. In 7.a they stay ``{}`` because only
        NoOp is registered; 7.b + 7.c populate them.
        """
        # 7.c architectural correction: eye-line evidence lives
        # inside CropStage(v2)'s ``details['eye_line_adjustments']``
        # nested block. The manifest hoists it into the top-level
        # ``eye_line_adjustments`` field and excludes it from
        # ``crop_metadata`` so the two fields don't duplicate.
        # CropStage(v1) at 7.b had no eye-line evidence at all;
        # both stage versions produce a valid empty-or-populated
        # manifest structure.
        return {
            "pipeline_version": self.pipeline_version(profile, family),
            "surface_profile_id": profile.profile_id,
            "surface_profile_version": profile.version,
            "background_id": background_id,
            "stages_executed": [
                _execution_to_dict(e) for e in executions if e.status == "executed"
            ],
            "stages_skipped": [
                _execution_to_dict(e) for e in executions if e.status != "executed"
            ],
            "eye_line_adjustments": _nested_from_crop(
                executions, "eye_line_adjustments"
            ),
            "crop_metadata": _crop_details_without_nested(
                executions, "eye_line_adjustments"
            ),
            "execution_duration_ms": duration_ms,
        }


def _execution_to_dict(e: StageExecution) -> dict:
    """Hand-serialize a StageExecution to a JSON-safe dict.

    Not ``dataclasses.asdict`` — that would recursively serialize
    nested dataclasses inside ``details`` if a stage put one
    there. Stages MUST place only JSON-primitive values in
    ``details``; this helper enforces the boundary by not
    reaching for a generic recursive serializer.
    """
    return {
        "stage_name": e.stage_name,
        "stage_version": e.stage_version,
        "status": e.status,
        "input_width_px": e.input_width_px,
        "input_height_px": e.input_height_px,
        "output_width_px": e.output_width_px,
        "output_height_px": e.output_height_px,
        "duration_ms": e.duration_ms,
        "details": dict(e.details),
    }


def _details_of(executions: Sequence[StageExecution], stage_name: str) -> dict:
    """Return the ``details`` dict of the named stage, or ``{}``
    if the stage is not in this pipeline. Kept for internal
    callers; ``_crop_details_without_nested`` +
    ``_nested_from_crop`` are the load-bearing helpers used by
    manifest assembly.
    """
    for e in executions:
        if e.stage_name == stage_name:
            return dict(e.details)
    return {}


def _crop_details_without_nested(
    executions: Sequence[StageExecution], nested_key: str
) -> dict:
    """Return CropStage's details minus one nested-key entry.
    Used to populate ``crop_metadata`` while excluding the
    ``eye_line_adjustments`` sub-block (which is hoisted to its
    own top-level manifest field).
    """
    for e in executions:
        if e.stage_name == "crop":
            return {k: v for k, v in e.details.items() if k != nested_key}
    return {}


def _nested_from_crop(
    executions: Sequence[StageExecution], nested_key: str
) -> dict:
    """Return the named nested block from CropStage's details.
    Empty dict when CropStage is not in the pipeline OR when the
    named block is absent (CropStage v1 at 7.b did not emit
    ``eye_line_adjustments``; v2 at 7.c does).
    """
    for e in executions:
        if e.stage_name == "crop":
            nested = e.details.get(nested_key, {})
            return dict(nested) if isinstance(nested, dict) else {}
    return {}
