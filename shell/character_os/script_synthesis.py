"""Render-time script synthesis — knowledge → render brief.

SESSION 139 / K6. The piece that makes spokespeople *informed*:
takes the operator's typed brief, runs RAG against the
spokesperson's visible knowledge (via the K2 retrieval
surface), and synthesizes a paragraph-length brief the
media-engine will send to Runway as the script.

Three operating modes:

* **Force-mock** (``RENDER_SCRIPT_FORCE_MOCK=1`` env or
  ``settings.RENDER_SCRIPT_FORCE_MOCK=True``): returns a
  deterministic, no-API-call brief. Same shape as
  ``RUNWAY_FORCE_MOCK`` / ``EMBEDDING_FORCE_MOCK``. Used by
  tests + by local dev workflows that don't want to burn
  OpenAI credits.

* **Empty knowledge** (no chunks visible to the spokesperson):
  graceful degradation per scope-lock contract rule 6 —
  return the operator prompt verbatim, no LLM call, no
  citations. Render still works; it just runs on the
  pre-K6 path.

* **Real mode** (knowledge visible + ``OPENAI_API_KEY`` set):
  one chat-completion against ``gpt-5-mini`` via the
  Responses API (NOT chat-completions — gpt-4o-mini is
  deprecating; gpt-5 family uses ``responses.create``).
  Returns the synthesized script string + citation ids.

Failure of the LLM call falls back to the empty-knowledge
path: log the error, return the operator prompt + empty
citation list. The render keeps working; an alert can
investigate the underlying failure asynchronously.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.conf import settings

from apps.embeddings.retrieval import retrieve_for_teammate
from character_os.writing_contract import (
    WRITING_CONTRACT_VERSION,
    WritingContract,
    merged_avoid_phrases,
)

if TYPE_CHECKING:
    from apps.spokespeople.models import Teammate

logger = logging.getLogger(__name__)


# SESSION 171 — promoted from gpt-5-mini to gpt-5 (full).
#
# Rationale: the K6.6.1 leak fix tightened the system prompt against
# self-introduction, but gpt-5-mini still produced "I'm Marcus, your
# AP Roman tutor…" — classic LLM failure mode where negative
# instructions ("Do NOT introduce yourself") get overridden by
# strong positive patterns in the brief (Marcus's brief contains a
# literal quoted opener + role description). Bigger model follows
# negative instructions more reliably.
#
# Cost: ~$0.0002 → ~$0.001 per render (~5x). Absolute cost still
# rounding error compared to Runway spend per video. Mini is kept
# for structured-output call sites (split_script, transcription
# hook picker) where capability gain doesn't justify the cost.
#
# Responses API only (NOT chat-completions — same calibration that
# pinned us to gpt-5 family; see internal feedback note on the
# OpenAI GPT-5 Responses API for the calibration record).
SCRIPT_MODEL = "gpt-5"

# SESSION 171 — raised from 500 to 2000.
#
# ``max_output_tokens`` on the Responses API counts BOTH reasoning
# tokens AND actual output tokens against the same cap. With
# ``reasoning_effort="medium"`` on gpt-5, a complex K6 prompt burns
# 400-1000+ reasoning tokens before producing visible output. The
# old 500 cap caused gpt-5 to silently hit the cap mid-reasoning,
# return empty ``output_text``, and fall back to the operator
# prompt — looked like K6 had degraded when in fact the model
# was just out of budget. 2000 covers worst-case medium-reasoning +
# 60-100 word script + headroom. Unused tokens cost nothing.
MAX_OUTPUT_TOKENS = 2000

# SESSION 251 — long-form shape has a bigger output budget because a
# 5-minute script (~660 words ≈ ~880 output tokens) plus medium-
# reasoning overhead can exceed the standalone 2000-token cap.
# Actual per-call budget scales with the requested duration; this is
# the floor. See ``_max_output_tokens_for_shape``.
MAX_OUTPUT_TOKENS_LONG_FORM_FLOOR = 4000

# SESSION 171 — kept at 'low' after a brief experiment with 'medium'.
# On gpt-5, ``reasoning_effort="medium"`` expanded to consume the
# full ``max_output_tokens`` budget on reasoning alone (1984 of
# 2000 tokens — zero visible output) before terminating. The
# capability gain over 'low' is real but the practical effect on
# this workload was empty responses falling back to the operator
# prompt. The leak-suppression bet rides on gpt-5's capability
# alone at 'low' effort.
REASONING_EFFORT = "low"

# How many chunks to retrieve. Top-5 fits comfortably inside the
# input context budget even for verbose chunks.
DEFAULT_TOP_K = 5

# SESSION 251 — canonical speaking-rate assumption for word-budget
# derivation, ~11 chars/sec × ~5 chars/word ≈ 132 words/minute.
# Mirrors ``apps.compositions.starters._AVATAR_SPEECH_CHARS_PER_SECOND``
# — both must move together (they're the same real-world quantity
# expressed two ways). Long-form callers pass ``target_duration_seconds``
# and we derive ``target_words = duration * WORDS_PER_SECOND``.
WORDS_PER_SECOND = 132 / 60  # ≈ 2.2 words/sec

# Long-form validation tolerance. Callers accept anything inside
# [target * (1 - LONG_FORM_TOLERANCE), target * (1 + LONG_FORM_TOLERANCE)].
# 0.20 = ±20%; wider than TTS pace variation but tight enough that a
# 5-minute request can't silently ship a 2-minute script.
LONG_FORM_TOLERANCE = 0.20


def word_budget_for_duration(target_duration_seconds: int) -> tuple[int, int, int]:
    """Return ``(target_words, min_words, max_words)`` for a
    long-form duration request. Uses ``WORDS_PER_SECOND`` and
    ``LONG_FORM_TOLERANCE``. Single source of truth so caller,
    prompt builder, and validator all agree on the math.

    Word guidance is secondary to character guidance (below).
    Words is a lossy proxy — 300 words at 5 chars/word and 300
    words at 7 chars/word estimate very different durations
    under the canonical char/sec rate. Prompts include BOTH
    budgets; the final accept/reject gate uses the character
    estimator only.
    """
    target = max(1, round(target_duration_seconds * WORDS_PER_SECOND))
    low = max(1, round(target * (1 - LONG_FORM_TOLERANCE)))
    high = max(low + 1, round(target * (1 + LONG_FORM_TOLERANCE)))
    return target, low, high


def char_budget_for_duration(
    target_duration_seconds: int,
    chars_per_second: int | None = None,
) -> tuple[int, int, int]:
    """Return ``(ideal_chars, min_chars, max_chars)`` for a
    long-form duration request. Uses the canonical
    ``_AVATAR_SPEECH_CHARS_PER_SECOND`` from
    ``apps.compositions.starters`` (default 11) — same source of
    truth as the acceptance gate ``_estimate_avatar_speech_seconds``.

    LOAD-BEARING for the "compression correction" contract: the
    writer needs a concrete character ceiling to rewrite below,
    not just prose asking it to "compress." A hint that reads
    "rewrite below 1584 characters" produces materially different
    output than "please compress."
    """
    if chars_per_second is None:
        # Local import to avoid a top-level circular reference
        # (starters imports script_synthesis).
        from apps.compositions.starters import _AVATAR_SPEECH_CHARS_PER_SECOND
        chars_per_second = _AVATAR_SPEECH_CHARS_PER_SECOND
    ideal = max(1, target_duration_seconds * chars_per_second)
    low = max(1, round(ideal * (1 - LONG_FORM_TOLERANCE)))
    high = max(low + 1, round(ideal * (1 + LONG_FORM_TOLERANCE)))
    return ideal, low, high


def _max_output_tokens_for_shape(
    shape: str,
    target_duration_seconds: int | None,
) -> int:
    """Long-form calls need a larger token budget than standalone.
    ~1.3 tokens/word + reasoning overhead + headroom."""
    if shape == "long_form" and target_duration_seconds:
        target_words, _, _ = word_budget_for_duration(target_duration_seconds)
        needed = int(target_words * 1.5) + 1500  # reasoning + headroom
        return max(MAX_OUTPUT_TOKENS_LONG_FORM_FLOOR, needed)
    return MAX_OUTPUT_TOKENS


@dataclass(slots=True)
class ScriptResult:
    """What ``build_render_brief`` returns.

    * ``used_knowledge`` — real synthesis ran vs degraded path.
    * ``chunk_ids`` — retrieved K2 chunk ids for provenance.
    * ``verification_warnings`` — K6.4 unsupported claims.
    * ``verification_status`` — ``rejected|verified|skipped|
      trusted_passthrough`` (see
      ``apps.compositions.models.VerificationStatus``).
    * ``writing_contract_version`` (SESSION 253) — which version
      of ``character_os.writing_contract`` shaped this
      synthesis's system prompt. 0 on the degraded / passthrough
      paths (no contract was applied); ``WRITING_CONTRACT_VERSION``
      when synthesis actually ran. Callers persist onto
      ``Composition.writing_contract_version``.
    """
    brief: str
    chunk_ids: list[str] = field(default_factory=list)
    used_knowledge: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    verification_warnings: list[dict] = field(default_factory=list)
    verification_status: str = ""
    writing_contract_version: int = 0


def _is_force_mock() -> bool:
    """Settings beats env (same pattern as
    ``apps.embeddings.embedding_service._is_force_mock``)."""
    settings_flag = getattr(settings, "RENDER_SCRIPT_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("RENDER_SCRIPT_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def build_render_brief(
    spokesperson: "Teammate",
    operator_prompt: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    verifier_mode: str | None = None,
    opener: str | None = None,
    target_shape: str = "standalone",
    target_duration_seconds: int | None = None,
    corrective_hint: str | None = None,
) -> ScriptResult:
    """Build the brief that gets sent to media-engine.

    Args:
        spokesperson: who's speaking. Their workspace + M2M
            visibility drive the retrieval scope.
        operator_prompt: what the operator typed. Doubles as
            the RAG query and as the rendering topic.
        top_k: how many knowledge chunks to consider.
        verifier_mode: K6.4 v1.1 — optional per-render
            override for the verifier mode. ``"strict" |
            "warn" | "off"``. ``None`` (default) falls back
            to ``settings.K6_CLAIM_VERIFIER_MODE`` and then
            ``"warn"``. Lets operators flip per-render from
            the SPA without restarting Django.
        target_shape: SESSION 251. ``"standalone"`` (default,
            unchanged) → 60-100 word single-claim script for
            short talking heads. ``"long_form"`` → multi-beat
            narrative script sized to ``target_duration_seconds``.
            Every existing caller stays on the default; long-form
            callers (``long_form_ad`` starter) opt in.
        target_duration_seconds: SESSION 251. Required when
            ``target_shape="long_form"``. Drives the word budget
            interpolated into the system prompt. Raises
            ``ValueError`` if omitted with a long_form shape —
            no silent fallback to short-form length.
        corrective_hint: SESSION 251. Optional feedback string
            appended to the user prompt. Long-form callers use
            this to request one bounded expansion or compression
            retry when the first synthesis is materially outside
            tolerance. Standalone shape ignores it.

    Returns:
        ``ScriptResult`` — always has a usable ``brief`` field
        (never raises). ``used_knowledge`` reports whether
        synthesis actually ran or fell through to degradation.

    Raises:
        ``ValueError`` — ``target_shape="long_form"`` without
        a ``target_duration_seconds``.
    """
    if target_shape not in ("standalone", "long_form"):
        raise ValueError(
            f"target_shape must be 'standalone' or 'long_form', got {target_shape!r}"
        )
    if target_shape == "long_form" and not target_duration_seconds:
        raise ValueError(
            "target_shape='long_form' requires target_duration_seconds "
            "(long-form callers must specify their duration; there is "
            "no silent short-form fallback)"
        )

    operator_prompt = (operator_prompt or "").strip()
    fallback_brief = operator_prompt or (spokesperson.business_brief or "").strip()

    # Force-mock: no retrieval, no LLM. Deterministic shape that
    # tests can assert against. v1.2 — no synthesis means
    # trusted_passthrough.
    if _is_force_mock():
        chunks = retrieve_for_teammate(
            spokesperson, query=operator_prompt or spokesperson.name, top_k=top_k,
        )
        chunk_ids = [str(c.id) for c in chunks]
        return ScriptResult(
            brief=_mock_brief(spokesperson, operator_prompt, chunk_ids),
            chunk_ids=chunk_ids,
            used_knowledge=bool(chunk_ids),
            model=f"{SCRIPT_MODEL} (mock)",
            verification_status="trusted_passthrough",
        )

    # Real mode — first retrieve. Even if retrieval fails for
    # some weird reason, we degrade.
    try:
        chunks = retrieve_for_teammate(
            spokesperson, query=operator_prompt or spokesperson.name, top_k=top_k,
        )
    except Exception:
        logger.exception(
            "retrieve_for_teammate failed sp=%s — degrading to operator prompt",
            spokesperson.pk,
        )
        return ScriptResult(
            brief=fallback_brief,
            verification_status="trusted_passthrough",
        )

    if not chunks:
        # Contract rule 6 — graceful degradation. No knowledge,
        # no synthesis, original brief flows through.
        return ScriptResult(
            brief=fallback_brief,
            verification_status="trusted_passthrough",
        )

    if not _has_openai_key():
        # Real mode requested (force-mock not set) but no key.
        # Same shape as the embedding service — raising here
        # would fail the render; degrading is the better UX.
        logger.warning(
            "build_render_brief: knowledge visible but OPENAI_API_KEY "
            "unset — degrading to operator prompt (set "
            "RENDER_SCRIPT_FORCE_MOCK=1 for dev determinism)"
        )
        return ScriptResult(
            brief=fallback_brief,
            chunk_ids=[str(c.id) for c in chunks],
            verification_status="trusted_passthrough",
        )

    try:
        synthesised, tokens_in, tokens_out = _call_responses_api(
            spokesperson, operator_prompt, chunks,
            opener=opener,
            target_shape=target_shape,
            target_duration_seconds=target_duration_seconds,
            corrective_hint=corrective_hint,
        )
    except Exception:
        logger.exception(
            "OpenAI responses.create failed sp=%s chunks=%d — degrading",
            spokesperson.pk, len(chunks),
        )
        return ScriptResult(
            brief=fallback_brief,
            chunk_ids=[str(c.id) for c in chunks],
            verification_status="trusted_passthrough",
        )

    final_brief = synthesised.strip() or fallback_brief

    # K6.4 — post-synthesis claim verifier. SESSION 253 split:
    # factual_corpus (evidence capable of supporting a claim) is
    # distinct from allowed_vocabulary (entities allowed to appear
    # without triggering a warning but which do NOT license the
    # surrounding claim as factual). Operator prompt is NOT in
    # factual_corpus — the creative brief may itself contain
    # unsupported assertions.
    from character_os.claim_verifier import (
        _get_default_mode,
        build_allowed_vocabulary,
        build_factual_corpus,
        run_verifier,
    )

    factual_corpus = build_factual_corpus(chunks, spokesperson=spokesperson)
    allowed_vocabulary = build_allowed_vocabulary(spokesperson=spokesperson)

    resolved_mode = (verifier_mode or _get_default_mode()).lower()
    unsupported = run_verifier(
        final_brief,
        factual_corpus=factual_corpus,
        allowed_vocabulary=allowed_vocabulary,
        mode=verifier_mode,
    )
    if unsupported:
        logger.warning(
            "K6.4 verifier flagged %d unsupported claim(s) on sp=%s: %s",
            len(unsupported),
            spokesperson.pk,
            ", ".join(f"{u.claim!r}" for u in unsupported),
        )

    status = "skipped" if resolved_mode == "off" else "verified"

    return ScriptResult(
        brief=final_brief,
        chunk_ids=[str(c.id) for c in chunks],
        used_knowledge=True,
        model=SCRIPT_MODEL,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        verification_warnings=[u.to_dict() for u in unsupported],
        verification_status=status,
        writing_contract_version=WRITING_CONTRACT_VERSION,
    )


# ---- LLM call --------------------------------------------------


def _call_responses_api(
    spokesperson: "Teammate",
    operator_prompt: str,
    chunks: list,
    *,
    opener: str | None = None,
    target_shape: str = "standalone",
    target_duration_seconds: int | None = None,
    corrective_hint: str | None = None,
) -> tuple[str, int, int]:
    """Single Responses-API call. Returns ``(text, tokens_in,
    tokens_out)``. Raises on API error — caller handles
    degradation.

    SESSION 253 — assembled prompt structure:

        System = §1 Factual Basis (chunks + factual fields)
                 §2 Character Voice
                 §3 Brand Voice
                 §4 Writing Contract (shape-specific)
                 Precedence rules
        User   = §5 Task (topic + hard constraints)
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    system = _assemble_system_prompt(
        spokesperson,
        chunks=chunks,
        target_shape=target_shape,
        target_duration_seconds=target_duration_seconds,
    )
    user = _assemble_task_message(
        operator_prompt=operator_prompt,
        opener=opener,
        corrective_hint=corrective_hint,
    )

    response = client.responses.create(
        model=SCRIPT_MODEL,
        input=f"{system}\n\nUser: {user}",
        max_output_tokens=_max_output_tokens_for_shape(
            target_shape, target_duration_seconds,
        ),
        reasoning={"effort": REASONING_EFFORT},
    )

    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _assemble_system_prompt(
    spokesperson: "Teammate",
    *,
    chunks: list,
    target_shape: str = "standalone",
    target_duration_seconds: int | None = None,
) -> str:
    """SESSION 253 — assemble the 5-section system prompt.

    Sections are labeled and separated. Each section has one
    role and one rule. The precedence rules at the bottom tell
    the model how to resolve conflicts.
    """
    sections: list[str] = [
        _build_factual_basis_section(spokesperson, chunks=chunks),
        _build_character_voice_section(spokesperson),
        _build_brand_voice_section(spokesperson),
        _build_writing_contract_section(
            target_shape=target_shape,
            target_duration_seconds=target_duration_seconds,
        ),
        _PRECEDENCE_RULES,
    ]
    return "\n\n".join(s for s in sections if s)


def _assemble_task_message(
    *,
    operator_prompt: str,
    opener: str | None = None,
    corrective_hint: str | None = None,
) -> str:
    """SESSION 253 — assemble §5 Task (user message).

    Splits into topic vs. hard constraints so the model can
    honor pinned openers / corrective hints as overrides on
    Character-Voice and Writing-Contract preferences without
    breaking Factual Basis or Brand Voice.
    """
    parts: list[str] = ["=== SECTION 5 — TASK ==="]
    topic = operator_prompt.strip() or "(no explicit topic — use the Factual Basis)"
    parts.append(f"TOPIC:\n{topic}")

    hard_constraints: list[str] = []
    if opener and opener.strip():
        hard_constraints.append(
            f"PINNED OPENER (use verbatim as the first sentence; "
            f"the rest of the script must follow naturally from it):\n"
            f"{opener.strip()}"
        )
    if corrective_hint and corrective_hint.strip():
        hard_constraints.append(
            f"CORRECTIVE HINT (previous attempt feedback — apply this):\n"
            f"{corrective_hint.strip()}"
        )
    if hard_constraints:
        parts.append(
            "HARD CONSTRAINTS (override Character Voice and Writing "
            "Contract preferences; do NOT override Factual Basis or "
            "Brand Voice prohibitions):\n\n"
            + "\n\n".join(hard_constraints)
        )

    parts.append(
        "Write the spokesperson's spoken script for this task. Plain "
        "spoken English — this becomes voiceover."
    )
    return "\n\n".join(parts)


# ---- Section builders --------------------------------------------


def _build_factual_basis_section(
    spokesperson: "Teammate",
    *,
    chunks: list,
) -> str:
    """§1 Factual Basis — the ONLY sources capable of supporting
    factual claims. Retrieved K2 chunks + business_brief +
    who_you_help + what_you_sell. Operator prompt is NOT here."""
    lines = [
        "=== SECTION 1 — FACTUAL BASIS ===",
        "The ONLY sources capable of supporting factual claims. "
        "Every factual claim in the script must trace back to "
        "content in this section. Do not invent product details, "
        "prices, features, statistics, or named entities not "
        "present here. If a fact isn't in this section, leave "
        "it out.",
    ]
    brief = (getattr(spokesperson, "business_brief", "") or "").strip()
    who = (getattr(spokesperson, "who_you_help", "") or "").strip()
    what = (getattr(spokesperson, "what_you_sell", "") or "").strip()
    if brief:
        lines.append(f"BUSINESS SHAPE:\n{brief}")
    if who:
        lines.append(f"AUDIENCE:\n{who}")
    if what:
        lines.append(f"OFFERING:\n{what}")
    if chunks:
        chunks_text = "\n\n".join(
            f"[CHUNK {i + 1} — doc {c.document_id}]\n{c.chunk_text}"
            for i, c in enumerate(chunks)
        )
        lines.append(f"KNOWLEDGE CHUNKS:\n{chunks_text}")
    else:
        lines.append("KNOWLEDGE CHUNKS: (none retrieved for this task)")
    return "\n\n".join(lines)


def _build_character_voice_section(spokesperson: "Teammate") -> str:
    """§2 Character Voice — how this character thinks and writes.
    NOT facts. Never verified against K6.4."""
    name = getattr(spokesperson, "name", "") or "the speaker"
    tone = getattr(spokesperson, "tone_archetype", "") or "expert"
    personality = (getattr(spokesperson, "personality", "") or "").strip()
    pov = (getattr(spokesperson, "character_point_of_view", "") or "").strip()
    energy = getattr(spokesperson, "voice_energy", "") or "medium"
    humor = getattr(spokesperson, "voice_humor", "") or "warm"
    directness = getattr(spokesperson, "voice_directness", "") or "balanced"
    signature = (getattr(spokesperson, "voice_signature_phrases", "") or "").strip()

    lines = [
        "=== SECTION 2 — CHARACTER VOICE ===",
        f"How {name} thinks and writes. This section shapes register, "
        f"opinions, what the character notices, and sentence rhythm. "
        f"It introduces zero factual claims. It is NOT verified by "
        f"K6.4.",
        f"TONE ARCHETYPE: {tone}",
        f"VOICE AXES: energy={energy}; humor={humor}; directness={directness}",
    ]
    if personality:
        lines.append(f"WRITING STYLE (how {name} sounds):\n{personality}")
    if pov:
        lines.append(
            f"POINT OF VIEW (what {name} notices, believes, enjoys, "
            f"dislikes, opines about — shapes interpretation of the "
            f"topic; does NOT force an opinion into informational "
            f"topics):\n{pov}"
        )
    if signature:
        lines.append(
            f"SIGNATURE PHRASES (possibilities {name} might reach for "
            f"occasionally — NOT required catchphrases; use zero, one, "
            f"or at most two per script if genuinely natural; NEVER "
            f"force one that doesn't fit the moment):\n{signature}"
        )
    return "\n\n".join(lines)


def _build_brand_voice_section(spokesperson: "Teammate") -> str:
    """§3 Brand Voice — positioning the character must respect.
    NOT character opinion. Explicit rule: does not license facts."""
    emphasize = (getattr(spokesperson, "always_emphasize", "") or "").strip()
    never = (getattr(spokesperson, "never_say", "") or "").strip()
    feeling = (getattr(spokesperson, "desired_feeling", "") or "").strip()
    if not (emphasize or never or feeling):
        return ""

    lines = [
        "=== SECTION 3 — BRAND VOICE ===",
        "Positioning the character must respect. These are BRAND "
        "constraints, not character opinions. Honor them as brand "
        "direction, not as things to recite verbatim. Never narrate "
        "that these rules exist.",
        "IMPORTANT — Brand Voice tells you what to EMPHASIZE, but it "
        "does NOT independently establish factual truth. Any factual "
        "proposition contained in this section may appear in the "
        "script ONLY when independently supported by the Factual "
        "Basis (Section 1).",
    ]
    if emphasize:
        lines.append(f"ALWAYS EMPHASIZE (brand-set messaging):\n{emphasize}")
    if never:
        lines.append(
            f"NEVER SAY (brand-set prohibitions — no factual grounding "
            f"required; these are absolute):\n{never}"
        )
    if feeling:
        lines.append(f"DESIRED AUDIENCE FEELING:\n{feeling}")
    return "\n\n".join(lines)


def _build_writing_contract_section(
    *,
    target_shape: str,
    target_duration_seconds: int | None,
) -> str:
    """§4 Writing Contract — format-specific, character-agnostic.
    Delegates to ``character_os.writing_contract.WritingContract``."""
    char_budget = None
    word_budget = None
    if target_shape == "long_form" and target_duration_seconds:
        char_budget = char_budget_for_duration(target_duration_seconds)
        word_budget = word_budget_for_duration(target_duration_seconds)

    contract_body = WritingContract.for_shape(
        target_shape,
        target_duration_seconds=target_duration_seconds,
        char_budget=char_budget,
        word_budget=word_budget,
    )
    return (
        f"=== SECTION 4 — WRITING CONTRACT (version {WRITING_CONTRACT_VERSION}) ===\n"
        f"Format-specific rules. Same for every character; the "
        f"character's voice from Section 2 shapes HOW these rules "
        f"get executed.\n\n"
        f"{contract_body}"
    )


_PRECEDENCE_RULES = (
    "=== PRECEDENCE RULES ===\n"
    "When sections conflict, resolve in this order:\n"
    "  1. Factual Basis (§1) beats everything on TRUTH. No claim "
    "survives that isn't grounded in §1.\n"
    "  2. Brand Voice (§3) beats Character Voice (§2) on "
    "PROHIBITIONS. ``never_say`` overrides any character preference.\n"
    "  3. Writing Contract (§4) beats Character Voice on STRUCTURE. "
    "One-CTA-when-included applies even to characters who prefer "
    "multiple asks.\n"
    "  4. Character Voice (§2) beats Writing Contract on REGISTER. "
    "The contract's anti-generic list is a floor; character voice "
    "adds distinctive register on top.\n"
    "  5. Task (§5) Hard Constraints beat Character Voice preferences "
    "and Writing Contract defaults, but NEVER override Factual Basis "
    "or Brand Voice prohibitions.\n"
    "  6. Task Topic beats Character Voice on TOPIC SCOPE. POV shapes "
    "interpretation of the topic, not choice of topic."
)


# ---- mock path -----------------------------------------------


def _mock_brief(
    spokesperson: "Teammate",
    operator_prompt: str,
    chunk_ids: list[str],
) -> str:
    """Deterministic brief for force-mock + tests. Includes the
    chunk ids in a parseable suffix so e2e tests can assert
    citation flow without parsing real LLM output.
    """
    parts = []
    business_brief = (spokesperson.business_brief or "").strip()
    if business_brief:
        parts.append(business_brief)
    if operator_prompt:
        parts.append(operator_prompt)
    if not parts:
        parts.append(f"[no operator prompt; spokesperson={spokesperson.name}]")
    parts.append(f"[knowledge: {len(chunk_ids)} chunks: {','.join(chunk_ids)}]")
    return "\n\n".join(parts)
