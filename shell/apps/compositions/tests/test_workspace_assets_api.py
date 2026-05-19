"""Asset Library v1 (SESSION 188, A4) — `/api/workspace/assets/` endpoint tests.

The read endpoint A5/A6 will consume — paginated browse + per-asset
detail with full lineage. Filters (role / asset_type / primitive_kind /
storage / q / created_after / created_before) all live here.

Covered:

* Auth gate — unauthenticated → 401/403.
* Workspace scoping — non-member of a requested workspace → 403.
* Default-workspace fallback when ``?workspace=`` omitted.
* Cross-workspace leakage check — assets in other workspaces never
  appear regardless of filter shape.
* Pagination — default page_size, ``?page_size=`` override, ``?page=``
  navigation.
* Each filter individually — role, asset_type, primitive_kind, storage,
  q (full-text), created_after / created_before.
* ``storage_health`` attached to every list row (live computed via A3).
* ``producing_prompt`` falls back across source_spec / params keys.
* Retrieve happy path — every list field plus ``producing_step`` +
  ``downstream_compositions``.
* Retrieve lineage — downstream consumer compositions surface; the
  producing composition surfaces.
* Retrieve cross-workspace → 404 (Asset.DoesNotExist via scoped qs).
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.assets import StorageHealth
from apps.compositions.models import (
    Asset,
    AssetRole,
    AssetType,
    Composition,
    CompositionStep,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(ws: Workspace, name: str = "Sasha") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av_test",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_composition(
    ws: Workspace, sp: Spokesperson, *, name: str = "Test comp",
) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name=name,
        template_kind="talking_head",
    )


def _make_asset(
    ws: Workspace,
    *,
    asset_type: str = AssetType.CLIP,
    role: str = AssetRole.TALKING_HEAD.value,
    file_path: str = "https://cdn/x.mp4",
    primitive_kind: str = "generate_avatar_speech",
    composition: Composition | None = None,
    title: str = "",
    subject: str = "",
    source_spec_extra: dict | None = None,
) -> Asset:
    source_spec = {"primitive_kind": primitive_kind}
    if source_spec_extra:
        source_spec.update(source_spec_extra)
    return Asset.objects.create(
        workspace=ws,
        asset_type=asset_type,
        role=role,
        file_path=file_path,
        source_spec=source_spec,
        composition=composition,
        title=title,
        subject=subject,
    )


@pytest.fixture
def client_user() -> tuple[APIClient, Workspace, User]:
    ws, user = _make_workspace("a4@test.local")
    api = APIClient()
    api.force_authenticate(user=user)
    return api, ws, user


# ---- auth + scoping -------------------------------------------------


def test_unauthenticated_request_blocked() -> None:
    api = APIClient()
    url = reverse("workspace-asset-list")
    resp = api.get(url)
    assert resp.status_code in (http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN)


def test_default_workspace_used_when_not_specified(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp)
    resp = api.get(reverse("workspace-asset-list"))
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["count"] == 1


def test_non_member_cannot_query_other_workspace(client_user) -> None:
    api, _ws, _ = client_user
    other_ws, _ = _make_workspace("a4other@test.local", "Other")
    resp = api.get(
        reverse("workspace-asset-list"),
        {"workspace": str(other_ws.id)},
    )
    assert resp.status_code == http.HTTP_403_FORBIDDEN


def test_unknown_workspace_returns_404(client_user) -> None:
    api, _ws, _ = client_user
    resp = api.get(
        reverse("workspace-asset-list"),
        {"workspace": str(uuid.uuid4())},
    )
    assert resp.status_code == http.HTTP_404_NOT_FOUND


def test_cross_workspace_assets_not_listed(client_user) -> None:
    """Assets in another workspace never appear in this workspace's
    list, even with no filters."""
    api, ws, _ = client_user
    other_ws, _ = _make_workspace("a4xspace@test.local", "Other")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp, title="mine")
    other_sp = _make_spokesperson(other_ws, name="OtherSp")
    other_comp = _make_composition(other_ws, other_sp, name="other comp")
    _make_asset(other_ws, composition=other_comp, title="theirs")
    resp = api.get(reverse("workspace-asset-list"))
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["title"] == "mine"


# ---- list shape + storage_health -----------------------------------


def test_list_attaches_storage_health(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(
        ws,
        composition=comp,
        file_path="data:image/png;base64,iVBORw0KGgoAAA",
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE.value,
        primitive_kind="generate_image",
    )
    resp = api.get(reverse("workspace-asset-list"))
    assert resp.status_code == http.HTTP_200_OK
    row = resp.data["results"][0]
    assert row["storage_health"] == StorageHealth.DATA_URI


def test_list_attaches_producing_composition(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, name="Hero ad")
    _make_asset(ws, composition=comp, title="hero clip")
    resp = api.get(reverse("workspace-asset-list"))
    row = resp.data["results"][0]
    assert row["composition"]["name"] == "Hero ad"
    assert row["composition"]["status"] == comp.status
    assert row["composition"]["id"] == str(comp.id)


def test_list_producing_prompt_falls_through_to_params(client_user) -> None:
    """When primitive doesn't stash ``prompt`` at the top level of
    source_spec, the helper looks inside ``params`` — recipes that
    forward the operator's form data verbatim land it there."""
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(
        ws,
        composition=comp,
        source_spec_extra={"params": {"prompt": "donny in a meadow"}},
    )
    resp = api.get(reverse("workspace-asset-list"))
    row = resp.data["results"][0]
    assert row["producing_prompt"] == "donny in a meadow"


# ---- filters --------------------------------------------------------


def test_role_filter(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp, role=AssetRole.TALKING_HEAD.value)
    _make_asset(ws, composition=comp, role=AssetRole.BACKDROP.value)
    _make_asset(ws, composition=comp, role=AssetRole.COMPOSITE_OUTPUT.value)
    resp = api.get(
        reverse("workspace-asset-list"),
        {"role": "backdrop,composite_output"},
    )
    assert resp.data["count"] == 2
    roles = {r["role"] for r in resp.data["results"]}
    assert roles == {"backdrop", "composite_output"}


def test_asset_type_filter(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp, asset_type=AssetType.CLIP)
    _make_asset(ws, composition=comp, asset_type=AssetType.IMAGE)
    _make_asset(ws, composition=comp, asset_type=AssetType.AUDIO)
    resp = api.get(
        reverse("workspace-asset-list"),
        {"asset_type": "image,audio"},
    )
    assert resp.data["count"] == 2


def test_primitive_kind_filter(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp, primitive_kind="generate_avatar_speech")
    _make_asset(ws, composition=comp, primitive_kind="generate_visual_clip")
    _make_asset(ws, composition=comp, primitive_kind="composite_video")
    resp = api.get(
        reverse("workspace-asset-list"),
        {"primitive_kind": "composite_video"},
    )
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["primitive_kind"] == "composite_video"


def test_storage_filter_data_uri(client_user) -> None:
    """Storage filter runs post-query; verify it actually narrows to
    the requested computed state."""
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp, file_path="https://cdn/x.mp4")
    _make_asset(
        ws,
        composition=comp,
        file_path="data:image/png;base64,iVBOR",
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE.value,
        primitive_kind="generate_image",
    )
    resp = api.get(
        reverse("workspace-asset-list"),
        {"storage": StorageHealth.DATA_URI},
    )
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["storage_health"] == StorageHealth.DATA_URI


def test_storage_filter_with_unknown_state_returns_empty(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _make_asset(ws, composition=comp)
    resp = api.get(
        reverse("workspace-asset-list"),
        {"storage": "totally_made_up_state"},
    )
    assert resp.data["count"] == 0


def test_q_filter_matches_composition_name(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp_match = _make_composition(ws, sp, name="Riggs intro 1")
    comp_skip = _make_composition(ws, sp, name="Sasha cohost")
    _make_asset(ws, composition=comp_match, title="match")
    _make_asset(ws, composition=comp_skip, title="skip")
    resp = api.get(reverse("workspace-asset-list"), {"q": "riggs"})
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["title"] == "match"


def test_q_filter_matches_asset_title(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, name="Generic")
    _make_asset(ws, composition=comp, title="Maya beach shot")
    _make_asset(ws, composition=comp, title="Donny sunrise")
    resp = api.get(reverse("workspace-asset-list"), {"q": "beach"})
    assert resp.data["count"] == 1


def test_created_after_filter(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    old = _make_asset(ws, composition=comp, title="old")
    Asset.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=30),
    )
    _make_asset(ws, composition=comp, title="new")
    cutoff = (timezone.now() - timedelta(days=7)).date().isoformat()
    resp = api.get(reverse("workspace-asset-list"), {"created_after": cutoff})
    titles = {r["title"] for r in resp.data["results"]}
    assert titles == {"new"}


def test_created_before_filter(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    old = _make_asset(ws, composition=comp, title="old")
    Asset.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=30),
    )
    _make_asset(ws, composition=comp, title="new")
    cutoff = (timezone.now() - timedelta(days=7)).date().isoformat()
    resp = api.get(reverse("workspace-asset-list"), {"created_before": cutoff})
    titles = {r["title"] for r in resp.data["results"]}
    assert titles == {"old"}


# ---- pagination -----------------------------------------------------


def test_default_page_size_is_25(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    for i in range(30):
        _make_asset(ws, composition=comp, title=f"row-{i}")
    resp = api.get(reverse("workspace-asset-list"))
    assert resp.data["count"] == 30
    assert len(resp.data["results"]) == 25


def test_page_size_override_respected(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    for i in range(15):
        _make_asset(ws, composition=comp, title=f"row-{i}")
    resp = api.get(reverse("workspace-asset-list"), {"page_size": "5"})
    assert resp.data["count"] == 15
    assert len(resp.data["results"]) == 5


def test_page_navigation(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    for i in range(7):
        _make_asset(ws, composition=comp, title=f"row-{i}")
    resp_p1 = api.get(reverse("workspace-asset-list"), {"page_size": "3"})
    resp_p2 = api.get(
        reverse("workspace-asset-list"),
        {"page_size": "3", "page": "2"},
    )
    assert len(resp_p1.data["results"]) == 3
    assert len(resp_p2.data["results"]) == 3
    ids_p1 = {r["id"] for r in resp_p1.data["results"]}
    ids_p2 = {r["id"] for r in resp_p2.data["results"]}
    assert ids_p1.isdisjoint(ids_p2)


# ---- retrieve -------------------------------------------------------


def test_retrieve_returns_full_lineage_shape(client_user) -> None:
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, name="Producing comp")
    asset = _make_asset(ws, composition=comp, title="Detail target")
    step = CompositionStep.objects.create(
        composition=comp,
        position=0,
        primitive="generate_avatar_speech",
        params={"script": "hello world"},
        inputs=[],
        output_asset=asset,
    )
    resp = api.get(
        reverse("workspace-asset-detail", kwargs={"pk": asset.id}),
    )
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["id"] == str(asset.id)
    assert resp.data["composition"]["name"] == "Producing comp"
    ps = resp.data["producing_step"]
    assert ps["id"] == str(step.id)
    assert ps["primitive"] == "generate_avatar_speech"
    assert ps["position"] == 0
    assert resp.data["downstream_compositions"] == []


def test_retrieve_lists_downstream_consumers(client_user) -> None:
    """An asset that's referenced by another composition's step
    inputs surfaces in ``downstream_compositions`` of the source
    composition."""
    api, ws, _ = client_user
    sp = _make_spokesperson(ws)
    source_comp = _make_composition(ws, sp, name="Source comp")
    source_asset = _make_asset(
        ws,
        composition=source_comp,
        title="reused clip",
        role=AssetRole.BACKDROP.value,
    )
    CompositionStep.objects.create(
        composition=source_comp,
        position=0,
        primitive="generate_visual_clip",
        params={},
        inputs=[],
        output_asset=source_asset,
    )

    consumer_comp = _make_composition(ws, sp, name="Consumer comp")
    CompositionStep.objects.create(
        composition=consumer_comp,
        position=0,
        primitive="composite_video",
        params={},
        inputs=[{"slot": "base_clip", "asset_id": str(source_asset.id)}],
    )

    resp = api.get(
        reverse("workspace-asset-detail", kwargs={"pk": source_asset.id}),
    )
    assert resp.status_code == http.HTTP_200_OK
    downstream = resp.data["downstream_compositions"]
    assert len(downstream) == 1
    assert downstream[0]["id"] == str(consumer_comp.id)
    assert downstream[0]["name"] == "Consumer comp"


def test_retrieve_cross_workspace_returns_404(client_user) -> None:
    """An asset in another workspace can't be retrieved even by id —
    the scoped queryset filters it out before the .get() runs."""
    api, _ws, _ = client_user
    other_ws, _ = _make_workspace("a4retxs@test.local", "Other")
    other_sp = _make_spokesperson(other_ws, name="otherSp")
    other_comp = _make_composition(other_ws, other_sp)
    other_asset = _make_asset(other_ws, composition=other_comp)
    resp = api.get(
        reverse("workspace-asset-detail", kwargs={"pk": other_asset.id}),
    )
    assert resp.status_code == http.HTTP_404_NOT_FOUND


def test_retrieve_unknown_id_returns_404(client_user) -> None:
    api, _ws, _ = client_user
    resp = api.get(
        reverse("workspace-asset-detail", kwargs={"pk": uuid.uuid4()}),
    )
    assert resp.status_code == http.HTTP_404_NOT_FOUND
