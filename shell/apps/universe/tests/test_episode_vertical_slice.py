"""EPISODE_SCHEMA_V1 (SESSION 262) — vertical slice proof.

Per ``docs/design/EPISODE_SCHEMA_V1.md §Q20``. Patch/Rivet-style
fixture; no real provider calls. Simulates dialogue synthesis
failure then success via the same pattern as the SESSION 262
observability tests, then verifies the full architecture:

  Universe → Episode → cast → C1 (fail) → C2 (succeed)
    → Episode has both attempts
    → each Composition retains its own SESSION 262 observability
    → Episode.operator_topic unchanged across attempts
    → cross-Universe operations are rejected
"""
from __future__ import annotations

from unittest.mock import patch as mock_patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Composition, CompositionStatus
from apps.compositions.starters import (
    DialogueSynthesisFailedError,
    dialogue_scene,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe
from character_os.dialogue_synthesis import (
    DialogueResult,
    DialogueSynthesisError,
    DialogueTurn,
)
from character_os.writing_contract import WRITING_CONTRACT_VERSION

User = get_user_model()
# Vertical slice runs against a live DB (no transaction wrap) because
# it composes multiple pipeline steps that each open their own atomic
# blocks (dialogue_scene is decorated `@transaction.atomic`). Running
# under pytest-django's default transaction-wrapped mode risks the
# outer wrap being marked broken when a nested savepoint rolls back on
# DialogueSynthesisFailedError, which then blocks subsequent queries
# in the same test with `TransactionManagementError`.
pytestmark = pytest.mark.django_db(transaction=True)


def _make_valid_dialogue_result(primary, secondary):
    """Build an accepted DialogueResult mirroring the SESSION 262
    test fixture (attempt_count=1, first_pass populated)."""
    turns = [
        DialogueTurn(
            line_index=0, speaker_teammate=primary,
            speaker_alias="patch",
            text="Rivet — the AI took over the lab overnight.",
            verification_status="verified",
        ),
        DialogueTurn(
            line_index=1, speaker_teammate=secondary,
            speaker_alias="rivet",
            text="Once. It didn't. You forgot to close the loop.",
            verification_status="verified",
        ),
        DialogueTurn(
            line_index=2, speaker_teammate=primary,
            speaker_alias="patch",
            text="Well… okay, but the loop is basically an AI.",
            verification_status="verified",
        ),
        DialogueTurn(
            line_index=3, speaker_teammate=secondary,
            speaker_alias="rivet",
            text="Basically. Not actually. Run it again.",
            verification_status="verified",
        ),
    ]
    total = sum(len(t.text) for t in turns)
    return DialogueResult(
        turns=turns,
        chunk_ids=["chunk-patch-1", "chunk-rivet-1"],
        per_character_chunk_ids={
            "patch": ["chunk-patch-1"],
            "rivet": ["chunk-rivet-1"],
        },
        writing_contract_version=WRITING_CONTRACT_VERSION,
        overall_verification_status="verified",
        total_chars=total,
        predicted_seconds=total / 13,
        target_duration_seconds=60,
        aliases={"patch": "Patch", "rivet": "Rivet"},
        mock_mode=False,
        used_knowledge=True,
        model="gpt-5",
        tokens_input=200,
        tokens_output=600,
        raw_llm_json='{"turns":[{"line_index":0,"speaker_alias":"patch","text":"..."}]}',
        attempt_count=1,
        first_pass_raw='{"turns":[{"line_index":0,"speaker_alias":"patch","text":"..."}]}',
        corrective_hint="",
        corrective_pass_raw="",
    )


def test_vertical_slice_patch_rivet_ai_takeover():
    """End-to-end proof per EPISODE_SCHEMA_V1 §Q20.

    Zero provider calls (mock_mode + patched synthesis).
    Every assertion runs against DB state alone.
    """
    # ---- Setup: Workspace + Universe + cast Teammates ----
    owner = User.objects.create_user(
        email="vs-owner@test.local", password="x",
    )
    workspace = Workspace.objects.filter(owner=owner).first()
    if workspace is None:
        workspace = Workspace.objects.create(name="VS-WS", owner=owner)
    Membership.objects.get_or_create(
        user=owner, workspace=workspace,
        defaults={"role": Membership.Role.OWNER},
    )

    universe = Universe.objects.create(
        workspace=workspace, name="patch-rivet-workshop",
    )
    patch_tm = Teammate.objects.create(
        workspace=workspace, universe=universe, name="Patch",
        runway_avatar_id="av-patch",
        portrait_path="https://fake/patch.png",
        business_brief="Patch — workshop inventor.",
    )
    rivet_tm = Teammate.objects.create(
        workspace=workspace, universe=universe, name="Rivet",
        runway_avatar_id="av-rivet",
        portrait_path="https://fake/rivet.png",
        business_brief="Rivet — dry counter-weight.",
    )

    # ---- Step 4: Create Episode E1 ----
    story_topic = (
        "Rivet warns Patch the AI will fire the humans; Patch is skeptical."
    )
    e1 = Episode.objects.create(
        universe=universe,
        title="AI took over the lab",
        operator_topic=story_topic,
    )
    assert e1.pk is not None
    assert e1.archived_at is None
    assert e1.compositions.count() == 0

    # ---- Step 5: Add cast (Patch + Rivet) ----
    e1.cast.add(patch_tm)
    e1.cast.add(rivet_tm)
    assert e1.cast.count() == 2

    # ---- Step 6: Create Composition C1 under E1 with synthesis fail ----
    fail_raw_first = (
        '{"turns":[{"line_index":0,"speaker_alias":"patch",'
        '"text":"too long draft"}]}'
    )
    fail_hint = "Your dialogue is too long. Compress to ~800 chars."
    fail_raw_corr = (
        '{"turns":[{"line_index":0,"speaker_alias":"patch",'
        '"text":"still too long"}]}'
    )
    err = DialogueSynthesisError(
        "dialogue synthesis rejected after one corrective pass",
        raw_llm_json=fail_raw_corr,
        first_pass_raw=fail_raw_first,
        corrective_hint=fail_hint,
        corrective_pass_raw=fail_raw_corr,
        attempt_count=2,
        predicted_seconds=95.4,
        chunk_ids=["chunk-patch-1", "chunk-rivet-1"],
    )
    with mock_patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        side_effect=err,
    ):
        with pytest.raises(DialogueSynthesisFailedError) as exc_info:
            dialogue_scene(
                workspace=workspace,
                primary_spokesperson=patch_tm,
                lines=[],
                dialogue_mode="ai_topic",
                secondary_spokesperson=rivet_tm,
                topic=story_topic,
                target_duration_seconds=60,
                mock_mode=False,
                created_by=owner,
            )
    fex = exc_info.value
    # Simulate the view rescue: create the FAILED Composition WITH
    # Episode attachment (mirrors CompositionViewSet.create's rescue).
    c1 = Composition.objects.create(
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
        episode=e1,
    )

    # ---- Step 7: Verify C1 ----
    c1.refresh_from_db()
    assert c1.status == CompositionStatus.FAILED
    assert c1.episode_id == e1.pk
    assert c1.operator_topic == story_topic
    assert c1.first_pass_synthesis == fail_raw_first
    assert c1.corrective_hint == fail_hint
    assert c1.corrective_pass_synthesis == fail_raw_corr
    assert c1.synthesis_attempt_count == 2
    assert c1.synthesis_predicted_seconds == pytest.approx(95.4)
    assert c1.validation_failure_reason.startswith("dialogue_synthesis:")
    assert c1.render_dispatched_at is None  # never got past synthesis
    assert c1.steps.count() == 0

    # ---- Step 8: Create Composition C2 under E1; succeeds ----
    ok_result = _make_valid_dialogue_result(patch_tm, rivet_tm)
    with mock_patch(
        "character_os.dialogue_synthesis.synthesize_dialogue",
        return_value=ok_result,
    ):
        c2 = dialogue_scene(
            workspace=workspace,
            primary_spokesperson=patch_tm,
            lines=[],
            dialogue_mode="ai_topic",
            secondary_spokesperson=rivet_tm,
            topic=story_topic,
            target_duration_seconds=60,
            mock_mode=True,
            created_by=owner,
        )
    # Attach post-starter (mirrors what CompositionViewSet.create does).
    c2.episode = e1
    c2.full_clean()
    c2.save(update_fields=["episode", "updated_at"])
    c2.refresh_from_db()

    # ---- Step 9: Verify C2 ----
    assert c2.episode_id == e1.pk
    assert c2.operator_topic == story_topic
    assert c2.first_pass_synthesis == ok_result.first_pass_raw
    assert c2.synthesis_attempt_count == 1  # first-pass accepted
    assert c2.corrective_hint == ""  # no retry fired
    assert c2.corrective_pass_synthesis == ""
    assert c2.synthesized_brief != ""  # accepted synthesis text lives here
    assert c2.steps.count() > 0  # dialogue turns → speech steps + concat

    # ---- Step 10: Verify Episode E1 has both attempts ----
    e1.refresh_from_db()
    assert e1.compositions.count() == 2
    ids = {c.pk for c in e1.compositions.all()}
    assert c1.pk in ids and c2.pk in ids
    # C1 failed; C2 didn't.
    statuses = {c.status for c in e1.compositions.all()}
    assert CompositionStatus.FAILED in statuses
    # C2's status may be RUNNING/COMPLETED depending on eager mode;
    # what matters is FAILED is one of them.

    # ---- Step 11: Per-Composition provenance isolation ----
    # Both inherited operator_topic from E1 at create time.
    assert c1.operator_topic == e1.operator_topic
    assert c2.operator_topic == e1.operator_topic
    # But their first_pass content differs (rejected vs accepted).
    assert c1.first_pass_synthesis != c2.first_pass_synthesis

    # ---- Step 12: Episode story intent unchanged ----
    # Reload E1 and confirm nothing about it changed.
    e1_snapshot = {
        "title": e1.title,
        "operator_topic": e1.operator_topic,
        "archived_at": e1.archived_at,
    }
    e1.refresh_from_db()
    for k, v in e1_snapshot.items():
        assert getattr(e1, k) == v

    # ---- Step 13: Adversarial — Episode topic edit doesn't propagate ----
    e1.operator_topic = "COMPLETELY DIFFERENT STORY"
    e1.save(update_fields=["operator_topic", "updated_at"])
    c1.refresh_from_db()
    c2.refresh_from_db()
    assert c1.operator_topic == story_topic
    assert c2.operator_topic == story_topic

    # ---- Step 14: Adversarial — Composition observability immutable ----
    c1.operator_topic = "DIFFERENT"
    with pytest.raises(ValidationError):
        c1.save()

    # ---- Step 15: Cross-Universe safety ----
    bakery = Universe.objects.create(workspace=workspace, name="bakery")
    baker = Teammate.objects.create(
        workspace=workspace, universe=bakery, name="Baker",
        runway_avatar_id="av-baker",
        portrait_path="https://fake/baker.png",
        business_brief="Bakes.",
    )
    # Cross-Universe cast attach rejected.
    with pytest.raises(ValidationError):
        e1.cast.add(baker)
    # Cross-Universe Composition attach rejected via clean().
    bad_c = Composition(
        workspace=workspace, spokesperson=baker, name="Bad",
        episode=e1, operator_topic="p",
    )
    with pytest.raises(ValidationError):
        bad_c.full_clean()
