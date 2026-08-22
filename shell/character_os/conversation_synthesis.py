"""Conversation reply synthesis — user message → spokesperson reply.

SESSION 145 / K9. Mirrors `script_synthesis.py` (K6) for the
conversation surface. Takes a thread + the new user message,
runs `retrieve_for_thread` for workspace docs + thread
history, calls gpt-5-mini Responses API with the spokesperson's
voice anchoring, returns the synthesized reply text + chunk
citations.

Operating modes match K6's:

* **Force-mock** (`CONVERSATION_REPLY_FORCE_MOCK=1` env or
  `settings.CONVERSATION_REPLY_FORCE_MOCK=True`) — deterministic
  stub. Same shape pattern as `RENDER_SCRIPT_FORCE_MOCK`.
* **No knowledge / no OpenAI key** — graceful degradation:
  return a templated reply that echoes the question + flags
  the lack of context. The thread keeps working; the operator
  can investigate.
* **Real mode** — gpt-5-mini Responses API call, reasoning
  effort `low`. Chunks for context, recent history for tone
  continuity.

The result includes chunk ids so the caller can persist them
on `ConversationMessage.knowledge_chunk_ids` once that field
lands (post-v1; for v1 we just return them).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.conf import settings

from apps.embeddings.retrieval import retrieve_for_thread

if TYPE_CHECKING:
    from apps.conversations.models import ConversationThread

logger = logging.getLogger(__name__)


# SESSION 171 — promoted from gpt-5-mini to gpt-5 (full).
# Generative call site (multi-turn dialogue); same rationale as
# K6 (script_synthesis). REASONING_EFFORT stays 'low' here because
# K9 doesn't carry the K6 leak-bait risk (no static business_brief
# pattern matching against retrieved knowledge chunks).
REPLY_MODEL = "gpt-5"
# SESSION 176 — bumped 400 → 1000. gpt-5 with reasoning burns hidden
# tokens against the same output budget; operator-visible replies
# were truncating mid-sentence at 400 even on tight 1-2 paragraph
# answers. 1000 gives ~2-3 short paragraphs of visible text after
# reasoning overhead.
MAX_OUTPUT_TOKENS = 1000
REASONING_EFFORT = "low"
DEFAULT_TOP_K_DOCS = 3
DEFAULT_TOP_K_HISTORY = 6  # last few turns for tone continuity


@dataclass(slots=True)
class ReplyResult:
    """What `synthesize_spokesperson_reply` returns. Always
    has a usable `text` field — degradation paths still
    return something sensible. `used_knowledge` distinguishes
    "real synthesis ran" from "fell back to a stub."

    ``verification_warnings`` (K6.5, SESSION 162) is the list
    of named entities in the synthesized reply that don't
    appear in the retrieved corpus (docs + history + user
    message + spokesperson allow-list). Empty when synthesis
    didn't run (degraded path) OR
    ``settings.K6_CLAIM_VERIFIER_MODE == "off"``. In Strict
    mode the verifier raises ``ClaimVerifierError`` before
    this is populated; the API view catches and surfaces.
    """
    text: str
    chunk_ids: list[str] = field(default_factory=list)
    used_knowledge: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    verification_warnings: list[dict] = field(default_factory=list)
    # K6.4 v1.2 — see apps.compositions.models.VerificationStatus.
    verification_status: str = ""


def _is_force_mock() -> bool:
    settings_flag = getattr(settings, "CONVERSATION_REPLY_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("CONVERSATION_REPLY_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def synthesize_spokesperson_reply(
    thread: "ConversationThread",
    user_content: str,
    *,
    top_k_docs: int = DEFAULT_TOP_K_DOCS,
    top_k_history: int = DEFAULT_TOP_K_HISTORY,
    verifier_mode: str | None = None,
) -> ReplyResult:
    """Build the spokesperson's reply to a user message.

    Args:
        thread: the conversation thread (carries the
            spokesperson + workspace anchor).
        user_content: the user's latest message — doubles as
            the RAG query and as the prompt body.

    Returns:
        `ReplyResult` — always has a `text` field, never
        raises. `used_knowledge` reports whether real
        synthesis ran.
    """
    user_content = (user_content or "").strip()
    spokesperson = thread.spokesperson

    # Force-mock: no LLM, deterministic shape. Still pulls
    # retrieval so the chunk_ids round-trip is testable. v1.2 —
    # no synthesis means trusted_passthrough.
    if _is_force_mock():
        docs, history = retrieve_for_thread(
            thread, query=user_content or spokesperson.name,
            top_k_docs=top_k_docs, top_k_history=top_k_history,
        )
        chunk_ids = [str(c.id) for c in docs]
        return ReplyResult(
            text=_mock_reply(spokesperson, user_content, chunk_ids, len(history)),
            chunk_ids=chunk_ids,
            used_knowledge=bool(chunk_ids),
            model=f"{REPLY_MODEL} (mock)",
            verification_status="trusted_passthrough",
        )

    # Real mode — retrieve first. Any failure degrades.
    try:
        docs, history = retrieve_for_thread(
            thread, query=user_content or spokesperson.name,
            top_k_docs=top_k_docs, top_k_history=top_k_history,
        )
    except Exception:
        logger.exception(
            "retrieve_for_thread failed thread=%s — degrading",
            thread.pk,
        )
        return ReplyResult(
            text=_degraded_reply(spokesperson, user_content),
            verification_status="trusted_passthrough",
        )

    if not _has_openai_key():
        logger.warning(
            "synthesize_spokesperson_reply: no OPENAI_API_KEY — degrading "
            "(set CONVERSATION_REPLY_FORCE_MOCK=1 for dev determinism)"
        )
        return ReplyResult(
            text=_degraded_reply(spokesperson, user_content),
            chunk_ids=[str(c.id) for c in docs],
            verification_status="trusted_passthrough",
        )

    try:
        text, tokens_in, tokens_out = _call_responses_api(
            spokesperson, user_content, docs, history,
        )
    except Exception:
        logger.exception(
            "OpenAI responses.create failed thread=%s — degrading", thread.pk,
        )
        return ReplyResult(
            text=_degraded_reply(spokesperson, user_content),
            chunk_ids=[str(c.id) for c in docs],
            verification_status="trusted_passthrough",
        )

    final_text = text.strip() or _degraded_reply(spokesperson, user_content)

    # K6.5 — post-synthesis claim verifier. Mirrors K6.4 in
    # ``script_synthesis.py``. Runs only when the LLM actually
    # produced something; the degraded path is operator-trusted
    # by design. Strict mode raises ``ClaimVerifierError`` which
    # the API view catches and surfaces as a 422.
    #
    # SESSION 253 — split corpus: factual evidence vs allowed
    # vocabulary. History chunks contain PRIOR conversation
    # content and are legitimate factual context for the reply,
    # so they enter the factual corpus (mirrors the K2 chunk
    # role). The user prompt is NOT factual evidence — the user
    # may reference terms the system should verify against real
    # sources; treating the user's message as evidence would
    # silently ground its assertions.
    from character_os.claim_verifier import (
        _get_default_mode,
        build_allowed_vocabulary,
        build_factual_corpus,
        run_verifier,
    )

    class _HistoryChunk:
        """Adapt a history-message row to the factual-corpus
        chunk shape (``chunk_text`` attr)."""
        def __init__(self, text: str):
            self.chunk_text = text

    factual_corpus_chunks = list(docs) + [
        _HistoryChunk(getattr(h, "chunk_text", ""))
        for h in history
        if getattr(h, "chunk_text", None)
    ]
    factual_corpus = build_factual_corpus(
        factual_corpus_chunks, spokesperson=spokesperson,
    )
    allowed_vocabulary = build_allowed_vocabulary(spokesperson=spokesperson)

    # K6.4 v1.2 — same mode-resolution dance as script_synthesis
    # to stamp the right verification_status. Strict rejection
    # raises; the API view sets status=rejected on the persisted
    # placeholder message.
    resolved_mode = (verifier_mode or _get_default_mode()).lower()
    unsupported = run_verifier(
        final_text,
        factual_corpus=factual_corpus,
        allowed_vocabulary=allowed_vocabulary,
        mode=verifier_mode,
    )
    if unsupported:
        logger.warning(
            "K6.5 verifier flagged %d unsupported claim(s) on thread=%s: %s",
            len(unsupported),
            thread.pk,
            ", ".join(f"{u.claim!r}" for u in unsupported),
        )

    status = "skipped" if resolved_mode == "off" else "verified"

    return ReplyResult(
        text=final_text,
        chunk_ids=[str(c.id) for c in docs],
        used_knowledge=bool(docs),
        model=REPLY_MODEL,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        verification_warnings=[u.to_dict() for u in unsupported],
        verification_status=status,
    )


def _call_responses_api(
    spokesperson,
    user_content: str,
    docs: list,
    history: list,
) -> tuple[str, int, int]:
    """Single Responses-API call. Raises on API error —
    caller handles degradation."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    docs_block = "\n\n".join(
        f"[DOC CHUNK {i + 1}]\n{c.chunk_text}"
        for i, c in enumerate(docs)
    ) if docs else "(no workspace docs match this question)"

    history_block = "\n".join(
        f"- {h.chunk_text}"
        for h in history
    ) if history else "(no prior turns in this thread)"

    system = _system_prompt(spokesperson)
    user_msg = (
        f"User just said:\n{user_content or '(empty message)'}\n\n"
        f"Workspace knowledge:\n{docs_block}\n\n"
        f"Recent thread turns (for tone continuity):\n{history_block}\n\n"
        "Reply as the spokesperson in 1-3 short paragraphs. "
        "Use facts only from the workspace knowledge. If the "
        "answer isn't in the docs, say so plainly — don't invent."
    )

    response = client.responses.create(
        model=REPLY_MODEL,
        input=f"{system}\n\nUser: {user_msg}",
        max_output_tokens=MAX_OUTPUT_TOKENS,
        reasoning={"effort": REASONING_EFFORT},
    )
    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _system_prompt(spokesperson) -> str:
    """W11.y (SESSION 175) — same personality / business_brief
    split as script_synthesis._system_prompt. Personality drives
    HOW the avatar speaks (in-character voice); business_brief
    is the factual context they ground in. Pre-W11.y rows have
    personality backfilled from business_brief so existing
    conversations produce the same replies until the operator
    splits the content per-spokesperson."""
    tone = spokesperson.tone_archetype or "expert"
    personality = (
        getattr(spokesperson, "personality", "") or ""
    ).strip()
    brief = (spokesperson.business_brief or "").strip()
    # SESSION 277 Slice 8 (Q-277-8) — WORLD SHAPE. Compact
    # deterministic Universe identity for the realtime avatar
    # session. Omitted cleanly for legacy universe=NULL teammates.
    universe = getattr(spokesperson, "universe", None)
    world_brief = (getattr(universe, "brief", "") or "").strip() if universe else ""
    return (
        f"You are {spokesperson.name}, an on-camera spokesperson speaking "
        f"in first person to a user. Tone archetype: {tone!r}. "
        + (
            f"The World you belong to (shared context every "
            f"character in this World inherits — paraphrase as "
            f"needed): {world_brief}\n"
            if world_brief else ""
        )
        + (f"Your voice + character: {personality}\n" if personality else "")
        + (f"Business context (paraphrase as needed): {brief}\n" if brief else "")
        + "Stay in character. Pull facts only from the workspace knowledge "
        "the user supplies below + the business context above. If a fact "
        "isn't there, acknowledge it rather than invent. Keep replies "
        "conversational — short paragraphs, natural phrasing, no bullet "
        "lists unless the user asks. "
        # SESSION 176 — catchphrase guard. Operators frequently write
        # business_brief lines like 'Signature concept: "X"' which the
        # model otherwise treats as Marcus's verbatim opener on every
        # reply. Quoted phrases inside business_brief are concepts to
        # teach, not catchphrases to recite. Don't open consecutive
        # replies with the same phrase even when business_brief
        # features it prominently."
        "Quoted phrases inside the business context are CONCEPTS the "
        "speaker teaches, NOT catchphrases the speaker says. Do not "
        "open replies with quoted phrases from the business context. "
        "If the same concept is relevant across multiple replies, vary "
        "how you introduce it — never repeat a verbatim signature line "
        "as a recurring opener."
    )


def _mock_reply(
    spokesperson,
    user_content: str,
    chunk_ids: list[str],
    history_count: int,
) -> str:
    """Deterministic reply for force-mock + tests. Includes
    chunk ids + history counts in a parseable suffix so e2e
    tests can assert citation flow without parsing real LLM
    output."""
    parts = [
        f"[mock reply from {spokesperson.name}]",
        f"You said: {user_content or '(empty)'}",
        f"[knowledge: {len(chunk_ids)} chunks: {','.join(chunk_ids)}]",
        f"[history: {history_count} prior turns]",
    ]
    return "\n\n".join(parts)


def _degraded_reply(spokesperson, user_content: str) -> str:
    """Fallback when synthesis can't run (no key, retrieval
    failed, etc). Keeps the thread working without faking a
    knowledge-aware reply."""
    return (
        f"I hear you on \"{user_content[:80]}\" — but I don't have the "
        "workspace knowledge available right now to answer properly. "
        "Try again in a moment, or check that the workspace has docs "
        f"attached to {spokesperson.name}."
    )
