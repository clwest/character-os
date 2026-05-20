"""SESSION 194 V18 polish slice 2 — ``persist_smoke_asset`` tests.

The ``smoke_keyframes`` management command itself makes real Runway
calls (and refuses ``RUNWAY_FORCE_MOCK``), which makes the full
command path hard to integration-test without mocking httpx. The
testable surface is the ``persist_smoke_asset`` helper: pure DB
write, no network, exercises the same shape the command's
SUCCEEDED branch fires.

These tests verify the SESSION 184 calibration #4 fix
("smoke commands without --save-assets produce orphans") shipped:

* Helper writes an Asset with the right role + asset_type +
  source_spec + dimensions.
* Role is hard-coded to EXPERIMENT (matches the SESSION 185 A1
  backfill heuristic for smoke outputs — keeps them out of the
  A7 role-filtered backdrop picker).
* Workspace anchor honors the cross-workspace signal.
* The Asset surfaces in the Asset Library v1 list endpoint (A4)
  with role=experiment, exactly like the SESSION 184 manual-shell
  smoke UUIDs that were backfilled to EXPERIMENT.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.management.commands.smoke_keyframes import (
    persist_smoke_asset,
)
from apps.compositions.models import Asset, AssetRole, AssetType

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str, name: str = "WS") -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


# ---- shape tests ----------------------------------------------------


def test_persist_smoke_asset_creates_clip_row() -> None:
    ws = _make_workspace("smoke_clip@test")
    asset = persist_smoke_asset(
        workspace=ws,
        model="veo3.1_fast",
        output_url="https://cdn.runway/abc.mp4",
        task_id="task_xyz",
        prompt="cinematic camera move",
        duration_seconds=6,
        width=1280,
        height=720,
    )
    assert asset.asset_type == AssetType.CLIP
    assert asset.workspace_id == ws.pk
    assert asset.file_path == "https://cdn.runway/abc.mp4"
    assert asset.duration_ms == 6_000
    assert asset.width == 1280
    assert asset.height == 720
    assert asset.mime_type == "video/mp4"


def test_persist_smoke_asset_stamps_experiment_role() -> None:
    """Hard-coded role=EXPERIMENT — matches SESSION 185 A1 backfill
    heuristic. Keeps smoke outputs out of the A7 role-filtered
    backdrop picker (per SESSION 184 dogfood #6: re-using smoke
    outputs as backdrops drags drift into production renders)."""
    ws = _make_workspace("smoke_role@test")
    asset = persist_smoke_asset(
        workspace=ws,
        model="gen3a_turbo",
        output_url="https://cdn.runway/def.mp4",
        task_id="task_abc",
        prompt="ignored",
        duration_seconds=5,
        width=None,
        height=None,
    )
    assert asset.role == AssetRole.EXPERIMENT


def test_persist_smoke_asset_source_spec_includes_model_and_task() -> None:
    """source_spec carries enough to retrace the smoke. Operator
    can cross-reference task_id against Runway logs even after
    the asset lands in the UI."""
    ws = _make_workspace("smoke_spec@test")
    asset = persist_smoke_asset(
        workspace=ws,
        model="veo3.1_fast",
        output_url="https://cdn.runway/spec.mp4",
        task_id="task_spec",
        prompt="prompt text under test",
        duration_seconds=8,
        width=1280,
        height=720,
    )
    spec = asset.source_spec
    assert spec["primitive_kind"] == "smoke_keyframes"
    assert spec["model"] == "veo3.1_fast"
    assert spec["task_id"] == "task_spec"
    assert spec["prompt"] == "prompt text under test"
    assert spec["duration_seconds"] == 8


def test_persist_smoke_asset_handles_missing_dimensions() -> None:
    """Width/height aren't always available from the Runway poll
    response — gen3a_turbo notably returns dimensions but Veo may
    not. Helper accepts None gracefully so the call site doesn't
    have to fall back to defaults."""
    ws = _make_workspace("smoke_nodims@test")
    asset = persist_smoke_asset(
        workspace=ws,
        model="veo3.1_fast",
        output_url="https://cdn.runway/nodims.mp4",
        task_id="task_nodims",
        prompt="x",
        duration_seconds=6,
        width=None,
        height=None,
    )
    assert asset.width is None
    assert asset.height is None


def test_persist_smoke_asset_title_includes_model_name() -> None:
    """Title is operator-facing in the A5 list view — naming the
    smoke output by model means a glance at the Asset Library
    distinguishes a veo3.1_fast smoke from a gen3a_turbo smoke
    without opening detail."""
    ws = _make_workspace("smoke_title@test")
    asset = persist_smoke_asset(
        workspace=ws,
        model="gen3a_turbo",
        output_url="https://cdn.runway/title.mp4",
        task_id="t",
        prompt="x",
        duration_seconds=5,
        width=1280,
        height=768,
    )
    assert "gen3a_turbo" in asset.title
    assert "smoke" in asset.title.lower()


def test_persist_smoke_asset_workspace_filter_honors_isolation() -> None:
    """Two workspaces, two smoke outputs — each lands in its own
    workspace and the cross-workspace signal isn't violated."""
    ws_a = _make_workspace("smoke_iso_a@test", "A")
    ws_b = _make_workspace("smoke_iso_b@test", "B")
    asset_a = persist_smoke_asset(
        workspace=ws_a, model="veo3.1_fast",
        output_url="https://cdn.runway/a.mp4",
        task_id="t_a", prompt="a", duration_seconds=6,
        width=1280, height=720,
    )
    asset_b = persist_smoke_asset(
        workspace=ws_b, model="gen3a_turbo",
        output_url="https://cdn.runway/b.mp4",
        task_id="t_b", prompt="b", duration_seconds=5,
        width=1280, height=768,
    )
    # Each asset anchors to its own workspace.
    assert Asset.objects.filter(workspace=ws_a).count() == 1
    assert Asset.objects.filter(workspace=ws_b).count() == 1
    assert asset_a.workspace_id != asset_b.workspace_id
    # And the EXPERIMENT-role filter on a single workspace returns
    # only that workspace's smoke output — matches the A4 endpoint
    # surface A7 narrows.
    assert (
        Asset.objects.filter(
            workspace=ws_a,
            role=AssetRole.EXPERIMENT.value,
        ).count() == 1
    )
