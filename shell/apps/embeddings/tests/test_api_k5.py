"""SESSION 138 / K5 — spokesperson-filtered list + attach/detach.

The list-by-spokesperson filter mirrors
``retrieve_for_teammate``'s visibility logic: a doc is
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
    AudienceScope,
    DocumentType,
    KnowledgeDocument,
    KnowledgeDocumentSpokesperson,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
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
    # SESSION 276 Slice 21: derive audience_scope from shape.
    scope = AudienceScope.CHARACTER if spokespeople else AudienceScope.WORKSPACE
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        processed_content=title, content_hash=f"HASH-{title}",
        ingested_via="paste",
        audience_scope=scope,
    )
    if spokespeople:
        doc.spokespeople.set(spokespeople)
    return doc


def _rows(body):
    return body["results"] if isinstance(body, dict) and "results" in body else body


# ---- ?spokesperson=<uuid> filter -------------------------


def test_filter_by_spokesperson_returns_visible_docs() -> None:
    ws, user = _user_with_workspace("k5a@test", "WS A")
    sp_general = Teammate.objects.create(workspace=ws, name="General")
    sp_specific = Teammate.objects.create(workspace=ws, name="Specific")

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
    sp_a = Teammate.objects.create(workspace=ws_a, name="SP A")

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
    sp = Teammate.objects.create(workspace=ws, name="Riggs")
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
    sp = Teammate.objects.create(workspace=ws, name="Sasha")
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
    sp = Teammate.objects.create(workspace=ws, name="Maya")
    keep = Teammate.objects.create(workspace=ws, name="Keep")
    # SESSION 276 Slice 13/21: CHARACTER-scoped detach is legal only
    # when at least one spokesperson remains. Fixture uses TWO
    # attached spokespeople so detaching Maya leaves Keep and the
    # CHARACTER invariant remains satisfied.
    doc = _make_doc(ws, "detach-target", spokespeople=[sp, keep])

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
    assert keep in list(doc.spokespeople.all())


def test_detach_is_idempotent() -> None:
    ws, user = _user_with_workspace("k5f@test", "WS F")
    sp = Teammate.objects.create(workspace=ws, name="Donny")
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
    sp_in_b = Teammate.objects.create(workspace=ws_b, name="Foreign")

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
    sp_in_b = Teammate.objects.create(workspace=ws_b, name="JB-SP")

    client = APIClient()
    client.force_authenticate(user=user_b)
    response = client.post(
        f"/api/knowledge/{doc_in_a.pk}/attach/",
        {"spokesperson_id": str(sp_in_b.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


# =====================================================================
# SESSION 276 Slice 13 / Delta Stage 3C-1 (refined Q-276-27) — final-
# character detach guard. Reject detach requests that would leave an
# active CHARACTER KD with an empty M2M. See §210-§232 of the audit
# doc.
# =====================================================================


FINAL_DETACH_CODE = "final_character_detach_requires_audience_decision"


def _make_character_doc(
    ws: Workspace, title: str, spokespeople: list[Teammate], *,
    universe: Universe | None = None,
) -> KnowledgeDocument:
    """Slice 13 helper — creates a KD with ``audience_scope=CHARACTER``
    stamped (matching Slice 10's CREATE behavior). Distinct from the
    module-level ``_make_doc`` which intentionally leaves audience_scope
    as NULL to preserve pre-Delta legacy detach test semantics.
    """
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


# ---- Test A — multi-character detach unchanged ----


def test_slice13_A_multi_character_detach_narrows_normally() -> None:
    """Slice 13 Test A — detach one of two spokespeople on a CHARACTER
    KD still succeeds; the surviving spokesperson remains attached;
    audience_scope stays CHARACTER."""
    ws, user = _user_with_workspace("s13-a@test", "S13 A")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    b = Teammate.objects.create(workspace=ws, name="Beta")
    doc = _make_character_doc(ws, "multi-detach", [a, b])

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content

    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.is_active is True
    assert doc.deactivated_reason == ""
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [b.pk]


# ---- Test B — final-character detach rejected ----


def test_slice13_B_final_character_detach_rejected() -> None:
    """Slice 13 Test B — the load-bearing regression. Detach of the
    sole spokesperson on a CHARACTER KD returns a structured 4xx;
    the KD is unchanged."""
    ws, user = _user_with_workspace("s13-b@test", "S13 B")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    doc = _make_character_doc(ws, "single-detach", [a])

    pre_active = doc.is_active
    pre_reason = doc.deactivated_reason
    pre_universe = doc.universe_id
    pre_chunks = doc.chunks.count()

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body.get("code") == FINAL_DETACH_CODE, body
    assert isinstance(body.get("detail"), str) and body["detail"], body

    doc.refresh_from_db()
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.is_active is pre_active
    assert doc.deactivated_reason == pre_reason
    assert doc.universe_id == pre_universe
    assert doc.chunks.count() == pre_chunks


# ---- Test C — no partial mutation ----


def test_slice13_C_final_detach_leaves_through_row_intact() -> None:
    """Slice 13 Test C — the guard runs BEFORE ``.remove()``. Verify
    the through-row count is byte-identical pre/post rejection."""
    ws, user = _user_with_workspace("s13-c@test", "S13 C")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    doc = _make_character_doc(ws, "no-partial", [a])

    pre_through = KnowledgeDocumentSpokesperson.objects.filter(
        knowledgedocument=doc,
    ).count()
    assert pre_through == 1

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST

    post_through = KnowledgeDocumentSpokesperson.objects.filter(
        knowledgedocument=doc,
    ).count()
    assert post_through == pre_through, (
        "guard must run before .remove(); through-row count unchanged"
    )


# ---- Test D — Universe-scoped CHARACTER final detach also rejects ----


def test_slice13_D_universe_scoped_character_final_detach_rejected() -> None:
    """Slice 13 Test D — Universe context does NOT turn final-character
    detach into UNIVERSE sharing. The guard fires identically."""
    ws, user = _user_with_workspace("s13-d@test", "S13 D")
    u = Universe.objects.create(workspace=ws, name="S13D Universe")
    a = Teammate.objects.create(workspace=ws, name="Alpha", universe=u)
    doc = _make_character_doc(ws, "u-final-detach", [a], universe=u)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert body.get("code") == FINAL_DETACH_CODE

    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.universe_id == u.pk
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]


# ---- Test E — multi-character Universe-scoped narrowing unchanged ----


def test_slice13_E_multi_character_universe_scoped_detach_narrows() -> None:
    """Slice 13 Test E — {A,B} inside Universe U, detach A → {B}
    inside Universe U. Universe stays; audience_scope stays
    CHARACTER."""
    ws, user = _user_with_workspace("s13-e@test", "S13 E")
    u = Universe.objects.create(workspace=ws, name="S13E Universe")
    a = Teammate.objects.create(workspace=ws, name="Alpha", universe=u)
    b = Teammate.objects.create(workspace=ws, name="Beta", universe=u)
    doc = _make_character_doc(ws, "u-multi", [a, b], universe=u)

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content

    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.CHARACTER
    assert doc.universe_id == u.pk
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [b.pk]


# ---- Test F — non-attached spokesperson preserves current no-op ----


def test_slice13_F_detach_of_unattached_spokesperson_is_still_noop() -> None:
    """Slice 13 Test F — an idempotent-detach request for a
    spokesperson who is NOT currently attached must remain a no-op
    (200), NOT trip the final-detach guard. The guard's precondition
    ``spokespeople.filter(pk=sp.pk).exists()`` prevents false positives.
    """
    ws, user = _user_with_workspace("s13-f@test", "S13 F")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    other = Teammate.objects.create(workspace=ws, name="Other")
    # doc has A but caller asks to detach 'other'
    doc = _make_character_doc(ws, "noop-detach", [a])

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(other.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert list(doc.spokespeople.values_list("pk", flat=True)) == [a.pk]


# ---- Test G — shared canon (WORKSPACE / UNIVERSE) unaffected ----


def test_slice13_G_workspace_audience_row_unaffected_by_guard() -> None:
    """Slice 13 Test G — a WORKSPACE-audience row (empty M2M by
    construction) is unaffected by the detach guard. Any detach
    request against it is a no-op (the SP is not attached), matching
    pre-Slice-13 behavior."""
    ws, user = _user_with_workspace("s13-g-ws@test", "S13 G-WS")
    a = Teammate.objects.create(workspace=ws, name="Alpha")
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="workspace-canon",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S13G-WS",
        ingested_via="paste",
        audience_scope=AudienceScope.WORKSPACE,
    )  # M2M intentionally empty

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    # Detach of an unattached SP → 200 no-op. Guard is CHARACTER-only,
    # so it doesn't fire regardless.
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.WORKSPACE
    assert doc.spokespeople.count() == 0


def test_slice13_G_universe_audience_row_unaffected_by_guard() -> None:
    """Slice 13 Test G (paired) — same for UNIVERSE canon."""
    ws, user = _user_with_workspace("s13-g-u@test", "S13 G-U")
    u = Universe.objects.create(workspace=ws, name="S13GU Universe")
    a = Teammate.objects.create(workspace=ws, name="Alpha", universe=u)
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="universe-canon",
        document_type=DocumentType.TEXT,
        processed_content="body", content_hash="HASH-S13G-U",
        ingested_via="paste",
        universe=u,
        audience_scope=AudienceScope.UNIVERSE,
    )  # M2M intentionally empty

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/knowledge/{doc.pk}/detach/",
        {"spokesperson_id": str(a.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    doc.refresh_from_db()
    assert doc.audience_scope == AudienceScope.UNIVERSE
    assert doc.universe_id == u.pk
    assert doc.spokespeople.count() == 0


# ---- Legacy NULL-audience preservation ----


# Slice 13 legacy-NULL detach carve-out test removed by SESSION 276
# Slice 21 — migration 0009 made ``audience_scope IS NULL``
# unrepresentable at the DB layer.
