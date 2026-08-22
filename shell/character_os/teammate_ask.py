"""Chapter 6 slice-1 — spokesperson Ask + receipt.

SESSION 234. Companion to ``script_synthesis.py`` (K6). Takes a
question the operator typed under the spokesperson's portrait,
runs RAG against the workspace knowledge visible to that
spokesperson, synthesizes an in-voice answer via gpt-5, and
returns the answer + doc-level citations so the SPA can render
the first-class receipt Beat 2 requires.

Design lock: ``docs/design/CUSTOMER_JOURNEY_V1.md``
§"Chapter 6 — Ongoing training", Beats 1–2.

Ship bar (non-negotiable): no fabricated citations. Citations
name only docs whose chunks were actually placed in the model's
context. When retrieval returns nothing, the receipt is
explicitly empty and the answer states honestly that Oliver
answered from what he already knows — same shape as K6's
graceful-degradation branch.

Three operating modes (identical shape to ``build_render_brief``):

* **Force-mock** (``SPOKESPERSON_ASK_FORCE_MOCK=1`` env or
  ``settings.SPOKESPERSON_ASK_FORCE_MOCK=True``): deterministic
  answer that echoes the question + names the retrieved doc
  titles so tests can assert citation flow without an LLM.

* **No visible knowledge / no chunks matched**: honest fallback —
  Character-OS-voiced answer that states the spokesperson does
  not have specific material on this topic yet. Citations empty.
  No LLM call.

* **Real mode** (chunks visible + ``OPENAI_API_KEY`` set): one
  gpt-5 ``responses.create`` call. Chunks form the sole factual
  ground; citations dedupe to the source docs.
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


# Same model + effort as K6's ``script_synthesis`` — coaching-loop
# answers face the same negative-instruction reliability
# constraint (must NOT invent facts, must stay in-voice), so
# match the model that survived the K6.6.1 calibration.
ASK_MODEL = "gpt-5"
MAX_OUTPUT_TOKENS = 1200
REASONING_EFFORT = "low"

# Number of chunks to place in the model's context. Higher than
# K6's default because Ask questions can be narrower than a
# render brief (a single fact lookup), so we want enough breadth
# for the model to pick from.
DEFAULT_TOP_K = 5


@dataclass(slots=True)
class Citation:
    """One document the model was shown for this answer.

    ``chunk_count`` is the number of retrieved chunks that came
    from this doc — surfaces "3 chunks from About Hearth &
    Hollow Books" ordering in the receipt (most-cited first,
    per design lock Beat 2).
    """
    document_id: str
    title: str
    chunk_count: int


@dataclass(slots=True)
class AskResult:
    """What ``ask_teammate`` returns.

    ``used_knowledge`` distinguishes the receipt-bearing case
    from the honest-fallback case. When False, ``citations`` is
    always empty and the SPA renders the "answered from what he
    already knows" receipt shape.
    """
    answer: str
    citations: list[Citation] = field(default_factory=list)
    used_knowledge: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0


def _is_force_mock() -> bool:
    """Settings beats env — matches K6 + the embedding service."""
    settings_flag = getattr(settings, "SPOKESPERSON_ASK_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("SPOKESPERSON_ASK_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _dedupe_citations(chunks: list) -> list[Citation]:
    """Group retrieved chunks by document, preserving first-hit
    order (highest-similarity doc appears first). Doc-level dedup
    is what the receipt renders — the operator sees
    "From your notes on X, Y" not per-chunk mechanics.
    """
    order: list[str] = []
    titles: dict[str, str] = {}
    counts: dict[str, int] = {}
    for chunk in chunks:
        doc_id = str(chunk.document_id)
        if doc_id not in titles:
            titles[doc_id] = chunk.document.title
            order.append(doc_id)
            counts[doc_id] = 0
        counts[doc_id] += 1
    return [
        Citation(
            document_id=doc_id,
            title=titles[doc_id],
            chunk_count=counts[doc_id],
        )
        for doc_id in order
    ]


def _honest_fallback_answer(spokesperson: "Teammate") -> str:
    """The answer text when no chunks matched.

    Voiced in Character-OS neutral, not in the spokesperson's
    voice — this is Character OS reporting a fact about the
    spokesperson's current knowledge, not the spokesperson
    speaking. Matches the design lock's Beat 2 honest-fallback
    copy convention.
    """
    return (
        f"{spokesperson.name} answered from what {spokesperson.name} "
        f"already knows. Nothing specific was found in what you've "
        f"taught {spokesperson.name} yet."
    )


def ask_teammate(
    spokesperson: "Teammate",
    question: str,
    *,
    top_k: int = DEFAULT_TOP_K,
) -> AskResult:
    """Answer the operator's question in the spokesperson's voice.

    Never raises. Retrieval / LLM failures degrade to the
    honest-fallback shape so the SPA can always render something.

    Args:
        spokesperson: whose page the operator is on. Workspace +
            M2M visibility scope retrieval.
        question: the operator's typed question, natural language.
        top_k: chunks to place in the LLM's context.

    Returns:
        ``AskResult`` — always populated. When ``used_knowledge``
        is False, ``citations`` is empty and the answer is the
        honest-fallback text.
    """
    question = (question or "").strip()
    if not question:
        return AskResult(
            answer=_honest_fallback_answer(spokesperson),
            used_knowledge=False,
        )

    # Force-mock: skip the LLM entirely, but do run retrieval so
    # tests can assert citation-dedup behavior against real
    # workspace data. Mirrors ``build_render_brief`` mock.
    if _is_force_mock():
        try:
            chunks = retrieve_for_teammate(
                spokesperson, query=question, top_k=top_k,
            )
        except Exception:
            logger.exception(
                "teammate_ask retrieve failed sp=%s (mock path) — degrading",
                spokesperson.pk,
            )
            chunks = []
        citations = _dedupe_citations(chunks)
        if not citations:
            return AskResult(
                answer=_honest_fallback_answer(spokesperson),
                used_knowledge=False,
                model=f"{ASK_MODEL} (mock)",
            )
        return AskResult(
            answer=_mock_answer(spokesperson, question, citations),
            citations=citations,
            used_knowledge=True,
            model=f"{ASK_MODEL} (mock)",
        )

    # Real mode. Retrieve first.
    try:
        chunks = retrieve_for_teammate(
            spokesperson, query=question, top_k=top_k,
        )
    except Exception:
        logger.exception(
            "teammate_ask retrieve failed sp=%s — degrading",
            spokesperson.pk,
        )
        return AskResult(
            answer=_honest_fallback_answer(spokesperson),
            used_knowledge=False,
        )

    if not chunks:
        return AskResult(
            answer=_honest_fallback_answer(spokesperson),
            used_knowledge=False,
        )

    if not _has_openai_key():
        # Real mode requested but no key. Same pattern as K6 —
        # degrade rather than raise; log so operators can see
        # what happened.
        logger.warning(
            "ask_teammate: chunks visible but OPENAI_API_KEY "
            "unset sp=%s — degrading to honest fallback (set "
            "SPOKESPERSON_ASK_FORCE_MOCK=1 for dev determinism)",
            spokesperson.pk,
        )
        return AskResult(
            answer=_honest_fallback_answer(spokesperson),
            used_knowledge=False,
        )

    try:
        text, tokens_in, tokens_out = _call_responses_api(
            spokesperson, question, chunks,
        )
    except Exception:
        logger.exception(
            "teammate_ask openai call failed sp=%s chunks=%d — degrading",
            spokesperson.pk, len(chunks),
        )
        return AskResult(
            answer=_honest_fallback_answer(spokesperson),
            used_knowledge=False,
        )

    answer = text.strip()
    if not answer:
        # Empty LLM output — same failure mode script_synthesis
        # hit before MAX_OUTPUT_TOKENS was raised. Degrade.
        return AskResult(
            answer=_honest_fallback_answer(spokesperson),
            used_knowledge=False,
            model=ASK_MODEL,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
        )

    return AskResult(
        answer=answer,
        citations=_dedupe_citations(chunks),
        used_knowledge=True,
        model=ASK_MODEL,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
    )


# ---- LLM call --------------------------------------------------


def _call_responses_api(
    spokesperson: "Teammate",
    question: str,
    chunks: list,
) -> tuple[str, int, int]:
    """Single Responses-API call. Returns ``(text, tokens_in,
    tokens_out)``. Raises on API error — caller degrades.
    """
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    chunks_block = "\n\n".join(
        f"[CHUNK {i + 1} — from doc {c.document.title!r}]\n{c.chunk_text}"
        for i, c in enumerate(chunks)
    )

    system = _system_prompt(spokesperson)
    user = (
        f"Operator's question:\n{question}\n\n"
        f"Excerpts from what the operator has taught you "
        f"(these are your sole factual ground for this "
        f"answer):\n{chunks_block}\n\n"
        "Answer the operator's question in one to three short "
        "sentences. Use facts only from the excerpts above. If "
        "the excerpts do not cover the question, say honestly "
        "that you don't have specific information on that yet — "
        "do not invent details."
    )

    response = client.responses.create(
        model=ASK_MODEL,
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
    """Anchor the model to the spokesperson's identity + voice.

    Reuses the K6 personality-vs-brief split (W11.y): personality
    steers HOW the answer sounds; business_brief is authoritative
    business facts that can be grounded in alongside the chunks.
    """
    tone = spokesperson.tone_archetype or "expert"
    personality = (
        getattr(spokesperson, "personality", "") or ""
    ).strip()
    brief = (spokesperson.business_brief or "").strip()
    # SESSION 277 Slice 8 (Q-277-8) — WORLD SHAPE. Compact
    # deterministic Universe identity so the speaker knows what
    # World they inhabit even when the character's own
    # ``business_brief`` is thin or the Knowledge corpus is empty.
    # Omitted cleanly for legacy ``universe=NULL`` teammates or
    # when the Universe row's ``brief`` is blank.
    universe = getattr(spokesperson, "universe", None)
    world_brief = (getattr(universe, "brief", "") or "").strip() if universe else ""
    return (
        f"You are {spokesperson.name}, answering a question from "
        f"the operator who employs you. Your tone archetype is "
        f"{tone!r}. This is a one-turn Q&A — answer in first "
        f"person, plain conversational language, short (one to "
        f"three sentences).\n"
        + (
            f"The World you belong to (shared context every "
            f"character in this World inherits — paraphrase as "
            f"needed; authoritative alongside the excerpts): "
            f"{world_brief}\n"
            if world_brief else ""
        )
        + (
            f"Speaker voice + character (use this ONLY to shape "
            f"tone and perspective — do NOT recite or paraphrase "
            f"this in the answer): {personality}\n"
            if personality else ""
        )
        + (
            f"Business facts you can ground in (these ARE the "
            f"business you speak for — paraphrase as needed; "
            f"authoritative alongside the excerpts): {brief}\n"
            if brief else ""
        )
        + "Never invent product details, prices, customers, or "
        "policies that are not in the excerpts or business "
        "facts. When the operator asks about something the "
        "excerpts do not cover, say honestly that you don't "
        "know that specific detail yet — the operator will use "
        "your answer to teach you more."
    )


# ---- mock path -----------------------------------------------


def _mock_answer(
    spokesperson: "Teammate",
    question: str,
    citations: list[Citation],
) -> str:
    """Deterministic answer for force-mock + tests.

    Echoes the question and lists the doc titles so tests can
    assert citation flow without parsing real LLM output. Not
    voice-shaped — the mock is for coverage, not for humans.
    """
    titles = ", ".join(c.title for c in citations)
    return (
        f"[mock ask for {spokesperson.name}] question={question!r} "
        f"grounded_in={titles}"
    )
