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


def test_recipe_registry_has_eighteen_entries() -> None:
    """V15.4 added ``storyboard_voiced`` (was deferred from V13
    until V14 shipped ``audio_extract``), bringing the gallery
    to 18 starter compositions."""
    assert len(RECIPES) == 18


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
        "spokesperson_picker", "asset_picker", "dialogue_lines",
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


def test_get_recipes_returns_all_eighteen() -> None:
    ws, user = _make_workspace_with_user("v15list@test")
    client = APIClient()
    _login(client, user)
    response = client.get("/api/recipes/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert len(data) == 18


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
