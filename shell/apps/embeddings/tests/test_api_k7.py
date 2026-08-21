"""SESSION 140 / K7 — URL ingest + search-action API tests.

Covers:
* ``POST /api/knowledge/`` with ``source_url_input`` payload —
  fetch + extract + persist + embed (eager Celery).
* ``via_serper=True`` sets ``ingested_via='serper'``.
* Three-way XOR validation: text vs PDF vs URL — exactly one.
* URL fetch failure surfaces as a clean 400.
* ``POST /api/knowledge/search/`` returns serper results.
* search endpoint validates ``q`` + requires auth.

Mocks ``url_fetch.fetch_url`` and the serper httpx call so
tests stay hermetic.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.embeddings.url_fetch import ExtractedUrl
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mocks():
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        SERPER_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _user_ws(email: str, ws_name: str) -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = ws_name
    ws.save()
    return ws, user


# ---- URL create -------------------------------------------


def _fake_extracted(url: str = "https://example.com/article") -> ExtractedUrl:
    return ExtractedUrl(
        url=url,
        title="Sample Article",
        text=(
            "First paragraph of substantive article content here.\n\n"
            "Second paragraph keeps going with more relevant text."
        ),
        metadata={
            "hostname": "example.com",
            "author": "Jane Doe",
            "fetched_chars": 1024,
            "extracted_chars": 96,
        },
    )


def test_create_via_source_url_input_runs_full_pipeline() -> None:
    ws, user = _user_ws("k7a@test", "K7 WS A")

    client = APIClient()
    client.force_authenticate(user=user)
    with patch(
        "apps.embeddings.ingestion.url_fetch.fetch_url",
        return_value=_fake_extracted(),
    ):
        response = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "source_url_input": "https://example.com/article",
                "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
            },
            format="json",
        )

    assert response.status_code == http.HTTP_201_CREATED, response.content
    body = response.json()
    assert body["document_type"] == DocumentType.URL
    assert body["status"] == DocumentStatus.PROCESSED
    assert body["ingested_via"] == IngestedVia.PASTE
    assert body["source_url"] == "https://example.com/article"
    # Title falls back to the extracted page title when caller didn't supply one
    assert body["title"] == "Sample Article"
    assert body["chunk_count"] >= 1
    # Metadata from trafilatura carries through
    assert body["source_metadata"]["hostname"] == "example.com"
    assert body["source_metadata"]["author"] == "Jane Doe"


def test_create_via_source_url_input_with_via_serper_marks_ingested_via() -> None:
    ws, user = _user_ws("k7b@test", "K7 WS B")

    client = APIClient()
    client.force_authenticate(user=user)
    with patch(
        "apps.embeddings.ingestion.url_fetch.fetch_url",
        return_value=_fake_extracted(),
    ):
        response = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "source_url_input": "https://example.com/article",
                "via_serper": True,
                "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
            },
            format="json",
        )

    assert response.status_code == http.HTTP_201_CREATED
    assert response.json()["ingested_via"] == IngestedVia.SERPER


def test_create_via_source_url_with_caller_title_overrides_extracted() -> None:
    ws, user = _user_ws("k7c@test", "K7 WS C")

    client = APIClient()
    client.force_authenticate(user=user)
    with patch(
        "apps.embeddings.ingestion.url_fetch.fetch_url",
        return_value=_fake_extracted(),
    ):
        response = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "source_url_input": "https://example.com/article",
                "title": "Operator's own title",
                "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
            },
            format="json",
        )

    assert response.status_code == http.HTTP_201_CREATED
    assert response.json()["title"] == "Operator's own title"


def test_create_via_source_url_failure_surfaces_400() -> None:
    from apps.embeddings.url_fetch import UrlFetchError

    ws, user = _user_ws("k7d@test", "K7 WS D")

    client = APIClient()
    client.force_authenticate(user=user)
    with patch(
        "apps.embeddings.ingestion.url_fetch.fetch_url",
        side_effect=UrlFetchError("server returned 404"),
    ):
        response = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "source_url_input": "https://example.com/missing",
                "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
            },
            format="json",
        )

    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert "source_url_input" in body
    assert "404" in str(body["source_url_input"])


# ---- three-way XOR validation -----------------------------


def test_create_rejects_text_and_url() -> None:
    ws, user = _user_ws("k7e@test", "K7 WS E")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "text_content": "hello",
            "source_url_input": "https://example.com/x",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_pdf_and_url() -> None:
    ws, user = _user_ws("k7f@test", "K7 WS F")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/knowledge/",
        {
            "workspace": str(ws.pk),
            "pdf_data_uri": "data:application/pdf;base64,Zm9vYmFy",
            "source_url_input": "https://example.com/x",
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


# ---- search action ----------------------------------------


def test_search_returns_results_in_force_mock_mode() -> None:
    _, user = _user_ws("k7g@test", "K7 WS G")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/knowledge/search/",
        {"q": "character os"},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    body = response.json()
    assert body["query"] == "character os"
    assert len(body["results"]) > 0
    first = body["results"][0]
    assert "title" in first
    assert "url" in first
    assert "snippet" in first
    assert first["position"] == 1


def test_search_requires_query() -> None:
    _, user = _user_ws("k7h@test", "K7 WS H")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post("/api/knowledge/search/", {}, format="json")
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    assert "q" in response.json()


def test_search_requires_authentication() -> None:
    client = APIClient()
    response = client.post(
        "/api/knowledge/search/",
        {"q": "anything"},
        format="json",
    )
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED,
        http.HTTP_403_FORBIDDEN,
    }


def test_search_respects_top_k_clamp() -> None:
    _, user = _user_ws("k7i@test", "K7 WS I")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/knowledge/search/",
        {"q": "top k test", "top_k": 999},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    # Clamped to MAX_TOP_K = 20
    assert len(response.json()["results"]) == 20


def test_search_502_when_serper_errors_and_not_mocked() -> None:
    import os

    from apps.embeddings.serper import SerperError

    _, user = _user_ws("k7j@test", "K7 WS J")
    client = APIClient()
    client.force_authenticate(user=user)

    with override_settings(SERPER_FORCE_MOCK=False), \
         patch.dict(os.environ, {"SERPER_API_KEY": "fake-key"}), \
         patch(
            "apps.embeddings.serper._call_serper",
            side_effect=SerperError("upstream down"),
        ):
        # Clear cache so we hit the patched call
        from django.core.cache import cache
        cache.clear()
        response = client.post(
            "/api/knowledge/search/",
            {"q": "upstream broken"},
            format="json",
        )

    assert response.status_code == http.HTTP_502_BAD_GATEWAY


# ---- URL dedup --------------------------------------------


def test_url_ingest_is_idempotent_via_content_hash() -> None:
    """Same URL → same extracted content → same content_hash →
    second ingest dedups to the first row."""
    ws, user = _user_ws("k7k@test", "K7 WS K")
    fake = _fake_extracted("https://dedup.example.com/")

    client = APIClient()
    client.force_authenticate(user=user)
    with patch(
        "apps.embeddings.ingestion.url_fetch.fetch_url",
        return_value=fake,
    ):
        r1 = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "source_url_input": "https://dedup.example.com/",
                "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
            },
            format="json",
        )
        r2 = client.post(
            "/api/knowledge/",
            {
                "workspace": str(ws.pk),
                "source_url_input": "https://dedup.example.com/",
                "audience_scope": "workspace",  # SESSION 276 Slice 20 positive audience
            },
            format="json",
        )

    assert r1.status_code == http.HTTP_201_CREATED
    # DRF doesn't return a 200/dedup signal — the serializer
    # returns the existing row's serialised representation as
    # a 201. Both responses should carry the same id.
    assert r2.status_code == http.HTTP_201_CREATED
    assert r1.json()["id"] == r2.json()["id"]
    assert KnowledgeDocument.objects.filter(
        workspace=ws, source_url="https://dedup.example.com/",
    ).count() == 1
