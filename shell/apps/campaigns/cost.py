"""Cost helpers for the personalized-video arc.

C-arc slice B3.5 (SESSION 203). Q-c-2 resolution: new module
rather than coupling to R9 (realtime session cost helper has
different shape).

One constant + one function. The forecast endpoint reads
``estimate_campaign_cost_micros`` to surface the projected
spend in the SPA launch modal.
"""
from __future__ import annotations

# Per-recipient cost of one ``talking_head_polished`` render.
# Anchored to the B-arc SESSION 202 dogfood: composition
# b4ab9ea6 burned $0.25 for a 5s Marcus speech render.
# Personalized scripts will mostly be in this length range
# (~30s of speech for a 280-char script per scope-lock rule 8);
# we use the same $0.25 ballpark for forecast purposes. Real
# spend per render varies with the per-recipient script
# length; this is a "good enough" projection for the launch-
# time approval gate.
PER_RECIPIENT_COST_MICROS = 250_000  # $0.25


def estimate_campaign_cost_micros(recipient_count: int) -> int:
    """Return the projected total cost in micros for firing
    ``recipient_count`` per-recipient compositions.

    Rounds nothing; the gates upstream (per-batch cap +
    per-month videos cap) prevent runaway batches. This
    helper is purely informational — drives the SPA launch
    modal + the forecast endpoint's payload.
    """
    if recipient_count < 0:
        return 0
    return recipient_count * PER_RECIPIENT_COST_MICROS
