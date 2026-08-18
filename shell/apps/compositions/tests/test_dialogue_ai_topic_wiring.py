"""SESSION 257 / AI-D3 — dialogue_scene recipe wiring + AI-Topic
resolver / starter / view integration.

Covers:

* Manual mode regression (dialogue_mode omitted OR explicit "manual"
  behaves exactly like the pre-AI-D3 path; no synthesis call).
* AI request validation (resolver + starter enforce required fields,
  cast constraints, duration choices).
* Successful AI wiring (synthesize_dialogue invoked with correct
  kwargs; result hydrates the existing render graph).
* AI success persistence (writing_contract_version, verification_*,
  knowledge_chunk_ids, synthesized_brief all captured on the
  Composition row).
* AI rejection persistence (DialogueSynthesisFailedError → view
  creates FAILED composition; zero avatar_video calls; no partial
  speech steps).
* Cost regression (successful N-turn compositions still derive cost
  from the existing avatar_speech primitive; no new dialogue
  estimator).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.cost import estimate_composition_cost
from apps.compositions.models import (
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.recipes import _dialogue_resolver, get_recipe
from apps.compositions.starters import (
    DialogueSynthesisFailedError,
    dialogue_scene,
)
from apps.spokespeople.models import Teammate
from character_os.dialogue_synthesis import (
    DIALOGUE_MODEL,
    DialogueResult,
    DialogueSynthesisError,
    DialogueTurn,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures -----------------------------------------------------


def _ws(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _tm(ws: Workspace, name: str, *, avatar: str | None = None) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=avatar or f"av-{name.lower()}",
        portrait_path="https://fake/p.png",
        business_brief=f"{name}'s brief.",
    )


def _cast(ws: Workspace) -> tuple[Teammate, Teammate]:
    return _tm(ws, "Patch"), _tm(ws, "Rivet")


def _fake_dialogue_result(
    primary: Teammate, secondary: Teammate, *,
    n_turns: int = 6,
    total_chars: int = 900,
    warnings_on_turn: int | None = None,
    verification_status: str = "verified",
) -> DialogueResult:
    """Build a synthesized DialogueResult matching what
    synthesize_dialogue would return for a valid scene."""
    turns: list[DialogueTurn] = []
    per_turn_chars = max(1, total_chars // n_turns)
    # Interleave so we get at least one consecutive-same-speaker pair.
    order = [primary, secondary, secondary, primary, primary, secondary]
    while len(order) < n_turns:
        order.append(secondary if order[-1] is primary else primary)
    for i in range(n_turns):
        sp = order[i]
        alias = "patch" if sp is primary else "rivet"
        warns = []
        if warnings_on_turn is not None and warnings_on_turn == i:
            warns = [{"claim": "invented fact", "position": 0, "kind": "year"}]
        turns.append(DialogueTurn(
            line_index=i,
            speaker_teammate=sp,
            speaker_alias=alias,
            text=f"turn {i} by {alias}: " + "x" * (per_turn_chars - 20),
            verification_warnings=warns,
            verification_status="warned" if warns else "verified",
        ))
    total = sum(len(t.text) for t in turns)
    return DialogueResult(
        turns=turns,
        chunk_ids=["chunk-a", "chunk-b"],
        per_character_chunk_ids={"patch": ["chunk-a"], "rivet": ["chunk-b"]},
        writing_contract_version=WRITING_CONTRACT_VERSION,
        overall_verification_status=verification_status,
        total_chars=total,
        predicted_seconds=total / 13,  # SESSION 260 cps calibration
        target_duration_seconds=60,
        aliases={"patch": primary.name, "rivet": secondary.name},
        mock_mode=False,
        used_knowledge=True,
        # Track the constant so future model migrations don't
        # require a test edit (SESSION 264 model swap lesson).
        model=DIALOGUE_MODEL,
        tokens_input=100,
        tokens_output=500,
        raw_llm_json='{"turns": []}',
    )


# ========================================================================
# A. MANUAL MODE REGRESSION
# ========================================================================


def test_manual_mode_omitted_dialogue_mode_still_works():
    """Backward compat: pre-AI-D3 requests (no dialogue_mode field)
    resolve exactly like they did before."""
    ws = _ws("mm1@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "primary_spokesperson_id": str(p.pk),
            "lines": [
                {"spokesperson_id": str(p.pk), "text": "Hello"},
                {"spokesperson_id": str(r.pk), "text": "Hi back"},
            ],
        },
        created_by=None,
    )
    assert kwargs["dialogue_mode"] == "manual"
    assert len(kwargs["lines"]) == 2
    # Resolver goes through Teammate.objects.get so Python identity
    # won't match the fixture instance; assert by pk equality.
    assert kwargs["lines"][0]["spokesperson"].pk == p.pk
    assert kwargs["lines"][1]["spokesperson"].pk == r.pk


def test_manual_mode_explicit_produces_same_kwargs():
    ws = _ws("mm2@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "dialogue_mode": "manual",
            "primary_spokesperson_id": str(p.pk),
            "lines": [
                {"spokesperson_id": str(p.pk), "text": "one"},
                {"spokesperson_id": str(r.pk), "text": "two"},
            ],
        },
        created_by=None,
    )
    assert kwargs["dialogue_mode"] == "manual"
    assert len(kwargs["lines"]) == 2


def test_manual_mode_starter_produces_same_render_graph_as_before():
    """Manual mode starter path: 2 speech steps + 1 concat + optional
    outro. Bit-for-bit unchanged from pre-AI-D3."""
    ws = _ws("mm3@t")
    p, r = _cast(ws)
    comp = dialogue_scene(
        workspace=ws,
        primary_spokesperson=p,
        lines=[
            {"spokesperson": p, "text": "Hello"},
            {"spokesperson": r, "text": "Hi back"},
        ],
        outro_text="Brand",
        mock_mode=True,
    )
    steps = list(comp.steps.all().order_by("position"))
    assert [s.primitive for s in steps] == [
        "generate_avatar_speech",
        "generate_avatar_speech",
        "concat_clips",
        "add_intro_outro",
    ]
    # No AI metadata should be persisted on a manual composition.
    assert comp.writing_contract_version == 0
    assert comp.knowledge_chunk_ids == []
    assert comp.synthesized_brief == ""
    assert comp.verification_status == ""


def test_manual_mode_never_calls_synthesize_dialogue():
    """The synthesis module must not be touched by manual mode —
    would blow up cost + latency for the historical happy path."""
    ws = _ws("mm4@t")
    p, r = _cast(ws)
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue"
    ) as fake_synth:
        dialogue_scene(
            workspace=ws,
            primary_spokesperson=p,
            lines=[
                {"spokesperson": p, "text": "a"},
                {"spokesperson": r, "text": "b"},
            ],
            mock_mode=True,
        )
    assert fake_synth.call_count == 0


# ========================================================================
# B. AI REQUEST VALIDATION
# ========================================================================


def test_ai_mode_requires_secondary_spokesperson():
    ws = _ws("ai_v1@t")
    p, _ = _cast(ws)
    with pytest.raises(ValueError) as exc:
        _dialogue_resolver(
            workspace=ws,
            params={
                "dialogue_mode": "ai_topic",
                "primary_spokesperson_id": str(p.pk),
                "topic": "test topic",
            },
            created_by=None,
        )
    assert "secondary" in str(exc.value).lower()


def test_ai_mode_rejects_primary_equals_secondary():
    ws = _ws("ai_v2@t")
    p, _ = _cast(ws)
    with pytest.raises(ValueError) as exc:
        _dialogue_resolver(
            workspace=ws,
            params={
                "dialogue_mode": "ai_topic",
                "primary_spokesperson_id": str(p.pk),
                "secondary_spokesperson_id": str(p.pk),
                "topic": "test topic",
            },
            created_by=None,
        )
    assert "different" in str(exc.value).lower()


def test_ai_mode_rejects_cross_workspace_secondary():
    ws1 = _ws("ai_v3a@t")
    ws2 = _ws("ai_v3b@t")
    p = _tm(ws1, "Patch")
    r = _tm(ws2, "Rivet")  # different workspace
    with pytest.raises(Teammate.DoesNotExist):
        _dialogue_resolver(
            workspace=ws1,
            params={
                "dialogue_mode": "ai_topic",
                "primary_spokesperson_id": str(p.pk),
                "secondary_spokesperson_id": str(r.pk),
                "topic": "test topic",
            },
            created_by=None,
        )


def test_ai_mode_requires_non_empty_topic():
    ws = _ws("ai_v4@t")
    p, r = _cast(ws)
    with pytest.raises(ValueError) as exc:
        _dialogue_resolver(
            workspace=ws,
            params={
                "dialogue_mode": "ai_topic",
                "primary_spokesperson_id": str(p.pk),
                "secondary_spokesperson_id": str(r.pk),
                "topic": "   ",
            },
            created_by=None,
        )
    assert "topic" in str(exc.value).lower()


def test_ai_mode_rejects_unsupported_target_duration():
    ws = _ws("ai_v5@t")
    p, r = _cast(ws)
    for bad in (15, 45, 180, 300):
        with pytest.raises(ValueError) as exc:
            _dialogue_resolver(
                workspace=ws,
                params={
                    "dialogue_mode": "ai_topic",
                    "primary_spokesperson_id": str(p.pk),
                    "secondary_spokesperson_id": str(r.pk),
                    "topic": "test",
                    "target_duration_seconds": bad,
                },
                created_by=None,
            )
        assert "target_duration_seconds" in str(exc.value)


# ========================================================================
# C. SUCCESSFUL SYNTHESIS WIRING
# ========================================================================


def _run_ai_starter_with_fake_synth(
    ws, primary, secondary, *, fake_result=None,
    target=60, opener=None, use_knowledge=True, verifier_mode="warn",
    topic="the workshop", mock_mode=True,
):
    """Run the starter in AI mode with synthesize_dialogue patched."""
    fake_result = fake_result or _fake_dialogue_result(primary, secondary)
    fake_synth = MagicMock(return_value=fake_result)
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        fake_synth,
    ):
        comp = dialogue_scene(
            workspace=ws,
            primary_spokesperson=primary,
            dialogue_mode="ai_topic",
            secondary_spokesperson=secondary,
            topic=topic,
            target_duration_seconds=target,
            opener=opener,
            use_knowledge=use_knowledge,
            verifier_mode=verifier_mode,
            mock_mode=mock_mode,
        )
    return comp, fake_synth


def test_synthesize_dialogue_receives_primary_then_secondary_in_order():
    ws = _ws("ai_c1@t")
    p, r = _cast(ws)
    _, fake_synth = _run_ai_starter_with_fake_synth(ws, p, r)
    kwargs = fake_synth.call_args.kwargs
    assert kwargs["cast"] == [p, r]


def test_ai_kwargs_flow_through():
    """use_knowledge, verifier_mode, opener, target_duration all
    propagate from resolver → starter → synthesize_dialogue."""
    ws = _ws("ai_c2@t")
    p, r = _cast(ws)
    _, fake_synth = _run_ai_starter_with_fake_synth(
        ws, p, r,
        target=90, opener="Opening line.",
        use_knowledge=False, verifier_mode="strict",
        topic="a specific topic",
    )
    k = fake_synth.call_args.kwargs
    assert k["workspace"] is ws
    assert k["target_duration_seconds"] == 90
    assert k["opener"] == "Opening line."
    assert k["use_knowledge"] is False
    assert k["verifier_mode"] == "strict"
    assert k["topic"] == "a specific topic"
    assert k["mock_mode"] is True


def test_ai_result_normalizes_into_manual_lines_shape():
    """DialogueResult.turns → one speech step per turn, in order,
    using each turn's actual Teammate/avatar_id."""
    ws = _ws("ai_c3@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=6)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)

    speech_steps = list(
        comp.steps.filter(primitive="generate_avatar_speech").order_by("position")
    )
    assert len(speech_steps) == 6
    for i, step in enumerate(speech_steps):
        turn = result.turns[i]
        assert step.position == i
        assert step.params["script"] == turn.text
        assert step.params["spokesperson_avatar_id"] == \
            turn.speaker_teammate.runway_avatar_id
        assert step.params["use_knowledge"] is False


def test_ai_speech_step_records_speaker_alias_provenance():
    """Per-step provenance carries the AI-generated speaker_alias
    so operators can trace which alias produced which turn."""
    ws = _ws("ai_c4@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=4)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)
    steps = list(
        comp.steps.filter(primitive="generate_avatar_speech").order_by("position")
    )
    for i, step in enumerate(steps):
        assert step.params.get("ai_topic_speaker_alias") == \
            result.turns[i].speaker_alias


def test_ai_render_graph_matches_manual_graph_shape():
    """The AI branch must NOT create any AI-specific primitives.
    Final graph: N generate_avatar_speech + 1 concat_clips
    (+ optional add_intro_outro)."""
    ws = _ws("ai_c5@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=5)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)
    primitives = [s.primitive for s in comp.steps.all().order_by("position")]
    assert primitives == [
        "generate_avatar_speech",
        "generate_avatar_speech",
        "generate_avatar_speech",
        "generate_avatar_speech",
        "generate_avatar_speech",
        "concat_clips",
    ]


def test_ai_consecutive_same_speaker_turns_preserved():
    """AI-D2 mock deliberately produces A→B→B→A patterns; wiring
    must preserve them, not silently collapse. Contract rule 14."""
    ws = _ws("ai_c6@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=6)
    # sanity: fake fixture DOES include a consecutive-same-speaker pair
    consecutive = any(
        result.turns[i].speaker_alias == result.turns[i - 1].speaker_alias
        for i in range(1, len(result.turns))
    )
    assert consecutive
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)
    speech_steps = list(
        comp.steps.filter(primitive="generate_avatar_speech").order_by("position")
    )
    for i in range(1, len(speech_steps)):
        prev_alias = speech_steps[i - 1].params.get("ai_topic_speaker_alias")
        curr_alias = speech_steps[i].params.get("ai_topic_speaker_alias")
        # The generated ordering must be reproduced verbatim.
        assert curr_alias == result.turns[i].speaker_alias
        assert prev_alias == result.turns[i - 1].speaker_alias


def test_ai_outro_still_terminal_when_supplied():
    ws = _ws("ai_c7@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=4)
    fake_synth = MagicMock(return_value=result)
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        fake_synth,
    ):
        comp = dialogue_scene(
            workspace=ws,
            primary_spokesperson=p,
            dialogue_mode="ai_topic",
            secondary_spokesperson=r,
            topic="test",
            target_duration_seconds=60,
            outro_text="Brand outro",
            mock_mode=True,
        )
    steps = list(comp.steps.all().order_by("position"))
    assert steps[-1].primitive == "add_intro_outro"
    assert steps[-2].primitive == "concat_clips"


# ========================================================================
# D. PERSISTENCE (success)
# ========================================================================


def test_ai_success_persists_writing_contract_version():
    ws = _ws("ai_d1@t")
    p, r = _cast(ws)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r)
    assert comp.writing_contract_version == WRITING_CONTRACT_VERSION


def test_ai_success_persists_knowledge_chunk_ids():
    ws = _ws("ai_d2@t")
    p, r = _cast(ws)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r)
    assert set(comp.knowledge_chunk_ids) == {"chunk-a", "chunk-b"}


def test_ai_success_persists_verification_status_and_warnings():
    ws = _ws("ai_d3@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(
        p, r, n_turns=4, warnings_on_turn=2,
        verification_status="warned",
    )
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)
    # DialogueResult "warned" normalizes to "verified" with warnings
    # populated (matches VerificationStatus enum semantics).
    assert comp.verification_status == "verified"
    assert len(comp.verification_warnings) == 1
    warn = comp.verification_warnings[0]
    # Warning retains speaker + line context.
    assert warn["line_index"] == 2
    assert warn["speaker_alias"] in {"patch", "rivet"}
    assert warn["speaker_name"] in {"Patch", "Rivet"}


def test_ai_success_synthesized_brief_is_human_readable():
    ws = _ws("ai_d4@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=4)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)
    brief = comp.synthesized_brief
    # Header carries alias + per-character chunk provenance.
    assert "AI Topic dialogue synthesis" in brief
    assert "patch" in brief and "rivet" in brief
    assert "chunk-a" in brief and "chunk-b" in brief
    # Body contains each character's lines by name.
    assert "Patch:" in brief
    assert "Rivet:" in brief


def test_ai_success_per_character_chunk_provenance_preserved():
    """The per-character chunk provenance survives on the
    synthesized_brief header even though Composition.knowledge_chunk_ids
    is flat."""
    ws = _ws("ai_d5@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=4)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)
    # Header line format: "patch=[chunk-a]; rivet=[chunk-b]"
    assert "patch=[chunk-a]" in comp.synthesized_brief
    assert "rivet=[chunk-b]" in comp.synthesized_brief


def test_ai_success_composition_status_starts_in_normal_lifecycle():
    """Successful synthesis creates a normal composition ready
    for the Celery runner (DRAFT / PLANNING). FAILED is reserved
    for rejection."""
    ws = _ws("ai_d6@t")
    p, r = _cast(ws)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r)
    assert comp.status not in {
        CompositionStatus.FAILED,
        CompositionStatus.PARTIAL,
    }


# ========================================================================
# E. REJECTION / ECONOMIC INVARIANT
# ========================================================================


def test_ai_synthesis_rejection_raises_dialogue_synthesis_failed_error():
    """When synthesize_dialogue's own retry fails, the starter
    raises DialogueSynthesisFailedError with the persistence
    payload. Zero speech steps created; zero avatar_video calls."""
    ws = _ws("ai_e1@t")
    p, r = _cast(ws)
    fake_synth = MagicMock(side_effect=DialogueSynthesisError(
        "your scene runs about 20 seconds",
        raw_llm_json='{"turns": [{"line_index": 0, "speaker_alias": "patch", "text": "hi"}]}',
    ))
    baseline_steps = CompositionStep.objects.count()
    baseline_comps = Composition.objects.count()
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        fake_synth,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="test",
                target_duration_seconds=60,
                mock_mode=True,
            )
    # ZERO speech steps created.
    assert CompositionStep.objects.count() == baseline_steps
    # No composition row created inline (view creates it after).
    assert Composition.objects.count() == baseline_comps
    assert exc.value.workspace is ws
    assert exc.value.spokesperson is p
    assert exc.value.verification_status == "rejected"
    assert exc.value.writing_contract_version == WRITING_CONTRACT_VERSION


def test_ai_rejection_retains_raw_llm_json_when_available():
    ws = _ws("ai_e2@t")
    p, r = _cast(ws)
    raw = '{"turns": [{"line_index": 0, "speaker_alias": "x", "text": "y"}]}'
    fake_synth = MagicMock(side_effect=DialogueSynthesisError(
        "unknown speaker_alias 'x'", raw_llm_json=raw,
    ))
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        fake_synth,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="test",
                target_duration_seconds=60,
                mock_mode=True,
            )
    assert exc.value.rejected_synthesis == raw


def test_ai_rejection_creates_zero_avatar_speech_or_media_engine_calls():
    """Load-bearing economic invariant. If synthesis is rejected,
    NO downstream primitives (avatar_speech in particular) may
    fire. Assert by mocking MediaEngineClient's constructor: any
    real primitive dispatch would blow up before Runway."""
    ws = _ws("ai_e3@t")
    p, r = _cast(ws)
    fake_synth = MagicMock(side_effect=DialogueSynthesisError(
        "boom", raw_llm_json="",
    ))
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        fake_synth,
    ), patch(
        "character_os.clients.media_engine.MediaEngineClient",
        side_effect=AssertionError("media-engine touched on rejection"),
    ):
        with pytest.raises(DialogueSynthesisFailedError):
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="test",
                target_duration_seconds=60,
                mock_mode=False,  # deliberate — not mock; but no synth
            )


def test_ai_strict_k64_rejection_persists_warnings():
    """Strict K6.4 rejection is a synthesis-time failure. Starter
    catches ClaimVerifierError and raises DialogueSynthesisFailedError
    with the unsupported-claims payload preserved."""
    from character_os.claim_verifier import (
        ClaimVerifierError,
        UnsupportedClaim,
    )
    ws = _ws("ai_e4@t")
    p, r = _cast(ws)
    fake_synth = MagicMock(side_effect=ClaimVerifierError(
        unsupported=[
            UnsupportedClaim(claim="bogus fact", position=0, kind="year"),
        ],
        synthesized_text="Patch: bogus fact\nRivet: ok",
    ))
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        fake_synth,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="test",
                target_duration_seconds=60,
                verifier_mode="strict",
                mock_mode=True,
            )
    assert exc.value.verification_status == "rejected"
    assert len(exc.value.verification_warnings) == 1
    assert exc.value.verification_warnings[0]["claim"] == "bogus fact"
    assert "K6.4" in exc.value.reason


# ========================================================================
# F. COST REGRESSION
# ========================================================================


def test_ai_composition_cost_comes_from_avatar_speech_primitive_estimator():
    """SESSION 257 (46f5efd) — provider-truth cost lives on
    avatar_speech. AI mode must not introduce a dialogue-specific
    cost estimator; each generated turn's cost is the same
    flat-20_000-micros forecast (or provider-reported truth at
    execute time) that manual turns use."""
    ws = _ws("ai_f1@t")
    p, r = _cast(ws)
    result = _fake_dialogue_result(p, r, n_turns=6, total_chars=900)
    comp, _ = _run_ai_starter_with_fake_synth(ws, p, r, fake_result=result)

    # Sum step estimates should exactly equal N turns × 20_000
    # micros (avatar_speech estimator, SESSION 257) + 100 for the
    # single concat_clips (or 0 if degenerate). No AI-mode
    # multiplier or surcharge.
    from apps.compositions.primitives.avatar_speech import (
        _AVATAR_SPEECH_MICROS_PER_CALL,
    )
    expected_speech_cost = 6 * _AVATAR_SPEECH_MICROS_PER_CALL
    est = estimate_composition_cost(comp)
    # Allow for the +100 micros concat overhead.
    assert est in {expected_speech_cost, expected_speech_cost + 100}
