"""Per-step + per-composition cost estimation.

SESSION 142 / V2. Contract rule 7 from
``docs/design/VIDEO_COMPOSITION_V1.md`` requires that cost
is computed before render fires, not after. Operators see
``cost_estimate_micros`` before clicking render; actuals are
written per-step after execution.

The cost surface in V2 is intentionally minimal — two helpers
that compose per-primitive estimators. V3+ slices ship the
concrete estimators (e.g. gpt-5-mini at ~$0.0001/call,
``/v1/avatar_videos`` at ~$0.05/sec). V2 only needs the
runtime to sum what the primitives say + write actuals
back after execution.

Open question Q-v-4 in the scope lock resolves here: cost
estimators live as ``estimate_cost`` static methods on each
primitive class, called via ``estimate_step_cost`` /
``estimate_composition_cost``.
"""
from __future__ import annotations

from .primitives import UnknownPrimitiveError, get_primitive


def estimate_step_cost(step) -> int:
    """Estimate one step's cost in micros from its primitive +
    params. Returns 0 if the primitive is unknown (the step
    will fail at execute_composition time with a clearer
    error than what the cost estimator could produce here)."""
    try:
        primitive = get_primitive(step.primitive)
    except UnknownPrimitiveError:
        return 0
    return primitive.estimate_cost(step.params or {})


def estimate_composition_cost(composition) -> int:
    """Sum of estimated step costs. Operator sees this before
    clicking render; runtime persists into
    ``Composition.cost_estimate_micros`` at planning time."""
    return sum(
        estimate_step_cost(step)
        for step in composition.steps.all().order_by("position")
    )


def refresh_composition_cost_actual(composition) -> int:
    """Re-sum ``cost_actual_micros`` across all steps and
    persist on the composition. Called after each step
    completes (success or failure — failed steps cost zero
    but we still rebuild the sum for consistency)."""
    from django.db.models import Sum

    actual = (
        composition.steps.aggregate(total=Sum("cost_actual_micros"))["total"] or 0
    )
    composition.cost_actual_micros = actual
    composition.save(update_fields=["cost_actual_micros", "updated_at"])
    return actual
