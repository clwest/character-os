"""SESSION 264 Slice 2 — Universe narrative-memory retrieval lane.

Focused coverage for ``retrieve_universe_memory``. Every test uses
``_query_vector`` (the test hatch on the retrieval function) so the
OpenAI embedding path is bypassed and tests are hermetic.

The active/archived control pair the live probe uses:

  * ``f25e53af…`` — REMEMBERED, whole-cast witness. MUST retrieve.
  * ``3d1ba9bc…`` — ARCHIVED (soft-deleted).       MUST NOT retrieve.

Tests here rebuild that control pair from fixtures — the numeric
UUIDs above only exist in the live DB, but the semantic contract
does not depend on them.

Isolation invariants proven here:
  * cross-Workspace impossible
  * cross-Universe impossible
  * status=SUPERSEDED never retrieves
  * archived_at IS NOT NULL never retrieves
  * embedding_vector IS NULL never retrieves
  * witness overlap semantics (whole-cast + narrowed)
  * top_k bounded
  * retrieve_universe_memory returns NarrativeMemory rows, NOT
    KnowledgeChunk rows (isolation from the canon lane).
"""
from __future__ import annotations

from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.embeddings.models import EMBEDDING_DIMENSION, KnowledgeChunk
from apps.embeddings.retrieval import retrieve_universe_memory
from apps.memory.models import (
    NarrativeMemory,
    NarrativeMemoryStatus,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe

User = get_user_model()
pytestmark = pytest.mark.django_db


EMBEDDING_DIM = EMBEDDING_DIMENSION


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIM
    v[0] = seed
    return v


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _cast(ws: Workspace, universe: Universe):
    patch = Teammate.objects.create(
        workspace=ws, universe=universe, name="Patch",
        runway_avatar_id="av-patch",
        portrait_path="https://fake/patch.png",
        business_brief="Workshop inventor.",
    )
    rivet = Teammate.objects.create(
        workspace=ws, universe=universe, name="Rivet",
        runway_avatar_id="av-rivet",
        portrait_path="https://fake/rivet.png",
        business_brief="Counterweight.",
    )
    return patch, rivet


def _episode_with_composition(ws, universe, cast):
    from apps.compositions.models import Composition

    episode = Episode.objects.create(
        universe=universe,
        title="AI took over the lab",
        operator_topic="The printer decided to make Patch royalty.",
    )
    for tm in cast:
        episode.cast.add(tm)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=cast[0],
        name="AI-lab source",
        template_kind="dialogue_scene",
        mock_mode=True,
        operator_topic=episode.operator_topic,
        episode=episode,
    )
    return episode, comp


def _memory(
    ws, universe, episode, comp,
    body: str,
    *,
    status=NarrativeMemoryStatus.REMEMBERED,
    archived: bool = False,
    witnessed_by=None,
    vector: list[float] | None = None,
    embedded: bool = True,
) -> NarrativeMemory:
    m = NarrativeMemory.objects.create(
        episode=episode,
        source_composition=comp,
        workspace=ws,
        universe=universe,
        body=body,
        status=status,
        archived_at=timezone.now() if archived else None,
    )
    if witnessed_by:
        m.witnessed_by.set(witnessed_by)
    if embedded:
        m.embedding_vector = vector if vector is not None else _vec(0.5)
        m.embedding_model = "test-mock"
        m.embedding_dimension = EMBEDDING_DIM
        m.embedded_at = timezone.now()
        m.save(update_fields=[
            "embedding_vector",
            "embedding_model",
            "embedding_dimension",
            "embedded_at",
            "updated_at",
        ])
    return m


# ============================================================
# Empty-input + defensive guards
# ============================================================


def test_no_universe_returns_empty():
    ws = _workspace("nu@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)
    got = retrieve_universe_memory(
        ws, None, [patch], _query_vector=_vec(1.0),
    )
    assert got == []


def test_empty_cast_returns_empty():
    ws = _workspace("ec@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    got = retrieve_universe_memory(
        ws, universe, [], _query_vector=_vec(1.0),
    )
    assert got == []


def test_top_k_zero_returns_empty():
    ws = _workspace("tk0@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, _rivet = _cast(ws, universe)
    got = retrieve_universe_memory(
        ws, universe, [patch], top_k=0, _query_vector=_vec(1.0),
    )
    assert got == []


def test_cast_spanning_universes_returns_empty():
    ws = _workspace("csu@t")
    u1 = Universe.objects.create(workspace=ws, name="workshop")
    u2 = Universe.objects.create(workspace=ws, name="bakery")
    patch = Teammate.objects.create(
        workspace=ws, universe=u1, name="Patch",
        runway_avatar_id="av-p", portrait_path="https://p",
        business_brief="w",
    )
    baker = Teammate.objects.create(
        workspace=ws, universe=u2, name="Baker",
        runway_avatar_id="av-b", portrait_path="https://b",
        business_brief="b",
    )
    got = retrieve_universe_memory(
        ws, u1, [patch, baker], _query_vector=_vec(1.0),
    )
    assert got == []


# ============================================================
# Positive: active whole-cast row is returned
# ============================================================


def test_whole_cast_active_memory_retrieved():
    """Empty ``witnessed_by`` = whole cast. Row must retrieve for
    any subset of the Episode's cast."""
    ws = _workspace("wc@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    active = _memory(
        ws, universe, episode, comp,
        "the agent Patch wired to the workshop thinks it runs the place.",
        vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], _query_vector=_vec(1.0),
    )
    assert [m.id for m in got] == [active.id]


# ============================================================
# Exclusion: archived, superseded, no-vector
# ============================================================


def test_archived_memory_excluded():
    """The Slice 1 control pair: an archived memory MUST NOT
    surface even if semantically closest."""
    ws = _workspace("ax@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    active = _memory(
        ws, universe, episode, comp,
        "active memory",
        vector=_vec(0.1),  # farther from query
    )
    _archived = _memory(
        ws, universe, episode, comp,
        "archived memory",
        vector=_vec(1.0),  # cosine-closer to query
        archived=True,
    )
    # Manually flip status too — the promote endpoint does this
    # via the archive action; here we simulate the final state.
    _archived.status = NarrativeMemoryStatus.ARCHIVED
    _archived.save(update_fields=["status", "updated_at"])
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], _query_vector=_vec(1.0),
    )
    assert [m.id for m in got] == [active.id]
    assert _archived.id not in {m.id for m in got}


def test_superseded_memory_excluded():
    ws = _workspace("sx@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    superseded = _memory(
        ws, universe, episode, comp, "old",
        vector=_vec(1.0),
        status=NarrativeMemoryStatus.SUPERSEDED,
    )
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], _query_vector=_vec(1.0),
    )
    assert got == []


def test_unembedded_memory_excluded():
    ws = _workspace("ne@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    _memory(
        ws, universe, episode, comp, "no vec",
        embedded=False,
    )
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], _query_vector=_vec(1.0),
    )
    assert got == []


# ============================================================
# Cross-tenant / cross-universe isolation
# ============================================================


def test_cross_workspace_excluded():
    ws_a = _workspace("cwa@t")
    ws_b = _workspace("cwb@t")
    u_a = Universe.objects.create(workspace=ws_a, name="a")
    u_b = Universe.objects.create(workspace=ws_b, name="b")
    patch_a, rivet_a = _cast(ws_a, u_a)
    patch_b, rivet_b = _cast(ws_b, u_b)
    ep_b, comp_b = _episode_with_composition(ws_b, u_b, [patch_b, rivet_b])
    _memory(ws_b, u_b, ep_b, comp_b, "b-memory", vector=_vec(1.0))
    # Query as workspace A / universe A / cast A.
    got = retrieve_universe_memory(
        ws_a, u_a, [patch_a, rivet_a], _query_vector=_vec(1.0),
    )
    assert got == []


def test_cross_universe_excluded():
    ws = _workspace("cu@t")
    u1 = Universe.objects.create(workspace=ws, name="workshop")
    u2 = Universe.objects.create(workspace=ws, name="bakery")
    patch1, rivet1 = _cast(ws, u1)
    # Distinct teammate names — Teammate.name is unique per
    # workspace, so a second "Patch" in the same workspace 500s.
    patch2 = Teammate.objects.create(
        workspace=ws, universe=u2, name="Baker",
        runway_avatar_id="av-b", portrait_path="https://b",
        business_brief="bakes",
    )
    rivet2 = Teammate.objects.create(
        workspace=ws, universe=u2, name="Yeasty",
        runway_avatar_id="av-y", portrait_path="https://y",
        business_brief="rises",
    )
    ep2, comp2 = _episode_with_composition(ws, u2, [patch2, rivet2])
    _memory(ws, u2, ep2, comp2, "u2 mem", vector=_vec(1.0))
    got = retrieve_universe_memory(
        ws, u1, [patch1, rivet1], _query_vector=_vec(1.0),
    )
    assert got == []


# ============================================================
# Witness visibility
# ============================================================


def test_narrowed_witness_visible_when_overlap():
    """witnessed_by=[Patch]. Retrieval fired for cast=[Patch, Rivet]
    — overlap on {Patch} is non-empty, so the memory is visible."""
    ws = _workspace("nwo@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    m = _memory(
        ws, universe, episode, comp, "only patch witnessed",
        witnessed_by=[patch],
        vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], _query_vector=_vec(1.0),
    )
    assert [x.id for x in got] == [m.id]


def test_narrowed_witness_excluded_when_no_overlap():
    """witnessed_by=[Patch]. Retrieval fired for cast=[Rivet] only
    — zero overlap → excluded."""
    ws = _workspace("nwn@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    _memory(
        ws, universe, episode, comp, "patch-only memory",
        witnessed_by=[patch],
        vector=_vec(1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [rivet], _query_vector=_vec(1.0),
    )
    assert got == []


# ============================================================
# Bounds + ordering
# ============================================================


def test_top_k_bounded():
    ws = _workspace("tkb@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    for i in range(5):
        _memory(
            ws, universe, episode, comp, f"m{i}",
            vector=_vec(1.0 - i * 0.01),
        )
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], top_k=1, _query_vector=_vec(1.0),
    )
    assert len(got) == 1


def test_cosine_ordering():
    ws = _workspace("co@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    close = _memory(
        ws, universe, episode, comp, "close",
        vector=_vec(1.0),
    )
    _far = _memory(
        ws, universe, episode, comp, "far",
        vector=_vec(-1.0),
    )
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], top_k=1, _query_vector=_vec(1.0),
    )
    assert [m.id for m in got] == [close.id]


# ============================================================
# Isolation from the canon lane
# ============================================================


def test_returns_narrative_memory_not_knowledge_chunk():
    """The type of the returned rows must be ``NarrativeMemory``.
    A regression here would mean canon and memory lanes have
    silently merged."""
    ws = _workspace("nkc@t")
    universe = Universe.objects.create(workspace=ws, name="w")
    patch, rivet = _cast(ws, universe)
    episode, comp = _episode_with_composition(ws, universe, [patch, rivet])
    _memory(ws, universe, episode, comp, "m", vector=_vec(1.0))
    got = retrieve_universe_memory(
        ws, universe, [patch, rivet], _query_vector=_vec(1.0),
    )
    assert len(got) == 1
    assert isinstance(got[0], NarrativeMemory)
    assert not isinstance(got[0], KnowledgeChunk)
