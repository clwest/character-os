"""V15.0 tests — recipe gallery + composition REST surface.

Covers:

* ``GET /api/recipes/`` — lists all 17 recipes with valid metadata.
* ``GET /api/recipes/<kind>/`` — single recipe detail.
* Recipe registry consistency — every recipe.starter is the matching
  function from ``apps.compositions.starters``.
* ``POST /api/compositions/`` — happy path for talking_head
  (simplest single-step recipe).
* ``POST /api/compositions/`` — happy path for an asset-input recipe
  (reels_format) — confirms workspace-scoped Asset resolution.
* ``POST /api/compositions/`` — happy path for dialogue_scene
  (exercises the custom resolver).
* ``POST /api/compositions/`` — workspace isolation: cross-workspace
  spokesperson_id raises 400.
* ``POST /api/compositions/`` — workspace isolation: cross-workspace
  asset_id raises 400.
* ``POST /api/compositions/`` — workspace membership: non-member 403.
* ``POST /api/compositions/`` — non-owner role 403 in v1.
* ``POST /api/compositions/`` — unknown kind 400.
* ``GET /api/compositions/<id>/`` — retrieve includes steps + final asset.
* ``GET /api/compositions/<id>/`` — cross-workspace caller 404.
* ``GET /api/compositions/`` — list scoped to caller's workspaces.
* Unauthenticated → 403/401 on all endpoints.

Celery runs eagerly so ``execute_composition.delay()`` actually
runs the composition in-process and the final_asset is populated
on the response.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
)
from apps.compositions.recipes import RECIPES, list_recipes
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _eager_celery():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


# ---- helpers ------------------------------------------------------


def _make_workspace_with_user(email: str, ws_name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = ws_name
    ws.save()
    return ws, user


def _make_spokesperson(
    ws: Workspace, name: str = "Sp", avatar_id: str = "fake-avatar"
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=avatar_id,
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_clip(
    ws: Workspace, file_path: str = "/data/_assets/clip.mp4"
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path=file_path, duration_ms=5000, mime_type="video/mp4",
    )


def _make_audio(ws: Workspace) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/a.mp3", duration_ms=5000, mime_type="audio/mpeg",
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- registry shape ----------------------------------------------


def test_recipe_registry_has_twenty_entries() -> None:
    """V15.4 added ``storyboard_voiced`` (was deferred from V13
    until V14 shipped ``audio_extract``), bringing the gallery
    to 18 starter compositions. V17.2 (SESSION 182) added
    ``cinematic_visual_extended`` (the second post-close
    recipe, extends V4's cinematic_visual via V17.1's
    extend_visual_clip primitive), bringing the count to 19.
    B-2 / B2.4 (SESSION 206) added ``auto_script`` (the
    operator-facing surface for rendering a pre-drafted,
    knowledge-grounded Script row), bringing the count to 20.
    """
    assert len(RECIPES) == 20


def test_every_recipe_has_required_metadata() -> None:
    for recipe in RECIPES.values():
        assert recipe.kind, f"{recipe} missing kind"
        assert recipe.display_name, f"{recipe.kind} missing display_name"
        assert recipe.family, f"{recipe.kind} missing family"
        assert recipe.description, f"{recipe.kind} missing description"
        assert recipe.fields, f"{recipe.kind} has no fields"
        assert recipe.starter is not None, f"{recipe.kind} has no starter"


def test_every_recipe_kind_matches_starter_name() -> None:
    from apps.compositions import starters
    for recipe in RECIPES.values():
        starter_attr = getattr(starters, recipe.kind, None)
        assert starter_attr is recipe.starter, (
            f"recipe {recipe.kind!r}'s starter doesn't match "
            f"starters.{recipe.kind}"
        )


def test_recipe_field_types_use_allowed_vocab() -> None:
    allowed = {
        "text", "textarea", "checkbox", "select", "number",
        "spokesperson_picker", "asset_picker", "script_picker",
        "dialogue_lines",
    }
    for recipe in RECIPES.values():
        for f in recipe.fields:
            assert f.type in allowed, (
                f"recipe {recipe.kind!r} field {f.name!r}: "
                f"unknown type {f.type!r}"
            )


def test_recipe_select_fields_have_choices() -> None:
    for recipe in RECIPES.values():
        for f in recipe.fields:
            if f.type == "select":
                assert f.choices, f"{recipe.kind}.{f.name} select missing choices"


def test_recipe_asset_picker_fields_have_asset_type() -> None:
    for recipe in RECIPES.values():
        for f in recipe.fields:
            if f.type == "asset_picker":
                assert f.asset_type, (
                    f"{recipe.kind}.{f.name} asset_picker missing asset_type"
                )


# ---- GET /api/recipes/ -------------------------------------------


def test_get_recipes_returns_all_twenty() -> None:
    """V17.2 (SESSION 182) added ``cinematic_visual_extended``,
    bringing the gallery from 18 to 19. B-2 / B2.4 (SESSION
    206) added ``auto_script``, bringing the count to 20.
    """
    ws, user = _make_workspace_with_user("v15list@test")
    client = APIClient()
    _login(client, user)
    response = client.get("/api/recipes/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert len(data) == 20


def test_get_recipes_requires_auth() -> None:
    client = APIClient()
    response = client.get("/api/recipes/")
    assert response.status_code in {http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN}


def test_get_recipe_detail_by_kind() -> None:
    ws, user = _make_workspace_with_user("v15detail@test")
    client = APIClient()
    _login(client, user)
    response = client.get("/api/recipes/talking_head/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["kind"] == "talking_head"
    assert data["family"] == "talking_head"
    field_names = {f["name"] for f in data["fields"]}
    assert "spokesperson_id" in field_names
    assert "script" in field_names


def test_get_recipe_unknown_kind_404() -> None:
    ws, user = _make_workspace_with_user("v15unknown@test")
    client = APIClient()
    _login(client, user)
    response = client.get("/api/recipes/no_such_recipe/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- POST /api/compositions/ — happy paths -----------------------


def test_create_talking_head_composition_runs_end_to_end() -> None:
    ws, user = _make_workspace_with_user("v15th@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": "Welcome to our channel. Today we explore something new.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "talking_head"
    assert data["status"] == CompositionStatus.COMPLETED
    assert data["final_asset"] is not None
    assert data["final_asset"]["asset_type"] == AssetType.CLIP
    assert len(data["steps"]) == 1


def test_create_reels_format_resolves_workspace_asset() -> None:
    ws, user = _make_workspace_with_user("v15reels@test")
    sp = _make_spokesperson(ws)
    base = _make_clip(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "reels_format",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "base_clip_id": str(base.pk),
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "reels_format"
    assert data["status"] == CompositionStatus.COMPLETED


def test_create_dialogue_scene_uses_custom_resolver() -> None:
    ws, user = _make_workspace_with_user("v15dlg@test")
    sp_a = _make_spokesperson(ws, name="A", avatar_id="av_a")
    sp_b = _make_spokesperson(ws, name="B", avatar_id="av_b")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "dialogue_scene",
            "workspace": str(ws.pk),
            "params": {
                "primary_spokesperson_id": str(sp_a.pk),
                "lines": [
                    {"spokesperson_id": str(sp_a.pk), "text": "Line one"},
                    {"spokesperson_id": str(sp_b.pk), "text": "Line two"},
                ],
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "dialogue_scene"
    # 2 speech steps + 1 concat
    assert len(data["steps"]) == 3
    assert data["status"] == CompositionStatus.COMPLETED


# ---- POST /api/compositions/ — failure paths ---------------------


def test_create_rejects_unknown_kind() -> None:
    ws, user = _make_workspace_with_user("v15unk@test")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/compositions/",
        {"kind": "no_such", "workspace": str(ws.pk), "params": {}},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_missing_kind() -> None:
    ws, user = _make_workspace_with_user("v15nokind@test")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/compositions/",
        {"workspace": str(ws.pk), "params": {}},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_cross_workspace_spokesperson() -> None:
    ws_a, user_a = _make_workspace_with_user("v15xspa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("v15xspb@test", "B")
    foreign_sp = _make_spokesperson(ws_b)
    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws_a.pk),
            "params": {
                "spokesperson_id": str(foreign_sp.pk),
                "script": "some script content here",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_cross_workspace_asset() -> None:
    ws_a, user_a = _make_workspace_with_user("v15xasa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("v15xasb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign_clip = _make_clip(ws_b)
    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "reels_format",
            "workspace": str(ws_a.pk),
            "params": {
                "spokesperson_id": str(sp_a.pk),
                "base_clip_id": str(foreign_clip.pk),
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_non_member() -> None:
    ws_a, _user_a = _make_workspace_with_user("v15nmema@test", "A")
    _ws_b, user_b = _make_workspace_with_user("v15nmemb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    client = APIClient()
    _login(client, user_b)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws_a.pk),
            "params": {
                "spokesperson_id": str(sp_a.pk),
                "script": "trying to render in foreign workspace",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_403_FORBIDDEN


def test_create_rejects_non_owner_role() -> None:
    ws, owner = _make_workspace_with_user("v15roleown@test")
    sp = _make_spokesperson(ws)
    editor = User.objects.create_user(email="editor@test", password="x")
    Membership.objects.create(
        user=editor, workspace=ws, role=Membership.Role.EDITOR,
    )
    client = APIClient()
    _login(client, editor)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": "editors cannot create comps in v1",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_403_FORBIDDEN


def test_create_rejects_missing_required_field() -> None:
    ws, user = _make_workspace_with_user("v15missingfield@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    # talking_head requires script — omit it.
    response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_unauthenticated_rejected() -> None:
    client = APIClient()
    response = client.post(
        "/api/compositions/",
        {"kind": "talking_head", "workspace": "x", "params": {}},
        format="json",
    )
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


# ---- GET /api/compositions/ + retrieve ---------------------------


def test_retrieve_composition_includes_steps_and_final_asset() -> None:
    ws, user = _make_workspace_with_user("v15ret@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    create_response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": "retrieve flow test script content here.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert create_response.status_code == http.HTTP_201_CREATED
    comp_id = create_response.json()["id"]

    response = client.get(f"/api/compositions/{comp_id}/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["id"] == comp_id
    assert data["template_kind"] == "talking_head"
    assert data["final_asset"] is not None
    assert len(data["steps"]) == 1


# ---- A8 (SESSION 192) — produced_assets cross-link --------------


def test_retrieve_composition_includes_produced_assets() -> None:
    """A8: every Asset emitted by the composition's pipeline surfaces
    in the produced_assets field with role + storage_health attached.
    The list is ordered by Asset.created_at (oldest first) so the SPA
    panel reads top-to-bottom as the pipeline executed.
    """
    ws, user = _make_workspace_with_user("a8produced@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    create_response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": "A8 produced_assets cross-link test.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert create_response.status_code == http.HTTP_201_CREATED
    comp_id = create_response.json()["id"]

    response = client.get(f"/api/compositions/{comp_id}/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()

    # talking_head's mock_mode produces exactly one Asset
    # (the generate_avatar_speech output) that doubles as the
    # final_asset.
    produced = data["produced_assets"]
    assert len(produced) >= 1
    entry = produced[0]
    assert entry["id"] == data["final_asset"]["id"]
    assert entry["is_final"] is True
    assert entry["role"] == "talking_head"
    assert entry["asset_type"] == "clip"
    # mock_mode emits a `mock://` URL → unknown scheme falls
    # through to UPLOAD_PENDING per A3 classifier.
    assert entry["storage_health"] in {
        "upload_pending", "https_live", "local_present",
    }
    # Field shape check — the SPA's Zod schema requires these.
    for key in ("id", "asset_type", "role", "title", "file_path",
                "storage_health", "is_final"):
        assert key in entry


def test_produced_assets_marks_only_final_with_is_final() -> None:
    """A8: when a composition produces multiple assets (e.g. a
    backdrop + a composite + the final talking_head), only the
    one wired to ``final_asset`` carries is_final=True."""
    ws, user = _make_workspace_with_user("a8final@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    create_response = client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": "A8 is_final marker test.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    comp_id = create_response.json()["id"]

    # Seed a second Asset on the same composition that is NOT the
    # final asset. Same workspace anchor so the signal is happy.
    from apps.compositions.models import Composition as CompModel
    comp = CompModel.objects.get(pk=comp_id)
    Asset.objects.create(
        workspace=ws,
        composition=comp,
        asset_type=AssetType.IMAGE,
        role="reference_image",
        file_path="/data/reference.png",
        source_spec={"primitive_kind": "generate_image"},
    )

    response = client.get(f"/api/compositions/{comp_id}/")
    data = response.json()
    produced = data["produced_assets"]
    finals = [a for a in produced if a["is_final"]]
    assert len(finals) == 1
    assert finals[0]["id"] == data["final_asset"]["id"]


def test_produced_assets_empty_for_draft_composition() -> None:
    """A8: a composition with no emitted Assets yet returns
    produced_assets=[] (Zod default([]) handles this on the SPA
    side too)."""
    ws, user = _make_workspace_with_user("a8empty@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    # Build a Composition row directly so no pipeline fires.
    from apps.compositions.models import Composition as CompModel
    comp = CompModel.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="A8 empty",
        template_kind="talking_head",
    )

    response = client.get(f"/api/compositions/{comp.pk}/")
    assert response.status_code == http.HTTP_200_OK
    assert response.json()["produced_assets"] == []


def test_retrieve_cross_workspace_rejected() -> None:
    ws_a, user_a = _make_workspace_with_user("v15xret_a@test", "A")
    _ws_b, user_b = _make_workspace_with_user("v15xret_b@test", "B")
    sp_a = _make_spokesperson(ws_a)
    client_a = APIClient()
    _login(client_a, user_a)
    create_response = client_a.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(ws_a.pk),
            "params": {
                "spokesperson_id": str(sp_a.pk),
                "script": "private content in workspace A",
                "mock_mode": True,
            },
        },
        format="json",
    )
    comp_id = create_response.json()["id"]

    # User B (different workspace) tries to read it.
    client_b = APIClient()
    _login(client_b, user_b)
    response = client_b.get(f"/api/compositions/{comp_id}/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_list_assets_filters_by_workspace() -> None:
    ws_a, user_a = _make_workspace_with_user("v15assa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("v15assb@test", "B")
    _make_clip(ws_a, "/data/a-clip.mp4")
    _make_clip(ws_b, "/data/b-clip.mp4")
    client = APIClient()
    _login(client, user_a)

    response = client.get(f"/api/assets/?workspace={ws_a.pk}")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["workspace"] == str(ws_a.pk)


def test_list_assets_filters_by_asset_type() -> None:
    ws, user = _make_workspace_with_user("v15assfilter@test")
    _make_clip(ws)
    _make_audio(ws)
    client = APIClient()
    _login(client, user)

    clip_response = client.get(
        f"/api/assets/?workspace={ws.pk}&asset_type=clip"
    )
    assert clip_response.status_code == http.HTTP_200_OK
    clip_data = clip_response.json()
    assert len(clip_data) == 1
    assert clip_data[0]["asset_type"] == "clip"

    audio_response = client.get(
        f"/api/assets/?workspace={ws.pk}&asset_type=audio"
    )
    audio_data = audio_response.json()
    assert len(audio_data) == 1
    assert audio_data[0]["asset_type"] == "audio"


def test_list_assets_excludes_foreign_workspaces() -> None:
    ws_a, _user_a = _make_workspace_with_user("v15assfa@test", "A")
    _ws_b, user_b = _make_workspace_with_user("v15assfb@test", "B")
    _make_clip(ws_a)
    client = APIClient()
    _login(client, user_b)

    response = client.get(f"/api/assets/?workspace={ws_a.pk}")
    # User B has no membership in workspace A — queryset filter
    # drops the rows.
    assert response.status_code == http.HTTP_200_OK
    assert response.json() == []


def test_list_assets_requires_auth() -> None:
    client = APIClient()
    response = client.get("/api/assets/")
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


# ---- A7 (SESSION 190) — role filter on asset_picker endpoint ------


def _make_clip_with_role(ws: Workspace, role: str) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP, role=role,
        file_path=f"/data/{role}.mp4", duration_ms=5000,
        mime_type="video/mp4",
    )


def test_list_assets_role_filter_single() -> None:
    """A7: /api/assets/?role=backdrop narrows the picker to backdrops."""
    from apps.compositions.models import AssetRole

    ws, user = _make_workspace_with_user("a7role@test")
    _make_clip_with_role(ws, AssetRole.TALKING_HEAD.value)
    backdrop = _make_clip_with_role(ws, AssetRole.BACKDROP.value)
    _make_clip_with_role(ws, AssetRole.COMPOSITE_OUTPUT.value)
    client = APIClient()
    _login(client, user)

    response = client.get(
        f"/api/assets/?workspace={ws.pk}&role=backdrop"
    )
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(backdrop.id)


def test_list_assets_role_filter_comma_list() -> None:
    """A7: comma-list passes through as a Django __in filter."""
    from apps.compositions.models import AssetRole

    ws, user = _make_workspace_with_user("a7multi@test")
    _make_clip_with_role(ws, AssetRole.TALKING_HEAD.value)
    _make_clip_with_role(ws, AssetRole.BACKDROP.value)
    _make_clip_with_role(ws, AssetRole.B_ROLL.value)
    _make_clip_with_role(ws, AssetRole.COMPOSITE_OUTPUT.value)
    client = APIClient()
    _login(client, user)

    response = client.get(
        f"/api/assets/?workspace={ws.pk}&role=backdrop,b_roll"
    )
    assert response.status_code == http.HTTP_200_OK
    roles = {a["role"] if "role" in a else "" for a in response.json()}
    # /api/assets/ doesn't surface role in its inline serializer
    # shape (that's A4's). Verify count instead.
    assert len(response.json()) == 2


def test_list_assets_role_filter_unknown_returns_empty() -> None:
    """A7: unknown role value matches zero rows (typo'd value
    in the picker should produce an empty dropdown, not crash)."""
    from apps.compositions.models import AssetRole

    ws, user = _make_workspace_with_user("a7unknown@test")
    _make_clip_with_role(ws, AssetRole.BACKDROP.value)
    client = APIClient()
    _login(client, user)

    response = client.get(
        f"/api/assets/?workspace={ws.pk}&role=totally_invented"
    )
    assert response.status_code == http.HTTP_200_OK
    assert response.json() == []


def test_list_assets_no_role_param_returns_everything() -> None:
    """A7: backwards-compat — existing callers that don't pass
    ?role= keep getting the full workspace asset list."""
    from apps.compositions.models import AssetRole

    ws, user = _make_workspace_with_user("a7noparam@test")
    _make_clip_with_role(ws, AssetRole.TALKING_HEAD.value)
    _make_clip_with_role(ws, AssetRole.BACKDROP.value)
    client = APIClient()
    _login(client, user)

    response = client.get(f"/api/assets/?workspace={ws.pk}")
    assert response.status_code == http.HTTP_200_OK
    assert len(response.json()) == 2


def test_list_assets_role_combines_with_asset_type() -> None:
    """A7: ?role= AND ?asset_type= apply together (Django filters
    chain by intersection)."""
    from apps.compositions.models import AssetRole

    ws, user = _make_workspace_with_user("a7combo@test")
    # CLIP with role=backdrop — should match.
    _make_clip_with_role(ws, AssetRole.BACKDROP.value)
    # AUDIO with role=audio_track — same role but wrong asset_type.
    Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        role=AssetRole.AUDIO_TRACK.value,
        file_path="/data/x.mp3", duration_ms=3000,
        mime_type="audio/mpeg",
    )
    client = APIClient()
    _login(client, user)

    response = client.get(
        f"/api/assets/?workspace={ws.pk}&asset_type=clip&role=backdrop"
    )
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert len(data) == 1
    assert data[0]["asset_type"] == "clip"


# ---- A7 — RecipeField.role_filter serialization ------------------


def test_recipe_backdrop_clip_id_exposes_role_filter() -> None:
    """A7: V18's talking_head_with_backdrop recipe ships
    ``role_filter=backdrop`` on the backdrop_clip_id field so the
    SPA picker can narrow to BACKDROP-tagged clips."""
    ws, user = _make_workspace_with_user("a7thwb@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/talking_head_with_backdrop/")
    assert response.status_code == http.HTTP_200_OK
    fields = response.json()["fields"]
    backdrop_field = next(
        f for f in fields if f["name"] == "backdrop_clip_id"
    )
    assert backdrop_field["type"] == "asset_picker"
    assert backdrop_field["role_filter"] == "backdrop"


def test_recipe_broll_splice_exposes_role_filter() -> None:
    """A7: V8 broll_splice ships role_filter=b_roll on broll_clip_id."""
    ws, user = _make_workspace_with_user("a7broll@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/broll_splice/")
    assert response.status_code == http.HTTP_200_OK
    fields = response.json()["fields"]
    broll_field = next(f for f in fields if f["name"] == "broll_clip_id")
    assert broll_field["role_filter"] == "b_roll"
    # The other picker (base_clip_id) stays unfiltered — fuzzy
    # role; operator picks whichever CLIP makes sense.
    base_field = next(f for f in fields if f["name"] == "base_clip_id")
    assert "role_filter" not in base_field


def test_recipe_backdrop_layout_exposes_role_filter_on_background_only() -> None:
    """A7: V8 backdrop_layout — background_clip_id gets
    role_filter=backdrop; foreground_clip_id stays unfiltered
    (the foreground is whatever talking-head / composite the
    operator wants on top)."""
    ws, user = _make_workspace_with_user("a7bdrop@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/backdrop_layout/")
    assert response.status_code == http.HTTP_200_OK
    fields = response.json()["fields"]
    bg = next(f for f in fields if f["name"] == "background_clip_id")
    fg = next(f for f in fields if f["name"] == "foreground_clip_id")
    assert bg["role_filter"] == "backdrop"
    assert "role_filter" not in fg


def test_recipe_music_bed_pass_exposes_audio_role_filter() -> None:
    """A7: V8 music_bed_pass ships role_filter=audio_track on the
    music_asset_id picker. base_clip_id (the voice clip) stays
    unfiltered."""
    ws, user = _make_workspace_with_user("a7music@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/music_bed_pass/")
    assert response.status_code == http.HTTP_200_OK
    fields = response.json()["fields"]
    music = next(f for f in fields if f["name"] == "music_asset_id")
    assert music["role_filter"] == "audio_track"


def test_unfiltered_pickers_omit_role_filter_key() -> None:
    """A7 — to_json omits role_filter when None. Existing recipes
    without explicit role_filter should not start carrying an
    extra ``role_filter: null`` key (would force the SPA Zod
    schema to handle nulls + the schema currently uses .optional()
    which means 'not present', not 'null')."""
    from apps.compositions.recipes import get_recipe

    pip = get_recipe("pip_layout")
    base_field = pip.field_by_name("base_clip_id")
    pip_field = pip.field_by_name("pip_clip_id")
    assert base_field is not None
    assert pip_field is not None
    assert "role_filter" not in base_field.to_json()
    assert "role_filter" not in pip_field.to_json()


def test_create_storyboard_voiced_ten_steps() -> None:
    """V15.4 — storyboard_voiced creates 10 steps:
    3 images + 3 clips + concat + speech + audio_extract + mix_audio.
    Unblocked by V14's audio_extract primitive."""
    ws, user = _make_workspace_with_user("v15sbv@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_voiced",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "neon city skyline at dusk",
                "action_prompt": "founder walking confidently down a hallway",
                "payoff_prompt": "team celebrating around a table",
                "narration_script": (
                    "Welcome to our company. We build things that matter. "
                    "Join us today and see what's possible."
                ),
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "storyboard_voiced"
    assert len(data["steps"]) == 10
    primitives = [s["primitive"] for s in sorted(data["steps"], key=lambda s: s["position"])]
    assert primitives == [
        "generate_image", "generate_image", "generate_image",
        "generate_visual_clip", "generate_visual_clip", "generate_visual_clip",
        "concat_clips",
        "generate_avatar_speech",
        "audio_extract",
        "mix_audio",
    ]


def test_storyboard_voiced_outro_text_adds_eleventh_step() -> None:
    """SESSION 197 — when outro_text is set, the starter appends
    an add_intro_outro step at position 10 consuming the mix_audio
    output. Backwards-compat default (blank outro) keeps the
    10-step shape; with-outro is 11 steps."""
    ws, user = _make_workspace_with_user("v197sbv_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_voiced",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "founder lifting espresso machine handle",
                "action_prompt": "pouring latte art",
                "payoff_prompt": "busy storefront at golden hour",
                "narration_script": "Coffee for the community.",
                "outro_text": "Dog Food Coffee House",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "storyboard_voiced"
    assert len(data["steps"]) == 11
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    primitives = [s["primitive"] for s in steps_by_pos]
    assert primitives == [
        "generate_image", "generate_image", "generate_image",
        "generate_visual_clip", "generate_visual_clip", "generate_visual_clip",
        "concat_clips",
        "generate_avatar_speech",
        "audio_extract",
        "mix_audio",
        "add_intro_outro",
    ]
    # The outro step's params carry the operator's text + the
    # default 3-second duration matching talking_head_polished.
    outro_step = steps_by_pos[10]
    assert outro_step["params"]["outro"]["text"] == "Dog Food Coffee House"
    assert outro_step["params"]["outro"]["duration_s"] == 3.0
    # Inputs chain to the mix_audio step (position 9).
    assert outro_step["inputs"] == [
        {"slot": "base", "from_step_position": 9},
    ]


def test_storyboard_voiced_blank_outro_text_keeps_ten_steps() -> None:
    """Backwards-compat: empty / whitespace-only outro_text is a
    no-op. Existing storyboard_voiced renders without outro_text
    set keep the same 10-step shape they had pre-SESSION-197."""
    ws, user = _make_workspace_with_user("v197sbv_blank@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    # Whitespace-only — should still skip the outro step.
    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_voiced",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "scene 1",
                "action_prompt": "scene 2",
                "payoff_prompt": "scene 3",
                "narration_script": "Narration that fits ~15 seconds of video.",
                "outro_text": "   ",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    assert len(response.json()["steps"]) == 10


def test_storyboard_voiced_recipe_exposes_outro_text_field() -> None:
    """SESSION 197 — the recipe metadata endpoint surfaces
    outro_text so the SPA form renders the field. Mirrors the
    talking_head_polished shape (text, 80 char max, optional)."""
    ws, user = _make_workspace_with_user("v197sbv_metadata@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/storyboard_voiced/")
    assert response.status_code == http.HTTP_200_OK
    fields = {f["name"]: f for f in response.json()["fields"]}
    assert "outro_text" in fields
    outro_field = fields["outro_text"]
    assert outro_field["type"] == "text"
    assert outro_field["required"] is False
    assert outro_field["max_chars"] == 80


def test_storyboard_voiced_use_extend_for_shots_adds_extend_chain() -> None:
    """SESSION 200 — when use_extend_for_shots=True, three
    extend_visual_clip steps land between the generates and the
    concat. Each extend conditions on the prior generate's last
    frame. The concat then consumes positions 6-8 instead of 3-5.
    Composition shape: 3 image + 3 generate + 3 extend + concat +
    speech + extract + mix = 13 steps."""
    ws, user = _make_workspace_with_user("v200sbv_extend@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_voiced",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "neon city skyline at dusk",
                "action_prompt": "founder walking confidently down a hallway",
                "payoff_prompt": "team celebrating around a table",
                "narration_script": (
                    "Welcome to our company. We build things that matter."
                ),
                "use_extend_for_shots": True,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert len(data["steps"]) == 13
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    primitives = [s["primitive"] for s in steps_by_pos]
    assert primitives == [
        "generate_image", "generate_image", "generate_image",
        "generate_visual_clip", "generate_visual_clip", "generate_visual_clip",
        "extend_visual_clip", "extend_visual_clip", "extend_visual_clip",
        "concat_clips",
        "generate_avatar_speech",
        "audio_extract",
        "mix_audio",
    ]
    # Each extend conditions on the matching generate output via
    # the ``source`` slot. Position 6 → from 3, 7 → from 4, 8 → from 5.
    for idx in range(3):
        extend_step = steps_by_pos[6 + idx]
        assert extend_step["primitive"] == "extend_visual_clip"
        assert extend_step["inputs"] == [
            {"slot": "source", "from_step_position": 3 + idx},
        ]
    # The concat at position 9 now points at the extend outputs.
    concat_step = steps_by_pos[9]
    assert concat_step["primitive"] == "concat_clips"
    assert concat_step["inputs"] == [
        {"slot": "clip", "from_step_position": 6},
        {"slot": "clip", "from_step_position": 7},
        {"slot": "clip", "from_step_position": 8},
    ]
    # mix_audio still wires base=concat, music=audio_extract.
    mix_step = steps_by_pos[12]
    assert mix_step["primitive"] == "mix_audio"
    assert {i["slot"]: i["from_step_position"] for i in mix_step["inputs"]} == {
        "base": 9,
        "music": 11,
    }


def test_storyboard_voiced_extend_plus_outro_appends_fourteenth_step() -> None:
    """SESSION 200 — extend + outro combine cleanly. Outro lands
    after the mix at position 13."""
    ws, user = _make_workspace_with_user("v200sbv_extend_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_voiced",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "espresso steam rising",
                "action_prompt": "barista pulling shot",
                "payoff_prompt": "happy customer leaving",
                "narration_script": "Coffee that wakes up the neighborhood.",
                "use_extend_for_shots": True,
                "outro_text": "Dog Food Coffee House",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert len(data["steps"]) == 14
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    outro_step = steps_by_pos[13]
    assert outro_step["primitive"] == "add_intro_outro"
    assert outro_step["inputs"] == [
        {"slot": "base", "from_step_position": 12},
    ]


def test_storyboard_voiced_crossfade_ms_forwarded_to_concat() -> None:
    """SESSION 200 — when crossfade_ms is set, the starter stamps
    it into the concat step's params so the runner forwards it to
    the primitive at execute time."""
    ws, user = _make_workspace_with_user("v200sbv_xfade@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_voiced",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "a",
                "action_prompt": "b",
                "payoff_prompt": "c",
                "narration_script": "Narration that lines up with the cuts.",
                "crossfade_ms": 500,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    concat_step = next(s for s in steps_by_pos if s["primitive"] == "concat_clips")
    assert concat_step["params"]["crossfade_ms"] == 500


def test_storyboard_voiced_recipe_exposes_extend_and_crossfade_fields() -> None:
    """SESSION 200 — recipe metadata surfaces the two new fields
    so the SPA form renders them."""
    _, user = _make_workspace_with_user("v200sbv_meta@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/storyboard_voiced/")
    assert response.status_code == http.HTTP_200_OK
    fields = {f["name"]: f for f in response.json()["fields"]}
    assert "use_extend_for_shots" in fields
    assert fields["use_extend_for_shots"]["type"] == "checkbox"
    assert fields["use_extend_for_shots"]["default"] is False
    assert "crossfade_ms" in fields
    assert fields["crossfade_ms"]["type"] == "number"
    assert fields["crossfade_ms"]["default"] == 0
    assert fields["crossfade_ms"]["max_value"] == 5000


def test_storyboard_ad_use_extend_for_shots_adds_extend_chain() -> None:
    """SESSION 200 — storyboard_ad mirrors storyboard_voiced.
    Three extends between generates and concat. 10 steps total
    when extend is on (was 7 without)."""
    ws, user = _make_workspace_with_user("v200sba_extend@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "a hook image",
                "action_prompt": "an action image",
                "payoff_prompt": "a payoff image",
                "use_extend_for_shots": True,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert len(data["steps"]) == 10
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    primitives = [s["primitive"] for s in steps_by_pos]
    assert primitives == [
        "generate_image", "generate_image", "generate_image",
        "generate_visual_clip", "generate_visual_clip", "generate_visual_clip",
        "extend_visual_clip", "extend_visual_clip", "extend_visual_clip",
        "concat_clips",
    ]
    # Concat consumes the extends.
    concat_step = steps_by_pos[9]
    assert concat_step["inputs"] == [
        {"slot": "clip", "from_step_position": 6},
        {"slot": "clip", "from_step_position": 7},
        {"slot": "clip", "from_step_position": 8},
    ]


def test_storyboard_ad_extend_plus_outro_appends_eleventh_step() -> None:
    """SESSION 200 — outro still works when extend is on; position
    shifts up to 10."""
    ws, user = _make_workspace_with_user("v200sba_extend_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "scene 1",
                "action_prompt": "scene 2",
                "payoff_prompt": "scene 3",
                "use_extend_for_shots": True,
                "outro_text": "Brand",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert len(data["steps"]) == 11
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    outro_step = steps_by_pos[10]
    assert outro_step["primitive"] == "add_intro_outro"
    assert outro_step["inputs"] == [
        {"slot": "base", "from_step_position": 9},
    ]


def test_storyboard_ad_crossfade_ms_forwarded_to_concat() -> None:
    """SESSION 200 — crossfade_ms stamped into the concat step."""
    ws, user = _make_workspace_with_user("v200sba_xfade@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "a",
                "action_prompt": "b",
                "payoff_prompt": "c",
                "crossfade_ms": 300,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    concat_step = next(
        s for s in data["steps"] if s["primitive"] == "concat_clips"
    )
    assert concat_step["params"]["crossfade_ms"] == 300


def test_storyboard_ad_recipe_exposes_extend_and_crossfade_fields() -> None:
    """SESSION 200 — both fields exposed in storyboard_ad
    metadata, matching storyboard_voiced."""
    _, user = _make_workspace_with_user("v200sba_meta@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/storyboard_ad/")
    assert response.status_code == http.HTTP_200_OK
    fields = {f["name"]: f for f in response.json()["fields"]}
    assert fields["use_extend_for_shots"]["type"] == "checkbox"
    assert fields["use_extend_for_shots"]["default"] is False
    assert fields["crossfade_ms"]["type"] == "number"
    assert fields["crossfade_ms"]["max_value"] == 5000


def test_create_dialogue_scene_via_recipe_registry() -> None:
    """V15.4 confirms the dialogue_scene custom resolver still
    works post-V15 changes (covers regression risk from the
    storyboard_voiced addition)."""
    ws, user = _make_workspace_with_user("v15dlg154@test")
    sp_a = _make_spokesperson(ws, name="A", avatar_id="av_a")
    sp_b = _make_spokesperson(ws, name="B", avatar_id="av_b")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "dialogue_scene",
            "workspace": str(ws.pk),
            "params": {
                "primary_spokesperson_id": str(sp_a.pk),
                "lines": [
                    {"spokesperson_id": str(sp_a.pk), "text": "Welcome."},
                    {"spokesperson_id": str(sp_b.pk), "text": "Glad to be here."},
                    {"spokesperson_id": str(sp_a.pk), "text": "Let's get into it."},
                ],
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "dialogue_scene"
    # 3 speech + 1 concat = 4 steps
    assert len(data["steps"]) == 4


def test_create_voice_design_minimal() -> None:
    """V15.3 — voice_design has no asset inputs; pure text params."""
    ws, user = _make_workspace_with_user("v15voice@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "voice_design",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "description": "warm conversational founder voice",
                "voice_name": "Test voice",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    assert response.json()["template_kind"] == "voice_design"


def test_create_storyboard_ad_seven_steps() -> None:
    """V15.3 — storyboard_ad creates 7 steps (3 images + 3 clips + concat)."""
    ws, user = _make_workspace_with_user("v15sb@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "neon city skyline at dusk",
                "action_prompt": "founder walks confidently into the office",
                "payoff_prompt": "team raises glasses in celebration",
                "clip_duration": 5,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "storyboard_ad"
    assert len(data["steps"]) == 7


def test_create_long_form_ad_chunks_script() -> None:
    """V15.3 — long_form_ad pre-splits the script at starter time
    so the runtime sees a fixed N+1 plan."""
    ws, user = _make_workspace_with_user("v15lf@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    # ~500 char script splits into 2 chunks at default
    # DEFAULT_CHUNK_MAX_CHARS=280; that gives 2 speech steps +
    # 1 concat = 3 steps.
    script = (
        "Welcome to our spring launch event. "
        "We've been working all year on something special. "
        "Today we're proud to introduce three new products. "
        "First, our flagship pen — designed for daily writing. "
        "Second, our notebook line — premium recycled paper. "
        "Third, our gift box — perfect for any occasion. "
        "Order today and get free shipping on every order. "
        "Visit our website to learn more about each piece."
    )
    response = client.post(
        "/api/compositions/",
        {
            "kind": "long_form_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": script,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "long_form_ad"
    # At least 2 speech steps + 1 concat = 3+
    assert len(data["steps"]) >= 3


def test_storyboard_ad_outro_text_appends_eighth_step() -> None:
    """SESSION 198 — outro_text parity for storyboard_ad. When set,
    the starter appends an add_intro_outro step at position 7 after
    the concat. Backwards-compat default (blank) keeps the 7-step
    shape."""
    ws, user = _make_workspace_with_user("v198sba_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "neon skyline at dusk",
                "action_prompt": "founder walks the floor",
                "payoff_prompt": "team raises a glass",
                "outro_text": "Dog Food Coffee House",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "storyboard_ad"
    assert len(data["steps"]) == 8
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    assert steps_by_pos[7]["primitive"] == "add_intro_outro"
    assert steps_by_pos[7]["params"]["outro"]["text"] == "Dog Food Coffee House"
    assert steps_by_pos[7]["params"]["outro"]["duration_s"] == 3.0
    assert steps_by_pos[7]["inputs"] == [
        {"slot": "base", "from_step_position": 6},
    ]


def test_storyboard_ad_blank_outro_keeps_seven_steps() -> None:
    """SESSION 198 — backwards-compat for storyboard_ad."""
    ws, user = _make_workspace_with_user("v198sba_blank@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "scene 1",
                "action_prompt": "scene 2",
                "payoff_prompt": "scene 3",
                "outro_text": "   ",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    assert len(response.json()["steps"]) == 7


def test_long_form_ad_outro_text_appends_step_after_concat() -> None:
    """SESSION 198 — outro_text parity for long_form_ad multi-chunk
    path. Outro lives at position len(chunks)+1 (after the concat
    at position len(chunks))."""
    ws, user = _make_workspace_with_user("v198lf_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    script = (
        "Welcome to our spring launch event. "
        "We've been working all year on something special. "
        "Today we're proud to introduce three new products. "
        "First, our flagship pen. "
        "Second, our notebook line. "
        "Third, our gift box. "
        "Order today and get free shipping on every order. "
        "Visit our website to learn more about each piece."
    )
    response = client.post(
        "/api/compositions/",
        {
            "kind": "long_form_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": script,
                "outro_text": "Brand Co.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    # Last step is the outro card.
    last_step = steps_by_pos[-1]
    assert last_step["primitive"] == "add_intro_outro"
    assert last_step["params"]["outro"]["text"] == "Brand Co."
    # Penultimate is the concat (which chains the speech outputs).
    second_last = steps_by_pos[-2]
    assert second_last["primitive"] == "concat_clips"
    # Outro chains to the concat.
    assert last_step["inputs"] == [
        {"slot": "base", "from_step_position": second_last["position"]},
    ]


def test_long_form_ad_single_chunk_outro_chains_to_speech() -> None:
    """SESSION 198 — degenerate single-chunk path: no concat;
    outro consumes the lone generate_avatar_speech step directly."""
    ws, user = _make_workspace_with_user("v198lf_single@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    # ~280-char script (right at DEFAULT_CHUNK_MAX_CHARS) produces a
    # single chunk → 1 speech step + 1 outro = 2 steps total.
    script = (
        "Welcome to our spring launch event. We've been working all "
        "year on something special. Order today and get free "
        "shipping on every order. Visit our website to learn more."
    )
    response = client.post(
        "/api/compositions/",
        {
            "kind": "long_form_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": script,
                "outro_text": "Closer",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    # Expect 2 steps: speech + outro (no concat, single chunk).
    assert len(steps_by_pos) == 2
    assert steps_by_pos[0]["primitive"] == "generate_avatar_speech"
    assert steps_by_pos[1]["primitive"] == "add_intro_outro"
    # Outro chains to the speech (position 0), not a concat.
    assert steps_by_pos[1]["inputs"] == [
        {"slot": "base", "from_step_position": 0},
    ]


def test_long_form_ad_concat_uses_talking_head_result_role() -> None:
    """SESSION 198 slice C — long_form_ad's concat output is N
    chunked talking-head speeches stitched into long-form content;
    role should be TALKING_HEAD (extended TH), not BACKDROP. Keeps
    the long-form deliverable out of the A7 backdrop_clip_id
    picker."""
    ws, user = _make_workspace_with_user("v198lf_role@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    script = (
        "Welcome to our spring launch event. "
        "We've been working all year on something special. "
        "Today we're proud to introduce three new products. "
        "First, our flagship pen. Second, our notebook line. "
        "Third, our gift box. Order today and get free shipping. "
        "Visit our website to learn more about each piece."
    )
    response = client.post(
        "/api/compositions/",
        {
            "kind": "long_form_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "script": script,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    concat = next(s for s in steps_by_pos if s["primitive"] == "concat_clips")
    assert concat["params"]["result_role"] == "talking_head"


def test_storyboard_ad_concat_keeps_default_backdrop_role() -> None:
    """SESSION 198 — explicit non-decision for storyboard_ad. Per
    SESSION 196 handoff: a 3-shot cinematic IS picker-eligible as
    a backdrop for V18 avatar speech (defensible). Leaving the
    default BACKDROP stamp. Test guards against accidental
    regression if the operator changes their mind."""
    ws, user = _make_workspace_with_user("v198sba_role@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "storyboard_ad",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "hook_prompt": "scene 1",
                "action_prompt": "scene 2",
                "payoff_prompt": "scene 3",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    concat = next(s for s in steps_by_pos if s["primitive"] == "concat_clips")
    # No result_role override = default BACKDROP at primitive runtime.
    # The starter doesn't set it explicitly; primitive picks up the
    # default. Test asserts the starter doesn't pass an override.
    assert "result_role" not in concat["params"]


def test_create_style_remix_pass_with_clip() -> None:
    """V15.3 — style_remix_pass takes a CLIP + preset."""
    ws, user = _make_workspace_with_user("v15style@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "style_remix_pass",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "source_clip_id": str(clip.pk),
                "style_preset": "noir",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    assert response.json()["template_kind"] == "style_remix_pass"


def test_create_layout_recipe_uses_two_workspace_assets() -> None:
    """End-to-end V15.2 happy path: pip_layout takes two CLIP
    assets + integer styling params. Confirms the asset_picker
    flow + param_map FK renaming both work."""
    ws, user = _make_workspace_with_user("v15pip@test")
    sp = _make_spokesperson(ws)
    base = _make_clip(ws, "/data/base.mp4")
    pip = _make_clip(ws, "/data/pip.mp4")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "pip_layout",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "base_clip_id": str(base.pk),
                "pip_clip_id": str(pip.pk),
                "pip_width": 320,
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template_kind"] == "pip_layout"


def test_list_compositions_scoped_to_caller() -> None:
    ws_a, user_a = _make_workspace_with_user("v15lista@test", "A")
    ws_b, user_b = _make_workspace_with_user("v15listb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    sp_b = _make_spokesperson(ws_b)
    client_a = APIClient()
    _login(client_a, user_a)
    client_b = APIClient()
    _login(client_b, user_b)

    # Each user creates one composition in their workspace.
    for client, ws, sp in [(client_a, ws_a, sp_a), (client_b, ws_b, sp_b)]:
        r = client.post(
            "/api/compositions/",
            {
                "kind": "talking_head",
                "workspace": str(ws.pk),
                "params": {
                    "spokesperson_id": str(sp.pk),
                    "script": "list scoping content",
                    "mock_mode": True,
                },
            },
            format="json",
        )
        assert r.status_code == http.HTTP_201_CREATED, r.content

    response_a = client_a.get("/api/compositions/")
    assert response_a.status_code == http.HTTP_200_OK
    data_a = response_a.json()
    assert len(data_a) == 1
    assert data_a[0]["workspace"] == str(ws_a.pk)

    response_b = client_b.get("/api/compositions/")
    data_b = response_b.json()
    assert len(data_b) == 1
    assert data_b[0]["workspace"] == str(ws_b.pk)


# ---- W11.6.5 (SESSION 174) — recipe image-picker ----------------


def _make_image_asset(ws: Workspace, *, file_path: str = "data:image/png;base64,abcdef") -> Asset:
    """Image asset shape mirrors the W11.6.1 ImageViewSet
    create path. file_path holds the data URI; cinematic_visual
    will read it through the resolver."""
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        file_path=file_path,
        mime_type="image/png",
        purpose="scene", model="sd3-large",
        aspect_ratio="16:9",
    )


def test_cinematic_visual_recipe_exposes_image_picker_field() -> None:
    """W11.6.5 — the optional asset_picker field is part of
    cinematic_visual's metadata so the SPA form renders it."""
    ws, user = _make_workspace_with_user("w1165meta@test")
    client = APIClient()
    _login(client, user)
    resp = client.get("/api/recipes/cinematic_visual/")
    assert resp.status_code == http.HTTP_200_OK
    data = resp.json()
    image_fields = [
        f for f in data["fields"]
        if f["name"] == "prompt_image_asset_id"
    ]
    assert len(image_fields) == 1
    field = image_fields[0]
    assert field["type"] == "asset_picker"
    assert field["asset_type"] == AssetType.IMAGE
    assert field["required"] is False


def test_cinematic_visual_with_image_passes_data_uri_to_starter() -> None:
    """W11.6.5 — when the operator picks a workspace image,
    the resolver extracts the Asset's file_path (data URI)
    and passes it as prompt_image. The composition's step
    params should carry it through to the media-engine call."""
    ws, user = _make_workspace_with_user("w1165image@test")
    sp = _make_spokesperson(ws)
    image = _make_image_asset(
        ws, file_path="data:image/png;base64,IMAGEBYTES",
    )
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "prompt": "A craft brewery at sunrise",
                "prompt_image_asset_id": str(image.pk),
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    # Composition's single step should carry prompt_image
    # populated from the picked Asset's file_path.
    assert len(data["steps"]) == 1
    step_params = data["steps"][0]["params"]
    assert step_params.get("prompt_image") == (
        "data:image/png;base64,IMAGEBYTES"
    )


def test_cinematic_visual_without_image_does_not_set_prompt_image() -> None:
    """Invariant — the image picker is optional. Omitting it
    leaves prompt_image absent from step params (so the starter
    routes through gen4.5 text-to-video instead of gen4_turbo
    image-to-video)."""
    ws, user = _make_workspace_with_user("w1165noimage@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "prompt": "A craft brewery at sunrise",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    step_params = data["steps"][0]["params"]
    assert "prompt_image" not in step_params


def test_cinematic_visual_rejects_cross_workspace_image() -> None:
    """W11.6.5 — workspace isolation extends to the new
    image-picker. Picking an image from another workspace
    fails with 400 via the standard Asset.DoesNotExist path."""
    ws_a, user_a = _make_workspace_with_user("w1165xa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("w1165xb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign_image = _make_image_asset(ws_b)
    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual",
            "workspace": str(ws_a.pk),
            "params": {
                "spokesperson_id": str(sp_a.pk),
                "prompt": "A scene",
                "prompt_image_asset_id": str(foreign_image.pk),
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_resolver_passes_asset_row_for_clip_picker_unchanged() -> None:
    """W11.6.5 invariant — the special-case for IMAGE asset_type
    didn't change how clip asset_pickers resolve. pip_layout's
    base_clip + pip_clip should still arrive as Asset rows at
    the starter, not as file_path strings."""
    from apps.compositions.recipes import RECIPES, resolve_kwargs

    ws, user = _make_workspace_with_user("w1165clipinv@test")
    sp = _make_spokesperson(ws)
    base = _make_clip(ws, file_path="/data/base.mp4")
    pip = _make_clip(ws, file_path="/data/pip.mp4")
    recipe = RECIPES["pip_layout"]
    kwargs = resolve_kwargs(
        recipe,
        workspace=ws,
        params={
            "spokesperson_id": str(sp.pk),
            "base_clip_id": str(base.pk),
            "pip_clip_id": str(pip.pk),
            "mock_mode": True,
        },
        created_by=user,
    )
    assert isinstance(kwargs["base_clip"], Asset)
    assert isinstance(kwargs["pip_clip"], Asset)
    assert kwargs["base_clip"].file_path == "/data/base.mp4"


# ---- SESSION 199: outro_text parity (cinematic_visual + extended + dialogue) ----


def test_cinematic_visual_outro_text_appends_second_step() -> None:
    """SESSION 199 slice A — cinematic_visual gets a 2nd step
    when outro_text is set."""
    ws, user = _make_workspace_with_user("v199cv_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "prompt": "neon city skyline at dusk",
                "outro_text": "Brand Co.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert len(data["steps"]) == 2
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    assert steps_by_pos[0]["primitive"] == "generate_visual_clip"
    assert steps_by_pos[1]["primitive"] == "add_intro_outro"
    assert steps_by_pos[1]["params"]["outro"]["text"] == "Brand Co."
    assert steps_by_pos[1]["inputs"] == [
        {"slot": "base", "from_step_position": 0},
    ]


def test_cinematic_visual_blank_outro_keeps_one_step() -> None:
    """SESSION 199 — backwards-compat for cinematic_visual."""
    ws, user = _make_workspace_with_user("v199cv_blank@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "prompt": "neon skyline",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    assert len(response.json()["steps"]) == 1


def test_cinematic_visual_extended_outro_text_appends_after_chain() -> None:
    """SESSION 199 slice B — cinematic_visual_extended outro lands
    at position last_extend+1. target_duration=20 → 1 base + 2
    extends + 1 outro = 4 steps total."""
    ws, user = _make_workspace_with_user("v199cve_outro@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual_extended",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "prompt": "founder walking through the office",
                "target_duration": "20",
                "outro_text": "Brand Co.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    # 1 base + 2 extends + 1 outro = 4 steps
    assert len(steps_by_pos) == 4
    primitives = [s["primitive"] for s in steps_by_pos]
    assert primitives == [
        "generate_visual_clip",
        "extend_visual_clip",
        "extend_visual_clip",
        "add_intro_outro",
    ]
    # Outro chains to the last extend (position 2)
    outro_step = steps_by_pos[3]
    assert outro_step["inputs"] == [
        {"slot": "base", "from_step_position": 2},
    ]
    assert outro_step["params"]["outro"]["text"] == "Brand Co."


def test_cinematic_visual_extended_blank_outro_keeps_chain() -> None:
    """SESSION 199 — backwards-compat for cinematic_visual_extended.
    target_duration=15 → 1 base + 1 extend = 2 steps (no outro)."""
    ws, user = _make_workspace_with_user("v199cve_blank@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "cinematic_visual_extended",
            "workspace": str(ws.pk),
            "params": {
                "spokesperson_id": str(sp.pk),
                "prompt": "skyline",
                "target_duration": "15",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    assert len(response.json()["steps"]) == 2


def test_dialogue_scene_outro_text_multi_line_appends_after_concat() -> None:
    """SESSION 199 slice C — dialogue_scene multi-line outro lands
    after the concat. 3 lines → 3 speech + 1 concat + 1 outro = 5 steps."""
    ws, user = _make_workspace_with_user("v199ds_outro@test")
    sp_a = _make_spokesperson(ws, name="A", avatar_id="av_a")
    sp_b = _make_spokesperson(ws, name="B", avatar_id="av_b")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "dialogue_scene",
            "workspace": str(ws.pk),
            "params": {
                "primary_spokesperson_id": str(sp_a.pk),
                "lines": [
                    {"spokesperson_id": str(sp_a.pk), "text": "Line one."},
                    {"spokesperson_id": str(sp_b.pk), "text": "Line two."},
                    {"spokesperson_id": str(sp_a.pk), "text": "Line three."},
                ],
                "outro_text": "Brand Co.",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    primitives = [s["primitive"] for s in steps_by_pos]
    assert primitives == [
        "generate_avatar_speech",
        "generate_avatar_speech",
        "generate_avatar_speech",
        "concat_clips",
        "add_intro_outro",
    ]
    # Outro chains to concat at position 3.
    outro = steps_by_pos[4]
    assert outro["inputs"] == [
        {"slot": "base", "from_step_position": 3},
    ]
    assert outro["params"]["outro"]["text"] == "Brand Co."


def test_dialogue_scene_outro_text_single_line_chains_to_speech() -> None:
    """SESSION 199 — dialogue_scene single-line degenerate path:
    no concat; outro chains directly to the lone speech step at
    position 0."""
    ws, user = _make_workspace_with_user("v199ds_single@test")
    sp = _make_spokesperson(ws, name="A", avatar_id="av_a")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/compositions/",
        {
            "kind": "dialogue_scene",
            "workspace": str(ws.pk),
            "params": {
                "primary_spokesperson_id": str(sp.pk),
                "lines": [
                    {"spokesperson_id": str(sp.pk), "text": "Solo line."},
                ],
                "outro_text": "Closer",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    steps_by_pos = sorted(data["steps"], key=lambda s: s["position"])
    assert len(steps_by_pos) == 2
    assert steps_by_pos[0]["primitive"] == "generate_avatar_speech"
    assert steps_by_pos[1]["primitive"] == "add_intro_outro"
    assert steps_by_pos[1]["inputs"] == [
        {"slot": "base", "from_step_position": 0},
    ]


def test_dialogue_scene_outro_text_field_exposed_in_recipe_metadata() -> None:
    """SESSION 199 — the recipe metadata endpoint surfaces
    outro_text so the SPA form renders the field. Sanity check
    that the field landed alongside the existing dialogue fields."""
    ws, user = _make_workspace_with_user("v199ds_meta@test")
    client = APIClient()
    _login(client, user)

    response = client.get("/api/recipes/dialogue_scene/")
    assert response.status_code == http.HTTP_200_OK
    fields = {f["name"]: f for f in response.json()["fields"]}
    assert "outro_text" in fields
    outro_field = fields["outro_text"]
    assert outro_field["type"] == "text"
    assert outro_field["required"] is False
    assert outro_field["max_chars"] == 80
