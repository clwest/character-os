"""Named spokesperson templates for the wizard's Step 1 tile picker
(SESSION 133 — wizard slice 10).

Four starter templates per `docs/design/CREATE_SPOKESPERSON_WIZARD.md`
§"Templates": Riggs (SMB owner / authority), Sasha (creator / friend),
Donny (local business / expert), Maya (educator / tutor).

The CONTENT in this file is operator-collaborative starter material.
The mechanism (data shape + endpoint + tile UI) is the deliverable;
the briefs + visual subjects + voice presets are first drafts that
real operators will refine. Future sessions can rewrite the content
without touching the surrounding plumbing.

Stored as pure literals — no Django models, no DB. The wizard's
Step 1 tile picker reads ``TEMPLATES`` via the
``GET /api/spokespeople/templates/`` action; clicking a tile
dispatches the matching record's fields into the wizard reducer.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpokespersonTemplate:
    """One starter template the operator can pick on Step 1.

    Field shape mirrors the create-spokesperson payload + the wizard
    reducer's ``identity`` bag. Picking a template dispatches
    ``SET_IDENTITY`` (name + business_brief + tone + visual_subject)
    on the SPA side; the wizard's Step 2 Generate tab + Step 3
    Voice tab pick up ``visual_template`` and ``voice_preset``
    respectively when the operator continues through.
    """
    key: str  # url-safe slug
    name: str  # display name (Step 1 + tile label)
    tagline: str  # one-line audience description for the tile
    business_brief: str
    tone_archetype: str  # one of Spokesperson.Tone
    visual_template: str  # one of SUPPORTED_PORTRAIT_TEMPLATES
    visual_subject: str
    voice_preset: str  # one of SUPPORTED_VOICE_PRESETS


# Order is the tile display order on Step 1. Reordering here changes
# the operator-facing tile layout.
TEMPLATES: tuple[SpokespersonTemplate, ...] = (
    SpokespersonTemplate(
        key="riggs",
        name="Riggs",
        tagline="SMB owners — coffee shops, retail, professional services",
        business_brief=(
            "Owner-operator of a small business. Speaks directly to "
            "the camera about what makes the shop different — the "
            "craft, the people, the standards. Confident but not "
            "corporate."
        ),
        tone_archetype="authority",
        visual_template="founder",
        visual_subject="a polished founder spokesperson, mid-30s",
        voice_preset="vincent",
    ),
    SpokespersonTemplate(
        key="sasha",
        name="Sasha",
        tagline="Creators — coaches, course-sellers, lifestyle brands",
        business_brief=(
            "Coach and course creator. Speaks to the audience like a "
            "trusted friend with hard-won expertise. Warm, peer-level, "
            "actionable — never preachy."
        ),
        tone_archetype="friend",
        visual_template="coach",
        visual_subject="an energetic coach spokesperson, mid-30s, with a confident bright expression",
        voice_preset="clara",
    ),
    SpokespersonTemplate(
        key="donny",
        name="Donny",
        tagline="Local businesses — bike shops, restaurants, contractors",
        business_brief=(
            "Local-business face that knows the trade inside out. "
            "Speaks with the precision of someone who's done this for "
            "decades. Audience is the neighborhood — friendly but "
            "technically credible."
        ),
        tone_archetype="expert",
        visual_template="local_guide",
        visual_subject="a welcoming local-business spokesperson",
        voice_preset="drew",
    ),
    SpokespersonTemplate(
        key="maya",
        name="Maya",
        tagline="Educators — teachers, course-creators, homeschool tutors",
        business_brief=(
            "Patient educator who scaffolds explanations. Speaks to "
            "students like a tutor working through a problem together. "
            "Optimised for clarity over polish — meets learners where "
            "they are. (Added per James's classroom use case.)"
        ),
        tone_archetype="tutor",
        visual_template="mascot",
        visual_subject="a friendly classroom mascot character",
        voice_preset="victoria",
    ),
)

# Index by key for O(1) lookup.
_BY_KEY: dict[str, SpokespersonTemplate] = {t.key: t for t in TEMPLATES}


def get_template(key: str) -> SpokespersonTemplate | None:
    """Return a template by its slug, or ``None`` if unknown.

    Keys are case-insensitive on lookup (stored lowercase).
    """
    return _BY_KEY.get((key or "").strip().lower())
