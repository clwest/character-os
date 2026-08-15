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
    DurationContractError,
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
    # Second call carries a corrective_hint mentioning the
    # under-budget number.
    retry_kwargs = fake_brb.call_args_list[1].kwargs
    assert "corrective_hint" in retry_kwargs
    assert "792" in retry_kwargs["corrective_hint"]  # effective_min


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
    """SESSION 253 amendment — the LENGTH block K6 sees for a 180s
    request under the 1900-char cap must not tell the LLM to aim
    above 1900 or accept above 1900."""
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
    assert captured["kwargs"]["target_duration_seconds"] == 180
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
