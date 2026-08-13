"""B2.4 — Recipe-gallery integration tests for the
``auto_script`` recipe.

Five concerns:

1. ``auto_script`` appears in ``GET /api/recipes/`` with the
   right field shape (Script picker + name + mock_mode only;
   no free-form prompt textarea per Q-e-11).
2. ``GET /api/recipes/auto_script/`` returns proper metadata.
3. ``script_picker`` field type resolves to a Script row via
   ``resolve_kwargs``.
4. ``script_picker`` rejects non-READY scripts (Q-e-11 — the
   gallery picker filters to READY scripts).
5. ``script_picker`` rejects cross-workspace script_ids.

Note: the full ``POST /api/compositions/`` integration end-to-
end is exercised through ``test_v15_api.py`` for talking_head
+ the per-recipe families. The auto_script render path is
also tested at ``apps.scripts.tests.test_api.test_render_fires_auto_script_composition``.
This file covers the *gallery-discovery* shape that's unique
to B-2.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.recipes import RECIPES, get_recipe, resolve_kwargs
from apps.scripts.models import Script
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_teammate(ws: Workspace, *, name: str = "Marcus") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


def _make_script(
    ws: Workspace,
    sp: Teammate,
    *,
    status: str = "ready",
    draft_text: str = "approved draft",
) -> Script:
    return Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="x", prompt="x",
        draft_text=draft_text,
        status=status,
    )


# ---- registry shape --------------------------------------------


def test_auto_script_registered_in_recipes() -> None:
    """B2.4 — the recipe surfaces in the gallery (Q-e-11)."""
    assert "auto_script" in RECIPES
    recipe = get_recipe("auto_script")
    assert recipe.kind == "auto_script"
    assert recipe.starter is not None
    assert recipe.starter.__name__ == "auto_script"


def test_auto_script_has_script_picker_field_not_textarea() -> None:
    """Q-e-11 — the form metadata exposes a Script picker
    instead of a free-form textarea. This is the load-bearing
    UX bet that distinguishes auto_script from talking_head.
    """
    recipe = get_recipe("auto_script")
    field_names = {f.name for f in recipe.fields}
    assert "script_id" in field_names
    # Must NOT carry the free-form fields that would confuse
    # the operator about how to fire this recipe.
    assert "script" not in field_names, (
        "auto_script must not expose a 'script' textarea — the "
        "script comes from the picked Script row"
    )
    assert "spokesperson_id" not in field_names, (
        "auto_script gets the spokesperson from the Script row; "
        "no separate picker"
    )
    assert "use_knowledge" not in field_names, (
        "K6 already ran at draft-time per rule 7; the recipe must "
        "not let the operator re-enable in-primitive synthesis"
    )

    script_field = next(
        f for f in recipe.fields if f.name == "script_id"
    )
    assert script_field.type == "script_picker"
    assert script_field.required is True


# ---- API surface -----------------------------------------------


def test_get_recipes_lists_auto_script() -> None:
    user, _ws = _make_user_workspace("b24list@test")
    client = APIClient()
    _login(client, user)

    res = client.get("/api/recipes/")
    assert res.status_code == http.HTTP_200_OK
    kinds = {item["kind"] for item in res.json()}
    assert "auto_script" in kinds


def test_get_recipe_auto_script_detail() -> None:
    user, _ws = _make_user_workspace("b24detail@test")
    client = APIClient()
    _login(client, user)

    res = client.get("/api/recipes/auto_script/")
    assert res.status_code == http.HTTP_200_OK
    data = res.json()
    assert data["kind"] == "auto_script"
    assert data["family"] == "talking_head"
    field_types = {f["type"] for f in data["fields"]}
    assert "script_picker" in field_types


# ---- script_picker resolution ----------------------------------


def test_script_picker_resolves_ready_script_to_row() -> None:
    _, ws = _make_user_workspace("b24picker@test")
    sp = _make_teammate(ws)
    script = _make_script(ws, sp, status="ready")

    recipe = get_recipe("auto_script")
    kwargs = resolve_kwargs(
        recipe,
        workspace=ws,
        params={"script_id": str(script.pk)},
        created_by=None,
    )
    assert kwargs["script"] == script
    assert kwargs["workspace"] == ws


def test_script_picker_rejects_draft_script() -> None:
    """Q-e-11 — picker filters to status=READY. A DRAFT script
    must not flow through (operator hasn't approved it)."""
    _, ws = _make_user_workspace("b24draft@test")
    sp = _make_teammate(ws)
    script = _make_script(ws, sp, status="draft")

    recipe = get_recipe("auto_script")
    with pytest.raises(Script.DoesNotExist):
        resolve_kwargs(
            recipe,
            workspace=ws,
            params={"script_id": str(script.pk)},
            created_by=None,
        )


def test_script_picker_rejects_rendered_script() -> None:
    """RENDERED is past-READY in the state machine. Already-
    rendered scripts can be picked into a NEW render too —
    rule 8 says scripts are reusable. But the picker's status
    filter is READY-only; rendered scripts surface through
    different UX (re-render from the Script detail page, not
    the gallery picker).
    """
    _, ws = _make_user_workspace("b24rendered@test")
    sp = _make_teammate(ws)
    script = _make_script(ws, sp, status="rendered")

    recipe = get_recipe("auto_script")
    with pytest.raises(Script.DoesNotExist):
        resolve_kwargs(
            recipe,
            workspace=ws,
            params={"script_id": str(script.pk)},
            created_by=None,
        )


def test_script_picker_rejects_cross_workspace_script() -> None:
    _, ws_a = _make_user_workspace("b24xwa@test")
    _, ws_b = _make_user_workspace("b24xwb@test")
    sp_b = _make_teammate(ws_b)
    script_b = _make_script(ws_b, sp_b, status="ready")

    recipe = get_recipe("auto_script")
    with pytest.raises(Script.DoesNotExist):
        resolve_kwargs(
            recipe,
            workspace=ws_a,  # different workspace
            params={"script_id": str(script_b.pk)},
            created_by=None,
        )


def test_script_picker_rejects_unknown_id() -> None:
    _, ws = _make_user_workspace("b24unknown@test")
    recipe = get_recipe("auto_script")
    with pytest.raises(Script.DoesNotExist):
        resolve_kwargs(
            recipe,
            workspace=ws,
            params={"script_id": str(uuid.uuid4())},
            created_by=None,
        )
