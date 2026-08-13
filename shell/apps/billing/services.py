"""Tier-limit enforcement service.

Two responsibilities:
  - Compute current period usage (videos created this billing cycle,
    spokespeople in the workspace) for the usage meter the SPA renders.
  - Raise ``TierLimitExceeded`` when a workspace tries to create
    something its tier can't afford. Caller maps the exception to a
    DRF response with HTTP 402 (Payment Required) — design doc §2.2
    says the user never sees credit math, only "Upgrade to Pro" CTAs.

The middleware/viewset layer calls these *before* hitting the
media-engine so we never burn Runway credits on a request that's
going to fail at the tier wall.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from apps.spokespeople.models import Teammate

from .models import TIER_LIMITS, Subscription

if TYPE_CHECKING:
    from apps.accounts.models import Workspace


class TierLimitExceeded(Exception):
    """Raised when a workspace tries to do something its tier can't.

    Carries a structured ``payload`` the viewset surfaces straight to
    the client (current tier, limit, current count, suggested upgrade).
    """

    def __init__(self, payload: dict) -> None:
        super().__init__(payload.get("message", "tier limit exceeded"))
        self.payload = payload


@dataclass
class Usage:
    """Snapshot of a workspace's current-period usage + limits."""

    tier: str
    status: str
    videos_used: int
    videos_limit: int | None
    spokespeople_used: int
    spokespeople_limit: int | None
    # R3 — realtime sessions count against tier. See
    # `realtime_sessions_per_month` in TIER_LIMITS.
    realtime_sessions_used: int
    realtime_sessions_limit: int | None
    # R9 — finer-grained minutes budget. Aggregates
    # `RealtimeSession.duration_seconds` across the
    # current period (rounded up to whole minutes for
    # operator-facing display). The session-count gate
    # still fires as the cheaper coarse check.
    realtime_minutes_used: int
    realtime_minutes_limit: int | None
    # B-2 / Q-e-9 (SESSION 206) — per-month draft count.
    # Counts both initial-create and regenerate fires.
    # Each consumes a gpt-5 Responses-API call.
    drafts_used: int
    drafts_limit: int | None
    period_start: str
    period_end: str

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "status": self.status,
            "videos_used": self.videos_used,
            "videos_limit": self.videos_limit,
            "spokespeople_used": self.spokespeople_used,
            "spokespeople_limit": self.spokespeople_limit,
            "realtime_sessions_used": self.realtime_sessions_used,
            "realtime_sessions_limit": self.realtime_sessions_limit,
            "realtime_minutes_used": self.realtime_minutes_used,
            "realtime_minutes_limit": self.realtime_minutes_limit,
            "drafts_used": self.drafts_used,
            "drafts_limit": self.drafts_limit,
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


def _suggest_upgrade(current_tier: str) -> str | None:
    if current_tier == "starter":
        return "pro"
    if current_tier == "pro":
        return "agency"
    return None  # already on top tier


def get_usage(workspace: "Workspace") -> Usage:
    """Build the workspace's current usage snapshot for the SPA meter."""
    # Lazy import (see top-of-file note) — apps.realtime
    # depends on apps.compositions whose AppConfig graph
    # finishes loading after billing starts being read.
    from apps.compositions.models import Composition, CompositionStatus
    from apps.realtime.models import RealtimeSession

    from django.db.models import Sum

    sub = _subscription_for(workspace)
    # SESSION 204 — migrated from the legacy V6 Video shim to
    # Composition. The V6 backwards-compat surface (apps.videos)
    # only counted operator-facing one-off renders via the
    # legacy single-form path; the V-arc (V1-V18), B-arc
    # (transcripts), and C-arc (campaigns) all create
    # Compositions directly and never touch Video. Pre-migration
    # the per-month cap was effectively disabled for everything
    # except the few remaining legacy callers.
    #
    # Composition rows in DRAFT haven't fired yet — exclude
    # them. Everything else (PLANNING / RUNNING / COMPLETED /
    # PARTIAL / FAILED) represents an operator render attempt
    # that held Runway/upstream resources, so it counts against
    # the monthly cap. Same shape as the realtime exclusion
    # (DRAFT only; FAILED was excluded there because the
    # provider rejected pre-resource-allocation, but for V-arc
    # compositions a FAILED row typically had upstream calls
    # mid-pipeline).
    # D-arc / B14.1 (SESSION 205) — publish-variant
    # compositions are ffmpeg-only derivatives of an already-
    # rendered source. The source already counted at its own
    # render time; counting the variants would punish operators
    # for fanning out to multiple platforms. Exclude by
    # template_kind (the constant lives in
    # apps.compositions.platform_catalog so the recipe + this
    # filter can't drift). Per PUBLISH_BUNDLE_V1.md rule 5 +
    # Q-d-4.
    from apps.compositions.platform_catalog import (
        PUBLISH_VARIANT_TEMPLATE_KIND,
    )
    videos_used = Composition.objects.filter(
        workspace=workspace,
        created_at__gte=sub.current_period_start,
        created_at__lt=sub.current_period_end,
    ).exclude(
        status=CompositionStatus.DRAFT,
    ).exclude(
        template_kind=PUBLISH_VARIANT_TEMPLATE_KIND,
    ).count()
    spokespeople_used = Teammate.objects.filter(workspace=workspace).count()
    # Exclude DRAFT (never reached the upstream provider) and
    # FAILED (upstream rejected before any Runway resource was
    # held). Both states consume zero Runway quota; counting
    # them against the operator's monthly cap surfaces as
    # premature 402s when create flows fail. CREATING / READY /
    # NOT_READY / ENDED all represent a session the provider
    # accepted.
    period_sessions = RealtimeSession.objects.filter(
        workspace=workspace,
        created_at__gte=sub.current_period_start,
        created_at__lt=sub.current_period_end,
    ).exclude(
        status__in=[
            RealtimeSession.Status.DRAFT,
            RealtimeSession.Status.FAILED,
        ],
    )
    realtime_sessions_used = period_sessions.count()
    # B-2 / Q-e-9 (SESSION 206) — drafts/month accounting.
    # Counts Scripts created in period (each = 1 draft fire)
    # + revision_history entries with ts in period (each
    # regenerate snapshots the prior draft before re-firing,
    # so |revision_history| equals the regenerate count for
    # that Script).
    #
    # The Python sum is fine in v1 — drafts_per_month maxes
    # at 100 in Pro, so workspaces have O(100) Script rows
    # at most. If this becomes hot, denormalize via a
    # DraftEvent table in v2.
    drafts_used = _count_drafts_in_period(
        workspace,
        sub.current_period_start,
        sub.current_period_end,
    )
    # R9 — sum duration_seconds across the period; round
    # up to whole minutes for the operator-facing meter.
    # In-flight sessions (status<>ENDED) have
    # duration_seconds=0 until the broker's _end_session
    # writes the final value; partial-minute granularity
    # is a v2 concern (the SPA's CostTicker covers live
    # accumulation).
    period_seconds = period_sessions.aggregate(
        total=Sum("duration_seconds"),
    ).get("total") or 0
    realtime_minutes_used = (period_seconds + 59) // 60  # round up
    tier_table = TIER_LIMITS.get(sub.tier, TIER_LIMITS["starter"])
    return Usage(
        tier=sub.tier,
        status=sub.status,
        videos_used=videos_used,
        videos_limit=sub.videos_per_month,
        spokespeople_used=spokespeople_used,
        spokespeople_limit=sub.spokespeople_limit,
        realtime_sessions_used=realtime_sessions_used,
        realtime_sessions_limit=tier_table.get("realtime_sessions_per_month"),
        realtime_minutes_used=realtime_minutes_used,
        realtime_minutes_limit=tier_table.get("realtime_minutes_per_month"),
        drafts_used=drafts_used,
        drafts_limit=tier_table.get("drafts_per_month"),
        period_start=sub.current_period_start.isoformat(),
        period_end=sub.current_period_end.isoformat(),
    )


def _count_drafts_in_period(workspace, period_start, period_end) -> int:
    """Count draft-fire events in the period for the workspace.

    A draft fire is either:
    * The initial creation of a Script row (counts when
      ``Script.created_at`` falls in the period).
    * A regenerate (counts when the snapshot entry's ``ts``
      in ``revision_history`` falls in the period — the
      snapshot lands when the regenerate fires).

    Pre-create check before the LLM call hits the wire so
    over-cap workspaces fail fast.
    """
    # Lazy import — apps.scripts loads after apps.billing in
    # the AppConfig graph (settings.py order).
    from apps.scripts.models import Script

    in_period_creates = Script.objects.filter(
        workspace=workspace,
        created_at__gte=period_start,
        created_at__lt=period_end,
    ).count()

    regenerate_count = 0
    period_start_iso = period_start.isoformat()
    period_end_iso = period_end.isoformat()
    for revision_history in (
        Script.objects.filter(workspace=workspace)
        .values_list("revision_history", flat=True)
    ):
        for entry in (revision_history or []):
            ts = entry.get("ts") or ""
            if period_start_iso <= ts < period_end_iso:
                regenerate_count += 1
    return in_period_creates + regenerate_count


def check_video_limit(workspace: "Workspace") -> None:
    """Raise TierLimitExceeded if creating a video now would push the
    workspace past its monthly video allowance."""
    usage = get_usage(workspace)
    if usage.videos_limit is None:
        return  # unlimited tier
    if usage.videos_used >= usage.videos_limit:
        raise TierLimitExceeded(
            {
                "code": "video_limit_reached",
                "message": (
                    f"You've used all {usage.videos_limit} videos in your "
                    f"{usage.tier.capitalize()} plan this month."
                ),
                "current_tier": usage.tier,
                "videos_used": usage.videos_used,
                "videos_limit": usage.videos_limit,
                "suggested_tier": _suggest_upgrade(usage.tier),
            }
        )


def check_drafts_per_month(workspace: "Workspace") -> None:
    """Raise TierLimitExceeded if firing a draft now would push
    the workspace past its monthly drafts allowance.

    B-2 / Q-e-9 (SESSION 206). Called at POST /api/scripts/
    (create) and POST /api/scripts/<id>/regenerate/. Each draft
    fires a gpt-5 Responses-API call (~$0.001 / draft); the cap
    prevents unbounded LLM spend on retry storms.
    """
    usage = get_usage(workspace)
    if usage.drafts_limit is None:
        return  # unlimited tier
    if usage.drafts_used >= usage.drafts_limit:
        raise TierLimitExceeded(
            {
                "code": "draft_limit_reached",
                "message": (
                    f"You've used all {usage.drafts_limit} script "
                    f"drafts in your {usage.tier.capitalize()} plan "
                    "this month."
                ),
                "current_tier": usage.tier,
                "drafts_used": usage.drafts_used,
                "drafts_limit": usage.drafts_limit,
                "suggested_tier": _suggest_upgrade(usage.tier),
            }
        )


def check_teammate_limit(workspace: "Workspace") -> None:
    """Raise TierLimitExceeded if creating a teammate now would
    push the workspace past its tier's teammate cap.

    Error code ``spokesperson_limit_reached`` and the customer-
    facing message text are external contracts consumed by the
    SPA — preserved unchanged per §17.1.b even after the internal
    rename from Teammate to Teammate.
    """
    usage = get_usage(workspace)
    if usage.spokespeople_limit is None:
        return
    if usage.spokespeople_used >= usage.spokespeople_limit:
        raise TierLimitExceeded(
            {
                "code": "spokesperson_limit_reached",
                "message": (
                    f"Your {usage.tier.capitalize()} plan includes "
                    f"{usage.spokespeople_limit} spokesperson"
                    f"{'s' if usage.spokespeople_limit != 1 else ''}."
                ),
                "current_tier": usage.tier,
                "spokespeople_used": usage.spokespeople_used,
                "spokespeople_limit": usage.spokespeople_limit,
                "suggested_tier": _suggest_upgrade(usage.tier),
            }
        )


def check_realtime_session_limit(workspace: "Workspace") -> None:
    """Raise TierLimitExceeded if creating a realtime session now
    would push the workspace past its monthly session-count cap.

    R3 first line of defense — coarse gate that catches obvious
    abuse (many short sessions). R9 added the finer-grained
    minutes budget gate (``check_realtime_minutes_budget``) that
    fires alongside this one.
    """
    usage = get_usage(workspace)
    if usage.realtime_sessions_limit is None:
        return  # unlimited tier
    if usage.realtime_sessions_used >= usage.realtime_sessions_limit:
        raise TierLimitExceeded(
            {
                "code": "realtime_session_limit_reached",
                "message": (
                    f"You've used all {usage.realtime_sessions_limit} "
                    f"realtime sessions in your {usage.tier.capitalize()} "
                    "plan this month."
                ),
                "current_tier": usage.tier,
                "realtime_sessions_used": usage.realtime_sessions_used,
                "realtime_sessions_limit": usage.realtime_sessions_limit,
                "suggested_tier": _suggest_upgrade(usage.tier),
            }
        )


def check_realtime_minutes_budget(
    workspace: "Workspace",
    requested_minutes: int = 5,
) -> None:
    """Raise TierLimitExceeded if creating a realtime session
    now would push the workspace past its monthly minutes
    budget.

    R9 second line of defense — finer-grained than
    ``check_realtime_session_limit``. Both gates fire at
    session-create time; either can independently veto.

    Args:
        workspace: workspace the session would belong to.
        requested_minutes: projected session length in
            minutes. Defaults to the provider cap (5 for
            Runway). The check enforces "current usage +
            requested <= cap"; if a partial-minute session
            (say 3 min) is the realistic projection, pass
            ``requested_minutes=3``.

    The session-count gate stays the primary surface; this
    one catches long-talkers that the session-count gate
    misses (e.g., 5 × 5-minute sessions = 25 minutes burned
    by Starter, under the 5-session cap but at the 30-min
    minutes cap).
    """
    usage = get_usage(workspace)
    if usage.realtime_minutes_limit is None:
        return  # unlimited tier
    projected = usage.realtime_minutes_used + max(1, requested_minutes)
    if projected > usage.realtime_minutes_limit:
        raise TierLimitExceeded(
            {
                "code": "realtime_minutes_limit_reached",
                "message": (
                    f"You've used {usage.realtime_minutes_used} of "
                    f"{usage.realtime_minutes_limit} realtime minutes "
                    f"in your {usage.tier.capitalize()} plan this "
                    "month."
                ),
                "current_tier": usage.tier,
                "realtime_minutes_used": usage.realtime_minutes_used,
                "realtime_minutes_limit": usage.realtime_minutes_limit,
                "requested_minutes": requested_minutes,
                "suggested_tier": _suggest_upgrade(usage.tier),
            }
        )


def _subscription_for(workspace: "Workspace") -> Subscription:
    """Return the workspace's subscription. If it doesn't exist (e.g.,
    legacy workspace pre-signal), create a default Starter subscription
    so the rest of the code path has something to read."""
    sub = Subscription.objects.filter(workspace=workspace).first()
    if sub is None:
        sub = Subscription.objects.create(
            workspace=workspace,
            tier=Subscription.Tier.STARTER,
            status=Subscription.Status.TRIALING,
        )
    return sub


def get_workspace_tier(workspace: "Workspace") -> str:
    """Public tier accessor — returns the workspace's tier string
    (``'starter'`` / ``'pro'`` / ``'agency'``). Used by callers that
    want to gate features without pulling the full Usage shape
    (e.g. R7.1's tool-catalog filtering by tier).

    Lazy-creates a Starter subscription for workspaces missing one,
    matching the rest of the billing module's contract.
    """
    return _subscription_for(workspace).tier


# Surface TIER_LIMITS for callers (e.g., admin views) that just want
# to render the tier table without hitting the model layer.
__all__ = [
    "TIER_LIMITS",
    "TierLimitExceeded",
    "Usage",
    "check_drafts_per_month",
    "check_realtime_minutes_budget",
    "check_realtime_session_limit",
    "check_teammate_limit",
    "check_video_limit",
    "get_usage",
    "get_workspace_tier",
]
