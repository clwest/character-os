"""SESSION 273 §25 — pin the corrective-expansion hint to the RAW
acceptance floor.

The bug this test file guards against:
  * SESSION 253/254 introduced a 0.90 first-pass calibration
    multiplier (``K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER``) to
    compensate for gpt-5's habitual overshoot on the operator-
    requested target.
  * Prior to §25 the SAME calibrated synth target was passed to
    ``_expansion_hint`` on the corrective retry. For a 90 s
    operator target that meant telling the LLM "EXPAND TO AT
    LEAST 972 chars" while the actual render acceptance minimum
    is 1080 chars — a 108-char instrumentation gap.
  * On fresh / minimally-authored characters (Ruby SESSION 273
    Slice β — 4/4 attempts clustered at 893 / 1032 / 1031 / 1008
    chars; 3/4 cleared 972 but 0/4 cleared 1080) the LLM obeyed
    the stated minimum literally and the render failed
    deterministically. Saturated characters (Patch/Rivet — 15/15
    90 s attempts produced 1163-1599 chars) hid the gap by
    overshooting.
  * §25 fix: on the expansion path, pass the operator target's
    char budget (clamped to the provider cap) to the hint, so the
    LLM's stated "at least" floor equals the actual acceptance
    floor. First-pass calibration and compression retry are
    unchanged.

These tests are separate from
``test_session272_slice_f_expansion_hint_anchor.py`` (which pins
``_expansion_hint``'s function-level behaviour with fixed args) and
from the pre-existing ``test_duration_contract_talking_head`` tests
(which pin ``synthesize_with_duration_gate``'s general behaviour).
This file specifically pins the §25 caller-side change: the hint
arguments the gate chooses for the corrective retry.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os.duration_contract import (
    AVATAR_SPEECH_SAFE_MAX_CHARS,
    DurationContractError,
    synthesize_with_duration_gate,
)
from character_os.script_synthesis import ScriptResult


def _fake_script_result(text: str) -> ScriptResult:
    return ScriptResult(
        brief=text,
        used_knowledge=False,
        chunk_ids=[],
        verification_warnings=[],
        verification_status="skipped",
        writing_contract_version=0,
    )


def _workspace(email: str) -> Workspace:
    User = get_user_model()
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="probe", business_brief="b",
        runway_avatar_id="fake-avatar",
    )


# ---- 90s case (Ruby's exact scenario) ------------------------------


@pytest.mark.django_db
def test_90s_corrective_hint_targets_1080_render_min_not_972_synth_min():
    """A 90 s render whose first pass falls below 1080 chars must
    receive a corrective hint stating the RAW render minimum (1080),
    NOT the synth-calibrated minimum (972). This directly guards
    against Ruby SESSION 273 Slice β's four-run failure cluster
    (893 / 1032 / 1031 / 1008 — 3/4 obeyed 972 but 0/4 cleared 1080).
    """
    ws = _workspace("s273-90s@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 400),   # first pass too short
            _fake_script_result("x" * 1350),  # corrective succeeds
        ],
    ) as fake_brb:
        result = synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=90,
        )
    assert result.brief == "x" * 1350
    retry_hint = fake_brb.call_args_list[1].kwargs["corrective_hint"]
    # Positive: raw acceptance min for 90 s = 90 * 15 * 0.8 = 1080.
    assert "EXPAND YOUR SCRIPT TO AT LEAST 1080 CHARACTERS" in retry_hint
    assert "Target is 90s" in retry_hint
    assert "aim for ~1350" in retry_hint
    assert "do not exceed 1620" in retry_hint
    # Negative: the pre-§25 synth-min references must be absent.
    assert "AT LEAST 972 CHARACTERS" not in retry_hint
    assert "Target is 81s" not in retry_hint


# ---- 60s / 120s scale-check -----------------------------------------


@pytest.mark.django_db
def test_60s_corrective_hint_targets_720_render_min():
    """60 s raw acceptance min = 60 * 15 * 0.8 = 720 chars.
    Synth-calibrated (54 s) min would be 648 — a 72-char gap.
    Post-§25 hint must state 720."""
    ws = _workspace("s273-60s@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 300),
            _fake_script_result("x" * 900),
        ],
    ) as fake_brb:
        synthesize_with_duration_gate(tm, "topic", target_duration_seconds=60)
    retry_hint = fake_brb.call_args_list[1].kwargs["corrective_hint"]
    assert "EXPAND YOUR SCRIPT TO AT LEAST 720 CHARACTERS" in retry_hint
    assert "Target is 60s" in retry_hint
    assert "AT LEAST 648 CHARACTERS" not in retry_hint


@pytest.mark.django_db
def test_120s_corrective_hint_targets_1440_render_min_clamped_at_cap():
    """120 s raw acceptance min = 120 * 15 * 0.8 = 1440 chars.
    Raw max would be 2160 but is clamped to the 1900 provider cap.
    Ideal (1800) is nudged below max under
    ``_IDEAL_SAFETY_BUFFER_CHARS`` when needed. Post-§25 hint must
    state 1440 as the minimum and honour the cap on the max."""
    ws = _workspace("s273-120s@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 800),
            _fake_script_result("x" * 1700),  # in [1440, 1900] band
        ],
    ) as fake_brb:
        synthesize_with_duration_gate(
            tm, "topic", target_duration_seconds=120,
            max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
        )
    retry_hint = fake_brb.call_args_list[1].kwargs["corrective_hint"]
    assert "EXPAND YOUR SCRIPT TO AT LEAST 1440 CHARACTERS" in retry_hint
    assert "Target is 120s" in retry_hint
    # Max is clamped to the 1900 provider cap.
    assert "do not exceed 1900" in retry_hint
    # Ideal (1800 = 120 * 15) already sits under the 1900 cap so the
    # safety-buffer branch does not fire.
    assert "aim for ~1800" in retry_hint


# ---- Structural invariant: hint min == render acceptance min --------


@pytest.mark.django_db
def test_corrective_hint_min_equals_render_acceptance_min_across_targets():
    """The §25 structural invariant: for every operator target, the
    corrective-expansion hint's minimum equals the acceptance-gate's
    minimum. A drift here reintroduces the pre-§25 instrumentation
    gap that caused Ruby's four failures.
    """
    for target, expected_hint_min in [
        (45, 540),   # 45 * 15 * 0.8
        (60, 720),
        (75, 900),
        (90, 1080),
        (105, 1260),
        (120, 1440),
    ]:
        ws = _workspace(f"s273-scan-{target}s@t")
        tm = _teammate(ws)
        with patch(
            "character_os.duration_contract.build_render_brief",
            side_effect=[
                _fake_script_result("x" * 100),
                _fake_script_result("x" * (expected_hint_min + 50)),
            ],
        ) as fake_brb:
            synthesize_with_duration_gate(
                tm, "topic", target_duration_seconds=target,
            )
        hint = fake_brb.call_args_list[1].kwargs["corrective_hint"]
        assert f"AT LEAST {expected_hint_min} CHARACTERS" in hint, (
            f"target={target}s: expected 'AT LEAST {expected_hint_min}' in "
            f"corrective hint but got:\n{hint}"
        )
        assert f"Target is {target}s" in hint


# ---- Compression path unchanged (§25 scope is expansion only) -------


@pytest.mark.django_db
def test_compression_hint_unchanged_by_session_273_still_uses_synth_target():
    """§25 changed the EXPANSION path only. Compression retries
    still use the synth-target math (compression naturally over-
    corrects; we do not want to push it further). This test guards
    against an accidental symmetric change to the compression
    branch."""
    ws = _workspace("s273-compress@t")
    tm = _teammate(ws)
    with patch(
        "character_os.duration_contract.build_render_brief",
        side_effect=[
            _fake_script_result("x" * 1800),  # over 90s max (1620)
            _fake_script_result("x" * 1350),  # in-band
        ],
    ) as fake_brb:
        synthesize_with_duration_gate(tm, "topic", target_duration_seconds=90)
    retry_hint = fake_brb.call_args_list[1].kwargs["corrective_hint"]
    # Compression hint still references the synth-target compression
    # anchor (SESSION 272 Slice F left the compression hint alone).
    assert "REWRITE THE SAME NARRATIVE BELOW" in retry_hint
    # And references the synth-target seconds (81), not the raw 90.
    # This is intentional per §25 — the fix is asymmetric.
    assert "81" in retry_hint


# ---- Ruby specimen recap (deterministic proof the fix helps) --------


@pytest.mark.django_db
def test_gate_still_rejects_ruby_cluster_at_or_below_1080_chars():
    """Ruby's four observed corrective outputs (893, 1032, 1031,
    1008) are all below the 1080 render acceptance floor. Even
    with the §25 fix, the gate correctly rejects each of them.
    §25's contribution is that the LLM was now instructed to
    reach 1080 (not 972), so future draws are more likely to
    clear the floor — but the gate is still the last line of
    provider-cost defense."""
    ws = _workspace("s273-ruby-recap@t")
    tm = _teammate(ws)
    for observed_chars in (893, 1032, 1031, 1008):
        with patch(
            "character_os.duration_contract.build_render_brief",
            side_effect=[
                _fake_script_result("x" * 500),  # short first
                _fake_script_result("x" * observed_chars),
            ],
        ):
            with pytest.raises(DurationContractError) as exc_info:
                synthesize_with_duration_gate(
                    tm, "topic", target_duration_seconds=90,
                )
        assert exc_info.value.reason == DurationContractError.REASON_TOO_SHORT
        assert exc_info.value.actual_chars == observed_chars
        # Operator-facing bounds still use the raw acceptance band.
        assert exc_info.value.effective_min_chars == 1080
        assert exc_info.value.effective_max_chars == 1620
