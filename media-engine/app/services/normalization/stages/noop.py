"""NoOpStage — the pipeline harness exerciser (v1).

Passes bytes through unchanged and records
``status='not_applied'``. Its purpose is to prove that the
pipeline machinery — context threading, execution timing,
manifest assembly, pipeline-version composition — works
end-to-end without needing a real Pillow transform. That lets
7.a ship + push with cross-slice testing before crop / framing /
eye-line / background land in 7.b and 7.c.

Registered per SESSION 246 operator discipline: NoOp is a
legitimate registered ``Stage`` (so 7.a has a real thing to
exercise the harness against), but it is **explicitly excluded
from the default v1 pipeline chain**. See
``pipeline.build_default_v1_pipeline`` (which lands at 7.c
close and does NOT include NoOp in the ordered stage tuple).
Tests that need a NoOp-only pipeline instantiate it directly.
"""
from __future__ import annotations

import time
from typing import ClassVar

from . import StageContext, StageExecution, StageOutput


class NoOpStage:
    """Pass-through stage.

    Records ``status='not_applied'`` — the honest label for a
    stage that did no work. Input dimensions == output dimensions
    because bytes are unchanged.
    """

    stage_name: ClassVar[str] = "noop"
    stage_version: ClassVar[int] = 1

    def apply(self, ctx: StageContext) -> StageOutput:
        started = time.perf_counter()
        # Deliberately no image work. Bytes flow through verbatim.
        duration_ms = int((time.perf_counter() - started) * 1000)
        execution = StageExecution(
            stage_name=self.stage_name,
            stage_version=self.stage_version,
            status="not_applied",
            input_width_px=ctx.width_px,
            input_height_px=ctx.height_px,
            output_width_px=ctx.width_px,
            output_height_px=ctx.height_px,
            duration_ms=duration_ms,
            details={
                # Factual record of why this row exists in
                # stages_skipped: the stage is a pipeline
                # harness exerciser with no transform behavior.
                "reason": "harness_exerciser_no_transform_behavior",
            },
        )
        # New (frozen) context has the same values — but returning
        # a fresh instance keeps the immutable-context contract
        # explicit (no accidental "return the input" pattern that
        # would let a future stage rely on identity comparison).
        new_context = StageContext(
            image_bytes=ctx.image_bytes,
            width_px=ctx.width_px,
            height_px=ctx.height_px,
            surface_profile=ctx.surface_profile,
            background=ctx.background,
        )
        return StageOutput(new_context=new_context, execution=execution)
