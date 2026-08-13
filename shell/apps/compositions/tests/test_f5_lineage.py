"""F5 tests — ``GET /api/compositions/<id>/lineage/`` workspace fabric arc.

Two read-only shapes:

* ``derived_from`` — source compositions whose output assets
  this composition consumes as inputs. One hop (Q-f-5).
* ``used_by`` — downstream compositions that consume any asset
  this composition produced.

Both surfaces are workspace-scoped via the viewset queryset
+ the V1 cross-workspace signal that already prevents foreign
asset references.

Covered:

* Auth gate.
* Composition with no asset inputs → empty derived_from.
* Composition consuming a parent's asset → derived_from
  surfaces the parent.
* Producer composition → used_by surfaces downstream
  consumers; dedup when the same consumer references multiple
  outputs.
* Cross-workspace caller → 404 (the queryset already excludes
  it).
* Same-composition references via from_step_position are NOT
  treated as lineage (would be a self-loop).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _eager_celery():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace_with_user(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Sp", runway_avatar_id="av",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_composition(
    ws: Workspace, sp: Teammate, *, template_kind: str = "talking_head",
    name: str = "comp",
) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name=name,
        template_kind=template_kind, status=CompositionStatus.COMPLETED,
    )


def _make_asset(ws: Workspace, producer: Composition) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/clip.mp4", duration_ms=5000,
        mime_type="video/mp4",
        composition=producer,
    )


def _make_step(
    comp: Composition, *, primitive: str = "reformat_clip",
    inputs: list[dict] | None = None,
    position: int = 0,
) -> CompositionStep:
    return CompositionStep.objects.create(
        composition=comp, position=position, primitive=primitive,
        inputs=inputs or [], params={},
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- auth + scoping -----------------------------------------------


def test_lineage_requires_auth() -> None:
    ws, user = _make_workspace_with_user("f5auth@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    client = APIClient()  # not logged in
    response = client.get(f"/api/compositions/{comp.pk}/lineage/")
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_lineage_404_for_cross_workspace_caller() -> None:
    ws_a, _user_a = _make_workspace_with_user("f5xa@test", "A")
    _ws_b, user_b = _make_workspace_with_user("f5xb@test", "B")
    sp_a = _make_teammate(ws_a)
    comp = _make_composition(ws_a, sp_a)
    client = APIClient()
    _login(client, user_b)
    response = client.get(f"/api/compositions/{comp.pk}/lineage/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- derived_from shape -------------------------------------------


def test_lineage_empty_for_standalone_composition() -> None:
    ws, user = _make_workspace_with_user("f5alone@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{comp.pk}/lineage/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["derived_from"] == []
    assert data["used_by"] == []
    assert data["composition_id"] == str(comp.id)


def test_lineage_derived_from_surfaces_parent_composition() -> None:
    """Layout recipes consume a CLIP from a prior render.
    Lineage shows the producer."""
    ws, user = _make_workspace_with_user("f5deriv@test")
    sp = _make_teammate(ws)
    parent = _make_composition(
        ws, sp, template_kind="talking_head", name="Parent",
    )
    parent_clip = _make_asset(ws, parent)

    child = _make_composition(
        ws, sp, template_kind="reels_format", name="Child",
    )
    _make_step(child, inputs=[
        {"slot": "base", "asset_id": str(parent_clip.id)},
    ])

    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{child.pk}/lineage/")
    data = response.json()
    assert len(data["derived_from"]) == 1
    entry = data["derived_from"][0]
    assert entry["composition_id"] == str(parent.id)
    assert entry["composition_name"] == "Parent"
    assert entry["template_kind"] == "talking_head"
    assert entry["asset_id"] == str(parent_clip.id)


def test_lineage_dedups_multiple_assets_from_same_parent() -> None:
    """Compositing two assets from the same parent shows
    that parent once."""
    ws, user = _make_workspace_with_user("f5dedupderiv@test")
    sp = _make_teammate(ws)
    parent = _make_composition(ws, sp, name="Parent")
    a1 = _make_asset(ws, parent)
    a2 = _make_asset(ws, parent)

    child = _make_composition(ws, sp, template_kind="pip_layout", name="Child")
    _make_step(child, inputs=[
        {"slot": "base", "asset_id": str(a1.id)},
        {"slot": "pip", "asset_id": str(a2.id)},
    ])
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{child.pk}/lineage/")
    data = response.json()
    assert len(data["derived_from"]) == 1
    assert data["derived_from"][0]["composition_id"] == str(parent.id)


def test_lineage_from_step_position_is_not_lineage() -> None:
    """Same-composition references via from_step_position are
    internal plumbing, not derived_from."""
    ws, user = _make_workspace_with_user("f5fromstep@test")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="storyboard_ad")
    _make_step(comp, position=0, primitive="generate_image", inputs=[])
    _make_step(
        comp, position=1, primitive="generate_visual_clip",
        inputs=[{"slot": "reference_image", "from_step_position": 0}],
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{comp.pk}/lineage/")
    assert response.json()["derived_from"] == []


# ---- used_by shape ------------------------------------------------


def test_lineage_used_by_surfaces_downstream_consumer() -> None:
    """A producer composition's lineage shows the consumers
    of its outputs."""
    ws, user = _make_workspace_with_user("f5usedby@test")
    sp = _make_teammate(ws)
    producer = _make_composition(ws, sp, name="Producer")
    asset = _make_asset(ws, producer)

    consumer = _make_composition(
        ws, sp, template_kind="reels_format", name="Consumer",
    )
    _make_step(consumer, inputs=[
        {"slot": "base", "asset_id": str(asset.id)},
    ])

    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{producer.pk}/lineage/")
    data = response.json()
    assert len(data["used_by"]) == 1
    assert data["used_by"][0]["composition_id"] == str(consumer.id)
    assert data["used_by"][0]["template_kind"] == "reels_format"


def test_lineage_used_by_dedups_multi_input_consumers() -> None:
    """Consumer using two of the producer's outputs is listed
    once (not twice per asset)."""
    ws, user = _make_workspace_with_user("f5usedbydedup@test")
    sp = _make_teammate(ws)
    producer = _make_composition(ws, sp, name="Producer")
    a1 = _make_asset(ws, producer)
    a2 = _make_asset(ws, producer)
    consumer = _make_composition(ws, sp, template_kind="pip_layout", name="Consumer")
    _make_step(consumer, inputs=[
        {"slot": "base", "asset_id": str(a1.id)},
        {"slot": "pip", "asset_id": str(a2.id)},
    ])
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{producer.pk}/lineage/")
    data = response.json()
    assert len(data["used_by"]) == 1


def test_lineage_used_by_finds_multiple_consumers() -> None:
    ws, user = _make_workspace_with_user("f5multi@test")
    sp = _make_teammate(ws)
    producer = _make_composition(ws, sp, name="Producer")
    asset = _make_asset(ws, producer)
    consumer_a = _make_composition(ws, sp, template_kind="reels_format", name="A")
    consumer_b = _make_composition(ws, sp, template_kind="style_remix_pass", name="B")
    _make_step(consumer_a, inputs=[{"slot": "base", "asset_id": str(asset.id)}])
    _make_step(consumer_b, inputs=[{"slot": "source", "asset_id": str(asset.id)}])
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{producer.pk}/lineage/")
    data = response.json()
    names = {entry["composition_name"] for entry in data["used_by"]}
    assert names == {"A", "B"}


def test_lineage_used_by_isolated_per_workspace() -> None:
    """A consumer in another workspace cannot see this
    producer's output (the V1 cross-workspace signal would
    have blocked the asset reference; the lineage query
    additionally filters by workspace as defense in
    depth)."""
    ws_a, user_a = _make_workspace_with_user("f5wsa@test", "A")
    _ws_b, _user_b = _make_workspace_with_user("f5wsb@test", "B")
    sp_a = _make_teammate(ws_a)
    producer = _make_composition(ws_a, sp_a, name="A-producer")
    # No consumer exists; just confirm the producer's used_by
    # is empty and we don't accidentally pick up anything from
    # workspace B's data.
    _ = _make_asset(ws_a, producer)
    client = APIClient()
    _login(client, user_a)
    response = client.get(f"/api/compositions/{producer.pk}/lineage/")
    assert response.json()["used_by"] == []
