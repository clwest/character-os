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
        "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
            "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
                    "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
            "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
            "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
            "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
            "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
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
    """Slice 12 (SUPERSEDED by Slice 20 Q-276-36) — DRF CREATE payload
    with no spokespeople + no Universe + no ``audience_scope="workspace"``
    marker now fails at the serializer boundary with a 4xx instead of
    landing at ``audience_scope=NULL``. See
    ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §345/§346.
    """
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
    assert response.status_code == http.HTTP_400_BAD_REQUEST, response.content
    assert not KnowledgeDocument.objects.filter(
        workspace=ws, title="slice12-api-null",
    ).exists(), "no KD row must persist when the API fails closed"


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


# =====================================================================
# SESSION 276 Slice 14 / Delta Stage 3C-2 (Q-276-28) — PATCH empty-
# spokesperson-set on active CHARACTER KDs fails closed with the
# same structured error the Slice 13 /detach/ guard returns. Symmetric
# invariant: CHARACTER requires at least one spokesperson. See
# docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §230-§252.
# =====================================================================


FINAL_DETACH_CODE = "final_character_detach_requires_audience_decision"


def _make_char_doc_with_sp(
    ws: Workspace,
    title: str,
    spokespeople: list[Teammate],
    *,
    universe=None,
) -> KnowledgeDocument:
    """Slice 14 helper — matches Slice 10's CREATE-time CHARACTER stamp
    so PATCH semantics test the intended shape."""
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        processed_content=title, content_hash=f"HASH-{title}",
        ingested_via="paste",
        universe=universe,
        audience_scope=AudienceScope.CHARACTER,
    )
    doc.spokespeople.set(spokespeople)
    return doc


# ---- Test A — CHARACTER {A} + PATCH [] rejected ----


def test_slice14_A_patch_empty_on_single_character_rejected() -> None:
    ws, user = _make_workspace_with_user("s14-a@k4.test", "S14A")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    doc = _make_char_doc_with_sp(ws, "s14-a", [a])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST, response.content
    body = response.json()
    assert body.get("code") == FINAL_DETACH_CODE, body
    assert isinstance(body.get("detail"), str) and body["detail"], body

    doc.refresh_from_db()
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.is_active is True
    assert doc.deactivated_reason == ""
    assert doc.title == "s14-a"


# ---- Test B — CHARACTER {A,B} + PATCH [] also rejected ----


def test_slice14_B_patch_empty_on_multi_character_also_rejected() -> None:
    """Slice 14 Test B — proves the invariant is about the RESULTING
    row shape (CHARACTER + empty M2M is malformed), not about count>1
    protection. Empty-list PATCH on a two-member CHARACTER row fails
    identically to a one-member row."""
    ws, user = _make_workspace_with_user("s14-b@k4.test", "S14B")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    b = Teammate.objects.create(workspace=ws, name="Beta")
    doc = _make_char_doc_with_sp(ws, "s14-b", [a, b])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body.get("code") == FINAL_DETACH_CODE

    doc.refresh_from_db()
    assert set(doc.spokespeople.values_list("pk", flat=True)) == {a.pk, b.pk}


# ---- Test C — narrowing via PATCH still works ----


def test_slice14_C_patch_narrowing_still_works() -> None:
    ws, user = _make_workspace_with_user("s14-c@k4.test", "S14C")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    b = Teammate.objects.create(workspace=ws, name="Beta")
    doc = _make_char_doc_with_sp(ws, "s14-c", [a, b])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": [str(b.pk)]},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [b.pk]
    assert doc.audience_scope == AudienceScope.CHARACTER


# ---- Test D — character replacement via PATCH still works ----


def test_slice14_D_patch_character_replacement_works() -> None:
    ws, user = _make_workspace_with_user("s14-d@k4.test", "S14D")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    b = Teammate.objects.create(workspace=ws, name="Beta")
    doc = _make_char_doc_with_sp(ws, "s14-d", [a])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": [str(b.pk)]},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [b.pk]


# ---- Test E — Universe-scoped CHARACTER + empty rejected ----


def test_slice14_E_universe_scoped_character_empty_patch_rejected() -> None:
    """Slice 14 Test E — Universe context does NOT auto-promote to
    UNIVERSE-shared via an empty spokespeople PATCH."""
    ws, user = _make_workspace_with_user("s14-e@k4.test", "S14E")
    u = Universe.objects.create(workspace=ws, name="S14E U")
    a = Teammate.objects.create(workspace=ws, name="Alpha", universe=u)
    doc = _make_char_doc_with_sp(ws, "s14-e", [a], universe=u)

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body.get("code") == FINAL_DETACH_CODE

    doc.refresh_from_db()
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.universe_id == u.pk


# ---- Test F — shared-canon rows (UNIVERSE/WORKSPACE) PATCH [] is no-op ----


def test_slice14_F_workspace_row_patch_empty_is_noop_unchanged() -> None:
    """Slice 14 Test F — WORKSPACE-audience row (already empty M2M
    by construction). PATCH sp_ids=[] is a no-op today and remains
    so — the Slice 14 guard is CHARACTER-only."""
    ws, user = _make_workspace_with_user("s14-f-ws@k4.test", "S14FWS")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="s14-f-ws",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S14FWS",
        ingested_via="paste",
        audience_scope=AudienceScope.WORKSPACE,
    )  # M2M intentionally empty

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.WORKSPACE
    assert doc.spokespeople.count() == 0


def test_slice14_F_universe_row_patch_empty_is_noop_unchanged() -> None:
    """Slice 14 Test F (paired) — same for UNIVERSE canon rows."""
    ws, user = _make_workspace_with_user("s14-f-u@k4.test", "S14FU")
    u = Universe.objects.create(workspace=ws, name="S14FU U")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="s14-f-u",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S14FU",
        ingested_via="paste",
        universe=u,
        audience_scope=AudienceScope.UNIVERSE,
    )

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.UNIVERSE
    assert doc.universe_id == u.pk
    assert doc.spokespeople.count() == 0


# ---- Test G — legacy NULL row PATCH [] preserved (carve-out) ----


def test_slice14_G_legacy_null_audience_patch_empty_preserved() -> None:
    """Slice 14 Test G — a legacy NULL-audience row (pre-Slice-10
    shape, only exists in test fixtures — real DB has zero) is NOT
    guarded by Slice 14. PATCH sp_ids=[] on it behaves as before,
    emptying the M2M without stamping any audience. Documents the
    deliberate carve-out for the transitional debt."""
    ws, user = _make_workspace_with_user("s14-g@k4.test", "S14G")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    # Legacy shape: direct create without audience_scope + explicit
    # M2M attach post-creation.
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="s14-g",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S14G",
        ingested_via="paste",
    )
    doc.spokespeople.set([a])
    assert doc.audience_scope is None
    assert doc.spokespeople.count() == 1

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    # Legacy behavior preserved — 200 OK, M2M emptied.
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert doc.audience_scope is None
    assert doc.spokespeople.count() == 0


# ---- Test H — atomic rejection preserves unrelated fields ----


def test_slice14_H_rejected_patch_does_not_partially_persist_title() -> None:
    """Slice 14 Test H — the guard lives in ``validate()``, which runs
    inside DRF's ``is_valid()`` phase BEFORE ``save()``/``update()``.
    A PATCH that bundles a valid title change with an invalid empty
    spokespeople list must fail the whole request; neither field
    should partially persist."""
    ws, user = _make_workspace_with_user("s14-h@k4.test", "S14H")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    doc = _make_char_doc_with_sp(ws, "s14-h", [a])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"title": "changed-title", "spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body.get("code") == FINAL_DETACH_CODE

    doc.refresh_from_db()
    # Title MUST NOT have changed — the guard rejected the whole request.
    assert doc.title == "s14-h", (
        "title must not partially persist when the guard rejects the "
        "same-request audience mutation"
    )
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]


# ---- Test I — combined Universe + empty rejected ----


def test_slice14_I_combined_universe_plus_empty_rejected() -> None:
    """Slice 14 Test I — a PATCH that bundles a Universe reassignment
    with an empty spokespeople list on an active CHARACTER row must
    NOT sneak through the audience-broadening path via Universe.
    The empty-list rejection fires first (in validate()); the whole
    request 400s; no partial state persists.

    Slice 14 does NOT define the "correct" Universe-transition
    audience semantics — those remain a separate unresolved question.
    The invariant this test protects is: an invalid CHARACTER shape
    is never persisted regardless of what else is in the payload.
    """
    ws, user = _make_workspace_with_user("s14-i@k4.test", "S14I")
    u_from = Universe.objects.create(workspace=ws, name="S14I From")
    u_to = Universe.objects.create(workspace=ws, name="S14I To")
    a = Teammate.objects.create(workspace=ws, name="Alpha", universe=u_from)
    doc = _make_char_doc_with_sp(ws, "s14-i", [a], universe=u_from)

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": str(u_to.pk), "spokesperson_ids": []},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST

    doc.refresh_from_db()
    # Universe MUST NOT have moved — request atomically rejected.
    assert doc.universe_id == u_from.pk, (
        "Universe must not partially persist alongside a rejected "
        "empty-spokespeople payload"
    )
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]
    assert doc.audience_scope == AudienceScope.CHARACTER


# ---- Error-contract consistency with Slice 13 detach ----


def test_slice14_error_code_matches_slice13_detach_guard() -> None:
    """Slice 14 — SPA + external clients should be able to discriminate
    the same underlying invariant across BOTH mutation surfaces
    (``/detach/`` and PATCH) using the same ``code`` value. This test
    hits both endpoints and asserts the ``code`` string is byte-
    identical, preventing future drift between the two guards.
    """
    ws, user = _make_workspace_with_user("s14-code@k4.test", "S14C")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    doc = _make_char_doc_with_sp(ws, "s14-code", [a])

    client = APIClient()
    _login(client, user)

    detach_resp = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert detach_resp.status_code == http.HTTP_400_BAD_REQUEST
    detach_code = detach_resp.json().get("code")

    patch_resp = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"spokesperson_ids": []},
        format="json",
    )
    assert patch_resp.status_code == http.HTTP_400_BAD_REQUEST
    patch_code = patch_resp.json().get("code")

    assert detach_code == patch_code == FINAL_DETACH_CODE, (
        f"error code drift: detach={detach_code!r} patch={patch_code!r}"
    )


# =====================================================================
# SESSION 276 Slice 15 / Delta Stage 3C-3 (Q-276-29) — Universe
# reassignment shape-preservation guards on PATCH. Reject two malformed
# Delta transitions (UNIVERSE+null and WORKSPACE+non-null) BEFORE any
# mutation. Do NOT auto-transition audience. Do NOT change CHARACTER
# Universe move behavior (existing M2M-orphan preflight already
# protects). See §254-§278 of the audit doc.
# =====================================================================


UNIVERSE_AUDIENCE_REQUIRES_UNIVERSE = "universe_audience_row_requires_universe"
WORKSPACE_AUDIENCE_FORBIDS_UNIVERSE = "workspace_audience_row_forbids_universe"


def _make_universe_canon(
    ws: Workspace, title: str, universe: Universe,
) -> KnowledgeDocument:
    """Slice 15 helper — creates a UNIVERSE-audience canon row
    matching the Slice 11 fresh-CREATE inference: universe non-null,
    M2M empty, audience_scope=UNIVERSE."""
    return KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        processed_content=title, content_hash=f"HASH-{title}",
        ingested_via="paste",
        universe=universe,
        audience_scope=AudienceScope.UNIVERSE,
    )


def _make_workspace_canon(ws: Workspace, title: str) -> KnowledgeDocument:
    """Slice 15 helper — creates a WORKSPACE-audience canon row
    matching the Slice 12 fresh-CREATE marker path: universe null,
    M2M empty, audience_scope=WORKSPACE."""
    return KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        processed_content=title, content_hash=f"HASH-{title}",
        ingested_via="paste",
        audience_scope=AudienceScope.WORKSPACE,
    )


# ---- Test B — UNIVERSE + PATCH universe=null rejected ----


def test_slice15_universe_row_rejects_universe_removal() -> None:
    """Slice 15 Guard #1 — PATCH universe=null on a UNIVERSE-audience
    row would produce audience_scope=UNIVERSE + universe=NULL, the
    Slice 4 §51 row-#5 malformed shape. Reject with structured 4xx."""
    ws, user = _make_workspace_with_user("s15-b@k4.test", "S15B")
    u = Universe.objects.create(workspace=ws, name="S15B U")
    doc = _make_universe_canon(ws, "s15-b", u)

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": None},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST, response.content
    body = response.json()
    assert body.get("code") == UNIVERSE_AUDIENCE_REQUIRES_UNIVERSE, body
    assert isinstance(body.get("detail"), str) and body["detail"], body

    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.UNIVERSE
    assert doc.universe_id == u.pk
    assert doc.is_active is True


# ---- Test C — WORKSPACE + PATCH universe=U rejected ----


def test_slice15_workspace_row_rejects_universe_assignment() -> None:
    """Slice 15 Guard #2 — PATCH universe=<U> on a WORKSPACE-audience
    row would produce audience_scope=WORKSPACE + universe=U, the
    Slice 4 §51 row-#7 malformed shape. Reject."""
    ws, user = _make_workspace_with_user("s15-c@k4.test", "S15C")
    u = Universe.objects.create(workspace=ws, name="S15C U")
    doc = _make_workspace_canon(ws, "s15-c")

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": str(u.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST, response.content
    body = response.json()
    assert body.get("code") == WORKSPACE_AUDIENCE_FORBIDS_UNIVERSE, body

    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.WORKSPACE
    assert doc.universe_id is None
    assert doc.is_active is True


# ---- Test A — UNIVERSE + PATCH universe=U_new preserved (unchanged) ----


def test_slice15_universe_row_universe_swap_preserved() -> None:
    """Slice 15 Test A — UNIVERSE row + PATCH universe=U_new preserves
    current behavior. The audience-replacement question (is this a
    legitimate operator gesture?) is deferred until a positive-intent
    UI/API contract exists. Slice 15 does NOT change this behavior."""
    ws, user = _make_workspace_with_user("s15-a@k4.test", "S15A")
    u_old = Universe.objects.create(workspace=ws, name="S15A Old")
    u_new = Universe.objects.create(workspace=ws, name="S15A New")
    doc = _make_universe_canon(ws, "s15-a", u_old)

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": str(u_new.pk)},
        format="json",
    )
    # Preserved current behavior — Slice 15 did NOT block this.
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.UNIVERSE
    assert doc.universe_id == u_new.pk


# ---- Test D — CHARACTER Universe moves protected by existing preflight ----


def test_slice15_character_universe_swap_still_protected_by_existing_preflight() -> None:
    """Slice 15 Test D — CHARACTER + M2M members inside U_old + PATCH
    universe=U_new must reject via the existing M2M-orphan preflight
    at ``serializers.py:567-579`` (SESSION 261). Slice 15 did NOT
    modify this behavior; verifying it still works as designed."""
    ws, user = _make_workspace_with_user("s15-d@k4.test", "S15D")
    u_old = Universe.objects.create(workspace=ws, name="S15D Old")
    u_new = Universe.objects.create(workspace=ws, name="S15D New")
    a = Teammate.objects.create(workspace=ws, name="Alpha", universe=u_old)
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="s15-d",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S15D",
        ingested_via="paste",
        universe=u_old,
        audience_scope=AudienceScope.CHARACTER,
    )
    doc.spokespeople.set([a])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": str(u_new.pk)},
        format="json",
    )
    # SESSION 261 M2M-orphan preflight rejects: A.universe=U_old ≠ U_new.
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    # Not the Slice-15 code — this is the SESSION 261 preflight error.
    assert "universe" in body
    doc.refresh_from_db()
    assert doc.universe_id == u_old.pk
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]


# ---- Test E — CHARACTER + universe=U + M2M empty (already malformed) ----


def test_slice15_character_universe_empty_m2m_universe_removal_currently_passes() -> None:
    """Slice 15 characterization — a CHARACTER row with empty M2M
    is ALREADY malformed (Slice 4 §51 row #3). Slice 15 does NOT
    guard against Universe-PATCH on already-malformed rows because
    the CHARACTER+empty invariant is enforced at other mutation
    surfaces (Slice 13 detach, Slice 14 PATCH-empty). This test
    characterizes current behavior — real DB has zero such rows;
    only test fixtures land here."""
    ws, user = _make_workspace_with_user("s15-e@k4.test", "S15E")
    u = Universe.objects.create(workspace=ws, name="S15E U")
    # Directly construct the malformed shape (would not be reachable
    # via normal API paths post-Slice-13/14).
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="s15-e",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S15E",
        ingested_via="paste",
        universe=u,
        audience_scope=AudienceScope.CHARACTER,
    )  # NO M2M attached

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": None},
        format="json",
    )
    # Preflight passes (M2M empty); universe change applies.
    # Documented characterization: Slice 15 does not add coverage
    # for pre-malformed rows; those are Slice 13/14's problem class.
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.universe_id is None


# ---- Test F — atomic rejection preserves unrelated fields ----


def test_slice15_universe_removal_rejection_does_not_partially_persist_title() -> None:
    """Slice 15 — guard runs at top of update(); rejected PATCH must
    not partially persist unrelated fields such as title."""
    ws, user = _make_workspace_with_user("s15-f@k4.test", "S15F")
    u = Universe.objects.create(workspace=ws, name="S15F U")
    doc = _make_universe_canon(ws, "s15-f", u)

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"title": "changed-title", "universe": None},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body.get("code") == UNIVERSE_AUDIENCE_REQUIRES_UNIVERSE

    doc.refresh_from_db()
    # Title MUST NOT have changed — guard rejected the whole request.
    assert doc.title == "s15-f", (
        "title must not partially persist when the Universe guard rejects"
    )
    assert doc.universe_id == u.pk


# ---- Test G — NULL legacy row Universe PATCH characterization ----


def test_slice15_legacy_null_audience_universe_patch_characterization() -> None:
    """Slice 15 characterization — pre-Delta NULL-audience row +
    PATCH universe=U. Slice 15 does NOT classify these rows; the
    Universe FK change applies but audience_scope stays NULL
    (transitional). Documents deliberate carve-out. Real DB has
    zero such rows with any spokespeople attached; the 10 real NULL
    rows are all empty-M2M ambiguous historical rows requiring
    operator triage (Slice 4 §55.2)."""
    ws, user = _make_workspace_with_user("s15-g@k4.test", "S15G")
    u = Universe.objects.create(workspace=ws, name="S15G U")
    # Direct-create fixture matching the ambiguous legacy shape.
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="s15-g",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S15G",
        ingested_via="paste",
    )
    assert doc.audience_scope is None

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": str(u.pk)},
        format="json",
    )
    # Preserved current behavior — guards fire only on CHARACTER/
    # UNIVERSE/WORKSPACE, not on NULL transitional rows.
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert doc.audience_scope is None  # unchanged
    assert doc.universe_id == u.pk


# ---- Test H — inactive KD PATCH unreachable (queryset filter) ----


def test_slice15_inactive_kd_patch_returns_404() -> None:
    """Slice 15 characterization — inactive KDs are unreachable via
    PATCH because ``KnowledgeDocumentViewSet.get_queryset`` filters
    ``is_active=True`` (``views.py:70``). Confirms our guards need not
    handle inactive rows explicitly — the queryset gate blocks them
    first with 404."""
    ws, user = _make_workspace_with_user("s15-h@k4.test", "S15H")
    u = Universe.objects.create(workspace=ws, name="S15H U")
    doc = _make_universe_canon(ws, "s15-h", u)
    doc.is_active = False
    doc.deactivated_reason = "operator_delete"
    doc.save(update_fields=["is_active", "deactivated_reason", "updated_at"])

    client = APIClient()
    _login(client, user)
    response = client.patch(
        f"/api/knowledge/{doc.pk}/",
        {"universe": None},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND
