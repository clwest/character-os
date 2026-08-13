"""SESSION 210 — `_aggregate_knowledge_chunk_ids` tests.

Closes the SESSION 209 calibration finding: every
`use_knowledge=True` render not anchored in a Script-row
lineage was writing chunks to the final Asset's
`source_spec.knowledge_chunk_ids` but never aggregating to
``Composition.knowledge_chunk_ids``. SPA citation surfaces
(F-arc brief-mode panel, BC4 lineage, verifier panel) fail
for single-step renders without this aggregation.

The aggregator at ``apps.compositions.tasks._aggregate_knowledge_chunk_ids``
runs at composition completion. Covers:

* Single-step recipe — chunks lift from asset to composition.
* Multi-step recipe — chunks aggregated from every step's
  produced asset.
* BC2 Script-lineage path preserved — existing
  ``composition.knowledge_chunk_ids`` carries forward.
* No-knowledge composition stays empty.
* Dedup across assets — same chunk_id in multiple step
  outputs only appears once.
* Stable ordering — existing entries keep their order;
  newly-discovered ids are appended sorted.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStep,
)
from apps.compositions.tasks import _aggregate_knowledge_chunk_ids
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str = "agg@test") -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(workspace=ws, name="Sp")


def _make_composition(ws: Workspace, sp: Teammate) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="test",
        mock_mode=True,
    )


def _add_step(comp: Composition, position: int = 0) -> CompositionStep:
    return CompositionStep.objects.create(
        composition=comp,
        position=position,
        primitive="generate_avatar_speech",
        inputs=[],
        params={},
    )


def _add_produced_asset(
    comp: Composition,
    step: CompositionStep,
    chunk_ids: list[str] | None = None,
) -> Asset:
    source_spec: dict = {
        "primitive_kind": "generate_avatar_speech",
        "used_knowledge": bool(chunk_ids),
    }
    if chunk_ids:
        source_spec["knowledge_chunk_ids"] = chunk_ids
    asset = Asset.objects.create(
        workspace=comp.workspace,
        composition=comp,
        asset_type=AssetType.CLIP,
        file_path=f"mock://{uuid4()}.mp4",
        cost_micros=0,
        source_spec=source_spec,
    )
    step.output_asset = asset
    step.save(update_fields=["output_asset"])
    return asset


# ---- tests ----------------------------------------------------------


def test_single_step_chunks_lift_to_composition() -> None:
    """talking_head with use_knowledge=True path. Single
    avatar_speech step writes chunks to its asset's
    source_spec; aggregator lifts them to the composition."""
    ws = _make_workspace("agg-single@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp)
    _add_produced_asset(comp, step, chunk_ids=["chunk-a", "chunk-b"])

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is True
    assert sorted(comp.knowledge_chunk_ids) == ["chunk-a", "chunk-b"]


def test_multi_step_chunks_aggregated_and_deduped() -> None:
    """long_form_ad pattern. Multiple speech steps each carry
    chunks in their asset's source_spec; aggregator unions
    and dedupes across steps."""
    ws = _make_workspace("agg-multi@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    s0 = _add_step(comp, position=0)
    s1 = _add_step(comp, position=1)
    s2 = _add_step(comp, position=2)
    _add_produced_asset(comp, s0, chunk_ids=["c1", "c2"])
    _add_produced_asset(comp, s1, chunk_ids=["c2", "c3"])  # c2 duplicate
    _add_produced_asset(comp, s2, chunk_ids=["c4"])

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is True
    assert sorted(comp.knowledge_chunk_ids) == ["c1", "c2", "c3", "c4"]


def test_bc2_script_lineage_existing_chunks_preserved() -> None:
    """BC2 path (starters.py:252) writes chunks at composition
    create time from a Script-row lineage source. The
    aggregator must preserve those entries verbatim, in
    original order, when assets contribute additional chunks."""
    ws = _make_workspace("agg-bc2@test")
    sp = _make_teammate(ws)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="bc2",
        mock_mode=True,
        knowledge_chunk_ids=["bc2-existing-a", "bc2-existing-b"],
    )
    step = _add_step(comp)
    _add_produced_asset(comp, step, chunk_ids=["asset-new-c"])

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is True
    # Existing entries first, in original order; new entry appended.
    assert comp.knowledge_chunk_ids == [
        "bc2-existing-a",
        "bc2-existing-b",
        "asset-new-c",
    ]


def test_bc2_existing_chunks_only_no_assets_returns_unchanged() -> None:
    """BC2-only composition (Script lineage with no
    knowledge-using steps). knowledge_chunk_ids already
    populated; no asset chunks to add. Returns False; field
    stays as-is."""
    ws = _make_workspace("agg-bc2-nochg@test")
    sp = _make_teammate(ws)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="bc2-no-add",
        mock_mode=True,
        knowledge_chunk_ids=["bc2-x", "bc2-y"],
    )
    step = _add_step(comp)
    _add_produced_asset(comp, step, chunk_ids=None)  # no knowledge

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is False
    assert comp.knowledge_chunk_ids == ["bc2-x", "bc2-y"]


def test_no_knowledge_composition_stays_empty() -> None:
    """talking_head with use_knowledge=False. No chunks
    anywhere; aggregator is a no-op."""
    ws = _make_workspace("agg-empty@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp)
    _add_produced_asset(comp, step, chunk_ids=None)

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is False
    assert comp.knowledge_chunk_ids == []


def test_dedupes_across_existing_and_assets() -> None:
    """Existing entries (BC2 path) that ALSO appear in
    asset source_spec must not be re-appended."""
    ws = _make_workspace("agg-dedup@test")
    sp = _make_teammate(ws)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="dedup",
        mock_mode=True,
        knowledge_chunk_ids=["shared-x", "bc2-only-y"],
    )
    step = _add_step(comp)
    _add_produced_asset(
        comp, step, chunk_ids=["shared-x", "asset-only-z"],
    )

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is True
    assert comp.knowledge_chunk_ids == [
        "shared-x",
        "bc2-only-y",
        "asset-only-z",
    ]


def test_composition_with_no_produced_assets() -> None:
    """Edge case — composition completes with no produced
    assets (degenerate; shouldn't happen in production but
    aggregator must not crash)."""
    ws = _make_workspace("agg-noassets@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is False
    assert comp.knowledge_chunk_ids == []


def test_handles_missing_source_spec_key() -> None:
    """Asset with source_spec dict but no `knowledge_chunk_ids`
    key — common case for assets produced by primitives that
    don't ground (composite_video, mix_audio, etc.)."""
    ws = _make_workspace("agg-nokey@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp)
    asset = Asset.objects.create(
        workspace=ws,
        composition=comp,
        asset_type=AssetType.CLIP,
        file_path="mock://no-knowledge.mp4",
        cost_micros=0,
        source_spec={"primitive_kind": "composite_video"},
    )
    step.output_asset = asset
    step.save(update_fields=["output_asset"])

    changed = _aggregate_knowledge_chunk_ids(comp)

    assert changed is False
    assert comp.knowledge_chunk_ids == []
