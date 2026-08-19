"""SESSION 260 — dialogue cps recalibration 15 → 13.

Empirical planning-estimator recalibration derived from a
read-only audit of 10 completed real-mode ``dialogue_scene``
compositions (83 authoritative ``duration_source == "media_probe"``
speech turns). See the top-of-module docstring in
``character_os/dialogue_synthesis.py`` for the corpus provenance
(weighted global cps = 13.05, per-comp median 13.15, per-turn
median 12.83, Patch 13.24, Rivet 12.83, replay showed zero
false-positive compression at 13 cps vs the corpus).

The slice changes ONLY:

* ``_DIALOGUE_CPS`` (planning estimator, 15 → 13).

Everything else is intentionally preserved:

* ``_DURATION_TOLERANCE = 0.20``
* ``DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 1.00``
* Writing Contract v4 (``WRITING_CONTRACT_VERSION == 4``)
* ``_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION = 0.92``
* Turn-count bands (``_TURN_BANDS`` + ``_HARD_MIN_TURNS``)
* Provider behavior + parallel execution.

The tests below are deterministic (no LLM output, no provider
calls, no fixtures that need Django DB) except where a
workspace-scoped ``_parse_and_validate`` call needs Teammate
rows.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os.dialogue_synthesis import (
    DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER,
    _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION,
    _DIALOGUE_CPS,
    _DURATION_TOLERANCE,
    _HARD_MIN_TURNS,
    _TURN_BANDS,
    _dialogue_over_length_hint,
    _dialogue_under_length_hint,
    _parse_and_validate,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures ----------------------------------------------------


def _teammate(ws: Workspace, name: str) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief="b",
        personality="",
        tone_archetype="expert",
        voice_energy="medium",
        voice_humor="warm",
        voice_directness="balanced",
        character_point_of_view="",
        voice_signature_phrases="",
        voice_avoid_phrases="",
        who_you_help="",
        what_you_sell="",
        always_emphasize="",
        never_say="",
        desired_feeling="",
    )


@pytest.fixture
def ws() -> Workspace:
    u = User.objects.create_user(email="session260@example.com", password="x")
    workspace = Workspace.objects.filter(owner=u).first()
    assert workspace is not None
    return workspace


# ---- 1. _DIALOGUE_CPS == 13 --------------------------------------


def test_dialogue_cps_is_thirteen() -> None:
    """Planning estimator recalibrated 15 → 13. Source of truth
    is the SESSION 260 audit: 10 completed real-mode
    dialogue_scene compositions, 83 authoritative media_probe
    speech turns, weighted global cps = 13.05."""
    assert _DIALOGUE_CPS == 13


# ---- 2, 4. ideal char counts at 60 s and 90 s --------------------


def test_sixty_second_target_ideal_chars_is_seven_eighty() -> None:
    """60 s × 13 cps = 780 chars — the middle of the ±20 %
    acceptance band the LLM aims at."""
    assert 60 * _DIALOGUE_CPS == 780


def test_ninety_second_target_ideal_chars_is_eleven_seventy() -> None:
    """90 s × 13 cps = 1170 chars — the middle of the ±20 %
    acceptance band the LLM aims at."""
    assert 90 * _DIALOGUE_CPS == 1170


# ---- 3. 60 s acceptance band in chars -----------------------------


def test_sixty_second_acceptance_band_char_edges() -> None:
    """Band in seconds is preserved (48–72 s at ±20 %). Under
    the SESSION 260 recalibration the char translation becomes
    624–936 chars."""
    lower_seconds = 60 * (1.0 - _DURATION_TOLERANCE)
    upper_seconds = 60 * (1.0 + _DURATION_TOLERANCE)
    assert lower_seconds == 48.0
    assert upper_seconds == 72.0
    assert round(lower_seconds * _DIALOGUE_CPS) == 624
    assert round(upper_seconds * _DIALOGUE_CPS) == 936


# ---- 5. 90 s acceptance band in chars -----------------------------


def test_ninety_second_acceptance_band_char_edges() -> None:
    """90 s ±20 % = 72–108 s. At 13 cps the char band becomes
    936–1404. The rejected-90s dogfood (~1069 chars) sits
    comfortably inside this band — see the dedicated replay
    test below."""
    lower_seconds = 90 * (1.0 - _DURATION_TOLERANCE)
    upper_seconds = 90 * (1.0 + _DURATION_TOLERANCE)
    assert lower_seconds == 72.0
    assert upper_seconds == 108.0
    assert round(lower_seconds * _DIALOGUE_CPS) == 936
    assert round(upper_seconds * _DIALOGUE_CPS) == 1404


# ---- 6. rejected ~1069-char 90 s scene now validates -------------


def test_rejected_ninety_second_scene_now_inside_band(ws) -> None:
    """Empirical replay: the 90 s scene that was rejected today
    at 15 cps (1069 chars → predicted 71.3 s → below the
    72 s floor → EXPAND) accepts at 13 cps (predicted 82.2 s →
    inside 72–108 s band). Construct a 1069-char parseable
    dialogue and prove ``_parse_and_validate`` returns no hint."""
    tm_a = _teammate(ws, "Patch")
    tm_b = _teammate(ws, "Rivet")

    # 1069 chars across 9 turns approximates the actual first-pass
    # shape observed. Distribute reasonably: eight 119-char turns +
    # one 117-char turn = 8*119 + 117 = 952 + 117 = 1069.
    per_turn = 119
    remainder_turn = 117
    turns_json = '{"turns":['
    parts = []
    for i in range(8):
        alias = "a" if i % 2 == 0 else "b"
        parts.append(
            f'{{"line_index":{i},"speaker_alias":"{alias}","text":"'
            + ("x" * per_turn) + '"}'
        )
    parts.append(
        '{"line_index":8,"speaker_alias":"a","text":"'
        + ("x" * remainder_turn) + '"}'
    )
    turns_json += ",".join(parts) + "]}"

    turns, hint = _parse_and_validate(
        turns_json,
        alias_to_teammate={"a": tm_a, "b": tm_b},
        target_duration_seconds=90,
        opener=None,
    )
    assert hint is None, (
        f"1069 chars at 90 s target must accept at 13 cps "
        f"(hint={hint!r})"
    )
    assert turns is not None
    total = sum(len(t.text) for t in turns)
    assert total == 1069
    # And predicted seconds = 1069 / 13 ≈ 82.2 → inside 72-108.
    assert 72.0 <= total / _DIALOGUE_CPS <= 108.0


# ---- 7. SESSION 259 final 809-char / 60 s remains accepted -------


def test_session_259_final_scene_still_accepted(ws) -> None:
    """The final SESSION 259 controlled dogfood (composition
    d79ab53c, 809 chars, target 60 s) rendered at 68.3 s and
    was accepted at synthesis under 15 cps. Under the SESSION
    260 recalibration it must still accept — the whole
    calibration story fails if a known-good final render newly
    rejects. Predicted at 13 cps = 809 / 13 = 62.2 s → inside
    48–72 s band."""
    tm_a = _teammate(ws, "Patch")
    tm_b = _teammate(ws, "Rivet")

    # 9 turns; distribute 809 chars. Alternate A/B. 8*90 + 1*89 = 809.
    parts = []
    for i in range(8):
        alias = "a" if i % 2 == 0 else "b"
        parts.append(
            f'{{"line_index":{i},"speaker_alias":"{alias}","text":"'
            + ("x" * 90) + '"}'
        )
    parts.append(
        '{"line_index":8,"speaker_alias":"a","text":"'
        + ("x" * 89) + '"}'
    )
    turns_json = '{"turns":[' + ",".join(parts) + "]}"

    turns, hint = _parse_and_validate(
        turns_json,
        alias_to_teammate={"a": tm_a, "b": tm_b},
        target_duration_seconds=60,
        opener=None,
    )
    assert hint is None, (
        f"SESSION 259 final (809 chars, 60 s target) must remain "
        f"accepted at 13 cps (hint={hint!r})"
    )
    assert turns is not None
    total = sum(len(t.text) for t in turns)
    assert total == 809
    assert 48.0 <= total / _DIALOGUE_CPS <= 72.0


# ---- 8. previously overlong 60 s scenes now trigger compression --


@pytest.mark.parametrize(
    "chars",
    [
        # Real corpus rows that rendered outside the 72 s ceiling
        # (76.3 s / 75.1 s / 79.5 s) and were only accepted under
        # 15 cps because the estimator was optimistic. At 13 cps
        # the same char counts predict outside the ceiling and
        # correctly trigger the compression retry.
        1034,  # comp 9e4601c7 (P2 concurrency Patch/Rivet run)
        1047,  # comp 8345779c
        1066,  # comp b75a9dba
    ],
)
def test_previously_overlong_60s_now_triggers_compression(ws, chars) -> None:
    """Not a regression — a correction. These three shipped
    scenes were accepted at synthesis under 15 cps because the
    estimator predicted them at 68.9 / 69.8 / 71.1 s (inside
    the 48-72 s band) but they actually rendered at 76.3 / 75.1
    / 79.5 s (outside). Under 13 cps their predictions become
    79.5 / 80.5 / 82.0 s (over ceiling) and the compression
    retry correctly fires."""
    tm_a = _teammate(ws, "Patch")
    tm_b = _teammate(ws, "Rivet")

    # 8 turns of equal chars sums close to target. Distribute
    # remainder across turns so total == chars exactly.
    n_turns = 8
    per = chars // n_turns
    remainder = chars - per * n_turns
    parts = []
    for i in range(n_turns):
        alias = "a" if i % 2 == 0 else "b"
        length = per + (1 if i < remainder else 0)
        parts.append(
            f'{{"line_index":{i},"speaker_alias":"{alias}","text":"'
            + ("x" * length) + '"}'
        )
    turns_json = '{"turns":[' + ",".join(parts) + "]}"

    turns, hint = _parse_and_validate(
        turns_json,
        alias_to_teammate={"a": tm_a, "b": tm_b},
        target_duration_seconds=60,
        opener=None,
    )
    assert turns is None
    assert hint is not None
    assert "Your dialogue is too long" in hint
    # Ceiling in the hint must be the recalibrated 936 chars.
    assert "936 characters" in hint


# ---- 9. known 917-char 60 s example remains accepted -------------


def test_known_917_char_60s_scene_remains_accepted(ws) -> None:
    """Composition 5e74323f: 917 chars at 60 s target rendered
    at 70.2 s (inside band). Under 15 cps predicted 61.1 s;
    under 13 cps predicts 70.5 s — still inside 48–72 s band.
    Zero false-positive compression on this row is one of the
    two reasons the audit picked 13 over 12."""
    tm_a = _teammate(ws, "Patch")
    tm_b = _teammate(ws, "Rivet")

    # 8 turns totaling 917 chars. 7 × 115 + 1 × 112 = 805 + 112 = 917.
    parts = []
    for i in range(7):
        alias = "a" if i % 2 == 0 else "b"
        parts.append(
            f'{{"line_index":{i},"speaker_alias":"{alias}","text":"'
            + ("x" * 115) + '"}'
        )
    parts.append(
        '{"line_index":7,"speaker_alias":"b","text":"'
        + ("x" * 112) + '"}'
    )
    turns_json = '{"turns":[' + ",".join(parts) + "]}"

    turns, hint = _parse_and_validate(
        turns_json,
        alias_to_teammate={"a": tm_a, "b": tm_b},
        target_duration_seconds=60,
        opener=None,
    )
    assert hint is None, (
        f"917 chars at 60 s target must still accept at 13 cps "
        f"(hint={hint!r})"
    )
    assert turns is not None
    total = sum(len(t.text) for t in turns)
    assert total == 917
    assert 48.0 <= total / _DIALOGUE_CPS <= 72.0


# ---- 10. corrective-headroom arithmetic derives from new ceiling -


def test_corrective_headroom_derives_from_recalibrated_ceiling() -> None:
    """Compression headroom = round(ceiling_chars * 0.92) where
    ceiling_chars = round(upper_seconds * _DIALOGUE_CPS). Verify
    for 30 / 60 / 90 / 120 s targets that the hint uses the
    SESSION 260 char ceilings."""
    for target, expected_ceiling in [
        (30, 468),    # 36 s × 13 cps
        (60, 936),    # 72 s × 13 cps
        (90, 1404),   # 108 s × 13 cps
        (120, 1872),  # 144 s × 13 cps
    ]:
        expected_headroom = round(expected_ceiling * _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION)
        hint = _dialogue_over_length_hint(
            total_chars=expected_ceiling + 100,
            predicted_seconds=(expected_ceiling + 100) / _DIALOGUE_CPS,
            target_duration_seconds=target,
            upper_seconds=target * (1.0 + _DURATION_TOLERANCE),
        )
        assert f"{expected_ceiling} characters" in hint, (
            f"target {target} s expected ceiling {expected_ceiling} in hint"
        )
        assert f"{expected_headroom} characters" in hint, (
            f"target {target} s expected headroom {expected_headroom} in hint"
        )


def test_corrective_headroom_expansion_derives_from_recalibrated_floor() -> None:
    """Expansion headroom (mirror of compression): floor_chars =
    round(lower_seconds * _DIALOGUE_CPS); headroom = round(floor
    × (2 - 0.92)) = round(floor × 1.08)."""
    for target, expected_floor in [
        (30, 312),    # 24 s × 13 cps
        (60, 624),    # 48 s × 13 cps
        (90, 936),    # 72 s × 13 cps
        (120, 1248),  # 96 s × 13 cps
    ]:
        expected_headroom = round(expected_floor * (2.0 - _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION))
        # Contrive a total 100 chars below the floor.
        contrived_total = expected_floor - 100
        hint = _dialogue_under_length_hint(
            total_chars=contrived_total,
            predicted_seconds=contrived_total / _DIALOGUE_CPS,
            target_duration_seconds=target,
            lower_seconds=target * (1.0 - _DURATION_TOLERANCE),
        )
        assert f"{expected_floor} characters" in hint, (
            f"target {target} s expected floor {expected_floor} in hint"
        )
        assert f"{expected_headroom} characters" in hint, (
            f"target {target} s expected headroom {expected_headroom} in hint"
        )


# ---- 11. no other duration constants changed --------------------


def test_duration_tolerance_unchanged() -> None:
    assert _DURATION_TOLERANCE == 0.20


def test_dialogue_synthesis_target_multiplier_unchanged() -> None:
    assert DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 1.00


def test_corrective_headroom_fraction_unchanged() -> None:
    assert _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION == 0.92


def test_writing_contract_version_unchanged() -> None:
    """SESSION 260 is calibration-only — bumps to the WRITING
    CONTRACT version stamp come from separate slices (v4 =
    SESSION 259 dialogue causal chain; v5 = SESSION 269 §15
    solo_scene shape). This suite must track whatever the
    current stamp is; the assertion below is the deliberate
    version-stamp conversation for §15."""
    assert WRITING_CONTRACT_VERSION == 5


def test_turn_bands_unchanged() -> None:
    """SESSION 260 recalibration must NOT retune turn-count
    guidance. Bands stay at their SESSION 257 values."""
    assert _TURN_BANDS == {
        30: (4, 6, 12),
        60: (6, 9, 18),
        90: (8, 12, 24),
        120: (10, 15, 30),
    }


def test_hard_min_turns_unchanged() -> None:
    """Below two participants it is not a conversation."""
    assert _HARD_MIN_TURNS == 2
