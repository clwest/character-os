"""B2.3 — REST surface tests for the B-2 / E-arc auto-scripting.

Five groups:

1. **CRUD** — create / list / retrieve / destroy.
2. **Regenerate** — snapshots, prompt override, refusal on
   RENDERED.
3. **Approve** — DRAFT → READY, blocked verification refused.
4. **Render** — fires auto_script Composition, flips → RENDERED.
5. **Clone + tier-gate + cross-workspace isolation**.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import Composition
from apps.scripts.models import Script
from apps.scripts.synthesis import ScriptDraftResult
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_celery_dispatch():
    """Patch execute_composition.delay so no broker is needed
    in the render action tests."""
    with patch("apps.compositions.tasks.execute_composition.delay") as p:
        yield p


@pytest.fixture(autouse=True)
def _force_mock_synthesis():
    """draft_script runs under force-mock so tests don't burn
    OpenAI credits. Mock mode is deterministic + fast."""
    with override_settings(RENDER_SCRIPT_FORCE_MOCK=True):
        yield


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_teammate(
    ws: Workspace, *, name: str = "Marcus", brief: str = "Test."
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief=brief,
    )


# ---- create -----------------------------------------------------


def test_create_script_fires_draft_and_returns_201() -> None:
    user, ws = _make_user_workspace("b23create@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)

    res = client.post("/api/scripts/", {
        "spokesperson_id": str(sp.pk),
        "name": "Q3 launch",
        "prompt": "30 seconds about our new pricing tiers.",
    }, format="json")

    assert res.status_code == http.HTTP_201_CREATED, res.content
    data = res.json()
    assert data["status"] == "draft"
    assert data["name"] == "Q3 launch"
    assert "draft_text" in data and data["draft_text"]
    assert data["spokesperson_id"] == str(sp.pk)

    # Persisted with status=DRAFT + draft populated.
    script = Script.objects.get(pk=data["id"])
    assert script.status == Script.Status.DRAFT
    assert script.draft_text
    assert script.created_by == user


def test_create_script_with_blank_name_falls_back_to_default() -> None:
    user, ws = _make_user_workspace("b23createblank@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)

    res = client.post("/api/scripts/", {
        "spokesperson_id": str(sp.pk),
        "name": "   ",
        "prompt": "topic",
    }, format="json")
    assert res.status_code == http.HTTP_201_CREATED
    assert res.json()["name"] == "Untitled script"


def test_create_script_rejects_unknown_spokesperson() -> None:
    user, _ = _make_user_workspace("b23unksp@test")
    client = APIClient()
    _login(client, user)

    res = client.post("/api/scripts/", {
        "spokesperson_id": str(uuid.uuid4()),
        "name": "x",
        "prompt": "topic",
    }, format="json")
    assert res.status_code == http.HTTP_404_NOT_FOUND


def test_create_script_rejects_cross_workspace_spokesperson() -> None:
    """Rule 1 — spokesperson must live in the user's workspace."""
    user_a, _ws_a = _make_user_workspace("b23xworks_a@test")
    _, ws_b = _make_user_workspace("b23xworks_b@test")
    sp_b = _make_teammate(ws_b, name="Bob")
    client = APIClient()
    _login(client, user_a)

    res = client.post("/api/scripts/", {
        "spokesperson_id": str(sp_b.pk),
        "name": "leaky",
        "prompt": "topic",
    }, format="json")
    assert res.status_code == http.HTTP_404_NOT_FOUND


def test_create_script_rejects_invalid_verifier_mode() -> None:
    user, ws = _make_user_workspace("b23badmode@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)

    res = client.post("/api/scripts/", {
        "spokesperson_id": str(sp.pk),
        "name": "x",
        "prompt": "topic",
        "verifier_mode": "loud",
    }, format="json")
    assert res.status_code == http.HTTP_400_BAD_REQUEST


# ---- list / retrieve -------------------------------------------


def test_list_filters_to_workspace_scripts() -> None:
    user_a, ws_a = _make_user_workspace("b23list_a@test")
    _, ws_b = _make_user_workspace("b23list_b@test")
    sp_a = _make_teammate(ws_a)
    sp_b = _make_teammate(ws_b)
    Script.objects.create(workspace=ws_a, spokesperson=sp_a, name="a", prompt="x")
    Script.objects.create(workspace=ws_b, spokesperson=sp_b, name="b", prompt="x")
    client = APIClient()
    _login(client, user_a)

    res = client.get("/api/scripts/")
    assert res.status_code == http.HTTP_200_OK
    names = [item["name"] for item in res.json()]
    assert names == ["a"]


def test_list_filterable_by_status() -> None:
    user, ws = _make_user_workspace("b23filter@test")
    sp = _make_teammate(ws)
    Script.objects.create(
        workspace=ws, spokesperson=sp, name="d", prompt="x",
        status=Script.Status.DRAFT,
    )
    Script.objects.create(
        workspace=ws, spokesperson=sp, name="r", prompt="x",
        status=Script.Status.READY,
    )
    client = APIClient()
    _login(client, user)

    res = client.get("/api/scripts/?status=ready")
    assert res.status_code == http.HTTP_200_OK
    names = [item["name"] for item in res.json()]
    assert names == ["r"]


def test_retrieve_detail_returns_cited_documents_field() -> None:
    user, ws = _make_user_workspace("b23retrieve@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
    )
    client = APIClient()
    _login(client, user)

    res = client.get(f"/api/scripts/{s.pk}/")
    assert res.status_code == http.HTTP_200_OK
    assert "cited_documents" in res.json()


# ---- regenerate ------------------------------------------------


def test_regenerate_snapshots_and_resets_to_draft() -> None:
    user, ws = _make_user_workspace("b23regen@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="x", prompt="first prompt",
        draft_text="initial draft", model="gpt-5",
        status=Script.Status.READY,
    )
    client = APIClient()
    _login(client, user)

    res = client.post(
        f"/api/scripts/{s.pk}/regenerate/",
        {"prompt": "new prompt"},
        format="json",
    )
    assert res.status_code == http.HTTP_200_OK
    data = res.json()
    assert data["status"] == "draft", "regenerate should snap READY → DRAFT"
    assert data["prompt"] == "new prompt"
    s.refresh_from_db()
    assert len(s.revision_history) == 1
    assert s.revision_history[0]["draft_text"] == "initial draft"


def test_regenerate_refuses_rendered() -> None:
    """Rule 10 — RENDERED rows are immutable; clone first."""
    user, ws = _make_user_workspace("b23rendered@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        status=Script.Status.RENDERED,
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/regenerate/", {}, format="json")
    assert res.status_code == http.HTTP_409_CONFLICT


# ---- approve ---------------------------------------------------


def test_approve_flips_draft_to_ready() -> None:
    user, ws = _make_user_workspace("b23approve@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        draft_text="ready to ship",
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/approve/", {}, format="json")
    assert res.status_code == http.HTTP_200_OK
    s.refresh_from_db()
    assert s.status == Script.Status.READY
    assert s.approved_at is not None


def test_approve_refuses_blocked_verification() -> None:
    """Rule 4 — blocked drafts must regenerate before approving."""
    user, ws = _make_user_workspace("b23blockedapprove@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        draft_text="hallucinated", verification_status="blocked",
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/approve/", {}, format="json")
    assert res.status_code == http.HTTP_409_CONFLICT
    assert res.json().get("code") == "verification_blocked"


def test_approve_refuses_already_ready() -> None:
    user, ws = _make_user_workspace("b23alreadyready@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        status=Script.Status.READY,
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/approve/", {}, format="json")
    assert res.status_code == http.HTTP_409_CONFLICT


# ---- render ----------------------------------------------------


def test_render_fires_auto_script_composition(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b23render@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="render me",
        prompt="x", draft_text="approved draft",
        knowledge_chunk_ids=["c1", "c2"],
        status=Script.Status.READY,
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/render/", {}, format="json")
    assert res.status_code == http.HTTP_200_OK, res.content
    data = res.json()
    assert "composition_id" in data

    comp = Composition.objects.get(pk=data["composition_id"])
    assert comp.template_kind == "auto_script"
    assert comp.synthesized_brief == "approved draft"
    assert comp.knowledge_chunk_ids == ["c1", "c2"]
    assert comp.spokesperson == sp
    # Step 0 should have the draft baked in + use_knowledge=False.
    step = comp.steps.first()
    assert step is not None
    assert step.primitive == "generate_avatar_speech"
    assert step.params["script"] == "approved draft"
    assert step.params["use_knowledge"] is False

    # Script flipped to RENDERED.
    s.refresh_from_db()
    assert s.status == Script.Status.RENDERED

    # Celery enqueue fired once.
    assert _no_celery_dispatch.called


def test_render_refuses_unapproved_script() -> None:
    user, ws = _make_user_workspace("b23renderdraft@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        draft_text="x", status=Script.Status.DRAFT,
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/render/", {}, format="json")
    assert res.status_code == http.HTTP_409_CONFLICT


def test_render_refuses_empty_draft() -> None:
    user, ws = _make_user_workspace("b23renderempty@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        draft_text="", status=Script.Status.READY,
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{s.pk}/render/", {}, format="json")
    assert res.status_code == http.HTTP_400_BAD_REQUEST


# ---- clone -----------------------------------------------------


def test_clone_creates_fresh_draft_with_source_prompt() -> None:
    user, ws = _make_user_workspace("b23clone@test")
    sp = _make_teammate(ws)
    source = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="Q3", prompt="pricing",
        status=Script.Status.RENDERED,  # immutable; clone is the way
    )
    client = APIClient()
    _login(client, user)

    res = client.post(f"/api/scripts/{source.pk}/clone/", {}, format="json")
    assert res.status_code == http.HTTP_201_CREATED
    data = res.json()
    assert data["status"] == "draft"
    assert data["prompt"] == "pricing"
    assert data["id"] != str(source.pk)
    assert "(clone)" in data["name"]


# ---- destroy ---------------------------------------------------


def test_destroy_refuses_rendered() -> None:
    user, ws = _make_user_workspace("b23destroy@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        status=Script.Status.RENDERED,
    )
    client = APIClient()
    _login(client, user)

    res = client.delete(f"/api/scripts/{s.pk}/")
    assert res.status_code == http.HTTP_409_CONFLICT
    # Still there.
    assert Script.objects.filter(pk=s.pk).exists()


def test_destroy_draft_cascade_succeeds() -> None:
    user, ws = _make_user_workspace("b23destroydraft@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
    )
    client = APIClient()
    _login(client, user)

    res = client.delete(f"/api/scripts/{s.pk}/")
    assert res.status_code == http.HTTP_204_NO_CONTENT
    assert not Script.objects.filter(pk=s.pk).exists()


# ---- tier gate -------------------------------------------------


def test_create_tier_gates_at_drafts_per_month_cap() -> None:
    """Rule per Q-e-9 — Starter=10 drafts/month."""
    user, ws = _make_user_workspace("b23tier@test")
    sp = _make_teammate(ws)
    # Seed 10 existing scripts in the current period.
    for i in range(10):
        Script.objects.create(
            workspace=ws, spokesperson=sp,
            name=f"x{i}", prompt="x",
        )
    client = APIClient()
    _login(client, user)

    res = client.post("/api/scripts/", {
        "spokesperson_id": str(sp.pk),
        "name": "11th draft",
        "prompt": "topic",
    }, format="json")
    assert res.status_code == http.HTTP_402_PAYMENT_REQUIRED
    assert res.json()["code"] == "draft_limit_reached"


def test_regenerate_counts_against_tier_gate() -> None:
    """Each regenerate snapshots to revision_history; the
    period-windowed sum of those snapshots PLUS in-period
    creates is the tier-gate count."""
    user, ws = _make_user_workspace("b23regentier@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp, name="x", prompt="x",
        draft_text="initial", model="gpt-5",
    )
    # Pre-seed 9 revision snapshots; with the 1 initial create
    # that's 10 drafts in the current period — Starter's cap.
    from django.utils import timezone
    now_iso = timezone.now().isoformat()
    s.revision_history = [
        {
            "ts": now_iso, "draft_text": f"v{i}", "prompt": "x",
            "opener": "", "knowledge_chunk_ids": [],
            "model": "gpt-5", "verification_status": "warned",
            "verification_warnings": [],
            "tokens_input": 0, "tokens_output": 0,
        }
        for i in range(9)
    ]
    s.save()

    client = APIClient()
    _login(client, user)
    res = client.post(
        f"/api/scripts/{s.pk}/regenerate/",
        {"prompt": "another"},
        format="json",
    )
    assert res.status_code == http.HTTP_402_PAYMENT_REQUIRED
    assert res.json()["code"] == "draft_limit_reached"


# ---- BC3 — derived_campaigns endpoint ----------------------------


def test_derived_campaigns_returns_workspace_filtered_list() -> None:
    """BC3 / BC0 rule 1 — Script→Campaign reverse query works
    via the related_name='derived_campaigns' on the FK. No back-
    reference field on Script needed."""
    from apps.campaigns.models import PersonalizedCampaign

    user, ws = _make_user_workspace("bc3der@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="src", prompt="x",
        draft_text="Hi {n}",
        knowledge_chunk_ids=["c1"],
        status="ready",
    )
    # Two campaigns derive from this Script.
    c1 = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="C1", template="Hi {n}", placeholders=["n"],
        source_script=s, created_by=user,
    )
    c2 = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="C2", template="Hi {n}", placeholders=["n"],
        source_script=s, created_by=user,
    )
    # One unrelated campaign (no source_script).
    PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="unrelated", template="Hi", placeholders=[],
        created_by=user,
    )

    client = APIClient()
    _login(client, user)
    res = client.get(f"/api/scripts/{s.pk}/derived_campaigns/")
    assert res.status_code == http.HTTP_200_OK
    rows = res.json()
    assert len(rows) == 2
    ids = {r["id"] for r in rows}
    assert ids == {str(c1.pk), str(c2.pk)}


def test_derived_campaigns_empty_when_no_derivations() -> None:
    """BC3 — Script with zero derived Campaigns returns []."""
    user, ws = _make_user_workspace("bc3derempty@test")
    sp = _make_teammate(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="lonely", prompt="x",
        draft_text="Hi", status="ready",
    )
    client = APIClient()
    _login(client, user)
    res = client.get(f"/api/scripts/{s.pk}/derived_campaigns/")
    assert res.status_code == http.HTTP_200_OK
    assert res.json() == []
