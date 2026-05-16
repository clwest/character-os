"""W11.6.2 — tests for the image generation REST surface.

Covers the five new endpoints introduced by W11.6.2:

* ``POST /api/images/`` — generate + persist for each non-avatar
  purpose. Validates request shape, workspace ownership,
  cross-workspace spokesperson rejection, MediaEngineClient
  failure surface, and Asset-row persistence.
* ``GET /api/images/`` — workspace-scoped list with filters
  (purpose, model, style_preset, spokesperson). Newest first.
* ``GET /api/images/<id>/`` — workspace isolation 404.
* ``DELETE /api/images/<id>/`` — workspace-owner-only.
* ``GET /api/styles/`` — proxy through MediaEngineClient.

MediaEngineClient is patched throughout — no live media-engine
calls. The W11.6.1 mock-mode tests already cover the
media-engine side; these tests verify only the Django layer.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Asset, AssetType
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    StabilityImageResult,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- helpers ------------------------------------------------------


def _make_workspace_with_user(email: str, ws_name: str = "WS"):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = ws_name
    ws.save()
    return ws, user


def _make_spokesperson(
    ws: Workspace, name: str = "Sp", avatar_id: str = "fake-avatar",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=avatar_id,
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _stability_result(
    *,
    purpose: str = "scene",
    model: str = "sd3-large",
    style_preset: str | None = "minimalist",
    aspect_ratio: str = "16:9",
    cost_credits: float = 6.5,
    mock_mode: bool = True,
) -> StabilityImageResult:
    return StabilityImageResult(
        image_data_uri="data:image/png;base64,iVBORw0KGgo=",
        prompt="composed prompt for testing",
        mime_type="image/png",
        cost_credits=cost_credits,
        model=model,
        purpose=purpose,
        style_preset=style_preset,
        aspect_ratio=aspect_ratio,
        mock_mode=mock_mode,
    )


def _patched_client(
    result: StabilityImageResult,
) -> tuple[MagicMock, MagicMock]:
    """Context-manager-shaped MediaEngineClient stub.

    Matches the production usage:
        with MediaEngineClient() as client:
            client.create_stability_image(...)

    Returns ``(context_manager_mock, inner_client_mock)`` — the
    first is what ``patch("...MediaEngineClient", return_value=cm)``
    expects; the second is what the test asserts on.
    """
    fake_client = MagicMock()
    fake_client.create_stability_image.return_value = result
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False
    return cm, fake_client


def _styles_payload() -> dict:
    return {
        "categories": [
            {
                "id": "photography",
                "display_name": "Photography Styles",
                "description": "Realistic, professional photo-based looks",
                "icon": "📷",
                "presets": [
                    {
                        "name": "photorealistic",
                        "display_name": "Photorealistic",
                        "category": "photography",
                        "description": "Ultra-realistic photography quality",
                        "best_for": ["corporate"],
                        "mood": "professional",
                        "example_prompt_suffix": "photorealistic, 8k uhd",
                    },
                ],
            },
        ],
        "total_presets": 42,
    }


# ---- POST /api/images/ — happy paths -----------------------------


@pytest.mark.parametrize("purpose", ["scene", "broll", "product", "ad"])
def test_create_image_per_purpose_persists_asset(purpose: str):
    """Each non-avatar purpose round-trips through the
    MediaEngineClient and lands as an Asset(image) row with all
    image-specific fields populated."""
    ws, user = _make_workspace_with_user(f"img-{purpose}@test")
    api = APIClient()
    _login(api, user)

    result = _stability_result(purpose=purpose)
    cm, fake = _patched_client(result)
    with patch(
        "apps.compositions.views.MediaEngineClient", return_value=cm,
    ):
        resp = api.post(
            "/api/images/",
            {
                "workspace": str(ws.pk),
                "purpose": purpose,
                "subject": f"a subject for {purpose}",
                "model": "sd3-large",
                "style_preset": "minimalist",
                "aspect_ratio": "16:9",
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_201_CREATED, resp.content
    data = resp.json()
    assert data["asset_type"] == AssetType.IMAGE
    assert data["purpose"] == purpose
    assert data["model"] == "sd3-large"
    assert data["style_preset"] == "minimalist"
    assert data["aspect_ratio"] == "16:9"
    assert data["mime_type"] == "image/png"
    assert data["file_path"].startswith("data:image/png;base64,")
    assert data["cost_micros"] == 6500  # 6.5 credits × 1000
    assert data["workspace"] == str(ws.pk)
    assert data["spokesperson"] is None

    # Persisted in DB.
    asset = Asset.objects.get(pk=data["id"])
    assert asset.purpose == purpose
    assert asset.prompt == "composed prompt for testing"

    # MediaEngineClient was called with the expected kwargs.
    fake.create_stability_image.assert_called_once()
    _, kwargs = fake.create_stability_image.call_args
    assert kwargs["purpose"] == purpose
    assert kwargs["subject"] == f"a subject for {purpose}"


def test_create_image_with_spokesperson_link():
    """Optional spokesperson FK threads through end-to-end."""
    ws, user = _make_workspace_with_user("img-sp@test")
    sp = _make_spokesperson(ws)
    api = APIClient()
    _login(api, user)

    cm, _fake = _patched_client(_stability_result())
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {
                "workspace": str(ws.pk),
                "purpose": "broll",
                "subject": "b-roll subject",
                "spokesperson": str(sp.pk),
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_201_CREATED, resp.content
    data = resp.json()
    assert data["spokesperson"] == str(sp.pk)
    asset = Asset.objects.get(pk=data["id"])
    assert asset.spokesperson_id == sp.pk


def test_create_image_persists_original_subject_for_regenerate():
    """W11.6.4 — Asset.subject preserves the operator's pre-
    composition input so the SPA's Regenerate CTA can re-fire
    with the same subject (sending the composed prompt back as
    a new subject would double-apply the purpose framing)."""
    ws, user = _make_workspace_with_user("img-subj@test")
    api = APIClient()
    _login(api, user)

    cm, _fake = _patched_client(_stability_result())
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {
                "workspace": str(ws.pk),
                "purpose": "scene",
                "subject": "a craft brewery owner at sunrise",
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_201_CREATED
    data = resp.json()
    assert data["subject"] == "a craft brewery owner at sunrise"
    asset = Asset.objects.get(pk=data["id"])
    assert asset.subject == "a craft brewery owner at sunrise"


def test_create_image_negative_prompt_override_is_persisted():
    ws, user = _make_workspace_with_user("img-neg@test")
    api = APIClient()
    _login(api, user)

    cm, fake = _patched_client(_stability_result())
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {
                "workspace": str(ws.pk),
                "purpose": "scene",
                "subject": "subject",
                "negative_prompt_override": "no people, no cars",
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_201_CREATED
    asset = Asset.objects.get(pk=resp.json()["id"])
    assert asset.negative_prompt == "no people, no cars"
    _, kwargs = fake.create_stability_image.call_args
    assert kwargs["negative_prompt_override"] == "no people, no cars"


# ---- POST /api/images/ — validation ------------------------------


def test_create_image_rejects_avatar_purpose_for_v1():
    """Contract rule 2 — avatar wizard owns the avatar path in v1.
    The error message points operators to the right surface
    (scene + creature-anatomy preset for cheap iteration)."""
    ws, user = _make_workspace_with_user("img-av@test")
    api = APIClient()
    _login(api, user)

    cm, fake = _patched_client(_stability_result(purpose="avatar"))
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {
                "workspace": str(ws.pk),
                "purpose": "avatar",
                "subject": "any subject",
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_400_BAD_REQUEST
    assert "purpose" in resp.json()
    # Avatar wizard remains untouched — no media-engine call.
    fake.create_stability_image.assert_not_called()


def test_create_image_rejects_unknown_purpose():
    ws, user = _make_workspace_with_user("img-bad@test")
    api = APIClient()
    _login(api, user)
    resp = api.post(
        "/api/images/",
        {"workspace": str(ws.pk), "purpose": "skyline", "subject": "x"},
        format="json",
    )
    assert resp.status_code == http.HTTP_400_BAD_REQUEST


def test_create_image_rejects_invalid_aspect_ratio():
    ws, user = _make_workspace_with_user("img-ar@test")
    api = APIClient()
    _login(api, user)
    resp = api.post(
        "/api/images/",
        {
            "workspace": str(ws.pk),
            "purpose": "scene",
            "subject": "x",
            "aspect_ratio": "42:17",
        },
        format="json",
    )
    assert resp.status_code == http.HTTP_400_BAD_REQUEST


def test_create_image_rejects_unsupported_model():
    ws, user = _make_workspace_with_user("img-md@test")
    api = APIClient()
    _login(api, user)
    resp = api.post(
        "/api/images/",
        {
            "workspace": str(ws.pk),
            "purpose": "scene",
            "subject": "x",
            "model": "dall-e-99",
        },
        format="json",
    )
    assert resp.status_code == http.HTTP_400_BAD_REQUEST


def test_create_image_requires_subject_and_workspace():
    ws, user = _make_workspace_with_user("img-req@test")
    api = APIClient()
    _login(api, user)
    resp = api.post(
        "/api/images/",
        {"workspace": str(ws.pk), "purpose": "scene"},
        format="json",
    )
    assert resp.status_code == http.HTTP_400_BAD_REQUEST


def test_create_image_rejects_cross_workspace_spokesperson():
    ws_a, user_a = _make_workspace_with_user("img-xsp-a@test", "A")
    ws_b, _user_b = _make_workspace_with_user("img-xsp-b@test", "B")
    foreign_sp = _make_spokesperson(ws_b)
    api = APIClient()
    _login(api, user_a)

    cm, fake = _patched_client(_stability_result())
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {
                "workspace": str(ws_a.pk),
                "purpose": "scene",
                "subject": "x",
                "spokesperson": str(foreign_sp.pk),
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_400_BAD_REQUEST
    fake.create_stability_image.assert_not_called()


def test_create_image_non_member_403():
    ws_a, user_a = _make_workspace_with_user("img-mem-a@test", "A")
    _ws_b, user_b = _make_workspace_with_user("img-mem-b@test", "B")
    api = APIClient()
    _login(api, user_b)

    cm, _fake = _patched_client(_stability_result())
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {"workspace": str(ws_a.pk), "purpose": "scene", "subject": "x"},
            format="json",
        )

    assert resp.status_code in {
        http.HTTP_403_FORBIDDEN, http.HTTP_400_BAD_REQUEST,
    }


def test_create_image_non_owner_403():
    """Editor / Viewer roles can read images but not generate."""
    ws, owner = _make_workspace_with_user("img-own@test")
    editor = User.objects.create_user(email="img-ed@test", password="x")
    Membership.objects.create(user=editor, workspace=ws,
                              role=Membership.Role.EDITOR)
    api = APIClient()
    _login(api, editor)

    cm, _fake = _patched_client(_stability_result())
    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {"workspace": str(ws.pk), "purpose": "scene", "subject": "x"},
            format="json",
        )

    assert resp.status_code == http.HTTP_403_FORBIDDEN


def test_create_image_requires_auth():
    ws, _user = _make_workspace_with_user("img-auth@test")
    api = APIClient()  # not logged in
    resp = api.post(
        "/api/images/",
        {"workspace": str(ws.pk), "purpose": "scene", "subject": "x"},
        format="json",
    )
    assert resp.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_create_image_media_engine_failure_returns_502():
    ws, user = _make_workspace_with_user("img-fail@test")
    api = APIClient()
    _login(api, user)

    fake_client = MagicMock()
    fake_client.create_stability_image.side_effect = MediaEngineError(
        "stability down", status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False

    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.post(
            "/api/images/",
            {"workspace": str(ws.pk), "purpose": "scene", "subject": "x"},
            format="json",
        )

    assert resp.status_code == http.HTTP_502_BAD_GATEWAY
    body = resp.json()
    assert body["code"] == "upstream_media_engine"
    # No Asset row created on upstream failure.
    assert Asset.objects.filter(workspace=ws).count() == 0


# ---- GET /api/images/ — list + filter ----------------------------


def test_list_images_workspace_scoped_with_filters():
    ws_a, user_a = _make_workspace_with_user("img-list-a@test", "A")
    ws_b, _user_b = _make_workspace_with_user("img-list-b@test", "B")

    # Two scene images + one broll in ws_a.
    Asset.objects.create(workspace=ws_a, asset_type=AssetType.IMAGE,
                         purpose="scene", model="sd3-large",
                         style_preset="minimalist", aspect_ratio="16:9",
                         file_path="data:image/png;base64,a")
    Asset.objects.create(workspace=ws_a, asset_type=AssetType.IMAGE,
                         purpose="scene", model="core",
                         style_preset="cyberpunk", aspect_ratio="1:1",
                         file_path="data:image/png;base64,b")
    Asset.objects.create(workspace=ws_a, asset_type=AssetType.IMAGE,
                         purpose="broll", model="sd3-large",
                         file_path="data:image/png;base64,c")
    # One foreign-workspace image — must not leak.
    Asset.objects.create(workspace=ws_b, asset_type=AssetType.IMAGE,
                         purpose="scene", file_path="data:image/png;base64,x")
    # And a non-image asset in ws_a — must not appear in /api/images/.
    Asset.objects.create(workspace=ws_a, asset_type=AssetType.CLIP,
                         file_path="/data/clip.mp4")

    api = APIClient()
    _login(api, user_a)

    # No filters → 3 ws_a images (clip excluded).
    resp = api.get(f"/api/images/?workspace={ws_a.pk}")
    assert resp.status_code == http.HTTP_200_OK
    assert len(resp.json()) == 3

    # Filter by purpose.
    resp = api.get(f"/api/images/?workspace={ws_a.pk}&purpose=scene")
    assert resp.status_code == http.HTTP_200_OK
    purposes = {row["purpose"] for row in resp.json()}
    assert purposes == {"scene"}
    assert len(resp.json()) == 2

    # Filter by model.
    resp = api.get(f"/api/images/?workspace={ws_a.pk}&model=core")
    assert len(resp.json()) == 1
    assert resp.json()[0]["model"] == "core"

    # Filter by style_preset.
    resp = api.get(
        f"/api/images/?workspace={ws_a.pk}&style_preset=cyberpunk",
    )
    assert len(resp.json()) == 1
    assert resp.json()[0]["style_preset"] == "cyberpunk"


def test_list_images_empty_for_workspace_with_no_images():
    ws, user = _make_workspace_with_user("img-empty@test")
    api = APIClient()
    _login(api, user)
    resp = api.get(f"/api/images/?workspace={ws.pk}")
    assert resp.status_code == http.HTTP_200_OK
    assert resp.json() == []


# ---- GET /api/images/<id>/ + DELETE -------------------------------


def test_retrieve_image_cross_workspace_404():
    ws_a, _user_a = _make_workspace_with_user("img-ret-a@test", "A")
    ws_b, user_b = _make_workspace_with_user("img-ret-b@test", "B")
    foreign = Asset.objects.create(
        workspace=ws_a, asset_type=AssetType.IMAGE,
        purpose="scene", file_path="data:image/png;base64,x",
    )
    api = APIClient()
    _login(api, user_b)
    resp = api.get(f"/api/images/{foreign.pk}/")
    assert resp.status_code == http.HTTP_404_NOT_FOUND


def test_delete_image_owner_succeeds_then_404():
    ws, user = _make_workspace_with_user("img-del@test")
    asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        purpose="scene", file_path="data:image/png;base64,x",
    )
    api = APIClient()
    _login(api, user)

    resp = api.delete(f"/api/images/{asset.pk}/")
    assert resp.status_code == http.HTTP_204_NO_CONTENT
    # Gone.
    assert not Asset.objects.filter(pk=asset.pk).exists()
    # Subsequent retrieve is 404.
    resp = api.get(f"/api/images/{asset.pk}/")
    assert resp.status_code == http.HTTP_404_NOT_FOUND


def test_delete_image_non_owner_403():
    ws, owner = _make_workspace_with_user("img-del-o@test")
    editor = User.objects.create_user(email="img-del-ed@test", password="x")
    Membership.objects.create(user=editor, workspace=ws,
                              role=Membership.Role.EDITOR)
    asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        purpose="scene", file_path="data:image/png;base64,x",
    )
    api = APIClient()
    _login(api, editor)
    resp = api.delete(f"/api/images/{asset.pk}/")
    assert resp.status_code == http.HTTP_403_FORBIDDEN
    assert Asset.objects.filter(pk=asset.pk).exists()


# ---- GET /api/styles/ ---------------------------------------------


def test_styles_endpoint_proxies_media_engine():
    _ws, user = _make_workspace_with_user("img-styles@test")
    api = APIClient()
    _login(api, user)

    fake_client = MagicMock()
    fake_client.list_styles.return_value = _styles_payload()
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False

    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.get("/api/styles/")

    assert resp.status_code == http.HTTP_200_OK
    data = resp.json()
    assert data["total_presets"] == 42
    assert data["categories"][0]["id"] == "photography"
    fake_client.list_styles.assert_called_once()


def test_styles_endpoint_requires_auth():
    api = APIClient()  # not logged in
    resp = api.get("/api/styles/")
    assert resp.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_styles_endpoint_502_on_media_engine_failure():
    _ws, user = _make_workspace_with_user("img-styles-fail@test")
    api = APIClient()
    _login(api, user)

    fake_client = MagicMock()
    fake_client.list_styles.side_effect = MediaEngineError(
        "engine down", status_code=None,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False

    with patch("apps.compositions.views.MediaEngineClient", return_value=cm):
        resp = api.get("/api/styles/")

    assert resp.status_code == http.HTTP_502_BAD_GATEWAY
