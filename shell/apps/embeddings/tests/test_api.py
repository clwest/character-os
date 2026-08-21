"""DRF integration tests for the knowledge layer API.

SESSION 138 / K4. Covers:

* GET ``/api/knowledge/`` — list scoped to caller's workspaces.
* POST ``/api/knowledge/`` — create via ``text_content`` path.
* POST ``/api/knowledge/`` — create via ``pdf_data_uri`` path
  (mocked PDF extraction so the test is hermetic).
* POST ``/api/knowledge/`` — exclusive-or on text vs pdf input.
* GET ``/api/knowledge/<id>/`` — detail.
* PATCH ``/api/knowledge/<id>/`` — title + spokespeople update.
* DELETE ``/api/knowledge/<id>/`` — soft delete leaves chunks.
* Workspace scoping — caller from workspace A cannot read or
  mutate workspace B's docs.

Tests use ``EMBEDDING_FORCE_MOCK=True`` so the synchronous
embedding pass inside ``embed_document.delay()`` (which falls
back to in-process when no worker is configured for tests)
returns deterministic vectors without burning OpenAI credits.

Celery is configured to run tasks eagerly in tests via the
``CELERY_TASK_ALWAYS_EAGER`` override below — that way
``embed_document.delay()`` actually runs the embedding pass
in-process, so the resulting document hits ``status=processed``
before the assertion. Mirrors how the smoke command uses
``.apply()``.
"""
from __future__ import annotations

import base64
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    AudienceScope,
    DocumentStatus,
    DocumentType,
    KnowledgeDocument,
)
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from django.contrib.auth import get_user_model

User = get_user_model()

# Eager Celery + force-mock embeddings: every API test runs the
# real ingestion pipeline end-to-end without external services.
pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_and_eager():
    """Every test in this module runs with mock embeddings and
    eager Celery. ``override_settings`` is a context manager
    rather than a pytest mark, so an autouse fixture is the
    canonical way to apply it across a module."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


# ---- fixtures --------------------------------------------


def _make_workspace_with_user(email: str, ws_name: str) -> tuple[Workspace, User]:
    """Create a user + their auto-workspace (per accounts.signals).
    Returns (workspace, user)."""
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = ws_name
    ws.save()
    return ws, user


def _login(client: APIClient, user: User) -> None:
    client.force_authenticate(user=user)


# ---- list + scope -----------------------------------------


def test_list_returns_only_my_workspaces_docs() -> None:
    ws_a, user_a = _make_workspace_with_user("aa@k4.test", "A")
    ws_b, user_b = _make_workspace_with_user("bb@k4.test", "B")

    KnowledgeDocument.objects.create(
        workspace=ws_a, title="A doc",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-A",
        ingested_via="paste",
    )
    KnowledgeDocument.objects.create(
        workspace=ws_b, title="B doc",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-B",
        ingested_via="paste",
    )

    client = APIClient()
    _login(client, user_a)
    response = client.get("/api/knowledge/")
    assert response.status_code == http.HTTP_200_OK
    titles = {row["title"] for row in response.json()["results"]} if "results" in response.json() else {row["title"] for row in response.json()}
    assert "A doc" in titles
    assert "B doc" not in titles


def test_list_requires_authentication() -> None:
    client = APIClient()
    response = client.get("/api/knowledge/")
    assert response.status_code in {http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN}


def test_list_filters_by_workspace_query_param() -> None:
    ws_a, user_a = _make_workspace_with_user("multi@k4.test", "A")
    # Create a SECOND workspace owned by the same user — both
    # are accessible but the filter narrows to one.
    ws_b = Workspace.objects.create(owner=user_a, name="Second")
    from apps.accounts.models import Membership
    Membership.objects.create(user=user_a, workspace=ws_b, role=Membership.Role.OWNER)

    KnowledgeDocument.objects.create(
        workspace=ws_a, title="In A",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-A",
        ingested_via="paste",
    )
    KnowledgeDocument.objects.create(
        workspace=ws_b, title="In B",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-B",
        ingested_via="paste",
    )

    client = APIClient()
    _login(client, user_a)
    response = client.get(f"/api/knowledge/?workspace={ws_a.pk}")
    titles = {row["title"] for row in _rows(response.json())}
    assert "In A" in titles
    assert "In B" not in titles


# ---- create: text ---------------------------------------


def test_create_via_text_content_runs_full_pipeline() -> None:
    ws, user = _make_workspace_with_user("txt@k4.test", "TxtWS")

    client = APIClient()
    _login(client, user)
    payload = {
        "workspace": str(ws.pk),
        "title": "First doc",
        "text_content": (
            "First paragraph of substantive content.\n\n"
            "Second paragraph keeps going with more text."
        ),
    }
    response = client.post("/api/knowledge/", payload, format="json")
    assert response.status_code == http.HTTP_201_CREATED, response.content

    body = response.json()
    assert body["title"] == "First doc"
    # The doc was just created via eager Celery → status=processed
    assert body["status"] == DocumentStatus.PROCESSED
    assert body["document_type"] == DocumentType.TEXT
    assert body["chunk_count"] >= 1

    # Real row exists on the workspace
    doc = KnowledgeDocument.objects.get(pk=body["id"])
    assert doc.workspace == ws
    assert doc.created_by == user
    assert doc.chunks.count() == body["chunk_count"]


def test_create_via_markdown_auto_detects_doc_type() -> None:
    ws, user = _make_workspace_with_user("md@k4.test", "MdWS")

    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "MD doc",
            "text_content": "# A heading\n\n## A subheading\n\nBody",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    assert response.json()["document_type"] == DocumentType.MARKDOWN


# ---- create: PDF -----------------------------------------


def test_create_via_pdf_data_uri_runs_full_pipeline() -> None:
    """The PDF path: base64 data URI in → pdfminer extract →
    ingest_pdf → ingestion → embed_document → processed.

    Mocks pdfminer.high_level.extract_text so the test doesn't
    need a real PDF fixture (it would need to be checked in
    as binary, and we're a few MB-conscious here). The route
    + serializer + ingest_pdf + tasks all run for real.
    """
    ws, user = _make_workspace_with_user("pdf@k4.test", "PdfWS")

    # Fake "PDF" bytes — anything >=100 bytes that passes our
    # base64 sanity check. pdfminer's high_level.extract_text is
    # patched out so it doesn't actually parse this.
    fake_pdf_bytes = b"%PDF-1.7 fake-content-" + (b"x" * 200)
    pdf_data_uri = (
        "data:application/pdf;base64,"
        + base64.b64encode(fake_pdf_bytes).decode("ascii")
    )

    client = APIClient()
    _login(client, user)

    with patch(
        "apps.embeddings.pdf.pdfminer_extract", create=True,
    ):
        with patch("pdfminer.high_level.extract_text") as mock_extract:
            mock_extract.return_value = (
                "First paragraph from the PDF.\n\n"
                "Second paragraph from the PDF."
            )
            response = client.post(
                "/api/knowledge/",
                {
                    "workspace": str(ws.pk),
                    "title": "fake.pdf",
                    "pdf_data_uri": pdf_data_uri,
                },
                format="json",
            )

    assert response.status_code == http.HTTP_201_CREATED, response.content
    body = response.json()
    assert body["document_type"] == DocumentType.PDF
    assert body["status"] == DocumentStatus.PROCESSED
    assert body["chunk_count"] >= 1


def test_create_rejects_both_text_and_pdf() -> None:
    ws, user = _make_workspace_with_user("xor@k4.test", "WS")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "ambiguous",
            "text_content": "hello",
            "pdf_data_uri": "data:application/pdf;base64,Zm9vYmFy",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_neither_text_nor_pdf() -> None:
    ws, user = _make_workspace_with_user("emp@k4.test", "WS")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/",
        {"workspace": str(ws.pk), "title": "empty"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_invalid_pdf_data_uri() -> None:
    ws, user = _make_workspace_with_user("badpdf@k4.test", "WS")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "bad.pdf",
            "pdf_data_uri": "not-a-data-uri",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


# ---- spokesperson scoping -------------------------------


def test_create_with_attached_spokesperson_succeeds() -> None:
    ws, user = _make_workspace_with_user("att@k4.test", "WS")
    sp = Teammate.objects.create(workspace=ws, name="Sp")

    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "scoped",
            "text_content": "scoped content",
            "spokesperson_ids": [str(sp.pk)],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    doc = KnowledgeDocument.objects.get(pk=response.json()["id"])
    assert list(doc.spokespeople.all()) == [sp]


def test_create_rejects_cross_workspace_spokesperson() -> None:
    ws_a, user_a = _make_workspace_with_user("aa@xws.test", "A")
    ws_b, _user_b = _make_workspace_with_user("bb@xws.test", "B")
    foreign_sp = Teammate.objects.create(workspace=ws_b, name="Foreign")

    client = APIClient()
    _login(client, user_a)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws_a.pk),
            "title": "evil",
            "text_content": "x",
            "spokesperson_ids": [str(foreign_sp.pk)],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


# ---- detail + update + delete ----------------------------


def test_detail_succeeds_for_member() -> None:
    ws, user = _make_workspace_with_user("dt@k4.test", "WS")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="doc",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH",
        ingested_via="paste",
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/knowledge/{doc.pk}/")
    assert response.status_code == http.HTTP_200_OK
    assert response.json()["title"] == "doc"


def test_detail_denied_for_outsider() -> None:
    ws_a, user_a = _make_workspace_with_user("dn_a@k4.test", "A")
    ws_b, _user_b = _make_workspace_with_user("dn_b@k4.test", "B")
    doc = KnowledgeDocument.objects.create(
        workspace=ws_b, title="B doc",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-B-DN",
        ingested_via="paste",
    )
    client = APIClient()
    _login(client, user_a)
    response = client.get(f"/api/knowledge/{doc.pk}/")
    # Outsider sees a 404 (queryset filter excludes the row),
    # not a 403 — leak-shape-safe.
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_patch_updates_title_only() -> None:
    ws, user = _make_workspace_with_user("pt@k4.test", "WS")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="old",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-PT",
        ingested_via="paste",
    )
    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"title": "new"},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert doc.title == "new"


def test_patch_still_rejects_pdf_data_uri() -> None:
    """SESSION 235 lifted the text_content invariant for Beat 3's
    fix-loop, but PDF and URL re-ingest remain create-only —
    editing a PDF-provenance doc means editing its extracted
    text, not re-uploading a fresh source."""
    ws, user = _make_workspace_with_user("pdfpatch@k4.test", "WS")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="pdf-src",
        document_type=DocumentType.PDF,
        processed_content="x", content_hash="HASH-PDFPATCH",
        ingested_via="upload",
    )
    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"pdf_data_uri": "data:application/pdf;base64,Zm9vYmFy"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert "pdf_data_uri" in body


# ---- SESSION 235 / Chapter 6 slice-2 (Beat 3 — Fix the source) ------
#
# PATCH with text_content re-ingests in place. Same row keeps its id,
# workspace, and M2M attachments; its processed_content + content_hash
# are recomputed and its chunks are dropped and re-embedded (eager
# Celery in these tests re-embeds inline). Design lock:
# ``docs/design/CUSTOMER_JOURNEY_V1.md`` §"Chapter 6" §"Beat 3".


def test_patch_text_content_reingests_in_place() -> None:
    """Happy path: edit text_content, doc id + workspace + title +
    M2M survive; content_hash + processed_content update; chunks
    regenerate (eager Celery → status=processed with new chunk
    count reflecting the new text)."""
    ws, user = _make_workspace_with_user("edit@k4.test", "WS")
    sp = Teammate.objects.create(workspace=ws, name="Oliver")

    client = APIClient()
    _login(client, user)
    create_response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "Notes on hours",
            "text_content": "We are open weekdays 9-5.",
            "spokesperson_ids": [str(sp.pk)],
        },
        format="json",
    )
    assert create_response.status_code == http.HTTP_201_CREATED
    doc_id = create_response.json()["id"]
    original_hash = create_response.json()["content_hash"]

    patch_response = client.patch(
        f"/api/knowledge/{doc_id}/",
        {
            "text_content": (
                "We are open Monday-Saturday 9-6 and Sunday 10-4."
            ),
        },
        format="json",
    )
    assert patch_response.status_code == http.HTTP_200_OK, patch_response.content

    doc = KnowledgeDocument.objects.get(pk=doc_id)
    assert doc.processed_content.startswith("We are open Monday-Saturday")
    assert doc.content_hash != original_hash
    # Title + M2M preserved across the re-ingest.
    assert doc.title == "Notes on hours"
    assert list(doc.spokespeople.all()) == [sp]
    # Eager Celery re-embed leaves the doc processed with chunks
    # matching the new content, not the old.
    assert doc.status == DocumentStatus.PROCESSED
    assert doc.chunks.count() >= 1
    assert all(
        "Monday-Saturday" in c.chunk_text or "Sunday" in c.chunk_text
        for c in doc.chunks.all()
    )


def test_patch_text_content_no_op_when_unchanged() -> None:
    """Idempotency: re-submitting the same text (post-normalize)
    is a no-op — hash unchanged, status not reset, no re-embed."""
    ws, user = _make_workspace_with_user("noop@k4.test", "WS")

    client = APIClient()
    _login(client, user)
    create_response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "Static",
            "text_content": "Line one.\nLine two.",
        },
        format="json",
    )
    doc_id = create_response.json()["id"]
    original = KnowledgeDocument.objects.get(pk=doc_id)
    original_hash = original.content_hash
    original_chunk_ids = list(original.chunks.values_list("pk", flat=True))
    assert original_chunk_ids, "seed create should have produced chunks"

    # Same text, plus trailing whitespace that _normalize collapses.
    patch_response = client.patch(
        f"/api/knowledge/{doc_id}/",
        {"text_content": "Line one.   \nLine two.   \n"},
        format="json",
    )
    assert patch_response.status_code == http.HTTP_200_OK

    unchanged = KnowledgeDocument.objects.get(pk=doc_id)
    assert unchanged.content_hash == original_hash
    # Chunks were not touched — same primary keys.
    assert list(unchanged.chunks.values_list("pk", flat=True)) == original_chunk_ids


def test_patch_text_content_rejects_empty() -> None:
    """Whitespace-only content is not a valid save — the operator
    is either editing to something real or should delete."""
    ws, user = _make_workspace_with_user("empty@k4.test", "WS")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="t",
        document_type=DocumentType.TEXT,
        processed_content="original", content_hash="HASH-EMPTY",
        ingested_via="paste",
    )
    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"text_content": "   \n\n   "},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_patch_text_content_rejects_workspace_hash_collision() -> None:
    """(workspace, content_hash) is unique. If the operator edits
    doc A to match doc B's existing content, we hand back a
    clean 400 instead of letting the DB raise IntegrityError."""
    ws, user = _make_workspace_with_user("clash@k4.test", "WS")

    client = APIClient()
    _login(client, user)
    # Doc B occupies "This exact text."
    client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "B",
            "text_content": "This exact text.",
        },
        format="json",
    )
    # Doc A starts different.
    a_response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "A",
            "text_content": "Something else entirely.",
        },
        format="json",
    )
    a_id = a_response.json()["id"]

    # Editing A to collide with B's content — rejected.
    patch_response = client.patch(
        f"/api/knowledge/{a_id}/",
        {"text_content": "This exact text."},
        format="json",
    )
    assert patch_response.status_code == http.HTTP_400_BAD_REQUEST
    assert "text_content" in patch_response.json()


def test_patch_text_content_and_title_together() -> None:
    """Both fields in one PATCH — title updates + content re-
    ingests. Common operator flow: renaming the note while
    correcting it."""
    ws, user = _make_workspace_with_user("both@k4.test", "WS")

    client = APIClient()
    _login(client, user)
    create_response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "old-title",
            "text_content": "old body content.",
        },
        format="json",
    )
    doc_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/knowledge/{doc_id}/",
        {
            "title": "new-title",
            "text_content": "new body content.",
        },
        format="json",
    )
    assert patch_response.status_code == http.HTTP_200_OK

    doc = KnowledgeDocument.objects.get(pk=doc_id)
    assert doc.title == "new-title"
    assert doc.processed_content == "new body content."


def test_patch_text_content_denied_for_outsider() -> None:
    """Workspace-scope: caller from workspace A cannot PATCH a doc
    in workspace B (queryset filter → 404, not 403)."""
    ws_a, user_a = _make_workspace_with_user("outa@k4.test", "A")
    ws_b, _user_b = _make_workspace_with_user("outb@k4.test", "B")
    doc_b = KnowledgeDocument.objects.create(
        workspace=ws_b, title="B doc",
        document_type=DocumentType.TEXT,
        processed_content="orig", content_hash="HASH-OUT",
        ingested_via="paste",
    )
    client = APIClient()
    _login(client, user_a)
    response = client.patch(
        f"/api/knowledge/{doc_b.pk}/",
        {"text_content": "hijack"},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND

    doc_b.refresh_from_db()
    assert doc_b.processed_content == "orig"


def test_delete_soft_deletes() -> None:
    ws, user = _make_workspace_with_user("sd@k4.test", "WS")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="t",
        document_type=DocumentType.TEXT,
        processed_content="x", content_hash="HASH-SD",
        ingested_via="paste",
    )
    client = APIClient()
    _login(client, user)
    response = client.delete(f"/api/knowledge/{doc.pk}/")
    assert response.status_code == http.HTTP_204_NO_CONTENT
    doc.refresh_from_db()
    assert doc.is_active is False
    # And the list view no longer includes it
    list_response = client.get("/api/knowledge/")
    titles = {row["title"] for row in _rows(list_response.json())}
    assert "t" not in titles


# ---- helpers --------------------------------------------


def _rows(body):
    """DRF can return either a paginated dict or a bare list
    depending on the global pagination settings. Normalise."""
    if isinstance(body, dict) and "results" in body:
        return body["results"]
    return body


# =====================================================================
# SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-26) — DRF-boundary
# tests for the explicit WORKSPACE fresh-create marker. Covers the
# serializer's contradiction rejection + write-only forwarding into
# ``_persist``. Ingestion-boundary tests are in test_ingestion.py.
# =====================================================================


def test_slice12_api_workspace_marker_stamps_workspace() -> None:
    """Slice 12 — end-to-end via DRF. Payload with the marker but
    without ``spokesperson_ids`` or ``universe`` produces a
    WORKSPACE-stamped KD."""
    ws, user = _make_workspace_with_user("s12-w@k4.test", "S12WS")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "slice12-api-workspace",
            "text_content": "Content marked workspace-shared at API.",
            "audience_scope": "workspace",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    body = response.json()

    doc = KnowledgeDocument.objects.get(pk=body["id"])
    assert doc.audience_scope == AudienceScope.WORKSPACE
    assert doc.universe_id is None
    assert doc.spokespeople.count() == 0


def test_slice12_api_omission_remains_null() -> None:
    """Slice 12 — DRF payload with no spokespeople + no Universe + no
    marker must NOT be silently defaulted to WORKSPACE by the
    serializer."""
    ws, user = _make_workspace_with_user("s12-null@k4.test", "S12Null")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "slice12-api-null",
            "text_content": "Content with no marker at API.",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    body = response.json()

    doc = KnowledgeDocument.objects.get(pk=body["id"])
    assert doc.audience_scope is None, (
        "DRF serializer must not silently default omission to WORKSPACE"
    )


def test_slice12_api_rejects_marker_with_spokespeople() -> None:
    """Slice 12 — serializer rejects contradiction with 400."""
    ws, user = _make_workspace_with_user("s12-cont-sp@k4.test", "S12CS")
    client = APIClient()
    _login(client, user)
    a = Teammate.objects.create(workspace=ws, name="A")

    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "slice12-api-contradiction-sp",
            "text_content": "Contradictory payload.",
            "spokesperson_ids": [str(a.pk)],
            "audience_scope": "workspace",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert "audience_scope" in body or "non_field_errors" in body


def test_slice12_api_rejects_marker_with_universe() -> None:
    """Slice 12 — serializer rejects Universe + marker."""
    ws, user = _make_workspace_with_user("s12-cont-u@k4.test", "S12CU")
    client = APIClient()
    _login(client, user)
    u = Universe.objects.create(workspace=ws, name="S12CU U")

    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "slice12-api-contradiction-u",
            "text_content": "Contradictory payload with universe.",
            "universe": str(u.pk),
            "audience_scope": "workspace",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert "audience_scope" in body or "non_field_errors" in body


def test_slice12_api_rejects_invalid_audience_scope_value() -> None:
    """Slice 12 — only ``"workspace"`` is a valid marker value. The
    serializer's ChoiceField rejects any other string with 400. Ensures
    the marker cannot be used to stamp CHARACTER / UNIVERSE / NONE via
    the API — those states only derive from their positive inputs."""
    ws, user = _make_workspace_with_user("s12-bad@k4.test", "S12Bad")
    client = APIClient()
    _login(client, user)

    for bad_value in ("character", "universe", "none", "anything"):
        response = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "title": f"slice12-bad-{bad_value}",
                "text_content": "Content with bad marker.",
                "audience_scope": bad_value,
            },
            format="json",
        )
        assert response.status_code == http.HTTP_400_BAD_REQUEST, (
            f"expected 400 for audience_scope={bad_value!r}, got "
            f"{response.status_code}: {response.content}"
        )


def test_slice12_api_patch_ignores_marker() -> None:
    """Slice 12 — PATCH must silently ignore the marker (create-only).
    An existing CHARACTER-scoped row must not be transitioned to
    WORKSPACE by PATCHing ``audience_scope=workspace``.
    """
    ws, user = _make_workspace_with_user("s12-patch@k4.test", "S12P")
    client = APIClient()
    _login(client, user)
    a = Teammate.objects.create(workspace=ws, name="A")

    # Create a CHARACTER-scoped KD via existing path.
    create_resp = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "title": "slice12-patch-target",
            "text_content": "Character-scoped content.",
            "spokesperson_ids": [str(a.pk)],
        },
        format="json",
    )
    assert create_resp.status_code == http.HTTP_201_CREATED
    kd_id = create_resp.json()["id"]
    kd = KnowledgeDocument.objects.get(pk=kd_id)
    assert kd.audience_scope == AudienceScope.CHARACTER

    # PATCH with the marker — should be silently ignored, not applied.
    patch_resp = client.patch(
        f"/api/knowledge/{kd_id}/",
        {"audience_scope": "workspace"},
        format="json",
    )
    # PATCH should succeed (200) — the field is silently dropped.
    assert patch_resp.status_code == http.HTTP_200_OK, patch_resp.content
    kd.refresh_from_db()
    assert kd.audience_scope == AudienceScope.CHARACTER, (
        "PATCH must not transition audience_scope via the marker"
    )
    assert list(kd.spokespeople.values_list("pk", flat=True)) == [a.pk]
