"""Brand identity data + helpers.

Ported SESSION 122 from
`a sibling private-project source module`.
The agent harness was stripped — the data dicts are pure, no
dependencies. Added helper functions to make consumers' lives easy.

Use sites in character-os (planned):

  - **Teammate create wizard.** Infer a tone + palette from the
    typed business_brief; suggest it as a default in the portrait /
    voice steps. Operator can override.
  - **Portrait generation** (when AI-generated portraits land as an
    alternative to upload/camera capture). Pipe the chosen style's
    ``characteristics`` into the Runway gen4_image prompt.
  - **Video render**. Pipe the chosen tone keywords into Runway's
    script prompt so the same spokesperson sounds coherent across
    every video.

All data is **pure literal** — no Django, no I/O, no LLM calls.
"""
from __future__ import annotations

from typing import Optional


# Six named palettes covering the v1 archetype space. Hex values are
# unchanged from the sibling project; the keys map to industry vibes, not
# customer-facing brand names. Surface friendly names via
# BRAND_STYLES + INDUSTRY_PALETTE_MAP when needed.
COLOR_PALETTES: dict[str, dict[str, str]] = {
    "tech_modern": {
        "primary": "#2563EB",
        "secondary": "#1E293B",
        "accent": "#10B981",
        "background": "#F8FAFC",
        "text": "#0F172A",
    },
    "creative_bold": {
        "primary": "#EC4899",
        "secondary": "#8B5CF6",
        "accent": "#F59E0B",
        "background": "#FFFFFF",
        "text": "#1F2937",
    },
    "professional_corporate": {
        "primary": "#1E40AF",
        "secondary": "#475569",
        "accent": "#0EA5E9",
        "background": "#F9FAFB",
        "text": "#111827",
    },
    "eco_natural": {
        "primary": "#059669",
        "secondary": "#065F46",
        "accent": "#D97706",
        "background": "#ECFDF5",
        "text": "#1F2937",
    },
    "luxury_elegant": {
        "primary": "#1C1917",
        "secondary": "#78716C",
        "accent": "#CA8A04",
        "background": "#FAFAF9",
        "text": "#1C1917",
    },
    "startup_energetic": {
        "primary": "#7C3AED",
        "secondary": "#2DD4BF",
        "accent": "#FB923C",
        "background": "#FFFFFF",
        "text": "#18181B",
    },
}


# Style descriptors that translate well into LLM/image-gen prompts.
# Each style names what to lean into + what to avoid + font family
# hints. The ``avoid`` list is critical for negative prompting on
# image-gen models.
BRAND_STYLES: dict[str, dict[str, list[str]]] = {
    "minimalist": {
        "characteristics": ["clean lines", "white space", "simple shapes"],
        "avoid": ["clutter", "gradients", "complex patterns"],
        "fonts": ["sans-serif", "geometric"],
    },
    "modern": {
        "characteristics": ["bold", "contemporary", "dynamic"],
        "avoid": ["ornate details", "traditional elements"],
        "fonts": ["sans-serif", "modern serif"],
    },
    "playful": {
        "characteristics": ["fun", "colorful", "energetic", "rounded shapes"],
        "avoid": ["corporate", "formal", "straight lines"],
        "fonts": ["rounded", "handwritten"],
    },
    "professional": {
        "characteristics": ["trustworthy", "clean", "established"],
        "avoid": ["casual", "trendy", "experimental"],
        "fonts": ["classic serif", "traditional sans-serif"],
    },
    "artistic": {
        "characteristics": ["creative", "unique", "expressive"],
        "avoid": ["generic", "corporate", "template-like"],
        "fonts": ["display", "decorative"],
    },
    "tech": {
        "characteristics": ["futuristic", "digital", "innovative"],
        "avoid": ["organic", "traditional", "handmade"],
        "fonts": ["geometric sans-serif", "monospace"],
    },
}


INDUSTRY_PALETTE_MAP: dict[str, str] = {
    "tech": "tech_modern",
    "creative": "creative_bold",
    "corporate": "professional_corporate",
    "eco": "eco_natural",
    "luxury": "luxury_elegant",
    "startup": "startup_energetic",
}


# Keyword signals used by suggest_palette_from_brief. Order matters:
# the first match wins. The keys mirror INDUSTRY_PALETTE_MAP so the
# palette returned is one of the six known names.
_BRIEF_INDUSTRY_HINTS: list[tuple[str, list[str]]] = [
    ("eco", ["sustainab", "organic", "eco", "plant-based", "green", "natural"]),
    ("luxury", ["luxury", "premium", "artisan", "handcraft", "bespoke", "high-end"]),
    ("tech", ["software", "app", "saas", "platform", "ai", "developer", "engineer", "tech"]),
    ("creative", ["design", "art", "creative", "studio", "agency", "illustrat"]),
    ("startup", ["startup", "founder", "early-stage", "indie hack", "side project"]),
    ("corporate", ["b2b", "enterprise", "compliance", "industry", "firm", "consult"]),
]


def get_palette(name: str) -> Optional[dict[str, str]]:
    """Return a palette by name; ``None`` if the key isn't known.

    Accepts either an internal key (``tech_modern``) or an industry
    alias (``tech``) via ``INDUSTRY_PALETTE_MAP``.
    """
    if name in COLOR_PALETTES:
        return COLOR_PALETTES[name]
    industry_key = INDUSTRY_PALETTE_MAP.get(name)
    if industry_key:
        return COLOR_PALETTES.get(industry_key)
    return None


def get_style(name: str) -> Optional[dict[str, list[str]]]:
    """Return a brand style descriptor by name; ``None`` if not known."""
    return BRAND_STYLES.get(name)


def suggest_palette_from_brief(brief: str) -> str:
    """Infer the best-fit palette name from a business brief.

    Falls back to ``professional_corporate`` when no keywords match —
    that's the safest neutral default for the SMB audience the design
    lock targets.

    Returns a palette key (one of ``COLOR_PALETTES.keys()``).
    """
    text = (brief or "").lower()
    for industry, hints in _BRIEF_INDUSTRY_HINTS:
        if any(h in text for h in hints):
            return INDUSTRY_PALETTE_MAP[industry]
    return "professional_corporate"


# ---- Tone archetype helpers (SESSION 127 — wizard slice 4) ---------
#
# The five archetypes mirror ``Teammate.Tone`` and the wizard
# scope-lock (`docs/design/CREATE_SPOKESPERSON_WIZARD.md`
# §"Tone archetypes"). Keep this list in sync with the model when
# either side changes.

TONE_ARCHETYPES: tuple[str, ...] = (
    "tutor",
    "authority",
    "friend",
    "expert",
    "performer",
)


# Keyword signals per archetype. Same shape as _BRIEF_INDUSTRY_HINTS:
# first match wins, falls back to ``expert``. Hints are deliberately
# spelled as substrings so common stems match without us writing every
# inflection (`teach` matches `teaches`, `teaching`, `teacher`).
_BRIEF_TONE_HINTS: list[tuple[str, list[str]]] = [
    # tutor — education + scaffolded explanation
    ("tutor", [
        "teach", "tutor", "lesson", "classroom", "student", "course",
        "curriculum", "educator", "homeschool", "learn ", "explainer",
    ]),
    # performer — entertainment, hype, persuasion
    ("performer", [
        "entertain", "perform", "host", "comedian", "showman", "creator",
        "influencer", "viral", "stage", "stand-up", "hype", "promote",
    ]),
    # friend — peer-level, casual, community
    ("friend", [
        "friend", "buddy", "neighbor", "community", "peer", "casual",
        "approachable", "small-business", "local shop", "mom-and-pop",
    ]),
    # authority — direct, decisive, expert claim
    ("authority", [
        "leader", "authoritative", "decisive", "blunt", "no-nonsense",
        "straight-talk", "ceo", "executive", "command", "the truth",
    ]),
    # expert is the fallback — no positive hints, just structured /
    # credentialed signals as a tiebreaker before the default kicks in.
    ("expert", [
        "expert", "specialist", "phd", "research", "academic", "evidence",
        "credential", "engineer", "scientist", "consult",
    ]),
]


def suggest_tone_from_brief(brief: str) -> str:
    """Infer the best-fit tone archetype from a business brief.

    Returns one of ``TONE_ARCHETYPES``. Falls back to ``"expert"`` when
    no keywords match — the safest neutral for SMBs (same calibration
    as ``suggest_palette_from_brief``'s ``professional_corporate``
    default).

    Pure function: no I/O, no LLM calls. Cheap keyword scan, ordered
    so that the more distinctive archetypes (tutor, performer) win
    over the generic ones when both could match.
    """
    text = (brief or "").lower()
    for tone, hints in _BRIEF_TONE_HINTS:
        if any(h in text for h in hints):
            return tone
    return "expert"
