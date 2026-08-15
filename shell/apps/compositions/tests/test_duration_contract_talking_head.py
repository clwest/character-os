"""SESSION 253 amendment — shared duration contract + topic-driven
``talking_head`` wiring.

Pins the economic invariant the operator's dogfood exposed:

    when an operator requests N seconds of AI-synthesized talking-
    head speech, the requested duration must control K6's
    character budget AND the generated script must pass the
    duration tolerance gate BEFORE any Runway avatar call fires.

Coverage layers:

1. ``AVATAR_SPEECH_SAFE_MAX_CHARS`` value + reuse.
2. Effective-budget math for 30s / 60s / 90s / 120s / 180s + the
   incompatible-with-provider case (300s + default cap).
3. ``synthesize_with_duration_gate`` — first-pass accept, first-
   pass too-short-then-retry, still-out-after-retry raises, and
   provider-cap enforcement.
4. talking_head recipe form exposes the field.
5. Starter accepts + persists on the step; ignores when
   use_knowledge=False (manual scripts spoken verbatim).
6. Primitive routes through the helper when duration + use_knowledge;
   raises PrimitiveError WITHOUT invoking the media-engine client
   when the duration gate rejects.
7. Backward compat: no duration → build_render_brief default
   (standalone shape, no gate).
8. long_form_ad still works via the extracted helper.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Composition,
    CompositionStatus,
    CompositionStep,
    StepStatus,
)
from apps.compositions.primitives.avatar_speech import (
    GenerateAvatarSpeechPrimitive,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.recipes import RECIPES
from apps.compositions.starters import talking_head
from apps.spokespeople.models import Teammate
from character_os.duration_contract import (
    AVATAR_SPEECH_SAFE_MAX_CHARS,
    K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER,
    DurationContractError,
    calibrated_synthesis_target,
    compute_effective_budget,
    synthesize_with_duration_gate,
)
from character_os.script_synthesis import ScriptResult, char_budget_for_duration

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ----------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(ws: Workspace, *, name: str = "T") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name, business_brief="b",
        runway_avatar_id="fake-avatar",
    )


# ---- 1. cap constant ---------------------------------------------


def test_avatar_speech_safe_max_chars_locked_at_1900():
    """Media-engine cap is 2000; we run 100 chars below for safety."""
    assert AVATAR_SPEECH_SAFE_MAX_CHARS == 1900


# ---- 2. effective budget across durations -----------------------


def test_effective_budget_short_targets_unaffected_by_cap():
    """30s/60s/90s targets are well below the 1900-char cap; the
    cap should not alter their budgets."""
    for target in (30, 60, 90, 120):
        raw_ideal, raw_low, raw_high = char_budget_for_duration(target)
        eff_ideal, eff_low, eff_high = compute_effective_budget(
            target, AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
        assert eff_low == raw_low
        assert eff_high == raw_high
        assert eff_ideal == raw_ideal


def test_effective_budget_180s_clamps_at_cap():
    """180s raw budget is (1980, 1584, 2376). With the 1900 cap,
    high clamps to 1900 and ideal drops to leave a 50-char
    safety buffer below the ceiling."""
    ideal, low, high = compute_effective_budget(180, AVATAR_SPEECH_SAFE_MAX_CHARS)
    assert high == 1900
    assert low == 1584  # duration-min unchanged; still inside cap
    assert ideal == 1850  # 1900 - 50-char safety buffer
    # Predicted duration for effective ideal.
    assert 1850 / 11 > 165  # ~168s, inside the 144-216s tolerance for 180s


def test_effective_budget_300s_incompatible_raises_before_llm():
    """300s target requires min 2640 chars (300 * 11 * 0.8), which
    exceeds the 1900-char cap. Reject up front — no LLM call
    could satisfy both constraints."""
    with pytest.raises(DurationContractError) as exc_info:
        compute_effective_budget(300, AVATAR_SPEECH_SAFE_MAX_CHARS)
    assert exc_info.value.reason == (
        DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER
    )


def test_char_budget_for_duration_with_cap_matches_effective_budget():
    """SESSION 253 amendment — char_budget_for_duration itself
    accepts max_script_chars and produces the same clamped
    triple as compute_effective_budget for the same inputs."""
    for target in (30, 60, 90, 120, 180):
        via_helper = compute_effective_budget(target, AVATAR_SPEECH_SAFE_MAX_CHARS)
        via_budget = char_budget_for_duration(
            target, max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
        assert via_helper == via_budget


# ---- 3. synthesize_with_duration_gate ----------------------------


def _fake_script_result(text: str) -> ScriptResult:
    return ScriptResult(
        brief=text,
        chunk_ids=["c1"],
        used_knowledge=True,
        verification_status="verified",
        writing_contract_version=1,
    )


def test_gate_accepts_first_pass_in_tolerance():
    """When K6 returns a script inside the tolerance band on the
    first pass, no retry fires and the result flows through."""
    ws = _workspace("dc-first-pass@t")
    tm = _teammate(ws)
    # 90s target → effective budget (990, 792, 1188). Return 990.
    perfect = "x" * 990

    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result(perfect),
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == perfect
    fake_brb.assert_called_once()  # no retry


def test_gate_retries_when_short_then_accepts():
    """First pass too short → one expansion retry → accept."""
    ws = _workspace("dc-retry-short@t")
    tm = _teammate(ws)
    # 90s target → tolerance [792, 1188]. First = 300 chars (too
    # short); retry = 990 chars (accept).
    short = "x" * 300
    corrected = "x" * 990

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(short),
            _fake_script_result(corrected),
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == corrected
    assert fake_brb.call_count == 2
    # Second call carries a corrective_hint that references the
    # SYNTH-target budget (SESSION 253 amendment B) so K6 keeps
    # aiming low on the retry. For a 90 s request the synth
    # target is 70 s → synth_min = round(70 * 11 * 0.8) = 616.
    retry_kwargs = fake_brb.call_args_list[1].kwargs
    assert "corrective_hint" in retry_kwargs
    assert "616" in retry_kwargs["corrective_hint"]


def test_gate_retries_when_long_then_accepts():
    """First pass too long → one compression retry → accept."""
    ws = _workspace("dc-retry-long@t")
    tm = _teammate(ws)
    long_ = "x" * 1500  # 90s + tolerance high is 1188; 1500 is over
    corrected = "x" * 990

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result(long_),
            _fake_script_result(corrected),
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == corrected
    assert fake_brb.call_count == 2


def test_gate_still_short_after_retry_raises():
    """If the retry ALSO produces a too-short script, raise
    DurationContractError with reason=too_short. Caller must not
    fire the Runway call."""
    ws = _workspace("dc-still-short@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 100),
            _fake_script_result("x" * 300),
        ],
    ):
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic", target_duration_seconds=90,
            )
    assert exc_info.value.reason == DurationContractError.REASON_TOO_SHORT
    assert exc_info.value.actual_chars == 300


def test_synthesis_target_multiplier_locked_at_calibrated_value():
    """SESSION 253 amendment B — the synthesis-target multiplier
    is empirically calibrated from the D dogfood. Locking the
    value so accidental drift lights up as an explicit test
    failure. Recalibrate ONLY from new dogfood evidence."""
    assert K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 0.78


def test_calibrated_synthesis_target_90s_is_70s():
    """The load-bearing case for the SESSION 253 fix: 90 s
    operator request → K6 sees a 70 s synthesis target."""
    assert calibrated_synthesis_target(90) == 70


def test_calibrated_synthesis_target_120s_is_about_94s():
    assert calibrated_synthesis_target(120) == 94


def test_calibrated_synthesis_target_short_targets_disable_bias():
    """Below the 30 s calibration floor, the bias is skipped
    (unvalidated regime; applying 0.78 would push very short
    scripts under the acceptance floor)."""
    for short in (5, 10, 20, 29):
        assert calibrated_synthesis_target(short) == short


def test_synth_target_never_leaks_into_prompt_target_arg():
    """SESSION 253 amendment B — K6's ``build_render_brief`` call
    must receive the SYNTHESIS target (biased) as its
    ``target_duration_seconds`` kwarg, NOT the operator-requested
    target. The prompt LENGTH block and word-budget interpolation
    derive from whatever this arg is set to."""
    ws = _workspace("dc-synth-in-prompt@t")
    tm = _teammate(ws)
    captured = {}

    def _capture(sp, prompt, **kwargs):
        captured["kwargs"] = kwargs
        return _fake_script_result("x" * 990)

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=_capture,
    ):
        synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    # K6 sees synth target (70), NOT requested target (90).
    assert captured["kwargs"]["target_duration_seconds"] == 70
    assert captured["kwargs"]["target_duration_seconds"] != 90


def test_synth_target_leak_test_120s_covers_the_general_case():
    ws = _workspace("dc-synth-120@t")
    tm = _teammate(ws)
    captured = {}

    def _capture(sp, prompt, **kwargs):
        captured["kwargs"] = kwargs
        return _fake_script_result("x" * 1300)

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=_capture,
    ):
        synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=120,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert captured["kwargs"]["target_duration_seconds"] == 94


def test_acceptance_band_derives_from_requested_not_synth_target():
    """SESSION 253 amendment B — 90 s request accepts 792-1188
    chars (=72-108 s). NOT the synth-target band (770 ideal /
    616-924 chars for 70 s)."""
    # A 900-char script for 90 s request is:
    #   below acceptance-max 1188 → accept
    #   above synth-max 924 → would REJECT under the wrong contract
    # Assert we accept it (correct acceptance band).
    ws = _workspace("dc-accept-band@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result("x" * 900),
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    # No retry, accepted on first pass.
    fake_brb.assert_called_once()
    assert result.brief == "x" * 900


def test_180s_synth_budget_still_respects_provider_cap():
    """SESSION 253 amendment B — for 180 s the synth target is
    140 s → budget (ideal 1540, min 1232, max 1848). All under
    the 1900 cap. The K6 prompt must not tell the LLM to aim
    above the cap even after the calibration bias."""
    ws = _workspace("dc-180-cap-under-synth@t")
    tm = _teammate(ws)
    captured = {}

    def _capture(sp, prompt, **kwargs):
        captured["kwargs"] = kwargs
        return _fake_script_result("x" * 1800)

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=_capture,
    ):
        synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=180,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert captured["kwargs"]["target_duration_seconds"] == 140
    # Provider cap flows through untouched — still enforced.
    assert captured["kwargs"]["max_script_chars"] == AVATAR_SPEECH_SAFE_MAX_CHARS


def test_error_message_never_names_synth_target():
    """SESSION 253 amendment B — error messages must NEVER refer
    to the calibrated synth target. The operator asked for 90 s;
    error messages say 90 s (even though K6 was internally
    aiming at 70 s)."""
    ws = _workspace("dc-err-msg-req-only@t")
    tm = _teammate(ws)
    # 90 s request. K6 delivers 1400 (over acceptance-max 1188)
    # → compression retry. Retry delivers 1250 (still over
    # 1188). Rejected as TOO_LONG.
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1400),
            _fake_script_result("x" * 1250),
        ],
    ):
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic",
                target_duration_seconds=90,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    err = exc_info.value
    # Reason: too_long (correct classification per amendment A).
    assert err.reason == DurationContractError.REASON_TOO_LONG
    # Exception carries REQUESTED target — not synth (70).
    assert err.target_duration_seconds == 90
    msg = str(err)
    # 90-second target must appear (operator asked for 90).
    assert "90-second target" in msg
    # 70-second synth target must NOT leak.
    assert "70-second" not in msg
    assert "70s" not in msg
    # Acceptance band uses requested-target bounds: 72-108 s /
    # 792-1188 chars.
    assert "108-second" in msg
    assert "792" in msg
    assert "1188" in msg


def test_retry_still_fires_when_first_pass_below_acceptance_min():
    """Expansion retry fires when the first pass lands below
    the REQUESTED-target acceptance minimum. Even though K6 was
    told to aim at synth (70 s / min 616 chars), the retry
    decision uses acceptance min (792 chars) — so a 600-char
    first pass triggers retry."""
    ws = _workspace("dc-expand-retry@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 600),   # below 792 acceptance min
            _fake_script_result("x" * 990),   # inside acceptance
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert fake_brb.call_count == 2
    assert result.brief == "x" * 990


def test_retry_still_fires_when_first_pass_above_acceptance_max():
    """Compression retry fires when the first pass overshoots
    the REQUESTED-target acceptance max."""
    ws = _workspace("dc-compress-retry@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1400),  # over 1188 acceptance max
            _fake_script_result("x" * 1000),  # inside acceptance
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert fake_brb.call_count == 2
    assert result.brief == "x" * 1000


def test_gate_duration_overshoot_below_provider_cap_raises_too_long():
    """SESSION 253 amendment A — classification correctness.

    90s target with the 1900-char provider cap:
      * duration tolerance high = 1188 chars (11 cps × 108 s)
      * provider cap high = 1900 chars
    A 1266-char script (~117 s) is over the duration tolerance
    but under the provider cap. Must raise REASON_TOO_LONG (NOT
    REASON_OVER_PROVIDER_CAP — the provider cap wasn't the
    binding constraint)."""
    ws = _workspace("dc-too-long-not-cap@t")
    tm = _teammate(ws)
    # First: 1303 (over duration max 1188, under cap 1900).
    # Retry:  1266 (still over duration max, under cap).
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1303),
            _fake_script_result("x" * 1266),
        ],
    ):
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic",
                target_duration_seconds=90,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    err = exc_info.value
    assert err.reason == DurationContractError.REASON_TOO_LONG
    # Message names seconds first (operator unit) and does NOT
    # mention "provider ceiling" for a duration-only violation.
    msg = str(err)
    assert "provider" not in msg.lower()
    assert "provider ceiling" not in msg.lower()
    assert "108-second maximum" in msg or "108-second" in msg
    # Attributes carry both bounds distinctly so future consumers
    # can render richer UIs without misclassifying.
    assert err.duration_max_chars == 1188
    assert err.provider_cap_chars == AVATAR_SPEECH_SAFE_MAX_CHARS


def test_gate_true_provider_cap_violation_still_classifies_as_over_cap():
    """SESSION 253 amendment A — the OTHER classification.

    A synthesis result that actually exceeds the 1900-char provider
    cap must still raise REASON_OVER_PROVIDER_CAP. Only fireable
    for targets long enough that the cap is the binding constraint
    (~172s+ at 11 cps + default cap)."""
    ws = _workspace("dc-true-cap-violation@t")
    tm = _teammate(ws)
    # 180s target → duration tolerance (1584, 2376), effective
    # (1584, 1900) under cap. First pass 2100 (over cap), retry
    # 1950 (still over cap). Must raise OVER_PROVIDER_CAP with
    # 1900 in the message.
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 2100),
            _fake_script_result("x" * 1950),
        ],
    ):
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic",
                target_duration_seconds=180,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    err = exc_info.value
    assert err.reason == DurationContractError.REASON_OVER_PROVIDER_CAP
    msg = str(err)
    assert "1900-char per-call provider ceiling" in msg
    assert err.provider_cap_chars == 1900


def test_gate_over_provider_cap_after_retry_raises_over_cap_reason():
    """180s target WITH the 1900 cap: if retry still exceeds
    1900 chars, raise REASON_OVER_PROVIDER_CAP (not TOO_LONG).
    Caller MUST pass ``max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS``
    to activate the cap (defaults to no-cap for the long_form_ad
    chunked path)."""
    ws = _workspace("dc-over-cap@t")
    tm = _teammate(ws)
    # First: 2100 (over cap). Retry: 1950 (still over cap 1900).
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 2100),
            _fake_script_result("x" * 1950),
        ],
    ):
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic",
                target_duration_seconds=180,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    assert exc_info.value.reason == (
        DurationContractError.REASON_OVER_PROVIDER_CAP
    )
    assert exc_info.value.effective_max_chars == 1900


def test_gate_180s_1900_char_result_accepts():
    """A 1900-char result for 180s target is at the top of the
    provider-safe budget. Predicts ~172s speech; inside the
    ±20% tolerance band (144-216s) AND under the 1900 cap.
    Must accept."""
    ws = _workspace("dc-180s-happy@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result("x" * 1850),
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=180,
        )
    assert result.brief == "x" * 1850
    fake_brb.assert_called_once()


def test_gate_180s_never_asks_llm_above_provider_cap():
    """SESSION 253 amendment — the LENGTH block K6 sees for a 180 s
    request under the 1900-char cap must not tell the LLM to aim
    above 1900 or accept above 1900.

    Post-amendment-B: K6 sees the SYNTH target (140 s for 180 s
    requested); the provider cap flow-through is what this test
    actually guards, plus the shape."""
    ws = _workspace("dc-180s-prompt@t")
    tm = _teammate(ws)
    captured = {}

    def _capture(sp, prompt, **kwargs):
        captured["kwargs"] = kwargs
        return _fake_script_result("x" * 1800)

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=_capture,
    ):
        synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=180,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert captured["kwargs"]["target_shape"] == "long_form"
    # K6 sees the SYNTH target (140), not the operator-requested
    # 180. Acceptance still uses 180 (asserted elsewhere).
    assert captured["kwargs"]["target_duration_seconds"] == 140
    # Provider cap flows through to K6.
    assert captured["kwargs"]["max_script_chars"] == AVATAR_SPEECH_SAFE_MAX_CHARS


def test_gate_max_script_chars_none_disables_provider_cap():
    """long_form_ad calls with max_script_chars=None because it
    chunks output. In that path the cap doesn't apply — a 2200-
    char result for 180s should PASS the char check (still inside
    duration tolerance) rather than reject as over-cap."""
    ws = _workspace("dc-no-cap@t")
    tm = _teammate(ws)
    # 180s tolerance: (1584, 2376) chars. 2200 sits inside.
    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result("x" * 2200),
    ):
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=180,
            max_script_chars=None,
        )
    assert result.brief == "x" * 2200


def test_gate_incompatible_target_fails_before_llm_call():
    """300s target with the 1900-char cap is incompatible;
    the helper raises before making the first LLM call."""
    ws = _workspace("dc-incompat@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
    ) as fake_brb:
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic",
                target_duration_seconds=300,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    assert exc_info.value.reason == (
        DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER
    )
    fake_brb.assert_not_called()


# ---- 4. talking_head recipe form -------------------------------


def test_talking_head_recipe_exposes_target_duration_seconds():
    """Recipe form has the new duration select field (was missing
    pre-SESSION 253; the operator dogfood exposed the omission)."""
    recipe = RECIPES["talking_head"]
    field_names = [f.name for f in recipe.fields]
    assert "target_duration_seconds" in field_names
    dur_field = next(
        f for f in recipe.fields if f.name == "target_duration_seconds"
    )
    assert dur_field.type == "select"
    assert dur_field.default == ""  # no default duration
    # 30 / 60 / 90 / 120 / 180 + empty option.
    values = {c["value"] for c in dur_field.choices}
    assert values == {"", "30", "60", "90", "120", "180"}


# ---- 5. starter accepts + persists / gates on use_knowledge ----


def test_talking_head_starter_persists_duration_when_use_knowledge_true():
    ws = _workspace("th-persist@t")
    tm = _teammate(ws)
    comp = talking_head(
        workspace=ws, spokesperson=tm,
        script="Topic about kayaking basics",
        use_knowledge=True,
        target_duration_seconds=90,
        mock_mode=True,
    )
    step = comp.steps.first()
    assert step.params["target_duration_seconds"] == 90
    assert step.params["use_knowledge"] is True


def test_talking_head_starter_ignores_duration_when_use_knowledge_false():
    """SESSION 253 amendment 2 — never silently rewrite an exact
    operator script. If use_knowledge=False, the duration is
    dropped from step params (with a log warning)."""
    ws = _workspace("th-ignore-dur@t")
    tm = _teammate(ws)
    comp = talking_head(
        workspace=ws, spokesperson=tm,
        script="This is my exact hand-written script that must be spoken verbatim.",
        use_knowledge=False,
        target_duration_seconds=90,
        mock_mode=True,
    )
    step = comp.steps.first()
    assert "target_duration_seconds" not in step.params
    assert step.params["use_knowledge"] is False


def test_talking_head_starter_accepts_string_duration_from_drf():
    """DRF select choices serialize to strings; starter must coerce."""
    ws = _workspace("th-str-dur@t")
    tm = _teammate(ws)
    comp = talking_head(
        workspace=ws, spokesperson=tm,
        script="topic",
        use_knowledge=True,
        target_duration_seconds="90",
        mock_mode=True,
    )
    step = comp.steps.first()
    assert step.params["target_duration_seconds"] == 90


def test_talking_head_starter_no_duration_omits_step_param():
    """When the operator picks the empty/default option, no
    duration ends up on step params (preserves pre-SESSION-253
    standalone-shape behavior)."""
    ws = _workspace("th-no-dur@t")
    tm = _teammate(ws)
    comp = talking_head(
        workspace=ws, spokesperson=tm,
        script="topic",
        use_knowledge=True,
        target_duration_seconds="",
        mock_mode=True,
    )
    step = comp.steps.first()
    assert "target_duration_seconds" not in step.params


# ---- 6. primitive routing + Runway-not-called-on-rejection ----


def test_primitive_calls_duration_helper_when_duration_and_knowledge():
    """Real-mode avatar_speech with use_knowledge=True and
    target_duration_seconds set MUST route synthesis through
    synthesize_with_duration_gate (not the naked build_render_brief)."""
    ws = _workspace("th-prim-route@t")
    tm = _teammate(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="test",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={
            "script": "topic",
            "use_knowledge": True,
            "target_duration_seconds": 90,
        },
    )
    # Media-engine mock — must not be called on rejection paths.
    cm = MagicMock()
    cm.__enter__.return_value = MagicMock()
    cm.__exit__.return_value = False

    # Mock the helper to return a valid ScriptResult.
    def _fake_helper(sp, prompt, **kwargs):
        assert kwargs["target_duration_seconds"] == 90
        assert kwargs["max_script_chars"] == AVATAR_SPEECH_SAFE_MAX_CHARS
        return _fake_script_result("x" * 990)

    with patch(
        "apps.compositions.primitives.avatar_speech.synthesize_with_duration_gate",
        side_effect=_fake_helper,
    ) as fake_helper, patch(
        "apps.compositions.primitives.avatar_speech.build_render_brief",
    ) as fake_brb, patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.avatar_speech.time.sleep",
    ):
        from character_os.clients.media_engine import (
            VideoCreateResult, VideoPollResult,
        )
        cm.__enter__.return_value.create_avatar_speech.return_value = (
            VideoCreateResult(
                task_id="t", status="pending", kind="avatar_speech",
                mock_mode=False,
            )
        )
        cm.__enter__.return_value.poll_task.return_value = VideoPollResult(
            task_id="t", status="ready", progress=1.0,
            output_url="/fake.mp4", duration_seconds=57.0,
            error=None, failure_code=None, mock_mode=False,
        )
        # Also mock _resolve_avatar_id to avoid teammate.runway_avatar_id
        # requirements not related to this test.
        GenerateAvatarSpeechPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    fake_helper.assert_called_once()
    # The non-duration path must NOT have been invoked.
    fake_brb.assert_not_called()


def test_primitive_falls_through_to_build_render_brief_without_duration():
    """Backward compat: no target_duration_seconds on the step →
    standalone shape via build_render_brief (existing behavior).
    """
    ws = _workspace("th-prim-nofallthrough@t")
    tm = _teammate(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="test",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={
            "script": "topic",
            "use_knowledge": True,
            # NO target_duration_seconds
        },
    )
    cm = MagicMock()
    cm.__enter__.return_value = MagicMock()
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.avatar_speech.synthesize_with_duration_gate",
    ) as fake_helper, patch(
        "apps.compositions.primitives.avatar_speech.build_render_brief",
        return_value=_fake_script_result("short standalone script"),
    ) as fake_brb, patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.avatar_speech.time.sleep",
    ):
        from character_os.clients.media_engine import (
            VideoCreateResult, VideoPollResult,
        )
        cm.__enter__.return_value.create_avatar_speech.return_value = (
            VideoCreateResult(
                task_id="t", status="pending", kind="avatar_speech",
                mock_mode=False,
            )
        )
        cm.__enter__.return_value.poll_task.return_value = VideoPollResult(
            task_id="t", status="ready", progress=1.0,
            output_url="/fake.mp4", duration_seconds=30.0,
            error=None, failure_code=None, mock_mode=False,
        )
        GenerateAvatarSpeechPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    fake_helper.assert_not_called()
    fake_brb.assert_called_once()


def test_primitive_rejection_prevents_media_engine_call():
    """LOAD-BEARING ECONOMIC INVARIANT (SESSION 253 amendment).

    When the duration helper raises DurationContractError, the
    primitive must convert to PrimitiveError and MUST NOT call
    create_avatar_speech. Zero Runway credits spent on a duration-
    mismatched script."""
    ws = _workspace("th-prim-noruncall@t")
    tm = _teammate(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="test",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={
            "script": "topic",
            "use_knowledge": True,
            "target_duration_seconds": 90,
        },
    )

    fake_client = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False

    def _reject(sp, prompt, **kwargs):
        raise DurationContractError(
            actual_chars=300, actual_words=60, actual_seconds=27,
            target_duration_seconds=90,
            min_seconds=72, max_seconds=108,
            effective_min_chars=792, effective_max_chars=1188,
            synthesized_text="x" * 300,
            reason=DurationContractError.REASON_TOO_SHORT,
        )

    with patch(
        "apps.compositions.primitives.avatar_speech.synthesize_with_duration_gate",
        side_effect=_reject,
    ), patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc_info:
            GenerateAvatarSpeechPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )

    # THE INVARIANT: media-engine client's create_avatar_speech
    # method must never be called.
    fake_client.create_avatar_speech.assert_not_called()
    # And PrimitiveError message carries the actionable
    # duration-mismatch detail.
    assert "Duration contract failed" in str(exc_info.value)
    assert "too_short" in str(exc_info.value)


def test_primitive_persists_rejection_metadata_on_composition():
    """Same shape as K6.4 rejection persistence: verification_status
    = 'rejected', rejected_synthesis carries the draft, error_message
    describes the miss. Operator sees this on the composition
    detail page."""
    ws = _workspace("th-prim-rejmeta@t")
    tm = _teammate(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="test",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={
            "script": "topic",
            "use_knowledge": True,
            "target_duration_seconds": 90,
        },
    )

    def _reject(sp, prompt, **kwargs):
        raise DurationContractError(
            actual_chars=300, actual_words=60, actual_seconds=27,
            target_duration_seconds=90,
            min_seconds=72, max_seconds=108,
            effective_min_chars=792, effective_max_chars=1188,
            synthesized_text="short draft",
            reason=DurationContractError.REASON_TOO_SHORT,
        )

    with patch(
        "apps.compositions.primitives.avatar_speech.synthesize_with_duration_gate",
        side_effect=_reject,
    ):
        with pytest.raises(PrimitiveError):
            GenerateAvatarSpeechPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )

    comp.refresh_from_db()
    assert comp.verification_status == "rejected"
    assert comp.rejected_synthesis == "short draft"
    assert "Duration contract failed" in comp.error_message
    assert comp.writing_contract_version == 1


# ---- 8. long_form_ad still works via extracted helper ----------


def test_long_form_ad_delegates_to_shared_duration_gate():
    """long_form_ad's synthesis path now calls
    synthesize_with_duration_gate directly. Assert the delegation
    happens (no inline retry logic left in the starter)."""
    from apps.compositions.starters import long_form_ad
    from character_os.script_synthesis import ScriptResult

    ws = _workspace("lfa-delegates@t")
    tm = _teammate(ws)

    def _fake_helper(sp, prompt, **kwargs):
        # long_form_ad chunks output — no provider cap.
        assert kwargs["max_script_chars"] is None
        assert kwargs["target_duration_seconds"] == 90
        return ScriptResult(
            brief="a synthesized long-form brief that fits the target",
            chunk_ids=[], used_knowledge=True,
            verification_status="verified", writing_contract_version=1,
        )

    with patch(
        "apps.compositions.starters.synthesize_with_duration_gate",
        side_effect=_fake_helper,
    ) as fake_helper:
        comp = long_form_ad(
            workspace=ws, spokesperson=tm,
            script="topic",
            use_knowledge=True,
            target_duration_seconds=90,
            mock_mode=True,
        )
    fake_helper.assert_called_once()
    assert comp.template_kind == "long_form_ad"
