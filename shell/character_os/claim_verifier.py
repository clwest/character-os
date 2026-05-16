"""K6.4 — post-synthesis claim verifier.

SESSION 159. The piece that catches what
`script_synthesis.py:_system_prompt` is supposed to prevent
by instruction: ``gpt-5-mini`` confidently hallucinates named
entities (libraries, products, companies, places) that aren't
in the retrieved chunks when its training data already knows
about them.

The failure mode the SESSION 158 Donny render exposed:
the script said *"Wikipedia is its absolute home turf"* and
*"the library doing the work is called trafilatura"* with
both terms absent from every retrieved chunk. The K6 system
prompt's *"Use facts only from the knowledge chunks. Do not
invent. Leave it out."* instruction is necessary but not
sufficient — prompt-only no-invention contracts leak when the
model already knows the truth.

This module sits *after* the synthesis call. It extracts
named-entity-shaped tokens from the synthesized text and
checks each against a corpus of supported content (retrieved
chunks + spokesperson business brief + operator prompt +
``KNOWN_PLATFORM_TERMS``). Any extracted entity with no
case-insensitive substring match in the corpus is reported
as an ``UnsupportedClaim``.

v1 is deterministic / regex-based — zero added LLM cost, zero
added latency. Lowercase technology names (``trafilatura``,
``pgvector``) are a known false-negative class in v1 unless
they happen to be capitalized in the source or in
``KNOWN_PLATFORM_TERMS``. v2 upgrade path is small-model
semantic similarity; deferred until first false-positive
event motivates it.

Three modes, keyed off ``settings.K6_CLAIM_VERIFIER_MODE``:

* ``"strict"`` — raise ``ClaimVerifierError`` on any
  unsupported claim. The composition fails before the
  render fires.
* ``"warn"`` (default) — return the unsupported list to the
  caller, who persists it onto ``Composition.verification_warnings``
  but lets the render proceed.
* ``"off"`` — skip verification entirely (legacy behavior).
"""
from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Iterable

from django.conf import settings

if TYPE_CHECKING:
    from apps.spokespeople.models import Spokesperson


# Platform terms that any spokesperson is allowed to reference
# without explicit chunk support. The product name belongs here;
# generic platform vocabulary the operator hasn't put in their
# business brief yet also goes here. Keep narrow — every entry
# is a free hallucination license.
KNOWN_PLATFORM_TERMS: tuple[str, ...] = (
    "Character OS",
)


# K6.4 v2 — case-insensitive technology / library names the
# extractor should catch even when lowercase. Closes the
# SESSION 158 ``trafilatura`` miss: substring extraction's
# capitalized-only rule missed lowercase tech names entirely,
# so they were never checked against the corpus and silently
# passed through hallucination paths.
#
# This is a curated allow-list of names worth treating as
# proper nouns for verification purposes. Adding to it costs
# nothing at runtime (one extra regex alternation); the cost
# is operator-curation drift. Run the SESSION 165 watchdog
# periodically to surface tech names appearing in flagged
# events that the operator might want to add here.
#
# Don't add generic ML terms (``embedding``, ``transformer``,
# ``vector``) — they appear in normal English prose and would
# generate noise. Names only (libraries, products, services).
KNOWN_TECH_TERMS: frozenset[str] = frozenset({
    # The SESSION 158 hallucination — the canonical case
    # v2 closes.
    "trafilatura",
    # Storage / db
    "pgvector", "postgres", "postgresql", "sqlite",
    "redis", "memcached",
    # Web frameworks
    "django", "fastapi", "flask", "express",
    "react", "vite", "nextjs",
    # ML / AI libraries
    "pytorch", "tensorflow", "huggingface",
    "langchain", "llamaindex", "haystack",
    "openai", "anthropic",
    # Tooling
    "celery", "docker", "kubernetes", "ffmpeg",
    "ollama", "playwright", "pytest",
    # Models the operator might invoke
    "gpt", "claude", "gemini", "llama", "mistral",
    # Evaluation benchmarks (mentioned in the RAG doc)
    "beir",
})


# Common English words that look proper-noun-shaped because
# of sentence-initial capitalization but aren't actually named
# entities. Lowercase, since we lowercase the candidate before
# checking. Curated narrowly — the test is whether removing
# them from this list causes the Donny smoke test to false-
# positive on a legitimate render.
_COMMON_PROPER_NOUN_FALSE_POSITIVES: frozenset[str] = frozenset({
    # Capitalized sentence starters that look like proper nouns
    "the", "this", "that", "these", "those", "their", "there",
    "we", "our", "us",
    "you", "your",
    "i", "my", "me",
    "he", "she", "it", "its",
    "they", "them",
    "what", "when", "where", "why", "how", "who",
    "yes", "no", "maybe",
    "turns", "look", "looks", "see", "sees", "watch", "watches",
    "now", "then", "next", "first", "last", "finally",
    "some", "many", "most", "few", "each", "every", "all", "none",
    "could", "would", "should", "will", "shall", "may", "might",
    "let", "lets",
    "make", "makes", "made",
    "get", "gets", "got",
    "take", "takes", "took",
    "and", "or", "but", "so", "yet",
    # Common verbs + adjectives that show up at sentence starts
    "drop", "drops", "dropped",
    "stop", "stops", "stopped",
    "start", "starts", "started",
    "use", "uses", "used",
    "try", "tries", "tried",
    "ask", "asks", "asked",
    "tell", "tells", "told",
    "show", "shows", "showed",
    "give", "gives", "gave",
    "find", "finds", "found",
    "open", "opens", "opened",
    "close", "closes", "closed",
    "talking", "speaking", "listening", "reading", "writing",
    "according",
    # Sentence-initial adjectives + greetings
    "cleanest", "clearest", "brightest", "darkest", "softest", "hardest",
    "best", "worst", "biggest", "smallest", "fastest", "slowest",
    "welcome", "hello", "hi", "thanks", "thank",
    "great", "good", "bad",
    "real", "true", "false",
    "every", "everyone", "everything", "everywhere",
    "everybody", "anybody", "somebody", "nobody",
    "anyone", "someone",
    "anything", "something", "nothing",
    "anywhere", "somewhere", "nowhere",
    "even", "still", "again",
    "since", "while", "though", "although", "however",
    "because", "therefore",
    # K6.5 dogfood finding (SESSION 162): refusal-pattern
    # sentence starters get flagged when the model honestly
    # says "I don't know X". These aren't fact claims — they
    # are meta-language framing the refusal. Punishing honest
    # refusals is the *opposite* of what the verifier is for.
    "short", "long", "brief", "quick",
    "which", "what", "where", "whose", "whom",
    "either", "neither", "both",
    "many", "lots",
    "rather", "instead", "otherwise",
    "frankly", "honestly", "actually", "really",
    "straight", "plain", "plainly", "simply",
    "fine",
    "ok", "okay",
    # K6.4 v2 (SESSION 166): watchdog-surfaced false positives
    # from SESSIONS 164-165 dogfood. ``alright`` was caught
    # by the K6.4.1 strict-mode probe; the watchdog
    # systematically classifies it as sentence-initial. Adding
    # here closes the regression.
    "alright",
    "sure", "yeah", "yep", "yup", "nope",
    "agreed", "totally", "absolutely", "definitely",
    "exactly", "precisely", "right",
    "indeed", "certainly",
    "wow", "wait",
    # K6.4.1 — sentence-initial common adjectives. Captured
    # SESSION 161 after the K6.4 strict-mode dogfood flagged
    # "Modern" as a false positive on a real render. Same
    # class as the originals: adjectives that appear
    # capitalized at sentence starts in marketing prose but
    # aren't proper nouns.
    "modern", "digital", "smart", "advanced", "simple", "basic",
    "classic", "premium", "natural", "easy", "hard", "normal",
    "complete", "full", "partial", "open", "closed",
    "small", "large", "tiny", "huge", "quick", "slow",
    "fast", "rapid", "instant", "live", "active", "passive",
    "main", "primary", "secondary", "regular", "standard",
    "custom", "special", "general", "specific",
    "popular", "common", "rare", "unique",
    "free", "paid",
    "young", "old", "ancient",
    "new", "fresh", "recent",
    "early", "late", "final", "initial",
    "internal", "external",
    "online", "offline", "local", "remote",
    "public", "private",
    "modern-day",
})


# Pattern for multi-word capitalized phrases: 2+ capitalized
# words in sequence (with a small set of joining lowercase
# connectors that are real proper-noun glue).
# Catches "Character OS", "James Webb Space Telescope",
# "Federal Bureau of Investigation".
#
# K6.4 v2 (SESSION 166) tightening: dropped ``a`` and ``an``
# from the joining set. Both are too common in English to be
# reliable connectors — the SESSION 165 watchdog surfaced
# ``"Drop a Wikipedia"`` as a multi-word match where "Drop"
# (sentence-initial common verb) + lowercase "a" + "Wikipedia"
# (real proper noun) parses as one entity. After this change
# the same input produces two single-token claims:
# ``Drop`` (caught by the stoplist) + ``Wikipedia`` (the real
# entity, correctly flagged if absent from chunks).
_MULTIWORD_CAPS_RE = re.compile(
    r"\b[A-Z][a-zA-Z]+(?:\s+(?:of|and|the|de|du|von)\s+[A-Z][a-zA-Z]+|\s+[A-Z][a-zA-Z]+)+\b"
)

# Pattern for single capitalized words 4+ chars. Run after
# multi-word so we don't double-extract.
_SINGLE_CAP_RE = re.compile(r"\b[A-Z][a-zA-Z]{3,}\b")

# Pattern for numeric claims — $X, X%, large numbers. Catches
# "$100 billion", "2020", "30 seconds".
_NUMERIC_RE = re.compile(
    r"\$\d[\d,]*(?:\.\d+)?(?:\s*(?:billion|million|trillion|thousand|k))?"
    r"|\b\d[\d,]*(?:\.\d+)?%"
    r"|\b\d{4}\b"  # standalone 4-digit numbers (years)
)

# K6.4 v2 — case-insensitive tech-name extractor. Built from
# ``KNOWN_TECH_TERMS`` so adding a name to the frozenset is the
# only edit needed. Word-boundary anchored so "post" in
# "postgres" doesn't match by accident.
def _build_tech_terms_re() -> re.Pattern[str]:
    if not KNOWN_TECH_TERMS:
        # Match nothing — defensive against an empty set.
        return re.compile(r"(?!)")
    # Sort longest-first so multi-word names (none in v2's set,
    # but future-safe) win over their prefixes.
    sorted_terms = sorted(KNOWN_TECH_TERMS, key=len, reverse=True)
    return re.compile(
        r"\b(?:" + "|".join(re.escape(t) for t in sorted_terms) + r")\b",
        re.IGNORECASE,
    )


_TECH_TERMS_RE = _build_tech_terms_re()


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class UnsupportedClaim:
    """A named entity in the script that has no support in the corpus."""
    claim: str
    kind: str  # "proper_noun" | "multi_word" | "numeric"
    position: int  # character offset in the script

    def to_dict(self) -> dict:
        return asdict(self)


class ClaimVerifierError(Exception):
    """Raised in Strict mode when at least one claim is unsupported.

    Carries both the unsupported claims AND the synthesized text
    that produced them (added K6.4.1). The text matters at the
    caller layer: when the primitive catches this exception and
    fails the composition, the operator needs to see *what the
    LLM said* to triage. Without it, the failure surface is just
    "rejected on terms X, Y" — no way to inspect context.
    """

    def __init__(
        self,
        unsupported: list[UnsupportedClaim],
        synthesized_text: str = "",
    ) -> None:
        self.unsupported = unsupported
        self.synthesized_text = synthesized_text
        summary = ", ".join(f"{c.claim!r} ({c.kind})" for c in unsupported)
        super().__init__(
            f"K6.4 claim verifier rejected the synthesized script: "
            f"{len(unsupported)} unsupported claim(s): {summary}"
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_verifier(
    text: str,
    *,
    corpus: str,
    mode: str | None = None,
) -> list[UnsupportedClaim]:
    """Verify ``text``'s claims against ``corpus``.

    Args:
        text: the synthesized script to check.
        corpus: the concatenation of retrieved chunks +
            spokesperson allow-list inputs. Built by
            :func:`build_corpus`.
        mode: ``"strict" | "warn" | "off"``. ``None`` reads
            ``settings.K6_CLAIM_VERIFIER_MODE`` (default ``"warn"``).

    Returns:
        List of ``UnsupportedClaim``s (empty in ``"off"`` mode
        and on clean text).

    Raises:
        ClaimVerifierError: in Strict mode when any claim is
            unsupported. Caller decides how to surface that
            (composition status = FAILED, PrimitiveError, etc).
    """
    resolved_mode = (mode or _get_default_mode()).lower()
    if resolved_mode == "off":
        return []
    if resolved_mode not in ("strict", "warn"):
        # Unknown mode — fall back to warn so the verifier
        # never silently disables itself.
        resolved_mode = "warn"

    unsupported = verify_claims(text, corpus=corpus)
    if resolved_mode == "strict" and unsupported:
        raise ClaimVerifierError(unsupported, synthesized_text=text)
    return unsupported


def verify_claims(text: str, *, corpus: str) -> list[UnsupportedClaim]:
    """Extract candidate entities from ``text`` and return any
    that don't appear in ``corpus``.

    Pure function — no mode handling, no exceptions. The
    caller picks the policy.
    """
    candidates = extract_named_entities(text)
    if not candidates:
        return []
    corpus_lower = corpus.lower()
    unsupported: list[UnsupportedClaim] = []
    for candidate in candidates:
        if candidate.claim.lower() in corpus_lower:
            continue
        unsupported.append(candidate)
    return unsupported


def extract_named_entities(text: str) -> list[UnsupportedClaim]:
    """Find named-entity-shaped tokens in ``text``.

    v1 catches:

    * Multi-word capitalized phrases (e.g. ``"Character OS"``,
      ``"James Webb Space Telescope"``).
    * Single capitalized words 4+ chars (e.g. ``"Wikipedia"``,
      ``"Trafilatura"``), filtered by a small stoplist of
      sentence-starter common English words.
    * Numeric claims (``"$100 billion"``, ``"2020"``,
      ``"30%"``).

    Known v1 false-negative: lowercase technology names
    (``"trafilatura"``, ``"pgvector"``). Add a v2 upgrade path
    that runs a small-model NER pass if false negatives
    motivate it.
    """
    if not text:
        return []

    found: dict[str, UnsupportedClaim] = {}
    matched_spans: list[tuple[int, int]] = []

    # 1) Multi-word capitalized phrases first — they take
    #    precedence so we don't extract their parts as singles.
    for match in _MULTIWORD_CAPS_RE.finditer(text):
        claim = match.group(0).strip()
        if claim in found:
            continue
        found[claim] = UnsupportedClaim(
            claim=claim,
            kind="multi_word",
            position=match.start(),
        )
        matched_spans.append((match.start(), match.end()))

    # 2) Single capitalized words 4+ chars.
    for match in _SINGLE_CAP_RE.finditer(text):
        # Skip if inside a multi-word match.
        if _span_overlaps(match.start(), match.end(), matched_spans):
            continue
        claim = match.group(0).strip()
        if claim.lower() in _COMMON_PROPER_NOUN_FALSE_POSITIVES:
            continue
        if claim in found:
            continue
        # K6.4 v2 — dedupe by lowercase form so casing variants
        # ("PyTorch" / "PYTORCH") collapse to one claim. Same
        # rule the tech-term extractor uses; applied here so
        # the two passes can't double-count the same entity.
        if any(claim.lower() == existing.lower() for existing in found):
            continue
        found[claim] = UnsupportedClaim(
            claim=claim,
            kind="proper_noun",
            position=match.start(),
        )

    # 3) Numeric tokens — always specific, never stoplisted.
    for match in _NUMERIC_RE.finditer(text):
        claim = match.group(0).strip()
        if claim in found:
            continue
        found[claim] = UnsupportedClaim(
            claim=claim,
            kind="numeric",
            position=match.start(),
        )

    # 4) K6.4 v2 — case-insensitive tech-name extraction.
    # Closes the SESSION 158 lowercase-tech-name miss
    # (``trafilatura`` slipped through v1 because the
    # capitalized-only single-cap regex doesn't see lowercase).
    # Skip if the same token is already extracted by an earlier
    # pass (e.g. "PyTorch" caught by single-cap regex).
    for match in _TECH_TERMS_RE.finditer(text):
        # Skip overlap with earlier matches.
        if _span_overlaps(match.start(), match.end(), matched_spans):
            continue
        claim = match.group(0).strip()
        # Dedupe by canonical lowercase form so "PyTorch" and
        # "pytorch" don't both register if the script mixes
        # cases.
        if claim in found:
            continue
        if any(claim.lower() == existing.lower() for existing in found):
            continue
        found[claim] = UnsupportedClaim(
            claim=claim,
            kind="tech_term",
            position=match.start(),
        )

    return sorted(found.values(), key=lambda c: c.position)


def build_corpus(
    chunks: Iterable,
    *,
    spokesperson: "Spokesperson | None" = None,
    operator_prompt: str = "",
    extras: Iterable[str] = (),
) -> str:
    """Concatenate the allow-list sources into one big lowercase
    haystack the verifier substring-matches against.

    The allow-list is intentionally generous: everything that
    *could* legitimately introduce a named entity into the
    synthesized script is in the corpus. False negatives are
    the safe failure mode (an unsupported claim slips through);
    false positives are the unsafe one (a legitimate claim
    gets flagged).

    Sources, in order:

    * Retrieved chunks (`chunk_text` on each).
    * Spokesperson name + business_brief.
    * Operator prompt (what the operator typed for *this*
      render — they're allowed to introduce terms).
    * KNOWN_PLATFORM_TERMS.
    * Caller-provided extras (e.g. workspace name).
    """
    parts: list[str] = []
    for chunk in chunks:
        text = getattr(chunk, "chunk_text", "") or ""
        if text:
            parts.append(text)
    if spokesperson is not None:
        name = getattr(spokesperson, "name", "") or ""
        if name:
            parts.append(name)
        brief = getattr(spokesperson, "business_brief", "") or ""
        if brief:
            parts.append(brief)
    if operator_prompt:
        parts.append(operator_prompt)
    parts.extend(KNOWN_PLATFORM_TERMS)
    parts.extend(extras)
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _span_overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    for s, e in spans:
        if start < e and end > s:
            return True
    return False


def is_sentence_initial(text: str, position: int) -> bool:
    """K6.4 v2 — true when ``position`` in ``text`` is the start of
    a new sentence.

    Used by the stoplist watchdog (SESSION 165) to classify
    flagged tokens: a sentence-initial flagged token is almost
    always a false-positive class (a capitalized common word at
    sentence start that looks proper-noun-shaped); a
    mid-sentence flagged token is almost always a true positive
    (the model named an entity not in the chunks).

    A position counts as sentence-initial when:

    * ``position == 0``, OR
    * the prior non-whitespace character is one of ``.!?:``
      (sentence-ending punctuation that may be followed by
      whitespace before the position).

    Edge cases:

    * Position pointing inside the text returns ``False`` for
      mid-sentence positions even after a period that's part of
      an abbreviation (the heuristic is intentionally aggressive
      on false positives — better to suggest a stoplist
      candidate that turns out to be a real entity than to miss
      a sentence-initial false positive).
    * Negative or out-of-range positions return ``False``.
    """
    if not text or position < 0 or position >= len(text):
        return False
    if position == 0:
        return True
    # Walk backwards past whitespace to find the previous
    # non-whitespace char.
    cursor = position - 1
    while cursor >= 0 and text[cursor].isspace():
        cursor -= 1
    if cursor < 0:
        return True  # only whitespace before — treat as start
    return text[cursor] in ".!?:"


def _get_default_mode() -> str:
    """Resolve the default verifier mode.

    Settings beats env, matching the ``RENDER_SCRIPT_FORCE_MOCK``
    pattern. Default is ``"warn"`` — the slice ships safe-by-
    default in the sense that the verifier runs and surfaces
    drift but doesn't break renders that the operator already
    tolerated under the pre-K6.4 contract.
    """
    settings_value = getattr(settings, "K6_CLAIM_VERIFIER_MODE", None)
    if settings_value:
        return str(settings_value).lower()
    env_value = os.environ.get("K6_CLAIM_VERIFIER_MODE", "").strip().lower()
    if env_value:
        return env_value
    return "warn"
