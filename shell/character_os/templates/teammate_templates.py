"""Named spokesperson templates for the wizard's Step 1 tile picker
(SESSION 133 — wizard slice 10; content refined SESSION 135).

These are **Character OS's in-house marketing cast** — the four
anthropomorphic animal characters who star in the videos that
promote the product itself. They double as tile starting points
for new operators: pick the closest match, clone the structure,
edit the brief for your own brand.

The cast:

  - **Riggs** (Donkey) — founder voice; substantive content
    explaining why the product exists.
  - **Sasha** (Raccoon) — sales; short hook videos for socials,
    ads, landing-page intros.
  - **Donny** (Sloth) — user stories; documentary-style
    interviews that let customers tell their own story.
  - **Maya** (Panda) — product education + onboarding tutor;
    the dual-mode educator (lessons students watch + questions
    students ask).

James's classroom battle unicorn is **not** a template — it's the
demo of an operator using Character OS to build a fully-custom
spokesperson, separate from the cast.

Wardrobe across all four is hoodie + tee in distinctive colours
(charcoal / black / olive / sage) — Character OS is an AI startup
run by AI animals; nobody on this team owns a blazer. The visual
distinction by colour + cut keeps them readable as a team.

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
    tone_archetype: str  # one of Teammate.Tone
    visual_template: str  # one of SUPPORTED_PORTRAIT_TEMPLATES
    visual_subject: str
    voice_preset: str  # one of SUPPORTED_VOICE_PRESETS


# Order is the tile display order on Step 1. Reordering here changes
# the operator-facing tile layout.
TEMPLATES: tuple[SpokespersonTemplate, ...] = (
    SpokespersonTemplate(
        key="riggs",
        name="Riggs",
        tagline="Founders + solo brands — substantive content",
        business_brief=(
            "Founder-voice spokesperson — substantive, not "
            "promotional. Speaks like someone who's been thinking "
            "about a problem for years and now wants to explain it. "
            "Takes positions; names what's broken about the status "
            "quo; says where the industry is going. Confident, "
            "never grandstanding. Longer-form pacing — room to "
            "think out loud. The audience is anyone deciding "
            "whether to take the idea seriously."
        ),
        tone_archetype="authority",
        visual_template="mascot",
        visual_subject=(
            "an anthropomorphic donkey founder character, calm and "
            "decisive, intelligent eyes, in a fitted charcoal hoodie "
            "over a plain white tee"
        ),
        voice_preset="vincent",
    ),
    SpokespersonTemplate(
        key="sasha",
        name="Sasha",
        tagline="Coaches + course-sellers — marketing video",
        business_brief=(
            "Marketing-video spokesperson with cool-composed energy. "
            "Direct-to-camera, casual but precise — treats the "
            "audience as smart adults, never raises the volume to "
            "sell. Short sentences, clean hooks. Sees the "
            "through-line from audience pain to outcome and lands "
            "it in under a minute. Refuses copy that sounds like "
            "ad copy."
        ),
        tone_archetype="friend",
        visual_template="mascot",
        visual_subject=(
            "a sleek anthropomorphic raccoon character with a knowing "
            "smirk and sharp eyes, in a fitted black hoodie with "
            "subtle branding"
        ),
        voice_preset="clara",
    ),
    SpokespersonTemplate(
        key="donny",
        name="Donny",
        tagline="Case studies + customer stories — documentary video",
        business_brief=(
            "Documentary-style interviewer. Sits down with the "
            "customer and lets them tell the story — slow pacing, "
            "attentive listening, the kind of patient pauses that "
            "get real answers. Asks the follow-up that surfaces "
            "what wouldn't have come up otherwise. The audience is "
            "people considering becoming the next customer. The "
            "interviewee is the star; Donny just makes sure the "
            "story lands."
        ),
        tone_archetype="expert",
        visual_template="mascot",
        visual_subject=(
            "a thoughtful anthropomorphic sloth interviewer character "
            "with attentive kind eyes, in a soft oversized olive "
            "hoodie"
        ),
        voice_preset="drew",
    ),
    SpokespersonTemplate(
        key="maya",
        name="Maya",
        tagline="Teachers — lessons + tutoring",
        business_brief=(
            "Patient teacher-shaped educator. Voices the lesson when "
            "the student is watching; answers the question when the "
            "student is stuck. Scaffolds explanations in small steps; "
            "never makes a learner feel dumb for asking. Tone is warm "
            "but precise — the goal is always \"now you've got it,\" "
            "not \"aren't I smart.\" Works for any subject; the "
            "teacher's own brief narrows the topic."
        ),
        tone_archetype="tutor",
        visual_template="mascot",
        visual_subject=(
            "a gentle anthropomorphic panda teacher character with "
            "warm welcoming eyes, in a soft sage hoodie"
        ),
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
