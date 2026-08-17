"""SESSION 258 P1 — Composition-level concurrency safety.

Three shared-state races were identified by the parallel-executor
audit (SESSION 257 close report §7) as blockers for a future
fan-out scheduler:

1. ``refresh_composition_cost_actual`` — Python read-then-write
   pattern loses updates under parallel step completion.
2. ``verification_status`` — read-modify-write on stale in-memory
   composition allows silent downgrade under parallel writes.
3. ``verification_warnings`` — JSONField append via Python extend
   loses warnings when two workers both read the empty (or stale)
   list.

P1 fixes all three IN PLACE without touching the runner's
sequential execution shape. The runner is still one-Celery-task-
owns-graph; these fixes are prerequisites for the P2 layer
scheduler.

Tests use ``@pytest.mark.django_db(transaction=True)`` +
``ThreadPoolExecutor`` with per-thread ``connections.close_all()``
so real transactions cross the thread boundary. Same pattern
as ``apps/identity/tests/test_services_concurrency.py``.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth import get_user_model
from django.db import connections

from apps.accounts.models import Workspace
from apps.compositions.cost import refresh_composition_cost_actual
from apps.compositions.models import (
    Composition,
    CompositionStep,
)
from apps.compositions.primitives.avatar_speech import (
    _apply_composition_status_and_warnings,
    _should_stamp_verification_status,
    _VERIFICATION_STATUS_RANK,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db(transaction=True)


# ---- fixtures ---------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(ws: Workspace, name: str = "Sp") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=f"av-{name.lower()}",
        portrait_path="https://fake/p.png",
        business_brief="brief",
    )


def _composition(ws, sp, **kwargs) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="p1", **kwargs,
    )


def _step(comp, position: int, cost: int = 0) -> CompositionStep:
    return CompositionStep.objects.create(
        composition=comp, position=position,
        primitive="generate_avatar_speech",
        params={"script": "x"},
        cost_actual_micros=cost,
    )


# ---- P1.1 cost aggregation --------------------------------------


def test_refresh_cost_actual_sequential_baseline() -> None:
    """Prior contract preserved: single-caller refresh sums step
    costs and persists on the composition row. Zero-step composition
    yields 0. Return value equals persisted value."""
    ws = _workspace("p1cs_baseline@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)
    # Zero-step composition.
    assert refresh_composition_cost_actual(comp) == 0
    comp.refresh_from_db()
    assert comp.cost_actual_micros == 0

    # N-step composition.
    for i in range(5):
        _step(comp, position=i, cost=(i + 1) * 1000)
    expected = 1000 + 2000 + 3000 + 4000 + 5000  # 15000
    assert refresh_composition_cost_actual(comp) == expected
    comp.refresh_from_db()
    assert comp.cost_actual_micros == expected


def test_refresh_cost_actual_race_safe_under_concurrent_completions() -> None:
    """P1.1 load-bearing regression — the SQL-subquery UPDATE
    serializes on the composition row under real concurrent writes.

    Prior read-then-write pattern could lose updates when two
    workers computed SUM at different moments and raced to write:
    the later worker's write could reflect an older SUM.

    Setup: N steps each carry a distinct cost. N threads call
    ``refresh_composition_cost_actual`` in parallel using
    per-thread DB connections. Final persisted total MUST equal
    the sum of every step cost.
    """
    ws = _workspace("p1cs_race@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)
    for i in range(8):
        _step(comp, position=i, cost=(i + 1) * 20_000)
    expected = sum((i + 1) * 20_000 for i in range(8))  # 720_000

    barrier = threading.Barrier(8)

    def _worker(_idx: int) -> None:
        try:
            barrier.wait()  # release all 8 threads simultaneously
            refresh_composition_cost_actual(comp)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_worker, range(8)))

    comp.refresh_from_db()
    assert comp.cost_actual_micros == expected, (
        f"cost lost update — expected {expected}, "
        f"got {comp.cost_actual_micros}"
    )


def test_refresh_cost_actual_reflects_concurrent_step_writes() -> None:
    """Even harder scenario: threads MUTATE distinct step costs
    concurrently AND call refresh concurrently. Final total must
    include every committed step-cost change."""
    ws = _workspace("p1cs_mutating@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)
    steps = [_step(comp, position=i, cost=0) for i in range(8)]

    barrier = threading.Barrier(8)

    def _worker(idx: int) -> None:
        try:
            barrier.wait()
            # First: write a distinct cost to my step.
            CompositionStep.objects.filter(pk=steps[idx].pk).update(
                cost_actual_micros=(idx + 1) * 5_000,
            )
            # Then: refresh the composition sum.
            refresh_composition_cost_actual(comp)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_worker, range(8)))

    expected = sum((i + 1) * 5_000 for i in range(8))  # 180_000
    comp.refresh_from_db()
    assert comp.cost_actual_micros == expected


# ---- P1.2 verification_status precedence + concurrency ---------


def test_verification_status_no_downgrade_helper_pure_ranking() -> None:
    """Precedence rule unchanged from SESSION 257 AI-D5. Regression
    guard against the pure ranking helper."""
    # Elevate
    assert _should_stamp_verification_status("", "verified") is True
    assert _should_stamp_verification_status("trusted_passthrough", "verified") is True
    assert _should_stamp_verification_status("verified", "rejected") is True
    # Never downgrade
    assert _should_stamp_verification_status("verified", "trusted_passthrough") is False
    assert _should_stamp_verification_status("rejected", "verified") is False
    # Same-status no-op
    assert _should_stamp_verification_status("verified", "verified") is False
    # Rank ordering
    assert _VERIFICATION_STATUS_RANK["rejected"] > _VERIFICATION_STATUS_RANK["verified"]
    assert _VERIFICATION_STATUS_RANK["verified"] > _VERIFICATION_STATUS_RANK["skipped"]
    assert _VERIFICATION_STATUS_RANK["skipped"] > _VERIFICATION_STATUS_RANK["trusted_passthrough"]
    assert _VERIFICATION_STATUS_RANK["trusted_passthrough"] > _VERIFICATION_STATUS_RANK[""]


def test_verification_status_sequential_baseline_unchanged() -> None:
    """Single-caller behavior identical to prior inline block:
    empty → verified, verified stays verified against passthrough,
    verified → rejected upgrades."""
    ws = _workspace("p1vs_baseline@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)

    # Empty → verified.
    _apply_composition_status_and_warnings(
        comp, incoming_status="verified",
    )
    comp.refresh_from_db()
    assert comp.verification_status == "verified"

    # verified vs passthrough: no downgrade.
    _apply_composition_status_and_warnings(
        comp, incoming_status="trusted_passthrough",
    )
    comp.refresh_from_db()
    assert comp.verification_status == "verified"

    # verified → rejected.
    _apply_composition_status_and_warnings(
        comp, incoming_status="rejected",
    )
    comp.refresh_from_db()
    assert comp.verification_status == "rejected"


def test_verification_status_concurrent_verified_vs_passthrough_ends_verified() -> None:
    """P1.2 — under concurrent writes, verified vs
    trusted_passthrough MUST end verified. Prior code (bare
    ``.save()`` on stale in-memory) could last-writer-wins to
    ``trusted_passthrough``. Locked helper reads fresh under
    ``select_for_update`` and applies the no-downgrade rule."""
    ws = _workspace("p1vs_race_a@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)  # starts verification_status=""

    barrier = threading.Barrier(2)
    results: dict[int, str] = {}

    def _worker_verified(_idx: int) -> None:
        try:
            barrier.wait()
            _apply_composition_status_and_warnings(
                comp, incoming_status="verified",
            )
            results[0] = "ok"
        finally:
            connections.close_all()

    def _worker_passthrough(_idx: int) -> None:
        try:
            barrier.wait()
            _apply_composition_status_and_warnings(
                comp, incoming_status="trusted_passthrough",
            )
            results[1] = "ok"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_worker_verified, 0)
        f2 = pool.submit(_worker_passthrough, 0)
        f1.result()
        f2.result()

    comp.refresh_from_db()
    assert comp.verification_status == "verified", (
        "concurrent verified-vs-passthrough must end verified; "
        f"got {comp.verification_status!r}"
    )


def test_verification_status_concurrent_verified_vs_rejected_ends_rejected() -> None:
    """P1.2 — concurrent verified vs rejected MUST end rejected.
    Rejection is the highest rank; it should dominate regardless
    of write order."""
    ws = _workspace("p1vs_race_b@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)

    barrier = threading.Barrier(2)

    def _worker(status: str) -> None:
        try:
            barrier.wait()
            _apply_composition_status_and_warnings(
                comp, incoming_status=status,
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_worker, "verified")
        f2 = pool.submit(_worker, "rejected")
        f1.result()
        f2.result()

    comp.refresh_from_db()
    assert comp.verification_status == "rejected"


# ---- P1.3 verification_warnings append concurrency -------------


def test_verification_warnings_sequential_append_baseline() -> None:
    """Single caller: warnings append (never replace)."""
    ws = _workspace("p1vw_baseline@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)
    _apply_composition_status_and_warnings(
        comp,
        incoming_status="verified",
        incoming_warnings=[{"claim": "one"}],
    )
    _apply_composition_status_and_warnings(
        comp,
        incoming_status="verified",
        incoming_warnings=[{"claim": "two"}],
    )
    comp.refresh_from_db()
    assert comp.verification_warnings == [{"claim": "one"}, {"claim": "two"}]


def test_verification_warnings_concurrent_appends_preserve_both_sets() -> None:
    """P1.3 load-bearing regression — under concurrent writes,
    BOTH warning sets survive. Prior code (Python read+extend+save)
    would lose the earlier writer's warnings when both workers
    read the same empty list.

    Two threads each append 3 distinct warnings under a barrier.
    Final list must contain all 6 warnings."""
    ws = _workspace("p1vw_race@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)

    warnings_a = [
        {"claim": "a1", "line_index": 0, "speaker_alias": "patch"},
        {"claim": "a2", "line_index": 1, "speaker_alias": "patch"},
        {"claim": "a3", "line_index": 2, "speaker_alias": "patch"},
    ]
    warnings_b = [
        {"claim": "b1", "line_index": 0, "speaker_alias": "rivet"},
        {"claim": "b2", "line_index": 1, "speaker_alias": "rivet"},
        {"claim": "b3", "line_index": 2, "speaker_alias": "rivet"},
    ]

    barrier = threading.Barrier(2)

    def _worker(warns: list[dict]) -> None:
        try:
            barrier.wait()
            _apply_composition_status_and_warnings(
                comp,
                incoming_status="verified",
                incoming_warnings=warns,
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_worker, warnings_a)
        f2 = pool.submit(_worker, warnings_b)
        f1.result()
        f2.result()

    comp.refresh_from_db()
    persisted = comp.verification_warnings
    assert len(persisted) == 6, (
        f"lost warnings — expected 6, got {len(persisted)}: {persisted!r}"
    )
    claims = {w["claim"] for w in persisted}
    assert claims == {"a1", "a2", "a3", "b1", "b2", "b3"}


def test_verification_warnings_concurrent_status_and_warnings_coexist() -> None:
    """Combined P1.2 + P1.3 case — one worker upgrades status +
    appends warnings, another appends passthrough + warnings.
    Final: verified status wins (no downgrade), BOTH warning
    sets present (no loss)."""
    ws = _workspace("p1vsvw_combined@t")
    sp = _teammate(ws)
    comp = _composition(ws, sp)

    barrier = threading.Barrier(2)

    def _worker_verified() -> None:
        try:
            barrier.wait()
            _apply_composition_status_and_warnings(
                comp,
                incoming_status="verified",
                incoming_warnings=[{"claim": "v_only"}],
            )
        finally:
            connections.close_all()

    def _worker_passthrough() -> None:
        try:
            barrier.wait()
            _apply_composition_status_and_warnings(
                comp,
                incoming_status="trusted_passthrough",
                incoming_warnings=[{"claim": "pt_only"}],
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        f1 = pool.submit(_worker_verified)
        f2 = pool.submit(_worker_passthrough)
        f1.result()
        f2.result()

    comp.refresh_from_db()
    assert comp.verification_status == "verified"
    claims = {w["claim"] for w in comp.verification_warnings}
    assert claims == {"v_only", "pt_only"}
