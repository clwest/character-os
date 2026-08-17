"""SESSION 258 P2.A — pure DAG layer builder.

Reads `CompositionStep.inputs` to compute execution layers for a
composition. Independent of runtime, Celery, database side effects —
callable from tests without any fixture beyond in-memory step objects.

Consumers:

* `apps.compositions.tasks.execute_composition` (parallel path) —
  uses `compute_execution_layers(steps)` to decide which steps to
  dispatch as one Celery group.
* Tests — use it to prove the graph shape of dialogue_scene,
  storyboard_ad, talking_head_with_backdrop, etc.

Dependency model (matches `CompositionStep.inputs` semantic — see
`apps/compositions/models.py:569-573`):

* `{"slot": "...", "asset_id": "<uuid>"}` — workspace asset;
  introduces NO step dependency.
* `{"slot": "...", "from_step_position": <int>}` — hard dependency
  on the step at that position.

Layer contract:

* Layer 0 contains every step with no `from_step_position` inputs.
* Layer i (i > 0) contains every step whose from_step_position
  dependencies are all satisfied by layers 0..i-1.
* Step order WITHIN a layer is ascending `step.position`
  (deterministic — the sequencer inside a layer never varies).
* Layer order across layers is topological.

Validation errors surface as `DagValidationError` BEFORE any
provider call fires:

* self-reference (`from_step_position == own position`)
* forward reference (`from_step_position >= own position`) —
  the current linear-only model (contract rule 5 in
  VIDEO_COMPOSITION_V1) disallows this
* missing upstream position (references an integer that no step
  in the composition has)
* cycle (unreachable step remaining after topological pass)
* malformed input entries (missing slot, both asset_id +
  from_step_position, non-integer position, etc.)

The DAG builder never touches the DB. It runs on the exact
`CompositionStep` objects the caller passed — typically loaded
via `composition.steps.all().order_by("position")`.
"""
from __future__ import annotations

from typing import Sequence


class DagValidationError(Exception):
    """Raised when a composition's step graph is not a valid DAG.

    Includes cycles, self-references, forward references, missing
    upstream positions, and malformed input entries. Callers MUST
    catch this before any provider dispatch — a malformed graph is
    an operator-fixable issue, not a runtime retry candidate.
    """


def compute_execution_layers(steps: Sequence) -> list[list[int]]:
    """Return execution layers as list-of-list-of-position.

    Args:
        steps: Sequence of CompositionStep-like objects. Each must
            have ``.position`` (int) and ``.inputs`` (list of dict).
            Duck-typed for test convenience — no ORM required.

    Returns:
        List of layers. Each layer is a sorted list of step positions
        that may execute in parallel because every dependency they
        declare is satisfied by an earlier layer.

    Example (dialogue_scene, 8 turns + concat + outro):

        Layer 0: [0, 1, 2, 3, 4, 5, 6, 7]   # 8 speech steps
        Layer 1: [8]                          # concat
        Layer 2: [9]                          # optional outro

    Raises:
        DagValidationError: on any of the validation failures listed
        in the module docstring.
    """
    if not steps:
        return []

    # Position → step (order-preserving lookup + dedup check).
    by_position: dict[int, object] = {}
    for step in steps:
        pos = getattr(step, "position", None)
        if not isinstance(pos, int):
            raise DagValidationError(
                f"step has non-integer position: {pos!r}"
            )
        if pos in by_position:
            raise DagValidationError(
                f"duplicate step position {pos}"
            )
        by_position[pos] = step

    # Extract from_step_position dependencies per step.
    # asset_id inputs contribute no dependency by contract.
    deps: dict[int, set[int]] = {}
    for pos, step in by_position.items():
        step_deps: set[int] = set()
        inputs = getattr(step, "inputs", None) or []
        for i, entry in enumerate(inputs):
            if not isinstance(entry, dict):
                raise DagValidationError(
                    f"step {pos} input {i}: entry is not a dict "
                    f"({type(entry).__name__})"
                )
            if "slot" not in entry or not entry["slot"]:
                raise DagValidationError(
                    f"step {pos} input {i}: missing or empty slot"
                )
            has_asset_id = bool(entry.get("asset_id"))
            has_from_pos = "from_step_position" in entry and entry["from_step_position"] is not None
            if has_asset_id and has_from_pos:
                raise DagValidationError(
                    f"step {pos} input {i}: cannot have both "
                    f"asset_id and from_step_position"
                )
            if not has_asset_id and not has_from_pos:
                raise DagValidationError(
                    f"step {pos} input {i}: must have exactly one of "
                    f"asset_id or from_step_position"
                )
            if has_from_pos:
                raw = entry["from_step_position"]
                try:
                    upstream_pos = int(raw)
                except (TypeError, ValueError) as exc:
                    raise DagValidationError(
                        f"step {pos} input {i}: from_step_position "
                        f"{raw!r} is not an integer"
                    ) from exc
                if upstream_pos == pos:
                    raise DagValidationError(
                        f"step {pos} input {i}: self-reference "
                        f"(from_step_position == own position)"
                    )
                if upstream_pos > pos:
                    raise DagValidationError(
                        f"step {pos} input {i}: forward reference "
                        f"(from_step_position {upstream_pos} > own "
                        f"position {pos}); linear ordering only"
                    )
                if upstream_pos not in by_position:
                    raise DagValidationError(
                        f"step {pos} input {i}: from_step_position "
                        f"{upstream_pos} references no step in this "
                        f"composition"
                    )
                step_deps.add(upstream_pos)
        deps[pos] = step_deps

    # Topological layering — Kahn-style, but grouped into parallel
    # layers per pass. Each iteration: pick every step whose deps
    # are entirely satisfied by prior layers; add them to the next
    # layer; mark them satisfied; repeat until no positions remain.
    layers: list[list[int]] = []
    satisfied: set[int] = set()
    remaining: set[int] = set(by_position.keys())

    while remaining:
        # Find every remaining position whose deps are all satisfied.
        ready = [pos for pos in remaining if deps[pos] <= satisfied]
        if not ready:
            # No forward progress — every remaining step depends on
            # another remaining step. Forward-ref check above catches
            # the strictly-linear case (upstream > position), so this
            # branch fires only on genuine cycles — which are
            # actually impossible in the current linear model, but
            # kept as defense in depth.
            raise DagValidationError(
                f"cycle detected — remaining positions "
                f"{sorted(remaining)} depend on each other"
            )
        # Deterministic layer ordering: ascending step.position.
        ready.sort()
        layers.append(ready)
        satisfied.update(ready)
        remaining -= set(ready)

    return layers


__all__ = ["DagValidationError", "compute_execution_layers"]
