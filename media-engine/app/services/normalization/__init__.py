"""Normalization pipeline — §19 Step 7 (SESSION 246).

Deterministic transformation from a raw provider portrait
(bytes) plus declarative surface / background configuration
into a normalized portrait (bytes) plus a factual manifest
describing exactly what happened. §17.6.a scope-locked at
round one to four stages — crop, framing, eye-line
normalization, background replacement — with tonal, lighting,
shadow, relighting, white-balance, exposure, skin-tone, and
"beautification" stages explicitly deferred until benchmark
evidence justifies them.

Load-bearing invariants (per §10.6):

* **Deterministic.** Given identical raw bytes + identical
  ``NormalizationSpec`` + identical pipeline version, the
  normalized bytes must be byte-for-byte identical. Randomness
  is refused; PNG-encode metadata is fixed. If a downstream
  primitive (rembg / opencv / Pillow) turns out to be
  nondeterministic, surface the contradiction — do not
  paper over it.

* **Raw bytes are canonical.** The pipeline never mutates or
  overwrites its input. Raw + normalized + manifest are three
  independent artifacts (§10.3). Losing the raw asset loses
  the ability to re-interpret evidence against a better
  pipeline later.

* **Manifest is factual, not aesthetic.** Stage rows record
  what happened (input/output dimensions, crop coordinates,
  method identifier for proxies vs. real detectors,
  background_source, per-stage version) — never quality
  judgments. That evidence supports Step 8/10 human review.

* **Surface profiles + background family are data, not code.**
  Loaded from ratified YAML at
  ``docs/design/visual/portrait_qualification/schemas/``.
  Bumping a profile's ``version`` bumps the pipeline version
  recorded on downstream manifests without a code change
  (§10.8, §17.5.b's declarative discipline).

Boundary (mirrors Step 5 / Step 6 architectural finding):

* Media-engine owns bytes-in → stages → bytes-out + manifest
  payload.
* Django / shell owns ``Asset`` persistence, ``GenerationRecord``
  linkage, and ``NormalizationManifest`` row writes via the
  ratified ``record_normalization_manifest`` service.

Sub-slice progress:

* Pre-7.a — config loaders + Pillow/PyYAML pins. ✓ shipped.
* 7.a — pipeline harness + Stage protocol + NoOp + drift +
  determinism anchor. ✓ shipped (this slice).
* 7.b — CropStage + FramingStage. Pending.
* 7.c — EyeLineStage + BackgroundReplacementStage. Pending.
"""
from __future__ import annotations

from .config import (
    Background,
    BackgroundFamily,
    InvalidBackgroundFamilyError,
    InvalidSurfaceProfileError,
    NormalizationConfigError,
    ProceduralV1,
    SurfaceProfile,
    SurfaceProfileCrop,
    SurfaceProfileEyeLine,
    SurfaceProfileFramingBehavior,
    SurfaceProfileMargins,
    SurfaceProfileOutput,
    UnknownBackgroundIdError,
    UnknownSurfaceProfileError,
    default_backgrounds_path,
    default_surface_profiles_dir,
    get_background,
    load_background_family,
    load_surface_profile,
    resolve_background_for_profile,
    stable_yaml_hash,
)
from .pipeline import (
    NormalizationPipeline,
    NormalizationResult,
    NormalizationSpec,
    PipelineError,
    PipelineInputError,
    PipelineStageError,
)
from .png import BadPngError, PngEncodingError, PngError, decode_png, dimensions_of, encode_png
from .stages import (
    Stage,
    StageContext,
    StageDeterminismError,
    StageError,
    StageExecution,
    StageOutput,
    get_stage,
)

__all__ = [
    # config
    "Background",
    "BackgroundFamily",
    "InvalidBackgroundFamilyError",
    "InvalidSurfaceProfileError",
    "NormalizationConfigError",
    "ProceduralV1",
    "SurfaceProfile",
    "SurfaceProfileCrop",
    "SurfaceProfileEyeLine",
    "SurfaceProfileFramingBehavior",
    "SurfaceProfileMargins",
    "SurfaceProfileOutput",
    "UnknownBackgroundIdError",
    "UnknownSurfaceProfileError",
    "default_backgrounds_path",
    "default_surface_profiles_dir",
    "get_background",
    "load_background_family",
    "load_surface_profile",
    "resolve_background_for_profile",
    "stable_yaml_hash",
    # png
    "BadPngError",
    "PngEncodingError",
    "PngError",
    "decode_png",
    "dimensions_of",
    "encode_png",
    # stages
    "Stage",
    "StageContext",
    "StageDeterminismError",
    "StageError",
    "StageExecution",
    "StageOutput",
    "get_stage",
    # pipeline
    "NormalizationPipeline",
    "NormalizationResult",
    "NormalizationSpec",
    "PipelineError",
    "PipelineInputError",
    "PipelineStageError",
]
