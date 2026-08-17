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
    error than what the cost estimator could produce here).

    Some primitives (currently ``generate_visual_clip``) also
    consume the step's raw ``inputs`` wiring to distinguish
    routing decisions that aren't visible in ``params`` alone
    — e.g. a slot-wired ``reference_image`` from an upstream
    ``generate_image`` step changes the Runway model from
    gen4.5 to gen4_turbo. The dispatch here tries the
    inputs-aware call first and falls back to the params-only
    signature so unrelated primitives don't need churn."""
    try:
        primitive = get_primitive(step.primitive)
    except UnknownPrimitiveError:
        return 0
    params = step.params or {}
    inputs = step.inputs or []
    try:
        return primitive.estimate_cost(params, inputs=inputs)
    except TypeError:
        return primitive.estimate_cost(params)


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
    but we still rebuild the sum for consistency).

    SESSION 258 P1.1 — race-safe under concurrent step
    completions.

    Prior implementation did a Python-side aggregate then a
    separate ``composition.save()`` — a classic read-then-
    write pattern that lost updates under parallel workers:

        Worker A: SUM=20_000 (only step 1 committed yet)
        Worker B: SUM=40_000 (both step 1 + step 2 committed)
        Worker A writes cost_actual_micros=20_000
        Worker B writes cost_actual_micros=40_000
        (order of the two writes decides the persisted value)

    The audit for the parallel dialogue-executor slice
    (SESSION 258 P0) flagged this as one of three shared-
    Composition-field races that would break under a fan-out
    scheduler.

    This version issues a single UPDATE statement whose new
    value is a subquery evaluated by Postgres at write time
    against the currently-committed CompositionStep rows.
    Two concurrent calls serialize on the composition row's
    row-level UPDATE lock; each subquery re-evaluates against
    the committed step state at its own moment. No lost
    updates.

    Sequential semantics unchanged — a single call still
    computes the same total the prior code did.

    Zero-step semantics preserved via ``Coalesce(..., 0)``.

    Returns the persisted total (fresh-read from DB so the
    caller sees the same value the row actually holds).
    """
    from django.db.models import OuterRef, Subquery, Sum, Value
    from django.db.models.functions import Coalesce
    from django.utils import timezone

    from .models import Composition, CompositionStep

    step_sum_subquery = (
        CompositionStep.objects
        .filter(composition_id=OuterRef("pk"))
        .order_by()
        .values("composition_id")
        .annotate(total=Sum("cost_actual_micros"))
        .values("total")
    )
    Composition.objects.filter(pk=composition.pk).update(
        cost_actual_micros=Coalesce(Subquery(step_sum_subquery), Value(0)),
        updated_at=timezone.now(),
    )
    # Sync the caller's in-memory instance so downstream logic
    # that reads ``composition.cost_actual_micros`` sees the
    # persisted value (matches prior return-value contract).
    composition.refresh_from_db(fields=["cost_actual_micros", "updated_at"])
    return composition.cost_actual_micros
