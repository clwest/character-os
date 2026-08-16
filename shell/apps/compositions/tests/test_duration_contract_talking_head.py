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
from character_os.writing_contract import WRITING_CONTRACT_VERSION

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


def test_avatar_speech_delivery_rate_locked_at_15_cps():
    """SESSION 253 Stage 1 CALIBRATION LOCK — the delivery-rate
    estimator is 15 cps, empirically calibrated from five
    controlled real-Runway avatar_video renders (mean 15.40 cps,
    median 15.446, StdDev 0.448, CV 2.9%). Moving this value
    changes every duration/char translation in the codebase.

    Recalibrate ONLY from fresh dogfood evidence, and update this
    test alongside so the check remains a deliberate lock rather
    than accidental drift catch.

    Both peer copies MUST move together — they represent the same
    real-world quantity (Runway avatar delivery rate)."""
    from apps.compositions.primitives.avatar_speech import (
        _AVATAR_SPEECH_CHARS_PER_SECOND as PRIMITIVE_CPS,
    )
    from apps.compositions.starters import (
        _AVATAR_SPEECH_CHARS_PER_SECOND as STARTERS_CPS,
    )
    assert PRIMITIVE_CPS == 15
    assert STARTERS_CPS == 15
    assert PRIMITIVE_CPS == STARTERS_CPS


def test_90s_duration_math_reflects_15_cps():
    """SESSION 253 Stage 3 — the ideal/min/max char budget for a
    90-second request MUST derive from 15 cps.

    90 * 15 = 1350 ideal.
    90 * 15 * 0.8 = 1080 min.
    90 * 15 * 1.2 = 1620 max.

    Regression guard against the pre-Stage-1 11 cps that produced
    (990, 792, 1188) and silently underestimated the character
    budget by ~35 %, causing the operator's SESSION 253 dogfood
    to ship 62.7 s videos for 90 s requests."""
    ideal, low, high = char_budget_for_duration(90)
    assert ideal == 1350
    assert low == 1080
    assert high == 1620


# ---- 2. effective budget across durations -----------------------


def test_effective_budget_short_targets_unaffected_by_cap():
    """30s/60s/90s targets are well below the 1900-char cap; the
    cap should not alter their budgets. SESSION 253 Stage 3 —
    120 s dropped from this iteration because at 15 cps its
    raw_max = 2160 does clip against the 1900 cap (asserted
    separately in the 120-s clamp test)."""
    for target in (30, 60, 90):
        raw_ideal, raw_low, raw_high = char_budget_for_duration(target)
        eff_ideal, eff_low, eff_high = compute_effective_budget(
            target, AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
        assert eff_low == raw_low
        assert eff_high == raw_high
        assert eff_ideal == raw_ideal


def test_effective_budget_120s_clamps_at_cap():
    """SESSION 253 Stage 3 — 120 s raw budget at 15 cps is
    (1800, 1440, 2160). Provider cap 1900 clips the high edge;
    duration min is well under the cap so the target is still
    FEASIBLE, unlike 180 s which raises INCOMPATIBLE.

    eff_ideal follows the 50-char safety-buffer rule from
    ``duration_contract._IDEAL_SAFETY_BUFFER_CHARS``: min(ideal,
    max(low, high - 50)) = min(1800, max(1440, 1850)) = 1800."""
    ideal, low, high = compute_effective_budget(120, AVATAR_SPEECH_SAFE_MAX_CHARS)
    assert high == 1900
    assert low == 1440
    assert ideal == 1800


def test_effective_budget_180s_incompatible_under_15cps():
    """SESSION 253 Stage 3 — at the recalibrated 15 cps rate, a
    180-second request needs raw_min = 180 * 15 * 0.8 = 2160
    chars, which exceeds the 1900-char provider cap. The gate
    must raise INCOMPATIBLE up front rather than clamping
    silently — the talking_head recipe removed 180 s from its
    choices for exactly this reason (long_form_ad still offers
    180 s because it chunks)."""
    with pytest.raises(DurationContractError) as exc_info:
        compute_effective_budget(180, AVATAR_SPEECH_SAFE_MAX_CHARS)
    assert exc_info.value.reason == (
        DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER
    )


def test_effective_budget_300s_incompatible_raises_before_llm():
    """300s target requires min 3600 chars (300 * 15 * 0.8), which
    far exceeds the 1900-char cap. Reject up front — no LLM call
    could satisfy both constraints."""
    with pytest.raises(DurationContractError) as exc_info:
        compute_effective_budget(300, AVATAR_SPEECH_SAFE_MAX_CHARS)
    assert exc_info.value.reason == (
        DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER
    )


def test_char_budget_for_duration_with_cap_matches_effective_budget():
    """SESSION 253 amendment — char_budget_for_duration itself
    accepts max_script_chars and produces the same clamped
    triple as compute_effective_budget for the same inputs.
    SESSION 253 Stage 3 — 180 s excluded because it now raises
    INCOMPATIBLE at the recalibrated 15 cps rate."""
    for target in (30, 60, 90, 120):
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
        writing_contract_version=WRITING_CONTRACT_VERSION,
    )


def test_gate_accepts_first_pass_in_tolerance():
    """When K6 returns a script inside the tolerance band on the
    first pass, no retry fires and the result flows through.
    SESSION 253 Stage 3 — 90 s at 15 cps: raw budget (1350,
    1080, 1620). 1350 sits exactly at the ideal."""
    ws = _workspace("dc-first-pass@t")
    tm = _teammate(ws)
    perfect = "x" * 1350

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
    """First pass too short → one expansion retry → accept.
    SESSION 253 Stage 3 — 90 s at 15 cps: acceptance [1080, 1620].
    First = 400 (way below 1080); retry = 1350 (accept)."""
    ws = _workspace("dc-retry-short@t")
    tm = _teammate(ws)
    short = "x" * 400
    corrected = "x" * 1350

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
    # Second call carries a corrective_hint referencing the
    # SYNTH-target budget (SESSION 253 amendment B / SESSION 254
    # multiplier 0.90) so K6 keeps aiming low on the retry. For a
    # 90 s request the synth target is 81 s → synth_min =
    # round(81 * 15 * 0.8) = 972.
    retry_kwargs = fake_brb.call_args_list[1].kwargs
    assert "corrective_hint" in retry_kwargs
    assert "972" in retry_kwargs["corrective_hint"]


def test_gate_retries_when_long_then_accepts():
    """First pass too long → one compression retry → accept.
    SESSION 253 Stage 3 — 90 s at 15 cps: acceptance high is
    1620 chars; 1800 chars overshoots; retry 1350 accepts."""
    ws = _workspace("dc-retry-long@t")
    tm = _teammate(ws)
    long_ = "x" * 1800  # over 1620 acceptance max, under 1900 cap
    corrected = "x" * 1350

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
    """SESSION 253 amendment B / SESSION 254 recalibration — the
    synthesis-target multiplier is empirically calibrated. The
    original 0.78 was measured against a cps=11 estimator and
    over-corrected after the cps 11 → 15 recalibration in Stage 3;
    SESSION 254 raised it to 0.90 based on the post-Stage-3 Penny
    dogfood. Locking the value so accidental drift lights up as
    an explicit test failure. Recalibrate ONLY from new dogfood
    evidence."""
    assert K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 0.90


def test_calibrated_synthesis_target_90s_is_81s():
    """SESSION 254 — 90 s operator request → K6 sees an 81 s
    synthesis target under the 0.90 multiplier."""
    assert calibrated_synthesis_target(90) == 81


def test_calibrated_synthesis_target_120s_is_108s():
    assert calibrated_synthesis_target(120) == 108


def test_calibrated_synthesis_target_short_targets_disable_bias():
    """Below the 30 s calibration floor, the bias is skipped
    (unvalidated regime; applying the bias could push very short
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
        return _fake_script_result("x" * 1350)

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=_capture,
    ):
        synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    # K6 sees synth target (81), NOT requested target (90).
    assert captured["kwargs"]["target_duration_seconds"] == 81
    assert captured["kwargs"]["target_duration_seconds"] != 90


def test_synth_target_leak_test_120s_covers_the_general_case():
    ws = _workspace("dc-synth-120@t")
    tm = _teammate(ws)
    captured = {}

    def _capture(sp, prompt, **kwargs):
        captured["kwargs"] = kwargs
        # 120 s at 15 cps: acceptance (1440, 1900-clamped). 1800
        # sits inside; no retry required for this capture test.
        return _fake_script_result("x" * 1800)

    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=_capture,
    ):
        synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=120,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert captured["kwargs"]["target_duration_seconds"] == 108


def test_acceptance_band_derives_from_requested_not_synth_target():
    """SESSION 253 amendment B / SESSION 254 — 90 s request
    accepts 1080-1620 chars (=72-108 s at 15 cps). NOT the
    synth-target band (1215 ideal / 972-1458 chars for 81 s).

    A 1500-char script for 90 s request is:
      below acceptance-max 1620 → accept
      above synth-max 1458 → would REJECT under the wrong contract
    Assert we accept it (correct acceptance band)."""
    ws = _workspace("dc-accept-band@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        return_value=_fake_script_result("x" * 1500),
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    # No retry, accepted on first pass.
    fake_brb.assert_called_once()
    assert result.brief == "x" * 1500


def test_180s_target_raises_incompatible_before_llm():
    """SESSION 253 Stage 3 — at 15 cps + 1900-char cap, 180 s is
    INCOMPATIBLE (raw_min = 2160 > 1900). The gate must raise
    before any LLM call fires."""
    ws = _workspace("dc-180-incompat@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
    ) as fake_brb:
        with pytest.raises(DurationContractError) as exc_info:
            synthesize_with_duration_gate(
                tm, "topic",
                target_duration_seconds=180,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    assert exc_info.value.reason == (
        DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER
    )
    fake_brb.assert_not_called()


def test_error_message_never_names_synth_target():
    """SESSION 253 amendment B / SESSION 254 — error messages must
    NEVER refer to the calibrated synth target. The operator asked
    for 90 s; error messages say 90 s (even though K6 was
    internally aiming at 81 s).

    SESSION 253 Stage 3 — 90 s at 15 cps: acceptance chars
    (1080, 1620). First 1850 (over 1620); retry 1800 (still over).
    Both TOO_LONG, both below 1900 cap."""
    ws = _workspace("dc-err-msg-req-only@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1850),
            _fake_script_result("x" * 1800),
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
    # Exception carries REQUESTED target — not synth (81).
    assert err.target_duration_seconds == 90
    msg = str(err)
    # 90-second target must appear (operator asked for 90).
    assert "90-second target" in msg
    # 81-second synth target must NOT leak.
    assert "81-second" not in msg
    assert "81s" not in msg
    # Acceptance band uses requested-target bounds: 72-108 s /
    # 1080-1620 chars at 15 cps.
    assert "108-second" in msg
    assert "1080" in msg
    assert "1620" in msg


def test_retry_still_fires_when_first_pass_below_acceptance_min():
    """Expansion retry fires when the first pass lands below
    the REQUESTED-target acceptance minimum. Even though K6 was
    told to aim at synth (81 s / min 972 chars at 15 cps under
    the SESSION 254 multiplier 0.90), the retry decision uses
    acceptance min (1080 chars) — so an 800-char first pass
    triggers retry."""
    ws = _workspace("dc-expand-retry@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 800),   # below 1080 acceptance min
            _fake_script_result("x" * 1350),  # inside acceptance
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert fake_brb.call_count == 2
    assert result.brief == "x" * 1350


def test_retry_still_fires_when_first_pass_above_acceptance_max():
    """Compression retry fires when the first pass overshoots
    the REQUESTED-target acceptance max. 90 s at 15 cps →
    acceptance max 1620."""
    ws = _workspace("dc-compress-retry@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1800),  # over 1620 acceptance max
            _fake_script_result("x" * 1350),  # inside acceptance
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic",
            target_duration_seconds=90,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    assert fake_brb.call_count == 2
    assert result.brief == "x" * 1350


def test_gate_duration_overshoot_below_provider_cap_raises_too_long():
    """SESSION 253 amendment A — classification correctness.

    90s target with the 1900-char provider cap:
      * duration tolerance high = 1620 chars (15 cps × 108 s)
      * provider cap high = 1900 chars
    An 1800-char script is over the duration tolerance but
    under the provider cap. Must raise REASON_TOO_LONG (NOT
    REASON_OVER_PROVIDER_CAP — the provider cap wasn't the
    binding constraint)."""
    ws = _workspace("dc-too-long-not-cap@t")
    tm = _teammate(ws)
    # First: 1850 (over duration max 1620, under cap 1900).
    # Retry:  1800 (still over duration max, under cap).
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1850),
            _fake_script_result("x" * 1800),
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
    assert err.duration_max_chars == 1620
    assert err.provider_cap_chars == AVATAR_SPEECH_SAFE_MAX_CHARS


def test_gate_true_provider_cap_violation_still_classifies_as_over_cap():
    """SESSION 253 amendment A — the OTHER classification.

    A synthesis result that actually exceeds the 1900-char provider
    cap must still raise REASON_OVER_PROVIDER_CAP. At 15 cps + the
    default cap, the cap becomes binding at ~106 s target and
    above (raw_max = target * 15 * 1.2 exceeds 1900).

    SESSION 253 Stage 3 — target moved from 180 s → 120 s. 180 s
    is now INCOMPATIBLE at 15 cps (raw_min 2160 > cap 1900), so
    the cap-violation-after-retry path cannot be exercised there
    any more. 120 s: raw budget (1800, 1440, 2160), effective
    (1800, 1440, 1900). First pass 2100 (over cap 1900), retry
    1950 (still over cap 1900)."""
    ws = _workspace("dc-true-cap-violation@t")
    tm = _teammate(ws)
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
                target_duration_seconds=120,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    err = exc_info.value
    assert err.reason == DurationContractError.REASON_OVER_PROVIDER_CAP
    msg = str(err)
    assert "1900-char per-call provider ceiling" in msg
    assert err.provider_cap_chars == 1900


def test_gate_over_provider_cap_after_retry_raises_over_cap_reason():
    """120 s target WITH the 1900 cap: if retry still exceeds
    1900 chars, raise REASON_OVER_PROVIDER_CAP (not TOO_LONG).
    Caller MUST pass ``max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS``
    to activate the cap (defaults to no-cap for the long_form_ad
    chunked path).

    SESSION 253 Stage 3 — target moved 180 → 120 for the same
    reason as the sibling test above."""
    ws = _workspace("dc-over-cap@t")
    tm = _teammate(ws)
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
                target_duration_seconds=120,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
            )
    assert exc_info.value.reason == (
        DurationContractError.REASON_OVER_PROVIDER_CAP
    )
    assert exc_info.value.effective_max_chars == 1900


def test_gate_max_script_chars_none_disables_provider_cap():
    """long_form_ad calls with max_script_chars=None because it
    chunks output. In that path the cap doesn't apply — a 2200-
    char result for 180s should PASS the char check (still inside
    duration tolerance) rather than reject as over-cap.

    At 15 cps, 180 s tolerance = (2160, 3240) chars. 2200 sits
    inside."""
    ws = _workspace("dc-no-cap@t")
    tm = _teammate(ws)
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
    # SESSION 253 Stage 3 — 180 s removed from talking_head choices
    # after the 15 cps recalibration made it INCOMPATIBLE with the
    # 1900-char single-call provider ceiling. long_form_ad still
    # offers 180 s because it chunks.
    # 30 / 60 / 90 / 120 + empty option.
    values = {c["value"] for c in dur_field.choices}
    assert values == {"", "30", "60", "90", "120"}
    # 180 s must NOT appear.
    assert "180" not in values


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
    assert comp.writing_contract_version == WRITING_CONTRACT_VERSION


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
            verification_status="verified",
            writing_contract_version=WRITING_CONTRACT_VERSION,
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
