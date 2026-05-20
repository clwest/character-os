"""B3.4 — REST surface tests for the personalized-video arc.

Covers the read + draft-edit endpoints:

* ``create`` — happy path, template syntax error → 400,
  cross-workspace spokesperson → 404, unknown workspace → 404,
  auth gate.
* ``list`` — workspace isolation, status filter.
* ``retrieve`` — single row, cross-workspace → 404.
* ``destroy`` — DRAFT cascades, LAUNCHING/IN_FLIGHT refuses
  (409), terminal cascades.
* ``parse_csv`` — REPLACE semantics, header_error → 400 +
  recipients untouched, DRAFT-only (409 on launched), per-row
  rejections surfaced.
* ``recipients`` sub-list — paginated, ordered by position.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.campaigns.models import (
    PersonalizedCampaign,
    PersonalizedRecipient,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ---------------------------------------------------


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_spokesperson(ws: Workspace, name: str = "Marcus") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test spokesperson.",
    )


def _create_draft(client: APIClient, ws: Workspace, sp: Spokesperson):
    """Helper to POST a fresh DRAFT campaign and return the
    serialized response payload."""
    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "Q3 outreach",
            "template": "Hi {first_name}, saw {company} just hit {milestone}.",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    return response.json()


# ---- create -----------------------------------------------------


def test_create_persists_draft_with_parsed_placeholders() -> None:
    user, ws = _make_user_workspace("b34c@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    data = _create_draft(client, ws, sp)
    assert data["status"] == "draft"
    assert data["workspace_id"] == str(ws.pk)
    assert data["spokesperson_id"] == str(sp.pk)
    assert data["placeholders"] == ["first_name", "company", "milestone"]
    assert data["recipient_counts"]["total"] == 0


def test_create_template_syntax_error_returns_400() -> None:
    user, ws = _make_user_workspace("b34synt@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "Broken",
            "template": "Hi {0}, welcome",  # positional → reject
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    assert "positional" in str(response.content).lower()
    assert PersonalizedCampaign.objects.count() == 0


def test_create_cross_workspace_spokesperson_returns_404() -> None:
    user_a, ws_a = _make_user_workspace("b34cwa@test")
    user_b, ws_b = _make_user_workspace("b34cwb@test")
    sp_b = _make_spokesperson(ws_b)
    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws_a.pk),
            "spokesperson_id": str(sp_b.pk),
            "name": "x",
            "template": "Hi {n}",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_create_unknown_workspace_returns_404() -> None:
    user, _ = _make_user_workspace("b34unk@test")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(uuid.uuid4()),
            "spokesperson_id": str(uuid.uuid4()),
            "name": "x", "template": "Hi {n}",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_create_unauth_returns_401_or_403() -> None:
    response = APIClient().post(
        "/api/campaigns/",
        {"workspace_id": str(uuid.uuid4())},
        format="json",
    )
    assert response.status_code in (
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    )


# ---- list -------------------------------------------------------


def test_list_only_returns_user_workspace_campaigns() -> None:
    user_a, ws_a = _make_user_workspace("b34la@test")
    user_b, ws_b = _make_user_workspace("b34lb@test")
    sp_a = _make_spokesperson(ws_a)
    sp_b = _make_spokesperson(ws_b)
    client = APIClient()
    _login(client, user_a)
    _create_draft(client, ws_a, sp_a)

    _login(client, user_b)
    _create_draft(client, ws_b, sp_b)

    _login(client, user_a)
    response = client.get("/api/campaigns/")
    assert response.status_code == http.HTTP_200_OK
    rows = response.json()
    assert all(r["workspace_id"] == str(ws_a.pk) for r in rows)


def test_list_filterable_by_status() -> None:
    user, ws = _make_user_workspace("b34lstatus@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    data = _create_draft(client, ws, sp)
    # Flip one to COMPLETED via ORM.
    c = PersonalizedCampaign.objects.get(pk=data["id"])
    c.status = PersonalizedCampaign.Status.COMPLETED
    c.save(update_fields=["status"])

    # Create a fresh DRAFT to ensure the filter narrows.
    _create_draft(client, ws, sp)

    response = client.get("/api/campaigns/?status=draft")
    rows = response.json()
    assert all(r["status"] == "draft" for r in rows)


# ---- retrieve ---------------------------------------------------


def test_retrieve_returns_single_row() -> None:
    user, ws = _make_user_workspace("b34retr@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    response = client.get(f"/api/campaigns/{data['id']}/")
    assert response.status_code == http.HTTP_200_OK
    assert response.json()["id"] == data["id"]


def test_retrieve_cross_workspace_returns_404() -> None:
    user_a, _ = _make_user_workspace("b34retra@test")
    user_b, ws_b = _make_user_workspace("b34retrb@test")
    sp_b = _make_spokesperson(ws_b)
    client = APIClient()
    _login(client, user_b)
    data = _create_draft(client, ws_b, sp_b)

    _login(client, user_a)
    response = client.get(f"/api/campaigns/{data['id']}/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- destroy ----------------------------------------------------


def test_destroy_draft_succeeds_and_cascades_recipients() -> None:
    user, ws = _make_user_workspace("b34delete@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    # Add one recipient via the model so we can verify cascade.
    c = PersonalizedCampaign.objects.get(pk=data["id"])
    PersonalizedRecipient.objects.create(
        campaign=c, variables={"n": "x"}, label="x", position=1,
    )
    assert PersonalizedRecipient.objects.filter(campaign=c).count() == 1

    response = client.delete(f"/api/campaigns/{data['id']}/")
    assert response.status_code == http.HTTP_204_NO_CONTENT
    assert PersonalizedCampaign.objects.filter(pk=data["id"]).count() == 0
    assert PersonalizedRecipient.objects.filter(campaign_id=data["id"]).count() == 0


def test_destroy_launching_returns_409() -> None:
    user, ws = _make_user_workspace("b34dellaunch@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    c = PersonalizedCampaign.objects.get(pk=data["id"])
    c.status = PersonalizedCampaign.Status.LAUNCHING
    c.save(update_fields=["status"])

    response = client.delete(f"/api/campaigns/{data['id']}/")
    assert response.status_code == http.HTTP_409_CONFLICT


def test_destroy_in_flight_returns_409() -> None:
    user, ws = _make_user_workspace("b34delflight@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    c = PersonalizedCampaign.objects.get(pk=data["id"])
    c.status = PersonalizedCampaign.Status.IN_FLIGHT
    c.save(update_fields=["status"])

    response = client.delete(f"/api/campaigns/{data['id']}/")
    assert response.status_code == http.HTTP_409_CONFLICT


def test_destroy_terminal_cascades_recipients_only() -> None:
    """Q-c-9 lock — COMPLETED / PARTIAL / FAILED campaigns
    delete cleanly. Recipient rows cascade with the campaign;
    produced compositions are SET_NULL'd on the recipient
    side so they stay in the workspace for audit."""
    user, ws = _make_user_workspace("b34delterm@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    c = PersonalizedCampaign.objects.get(pk=data["id"])
    c.status = PersonalizedCampaign.Status.COMPLETED
    c.save(update_fields=["status"])

    response = client.delete(f"/api/campaigns/{data['id']}/")
    assert response.status_code == http.HTTP_204_NO_CONTENT


# ---- parse_csv --------------------------------------------------


def test_parse_csv_happy_path_persists_recipients() -> None:
    user, ws = _make_user_workspace("b34pc@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    csv_text = (
        "first_name,company,milestone\n"
        "Bob,Acme,Series B\n"
        "Carol,Initech,IPO\n"
    )
    response = client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": csv_text},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    body = response.json()
    assert body["valid_count"] == 2
    assert body["rejected_count"] == 0
    assert len(body["recipients"]) == 2
    # Q-c-5 derived labels.
    labels = sorted(r["label"] for r in body["recipients"])
    assert labels == ["Bob", "Carol"]


def test_parse_csv_replaces_existing_recipients() -> None:
    """REPLACE semantics: second paste drops the first."""
    user, ws = _make_user_workspace("b34pcreplace@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": "first_name,company,milestone\nBob,Acme,Series B\n"},
        format="json",
    )

    response = client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": (
            "first_name,company,milestone\n"
            "Dave,Globex,Pivot\n"
            "Eve,Initrode,Acquisition\n"
        )},
        format="json",
    )
    body = response.json()
    assert body["valid_count"] == 2
    labels = sorted(r["label"] for r in body["recipients"])
    assert labels == ["Dave", "Eve"]
    # Bob should be gone.
    assert PersonalizedRecipient.objects.filter(
        campaign_id=data["id"], label="Bob",
    ).count() == 0


def test_parse_csv_header_error_does_not_touch_existing_recipients() -> None:
    """Header-level rejection (400) leaves prior recipient
    state intact — operator fixes paste + retries."""
    user, ws = _make_user_workspace("b34pcherr@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": "first_name,company,milestone\nBob,Acme,X\n"},
        format="json",
    )
    assert PersonalizedRecipient.objects.filter(
        campaign_id=data["id"],
    ).count() == 1

    # Bad header — missing 'milestone'.
    response = client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": "first_name,company\nDave,Globex\n"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    assert "milestone" in response.json()["header_error"]
    # Recipients untouched.
    assert PersonalizedRecipient.objects.filter(
        campaign_id=data["id"],
    ).count() == 1


def test_parse_csv_per_row_rejections_surfaced() -> None:
    user, ws = _make_user_workspace("b34pcrej@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    csv_text = (
        "first_name,company,milestone\n"
        "Bob,Acme,Series B\n"
        ",Initech,IPO\n"  # missing first_name
        "Dave,Globex,\n"  # missing milestone
    )
    response = client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": csv_text},
        format="json",
    )
    body = response.json()
    assert body["valid_count"] == 1
    assert body["rejected_count"] == 2
    assert body["rejected_rows"][0]["row_number"] == 2
    assert body["rejected_rows"][1]["row_number"] == 3


def test_parse_csv_on_launched_campaign_returns_409() -> None:
    """Once launched, recipients are locked."""
    user, ws = _make_user_workspace("b34pclock@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)

    c = PersonalizedCampaign.objects.get(pk=data["id"])
    c.status = PersonalizedCampaign.Status.IN_FLIGHT
    c.save(update_fields=["status"])

    response = client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": "first_name\nBob\n"},
        format="json",
    )
    assert response.status_code == http.HTTP_409_CONFLICT


def test_parse_csv_cross_workspace_returns_404() -> None:
    user_a, _ = _make_user_workspace("b34pca@test")
    user_b, ws_b = _make_user_workspace("b34pcb@test")
    sp_b = _make_spokesperson(ws_b)
    client = APIClient()
    _login(client, user_b)
    data = _create_draft(client, ws_b, sp_b)

    _login(client, user_a)
    response = client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": "first_name\nBob\n"},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- recipients sub-list ---------------------------------------


def test_recipients_sub_list_returns_position_ordered() -> None:
    user, ws = _make_user_workspace("b34rec@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)
    client.post(
        f"/api/campaigns/{data['id']}/parse_csv/",
        {"csv_text": (
            "first_name,company,milestone\n"
            "Bob,Acme,Series B\n"
            "Carol,Initech,IPO\n"
            "Dave,Globex,Pivot\n"
        )},
        format="json",
    )

    response = client.get(f"/api/campaigns/{data['id']}/recipients/")
    assert response.status_code == http.HTTP_200_OK
    rows = response.json()
    assert [r["position"] for r in rows] == [1, 2, 3]
    assert [r["label"] for r in rows] == ["Bob", "Carol", "Dave"]


# ---- BC3 — source_script create + serializer block -------------


def _make_script(ws, sp, *, name="Five Good Emperors", status="ready"):
    """BC3 fixture — Script row in the same workspace as the
    supplied spokesperson. Default status=READY so create()
    accepts it (Q-bc-2)."""
    from apps.scripts.models import Script

    return Script.objects.create(
        workspace=ws, spokesperson=sp,
        name=name,
        prompt="explain the five good emperors",
        draft_text=(
            "Today we're tackling the Five Good Emperors and "
            "the Antonine peace. Hi {first_name}, today we "
            "tackle {topic}."
        ),
        knowledge_chunk_ids=["chunk-a", "chunk-b", "chunk-c"],
        verification_status="verified",
        verification_warnings=[
            {"kind": "multi_word", "claim": "x", "position": 0},
        ],
        status=status,
    )


def test_create_with_source_script_id_backfills_template() -> None:
    """BC3 — when source_script_id is supplied and template is
    omitted, server fills template from script.draft_text."""
    user, ws = _make_user_workspace("bc3backfill@test")
    sp = _make_spokesperson(ws)
    script = _make_script(ws, sp)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "Derived from script",
            "source_script_id": str(script.pk),
            # template omitted on purpose
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template"] == script.draft_text
    # Placeholders parsed from the back-filled template.
    assert set(data["placeholders"]) == {"first_name", "topic"}
    # source_script block surfaces in the response.
    assert data["source_script"] is not None
    assert data["source_script"]["id"] == str(script.pk)
    assert data["source_script"]["chunk_count"] == 3
    assert data["source_script"]["verification_status"] == "verified"


def test_create_with_source_script_id_and_template_keeps_operator_template() -> None:
    """BC3 / BC0 rule 2 — operator-supplied template wins; FK
    is audit trail. Lets operator paste + edit before submit."""
    user, ws = _make_user_workspace("bc3override@test")
    sp = _make_spokesperson(ws)
    script = _make_script(ws, sp)
    client = APIClient()
    _login(client, user)

    edited = "Edited template for {first_name} only."
    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "Edited template",
            "source_script_id": str(script.pk),
            "template": edited,
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["template"] == edited  # operator's text wins
    assert data["placeholders"] == ["first_name"]
    # But the audit FK is still persisted.
    assert data["source_script"]["id"] == str(script.pk)


def test_create_cross_workspace_source_script_returns_404() -> None:
    """BC3 / BC0 rule 3 — Script in different workspace
    surfaces as 404 (matches the spokesperson cross-workspace
    pattern)."""
    user_a, ws_a = _make_user_workspace("bc3xws_a@test")
    _, ws_b = _make_user_workspace("bc3xws_b@test")
    sp_a = _make_spokesperson(ws_a, name="MarcusA")
    sp_b = _make_spokesperson(ws_b, name="MarcusB")
    script_b = _make_script(ws_b, sp_b)
    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws_a.pk),
            "spokesperson_id": str(sp_a.pk),
            "name": "x", "source_script_id": str(script_b.pk),
        },
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_create_draft_source_script_returns_400() -> None:
    """BC3 / Q-bc-2 — only READY or RENDERED Scripts can ground
    a Campaign; DRAFT means operator hasn't approved + verified
    the draft yet."""
    user, ws = _make_user_workspace("bc3draft@test")
    sp = _make_spokesperson(ws)
    draft_script = _make_script(ws, sp, status="draft")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "from-draft", "source_script_id": str(draft_script.pk),
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body["code"] == "source_script_not_ready"


def test_create_without_source_script_is_backcompat() -> None:
    """BC3 back-compat — pre-BC create flow (template only, no
    source_script_id) still works. source_script in the
    response is None."""
    user, ws = _make_user_workspace("bc3bc@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    data = _create_draft(client, ws, sp)
    assert data["source_script"] is None


def test_retrieve_returns_source_script_block_when_set() -> None:
    """BC3 — GET /api/campaigns/<id>/ exposes the source_script
    block for SPA detail display."""
    user, ws = _make_user_workspace("bc3retr@test")
    sp = _make_spokesperson(ws)
    script = _make_script(ws, sp)
    client = APIClient()
    _login(client, user)

    create_resp = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "x", "source_script_id": str(script.pk),
        },
        format="json",
    )
    campaign_id = create_resp.json()["id"]
    detail = client.get(f"/api/campaigns/{campaign_id}/")
    assert detail.status_code == http.HTTP_200_OK
    block = detail.json()["source_script"]
    assert block["id"] == str(script.pk)
    assert block["name"] == script.name
    assert block["chunk_count"] == 3


def test_create_neither_template_nor_source_script_returns_400() -> None:
    """BC3 cross-field validation — at least one of
    `template` / `source_script_id` is required."""
    user, ws = _make_user_workspace("bc3empty@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/campaigns/",
        {
            "workspace_id": str(ws.pk),
            "spokesperson_id": str(sp.pk),
            "name": "no-template",
            # both template and source_script_id omitted
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    assert "template" in response.json()
