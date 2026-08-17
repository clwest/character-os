"""SESSION 259 corrective-duration slice tests.

Closes the failure mode observed in v4 dogfoods `3c24689c` and
`92e0ff18`: the pre-259 corrective hint told the LLM to "Tighten by
removing any turn that could be cut without loss to the arc" — under
Writing Contract v4 CAUSAL CHAIN, every turn is a load-bearing beat,
so the model correctly resisted turn deletion and had no other
compression lever. Both retries then under-compressed and missed the
72s / 1080-char ceiling by tens of characters.

The slice replaces the terse one-liner with a dialogue-shaped hint
that gives the retry concrete numeric targets, a "preserve the beats,
shorten the beats" framing, explicit language-compression tactics,
and a preservation contract.

Deterministic prompt-shape tests only — no LLM output assertions.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os.dialogue_synthesis import (
    _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION,
    _DIALOGUE_CPS,
    _dialogue_over_length_hint,
    _dialogue_under_length_hint,
    _parse_and_validate,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures --------------------------------------------------


def _teammate(ws, **kwargs) -> Teammate:
    defaults = {
        "name": "T",
        "business_brief": "b",
        "personality": "",
        "tone_archetype": "expert",
        "voice_energy": "medium",
        "voice_humor": "warm",
        "voice_directness": "balanced",
        "character_point_of_view": "",
        "voice_signature_phrases": "",
        "voice_avoid_phrases": "",
        "who_you_help": "",
        "what_you_sell": "",
        "always_emphasize": "",
        "never_say": "",
        "desired_feeling": "",
    }
    defaults.update(kwargs)
    return Teammate.objects.create(workspace=ws, **defaults)


@pytest.fixture
def ws() -> Workspace:
    u = User.objects.create_user(email="corrective-hint@example.com", password="x")
    workspace = Workspace.objects.filter(owner=u).first()
    assert workspace is not None
    return workspace


# ---- constants ----------------------------------------------------


def test_headroom_fraction_is_ninety_two_percent() -> None:
    """Documented at the top of dialogue_synthesis.py: 0.92 was
    chosen to pull the retry target off the acceptance boundary
    by 8 pt so a passing synthesis produces a finished video
    comfortably inside the operator's target. SESSION 260's cps
    recalibration (15 → 13) does not move the headroom; the
    pull-off is still needed for per-turn cps variance."""
    assert _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION == 0.92


def test_cps_matches_session_260_recalibration() -> None:
    """SESSION 260 recalibrated _DIALOGUE_CPS from 15 to 13
    based on 83 real ``duration_source=="media_probe"`` turns
    across 10 completed real-mode dialogue_scene compositions
    (weighted global cps = 13.05). See dialogue_synthesis.py
    top-of-module docstring for the full corpus provenance."""
    assert _DIALOGUE_CPS == 13


# ---- over-length hint (compression) — concrete numbers ------------


def test_over_length_hint_second_v4_failure_replay() -> None:
    """Replay of the second v4 rejection (composition 92e0ff18):
    1141 chars synthesized for a 60s target. Assertions cover
    every numeric field the hint promises and every semantic
    preservation clause the SESSION 259 audit specified. Numeric
    fields recomputed at SESSION 260's 13-cps calibration."""
    hint = _dialogue_over_length_hint(
        total_chars=1141,
        predicted_seconds=1141 / _DIALOGUE_CPS,  # ~87.77
        target_duration_seconds=60,
        upper_seconds=72.0,
    )

    # Concrete numbers.
    assert "1141 characters" in hint
    assert "~88s" in hint
    assert "Target: 60s" in hint
    assert "936 characters" in hint            # hard ceiling = 72 * 13
    assert "~72s" in hint                       # hard ceiling seconds
    assert "at least 205 characters" in hint    # excess = 1141 - 936
    assert "861 characters" in hint             # headroom = round(936 * 0.92)
    assert "~66s" in hint                       # headroom seconds = round(861/13)

    # "Preserve the beats" wording — NOT "every turn is load-bearing"
    # (the audit warned against that phrasing accidentally reinforcing
    # v4 density).
    assert "Preserve the conversational beats and causal chain" in hint
    assert "Do not solve this primarily by deleting turns" in hint

    # Compression tactics.
    assert "prefer short direct replies when natural" in hint
    assert "fragments are allowed" in hint
    assert "one idea per turn" in hint
    assert "short reactions are valuable" in hint
    assert "remove second or third clauses" in hint
    assert "remove explanations the previous line already made obvious" in hint
    assert "remove duplicated setup" in hint
    assert "remove repeated framing" in hint
    assert "remove decorative language" in hint
    assert (
        "do not narrate why a response is causally connected"
        in hint
    )

    # Preservation contract — every item the audit named.
    assert "character identity" in hint
    assert "factual grounding" in hint
    assert "conversational causality" in hint
    assert "scene's arc" in hint
    assert "ending" in hint  # "ending payoff"


# ---- over-length hint (compression) — scaling ---------------------


@pytest.mark.parametrize(
    "target,expected_ceiling_chars,expected_ceiling_secs,expected_headroom_chars,expected_headroom_secs",
    [
        # SESSION 260 recalibration: ceiling = round(upper * 13);
        # headroom = round(ceiling * 0.92); seconds = round(chars / 13).
        # 30s target: upper=36s → 468 chars → 468*0.92=431 (~33s)
        (30, 468, 36, 431, 33),
        # 60s target: upper=72s → 936 chars → 936*0.92=861 (~66s)
        (60, 936, 72, 861, 66),
        # 90s target: upper=108s → 1404 chars → 1404*0.92=1292 (~99s)
        (90, 1404, 108, 1292, 99),
        # 120s target: upper=144s → 1872 chars → 1872*0.92=1722 (~132s)
        (120, 1872, 144, 1722, 132),
    ],
)
def test_over_length_hint_scales_correctly(
    target, expected_ceiling_chars, expected_ceiling_secs,
    expected_headroom_chars, expected_headroom_secs,
) -> None:
    """For any operator-target duration, the hint's numeric fields
    scale off the ±20 % band with a 0.92 headroom pull-in.
    Verified against four targets used in `_TURN_BANDS`."""
    upper_seconds = target * 1.20
    # Contrive a total_chars 5 % over the ceiling.
    total_chars = int(round(expected_ceiling_chars * 1.05))
    hint = _dialogue_over_length_hint(
        total_chars=total_chars,
        predicted_seconds=total_chars / _DIALOGUE_CPS,
        target_duration_seconds=target,
        upper_seconds=upper_seconds,
    )
    assert f"Target: {target}s" in hint
    assert f"{expected_ceiling_chars} characters" in hint
    assert f"~{expected_ceiling_secs}s" in hint
    assert f"{expected_headroom_chars} characters" in hint
    assert f"~{expected_headroom_secs}s" in hint


def test_over_length_hint_excess_never_reports_zero() -> None:
    """When ``total_chars == upper_chars`` exactly (edge of the
    band), the excess would arithmetically be 0. That's a
    validation quirk not the operator's problem; report the
    smallest positive value so the retry sees an actionable
    'remove at least 1 character' rather than 'remove at least
    0 characters'."""
    hint = _dialogue_over_length_hint(
        total_chars=936,            # exactly at ceiling (13 cps × 72s)
        predicted_seconds=72.0,
        target_duration_seconds=60,
        upper_seconds=72.0,
    )
    assert "at least 1 characters" in hint


# ---- under-length hint (expansion) — concrete numbers ------------


def test_under_length_hint_carries_floor_and_deficit() -> None:
    """Mirror of the compression hint: concrete numbers, tactics
    that add substance rather than filler, preservation contract."""
    # 60s target, floor=48s → 624 chars at 13 cps. Contrive 520 chars.
    hint = _dialogue_under_length_hint(
        total_chars=520,
        predicted_seconds=520 / _DIALOGUE_CPS,  # 40.0
        target_duration_seconds=60,
        lower_seconds=48.0,
    )
    # Concrete numbers.
    assert "520 characters" in hint
    assert "~40s" in hint
    assert "Target: 60s" in hint
    assert "624 characters" in hint    # floor = 48 * 13
    assert "~48s" in hint              # floor seconds
    assert "at least 104 characters" in hint  # deficit = 624 - 520
    # Headroom on the floor side: 624 * (2 - 0.92) = 624 * 1.08 = 673.92 → 674
    assert "674 characters" in hint
    assert "~52s" in hint              # 674 / 13 ≈ 51.85 → 52

    # Expansion tactics — substance, not padding.
    assert "Expand conversational substance, not padding" in hint
    assert "add a beat" in hint
    assert "existing beat more room" in hint
    assert "challenge, callback, or reveal" in hint
    assert "specific example" in hint
    assert "new question the next speaker earns the answer to" in hint

    # Explicit prohibitions.
    assert "Do NOT add filler" in hint
    assert "repeated framing" in hint
    assert "generic" in hint  # "generic methodology explanation"

    # Preservation contract.
    assert "character identity" in hint
    assert "factual grounding" in hint
    assert "conversational causality" in hint
    assert "each character's voice" in hint


def test_under_length_hint_deficit_never_reports_zero() -> None:
    hint = _dialogue_under_length_hint(
        total_chars=624,           # exactly at floor (13 cps × 48s)
        predicted_seconds=48.0,
        target_duration_seconds=60,
        lower_seconds=48.0,
    )
    assert "at least 1 characters" in hint


# ---- validation-thresholds byte-stability ------------------------


def test_acceptance_band_seconds_unchanged_at_60s(ws) -> None:
    """The ±20 % acceptance band in **seconds** is preserved
    (48–72s for a 60s target). SESSION 260 recalibrated
    _DIALOGUE_CPS 15 → 13 which changes the char translation
    (720/1080 → 624/936) but not the seconds tolerance."""
    tm_a = _teammate(ws, name="A")
    tm_b = _teammate(ws, name="B")
    alias_map = {"a": tm_a, "b": tm_b}

    # 936 chars = 72.0 s at 13 cps = ceiling exactly. Splitting
    # across 4 equal turns × 234 chars satisfies HARD_MIN_TURNS (2).
    seven_two_seconds = '{"turns":[' + ",".join(
        f'{{"line_index":{i},"speaker_alias":"{"a" if i%2==0 else "b"}","text":"' + ("x" * 234) + '"}'
        for i in range(4)
    ) + "]}"
    turns, hint = _parse_and_validate(
        seven_two_seconds,
        alias_to_teammate=alias_map,
        target_duration_seconds=60,
        opener=None,
    )
    assert hint is None, f"936 chars at 60s target must accept (hint={hint!r})"
    assert turns is not None
    assert sum(len(t.text) for t in turns) == 936

    # 940 chars = 72.31 s at 13 cps → over ceiling → compression hint.
    over = '{"turns":[' + ",".join(
        f'{{"line_index":{i},"speaker_alias":"{"a" if i%2==0 else "b"}","text":"' + ("x" * 235) + '"}'
        for i in range(4)
    ) + "]}"
    turns, hint = _parse_and_validate(
        over,
        alias_to_teammate=alias_map,
        target_duration_seconds=60,
        opener=None,
    )
    assert turns is None
    assert hint is not None
    assert "Your dialogue is too long" in hint

    # 620 chars = 47.69 s at 13 cps → below floor → expansion hint.
    under_turn = "x" * 155
    under = '{"turns":[' + ",".join(
        f'{{"line_index":{i},"speaker_alias":"{"a" if i%2==0 else "b"}","text":"{under_turn}"}}'
        for i in range(4)
    ) + "]}"
    turns, hint = _parse_and_validate(
        under,
        alias_to_teammate=alias_map,
        target_duration_seconds=60,
        opener=None,
    )
    assert turns is None
    assert hint is not None
    assert "Your dialogue is too short" in hint


# ---- observability contract ---------------------------------------


def test_hint_never_says_every_turn_is_load_bearing() -> None:
    """The audit specifically flagged "every turn is causally
    load-bearing" as wording that could accidentally reinforce
    v4 density. Verify neither hint uses that phrase."""
    over = _dialogue_over_length_hint(
        total_chars=1141, predicted_seconds=76.0,
        target_duration_seconds=60, upper_seconds=72.0,
    )
    under = _dialogue_under_length_hint(
        total_chars=640, predicted_seconds=43.0,
        target_duration_seconds=60, lower_seconds=48.0,
    )
    for hint in (over, under):
        assert "load-bearing" not in hint
        assert "causally load-bearing" not in hint


def test_over_length_hint_does_not_advise_removing_a_turn() -> None:
    """The pre-259 hint said "Tighten by removing any turn that
    could be cut without loss to the arc." That is the exact
    advice the SESSION 259 audit found to be counterproductive
    under Writing Contract v4. The replacement must invert it."""
    hint = _dialogue_over_length_hint(
        total_chars=1141, predicted_seconds=76.0,
        target_duration_seconds=60, upper_seconds=72.0,
    )
    assert "Tighten by removing any turn" not in hint
    assert "removing any turn" not in hint
