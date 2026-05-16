"""K6.4 (SESSION 159) — post-synthesis claim verifier tests.

Covers ``character_os.claim_verifier``:

* Named-entity extraction (multi-word phrases, single
  capitalized words, numerics) catches Donny's actual script.
* Common-word stoplist prevents false positives on sentence
  starters like "Turns", "When", "Drop".
* ``KNOWN_PLATFORM_TERMS`` allow-lists "Character OS".
* ``build_corpus`` concatenates chunks + spokesperson context
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
from apps.spokespeople.models import Spokesperson
from character_os.claim_verifier import (
    KNOWN_PLATFORM_TERMS,
    ClaimVerifierError,
    UnsupportedClaim,
    build_corpus,
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


def test_build_corpus_concatenates_chunks() -> None:
    chunks = [_FakeChunk("Alpha content"), _FakeChunk("Beta content")]
    corpus = build_corpus(chunks)
    assert "Alpha content" in corpus
    assert "Beta content" in corpus


def test_build_corpus_includes_known_platform_terms() -> None:
    corpus = build_corpus([])
    for term in KNOWN_PLATFORM_TERMS:
        assert term in corpus


def test_build_corpus_includes_operator_prompt_and_brief() -> None:
    class _FakeSp:
        name = "Riggs"
        business_brief = "Founder voice for the donkey brand."

    corpus = build_corpus(
        [_FakeChunk("chunk text")],
        spokesperson=_FakeSp(),
        operator_prompt="Talk about the spring sale.",
    )
    assert "chunk text" in corpus
    assert "Riggs" in corpus
    assert "donkey brand" in corpus
    assert "spring sale" in corpus


def test_verify_claims_donny_against_rag_doc_flags_wikipedia() -> None:
    """The whole point of the slice: when Donny's script is
    checked against the actual RAG doc he was supposedly
    citing, Wikipedia gets flagged."""
    unsupported = verify_claims(
        DONNY_ACTUAL_SCRIPT,
        corpus=RAG_DOC_EXCERPT,
    )
    claims = {u.claim for u in unsupported}
    assert "Wikipedia" in claims


def test_verify_claims_character_os_protected_by_platform_terms() -> None:
    """Character OS appears in the script and isn't in the doc.
    But it's in KNOWN_PLATFORM_TERMS, so the full corpus from
    build_corpus protects it."""
    corpus = build_corpus(
        [_FakeChunk(RAG_DOC_EXCERPT)],
    )
    unsupported = verify_claims(DONNY_ACTUAL_SCRIPT, corpus=corpus)
    claims = {u.claim for u in unsupported}
    assert "Character OS" not in claims
    # But Wikipedia is still flagged.
    assert "Wikipedia" in claims


def test_verify_claims_operator_prompt_allows_terms() -> None:
    """The operator may legitimately introduce terms via the
    prompt. Those shouldn't flag in the script."""
    script = "Wikipedia is one of the largest sources of structured text."
    corpus = build_corpus(
        [],
        operator_prompt="Pitch how Wikipedia improves coverage.",
    )
    unsupported = verify_claims(script, corpus=corpus)
    claims = {u.claim for u in unsupported}
    assert "Wikipedia" not in claims


def test_verify_claims_returns_empty_on_clean_script() -> None:
    script = "Welcome to our store. Take a look around."
    corpus = "We sell things. Drop by anytime."
    unsupported = verify_claims(script, corpus=corpus)
    # No specific entities, no flags.
    assert unsupported == []


# ---------------------------------------------------------------
# Mode handling
# ---------------------------------------------------------------


def test_run_verifier_strict_raises_on_unsupported() -> None:
    with pytest.raises(ClaimVerifierError) as exc_info:
        run_verifier(
            DONNY_ACTUAL_SCRIPT,
            corpus=RAG_DOC_EXCERPT,
            mode="strict",
        )
    assert any(u.claim == "Wikipedia" for u in exc_info.value.unsupported)


def test_run_verifier_warn_returns_list() -> None:
    result = run_verifier(
        DONNY_ACTUAL_SCRIPT,
        corpus=RAG_DOC_EXCERPT,
        mode="warn",
    )
    assert any(u.claim == "Wikipedia" for u in result)
    assert all(isinstance(u, UnsupportedClaim) for u in result)


def test_run_verifier_off_returns_empty() -> None:
    result = run_verifier(
        DONNY_ACTUAL_SCRIPT,
        corpus=RAG_DOC_EXCERPT,
        mode="off",
    )
    assert result == []


def test_run_verifier_default_mode_via_settings() -> None:
    """No explicit mode → reads K6_CLAIM_VERIFIER_MODE setting."""
    with override_settings(K6_CLAIM_VERIFIER_MODE="off"):
        assert (
            run_verifier(DONNY_ACTUAL_SCRIPT, corpus=RAG_DOC_EXCERPT)
            == []
        )


def test_run_verifier_unknown_mode_falls_back_to_warn() -> None:
    """Defensive: a typo in settings doesn't silently disable
    the verifier — it stays on in Warn mode."""
    result = run_verifier(
        DONNY_ACTUAL_SCRIPT,
        corpus=RAG_DOC_EXCERPT,
        mode="bogus_mode_value",
    )
    assert any(u.claim == "Wikipedia" for u in result)


def test_strict_mode_error_carries_full_unsupported_list() -> None:
    try:
        run_verifier(
            DONNY_ACTUAL_SCRIPT,
            corpus=RAG_DOC_EXCERPT,
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
            corpus=RAG_DOC_EXCERPT,
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


def _make_spokesperson(ws: Workspace, name: str, brief: str = "") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws,
        name=name,
        business_brief=brief,
    )


def _ingest_attached(ws: Workspace, sp: Spokesperson, title: str, body: str) -> None:
    result = ingest_text(workspace=ws, title=title, content=body)
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    result.document.spokespeople.add(sp)


def test_build_render_brief_populates_verification_warnings() -> None:
    """End-to-end: ingest a RAG doc, patch the LLM to produce
    Donny's actual hallucinated script, confirm
    verification_warnings comes back populated."""
    ws = _make_workspace("k64a@test", "K6.4 WS A")
    sp = _make_spokesperson(ws, "Donny", "Documentary-style interviewer.")
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
    sp = _make_spokesperson(ws, "Donny", "Documentary-style interviewer.")
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
    sp = _make_spokesperson(ws, "Donny", "Documentary interviewer.")
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


def test_build_render_brief_off_mode_skips_verifier() -> None:
    """Off mode lets the synthesis through with no warnings."""
    ws = _make_workspace("k64c@test", "K6.4 WS C")
    sp = _make_spokesperson(ws, "Donny", "Documentary-style interviewer.")
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
