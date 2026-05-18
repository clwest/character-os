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

from apps.spokespeople.models import Spokesperson
from apps.videos.models import Video

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
    from apps.realtime.models import RealtimeSession

    from django.db.models import Sum

    sub = _subscription_for(workspace)
    videos_used = Video.objects.filter(
        spokesperson__workspace=workspace,
        created_at__gte=sub.current_period_start,
        created_at__lt=sub.current_period_end,
    ).count()
    spokespeople_used = Spokesperson.objects.filter(workspace=workspace).count()
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
        period_start=sub.current_period_start.isoformat(),
        period_end=sub.current_period_end.isoformat(),
    )


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


def check_spokesperson_limit(workspace: "Workspace") -> None:
    """Raise TierLimitExceeded if creating a spokesperson now would
    push the workspace past its tier's spokesperson cap."""
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
    "check_realtime_minutes_budget",
    "check_realtime_session_limit",
    "check_spokesperson_limit",
    "check_video_limit",
    "get_usage",
    "get_workspace_tier",
]
