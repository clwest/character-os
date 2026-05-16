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
  spokesperson_picker — pick a workspace Spokesperson by id
  asset_picker        — pick an existing workspace Asset by id,
                        filtered by ``asset_type``
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
from .models import AssetType, Composition


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
        return {
            "kind": self.kind,
            "display_name": self.display_name,
            "family": self.family,
            "description": self.description,
            "fields": [f.to_json() for f in self.fields],
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
_VERIFIER_MODE_FIELD = RecipeField(
    name="verifier_mode",
    type="select",
    label="K6.4 claim verifier",
    required=False,
    default="warn",
    choices=(
        {"value": "warn", "label": "Warn (flag inventions; let render proceed)"},
        {"value": "strict", "label": "Strict (reject inventions before Runway fires)"},
        {"value": "off", "label": "Off (no post-synthesis verification)"},
    ),
    help_text=(
        "Only applies when 'Use workspace knowledge' is on. Strict blocks "
        "renders with unsupported claims (saves Runway cost); Warn logs "
        "warnings but ships; Off skips verification entirely."
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
    ``spokesperson_id`` has to be resolved to a Spokesperson row.
    Everything else maps the standard way.
    """
    from apps.spokespeople.models import Spokesperson

    primary_id = params.get("primary_spokesperson_id")
    if not primary_id:
        raise ValueError("dialogue_scene requires primary_spokesperson_id")
    primary = Spokesperson.objects.get(pk=primary_id, workspace=workspace)

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
        sp = Spokesperson.objects.get(pk=sp_id, workspace=workspace)
        resolved_lines.append({"spokesperson": sp, "text": text})

    return {
        "workspace": workspace,
        "primary_spokesperson": primary,
        "lines": resolved_lines,
        "mock_mode": bool(params.get("mock_mode", False)),
        "name": params.get("name", "") or "",
        "created_by": created_by,
    }


RECIPES: dict[str, Recipe] = {
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
                name="script", type="textarea", label="Script",
                min_chars=8, max_chars=4000,
                help_text="What the avatar will say. 1-3 paragraphs work best.",
            ),
            RecipeField(
                name="use_knowledge", type="checkbox",
                label="Use workspace knowledge", required=False, default=False,
                help_text="Pipe the script through RAG synthesis using attached docs.",
            ),
            _VERIFIER_MODE_FIELD,
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
            RecipeField(
                name="backdrop_prompt", type="textarea",
                label="Backdrop prompt", min_chars=4, max_chars=600,
                help_text="Visual scene generated as the background (e.g. 'sunset on a city skyline').",
            ),
            RecipeField(
                name="backdrop_ratio", type="select", label="Backdrop aspect ratio",
                required=False, default="1280:720", choices=_RATIO_CHOICES,
            ),
            RecipeField(
                name="backdrop_duration", type="number", label="Backdrop duration (seconds)",
                required=False, default=10, min_value=5, max_value=10,
            ),
            RecipeField(name="use_knowledge", type="checkbox", label="Use workspace knowledge", required=False, default=False),
            _VERIFIER_MODE_FIELD,
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.talking_head_with_backdrop,
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
            _VERIFIER_MODE_FIELD,
            # captions + intro + outro are JSON-shaped; v1 leaves them
            # null and ships the simple flavor. V15.3 may add a captions
            # builder UI.
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
                name="script", type="textarea", label="Long-form script",
                min_chars=200, max_chars=20000,
                help_text="Auto-split into ~280-character chunks at sentence boundaries.",
            ),
            RecipeField(
                name="use_llm_split", type="checkbox",
                label="Use AI for chunk boundaries", required=False, default=False,
                help_text="Consults gpt-5-mini for semantically-clean splits (small cost; otherwise naive at sentence boundaries).",
            ),
            RecipeField(name="use_knowledge", type="checkbox", label="Use workspace knowledge per chunk", required=False, default=False),
            _VERIFIER_MODE_FIELD,
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
            RecipeField(
                name="ratio", type="select", label="Aspect ratio",
                required=False, default="1280:720", choices=_RATIO_CHOICES,
            ),
            RecipeField(
                name="duration", type="number", label="Duration (seconds)",
                required=False, default=5, min_value=5, max_value=10,
            ),
            _NAME_FIELD,
            _MOCK_MODE_FIELD,
        ),
        starter=starters.cinematic_visual,
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
            RecipeField(
                name="image_seed", type="number", label="Image seed (optional)",
                required=False, help_text="Same seed across shots = same visual style.",
            ),
            RecipeField(
                name="clip_duration", type="number", label="Per-shot duration (seconds)",
                required=False, default=5, min_value=5, max_value=5,
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
            RecipeField(
                name="image_seed", type="number", label="Image seed (optional)",
                required=False, help_text="Same seed across shots = same visual style.",
            ),
            RecipeField(
                name="clip_duration", type="number", label="Per-shot duration (seconds)",
                required=False, default=5, min_value=5, max_value=5,
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
            RecipeField(name="background_clip_id", type="asset_picker", label="Background clip", asset_type=AssetType.CLIP),
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
            RecipeField(name="broll_clip_id", type="asset_picker", label="B-roll clip", asset_type=AssetType.CLIP),
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
            RecipeField(name="music_asset_id", type="asset_picker", label="Music track", asset_type=AssetType.AUDIO),
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

    from apps.spokespeople.models import Spokesperson
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
            sp = Spokesperson.objects.get(pk=value, workspace=workspace)
            # form-field is "spokesperson_id", starter kwarg is "spokesperson"
            kwargs[starter_kwarg.removesuffix("_id")] = sp
        elif f.type == "asset_picker":
            asset = Asset.objects.get(pk=value, workspace=workspace)
            kwargs[starter_kwarg] = asset
        else:
            kwargs[starter_kwarg] = value

    return kwargs
