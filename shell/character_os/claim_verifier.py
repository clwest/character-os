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
})


# Pattern for multi-word capitalized phrases: 2+ capitalized
# words in sequence (with optional joining lowercase article).
# Catches "Character OS", "James Webb Space Telescope".
_MULTIWORD_CAPS_RE = re.compile(
    r"\b[A-Z][a-zA-Z]+(?:\s+(?:of|and|the|a|an|de|du|von)\s+[A-Z][a-zA-Z]+|\s+[A-Z][a-zA-Z]+)+\b"
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
    """Raised in Strict mode when at least one claim is unsupported."""

    def __init__(self, unsupported: list[UnsupportedClaim]) -> None:
        self.unsupported = unsupported
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
        raise ClaimVerifierError(unsupported)
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
