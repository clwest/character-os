"""SESSION 276 / Slice 16 / Delta Stage 5A — retrieval cutover regression.

Q-276-30. Directly exercises the Delta predicate at
``shell/apps/embeddings/retrieval.py`` — positive-audience retrieval
keyed on ``audience_scope`` with a NULL compatibility fallback.

Test taxonomy (A-N):
  * A / B — NULL compatibility fallback preserves legacy semantics
    byte-identically for pre-migration rows (M2M empty broadcast
    + M2M explicit narrow).
  * C / D / E — CHARACTER audience keyed on explicit M2M membership.
  * F / G / H — UNIVERSE audience gated by universe filter above.
  * I / J — WORKSPACE audience gated by universe filter (NULL-vs-NULL).
  * K — NONE fails closed.
  * L — Unknown / future ``audience_scope`` value fails closed
        (load-bearing: NULL fallback must match EXACTLY
        ``audience_scope IS NULL``, not "anything other than known").
  * M / N — Cross-scope workspace query returns the correct union
        without cross-contamination.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    AudienceScope,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.embeddings.retrieval import retrieve_for_teammate
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
    audience_scope: str | None = None,
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
        audience_scope=audience_scope,
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


def _visible_ids(results) -> set:
    return {c.document_id for c in results}


# ---- A / B removed by SESSION 276 Slice 21 --------------------------
# Slice 16 tests A/B exercised the temporary NULL compatibility branch
# in `retrieve_for_teammate`. That branch was removed by Slice 21;
# migration 0009 makes `audience_scope IS NULL` unrepresentable at the
# DB layer. Tests C-N below remain — they cover the permanent Delta
# retrieval semantics.


# ---- C / D / E — CHARACTER audience --------------------------------


@pytest.mark.django_db
def test_slice16_C_character_visible_only_to_m2m_member():
    ws = _make_workspace("s16c@u.test", "C")
    tm = Teammate.objects.create(workspace=ws, name="C")
    doc = _make_doc(
        ws, "CHARACTER doc", _vec(1.0),
        spokespeople=[tm], audience_scope=AudienceScope.CHARACTER,
    )
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in _visible_ids(results)


@pytest.mark.django_db
def test_slice16_D_character_visible_to_every_m2m_member():
    ws = _make_workspace("s16d@u.test", "D")
    tm_a = Teammate.objects.create(workspace=ws, name="A")
    tm_b = Teammate.objects.create(workspace=ws, name="B")
    doc = _make_doc(
        ws, "Shared CHARACTER", _vec(1.0),
        spokespeople=[tm_a, tm_b], audience_scope=AudienceScope.CHARACTER,
    )
    r_a = retrieve_for_teammate(tm_a, _query_vector=_vec(1.0), top_k=10)
    r_b = retrieve_for_teammate(tm_b, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in _visible_ids(r_a)
    assert doc.id in _visible_ids(r_b)


@pytest.mark.django_db
def test_slice16_E_character_not_visible_to_non_m2m_teammate():
    """Load-bearing: CHARACTER + M2M={A} must NOT surface to B."""
    ws = _make_workspace("s16e@u.test", "E")
    tm_a = Teammate.objects.create(workspace=ws, name="A")
    tm_b = Teammate.objects.create(workspace=ws, name="B")
    doc = _make_doc(
        ws, "A-only CHARACTER", _vec(1.0),
        spokespeople=[tm_a], audience_scope=AudienceScope.CHARACTER,
    )
    results = retrieve_for_teammate(tm_b, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in _visible_ids(results)


# ---- F / G / H — UNIVERSE audience ---------------------------------


@pytest.mark.django_db
def test_slice16_F_universe_visible_to_every_teammate_in_same_universe():
    ws = _make_workspace("s16f@u.test", "F")
    u = Universe.objects.create(workspace=ws, name="U")
    tm_a = Teammate.objects.create(workspace=ws, name="A", universe=u)
    tm_b = Teammate.objects.create(workspace=ws, name="B", universe=u)
    doc = _make_doc(
        ws, "UNIVERSE canon", _vec(1.0),
        universe=u, audience_scope=AudienceScope.UNIVERSE,
    )
    r_a = retrieve_for_teammate(tm_a, _query_vector=_vec(1.0), top_k=10)
    r_b = retrieve_for_teammate(tm_b, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in _visible_ids(r_a)
    assert doc.id in _visible_ids(r_b)


@pytest.mark.django_db
def test_slice16_G_universe_not_visible_to_legacy_no_universe_teammate():
    """Universe filter above should exclude UNIVERSE docs for a legacy teammate."""
    ws = _make_workspace("s16g@u.test", "G")
    u = Universe.objects.create(workspace=ws, name="U")
    tm_legacy = Teammate.objects.create(workspace=ws, name="Legacy")  # no universe
    doc = _make_doc(
        ws, "UNIVERSE canon", _vec(1.0),
        universe=u, audience_scope=AudienceScope.UNIVERSE,
    )
    results = retrieve_for_teammate(tm_legacy, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in _visible_ids(results)


@pytest.mark.django_db
def test_slice16_H_universe_not_visible_across_different_universes():
    ws = _make_workspace("s16h@u.test", "H")
    u1 = Universe.objects.create(workspace=ws, name="U1")
    u2 = Universe.objects.create(workspace=ws, name="U2")
    tm_u2 = Teammate.objects.create(workspace=ws, name="U2-mate", universe=u2)
    doc = _make_doc(
        ws, "U1 canon", _vec(1.0),
        universe=u1, audience_scope=AudienceScope.UNIVERSE,
    )
    results = retrieve_for_teammate(tm_u2, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in _visible_ids(results)


# ---- I / J — WORKSPACE audience ------------------------------------


@pytest.mark.django_db
def test_slice16_I_workspace_visible_to_legacy_teammate_only():
    ws = _make_workspace("s16i@u.test", "I")
    tm_legacy = Teammate.objects.create(workspace=ws, name="Legacy")
    doc = _make_doc(
        ws, "WS legacy canon", _vec(1.0),
        universe=None, audience_scope=AudienceScope.WORKSPACE,
    )
    results = retrieve_for_teammate(tm_legacy, _query_vector=_vec(1.0), top_k=10)
    assert doc.id in _visible_ids(results)


@pytest.mark.django_db
def test_slice16_J_workspace_not_visible_to_universe_teammate():
    """Delta invariant: WORKSPACE requires universe=NULL; universe teammate excluded by universe filter."""
    ws = _make_workspace("s16j@u.test", "J")
    u = Universe.objects.create(workspace=ws, name="U")
    tm_u = Teammate.objects.create(workspace=ws, name="U-mate", universe=u)
    doc = _make_doc(
        ws, "WS legacy canon", _vec(1.0),
        universe=None, audience_scope=AudienceScope.WORKSPACE,
    )
    results = retrieve_for_teammate(tm_u, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in _visible_ids(results)


# ---- K / L — Fail-closed ------------------------------------------


# Test K removed by SESSION 276 Slice 21 — the NONE + is_active=True
# shape is now unrepresentable at the DB layer via
# `session276_none_requires_inactive`. The audience-branch defense-in-
# depth check is superseded by the CHECK constraint; NONE rows must be
# is_active=False, and the `is_active=True` filter in retrieval
# already excludes them.


@pytest.mark.django_db
def test_slice16_L_unknown_audience_scope_value_fails_closed():
    """Load-bearing: NULL fallback matches EXACTLY audience_scope IS NULL.
    A future unknown value must NOT silently receive legacy broadcast semantics.
    """
    ws = _make_workspace("s16l@u.test", "L")
    tm = Teammate.objects.create(workspace=ws, name="L")
    doc = _make_doc(
        ws, "Future unknown scope", _vec(1.0),
        spokespeople=[tm],  # even with M2M membership, unknown scope fails closed
        audience_scope="future_x",  # fits max_length=20; unknown to Delta predicate
    )
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=10)
    assert doc.id not in _visible_ids(results), (
        "Unknown audience_scope values must fail closed, not silently broadcast"
    )


# ---- M / N — Multi-scope union correctness ------------------------


@pytest.mark.django_db
def test_slice16_M_multi_scope_union_returns_correct_visible_set():
    """A teammate in a Universe should see: their own CHARACTER docs
    + UNIVERSE docs in their universe + their NULL-fallback legacy
    docs (via universe filter). NULL-fallback docs in a different
    universe should NOT appear.
    """
    ws = _make_workspace("s16m@u.test", "M")
    u = Universe.objects.create(workspace=ws, name="U")
    tm = Teammate.objects.create(workspace=ws, name="M-mate", universe=u)
    # Should be visible:
    doc_char = _make_doc(
        ws, "CHAR", _vec(1.0),
        universe=u, spokespeople=[tm], audience_scope=AudienceScope.CHARACTER,
        content_hash_seed="1",
    )
    doc_universe = _make_doc(
        ws, "UNIVERSE", _vec(1.0),
        universe=u, audience_scope=AudienceScope.UNIVERSE,
        content_hash_seed="2",
    )
    # Should NOT be visible (different universe):
    other_u = Universe.objects.create(workspace=ws, name="Other")
    doc_other = _make_doc(
        ws, "Other UNIVERSE", _vec(1.0),
        universe=other_u, audience_scope=AudienceScope.UNIVERSE,
        content_hash_seed="3",
    )
    # Should NOT be visible (WORKSPACE requires universe=NULL; tm has universe):
    doc_ws_canon = _make_doc(
        ws, "WS canon", _vec(1.0),
        universe=None, audience_scope=AudienceScope.WORKSPACE,
        content_hash_seed="4",
    )
    results = retrieve_for_teammate(tm, _query_vector=_vec(1.0), top_k=20)
    visible = _visible_ids(results)
    assert doc_char.id in visible
    assert doc_universe.id in visible
    assert doc_other.id not in visible
    assert doc_ws_canon.id not in visible


@pytest.mark.django_db
def test_slice16_N_provenance_carve_out_unchanged():
    """resolve_chunk_ids_to_docs is provenance resolution and must NOT
    apply the Delta audience predicate. A caller passing chunk IDs it
    already knows about should get them resolved regardless of the
    referenced doc's audience_scope.
    """
    from apps.embeddings.retrieval import resolve_chunk_ids_to_docs

    ws = _make_workspace("s16n@u.test", "N")
    tm_a = Teammate.objects.create(workspace=ws, name="A")
    tm_b = Teammate.objects.create(workspace=ws, name="B")
    # tm_b would not see this via retrieve_for_teammate under Delta,
    # but provenance resolution must still surface it.
    doc = _make_doc(
        ws, "A-only CHARACTER", _vec(1.0),
        spokespeople=[tm_a], audience_scope=AudienceScope.CHARACTER,
    )
    chunk_id = str(doc.chunks.first().id)
    resolved = resolve_chunk_ids_to_docs([chunk_id], workspace=ws)
    assert len(resolved) == 1
    assert resolved[0]["id"] == str(doc.id)
    # Sanity: same doc invisible to tm_b via audience-filtered retrieval.
    assert doc.id not in _visible_ids(
        retrieve_for_teammate(tm_b, _query_vector=_vec(1.0), top_k=10)
    )
