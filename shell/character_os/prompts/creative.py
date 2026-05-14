"""Creative principles per content kind.

Ported SESSION 122 from
``unified-donkey-betz/core/agents/executive/creative_director_agent.py``.
The agent harness was stripped; the ``CREATIVE_PRINCIPLES`` dict is
pure data. Keys were **adapted** for character-os: u-d-b shipped
``logo`` / ``thumbnail`` / ``social`` (not directly relevant to a
spokesperson-driven video product). character-os keys it on our
actual video kinds — ``spokesperson_ad`` is shipped end-to-end after
SESSION 121; the others (``cinematic_video``, ``dialogue_scene``,
``long_ad``) ship in subsequent slices.

Use sites in character-os (planned):

  - **Make-a-video render prompt augmentation.** When the operator
    submits a brief, ``principles_for_kind(video.kind)`` returns the
    right guidance dict; the backend can inject it into the Runway
    script prompt so cinematic videos sound cinematic, dialogue
    scenes feel like dialogue, etc.
  - **Thumbnail / social variants.** Kept from u-d-b for Phase 4+
    when the SPA grows variant-export UI.

All data is pure literal — no Django, no I/O, no LLM calls.
"""
from __future__ import annotations

from typing import Optional


# Per-kind creative guidance. Shape: each kind has three lists —
# ``key_principles`` (positive signals), ``common_mistakes``
# (negative signals for negative prompting), and
# ``enhancement_tips`` (concrete operator nudges).
CREATIVE_PRINCIPLES: dict[str, dict[str, list[str]]] = {
    # === Shipped (SESSION 121 video pipeline) ========================
    "spokesperson_ad": {
        "key_principles": [
            "Direct address — the spokesperson speaks to one viewer, not a crowd",
            "Confidence in 5-10 seconds — the hook lands fast",
            "One claim, one CTA — no buried lede",
            "Tone matches the business brief — the spokesperson sounds like the brand",
        ],
        "common_mistakes": [
            "Reading the brief verbatim — sounds like a brochure",
            "Multiple competing CTAs",
            "Trying to be funny when the brand isn't",
            "Generic openings ('Hey everyone…')",
        ],
        "enhancement_tips": [
            "Lead with the problem the customer has, not the solution",
            "Use the operator's actual words from the brief where possible",
            "End with one specific action ('Tap the link', 'Book a call')",
            "Keep the script under ~80 words for a 30s ad",
        ],
    },

    # === Planned (subsequent slices) =================================
    "cinematic_video": {
        "key_principles": [
            "Atmosphere over information — the video sells a feeling",
            "Single visual idea per clip — don't cram multiple beats",
            "Tonal continuity with the spokesperson's voice",
            "Score / pacing serves the spokesperson, not the other way",
        ],
        "common_mistakes": [
            "Generic stock-footage feel",
            "On-screen text that competes with the spokesperson",
            "Music that overpowers the voice",
            "Cuts that contradict the spoken pacing",
        ],
        "enhancement_tips": [
            "Pick one verb the video performs ('show', 'evoke', 'tease')",
            "Resolve every cut on the spokesperson's word",
            "Match the colour grade to the brand palette",
            "Use silence — 1-2 second beats between phrases",
        ],
    },
    "dialogue_scene": {
        "key_principles": [
            "Two distinct voices — each spokesperson has their own opinion",
            "Tension before resolution — a real exchange, not a script",
            "Brevity — 60s max for v1",
            "The audience learns something each spokesperson didn't already know",
        ],
        "common_mistakes": [
            "One spokesperson agreeing with everything the other says",
            "Both spokespeople reading the same brief",
            "On-the-nose 'as you know' setups",
            "Equal screen time when one has the more interesting line",
        ],
        "enhancement_tips": [
            "Define each spokesperson's stance in one sentence before drafting",
            "Trade lines under ~12 words to keep cadence brisk",
            "End on the less-expected position",
            "Pick one spokesperson to ask the question, the other to answer",
        ],
    },
    "long_ad": {
        "key_principles": [
            "Three acts — hook, deepen, close. Each ~30s.",
            "One throughline — the same claim threads the whole runtime",
            "Earned CTAs — the longer the ad, the harder the close should hit",
            "Repeat the brand 2-3 times, not more",
        ],
        "common_mistakes": [
            "Padding scenes that don't advance the throughline",
            "Multiple disconnected vignettes",
            "Saving the CTA for the last 5 seconds",
            "Repeating the same beat at different lengths",
        ],
        "enhancement_tips": [
            "Outline the three acts before writing any line",
            "Front-load the strongest claim in the first 10s",
            "Build emotional stakes in act 2 — not just more information",
            "Land the CTA twice: midpoint preview + close",
        ],
    },

    # === Kept from u-d-b for Phase 4+ uses ===========================
    "thumbnail": {
        "key_principles": [
            "Curiosity gap — make viewers want to click",
            "Bold, readable text (3-5 words max)",
            "High contrast and saturation",
            "Human faces with expressions",
        ],
        "common_mistakes": [
            "Too much text",
            "Low contrast",
            "No clear focal point",
            "Misleading content",
        ],
        "enhancement_tips": [
            "Use complementary colors for text",
            "Include a human element",
            "Create visual hierarchy",
            "Match video content",
        ],
    },
    "social": {
        "key_principles": [
            "Stop the scroll — first impression matters",
            "Platform-native aesthetics",
            "Clear message in 3 seconds",
            "Emotional connection",
        ],
        "common_mistakes": [
            "Generic stock imagery",
            "Too much text",
            "Off-brand colors",
            "No clear CTA",
        ],
        "enhancement_tips": [
            "Use platform-specific formats",
            "Lead with strong visuals",
            "Include brand elements subtly",
            "Test different variations",
        ],
    },
}


def principles_for_kind(kind: str) -> Optional[dict[str, list[str]]]:
    """Return the creative-principles dict for a content kind.

    ``kind`` matches ``Video.Kind`` choices for the shipped + planned
    cases; ``thumbnail`` / ``social`` covered too for Phase 4+ uses.
    Returns ``None`` for unknown kinds so callers can fall back to a
    generic prompt without crashing.
    """
    return CREATIVE_PRINCIPLES.get(kind)
