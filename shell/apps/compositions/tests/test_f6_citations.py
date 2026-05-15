"""F6 tests — knowledge citations resolved into the composition
serializer.

K6 populates ``Composition.knowledge_chunk_ids`` whenever a
knowledge-aware render fires. F6 surfaces the doc-level
resolution via a new ``knowledge_docs_used`` field on the
composition retrieve response — no new endpoint per the F0
scope lock (the chunk ids already round-trip).

Covered:

* Empty knowledge_chunk_ids → empty knowledge_docs_used.
* Chunks from one doc → single doc entry with count.
* Chunks from multiple docs → ordered, deduped, counted by
  first-occurrence in the input list.
* Cross-workspace chunk ids (shouldn't happen but defense in
  depth via the resolver's workspace filter) → silently
  dropped.
* Stale chunk ids (chunk deleted since the render) →
  silently dropped, no 500.
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


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sp", runway_avatar_id="av",
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
    ws: Workspace, sp: Spokesperson, *, chunk_ids: list[str] | None = None,
) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        template_kind="talking_head", status=CompositionStatus.COMPLETED,
        knowledge_chunk_ids=chunk_ids or [],
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- empty + single-doc shapes ------------------------------------


def test_citations_empty_when_no_chunks() -> None:
    ws, user = _make_workspace_with_user("f6none@test")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, chunk_ids=[])
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{comp.pk}/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert "knowledge_docs_used" in data
    assert data["knowledge_docs_used"] == []


def test_citations_single_doc_returns_count() -> None:
    ws, user = _make_workspace_with_user("f6single@test")
    sp = _make_spokesperson(ws)
    doc, chunks = _make_doc(ws, "Spring launch FAQ", chunk_count=3)
    comp = _make_composition(
        ws, sp, chunk_ids=[str(c.id) for c in chunks],
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{comp.pk}/")
    data = response.json()
    docs = data["knowledge_docs_used"]
    assert len(docs) == 1
    assert docs[0]["id"] == str(doc.id)
    assert docs[0]["title"] == "Spring launch FAQ"
    assert docs[0]["chunk_count"] == 3


def test_citations_multi_doc_grouped_and_ordered() -> None:
    """Chunk ids from two docs interleaved should produce
    two doc entries ordered by first-occurrence."""
    ws, user = _make_workspace_with_user("f6multi@test")
    sp = _make_spokesperson(ws)
    doc_a, chunks_a = _make_doc(ws, "A", chunk_count=2, seed=0.9)
    doc_b, chunks_b = _make_doc(ws, "B", chunk_count=2, seed=0.5)
    # Interleave A, B, A, B so first-occurrence is A then B.
    chunk_ids = [
        str(chunks_a[0].id),
        str(chunks_b[0].id),
        str(chunks_a[1].id),
        str(chunks_b[1].id),
    ]
    comp = _make_composition(ws, sp, chunk_ids=chunk_ids)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{comp.pk}/")
    docs = response.json()["knowledge_docs_used"]
    assert [d["title"] for d in docs] == ["A", "B"]
    assert {d["id"] for d in docs} == {str(doc_a.id), str(doc_b.id)}
    assert {d["title"]: d["chunk_count"] for d in docs} == {"A": 2, "B": 2}


def test_citations_drop_stale_chunk_ids() -> None:
    """If a chunk got deleted since the render fired (admin
    audit, dedup-restore cleanup, etc.) we should silently
    drop the stale id, not 500."""
    ws, user = _make_workspace_with_user("f6stale@test")
    sp = _make_spokesperson(ws)
    doc, chunks = _make_doc(ws, "FAQ", chunk_count=2)
    stale_id = "11111111-1111-1111-1111-111111111111"
    chunk_ids = [str(chunks[0].id), stale_id, str(chunks[1].id)]
    comp = _make_composition(ws, sp, chunk_ids=chunk_ids)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/compositions/{comp.pk}/")
    docs = response.json()["knowledge_docs_used"]
    assert len(docs) == 1
    assert docs[0]["chunk_count"] == 2


def test_citations_workspace_isolation_drops_foreign_ids() -> None:
    """Defense in depth: K6 only writes in-workspace chunk
    ids, but if some bug ever leaked a foreign id into the
    JSON field, the resolver's workspace filter must drop it
    before it surfaces in another workspace's UI."""
    ws_a, user_a = _make_workspace_with_user("f6wa@test", "A")
    ws_b, _user_b = _make_workspace_with_user("f6wb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    _doc_a, chunks_a = _make_doc(ws_a, "A-doc", chunk_count=1)
    _doc_b, chunks_b = _make_doc(ws_b, "B-doc", chunk_count=1)
    # Workspace A composition references a workspace B chunk
    # (theoretically blocked by signals; here we set the JSON
    # field directly to simulate the leak).
    comp = _make_composition(
        ws_a, sp_a, chunk_ids=[str(chunks_a[0].id), str(chunks_b[0].id)],
    )
    client = APIClient()
    _login(client, user_a)
    response = client.get(f"/api/compositions/{comp.pk}/")
    docs = response.json()["knowledge_docs_used"]
    # B-doc must NOT appear in workspace A's composition view.
    assert len(docs) == 1
    assert docs[0]["title"] == "A-doc"
