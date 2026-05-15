"""Subscription + tier definitions for workspaces.

The customer-facing monetization shape from design doc §2.1:

    Starter $29/mo — 10 videos/mo, 1 spokesperson, 1 seat
    Pro     $79/mo — 30 videos/mo, 3 spokespeople, 1 seat
    Agency $199/mo — unlimited videos + spokespeople, 5 seats + $30/extra

This module ships the **gating data model** — what tier each workspace
is on and how the limits translate to enforceable numbers. The actual
Stripe integration (customer creation, webhook handling, customer
portal) lives in a follow-up slice once real Stripe credentials are
wired through env. The ``stripe_customer_id`` + ``stripe_subscription_id``
fields are landing zones that ``dj-stripe`` will populate once it does.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.accounts.models import Workspace


# ---- Tier definitions -------------------------------------------------

# `None` for any field means "unlimited" — design doc §2.1 reserves
# this for Agency. Spokesperson + seat values come straight from the
# design doc table; videos_per_month is the headline number.
TIER_LIMITS: dict[str, dict[str, int | None]] = {
    "starter": {
        "videos_per_month": 10,
        "spokespeople": 1,
        "seats": 1,
        # R3 — realtime session monthly cap. Each session
        # burns Runway audio/video minutes; the cap is the
        # first line of defense against runaway cost. R9
        # adds `realtime_minutes_per_month` as the
        # finer-grained second gate.
        "realtime_sessions_per_month": 5,
        # R9 (SESSION 156) — per-month minutes budget.
        # `check_realtime_minutes_budget` enforces at
        # session-create alongside the session-count
        # gate.
        "realtime_minutes_per_month": 30,
        "price_usd": 29,
    },
    "pro": {
        "videos_per_month": 30,
        "spokespeople": 3,
        "seats": 1,
        "realtime_sessions_per_month": 20,
        "realtime_minutes_per_month": 120,
        "price_usd": 79,
    },
    "agency": {
        "videos_per_month": None,
        "spokespeople": None,
        "seats": 5,
        "realtime_sessions_per_month": None,
        "realtime_minutes_per_month": None,
        "price_usd": 199,
    },
}


def tier_limit(tier: str, key: str) -> int | None:
    """Look up a single tier limit; falls back to Starter on unknown tier."""
    table = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])
    return table.get(key)


# ---- Subscription model -----------------------------------------------


class Subscription(models.Model):
    """One subscription per workspace. Tracks which tier they're on,
    the current billing period (for the usage meter), and the Stripe
    identifiers that ``dj-stripe`` will fill in once wired."""

    class Tier(models.TextChoices):
        STARTER = "starter", "Starter ($29/mo)"
        PRO = "pro", "Pro ($79/mo)"
        AGENCY = "agency", "Agency ($199/mo)"

    class Status(models.TextChoices):
        # Trial — design doc §2.1: 3 free videos, no card required.
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past due"
        CANCELED = "canceled", "Canceled"
        UNPAID = "unpaid", "Unpaid"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(
        Workspace,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    tier = models.CharField(max_length=20, choices=Tier.choices, default=Tier.STARTER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)

    # Billing period — used by the usage meter. For trial-mode workspaces
    # the period starts at creation and runs 30 days; for active Stripe
    # subscriptions these get overwritten by dj-stripe on webhook.
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()

    # Stripe landing-zone fields — empty until dj-stripe wires in.
    stripe_customer_id = models.CharField(max_length=120, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=120, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.workspace.name} — {self.get_tier_display()} ({self.status})"

    def save(self, *args, **kwargs) -> None:
        if not self.current_period_end:
            self.current_period_end = self.current_period_start + timedelta(days=30)
        super().save(*args, **kwargs)

    # Convenience accessors so callers don't have to look up TIER_LIMITS
    # themselves.

    @property
    def videos_per_month(self) -> int | None:
        return tier_limit(self.tier, "videos_per_month")

    @property
    def spokespeople_limit(self) -> int | None:
        return tier_limit(self.tier, "spokespeople")

    @property
    def seats_limit(self) -> int | None:
        return tier_limit(self.tier, "seats")
