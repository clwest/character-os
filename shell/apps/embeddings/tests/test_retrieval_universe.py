"""Universe-aware retrieval — 9-row truth table.

SESSION 261 / Phase 3. Exercises every row of the retrieval truth
table in ``docs/design/UNIVERSE_SCHEMA_V1.md §"Retrieval truth table"``.

Load-bearing rows:
  * Row 5 (T=Universe, D=legacy) → NOT VISIBLE. Closes the
    SESSION 259 audit §6 leak class.
  * Row 9 (T=U_X, D=U_Y, X != Y) → NOT VISIBLE regardless of cosine
    distance. Two-Universe isolation.

Plus: legacy semantics for the pure-legacy workspace (rows 1-3)
MUST match today's ``test_retrieval_privacy.py`` behavior verbatim.
"""
from __future__ import annotations

import pytest

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.embeddings.retrieval import retrieve_for_teammate
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()

EMBEDDING_DIM = 1536


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIM
    v[0] = seed
    return v


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    if ws is None:
        ws = Workspace.objects.create(name=name, owner=user)
    ws.name = name
    ws.save()
    return ws


def _make_doc(
    ws: Workspace,
    title: str,
    vector: list[float],
    *,
    universe: Universe | None = None,
    spokespeople: list[Teammate] | None = None,
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
        ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    if spokespeople:
        doc.spokespeople.set(spokespeople)
    KnowledgeChunk.objects.create(
        document=doc,
        chunk_index=0,
        chunk_text=title,
        chunk_size=len(title),
        embedding_vector=vector,
    )
    return doc


# ---- Truth table rows 1-9 ----------------------------------------------


@pytest.mark.django_db
def test_row1_legacy_teammate_legacy_doc_empty_m2m_visible():
    ws = _make_workspace("row1@u.test", "Row1 WS")
    tm = Teammate.objects.create(workspace=ws, name="Legacy")
    doc = _make_doc(ws, "Legacy Doc", _vec(1.0))
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in {c.document_id for c in results}


@pytest.mark.django_db
def test_row2_legacy_teammate_legacy_doc_m2m_contains_visible():
    ws = _make_workspace("row2@u.test", "Row2 WS")
    tm = Teammate.objects.create(workspace=ws, name="Legacy")
    doc = _make_doc(ws, "Legacy Doc", _vec(1.0), spokespeople=[tm])
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in {c.document_id for c in results}


@pytest.mark.django_db
def test_row3_legacy_teammate_legacy_doc_m2m_excludes_not_visible():
    ws = _make_workspace("row3@u.test", "Row3 WS")
    tm_query = Teammate.objects.create(workspace=ws, name="Legacy Query")
    tm_owner = Teammate.objects.create(workspace=ws, name="Legacy Owner")
    doc = _make_doc(ws, "Locked Doc", _vec(1.0), spokespeople=[tm_owner])
    results = retrieve_for_teammate(tm_query, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in {c.document_id for c in results}


@pytest.mark.django_db
def test_row4_legacy_teammate_universe_doc_not_visible():
    ws = _make_workspace("row4@u.test", "Row4 WS")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    tm = Teammate.objects.create(workspace=ws, name="Legacy")
    doc = _make_doc(ws, "Universe Doc", _vec(1.0), universe=u)
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in {c.document_id for c in results}


@pytest.mark.django_db
def test_row5_universe_teammate_legacy_doc_not_visible_LOAD_BEARING():
    """Row 5 — SESSION 259 audit §6 leak class. A Universe-scoped
    teammate MUST NOT retrieve from a legacy workspace-wide doc,
    even when cosine distance is a perfect match.
    """
    ws = _make_workspace("row5@u.test", "Row5 WS")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    tm = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    doc = _make_doc(ws, "Legacy Doc", _vec(1.0))
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in {c.document_id for c in results}


@pytest.mark.django_db
def test_row6_universe_teammate_same_universe_doc_empty_m2m_visible():
    ws = _make_workspace("row6@u.test", "Row6 WS")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    tm = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    doc = _make_doc(ws, "Workshop Doc", _vec(1.0), universe=u)
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in {c.document_id for c in results}


@pytest.mark.django_db
def test_row7_universe_teammate_same_universe_doc_m2m_contains_visible():
    ws = _make_workspace("row7@u.test", "Row7 WS")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    tm = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    doc = _make_doc(ws, "Workshop Doc", _vec(1.0), universe=u, spokespeople=[tm])
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in {c.document_id for c in results}


@pytest.mark.django_db
def test_row8_universe_teammate_same_universe_doc_m2m_excludes_not_visible():
    ws = _make_workspace("row8@u.test", "Row8 WS")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    tm_query = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    tm_owner = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    doc = _make_doc(
        ws, "Locked Doc", _vec(1.0), universe=u, spokespeople=[tm_owner]
    )
    results = retrieve_for_teammate(tm_query, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in {c.document_id for c in results}


@pytest.mark.django_db
def test_row9_universe_teammate_other_universe_doc_not_visible_LOAD_BEARING():
    """Row 9 — two-Universe cosine isolation. A doc in Universe
    Y MUST NOT surface to a teammate in Universe X even when the
    cosine distance is a perfect match.
    """
    ws = _make_workspace("row9@u.test", "Row9 WS")
    u_x = Universe.objects.create(workspace=ws, name="Workshop")
    u_y = Universe.objects.create(workspace=ws, name="Bakery")
    tm = Teammate.objects.create(workspace=ws, name="Patch", universe=u_x)
    doc_x = _make_doc(ws, "Workshop Doc", _vec(1.0), universe=u_x, content_hash_seed="x")
    doc_y = _make_doc(ws, "Bakery Doc", _vec(1.0), universe=u_y, content_hash_seed="y")
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    ids = {c.document_id for c in results}
    assert doc_x.id in ids
    assert doc_y.id not in ids


# ---- Two-Universe cosine isolation (SPA E2E Test B analogue) ---


@pytest.mark.django_db
def test_two_universe_cosine_isolation_intentional_similar_content():
    """Same workspace, two Universes, near-identical embedding
    content in each. Each Universe's teammate retrieves ONLY
    their Universe's chunks — cosine distance is irrelevant to
    the Universe boundary.
    """
    ws = _make_workspace("two-u@u.test", "Two-U WS")
    workshop = Universe.objects.create(workspace=ws, name="Workshop")
    bakery = Universe.objects.create(workspace=ws, name="Bakery")

    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=workshop)
    muffin = Teammate.objects.create(workspace=ws, name="Muffin", universe=bakery)

    # Intentionally near-identical content — same seed vector.
    doc_workshop = _make_doc(
        ws, "About the Workshop", _vec(1.0),
        universe=workshop, content_hash_seed="ws",
    )
    doc_bakery = _make_doc(
        ws, "About the Bakery-styled Workshop", _vec(1.0),
        universe=bakery, content_hash_seed="bak",
    )

    patch_results = retrieve_for_teammate(patch, _query_vector=_vec(1.0), top_k=10)
    patch_ids = {c.document_id for c in patch_results}
    assert doc_workshop.id in patch_ids
    assert doc_bakery.id not in patch_ids

    muffin_results = retrieve_for_teammate(muffin, _query_vector=_vec(1.0), top_k=10)
    muffin_ids = {c.document_id for c in muffin_results}
    assert doc_bakery.id in muffin_ids
    assert doc_workshop.id not in muffin_ids
