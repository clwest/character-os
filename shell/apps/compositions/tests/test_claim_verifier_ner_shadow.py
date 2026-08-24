"""K6.4 D-POS shadow classifier regression tests.

SESSION 278 Q-278-3.2 — pins the measured properties from the
Q-278-3.1 feasibility spike so any future edit to
``character_os.claim_verifier_ner`` declares its intent explicitly.

Tests DO NOT hit the ORM. The shadow classifier is a pure function
over ``(text, factual_corpus, allowed_vocabulary)`` so we exercise
it in isolation — no Composition rows created, no
``test_isolation.py`` allow-list change required.

Test skip semantics: if spaCy or ``en_core_web_sm`` is not
importable the entire module is skipped with a clear reason so CI
environments that opt out of the model still show a green run. In
the sanctioned local dev + CI setup (``pip install -e shell``) both
are installed as first-class dependencies (see ``shell/pyproject.toml``
§SESSION 278) and every test runs.
"""
from __future__ import annotations

import pytest

# Skip the entire module cleanly if spaCy or the model aren't
# importable. This defends both against a partial install
# (``pip install spacy`` but no model download) and against a CI env
# that deliberately excludes the model wheel.
spacy = pytest.importorskip("spacy")
try:
    _NLP = spacy.load("en_core_web_sm")
except OSError:
    pytest.skip(
        "en_core_web_sm not installed; K6.4 NER shadow tests skipped. "
        "Install via `pip install -e shell` (see shell/pyproject.toml).",
        allow_module_level=True,
    )

from character_os.claim_verifier_ner import (  # noqa: E402
    extract_named_entities_ner,
    run_shadow_verifier,
)


# Shared corpus fixture — represents the Fox & Flour + KNOWN_TECH_TERMS
# world used by the Q-278-3.1 measurements. Every test row keeps the
# corpus/vocabulary constant so a specimen's classification is a pure
# function of the text.
#
# Deliberately does NOT include Wikipedia / NASA / SpaceX / etc. —
# the "UNSUPPORTED ENTITIES MUST SHADOW-FLAG" tests below expect
# those names to be absent from the corpus so the grounding check
# produces an unsupported claim.
_CORPUS = (
    "Fox and Flour is a neighborhood artisan bakery. "
    "Fox and Flour is closed on Christmas Day. "
    "Trafilatura extracts HTML."
)
_ALLOWED_VOCAB = ["Ruby", "Tyson", "Character OS"]


def _flag_claims(text: str) -> set[str]:
    """Convenience: run the shadow verifier and return the set of
    ``claim`` strings it flagged."""
    return {
        w.claim for w in run_shadow_verifier(
            text,
            factual_corpus=_CORPUS,
            allowed_vocabulary=_ALLOWED_VOCAB,
        )
    }


# ---- ORDINARY LANGUAGE — must NOT shadow-flag ------------------------
# Q-278-1 class: sentence-initial ordinary English capitalized words.
# Legacy verifier flags these; D-POS must silence them (POS tags them
# ADV/ADJ/VERB/SCONJ/INTJ — not PROPN).


@pytest.mark.parametrize(
    "sentence",
    [
        "Fair enough.",
        "Come inside.",
        "Unless you disagree.",
        "Please sit down.",
        "Always check first.",
    ],
)
def test_ordinary_language_does_not_shadow_flag(sentence: str) -> None:
    """Sentence-initial ordinary English words must not surface as
    D-POS candidates. This is the Q-278-1 class the whole
    Q-278-3.x arc exists to close."""
    assert _flag_claims(sentence) == set(), (
        f"Q-278-1 regression: D-POS shadow flagged in {sentence!r}"
    )


# ---- UNSUPPORTED ENTITIES — must shadow-flag -------------------------
# Founding K6.4 invariant: unsupported named entities must surface.


@pytest.mark.parametrize(
    "sentence, expected_claim",
    [
        ("Antoninus reigned peacefully.", "Antoninus"),
        ("Wikipedia said something new today.", "Wikipedia"),
        ("NASA supplied the equipment.", "NASA"),
        ("France changed the rule.", "France"),
        ("Microsoft built it.", "Microsoft"),
        ("OpenAI released it.", "OpenAI"),
    ],
)
def test_unsupported_entities_shadow_flag(
    sentence: str, expected_claim: str,
) -> None:
    """Real unsupported named entities must remain flagged under
    D-POS — the founding K6.4 invariant is preserved."""
    claims = _flag_claims(sentence)
    assert expected_claim in claims, (
        f"D-POS lost the {expected_claim!r} flag in {sentence!r}. "
        f"Got: {claims}"
    )


# ---- SHORT ACRONYMS — must be candidates -----------------------------
# 1-3 char acronyms are silently missed by the legacy 4+ char regex.
# D-POS closes that class via PROPN + NER supplement.


@pytest.mark.parametrize(
    "sentence, expected_claim",
    [
        ("FBI called.", "FBI"),
        ("CIA is watching.", "CIA"),
        ("FDA approved it.", "FDA"),
        ("IRS audited us.", "IRS"),
    ],
)
def test_short_acronyms_shadow_flag(
    sentence: str, expected_claim: str,
) -> None:
    """3-char all-caps acronyms are PROPN + NER=ORG. D-POS surfaces
    them; the legacy 4+ char regex misses them silently."""
    claims = _flag_claims(sentence)
    assert expected_claim in claims, (
        f"D-POS missed the {expected_claim!r} short-acronym flag in "
        f"{sentence!r}. Got: {claims}"
    )


# ---- POLYSEMY — context-aware classification -------------------------


def test_polysemy_rose_person_flags() -> None:
    """`Rose baked` → PROPN → flag (person name). D-POS catches this
    even though spaCy's `doc.ents` alone misses `Rose` here."""
    assert "Rose" in _flag_claims("Rose baked the bread.")


def test_polysemy_rose_flower_does_not_flag() -> None:
    """`A rose bloomed` → lowercase `rose` tagged VERB (past tense)
    → not extracted."""
    assert _flag_claims("A rose bloomed.") == set()


def test_polysemy_mark_person_flags() -> None:
    """`Mark called` → PROPN + PERSON → flag."""
    assert "Mark" in _flag_claims("Mark called today.")


def test_polysemy_mark_verb_does_not_flag() -> None:
    """`Make a mark here` — lowercase `mark` as NOUN → not extracted."""
    assert _flag_claims("Make a mark here.") == set()


def test_polysemy_bill_person_flags() -> None:
    """`Bill approved` → PROPN + PERSON → flag. This is the KEY case
    Option B (static wordlist) would have gotten wrong — polysemous
    names common English words like `Bill`/`Rose`/`Mark`/`May` still
    flag when actually used as PERSON."""
    assert "Bill" in _flag_claims("Bill approved it.")


def test_polysemy_bill_noun_does_not_flag() -> None:
    """`Pay the bill` — lowercase `bill` as NOUN → not extracted."""
    assert _flag_claims("Pay the bill.") == set()


def test_polysemy_fair_idiom_does_not_flag() -> None:
    """`Fair enough` — sentence-initial `Fair` tagged ADV (adverb)
    → not extracted. Same specimen as the Q-278-1 Ruby/Tyson
    warning. Confirms the fix on the exact adversarial input."""
    assert _flag_claims("Fair enough.") == set()


# ---- DOCUMENTED RESIDUAL — May-as-person miss ------------------------


def test_may_as_person_currently_missed_documented_gap() -> None:
    """`May arrived.` (person named May) — spaCy tags `May` as
    AUX/MD (modal verb); NER labels DATE (not in the
    entity-relevant set). D-POS misses this case. Documented gap in
    SESSION_278_AUDIT.md §Q-278-3.1. Test pins the CURRENT behavior
    so a future "fix" surfaces intentionally, not accidentally."""
    assert _flag_claims("May arrived.") == set()


# ---- LOWERCASE TECH — KNOWN_TECH_TERMS coverage preserved ------------


@pytest.mark.parametrize(
    "sentence, expected_claim",
    [
        ("pgvector powers embeddings.", "pgvector"),
        ("redis caches the values.", "redis"),
    ],
)
def test_lowercase_tech_terms_still_flagged_via_known_tech_terms(
    sentence: str, expected_claim: str,
) -> None:
    """spaCy tags `pgvector` and `redis` as common NOUN (not PROPN),
    so the PROPN pass would miss them. The preserved
    ``KNOWN_TECH_TERMS`` pass must still catch them. Confirms the
    ``hybrid`` in D-POS Hybrid remains load-bearing for lowercase
    domain entities."""
    assert expected_claim in _flag_claims(sentence)


def test_numpy_lowercase_currently_missed_documented_gap() -> None:
    """`numpy` is NOT in `KNOWN_TECH_TERMS`. Under the pinned
    ``en_core_web_sm==3.8.0`` model, lowercase ``numpy`` is tagged
    ``NOUN`` (NOT PROPN — 3.8 changed this from 3.7's PROPN tagging).
    The PROPN pass therefore does NOT extract it and the shadow flag
    is silent — same behavior as legacy A. Test pins CURRENT
    behavior so any fix (e.g. adding ``numpy`` to ``KNOWN_TECH_TERMS``)
    surfaces intentionally, not accidentally.

    Note: capitalized ``Numpy`` DOES flag via PROPN + NER=NORP;
    that is not the operator-facing usage."""
    assert _flag_claims("numpy is fast.") == set()


# ---- FOUNDING HALLUCINATION INVARIANT --------------------------------


def test_founding_wikipedia_hallucination_still_flags() -> None:
    """The SESSION 158 canonical hallucination class. Corpus mentions
    Wikipedia only as an unrelated reference; a claim asserting a
    NEW proposition about it must still flag on the Wikipedia
    entity."""
    # Note: `Wikipedia` alone would substring-match the corpus. This
    # test is about the extraction PATH still emitting the entity so
    # the corpus check can gate it. Use a corpus WITHOUT `wikipedia`
    # for this one specimen to verify the entity flows through.
    unsupported = run_shadow_verifier(
        "Wikipedia is our absolute home turf.",
        factual_corpus="",  # deliberately empty for the invariant test
        allowed_vocabulary=[],
    )
    claims = {u.claim for u in unsupported}
    assert "Wikipedia" in claims


def test_founding_trafilatura_hallucination_still_flags() -> None:
    """SESSION 158 companion — lowercase tech name. Same shape: on an
    empty corpus, `trafilatura` must flow through as a candidate."""
    unsupported = run_shadow_verifier(
        "the library doing the work is called trafilatura.",
        factual_corpus="",
        allowed_vocabulary=[],
    )
    claims = {u.claim for u in unsupported}
    assert "trafilatura" in claims


# ---- MULTI-WORD ENTITIES (PROPN span extraction) ---------------------


def test_multiword_propn_span_extracts_full_span() -> None:
    """`James Webb Space Telescope` — contiguous PROPN run. D-POS
    should emit the FULL span as one multi_word_pos claim (spaCy's
    `doc.ents` truncates to `James Webb Space`; the PROPN span is
    what preserves accuracy)."""
    entities = extract_named_entities_ner(
        "James Webb Space Telescope launched.",
    )
    claim_texts = {e.claim for e in entities}
    assert "James Webb Space Telescope" in claim_texts


def test_multiword_supported_multi_word_passes() -> None:
    """`Fox and Flour is open.` — corpus mentions `Fox and Flour`.
    D-POS extracts `Fox` + `Flour` as two singletons (the `and`
    breaks the PROPN run) but both substring-match the corpus so
    neither is flagged."""
    claims = _flag_claims("Fox and Flour is open.")
    # Neither piece should end up as an unsupported claim.
    assert "Fox" not in claims
    assert "Flour" not in claims


# ---- EXTRACTOR MECHANICAL SHAPE --------------------------------------


def test_empty_text_returns_empty() -> None:
    """Defensive empty-input branch."""
    assert extract_named_entities_ner("") == []
    assert run_shadow_verifier(
        "", factual_corpus="anything", allowed_vocabulary=[],
    ) == []


def test_kind_labels_are_distinguishable() -> None:
    """Every extraction pass emits its own `kind` so downstream
    reporters (k64_shadow_diff, SPA panels) can tell them apart."""
    entities = extract_named_entities_ner(
        "Antoninus reigned in 1789. pgvector powers embeddings."
    )
    kinds = {e.kind for e in entities}
    assert "numeric" in kinds  # 1789
    assert "tech_term" in kinds  # pgvector via KNOWN_TECH_TERMS
    # Antoninus emitted as either proper_noun_pos or ner_*; both are D-POS.
    assert any(k.startswith("proper_noun_pos") or k.startswith("ner_") for k in kinds)


# ---- Q-278-4.1 — NER supplement POS=PROPN gate -----------------------
# The Q-278-3.2 fresh-window Specimen 4 surfaced ``Success`` (a common
# noun spaCy small-model NER mislabels as ORG) as a shadow-BOTH-parity
# noise entry. Q-278-4 §2 mechanically measured that requiring at
# least one PROPN token in the entity span closes the common-noun
# over-fire without regressing the short-acronym coverage the
# supplement was designed to provide. This block locks the gate.


def test_ner_supplement_rejects_success_common_noun_q278_4_1() -> None:
    """Canonical Q-278-3.2 Specimen 4 turn-3 shape. spaCy tags both
    occurrences of `success` as POS=NOUN but NER labels the
    capitalized one as ORG. Pre-gate the shadow verifier emitted
    `('Success', 'ner_org')`; post-gate the PROPN check rejects
    the span (POS=NOUN, not PROPN) so `Success` is NOT flagged."""
    text = (
        "Then success is not \"it picked an idea.\" Success is whether "
        "its suggestion helps us learn something without sending us "
        "halfway through three unrelated builds."
    )
    # Empty corpus so grounding cannot rescue a bad extraction —
    # any extracted candidate would appear in the returned list.
    unsupported = run_shadow_verifier(
        text, factual_corpus="", allowed_vocabulary=[],
    )
    claims = {u.claim for u in unsupported}
    assert "Success" not in claims, (
        f"Q-278-4.1 regression: NER-supplement PROPN gate should "
        f"reject common-noun ORG mislabel `Success`. Got: {claims}"
    )
    assert "success" not in claims  # lowercase form must not slip in either


@pytest.mark.parametrize(
    "sentence, acronym",
    [
        ("FBI called.", "FBI"),
        ("CIA is watching.", "CIA"),
        ("FDA approved it.", "FDA"),
        ("IRS audited us.", "IRS"),
    ],
)
def test_ner_supplement_preserves_short_acronyms_after_propn_gate_q278_4_1(
    sentence: str, acronym: str,
) -> None:
    """The Q-278-4.1 PROPN gate must NOT sacrifice short-acronym
    coverage. spaCy tags FBI/CIA/FDA/IRS as POS=PROPN + NER=ORG;
    the supplement should still emit them. This is the load-bearing
    non-regression guarantee for the gate: closing the ``Success``
    over-fire while keeping the sub-4-char class the supplement was
    designed for."""
    unsupported = run_shadow_verifier(
        sentence, factual_corpus="", allowed_vocabulary=[],
    )
    claims = {u.claim for u in unsupported}
    assert acronym in claims, (
        f"Q-278-4.1 regression: PROPN gate should NOT remove "
        f"short-acronym {acronym!r} in {sentence!r}. Got: {claims}"
    )


def test_ner_supplement_preserves_real_proper_noun_entities_q278_4_1() -> None:
    """Sanity net across the Q-278-4 §2 measured matrix: every real
    proper-noun entity spaCy identifies (regardless of label) has at
    least one PROPN token in its span and therefore survives the
    Q-278-4.1 gate. This test pins Wikipedia / NASA / France /
    Microsoft / OpenAI / Antoninus / Mark / Bill / James Webb Space
    Telescope / New York — the full Q-278-3.1 unsupported-entity
    matrix plus polysemous PERSON names + multi-word entities — as
    a single deterministic assertion."""
    for sentence, expected in [
        ("Wikipedia is our source.", "Wikipedia"),
        ("NASA supplied the equipment.", "NASA"),
        ("France changed the rule.", "France"),
        ("Microsoft built it.", "Microsoft"),
        ("OpenAI released it.", "OpenAI"),
        ("Antoninus reigned peacefully.", "Antoninus"),
        ("Mark called today.", "Mark"),
        ("Bill approved it.", "Bill"),
        ("James Webb Space Telescope launched.", "James Webb Space Telescope"),
        ("New York is far.", "New York"),
    ]:
        unsupported = run_shadow_verifier(
            sentence, factual_corpus="", allowed_vocabulary=[],
        )
        claims = {u.claim for u in unsupported}
        assert expected in claims, (
            f"Q-278-4.1 regression: PROPN gate should NOT remove "
            f"{expected!r} in {sentence!r}. Got: {claims}"
        )
