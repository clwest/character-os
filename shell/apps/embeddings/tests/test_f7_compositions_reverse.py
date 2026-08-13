"""F7 tests — ``GET /api/knowledge/<id>/compositions/`` workspace fabric arc.

Reverse view of F6: from a knowledge document, list the
compositions that drew on its chunks. Powers the
"Used in N compositions" panel at /workspace/knowledge/:id.

Covered:

* Auth gate.
* Cross-workspace caller → 404 (queryset filter).
* Doc with zero chunks → empty list.
* Doc with chunks but no compositions referencing them →
  empty list.
* Composition uses chunks from this doc → surfaces in
  response with correct chunk_count.
* Multiple compositions referencing one doc → all surface.
* A composition referencing only a different doc's chunks
  does NOT surface.
* Workspace isolation — a foreign-workspace composition
  whose chunk_ids happen to overlap (impossible in practice
  due to the cross-workspace signal, but defense in depth)
  must not surface.
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
    EMBEDDING_DIMENSION,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
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


def _make_teammate(ws: Workspace, name: str = "Sp") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name, runway_avatar_id="av",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_doc(
    ws: Workspace, title: str, *, chunk_count: int = 1, seed: float = 0.9,
) -> tuple[KnowledgeDocument, list[KnowledgeChunk]]:
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        raw_content="x", processed_content="x",
        content_hash=f"hash-{title}-{seed}",
        status=DocumentStatus.PROCESSED,
    )
    chunks = [
        KnowledgeChunk.objects.create(
            document=doc,
            chunk_index=i,
            chunk_text=f"chunk-{i} of {title}",
            chunk_size=20,
            embedding_vector=_vec(seed),
        )
        for i in range(chunk_count)
    ]
    return doc, chunks


def _make_composition(
    ws: Workspace, sp: Teammate, *, chunk_ids: list[str] | None = None,
    name: str = "comp",
) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name=name,
        template_kind="talking_head", status=CompositionStatus.COMPLETED,
        knowledge_chunk_ids=chunk_ids or [],
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- auth + scoping ----------------------------------------------


def test_compositions_reverse_requires_auth() -> None:
    ws, user = _make_workspace_with_user("f7auth@test")
    doc, _ = _make_doc(ws, "D")
    client = APIClient()
    response = client.get(f"/api/knowledge/{doc.pk}/compositions/")
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_compositions_reverse_404_for_cross_workspace_caller() -> None:
    ws_a, _user_a = _make_workspace_with_user("f7xa@test", "A")
    _ws_b, user_b = _make_workspace_with_user("f7xb@test", "B")
    doc_a, _ = _make_doc(ws_a, "A-doc")
    client = APIClient()
    _login(client, user_b)
    response = client.get(f"/api/knowledge/{doc_a.pk}/compositions/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- shape -------------------------------------------------------


def test_compositions_reverse_empty_for_unused_doc() -> None:
    ws, user = _make_workspace_with_user("f7unused@test")
    doc, _ = _make_doc(ws, "Unused", chunk_count=2)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/knowledge/{doc.pk}/compositions/")
    assert response.status_code == http.HTTP_200_OK
    assert response.json()["compositions"] == []


def test_compositions_reverse_surfaces_using_composition() -> None:
    ws, user = _make_workspace_with_user("f7using@test")
    sp = _make_teammate(ws, name="Sasha")
    doc, chunks = _make_doc(ws, "FAQ", chunk_count=3)
    comp = _make_composition(
        ws, sp, name="Spring spot",
        chunk_ids=[str(chunks[0].id), str(chunks[1].id)],
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/knowledge/{doc.pk}/compositions/")
    items = response.json()["compositions"]
    assert len(items) == 1
    entry = items[0]
    assert entry["composition_id"] == str(comp.id)
    assert entry["composition_name"] == "Spring spot"
    assert entry["spokesperson_name"] == "Sasha"
    assert entry["chunk_count"] == 2


def test_compositions_reverse_skips_unrelated_compositions() -> None:
    """A composition that drew from a different doc must
    not show up in this doc's reverse view."""
    ws, user = _make_workspace_with_user("f7unrelated@test")
    sp = _make_teammate(ws)
    doc_target, target_chunks = _make_doc(ws, "Target", chunk_count=1)
    _doc_other, other_chunks = _make_doc(ws, "Other", chunk_count=1, seed=0.5)
    # Composition uses only the OTHER doc's chunks.
    _make_composition(ws, sp, chunk_ids=[str(other_chunks[0].id)])
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/knowledge/{doc_target.pk}/compositions/")
    assert response.json()["compositions"] == []


def test_compositions_reverse_finds_multiple_consumers() -> None:
    ws, user = _make_workspace_with_user("f7multi@test")
    sp = _make_teammate(ws)
    doc, chunks = _make_doc(ws, "FAQ", chunk_count=2)
    _make_composition(ws, sp, name="A", chunk_ids=[str(chunks[0].id)])
    _make_composition(ws, sp, name="B", chunk_ids=[str(chunks[1].id)])
    _make_composition(
        ws, sp, name="C",
        chunk_ids=[str(chunks[0].id), str(chunks[1].id)],
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/knowledge/{doc.pk}/compositions/")
    items = response.json()["compositions"]
    names_to_counts = {it["composition_name"]: it["chunk_count"] for it in items}
    assert names_to_counts == {"A": 1, "B": 1, "C": 2}


def test_compositions_reverse_isolates_workspaces() -> None:
    """A foreign-workspace composition whose chunk_ids happen
    to overlap with this doc's chunks (theoretically blocked
    by the V1 cross-workspace signal but defense in depth)
    must not surface in this workspace's reverse view."""
    ws_a, user_a = _make_workspace_with_user("f7wa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("f7wb@test", "B")
    sp_b = _make_teammate(ws_b)
    doc_a, chunks_a = _make_doc(ws_a, "A-doc", chunk_count=1)
    # B's composition references A's chunk id (simulated leak).
    _make_composition(ws_b, sp_b, chunk_ids=[str(chunks_a[0].id)])
    client = APIClient()
    _login(client, user_a)
    response = client.get(f"/api/knowledge/{doc_a.pk}/compositions/")
    # The composition lives in workspace B and the endpoint
    # filters by doc.workspace (= A), so it cannot surface.
    assert response.json()["compositions"] == []
