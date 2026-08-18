"""SESSION 264 Slice 3 — Composition.memory_ids enrichment
surface for the SPA "Memories used in this render" panel.

Load-bearing invariants:

1. Empty ``Composition.memory_ids`` → empty ``memories_used``.
2. Populated ``memory_ids`` → enriched list preserving order.
3. Enrichment carries body, kind, weight, status, archived_at,
   witnessed_by, episode, universe, source_composition.
4. Archived-since-render rows STILL appear (provenance is
   what fed the render, not what is currently retrievable),
   with ``status=archived`` and ``archived_at`` populated so
   the SPA can render the "archived after this render"
   indicator.
5. Cross-workspace UUIDs in memory_ids never re-hydrate —
   defense-in-depth against a smuggled-ID attack.
6. Missing / deleted memory rows serialize as
   ``{id, resolved: False}`` so the SPA doesn't break layout
   on stale references.
7. The resolver NEVER mutates any NarrativeMemory row (audit
   §8: Remembered != Canon; provenance display is read-only).
8. NEVER touches KnowledgeDocument / KnowledgeChunk.

Zero provider calls; the resolver is pure ORM.
"""
from __future__ import annotations

from unittest.mock import patch as mock_patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Composition
from apps.compositions.serializers import CompositionSerializer
from apps.embeddings.models import EMBEDDING_DIMENSION
from apps.memory.models import (
    NarrativeMemory,
    NarrativeMemoryKind,
    NarrativeMemoryStatus,
    NarrativeMemoryWeight,
)
from apps.memory.services import resolve_memory_ids_to_rows
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe

User = get_user_model()
pytestmark = pytest.mark.django_db


def _mkworkspace(email: str, name: str) -> tuple[User, Workspace]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    if ws is None:
        ws = Workspace.objects.create(name=name, owner=user)
    Membership.objects.get_or_create(
        user=user, workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return user, ws


@pytest.fixture
def scene():
    """Patch/Rivet fixture with one Composition + one active
    memory + one archived memory."""
    owner, ws = _mkworkspace("s3-owner@test", "S3-WS")
    universe = Universe.objects.create(workspace=ws, name="workshop")
    patch = Teammate.objects.create(
        workspace=ws, universe=universe, name="Patch",
        runway_avatar_id="av-p",
        portrait_path="https://fake/p.png",
        business_brief="Patch",
    )
    rivet = Teammate.objects.create(
        workspace=ws, universe=universe, name="Rivet",
        runway_avatar_id="av-r",
        portrait_path="https://fake/r.png",
        business_brief="Rivet",
    )
    episode = Episode.objects.create(
        universe=universe,
        title="AI took over the lab",
        operator_topic="the printer decided to make Patch royalty",
    )
    episode.cast.add(patch)
    episode.cast.add(rivet)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=patch,
        name="source render",
        template_kind="dialogue_scene",
        mock_mode=True,
        operator_topic=episode.operator_topic,
        episode=episode,
    )
    # Active memory (whole-cast witness).
    active = NarrativeMemory.objects.create(
        workspace=ws,
        universe=universe,
        episode=episode,
        source_composition=comp,
        kind=NarrativeMemoryKind.EVENT,
        weight=NarrativeMemoryWeight.CENTRAL,
        body="the agent Patch wired to the workshop thinks it runs the place",
    )
    # Narrowed-witness memory (Patch only).
    narrowed = NarrativeMemory.objects.create(
        workspace=ws,
        universe=universe,
        episode=episode,
        source_composition=comp,
        kind=NarrativeMemoryKind.ACTION,
        weight=NarrativeMemoryWeight.PERIPHERAL,
        body="Patch pulled printer tokens",
    )
    narrowed.witnessed_by.set([patch])
    # Archived control (was in a render's memory_ids, since forgotten).
    archived = NarrativeMemory.objects.create(
        workspace=ws,
        universe=universe,
        episode=episode,
        source_composition=comp,
        kind=NarrativeMemoryKind.DIALOGUE_CALLBACK,
        body="the throne joke",
    )
    archived.status = NarrativeMemoryStatus.ARCHIVED
    archived.archived_at = timezone.now()
    archived.save(update_fields=["status", "archived_at", "updated_at"])

    return {
        "owner": owner,
        "workspace": ws,
        "universe": universe,
        "patch": patch,
        "rivet": rivet,
        "episode": episode,
        "composition": comp,
        "active": active,
        "narrowed": narrowed,
        "archived": archived,
    }


# ============================================================
# 1. Empty memory_ids → empty memories_used
# ============================================================


def test_empty_memory_ids_serializes_as_empty_list(scene):
    scene["composition"].memory_ids = []
    scene["composition"].save(update_fields=["memory_ids", "updated_at"])
    data = CompositionSerializer(scene["composition"]).data
    assert data["memory_ids"] == []
    assert data["memories_used"] == []


# ============================================================
# 2. Populated memory_ids → enriched rows in order
# ============================================================


def test_populated_memory_ids_enriched_in_input_order(scene):
    comp = scene["composition"]
    comp.memory_ids = [str(scene["active"].id), str(scene["narrowed"].id)]
    comp.save(update_fields=["memory_ids", "updated_at"])
    data = CompositionSerializer(comp).data
    assert data["memory_ids"] == [
        str(scene["active"].id),
        str(scene["narrowed"].id),
    ]
    assert len(data["memories_used"]) == 2
    # Order preserved from memory_ids input.
    assert data["memories_used"][0]["id"] == str(scene["active"].id)
    assert data["memories_used"][1]["id"] == str(scene["narrowed"].id)


# ============================================================
# 3. Enrichment shape carries every load-bearing field
# ============================================================


def test_enrichment_carries_body_kind_weight_status_episode_universe_witnesses(scene):
    comp = scene["composition"]
    comp.memory_ids = [str(scene["narrowed"].id)]
    comp.save(update_fields=["memory_ids", "updated_at"])
    row = CompositionSerializer(comp).data["memories_used"][0]
    assert row["resolved"] is True
    assert row["id"] == str(scene["narrowed"].id)
    assert row["kind"] == NarrativeMemoryKind.ACTION
    assert row["weight"] == NarrativeMemoryWeight.PERIPHERAL
    assert row["body"] == "Patch pulled printer tokens"
    assert row["status"] == NarrativeMemoryStatus.REMEMBERED
    assert row["archived_at"] is None
    assert row["episode_id"] == str(scene["episode"].id)
    assert row["episode_title"] == scene["episode"].title
    assert row["universe_id"] == str(scene["universe"].id)
    assert row["universe_name"] == scene["universe"].name
    assert row["source_composition_id"] == str(scene["composition"].id)
    # Narrowed witness surfaces as name+id (matches SPA render shape).
    assert row["witnessed_by"] == [
        {"id": str(scene["patch"].id), "name": scene["patch"].name},
    ]


def test_whole_cast_memory_has_empty_witnessed_by(scene):
    """Empty ``witnessed_by`` is the "whole cast" convention;
    the SPA renders this as "Everyone in the episode."""
    comp = scene["composition"]
    comp.memory_ids = [str(scene["active"].id)]
    comp.save(update_fields=["memory_ids", "updated_at"])
    row = CompositionSerializer(comp).data["memories_used"][0]
    assert row["witnessed_by"] == []


# ============================================================
# 4. Archived-since-render rows still appear as provenance
# ============================================================


def test_archived_memory_still_appears_in_memories_used(scene):
    """Provenance is *what fed the render*, not *what is
    currently retrievable*. A memory archived AFTER the render
    must still surface in ``memories_used``, with its current
    ``status=archived`` and ``archived_at`` populated so the SPA
    can render an "archived after this render" indicator."""
    comp = scene["composition"]
    comp.memory_ids = [str(scene["archived"].id)]
    comp.save(update_fields=["memory_ids", "updated_at"])
    row = CompositionSerializer(comp).data["memories_used"][0]
    assert row["resolved"] is True
    assert row["id"] == str(scene["archived"].id)
    assert row["status"] == NarrativeMemoryStatus.ARCHIVED
    assert row["archived_at"] is not None


# ============================================================
# 5. Cross-workspace UUIDs never re-hydrate
# ============================================================


def test_cross_workspace_memory_id_does_not_hydrate(scene):
    """A ``NarrativeMemory`` id from another workspace, if
    somehow smuggled into ``Composition.memory_ids``, must NOT
    resolve — the workspace filter is the tenant wall."""
    _, other_ws = _mkworkspace("s3-other@test", "OTHER-WS-S3")
    other_universe = Universe.objects.create(
        workspace=other_ws, name="foreign",
    )
    other_teammate = Teammate.objects.create(
        workspace=other_ws, universe=other_universe, name="Foreign",
        runway_avatar_id="av-f",
        portrait_path="https://fake/f.png",
        business_brief="foreign",
    )
    other_episode = Episode.objects.create(
        universe=other_universe,
        title="Foreign story",
        operator_topic="foreign topic",
    )
    other_episode.cast.add(other_teammate)
    other_comp = Composition.objects.create(
        workspace=other_ws,
        spokesperson=other_teammate,
        name="foreign source",
        template_kind="dialogue_scene",
        mock_mode=True,
        operator_topic="foreign",
        episode=other_episode,
    )
    foreign_memory = NarrativeMemory.objects.create(
        workspace=other_ws,
        universe=other_universe,
        episode=other_episode,
        source_composition=other_comp,
        body="foreign memory",
    )
    comp = scene["composition"]
    comp.memory_ids = [str(foreign_memory.id)]
    comp.save(update_fields=["memory_ids", "updated_at"])
    rows = CompositionSerializer(comp).data["memories_used"]
    # Cross-workspace id surfaces as an unresolved stub, not the
    # foreign row's body.
    assert len(rows) == 1
    assert rows[0]["id"] == str(foreign_memory.id)
    assert rows[0]["resolved"] is False
    assert "body" not in rows[0]


# ============================================================
# 6. Missing / never-existed IDs serialize as stubs
# ============================================================


def test_never_existed_memory_id_serializes_as_unresolved_stub(scene):
    comp = scene["composition"]
    fake_id = "00000000-0000-0000-0000-000000000000"
    comp.memory_ids = [fake_id]
    comp.save(update_fields=["memory_ids", "updated_at"])
    rows = CompositionSerializer(comp).data["memories_used"]
    assert len(rows) == 1
    assert rows[0] == {"id": fake_id, "resolved": False}


# ============================================================
# 7 + 8. Read-only — no NarrativeMemory or KnowledgeDocument writes
# ============================================================


def test_serializer_does_not_mutate_narrative_memory(scene):
    """Serializing a Composition with populated memory_ids MUST
    NOT touch any NarrativeMemory row. Guards against a future
    edit that starts stamping a 'last surfaced at' or similar
    denormalized field."""
    comp = scene["composition"]
    comp.memory_ids = [
        str(scene["active"].id),
        str(scene["archived"].id),
    ]
    comp.save(update_fields=["memory_ids", "updated_at"])

    baseline = {
        m.id: (m.status, m.archived_at, m.updated_at, m.body, m.kind, m.weight)
        for m in NarrativeMemory.objects.filter(
            id__in=[scene["active"].id, scene["archived"].id],
        )
    }
    CompositionSerializer(comp).data  # exercise the enrichment
    after = {
        m.id: (m.status, m.archived_at, m.updated_at, m.body, m.kind, m.weight)
        for m in NarrativeMemory.objects.filter(
            id__in=[scene["active"].id, scene["archived"].id],
        )
    }
    assert baseline == after


def test_serializer_does_not_hit_knowledge_document_tables(scene):
    """Slice 3 is a memory-provenance surface. It MUST NOT
    resolve against KnowledgeDocument (which is what
    ``knowledge_docs_used`` does for the canon lane). Guards
    against a future refactor that accidentally routes memory
    lookups through the canon resolver."""
    comp = scene["composition"]
    comp.memory_ids = [str(scene["active"].id)]
    comp.knowledge_chunk_ids = []
    comp.save(update_fields=[
        "memory_ids", "knowledge_chunk_ids", "updated_at",
    ])
    with mock_patch(
        "apps.embeddings.retrieval.resolve_chunk_ids_to_docs",
    ) as canon_resolver:
        CompositionSerializer(comp).data
    canon_resolver.assert_not_called()


# ============================================================
# resolve_memory_ids_to_rows service-level unit tests
# ============================================================


def test_resolver_empty_input_returns_empty_list(scene):
    assert resolve_memory_ids_to_rows([], workspace=scene["workspace"]) == []


def test_resolver_workspace_filter_isolates_tenants(scene):
    """Direct-call unit test: pass a foreign workspace and expect
    unresolved stub for the in-scene memory id."""
    _, other_ws = _mkworkspace("s3-uxx@test", "UXX-WS")
    payload = resolve_memory_ids_to_rows(
        [str(scene["active"].id)],
        workspace=other_ws,
    )
    assert payload == [{"id": str(scene["active"].id), "resolved": False}]
