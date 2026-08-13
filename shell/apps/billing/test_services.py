"""B-billing — `get_usage` semantics + tier-gate behavior.

SESSION 204 pins the migration from the legacy V6 Video shim
to Composition-based usage accounting. Before this slice,
``videos_used`` counted only legacy Video rows — the V-arc,
B-arc, and C-arc compositions slipped past the cap entirely.
Post-migration, ``videos_used`` is "Composition rows in the
period, excluding DRAFT."

Six concerns:

1. Composition rows in the period count.
2. DRAFT compositions don't count.
3. Compositions outside the period don't count.
4. Cross-workspace compositions don't count.
5. Legacy Video rows are NOT counted (deprecated read path).
6. ``check_video_limit`` raises at the new threshold.
"""
from __future__ import annotations

import datetime

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.billing.services import (
    TierLimitExceeded,
    check_video_limit,
    get_usage,
)
from apps.compositions.models import Composition, CompositionStatus
from apps.spokespeople.models import Teammate
from apps.videos.models import Video

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Marcus", runway_avatar_id="av_marcus",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


def _make_composition(
    ws: Workspace,
    sp: Teammate,
    status: str = CompositionStatus.COMPLETED,
) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp,
        name="x", template_kind="talking_head_polished",
        status=status,
    )


# ---- happy path ------------------------------------------------


def test_get_usage_counts_completed_compositions_in_period() -> None:
    """The headline migration: COMPLETED Compositions in the
    current billing period count against videos_used."""
    _, ws = _make_user_workspace("b204hp@test")
    sp = _make_teammate(ws)
    for _ in range(3):
        _make_composition(ws, sp, status=CompositionStatus.COMPLETED)

    usage = get_usage(ws)
    assert usage.videos_used == 3


def test_get_usage_counts_failed_partial_running_planning_compositions() -> None:
    """Any non-DRAFT status counts — operator pressed the
    render button, Runway/upstream resources were held.
    PLANNING / RUNNING / COMPLETED / PARTIAL / FAILED all
    count."""
    _, ws = _make_user_workspace("b204mixed@test")
    sp = _make_teammate(ws)
    for status_value in (
        CompositionStatus.PLANNING,
        CompositionStatus.RUNNING,
        CompositionStatus.COMPLETED,
        CompositionStatus.PARTIAL,
        CompositionStatus.FAILED,
    ):
        _make_composition(ws, sp, status=status_value)

    usage = get_usage(ws)
    assert usage.videos_used == 5


def test_get_usage_excludes_draft_compositions() -> None:
    """DRAFT means the operator hasn't fired yet — no
    resources held. Excluded from the count."""
    _, ws = _make_user_workspace("b204draft@test")
    sp = _make_teammate(ws)
    _make_composition(ws, sp, status=CompositionStatus.DRAFT)
    _make_composition(ws, sp, status=CompositionStatus.COMPLETED)

    usage = get_usage(ws)
    assert usage.videos_used == 1


def test_get_usage_excludes_out_of_period_compositions() -> None:
    """Period filter: compositions older than the current
    period_start don't count toward the rolling cap."""
    _, ws = _make_user_workspace("b204period@test")
    sp = _make_teammate(ws)

    # Get current period start so we can backdate a row.
    sub = Subscription.objects.get(workspace=ws)
    period_start = sub.current_period_start
    backdated_at = period_start - datetime.timedelta(days=5)

    old = _make_composition(ws, sp, status=CompositionStatus.COMPLETED)
    Composition.objects.filter(pk=old.pk).update(created_at=backdated_at)

    in_period = _make_composition(ws, sp, status=CompositionStatus.COMPLETED)
    assert in_period.created_at >= period_start

    usage = get_usage(ws)
    assert usage.videos_used == 1


def test_get_usage_excludes_cross_workspace_compositions() -> None:
    _, ws_a = _make_user_workspace("b204wsa@test")
    _, ws_b = _make_user_workspace("b204wsb@test")
    sp_a = _make_teammate(ws_a)
    sp_b = _make_teammate(ws_b)

    _make_composition(ws_a, sp_a, status=CompositionStatus.COMPLETED)
    _make_composition(ws_b, sp_b, status=CompositionStatus.COMPLETED)
    _make_composition(ws_b, sp_b, status=CompositionStatus.COMPLETED)

    assert get_usage(ws_a).videos_used == 1
    assert get_usage(ws_b).videos_used == 2


# ---- legacy Video shim is no longer counted --------------------


def test_legacy_video_rows_are_no_longer_counted() -> None:
    """SESSION 204 — pre-migration, this would have counted as
    5 videos_used (the V6 shim's surface). Post-migration,
    Video rows are invisible to get_usage. The V6 backwards-
    compat path stays functional, but the cap reads
    Composition instead.

    This test pins the deprecation: any operator
    relying on Video rows alone (without corresponding
    Composition rows) would see videos_used=0. The dev DB's
    37 legacy Video rows likewise no longer count."""
    _, ws = _make_user_workspace("b204legacy@test")
    sp = _make_teammate(ws)
    # Seed 5 legacy Video rows (no Composition link).
    for _ in range(5):
        Video.objects.create(
            spokesperson=sp,
            kind=Video.Kind.SPOKESPERSON_AD,
            status=Video.Status.READY,
            title="legacy",
        )

    assert get_usage(ws).videos_used == 0


# ---- check_video_limit threshold integration -------------------


def test_check_video_limit_raises_when_compositions_hit_cap() -> None:
    """Starter cap=10. Seed exactly 10 completed
    Compositions; check_video_limit raises."""
    _, ws = _make_user_workspace("b204cap@test")
    sp = _make_teammate(ws)
    for _ in range(10):
        _make_composition(ws, sp, status=CompositionStatus.COMPLETED)

    with pytest.raises(TierLimitExceeded) as exc:
        check_video_limit(ws)
    assert exc.value.payload["videos_used"] == 10
    assert exc.value.payload["videos_limit"] == 10


def test_check_video_limit_passes_under_cap() -> None:
    _, ws = _make_user_workspace("b204under@test")
    sp = _make_teammate(ws)
    for _ in range(9):
        _make_composition(ws, sp, status=CompositionStatus.COMPLETED)

    # Should not raise.
    check_video_limit(ws)
