"""SESSION 263 Slice B — Universe canon retrieval lane.

Focused coverage for ``retrieve_universe_canon``. Deliberately
kept separate from ``test_retrieval_universe.py`` so the 9-row
truth table for ``retrieve_for_teammate`` stays visually locked
and the canon-lane surface has its own test file.

Every test uses ``_query_vector`` (the test hatch on the
retrieval function) so the OpenAI embedding path is bypassed and
tests are hermetic.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.embeddings.retrieval import retrieve_universe_canon
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe

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


# ---- Empty-input guards -----------------------------------------


@pytest.mark.django_db
def test_no_universe_returns_empty():
    """A legacy universe-less call yields no canon regardless of
    corpus state — canon lane is a Universe primitive."""
    ws = _make_workspace("canon-nou@t", "NoU")
    tm = Teammate.objects.create(workspace=ws, name="Legacy")
    _make_doc(ws, "Doc", _vec(1.0))
    got = retrieve_universe_canon(ws, None, [tm], _query_vector=_vec(1.0))
    assert got == []


@pytest.mark.django_db
def test_empty_cast_returns_empty():
    ws = _make_workspace("canon-empty@t", "EmptyCast")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    _make_doc(ws, "Doc", _vec(1.0), universe=u)
    got = retrieve_universe_canon(ws, u, [], _query_vector=_vec(1.0))
    assert got == []


@pytest.mark.django_db
def test_top_k_zero_returns_empty():
    ws = _make_workspace("canon-tk0@t", "TK0")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    tm = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    _make_doc(ws, "Doc", _vec(1.0), universe=u)
    got = retrieve_universe_canon(
        ws, u, [tm], _query_vector=_vec(1.0), top_k=0,
    )
    assert got == []


# ---- Positive cases: M2M-null + M2M-many ------------------------


@pytest.mark.django_db
def test_m2m_null_broadcast_is_canon_for_full_cast():
    """Row 6 case — Universe-scoped, M2M-null (broadcast).
    Visible to every cast member; participates in canon lane."""
    ws = _make_workspace("canon-null@t", "Null")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    doc = _make_doc(ws, "Canon Broadcast", _vec(1.0), universe=u)
    # Sanity — this doc has NO M2M rows.
    assert doc.spokespeople.count() == 0

    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    ids = {str(c.document_id) for c in got}
    assert str(doc.id) in ids


@pytest.mark.django_db
def test_m2m_many_covering_full_cast_is_canon():
    """Row 7 case — Universe-scoped, M2M explicitly covers every
    cast member. Legitimate shared canon."""
    ws = _make_workspace("canon-many@t", "Many")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    doc = _make_doc(
        ws, "Canon Patch+Rivet", _vec(1.0),
        universe=u, spokespeople=[patch, rivet],
    )
    assert doc.spokespeople.count() == 2

    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    ids = {str(c.document_id) for c in got}
    assert str(doc.id) in ids


# ---- Negative cases: character-only docs are NOT canon ----------


@pytest.mark.django_db
def test_m2m_single_teammate_is_not_canon():
    """A doc scoped to exactly one teammate — even a cast member —
    is per-character retrieval, NOT canon."""
    ws = _make_workspace("canon-single@t", "Single")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    doc = _make_doc(
        ws, "Patch Doc", _vec(1.0),
        universe=u, spokespeople=[patch],
    )
    assert doc.spokespeople.count() == 1

    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    ids = {str(c.document_id) for c in got}
    assert str(doc.id) not in ids


@pytest.mark.django_db
def test_m2m_many_missing_one_cast_member_is_not_canon():
    """A doc M2M-scoped to some-but-not-all cast is NOT canon —
    the missing cast member cannot legitimately cite it."""
    ws = _make_workspace("canon-miss@t", "Miss")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    muffin = Teammate.objects.create(workspace=ws, name="Muffin", universe=u)
    # Shared between Patch + Muffin only — Rivet not in M2M.
    doc = _make_doc(
        ws, "Patch+Muffin Doc", _vec(1.0),
        universe=u, spokespeople=[patch, muffin],
    )
    assert doc.spokespeople.count() == 2

    # Cast = [Patch, Rivet]. Rivet not in M2M → NOT canon.
    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    ids = {str(c.document_id) for c in got}
    assert str(doc.id) not in ids


# ---- Universe isolation ----------------------------------------


@pytest.mark.django_db
def test_cross_universe_doc_is_not_canon():
    """A canon doc in Universe Y MUST NOT surface for a cast
    anchored in Universe X."""
    ws = _make_workspace("canon-cross@t", "Cross")
    u_x = Universe.objects.create(workspace=ws, name="Workshop")
    u_y = Universe.objects.create(workspace=ws, name="Bakery")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u_x)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u_x)
    doc_y = _make_doc(
        ws, "Bakery Canon", _vec(1.0),
        universe=u_y, content_hash_seed="y",
    )

    got = retrieve_universe_canon(
        ws, u_x, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    ids = {str(c.document_id) for c in got}
    assert str(doc_y.id) not in ids


@pytest.mark.django_db
def test_legacy_doc_not_visible_from_universe_cast():
    """SESSION 259 audit §6 class — Universe cast MUST NOT retrieve
    legacy (universe=NULL) docs via the canon lane."""
    ws = _make_workspace("canon-legacy@t", "Legacy")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    doc_legacy = _make_doc(ws, "Legacy Doc", _vec(1.0), universe=None)

    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    ids = {str(c.document_id) for c in got}
    assert str(doc_legacy.id) not in ids


@pytest.mark.django_db
def test_cast_spanning_universes_returns_empty():
    """Defense in depth — a cast whose members belong to different
    Universes returns empty. In production, synthesize_dialogue's
    workspace guard rejects this before reaching retrieval; the
    retrieval function itself should also refuse."""
    ws = _make_workspace("canon-span@t", "Span")
    u_x = Universe.objects.create(workspace=ws, name="Workshop")
    u_y = Universe.objects.create(workspace=ws, name="Bakery")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u_x)
    muffin = Teammate.objects.create(workspace=ws, name="Muffin", universe=u_y)
    _make_doc(ws, "Doc", _vec(1.0), universe=u_x)

    got = retrieve_universe_canon(
        ws, u_x, [patch, muffin], _query_vector=_vec(1.0), top_k=5,
    )
    assert got == []


# ---- Cross-workspace isolation ----------------------------------


@pytest.mark.django_db
def test_cross_workspace_doc_never_returned():
    """Tenant wall — a canon doc in Workspace B never surfaces
    to a Universe in Workspace A even at identical vectors."""
    ws_a = _make_workspace("canon-a@t", "A")
    ws_b = _make_workspace("canon-b@t", "B")
    u_a = Universe.objects.create(workspace=ws_a, name="Workshop A")
    u_b = Universe.objects.create(workspace=ws_b, name="Workshop B")
    patch_a = Teammate.objects.create(workspace=ws_a, name="Patch A", universe=u_a)
    rivet_a = Teammate.objects.create(workspace=ws_a, name="Rivet A", universe=u_a)
    _make_doc(ws_b, "Canon B", _vec(1.0), universe=u_b, content_hash_seed="b")

    got = retrieve_universe_canon(
        ws_a, u_a, [patch_a, rivet_a], _query_vector=_vec(1.0), top_k=5,
    )
    assert got == []


# ---- Ranking + bounded budget -----------------------------------


@pytest.mark.django_db
def test_top_k_two_caps_return_at_two_chunks():
    """Default ``top_k=2`` bounds the canon budget per audit."""
    ws = _make_workspace("canon-tk2@t", "TK2")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    # 4 canon docs, each with 1 chunk — ranks purely on distance.
    for i in range(4):
        _make_doc(
            ws, f"Canon {i}", _vec(1.0),
            universe=u, content_hash_seed=str(i),
        )

    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=2,
    )
    assert len(got) == 2


@pytest.mark.django_db
def test_cosine_ordering_closest_first():
    """Within canon, chunks are ordered by cosine distance ASC
    (closest match first) — same ordering contract as
    ``retrieve_for_teammate``."""
    ws = _make_workspace("canon-ord@t", "Ord")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    # Two canon docs with distinct vectors along axis 0.
    doc_close = _make_doc(
        ws, "Close", _vec(1.0),
        universe=u, content_hash_seed="c",
    )
    doc_far = _make_doc(
        ws, "Far", _vec(-1.0),
        universe=u, content_hash_seed="f",
    )

    # Query near doc_close.
    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=2,
    )
    assert len(got) == 2
    assert str(got[0].document_id) == str(doc_close.id)
    assert str(got[1].document_id) == str(doc_far.id)


@pytest.mark.django_db
def test_no_canon_present_returns_empty():
    """A Universe with only character-scoped docs returns empty
    canon (regression: must not accidentally include per-character
    docs)."""
    ws = _make_workspace("canon-none@t", "None")
    u = Universe.objects.create(workspace=ws, name="Workshop")
    patch = Teammate.objects.create(workspace=ws, name="Patch", universe=u)
    rivet = Teammate.objects.create(workspace=ws, name="Rivet", universe=u)
    _make_doc(
        ws, "Patch Only", _vec(1.0),
        universe=u, spokespeople=[patch], content_hash_seed="p",
    )
    _make_doc(
        ws, "Rivet Only", _vec(1.0),
        universe=u, spokespeople=[rivet], content_hash_seed="r",
    )

    got = retrieve_universe_canon(
        ws, u, [patch, rivet], _query_vector=_vec(1.0), top_k=5,
    )
    assert got == []
