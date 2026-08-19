"""SESSION 266 §14 — Verify Chris's Rivet-only memory promotion.

READ-ONLY. Inspects real Patch's Workshop for the new NarrativeMemory
tied to Composition e425f5fe. Reports every field + confirms
witnessed_by = [Rivet].
"""
import json
from datetime import datetime, timezone

from apps.universe.models import Universe
from apps.memory.models import NarrativeMemory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
COMP_ID = "e425f5fe-fab5-4ce9-9c73-0de4eaa55c2f"

uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)

# Total active count first
all_active = list(
    NarrativeMemory.objects.filter(
        universe=uni,
        status="remembered",
        archived_at__isnull=True,
        embedding_vector__isnull=False,
    ).order_by("created_at")
)
print(f"Active memories in Patch's Workshop: {len(all_active)}")

# Find the memory attached to composition e425f5fe
new_mems = list(
    NarrativeMemory.objects.filter(
        universe=uni,
        source_composition_id=COMP_ID,
    ).select_related("episode", "source_composition", "promoted_by")
    .prefetch_related("witnessed_by")
    .order_by("created_at")
)
print(f"Memories sourced from Composition {COMP_ID}: {len(new_mems)}")

report: dict = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "prod_universe_id": PROD_UNIVERSE_ID,
    "source_composition_id": COMP_ID,
    "active_memory_count": len(all_active),
    "memories_from_this_composition": len(new_mems),
    "memories": [],
    "active_memory_ids": [str(m.id) for m in all_active],
}

for m in new_mems:
    witnesses = [
        {"id": str(w.id), "name": w.name}
        for w in m.witnessed_by.all()
    ]
    payload = {
        "id": str(m.id),
        "body": m.body,
        "kind": m.kind,
        "weight": m.weight,
        "status": m.status,
        "archived_at": (m.archived_at.isoformat() if m.archived_at else None),
        "witnessed_by": witnesses,
        "witness_count": len(witnesses),
        "whole_cast_convention": len(witnesses) == 0,
        "workspace_id": str(m.workspace_id),
        "universe_id": str(m.universe_id),
        "source_episode_id": str(m.episode_id),
        "source_episode_title": m.episode.title if m.episode_id else None,
        "source_composition_id": str(m.source_composition_id),
        "source_composition_name": (
            m.source_composition.name if m.source_composition_id else None
        ),
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
        "embedding_model": m.embedding_model,
        "embedding_dimension": m.embedding_dimension,
        "embedding_cost_micros": m.embedding_cost_micros,
        "embedded_at": (m.embedded_at.isoformat() if m.embedded_at else None),
        "has_embedding_vector": m.embedding_vector is not None,
        "promoted_by_id": m.promoted_by_id,
        "supersedes_id": str(m.supersedes_id) if m.supersedes_id else None,
    }
    report["memories"].append(payload)
    print(f"\n=== {m.id} ===")
    print(f"  body: {m.body!r}")
    print(f"  status: {m.status} archived_at: {m.archived_at}")
    print(f"  witnessed_by: {witnesses}")
    print(f"  witness_count: {len(witnesses)} (whole_cast if 0)")
    print(f"  kind: {m.kind}  weight: {m.weight}")
    print(f"  embedding: model={m.embedding_model!r} cost={m.embedding_cost_micros}"
          f" dim={m.embedding_dimension} embedded_at={m.embedded_at}")

with open(
    "../docs/design/session_266_experiment_data/15_verify_rivet_memory.json",
    "w",
) as fh:
    json.dump(report, fh, indent=2)

print("\n=== VERIFICATION COMPLETE ===")
