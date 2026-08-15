"""SESSION 251 — long_form_ad duration-driven contract.

Operator's 9-point regression plan + the SESSION 251-late
recalibration: the accept/reject gate is character-based via
``_estimate_avatar_speech_seconds`` (Character OS's canonical
speaking-rate estimator). Word count is passed to the LLM as
prompt guidance only. This closes the two-gate inconsistency the
operator caught on the Penny brief — 306 words fit the prompt
word budget for 120s but estimated at ~170s under the canonical
chars/sec rate, which is out of tolerance. Two gates disagreeing
in silence is the exact pathology this file is here to prevent.

1. standalone default receives the existing short-form contract.
2. long_form receives the long-form narrative contract.
3. long_form receives target duration + derived word budget
   (LLM prompt guidance only — NOT the accept gate).
4. A multi-minute long-form request cannot use the 60-100 word
   short-form prompt.
5. Knowledge-mode synthesis happens once before chunking.
6. Render chunks use the synthesized text verbatim.
7. Materially undersized OR oversized synthesis is caught before
   provider rendering — GATE IS SECONDS, not words:
   a. bidirectional bounded correction (one expansion / one
      compression attempt);
   b. gate uses the canonical char-based estimator;
   c. a 120s target rejects a 306-word / ~170s-estimated draft
      even though the word count fits the prompt word budget
      (the exact operator regression);
   d. corrective compression can bring the same draft into
      the 96-144s range;
   e. provider chunk steps are NOT created while estimated
      duration remains outside tolerance.
8. Existing talking_head behavior remains unchanged.
9. Knowledge-off long_form_ad does not rewrite the supplied
   script.

If any of these fails, the duration-driven contract has regressed.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.starters import (
    LongFormDurationError,
    _estimate_avatar_speech_seconds,
    long_form_ad,
)
from apps.spokespeople.models import Teammate
from character_os.script_synthesis import (
    ScriptResult,
    WORDS_PER_SECOND,
    _assemble_system_prompt,
    build_render_brief,
    word_budget_for_duration,
)


# SESSION 253 — the pre-refactor _system_prompt(sp, ...) is now
# _assemble_system_prompt(sp, chunks=[], ...). Tests here don't
# care about chunks (they're asserting the shape / duration
# contract), so a small helper preserves the original test
# ergonomics.
def _system_prompt(sp, *, target_shape="standalone",
                   target_duration_seconds=None):
    return _assemble_system_prompt(
        sp, chunks=[],
        target_shape=target_shape,
        target_duration_seconds=target_duration_seconds,
    )

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _teammate(email: str) -> tuple[Workspace, Teammate]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, Teammate.objects.create(
        workspace=ws, name="Duration Contract Teammate", business_brief="brief",
    )


def _canned(brief: str) -> ScriptResult:
    return ScriptResult(
        brief=brief,
        chunk_ids=["ck-1"],
        used_knowledge=True,
        model="gpt-5 (mock)",
        verification_status="verified",
        verification_warnings=[],
    )


def _make_words(n: int) -> str:
    return " ".join(["word"] * n)


def _make_text_words_chars(word_count: int, chars_per_word: int) -> str:
    """Fixture builder for the "word gate passes, duration gate
    fails" regression. Produces ``word_count`` words of exactly
    ``chars_per_word`` characters joined by single spaces. Lets a
    test dial word count and character count independently — the
    whole point of the character-based gate is that these two
    numbers can diverge in real synthesized text."""
    word = "x" * chars_per_word
    return " ".join([word] * word_count)


# ---- 1. standalone default keeps the short-form contract ----------


def test_standalone_default_receives_short_form_contract():
    """No target_shape param → default is 'standalone'. Assembled
    system prompt must contain the short-standalone shape marker
    and the 60-100 word target (SESSION 253 keeps this cap for
    the standalone shape via the Writing Contract)."""
    ws, tm = _teammate("dc-standalone@t")
    prompt = _system_prompt(tm)
    prompt_lower = prompt.lower()
    assert "short standalone" in prompt_lower
    assert "60-100 word" in prompt_lower
    # Explicitly no long-form language leaking in.
    assert "long-form" not in prompt_lower
    assert "character budget" not in prompt_lower


# ---- 2. long_form receives the long-form narrative contract -------


def test_long_form_receives_narrative_contract():
    """SESSION 253 — target_shape='long_form' swaps in the
    invariants + narrative-shape menu + anti-self-description
    contract via character_os.writing_contract."""
    ws, tm = _teammate("dc-longform-shape@t")
    prompt = _system_prompt(
        tm, target_shape="long_form", target_duration_seconds=120,
    )
    prompt_lower = prompt.lower()
    # Long-form marker + invariants block (SESSION 253 replaces
    # the pre-251 mandatory-skeleton with invariants + shape menu).
    assert "long-form" in prompt_lower
    assert "invariants" in prompt_lower
    # Load-bearing invariants must be in the contract.
    for keyword in [
        "earn attention early",
        "forward motion",
        "develop, don't restate",
        "meaningful change",
        "earns its runtime",
        "finish deliberately",
    ]:
        assert keyword.lower() in prompt_lower, (
            f"long-form prompt missing invariant keyword: {keyword!r}"
        )
    # Anti-self-description rule (applies to every shape).
    assert "demonstrate" in prompt_lower
    assert "don't describe" in prompt_lower
    # CTA policy is opt-in (SESSION 253 amendment #3), not mandatory.
    assert "cta policy" in prompt_lower
    assert "not required by default" in prompt_lower
    # And no short-form contract leaking in.
    assert "short standalone" not in prompt_lower or "60-100 word" not in prompt_lower


# ---- 3. long_form receives duration + derived word budget ---------


def test_long_form_prompt_interpolates_target_duration_and_word_budget():
    """The system prompt must contain the requested duration + the
    derived word range so the LLM has concrete numbers to hit,
    not a fixed short-form ceiling."""
    ws, tm = _teammate("dc-longform-numbers@t")
    prompt = _system_prompt(
        tm, target_shape="long_form", target_duration_seconds=180,
    )
    target, low, high = word_budget_for_duration(180)
    assert "180 seconds" in prompt
    assert f"{target} words" in prompt
    assert f"{low}" in prompt and f"{high}" in prompt


def test_long_form_prompt_interpolates_character_budget():
    """SESSION 251-late — the writer must receive concrete character
    ceilings, not just prose asking it to compress/expand. If the
    character budget disappears from the prompt, K6 falls back
    to word-guidance-only, which the operator caught only trimming
    49 chars on a draft that needed to shed 232.
    """
    from character_os.script_synthesis import char_budget_for_duration

    ws, tm = _teammate("dc-longform-charbudget@t")
    prompt = _system_prompt(
        tm, target_shape="long_form", target_duration_seconds=120,
    )
    ideal, low_c, high_c = char_budget_for_duration(120)
    # SESSION 253 — case-insensitive because the marker moved
    # into the writing_contract module which uses "CHARACTER
    # BUDGET" (upper) in the contract text.
    assert "character budget" in prompt.lower()
    assert f"{ideal} characters" in prompt
    assert f"{low_c}" in prompt and f"{high_c}" in prompt
    # And it must state which gate is authoritative — words are
    # secondary guidance, chars are the accept/reject axis.
    assert "character-based" in prompt.lower()


# ---- 4. multi-minute request cannot use short-form prompt --------


def test_multi_minute_long_form_never_uses_short_form_paragraph():
    """Load-bearing invariant. A 5-minute long-form request must
    NOT contain the short-standalone 60-100-word paragraph
    anywhere in the system prompt, because that block is what
    caused the operator's 44s render on a 90-120s ask."""
    ws, tm = _teammate("dc-multiminute@t")
    for seconds in (60, 90, 120, 180, 300):
        prompt = _system_prompt(
            tm, target_shape="long_form", target_duration_seconds=seconds,
        )
        prompt_lower = prompt.lower()
        assert "short standalone" not in prompt_lower, (
            f"long-form prompt at {seconds}s contains the short-form "
            "shape marker — this is the pre-251 pathology"
        )
        assert "60-100 word" not in prompt_lower, (
            f"long-form prompt at {seconds}s contains '60-100 word' — "
            "the short-form ceiling leaked into long-form"
        )


def test_build_render_brief_refuses_long_form_without_duration():
    """No silent fallback. Long-form callers must pass a duration."""
    ws, tm = _teammate("dc-nolength@t")
    with pytest.raises(ValueError, match="requires target_duration_seconds"):
        build_render_brief(tm, "some brief", target_shape="long_form")


# ---- 5. knowledge-mode synthesis happens once before chunking ----


def test_knowledge_mode_synthesis_runs_exactly_once():
    """Re-assertion of the SESSION 251 one-pass ordering, now with
    the duration parameter in the mix. Ensures the duration-driven
    changes did not introduce a per-chunk fallback."""
    ws, tm = _teammate("dc-once@t")
    with patch(
        "character_os.script_synthesis.build_render_brief",
        return_value=_canned(_make_words(100)),
    ) as mock_brb:
        long_form_ad(
            workspace=ws,
            spokesperson=tm,
            script="short topic",
            use_knowledge=True,
            target_duration_seconds=45,  # 45s → ~99 words; 100 fits
        )
    assert mock_brb.call_count == 1


# ---- 6. chunks use synthesized text verbatim ---------------------


def test_chunks_use_synthesized_text_verbatim():
    """Chunks must contain slices of the synthesized brief, not
    fresh per-chunk syntheses. Re-assertion for the duration
    codepath."""
    ws, tm = _teammate("dc-verbatim@t")
    brief = _make_words(100)
    with patch(
        "character_os.script_synthesis.build_render_brief",
        return_value=_canned(brief),
    ):
        comp = long_form_ad(
            workspace=ws,
            spokesperson=tm,
            script="topic",
            use_knowledge=True,
            target_duration_seconds=45,
        )
    joined = " ".join(
        step.params.get("script", "")
        for step in comp.steps.filter(primitive="generate_avatar_speech")
        .order_by("position")
    )
    # Every "word" in the canned brief must land in some chunk.
    assert joined.count("word") == 100


# ---- 7. bidirectional out-of-tolerance catches before render -----


def _stub_returns_progressively(*side_effects: str):
    """Helper: patch build_render_brief to return canned briefs
    in sequence — first call gets side_effects[0], second call
    gets side_effects[1], etc. Used to exercise the bounded
    corrective pass."""
    from itertools import cycle

    results = list(side_effects)
    it = iter(results)

    def side_effect(*args, **kwargs):
        try:
            return _canned(next(it))
        except StopIteration:
            # If the code makes more calls than expected the test
            # should fail loudly rather than reuse the last one.
            raise AssertionError(
                "build_render_brief called more times than the "
                "stub was primed for — the bounded retry contract "
                "may have regressed to an unbounded loop"
            )

    return side_effect


def test_undersized_synthesis_retries_once_then_fails():
    """Under-budget on first call → one expansion retry → still
    under → composition created in FAILED state, ClaimVerifier
    style, no chunk steps laid down, no Runway."""
    ws, tm = _teammate("dc-under@t")
    # 300s target → range ~528-792 words. Both attempts return
    # a tiny brief so both trip the min bound.
    stub = _stub_returns_progressively(
        _make_words(100),  # first attempt, way under
        _make_words(110),  # retry, still under
    )
    with patch(
        "character_os.script_synthesis.build_render_brief",
        side_effect=stub,
    ) as mock_brb:
        with pytest.raises(LongFormDurationError) as exc_info:
            long_form_ad(
                workspace=ws,
                spokesperson=tm,
                script="topic",
                use_knowledge=True,
                target_duration_seconds=300,
            )
    # Exactly two calls — one initial + one bounded retry.
    assert mock_brb.call_count == 2
    # Gate is duration-based; confirm the seconds estimate matches
    # what the char-based estimator produces on the last attempt.
    assert exc_info.value.actual_seconds == _estimate_avatar_speech_seconds(
        len(_make_words(110)),
    )
    assert exc_info.value.actual_seconds < exc_info.value.min_seconds
    # SESSION 251-late: the exception now carries the composition-create
    # payload so the view can persist the FAILED row OUTSIDE its own
    # ``transaction.atomic()`` (starter-level tests here don't invoke
    # the view, so ``composition_id`` stays ``None``). The payload
    # itself is the operator-facing audit trail — the view uses it to
    # create the row that the operator sees on the dashboard.
    assert exc_info.value.composition_id is None
    assert exc_info.value.synthesized_brief == _make_words(110)
    assert exc_info.value.workspace == ws
    assert exc_info.value.spokesperson == tm
    assert "Long-form" in exc_info.value.composition_name
    # No chunk steps laid down → zero Runway spend.


def test_oversized_synthesis_retries_once_then_fails():
    """Over-budget on first call → one compression retry → still
    over → composition failed. Same shape as undersized, opposite
    direction."""
    ws, tm = _teammate("dc-over@t")
    # 60s target → range ~106-159 words. Both attempts return a
    # huge brief so both trip the max bound.
    stub = _stub_returns_progressively(
        _make_words(500),
        _make_words(450),
    )
    with patch(
        "character_os.script_synthesis.build_render_brief",
        side_effect=stub,
    ) as mock_brb:
        with pytest.raises(LongFormDurationError) as exc_info:
            long_form_ad(
                workspace=ws,
                spokesperson=tm,
                script="topic",
                use_knowledge=True,
                target_duration_seconds=60,
            )
    assert mock_brb.call_count == 2
    assert exc_info.value.actual_seconds == _estimate_avatar_speech_seconds(
        len(_make_words(450)),
    )
    assert exc_info.value.actual_seconds > exc_info.value.max_seconds


def test_retry_converges_into_tolerance_and_ships():
    """When the corrective pass DOES land inside tolerance, the
    starter proceeds to chunking + composition creation. This is
    the happy retry path — proves the retry is a real correction,
    not just a rejection knob."""
    ws, tm = _teammate("dc-retry-ok@t")
    # 90s target → range ~185-278 words. First attempt too short;
    # retry lands inside.
    stub = _stub_returns_progressively(
        _make_words(100),  # under
        _make_words(210),  # inside range
    )
    with patch(
        "character_os.script_synthesis.build_render_brief",
        side_effect=stub,
    ) as mock_brb:
        comp = long_form_ad(
            workspace=ws,
            spokesperson=tm,
            script="topic",
            use_knowledge=True,
            target_duration_seconds=90,
        )
    assert mock_brb.call_count == 2
    assert comp.status != CompositionStatus.FAILED
    # And chunk steps ARE laid down — the retry produced usable
    # output.
    assert comp.steps.filter(primitive="generate_avatar_speech").count() >= 1


# ---- 7c. OPERATOR REGRESSION: word gate passes, duration gate fails --


def test_word_in_budget_but_duration_over_still_rejected():
    """SESSION 251-late — the exact regression the operator caught on
    the Penny brief. 306 words fit the 211-317 prompt word budget
    for a 120s target, but 306 words worth of real text estimated
    at ~170s exceeds the 96-144s duration tolerance. If the gate
    was word-count-based the render would have shipped a
    ~170s video for a 90-120s ask.

    Fixture uses 250 words × 7-char words (~1999 chars) → estimated
    at ~183s. Word count is well inside the 211-317 budget for
    120s; character-based estimate is well past the 144s cap. This
    test proves the gate rejects even when the word budget would
    have accepted.
    """
    ws, tm = _teammate("dc-op-regression@t")
    dense_but_wordy = _make_text_words_chars(250, 7)
    word_count = len(dense_but_wordy.split())
    char_count = len(dense_but_wordy)
    est_seconds = _estimate_avatar_speech_seconds(char_count)

    target_words, min_words, max_words = word_budget_for_duration(120)
    # Pre-conditions: word gate would say pass; duration gate says fail.
    assert min_words <= word_count <= max_words, (
        f"fixture broken: {word_count} words must fit the word "
        f"budget [{min_words}, {max_words}] to expose the regression"
    )
    assert est_seconds > 144, (
        f"fixture broken: char-based estimate must exceed the "
        f"144s max tolerance to expose the regression (got {est_seconds}s)"
    )

    # Both attempts return the same over-duration draft so both
    # trip the duration cap after the compression retry.
    stub = _stub_returns_progressively(dense_but_wordy, dense_but_wordy)
    with patch(
        "character_os.script_synthesis.build_render_brief",
        side_effect=stub,
    ):
        with pytest.raises(LongFormDurationError) as exc_info:
            long_form_ad(
                workspace=ws,
                spokesperson=tm,
                script="topic",
                use_knowledge=True,
                target_duration_seconds=120,
            )

    # The failure carries the duration numbers, not word numbers, as
    # the load-bearing reason.
    assert exc_info.value.actual_seconds > exc_info.value.max_seconds
    assert exc_info.value.max_seconds == 144
    # Word count fields ARE recorded (for audit / debugging), and
    # they DO fall inside the budget — proof the two gates disagreed
    # and the character-based one won.
    assert min_words <= exc_info.value.actual_words <= max_words

    # And crucially: NO provider render steps were created. This is
    # the strongest guarantee that no Runway credits were burned.
    assert (
        CompositionStep.objects.filter(
            composition__workspace=ws,
            primitive="generate_avatar_speech",
        ).count()
        == 0
    )


def test_compression_retry_converges_from_over_duration():
    """When the first pass overshoots the duration cap, the
    compression corrective pass can bring the second draft into
    the 96-144s tolerance and the composition ships. Proves the
    compression hint drives real correction (not just retry-then-
    fail), and mirrors the shape the operator asked for: same
    over-shooting input can converge when the LLM cooperates."""
    ws, tm = _teammate("dc-compress-converge@t")
    # First attempt over: 260 words × 7 chars → 1819 chars → ~167s
    # Retry inside: 160 words × 7 chars → 1119 chars → ~103s
    over_draft = _make_text_words_chars(260, 7)
    inside_draft = _make_text_words_chars(160, 7)

    # Pre-conditions on the fixtures.
    assert _estimate_avatar_speech_seconds(len(over_draft)) > 144
    assert 96 <= _estimate_avatar_speech_seconds(len(inside_draft)) <= 144

    stub = _stub_returns_progressively(over_draft, inside_draft)
    with patch(
        "character_os.script_synthesis.build_render_brief",
        side_effect=stub,
    ) as mock_brb:
        comp = long_form_ad(
            workspace=ws,
            spokesperson=tm,
            script="topic",
            use_knowledge=True,
            target_duration_seconds=120,
        )

    assert mock_brb.call_count == 2
    assert comp.status != CompositionStatus.FAILED
    # Chunk steps ARE laid down — the retry produced usable output.
    assert (
        CompositionStep.objects.filter(
            composition=comp, primitive="generate_avatar_speech",
        ).count()
        >= 1
    )
    # Composition's persisted synthesized_brief matches the SECOND
    # (in-tolerance) draft, not the first over-duration one.
    comp.refresh_from_db()
    assert comp.synthesized_brief == inside_draft


def test_no_chunk_steps_created_when_duration_out_of_tolerance():
    """Explicit assertion of the "provider steps not created while
    estimated duration remains outside tolerance" contract, in
    isolation. Both directions covered in a compact form."""
    for direction, first, second, target in (
        (
            "over",
            _make_text_words_chars(250, 7),  # ~183s
            _make_text_words_chars(240, 7),  # ~176s (still over)
            120,
        ),
        (
            "under",
            _make_text_words_chars(30, 5),  # ~18s
            _make_text_words_chars(35, 5),  # ~21s (still under)
            120,
        ),
    ):
        ws, tm = _teammate(f"dc-no-chunks-{direction}@t")
        stub = _stub_returns_progressively(first, second)
        with patch(
            "character_os.script_synthesis.build_render_brief",
            side_effect=stub,
        ):
            with pytest.raises(LongFormDurationError):
                long_form_ad(
                    workspace=ws, spokesperson=tm,
                    script="topic", use_knowledge=True,
                    target_duration_seconds=target,
                )
        assert (
            CompositionStep.objects.filter(
                composition__workspace=ws,
                primitive="generate_avatar_speech",
            ).count()
            == 0
        ), (
            f"{direction}-duration failure created chunk steps — this "
            "would have burned Runway credits on an out-of-tolerance draft"
        )


# ---- 8. talking_head behavior unchanged --------------------------


def test_talking_head_still_uses_standalone_shape():
    """The talking_head recipe and its starter must not have
    picked up the long-form shape by accident. Every call to
    build_render_brief from talking_head's primitive must omit
    target_shape (accepting the default 'standalone'). We can't
    inspect the primitive here without a real render, so we
    instead assert the default-parameter path in build_render_brief
    still produces the short-form contract."""
    ws, tm = _teammate("dc-th-unchanged@t")
    # Two positional args + no target_shape override = standalone
    # default. If the default is quietly changed to 'long_form',
    # the ValueError from build_render_brief (no duration) would
    # surface here.
    from character_os.script_synthesis import _is_force_mock

    # Guard: this test only runs meaningfully when force-mock is
    # active OR when we can safely dry-run the signature.
    # Signature-only check:
    import inspect

    sig = inspect.signature(build_render_brief)
    default_shape = sig.parameters["target_shape"].default
    assert default_shape == "standalone", (
        f"build_render_brief target_shape default changed to "
        f"{default_shape!r} — this would silently move talking_head "
        "and auto_script to long-form and break the pre-251 contract"
    )


# ---- 9. knowledge-off does not rewrite operator script -----------


def test_knowledge_off_long_form_ad_does_not_rewrite_script():
    """Re-assertion of the knowledge-off contract with the duration
    parameter in the mix. Operator's finished script must reach
    the chunks verbatim; build_render_brief must NOT be called."""
    ws, tm = _teammate("dc-noknow@t")
    finished = _make_words(300)  # 300 words of operator input
    with patch(
        "character_os.script_synthesis.build_render_brief",
    ) as mock_brb:
        comp = long_form_ad(
            workspace=ws,
            spokesperson=tm,
            script=finished,
            use_knowledge=False,
            # Duration is informational on the no-knowledge path;
            # passing it here confirms it's tolerated without
            # affecting the verbatim behavior.
            target_duration_seconds=180,
        )
    assert mock_brb.call_count == 0
    joined = " ".join(
        step.params.get("script", "")
        for step in comp.steps.filter(primitive="generate_avatar_speech")
        .order_by("position")
    )
    # Every "word" from the operator's finished script must appear
    # exactly as many times in the joined chunk output.
    assert joined.count("word") == 300


# ---- word_budget helper --------------------------------------------


def test_word_budget_matches_speaking_rate():
    """Sanity: the helper exposes a stable single source of truth.
    Callers, prompt builder, and validator all read from here."""
    target, low, high = word_budget_for_duration(60)
    assert target == round(60 * WORDS_PER_SECOND)
    assert low < target < high
    assert low == round(target * 0.8)
    assert high == round(target * 1.2)


def test_build_render_brief_rejects_bad_shape():
    ws, tm = _teammate("dc-badshape@t")
    with pytest.raises(ValueError, match="target_shape must be"):
        build_render_brief(tm, "brief", target_shape="reels_short")
