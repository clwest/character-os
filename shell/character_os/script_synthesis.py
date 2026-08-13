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


@dataclass(slots=True)
class ScriptResult:
    """What ``build_render_brief`` returns. ``used_knowledge``
    distinguishes the 'real synthesis ran' case from the
    'degraded to operator prompt' case; the caller persists
    ``chunk_ids`` onto ``Video.knowledge_chunk_ids`` regardless
    (empty list on degraded path).

    ``verification_warnings`` (K6.4, SESSION 159) is the list
    of named entities in the synthesized brief that don't
    appear in the retrieved chunks (or the allow-list extras —
    spokesperson name, business brief, operator prompt,
    ``KNOWN_PLATFORM_TERMS``). Empty when synthesis didn't
    actually run (degraded path) OR
    ``settings.K6_CLAIM_VERIFIER_MODE == "off"``. In Strict
    mode the verifier raises before this list is populated,
    so callers see the exception, not the field.
    """
    brief: str
    chunk_ids: list[str] = field(default_factory=list)
    used_knowledge: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    verification_warnings: list[dict] = field(default_factory=list)
    # K6.4 v1.2 — see ``apps.compositions.models.VerificationStatus``.
    # Empty string when the code path doesn't set it (defensive
    # default; every return path in build_render_brief sets one
    # of the four explicit values).
    verification_status: str = ""


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

    Returns:
        ``ScriptResult`` — always has a usable ``brief`` field
        (never raises). ``used_knowledge`` reports whether
        synthesis actually ran or fell through to degradation.
    """
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
            spokesperson, operator_prompt, chunks, opener=opener,
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

    # K6.4 — post-synthesis claim verifier. Runs only when the
    # LLM actually produced something (the fallback path is
    # operator-typed and trusted by definition). The verifier
    # raises in Strict mode; we let that propagate to the
    # primitive caller, who will fail the composition.
    from character_os.claim_verifier import build_corpus, run_verifier

    corpus = build_corpus(
        chunks,
        spokesperson=spokesperson,
        operator_prompt=operator_prompt,
    )
    # K6.4 v1.2 — resolve the mode the verifier *actually* runs
    # under so we can stamp the right verification_status. Strict
    # rejection raises; Warn/clean → verified; Off → skipped.
    from character_os.claim_verifier import _get_default_mode

    resolved_mode = (verifier_mode or _get_default_mode()).lower()
    unsupported = run_verifier(final_brief, corpus=corpus, mode=verifier_mode)
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
    )


# ---- LLM call --------------------------------------------------


def _call_responses_api(
    spokesperson: "Teammate",
    operator_prompt: str,
    chunks: list,
    *,
    opener: str | None = None,
) -> tuple[str, int, int]:
    """Single Responses-API call. Returns ``(text, tokens_in,
    tokens_out)``. Raises on API error — caller handles
    degradation.

    K6.6 (SESSION 168) — optional ``opener`` lets the operator
    pin the script's first line verbatim. When ``None``, the
    system prompt's structural guidance steers the model to
    pick its own standalone opener.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    chunks_block = "\n\n".join(
        f"[CHUNK {i + 1} — from doc {c.document_id}]\n{c.chunk_text}"
        for i, c in enumerate(chunks)
    )

    system = _system_prompt(spokesperson)
    opener_clause = (
        f"Operator-supplied opening line (use verbatim as the first "
        f"sentence; the rest of the script must follow naturally from "
        f"it):\n{opener.strip()}\n\n"
        if opener and opener.strip()
        else ""
    )
    user = (
        f"Operator's brief for this video:\n{operator_prompt or '(no prompt — use the brief above)'}\n\n"
        + opener_clause
        + f"Knowledge chunks available:\n{chunks_block}\n\n"
        "Write the spokesperson's spoken script for this video. "
        "Use facts only from the chunks above. Keep it to 60-100 "
        "words. Plain spoken English — this becomes voiceover."
    )

    response = client.responses.create(
        model=SCRIPT_MODEL,
        input=f"{system}\n\nUser: {user}",
        max_output_tokens=MAX_OUTPUT_TOKENS,
        reasoning={"effort": REASONING_EFFORT},
    )

    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _system_prompt(spokesperson: "Teammate") -> str:
    """Anchor the model to the spokesperson's tone + business
    context. Kept minimal — the chunks carry the facts; this
    just steers voice.

    K6.6 (SESSION 168) — structural guidance added after operator
    feedback that scripts "feel like picking up mid conversation."

    K6.6.1 (SESSION 171) — business-brief leak fix. Fenced
    business_brief as tone-only + added anti-recitation rule.

    W11.y (SESSION 175) — personality / business_brief split.
    Pre-split the single business_brief field did double duty:
    voice-on-the-page (HOW) AND business facts (WHAT). K6.6.1
    fenced the whole blob as tone-only, but that meant the
    model couldn't ground in real business facts; chunks were
    the only fact source. Post-split:

    * ``personality`` (operator-supplied voice / character) goes
      in the TONE fence with the recitation guard. This is the
      previous ``business_brief`` tone-only role.
    * ``business_brief`` (operator-supplied business facts)
      moves to the FACT fence alongside chunks. The model MAY
      paraphrase + ground in it; the recitation guard no
      longer applies because it's facts the operator wants
      voiced, not character description.

    Backfill (migration 0005, Option B) populated personality
    from the old business_brief for every existing row, so
    pre-W11.y rows produce the same K6 output (both fences
    see the same content) until the operator splits them.
    """
    tone = spokesperson.tone_archetype or "expert"
    personality = (
        getattr(spokesperson, "personality", "") or ""
    ).strip()
    brief = (spokesperson.business_brief or "").strip()
    return (
        f"You are writing the spoken script for {spokesperson.name}, "
        f"an on-camera spokesperson. Their tone archetype is {tone!r}. "
        + (
            f"Speaker voice + character (use this ONLY to shape tone "
            f"and perspective — do NOT recite, paraphrase, or describe "
            f"this in the script): {personality}\n"
            if personality else ""
        )
        + (
            f"Business facts the speaker can ground in (these ARE "
            f"the product / business — paraphrase as needed; treat "
            f"as authoritative alongside the knowledge chunks. "
            f"Quoted phrases inside these facts are CONCEPTS the "
            f"speaker teaches, NOT catchphrases to recite verbatim — "
            f"reframe them in your own words): "
            f"{brief}\n"
            if brief else ""
        )
        + (
            "This is a SHORT STANDALONE VIDEO (60-100 words, "
            "about 30-60 seconds). The viewer has not seen "
            "anything else from you — there is no prior context. "
            "Open with a brief setup that grounds the viewer in "
            "what this video is about (one or two short sentences). "
            "Then make your one clear claim or insight from the "
            "knowledge chunks or business facts. Then one call to "
            "action. "
            "Do NOT begin mid-thought as if continuing a "
            "conversation. The first sentence must stand alone. "
            "Do NOT introduce yourself, name your role, describe "
            "your audience, or recite the speaker voice + character "
            "block — the viewer cares about the topic, not your "
            "resume.\n"
        )
        + "Use facts only from the knowledge chunks + business facts "
        "the user supplies. Do not invent product details, prices, "
        "or features. If a fact isn't in either source, leave it out. "
        "Speak naturally — first person where appropriate."
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
