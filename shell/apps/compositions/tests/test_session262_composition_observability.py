"""SESSION 262 — Composition observability v1 behavioral tests.

Scope: `docs/design/COMPOSITION_OBSERVABILITY_V1.md` +
`docs/design/COMPOSITION_OBSERVABILITY_SCHEMA_V1.md` (implementation
report). Nine behavioral scenarios per the operator's brief:

  1. First-pass accepted synthesis populates provenance correctly.
  2. Corrective-pass accepted synthesis populates the full attempt log.
  3. Final synthesis rejection persists first-pass + corrective + hint
     + validation reason even when zero CompositionSteps exist.
  4. Retrieval-before-rejection: knowledge_chunk_ids carries the actual
     retrieved chunk IDs, not [].
  5. Pre-retrieval failure: knowledge_chunk_ids=[] remains correct.
  6. Duration provenance: target_duration + predicted_seconds preserved.
  7. Render dispatch: NULL when synthesis rejects before dispatch;
     populated when primitive dispatches; not erased after dispatch.
  8. Legacy behavior: non-synthesis / mock / operator-typed paths land
     with sensible defaults; no provenance invention.
  9. Immutability: observability fields cannot be silently overwritten;
     legitimate lifecycle writes (status / cost / verification / etc.)
     remain functional.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.starters import (
    DialogueSynthesisFailedError,
    dialogue_scene,
    talking_head,
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


# ---- fixtures ----------------------------------------------------


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


def _dialogue_result(
    primary: Teammate, secondary: Teammate, *,
    n_turns: int = 4,
    attempt_count: int = 1,
    first_pass_raw: str = '{"turns":[{"line_index":0,"speaker_alias":"patch","text":"first-pass content"}]}',
    corrective_hint: str = "",
    corrective_pass_raw: str = "",
) -> DialogueResult:
    turns: list[DialogueTurn] = []
    order = [primary, secondary, secondary, primary]
    while len(order) < n_turns:
        order.append(secondary if order[-1] is primary else primary)
    for i in range(n_turns):
        sp = order[i]
        alias = "patch" if sp is primary else "rivet"
        turns.append(DialogueTurn(
            line_index=i,
            speaker_teammate=sp,
            speaker_alias=alias,
            text=f"turn {i} by {alias}",
            verification_status="verified",
        ))
    total_chars = sum(len(t.text) for t in turns)
    return DialogueResult(
        turns=turns,
        chunk_ids=["chunk-a", "chunk-b"],
        per_character_chunk_ids={"patch": ["chunk-a"], "rivet": ["chunk-b"]},
        writing_contract_version=WRITING_CONTRACT_VERSION,
        overall_verification_status="verified",
        total_chars=total_chars,
        predicted_seconds=total_chars / 13,
        target_duration_seconds=60,
        aliases={"patch": primary.name, "rivet": secondary.name},
        mock_mode=False,
        used_knowledge=True,
        # Track the constant so future model migrations don't
        # require a test edit (SESSION 264 model swap lesson).
        model=DIALOGUE_MODEL,
        tokens_input=100,
        tokens_output=500,
        raw_llm_json=corrective_pass_raw or first_pass_raw,
        attempt_count=attempt_count,
        first_pass_raw=first_pass_raw,
        corrective_hint=corrective_hint,
        corrective_pass_raw=corrective_pass_raw,
    )


# ==================================================================
# 1. First-pass accepted synthesis
# ==================================================================


def test_first_pass_accepted_dialogue_persists_correct_provenance():
    """attempt_count=1, first_pass populated, corrective hint / pass
    remain empty, operator_topic verbatim."""
    ws = _ws("t1a@t")
    p, r = _cast(ws)
    result = _dialogue_result(p, r, attempt_count=1)
    topic = "Patch and Rivet debate the AI takeover"
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        return_value=result,
    ):
        comp = dialogue_scene(
            workspace=ws,
            primary_spokesperson=p,
            lines=[],  # will be hydrated from AI result
            dialogue_mode="ai_topic",
            secondary_spokesperson=r,
            topic=topic,
            target_duration_seconds=60,
            mock_mode=True,
        )
    comp.refresh_from_db()
    assert comp.operator_topic == topic
    assert comp.target_duration_seconds == 60
    assert comp.synthesis_attempt_count == 1
    assert comp.first_pass_synthesis == result.first_pass_raw
    assert comp.corrective_hint == ""
    assert comp.corrective_pass_synthesis == ""
    assert comp.validation_failure_reason == ""
    assert comp.synthesis_predicted_seconds == pytest.approx(
        result.predicted_seconds
    )
    # Existing behavior preserved.
    assert comp.status != CompositionStatus.FAILED
    assert comp.rejected_synthesis == ""


# ==================================================================
# 2. Corrective-pass accepted synthesis
# ==================================================================


def test_corrective_pass_accepted_dialogue_persists_full_attempt_log():
    """attempt_count=2, first_pass + corrective_hint + corrective_pass
    all populated; synthesized_brief remains the ACCEPTED output shape."""
    ws = _ws("t2a@t")
    p, r = _cast(ws)
    first_raw = '{"turns":[{"line_index":0,"speaker_alias":"patch","text":"too long draft"}]}'
    hint_used = "Your dialogue is too long. Compress to ~800 chars."
    corrective_raw = '{"turns":[{"line_index":0,"speaker_alias":"patch","text":"tighter"}]}'
    result = _dialogue_result(
        p, r,
        attempt_count=2,
        first_pass_raw=first_raw,
        corrective_hint=hint_used,
        corrective_pass_raw=corrective_raw,
    )
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        return_value=result,
    ):
        comp = dialogue_scene(
            workspace=ws,
            primary_spokesperson=p,
            lines=[],
            dialogue_mode="ai_topic",
            secondary_spokesperson=r,
            topic="another topic",
            target_duration_seconds=60,
            mock_mode=True,
        )
    comp.refresh_from_db()
    assert comp.synthesis_attempt_count == 2
    assert comp.first_pass_synthesis == first_raw
    assert comp.corrective_hint == hint_used
    assert comp.corrective_pass_synthesis == corrective_raw
    # synthesized_brief remains the human-readable ACCEPTED output;
    # it is the corrective-pass content in this case (via the
    # existing dialogue_scene starter's _dialogue_ai_synthesized_brief
    # helper). We just assert non-empty here — its exact shape is
    # covered by SESSION 257 tests.
    assert comp.synthesized_brief != ""


# ==================================================================
# 3. Final synthesis rejection
# ==================================================================


def test_final_synthesis_rejection_persists_full_attempt_log_and_no_steps():
    """After bounded corrective failed, DialogueSynthesisFailedError is
    raised; view/starter path creates a FAILED composition with zero
    CompositionSteps and full attempt-log provenance."""
    ws = _ws("t3a@t")
    p, r = _cast(ws)
    first_raw = '{"turns":[{"line_index":0,"speaker_alias":"patch","text":"attempt 1 too long"}]}'
    hint_used = "Compress please."
    corrective_raw = '{"turns":[{"line_index":0,"speaker_alias":"patch","text":"still too long attempt 2"}]}'
    err = DialogueSynthesisError(
        "dialogue synthesis rejected after one corrective pass: still over",
        raw_llm_json=corrective_raw,
        first_pass_raw=first_raw,
        corrective_hint=hint_used,
        corrective_pass_raw=corrective_raw,
        attempt_count=2,
        predicted_seconds=95.4,
        chunk_ids=["chunk-a", "chunk-b"],
    )
    topic = "Patch retries — persistent overshoot"
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        side_effect=err,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc_info:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                lines=[],
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic=topic,
                target_duration_seconds=60,
                mock_mode=False,  # exercise the real rejection path
            )
    # The starter itself hasn't persisted the composition yet — the
    # view is the rescue point in production. Simulate the view's
    # persistence path here.
    fex = exc_info.value
    assert fex.operator_topic == topic
    assert fex.target_duration_seconds == 60
    assert fex.first_pass_synthesis == first_raw
    assert fex.corrective_hint == hint_used
    assert fex.corrective_pass_synthesis == corrective_raw
    assert fex.synthesis_attempt_count == 2
    assert fex.synthesis_predicted_seconds == pytest.approx(95.4)
    assert fex.knowledge_chunk_ids == ["chunk-a", "chunk-b"]
    # The rescue itself:
    comp = Composition.objects.create(
        workspace=fex.workspace,
        spokesperson=fex.spokesperson,
        name=fex.composition_name,
        template_kind="dialogue_scene",
        mock_mode=fex.mock_mode,
        created_by=fex.created_by,
        status=CompositionStatus.FAILED,
        error_message=fex.error_message_text,
        rejected_synthesis=fex.rejected_synthesis,
        verification_warnings=fex.verification_warnings,
        verification_status=fex.verification_status,
        writing_contract_version=fex.writing_contract_version,
        knowledge_chunk_ids=fex.knowledge_chunk_ids,
        synthesized_brief=fex.synthesized_brief,
        operator_topic=fex.operator_topic,
        target_duration_seconds=fex.target_duration_seconds,
        synthesis_attempt_count=fex.synthesis_attempt_count,
        first_pass_synthesis=fex.first_pass_synthesis,
        corrective_hint=fex.corrective_hint,
        corrective_pass_synthesis=fex.corrective_pass_synthesis,
        synthesis_predicted_seconds=fex.synthesis_predicted_seconds,
        validation_failure_reason=fex.validation_failure_reason,
    )
    assert comp.status == CompositionStatus.FAILED
    # ZERO steps exist on this failed row.
    assert CompositionStep.objects.filter(composition=comp).count() == 0
    # rejected_synthesis retains its existing semantic (final rejected
    # output; here the corrective pass raw).
    assert comp.rejected_synthesis == corrective_raw
    # Full attempt log persisted.
    assert comp.first_pass_synthesis == first_raw
    assert comp.corrective_hint == hint_used
    assert comp.corrective_pass_synthesis == corrective_raw
    assert comp.synthesis_attempt_count == 2
    assert comp.validation_failure_reason.startswith("dialogue_synthesis:")


# ==================================================================
# 4. Retrieval-before-rejection
# ==================================================================


def test_retrieval_snapshot_survives_synthesis_rejection():
    """Blocker #4 fix: knowledge_chunk_ids populates non-empty when
    retrieval succeeded pre-rejection. Previously starters.py:3463
    passed knowledge_chunk_ids=[] unconditionally."""
    ws = _ws("t4a@t")
    p, r = _cast(ws)
    err = DialogueSynthesisError(
        "still too long",
        raw_llm_json="{}",
        first_pass_raw="{}",
        corrective_hint="tighten",
        corrective_pass_raw="{}",
        attempt_count=2,
        predicted_seconds=90.0,
        chunk_ids=["retrieved-a", "retrieved-b", "retrieved-c"],
    )
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        side_effect=err,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc_info:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                lines=[],
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="topic",
                target_duration_seconds=60,
                mock_mode=False,
            )
    # The exception carries the snapshot forward.
    assert exc_info.value.knowledge_chunk_ids == [
        "retrieved-a", "retrieved-b", "retrieved-c",
    ]


# ==================================================================
# 5. Pre-retrieval failure
# ==================================================================


def test_pre_retrieval_failure_keeps_chunk_ids_empty():
    """When retrieval never happened (e.g. missing OPENAI_API_KEY, cast
    validation, empty topic), knowledge_chunk_ids remains []. We
    signal this via chunk_ids=[] on the exception."""
    ws = _ws("t5a@t")
    p, r = _cast(ws)
    err = DialogueSynthesisError(
        "cast validation failed",
        raw_llm_json="",
        first_pass_raw="",
        corrective_hint="",
        corrective_pass_raw="",
        attempt_count=0,
        predicted_seconds=None,
        chunk_ids=[],
    )
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        side_effect=err,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc_info:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                lines=[],
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="topic",
                target_duration_seconds=60,
                mock_mode=False,
            )
    assert exc_info.value.knowledge_chunk_ids == []
    assert exc_info.value.synthesis_attempt_count == 0
    assert exc_info.value.synthesis_predicted_seconds is None


# ==================================================================
# 6. Duration provenance
# ==================================================================


def test_duration_provenance_target_and_predicted_persist():
    ws = _ws("t6a@t")
    p, r = _cast(ws)
    result = _dialogue_result(p, r, attempt_count=1)
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        return_value=result,
    ):
        comp = dialogue_scene(
            workspace=ws,
            primary_spokesperson=p,
            lines=[],
            dialogue_mode="ai_topic",
            secondary_spokesperson=r,
            topic="duration test",
            target_duration_seconds=60,
            mock_mode=True,
        )
    comp.refresh_from_db()
    assert comp.target_duration_seconds == 60
    assert comp.synthesis_predicted_seconds == pytest.approx(
        result.predicted_seconds
    )


# ==================================================================
# 7. Render dispatch
# ==================================================================


def test_render_dispatched_at_null_when_synthesis_fails_before_dispatch():
    """Dialogue AI-Topic rejection path: composition FAILED, no steps
    fired, render_dispatched_at MUST remain NULL."""
    ws = _ws("t7a@t")
    p, r = _cast(ws)
    err = DialogueSynthesisError(
        "rejected",
        raw_llm_json="{}",
        first_pass_raw="{}",
        corrective_hint="",
        corrective_pass_raw="",
        attempt_count=1,
        predicted_seconds=50.0,
        chunk_ids=[],
    )
    with patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        side_effect=err,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc_info:
            dialogue_scene(
                workspace=ws,
                primary_spokesperson=p,
                lines=[],
                dialogue_mode="ai_topic",
                secondary_spokesperson=r,
                topic="topic",
                target_duration_seconds=60,
                mock_mode=False,
            )
    fex = exc_info.value
    # Simulate the view rescue and confirm the row has NULL dispatch.
    comp = Composition.objects.create(
        workspace=fex.workspace,
        spokesperson=fex.spokesperson,
        name=fex.composition_name,
        template_kind="dialogue_scene",
        status=CompositionStatus.FAILED,
        error_message=fex.error_message_text,
        operator_topic=fex.operator_topic,
        target_duration_seconds=fex.target_duration_seconds,
        first_pass_synthesis=fex.first_pass_synthesis,
    )
    assert comp.render_dispatched_at is None


def test_render_dispatched_at_populated_by_primitive_dispatch():
    """A mock-mode talking-head composition runs the primitive
    dispatch path, which calls mark_render_dispatched()."""
    ws = _ws("t7b@t")
    sp = _tm(ws, "Solo")
    comp = talking_head(
        workspace=ws,
        spokesperson=sp,
        script="Hello world",
        use_knowledge=False,  # no in-primitive K6; direct dispatch
        mock_mode=True,
    )
    assert comp.render_dispatched_at is None
    # Manually execute the primitive to simulate runtime dispatch.
    step = comp.steps.first()
    from apps.compositions.primitives.avatar_speech import (
        GenerateAvatarSpeechPrimitive,
    )
    GenerateAvatarSpeechPrimitive.execute(
        step=step, resolved_inputs={}, mock_mode=True,
    )
    comp.refresh_from_db()
    assert comp.render_dispatched_at is not None


def test_render_dispatched_at_immutable_after_first_dispatch():
    """Second and subsequent primitives on the same composition must
    NOT overwrite render_dispatched_at."""
    ws = _ws("t7c@t")
    sp = _tm(ws, "Solo7c")
    comp = talking_head(
        workspace=ws, spokesperson=sp, script="hi",
        use_knowledge=False, mock_mode=True,
    )
    step = comp.steps.first()
    from apps.compositions.primitives.avatar_speech import (
        GenerateAvatarSpeechPrimitive,
    )
    GenerateAvatarSpeechPrimitive.execute(
        step=step, resolved_inputs={}, mock_mode=True,
    )
    comp.refresh_from_db()
    first_ts = comp.render_dispatched_at
    assert first_ts is not None
    # Fire again — helper is idempotent.
    comp.mark_render_dispatched()
    comp.refresh_from_db()
    assert comp.render_dispatched_at == first_ts


# ==================================================================
# 8. Legacy behavior
# ==================================================================


def test_operator_typed_script_leaves_topic_and_attempt_empty():
    """talking_head with use_knowledge=False (operator-typed script):
    operator_topic stays empty and attempt count stays 0 because no
    synthesis fires — the script IS the operator's exact words."""
    ws = _ws("t8a@t")
    sp = _tm(ws, "S8a")
    comp = talking_head(
        workspace=ws,
        spokesperson=sp,
        script="This is the exact script the operator typed.",
        use_knowledge=False,
        mock_mode=True,
    )
    assert comp.operator_topic == ""
    assert comp.synthesis_attempt_count == 0
    assert comp.first_pass_synthesis == ""
    assert comp.corrective_hint == ""
    assert comp.corrective_pass_synthesis == ""
    assert comp.target_duration_seconds is None
    assert comp.synthesis_predicted_seconds is None


def test_talking_head_use_knowledge_records_operator_topic_at_create():
    """When use_knowledge=True, operator_topic is stamped at
    composition-create (synthesis fires later in the primitive)."""
    ws = _ws("t8b@t")
    sp = _tm(ws, "S8b")
    topic_text = "Explain photosynthesis for first graders."
    comp = talking_head(
        workspace=ws,
        spokesperson=sp,
        script=topic_text,
        use_knowledge=True,
        target_duration_seconds=60,
        mock_mode=True,
    )
    assert comp.operator_topic == topic_text
    assert comp.target_duration_seconds == 60
    # Attempt fields are populated later by the primitive.
    assert comp.synthesis_attempt_count == 0
    assert comp.first_pass_synthesis == ""


# ==================================================================
# 9. Immutability
# ==================================================================


IMMUTABLE_FIELDS_AND_VALUES = [
    ("operator_topic", "first value", "second value"),
    ("target_duration_seconds", 60, 90),
    ("synthesis_attempt_count", 1, 2),
    ("first_pass_synthesis", "first draft", "different draft"),
    ("corrective_hint", "compress please", "expand please"),
    ("corrective_pass_synthesis", "tighter", "even tighter"),
    ("validation_failure_reason", "duration_contract:too_long", "k6_4:strict"),
    ("synthesis_predicted_seconds", 54.0, 71.0),
]


@pytest.mark.parametrize(
    "field,first,second",
    IMMUTABLE_FIELDS_AND_VALUES,
    ids=[t[0] for t in IMMUTABLE_FIELDS_AND_VALUES],
)
def test_immutable_field_cannot_be_silently_changed(field, first, second):
    ws = _ws(f"imm_{field}@t")
    sp = _tm(ws, f"tm_{field}")
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp,
        name=f"immutable-test-{field}",
        **{field: first},
    )
    # Reload from DB so from_db() snapshot fires.
    comp = Composition.objects.get(pk=comp.pk)
    setattr(comp, field, second)
    with pytest.raises(ValidationError) as exc:
        comp.save()
    assert field in str(exc.value)


def test_immutable_render_dispatched_at_cannot_be_silently_changed():
    from django.utils import timezone
    ws = _ws("imm_rda@t")
    sp = _tm(ws, "tm_rda")
    t1 = timezone.now()
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="imm-rda",
        render_dispatched_at=t1,
    )
    comp = Composition.objects.get(pk=comp.pk)
    comp.render_dispatched_at = timezone.now()
    with pytest.raises(ValidationError) as exc:
        comp.save()
    assert "render_dispatched_at" in str(exc.value)


def test_lifecycle_writes_remain_functional_after_provenance_persisted():
    """Normal status / final_asset / cost / verification / error_message
    updates must still work on a composition whose observability fields
    are already populated."""
    ws = _ws("lc@t")
    sp = _tm(ws, "lc-sp")
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="lc",
        operator_topic="fixed topic",
        target_duration_seconds=60,
        synthesis_attempt_count=1,
        first_pass_synthesis="first pass content",
        synthesis_predicted_seconds=45.0,
    )
    comp = Composition.objects.get(pk=comp.pk)
    # Every one of the following should NOT raise.
    comp.status = CompositionStatus.RUNNING
    comp.error_message = "temporary transient"
    comp.save(update_fields=["status", "error_message", "updated_at"])
    comp.status = CompositionStatus.COMPLETED
    comp.error_message = ""
    comp.cost_actual_micros = 12345
    comp.knowledge_chunk_ids = ["chunk-1", "chunk-2"]
    comp.verification_status = "verified"
    comp.verification_warnings = [{"claim": "x"}]
    comp.synthesized_brief = "final brief"
    comp.writing_contract_version = WRITING_CONTRACT_VERSION
    comp.save(update_fields=[
        "status", "error_message", "cost_actual_micros",
        "knowledge_chunk_ids", "verification_status",
        "verification_warnings", "synthesized_brief",
        "writing_contract_version", "updated_at",
    ])
    comp.refresh_from_db()
    # Immutable provenance still intact.
    assert comp.operator_topic == "fixed topic"
    assert comp.target_duration_seconds == 60
    assert comp.synthesis_attempt_count == 1
    assert comp.first_pass_synthesis == "first pass content"
    assert comp.synthesis_predicted_seconds == 45.0
    # Lifecycle fields updated correctly.
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.cost_actual_micros == 12345
    assert comp.verification_status == "verified"


def test_same_value_reassignment_is_a_noop_not_a_violation():
    """Writing the SAME persisted value must not raise; only DIFFERENT
    values should be rejected."""
    ws = _ws("sv@t")
    sp = _tm(ws, "sv-sp")
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="sv",
        operator_topic="unchanged",
        synthesis_attempt_count=1,
    )
    comp = Composition.objects.get(pk=comp.pk)
    comp.operator_topic = "unchanged"  # same value
    comp.save()  # should not raise
    comp.refresh_from_db()
    assert comp.operator_topic == "unchanged"


def test_empty_default_values_do_not_lock_the_field():
    """A row with the empty/default value for an immutable field must
    still accept its first real write."""
    ws = _ws("ed@t")
    sp = _tm(ws, "ed-sp")
    # Create without setting operator_topic (default "").
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="ed",
    )
    assert comp.operator_topic == ""
    # Reload + first real write should succeed.
    comp = Composition.objects.get(pk=comp.pk)
    comp.operator_topic = "first real value"
    comp.save()
    comp.refresh_from_db()
    assert comp.operator_topic == "first real value"
    # Second attempt to change must raise.
    comp = Composition.objects.get(pk=comp.pk)
    comp.operator_topic = "different"
    with pytest.raises(ValidationError):
        comp.save()
