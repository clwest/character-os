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
    sub = _subscription_for(workspace)
    videos_used = Video.objects.filter(
        spokesperson__workspace=workspace,
        created_at__gte=sub.current_period_start,
        created_at__lt=sub.current_period_end,
    ).count()
    spokespeople_used = Spokesperson.objects.filter(workspace=workspace).count()
    return Usage(
        tier=sub.tier,
        status=sub.status,
        videos_used=videos_used,
        videos_limit=sub.videos_per_month,
        spokespeople_used=spokespeople_used,
        spokespeople_limit=sub.spokespeople_limit,
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


# Surface TIER_LIMITS for callers (e.g., admin views) that just want
# to render the tier table without hitting the model layer.
__all__ = [
    "TIER_LIMITS",
    "TierLimitExceeded",
    "Usage",
    "check_spokesperson_limit",
    "check_video_limit",
    "get_usage",
]
