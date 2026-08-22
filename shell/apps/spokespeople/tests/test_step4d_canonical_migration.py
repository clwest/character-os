"""§19 Step 4.d — Production mirror-write migration coverage.

After 4.d, every production write of the three ``Teammate``
compatibility mirrors (``portrait_path`` / ``voice_id`` /
``runway_avatar_id``) routes through
``apps.identity.services.record_prequalification_representation``.
Provider calls stay where they are; only the persistence changes.

Coverage in this module:

* ``perform_create`` — canonical write on the wizard success path;
  runway_avatar_status + status remain direct writes.
* ``clone_voice`` preset + clone paths — canonical write for voice;
  D1 refusal (409 ``portrait_required``) for voice-only authoring on
  a portrait-less teammate.
* ``change_voice`` — canonical write regardless of media-engine PATCH
  result; D1 refusal on portrait-less.
* ``rebake_avatar`` — voice_id no longer written pre-bake (D2 drop);
  full canonical write on bake success.
* ``refresh_portrait`` — canonical write with the fresh URL.
* Direct-write regression gate — no ``.py`` under
  ``shell/apps/**/`` writes ``.portrait_path`` / ``.voice_id`` /
  ``.runway_avatar_id`` outside the sanctioned allowlist.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    PrequalificationProvenance,
    PrequalificationSourceCall,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from character_os.clients.media_engine import (
    AvatarCreateResult,
    PortraitCreateResult,
    VoiceCloneResult,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# =====================================================================
# Fixtures
# =====================================================================


def _make_workspace(email: str):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _universe(ws: Workspace, name: str = "Test World") -> Universe:
    """SESSION 277 Slice 5 — helper. New teammate API creates now
    require a Universe (``universe_required_on_create``); tests that
    POST to /api/spokespeople/ must supply one. Direct
    ``Teammate.objects.create(...)`` calls bypass the serializer."""
    return Universe.objects.create(workspace=ws, name=name)


def _fake_avatar_client(
    *,
    avatar_id: str = "av_test_123",
    mock_mode: bool = True,
    thumbnail_url: str = "https://runway/thumb.png",
):
    fake = MagicMock()
    fake.create_avatar.return_value = AvatarCreateResult(
        avatar_id=avatar_id,
        status="mock" if mock_mode else "ready",
        thumbnail_url=thumbnail_url,
        mock_mode=mock_mode,
    )
    fake.persist_avatar_portrait.return_value = None  # skip persist path
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


def _fake_clone_client(*, voice_id: str = "clone_abc"):
    fake = MagicMock()
    fake.clone_voice.return_value = VoiceCloneResult(
        voice_id=voice_id,
        status="mock",
        preview_url=None,
        mock_mode=True,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


def _fake_change_voice_client(*, status_str: str = "ready"):
    fake = MagicMock()
    fake.change_avatar_voice.return_value = {"status": status_str, "error": None}
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


def _fake_rebake_client(
    *,
    avatar_id: str = "av_new_456",
    thumbnail_url: str = "https://runway/newthumb.png",
    mock_mode: bool = True,
):
    fake = MagicMock()
    fake.create_portrait.return_value = PortraitCreateResult(
        portrait_data_uri="data:image/png;base64,fake",
        template="mascot",
        prompt="(mock)",
        mock_mode=mock_mode,
    )
    fake.create_avatar.return_value = AvatarCreateResult(
        avatar_id=avatar_id,
        status="mock" if mock_mode else "ready",
        thumbnail_url=thumbnail_url,
        mock_mode=mock_mode,
    )
    fake.persist_avatar_portrait.return_value = None
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# =====================================================================
# perform_create
# =====================================================================


def test_perform_create_routes_mirrors_through_canonical() -> None:
    ws, user = _make_workspace("pc-canonical@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    portrait_uri = "data:image/png;base64,abc"
    cm, fake = _fake_avatar_client(avatar_id="av_pc_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        resp = client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Ada",
                "business_brief": "brief",
                "portrait_data_uri": portrait_uri,
                "voice_preset": "vincent",
            },
            format="json",
        )
    assert resp.status_code == http.HTTP_201_CREATED, resp.json()
    teammate = Teammate.objects.get(name="Ada")
    # Canonical state exists.
    identity = CharacterIdentity.objects.get(teammate=teammate)
    version = CharacterIdentityVersion.objects.get(
        identity=identity, state=CharacterIdentityVersion.State.APPROVED,
    )
    prov = PrequalificationProvenance.objects.get(identity_version=version)
    assert prov.source_call == PrequalificationSourceCall.WIZARD_CREATE
    # Mirrors written via sync (not directly).
    assert teammate.voice_id == "vincent"
    assert teammate.runway_avatar_id == "av_pc_001"
    # SESSION 228 rule: reference image (portrait_data_uri) preferred.
    assert teammate.portrait_path == portrait_uri
    # Non-mirror status field set.
    assert teammate.status == Teammate.Status.READY
    assert teammate.runway_avatar_status == "mock"


def test_perform_create_without_portrait_skips_canonical() -> None:
    """No portrait_data_uri → no media-engine call → no canonical
    write. Teammate lands as SETUP_NEEDED with empty mirrors.
    """
    ws, user = _make_workspace("pc-no-portrait@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(ws.pk),
            "universe": str(u.id),
            "name": "NoPortrait",
            "business_brief": "brief",
        },
        format="json",
    )
    assert resp.status_code == http.HTTP_201_CREATED, resp.json()
    teammate = Teammate.objects.get(name="NoPortrait")
    assert teammate.portrait_path == ""
    assert teammate.voice_id == ""
    assert teammate.runway_avatar_id == ""
    assert not CharacterIdentity.objects.filter(teammate=teammate).exists()


# =====================================================================
# clone_voice — D1 portrait_required refusal + canonical apply
# =====================================================================


def test_clone_voice_preset_refuses_portrait_less_teammate_with_409() -> None:
    ws, user = _make_workspace("cvp-no-portrait@t")
    client = APIClient()
    client.force_authenticate(user)

    teammate = Teammate.objects.create(workspace=ws, name="NoPortrait")

    resp = client.post(
        f"/api/spokespeople/{teammate.id}/clone-voice/",
        data={"preset": "vincent"},
        format="json",
    )
    assert resp.status_code == http.HTTP_409_CONFLICT, resp.json()
    body = resp.json()
    assert body["code"] == "portrait_required"
    # Mirror unchanged.
    teammate.refresh_from_db()
    assert teammate.voice_id == ""


def test_clone_voice_preset_succeeds_after_portrait_authoring() -> None:
    ws, user = _make_workspace("cvp-with-portrait@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    cm, _ = _fake_avatar_client(avatar_id="av_cvp_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        create_resp = client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Beth",
                "business_brief": "b",
                "portrait_data_uri": "data:image/png;base64,x",
                "voice_preset": "vincent",
            },
            format="json",
        )
    assert create_resp.status_code == http.HTTP_201_CREATED
    teammate = Teammate.objects.get(name="Beth")

    resp = client.post(
        f"/api/spokespeople/{teammate.id}/clone-voice/",
        data={"preset": "marcus"},
        format="json",
    )
    assert resp.status_code == http.HTTP_200_OK, resp.json()
    teammate.refresh_from_db()
    assert teammate.voice_id == "marcus"


def test_clone_voice_clone_path_persists_via_canonical() -> None:
    ws, user = _make_workspace("cvc-with-portrait@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    cm, _ = _fake_avatar_client(avatar_id="av_cvc_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Cara",
                "business_brief": "b",
                "portrait_data_uri": "data:image/png;base64,x",
                "voice_preset": "vincent",
            },
            format="json",
        )
    teammate = Teammate.objects.get(name="Cara")

    cm2, _ = _fake_clone_client(voice_id="voice_new_xyz")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm2):
        resp = client.post(
            f"/api/spokespeople/{teammate.id}/clone-voice/",
            data={"audio_data_uri": "data:audio/wav;base64,fake"},
            format="json",
        )
    assert resp.status_code == http.HTTP_200_OK, resp.json()
    teammate.refresh_from_db()
    assert teammate.voice_id == "voice_new_xyz"


# =====================================================================
# change_voice
# =====================================================================


def test_change_voice_refuses_portrait_less_teammate_with_409() -> None:
    ws, user = _make_workspace("cv-no-portrait@t")
    client = APIClient()
    client.force_authenticate(user)

    teammate = Teammate.objects.create(workspace=ws, name="D")

    resp = client.post(
        f"/api/spokespeople/{teammate.id}/change-voice/",
        data={"preset": "vincent"},
        format="json",
    )
    assert resp.status_code == http.HTTP_409_CONFLICT, resp.json()
    assert resp.json()["code"] == "portrait_required"


def test_change_voice_persists_via_canonical_even_when_patch_fails() -> None:
    """Media-engine change-voice PATCH failure must not skip the
    canonical persist — the operator's intent should still land as
    identity state (matches pre-4.d "persist regardless" behavior).
    """
    ws, user = _make_workspace("cv-patch-fail@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    cm, _ = _fake_avatar_client(avatar_id="av_cv_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Ellis",
                "business_brief": "b",
                "portrait_data_uri": "data:image/png;base64,x",
                "voice_preset": "vincent",
            },
            format="json",
        )
    teammate = Teammate.objects.get(name="Ellis")

    fake = MagicMock()
    fake.change_avatar_voice.return_value = {
        "status": "failed",
        "error": "Runway 500",
    }
    cm2 = MagicMock()
    cm2.__enter__.return_value = fake
    cm2.__exit__.return_value = False

    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm2):
        resp = client.post(
            f"/api/spokespeople/{teammate.id}/change-voice/",
            data={"preset": "clara"},
            format="json",
        )
    assert resp.status_code == http.HTTP_200_OK
    teammate.refresh_from_db()
    assert teammate.voice_id == "clara"
    assert resp.json()["voice_patch"]["status"] == "failed"


# =====================================================================
# rebake_avatar
# =====================================================================


def test_rebake_avatar_landed_pre_bake_save_drops_voice_id() -> None:
    """D2 discipline: pre-bake save persists non-mirror
    visual_subject + visual_template only. If the bake later fails,
    voice_id stays canonically consistent with the last successful
    authoring event, not overwritten by the failed intent.
    """
    ws, user = _make_workspace("rb-pre@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    # Establish canonical state via first perform_create.
    cm_create, _ = _fake_avatar_client(avatar_id="av_rb_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm_create):
        client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Frida",
                "business_brief": "b",
                "portrait_data_uri": "data:image/png;base64,x",
                "voice_preset": "vincent",
                "visual_template": "mascot",
                "visual_subject": "battle unicorn",
            },
            format="json",
        )
    teammate = Teammate.objects.get(name="Frida")
    assert teammate.voice_id == "vincent"

    # Rebake with a NEW voice preset AND a failing media-engine.
    fake = MagicMock()
    fake.create_portrait.return_value = PortraitCreateResult(
        portrait_data_uri="data:image/png;base64,fake",
        template="mascot",
        prompt="(mock)",
        mock_mode=True,
    )
    fake.create_avatar.side_effect = __import__(
        "character_os.clients.media_engine",
        fromlist=["MediaEngineError"],
    ).MediaEngineError("simulated bake failure")
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        resp = client.post(
            f"/api/spokespeople/{teammate.id}/rebake-avatar/",
            data={"voice_preset": "clara"},  # requested but never lands
            format="json",
        )
    # 502 from bake failure.
    assert resp.status_code == http.HTTP_502_BAD_GATEWAY, resp.json()
    teammate.refresh_from_db()
    # voice_id preserved (not overwritten by the failed intent).
    assert teammate.voice_id == "vincent"


def test_rebake_avatar_success_routes_all_three_mirrors_through_canonical() -> None:
    ws, user = _make_workspace("rb-success@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    cm_create, _ = _fake_avatar_client(avatar_id="av_rb2_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm_create):
        client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Gray",
                "business_brief": "b",
                "portrait_data_uri": "data:image/png;base64,x",
                "voice_preset": "vincent",
                "visual_template": "mascot",
                "visual_subject": "friendly mascot",
            },
            format="json",
        )
    teammate = Teammate.objects.get(name="Gray")

    cm_rebake, _ = _fake_rebake_client(avatar_id="av_rb2_new")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm_rebake):
        resp = client.post(
            f"/api/spokespeople/{teammate.id}/rebake-avatar/",
            data={"voice_preset": "marcus"},
            format="json",
        )
    assert resp.status_code == http.HTTP_200_OK, resp.json()
    teammate.refresh_from_db()
    assert teammate.runway_avatar_id == "av_rb2_new"
    assert teammate.voice_id == "marcus"
    # New canonical version landed (not the initial one).
    identity = CharacterIdentity.objects.get(teammate=teammate)
    approved_count = CharacterIdentityVersion.objects.filter(
        identity=identity, state=CharacterIdentityVersion.State.APPROVED,
    ).count()
    assert approved_count == 1
    versions_total = CharacterIdentityVersion.objects.filter(
        identity=identity,
    ).count()
    assert versions_total == 2  # create + rebake


# =====================================================================
# refresh_portrait
# =====================================================================


def test_refresh_portrait_refuses_pre_backfill_teammate_with_409() -> None:
    """§19 Step 4.d correction — a teammate that has
    ``runway_avatar_id`` set but was never imported into the
    canonical substrate (no ``CharacterIdentity``) triggers the
    canonical bundle-approval invariant. Under the ratified
    correction, the endpoint returns HTTP 409 with a stable domain
    code (``canonical_identity_required``) rather than a silent 200
    or a misleading 502. The correct remediation is running
    ``backfill_identity_substrate``.
    """
    ws, user = _make_workspace("rp-pre-backfill@t")
    client = APIClient()
    client.force_authenticate(user)

    # Pre-4.d shape: direct Teammate row with runway_avatar_id but
    # no canonical identity underneath.
    teammate = Teammate.objects.create(
        workspace=ws,
        name="LegacyRow",
        runway_avatar_id="av_legacy_123",
        runway_avatar_status="ready",
        portrait_path="https://old/portrait.png",
    )

    fake = MagicMock()
    fake.refresh_avatar_thumbnail.return_value = "https://runway/refreshed.png"
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        resp = client.post(
            f"/api/spokespeople/{teammate.id}/refresh-portrait/",
            format="json",
        )
    assert resp.status_code == http.HTTP_409_CONFLICT, resp.json()
    body = resp.json()
    assert body["code"] == "canonical_identity_required"
    assert "backfill_identity_substrate" in body["error"]

    # No canonical state manufactured, no mirror mutation.
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://old/portrait.png"
    assert not CharacterIdentity.objects.filter(teammate=teammate).exists()


def test_refresh_portrait_creates_new_version_on_success() -> None:
    ws, user = _make_workspace("rp-success@t")
    u = _universe(ws)
    client = APIClient()
    client.force_authenticate(user)

    cm_create, _ = _fake_avatar_client(avatar_id="av_rp_001")
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm_create):
        client.post(
            "/api/spokespeople/",
            data={
                "workspace": str(ws.pk),
                "universe": str(u.id),
                "name": "Hana",
                "business_brief": "b",
                "portrait_data_uri": "data:image/png;base64,x",
                "voice_preset": "vincent",
            },
            format="json",
        )
    teammate = Teammate.objects.get(name="Hana")

    fake = MagicMock()
    fake.refresh_avatar_thumbnail.return_value = "https://runway/refreshed.png"
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.spokespeople.views.MediaEngineClient", return_value=cm):
        resp = client.post(
            f"/api/spokespeople/{teammate.id}/refresh-portrait/",
            format="json",
        )
    assert resp.status_code == http.HTTP_200_OK, resp.json()
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://runway/refreshed.png"


# =====================================================================
# Direct-write regression gate
# =====================================================================


#: Only these production paths may perform physical assignment to
#: the three ``Teammate`` compatibility mirror fields under §17.10.a
#: Amendment 4 direct-write allowlist. Everything else is
#: historical/migration/test code.
_MIRROR_WRITE_ALLOWLIST = frozenset({
    "apps/identity/compat.py",  # the sanctioned production writer
    "apps/identity/import_service.py",  # Step 3 legacy backfill
})


_MIRROR_ASSIGNMENT_RE = re.compile(
    r"\.(portrait_path|voice_id|runway_avatar_id)\s*="
)


def _iter_apps_py_files():
    apps_root = Path(__file__).resolve().parents[3] / "apps"
    for p in apps_root.rglob("*.py"):
        rel = p.relative_to(apps_root.parent).as_posix()
        yield p, rel


def test_no_direct_mirror_writes_outside_allowlist() -> None:
    """§17.10.a Amendment 4 direct-write discipline (SESSION 243
    4.d gate). Only ``compat.py`` and ``import_service.py`` may
    physically assign to the three compatibility mirror fields in
    production. Tests, migrations, and historical imports are
    exempt.
    """
    offenders: list[str] = []

    for path, rel in _iter_apps_py_files():
        # Test files and migration files are exempt.
        if "/tests/" in rel or "/migrations/" in rel:
            continue
        if rel in _MIRROR_WRITE_ALLOWLIST:
            continue

        source = path.read_text()
        # Fast path: skip files that don't mention any mirror field.
        if not any(
            field in source
            for field in ("portrait_path", "voice_id", "runway_avatar_id")
        ):
            continue

        # Parse the AST and walk every Assign node looking for
        # ``<expr>.portrait_path = ...`` etc. on the LHS.
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Attribute):
                    continue
                if target.attr in {
                    "portrait_path",
                    "voice_id",
                    "runway_avatar_id",
                }:
                    offenders.append(
                        f"{rel}:{node.lineno}  {target.attr}"
                    )

    assert not offenders, (
        "Direct-mirror-write regression — production code outside the "
        "sanctioned allowlist assigns to a Teammate compatibility "
        "mirror. §17.10.a Amendment 4 requires every production write "
        "to route through canonical services + compat.sync_teammate_"
        "mirrors. Offenders:\n"
        + "\n".join(offenders)
    )
