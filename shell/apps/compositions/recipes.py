"""Recipe registry for the V15 SPA gallery.

SESSION 144 / V15.0. Each recipe is metadata + a builder
callable that wraps one of the 17 starters from
``apps.compositions.starters``. The SPA reads recipe metadata
via ``GET /api/recipes/`` and POSTs to ``/api/compositions/``
with ``{kind, workspace, params}`` to instantiate one.

The registry is the single source of truth for what recipes
exist + what fields they need + how to map a JSON params dict
to a starter kwargs call. Adding a new recipe is: write the
starter, then add one entry here. No view-layer changes
needed.

Field types used by the SPA form renderer:

  text                — short string input
  textarea            — long string input (scripts, prompts)
  checkbox            — bool
  select              — fixed-choice dropdown
  number              — integer or float input
  spokesperson_picker — pick a workspace Teammate by id
  asset_picker        — pick an existing workspace Asset by id,
                        filtered by ``asset_type``
  script_picker       — pick an approved (status in {READY, RENDERED})
                        workspace Script by id; B-2 / B2.4 (SESSION 206),
                        widened to include RENDERED in SESSION 251
                        so previously-fired scripts stay reusable
  dialogue_lines      — special composite for ``dialogue_scene``;
                        the SPA renders an add/remove list of
                        ``{spokesperson_id, text}`` rows

The instantiate path resolves spokesperson_picker + asset_picker
fields to ORM rows (workspace-scoped via the queryset filter),
then calls the starter with resolved kwargs.

Cross-workspace fences live in the starters themselves — this
registry doesn't re-implement them. The view layer rejects
foreign-workspace ids at lookup time (DoesNotExist → 400).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from . import starters
from .models import AssetRole, AssetType, Composition


@dataclass(frozen=True)
class RecipeField:
    """One form field on a recipe."""

    name: str
    type: str
    label: str
    required: bool = True
    default: Any = None
    help_text: str = ""
    # Type-specific constraints. Only the ones relevant to the
    # field's ``type`` are set; others stay None.
    min_chars: int | None = None
    max_chars: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    choices: tuple[dict, ...] | None = None  # for select
    asset_type: str | None = None  # for asset_picker
    # Asset Library v1 (SESSION 190, A7) — narrows the
    # asset_picker dropdown to a single AssetRole. Q-a-5
    # resolved this as a first-class RecipeField field (not a
    # per-recipe override). Apply conservatively — only set
    # when the field semantically demands one role
    # (V18 backdrop_clip_id wants BACKDROP, broll_clip_id
    # wants B_ROLL, music_asset_id wants AUDIO_TRACK). Leave
    # fuzzy picker fields (base_clip_id, pip_clip_id, etc.)
    # unfiltered so the operator can still pick whichever
    # CLIP makes sense.
    role_filter: str | None = None  # for asset_picker; AssetRole value

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "label": self.label,
            "required": self.required,
        }
        if self.default is not None:
            out["default"] = self.default
        if self.help_text:
            out["help_text"] = self.help_text
        if self.min_chars is not None:
            out["min_chars"] = self.min_chars
        if self.max_chars is not None:
            out["max_chars"] = self.max_chars
        if self.min_value is not None:
            out["min_value"] = self.min_value
        if self.max_value is not None:
            out["max_value"] = self.max_value
        if self.choices is not None:
            out["choices"] = list(self.choices)
        if self.asset_type is not None:
            out["asset_type"] = self.asset_type
        if self.role_filter is not None:
            out["role_filter"] = self.role_filter
        return out


@dataclass(frozen=True)
class Recipe:
    """A single recipe — metadata + builder."""

    kind: str
    display_name: str
    family: str
    description: str
    fields: tuple[RecipeField, ...]
    starter: Callable[..., Composition]
    # form-field-name → starter-kwarg-name. Default: identity
    # (form names match starter param names). Override per recipe
    # when they diverge (e.g. dialogue_scene's primary_spokesperson_id
    # → primary_spokesperson kwarg).
    param_map: dict[str, str] = field(default_factory=dict)
    # Optional custom resolver for the rare case where the default
    # field-by-field resolution doesn't fit (dialogue_scene's
    # ``lines`` field is the only one in v1).
    custom_resolver: Callable[..., dict] | None = None

    def to_json(self) -> dict[str, Any]:
        # SESSION 251 — surface the canonical speaking-rate constant
        # so the SPA can compute the knowledge-off duration hint
        # ("your script is ~Ns") without hardcoding the value on the
        # client. Same source of truth as the starter's word-budget
        # math. Kept as a top-level recipe property because it's
        # workspace-wide, not per-field.
        from apps.compositions.starters import _AVATAR_SPEECH_CHARS_PER_SECOND

        return {
            "kind": self.kind,
            "display_name": self.display_name,
            "family": self.family,
            "description": self.description,
            "fields": [f.to_json() for f in self.fields],
            "speaking_rate_chars_per_second": _AVATAR_SPEECH_CHARS_PER_SECOND,
        }

    def field_by_name(self, name: str) -> RecipeField | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


# ---- Family vocabulary --------------------------------------------
#
# Used by the SPA gallery to group recipe cards. v1 is a flat
# string; v2 could carry a display ordering + color treatment.

FAMILY_TALKING_HEAD = "talking_head"
FAMILY_CINEMATIC = "cinematic"
FAMILY_LAYOUT = "layout"
FAMILY_POLISH = "polish"
FAMILY_VOICE = "voice"
FAMILY_STYLE = "style"
FAMILY_CREATIVE = "creative"
FAMILY_DIALOGUE = "dialogue"


# ---- Reusable field templates -------------------------------------
#
# Many recipes share the same optional name field. Define once.

_NAME_FIELD = RecipeField(
    name="name",
    type="text",
    label="Composition name (optional)",
    required=False,
    max_chars=200,
    help_text="Display name in the dashboard. Auto-generated if blank.",
)

_MOCK_MODE_FIELD = RecipeField(
    name="mock_mode",
    type="checkbox",
    label="Mock mode (skip real provider calls)",
    required=False,
    default=False,
    help_text="Run with deterministic stubs — useful for testing without burning credits.",
)

# K6.4 v1.1 — per-render verifier mode override. Reusable across
# any recipe that runs K6 synthesis (use_knowledge=True). v1.1
# adds it only to ``talking_head``; future K6.4 v1.x can roll it
# out across more recipes as the operator-facing semantics settle.
_OPENER_FIELD = RecipeField(
    name="opener",
    type="text",
    label="Opening line (optional)",
    required=False,
    max_chars=240,
    help_text=(
        "Pin the script's first sentence verbatim. The rest of the "
        "script follows from it. Leave blank to let the writer pick "
        "the opener — recommended unless you want a specific hook."
    ),
)


_VERIFIER_MODE_FIELD = RecipeField(
    name="verifier_mode",
    type="select",
    label="Fact-check mode",
    required=False,
    default="warn",
    choices=(
        {"value": "warn", "label": "Warn (flag invented details; keep rendering)"},
        {"value": "strict", "label": "Strict (reject invented details before rendering)"},
        {"value": "off", "label": "Off (skip fact-checking)"},
    ),
    help_text=(
        "Only applies when 'Use workspace knowledge' is on. Strict "
        "blocks the render if the writer invents details not supported "
        "by your workspace knowledge (saves render cost). Warn flags "
        "them but ships the video. Off skips the check entirely."
    ),
)


# ---- The 17 recipes -----------------------------------------------

_RATIO_CHOICES = (
    {"value": "1280:720", "label": "Landscape 16:9"},
    {"value": "720:1280", "label": "Portrait 9:16 (Reels)"},
    {"value": "960:960", "label": "Square 1:1"},
)

_STYLE_PRESET_CHOICES = (
    {"value": "noir", "label": "Noir"},
    {"value": "anime", "label": "Anime"},
    {"value": "chrome", "label": "Chrome"},
    {"value": "watercolor", "label": "Watercolor"},
    {"value": "cyberpunk", "label": "Cyberpunk"},
)

_DUB_LANGUAGE_CHOICES = tuple(
    {"value": code, "label": label}
    for code, label in [
        ("en", "English"), ("es", "Spanish"), ("fr", "French"),
        ("de", "German"), ("it", "Italian"), ("pt", "Portuguese"),
        ("nl", "Dutch"), ("ru", "Russian"), ("pl", "Polish"),
        ("uk", "Ukrainian"), ("cs", "Czech"), ("sk", "Slovak"),
        ("hr", "Croatian"), ("bg", "Bulgarian"), ("ro", "Romanian"),
        ("el", "Greek"), ("sv", "Swedish"), ("da", "Danish"),
        ("fi", "Finnish"), ("tr", "Turkish"), ("ar", "Arabic"),
        ("hi", "Hindi"), ("ta", "Tamil"), ("zh", "Chinese"),
        ("ja", "Japanese"), ("ko", "Korean"), ("id", "Indonesian"),
        ("ms", "Malay"), ("fil", "Filipino"),
    ]
)

_RECUT_CRITERION_CHOICES = (
    {"value": "hook", "label": "Strongest hook (gpt-5-mini picks)"},
    {"value": "first", "label": "First sentence"},
    {"value": "last", "label": "Last sentence"},
    {"value": "longest", "label": "Longest sentence"},
)


def _dialogue_resolver(
    *, workspace, params: dict, created_by
) -> dict[str, Any]:
    """Custom resolver for dialogue_scene.

    The ``lines`` form field is a list of dicts; each entry's
    ``spokesperson_id`` has to be resolved to a Teammate row.
    Everything else maps the standard way.
    """
    from apps.spokespeople.models import Teammate

    primary_id = params.get("primary_spokesperson_id")
    if not primary_id:
        raise ValueError("dialogue_scene requires primary_spokesperson_id")
    primary = Teammate.objects.get(pk=primary_id, workspace=workspace)

    raw_lines = params.get("lines") or []
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValueError("dialogue_scene requires at least one line")

    resolved_lines: list[dict] = []
    for idx, entry in enumerate(raw_lines):
        if not isinstance(entry, dict):
            raise ValueError(f"dialogue_scene line {idx} must be a dict")
        sp_id = entry.get("spokesperson_id")
        text = entry.get("text", "")
        if not sp_id:
            raise ValueError(f"dialogue_scene line {idx} missing spokesperson_id")
        sp = Teammate.objects.get(pk=sp_id, workspace=workspace)
        resolved_lines.append({"spokesperson": sp, "text": text})

    return {
        "workspace": workspace,
        "primary_spokesperson": primary,
        "lines": resolved_lines,
        # SESSION 199 — outro_text parity. Pass-through to the
        # starter; the starter handles the multi-line (after
        # concat) vs single-line (after speech) wiring.
        "outro_text": params.get("outro_text") or None,
        "mock_mode": bool(params.get("mock_mode", False)),
        "name": params.get("name", "") or "",
        "created_by": created_by,
    }


RECIPES: dict[str, Recipe] = {
    # ---- B-2 / E-arc auto-scripting --------------------------
    #
    # ``auto_script`` is the operator-facing surface for
    # rendering a pre-drafted Script — the K6 synthesis ran at
    # draft time, the K6.4 verifier already flagged any
    # hallucinations, the operator already approved the draft.
    # Picking it in the gallery just fires the render.
    #
    # Q-e-11 (SESSION 206) — surfaced in the gallery with a
    # special Script picker form (instead of the free-form
    # textarea). SESSION 251 widened the picker to include
    # RENDERED scripts in addition to READY, so scripts stay
    # reusable after their first render. DRAFT is still
    # excluded — operators can't accidentally fire an
    # unapproved script.
    "auto_script": Recipe(
        kind="auto_script",
        display_name="Render approved script",
        family=FAMILY_TALKING_HEAD,
        description=(
            "Pick an existing approved Script from /workspace/scripts "
            "and render it as a talking-head video. This recipe does "
            "not generate a new script — it only renders one you've "
            "already drafted, reviewed, and approved. To draft a fresh "
            "script from a topic + workspace knowledge, use \"Talking "
            "head\" with \"Use workspace knowledge\" ticked."
        ),
        fields=(
            RecipeField(
                name="script_id", type="script_picker",
                label="Approved script",
                help_text=(
                    "Approved scripts — ready-to-use or previously "
                    "rendered. Rendered scripts are tagged so you can "
                    "tell them apart; both are reusable. Draft new "
                    "scripts at /workspace/scripts."
                ),
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.auto_script,
    ),
    # ---- Talking-head family ---------------------------------
    "talking_head": Recipe(
        kind="talking_head",
        display_name="Talking head",
        family=FAMILY_TALKING_HEAD,
        description="One spokesperson speaking your script straight to camera.",
        fields=(
            RecipeField(
                name="spokesperson_id", type="spokesperson_picker",
                label="Spokesperson",
            ),
            RecipeField(
                name="script", type="textarea", label="Script or topic",
                min_chars=8, max_chars=4000,
                help_text=(
                    "What the avatar will say. Provide a finished "
                    "script and it will be spoken verbatim; or provide "
                    "a short topic / brief (a few words to a couple of "
                    "sentences) and tick \"Use workspace knowledge\" "
                    "below to have the writer draft a grounded script "
                    "from your workspace docs before rendering. Every "
                    "render drafts fresh — no cached output is reused."
                ),
            ),
            RecipeField(
                name="use_knowledge", type="checkbox",
                label="Use workspace knowledge", required=False, default=False,
                help_text=(
                    "When ticked, the field above is treated as a "
                    "topic / brief rather than a finished script. The "
                    "writer pulls the most relevant workspace knowledge "
                    "and drafts a grounded speech-ready script, then "
                    "renders it. Leave unticked to render the field "
                    "above verbatim."
                ),
            ),
            # SESSION 253 — target duration for AI-synthesized talking
            # heads. Only applies when \"Use workspace knowledge\" is
            # ticked. Manual-script mode ignores this field to prevent
            # silent rewriting of an exact operator script.
            #
            # Values coerced to int by the starter (DRF ``choices``
            # serialize to strings). Format matches
            # long_form_ad.target_duration_seconds. Empty (\"\") means
            # \"no duration constraint — use the default short-standalone
            # shape.\" This preserves the pre-SESSION 253 behavior for
            # operators who don't touch the field.
            RecipeField(
                name="target_duration_seconds", type="select",
                label="Target duration (AI-synthesized topic only)",
                required=False, default="",
                choices=(
                    {"value": "", "label": "Default (~30-60s standalone)"},
                    {"value": "30", "label": "30 seconds"},
                    {"value": "60", "label": "60 seconds"},
                    {"value": "90", "label": "90 seconds"},
                    {"value": "120", "label": "2 minutes"},
                    {"value": "180", "label": "3 minutes"},
                ),
                help_text=(
                    "Applies only when \"Use workspace knowledge\" is "
                    "ticked. The writer drafts to this length (±20% "
                    "tolerance, one corrective pass if outside). If the "
                    "corrected draft still doesn't fit, the composition "
                    "fails BEFORE any Runway credit is spent. When you "
                    "supply your own script (checkbox off), this field "
                    "is ignored — your script is spoken exactly as "
                    "written."
                ),
            ),
            _VERIFIER_MODE_FIELD,
            _OPENER_FIELD,
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.talking_head,
    ),
    "talking_head_with_backdrop": Recipe(
        kind="talking_head_with_backdrop",
        display_name="Talking head with cinematic backdrop",
        family=FAMILY_TALKING_HEAD,
        description="Avatar talking over a generated cinematic background.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Spokesperson"),
            RecipeField(name="script", type="textarea", label="Script", min_chars=8, max_chars=4000),
            # SESSION 184 / V18 — backdrop_prompt is now optional;
            # the operator can pick an existing workspace CLIP as
            # the backdrop instead of paying $1.25-$1.75 to bake a
            # fresh one. XOR validation lives in the starter
            # (exactly one of backdrop_prompt / backdrop_clip_id
            # required). When both are set, backdrop_clip_id wins
            # (the operator's intent is to reuse the saved clip).
            RecipeField(
                name="backdrop_prompt", type="textarea",
                label="Backdrop prompt", required=False,
                min_chars=4, max_chars=600,
                help_text=(
                    "Visual scene generated as the background "
                    "(e.g. 'sunset on a city skyline'). Leave blank "
                    "if you pick an existing backdrop clip below."
                ),
            ),
            # SESSION 184 / V18 — pre-recorded backdrop library.
            # When set, skips both the generate-and-concat path and
            # the V17.5 generate-and-extend path; uses the picked
            # CLIP directly as the composite background. Saves the
            # $1.25-$1.75 Runway backdrop cost across script
            # iterations and unlocks operator-uploaded footage
            # reuse when the asset-upload UI lands.
            RecipeField(
                name="backdrop_clip_id", type="asset_picker",
                label="Pre-recorded backdrop clip (optional)",
                required=False, asset_type=AssetType.CLIP,
                role_filter=AssetRole.BACKDROP.value,
                help_text=(
                    "Pick a saved workspace clip to reuse as the "
                    "backdrop. When set, the backdrop prompt is "
                    "ignored and no Runway calls fire for the "
                    "backdrop — saves ~$1.25-$1.75 per render."
                ),
            ),
            RecipeField(
                name="backdrop_ratio", type="select", label="Backdrop aspect ratio",
                required=False, default="1280:720", choices=_RATIO_CHOICES,
                help_text="Ignored when a pre-recorded backdrop clip is picked.",
            ),
            RecipeField(
                name="backdrop_duration", type="number", label="Backdrop duration (seconds)",
                required=False, default=10, min_value=5, max_value=10,
            ),
            RecipeField(name="use_knowledge", type="checkbox", label="Use workspace knowledge", required=False, default=False),
            RecipeField(
                name="remove_avatar_bg", type="checkbox",
                label="Remove avatar background (slower)",
                required=False, default=False,
                help_text=(
                    "Mat the avatar out of its baked white background "
                    "so it sits cleanly over the cinematic backdrop. "
                    "Adds ~2-3 minutes per render."
                ),
            ),
            # SESSION 183 / V17.5 — opt-in extend chain. When set,
            # the backdrop is built as 1 generate (10s) + N extend
            # (5s each, last-frame conditioned) instead of N
            # separate 10s backdrops + concat. Removes the visible
            # motion seams every 10s of the concat path.
            RecipeField(
                name="use_extend_for_backdrop", type="checkbox",
                label="Use seam-free extend chain for backdrop",
                required=False, default=False,
                help_text=(
                    "Use Runway's extend feature so the backdrop "
                    "flows as one continuous motion instead of N "
                    "separately-generated 10s clips stitched "
                    "together. Recommended for longer scripts (>10s "
                    "of speech). Ignores the backdrop duration knob "
                    "above — extends are fixed at 5s per segment."
                ),
            ),
            _VERIFIER_MODE_FIELD,
            _OPENER_FIELD,
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.talking_head_with_backdrop,
        # V18 — resolver renames backdrop_clip_id → backdrop_clip
        # (passes the resolved Asset row to the starter, mirrors
        # the source_clip_id → source_clip pattern used by
        # style_remix_pass / recut_teaser).
        param_map={"backdrop_clip_id": "backdrop_clip"},
    ),
    "talking_head_polished": Recipe(
        kind="talking_head_polished",
        display_name="Polished talking head (captions + intro/outro)",
        family=FAMILY_POLISH,
        description="Talking-head clip with burnt-in subtitles and a brand title card.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Spokesperson"),
            RecipeField(name="script", type="textarea", label="Script", min_chars=8, max_chars=4000),
            RecipeField(name="use_knowledge", type="checkbox", label="Use workspace knowledge", required=False, default=False),
            # SESSION 180 — plain-string shorthands so the polish
            # steps can actually fire from the SPA form. Each
            # builds a default-styled title card / auto-timed
            # caption list inside the starter; programmatic
            # callers can still pass full intro / outro / captions
            # dicts for tight control.
            RecipeField(
                name="intro_text", type="text",
                label="Intro card text (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card prepended to the clip. 3 seconds, "
                    "white text on black. Leave blank to skip."
                ),
            ),
            RecipeField(
                name="outro_text", type="text",
                label="Outro card text (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended to the clip. 3 seconds, "
                    "white text on black. Leave blank to skip."
                ),
            ),
            RecipeField(
                name="burn_captions", type="checkbox",
                label="Burn captions from script",
                required=False, default=False,
                help_text=(
                    "Auto-time subtitles from the script "
                    "(~11 chars/sec). Timing is approximate — "
                    "fine for social cuts, drift may be visible "
                    "on long scripts."
                ),
            ),
            _VERIFIER_MODE_FIELD,
            _OPENER_FIELD,
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.talking_head_polished,
    ),
    "long_form_ad": Recipe(
        kind="long_form_ad",
        display_name="Long-form ad (auto-chunked)",
        family=FAMILY_TALKING_HEAD,
        description="Long scripts split into chunks, rendered separately, then stitched. The platform's launch differentiator — no AI provider ships single-call video longer than ~20s.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Spokesperson"),
            RecipeField(
                name="script", type="textarea", label="Script or topic",
                min_chars=200, max_chars=20000,
                help_text=(
                    "When \"Use workspace knowledge\" is off, this is "
                    "your finished script — split into chunks at "
                    "sentence boundaries and rendered verbatim. When "
                    "\"Use workspace knowledge\" is on, this is a "
                    "topic / brief; the writer drafts one complete "
                    "long-form script from your workspace docs targeted "
                    "at the chosen duration, then chunks the finished "
                    "script for rendering."
                ),
            ),
            # SESSION 251 — duration-driven synthesis. Values are
            # strings because DRF ``choices`` serialize to strings;
            # the starter coerces to int. Format-consistent with
            # ``cinematic_visual_extended.target_duration``.
            RecipeField(
                name="target_duration_seconds", type="select",
                label="Target duration",
                default="90",
                choices=(
                    {"value": "60", "label": "60 seconds"},
                    {"value": "90", "label": "90 seconds"},
                    {"value": "120", "label": "2 minutes"},
                    {"value": "180", "label": "3 minutes"},
                    {"value": "300", "label": "5 minutes"},
                ),
                help_text=(
                    "Approximate target length for the finished ad. "
                    "When \"Use workspace knowledge\" is on, the writer "
                    "drafts to this length (±20% tolerance; one "
                    "corrective pass if outside). When off, this is "
                    "informational — your script's duration comes from "
                    "its length. Actual duration also varies with the "
                    "voice's speaking pace."
                ),
            ),
            RecipeField(
                name="use_llm_split", type="checkbox",
                label="Use AI for chunk boundaries", required=False, default=False,
                help_text=(
                    "Finds semantically clean split points (small "
                    "extra cost). Otherwise splits naively at "
                    "sentence boundaries."
                ),
            ),
            RecipeField(
                name="use_knowledge", type="checkbox",
                label="Use workspace knowledge", required=False, default=False,
                help_text=(
                    "When ticked, the field above is treated as a "
                    "topic / brief. The writer drafts ONE continuous "
                    "long-form script from your workspace knowledge "
                    "(single opener, flowing body, single closing "
                    "invitation) targeted at the duration above, then "
                    "splits it into render chunks. Each chunk is "
                    "spoken verbatim so the narrative flows as one "
                    "piece. Leave unticked to provide and render "
                    "your own finished script."
                ),
            ),
            # SESSION 198 — outro_text parity with the cinematic
            # recipes. Brand outro for the long-form deliverable;
            # appended after the concat step (or after the lone
            # speech step for degenerate single-chunk renders).
            RecipeField(
                name="outro_text", type="text",
                label="Brand outro card (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended after the ad. 3 seconds, "
                    "white text on black. Leave blank to skip."
                ),
            ),
            # SESSION 251-late — expose the ffmpeg concat mode.
            # Default OFF uses the demuxer (``-c copy``): fastest,
            # but the boundary between chunks is a hard cut and can
            # show a visible jump when the avatar's pose / lighting
            # shifts between renders. ON re-encodes through
            # ``filter_complex``, which normalizes timebase / pixel
            # format / audio sample rate across chunks and usually
            # smooths the seam. Trade-off: slower (still local
            # ffmpeg, no Runway spend).
            RecipeField(
                name="reencode_concat", type="checkbox",
                label="Smooth chunk transitions (re-encode)",
                required=False, default=False,
                help_text=(
                    "Softens the visible jump between avatar chunks "
                    "at the cost of a slower concat step. Recommended "
                    "when the raw stitch feels choppy. Local ffmpeg — "
                    "no extra provider cost."
                ),
            ),
            # SESSION 251-late — crossfade between adjacent avatar
            # chunks. Reencode alone helps codec-level mismatch but
            # a hard cut is still perceptible even when the encode is
            # normalized. Crossfade at the sentence-boundary pause
            # (~200-400ms) blends the visual jump. Options avoid
            # exposing millisecond-level precision to the operator.
            RecipeField(
                name="crossfade_ms", type="select",
                label="Crossfade between chunks",
                default="0",
                choices=(
                    {"value": "0", "label": "None (hard cut)"},
                    {"value": "200", "label": "Subtle (0.2s)"},
                    {"value": "400", "label": "Smooth (0.4s)"},
                    {"value": "600", "label": "Cinematic (0.6s)"},
                ),
                help_text=(
                    "Overlaps adjacent avatar chunks with a short "
                    "crossfade so the transition between renders "
                    "feels continuous rather than pieced together. "
                    "Chunks are split at sentence boundaries where "
                    "the avatar has a natural pause, so 0.2-0.4s "
                    "usually blends cleanly. Local ffmpeg — no "
                    "extra provider cost."
                ),
            ),
            _VERIFIER_MODE_FIELD,
            _OPENER_FIELD,
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.long_form_ad,
    ),
    # ---- Cinematic family ------------------------------------
    "cinematic_visual": Recipe(
        kind="cinematic_visual",
        display_name="Cinematic visual (no avatar)",
        family=FAMILY_CINEMATIC,
        description="Silent cinematic clip generated from a text prompt. Use for backdrops, b-roll, or visual ads.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(
                name="prompt", type="textarea", label="Visual prompt",
                min_chars=4, max_chars=1000,
            ),
            # W11.6.5 (SESSION 174) — optional workspace image
            # used as Runway's reference image. When supplied,
            # routes through gen4_turbo (image-to-video) instead
            # of gen4.5 (text-to-video). Pick from the workspace
            # library populated via /images. Resolver extracts
            # the data URI from the Asset's file_path; the
            # starter's existing ``prompt_image: str`` param
            # accepts it directly.
            RecipeField(
                name="prompt_image_asset_id",
                type="asset_picker", label="Reference image (optional)",
                required=False,
                asset_type=AssetType.IMAGE,
                help_text=(
                    "Pick a workspace image to use as the "
                    "reference frame. Generates via Runway "
                    "image-to-video when set."
                ),
            ),
            RecipeField(
                name="ratio", type="select", label="Aspect ratio",
                required=False, default="1280:720", choices=_RATIO_CHOICES,
            ),
            RecipeField(
                name="duration", type="number", label="Duration (seconds)",
                required=False, default=5, min_value=5, max_value=10,
            ),
            # SESSION 199 — outro_text parity. Mirrors the
            # storyboard recipes (SESSION 197/198 pattern).
            RecipeField(
                name="outro_text", type="text",
                label="Brand outro card (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended after the clip. "
                    "3 seconds, white text on black. Leave "
                    "blank to skip."
                ),
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        # W11.6.5 — map the asset-picker field name to the
        # starter's existing ``prompt_image`` param.
        param_map={"prompt_image_asset_id": "prompt_image"},
        starter=starters.cinematic_visual,
    ),
    # V17.2 (SESSION 182) — extend chain off V4 generate_visual_clip.
    # Produces cinematic clips longer than Runway's 10s per-render
    # ceiling by chaining V17.1's extend_visual_clip primitive off
    # the base generate. Q-v17-1 pivot baked in — extends use
    # gen4_turbo image-to-video conditioned on the prior step's
    # last frame; base uses gen4.5 text-to-video for the 10s
    # opening shot. Operators wanting an image-conditioned base
    # should use V17.3's keyframe_shot recipe (when it ships).
    "cinematic_visual_extended": Recipe(
        kind="cinematic_visual_extended",
        display_name="Cinematic visual (extended)",
        family=FAMILY_CINEMATIC,
        description=(
            "Cinematic clip longer than Runway's 10s per-render ceiling. "
            "Base 10s shot + N 5s extensions; visual continuity preserved "
            "by conditioning each extension on the prior step's last frame."
        ),
        fields=(
            RecipeField(
                name="spokesperson_id", type="spokesperson_picker",
                label="Brand owner (spokesperson)",
            ),
            RecipeField(
                name="prompt", type="textarea", label="Visual prompt",
                min_chars=4, max_chars=1000,
                help_text=(
                    "Shared across the base 10s shot and every 5s "
                    "extension. v1 uses one prompt for the whole chain."
                ),
            ),
            RecipeField(
                # SPA's Zod schema enforces choice values as
                # strings (see web/src/lib/api/recipes.ts
                # `recipeFieldChoice`). Numeric defaults submit
                # back as strings; the starter coerces.
                name="target_duration", type="select",
                label="Target duration",
                default="15",
                choices=(
                    {"value": "15", "label": "15 seconds (1 extension)"},
                    {"value": "20", "label": "20 seconds (2 extensions)"},
                    {"value": "25", "label": "25 seconds (3 extensions)"},
                    {"value": "30", "label": "30 seconds (4 extensions)"},
                    {"value": "40", "label": "40 seconds (6 extensions)"},
                    {"value": "50", "label": "50 seconds (8 extensions)"},
                ),
                help_text=(
                    "Longer targets fire more Runway extend calls "
                    "(each ~$0.25). The cost forecast updates with "
                    "the selection."
                ),
            ),
            RecipeField(
                name="ratio", type="select", label="Aspect ratio",
                required=False, default="1280:720", choices=_RATIO_CHOICES,
            ),
            RecipeField(
                name="seed", type="number", label="Seed (optional)",
                required=False,
                help_text=(
                    "Optional integer seed passed to every extension "
                    "for visual coherence across the chain."
                ),
            ),
            # SESSION 199 — outro_text parity.
            RecipeField(
                name="outro_text", type="text",
                label="Brand outro card (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended after the chain. "
                    "3 seconds, white text on black. Leave "
                    "blank to skip."
                ),
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.cinematic_visual_extended,
    ),
    "storyboard_voiced": Recipe(
        kind="storyboard_voiced",
        display_name="Storyboard with avatar narration",
        family=FAMILY_CINEMATIC,
        description="Three-shot cinematic storyboard with the spokesperson narrating over it. Unblocked by V14's audio_extract primitive.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Narrator"),
            RecipeField(name="hook_prompt", type="textarea", label="Hook prompt", min_chars=4, max_chars=600),
            RecipeField(name="action_prompt", type="textarea", label="Action prompt", min_chars=4, max_chars=600),
            RecipeField(name="payoff_prompt", type="textarea", label="Payoff prompt", min_chars=4, max_chars=600),
            RecipeField(
                name="narration_script", type="textarea", label="Narration script",
                min_chars=8, max_chars=4000,
                help_text="What the avatar says over the storyboard. ~15s of speech fits the default 3-shot 15s storyboard.",
            ),
            # SESSION 197 — operator-noticed during SESSION 195
            # dogfood that the storyboard ended cold without any
            # brand mark. Mirrors talking_head_polished's
            # outro_text shape; starter conditionally appends an
            # add_intro_outro step at the end of the pipeline.
            RecipeField(
                name="outro_text", type="text",
                label="Brand outro card (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended after the storyboard. "
                    "3 seconds, white text on black. Leave blank "
                    "to skip."
                ),
            ),
            RecipeField(
                name="image_seed", type="number", label="Image seed (optional)",
                required=False, help_text="Same seed across shots = same visual style.",
            ),
            RecipeField(
                name="clip_duration", type="number", label="Per-shot duration (seconds)",
                required=False, default=5, min_value=5, max_value=5,
            ),
            # SESSION 200 — closes the V-arc UX gap. Per-shot extend
            # doubles each shot from 5s → 10s (last-frame conditioned)
            # to soften intra-shot motion; crossfade softens the cuts
            # between shots at concat time.
            RecipeField(
                name="use_extend_for_shots", type="checkbox",
                label="Smooth per-shot motion (extend chain)",
                required=False, default=False,
                help_text=(
                    "Doubles each shot from 5s to 10s by chaining a "
                    "last-frame-conditioned extend. Costs ~3× more "
                    "(3 extra Runway renders) but removes the abrupt "
                    "motion within each shot."
                ),
            ),
            RecipeField(
                name="crossfade_ms", type="number",
                label="Crossfade between shots (ms)",
                required=False, default=0, min_value=0, max_value=5000,
                help_text=(
                    "ffmpeg xfade duration between consecutive shots. "
                    "0 = hard cuts (default). 250-500ms is a tasteful "
                    "soft blend."
                ),
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.storyboard_voiced,
    ),
    "storyboard_ad": Recipe(
        kind="storyboard_ad",
        display_name="Storyboard ad (Hook / Action / Payoff)",
        family=FAMILY_CINEMATIC,
        description="Three-shot cinematic ad. Same seed across shots keeps visuals coherent.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="hook_prompt", type="textarea", label="Hook prompt", min_chars=4, max_chars=600),
            RecipeField(name="action_prompt", type="textarea", label="Action prompt", min_chars=4, max_chars=600),
            RecipeField(name="payoff_prompt", type="textarea", label="Payoff prompt", min_chars=4, max_chars=600),
            # SESSION 198 — outro_text parity with storyboard_voiced.
            # Same shape (text, optional, 80 char max) so the operator
            # gets the same UX across the cinematic family.
            RecipeField(
                name="outro_text", type="text",
                label="Brand outro card (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended after the ad. 3 seconds, "
                    "white text on black. Leave blank to skip."
                ),
            ),
            RecipeField(
                name="image_seed", type="number", label="Image seed (optional)",
                required=False, help_text="Same seed across shots = same visual style.",
            ),
            RecipeField(
                name="clip_duration", type="number", label="Per-shot duration (seconds)",
                required=False, default=5, min_value=5, max_value=5,
            ),
            # SESSION 200 — mirrors storyboard_voiced. Per-shot extend
            # for intra-shot smoothness + crossfade for inter-shot
            # softness.
            RecipeField(
                name="use_extend_for_shots", type="checkbox",
                label="Smooth per-shot motion (extend chain)",
                required=False, default=False,
                help_text=(
                    "Doubles each shot from 5s to 10s by chaining a "
                    "last-frame-conditioned extend. Costs ~3× more "
                    "(3 extra Runway renders) but removes the abrupt "
                    "motion within each shot."
                ),
            ),
            RecipeField(
                name="crossfade_ms", type="number",
                label="Crossfade between shots (ms)",
                required=False, default=0, min_value=0, max_value=5000,
                help_text=(
                    "ffmpeg xfade duration between consecutive shots. "
                    "0 = hard cuts (default). 250-500ms is a tasteful "
                    "soft blend."
                ),
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.storyboard_ad,
    ),
    # ---- Layout family ---------------------------------------
    "pip_layout": Recipe(
        kind="pip_layout",
        display_name="Picture-in-picture",
        family=FAMILY_LAYOUT,
        description="Overlay a second clip in the bottom-right of a base clip.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="base_clip_id", type="asset_picker", label="Base clip", asset_type=AssetType.CLIP),
            RecipeField(name="pip_clip_id", type="asset_picker", label="PiP overlay clip", asset_type=AssetType.CLIP),
            RecipeField(name="pip_width", type="number", label="PiP width (px)", required=False, default=360, min_value=80, max_value=1920),
            RecipeField(name="margin_x", type="number", label="Margin X (px)", required=False, default=40, min_value=0, max_value=500),
            RecipeField(name="margin_y", type="number", label="Margin Y (px)", required=False, default=40, min_value=0, max_value=500),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.pip_layout,
        param_map={"base_clip_id": "base_clip", "pip_clip_id": "pip_clip"},
    ),
    "backdrop_layout": Recipe(
        kind="backdrop_layout",
        display_name="Backdrop composite",
        family=FAMILY_LAYOUT,
        description="Foreground clip over a background clip (audio = foreground).",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(
                name="background_clip_id", type="asset_picker",
                label="Background clip", asset_type=AssetType.CLIP,
                role_filter=AssetRole.BACKDROP.value,
            ),
            RecipeField(name="foreground_clip_id", type="asset_picker", label="Foreground clip", asset_type=AssetType.CLIP),
            RecipeField(name="fg_width", type="number", label="Foreground width (px)", required=False, default=320, min_value=80, max_value=1920),
            RecipeField(name="margin_x", type="number", label="Margin X (px)", required=False, default=40, min_value=0, max_value=500),
            RecipeField(name="margin_y", type="number", label="Margin Y (px)", required=False, default=40, min_value=0, max_value=500),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.backdrop_layout,
        param_map={
            "background_clip_id": "background_clip",
            "foreground_clip_id": "foreground_clip",
        },
    ),
    "cohost_layout": Recipe(
        kind="cohost_layout",
        display_name="Cohost layout",
        family=FAMILY_LAYOUT,
        description="Main avatar with a smaller cohost tile in the top-left.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="main_clip_id", type="asset_picker", label="Main clip", asset_type=AssetType.CLIP),
            RecipeField(name="cohost_clip_id", type="asset_picker", label="Cohost clip", asset_type=AssetType.CLIP),
            RecipeField(name="cohost_width", type="number", label="Cohost width (px)", required=False, default=240, min_value=80, max_value=1920),
            RecipeField(name="margin_x", type="number", label="Margin X (px)", required=False, default=40, min_value=0, max_value=500),
            RecipeField(name="margin_y", type="number", label="Margin Y (px)", required=False, default=40, min_value=0, max_value=500),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.cohost_layout,
        param_map={"main_clip_id": "main_clip", "cohost_clip_id": "cohost_clip"},
    ),
    "broll_splice": Recipe(
        kind="broll_splice",
        display_name="B-roll cutaway",
        family=FAMILY_LAYOUT,
        description="Splice a cinematic clip into the middle of an avatar's timeline (audio stays from base).",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="base_clip_id", type="asset_picker", label="Base clip (avatar)", asset_type=AssetType.CLIP),
            RecipeField(
                name="broll_clip_id", type="asset_picker",
                label="B-roll clip", asset_type=AssetType.CLIP,
                role_filter=AssetRole.B_ROLL.value,
            ),
            RecipeField(name="cutaway_start_s", type="number", label="Cutaway start (seconds)", min_value=0, max_value=600),
            RecipeField(name="cutaway_end_s", type="number", label="Cutaway end (seconds)", min_value=0, max_value=600),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.broll_splice,
        param_map={"base_clip_id": "base_clip", "broll_clip_id": "broll_clip"},
    ),
    "music_bed_pass": Recipe(
        kind="music_bed_pass",
        display_name="Music bed",
        family=FAMILY_LAYOUT,
        description="Mix a music AUDIO track under a base clip's voice.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="base_clip_id", type="asset_picker", label="Base clip (voice)", asset_type=AssetType.CLIP),
            RecipeField(
                name="music_asset_id", type="asset_picker",
                label="Music track", asset_type=AssetType.AUDIO,
                role_filter=AssetRole.AUDIO_TRACK.value,
            ),
            RecipeField(
                name="music_gain_db", type="number", label="Music gain (dB)",
                required=False, default=-18.0, min_value=-40.0, max_value=0.0,
            ),
            RecipeField(
                name="fade_in_ms", type="number", label="Fade in (ms)",
                required=False, default=1000, min_value=0, max_value=10000,
            ),
            RecipeField(
                name="fade_out_ms", type="number", label="Fade out (ms)",
                required=False, default=2000, min_value=0, max_value=10000,
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.music_bed_pass,
        param_map={"base_clip_id": "base_clip", "music_asset_id": "music_asset"},
    ),
    # ---- Polish family ---------------------------------------
    "reels_format": Recipe(
        kind="reels_format",
        display_name="Reformat to Reels (9:16)",
        family=FAMILY_POLISH,
        description="Convert a landscape clip to vertical 9:16 format for Reels / TikTok / Shorts.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="base_clip_id", type="asset_picker", label="Source clip", asset_type=AssetType.CLIP),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.reels_format,
        param_map={"base_clip_id": "base_clip"},
    ),
    # ---- Voice family ----------------------------------------
    "voice_design": Recipe(
        kind="voice_design",
        display_name="Design a new voice",
        family=FAMILY_VOICE,
        description="Generate a new brand voice from a text description. Produces a VOICE asset with a preview MP3.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Spokesperson"),
            RecipeField(
                name="description", type="textarea", label="Voice description",
                min_chars=4, max_chars=1000,
                help_text="e.g. 'warm, conversational founder voice with a slight Southern drawl'.",
            ),
            RecipeField(
                name="voice_name", type="text", label="Voice name (optional)",
                required=False, max_chars=120,
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.voice_design,
    ),
    "multi_lang_dub": Recipe(
        kind="multi_lang_dub",
        display_name="Dub audio to another language",
        family=FAMILY_VOICE,
        description="Translate + re-voice an audio track in one of 29 supported languages.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Spokesperson"),
            RecipeField(name="source_audio_id", type="asset_picker", label="Source audio", asset_type=AssetType.AUDIO),
            RecipeField(
                name="target_language", type="select", label="Target language",
                choices=_DUB_LANGUAGE_CHOICES,
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.multi_lang_dub,
        param_map={"source_audio_id": "source_audio"},
    ),
    # ---- Style family ----------------------------------------
    "style_remix_pass": Recipe(
        kind="style_remix_pass",
        display_name="Style remix (Aleph)",
        family=FAMILY_STYLE,
        description="Apply a style preset (noir / anime / chrome / watercolor / cyberpunk) to a clip via Runway Aleph. Chunked + parallel for clips > 5s.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="source_clip_id", type="asset_picker", label="Source clip", asset_type=AssetType.CLIP),
            RecipeField(
                name="style_preset", type="select", label="Style preset",
                choices=_STYLE_PRESET_CHOICES,
            ),
            RecipeField(
                name="seed", type="number", label="Seed (optional)",
                required=False, help_text="Same seed = same look across reruns.",
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.style_remix_pass,
        param_map={"source_clip_id": "source_clip"},
    ),
    # ---- Creative family -------------------------------------
    "recut_teaser": Recipe(
        kind="recut_teaser",
        display_name="Recut teaser",
        family=FAMILY_CREATIVE,
        description="Take a long clip, auto-pick the strongest sentence, output a short vertical teaser. First net-new capability beyond the hackathon.",
        fields=(
            RecipeField(name="spokesperson_id", type="spokesperson_picker", label="Brand owner (spokesperson)"),
            RecipeField(name="source_clip_id", type="asset_picker", label="Source clip", asset_type=AssetType.CLIP),
            RecipeField(
                name="criterion", type="select", label="Pick by",
                required=False, default="hook", choices=_RECUT_CRITERION_CHOICES,
            ),
            RecipeField(
                name="target_ratio", type="select", label="Output aspect ratio",
                required=False, default="720:1280", choices=_RATIO_CHOICES,
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.recut_teaser,
        param_map={"source_clip_id": "source_clip"},
    ),
    # ---- Dialogue family -------------------------------------
    "dialogue_scene": Recipe(
        kind="dialogue_scene",
        display_name="Dialogue scene (multi-character)",
        family=FAMILY_DIALOGUE,
        description="N speech turns alternating across cast members. Each line speaks as a different spokesperson.",
        fields=(
            RecipeField(
                name="primary_spokesperson_id", type="spokesperson_picker",
                label="Primary spokesperson (owner / narrator)",
            ),
            RecipeField(
                name="lines", type="dialogue_lines",
                label="Dialogue lines",
                help_text="Ordered list of turns. Each turn: pick a spokesperson + write what they say.",
            ),
            # SESSION 199 — outro_text parity.
            RecipeField(
                name="outro_text", type="text",
                label="Brand outro card (optional)",
                required=False, max_chars=80,
                help_text=(
                    "Title card appended after the dialogue. "
                    "3 seconds, white text on black. Leave "
                    "blank to skip."
                ),
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.dialogue_scene,
        custom_resolver=_dialogue_resolver,
    ),
}


def list_recipes() -> list[Recipe]:
    """All recipes in stable order (kind alphabetical)."""
    return sorted(RECIPES.values(), key=lambda r: r.kind)


def get_recipe(kind: str) -> Recipe:
    """Look up a recipe by kind. Raises ``KeyError`` if unknown."""
    return RECIPES[kind]


def resolve_kwargs(
    recipe: Recipe,
    *,
    workspace,
    params: dict,
    created_by,
) -> dict[str, Any]:
    """Map a JSON params dict to starter kwargs.

    Resolves spokesperson_picker / asset_picker fields to ORM
    rows (workspace-scoped). Cross-workspace ids raise
    ``DoesNotExist`` which the view layer turns into 400.

    Recipes with a ``custom_resolver`` short-circuit through it
    instead of the default field-by-field resolution.
    """
    if recipe.custom_resolver is not None:
        return recipe.custom_resolver(
            workspace=workspace, params=params, created_by=created_by,
        )

    from apps.spokespeople.models import Teammate
    from .models import Asset

    kwargs: dict[str, Any] = {
        "workspace": workspace,
        "created_by": created_by,
    }

    for f in recipe.fields:
        if f.name not in params:
            if f.required and f.default is None:
                raise ValueError(f"missing required field: {f.name}")
            continue
        value = params[f.name]
        starter_kwarg = recipe.param_map.get(f.name, f.name)

        if value is None and not f.required:
            continue

        if f.type == "spokesperson_picker":
            sp = Teammate.objects.get(pk=value, workspace=workspace)
            # form-field is "spokesperson_id", starter kwarg is "spokesperson"
            kwargs[starter_kwarg.removesuffix("_id")] = sp
        elif f.type == "script_picker":
            # B-2 / B2.4 (SESSION 206) — pick an approved Script
            # by id; cross-workspace lookups raise DoesNotExist
            # (turned into 400 by the view layer). SESSION 251
            # widened the accepted set from ``status=READY`` to
            # ``status in {READY, RENDERED}`` so operators can
            # reuse a script they've already rendered without
            # cloning + re-approving. The auto_script starter
            # only requires a non-empty draft_text + matching
            # workspace + a spokesperson — both READY and
            # RENDERED satisfy that. DRAFT is still excluded
            # (unverified) and ARCHIVED is still excluded
            # (explicitly retired).
            from apps.scripts.models import Script

            script_row = Script.objects.get(
                pk=value,
                workspace=workspace,
                status__in=(Script.Status.READY, Script.Status.RENDERED),
            )
            # form-field is "script_id", starter kwarg is "script"
            kwargs[starter_kwarg.removesuffix("_id")] = script_row
        elif f.type == "asset_picker":
            asset = Asset.objects.get(pk=value, workspace=workspace)
            # W11.6.5 (SESSION 174) — image assets get unwrapped
            # to their ``file_path`` (data URI for W11.6.1
            # images) because recipes that consume images take
            # URL strings, not Asset rows. cinematic_visual's
            # ``prompt_image: str | None`` is the canonical
            # example. Clips + audio continue to flow through
            # as Asset rows because their consuming starters
            # (e.g. pip_layout's ``base_clip: Asset``) operate
            # on metadata, not URL strings.
            if asset.asset_type == AssetType.IMAGE:
                kwargs[starter_kwarg] = asset.file_path
            else:
                kwargs[starter_kwarg] = asset
        else:
            kwargs[starter_kwarg] = value

    return kwargs
