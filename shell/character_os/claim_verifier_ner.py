"""K6.4 D-POS Hybrid — shadow-only NER-driven claim verifier.

SESSION 278 Q-278-3.2. Companion to :mod:`character_os.claim_verifier`.
Observational only — runs behind ``CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT``
and never influences render behavior. The current regex + stoplist
verifier remains authoritative.

Architecture (measured evidence in ``docs/design/SESSION_278_AUDIT.md``
§Q-278-3 and §Q-278-3.1):

* **Numeric pass** — reuses :data:`claim_verifier._NUMERIC_RE`. Regex
  is invariant under NER; no reason to rebuild.
* **KNOWN_TECH_TERMS pass** — reuses :data:`claim_verifier._TECH_TERMS_RE`.
  ``en_core_web_sm`` tags ``pgvector`` / ``redis`` as common NOUN
  (measured Q-278-3.1); the curated frozenset is the only pass that
  extracts them.
* **PROPN pass (NEW; replaces capitalization-as-NER)** — walks the
  spaCy document and emits contiguous ``token.pos_ == "PROPN"`` runs
  as claim candidates. Single-token runs are ``kind="proper_noun_pos"``;
  multi-token runs are ``kind="multi_word_pos"``. This is the load-
  bearing signal that closes the Q-278-1 false-positive class:
  ``Fair`` / ``Come`` / ``Unless`` / ``Please`` / ``Always`` are
  tagged ADV/ADJ/VERB/SCONJ/INTJ and are never emitted.
* **NER supplement (NEW; supplements PROPN)** — walks ``doc.ents``
  and emits any entity whose label is in
  :data:`_ENTITY_RELEVANT_LABELS`, whose span is not already covered
  by the PROPN pass, **and whose span contains at least one
  ``POS=PROPN`` token** (SESSION 278 Q-278-4.1 gate). This closes
  the sub-4-char acronym silent-miss class (``FBI``/``CIA``/``FDA``/
  ``IRS`` — all POS=PROPN, all correctly labeled ORG by spaCy) while
  rejecting the small-model NER's common-noun over-fires — the
  Q-278-3.2 Specimen 4 ``Success`` (POS=NOUN) is the canonical case
  the gate closes. Legacy single-cap regex missed the acronym class
  on the 4-char length gate; the PROPN-gated NER supplement adds a
  redundant belt for the same coverage without importing spaCy's
  ORG-on-capitalized-noun noise.
* **Grounding** — identical to the legacy verifier's
  :func:`claim_verifier.verify_claims`: candidate lowercased,
  ``needle in factual_corpus.lower()`` case-insensitive substring
  match; allowed-vocabulary substring-either-way fallback; miss
  ⇒ :class:`claim_verifier.UnsupportedClaim`.

The stoplist (``_COMMON_PROPER_NOUN_FALSE_POSITIVES``) is
**intentionally not consumed** by this classifier. Its job in the
legacy verifier is to fight the capitalization-as-NER proxy; PROPN
tagging obviates it. The stoplist stays alive in the legacy verifier
during the shadow-evaluation phase per Q-278-3.2 scope (do NOT clean
up the stoplist in this slice).

Failure modes to keep in mind (measured in Q-278-3.1, pinned by the
regression suite):

* ``May arrived.`` — spaCy tags ``May`` as AUX/MD (modal verb).
  PROPN pass MISSES it. NER labels it DATE (not in relevant labels).
  Documented residual false-negative; not "fixed" here.
* ``James Webb Space Telescope`` — spaCy's NER truncates the span to
  ``James Webb Space`` (PERSON). PROPN pass emits the FULL
  contiguous PROPN run ``James Webb Space Telescope`` as one
  multi_word_pos claim, so grounding correctness is preserved.
* ``Fox and Flour is open.`` — spaCy NER splits into ``Fox``(ORG) +
  ``Flour``(PERSON); PROPN pass emits ``Fox`` + ``Flour`` as two
  singletons because the coordinator ``and`` breaks the PROPN run.
  Case-insensitive corpus check on ``fox and flour`` still passes
  because both individual tokens hit the substring test — same
  behavior as the legacy verifier.

Reserved for a later slice (not this one):

* Loading spaCy at import time. Model cold-load is ~215 ms
  (Q-278-3.1) — imposed only on workers where the shadow flag is
  set. The lazy-load singleton in :func:`_get_nlp` handles this.
* Shadow-diff reporting — see ``apps/compositions/management/
  commands/k64_shadow_diff.py``.
"""
from __future__ import annotations

import logging
import os
from typing import Iterable

from django.conf import settings

from character_os.claim_verifier import (
    UnsupportedClaim,
    _NUMERIC_RE,
    _TECH_TERMS_RE,
    _span_overlaps,
)

logger = logging.getLogger(__name__)


_SHADOW_EXPERIMENT_ENV = "CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT"
_SHADOW_EXPERIMENT_SETTING = "CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT"


# spaCy `doc.ents` labels we treat as "named entity" for the invariant.
# Excluded on purpose: DATE / TIME / PERCENT / MONEY / QUANTITY /
# ORDINAL / CARDINAL — these are numeric-adjacent and either handled
# by the numeric pass or (like ``Today``) explicitly NOT the target
# of the named-entity grounding invariant.
_ENTITY_RELEVANT_LABELS: frozenset[str] = frozenset({
    "PERSON",
    "ORG",
    "GPE",
    "NORP",
    "FAC",
    "PRODUCT",
    "EVENT",
    "WORK_OF_ART",
    "LAW",
    "LANGUAGE",
})


def ner_shadow_experiment_active() -> bool:
    """Return ``True`` when the K6.4 NER shadow experiment is enabled.

    Precedence: Django settings → env var. Whitespace-only values count
    as inactive so operators can toggle off with
    ``export CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT=`` without a stale-
    value trap (mirrors :func:`avatar_speech._patch_communication_policy_experiment_active`).
    """
    setting_value = getattr(settings, _SHADOW_EXPERIMENT_SETTING, None)
    if isinstance(setting_value, bool):
        return setting_value
    if isinstance(setting_value, str) and setting_value.strip():
        return setting_value.strip().lower() not in {"0", "false", "no", "off"}
    env_value = os.environ.get(_SHADOW_EXPERIMENT_ENV, "").strip().lower()
    if not env_value:
        return False
    return env_value not in {"0", "false", "no", "off"}


# ---- Lazy spaCy singleton --------------------------------------------


_nlp = None
_nlp_load_attempted = False


def _get_nlp():
    """Lazy-load ``en_core_web_sm`` once per process.

    Returns the loaded ``Language`` pipeline, or ``None`` if spaCy /
    the model are unavailable (defensive — shadow mode must never
    disrupt production). The failure branch is logged once at WARNING
    then remembered so we don't spam the log on every turn.
    """
    global _nlp, _nlp_load_attempted
    if _nlp is not None:
        return _nlp
    if _nlp_load_attempted:
        return None
    _nlp_load_attempted = True
    try:
        import spacy  # noqa: WPS433 — deliberate lazy import
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Model not installed. Shadow classifier degrades to a
            # silent no-op; loud enough at WARNING that an operator
            # investigating shadow-empty diffs sees the reason.
            logger.warning(
                "K6.4 NER shadow: en_core_web_sm not installed; "
                "shadow verifier will return empty. Install via "
                "`pip install -e shell` (see shell/pyproject.toml)."
            )
            return None
    except ImportError:
        logger.warning(
            "K6.4 NER shadow: spaCy not importable; shadow verifier "
            "will return empty. Install via `pip install -e shell`."
        )
        return None
    return _nlp


# ---- Public entry point ----------------------------------------------


def run_shadow_verifier(
    text: str,
    *,
    factual_corpus: str,
    allowed_vocabulary: Iterable[str] = (),
) -> list[UnsupportedClaim]:
    """D-POS shadow verifier. Returns unsupported-claim candidates.

    Never raises. Returns an empty list on any failure path — spaCy
    missing, model missing, empty text, or exception during extraction.
    Callers persist the returned list into a shadow-only column;
    production behavior is unaffected.

    Grounding semantics are identical to
    :func:`claim_verifier.verify_claims`: case-insensitive substring
    against ``factual_corpus`` first, then substring-either-way
    against ``allowed_vocabulary``.

    Args:
        text: Synthesized text to shadow-verify.
        factual_corpus: Concatenated factual evidence (same shape the
            legacy verifier receives via
            :func:`claim_verifier.build_factual_corpus`).
        allowed_vocabulary: Whitelist entries (same shape the legacy
            verifier receives via
            :func:`claim_verifier.build_allowed_vocabulary`).
    """
    if not text:
        return []

    candidates = extract_named_entities_ner(text)
    if not candidates:
        return []

    corpus_lower = (factual_corpus or "").lower()
    allowed_lower = {
        v.strip().lower()
        for v in (allowed_vocabulary or ())
        if v and v.strip()
    }
    unsupported: list[UnsupportedClaim] = []
    for candidate in candidates:
        needle = candidate.claim.lower()
        if needle in corpus_lower:
            continue
        if any(a in needle or needle in a for a in allowed_lower):
            continue
        unsupported.append(candidate)
    return unsupported


def extract_named_entities_ner(text: str) -> list[UnsupportedClaim]:
    """Extract candidate entities via numeric + tech-term + PROPN + NER passes.

    Ordering intentionally chosen so downstream span-dedupe is simple:

    1. **Numeric** first — always specific, never overlaps with the
       cap-based passes.
    2. **KNOWN_TECH_TERMS** second — lowercase tech names spaCy
       doesn't tag PROPN. Registered spans block later passes.
    3. **PROPN spans** third — the load-bearing NER-replacement.
       Consecutive ``token.pos_ == "PROPN"`` runs become one claim.
       Skips any span that overlaps a numeric or tech-term span.
    4. **NER supplement** fourth — ``doc.ents`` labels in
       :data:`_ENTITY_RELEVANT_LABELS` that PROPN missed (mainly
       sub-4-char acronyms if spaCy tags them PROPN but the PROPN
       span dedupe caught them; when a PROPN token is inside a
       PERSON entity, it's already captured — this pass mainly
       covers unusual span shapes).

    Deduplication is span-based (position overlap) and text-based
    (case-insensitive) — same conventions as the legacy verifier.
    Empty text ⇒ empty list. spaCy missing ⇒ empty list.
    """
    nlp = _get_nlp()
    if nlp is None:
        return []

    try:
        doc = nlp(text)
    except Exception:  # noqa: BLE001 — shadow must not crash the caller
        logger.exception("K6.4 NER shadow: spaCy inference raised; returning empty")
        return []

    found: dict[str, UnsupportedClaim] = {}
    matched_spans: list[tuple[int, int]] = []

    def _emit(claim: str, kind: str, position: int, span: tuple[int, int]) -> None:
        # Case-insensitive dedupe on the claim text — matches the
        # legacy verifier's single-cap dedupe rule.
        lower_key = claim.lower()
        for existing in found:
            if existing.lower() == lower_key:
                return
        found[claim] = UnsupportedClaim(
            claim=claim,
            kind=kind,
            position=position,
        )
        matched_spans.append(span)

    # 1) Numeric — regex on the raw text.
    for match in _NUMERIC_RE.finditer(text):
        _emit(
            match.group(0).strip(),
            "numeric",
            match.start(),
            (match.start(), match.end()),
        )

    # 2) KNOWN_TECH_TERMS — regex on the raw text.
    for match in _TECH_TERMS_RE.finditer(text):
        if _span_overlaps(match.start(), match.end(), matched_spans):
            continue
        _emit(
            match.group(0).strip(),
            "tech_term",
            match.start(),
            (match.start(), match.end()),
        )

    # 3) PROPN spans — contiguous PROPN runs from spaCy.
    i = 0
    tokens = list(doc)
    while i < len(tokens):
        tok = tokens[i]
        if tok.pos_ != "PROPN":
            i += 1
            continue
        # Grow the run through consecutive PROPN tokens.
        j = i + 1
        while j < len(tokens) and tokens[j].pos_ == "PROPN":
            j += 1
        # Character span for the run: from first token's idx to end of
        # last token's idx + len.
        start_char = tok.idx
        last = tokens[j - 1]
        end_char = last.idx + len(last.text)
        if _span_overlaps(start_char, end_char, matched_spans):
            i = j
            continue
        span_text = text[start_char:end_char]
        # Choose kind by token count; singletons vs multi-word runs.
        kind = "proper_noun_pos" if (j - i) == 1 else "multi_word_pos"
        _emit(span_text, kind, start_char, (start_char, end_char))
        i = j

    # 4) NER supplement — entity labels PROPN might not cover.
    #
    # SESSION 278 Q-278-4.1 — POS=PROPN gate on the supplement.
    # The Q-278-3.2 fresh dogfood surfaced ``Success`` (Specimen 4
    # turn 3) as a spaCy NER=ORG label on a common noun (POS=NOUN).
    # Without a gate, the supplement pass emits `Success` as a
    # ``ner_org`` candidate — an over-fire on capitalized common
    # nouns that the small-model NER routinely mislabels.
    #
    # Q-278-4 §2 mechanically measured this: requiring at least one
    # PROPN token in the entity span rejects the ``Success`` over-
    # fire while preserving every short-acronym target
    # (FBI/CIA/FDA/IRS — all POS=PROPN) and every real proper-noun
    # case tested (PERSON/ORG/GPE spans on Wikipedia, NASA, France,
    # Microsoft, OpenAI, Mark, Bill, Antoninus, James Webb Space
    # Telescope, New York, ...).
    #
    # This is Q-278-4 Slice 1 — non-authority-changing correction.
    # No dispatcher, no schema change, no strict-mode change.
    for ent in doc.ents:
        if ent.label_ not in _ENTITY_RELEVANT_LABELS:
            continue
        if _span_overlaps(ent.start_char, ent.end_char, matched_spans):
            continue
        # Require at least one PROPN token in the entity span.
        # spaCy tags real proper nouns (short acronyms + real
        # names) as PROPN; common-noun ORG mislabels
        # (``Success``, ``Coffee``, ``Bread``, etc.) fail this
        # gate and are correctly excluded from the supplement.
        if not any(tok.pos_ == "PROPN" for tok in ent):
            continue
        _emit(
            ent.text.strip(),
            f"ner_{ent.label_.lower()}",
            ent.start_char,
            (ent.start_char, ent.end_char),
        )

    return sorted(found.values(), key=lambda c: c.position)


__all__ = [
    "extract_named_entities_ner",
    "ner_shadow_experiment_active",
    "run_shadow_verifier",
]
