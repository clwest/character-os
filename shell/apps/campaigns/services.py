"""Tier-gate + rollup helpers for the personalized-video arc.

B3.5 + B3.6 (SESSION 203).

Two helper surfaces:

* ``check_personalized_batch(workspace, recipient_count)`` —
  composite tier gate. Per scope-lock rule 4: per-batch cap +
  per-month videos cap. Raises ``TierLimitExceeded``.
* ``rollup_campaign_status(campaign)`` — examines the
  recipients' terminal-state distribution and flips the
  campaign to COMPLETED / PARTIAL / FAILED accordingly.
  Called by the post_save Composition signal (B3.6) and by
  the per-recipient retry handler.

Both gates checked at LAUNCH time, not at create time —
operator can draft batches over-cap and trim before launching.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

from apps.billing.models import tier_limit
from apps.billing.services import (
    TierLimitExceeded,
    _suggest_upgrade,
    get_usage,
)

if TYPE_CHECKING:
    from apps.accounts.models import Workspace

    from .models import PersonalizedCampaign


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


def rollup_campaign_status(campaign: "PersonalizedCampaign") -> bool:
    """Examine recipient terminal-state distribution; flip
    the campaign's status accordingly.

    Returns True when the campaign reached a new terminal
    state (COMPLETED / PARTIAL / FAILED) on this call; False
    when nothing changed.

    Rules:
    * Any recipient still PENDING / QUEUED / RUNNING → leave
      campaign in IN_FLIGHT (or LAUNCHING). Don't flip.
    * All recipients terminal (COMPLETED or FAILED):
        * All COMPLETED → campaign COMPLETED.
        * Some COMPLETED, some FAILED → campaign PARTIAL.
        * All FAILED → campaign FAILED.
    * Sets ``completed_at`` on the campaign for any terminal
      flip.

    Idempotent — calling it on a campaign already in a
    terminal state is safe; will return False since the
    status doesn't change.

    Lazy import for the model — this helper is called from
    apps.campaigns.signals at module-load-via-ready() time,
    so the model import has to happen at call time, not
    module-load time.
    """
    from .models import PersonalizedCampaign, PersonalizedRecipient

    status_counts = {
        choice: 0
        for choice, _ in PersonalizedRecipient.Status.choices
    }
    for status_value in campaign.recipients.values_list(
        "status", flat=True,
    ):
        status_counts[status_value] = status_counts.get(status_value, 0) + 1

    terminal = (
        status_counts[PersonalizedRecipient.Status.COMPLETED]
        + status_counts[PersonalizedRecipient.Status.FAILED]
    )
    in_flight = (
        status_counts[PersonalizedRecipient.Status.PENDING]
        + status_counts[PersonalizedRecipient.Status.QUEUED]
        + status_counts[PersonalizedRecipient.Status.RUNNING]
    )
    total = terminal + in_flight

    if total == 0 or in_flight > 0:
        # Either no recipients at all (unlikely; launch
        # rejects empty batches) or at least one still
        # running.
        return False

    succeeded = status_counts[PersonalizedRecipient.Status.COMPLETED]
    failed = status_counts[PersonalizedRecipient.Status.FAILED]
    if succeeded == terminal:
        new_status = PersonalizedCampaign.Status.COMPLETED
    elif failed == terminal:
        new_status = PersonalizedCampaign.Status.FAILED
    else:
        new_status = PersonalizedCampaign.Status.PARTIAL

    if campaign.status == new_status:
        return False

    campaign.status = new_status
    if campaign.completed_at is None:
        campaign.completed_at = timezone.now()
    campaign.save(update_fields=[
        "status", "completed_at", "updated_at",
    ])
    return True
