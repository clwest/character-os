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
    chosen because real Patch/Rivet renders often speak slower
    than the 15-cps planning estimator; the retry target sits
    off the boundary by 8 pt so a passing synthesis produces a
    finished video comfortably inside the operator's target."""
    assert _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION == 0.92


def test_cps_unchanged_by_slice() -> None:
    """Guard: SESSION 259 corrective slice must NOT retune the
    dialogue characters-per-second estimator. Any change to
    _DIALOGUE_CPS is a separate calibration event."""
    assert _DIALOGUE_CPS == 15


# ---- over-length hint (compression) — concrete numbers ------------


def test_over_length_hint_second_v4_failure_replay() -> None:
    """Replay of the second v4 rejection (composition 92e0ff18):
    1141 chars synthesized for a 60s target. Assertions cover
    every numeric field the hint promises and every semantic
    preservation clause the SESSION 259 audit specified."""
    hint = _dialogue_over_length_hint(
        total_chars=1141,
        predicted_seconds=1141 / _DIALOGUE_CPS,  # ~76.07
        target_duration_seconds=60,
        upper_seconds=72.0,
    )

    # Concrete numbers.
    assert "1141 characters" in hint
    assert "~76s" in hint
    assert "Target: 60s" in hint
    assert "1080 characters" in hint          # hard ceiling
    assert "~72s" in hint                      # hard ceiling seconds
    assert "at least 61 characters" in hint    # excess
    assert "994 characters" in hint            # headroom = round(1080 * 0.92)
    assert "~66s" in hint                      # headroom seconds

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
        # 30s target: upper=36s → 540 chars → 540*0.92=497 (~33s)
        (30, 540, 36, 497, 33),
        # 60s target: upper=72s → 1080 chars → 1080*0.92=994 (~66s)
        (60, 1080, 72, 994, 66),
        # 90s target: upper=108s → 1620 chars → 1620*0.92=1490 (~99s)
        (90, 1620, 108, 1490, 99),
        # 120s target: upper=144s → 2160 chars → 2160*0.92=1987 (~132s)
        (120, 2160, 144, 1987, 132),
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
        total_chars=1080,           # exactly at ceiling
        predicted_seconds=72.0,
        target_duration_seconds=60,
        upper_seconds=72.0,
    )
    assert "at least 1 characters" in hint


# ---- under-length hint (expansion) — concrete numbers ------------


def test_under_length_hint_carries_floor_and_deficit() -> None:
    """Mirror of the compression hint: concrete numbers, tactics
    that add substance rather than filler, preservation contract."""
    # 60s target, floor=48s → 720 chars. Contrive 640 chars (~43s).
    hint = _dialogue_under_length_hint(
        total_chars=640,
        predicted_seconds=640 / _DIALOGUE_CPS,  # ~42.67
        target_duration_seconds=60,
        lower_seconds=48.0,
    )
    # Concrete numbers.
    assert "640 characters" in hint
    assert "~43s" in hint
    assert "Target: 60s" in hint
    assert "720 characters" in hint    # floor
    assert "~48s" in hint              # floor seconds
    assert "at least 80 characters" in hint  # deficit = 720 - 640
    # Headroom on the floor side: 720 * (2 - 0.92) = 720 * 1.08 = 777.6 → 778
    assert "778 characters" in hint
    assert "~52s" in hint              # 778 / 15 ≈ 51.87 → 52

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
        total_chars=720,
        predicted_seconds=48.0,
        target_duration_seconds=60,
        lower_seconds=48.0,
    )
    assert "at least 1 characters" in hint


# ---- validation-thresholds byte-stability ------------------------


def test_acceptance_band_unchanged_at_60s(ws) -> None:
    """The SESSION 259 corrective slice must NOT move the ±20 %
    acceptance band. A 60s target still accepts 48–72s of predicted
    speech; only the wording of the corrective hint changed."""
    tm_a = _teammate(ws, name="A")
    tm_b = _teammate(ws, name="B")
    alias_map = {"a": tm_a, "b": tm_b}

    # 1080 chars = 72.0 s = ceiling exactly. Splitting across 4
    # equal turns × 270 chars satisfies HARD_MIN_TURNS (2).
    seven_two_seconds = '{"turns":[' + ",".join(
        f'{{"line_index":{i},"speaker_alias":"{"a" if i%2==0 else "b"}","text":"' + ("x" * 270) + '"}'
        for i in range(4)
    ) + "]}"
    turns, hint = _parse_and_validate(
        seven_two_seconds,
        alias_to_teammate=alias_map,
        target_duration_seconds=60,
        opener=None,
    )
    assert hint is None, f"1080 chars at 60s target must accept (hint={hint!r})"
    assert turns is not None
    assert sum(len(t.text) for t in turns) == 1080

    # 1081 chars = 72.067 s → over ceiling → reject with compression hint.
    over = '{"turns":[' + ",".join(
        f'{{"line_index":{i},"speaker_alias":"{"a" if i%2==0 else "b"}","text":"' + ("x" * 271) + '"}'
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

    # 719 chars = 47.93 s → below floor → reject with expansion hint.
    # 4 turns × 179 chars = 716 chars = 47.7s. Use 179 * 4 = 716
    # which is below 720. Pick a size that's definitely under.
    under_turn = "x" * 179
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
