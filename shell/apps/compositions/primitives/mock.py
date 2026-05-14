"""Mock primitives for the V2 composition runtime.

SESSION 142 / V2. These primitives exist to exercise the
runtime state machine end-to-end without touching Runway,
OpenAI, ffmpeg, or any external service. They mirror the
shape every real primitive (V3+) will have:

* ``execute`` returns a ``PrimitiveResult`` on success or
  raises ``PrimitiveError`` on failure.
* ``estimate_cost`` is a pure function from params to micros.
* Output is deterministic given identical inputs — re-running
  with the same step id produces the same file_path so
  tests + future caching can rely on it.

Three primitives ship in V2:

* ``mock_passthrough`` — always succeeds, returns a stub
  CLIP asset. The default "this runtime works" verifier.
* ``mock_failure`` — always raises. Exercises the FAILED
  step path + the composition's PARTIAL state.
* ``mock_slow`` — succeeds but records a non-trivial
  ``elapsed_ms`` so timing assertions in tests have something
  to bite on.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from apps.compositions.models import AssetType


class PrimitiveError(Exception):
    """Raised by a primitive when execution fails. The runtime
    catches this, marks the step FAILED, and records the
    message on ``CompositionStep.error_message``."""


@dataclass
class PrimitiveResult:
    """What a primitive returns on success. The runtime
    persists these fields onto a new ``Asset`` row.

    ``asset_type`` is required; everything else is type-
    specific. Clips fill ``file_path`` + ``duration_ms`` +
    dimensions; transcripts fill ``inline_content``; voices
    fill ``file_path`` (Runway voice_id, not a local path).
    """

    asset_type: str  # one of AssetType.choices values
    file_path: str = ""
    inline_content: str = ""
    duration_ms: int | None = None
    width: int | None = None
    height: int | None = None
    mime_type: str = ""
    size_bytes: int | None = None
    cost_micros: int = 0
    extra_source_spec: dict[str, Any] = field(default_factory=dict)


def _deterministic_path(step_id: str, suffix: str) -> str:
    """Deterministic mock URL keyed by the step id. Re-running
    a primitive on the same step yields the same path so
    re-execution semantics stay clean."""
    digest = hashlib.sha256(step_id.encode("utf-8")).hexdigest()[:12]
    return f"mock://compositions/{digest}{suffix}"


class MockPassthroughPrimitive:
    """The reference primitive — always succeeds. Returns a
    stub CLIP asset. ``cost_micros`` is fixed at 100 (one
    cent of a dollar's millionth — deterministic stub) so
    cost aggregation tests have predictable numbers."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        # ``resolved_inputs`` is a list of {slot, asset}; we
        # don't need to do anything with them in the mock,
        # but we include the slot names in the source_spec so
        # the test assertions can verify input wiring.
        slot_names = [entry.get("slot", "") for entry in resolved_inputs]
        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=_deterministic_path(str(step.id), ".mp4"),
            duration_ms=5000,
            width=1280,
            height=720,
            mime_type="video/mp4",
            size_bytes=1024 * 1024,
            cost_micros=100,
            extra_source_spec={
                "mock": True,
                "resolved_input_slots": slot_names,
            },
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return 100


class MockFailurePrimitive:
    """The reference failure path — always raises. Used in
    tests for the FAILED step + PARTIAL composition states.

    The error message is operator-actionable enough to verify
    the runtime's error propagation works."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        reason = step.params.get("reason", "intentional mock failure")
        raise PrimitiveError(
            f"mock_failure primitive raised: {reason} (step {step.id})"
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        # Failed primitives still need a cost estimate so
        # composition.cost_estimate_micros can be computed
        # before the failure happens (the operator was going
        # to commit those micros if it had succeeded).
        return 100


class MockSlowPrimitive:
    """A primitive that succeeds but takes a measurable
    fraction of a second. Lets timing-related tests verify
    ``CompositionStep.elapsed_ms`` is populated correctly
    without forcing every other test to wait."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        # 50ms is enough to land a non-zero elapsed_ms without
        # making the test suite slow.
        time.sleep(0.05)
        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=_deterministic_path(str(step.id), "-slow.mp4"),
            duration_ms=5000,
            cost_micros=50,
            extra_source_spec={"mock": True, "slow": True},
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return 50
