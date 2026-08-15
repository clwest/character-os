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
    from apps.spokespeople.models import Teammate


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
    # K6.4 v2 (SESSION 166) — CTA-verb false-positive class
    # surfaced by the real-Runway dogfood. K6 produced a
    # grounded technical reply ending in
    # "Want to see this? Reach out." — Want / Reach got
    # flagged because they're capitalized sentence-initial
    # imperatives. Stoplist additions cover the common
    # marketing CTA verb forms.
    "want", "wants", "wanted",
    "reach", "reaches", "reached",
    "need", "needs", "needed",
    "learn", "learns", "learned",
    "hear", "hears", "heard",
    "watch", "watches", "watched",
    "listen", "listens", "listened",
    "click", "clicks", "clicked",
    "sign", "signs", "signed",
    "join", "joins", "joined",
    "follow", "follows", "followed",
    "subscribe", "subscribes", "subscribed",
    "ready", "set", "go",
    "ping", "pings", "pinged",
    "email", "emails", "emailed",
    "call", "calls", "called",
    "visit", "visits", "visited",
    "check", "checks", "checked",
    "discover", "discovers", "discovered",
    "explore", "explores", "explored",
    "remember", "remembers", "remembered",
    "imagine", "imagines", "imagined",
    "picture", "pictures", "pictured",
    "consider", "considers", "considered",
    "skip", "skips", "skipped",
    "save", "saves", "saved",
    "share", "shares", "shared",
    "create", "creates", "created",
    "build", "builds", "built",
    "design", "designs", "designed",
    "send", "sends", "sent",
    "read", "reads",  # "read" is past tense too (same spelling)
    "say", "says", "said",
    "set", "sets",  # set already in list; duplicates are fine
    "leave", "leaves", "left",
    "keep", "keeps", "kept",
    "stay", "stays", "stayed",
    "wait", "waits", "waited",
    "pause", "pauses", "paused",
    "stop", "stops", "stopped",  # stop already in list
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
    # K6.4 v2.1 (SESSION 174) — sentence-initial time adverbs.
    # Real-mode K6 dogfood produced briefs starting "Today, ..."
    # ("Today, the 'Five Good Emperors'—and why many see their
    # era as a Roman golden age."). The verifier flagged "Today"
    # as a proper noun because it's 5 chars + capitalized at
    # sentence start. Time adverbs are common opening words in
    # marketing prose and are never proper nouns.
    "today", "tomorrow", "yesterday", "tonight",
    "lately", "recently",
    # K6.4 v2.1 — `think` was missing from the CTA-verbs class
    # added in v2 (SESSION 166). Dogfood found "Think Antoninus'
    # peaceful, Senate-sharing reign" — the imperative verb at
    # sentence start was concatenated with the real proper noun
    # that followed and flagged as a multi-word entity. With
    # `think` in the stoplist + the new sentence-initial-leader
    # demotion (see extract_named_entities), the multi-word
    # match drops and "Antoninus" alone flows to the single-cap
    # pass + corpus check.
    "think", "thinks", "thought", "thinking",
    # K6.4 v2.1 — sentence-opener prepositions that capitalize
    # at sentence start but are never proper nouns. Some of
    # these (``with``, ``from``) typically appear in the
    # retrieved corpus too so they wouldn't fail the substring
    # check; the stoplist entries are belt-and-suspenders for
    # the small-corpus edge cases (single-doc workspaces,
    # paraphrase queries that hit only narrow doc sections).
    "from", "with", "without", "through", "throughout",
    "between", "among", "across", "around", "within", "beyond",
    # K6.4 v2.2 (SESSION 175) — Donny K6 dogfood surfaced
    # "Respect HTML" (sentence-opener "Respect" + real tech
    # term "HTML"). Same exact shape as "Think Antoninus" that
    # v2.1 fixed; "respect" was just missing from the CTA-verb
    # set v2 (SESSION 166) introduced. Adding a tight batch of
    # common imperative CTA verbs that K6 emits in marketing
    # prose. Each entry is almost never a proper noun in
    # operator-facing text (would be flagged by the watchdog
    # if it turned out to be).
    "respect", "respects", "respected", "respecting",
    "protect", "protects", "protected", "protecting",
    "prepare", "prepares", "prepared", "preparing",
    "maintain", "maintains", "maintained", "maintaining",
    "include", "includes", "included", "including",
    "ensure", "ensures", "ensured", "ensuring",
    "verify", "verifies", "verified", "verifying",
    "focus", "focuses", "focused", "focusing",
    "avoid", "avoids", "avoided", "avoiding",
    "prioritize", "prioritizes", "prioritized", "prioritizing",
    "prefer", "prefers", "preferred", "preferring",
    "proceed", "proceeds", "proceeded", "proceeding",
    "treat", "treats", "treated", "treating",
    "handle", "handles", "handled", "handling",
    "choose", "chooses", "chose", "chosen", "choosing",
    "pick", "picks", "picked", "picking",
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
    factual_corpus: str,
    allowed_vocabulary: Iterable[str] = (),
    mode: str | None = None,
) -> list[UnsupportedClaim]:
    """Verify ``text``'s claims against factual evidence.

    SESSION 253 split — the corpus is now two distinct
    structures:

    * ``factual_corpus`` — evidence capable of supporting a
      factual claim. Retrieved K2 chunks + business_brief +
      who_you_help + what_you_sell. Built by
      :func:`build_factual_corpus`. Operator prompt is
      **NOT** in factual_corpus (creative briefs may contain
      unsupported assertions).
    * ``allowed_vocabulary`` — entity strings that should not
      independently trigger an ``UnsupportedClaim`` warning
      but which do **NOT** constitute factual evidence. Built
      by :func:`build_allowed_vocabulary`. Includes the
      spokesperson name, platform terms, and proper nouns
      the operator wrote into voice metadata fields.

    An entity present in ``allowed_vocabulary`` alone does
    NOT license a factual claim containing that entity. It
    only prevents a "hallucinated entity" false positive.

    Args:
        text: the synthesized script to check.
        factual_corpus: concatenated evidence text.
        allowed_vocabulary: entity strings allowed to appear
            without triggering the verifier (see above).
        mode: ``"strict" | "warn" | "off"``. ``None`` reads
            ``settings.K6_CLAIM_VERIFIER_MODE`` (default
            ``"warn"``).

    Returns:
        List of ``UnsupportedClaim``s (empty in ``"off"`` mode
        and on clean text).

    Raises:
        ClaimVerifierError: in Strict mode when any claim is
            unsupported.
    """
    resolved_mode = (mode or _get_default_mode()).lower()
    if resolved_mode == "off":
        return []
    if resolved_mode not in ("strict", "warn"):
        # Unknown mode — fall back to warn so the verifier
        # never silently disables itself.
        resolved_mode = "warn"

    unsupported = verify_claims(
        text,
        factual_corpus=factual_corpus,
        allowed_vocabulary=allowed_vocabulary,
    )
    if resolved_mode == "strict" and unsupported:
        raise ClaimVerifierError(unsupported, synthesized_text=text)
    return unsupported


def verify_claims(
    text: str,
    *,
    factual_corpus: str,
    allowed_vocabulary: Iterable[str] = (),
) -> list[UnsupportedClaim]:
    """Extract candidate entities from ``text`` and return any
    that neither appear in the factual corpus nor in the
    allowed vocabulary.

    Pure function — no mode handling, no exceptions. The
    caller picks the policy.

    Semantic distinction:

    * ``factual_corpus`` presence  → supported (surrounding claim
      is grounded, entity itself is fine).
    * ``allowed_vocabulary`` presence → NOT flagged (entity is
      allowed to appear) but the entity's presence does not
      license the surrounding claim as factually supported.
    * Neither → ``UnsupportedClaim``.
    """
    candidates = extract_named_entities(text)
    if not candidates:
        return []
    corpus_lower = factual_corpus.lower()
    allowed_lower = {
        v.strip().lower() for v in (allowed_vocabulary or ()) if v and v.strip()
    }
    unsupported: list[UnsupportedClaim] = []
    for candidate in candidates:
        needle = candidate.claim.lower()
        if needle in corpus_lower:
            continue
        # Allowed-vocabulary hit: substring match either way so
        # single-token allow-list entries match multi-word entities
        # containing them, and multi-word allow-list entries match
        # single-token substrings. Behaves like the flat-corpus
        # check did in K6.4 v1, just against a separate structure.
        if any(a in needle or needle in a for a in allowed_lower):
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
    #
    # K6.4 v2.1 (SESSION 174) — sentence-initial demotion:
    # when the leading word of a multi-word match is sentence-
    # initial AND in the common-words stoplist, drop just the
    # leader and let single-cap extraction handle the rest.
    # Closes the "Think Antoninus" dogfood case where an
    # imperative verb opener was concatenated with a real
    # proper noun and flagged as one multi-word entity. After
    # this change "Think Antoninus" produces zero multi_word
    # claims; "Antoninus" then flows through the single-cap
    # pass and matches the corpus correctly.
    for match in _MULTIWORD_CAPS_RE.finditer(text):
        claim = match.group(0).strip()
        first_word = claim.split(None, 1)[0]
        if (
            first_word.lower() in _COMMON_PROPER_NOUN_FALSE_POSITIVES
            and is_sentence_initial(text, match.start())
        ):
            # K6.4 v2.1 demotion — drop the stoplisted leader,
            # then re-extract the remainder. Two shapes to
            # preserve:
            #
            # 1) "Think Antoninus" — remainder is one cap word.
            #    Block the leader's span; let single-cap pick
            #    up "Antoninus" naturally.
            # 2) "The Federal Bureau of Investigation" —
            #    remainder is itself a multi-word proper-noun.
            #    Block the leader's span AND emit the remainder
            #    as a fresh multi_word claim so single-cap
            #    doesn't shred it into ("Federal", "Bureau",
            #    "Investigation").
            leader_end = match.start() + len(first_word)
            matched_spans.append((match.start(), leader_end))
            # Look for a multi-word match inside the remainder
            # of the original span (start after the leader's
            # trailing whitespace).
            remainder_start = leader_end
            while (
                remainder_start < match.end()
                and text[remainder_start].isspace()
            ):
                remainder_start += 1
            if remainder_start < match.end():
                sub_match = _MULTIWORD_CAPS_RE.search(
                    text, remainder_start, match.end(),
                )
                if sub_match:
                    sub_claim = sub_match.group(0).strip()
                    sub_start = sub_match.start()
                    sub_end = sub_match.end()
                    if sub_claim not in found:
                        found[sub_claim] = UnsupportedClaim(
                            claim=sub_claim,
                            kind="multi_word",
                            position=sub_start,
                        )
                        matched_spans.append((sub_start, sub_end))
            continue
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


def build_factual_corpus(
    chunks: Iterable,
    *,
    spokesperson: "Teammate | None" = None,
) -> str:
    """SESSION 253 — build the FACTUAL evidence corpus. Only
    sources capable of supporting a factual claim belong here.

    Included:

    * Retrieved K2 chunks (``chunk_text`` on each).
    * Teammate ``business_brief`` (business shape / facts).
    * Teammate ``who_you_help`` (audience shape — factual).
    * Teammate ``what_you_sell`` (offering shape — factual).

    Deliberately EXCLUDED:

    * Operator prompt — the creative brief may itself contain
      unsupported assertions (e.g. "make a video about how we
      are the highest-rated company in Colorado"). Treating
      the brief as evidence would silently ground its own
      assertions.
    * Teammate ``name`` — allowed vocabulary, not evidence.
      (Names appear via :func:`build_allowed_vocabulary`.)
    * ``personality`` / ``character_point_of_view`` — voice
      metadata, not evidence.
    * ``always_emphasize`` / ``never_say`` / ``desired_feeling``
      — brand positioning / prohibitions, not evidence. Any
      factual proposition in Brand Voice must be independently
      supported by this corpus.
    * ``voice_signature_phrases`` / ``voice_avoid_phrases`` —
      allowed vocabulary, not evidence.
    * ``KNOWN_PLATFORM_TERMS`` — allowed vocabulary, not
      evidence.

    Every excluded field is intentional. See the SESSION 253
    design doc for the full evidence / allowed-vocabulary
    boundary reasoning.
    """
    parts: list[str] = []
    for chunk in chunks:
        text = getattr(chunk, "chunk_text", "") or ""
        if text:
            parts.append(text)
    if spokesperson is not None:
        for field_name in ("business_brief", "who_you_help", "what_you_sell"):
            value = (getattr(spokesperson, field_name, "") or "").strip()
            if value:
                parts.append(value)
    return "\n\n".join(parts)


def build_allowed_vocabulary(
    *,
    spokesperson: "Teammate | None" = None,
    extras: Iterable[str] = (),
) -> list[str]:
    """SESSION 253 — build the ALLOWED VOCABULARY list. Entity
    strings that should not independently trigger an
    ``UnsupportedClaim`` warning but which do NOT constitute
    factual evidence for surrounding claims.

    Included:

    * Teammate ``name``.
    * ``KNOWN_PLATFORM_TERMS`` (Character OS, etc).
    * Caller-provided ``extras`` (typically the workspace name).
    * Proper nouns extracted from voice metadata fields as a
      false-negative safety valve (``personality``,
      ``character_point_of_view``, ``voice_signature_phrases``).
      Operators legitimately write named entities into these
      fields (role models, signature vocabulary); the verifier
      should not false-positive on them. Their presence does
      NOT license the surrounding factual claim.

    Deliberately EXCLUDED:

    * ``always_emphasize`` / ``never_say`` / ``desired_feeling``
      — brand positioning / prohibitions. If the operator wants
      a specific fact conveyed, it must appear in the factual
      corpus (via business_brief or knowledge).

    Returns a list (order preserved for deterministic prompt
    assembly). Callers substring-match case-insensitively.
    """
    tokens: list[str] = []
    seen: set[str] = set()

    def _push(token: str) -> None:
        clean = (token or "").strip()
        key = clean.lower()
        if clean and key not in seen:
            tokens.append(clean)
            seen.add(key)

    if spokesperson is not None:
        _push(getattr(spokesperson, "name", "") or "")
        # Voice-metadata proper-noun extraction — false-negative
        # safety valve only. Full free-text goes in, and the
        # extractor pulls capitalized tokens. Callers may match
        # substring so single tokens still hit.
        for source_field in (
            "personality",
            "character_point_of_view",
            "voice_signature_phrases",
        ):
            text = (getattr(spokesperson, source_field, "") or "").strip()
            if text:
                for entity in extract_named_entities(text):
                    _push(entity.claim)
    for term in KNOWN_PLATFORM_TERMS:
        _push(term)
    for extra in extras:
        _push(extra)
    return tokens


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
