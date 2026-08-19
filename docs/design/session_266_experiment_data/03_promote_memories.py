"""SESSION 266 — Promote W and S memories via the sanctioned service.

Uses apps.memory.views.promote_from_composition — the same code path
POST /api/compositions/<id>/promote-narrative-memory/ invokes.
"""
import json

from apps.universe.models import Universe, Episode
from apps.compositions.models import Composition
from apps.memory.models import NarrativeMemory
from apps.memory.views import promote_from_composition

with open(
    "../docs/design/session_266_experiment_data/02_setup_manifest.json"
) as fh:
    manifest = json.load(fh)

VARIANT_BODIES = {
    "WEAK": (
        "The workshop agent moved the printer job ahead of three of "
        "Patch's projects."
    ),
    "STRONG": (
        "The workshop agent began rearranging the order of Patch's "
        "projects without explaining its criteria."
    ),
}

memory_manifest: dict = {"sides": {}}

for side in ("WEAK", "STRONG"):
    print(f"\n=== Promoting {side} memory ===")
    side_info = manifest["sides"][side]
    universe = Universe.objects.get(pk=side_info["universe_id"])
    src_ep = Episode.objects.get(pk=side_info["source_episode_id"])
    src_comp = Composition.objects.get(pk=side_info["source_composition_id"])

    body = VARIANT_BODIES[side]

    # Delete any preexisting experimental memories on this side to keep
    # the invariant "exactly 1 eligible memory per Universe" clean.
    existing = list(NarrativeMemory.objects.filter(universe=universe))
    if existing:
        print(f"  Removing {len(existing)} preexisting memory rows first")
        NarrativeMemory.objects.filter(universe=universe).delete()

    created = promote_from_composition(
        composition=src_comp,
        episode=src_ep,
        memory_items=[{
            "body": body,
            "kind": "event",  # default per NarrativeMemoryKind
            "weight": "peripheral",  # default per NarrativeMemoryWeight
        }],  # whole-cast default (empty witnessed_by)
        promoted_by=None,  # experimental — no user attribution
    )
    assert len(created) == 1, f"expected 1 memory, got {len(created)}"
    m = created[0]

    # Re-fetch to see embed persistence
    m.refresh_from_db()

    print(f"  Memory id={m.id}")
    print(f"    body={m.body!r}")
    print(f"    status={m.status} archived_at={m.archived_at}")
    print(f"    workspace={m.workspace_id} universe={m.universe_id}")
    print(f"    embedding_model={m.embedding_model!r} "
          f"cost={m.embedding_cost_micros} dim={m.embedding_dimension}")
    print(f"    embedded_at={m.embedded_at}")
    print(f"    kind={m.kind} weight={m.weight}")
    witnesses = list(m.witnessed_by.values_list("name", flat=True))
    print(f"    witnessed_by={witnesses} (empty=whole cast)")

    # Assertions — no silent divergence from spec
    assert m.status == "remembered", f"status={m.status}"
    assert m.archived_at is None
    assert m.embedding_model == "text-embedding-3-small", (
        f"embedding_model={m.embedding_model!r} — mock path suspected"
    )
    assert m.embedding_cost_micros >= 1, (
        f"cost={m.embedding_cost_micros} — mock path suspected"
    )
    assert m.embedding_dimension == 1536
    assert m.embedding_vector is not None
    assert m.body == body

    # Confirm exactly 1 eligible memory in this Universe
    eligible = NarrativeMemory.objects.filter(
        universe=universe,
        status="remembered",
        archived_at__isnull=True,
        embedding_vector__isnull=False,
    ).count()
    print(f"    eligible memory count in universe: {eligible}")
    assert eligible == 1

    memory_manifest["sides"][side] = {
        "memory_id": str(m.id),
        "memory_body": m.body,
        "kind": m.kind,
        "weight": m.weight,
        "witnessed_by": witnesses,
        "embedding_model": m.embedding_model,
        "embedding_cost_micros": m.embedding_cost_micros,
        "embedding_dimension": m.embedding_dimension,
        "embedded_at": (
            m.embedded_at.isoformat() if m.embedded_at else None
        ),
        "created_at": m.created_at.isoformat(),
        "source_composition_id": str(m.source_composition_id),
        "source_episode_id": str(m.episode_id),
        "workspace_id": str(m.workspace_id),
        "universe_id": str(m.universe_id),
    }

with open(
    "../docs/design/session_266_experiment_data/03_memory_manifest.json",
    "w",
) as fh:
    json.dump(memory_manifest, fh, indent=2)

print("\n=== PROMOTION COMPLETE ===")
print(json.dumps(memory_manifest, indent=2))
