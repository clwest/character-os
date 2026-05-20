"""Tier-gate + launch helpers for the personalized-video arc.

B3.5 (SESSION 203). Composes the existing
``apps.billing.services.check_video_limit`` (per-month
videos cap) with the new ``personalized_batch_max`` per-batch
cap (Q-c-1 lock at TIER_LIMITS) to provide one
``check_personalized_batch`` entry point the launch endpoint
calls.

Two gates per scope-lock rule 4:

* **Per-batch cap** — Starter=5, Pro=30, Agency=200. Prevents
  one accidental click from blowing through a quarter's
  worth of monthly videos in one fire.
* **Per-month videos cap** — the existing
  ``videos_per_month`` ceiling. Launching N more videos
  must not push ``videos_used + N`` past the tier limit.

Both checked at LAUNCH time, not at create time — operator
can draft batches over-cap and trim before launching.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from apps.billing.models import tier_limit
from apps.billing.services import (
    TierLimitExceeded,
    _suggest_upgrade,
    get_usage,
)

if TYPE_CHECKING:
    from apps.accounts.models import Workspace


def check_personalized_batch(
    workspace: "Workspace", recipient_count: int,
) -> None:
    """Composite tier gate for B-3 campaign launch.

    Args:
        workspace: The campaign's workspace.
        recipient_count: How many compositions the launch
            will create.

    Raises:
        ``TierLimitExceeded`` with a structured payload:
        * ``code="personalized_batch_too_large"`` — batch
          exceeds the per-tier cap.
        * ``code="video_limit_reached"`` — launching this
          batch would push ``videos_used + recipient_count``
          past the monthly cap.
    """
    if recipient_count <= 0:
        # Nothing to launch — caller handles the "no recipients"
        # case as a 400 separately; this helper only gates
        # non-empty batches.
        return

    usage = get_usage(workspace)
    tier_name = usage.tier

    # Gate 1 — per-batch cap (rule 4 first dimension).
    batch_cap = tier_limit(tier_name, "personalized_batch_max")
    if batch_cap is not None and recipient_count > batch_cap:
        raise TierLimitExceeded({
            "code": "personalized_batch_too_large",
            "message": (
                f"This batch has {recipient_count} recipients but "
                f"your {tier_name.capitalize()} plan caps a single "
                f"batch at {batch_cap}."
            ),
            "current_tier": tier_name,
            "recipient_count": recipient_count,
            "batch_cap": batch_cap,
            "suggested_tier": _suggest_upgrade(tier_name),
        })

    # Gate 2 — per-month videos cap (rule 4 second dimension).
    # The existing check_video_limit raises when already at
    # the limit; for B-3 we need a forward-looking check
    # ("would adding N push us over?").
    if usage.videos_limit is None:
        return  # unlimited tier

    if usage.videos_used + recipient_count > usage.videos_limit:
        remaining = max(0, usage.videos_limit - usage.videos_used)
        raise TierLimitExceeded({
            "code": "video_limit_reached",
            "message": (
                f"Launching {recipient_count} videos would exceed "
                f"your {tier_name.capitalize()} plan's monthly "
                f"limit of {usage.videos_limit} (you've used "
                f"{usage.videos_used}; {remaining} remaining)."
            ),
            "current_tier": tier_name,
            "videos_used": usage.videos_used,
            "videos_limit": usage.videos_limit,
            "recipient_count": recipient_count,
            "remaining": remaining,
            "suggested_tier": _suggest_upgrade(tier_name),
        })
