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

from apps.embeddings.retrieval import retrieve_for_spokesperson

if TYPE_CHECKING:
    from apps.spokespeople.models import Spokesperson

logger = logging.getLogger(__name__)


# Locked to gpt-5-mini (Responses API). Pricing matches the old
# gpt-4o-mini ($0.15 / $0.60 per 1M tokens). See the memory at
# ~/.claude/projects/.../feedback_openai_gpt5_responses_api.md.
SCRIPT_MODEL = "gpt-5-mini"

# Conservative cap. A single ad spot needs maybe 80-120 words;
# 500 output tokens is well above the realistic ceiling and gives
# the model room to phrase a longer cinematic.
MAX_OUTPUT_TOKENS = 500

# `reasoning_effort='low'` for K6 — script synthesis is
# pattern-matching against the chunks, not multi-step reasoning.
# Bumping to 'medium' or 'high' adds latency + cost without
# improving the output for this task.
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
    spokesperson: "Spokesperson",
    operator_prompt: str,
    *,
    top_k: int = DEFAULT_TOP_K,
) -> ScriptResult:
    """Build the brief that gets sent to media-engine.

    Args:
        spokesperson: who's speaking. Their workspace + M2M
            visibility drive the retrieval scope.
        operator_prompt: what the operator typed. Doubles as
            the RAG query and as the rendering topic.
        top_k: how many knowledge chunks to consider.

    Returns:
        ``ScriptResult`` — always has a usable ``brief`` field
        (never raises). ``used_knowledge`` reports whether
        synthesis actually ran or fell through to degradation.
    """
    operator_prompt = (operator_prompt or "").strip()
    fallback_brief = operator_prompt or (spokesperson.business_brief or "").strip()

    # Force-mock: no retrieval, no LLM. Deterministic shape that
    # tests can assert against.
    if _is_force_mock():
        chunks = retrieve_for_spokesperson(
            spokesperson, query=operator_prompt or spokesperson.name, top_k=top_k,
        )
        chunk_ids = [str(c.id) for c in chunks]
        return ScriptResult(
            brief=_mock_brief(spokesperson, operator_prompt, chunk_ids),
            chunk_ids=chunk_ids,
            used_knowledge=bool(chunk_ids),
            model=f"{SCRIPT_MODEL} (mock)",
        )

    # Real mode — first retrieve. Even if retrieval fails for
    # some weird reason, we degrade.
    try:
        chunks = retrieve_for_spokesperson(
            spokesperson, query=operator_prompt or spokesperson.name, top_k=top_k,
        )
    except Exception:
        logger.exception(
            "retrieve_for_spokesperson failed sp=%s — degrading to operator prompt",
            spokesperson.pk,
        )
        return ScriptResult(brief=fallback_brief)

    if not chunks:
        # Contract rule 6 — graceful degradation. No knowledge,
        # no synthesis, original brief flows through.
        return ScriptResult(brief=fallback_brief)

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
        )

    try:
        synthesised, tokens_in, tokens_out = _call_responses_api(
            spokesperson, operator_prompt, chunks,
        )
    except Exception:
        logger.exception(
            "OpenAI responses.create failed sp=%s chunks=%d — degrading",
            spokesperson.pk, len(chunks),
        )
        return ScriptResult(
            brief=fallback_brief,
            chunk_ids=[str(c.id) for c in chunks],
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
    unsupported = run_verifier(final_brief, corpus=corpus)
    if unsupported:
        logger.warning(
            "K6.4 verifier flagged %d unsupported claim(s) on sp=%s: %s",
            len(unsupported),
            spokesperson.pk,
            ", ".join(f"{u.claim!r}" for u in unsupported),
        )

    return ScriptResult(
        brief=final_brief,
        chunk_ids=[str(c.id) for c in chunks],
        used_knowledge=True,
        model=SCRIPT_MODEL,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        verification_warnings=[u.to_dict() for u in unsupported],
    )


# ---- LLM call --------------------------------------------------


def _call_responses_api(
    spokesperson: "Spokesperson",
    operator_prompt: str,
    chunks: list,
) -> tuple[str, int, int]:
    """Single Responses-API call. Returns ``(text, tokens_in,
    tokens_out)``. Raises on API error — caller handles
    degradation."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    chunks_block = "\n\n".join(
        f"[CHUNK {i + 1} — from doc {c.document_id}]\n{c.chunk_text}"
        for i, c in enumerate(chunks)
    )

    system = _system_prompt(spokesperson)
    user = (
        f"Operator's brief for this video:\n{operator_prompt or '(no prompt — use the brief above)'}\n\n"
        f"Knowledge chunks available:\n{chunks_block}\n\n"
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


def _system_prompt(spokesperson: "Spokesperson") -> str:
    """Anchor the model to the spokesperson's tone + business
    context. Kept minimal — the chunks carry the facts; this
    just steers voice."""
    tone = spokesperson.tone_archetype or "expert"
    brief = (spokesperson.business_brief or "").strip()
    return (
        f"You are writing the spoken script for {spokesperson.name}, "
        f"an on-camera spokesperson. Their tone archetype is {tone!r}. "
        + (f"Their business brief is: {brief}\n" if brief else "")
        + "Use facts only from the knowledge chunks the user supplies. "
        "Do not invent product details, prices, or features. If a fact "
        "isn't in the chunks, leave it out. Speak naturally — first "
        "person where appropriate, one clear claim, one call to action."
    )


# ---- mock path -----------------------------------------------


def _mock_brief(
    spokesperson: "Spokesperson",
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
