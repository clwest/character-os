"""Prompt helpers — Tier 1 port from unified-donkey-betz.

Stateless utility module. No Django models, no migrations, no API
endpoints (yet). Public surface is plain Python functions + data
dicts that future slices (wizard, render flow, voice clone naming,
portrait generation) can compose freely.

Provenance: ported SESSION 122 from
``unified-donkey-betz/core/prompts/sharpening.py`` +
``unified-donkey-betz/core/agents/strategy/brand_identity_agent.py``
+ ``unified-donkey-betz/core/agents/executive/creative_director_agent.py``.
The agent harness around the latter two was stripped — only the
load-bearing data + helper functions ported. See
``docs/design/PROMPT_HELPERS.md`` for the rationale + public API.

The deeper port (Tier 2: DynamicPromptBuilder) is deferred — see
the SESSION 122 handoff.
"""
from __future__ import annotations

from .brand import (
    BRAND_STYLES,
    COLOR_PALETTES,
    INDUSTRY_PALETTE_MAP,
    get_palette,
    get_style,
    suggest_palette_from_brief,
)
from .creative import CREATIVE_PRINCIPLES, principles_for_kind
from .sharpening import (
    SHARP_ANALYSIS_RULES,
    SHARP_DEBATE_RULES,
    SHARP_SYNTHESIS_RULES,
    SHARPENING_REPLACEMENTS,
    add_sharpening_rules,
    check_prompt_sharpness,
    clean_business_brief,
    sharpen_prompt,
)

__all__ = [
    # sharpening
    "SHARPENING_REPLACEMENTS",
    "SHARP_DEBATE_RULES",
    "SHARP_SYNTHESIS_RULES",
    "SHARP_ANALYSIS_RULES",
    "sharpen_prompt",
    "add_sharpening_rules",
    "check_prompt_sharpness",
    "clean_business_brief",
    # brand
    "COLOR_PALETTES",
    "BRAND_STYLES",
    "INDUSTRY_PALETTE_MAP",
    "get_palette",
    "get_style",
    "suggest_palette_from_brief",
    # creative
    "CREATIVE_PRINCIPLES",
    "principles_for_kind",
]
