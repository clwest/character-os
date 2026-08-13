"""Realtime cost estimation — R9 (SESSION 156).

Per-provider cost lookups + helpers for stamping
``cost_estimate_micros`` + ``cost_actual_micros`` on
``RealtimeSession`` rows. Same shape as V's per-primitive
cost estimators (V's Q-v-4 resolution).

v1 ships with one provider (Runway) at a conservative
$0.08/min placeholder. The shape exists so the operator
can plug in real per-provider rates as they're negotiated
without touching the broker or SPA call sites — they all
go through this module.

Cost convention everywhere: **micros of USD** (1 USD =
1_000_000 micros). Matches `cost_estimate_micros` /
`cost_actual_micros` field types on the model (positive
integer).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import RealtimeSession


# Provider rate table. One entry per supported provider.
# Adding a new provider (Synthesia, HeyGen, etc.) is one
# row here — the broker and the SPA stay stable.
#
# Source: Runway's avatar conversation pricing as of
# 2026-05. Conservative placeholder; the operator should
# refine when real billing data lands.
_PROVIDER_RATES: dict[str, int] = {
    "runway": 80_000,  # $0.08 per minute
}

# Fallback when an unknown provider name lands on the
# session row. Defensive — the same rate the SPA's
# hardcoded forecast used pre-R9 (so the UX doesn't
# regress on a misconfigured workspace).
DEFAULT_RATE_MICROS_PER_MINUTE = 80_000

# Runway's per-session cap. The SPA forecast uses this
# alongside the rate to project "~$X for an N-minute
# session." Lives here so SPA + broker share one
# constant (currently the SPA also has a copy — R9 ships
# the hook that consumes this number, but keeps the SPA
# constant as a fallback for the no-key case).
PROVIDER_MAX_SESSION_MINUTES = 5


def cost_per_minute_micros(provider: str) -> int:
    """Return the per-minute cost for the named provider.

    Defensive: unknown providers fall back to
    ``DEFAULT_RATE_MICROS_PER_MINUTE`` so a misconfigured
    workspace doesn't accidentally return 0 (which would
    free-tier-by-mistake all of its sessions).
    """
    return _PROVIDER_RATES.get(provider, DEFAULT_RATE_MICROS_PER_MINUTE)


def estimate_session_cost_micros(
    provider: str,
    minutes: float = PROVIDER_MAX_SESSION_MINUTES,
) -> int:
    """Estimate a session's cost in micros, given a
    provider + projected length.

    The broker calls this at session-create time with the
    full provider cap (5 min for Runway) so the stamped
    `cost_estimate_micros` reflects the worst-case spend.
    The SPA's cost-forecast pill uses the same calculation
    via the `/cost_estimate/` endpoint.

    Args:
        provider: provider name (matches
            ``RealtimeSession.provider`` choices).
        minutes: projected session length. Defaults to the
            provider's hard cap.

    Returns:
        Cost in micros. ``int`` — fractional micros are
        rounded down (matches positive-integer field
        contract).
    """
    rate = cost_per_minute_micros(provider)
    return max(0, int(rate * minutes))


def actual_session_cost_micros(session: "RealtimeSession") -> int:
    """Compute a session's actual cost from its
    `duration_seconds` field.

    The broker's `_end_session` flow already computes
    `duration_seconds` from `started_at` / `now`. This
    helper just converts to micros at the provider's
    per-minute rate. Called from the same `_end_session`
    flow + saved alongside `duration_seconds`.

    Returns 0 for sessions with zero duration (the
    create-failed paths that flip directly to FAILED
    without going live).
    """
    if session.duration_seconds <= 0:
        return 0
    minutes = session.duration_seconds / 60
    rate = cost_per_minute_micros(session.provider)
    return max(0, int(rate * minutes))
