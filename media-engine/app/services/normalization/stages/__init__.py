"""Stage protocol + registry for the normalization pipeline.

A ``Stage`` is one step in the ordered pipeline. Each stage is
independently versioned so the manifest's ``pipeline_version``
composition can prove exactly which stage bodies produced a
given normalized artifact (§10.7).

Contract:

* Stages are **pure**. Given identical ``StageContext``, a
  stage's ``apply`` must produce byte-for-byte identical
  ``StageOutput``. Any randomness is a defect. Stages that
  wrap a third-party primitive (rembg / opencv / etc.) inherit
  its determinism guarantees; if the primitive is
  nondeterministic on the target platform, the stage surfaces
  that as ``StageError`` rather than papering over it.

* Stages never mutate the input context. ``StageContext`` is
  frozen; every stage returns a new one. Raw bytes flow
  through the pipeline unchanged past a stage that does not
  touch the image (``NoOpStage``, and any stage that returns
  ``status='not_applied'``).

* Stage evidence is factual, not aesthetic. ``StageExecution``
  carries dimensions, method identifiers, and factual
  parameters — never quality judgments. "crop_quality: excellent"
  is forbidden; the crop-box coordinates are the evidence.

* Registered stages appear in ``_REGISTERED_STAGE_NAMES`` so
  the drift verifier can enumerate them at CI time. Adding a
  new stage without registering it trips the audit.

Registry ratchet (7.c): ``noop`` + ``crop`` + ``framing`` +
``background_replacement``. **No standalone ``eye_line``
stage** — SESSION 246 7.c inspection surfaced that eye-line
positioning after Framing has zero legal headroom under the
no-padding invariant, so eye-line was folded into CropStage
(v1 → v2). See ``crop.py`` module docstring for the
architectural rationale.

The default v1 pipeline chain after 7.c is
``(CropStage(v2), FramingStage(v1), BackgroundReplacementStage(v1))``
— the ``noop`` stage remains a registered harness exerciser
and is **not** part of the default chain (per SESSION 246
operator discipline: "Do not let NoOp survive accidentally").
See ``tests/normalization/test_pipeline.py`` for end-to-end
composition against all five ratified surface profiles × all
five ratified backgrounds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Protocol, runtime_checkable

from ..config import Background, SurfaceProfile


# ---- Stage-shared errors ----------------------------------------


class StageError(Exception):
    """Base for stage-authored errors. The pipeline lifts these
    into ``PipelineStageError`` so callers see one exception
    class per pipeline boundary.
    """


class StageDeterminismError(StageError):
    """A stage detected nondeterminism in a primitive it depends
    on (repeat invocation produced different bytes). Rather than
    silently masking, the stage raises and the pipeline surfaces
    the contradiction — per SESSION 246 operator discipline:
    "surface that as a contract contradiction rather than
    weakening the test silently."
    """


# ---- Frozen dataclasses -----------------------------------------


@dataclass(frozen=True, slots=True)
class StageContext:
    """State passed between pipeline stages.

    ``image_bytes`` is canonical PNG. Stages that transform the
    image must decode → transform → re-encode via the ``png``
    helpers to preserve determinism.

    ``width_px`` / ``height_px`` describe the CURRENT image
    (not the surface profile's target). Stages consult these
    for input-dimension logging; the profile's ``output``
    section describes the destination.
    """

    image_bytes: bytes
    width_px: int
    height_px: int
    surface_profile: SurfaceProfile
    background: Background


@dataclass(frozen=True, slots=True)
class StageExecution:
    """One row in the manifest's stages_executed / stages_skipped
    list.

    ``status`` semantics (per SESSION 246 operator discipline —
    factual, no aesthetic judgment):

    * ``executed`` — the stage ran a real transform.
    * ``not_applied`` — the stage is in the pipeline but did no
      work in this run. Reserved for future stages that are
      configuration-gated (e.g., a lighting stage that skips
      when no adjustment is warranted). Round-one usage: the
      ``NoOpStage`` harness exerciser.
    * ``skipped`` — the stage was in the pipeline but refused
      to run (e.g., input dimensions incompatible). Carries a
      reason in ``details['skip_reason']``.

    ``details`` is a JSON-serializable dict of stage-specific
    factual evidence. Examples: crop box coords, eye-line
    method identifier (``bbox_center_proxy`` vs. a future
    real detector), background source (``procedural_v1``),
    subject-detection method (``deterministic_center_proxy``).
    Never quality claims.
    """

    stage_name: str
    stage_version: int
    status: str
    input_width_px: int
    input_height_px: int
    output_width_px: int
    output_height_px: int
    duration_ms: int
    details: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StageOutput:
    """What a stage returns: the context to feed the next stage
    plus the audit row describing what happened.
    """

    new_context: StageContext
    execution: StageExecution


# ---- Stage Protocol ---------------------------------------------


@runtime_checkable
class Stage(Protocol):
    """One versioned step in the normalization pipeline.

    Implementations expose ``stage_name`` and ``stage_version``
    as class-level constants so the pipeline-version composition
    and the drift verifier can enumerate them without
    instantiating.
    """

    stage_name: ClassVar[str]
    stage_version: ClassVar[int]

    def apply(self, ctx: StageContext) -> StageOutput:
        """Execute this stage against ``ctx`` and return the new
        context + audit row. MUST NOT mutate ``ctx``. MUST be
        deterministic given identical input.
        """
        ...


# ---- Registry (drift-visible enumeration) -----------------------


def _registered_stage_names() -> tuple[str, ...]:
    """Names known to ``get_stage``. Full v1 registry at 7.c
    close is ``(noop, crop, framing, background_replacement)``
    — no ``eye_line`` entry (folded into CropStage v2 per
    SESSION 246 7.c architectural correction). Kept close to
    ``get_stage`` so the drift verifier can enumerate without
    importing every stage module.
    """
    return ("noop", "crop", "framing", "background_replacement")


def get_stage(name: str) -> Stage:
    """Look up a stage class by name and return an instance.

    Tests instantiate individual stages directly for isolation
    when a stage's constructor takes arguments (none of the
    round-one stages do; this helper suffices).

    Unknown names raise ``StageError`` — never silently return a
    NoOp or fallback stage.
    """
    if name == "noop":
        from .noop import NoOpStage

        return NoOpStage()
    if name == "crop":
        from .crop import CropStage

        return CropStage()
    if name == "framing":
        from .framing import FramingStage

        return FramingStage()
    if name == "background_replacement":
        from .background_replacement import BackgroundReplacementStage

        return BackgroundReplacementStage()
    raise StageError(
        f"unknown stage {name!r}. "
        f"Registered: {list(_registered_stage_names())}"
    )


__all__ = [
    "Stage",
    "StageContext",
    "StageDeterminismError",
    "StageError",
    "StageExecution",
    "StageOutput",
    "get_stage",
]
