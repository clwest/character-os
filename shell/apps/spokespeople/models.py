"""Teammate — the unit of brand identity.

Holds the business brief, voice + portrait references, and the
media-engine identifiers that link to Runway-side artefacts. Videos
and ConversationThreads FK here. Replaces the legacy `Character`
model from an earlier hackathon prototype (design doc §4.3).

Historical note: this class was originally named `Teammate`
(the pre-redesign product term). Renamed to `Teammate` in SESSION
240 per ratified §17.1.b of the Canonical Identity Contract
(`docs/design/visual/portrait_qualification/CANONICAL_IDENTITY_CONTRACT_V1.md`).
The Django app label, module path, DB table, and DB constraint
names are deliberately preserved as `spokespeople_*` /
`spokesperson_*` per the same ratification (persistence identifiers
stay stable across the rename).
"""
from __future__ import annotations

import uuid

from django.db import models

from apps.accounts.models import Workspace


class Teammate(models.Model):
    """A named on-camera identity inside a workspace."""

    class Status(models.TextChoices):
        SETUP_NEEDED = "setup_needed", "Setup needed"
        READY = "ready", "Ready"
        ARCHIVED = "archived", "Archived"

    class Tone(models.TextChoices):
        """Tone archetypes — the persona axis (orthogonal to the
        visual axis above). Five options, mirrored in the wizard
        scope-lock (`docs/design/CREATE_SPOKESPERSON_WIZARD.md`
        §"Tone archetypes"). Drives voice-preset suggestions today
        and render-flow prompt augmentation later.
        """
        TUTOR = "tutor", "Tutor"
        AUTHORITY = "authority", "Authority"
        FRIEND = "friend", "Friend"
        EXPERT = "expert", "Expert"
        PERFORMER = "performer", "Performer"

    class VisualTemplate(models.TextChoices):
        """Portrait templates — the visual axis. Mirrors
        ``media-engine/app/services/character_studio_client.py``
        ``PORTRAIT_TEMPLATES``. ``mascot`` is the stylized-creature
        track (Riggs/Sasha/Donny/Maya/Marcus); the other three are
        photorealistic-human variants. Persisted on the row so
        re-bake (W11.2) can default to the operator's original
        choice instead of a hardcoded fallback. The original W11.2
        rebake hardcoded ``"coach"`` and re-rendered Marcus as a
        photorealistic human instead of a battle unicorn —
        SESSION 171 lesson.
        """
        MASCOT = "mascot", "Mascot"
        FOUNDER = "founder", "Founder"
        COACH = "coach", "Coach"
        LOCAL_GUIDE = "local_guide", "Local guide"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="teammates",
    )
    name = models.CharField(max_length=120)
    business_brief = models.TextField(
        blank=True,
        help_text=(
            "WHAT the business does — facts the teammate grounds "
            "their claims in. Product, target market, pricing, key "
            "policies. The K6 system prompt treats this as factual "
            "context (alongside retrieved knowledge chunks). Pre-W11.y "
            "(SESSION 175) this field held both facts AND personality; "
            "they're split now — describe the BUSINESS here and put "
            "voice / character / mannerisms in ``personality``."
        ),
    )
    # W11.y (SESSION 175) — personality is HOW the teammate
    # speaks (voice, character, mannerisms) while ``business_brief``
    # above is WHAT the business does (facts). Splitting them lets
    # operators swap business briefs across personality types
    # without changing the teammate's voice on the page.
    # Backfilled from business_brief in migration 0005 so existing
    # K6 + Runway flows keep working unchanged.
    personality = models.TextField(
        blank=True,
        default="",
        help_text=(
            "HOW the teammate speaks — voice, character, "
            "mannerisms, opener style. K6's tone-guidance fence "
            "feeds from this; Runway's avatar create + realtime "
            "session ``personality`` field maps to this. Distinct "
            "from ``business_brief`` (facts) above so operators can "
            "swap business briefs across personality types without "
            "re-baking the voice on the page."
        ),
    )
    visual_subject = models.CharField(
        max_length=750,
        blank=True,
        default="",
        help_text=(
            "Free-text description of what this teammate looks "
            "like — 'armored battle unicorn', 'neon-pink raccoon in a "
            "denim jacket'. Threaded into the media-engine's "
            "/internal/portrait/ subject parameter when generating. "
            "Empty means 'use the visual template's built-in default "
            "subject' (e.g. mascot → 'a friendly brand mascot')."
        ),
    )
    visual_template = models.CharField(
        max_length=20,
        choices=VisualTemplate.choices,
        default=VisualTemplate.MASCOT,
        help_text=(
            "Portrait template used when generating this "
            "teammate's image. Mirrors the wizard's Step-1 "
            "tile choice. Re-bake (W11.2) defaults to this value "
            "so the operator doesn't have to re-pick the template "
            "every time. Originally hardcoded to ``coach`` at "
            "rebake-time, which silently flipped Marcus from a "
            "stylized battle unicorn to a photorealistic human "
            "(SESSION 171 fix)."
        ),
    )
    tone_archetype = models.CharField(
        max_length=20,
        choices=Tone.choices,
        default=Tone.EXPERT,
        help_text=(
            "Persona axis: how the teammate sounds + scripts read. "
            "Five options (tutor / authority / friend / expert / "
            "performer). Defaults to 'expert' — the safest neutral for "
            "SMBs. Inferable from business_brief via "
            "character_os.prompts.brand.suggest_tone_from_brief()."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SETUP_NEEDED,
    )

    # Media-engine integration — placeholders, populated by the
    # Django→FastAPI client when the avatar pipeline runs. Nullable
    # until the avatar is created. Compatibility mirrors per §17.10.a
    # of the Canonical Identity Contract; do not remove or repurpose
    # until the canonical identity substrate migration lands and
    # the growth-window exit conditions all hold.
    runway_avatar_id = models.CharField(max_length=120, blank=True, default="")
    runway_avatar_status = models.CharField(max_length=40, blank=True, default="")
    portrait_path = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Renderable URL or data URI for the teammate's portrait. "
            "Set by perform_create / seed_cast from the media-engine's "
            "AvatarCreateResult.thumbnail_url after a successful avatar "
            "bind. Real-mode: Runway CDN URL (~200 chars). Mock-mode: "
            "base64 data URI of the placeholder PNG (~2 KB). TextField "
            "(not CharField) because mock-mode URIs exceed 512 chars."
        ),
    )
    voice_id = models.CharField(max_length=120, blank=True, default="")

    # SESSION 232 — Identity surface (contract rule 10; three-layer
    # sequence body → identity → knowledge). These five fields plus
    # ``business_brief`` above form the six identity slots the
    # customer fills on ``/spokespeople/{id}/identity``. All accept
    # empty per the design lock; only ``business_brief`` is
    # server-required (unchanged from wizard v1-floor). The SPA's
    # ``Define {name}`` masthead button flips to plain ``Identity``
    # once >= 4 of 6 are non-empty (see
    # ``identity_fields_filled_count``).
    #
    # Deep reference material (documents, PDFs, URLs, FAQs) stays
    # on the knowledge side — these are always-on operating rules,
    # not facts. Full design lock at
    # ``docs/design/CUSTOMER_JOURNEY_V1.md`` §"The teammate
    # detail page — where identity gets defined".
    who_you_help = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Identity slot 2 — WHO the teammate is talking to "
            "(target customer / audience). Always-on operating rule; "
            "shapes every video and conversation. Not a facts field."
        ),
    )
    what_you_sell = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Identity slot 3 — the offering (products / services / "
            "packages), described at the shape level. Not a catalog "
            "— deep product detail lives on the knowledge side."
        ),
    )
    always_emphasize = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Identity slot 4 — the things the customer wants in "
            "every video and every conversation. Signature messages, "
            "positioning, brand claims. Positive direction."
        ),
    )
    never_say = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Identity slot 5 — guardrails. Off-limits topics, "
            "competitor names, legal claims that cannot be made. "
            "Negative direction; complements always_emphasize."
        ),
    )
    desired_feeling = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Identity slot 6 — the emotional outcome the customer "
            "wants people to walk away with after interacting with "
            "the teammate. Not personality; not what they said "
            "— how they *felt.*"
        ),
    )

    # SESSION 253 — Character Voice / Writing Identity fields. Six
    # new fields on top of the existing identity + personality
    # surface. All optional; all backfilled to non-null defaults.
    # See ``character_os.script_synthesis`` for how these feed the
    # K6 prompt architecture (§2 Character Voice section) and
    # ``character_os.claim_verifier`` for the K6.4 evidence /
    # allowed-vocabulary boundary.
    #
    # ``character_point_of_view`` describes WHAT the character
    # thinks (orthogonal to ``personality``, which describes HOW
    # they write). The three ``voice_*`` axes pin the writing
    # register more concretely than ``tone_archetype`` alone.
    # Signature / avoid phrases are operator-specified vocabulary
    # possibilities and prohibitions respectively.
    class VoiceEnergy(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    class VoiceHumor(models.TextChoices):
        NONE = "none", "None"
        DRY = "dry", "Dry"
        WARM = "warm", "Warm"
        PLAYFUL = "playful", "Playful"

    class VoiceDirectness(models.TextChoices):
        SOFT = "soft", "Soft"
        BALANCED = "balanced", "Balanced"
        DIRECT = "direct", "Direct"

    character_point_of_view = models.TextField(
        blank=True,
        default="",
        help_text=(
            "SESSION 253 — Character POV. What this teammate "
            "notices, believes, enjoys, dislikes, or opines about. "
            "Orthogonal to ``personality`` (HOW they write). Shapes "
            "what the character notices when interpreting a topic; "
            "informational topics don't force an opinion. Never "
            "enters the K6.4 factual corpus."
        ),
    )
    voice_energy = models.CharField(
        max_length=8,
        choices=VoiceEnergy.choices,
        default=VoiceEnergy.MEDIUM,
        help_text=(
            "SESSION 253 — voice energy axis. Backfilled from "
            "tone_archetype."
        ),
    )
    voice_humor = models.CharField(
        max_length=8,
        choices=VoiceHumor.choices,
        default=VoiceHumor.WARM,
        help_text=(
            "SESSION 253 — humor style. Backfilled from "
            "tone_archetype."
        ),
    )
    voice_directness = models.CharField(
        max_length=10,
        choices=VoiceDirectness.choices,
        default=VoiceDirectness.BALANCED,
        help_text=(
            "SESSION 253 — how directly the teammate sells / makes "
            "asks. Backfilled from tone_archetype."
        ),
    )
    voice_signature_phrases = models.TextField(
        blank=True,
        default="",
        help_text=(
            "SESSION 253 — phrases this teammate might reach for "
            "occasionally. Possibilities, not required catchphrases. "
            "Proper nouns extracted from this field enter the K6.4 "
            "allowed vocabulary (not the factual corpus)."
        ),
    )
    voice_avoid_phrases = models.TextField(
        blank=True,
        default="",
        help_text=(
            "SESSION 253 — phrases this teammate never uses. Merged "
            "with the platform anti-AI-copy default list at K6 "
            "prompt-assembly time."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Explicit db_table preserves the physical table name
        # across the Teammate → Teammate class rename
        # (§17.1.b: preserve existing DB tables initially). Without
        # this, Django's RenameModel operation would emit a physical
        # ALTER TABLE ... RENAME TO spokespeople_teammate.
        db_table = "spokespeople_spokesperson"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                # Constraint name is a persistence identifier — kept
                # as-is per §17.1.b DB-preservation constraint.
                name="spokesperson_unique_name_per_workspace",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.workspace.name})"

    # SESSION 232 — powers the SPA's "N of 6 filled" progress
    # signal on the identity page and the masthead button state
    # threshold (>= 4 fires the transition from "Define {name}"
    # to plain "Identity"). Whitespace-only content counts as
    # empty — the customer needs meaningful text to count, not
    # a stray space.
    IDENTITY_FIELDS = (
        "business_brief",
        "who_you_help",
        "what_you_sell",
        "always_emphasize",
        "never_say",
        "desired_feeling",
    )

    def identity_fields_filled_count(self) -> int:
        """Count of identity fields with non-whitespace content.
        Range 0–6. Drives the SPA's masthead button state (< 4 =
        "Define {name}", >= 4 = plain "Identity") and the "N of 6
        filled" progress signal on ``/spokespeople/{id}/identity``.
        """
        return sum(
            1 for f in self.IDENTITY_FIELDS
            if (getattr(self, f, "") or "").strip()
        )
