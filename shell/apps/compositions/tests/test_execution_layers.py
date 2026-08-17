"""SESSION 258 P2.A — pure DAG layer builder tests.

No Django ORM needed — uses lightweight duck-typed step objects.
The helper's contract is pure: (steps) → list-of-list-of-position.

Coverage matches audit §4 recipe classes:

* Class A (dialogue_scene, long_form_ad): N independent roots +
  concat + optional outro. Expected shape: `[[0..N-1], [N], [N+1]]`
  or `[[0..N-1], [N]]` without outro.
* Class B (storyboard_ad, talking_head_with_backdrop): mixed
  independent roots + sequential chains. Multiple non-trivial
  layers.
* Class C (talking_head, cinematic_visual, single-primitive
  recipes): linear chain → one step per layer, no parallelism.

Validation errors: cycles, self-references, forward references,
missing upstream positions, malformed input entries.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from apps.compositions.execution_layers import (
    DagValidationError,
    compute_execution_layers,
)


@dataclass
class _FakeStep:
    """Duck-typed CompositionStep for pure-DAG tests. Only fields the
    builder reads: ``position`` and ``inputs``."""
    position: int
    inputs: list[dict] = field(default_factory=list)


def _dep(pos: int, slot: str = "clip") -> dict:
    return {"slot": slot, "from_step_position": pos}


def _asset(slot: str = "backdrop") -> dict:
    return {"slot": slot, "asset_id": "00000000-0000-0000-0000-000000000000"}


# ---- Empty + trivial -------------------------------------------


def test_empty_steps_returns_empty_layers() -> None:
    assert compute_execution_layers([]) == []


def test_single_step_no_inputs_is_one_layer() -> None:
    steps = [_FakeStep(position=0, inputs=[])]
    assert compute_execution_layers(steps) == [[0]]


def test_single_step_asset_input_is_still_one_layer() -> None:
    """asset_id inputs introduce NO step dependency — the step is
    still a root even with a workspace asset reference."""
    steps = [_FakeStep(position=0, inputs=[_asset("bg")])]
    assert compute_execution_layers(steps) == [[0]]


# ---- Class A recipes: dialogue_scene shape ---------------------


def test_dialogue_scene_8_turns_produces_three_layers() -> None:
    """AI-D5 shape. 8 independent speech turns fan into concat +
    optional outro."""
    speech = [_FakeStep(position=i, inputs=[]) for i in range(8)]
    concat = _FakeStep(
        position=8,
        inputs=[_dep(i) for i in range(8)],
    )
    outro = _FakeStep(
        position=9,
        inputs=[{"slot": "base", "from_step_position": 8}],
    )
    layers = compute_execution_layers(speech + [concat, outro])
    assert layers == [
        [0, 1, 2, 3, 4, 5, 6, 7],
        [8],
        [9],
    ]


def test_dialogue_scene_degenerate_single_turn_no_concat() -> None:
    """N=1 dialogue: no concat step; just one speech (+ optional
    outro). Layer 0 = speech, layer 1 = outro if present."""
    steps = [
        _FakeStep(position=0, inputs=[]),
        _FakeStep(position=1, inputs=[_dep(0, "base")]),
    ]
    assert compute_execution_layers(steps) == [[0], [1]]


def test_dialogue_scene_two_turns_no_outro() -> None:
    """N=2 turns → concat but no outro. Two layers."""
    steps = [
        _FakeStep(position=0, inputs=[]),
        _FakeStep(position=1, inputs=[]),
        _FakeStep(position=2, inputs=[_dep(0), _dep(1)]),
    ]
    assert compute_execution_layers(steps) == [[0, 1], [2]]


def test_long_form_ad_shape_matches_dialogue_shape() -> None:
    """long_form_ad is Class A like dialogue: N independent
    generate_avatar_speech chunks + concat + optional outro."""
    chunks = [_FakeStep(position=i, inputs=[]) for i in range(5)]
    concat = _FakeStep(
        position=5,
        inputs=[_dep(i) for i in range(5)],
    )
    layers = compute_execution_layers(chunks + [concat])
    assert layers == [[0, 1, 2, 3, 4], [5]]


# ---- Class B recipes: storyboard_ad shape ----------------------


def test_storyboard_ad_shape_produces_expected_layers() -> None:
    """3 images (independent) → 3 visuals (each depends on matching
    image) → concat → outro.

    Expected: [[0,1,2], [3,4,5], [6], [7]]  — 4 layers because
    visuals fan out in parallel too once their respective image is
    ready.
    """
    images = [_FakeStep(position=i, inputs=[]) for i in range(3)]
    visuals = [
        _FakeStep(
            position=3 + i,
            inputs=[{"slot": "reference_image", "from_step_position": i}],
        )
        for i in range(3)
    ]
    concat = _FakeStep(
        position=6,
        inputs=[_dep(3), _dep(4), _dep(5)],
    )
    outro = _FakeStep(
        position=7,
        inputs=[{"slot": "base", "from_step_position": 6}],
    )
    layers = compute_execution_layers(images + visuals + [concat, outro])
    assert layers == [[0, 1, 2], [3, 4, 5], [6], [7]]


def test_storyboard_voiced_shape_with_parallel_narration() -> None:
    """3 images → 3 visuals → concat + independent narration →
    audio_extract → mix_audio → outro. Narration runs in parallel
    to the image/visual chain until mix_audio fans them in."""
    images = [_FakeStep(position=i, inputs=[]) for i in range(3)]
    visuals = [
        _FakeStep(
            position=3 + i,
            inputs=[{"slot": "reference_image", "from_step_position": i}],
        )
        for i in range(3)
    ]
    silent_concat = _FakeStep(
        position=6,
        inputs=[_dep(3), _dep(4), _dep(5)],
    )
    narration = _FakeStep(position=7, inputs=[])  # independent root
    audio_extract = _FakeStep(
        position=8,
        inputs=[{"slot": "source", "from_step_position": 7}],
    )
    mix_audio = _FakeStep(
        position=9,
        inputs=[
            {"slot": "base", "from_step_position": 6},
            {"slot": "voice", "from_step_position": 8},
        ],
    )
    steps = images + visuals + [silent_concat, narration, audio_extract, mix_audio]
    layers = compute_execution_layers(steps)
    # Layer 0: 3 images + narration (all roots)
    # Layer 1: 3 visuals + audio_extract
    # Layer 2: silent concat  (mix waits for both concat + audio)
    # Layer 3: mix_audio
    assert layers[0] == [0, 1, 2, 7]
    assert layers[1] == [3, 4, 5, 8]
    assert layers[2] == [6]
    assert layers[3] == [9]


# ---- Class C recipes: linear chains ---------------------------


def test_cinematic_visual_extended_is_pure_chain() -> None:
    """N sequential extend calls — each depends on prior. One step
    per layer, no parallelism possible."""
    base = _FakeStep(position=0, inputs=[])
    extends = [
        _FakeStep(
            position=i,
            inputs=[{"slot": "source", "from_step_position": i - 1}],
        )
        for i in range(1, 4)
    ]
    layers = compute_execution_layers([base] + extends)
    assert layers == [[0], [1], [2], [3]]


def test_single_primitive_recipe_is_one_layer() -> None:
    """talking_head-shaped: 1 speech step, no inputs."""
    assert compute_execution_layers([_FakeStep(position=0, inputs=[])]) == [[0]]


# ---- Deterministic ordering within layer ----------------------


def test_within_layer_order_is_ascending_position() -> None:
    """Layer order across layers is topological; within a layer,
    ascending position. This is deterministic — the same step
    graph must always produce the same layer sequence."""
    # 5 independent roots + fan-in.
    roots = [_FakeStep(position=p, inputs=[]) for p in [4, 2, 0, 3, 1]]
    fan_in = _FakeStep(position=5, inputs=[_dep(p) for p in range(5)])
    layers = compute_execution_layers(roots + [fan_in])
    # Within layer 0, positions are sorted ascending regardless of
    # the order in the input list.
    assert layers == [[0, 1, 2, 3, 4], [5]]


def test_deterministic_across_repeated_calls() -> None:
    """Same input → same output (pure function)."""
    steps = [
        _FakeStep(position=0, inputs=[]),
        _FakeStep(position=1, inputs=[]),
        _FakeStep(position=2, inputs=[_dep(0), _dep(1)]),
    ]
    assert (
        compute_execution_layers(steps)
        == compute_execution_layers(steps)
        == compute_execution_layers(steps)
    )


# ---- Validation errors ---------------------------------------


def test_self_reference_raises() -> None:
    steps = [_FakeStep(position=0, inputs=[_dep(0)])]
    with pytest.raises(DagValidationError, match="self-reference"):
        compute_execution_layers(steps)


def test_forward_reference_raises() -> None:
    """Current linear-only model disallows referring to a later
    position (contract rule 5 in VIDEO_COMPOSITION_V1)."""
    steps = [
        _FakeStep(position=0, inputs=[_dep(1)]),
        _FakeStep(position=1, inputs=[]),
    ]
    with pytest.raises(DagValidationError, match="forward reference"):
        compute_execution_layers(steps)


def test_missing_upstream_position_raises() -> None:
    """Reference a backward position that doesn't exist. (A forward
    reference to a missing position hits the forward-ref check
    first, which is also correct.)"""
    steps = [
        _FakeStep(position=0, inputs=[]),
        _FakeStep(position=5, inputs=[_dep(3)]),  # 3 doesn't exist, 5 > 3 so backward
    ]
    with pytest.raises(DagValidationError, match="references no step"):
        compute_execution_layers(steps)


def test_malformed_input_missing_slot_raises() -> None:
    steps = [
        _FakeStep(position=0, inputs=[{"from_step_position": 0}]),
    ]
    with pytest.raises(DagValidationError, match="missing or empty slot"):
        compute_execution_layers(steps)


def test_malformed_input_both_asset_id_and_from_step_raises() -> None:
    steps = [
        _FakeStep(position=0, inputs=[
            {"slot": "x", "asset_id": "a", "from_step_position": 0},
        ]),
    ]
    with pytest.raises(DagValidationError, match="cannot have both"):
        compute_execution_layers(steps)


def test_malformed_input_neither_asset_id_nor_from_step_raises() -> None:
    steps = [
        _FakeStep(position=0, inputs=[{"slot": "x"}]),
    ]
    with pytest.raises(DagValidationError, match="must have exactly one of"):
        compute_execution_layers(steps)


def test_non_integer_from_step_position_raises() -> None:
    steps = [
        _FakeStep(position=0, inputs=[]),
        _FakeStep(position=1, inputs=[
            {"slot": "x", "from_step_position": "zero"},
        ]),
    ]
    with pytest.raises(DagValidationError, match="not an integer"):
        compute_execution_layers(steps)


def test_duplicate_position_raises() -> None:
    steps = [
        _FakeStep(position=0, inputs=[]),
        _FakeStep(position=0, inputs=[]),
    ]
    with pytest.raises(DagValidationError, match="duplicate step position"):
        compute_execution_layers(steps)


def test_non_integer_position_raises() -> None:
    steps = [_FakeStep(position="0", inputs=[])]  # type: ignore[arg-type]
    with pytest.raises(DagValidationError, match="non-integer position"):
        compute_execution_layers(steps)


def test_non_dict_input_entry_raises() -> None:
    steps = [_FakeStep(position=0, inputs=["not-a-dict"])]  # type: ignore[list-item]
    with pytest.raises(DagValidationError, match="not a dict"):
        compute_execution_layers(steps)
