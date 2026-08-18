"""Multi-character dialogue synthesis — SESSION 257 / AI-D2.

One structured LLM call writes the whole conversation between a
selected cast, then post-parse validation + per-turn K6.4
verification produces normalized turns suitable for the EXISTING
manual ``dialogue_scene`` renderer.

Not a new render pipeline. This module's ONLY responsibility is
"who speaks when + what they say." Turn-to-render is handled by
``apps.compositions.starters.dialogue_scene`` unchanged — the
downstream contract is `lines = [{spokesperson_id, text}, ...]`,
and this module produces exactly that shape.

Contract alignment
------------------
See ``docs/design/DIALOGUE_SCENE_AI_TOPIC_V1.md`` for the
governing scope-lock. Load-bearing rules from that doc that
land here:

* **Rule 4** — one structured synthesis call per scene, not
  one call per character. Setup/payoff, callback, disagreement,
  correction require both characters to see each other's turns.
* **Rule 5** — stable Character-OS-generated aliases
  (``"patch"``, ``"rivet"``), not UUIDs. Alias→Teammate
  resolution runs post-parse.
* **Rule 6** — post-parse validation is mandatory. Rejection
  persists raw LLM JSON; one bounded corrective resynth
  maximum.
* **Rule 7** — per-character K2 retrieval + per-turn K6.4.
  Cross-character factual leak is prevented structurally by
  K2's M2M scope filter (``retrieve_for_teammate``), NOT by
  convention.
* **Rule 8** — character voices stay independent. Dual
  ``--- CHARACTER A ---`` / ``--- CHARACTER B ---`` blocks;
  no blending.
* **Rule 9** — duration is aggregate. Uses a dialogue-local
  cps planning estimator (``_DIALOGUE_CPS``, recalibrated
  15 → 13 in SESSION 260 from real-render corpus) with a
  dialogue-local ``DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER
  = 1.00`` (talking-head's 0.90 stays untouched).
* **Rule 10** — opener is a hard synthesis constraint in the
  prompt, verified after parse. No post-hoc turn-0 rewriting.
* **Rule 14** — no forced speaker alternation.
  ``A → B → B → A → B → A`` is legal and often better.
* **Rule 15** — no fixed turn count. Turn count emerges from
  target duration + pacing.

Mock behavior
-------------
``mock_mode=True`` OR ``DIALOGUE_SYNTHESIS_FORCE_MOCK`` env/
settings flag → deterministic stub result. No OpenAI call, no
K2 retrieval provider hop. Returns a valid ``DialogueResult``
that satisfies every post-parse validator and preserves the
opener if supplied. Used by unit tests and by
``composition.mock_mode=True`` renders.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Sequence

from django.conf import settings

from character_os.claim_verifier import (
    ClaimVerifierError,
    build_allowed_vocabulary,
    build_factual_corpus,
    run_verifier,
)
from character_os.duration_contract import AVATAR_SPEECH_SAFE_MAX_CHARS
from character_os.writing_contract import (
    WRITING_CONTRACT_VERSION,
    WritingContract,
)

if TYPE_CHECKING:
    from apps.accounts.models import Workspace
    from apps.embeddings.models import KnowledgeChunk
    from apps.spokespeople.models import Teammate

logger = logging.getLogger(__name__)


# ---- Constants ---------------------------------------------------

DIALOGUE_MODEL = "gpt-5"
_MAX_OUTPUT_TOKENS = 4000
_REASONING_EFFORT = "low"

# SESSION 257 / AI-D2 — dialogue owns its own synthesis
# calibration constant. Kept distinct from talking-head's
# ``K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 0.90`` so future
# per-character delivery calibration can move here without
# affecting talking-head behavior.
#
# The 1.00 value means "aim exactly at the operator target."
# Talking-head's 0.90 exists because GPT tends to overshoot char
# targets on prose; dialogue's discrete-turn structure doesn't
# overshoot the same way in practice. Recalibrate from real
# dogfood if evidence appears.
DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER: float = 1.00

# Planning estimator — characters/second used to (a) translate the
# operator's target-duration seconds into a first-pass ideal char
# count for the LLM prompt, (b) predict rendered seconds from the
# synthesized aggregate ``sum(len(turn.text))``, and (c) compute
# the ±20 % acceptance band and the corrective-retry char target.
# True acceptance is the band; this constant is only how the band
# is expressed in characters.
#
# SESSION 260 empirical recalibration 15 → 13. Source of truth for
# the value:
#
#   * corpus: 10 completed real-mode ``dialogue_scene`` compositions
#     (all 60s target) exercising Patch, Rivet, Mike, Repo Red;
#   * 83 authoritative ``duration_source == "media_probe"`` speech
#     turns (media-engine ffprobed the rendered mp4);
#   * weighted global observed CPS = 13.05
#     (8,554 chars / 655.6s);
#   * per-composition median CPS = 13.15 (min 11.85, max 13.94,
#     stdev 0.65 — tight);
#   * per-turn median CPS = 12.83 (min 9.21, max 16.19,
#     stdev 1.58 — short phrases carry silence overhead);
#   * Patch weighted = 13.24 (n=40 turns), Rivet weighted = 12.83
#     (n=37 turns) — 0.4 spread is inside per-comp stdev, does not
#     justify per-character calibration yet;
#   * candidate replay at 15 / 13 / 12 / 11.5 against the corpus
#     showed 13 produced zero false-positive compression decisions
#     against the actual rendered durations; 12 and 11.5 introduced
#     one and two false-positive compressions respectively.
#
# NOT a permanent provider constant — an empirical Character OS
# dialogue planning calibration. Re-audit as the corpus grows,
# especially once real 30 / 90 / 120-second renders exist. See
# ``docs/handoffs/SESSION_260_DIALOGUE_CPS_CALIBRATION.md``.
#
# Kept local to this module so a future per-character calibration
# does not have to move the talking-head constant
# ``avatar_speech.py :data:_AVATAR_SPEECH_CHARS_PER_SECOND``.
_DIALOGUE_CPS: int = 13

# SESSION 259 corrective-duration slice — headroom factor for
# the one bounded corrective retry's compression/expansion
# target. Chosen at 0.92 (offset 8 pt below the hard ceiling
# and above the hard floor). Originally introduced to protect
# against the 15-cps planning estimator running hot relative to
# real Patch/Rivet renders; SESSION 260 recalibrated the
# estimator to 13 cps, which materially closes that gap, but
# the retry-headroom stays because it also guards against
# turn-level cps variance (per-turn stdev = 1.58, p10 = 10.9,
# p90 = 15.2) — a scene that just clears the ceiling in
# characters can still render past it in seconds. Applies ONLY
# to the corrective-hint target string — never to the
# acceptance band, never to first-pass planning, never to
# global calibration. Not exported.
_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION: float = 0.92

# Duration-specific turn-count guidance. Tuple layout:
# ``(soft_min, soft_max, hard_max)``. Hard min is a module-
# global 2 (below that it isn't a conversation).
#
# Soft bounds go into the prompt as pacing guidance. Hard bounds
# are validator gates. NONE of these are cost bounds — SESSION
# 257 (`46f5efd`) established that turn count is not a COGS
# lever at Runway's flat 2-credit-per-call billing.
_TURN_BANDS: dict[int, tuple[int, int, int]] = {
    30: (4, 6, 12),
    60: (6, 9, 18),
    90: (8, 12, 24),
    120: (10, 15, 30),
}
_HARD_MIN_TURNS: int = 2

# Duration tolerance — mirrors talking-head's ±20 %.
_DURATION_TOLERANCE: float = 0.20


# ---- Exception ---------------------------------------------------


class DialogueSynthesisError(Exception):
    """Raised when structured synthesis + one corrective resynth
    both fail validation. Callers persist the raw LLM JSON to
    ``Composition.rejected_synthesis`` and surface the error to
    the operator without firing any Runway calls.

    SESSION 262 — additional per-attempt provenance is carried on
    the exception so the view-layer FAILED-composition rescue path
    can persist Composition-local observability fields
    (`first_pass_synthesis`, `corrective_hint`,
    `corrective_pass_synthesis`, `synthesis_attempt_count`,
    `synthesis_predicted_seconds`, and the retrieval snapshot as
    `chunk_ids`). All are optional — callers that don't yet plumb
    them default to the pre-SESSION-262 shape.
    """

    def __init__(
        self,
        reason: str,
        *,
        raw_llm_json: str = "",
        first_pass_raw: str = "",
        corrective_hint: str = "",
        corrective_pass_raw: str = "",
        attempt_count: int = 0,
        predicted_seconds: float | None = None,
        chunk_ids: list[str] | None = None,
        memory_ids: list[str] | None = None,
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.raw_llm_json = raw_llm_json
        self.first_pass_raw = first_pass_raw
        self.corrective_hint = corrective_hint
        self.corrective_pass_raw = corrective_pass_raw
        self.attempt_count = attempt_count
        self.predicted_seconds = predicted_seconds
        self.chunk_ids = list(chunk_ids or [])
        # SESSION 264 Slice 2 — retrieval snapshot for narrative
        # memory. Populated when retrieval succeeded before
        # validation failed; empty when the failure was
        # pre-retrieval.
        self.memory_ids = list(memory_ids or [])


# ---- Data model --------------------------------------------------


@dataclass
class DialogueTurn:
    """One turn in the synthesized dialogue.

    * ``line_index`` — 0..N-1 contiguous. Validated post-parse.
    * ``speaker_teammate`` — resolved from ``speaker_alias`` via
      the approved cast. Guaranteed to be one of the passed
      Teammates.
    * ``speaker_alias`` — the stable Character-OS-generated
      alias the LLM emitted (``"patch"``, ``"rivet"``). Kept
      for logs / audit; downstream render uses
      ``speaker_teammate.id``.
    * ``text`` — the spoken line. Non-empty after strip.
    * ``verification_warnings`` — per-turn K6.4 warnings (list
      of dicts from ``UnsupportedClaim.to_dict()``). Empty on
      supported turns.
    * ``verification_status`` — ``"verified" | "warned" |
      "rejected" | "skipped"``. Rejected only in strict-mode
      failure paths, which raise before this dataclass returns.
    """

    line_index: int
    speaker_teammate: "Teammate"
    speaker_alias: str
    text: str
    verification_warnings: list[dict] = field(default_factory=list)
    verification_status: str = ""


@dataclass
class DialogueResult:
    """What ``synthesize_dialogue`` returns.

    Shape is designed so callers can:

    * Hydrate the existing ``dialogue_scene`` starter's
      ``lines = [{spokesperson_id, text}, ...]`` shape by
      iterating ``turns`` and reading ``t.speaker_teammate.id``
      + ``t.text``.
    * Stamp ``Composition.writing_contract_version`` from
      :attr:`writing_contract_version`.
    * Persist ``verification_warnings`` per turn OR aggregated
      onto ``Composition.verification_warnings`` (contract v2
      compatible).
    * Persist ``chunk_ids`` onto ``Composition.knowledge_chunk_ids``
      (mirror of talking-head aggregation).
    * Persist ``raw_llm_json`` onto
      ``Composition.rejected_synthesis`` when rejection needs
      audit context. Only populated on failure paths that don't
      raise (i.e. mock-mode + explicit debug).
    """

    turns: list[DialogueTurn]
    chunk_ids: list[str]
    per_character_chunk_ids: dict[str, list[str]]
    writing_contract_version: int
    overall_verification_status: str
    total_chars: int
    predicted_seconds: float
    target_duration_seconds: int
    aliases: dict[str, str]
    mock_mode: bool = False
    used_knowledge: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    raw_llm_json: str = ""
    # SESSION 262 — per-attempt provenance for Composition observability.
    # `attempt_count` is 1 for first-pass-accepted, 2 for corrective-pass-
    # accepted. Mock branch returns 1 (no retry loop). `first_pass_raw`
    # is always the RAW first LLM response; `corrective_pass_raw` is the
    # RAW corrective response (empty when no retry fired); `corrective_hint`
    # is the exact hint the retry received.
    attempt_count: int = 0
    first_pass_raw: str = ""
    corrective_hint: str = ""
    corrective_pass_raw: str = ""
    # SESSION 264 Slice 2 — narrative-memory provenance. Flat
    # list of ``NarrativeMemory.id`` strings that fed the render
    # (SEPARATE from ``chunk_ids`` because narrative memory rows
    # are NOT ``KnowledgeChunk`` rows and would silently break
    # ``resolve_chunk_ids_to_docs`` / the F6 ``composed_in`` view
    # if commingled). Landed on ``Composition.memory_ids``.
    memory_ids: list[str] = field(default_factory=list)


# ---- Force-mock helpers ------------------------------------------


def _is_force_mock() -> bool:
    """Same pattern as ``script_synthesis._is_force_mock`` and
    the other ``*_FORCE_MOCK`` flags in the family.
    Settings beats env."""
    settings_flag = getattr(settings, "DIALOGUE_SYNTHESIS_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("DIALOGUE_SYNTHESIS_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


# ---- Alias generation --------------------------------------------


_ALIAS_SANITIZE_RE = re.compile(r"[^a-z0-9_]+")


def _sanitize_alias(name: str) -> str:
    """Deterministic alias root from a Teammate name.

    * Lowercase
    * Non-``[a-z0-9_]`` collapsed to underscore
    * Repeated underscores collapsed to single
    * Leading / trailing underscores stripped
    * Empty result (e.g. name was pure emoji / whitespace) →
      ``"speaker"``

    Alias root is stable given the same input name.
    """
    lower = (name or "").strip().lower()
    slug = _ALIAS_SANITIZE_RE.sub("_", lower)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "speaker"


def build_alias_map(cast: Sequence["Teammate"]) -> dict[str, "Teammate"]:
    """Deterministic collision-safe alias → Teammate map.

    Ordering: preserves ``cast`` order, so ``cast[0]`` gets first
    claim on its natural alias root; ``cast[1]`` gets suffix
    ``_2`` on collision, ``cast[2]`` gets ``_3``, and so on.

    Guarantees:

    * Alias values are unique within the returned map.
    * Every alias resolves back to exactly one Teammate.
    * Same input cast (same order, same names) always produces
      the same map (deterministic — safe to include in prompts,
      logs, cache keys).

    Raises ``DialogueSynthesisError`` if the cast is empty (a
    dialogue needs at least one speaker; the caller should
    already have enforced cast >= 2, but this stays defensive).
    """
    if not cast:
        raise DialogueSynthesisError("cast is empty")

    alias_to_teammate: dict[str, "Teammate"] = {}
    for tm in cast:
        root = _sanitize_alias(getattr(tm, "name", "") or "")
        candidate = root
        suffix = 2
        while candidate in alias_to_teammate:
            candidate = f"{root}_{suffix}"
            suffix += 1
        alias_to_teammate[candidate] = tm
    return alias_to_teammate


# ---- Prompt block builders ---------------------------------------
#
# Per scope-lock: prompt builders live inline in this module (not
# extracted from ``script_synthesis.py``) to avoid a broad refactor
# and to let dialogue's per-character shape evolve independently.
# The single-character K6 shape stays in ``script_synthesis.py``
# unchanged.


def _is_scope_shared_document(doc) -> bool:
    """C.1 scope-aware SHARED detector (SESSION 263).

    A KnowledgeDocument is "scope-shared" for a given synthesis
    iff either:

    * Its M2M ``spokespeople`` is empty (Universe-wide broadcast —
      row 6 of the retrieval truth table), OR
    * Its M2M contains more than one teammate (explicit shared
      canon — row 7 case).

    A doc scoped to exactly one teammate is per-character even if
    that teammate is one of the cast — it belongs in that
    character's SCOPED block.

    This is called on chunks that appeared in per-character
    retrievals so we can promote scope-shared ones to SHARED
    rather than mislabelling them under a character block.
    Prior to SESSION 263 the SHARED block was populated purely
    post-hoc (a chunk was SHARED iff it happened to appear in
    two characters' independent top-k lists); under B + C.1 the
    B pass fills SHARED deterministically, and this helper
    guards the per-character emission from mislabelling stray
    scope-shared chunks that leak in via cosine ranking.
    """
    if doc is None:
        return False
    try:
        count = doc.spokespeople.count()
    except Exception:
        return False
    return count == 0 or count > 1


def _build_factual_basis_section(
    cast_labels: list[tuple[str, "Teammate", list["KnowledgeChunk"]]],
    *,
    use_knowledge: bool,
    shared_chunks: "list[KnowledgeChunk] | None" = None,
    memory_rows: "list | None" = None,
) -> str:
    """§1 Factual Basis, dialogue-shaped.

    Four labeled sub-blocks (in prompt order):

    * SHARED — canon chunks legitimately visible to every cast
      member (SESSION 263 Slice B canon-lane pass + C.1
      scope-shared promotion).
    * NARRATIVE MEMORY — SESSION 264 Slice 2. Operator-promoted
      story history rows. Between SHARED and CHARACTER blocks so
      the LLM reads it as past events subordinate to static
      canon. Never contains synthesis-generated content; only
      rows the operator explicitly clicked "Remember this" on.
    * CHARACTER A / B — chunks + factual identity fields
      scoped to each speaker.

    Excludes personality / POV / brand fields per
    ``build_factual_corpus``'s existing rules.

    ``use_knowledge=False`` yields a factual section that
    still names the identity fields on each character (a
    "safe general conversation" fallback) but includes no
    K2 chunks and skips both canon + memory lanes.

    ``shared_chunks`` (SESSION 263 Slice B) is the deterministic
    output of ``retrieve_universe_canon``. ``memory_rows``
    (SESSION 264 Slice 2) is the deterministic output of
    ``retrieve_universe_memory``. When either is ``None``
    (legacy callers) or empty, that block is omitted.
    """
    lines = [
        "=== SECTION 1 — FACTUAL BASIS ===",
        "The ONLY sources capable of supporting factual claims. "
        "Every factual claim in the script must trace back to "
        "content in this section. Do not invent product details, "
        "prices, features, statistics, or named entities not "
        "present here. If a fact isn't in this section, leave it "
        "out.",
        "",
        "SCOPE RULE — each character may only cite facts from "
        "the SHARED section OR from THAT CHARACTER'S own scoped "
        "section. A character MAY NOT cite the other character's "
        "scoped facts as their own knowledge. (Characters may of "
        "course react to what the other character SAYS in the "
        "scene.)",
    ]

    # SESSION 263 Slice B + C.1. Emit SHARED deterministically
    # from the canon lane's output, and promote any scope-shared
    # chunks that leak into per-character retrieval so they don't
    # get mislabelled as character-scoped.
    shared_ids: set[str] = set()
    shared_lines: list[str] = []

    if use_knowledge:
        # B — canon-lane output (deterministic, cast-visible-by-scope).
        for c in shared_chunks or ():
            cid = str(getattr(c, "id", "") or "")
            if not cid or cid in shared_ids:
                continue
            shared_ids.add(cid)
            text = getattr(c, "chunk_text", "") or ""
            shared_lines.append(
                f"[SHARED CHUNK — doc {getattr(c, 'document_id', '')}]\n"
                f"{text}"
            )

        # C.1 — scope-aware promotion. A chunk from per-character
        # retrieval whose document is scope-shared (M2M-null or
        # M2M-many) is universe-visible; it must not be emitted
        # under a per-character SCOPED block, which would tell the
        # LLM the other character can't cite it (SCOPE RULE
        # violation via mislabelling). Promote to SHARED.
        for _alias, _tm, chunks in cast_labels:
            for c in chunks:
                cid = str(getattr(c, "id", "") or "")
                if not cid or cid in shared_ids:
                    continue
                if _is_scope_shared_document(getattr(c, "document", None)):
                    shared_ids.add(cid)
                    text = getattr(c, "chunk_text", "") or ""
                    shared_lines.append(
                        f"[SHARED CHUNK — doc {getattr(c, 'document_id', '')}]\n"
                        f"{text}"
                    )

        if shared_lines:
            lines.append("")
            lines.append("--- SHARED WORLD KNOWLEDGE (any character may cite) ---")
            lines.append("\n\n".join(shared_lines))

        # SESSION 264 Slice 2 — narrative-memory block. Sits between
        # SHARED WORLD KNOWLEDGE and per-character SCOPED KNOWLEDGE.
        # Same "any character may cite" visibility, but explicitly
        # framed as *past events* so the LLM treats it as callback
        # material rather than present factual claims. Static canon
        # wins on conflict (the wording below is load-bearing —
        # tests assert on the "canon wins" phrase).
        if memory_rows:
            memory_lines: list[str] = []
            for m in memory_rows:
                mid = str(getattr(m, "id", "") or "")
                body = (getattr(m, "body", "") or "").strip()
                if not (mid and body):
                    continue
                memory_lines.append(
                    f"[MEMORY {mid}]\n{body}"
                )
            if memory_lines:
                lines.append("")
                lines.append(
                    "--- EPISODE / NARRATIVE MEMORY (past events in this "
                    "Universe; static canon wins on conflict) ---"
                )
                lines.append(
                    "These are operator-promoted story memories. Use them "
                    "as historical context or callback material where "
                    "natural. Do not recite them verbatim; treat them as "
                    "background the cast already knows happened."
                )
                lines.append("\n\n".join(memory_lines))

    for alias, tm, chunks in cast_labels:
        header = f"--- {alias.upper()}'S SCOPED KNOWLEDGE (only {alias!r} may cite these as their own) ---"
        lines.append("")
        lines.append(header)
        brief = (getattr(tm, "business_brief", "") or "").strip()
        who = (getattr(tm, "who_you_help", "") or "").strip()
        what = (getattr(tm, "what_you_sell", "") or "").strip()
        if brief:
            lines.append(f"BUSINESS SHAPE:\n{brief}")
        if who:
            lines.append(f"AUDIENCE:\n{who}")
        if what:
            lines.append(f"OFFERING:\n{what}")
        if use_knowledge:
            per_char_lines: list[str] = []
            for c in chunks:
                cid = str(getattr(c, "id", "") or "")
                if cid in shared_ids:
                    continue
                text = getattr(c, "chunk_text", "") or ""
                per_char_lines.append(
                    f"[CHUNK — doc {getattr(c, 'document_id', '')}]\n{text}"
                )
            if per_char_lines:
                lines.append(
                    "SCOPED KNOWLEDGE CHUNKS:\n" + "\n\n".join(per_char_lines)
                )
            elif not (brief or who or what):
                lines.append("(no scoped facts on record)")
        elif not (brief or who or what):
            lines.append("(no scoped facts on record)")

    return "\n\n".join(lines)


def _build_character_voice_block(alias: str, tm: "Teammate") -> str:
    """One character's §2 sub-block. Same field layout as the
    single-character K6 §2 builder (see
    ``script_synthesis._build_character_voice_section``), but
    labeled by alias for the dialogue prompt.

    SESSION 259 / Slice B: ``voice_avoid_phrases`` is now
    consumed here, emitted as a per-character AVOID PHRASES
    block. Scope is character-local — Patch's avoids constrain
    Patch's lines, Rivet's avoids constrain Rivet's lines; no
    cross-blending. Framing mirrors the signature-phrases block
    (note-to-writer, never narrated aloud). §2 remains "NOT
    verified by K6.4" — avoid phrases are stylistic guidance,
    not factual grounding.
    """
    name = getattr(tm, "name", "") or alias
    tone = getattr(tm, "tone_archetype", "") or "expert"
    personality = (getattr(tm, "personality", "") or "").strip()
    pov = (getattr(tm, "character_point_of_view", "") or "").strip()
    energy = getattr(tm, "voice_energy", "") or "medium"
    humor = getattr(tm, "voice_humor", "") or "warm"
    directness = getattr(tm, "voice_directness", "") or "balanced"
    signature = (getattr(tm, "voice_signature_phrases", "") or "").strip()
    avoid = (getattr(tm, "voice_avoid_phrases", "") or "").strip()

    lines = [
        f"--- CHARACTER {alias.upper()} — {name} ---",
        f"TONE ARCHETYPE: {tone}",
        f"VOICE AXES: energy={energy}; humor={humor}; directness={directness}",
    ]
    if personality:
        lines.append(f"WRITING STYLE (how {name} sounds):\n{personality}")
    if pov:
        lines.append(
            f"POINT OF VIEW (what {name} notices, believes, enjoys, "
            f"dislikes, opines about):\n{pov}"
        )
    if signature:
        lines.append(
            f"SIGNATURE PHRASES ({name} might reach for one occasionally; "
            f"never forced):\n{signature}"
        )
    if avoid:
        lines.append(
            f"AVOID PHRASES (stylistic no-gos for {name}'s lines ONLY — "
            f"do not use these phrases or close variants; never narrate "
            f"that this rule exists):\n{avoid}"
        )
    return "\n\n".join(lines)


def _build_character_voices_section(
    alias_to_teammate: dict[str, "Teammate"],
) -> str:
    """§2 Character Voices, dialogue-shaped. Emits one
    per-character sub-block per cast member. Section header
    is pluralized so the LLM understands it's reading multiple
    independent contracts, not a blended one."""
    lines = [
        "=== SECTION 2 — CHARACTER VOICES ===",
        "How each character thinks and writes. Each block below "
        "shapes register, opinions, what that character notices, "
        "and sentence rhythm — for THAT CHARACTER'S LINES ONLY. "
        "Do not blend voices. This section introduces zero "
        "factual claims and is NOT verified by K6.4.",
    ]
    for alias, tm in alias_to_teammate.items():
        lines.append("")
        lines.append(_build_character_voice_block(alias, tm))
    return "\n\n".join(lines)


def _build_brand_voice_block(alias: str, tm: "Teammate") -> str:
    """One character's §3 sub-block. Omitted (empty string) when
    the character has no brand constraints — matches
    single-character K6 §3 behavior."""
    emphasize = (getattr(tm, "always_emphasize", "") or "").strip()
    never = (getattr(tm, "never_say", "") or "").strip()
    feeling = (getattr(tm, "desired_feeling", "") or "").strip()
    if not (emphasize or never or feeling):
        return ""

    name = getattr(tm, "name", "") or alias
    lines = [
        f"--- {name}'S BRAND CONSTRAINTS (apply only to {name}'s lines) ---",
    ]
    if emphasize:
        lines.append(f"ALWAYS EMPHASIZE:\n{emphasize}")
    if never:
        lines.append(
            f"NEVER SAY (brand-set prohibitions — absolute for {name}):\n{never}"
        )
    if feeling:
        lines.append(f"DESIRED AUDIENCE FEELING:\n{feeling}")
    return "\n\n".join(lines)


def _build_brand_voices_section(
    alias_to_teammate: dict[str, "Teammate"],
) -> str:
    """§3 Brand Voices, dialogue-shaped. Per-character
    constraints; each character's ``never_say`` applies only to
    that character's own lines. Returns empty string if no
    character has any brand constraints (matches
    single-character K6 §3 behavior)."""
    blocks: list[str] = []
    for alias, tm in alias_to_teammate.items():
        block = _build_brand_voice_block(alias, tm)
        if block:
            blocks.append(block)
    if not blocks:
        return ""
    header = [
        "=== SECTION 3 — BRAND VOICES ===",
        "Positioning each character must respect. These are "
        "BRAND constraints, not character opinions. Each block "
        "applies ONLY to that character's own lines. Brand Voice "
        "does NOT independently license factual truth — any "
        "factual proposition here must be independently supported "
        "by Section 1.",
    ]
    return "\n\n".join(header + [""] + blocks)


def _turn_band_for(target_seconds: int) -> tuple[int, int, int]:
    """Nearest supported band. Falls back to the closest of
    30/60/90/120 for arbitrary durations. Return tuple is
    ``(soft_min, soft_max, hard_max)``."""
    supported = sorted(_TURN_BANDS.keys())
    nearest = min(supported, key=lambda d: abs(d - target_seconds))
    return _TURN_BANDS[nearest]


def _build_task_section(
    *,
    topic: str,
    target_duration_seconds: int,
    alias_to_teammate: dict[str, "Teammate"],
    opener: str | None,
    corrective_hint: str | None,
) -> str:
    """§5 Task. Topic + cast alias map + soft turn guidance +
    (optional) pinned opener + (optional) corrective hint.

    Alias map is emitted as a fixed enumerated list so the LLM
    has no room to invent a third speaker or use a UUID."""
    soft_min, soft_max, hard_max = _turn_band_for(target_duration_seconds)
    lines = [
        "=== SECTION 5 — TASK ===",
        f"TOPIC:\n{topic.strip() or '(no topic supplied — use §1)'}",
        "",
        "CAST — use ONLY these speaker_alias values in your JSON "
        "output. Invented aliases will be rejected.",
    ]
    for alias, tm in alias_to_teammate.items():
        name = getattr(tm, "name", "") or alias
        lines.append(f"  * {alias!r} → {name}")
    lines.append("")
    lines.append(
        f"TARGET DURATION: approximately {target_duration_seconds} seconds "
        f"of total spoken runtime across the whole scene (not per "
        f"character). Aim for a natural conversational rhythm at ~"
        f"{_DIALOGUE_CPS} spoken characters per second."
    )
    lines.append(
        f"TURN COUNT GUIDANCE: {soft_min}–{soft_max} turns is a "
        f"pacing suggestion, not a hard requirement. Short "
        f"reactions and longer explanatory turns both welcome; "
        f"vary length naturally. Strict A→B→A→B alternation is NOT "
        f"required; consecutive same-speaker turns are legal when "
        f"the scene reads better that way. Hard maximum: {hard_max} "
        f"turns (validator gate)."
    )

    hard_constraints: list[str] = []
    if opener and opener.strip():
        primary_alias = next(iter(alias_to_teammate))
        primary_name = getattr(
            alias_to_teammate[primary_alias], "name", "",
        ) or primary_alias
        hard_constraints.append(
            f"PINNED OPENER (turn 0 belongs to {primary_alias!r} = "
            f"{primary_name}; use this text VERBATIM as the "
            f"``text`` of turn 0; the rest of the conversation "
            f"must follow naturally from it):\n{opener.strip()}"
        )
    if corrective_hint and corrective_hint.strip():
        hard_constraints.append(
            f"CORRECTIVE HINT (previous attempt failed validation; "
            f"apply this):\n{corrective_hint.strip()}"
        )
    if hard_constraints:
        lines.append("")
        lines.append(
            "HARD CONSTRAINTS (override Character Voice and Writing "
            "Contract preferences; do NOT override Factual Basis or "
            "Brand Voice prohibitions):\n\n"
            + "\n\n".join(hard_constraints)
        )

    lines.append("")
    lines.append(
        "OUTPUT — return a single JSON object matching this exact "
        "shape:\n"
        "{\n"
        '  "turns": [\n'
        '    {"line_index": 0, "speaker_alias": "<one of the '
        'cast aliases above>", "text": "..."},\n'
        '    {"line_index": 1, "speaker_alias": "...", '
        '"text": "..."},\n'
        "    ...\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        f"* Each turn's text MUST be ≤ {AVATAR_SPEECH_SAFE_MAX_CHARS} "
        "characters.\n"
        "* line_index MUST be 0, 1, 2, ... (contiguous, no gaps, no "
        "duplicates).\n"
        "* Every speaker_alias MUST be exactly one of the aliases "
        "listed under CAST above.\n"
        "* Every text MUST be non-empty after trim.\n"
        "* Output ONLY the JSON object, no prose around it, no "
        "code fences."
    )
    return "\n".join(lines)


def _build_writing_contract_section() -> str:
    """§4 Writing Contract, dialogue shape. Delegates to the
    canonical ``WritingContract.for_shape('dialogue_scene')``
    per contract rule 12 — no duplicated contract text here."""
    return (
        f"=== SECTION 4 — WRITING CONTRACT (version {WRITING_CONTRACT_VERSION}) ===\n"
        f"Format-specific rules. Same for every character; each "
        f"character's voice from Section 2 shapes HOW these rules "
        f"get executed for that character's lines.\n\n"
        f"{WritingContract.for_shape('dialogue_scene')}"
    )


_PRECEDENCE_RULES = (
    "=== PRECEDENCE RULES ===\n"
    "When sections conflict, resolve in this order:\n"
    "  1. Factual Basis (§1) beats everything on TRUTH. No claim "
    "survives that isn't grounded in the SPEAKING CHARACTER's "
    "allowed factual scope (SHARED + that character's own).\n"
    "  2. Brand Voice (§3) beats Character Voice (§2) on "
    "PROHIBITIONS. Each character's ``never_say`` overrides any "
    "of that character's other preferences.\n"
    "  3. Writing Contract (§4) beats Character Voice on "
    "INTERACTION STRUCTURE.\n"
    "  4. Character Voice (§2) beats Writing Contract on "
    "REGISTER — the contract's anti-generic list is a floor; "
    "each character's voice adds distinctive register on top.\n"
    "  5. Task (§5) Hard Constraints (pinned opener, corrective "
    "hint) beat Character Voice preferences and Writing Contract "
    "defaults, but NEVER override Factual Basis or Brand Voice "
    "prohibitions."
)


def _assemble_system_prompt(
    *,
    cast_labels: list[tuple[str, "Teammate", list["KnowledgeChunk"]]],
    alias_to_teammate: dict[str, "Teammate"],
    use_knowledge: bool,
    shared_chunks: "list[KnowledgeChunk] | None" = None,
    memory_rows: "list | None" = None,
) -> str:
    factual = _build_factual_basis_section(
        cast_labels,
        use_knowledge=use_knowledge,
        shared_chunks=shared_chunks,
        memory_rows=memory_rows,
    )
    voices = _build_character_voices_section(alias_to_teammate)
    brand = _build_brand_voices_section(alias_to_teammate)
    contract = _build_writing_contract_section()

    parts = [factual, voices]
    if brand:
        parts.append(brand)
    parts.append(contract)
    parts.append(_PRECEDENCE_RULES)
    return "\n\n".join(parts)


# ---- Corrective duration hints (SESSION 259 slice) ---------------
#
# Rewrites the one-liner validation strings the ``_parse_and_validate``
# path returns on aggregate-duration failure. The prior wording
# ("Tighten by removing any turn that could be cut without loss to
# the arc") fought Writing Contract v4's CAUSAL CHAIN invariant —
# every turn is a load-bearing beat, so the model correctly resisted
# turn deletion and had no other lever, then under-compressed.
#
# The dialogue-shaped hint gives the retry:
#   * concrete numeric targets (actual, ceiling/floor, headroom, delta);
#   * "preserve the beats, shorten the beats" framing;
#   * explicit language-compression tactics (fragments, drop second
#     clauses, remove decorative language, short reactions);
#   * a preservation contract (character identity + factual grounding
#     + causal continuity + arc + payoff).
#
# ``_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION`` (0.92, see top of
# module) sets the retry's target off the hard boundary so a scene
# that just passes synthesis still speaks safely inside the finished
# video budget.


def _dialogue_over_length_hint(
    *,
    total_chars: int,
    predicted_seconds: float,
    target_duration_seconds: int,
    upper_seconds: float,
) -> str:
    """Compression retry hint. Called when
    ``predicted_seconds > upper`` at first-pass validation."""
    upper_chars = int(round(upper_seconds * _DIALOGUE_CPS))
    upper_seconds_int = int(round(upper_seconds))
    excess_chars = max(1, total_chars - upper_chars)
    headroom_chars = int(round(
        upper_chars * _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION
    ))
    headroom_seconds = int(round(headroom_chars / _DIALOGUE_CPS))
    return (
        f"Your dialogue is too long.\n"
        f"\n"
        f"Previous attempt: {total_chars} characters "
        f"(~{predicted_seconds:.0f}s).\n"
        f"Target: {target_duration_seconds}s.\n"
        f"Hard acceptance ceiling: {upper_chars} characters "
        f"(~{upper_seconds_int}s).\n"
        f"You must remove at least {excess_chars} characters.\n"
        f"\n"
        f"Rewrite the SAME scene to approximately "
        f"{headroom_chars} characters (~{headroom_seconds}s), "
        f"leaving comfortable headroom below the hard ceiling.\n"
        f"\n"
        f"Preserve the conversational beats and causal chain. "
        f"Do not solve this primarily by deleting turns.\n"
        f"\n"
        f"Make the LANGUAGE lighter:\n"
        f"  * prefer short direct replies when natural;\n"
        f"  * fragments are allowed;\n"
        f"  * one idea per turn where possible;\n"
        f"  * short reactions are valuable;\n"
        f"  * remove second or third clauses that merely explain "
        f"the reaction;\n"
        f"  * remove explanations the previous line already made "
        f"obvious;\n"
        f"  * remove duplicated setup;\n"
        f"  * remove repeated framing;\n"
        f"  * remove decorative language that does not change the "
        f"scene;\n"
        f"  * do not narrate why a response is causally connected "
        f"— let the response itself make that clear.\n"
        f"\n"
        f"Preserve: character identity; factual grounding; "
        f"conversational causality; the scene's arc; the ending "
        f"payoff."
    )


def _dialogue_under_length_hint(
    *,
    total_chars: int,
    predicted_seconds: float,
    target_duration_seconds: int,
    lower_seconds: float,
) -> str:
    """Expansion retry hint. Called when
    ``predicted_seconds < lower`` at first-pass validation.

    Symmetric-ish counterpart to ``_dialogue_over_length_hint``:
    concrete numbers, tactics that add conversational substance
    rather than filler, and a preservation contract."""
    lower_chars = int(round(lower_seconds * _DIALOGUE_CPS))
    lower_seconds_int = int(round(lower_seconds))
    deficit_chars = max(1, lower_chars - total_chars)
    # Same 8-pt offset as compression uses on the ceiling side,
    # applied to the floor. 0.92 below the ceiling ↔ 1.08 above
    # the floor.
    headroom_chars = int(round(
        lower_chars * (2.0 - _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION)
    ))
    headroom_seconds = int(round(headroom_chars / _DIALOGUE_CPS))
    return (
        f"Your dialogue is too short.\n"
        f"\n"
        f"Previous attempt: {total_chars} characters "
        f"(~{predicted_seconds:.0f}s).\n"
        f"Target: {target_duration_seconds}s.\n"
        f"Hard acceptance floor: {lower_chars} characters "
        f"(~{lower_seconds_int}s).\n"
        f"You must add at least {deficit_chars} characters.\n"
        f"\n"
        f"Rewrite the SAME scene to approximately "
        f"{headroom_chars} characters (~{headroom_seconds}s), "
        f"leaving comfortable headroom above the hard floor.\n"
        f"\n"
        f"Expand conversational substance, not padding. You may "
        f"add a beat OR give an existing beat more room:\n"
        f"  * add a challenge, callback, or reveal that a "
        f"character has been holding back;\n"
        f"  * let a reaction land with a specific example instead "
        f"of a general one;\n"
        f"  * open a new question the next speaker earns the "
        f"answer to.\n"
        f"\n"
        f"Do NOT add filler, repeated framing, or generic "
        f"methodology explanation.\n"
        f"\n"
        f"Preserve: character identity; factual grounding; "
        f"conversational causality; and each character's voice."
    )


# ---- Parse + validation ------------------------------------------


def _parse_and_validate(
    raw_json: str,
    *,
    alias_to_teammate: dict[str, "Teammate"],
    target_duration_seconds: int,
    opener: str | None,
) -> tuple[list[DialogueTurn] | None, str | None]:
    """Parse + validate a structured LLM response.

    Returns ``(turns, corrective_hint)``. Exactly one is non-None:

    * ``(turns, None)`` — all validators passed.
    * ``(None, hint)`` — a validator failed; the hint describes
      the defect in operator-visible plain English so it can
      round-trip to the LLM for the ONE corrective resynth.

    Corrective hints intentionally do NOT tell the LLM "you
    said X, produce Y" — they describe the CONSTRAINT that was
    violated so the LLM can re-plan freely. Prescriptive
    hint-based debiasing is out of scope; a bounded retry with
    a descriptive constraint is the whole retry policy.
    """
    if not raw_json or not raw_json.strip():
        return None, "your response was empty; return a JSON object with a `turns` array"

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return None, (
            f"your response was not valid JSON ({exc.msg}); return a "
            f"single JSON object matching the schema in the task"
        )

    if not isinstance(parsed, dict):
        return None, "your response was JSON but not an object; return a JSON object with a `turns` array"

    raw_turns = parsed.get("turns")
    if not isinstance(raw_turns, list) or not raw_turns:
        return None, (
            "your JSON is missing a non-empty `turns` array; every "
            "response must include at least two turns"
        )

    # Structural pass — check each item shape.
    if len(raw_turns) < _HARD_MIN_TURNS:
        return None, (
            f"you returned {len(raw_turns)} turn(s); a dialogue "
            f"scene requires at least {_HARD_MIN_TURNS} turns"
        )

    _, _, hard_max = _turn_band_for(target_duration_seconds)
    if len(raw_turns) > hard_max:
        return None, (
            f"you returned {len(raw_turns)} turns; for a "
            f"{target_duration_seconds}-second scene the maximum "
            f"is {hard_max}. Consolidate into fewer, more "
            f"substantial exchanges"
        )

    seen_indices: set[int] = set()
    normalized: list[dict] = []
    for i, item in enumerate(raw_turns):
        if not isinstance(item, dict):
            return None, (
                f"turn at position {i} is not a JSON object; each "
                "turn must be an object with line_index, "
                "speaker_alias, text"
            )
        li = item.get("line_index")
        alias = item.get("speaker_alias")
        text = item.get("text")
        if not isinstance(li, int):
            return None, (
                f"turn at position {i} has non-integer line_index; "
                "line_index must be an integer starting at 0"
            )
        if li in seen_indices:
            return None, (
                f"duplicate line_index {li}; line_index values "
                "must be 0, 1, 2, ... with no duplicates"
            )
        seen_indices.add(li)
        if not isinstance(alias, str) or not alias.strip():
            return None, (
                f"turn line_index={li} has invalid speaker_alias; "
                "must be one of the cast aliases from the task"
            )
        if not isinstance(text, str) or not text.strip():
            return None, (
                f"turn line_index={li} has empty text; every turn "
                "must have non-empty spoken text"
            )
        text_stripped = text.strip()
        if len(text_stripped) > AVATAR_SPEECH_SAFE_MAX_CHARS:
            return None, (
                f"turn line_index={li} has "
                f"{len(text_stripped)} characters; the per-turn "
                f"maximum is {AVATAR_SPEECH_SAFE_MAX_CHARS}. "
                f"Split into multiple shorter turns"
            )
        normalized.append(
            {
                "line_index": li,
                "speaker_alias": alias.strip().lower(),
                "text": text_stripped,
            }
        )

    # Contiguity — sorted line_index must be 0, 1, ..., N-1.
    sorted_indices = sorted(seen_indices)
    if sorted_indices != list(range(len(normalized))):
        return None, (
            f"line_index values must be exactly 0, 1, 2, ..., "
            f"{len(normalized) - 1} with no gaps. You returned "
            f"{sorted_indices}"
        )

    # Sort turns by line_index for deterministic downstream order.
    normalized.sort(key=lambda t: t["line_index"])

    # Alias resolution — case-insensitive against approved map.
    approved_aliases = {a.lower(): a for a in alias_to_teammate}
    for turn in normalized:
        if turn["speaker_alias"] not in approved_aliases:
            return None, (
                f"turn line_index={turn['line_index']} uses "
                f"unknown speaker_alias {turn['speaker_alias']!r}. "
                f"Approved aliases: "
                f"{sorted(approved_aliases.keys())!r}. Do not "
                f"invent a third speaker"
            )

    # Opener preservation — checked BEFORE duration/count band so
    # a hard-constraint failure (wrong primary, missing opener
    # text) surfaces its actual defect in the corrective hint
    # rather than being masked by a fixable duration/count issue.
    # Existing K6 pinned-opener semantics is "opener appears
    # verbatim as the first sentence" — we check
    # ``turn[0].text.startswith(opener.strip())`` so the model
    # can extend the opener into a longer first turn without
    # failing validation.
    if opener and opener.strip():
        primary_alias = next(iter(alias_to_teammate))
        if normalized[0]["speaker_alias"] != primary_alias:
            return None, (
                f"turn 0 must be spoken by {primary_alias!r} "
                f"(the primary character owns the pinned opener)"
            )
        opener_stripped = opener.strip()
        if not normalized[0]["text"].startswith(opener_stripped):
            return None, (
                f"turn 0 must preserve the pinned opener "
                f"verbatim at its start. Opener was: "
                f"{opener_stripped!r}"
            )

    # Aggregate duration — ±20 % of target using ``_DIALOGUE_CPS``.
    total_chars = sum(len(t["text"]) for t in normalized)
    predicted_seconds = total_chars / _DIALOGUE_CPS if _DIALOGUE_CPS else 0.0
    target = float(target_duration_seconds)
    lower = target * (1.0 - _DURATION_TOLERANCE)
    upper = target * (1.0 + _DURATION_TOLERANCE)
    if predicted_seconds < lower:
        return None, _dialogue_under_length_hint(
            total_chars=total_chars,
            predicted_seconds=predicted_seconds,
            target_duration_seconds=target_duration_seconds,
            lower_seconds=lower,
        )
    if predicted_seconds > upper:
        return None, _dialogue_over_length_hint(
            total_chars=total_chars,
            predicted_seconds=predicted_seconds,
            target_duration_seconds=target_duration_seconds,
            upper_seconds=upper,
        )

    # All validators passed — resolve aliases to Teammate rows and
    # build DialogueTurn objects (verification stays empty here;
    # K6.4 runs in the caller after this returns).
    turns: list[DialogueTurn] = []
    for t in normalized:
        canonical_alias = approved_aliases[t["speaker_alias"]]
        turns.append(
            DialogueTurn(
                line_index=t["line_index"],
                speaker_teammate=alias_to_teammate[canonical_alias],
                speaker_alias=canonical_alias,
                text=t["text"],
            )
        )
    return turns, None


# ---- Mock output -------------------------------------------------


def _mock_result(
    *,
    alias_to_teammate: dict[str, "Teammate"],
    topic: str,
    target_duration_seconds: int,
    opener: str | None,
    per_character_chunks: dict[str, list["KnowledgeChunk"]],
    use_knowledge: bool,
    verifier_mode: str,
) -> DialogueResult:
    """Deterministic valid DialogueResult for mock mode.

    Design goals:

    * No provider calls (OpenAI, K2 embedding, Runway).
    * Passes every post-parse validator including duration
      band + turn count band for the target duration.
    * Includes at least one consecutive-same-speaker pair so
      tests can assert AI mode does NOT force alternation.
    * Preserves opener as turn 0 belonging to cast[0] when
      supplied.
    * Deterministic — same inputs yield the same output
      (safe for test snapshots and cache keys).
    """
    aliases = list(alias_to_teammate.keys())
    primary_alias = aliases[0]
    primary_tm = alias_to_teammate[primary_alias]
    # For 2+ character casts, pick the second cast entry;
    # single-character mock (should not happen in v1) just
    # echoes primary.
    secondary_alias = aliases[1] if len(aliases) > 1 else primary_alias
    secondary_tm = alias_to_teammate[secondary_alias]

    soft_min, soft_max, _ = _turn_band_for(target_duration_seconds)
    aim_turns = max(_HARD_MIN_TURNS, soft_min)
    # Ensure at least 4 turns so the consecutive-same-speaker
    # assertion below has room to exist.
    aim_turns = max(aim_turns, 4)

    # Target chars: hit the middle of the acceptance band.
    target_chars = target_duration_seconds * _DIALOGUE_CPS
    # Distribute chars roughly evenly; one turn gets bumped so
    # each turn is >= 1 char.
    per_turn_chars = max(1, target_chars // aim_turns)

    # Speaker order deliberately includes a consecutive-same-speaker
    # pair: primary, secondary, secondary, primary, primary,
    # secondary, ... Length capped to aim_turns.
    order_template = [
        primary_alias, secondary_alias, secondary_alias, primary_alias,
        primary_alias, secondary_alias,
    ]
    while len(order_template) < aim_turns:
        order_template.append(
            secondary_alias if order_template[-1] == primary_alias
            else primary_alias
        )
    order = order_template[:aim_turns]

    def _mock_line(alias: str, idx: int) -> str:
        # Deterministic filler that includes the alias for
        # visual inspection during test runs.
        name = getattr(alias_to_teammate[alias], "name", "") or alias
        base = f"[mock turn {idx} by {name}] "
        return base + ("x" * max(1, per_turn_chars - len(base)))

    turns: list[DialogueTurn] = []
    for i, alias in enumerate(order):
        text = _mock_line(alias, i)
        if i == 0 and opener and opener.strip():
            # Ensure opener preservation. Prepend verbatim; keep
            # the rest of the mock line so total char count stays
            # in-band. Trim if opener alone exceeds per-turn budget.
            op = opener.strip()
            if len(op) >= per_turn_chars:
                text = op[:AVATAR_SPEECH_SAFE_MAX_CHARS]
            else:
                remainder_len = max(1, per_turn_chars - len(op) - 1)
                text = op + " " + ("x" * remainder_len)
            # Opener forces primary to own turn 0.
            alias = primary_alias
        tm = alias_to_teammate[alias]
        turns.append(
            DialogueTurn(
                line_index=i,
                speaker_teammate=tm,
                speaker_alias=alias,
                text=text,
                verification_status="skipped" if verifier_mode == "off"
                else "verified",
            )
        )

    total_chars = sum(len(t.text) for t in turns)
    per_char_chunks: dict[str, list[str]] = {
        a: [str(getattr(c, "id", "")) for c in per_character_chunks.get(a, [])]
        for a in aliases
    }
    all_chunk_ids: list[str] = []
    seen: set[str] = set()
    for ids in per_char_chunks.values():
        for cid in ids:
            if cid and cid not in seen:
                seen.add(cid)
                all_chunk_ids.append(cid)

    aliases_map = {
        a: getattr(tm, "name", "") or a
        for a, tm in alias_to_teammate.items()
    }

    return DialogueResult(
        turns=turns,
        chunk_ids=all_chunk_ids,
        per_character_chunk_ids=per_char_chunks,
        writing_contract_version=WRITING_CONTRACT_VERSION,
        overall_verification_status=(
            "skipped" if verifier_mode == "off" else "verified"
        ),
        total_chars=total_chars,
        predicted_seconds=total_chars / _DIALOGUE_CPS,
        target_duration_seconds=target_duration_seconds,
        aliases=aliases_map,
        mock_mode=True,
        used_knowledge=use_knowledge and bool(all_chunk_ids),
        model="mock",
        # SESSION 262 — mock branch synthesizes deterministically
        # in one pass; no retry loop, no LLM raw response. Attempt
        # count is 1 so downstream observability distinguishes
        # "mock synthesized" (1) from "synthesis never fired" (0).
        # first_pass_raw carries the JSON-shaped mock output so the
        # audit trail is consistent with real-mode.
        attempt_count=1,
        first_pass_raw=json.dumps({
            "mock": True,
            "turns": [
                {"line_index": t.line_index,
                 "speaker_alias": t.speaker_alias,
                 "text": t.text}
                for t in turns
            ],
        }),
        corrective_hint="",
        corrective_pass_raw="",
    )


# ---- Public API --------------------------------------------------


def synthesize_dialogue(
    *,
    workspace: "Workspace",
    cast: Sequence["Teammate"],
    topic: str,
    target_duration_seconds: int,
    opener: str | None = None,
    use_knowledge: bool = True,
    verifier_mode: str = "warn",
    mock_mode: bool = False,
) -> DialogueResult:
    """Synthesize a multi-character dialogue scene.

    Returns a validated :class:`DialogueResult` whose ``turns``
    are ready to hydrate the existing ``dialogue_scene``
    starter's ``lines = [{spokesperson_id, text}, ...]`` shape.

    Args:
        workspace: the workspace owning the composition. Used
            for cross-workspace cast validation.
        cast: ordered sequence of Teammates. v1 callers pass 2;
            the interface accepts N so future N-cast expansion
            doesn't require signature change. All cast members
            must belong to ``workspace``.
        topic: one-sentence operator brief.
        target_duration_seconds: aggregate scene runtime target
            (not per-character). Acceptance band is ±20 %.
        opener: optional pinned first line belonging to
            ``cast[0]``. Included as a hard synthesis constraint
            in the prompt and verified post-parse.
        use_knowledge: when True, run K2 retrieval per character
            and build per-character factual corpora. When False,
            skip retrieval; the writer relies on Character Voice
            + identity fields only for grounding.
        verifier_mode: ``"warn"`` (default) | ``"strict"`` |
            ``"off"``. Passed through to K6.4 per-turn.
        mock_mode: when True (or when the
            ``DIALOGUE_SYNTHESIS_FORCE_MOCK`` env / settings
            flag is set), skip OpenAI + K2 provider calls and
            return a deterministic valid stub result.

    Raises:
        DialogueSynthesisError: cast too small, cross-workspace
            member, empty topic, both synthesis passes failed
            validation.
        ClaimVerifierError: strict-mode K6.4 rejection on any
            turn.
    """
    if len(cast) < 2:
        raise DialogueSynthesisError(
            f"dialogue scene requires at least 2 cast members; got {len(cast)}"
        )

    # Cross-workspace guard — matches the existing manual
    # dialogue_scene resolver's atomic-or-bust behavior.
    ws_id = getattr(workspace, "id", None)
    for tm in cast:
        tm_ws_id = getattr(getattr(tm, "workspace", None), "id", None)
        if tm_ws_id != ws_id:
            raise DialogueSynthesisError(
                f"cast member {getattr(tm, 'name', '<unknown>')!r} does "
                f"not belong to the specified workspace"
            )

    if not (topic or "").strip():
        raise DialogueSynthesisError("topic must be non-empty")

    alias_to_teammate = build_alias_map(cast)
    resolved_verifier_mode = (verifier_mode or "warn").lower()
    if resolved_verifier_mode not in {"warn", "strict", "off"}:
        resolved_verifier_mode = "warn"

    # ---- Retrieval ---------------------------------------------
    #
    # Run per-character even in mock mode isn't necessary — mock
    # is meant to avoid provider hops. We honor the same pattern
    # as script_synthesis.py: mock skips retrieval AND skips the
    # OpenAI call in one branch. Real mode with use_knowledge=False
    # still skips retrieval but calls the LLM (Character Voice +
    # identity fields form the grounding).
    per_character_chunks: dict[str, list["KnowledgeChunk"]] = {
        alias: [] for alias in alias_to_teammate
    }
    # SESSION 263 Slice B — the Universe canon lane. Populated
    # once per synthesis (not per character). Empty when the
    # dialogue is Universe-less, when knowledge is disabled, or
    # when no shared-tier canon exists.
    shared_chunks: list["KnowledgeChunk"] = []
    # SESSION 264 Slice 2 — narrative-memory lane. Populated
    # once per synthesis. Never overlaps with shared_chunks
    # (canon is a KnowledgeChunk; memory is a NarrativeMemory —
    # different tables, different retrieval functions). Empty
    # when Universe-less, knowledge disabled, or no active +
    # embedded operator-promoted memories match the visibility
    # predicate.
    memory_rows: list = []  # list[NarrativeMemory]

    force_mock = mock_mode or _is_force_mock()

    if not force_mock and use_knowledge:
        # Lazy import — retrieval touches embeddings + Django ORM.
        from apps.embeddings.retrieval import (
            retrieve_for_teammate,
            retrieve_universe_canon,
            retrieve_universe_memory,
        )
        for alias, tm in alias_to_teammate.items():
            try:
                per_character_chunks[alias] = list(
                    retrieve_for_teammate(tm, topic, top_k=5)
                )
            except Exception as exc:
                # K2 retrieval failure is not fatal — degrade to
                # identity-fields-only grounding. Same posture as
                # script_synthesis (Q-k-* series).
                logger.warning(
                    "dialogue_synthesis: retrieve_for_teammate "
                    "failed for %s (%s); proceeding without chunks",
                    alias, exc,
                )
                per_character_chunks[alias] = []

        # SESSION 263 Slice B — one canon-lane call per synthesis.
        # Universe derived from the cast (all cast members share
        # a Universe by workspace guard; taking cast[0] is safe).
        # A legacy universe-less cast yields empty canon (the
        # retrieval function returns [] on universe=None).
        canon_universe = getattr(cast[0], "universe", None)
        if canon_universe is not None:
            try:
                shared_chunks = list(
                    retrieve_universe_canon(
                        workspace, canon_universe, cast, topic, top_k=2,
                    )
                )
            except Exception as exc:
                # Canon-lane failure is non-fatal — degrade to
                # per-character retrieval only. Same posture as
                # per-character retrieval above.
                logger.warning(
                    "dialogue_synthesis: retrieve_universe_canon "
                    "failed workspace=%s universe=%s (%s); "
                    "proceeding without shared canon",
                    getattr(workspace, "id", None),
                    getattr(canon_universe, "id", None),
                    exc,
                )
                shared_chunks = []

            # SESSION 264 Slice 2 — one memory-lane call per synthesis.
            # top_k=1 fixed for v1 per the Slice 2 brief. Same
            # non-fatal degradation posture.
            try:
                memory_rows = list(
                    retrieve_universe_memory(
                        workspace, canon_universe, cast, topic, top_k=1,
                    )
                )
            except Exception as exc:
                logger.warning(
                    "dialogue_synthesis: retrieve_universe_memory "
                    "failed workspace=%s universe=%s (%s); "
                    "proceeding without narrative memory",
                    getattr(workspace, "id", None),
                    getattr(canon_universe, "id", None),
                    exc,
                )
                memory_rows = []

    # ---- Mock branch --------------------------------------------
    if force_mock:
        # Canon lane stays empty for mock (no provider hops); the
        # mock result path preserves the pre-SESSION-263 shape.
        return _mock_result(
            alias_to_teammate=alias_to_teammate,
            topic=topic,
            target_duration_seconds=target_duration_seconds,
            opener=opener,
            per_character_chunks=per_character_chunks,
            use_knowledge=use_knowledge,
            verifier_mode=resolved_verifier_mode,
        )

    # ---- Real mode requires OPENAI_API_KEY ---------------------
    if not _has_openai_key():
        raise DialogueSynthesisError(
            "OPENAI_API_KEY is not set; either provide a key or run "
            "with mock_mode=True / DIALOGUE_SYNTHESIS_FORCE_MOCK"
        )

    cast_labels = [
        (alias, tm, per_character_chunks[alias])
        for alias, tm in alias_to_teammate.items()
    ]

    system_prompt = _assemble_system_prompt(
        cast_labels=cast_labels,
        alias_to_teammate=alias_to_teammate,
        use_knowledge=use_knowledge,
        shared_chunks=shared_chunks,
        memory_rows=memory_rows,
    )

    # ---- First pass ---------------------------------------------
    raw_json, tokens_in_1, tokens_out_1 = _call_dialogue_api(
        system_prompt=system_prompt,
        task_message=_build_task_section(
            topic=topic,
            target_duration_seconds=target_duration_seconds,
            alias_to_teammate=alias_to_teammate,
            opener=opener,
            corrective_hint=None,
        ),
    )
    turns, corrective_hint = _parse_and_validate(
        raw_json,
        alias_to_teammate=alias_to_teammate,
        target_duration_seconds=target_duration_seconds,
        opener=opener,
    )

    tokens_in_total = tokens_in_1
    tokens_out_total = tokens_out_1
    final_raw = raw_json
    # SESSION 262 — freeze the first-pass response verbatim for
    # observability. `final_raw` may be overwritten by the retry;
    # this copy never is.
    first_pass_raw_persisted = raw_json
    corrective_hint_persisted = ""
    corrective_pass_raw_persisted = ""
    attempt_count = 1

    # ---- One bounded corrective resynth -------------------------
    if turns is None:
        assert corrective_hint is not None  # invariant
        logger.info(
            "dialogue_synthesis: first pass failed validation; "
            "attempting one corrective resynth. hint=%r",
            corrective_hint[:160],
        )
        # SESSION 262 — freeze the hint the retry actually received.
        corrective_hint_persisted = corrective_hint
        raw_json_2, tokens_in_2, tokens_out_2 = _call_dialogue_api(
            system_prompt=system_prompt,
            task_message=_build_task_section(
                topic=topic,
                target_duration_seconds=target_duration_seconds,
                alias_to_teammate=alias_to_teammate,
                opener=opener,
                corrective_hint=corrective_hint,
            ),
        )
        tokens_in_total += tokens_in_2
        tokens_out_total += tokens_out_2
        corrective_pass_raw_persisted = raw_json_2
        attempt_count = 2
        turns_2, hint_2 = _parse_and_validate(
            raw_json_2,
            alias_to_teammate=alias_to_teammate,
            target_duration_seconds=target_duration_seconds,
            opener=opener,
        )
        if turns_2 is None:
            # Both passes failed — reject. Persist the LATER raw
            # response so the operator can inspect the closer-to-
            # correct attempt.
            # SESSION 262 — also carry per-attempt provenance +
            # retrieval snapshot for the FAILED-composition rescue.
            # Predicted seconds is estimated from the LATER raw
            # response's total char count if parseable, else None.
            # SESSION 263 — the retrieval snapshot includes shared
            # canon chunk IDs alongside per-character chunk IDs
            # so the FAILED-composition rescue records the same
            # provenance the accepted path would have persisted.
            _predicted = _estimate_predicted_seconds_from_raw(raw_json_2)
            _chunk_ids_snapshot: list[str] = []
            _seen_ids: set[str] = set()
            for _c in shared_chunks:
                _cid = str(getattr(_c, "id", "") or "")
                if _cid and _cid not in _seen_ids:
                    _seen_ids.add(_cid)
                    _chunk_ids_snapshot.append(_cid)
            for _alias in alias_to_teammate:
                for _c in per_character_chunks[_alias]:
                    _cid = str(getattr(_c, "id", "") or "")
                    if _cid and _cid not in _seen_ids:
                        _seen_ids.add(_cid)
                        _chunk_ids_snapshot.append(_cid)
            # SESSION 264 Slice 2 — parallel snapshot for narrative
            # memory. Kept in its own list because memory IDs are
            # NarrativeMemory UUIDs, not KnowledgeChunk UUIDs.
            _memory_ids_snapshot: list[str] = []
            _seen_memory_ids: set[str] = set()
            for _m in memory_rows:
                _mid = str(getattr(_m, "id", "") or "")
                if _mid and _mid not in _seen_memory_ids:
                    _seen_memory_ids.add(_mid)
                    _memory_ids_snapshot.append(_mid)
            raise DialogueSynthesisError(
                f"dialogue synthesis rejected after one corrective "
                f"pass: {hint_2}",
                raw_llm_json=raw_json_2 or raw_json or "",
                first_pass_raw=first_pass_raw_persisted,
                corrective_hint=corrective_hint_persisted,
                corrective_pass_raw=corrective_pass_raw_persisted,
                attempt_count=attempt_count,
                predicted_seconds=_predicted,
                chunk_ids=_chunk_ids_snapshot,
                memory_ids=_memory_ids_snapshot,
            )
        turns = turns_2
        final_raw = raw_json_2

    # ---- Per-turn K6.4 verification -----------------------------
    #
    # Rule 7 — each turn verifies against the SPEAKING
    # character's corpus + vocabulary only. Do NOT merge
    # per-character corpora across speakers.
    #
    # SESSION 263 Slice B — shared canon (the SHARED §1 block)
    # IS legitimately visible to every cast member by scope
    # (Universe-broadcast OR M2M covers every cast member); it
    # participates in each speaker's factual corpus so a canon-
    # cited fact spoken by either character passes K6.4. This
    # does NOT merge per-character K2 across speakers.
    #
    # SESSION 264 Slice 2 — narrative memory participates on the
    # same "visible to every eligible speaker" footing. The
    # retrieval predicate already filtered by witness overlap;
    # each row surfaced here is eligible for every speaker in the
    # current cast that overlaps its witness set. We adapt each
    # NarrativeMemory to a chunk_text-shaped duck so
    # ``build_factual_corpus`` (which reads ``chunk_text``) works
    # unchanged. Weight: canon still wins on conflict — enforced
    # by the prompt's precedence rules + memory block wording.
    from types import SimpleNamespace as _NS
    memory_corpus_chunks = [
        _NS(chunk_text=(getattr(m, "body", "") or "").strip())
        for m in memory_rows
        if (getattr(m, "body", "") or "").strip()
    ]

    corpus_by_alias: dict[str, str] = {}
    vocab_by_alias: dict[str, list[str]] = {}
    for alias, tm in alias_to_teammate.items():
        combined_chunks = (
            list(shared_chunks)
            + list(memory_corpus_chunks)
            + list(per_character_chunks[alias])
        )
        corpus_by_alias[alias] = build_factual_corpus(
            combined_chunks, spokesperson=tm,
        )
        vocab_by_alias[alias] = build_allowed_vocabulary(spokesperson=tm)

    overall_status = "verified"
    if resolved_verifier_mode == "off":
        overall_status = "skipped"

    for turn in turns:
        if resolved_verifier_mode == "off":
            turn.verification_status = "skipped"
            continue
        try:
            warnings = run_verifier(
                turn.text,
                factual_corpus=corpus_by_alias[turn.speaker_alias],
                allowed_vocabulary=vocab_by_alias[turn.speaker_alias],
                mode=resolved_verifier_mode,
            )
        except ClaimVerifierError:
            # Strict-mode failure — bubble up. Caller (recipe
            # resolver in AI-D3) persists the raw JSON to
            # rejected_synthesis; this module attaches it via
            # exception chaining for context.
            turn.verification_status = "rejected"
            overall_status = "rejected"
            raise
        if warnings:
            turn.verification_warnings = [w.to_dict() for w in warnings]
            turn.verification_status = "warned"
            if overall_status == "verified":
                overall_status = "warned"
        else:
            turn.verification_status = "verified"

    # ---- Aggregate metadata -------------------------------------
    total_chars = sum(len(t.text) for t in turns)
    predicted_seconds = total_chars / _DIALOGUE_CPS

    per_char_chunk_ids: dict[str, list[str]] = {}
    all_ids: list[str] = []
    seen_ids: set[str] = set()
    # SESSION 263 Slice B — shared canon chunk IDs land first in
    # the aggregate ``knowledge_chunk_ids`` list so downstream
    # provenance panels can identify canon by ordering. Deduped
    # against the same seen-set that guards per-character IDs.
    #
    # SESSION 264 Slice 2 — narrative-memory IDs do NOT enter
    # ``knowledge_chunk_ids``. They land on the separate
    # ``memory_ids`` list because they resolve to
    # ``NarrativeMemory`` rows, not ``KnowledgeChunk`` rows.
    # See ``docs/design/EPISODIC_CONTINUITY_CANON_PROMOTION_AUDIT_SESSION_264.md``
    # Slice 2 addendum — observability decision.
    for c in shared_chunks:
        cid = str(getattr(c, "id", "") or "")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            all_ids.append(cid)
    for alias in alias_to_teammate:
        ids = [str(getattr(c, "id", "") or "") for c in per_character_chunks[alias]]
        ids = [i for i in ids if i]
        per_char_chunk_ids[alias] = ids
        for i in ids:
            if i not in seen_ids:
                seen_ids.add(i)
                all_ids.append(i)

    # Memory provenance — separate lane, separate list.
    memory_ids_out: list[str] = []
    seen_memory_ids: set[str] = set()
    for m in memory_rows:
        mid = str(getattr(m, "id", "") or "")
        if mid and mid not in seen_memory_ids:
            seen_memory_ids.add(mid)
            memory_ids_out.append(mid)

    aliases_map = {
        a: getattr(tm, "name", "") or a
        for a, tm in alias_to_teammate.items()
    }

    return DialogueResult(
        turns=turns,
        chunk_ids=all_ids,
        per_character_chunk_ids=per_char_chunk_ids,
        memory_ids=memory_ids_out,
        writing_contract_version=WRITING_CONTRACT_VERSION,
        overall_verification_status=overall_status,
        total_chars=total_chars,
        predicted_seconds=predicted_seconds,
        target_duration_seconds=target_duration_seconds,
        aliases=aliases_map,
        mock_mode=False,
        used_knowledge=use_knowledge and (bool(all_ids) or bool(memory_ids_out)),
        model=DIALOGUE_MODEL,
        tokens_input=tokens_in_total,
        tokens_output=tokens_out_total,
        raw_llm_json=final_raw,
        # SESSION 262 — per-attempt provenance for Composition
        # observability. See DialogueResult docstring.
        attempt_count=attempt_count,
        first_pass_raw=first_pass_raw_persisted,
        corrective_hint=corrective_hint_persisted,
        corrective_pass_raw=corrective_pass_raw_persisted,
    )


def _estimate_predicted_seconds_from_raw(raw_json: str) -> float | None:
    """Best-effort predicted-seconds estimate from a raw LLM response.
    Called on the DialogueSynthesisError path so
    ``Composition.synthesis_predicted_seconds`` can be populated even
    for the rejected case. Returns ``None`` when the raw response is
    not parseable — the caller then persists ``NULL``, correctly
    signalling "prediction unavailable" rather than an invented zero.
    """
    if not raw_json or not raw_json.strip():
        return None
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    turns = parsed.get("turns")
    if not isinstance(turns, list):
        return None
    total_chars = 0
    for t in turns:
        if isinstance(t, dict):
            text = t.get("text") or ""
            if isinstance(text, str):
                total_chars += len(text.strip())
    if total_chars == 0 or not _DIALOGUE_CPS:
        return None
    return total_chars / _DIALOGUE_CPS


def _call_dialogue_api(
    *,
    system_prompt: str,
    task_message: str,
) -> tuple[str, int, int]:
    """Single Responses-API call with JSON-object output.
    Returns ``(raw_text, tokens_input, tokens_output)``.

    Same shape as ``transcript_miner._call_openai`` and
    ``script_synthesis._call_responses_api``. Uses the
    ``text={"format": {"type": "json_object"}}`` argument to
    force structured output.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.responses.create(
        model=DIALOGUE_MODEL,
        input=f"{system_prompt}\n\nUser: {task_message}",
        max_output_tokens=_MAX_OUTPUT_TOKENS,
        reasoning={"effort": _REASONING_EFFORT},
        text={"format": {"type": "json_object"}},
    )
    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


__all__ = [
    "DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER",
    "DialogueResult",
    "DialogueSynthesisError",
    "DialogueTurn",
    "build_alias_map",
    "synthesize_dialogue",
]
