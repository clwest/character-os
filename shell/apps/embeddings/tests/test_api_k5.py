"""SESSION 138 / K5 — spokesperson-filtered list + attach/detach.

The list-by-spokesperson filter mirrors
``retrieve_for_spokesperson``'s visibility logic: a doc is
visible to a spokesperson if it has no M2M attachments OR the
spokesperson is one of the attached. Tests assert that
ordering plus the attach/detach round-trip (and the idempotent
+ cross-workspace cases).
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    DocumentType,
    KnowledgeDocument,
)
from apps.spokespeople.models import Spokesperson
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_and_eager():
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _user_with_workspace(email: str, name: str) -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_doc(ws: Workspace, title: str, *, spokespeople=None) -> KnowledgeDocument:
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        processed_content=title, content_hash=f"HASH-{title}",
        ingested_via="paste",
    )
    if spokespeople:
        doc.spokespeople.set(spokespeople)
    return doc


def _rows(body):
    return body["results"] if isinstance(body, dict) and "results" in body else body


# ---- ?spokesperson=<uuid> filter -------------------------


def test_filter_by_spokesperson_returns_visible_docs() -> None:
    ws, user = _user_with_workspace("k5a@test", "WS A")
    sp_general = Spokesperson.objects.create(workspace=ws, name="General")
    sp_specific = Spokesperson.objects.create(workspace=ws, name="Specific")

    open_doc = _make_doc(ws, "open")  # no M2M = visible to all
    locked_doc = _make_doc(ws, "locked", spokespeople=[sp_specific])

    client = APIClient()
    client.force_authenticate(user=user)

    # General spokesperson — sees only the open doc
    response = client.get(f"/api/knowledge/?spokesperson={sp_general.pk}")
    assert response.status_code == http.HTTP_200_OK
    titles = {row["title"] for row in _rows(response.json())}
    assert open_doc.title in titles
    assert locked_doc.title not in titles

    # Specific spokesperson — sees both
    response = client.get(f"/api/knowledge/?spokesperson={sp_specific.pk}")
    titles = {row["title"] for row in _rows(response.json())}
    assert open_doc.title in titles
    assert locked_doc.title in titles


def test_filter_by_spokesperson_excludes_other_workspaces() -> None:
    """A spokesperson filter never leaks across workspaces even
    if the caller is also a member of the other workspace —
    the visibility filter intersects with the workspace
    membership filter."""
    ws_a, user = _user_with_workspace("k5b@test", "A")
    sp_a = Spokesperson.objects.create(workspace=ws_a, name="SP A")

    # Different workspace + different user; current user has no
    # membership there
    _ws_b, _other = _user_with_workspace("k5b_other@test", "B")
    # Even though sp_a is in ws_a, querying with its id should
    # never surface ws_b docs:
    foreign_doc = _make_doc(_ws_b, "foreign-doc")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get(f"/api/knowledge/?spokesperson={sp_a.pk}")
    titles = {row["title"] for row in _rows(response.json())}
    assert foreign_doc.title not in titles


# ---- attach/detach actions -------------------------------


def test_attach_adds_spokesperson_to_m2m() -> None:
    ws, user = _user_with_workspace("k5c@test", "WS C")
    sp = Spokesperson.objects.create(workspace=ws, name="Riggs")
    doc = _make_doc(ws, "attach-target")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/attach/",
        {"spokesperson_id": str(sp.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert sp in list(doc.spokespeople.all())


def test_attach_is_idempotent() -> None:
    ws, user = _user_with_workspace("k5d@test", "WS D")
    sp = Spokesperson.objects.create(workspace=ws, name="Sasha")
    doc = _make_doc(ws, "idem-attach", spokespeople=[sp])

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/attach/",
        {"spokesperson_id": str(sp.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert doc.spokespeople.count() == 1


def test_detach_removes_spokesperson() -> None:
    ws, user = _user_with_workspace("k5e@test", "WS E")
    sp = Spokesperson.objects.create(workspace=ws, name="Maya")
    doc = _make_doc(ws, "detach-target", spokespeople=[sp])

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(sp.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    doc.refresh_from_db()
    assert sp not in list(doc.spokespeople.all())


def test_detach_is_idempotent() -> None:
    ws, user = _user_with_workspace("k5f@test", "WS F")
    sp = Spokesperson.objects.create(workspace=ws, name="Donny")
    doc = _make_doc(ws, "idem-detach")  # never attached

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(sp.pk)},
        format="json",
    )
    # Idempotent — Django M2M ``.remove()`` is a no-op when the
    # row isn't present.
    assert response.status_code == http.HTTP_200_OK


def test_attach_rejects_cross_workspace_spokesperson() -> None:
    ws_a, user_a = _user_with_workspace("k5g_a@test", "GA")
    ws_b, _user_b = _user_with_workspace("k5g_b@test", "GB")

    doc_in_a = _make_doc(ws_a, "doc-in-a")
    sp_in_b = Spokesperson.objects.create(workspace=ws_b, name="Foreign")

    client = APIClient()
    client.force_authenticate(user=user_a)
    response = client.post(
        f"/api/knowledge/{doc_in_a.pk}/attach/",
        {"spokesperson_id": str(sp_in_b.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_attach_404s_for_unknown_spokesperson() -> None:
    import uuid

    ws, user = _user_with_workspace("k5h@test", "WS H")
    doc = _make_doc(ws, "doc-h")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/attach/",
        {"spokesperson_id": str(uuid.uuid4())},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_attach_requires_spokesperson_id() -> None:
    ws, user = _user_with_workspace("k5i@test", "WS I")
    doc = _make_doc(ws, "doc-i")

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/attach/",
        {},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_attach_404s_for_outsider() -> None:
    """A user without membership in the workspace gets a 404
    when trying to attach (queryset excludes the doc from
    their list, so detail lookup fails)."""
    ws_a, _user_a = _user_with_workspace("k5j_a@test", "JA")
    ws_b, user_b = _user_with_workspace("k5j_b@test", "JB")
    doc_in_a = _make_doc(ws_a, "doc-j-a")
    sp_in_b = Spokesperson.objects.create(workspace=ws_b, name="JB-SP")

    client = APIClient()
    client.force_authenticate(user=user_b)
    response = client.post(
        f"/api/knowledge/{doc_in_a.pk}/attach/",
        {"spokesperson_id": str(sp_in_b.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND
