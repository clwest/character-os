"""K6.4 (SESSION 159) — post-synthesis claim verifier tests.

Covers ``character_os.claim_verifier``:

* Named-entity extraction (multi-word phrases, single
  capitalized words, numerics) catches Donny's actual script.
* Common-word stoplist prevents false positives on sentence
  starters like "Turns", "When", "Drop".
* ``KNOWN_PLATFORM_TERMS`` allow-lists "Character OS".
* ``build_factual_corpus`` concatenates chunks + spokesperson context
  + operator prompt.
* ``verify_claims`` returns unsupported claims when the
  corpus has nothing supporting them.
* Mode handling: ``"strict"`` raises ``ClaimVerifierError``,
  ``"warn"`` returns the list, ``"off"`` returns empty.
* Integration through ``build_render_brief`` — the synthesized
  brief feeds the verifier, warnings come back on
  ``ScriptResult``.
* Strict-mode integration: ``build_render_brief`` raises
  ``ClaimVerifierError`` when Strict and there are unsupported
  claims.
* Regression smoke: Donny's exact script (SESSION 158 first
  marketing video) flagged against the actual Wikipedia-RAG
  chunks the operator attached.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Teammate
from character_os.claim_verifier import (
    KNOWN_PLATFORM_TERMS,
    ClaimVerifierError,
    UnsupportedClaim,
    build_allowed_vocabulary,
    build_factual_corpus,
    extract_named_entities,
    is_sentence_initial,
    run_verifier,
    verify_claims,
)
from character_os.script_synthesis import build_render_brief

User = get_user_model()


# Donny's actual script from SESSION 158 (Composition
# e485d9f9-e711-4402-8bc5-a543c0315847). Locked into the test
# so the K6.4 regression is anchored to the real event.
DONNY_ACTUAL_SCRIPT = (
    "I was sitting down with the Character OS team last week. "
    "They were showing me how their knowledge layer ingests web "
    "pages. Turns out, when you paste a Wikipedia link, the "
    "library doing the work is called trafilatura — and Wikipedia "
    "is its absolute home turf. Cleanest text extraction you'll "
    "see from any AI tool. That is the kind of detail you only "
    "catch when you stop and listen."
)

# A small slice of the actual Wikipedia RAG doc content
# (KnowledgeDocument 33c07feb-...). Confirmed via Django shell
# during SESSION 159 forensics that this doc has zero
# occurrences of "trafilatura" and zero of "Wikipedia".
RAG_DOC_EXCERPT = (
    "Retrieval-augmented generation (RAG) is a technique that "
    "enables large language models (LLMs) to retrieve and "
    "incorporate new information from external data sources. "
    "RAG improves LLMs by incorporating information retrieval "
    "before generating responses. IBM states that RAG augments "
    "the prompt. Ars Technica and MIT Technology Review have "
    "written about the technique."
)


# ---------------------------------------------------------------
# Pure-function tests — no Django needed for these
# ---------------------------------------------------------------


class _FakeChunk:
    """Lightweight chunk stand-in. The verifier only reads
    ``chunk_text`` so we don't need a real ORM row."""

    def __init__(self, text: str) -> None:
        self.chunk_text = text


def test_extract_finds_wikipedia_in_donnys_script() -> None:
    """The exact entity that exposed the K6.4 failure mode."""
    entities = extract_named_entities(DONNY_ACTUAL_SCRIPT)
    claims = {e.claim for e in entities}
    assert "Wikipedia" in claims, claims


def test_extract_finds_character_os_multiword() -> None:
    """Multi-word capitalized phrase — Character OS."""
    entities = extract_named_entities(DONNY_ACTUAL_SCRIPT)
    claims = {e.claim for e in entities}
    assert "Character OS" in claims, claims


def test_extract_skips_common_sentence_starters() -> None:
    """'Turns out', 'Cleanest text', 'That is', 'When' — none
    of these should be extracted. Stoplist guards them."""
    entities = extract_named_entities(DONNY_ACTUAL_SCRIPT)
    claims = {e.claim for e in entities}
    for noise in {"Turns", "Cleanest", "That", "When", "They"}:
        assert noise not in claims, f"false-positive: {noise} in {claims}"


def test_extract_now_catches_lowercase_trafilatura_k6_4_v2() -> None:
    """K6.4 v2 (SESSION 166) — closes the SESSION 158
    canonical case. Lowercase tech names that v1 missed
    (trafilatura was the original example) now extract via
    ``KNOWN_TECH_TERMS``. The historical test name
    ``test_extract_misses_lowercase_trafilatura_known_v1_gap``
    was the inverse assertion — kept here as documentation
    of the calibration shift."""
    entities = extract_named_entities(DONNY_ACTUAL_SCRIPT)
    claims = {e.claim for e in entities}
    assert "trafilatura" in claims
    # Kind should be the v2 ``tech_term`` taxonomy so the
    # operator can distinguish how it was caught.
    trafilatura_entity = next(e for e in entities if e.claim == "trafilatura")
    assert trafilatura_entity.kind == "tech_term"


def test_known_tech_terms_case_insensitive_k6_4_v2() -> None:
    """v2 — tech terms match regardless of casing."""
    text = "We use PyTorch, pytorch, and PYTORCH consistently."
    entities = extract_named_entities(text)
    # All three should produce *one* claim (dedupe by lowercase).
    matching = [e for e in entities if e.claim.lower() == "pytorch"]
    assert len(matching) == 1


def test_multiword_no_longer_greedy_with_lowercase_a_k6_4_v2() -> None:
    """v2 — ``a`` and ``an`` are no longer multi-word joining
    words. The watchdog flagged ``"Drop a Wikipedia"`` as a
    multi-word entity in SESSION 165. After this tightening
    the same text produces two single-token claims instead."""
    text = "Drop a Wikipedia link to start."
    entities = extract_named_entities(text)
    claims = {e.claim for e in entities}
    assert "Drop a Wikipedia" not in claims
    # Drop is in the stoplist so it's silently dropped.
    # Wikipedia survives as the only flagged entity.
    assert "Wikipedia" in claims


def test_multiword_still_catches_genuine_multiword_proper_nouns_k6_4_v2() -> None:
    """v2 regression check — tightening the joining words
    didn't break legitimate multi-word proper-noun extraction.
    ``Federal Bureau of Investigation`` still works because
    ``of`` stays in the joining set. (The greedy regex
    captures the leading "The" too; that's fine because the
    substring corpus match operates on the whole claim and
    the leading article doesn't affect verification.)"""
    entities = extract_named_entities(
        "The Federal Bureau of Investigation issued a report."
    )
    claims = {e.claim for e in entities}
    assert any("Federal Bureau of Investigation" in c for c in claims)


def test_stoplist_alright_k6_4_v2() -> None:
    """v2 — watchdog-surfaced false positive from SESSION 164
    dogfood. ``Alright`` at sentence start no longer flags."""
    entities = extract_named_entities("Alright — the docs say RAG.")
    claims = {e.claim for e in entities}
    assert "Alright" not in claims


def test_stoplist_cta_verbs_k6_4_v2_dogfood() -> None:
    """v2 — CTA-verb false positives surfaced by the SESSION 166
    real-Runway dogfood. K6 produced a grounded reply ending
    in "Want to see this? Reach out." Both verbs were
    sentence-initial imperatives, not proper nouns. The full
    CTA-verb set ships in this commit."""
    text = (
        "Want to see this in action? Reach out and we'll demo. "
        "Need help? Learn more on the site. Watch the intro. "
        "Click below. Sign up today. Join us. Follow along. "
        "Subscribe for updates. Visit the docs. Discover what's new."
    )
    entities = extract_named_entities(text)
    claims = {e.claim for e in entities}
    for cta in {
        "Want", "Reach", "Need", "Learn", "Watch",
        "Click", "Sign", "Join", "Follow", "Subscribe",
        "Visit", "Discover",
    }:
        assert cta not in claims, f"K6.4 v2 CTA false-positive: {cta} in {claims}"


# ---- K6.4 v2.1 (SESSION 174) — sentence-opener fixes -------------


def test_stoplist_time_adverbs_k6_4_v2_1() -> None:
    """v2.1 — time adverbs at sentence start. Real K6 dogfood
    produced briefs starting "Today, the Five Good Emperors..."
    and the verifier flagged "Today" as a proper noun."""
    text = (
        "Today, the workspace is live. Tomorrow we ship. "
        "Yesterday we shipped. Tonight we celebrate. "
        "Lately the trend is up. Recently we hit our goal."
    )
    entities = extract_named_entities(text)
    claims = {e.claim for e in entities}
    for opener in {"Today", "Tomorrow", "Yesterday", "Tonight",
                   "Lately", "Recently"}:
        assert opener not in claims, (
            f"K6.4 v2.1 time-adverb false-positive: {opener} in {claims}"
        )


def test_multiword_demotes_sentence_initial_stoplisted_leader_k6_4_v2_1() -> None:
    """v2.1 — the canonical dogfood case. When a multi-word
    match starts at sentence-initial AND its leading word is
    in the stoplist, the leader should be dropped and the
    remainder should fall through to single-cap extraction.

    Input shape lifted from the SESSION 174 K6 brief:
    "Think Antoninus' peaceful, Senate-sharing reign..."
    "Think" (imperative verb opener) + "Antoninus" (real
    proper noun) used to flag as one multi_word entity.
    After the fix: zero multi_word, one proper_noun for
    "Antoninus" which will be checked against the corpus.
    """
    text = (
        "Gibbon called their rule absolute power guided by virtue. "
        "Think Antoninus' peaceful reign and Marcus as a gifted "
        "administrator."
    )
    entities = extract_named_entities(text)
    claims_by_kind = {(e.kind, e.claim) for e in entities}
    # No "Think Antoninus" as multi_word.
    assert ("multi_word", "Think Antoninus") not in claims_by_kind
    # "Antoninus" surfaces alone as a proper_noun.
    assert ("proper_noun", "Antoninus") in claims_by_kind
    # "Think" itself doesn't survive either (stoplisted).
    assert ("proper_noun", "Think") not in claims_by_kind


def test_multiword_demotes_only_at_sentence_initial_k6_4_v2_1() -> None:
    """v2.1 — the demotion fires ONLY at sentence-initial.
    Mid-sentence multi-word matches are unaffected.

    "remember Marcus Aurelius" would only ever appear mid-
    sentence as a phrase (operator-typed prompt or model
    output). The demotion logic must NOT strip "remember"
    here — the v1 multi-word regex doesn't match "remember
    Marcus" anyway because "remember" is lowercase, but the
    invariant matters: even if the operator writes
    "...if we Remember Marcus Aurelius...", the mid-sentence
    capitalized "Remember" shouldn't trigger demotion."""
    # Construct a mid-sentence multi-word that starts with a
    # stoplisted word. Capitalize "Remember" to satisfy the
    # multi-word regex, then put it mid-sentence (after a comma,
    # not a period).
    text = "Yes, Remember Marcus Aurelius once said something."
    entities = extract_named_entities(text)
    claims_by_kind = {(e.kind, e.claim) for e in entities}
    # Mid-sentence: the multi-word match survives.
    assert ("multi_word", "Remember Marcus Aurelius") in claims_by_kind


def test_stoplist_cta_verbs_k6_4_v2_2_dogfood() -> None:
    """K6.4 v2.2 (SESSION 175) — Donny multi-cast K6.6 dogfood
    surfaced "Respect HTML" (sentence-opener verb + real tech
    term) flagged as multi_word. Same shape as v2.1's
    "Think Antoninus" case; "respect" was just missing from
    the CTA-verb stoplist. v2.2 ships a tight batch of common
    imperative verbs that K6 emits in marketing prose."""
    # Construct sentences that put each new verb at the
    # sentence-initial position followed by a real entity.
    text = (
        "Respect HTML structure. Protect Wikipedia citations. "
        "Prepare RAG corpora carefully. Maintain Postgres indexes. "
        "Include Trafilatura output as a fallback. "
        "Ensure pgvector schemas match. "
        "Verify React renders against fixtures. "
        "Focus Stripe pipelines on cohorts. "
        "Avoid GraphQL n+1 issues. "
        "Prioritize Redis cache hits."
    )
    entities = extract_named_entities(text)
    claims = {(e.kind, e.claim) for e in entities}
    # None of the imperative-verb + entity pairs should be
    # extracted as multi_word — the demotion logic from
    # v2.1 plus the v2.2 stoplist additions should strip
    # the verb leaders cleanly.
    forbidden_pairs = {
        "Respect HTML", "Protect Wikipedia", "Prepare RAG",
        "Maintain Postgres", "Include Trafilatura",
        "Ensure pgvector", "Verify React",
        "Focus Stripe", "Avoid GraphQL", "Prioritize Redis",
    }
    for pair in forbidden_pairs:
        assert ("multi_word", pair) not in claims, (
            f"K6.4 v2.2 missed multi-word demotion for {pair!r} "
            f"in claims {sorted(claims)}"
        )
    # And the verbs themselves shouldn't be flagged as
    # proper_nouns either.
    for verb in {"Respect", "Protect", "Prepare", "Maintain",
                 "Include", "Ensure", "Verify", "Focus",
                 "Avoid", "Prioritize"}:
        assert ("proper_noun", verb) not in claims, (
            f"K6.4 v2.2 stoplist missed verb {verb!r}"
        )


def test_multiword_demotion_full_session_174_brief_k6_4_v2_1() -> None:
    """v2.1 regression — full brief from SESSION 174 dogfood,
    with a corpus that genuinely supports every real claim.
    After the fixes, verify_claims should return EMPTY."""
    brief = (
        "Today, the \"Five Good Emperors\"—and why many see their "
        "era as a Roman golden age. From 96 to 180 AD, Nerva, "
        "Trajan, Hadrian, Antoninus Pius, and Marcus Aurelius "
        "mostly chose successors by adoption. Machiavelli praised "
        "this. Gibbon called their rule absolute power guided by "
        "wisdom and virtue. Think Antoninus' peaceful, "
        "Senate-sharing reign and Marcus as an unpretentious, "
        "gifted administrator—before the shift to a birth heir, "
        "Commodus, in 180."
    )
    # Corpus shape matches what the real Nerva-Antonine chunks
    # contain — all the real proper nouns appear, including the
    # numeric "180" + "96" year markers.
    corpus = (
        "Nerva Trajan Hadrian Antoninus Pius Marcus Aurelius "
        "Machiavelli Gibbon Commodus Roman Senate "
        "Five Good Emperors 96 180 AD adoption "
    )
    unsupported = verify_claims(brief, factual_corpus=corpus)
    assert unsupported == [], (
        f"K6.4 v2.1 regression — expected zero unsupported "
        f"claims, got: {[(u.kind, u.claim) for u in unsupported]}"
    )


def test_is_sentence_initial_position_zero() -> None:
    assert is_sentence_initial("Wikipedia is great.", 0) is True


def test_is_sentence_initial_after_period_and_space() -> None:
    text = "I like RAG. Wikipedia is great."
    # Position 12 == 'W' of "Wikipedia" (after ". ")
    assert text[12] == "W"
    assert is_sentence_initial(text, 12) is True


def test_is_sentence_initial_after_question_mark() -> None:
    text = "What's RAG? Wikipedia explains it."
    pos = text.index("Wikipedia")
    assert is_sentence_initial(text, pos) is True


def test_is_sentence_initial_mid_sentence_returns_false() -> None:
    text = "I love Wikipedia."
    pos = text.index("Wikipedia")
    assert is_sentence_initial(text, pos) is False


def test_is_sentence_initial_handles_only_whitespace_before() -> None:
    text = "   Wikipedia"
    pos = text.index("Wikipedia")
    assert is_sentence_initial(text, pos) is True


def test_is_sentence_initial_handles_negative_position() -> None:
    assert is_sentence_initial("text", -1) is False


def test_is_sentence_initial_handles_out_of_range() -> None:
    assert is_sentence_initial("text", 100) is False


def test_extract_skips_refusal_pattern_starters_k6_5() -> None:
    """K6.5 dogfood finding (SESSION 162): refusal-pattern
    sentence starters should not flag. The model saying "Short
    answer: I don't know which library..." is honest, not a
    hallucination. The verifier exists to catch invented
    claims, not punish honest meta-language."""
    text = (
        "Short answer: the docs don't say. Which library does the "
        "parsing? Frankly, I don't know. Honestly, I'd rather not "
        "guess. Instead, here's what the docs do say. Plain answer: "
        "I can't tell you. Fine — try a different question. Both "
        "options have tradeoffs. Many people ask this."
    )
    entities = extract_named_entities(text)
    claims = {e.claim for e in entities}
    for noise in {
        "Short", "Which", "Frankly", "Honestly", "Instead",
        "Plain", "Fine", "Both", "Many",
    }:
        assert noise not in claims, f"K6.5 refusal false-positive: {noise} in {claims}"


def test_extract_skips_sentence_initial_adjectives_k6_4_1() -> None:
    """K6.4.1 — adjectives like 'Modern', 'Digital', 'Simple' at
    sentence starts must not be flagged. Triggered by the
    SESSION 161 strict-mode dogfood where 'Modern' rejected a
    legitimate render. Each adjective in this list got a real
    render to confirm — keep the list aligned with the stoplist."""
    text = (
        "Modern AI tools change quickly. Digital platforms ship "
        "weekly. Simple workflows scale better. Advanced features "
        "come later. Basic plans suit most teams. Smart caching "
        "saves money. Classic patterns still apply. Premium tiers "
        "unlock power."
    )
    entities = extract_named_entities(text)
    claims = {e.claim for e in entities}
    for adj in {
        "Modern", "Digital", "Simple", "Advanced",
        "Basic", "Smart", "Classic", "Premium",
    }:
        assert adj not in claims, f"K6.4.1 false-positive: {adj} in {claims}"


def test_extract_finds_numerics() -> None:
    text = "We're seeing a 30% lift, $100 billion in revenue, in 2020."
    entities = extract_named_entities(text)
    claims = {e.claim for e in entities}
    assert "30%" in claims
    assert "$100 billion" in claims
    assert "2020" in claims


def test_extract_dedupes_repeat_mentions() -> None:
    """Wikipedia appears twice in Donny's script; one
    UnsupportedClaim is returned (the first position)."""
    entities = extract_named_entities(DONNY_ACTUAL_SCRIPT)
    wikipedias = [e for e in entities if e.claim == "Wikipedia"]
    assert len(wikipedias) == 1


def test_build_factual_corpus_concatenates_chunks() -> None:
    chunks = [_FakeChunk("Alpha content"), _FakeChunk("Beta content")]
    corpus = build_factual_corpus(chunks)
    assert "Alpha content" in corpus
    assert "Beta content" in corpus


def test_build_factual_corpus_does_not_include_platform_terms() -> None:
    """SESSION 253 — platform terms are ALLOWED VOCABULARY (they
    do not independently trigger a warning) but are NOT factual
    evidence. Moving them out of the factual corpus is the point
    of the K6.4 evidence-boundary split."""
    corpus = build_factual_corpus([])
    for term in KNOWN_PLATFORM_TERMS:
        assert term not in corpus
    # ... and they land in the allowed vocabulary instead.
    allowed = build_allowed_vocabulary()
    for term in KNOWN_PLATFORM_TERMS:
        assert term in allowed


def test_build_factual_corpus_includes_business_brief_and_shape_fields() -> None:
    """SESSION 253 — factual corpus contains business_brief +
    who_you_help + what_you_sell. Voice / brand fields (name,
    personality, always_emphasize, etc.) are NOT factual
    evidence."""
    class _FakeSp:
        name = "Riggs"
        business_brief = "Founder voice for the donkey brand."
        who_you_help = "Small ranches in the west."
        what_you_sell = "Coaching packages."
        personality = "Blunt, direct, likes short sentences."
        always_emphasize = "Rigorous rewrite process."
        never_say = "cheapest"
        desired_feeling = "understood"

    corpus = build_factual_corpus(
        [_FakeChunk("chunk text")], spokesperson=_FakeSp(),
    )
    assert "chunk text" in corpus
    assert "donkey brand" in corpus
    assert "Small ranches" in corpus
    assert "Coaching packages" in corpus
    # Name is NOT factual evidence — belongs to allowed vocab.
    assert "Riggs" not in corpus
    # Voice / brand metadata is NOT factual evidence.
    assert "Blunt" not in corpus
    assert "Rigorous rewrite" not in corpus
    assert "cheapest" not in corpus
    assert "understood" not in corpus


def test_build_factual_corpus_signature_refuses_operator_prompt() -> None:
    """SESSION 253 correction 1 — the operator's creative brief
    may itself contain unsupported assertions (e.g. 'make a
    video about how we are the highest-rated company'). The
    signature must not accept it as a factual source."""
    import inspect

    sig = inspect.signature(build_factual_corpus)
    assert "operator_prompt" not in sig.parameters, (
        "SESSION 253: operator_prompt must not be a factual source"
    )


def test_build_allowed_vocabulary_includes_name_and_platform_terms() -> None:
    """Names and platform terms are allowed vocabulary — appear
    without triggering the verifier, but do NOT license
    surrounding factual claims."""
    class _FakeSp:
        name = "Riggs"
        business_brief = "brief"
        who_you_help = ""
        what_you_sell = ""
        personality = ""
        character_point_of_view = ""
        voice_signature_phrases = ""

    allowed = build_allowed_vocabulary(spokesperson=_FakeSp())
    assert "Riggs" in allowed
    for term in KNOWN_PLATFORM_TERMS:
        assert term in allowed


def test_build_allowed_vocabulary_extracts_from_voice_metadata() -> None:
    """SESSION 253 — proper nouns from personality /
    character_point_of_view / voice_signature_phrases enter the
    allowed vocabulary as a false-negative safety valve. They
    are NOT factual evidence — the surrounding claim still needs
    factual support."""
    class _FakeSp:
        name = "N"
        business_brief = ""
        who_you_help = ""
        what_you_sell = ""
        personality = "Writes with the cadence of Marcus Aurelius."
        character_point_of_view = "Believes Camelback bottles are overrated."
        voice_signature_phrases = "come curious"

    allowed = build_allowed_vocabulary(spokesperson=_FakeSp())
    joined_lower = " ".join(a.lower() for a in allowed)
    assert "marcus aurelius" in joined_lower
    assert "camelback" in joined_lower


def test_build_allowed_vocabulary_excludes_brand_voice_fields() -> None:
    """SESSION 253 — brand voice (always_emphasize / never_say /
    desired_feeling) is neither factual evidence nor allowed
    vocabulary. If the operator wants a specific fact conveyed,
    it must appear in the factual corpus."""
    class _FakeSp:
        name = "N"
        business_brief = ""
        who_you_help = ""
        what_you_sell = ""
        personality = ""
        character_point_of_view = ""
        voice_signature_phrases = ""
        always_emphasize = "Boulder Roasters — family-owned since 1987."
        never_say = "Blue Bottle"
        desired_feeling = "unhurried Boulder mornings"

    allowed = build_allowed_vocabulary(spokesperson=_FakeSp())
    joined_lower = " ".join(a.lower() for a in allowed)
    assert "boulder roasters" not in joined_lower
    assert "blue bottle" not in joined_lower


def test_verify_claims_donny_against_rag_doc_flags_wikipedia() -> None:
    """The whole point of the slice: when Donny's script is
    checked against the actual RAG doc he was supposedly
    citing, Wikipedia gets flagged."""
    unsupported = verify_claims(
        DONNY_ACTUAL_SCRIPT,
        factual_corpus=RAG_DOC_EXCERPT,
    )
    claims = {u.claim for u in unsupported}
    assert "Wikipedia" in claims


def test_verify_claims_character_os_protected_by_allowed_vocabulary() -> None:
    """Character OS appears in the script and isn't in the RAG
    doc. But it's in KNOWN_PLATFORM_TERMS which is part of
    ALLOWED VOCABULARY. The verifier skips it without flagging
    — but it does NOT license the surrounding claim as
    factually supported (that's SESSION 253's whole point)."""
    factual = build_factual_corpus([_FakeChunk(RAG_DOC_EXCERPT)])
    allowed = build_allowed_vocabulary()
    unsupported = verify_claims(
        DONNY_ACTUAL_SCRIPT,
        factual_corpus=factual,
        allowed_vocabulary=allowed,
    )
    claims = {u.claim for u in unsupported}
    assert "Character OS" not in claims
    # But Wikipedia is still flagged.
    assert "Wikipedia" in claims


def test_verify_claims_operator_prompt_does_not_license_terms() -> None:
    """SESSION 253 correction 1 — a term appearing in the
    operator's creative prompt does NOT ground the surrounding
    claim. Contrast with pre-SESSION 253 behavior which allowed
    any entity mentioned in the brief through the verifier.
    The whole factual_corpus surface refuses operator input at
    the signature level (see the signature test above)."""
    script = "Wikipedia is one of the largest sources of structured text."
    factual = build_factual_corpus([])
    allowed = build_allowed_vocabulary()
    unsupported = verify_claims(
        script,
        factual_corpus=factual,
        allowed_vocabulary=allowed,
    )
    claims = {u.claim for u in unsupported}
    # Wikipedia is neither in factual nor allowed → still flags.
    assert "Wikipedia" in claims


def test_verify_claims_returns_empty_on_clean_script() -> None:
    script = "Welcome to our store. Take a look around."
    corpus = "We sell things. Drop by anytime."
    unsupported = verify_claims(script, factual_corpus=corpus)
    # No specific entities, no flags.
    assert unsupported == []


# ---------------------------------------------------------------
# Mode handling
# ---------------------------------------------------------------


def test_run_verifier_strict_raises_on_unsupported() -> None:
    with pytest.raises(ClaimVerifierError) as exc_info:
        run_verifier(
            DONNY_ACTUAL_SCRIPT,
            factual_corpus=RAG_DOC_EXCERPT,
            mode="strict",
        )
    assert any(u.claim == "Wikipedia" for u in exc_info.value.unsupported)


def test_run_verifier_warn_returns_list() -> None:
    result = run_verifier(
        DONNY_ACTUAL_SCRIPT,
        factual_corpus=RAG_DOC_EXCERPT,
        mode="warn",
    )
    assert any(u.claim == "Wikipedia" for u in result)
    assert all(isinstance(u, UnsupportedClaim) for u in result)


def test_run_verifier_off_returns_empty() -> None:
    result = run_verifier(
        DONNY_ACTUAL_SCRIPT,
        factual_corpus=RAG_DOC_EXCERPT,
        mode="off",
    )
    assert result == []


def test_run_verifier_default_mode_via_settings() -> None:
    """No explicit mode → reads K6_CLAIM_VERIFIER_MODE setting."""
    with override_settings(K6_CLAIM_VERIFIER_MODE="off"):
        assert (
            run_verifier(DONNY_ACTUAL_SCRIPT, factual_corpus=RAG_DOC_EXCERPT)
            == []
        )


def test_run_verifier_unknown_mode_falls_back_to_warn() -> None:
    """Defensive: a typo in settings doesn't silently disable
    the verifier — it stays on in Warn mode."""
    result = run_verifier(
        DONNY_ACTUAL_SCRIPT,
        factual_corpus=RAG_DOC_EXCERPT,
        mode="bogus_mode_value",
    )
    assert any(u.claim == "Wikipedia" for u in result)


def test_strict_mode_error_carries_full_unsupported_list() -> None:
    try:
        run_verifier(
            DONNY_ACTUAL_SCRIPT,
            factual_corpus=RAG_DOC_EXCERPT,
            mode="strict",
        )
    except ClaimVerifierError as exc:
        assert len(exc.unsupported) >= 1
        assert "K6.4" in str(exc)


def test_strict_mode_error_carries_synthesized_text_k6_4_1() -> None:
    """K6.4.1 — the exception must carry the rejected text so
    the primitive can persist it onto the composition row.
    Without this the operator can't see what the LLM said when
    triaging a strict-mode failure."""
    try:
        run_verifier(
            DONNY_ACTUAL_SCRIPT,
            factual_corpus=RAG_DOC_EXCERPT,
            mode="strict",
        )
    except ClaimVerifierError as exc:
        assert exc.synthesized_text == DONNY_ACTUAL_SCRIPT


# ---------------------------------------------------------------
# Integration through build_render_brief
# ---------------------------------------------------------------


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_embeddings_and_eager():
    """Embedding calls go through the mock path so we don't need
    OPENAI_API_KEY for the ingest fixture, and Celery runs
    eagerly so chunks land synchronously before assertions."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace(email: str, ws_name: str) -> Workspace:
    """Workspace requires an owner — User.objects.create_user
    fires the post-save signal that auto-creates the
    operator's first workspace."""
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = ws_name
    ws.save()
    return ws


def _make_teammate(ws: Workspace, name: str, brief: str = "") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief=brief,
    )


def _ingest_attached(ws: Workspace, sp: Teammate, title: str, body: str) -> None:
    result = ingest_text(workspace=ws, title=title, content=body)
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    result.document.spokespeople.add(sp)


def test_build_render_brief_populates_verification_warnings() -> None:
    """End-to-end: ingest a RAG doc, patch the LLM to produce
    Donny's actual hallucinated script, confirm
    verification_warnings comes back populated."""
    ws = _make_workspace("k64a@test", "K6.4 WS A")
    sp = _make_teammate(ws, "Donny", "Documentary-style interviewer.")
    _ingest_attached(
        ws, sp,
        title="Wikipedia is trafilatura's home turf",
        body=RAG_DOC_EXCERPT * 5,
    )

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            RENDER_SCRIPT_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="warn",
        ):
            with patch(
                "character_os.script_synthesis._call_responses_api",
                return_value=(DONNY_ACTUAL_SCRIPT, 200, 80),
            ):
                result = build_render_brief(
                    sp,
                    "Tell viewers how character-os ingests pages.",
                )

    assert result.used_knowledge is True
    assert result.verification_warnings, (
        f"expected verification_warnings, got {result.verification_warnings}"
    )
    claims = {w["claim"] for w in result.verification_warnings}
    assert "Wikipedia" in claims


def test_build_render_brief_strict_raises() -> None:
    """Strict mode in the same end-to-end path raises
    ClaimVerifierError instead of returning a ScriptResult."""
    ws = _make_workspace("k64b@test", "K6.4 WS B")
    sp = _make_teammate(ws, "Donny", "Documentary-style interviewer.")
    _ingest_attached(ws, sp, title="RAG doc", body=RAG_DOC_EXCERPT * 5)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            RENDER_SCRIPT_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="strict",
        ):
            with patch(
                "character_os.script_synthesis._call_responses_api",
                return_value=(DONNY_ACTUAL_SCRIPT, 200, 80),
            ):
                with pytest.raises(ClaimVerifierError):
                    build_render_brief(
                        sp,
                        "Tell viewers how character-os ingests pages.",
                    )


def test_synthesized_brief_persists_on_successful_warn_render_k6_6() -> None:
    """K6.6 — successful renders (verified status) persist the
    synthesized brief on Composition. Closes the SESSION 168
    audit gap where operator feedback on rendered video quality
    had no place to land."""
    from apps.compositions.models import Composition
    from apps.compositions.primitives.avatar_speech import (
        GenerateAvatarSpeechPrimitive,
    )
    from apps.compositions.starters import talking_head

    ws = _make_workspace("k66a@test", "K6.6 WS A")
    sp = _make_teammate(ws, "Donny", "Documentary interviewer.")
    sp.runway_avatar_id = "avatar_test"
    sp.save()
    _ingest_attached(ws, sp, title="RAG doc", body=RAG_DOC_EXCERPT * 5)

    composition = talking_head(
        workspace=ws,
        spokesperson=sp,
        script="Tell me about RAG.",
        use_knowledge=True,
    )
    step = composition.steps.first()

    # Patch the LLM to return a clean grounded reply.
    clean_brief = (
        "I'm Donny — let me walk you through RAG in plain terms. "
        "It pulls relevant chunks before generation."
    )
    # Patch media-engine + Runway too so we don't try a real
    # render in this test.
    from unittest.mock import patch as _patch, MagicMock
    media_client = MagicMock()
    media_client.__enter__ = MagicMock(return_value=media_client)
    media_client.__exit__ = MagicMock(return_value=False)
    media_client.create_avatar_speech.return_value = MagicMock(
        task_id="task-1", mock_mode=False,
    )
    media_client.poll_avatar_speech.return_value = MagicMock(
        ready=True, file_path="https://fake.example/clip.mp4",
        duration_ms=5000, width=1280, height=720, mime_type="video/mp4",
        size_bytes=1024,
    )

    with _patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            RENDER_SCRIPT_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="warn",
        ):
            with _patch(
                "character_os.script_synthesis._call_responses_api",
                return_value=(clean_brief, 100, 30),
            ):
                with _patch(
                    "apps.compositions.primitives.avatar_speech.MediaEngineClient",
                    return_value=media_client,
                ):
                    with _patch(
                        "apps.compositions.primitives.avatar_speech.time.sleep",
                    ):
                        GenerateAvatarSpeechPrimitive.execute(
                            step, resolved_inputs={}, mock_mode=False,
                        )

    composition.refresh_from_db()
    assert composition.synthesized_brief == clean_brief
    assert composition.verification_status == "verified"


def test_strict_failure_persists_warnings_and_synthesis_k6_4_1() -> None:
    """K6.4.1 — when strict mode rejects, the primitive must
    save composition.verification_warnings and
    composition.rejected_synthesis before the failure propagates
    so the operator can triage."""
    from apps.compositions.models import Composition, CompositionStatus
    from apps.compositions.primitives.avatar_speech import (
        GenerateAvatarSpeechPrimitive,
    )
    from apps.compositions.starters import talking_head

    ws = _make_workspace("k64-1a@test", "K6.4.1 WS A")
    sp = _make_teammate(ws, "Donny", "Documentary interviewer.")
    sp.runway_avatar_id = "avatar_test"
    sp.save()
    _ingest_attached(ws, sp, title="RAG doc", body=RAG_DOC_EXCERPT * 5)

    composition = talking_head(
        workspace=ws,
        spokesperson=sp,
        script="Pitch how the platform works.",
        use_knowledge=True,
    )

    step = composition.steps.first()

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            RENDER_SCRIPT_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="strict",
        ):
            with patch(
                "character_os.script_synthesis._call_responses_api",
                return_value=(DONNY_ACTUAL_SCRIPT, 200, 80),
            ):
                with pytest.raises(Exception) as exc_info:
                    GenerateAvatarSpeechPrimitive.execute(
                        step, resolved_inputs={}, mock_mode=False,
                    )

    # PrimitiveError raised
    assert "K6.4 claim verifier rejected" in str(exc_info.value)

    # Composition got the forensic data persisted before the
    # exception propagated.
    composition.refresh_from_db()
    assert composition.rejected_synthesis == DONNY_ACTUAL_SCRIPT
    assert composition.verification_warnings
    claims = {w["claim"] for w in composition.verification_warnings}
    assert "Wikipedia" in claims


# NOTE — the six K6.6 / K6.6.1 / W11.y prompt-wording tests that
# used to live here (test_system_prompt_*) were removed SESSION 253.
# They pinned specific pre-SESSION 253 prompt phrasings ("ONLY to
# shape tone", "recite the speaker voice + character block",
# "Do NOT introduce yourself", etc.) that the 5-section refactor
# replaced with different but semantically-equivalent wording.
# Equivalent SESSION 253 coverage lives in
# ``test_session253_character_voice_prompt.py``.


def test_opener_blank_does_not_appear_in_user_prompt_k6_6() -> None:
    """K6.6 — when opener is None/empty, the user prompt has no
    operator-supplied opening clause; the model picks its own
    opener under the system prompt's structural guidance."""
    from unittest.mock import patch as _patch, MagicMock

    class _FakeSp:
        name = "Donny"
        tone_archetype = "expert"
        business_brief = ""

    class _FakeChunk:
        document_id = "doc"
        chunk_text = "Some chunk text."

    captured: dict = {}

    def _capture(*args, **kwargs):
        captured["input"] = kwargs.get("input") or (args[0] if args else "")
        resp = MagicMock()
        resp.output_text = "Mock script."
        resp.usage = MagicMock(input_tokens=0, output_tokens=0)
        return resp

    fake_client = MagicMock()
    fake_client.responses.create = _capture

    with _patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with _patch("openai.OpenAI", return_value=fake_client):
            from character_os.script_synthesis import _call_responses_api
            _call_responses_api(
                _FakeSp(), "topic", [_FakeChunk()], opener=None,
            )
            _call_responses_api(
                _FakeSp(), "topic", [_FakeChunk()], opener="   ",
            )

    # SESSION 253 — the pinned-opener block only appears when the
    # opener is non-empty; a whitespace opener is treated as empty
    # and produces no PINNED OPENER hard-constraint section.
    assert "PINNED OPENER" not in captured["input"]


def test_build_render_brief_off_mode_skips_verifier() -> None:
    """Off mode lets the synthesis through with no warnings."""
    ws = _make_workspace("k64c@test", "K6.4 WS C")
    sp = _make_teammate(ws, "Donny", "Documentary-style interviewer.")
    _ingest_attached(ws, sp, title="RAG doc", body=RAG_DOC_EXCERPT * 5)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            RENDER_SCRIPT_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="off",
        ):
            with patch(
                "character_os.script_synthesis._call_responses_api",
                return_value=(DONNY_ACTUAL_SCRIPT, 200, 80),
            ):
                result = build_render_brief(
                    sp,
                    "Tell viewers how character-os ingests pages.",
                )

    assert result.used_knowledge is True
    assert result.verification_warnings == []
