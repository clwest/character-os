"""SESSION 264 (post-Slice-2) — GPT-5.6 Terra model migration lock.

Pins the migration surface so a future model change (or an
accidental revert) fails a fast targeted test instead of
surfacing at operator dogfood time.

Load-bearing invariants for the migration:

1.  ``DIALOGUE_MODEL`` / ``SCRIPT_MODEL`` are the exact string
    ``"gpt-5.6-terra"``. (If the operator asks to change the
    tier, THIS is the file to touch — one place.)
2.  The Responses API path is unchanged. Same
    ``client.responses.create`` shape as SESSION 263 / 264
    Slice 1 & Slice 2 tests use.
3.  ``reasoning_effort`` stays at ``"low"``. GPT-5.6 supports
    the ladder ``none / low / medium / high / xhigh / max``;
    the operator brief explicitly says "do not arbitrarily
    increase reasoning because GPT-5.6 supports it."
4.  The dialogue structured-output kwarg
    ``text={"format": {"type": "json_object"}}`` is unchanged.
5.  The dialogue first-pass AND corrective-pass both go through
    the same ``DIALOGUE_MODEL`` (one constant covers both).
6.  Calibration / pacing constants are unchanged:
    - ``WRITING_CONTRACT_VERSION = 4``
    - ``_DIALOGUE_CPS = 13``
    - ``_DIALOGUE_CORRECTIVE_HEADROOM_FRACTION = 0.92``
    - ``_DURATION_TOLERANCE = 0.20``
    - ``DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER = 1.00``

Zero provider calls; the OpenAI client is mocked exactly as
SESSION 263/264 canon-lane and memory-lane tests do.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock
from unittest.mock import patch as mock_patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from character_os.dialogue_synthesis import (
    DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER,
    DIALOGUE_MODEL,
    _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION,
    _DIALOGUE_CPS,
    _DURATION_TOLERANCE,
    _MAX_OUTPUT_TOKENS,
    _REASONING_EFFORT,
    synthesize_dialogue,
)
from character_os.script_synthesis import (
    REASONING_EFFORT as SCRIPT_REASONING_EFFORT,
    SCRIPT_MODEL,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION

User = get_user_model()
pytestmark = pytest.mark.django_db


# ==================================================================
# 1 + 6 — constants
# ==================================================================


def test_dialogue_model_is_gpt_5_6_terra():
    """The operator-facing migration lock. If this fails, the
    model constant has drifted and the next dogfood will hit a
    different tier than expected."""
    assert DIALOGUE_MODEL == "gpt-5.6-terra"


def test_script_model_is_gpt_5_6_terra():
    assert SCRIPT_MODEL == "gpt-5.6-terra"


def test_reasoning_effort_preserved_at_low():
    """Preserved from the pre-migration configuration per operator
    brief: "if an explicit reasoning level is currently configured,
    preserve the closest equivalent supported value. Do not
    arbitrarily increase reasoning because GPT-5.6 supports it."

    ``"low"`` is legal on GPT-5.6 (ladder: none, low, medium,
    high, xhigh, max)."""
    assert _REASONING_EFFORT == "low"
    assert SCRIPT_REASONING_EFFORT == "low"


def test_dialogue_calibration_constants_unchanged_by_migration():
    """Migration must NOT touch calibration. If any of these
    drift under a "model swap" commit, the change scope was
    wrong.

    SESSION 269 §15 bumped ``WRITING_CONTRACT_VERSION`` 4 → 5 to
    add the ``solo_scene`` shape — a contract-content change, not
    a model-migration change. Calibration constants below remain
    unchanged."""
    assert WRITING_CONTRACT_VERSION == 5
    assert _DIALOGUE_CPS == 13
    assert _DIALOGUE_CORRECTIVE_HEADROOM_FRACTION == 0.92
    assert _DURATION_TOLERANCE == 0.20
    assert DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 1.00
    # _MAX_OUTPUT_TOKENS is a Responses-API budget for reasoning +
    # output combined. Preserved to give GPT-5.6's reasoning
    # headroom the same runway GPT-5 had.
    assert _MAX_OUTPUT_TOKENS == 4000


# ==================================================================
# 2 + 3 + 4 + 5 — the actual call shape
# ==================================================================


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _cast(ws: Workspace, universe: Universe | None = None):
    patch = Teammate.objects.create(
        workspace=ws, name="Patch",
        personality="Curious tinkerer.",
        business_brief="Runs the workshop.",
        universe=universe,
    )
    rivet = Teammate.objects.create(
        workspace=ws, name="Rivet",
        personality="Methodical robot.",
        business_brief="Robot assistant Patch built.",
        universe=universe,
    )
    return patch, rivet


def _valid_turns_json(*, n_turns: int, per_turn_chars: int = 113) -> str:
    turns = []
    for i in range(n_turns):
        alias = "patch" if i % 2 == 0 else "rivet"
        pad = "x" * max(1, per_turn_chars - 20)
        turns.append({
            "line_index": i,
            "speaker_alias": alias,
            "text": f"turn {i} content {pad}",
        })
    return json.dumps({"turns": turns})


def _openai_returning(*responses: str):
    """Same mock shape as SESSION 263/264 tests. GPT-5.6 responses
    should still surface via ``response.output_text`` + ``.usage``
    (Responses API contract; not model-specific)."""
    call_count = {"n": 0}

    def _side_effect(**_kwargs):
        idx = call_count["n"]
        call_count["n"] += 1
        payload = responses[min(idx, len(responses) - 1)]
        mock_resp = MagicMock()
        mock_resp.output_text = payload
        usage = MagicMock()
        usage.input_tokens = 100
        usage.output_tokens = 500
        mock_resp.usage = usage
        return mock_resp

    client = MagicMock()
    client.responses.create.side_effect = _side_effect
    return client, call_count


def test_dialogue_first_pass_call_sends_gpt_5_6_terra():
    ws = _workspace("mig-first@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json(n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic worth talking about",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # Exactly one call (first-pass accepted).
    assert fake_client.responses.create.call_count == 1
    kwargs = fake_client.responses.create.call_args.kwargs
    assert kwargs["model"] == "gpt-5.6-terra"
    assert kwargs["model"] == DIALOGUE_MODEL
    # Reasoning, max output tokens, structured output preserved.
    assert kwargs["reasoning"] == {"effort": "low"}
    assert kwargs["max_output_tokens"] == 4000
    assert kwargs["text"] == {"format": {"type": "json_object"}}
    # DialogueResult stamps the same model back onto the row.
    assert result.model == "gpt-5.6-terra"
    # Attempt count = 1 (first-pass accepted; no corrective).
    assert result.attempt_count == 1


def test_dialogue_corrective_pass_also_uses_gpt_5_6_terra():
    """The corrective pass shares ``DIALOGUE_MODEL`` — one
    constant covers both. Prove the second call also goes to
    the new tier."""
    ws = _workspace("mig-corrective@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    # First pass: too long (forces the corrective). Second pass:
    # in-band.
    too_long = _valid_turns_json(n_turns=20, per_turn_chars=200)
    in_band = _valid_turns_json(n_turns=8, per_turn_chars=113)
    fake_client, count = _openai_returning(too_long, in_band)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # Two calls (first-pass + one corrective).
    assert count["n"] == 2
    # BOTH calls used the new tier.
    for call in fake_client.responses.create.call_args_list:
        assert call.kwargs["model"] == "gpt-5.6-terra"
        assert call.kwargs["reasoning"] == {"effort": "low"}
        assert call.kwargs["text"] == {"format": {"type": "json_object"}}
    # Result stamps the constant.
    assert result.model == "gpt-5.6-terra"
    assert result.attempt_count == 2


def test_dialogue_uses_responses_api_not_chat_completions():
    """Guard against a future refactor that silently swaps to
    chat.completions.create (which has different kwargs and a
    different response shape)."""
    ws = _workspace("mig-api@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json(n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    # responses.create was called; chat.completions.create was NOT.
    assert fake_client.responses.create.called
    # chat.completions.create is never accessed via MagicMock's
    # attribute chain during a legitimate synthesis run.
    assert not fake_client.chat.completions.create.called


def test_dialogue_does_not_send_temperature_or_verbosity():
    """GPT-5.x reasoning models don't take ``temperature=`` or
    ``verbosity=``. Guard against a future edit that adds them."""
    ws = _workspace("mig-nokw@t")
    universe = Universe.objects.create(workspace=ws, name="Workshop")
    patch, rivet = _cast(ws, universe=universe)
    raw = _valid_turns_json(n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_returning(raw)

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_canon",
             return_value=[],
         ), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_universe_memory",
             return_value=[],
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=True,
        )

    kwargs = fake_client.responses.create.call_args.kwargs
    assert "temperature" not in kwargs
    assert "verbosity" not in kwargs
    # ``max_tokens`` is the Chat Completions name; Responses API
    # uses ``max_output_tokens``. Guard against confusion.
    assert "max_tokens" not in kwargs
    assert "max_output_tokens" in kwargs
