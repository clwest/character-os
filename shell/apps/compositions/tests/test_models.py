"""V1 model + privacy tests for the composition layer.

Named in ``docs/design/VIDEO_COMPOSITION_V1.md`` §"How to
verify the composability guarantee" — these tests are the
load-bearing contract. Implementation can vary; the tests
cannot fail.

V1 covers two of the four verification tests (the other two
land in V2 + V6):

* ``test_step_rejects_cross_workspace_assets`` — contract
  rule 3, cross-workspace asset references are rejected by
  the signal + clean().
* ``test_composition_rejects_cross_workspace_spokesperson`` —
  contract rule 2, both anchors must agree on workspace.
* ``test_composition_rejects_cross_workspace_final_asset`` —
  same shape on the deliverable side.
* ``test_step_position_unique_within_composition`` — contract
  rule 5, linear ordering enforced by DB constraint.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStep,
    StepStatus,
)
from apps.spokespeople.models import Spokesperson
from django.contrib.auth import get_user_model

User = get_user_model()


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_spokesperson(ws: Workspace, name: str) -> Spokesperson:
    return Spokesperson.objects.create(workspace=ws, name=name)


def _make_asset(ws: Workspace, asset_type: str = AssetType.CLIP) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=asset_type,
        file_path=f"/fake/{asset_type}.bin",
    )


def _make_composition(ws: Workspace, sp: Spokesperson, name: str) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name=name,
    )


# ---- contract rule 3: cross-workspace asset references -------------


@pytest.mark.django_db
def test_step_rejects_cross_workspace_assets_via_signal() -> None:
    """The pre_save signal in apps.compositions.signals must
    veto step.save() when inputs reference an asset from
    another workspace. This is the DB-save path; the
    clean()-based defense is covered in the next test."""
    ws_a = _make_workspace("compA@test.local", "WS A")
    ws_b = _make_workspace("compB@test.local", "WS B")
    sp_a = _make_spokesperson(ws_a, "SP A")
    foreign_asset = _make_asset(ws_b)

    comp_a = _make_composition(ws_a, sp_a, "comp in A")

    step = CompositionStep(
        composition=comp_a,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[{"slot": "script", "asset_id": str(foreign_asset.pk)}],
        params={},
    )

    with pytest.raises(ValidationError):
        step.save()


@pytest.mark.django_db
def test_step_rejects_cross_workspace_assets_via_clean() -> None:
    """``CompositionStep.clean()`` is the form-flow validator.
    It must reject the same shape the signal rejects so
    operator-form validation surfaces the error early."""
    ws_a = _make_workspace("compA2@test.local", "WS A2")
    ws_b = _make_workspace("compB2@test.local", "WS B2")
    sp_a = _make_spokesperson(ws_a, "SP A2")
    foreign_asset = _make_asset(ws_b)
    comp_a = _make_composition(ws_a, sp_a, "comp 2")

    step = CompositionStep(
        composition=comp_a,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[{"slot": "script", "asset_id": str(foreign_asset.pk)}],
        params={},
    )

    with pytest.raises(ValidationError):
        step.clean()


@pytest.mark.django_db
def test_step_accepts_same_workspace_assets() -> None:
    """Sanity check the inverse — same-workspace asset
    references should pass through both gates cleanly."""
    ws = _make_workspace("compok@test.local", "OK WS")
    sp = _make_spokesperson(ws, "SP")
    same_workspace_asset = _make_asset(ws, asset_type=AssetType.TRANSCRIPT)

    comp = _make_composition(ws, sp, "ok comp")
    step = CompositionStep(
        composition=comp,
        position=0,
        primitive="generate_avatar_speech",
        inputs=[
            {"slot": "script", "asset_id": str(same_workspace_asset.pk)},
        ],
        params={},
    )

    step.clean()  # should not raise
    step.save()
    assert CompositionStep.objects.filter(pk=step.pk).exists()


@pytest.mark.django_db
def test_step_rejects_cross_workspace_output_asset() -> None:
    """The output_asset assignment path also can't cross
    workspaces — covers the executor's persist-output flow."""
    ws_a = _make_workspace("compoa@test.local", "WS OA")
    ws_b = _make_workspace("compob@test.local", "WS OB")
    sp_a = _make_spokesperson(ws_a, "SP OA")
    foreign_asset = _make_asset(ws_b)
    comp_a = _make_composition(ws_a, sp_a, "out comp")

    step = CompositionStep(
        composition=comp_a,
        position=0,
        primitive="composite_video",
        output_asset=foreign_asset,  # cross-workspace assignment
    )

    with pytest.raises(ValidationError):
        step.save()


# ---- contract rule 2: composition workspace + spokesperson -------


@pytest.mark.django_db
def test_composition_rejects_cross_workspace_spokesperson() -> None:
    """A Composition whose spokesperson is in a different
    workspace must fail ``full_clean()``."""
    ws_a = _make_workspace("compsa@test.local", "WS SA")
    ws_b = _make_workspace("compsb@test.local", "WS SB")
    foreign_sp = _make_spokesperson(ws_b, "Foreign SP")

    comp = Composition(
        workspace=ws_a,
        spokesperson=foreign_sp,
        name="bad comp",
    )

    with pytest.raises(ValidationError):
        comp.full_clean()


@pytest.mark.django_db
def test_composition_rejects_cross_workspace_final_asset() -> None:
    """A Composition whose ``final_asset`` is in a different
    workspace must fail ``full_clean()``."""
    ws_a = _make_workspace("compfa@test.local", "WS FA")
    ws_b = _make_workspace("compfb@test.local", "WS FB")
    sp_a = _make_spokesperson(ws_a, "SP FA")
    foreign_asset = _make_asset(ws_b)

    comp = Composition(
        workspace=ws_a,
        spokesperson=sp_a,
        name="bad final asset",
        final_asset=foreign_asset,
    )

    with pytest.raises(ValidationError):
        comp.full_clean()


# ---- contract rule 5: linear ordering ----------------------------


@pytest.mark.django_db
def test_step_position_unique_within_composition() -> None:
    """``UniqueConstraint(composition, position)`` enforces
    linear ordering — two steps cannot occupy the same slot
    inside the same composition."""
    ws = _make_workspace("compord@test.local", "Ord WS")
    sp = _make_spokesperson(ws, "Ord SP")
    comp = _make_composition(ws, sp, "ord comp")

    CompositionStep.objects.create(
        composition=comp, position=0, primitive="step_one",
    )
    with pytest.raises(IntegrityError):
        CompositionStep.objects.create(
            composition=comp, position=0, primitive="step_two_collides",
        )


@pytest.mark.django_db
def test_step_position_reusable_across_compositions() -> None:
    """Position 0 in composition A is independent of position
    0 in composition B — the unique constraint is per-
    composition, not global."""
    ws = _make_workspace("compord2@test.local", "Ord2 WS")
    sp = _make_spokesperson(ws, "Ord2 SP")
    comp_a = _make_composition(ws, sp, "A")
    comp_b = _make_composition(ws, sp, "B")

    CompositionStep.objects.create(
        composition=comp_a, position=0, primitive="x",
    )
    CompositionStep.objects.create(
        composition=comp_b, position=0, primitive="y",
    )
    assert CompositionStep.objects.count() == 2


# ---- smoke tests for the model shape -----------------------------


@pytest.mark.django_db
def test_asset_defaults() -> None:
    """Schema sanity — the fields that need defaults have
    them, the fields that don't are required."""
    ws = _make_workspace("assetdef@test.local", "AssetDef")
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
    )
    assert asset.file_path == ""
    assert asset.inline_content == ""
    assert asset.source_spec == {}
    assert asset.cost_micros == 0
    assert asset.composition is None
    assert asset.created_at is not None


@pytest.mark.django_db
def test_composition_defaults() -> None:
    ws = _make_workspace("compdef@test.local", "CompDef")
    sp = _make_spokesperson(ws, "DefSP")
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="defaults",
    )
    assert comp.status == "draft"
    assert comp.template_kind == ""
    assert comp.knowledge_chunk_ids == []
    assert comp.cost_estimate_micros == 0
    assert comp.cost_actual_micros == 0
    assert comp.mock_mode is False
    assert comp.final_asset is None


@pytest.mark.django_db
def test_step_defaults() -> None:
    ws = _make_workspace("stepdef@test.local", "StepDef")
    sp = _make_spokesperson(ws, "StepSP")
    comp = _make_composition(ws, sp, "step defaults")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="x",
    )
    assert step.status == StepStatus.PENDING
    assert step.inputs == []
    assert step.params == {}
    assert step.output_asset is None
    assert step.media_engine_task_id == ""


@pytest.mark.django_db
def test_step_referenced_asset_ids_extracts_valid_uuids() -> None:
    """``referenced_asset_ids`` is the helper the signal +
    clean() share; the test guards its parsing logic."""
    ws = _make_workspace("refids@test.local", "RefIDs WS")
    sp = _make_spokesperson(ws, "RefSP")
    a = _make_asset(ws)
    b = _make_asset(ws)
    comp = _make_composition(ws, sp, "refs")

    step = CompositionStep(
        composition=comp,
        position=0,
        primitive="composite_video",
        inputs=[
            {"slot": "background", "asset_id": str(a.pk)},
            {"slot": "foreground", "from_step_position": 0},  # no asset_id
            {"slot": "overlay", "asset_id": str(b.pk)},
            {"slot": "garbage", "asset_id": "not-a-uuid"},
            "not-a-dict",
        ],
    )
    ids = step.referenced_asset_ids()
    assert set(ids) == {a.pk, b.pk}
