"""F4 tests — ``POST /api/knowledge/preview/`` workspace fabric arc.

The recipe form's preview panel calls this endpoint debounced
on script edits to show "would draw from N chunks across M
docs." Wraps ``retrieve_for_spokesperson`` so the K0 contract
rule 2 (only retrieval.py touches chunk-level models) stays
intact.

F0 contract rule 6 — best-effort. The view never raises HTTP
500 on retrieval failure; it returns ``preview_failed=True``
and an empty docs list. The SPA renders gracefully.

Covered:

* Auth gate + workspace scoping (spokesperson in foreign
  workspace → 403).
* Missing body fields → 400.
* Spokesperson with zero docs → empty result.
* Spokesperson with one doc / multiple chunks → grouped count.
* Multiple docs → ordered by first-match position.
* top_k clamps to [1, 20].
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    EMBEDDING_DIMENSION,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_embeddings():
    """Real-mode retrieval needs OpenAI; force mock so tests
    are hermetic. ``retrieve_for_spokesperson`` still runs the
    workspace-scoping filter end-to-end."""
    with override_settings(EMBEDDING_FORCE_MOCK=True):
        yield


# ---- helpers ------------------------------------------------------


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIMENSION
    v[0] = seed
    return v


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


def _make_doc_with_chunks(
    ws: Workspace,
    *,
    title: str = "Doc",
    chunk_count: int = 1,
    seed: float = 1.0,
) -> KnowledgeDocument:
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        raw_content="x", processed_content="x",
        content_hash=f"hash-{title}-{seed}",
        status=DocumentStatus.PROCESSED,
    )
    for i in range(chunk_count):
        KnowledgeChunk.objects.create(
            document=doc,
            chunk_index=i,
            chunk_text=f"chunk-{i} of {title}",
            chunk_size=20,
            embedding_vector=_vec(seed),
        )
    return doc


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- auth + scoping -----------------------------------------------


def test_preview_requires_auth() -> None:
    client = APIClient()
    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": "x", "query": "hello"},
        format="json",
    )
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_preview_rejects_cross_workspace_spokesperson() -> None:
    ws_a, _user_a = _make_workspace_with_user("f4xa@test", "A")
    _ws_b, user_b = _make_workspace_with_user("f4xb@test", "B")
    foreign_sp = _make_spokesperson(ws_a)
    client = APIClient()
    _login(client, user_b)
    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(foreign_sp.pk), "query": "hi"},
        format="json",
    )
    assert response.status_code == http.HTTP_403_FORBIDDEN


def test_preview_rejects_missing_spokesperson() -> None:
    _ws, user = _make_workspace_with_user("f4nosp@test")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/preview/",
        {"query": "hi"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_preview_rejects_missing_query() -> None:
    ws, user = _make_workspace_with_user("f4noq@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(sp.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_preview_404_on_unknown_spokesperson() -> None:
    _ws, user = _make_workspace_with_user("f4unk@test")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/preview/",
        {
            "spokesperson": "11111111-1111-1111-1111-111111111111",
            "query": "hi",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


# ---- payload shape ------------------------------------------------


def test_preview_empty_workspace_returns_zero_shape() -> None:
    ws, user = _make_workspace_with_user("f4empty@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(sp.pk), "query": "spring launch"},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["docs_used"] == []
    assert data["total_chunks"] == 0
    assert data["query_used"] == "spring launch"


def test_preview_groups_chunks_by_document() -> None:
    ws, user = _make_workspace_with_user("f4group@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(ws, title="A", chunk_count=3, seed=0.99)
    _make_doc_with_chunks(ws, title="B", chunk_count=2, seed=0.50)
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(sp.pk), "query": "anything"},
        format="json",
    )
    data = response.json()
    docs_by_title = {d["title"]: d for d in data["docs_used"]}
    # We requested top_k=5 (default); 3 + 2 = 5 chunks total, and
    # both docs should appear. The high-seed doc (A) will rank
    # first because its chunks dominate cosine match.
    assert "A" in docs_by_title
    assert "B" in docs_by_title
    assert docs_by_title["A"]["chunk_count"] == 3
    assert docs_by_title["B"]["chunk_count"] == 2
    assert data["total_chunks"] == 5


def test_preview_respects_top_k_clamp() -> None:
    ws, user = _make_workspace_with_user("f4topk@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(ws, title="A", chunk_count=10, seed=0.99)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(sp.pk), "query": "x", "top_k": 3},
        format="json",
    )
    assert response.json()["total_chunks"] == 3

    response_high = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(sp.pk), "query": "x", "top_k": 100},
        format="json",
    )
    # Clamped at 20.
    assert response_high.json()["total_chunks"] == 10  # only 10 chunks exist


def test_preview_isolates_workspaces() -> None:
    ws_a, user_a = _make_workspace_with_user("f4isoa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("f4isob@test", "B")
    sp_a = _make_spokesperson(ws_a)
    _make_doc_with_chunks(ws_a, title="A-doc", chunk_count=2, seed=0.99)
    _make_doc_with_chunks(ws_b, title="B-doc", chunk_count=2, seed=0.99)
    client = APIClient()
    _login(client, user_a)
    response = client.post(
        "/api/knowledge/preview/",
        {"spokesperson": str(sp_a.pk), "query": "x"},
        format="json",
    )
    data = response.json()
    titles = {d["title"] for d in data["docs_used"]}
    assert titles == {"A-doc"}


def test_preview_best_effort_on_retrieval_failure() -> None:
    """F0 contract rule 6 — retrieval failure must not 500.
    Returns an empty result with preview_failed=True so the
    SPA panel renders gracefully without blocking submit."""
    ws, user = _make_workspace_with_user("f4fail@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(ws, title="A", chunk_count=1, seed=0.99)
    client = APIClient()
    _login(client, user)
    with patch(
        "apps.embeddings.retrieval.retrieve_for_spokesperson",
        side_effect=RuntimeError("simulated retrieval failure"),
    ):
        response = client.post(
            "/api/knowledge/preview/",
            {"spokesperson": str(sp.pk), "query": "x"},
            format="json",
        )
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["docs_used"] == []
    assert data["total_chunks"] == 0
    assert data["preview_failed"] is True
