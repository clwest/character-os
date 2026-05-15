"""F3 tests — ``GET /api/workspace/overview/`` cross-cut endpoint.

The fabric arc's workspace overview powers the F3 dashboard
tiles (activity feed + knowledge corpus stats + spokesperson
badges). Single-roundtrip aggregate over Composition,
KnowledgeDocument, and Spokesperson — zero new persistence
per F0 contract rule 1.

Covered:

* Auth gate — unauthenticated → 401/403.
* Workspace scoping — non-member of the requested workspace → 403.
* Default-workspace fallback when ``?workspace=`` omitted.
* Spokespeople carry composition_count + attached_docs_count.
* Knowledge corpus stats (counts + source mix + most recent).
* Recent compositions list with spokesperson_name + cost.
* Empty workspace returns well-formed zero-shape (no
  null/undefined fields the SPA would have to guard).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Composition,
    CompositionStatus,
)
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
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


def _make_workspace_with_user(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(ws: Workspace, name: str = "Sp") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_composition(
    ws: Workspace, sp: Spokesperson,
    *, status: str = CompositionStatus.COMPLETED, cost: int = 100_000,
) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        template_kind="talking_head", status=status,
        cost_actual_micros=cost,
    )


def _make_knowledge_doc(
    ws: Workspace, *, title: str = "Doc",
    ingested_via: str = IngestedVia.PASTE,
    document_type: str = DocumentType.TEXT,
) -> KnowledgeDocument:
    return KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=document_type, ingested_via=ingested_via,
        raw_content="hello", processed_content="hello",
        content_hash=f"hash-{title}-{ingested_via}",
        status=DocumentStatus.PROCESSED,
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- Auth gates ---------------------------------------------------


def test_overview_requires_auth() -> None:
    client = APIClient()
    response = client.get("/api/workspace/overview/")
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_overview_rejects_non_member_workspace() -> None:
    ws_a, _user_a = _make_workspace_with_user("f3a@test", "A")
    _ws_b, user_b = _make_workspace_with_user("f3b@test", "B")
    client = APIClient()
    _login(client, user_b)
    response = client.get(f"/api/workspace/overview/?workspace={ws_a.pk}")
    assert response.status_code == http.HTTP_403_FORBIDDEN


def test_overview_404_on_unknown_workspace() -> None:
    _ws, user = _make_workspace_with_user("f3unk@test")
    client = APIClient()
    _login(client, user)
    response = client.get(
        "/api/workspace/overview/?workspace=00000000-0000-0000-0000-000000000000",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- Default workspace fallback -----------------------------------


def test_overview_uses_default_workspace_when_omitted() -> None:
    ws, user = _make_workspace_with_user("f3default@test", "Default")
    client = APIClient()
    _login(client, user)
    response = client.get("/api/workspace/overview/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["workspace"]["id"] == str(ws.pk)
    assert data["workspace"]["name"] == "Default"


# ---- Spokespeople with badges -------------------------------------


def test_overview_spokesperson_composition_count_badge() -> None:
    ws, user = _make_workspace_with_user("f3compsbadge@test")
    sp_a = _make_spokesperson(ws, name="Sasha")
    sp_b = _make_spokesperson(ws, name="Riggs")
    _make_composition(ws, sp_a)
    _make_composition(ws, sp_a)
    _make_composition(ws, sp_b)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    data = response.json()
    by_name = {sp["name"]: sp for sp in data["spokespeople"]}
    assert by_name["Sasha"]["composition_count"] == 2
    assert by_name["Riggs"]["composition_count"] == 1


def test_overview_spokesperson_attached_docs_badge() -> None:
    ws, user = _make_workspace_with_user("f3docsbadge@test")
    sp = _make_spokesperson(ws, name="Sasha")
    doc_1 = _make_knowledge_doc(ws, title="A")
    doc_1.spokespeople.add(sp)
    doc_2 = _make_knowledge_doc(ws, title="B")
    doc_2.spokespeople.add(sp)
    # An attached-to-none doc should NOT count toward the badge
    _make_knowledge_doc(ws, title="C")
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    data = response.json()
    sasha = next(sp for sp in data["spokespeople"] if sp["name"] == "Sasha")
    assert sasha["attached_docs_count"] == 2


# ---- Knowledge corpus stats ---------------------------------------


def test_overview_knowledge_stats_zero_shape() -> None:
    ws, user = _make_workspace_with_user("f3kzero@test")
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    data = response.json()["knowledge"]
    assert data["doc_count"] == 0
    assert data["chunk_count"] == 0
    assert data["most_recent"] is None
    # All four IngestedVia keys present with zero, so the SPA
    # renders fixed-order rows even on empty workspaces.
    assert set(data["source_mix"].keys()) >= {
        IngestedVia.PASTE, IngestedVia.UPLOAD,
        IngestedVia.SERPER, IngestedVia.SEED,
    }
    assert all(v == 0 for v in data["source_mix"].values())


def test_overview_knowledge_source_mix() -> None:
    ws, user = _make_workspace_with_user("f3kmix@test")
    _make_knowledge_doc(ws, title="A", ingested_via=IngestedVia.PASTE)
    _make_knowledge_doc(ws, title="B", ingested_via=IngestedVia.PASTE)
    _make_knowledge_doc(ws, title="C", ingested_via=IngestedVia.UPLOAD)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    data = response.json()["knowledge"]
    assert data["doc_count"] == 3
    assert data["source_mix"][IngestedVia.PASTE] == 2
    assert data["source_mix"][IngestedVia.UPLOAD] == 1
    assert data["source_mix"][IngestedVia.SERPER] == 0


def test_overview_knowledge_most_recent_is_latest_ingest() -> None:
    ws, user = _make_workspace_with_user("f3kmrecent@test")
    _make_knowledge_doc(ws, title="Old")
    newer = _make_knowledge_doc(ws, title="New")
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    most_recent = response.json()["knowledge"]["most_recent"]
    assert most_recent["id"] == str(newer.id)
    assert most_recent["title"] == "New"


# ---- Compositions: activity feed ----------------------------------


def test_overview_compositions_aggregate() -> None:
    ws, user = _make_workspace_with_user("f3comps@test")
    sp = _make_spokesperson(ws)
    _make_composition(ws, sp, status=CompositionStatus.RUNNING, cost=0)
    _make_composition(ws, sp, status=CompositionStatus.COMPLETED, cost=200_000)
    _make_composition(ws, sp, status=CompositionStatus.COMPLETED, cost=150_000)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    data = response.json()["compositions"]
    assert data["running_count"] == 1
    assert data["total_count"] == 3
    assert data["total_cost_micros"] == 350_000
    assert len(data["recent"]) == 3


def test_overview_compositions_recent_capped_at_ten() -> None:
    ws, user = _make_workspace_with_user("f3cap@test")
    sp = _make_spokesperson(ws)
    for _ in range(15):
        _make_composition(ws, sp)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    assert len(response.json()["compositions"]["recent"]) == 10


def test_overview_compositions_carry_spokesperson_name() -> None:
    ws, user = _make_workspace_with_user("f3compname@test")
    sp = _make_spokesperson(ws, name="Maya")
    _make_composition(ws, sp)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/workspace/overview/?workspace={ws.pk}")
    recent = response.json()["compositions"]["recent"]
    assert recent[0]["spokesperson_name"] == "Maya"
    assert recent[0]["template_kind"] == "talking_head"


def test_overview_isolates_workspaces() -> None:
    ws_a, user_a = _make_workspace_with_user("f3isoa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("f3isob@test", "B")
    sp_a = _make_spokesperson(ws_a, name="A_speaker")
    sp_b = _make_spokesperson(ws_b, name="B_speaker")
    _make_composition(ws_a, sp_a)
    _make_composition(ws_b, sp_b)
    _make_composition(ws_b, sp_b)
    _make_knowledge_doc(ws_b, title="B-doc")
    client = APIClient()
    _login(client, user_a)
    response = client.get(f"/api/workspace/overview/?workspace={ws_a.pk}")
    data = response.json()
    assert data["compositions"]["total_count"] == 1
    assert data["knowledge"]["doc_count"] == 0
    assert len(data["spokespeople"]) == 1
    assert data["spokespeople"][0]["name"] == "A_speaker"
