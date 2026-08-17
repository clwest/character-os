"""SESSION 257 / AI-D2 — ``character_os.dialogue_synthesis``.

Focused unit + integration coverage for multi-character dialogue
synthesis:

* Alias generation (deterministic, collision-safe).
* Structured LLM output parsing + validation.
* Per-character K2 retrieval isolation.
* Per-turn K6.4 verification.
* Bounded corrective resynth on validation failure.
* Duration + turn-count contracts.
* Talking-head calibration untouched.
* Mock mode.
* Cross-workspace + precondition guards.

Does NOT hit OpenAI or Runway. All provider calls are mocked or
routed through ``mock_mode=True``.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock
from unittest.mock import patch as mock_patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os.claim_verifier import ClaimVerifierError, UnsupportedClaim
from character_os.dialogue_synthesis import (
    DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER,
    DialogueResult,
    DialogueSynthesisError,
    DialogueTurn,
    build_alias_map,
    synthesize_dialogue,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures ----------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(
    ws: Workspace,
    *,
    name: str = "Test",
    business_brief: str = "",
    personality: str = "",
    character_point_of_view: str = "",
    voice_energy: str = "medium",
    voice_humor: str = "warm",
    voice_directness: str = "balanced",
    voice_signature_phrases: str = "",
    voice_avoid_phrases: str = "",
    always_emphasize: str = "",
    never_say: str = "",
    desired_feeling: str = "",
    who_you_help: str = "",
    what_you_sell: str = "",
    tone_archetype: str = "expert",
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief=business_brief,
        personality=personality,
        tone_archetype=tone_archetype,
        who_you_help=who_you_help,
        what_you_sell=what_you_sell,
        always_emphasize=always_emphasize,
        never_say=never_say,
        desired_feeling=desired_feeling,
        character_point_of_view=character_point_of_view,
        voice_energy=voice_energy,
        voice_humor=voice_humor,
        voice_directness=voice_directness,
        voice_signature_phrases=voice_signature_phrases,
        voice_avoid_phrases=voice_avoid_phrases,
    )


def _cast(ws: Workspace) -> tuple[Teammate, Teammate]:
    """Standard 2-character cast for tests."""
    patch = _teammate(
        ws,
        name="Patch",
        personality="Curious tinkerer.",
        business_brief="Runs the workshop.",
    )
    rivet = _teammate(
        ws,
        name="Rivet",
        personality="Methodical robot.",
        business_brief="Rivet is a robot assistant Patch built.",
    )
    return patch, rivet


def _valid_turns_json(patch_alias: str, rivet_alias: str, n_turns: int,
                       *, per_turn_chars: int = 100) -> str:
    """Build a valid structured response for the mocked LLM.
    Pads each turn to the requested char count so the caller can
    tune whether the aggregate falls inside / outside the ±20 %
    band."""
    turns = []
    for i in range(n_turns):
        alias = patch_alias if i % 2 == 0 else rivet_alias
        pad = "x" * max(1, per_turn_chars - 20)
        turns.append({
            "line_index": i,
            "speaker_alias": alias,
            "text": f"[turn {i} by {alias}] {pad}",
        })
    return json.dumps({"turns": turns})


def _openai_call_returning(*responses: str):
    """Build a MagicMock that returns each of ``responses`` in
    sequence when ``client.responses.create`` is invoked. Used
    to mock the OpenAI Responses API."""
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


# ---- 1. Alias generation -----------------------------------------


def test_alias_from_simple_name_is_deterministic():
    ws = _workspace("ali1@t")
    patch, rivet = _cast(ws)
    m1 = build_alias_map([patch, rivet])
    m2 = build_alias_map([patch, rivet])
    assert list(m1.keys()) == list(m2.keys()) == ["patch", "rivet"]
    assert m1["patch"] is patch
    assert m1["rivet"] is rivet


def test_alias_sanitizes_special_chars_and_punctuation():
    ws = _workspace("ali2@t")
    tm1 = _teammate(ws, name="Dr. Rivet-42!")
    tm2 = _teammate(ws, name="  Spaces  Around  ")
    m = build_alias_map([tm1, tm2])
    aliases = list(m.keys())
    assert aliases[0] == "dr_rivet_42"
    assert aliases[1] == "spaces_around"


def test_alias_collision_resolves_deterministically():
    """Two Teammates named 'Patch' → cast[0] wins 'patch',
    cast[1] gets 'patch_2'. Order-preserving + collision-safe."""
    ws = _workspace("ali3@t")
    tm1 = _teammate(ws, name="Patch")
    tm2 = _teammate(ws, name="patch")  # different casing, same slug
    m = build_alias_map([tm1, tm2])
    assert list(m.keys()) == ["patch", "patch_2"]
    assert m["patch"] is tm1
    assert m["patch_2"] is tm2


def test_alias_handles_empty_or_unrenderable_name():
    """Empty / pure-whitespace names fall back to 'speaker'
    with numeric suffixes on collision."""
    ws = _workspace("ali4@t")
    tm1 = _teammate(ws, name="")
    tm2 = _teammate(ws, name="   ")
    m = build_alias_map([tm1, tm2])
    assert list(m.keys()) == ["speaker", "speaker_2"]


# ---- 2. Structured output parsing (mocked LLM) ------------------


def _synthesize_with_mock(
    ws, cast, *, first_response: str, second_response: str | None = None,
    topic: str = "A test topic worth talking about.",
    target: int = 60,
    opener: str | None = None,
    use_knowledge: bool = False,
    verifier_mode: str = "warn",
):
    """Helper — call synthesize_dialogue with the OpenAI client
    stubbed to return the given raw payload(s). Uses
    use_knowledge=False by default so K2 retrieval doesn't fire
    (test-hermetic)."""
    payloads = [first_response] if second_response is None \
        else [first_response, second_response]
    fake_client, call_count = _openai_call_returning(*payloads)
    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        with mock_patch("openai.OpenAI", return_value=fake_client):
            result = synthesize_dialogue(
                workspace=ws,
                cast=cast,
                topic=topic,
                target_duration_seconds=target,
                opener=opener,
                use_knowledge=use_knowledge,
                verifier_mode=verifier_mode,
                mock_mode=False,
            )
    return result, call_count


def test_valid_two_character_response_parses_and_resolves():
    ws = _workspace("parse1@t")
    patch, rivet = _cast(ws)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    # 8 × 113 = 904 chars ≈ 60.3 s at 15 cps — inside 60 s ±20 %.
    result, call_count = _synthesize_with_mock(
        ws, [patch, rivet], first_response=raw,
    )
    assert call_count["n"] == 1
    assert len(result.turns) == 8
    assert result.turns[0].speaker_teammate is patch
    assert result.turns[1].speaker_teammate is rivet
    assert result.overall_verification_status == "verified"


def test_unknown_speaker_alias_rejected_after_retry():
    """First response uses an unknown alias → hint fires →
    second response repeats the same alias → hard rejection."""
    ws = _workspace("parse2@t")
    patch, rivet = _cast(ws)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "skipper", "text": "hi"},
        {"line_index": 1, "speaker_alias": "rivet", "text": "hello"},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "unknown speaker_alias" in str(exc.value)


def test_invented_third_speaker_rejected():
    """Semantically identical to unknown-alias but named
    separately per operator brief."""
    ws = _workspace("parse3@t")
    patch, rivet = _cast(ws)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch", "text": "hi"},
        {"line_index": 1, "speaker_alias": "rivet", "text": "hi back"},
        {"line_index": 2, "speaker_alias": "narrator", "text": "and then"},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "unknown speaker_alias" in str(exc.value)
    assert "narrator" in str(exc.value)


def test_gapped_line_index_rejected():
    ws = _workspace("parse4@t")
    patch, rivet = _cast(ws)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch", "text": "a"},
        {"line_index": 2, "speaker_alias": "rivet", "text": "b"},  # gap
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "line_index" in str(exc.value)


def test_duplicate_line_index_rejected():
    ws = _workspace("parse5@t")
    patch, rivet = _cast(ws)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch", "text": "a"},
        {"line_index": 0, "speaker_alias": "rivet", "text": "b"},  # dup
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "duplicate" in str(exc.value)


def test_empty_text_rejected():
    ws = _workspace("parse6@t")
    patch, rivet = _cast(ws)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch", "text": "a"},
        {"line_index": 1, "speaker_alias": "rivet", "text": "   "},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "empty text" in str(exc.value)


def test_over_provider_cap_turn_rejected():
    ws = _workspace("parse7@t")
    patch, rivet = _cast(ws)
    over = "x" * 2000  # > AVATAR_SPEECH_SAFE_MAX_CHARS (1900)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch", "text": "a"},
        {"line_index": 1, "speaker_alias": "rivet", "text": over},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "per-turn maximum" in str(exc.value)


def test_short_reaction_accepted():
    """SESSION 257 anti-min-line-length invariant — short
    reactions are legitimate dialogue tools. Prior audit's
    cost-driven 45-char floor was RETRACTED after billing
    correction (46f5efd)."""
    ws = _workspace("parse8@t")
    patch, rivet = _cast(ws)
    # Craft 8 turns hitting ~60s ±20% but with one short reaction.
    turns = [
        {"line_index": 0, "speaker_alias": "patch",
         "text": "x" * 200},
        {"line_index": 1, "speaker_alias": "rivet",
         "text": "Define 'still.'"},  # 15 chars — deliberately short
        {"line_index": 2, "speaker_alias": "patch",
         "text": "x" * 200},
        {"line_index": 3, "speaker_alias": "rivet",
         "text": "x" * 200},
        {"line_index": 4, "speaker_alias": "patch",
         "text": "x" * 200},
        {"line_index": 5, "speaker_alias": "rivet",
         "text": "x" * 145},
    ]
    # total = 200+15+200+200+200+145 = 960 chars → 64s (in 60±20)
    raw = json.dumps({"turns": turns})
    result, _ = _synthesize_with_mock(
        ws, [patch, rivet], first_response=raw,
    )
    assert len(result.turns) == 6
    assert result.turns[1].text == "Define 'still.'"


def test_hard_max_turn_count_enforced():
    """60s → hard max 18 turns. 25 turns triggers hint;
    second response also over → hard rejection."""
    ws = _workspace("parse9@t")
    patch, rivet = _cast(ws)
    bad = _valid_turns_json("patch", "rivet", n_turns=25, per_turn_chars=40)
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    assert "maximum is 18" in str(exc.value) or "consolidate" in str(exc.value).lower()


def test_below_hard_min_turns_rejected():
    ws = _workspace("parse10@t")
    patch, rivet = _cast(ws)
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch", "text": "x" * 900},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
        )
    reason = str(exc.value).lower()
    assert "at least 2" in reason or "requires at least" in reason


def test_aggregate_too_short_triggers_corrective_resynth():
    """First pass: 6 turns × 30 chars = 180 chars → 12s
    (target 60s, band 48–72). Hint fires. Second pass:
    valid — succeeds."""
    ws = _workspace("parse11@t")
    patch, rivet = _cast(ws)
    too_short = _valid_turns_json("patch", "rivet", n_turns=6,
                                   per_turn_chars=30)
    valid = _valid_turns_json("patch", "rivet", n_turns=8,
                              per_turn_chars=113)
    result, call_count = _synthesize_with_mock(
        ws, [patch, rivet],
        first_response=too_short, second_response=valid,
    )
    assert call_count["n"] == 2
    assert len(result.turns) == 8


def test_aggregate_too_long_triggers_corrective_resynth():
    """First pass overshoots by a wide margin; hint fires;
    second pass valid."""
    ws = _workspace("parse12@t")
    patch, rivet = _cast(ws)
    too_long = _valid_turns_json("patch", "rivet", n_turns=10,
                                  per_turn_chars=400)
    valid = _valid_turns_json("patch", "rivet", n_turns=8,
                              per_turn_chars=113)
    result, call_count = _synthesize_with_mock(
        ws, [patch, rivet],
        first_response=too_long, second_response=valid,
    )
    assert call_count["n"] == 2
    assert len(result.turns) == 8


def test_second_invalid_response_fails_cleanly_with_raw_json():
    """Two consecutive validation failures → DialogueSynthesisError
    that carries the raw LLM JSON for audit persistence."""
    ws = _workspace("parse13@t")
    patch, rivet = _cast(ws)
    too_short_1 = _valid_turns_json("patch", "rivet", n_turns=4,
                                     per_turn_chars=20)
    too_short_2 = _valid_turns_json("patch", "rivet", n_turns=5,
                                     per_turn_chars=20)
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet],
            first_response=too_short_1, second_response=too_short_2,
        )
    assert exc.value.raw_llm_json == too_short_2
    assert "after one corrective pass" in exc.value.reason


def test_opener_belongs_to_primary_after_parse():
    """Turn 0 spoken by cast[1] fails validation even if opener
    text matches."""
    ws = _workspace("parse14@t")
    patch, rivet = _cast(ws)
    opener = "Rivet was designed to improve workshop efficiency."
    # Turn 0 misassigned to rivet
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "rivet",
         "text": opener + " x" * 100},
        {"line_index": 1, "speaker_alias": "patch",
         "text": "x" * 100},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
            opener=opener,
        )
    assert "primary" in str(exc.value).lower() or "'patch'" in str(exc.value)


def test_opener_must_be_preserved_verbatim():
    """Turn 0 exists on primary but text does not start with the
    opener → rejection."""
    ws = _workspace("parse15@t")
    patch, rivet = _cast(ws)
    opener = "Rivet was designed to improve workshop efficiency."
    bad = json.dumps({"turns": [
        {"line_index": 0, "speaker_alias": "patch",
         "text": "Something else entirely " + "x" * 100},
        {"line_index": 1, "speaker_alias": "rivet",
         "text": "x" * 100},
    ]})
    with pytest.raises(DialogueSynthesisError) as exc:
        _synthesize_with_mock(
            ws, [patch, rivet], first_response=bad, second_response=bad,
            opener=opener,
        )
    assert "opener" in str(exc.value).lower()


# ---- 3. K2 isolation --------------------------------------------


def test_use_knowledge_true_calls_retrieve_per_character():
    """K2 retrieval is called ONCE PER CAST MEMBER with the same
    topic — matching contract rule 7. Corpora are per-character
    downstream."""
    ws = _workspace("k2iso@t")
    patch, rivet = _cast(ws)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_call_returning(raw)
    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ) as fake_retrieve:
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic worth talking about",
            target_duration_seconds=60,
            use_knowledge=True,
        )
    # One retrieval call per cast member, with the same topic.
    assert fake_retrieve.call_count == 2
    called_teammates = [c.args[0] for c in fake_retrieve.call_args_list]
    assert patch in called_teammates
    assert rivet in called_teammates
    for c in fake_retrieve.call_args_list:
        assert c.args[1] == "a topic worth talking about"


def test_use_knowledge_false_skips_retrieval():
    ws = _workspace("k2skip@t")
    patch, rivet = _cast(ws)
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_call_returning(raw)
    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             return_value=[],
         ) as fake_retrieve:
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="a topic",
            target_duration_seconds=60,
            use_knowledge=False,
        )
    assert fake_retrieve.call_count == 0
    assert result.used_knowledge is False
    assert result.chunk_ids == []


# ---- 4. Per-turn K6.4 -------------------------------------------


def test_k64_uses_speaking_character_corpus_per_turn():
    """Each turn's verifier call uses the SPEAKING character's
    factual corpus + allowed vocabulary. Patch turn → Patch
    inputs; Rivet turn → Rivet inputs. Never merged."""
    ws = _workspace("k64iso@t")
    patch = _teammate(
        ws, name="Patch", business_brief="Patch's brief.",
    )
    rivet = _teammate(
        ws, name="Rivet", business_brief="Rivet's brief.",
    )
    raw = _valid_turns_json("patch", "rivet", n_turns=8, per_turn_chars=113)
    fake_client, _ = _openai_call_returning(raw)

    seen_corpora: list[str] = []

    def _fake_verifier(text, *, factual_corpus, allowed_vocabulary,
                       mode=None):
        seen_corpora.append(factual_corpus)
        return []

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "character_os.dialogue_synthesis.run_verifier",
             side_effect=_fake_verifier,
         ):
        synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="test topic",
            target_duration_seconds=60,
            use_knowledge=False,
        )
    # 8 turns → 8 verifier calls; even indices = patch, odd = rivet.
    assert len(seen_corpora) == 8
    for i, corpus in enumerate(seen_corpora):
        if i % 2 == 0:
            assert "Patch's brief." in corpus
            assert "Rivet's brief." not in corpus
        else:
            assert "Rivet's brief." in corpus
            assert "Patch's brief." not in corpus


def test_warnings_retain_speaker_and_turn_context():
    """Warnings surface per-turn on the DialogueTurn row, not
    globally merged."""
    ws = _workspace("k64warn@t")
    patch, rivet = _cast(ws)
    raw = _valid_turns_json("patch", "rivet", n_turns=4, per_turn_chars=225)
    fake_client, _ = _openai_call_returning(raw)

    call_num = {"n": 0}

    def _fake_verifier(text, *, factual_corpus, allowed_vocabulary,
                       mode=None):
        call_num["n"] += 1
        # Only fire a warning on turn 2 (odd-indexed = rivet).
        if call_num["n"] == 3:
            return [UnsupportedClaim(
                claim="unsupported fact",
                position=0,
                kind="year",
            )]
        return []

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "character_os.dialogue_synthesis.run_verifier",
             side_effect=_fake_verifier,
         ):
        result = synthesize_dialogue(
            workspace=ws,
            cast=[patch, rivet],
            topic="test topic",
            target_duration_seconds=60,
            use_knowledge=False,
        )
    # Only turn 2 carries warnings; others clean.
    assert result.turns[0].verification_warnings == []
    assert result.turns[1].verification_warnings == []
    assert len(result.turns[2].verification_warnings) == 1
    assert result.turns[3].verification_warnings == []
    assert result.turns[2].verification_status == "warned"
    assert result.overall_verification_status == "warned"


def test_strict_verifier_failure_raises():
    ws = _workspace("k64strict@t")
    patch, rivet = _cast(ws)
    raw = _valid_turns_json("patch", "rivet", n_turns=4, per_turn_chars=225)
    fake_client, _ = _openai_call_returning(raw)

    def _fake_verifier(text, *, factual_corpus, allowed_vocabulary,
                       mode=None):
        # Strict mode: raise on the first turn.
        if (mode or "").lower() == "strict":
            raise ClaimVerifierError(
                unsupported=[
                    UnsupportedClaim(
                        claim="bogus", position=0, kind="year",
                    ),
                ],
                synthesized_text=text,
            )
        return []

    with mock_patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}), \
         mock_patch("openai.OpenAI", return_value=fake_client), \
         mock_patch(
             "character_os.dialogue_synthesis.run_verifier",
             side_effect=_fake_verifier,
         ):
        with pytest.raises(ClaimVerifierError):
            synthesize_dialogue(
                workspace=ws,
                cast=[patch, rivet],
                topic="test topic",
                target_duration_seconds=60,
                use_knowledge=False,
                verifier_mode="strict",
            )


# ---- 5. Duration + calibration ----------------------------------


def test_writing_contract_version_is_4():
    """Mock-mode result carries the current contract stamp.

    SESSION 259 continuity slice bumped the version 3 → 4 to
    distinguish dialogue outputs shaped by invariant #10 CAUSAL
    CHAIN (turn-to-turn conversational causation). v3 additions
    (watchability + anti-patterns) are preserved verbatim.
    Standalone + long_form contract text remain byte-stable.
    """
    ws = _workspace("v4stamp@t")
    patch, rivet = _cast(ws)
    result = synthesize_dialogue(
        workspace=ws, cast=[patch, rivet],
        topic="test topic", target_duration_seconds=60,
        mock_mode=True,
    )
    assert result.writing_contract_version == 4
    assert result.writing_contract_version == WRITING_CONTRACT_VERSION


def test_dialogue_multiplier_is_1_00():
    """Dialogue owns its own calibration constant. Separate
    from talking-head's 0.90."""
    assert DIALOGUE_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 1.00


def test_talking_head_multiplier_untouched_by_dialogue():
    """AI-D2 must not have moved talking-head's calibration."""
    from character_os.duration_contract import (
        K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER,
    )
    assert K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER == 0.90


# ---- 6. Preconditions -------------------------------------------


def test_cross_workspace_cast_rejected():
    ws1 = _workspace("xws1@t")
    ws2 = _workspace("xws2@t")
    patch = _teammate(ws1, name="Patch")
    rivet = _teammate(ws2, name="Rivet")  # different workspace
    with pytest.raises(DialogueSynthesisError) as exc:
        synthesize_dialogue(
            workspace=ws1, cast=[patch, rivet],
            topic="test", target_duration_seconds=60,
            mock_mode=True,
        )
    assert "does not belong" in str(exc.value)


def test_single_character_cast_rejected():
    ws = _workspace("solo@t")
    patch = _teammate(ws, name="Patch")
    with pytest.raises(DialogueSynthesisError) as exc:
        synthesize_dialogue(
            workspace=ws, cast=[patch],
            topic="test", target_duration_seconds=60,
            mock_mode=True,
        )
    assert "at least 2" in str(exc.value)


def test_empty_topic_rejected():
    ws = _workspace("notopic@t")
    patch, rivet = _cast(ws)
    with pytest.raises(DialogueSynthesisError) as exc:
        synthesize_dialogue(
            workspace=ws, cast=[patch, rivet],
            topic="   ", target_duration_seconds=60,
            mock_mode=True,
        )
    assert "topic" in str(exc.value).lower()


# ---- 7. Mock mode ------------------------------------------------


def test_mock_mode_returns_valid_dialogueresult_without_provider_call():
    """Mock mode never calls OpenAI or K2 retrieval. The result
    shape is a valid DialogueResult that would round-trip
    through any downstream consumer."""
    ws = _workspace("mock1@t")
    patch, rivet = _cast(ws)
    with mock_patch("openai.OpenAI", side_effect=AssertionError("openai called")), \
         mock_patch(
             "apps.embeddings.retrieval.retrieve_for_teammate",
             side_effect=AssertionError("retrieval called"),
         ):
        result = synthesize_dialogue(
            workspace=ws, cast=[patch, rivet],
            topic="mock scene topic",
            target_duration_seconds=60,
            mock_mode=True,
        )
    assert isinstance(result, DialogueResult)
    assert result.mock_mode is True
    assert result.model == "mock"
    assert len(result.turns) >= 2
    for turn in result.turns:
        assert isinstance(turn, DialogueTurn)
        assert turn.text.strip() != ""
        assert turn.line_index >= 0
        assert turn.speaker_teammate in (patch, rivet)


def test_mock_mode_uses_only_selected_aliases():
    ws = _workspace("mock2@t")
    patch, rivet = _cast(ws)
    result = synthesize_dialogue(
        workspace=ws, cast=[patch, rivet],
        topic="scene", target_duration_seconds=60,
        mock_mode=True,
    )
    approved = {"patch", "rivet"}
    for turn in result.turns:
        assert turn.speaker_alias in approved


def test_mock_mode_preserves_opener_on_primary():
    ws = _workspace("mock3@t")
    patch, rivet = _cast(ws)
    opener = "Rivet was designed to improve workshop efficiency."
    result = synthesize_dialogue(
        workspace=ws, cast=[patch, rivet],
        topic="scene", target_duration_seconds=60,
        opener=opener, mock_mode=True,
    )
    assert result.turns[0].speaker_teammate is patch
    assert result.turns[0].text.startswith(opener)


def test_mock_mode_satisfies_all_post_parse_validators():
    """Every validator that the real path enforces must pass
    against the mock result — otherwise the mock is a lie."""
    ws = _workspace("mock4@t")
    patch, rivet = _cast(ws)
    result = synthesize_dialogue(
        workspace=ws, cast=[patch, rivet],
        topic="scene", target_duration_seconds=60,
        mock_mode=True,
    )
    # Contiguous line_index.
    assert [t.line_index for t in result.turns] == list(
        range(len(result.turns))
    )
    # Turn count hard bounds — 60s → hard max 18.
    assert 2 <= len(result.turns) <= 18
    # Per-turn cap.
    from character_os.duration_contract import AVATAR_SPEECH_SAFE_MAX_CHARS
    for turn in result.turns:
        assert len(turn.text) <= AVATAR_SPEECH_SAFE_MAX_CHARS
    # Aggregate duration inside ±20 % of target.
    lower = 60 * 0.8
    upper = 60 * 1.2
    assert lower <= result.predicted_seconds <= upper


def test_mock_mode_includes_consecutive_same_speaker_pair():
    """Load-bearing invariant — mock output must demonstrate
    the anti-alternation contract by including at least one
    A→A or B→B adjacent pair. This is the assertion that pins
    contract rule 14 for downstream consumers."""
    ws = _workspace("mock5@t")
    patch, rivet = _cast(ws)
    result = synthesize_dialogue(
        workspace=ws, cast=[patch, rivet],
        topic="scene", target_duration_seconds=60,
        mock_mode=True,
    )
    seen_consecutive_same = False
    for i in range(1, len(result.turns)):
        if result.turns[i].speaker_alias == result.turns[i - 1].speaker_alias:
            seen_consecutive_same = True
            break
    assert seen_consecutive_same, (
        "mock dialogue must include at least one consecutive "
        "same-speaker pair to prove AI mode does not force "
        "alternation (contract rule 14)"
    )
