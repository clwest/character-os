"""SESSION 276 / Slice 17 / Delta Stage 5B — LIST `?spokesperson=`
cutover regression.

Q-276-31. Directly exercises the Delta predicate at
``shell/apps/embeddings/views.py`` KnowledgeDocumentViewSet.get_queryset
`?spokesperson=` branch — positive-audience list filtering keyed on
``audience_scope`` with a NULL compatibility fallback.

Test taxonomy A-L (parallels Slice 16 test_retrieval_delta_slice16
where semantics overlap; adds LIST-specific coverage for
``?universe=`` composition and the auth wall):

  * A — NULL + M2M empty: legacy broadcast preserved via NULL fallback.
  * B — NULL + M2M={T}: legacy narrow preserved via NULL fallback.
  * C — CHARACTER + T in M2M: visible.
  * D — CHARACTER + T NOT in M2M: not visible (defense against
    accidental exposure).
  * E — UNIVERSE: visible regardless of requesting sp's universe
    (LIST semantics — Universe scoping is via ``?universe=`` param
    below, not auto-derived).
  * F — WORKSPACE: visible.
  * G — NONE (with is_active=True forced): fail closed (defense in
    depth against future is_active bug).
  * H — Unknown ``audience_scope`` value: fail closed. Load-bearing —
    NULL fallback matches EXACTLY ``audience_scope IS NULL``.
  * I — Combined ``?spokesperson=T&?universe=U``: intersection of
    per-teammate predicate and explicit Universe narrowing.
  * J — is_active=False row invisible regardless of audience_scope
    (baseline unchanged).
  * K — Cross-workspace scoping unchanged: caller from workspace A
    querying ``?spokesperson=<sp in B>`` gets an empty set.
  * L — No ``?spokesperson=`` param: filter branch does not fire;
    full workspace list returned unchanged.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    AudienceScope,
    DocumentStatus,
    DocumentType,
    KnowledgeDocument,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe

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


def _mk_ws(email: str, name: str) -> tuple[Workspace, "User"]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _mk_doc(
    ws: Workspace,
    title: str,
    *,
    universe: Universe | None = None,
    spokespeople: list[Teammate] | None = None,
    audience_scope: str | None = None,
    is_active: bool = True,
    content_hash_seed: str = "",
) -> KnowledgeDocument:
    doc = KnowledgeDocument.objects.create(
        workspace=ws,
        universe=universe,
        title=title,
        document_type=DocumentType.TEXT,
        raw_content=title,
        processed_content=title,
        content_hash=f"hash-{title}-{content_hash_seed}",
        ingested_via="paste",
        status=DocumentStatus.PROCESSED,
        audience_scope=audience_scope,
        is_active=is_active,
    )
    if spokespeople:
        doc.spokespeople.set(spokespeople)
    return doc


def _rows(body):
    if isinstance(body, dict) and "results" in body:
        return body["results"]
    return body


def _list(client, workspace_id, spokesperson_id=None, universe=None):
    url = f"/api/knowledge/?workspace={workspace_id}"
    if spokesperson_id is not None:
        url += f"&spokesperson={spokesperson_id}"
    if universe is not None:
        url += f"&universe={universe}"
    return client.get(url)


def _titles(response) -> set:
    return {row["title"] for row in _rows(response.json())}


def _login(client, user):
    client.force_authenticate(user=user)


# ---- A / B — NULL compatibility fallback preserved -------------------


def test_slice17_A_null_fallback_empty_m2m_visible_via_list():
    ws, user = _mk_ws("s17a@t.test", "A")
    tm = Teammate.objects.create(workspace=ws, name="A")
    _mk_doc(ws, "NULL empty", audience_scope=None)
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm.pk)
    assert r.status_code == http.HTTP_200_OK
    assert "NULL empty" in _titles(r)


def test_slice17_B_null_fallback_m2m_narrows_via_list():
    ws, user = _mk_ws("s17b@t.test", "B")
    tm_in = Teammate.objects.create(workspace=ws, name="In")
    tm_out = Teammate.objects.create(workspace=ws, name="Out")
    _mk_doc(ws, "NULL narrow", spokespeople=[tm_in], audience_scope=None)
    client = APIClient(); _login(client, user)
    r_in = _list(client, ws.pk, spokesperson_id=tm_in.pk)
    r_out = _list(client, ws.pk, spokesperson_id=tm_out.pk)
    assert "NULL narrow" in _titles(r_in)
    assert "NULL narrow" not in _titles(r_out)


# ---- C / D — CHARACTER audience --------------------------------------


def test_slice17_C_character_visible_to_m2m_member_via_list():
    ws, user = _mk_ws("s17c@t.test", "C")
    tm = Teammate.objects.create(workspace=ws, name="C")
    _mk_doc(ws, "CHAR doc", spokespeople=[tm], audience_scope=AudienceScope.CHARACTER)
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm.pk)
    assert "CHAR doc" in _titles(r)


def test_slice17_D_character_hidden_from_non_m2m_via_list():
    ws, user = _mk_ws("s17d@t.test", "D")
    tm_a = Teammate.objects.create(workspace=ws, name="A")
    tm_b = Teammate.objects.create(workspace=ws, name="B")
    _mk_doc(ws, "A-only CHAR", spokespeople=[tm_a], audience_scope=AudienceScope.CHARACTER)
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm_b.pk)
    assert "A-only CHAR" not in _titles(r)


# ---- E — UNIVERSE broadcast at LIST layer ---------------------------


def test_slice17_E_universe_broadcast_via_list_regardless_of_sp_universe():
    """LIST does NOT auto-scope by sp.universe (that's retrieval.py's contract).
    UNIVERSE doc is visible via LIST to any teammate; operator narrows
    with explicit ?universe= param below.
    """
    ws, user = _mk_ws("s17e@t.test", "E")
    u = Universe.objects.create(workspace=ws, name="U")
    tm_legacy = Teammate.objects.create(workspace=ws, name="Legacy")
    _mk_doc(ws, "UNI doc", universe=u, audience_scope=AudienceScope.UNIVERSE)
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm_legacy.pk)
    assert "UNI doc" in _titles(r)


# ---- F — WORKSPACE audience -----------------------------------------


def test_slice17_F_workspace_audience_visible_via_list():
    ws, user = _mk_ws("s17f@t.test", "F")
    tm = Teammate.objects.create(workspace=ws, name="F")
    _mk_doc(ws, "WS canon", universe=None, audience_scope=AudienceScope.WORKSPACE)
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm.pk)
    assert "WS canon" in _titles(r)


# ---- G / H — Fail-closed --------------------------------------------


def test_slice17_G_none_audience_fails_closed_via_list_even_if_active():
    """Defense in depth: NONE fails closed at the audience predicate,
    not only via is_active=True. Row is intentionally is_active=True
    to prove the audience branch itself excludes it."""
    ws, user = _mk_ws("s17g@t.test", "G")
    tm = Teammate.objects.create(workspace=ws, name="G")
    _mk_doc(
        ws, "NONE doc",
        spokespeople=[tm],
        audience_scope=AudienceScope.NONE,
        is_active=True,
    )
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm.pk)
    assert "NONE doc" not in _titles(r)


def test_slice17_H_unknown_audience_scope_fails_closed_via_list():
    """Load-bearing: NULL fallback matches EXACTLY audience_scope IS NULL.
    A future unknown value must NOT silently receive legacy broadcast.
    """
    ws, user = _mk_ws("s17h@t.test", "H")
    tm = Teammate.objects.create(workspace=ws, name="H")
    _mk_doc(
        ws, "future scope doc",
        spokespeople=[tm],  # M2M member; unknown scope still fails closed
        audience_scope="future_x",
    )
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm.pk)
    assert "future scope doc" not in _titles(r), (
        "Unknown audience_scope values must fail closed at LIST layer"
    )


# ---- I — Composed with ?universe= ------------------------------------


def test_slice17_I_spokesperson_and_universe_filters_intersect():
    ws, user = _mk_ws("s17i@t.test", "I")
    u1 = Universe.objects.create(workspace=ws, name="U1")
    u2 = Universe.objects.create(workspace=ws, name="U2")
    tm = Teammate.objects.create(workspace=ws, name="I", universe=u1)
    # Two UNIVERSE docs, different universes; both visible via ?sp=T alone.
    _mk_doc(ws, "UNI in U1", universe=u1, audience_scope=AudienceScope.UNIVERSE, content_hash_seed="1")
    _mk_doc(ws, "UNI in U2", universe=u2, audience_scope=AudienceScope.UNIVERSE, content_hash_seed="2")
    client = APIClient(); _login(client, user)
    # ?spokesperson only: both visible
    r_sp_only = _list(client, ws.pk, spokesperson_id=tm.pk)
    both = _titles(r_sp_only)
    assert {"UNI in U1", "UNI in U2"}.issubset(both)
    # ?spokesperson + ?universe=U1: only U1 visible
    r_intersect = _list(client, ws.pk, spokesperson_id=tm.pk, universe=str(u1.pk))
    titles = _titles(r_intersect)
    assert "UNI in U1" in titles
    assert "UNI in U2" not in titles


# ---- J — is_active baseline preserved --------------------------------


def test_slice17_J_inactive_row_invisible_regardless_of_scope():
    ws, user = _mk_ws("s17j@t.test", "J")
    tm = Teammate.objects.create(workspace=ws, name="J")
    _mk_doc(
        ws, "archived CHAR",
        spokespeople=[tm],
        audience_scope=AudienceScope.CHARACTER,
        is_active=False,
    )
    client = APIClient(); _login(client, user)
    r = _list(client, ws.pk, spokesperson_id=tm.pk)
    assert "archived CHAR" not in _titles(r)


# ---- K — Cross-workspace auth scoping preserved ----------------------


def test_slice17_K_cross_workspace_spokesperson_returns_empty():
    ws_a, user_a = _mk_ws("s17k-a@t.test", "A")
    ws_b, _user_b = _mk_ws("s17k-b@t.test", "B")
    tm_b = Teammate.objects.create(workspace=ws_b, name="B-mate")
    _mk_doc(ws_b, "B doc", spokespeople=[tm_b], audience_scope=AudienceScope.CHARACTER)
    client = APIClient(); _login(client, user_a)
    # user_a queries with tm_b's UUID — auth wall + workspace scoping should
    # produce an empty result even though the predicate could theoretically
    # match if the workspace scope were bypassed.
    r = _list(client, ws_a.pk, spokesperson_id=tm_b.pk)
    assert _titles(r) == set()


# ---- L — No ?spokesperson= param ------------------------------------


def test_slice17_L_no_spokesperson_param_returns_full_workspace_list():
    ws, user = _mk_ws("s17l@t.test", "L")
    tm = Teammate.objects.create(workspace=ws, name="L")
    _mk_doc(ws, "unattached", audience_scope=None)
    _mk_doc(ws, "attached CHAR", spokespeople=[tm], audience_scope=AudienceScope.CHARACTER, content_hash_seed="2")
    client = APIClient(); _login(client, user)
    # Without ?spokesperson= the filter branch does not fire; both docs
    # visible via the workspace-scoped base queryset.
    r = _list(client, ws.pk)
    titles = _titles(r)
    assert "unattached" in titles
    assert "attached CHAR" in titles
