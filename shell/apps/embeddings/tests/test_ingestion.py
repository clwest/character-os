"""Integration tests for the ingestion + embed_document path.

Covers the full slice K3 ships:
* ingest_text persists a KnowledgeDocument and dedups via
  ``(workspace, content_hash)``.
* embed_document chunks + embeds + persists chunks + marks
  the doc processed.
* The cross-workspace cross-attach check in
  ``apps.embeddings.signals`` triggers when ingestion tries
  to set spokespeople from another workspace.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Teammate
from django.contrib.auth import get_user_model

User = get_user_model()


# ---- fixtures (reused from the privacy test pattern) -----


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_teammate(ws: Workspace, name: str) -> Teammate:
    return Teammate.objects.create(workspace=ws, name=name)


# ---- ingest_text + dedup ---------------------------------


@pytest.mark.django_db
def test_ingest_text_creates_pending_document() -> None:
    ws = _make_workspace("ingest1@test.local", "Ingest WS 1")
    result = ingest_text(
        workspace=ws,
        title="hello",
        content="Some content here.\n\nSecond paragraph.",
        document_type=DocumentType.TEXT,
    )
    assert result.deduped is False
    assert result.document.status == DocumentStatus.PENDING
    assert result.document.workspace == ws
    assert result.document.ingested_via == IngestedVia.PASTE
    assert result.document.content_hash  # populated


@pytest.mark.django_db
def test_ingest_text_dedups_same_content_in_workspace() -> None:
    ws = _make_workspace("ingest2@test.local", "Ingest WS 2")
    text = "Same exact content.\n\nMore content."

    first = ingest_text(workspace=ws, title="A", content=text)
    second = ingest_text(workspace=ws, title="B", content=text)

    assert first.deduped is False
    assert second.deduped is True
    assert first.document.pk == second.document.pk


@pytest.mark.django_db
def test_ingest_text_dedup_is_per_workspace() -> None:
    ws_a = _make_workspace("ingestA@test.local", "WS A")
    ws_b = _make_workspace("ingestB@test.local", "WS B")
    text = "Shared content across workspaces.\n\nMore."

    doc_a = ingest_text(workspace=ws_a, title="A", content=text)
    doc_b = ingest_text(workspace=ws_b, title="B", content=text)

    assert doc_a.deduped is False
    assert doc_b.deduped is False
    # Same content_hash, different rows
    assert doc_a.document.content_hash == doc_b.document.content_hash
    assert doc_a.document.pk != doc_b.document.pk


@pytest.mark.django_db
def test_ingest_text_empty_content_raises() -> None:
    ws = _make_workspace("empty@test.local", "Empty WS")
    with pytest.raises(ValueError):
        ingest_text(workspace=ws, title="empty", content="   \n  ")


@pytest.mark.django_db
def test_ingest_text_with_spokespeople_m2m_works() -> None:
    ws = _make_workspace("attach@test.local", "Attach WS")
    sp1 = _make_teammate(ws, "Sp1")
    sp2 = _make_teammate(ws, "Sp2")
    result = ingest_text(
        workspace=ws,
        title="visible to sp1",
        content="content",
        spokespeople=[sp1],
    )
    attached = set(result.document.spokespeople.values_list("pk", flat=True))
    assert attached == {sp1.pk}
    assert sp2.pk not in attached


@pytest.mark.django_db
def test_ingest_text_restores_soft_deleted_row() -> None:
    """K4.2 — re-ingesting the same content as a soft-deleted
    row should restore (flip ``is_active=True``, reset to
    PENDING, clear error) and return ``deduped=False`` so the
    caller re-fires ``embed_document``. Otherwise dedup hands
    back a row the operator can't see and never re-embeds."""
    ws = _make_workspace("restore@test.local", "Restore WS")
    text = "Content that will get soft-deleted then restored."

    first = ingest_text(workspace=ws, title="original", content=text)
    assert first.deduped is False

    # Operator soft-deletes (mirrors the viewset's destroy).
    doc = first.document
    doc.is_active = False
    doc.status = DocumentStatus.FAILED
    doc.error_message = "stale failure"
    doc.save()

    # Re-ingest — same content, new title.
    second = ingest_text(workspace=ws, title="restored", content=text)
    assert second.deduped is False, "restored row should re-fire embed"
    assert second.document.pk == first.document.pk, "same row, not a new one"
    assert second.document.is_active is True
    assert second.document.status == DocumentStatus.PENDING
    assert second.document.error_message == ""
    assert second.document.title == "restored", "new title wins"


@pytest.mark.django_db
def test_ingest_text_restore_preserves_title_when_new_is_blank() -> None:
    """K4.2 — when restoring, an empty new title shouldn't
    clobber the operator's original title."""
    ws = _make_workspace("restore-title@test.local", "Restore Title WS")
    text = "Content to test title preservation."

    first = ingest_text(workspace=ws, title="keep me", content=text)
    first.document.is_active = False
    first.document.save(update_fields=["is_active"])

    # URL-ingest path passes title="" when nothing supplied.
    second = ingest_text(workspace=ws, title="", content=text)
    assert second.deduped is False
    assert second.document.title == "keep me"


@pytest.mark.django_db
def test_ingest_text_rejects_cross_workspace_spokesperson_attach() -> None:
    ws_a = _make_workspace("x1@test.local", "X1")
    ws_b = _make_workspace("x2@test.local", "X2")
    foreign_sp = _make_teammate(ws_b, "Foreign")
    with pytest.raises(ValidationError):
        ingest_text(
            workspace=ws_a,
            title="cross-attach",
            content="content",
            spokespeople=[foreign_sp],
        )


# ---- embed_document --------------------------------------


@pytest.mark.django_db
@override_settings(EMBEDDING_FORCE_MOCK=True)
def test_embed_document_processes_to_completion() -> None:
    ws = _make_workspace("embed1@test.local", "Embed WS 1")
    result = ingest_text(
        workspace=ws,
        title="doc",
        content=("Paragraph one with content.\n\n" * 5),
    )
    out = embed_document.apply(args=[str(result.document.pk)]).get()
    assert out["status"] == "processed"
    assert out["chunks_created"] >= 1

    result.document.refresh_from_db()
    assert result.document.status == DocumentStatus.PROCESSED
    assert result.document.chunks.count() == out["chunks_created"]


@pytest.mark.django_db
@override_settings(EMBEDDING_FORCE_MOCK=True)
def test_embed_document_chunks_have_correct_dim() -> None:
    from apps.embeddings.models import EMBEDDING_DIMENSION

    ws = _make_workspace("embed2@test.local", "Embed WS 2")
    result = ingest_text(
        workspace=ws, title="dim doc", content="just one chunk worth of text",
    )
    embed_document.apply(args=[str(result.document.pk)])

    chunk = result.document.chunks.first()
    assert chunk is not None
    # pgvector returns the vector as a numpy array-like; just
    # confirm the dimension matches the model.
    assert len(list(chunk.embedding_vector)) == EMBEDDING_DIMENSION


@pytest.mark.django_db
@override_settings(EMBEDDING_FORCE_MOCK=True)
def test_embed_document_is_idempotent() -> None:
    """Re-running ``embed_document`` against an already-processed
    document wipes existing chunks and re-creates them. Used
    when re-embedding after content edits or model swaps."""
    ws = _make_workspace("idem@test.local", "Idem WS")
    result = ingest_text(
        workspace=ws, title="idem", content="some content to chunk",
    )
    embed_document.apply(args=[str(result.document.pk)])
    first_count = result.document.chunks.count()

    # Run again — should wipe + re-create.
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    second_count = result.document.chunks.count()
    assert first_count == second_count


@pytest.mark.django_db
def test_embed_document_handles_missing_doc() -> None:
    """An ID that doesn't exist returns a not_found result
    rather than raising — Celery tasks should be defensive."""
    import uuid

    out = embed_document.apply(args=[str(uuid.uuid4())]).get()
    assert out["status"] == "not_found"
    assert out["chunks_created"] == 0
