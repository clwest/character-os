"""SESSION 266 — Re-snapshot production Patch' Workshop after experiment.

Compares against 01_production_snapshot_before.json. Any drift signals
a leak.
"""
import json
from datetime import datetime, timezone
from django.db.models import Max

from apps.universe.models import Universe, Episode
from apps.spokespeople.models import Teammate
from apps.compositions.models import Composition
from apps.embeddings.models import KnowledgeDocument, KnowledgeChunk
from apps.memory.models import NarrativeMemory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"

uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)

snap = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "universe_id": str(uni.id),
    "universe_name": uni.name,
    "universe_updated_at": uni.updated_at.isoformat(),
    "counts": {
        "teammates": Teammate.objects.filter(universe=uni).count(),
        "episodes": Episode.objects.filter(universe=uni).count(),
        "knowledge_documents": KnowledgeDocument.objects.filter(
            universe=uni
        ).count(),
        "knowledge_chunks": KnowledgeChunk.objects.filter(
            document__universe=uni
        ).count(),
        "narrative_memories": NarrativeMemory.objects.filter(
            universe=uni
        ).count(),
        "narrative_memories_active": NarrativeMemory.objects.filter(
            universe=uni, archived_at__isnull=True,
        ).count(),
        "compositions": Composition.objects.filter(
            episode__universe=uni
        ).count(),
    },
    "max_updated_at": {
        "teammates": (
            Teammate.objects.filter(universe=uni)
            .aggregate(m=Max("updated_at"))["m"] or None
        ),
        "episodes": (
            Episode.objects.filter(universe=uni)
            .aggregate(m=Max("updated_at"))["m"] or None
        ),
        "knowledge_documents": (
            KnowledgeDocument.objects.filter(universe=uni)
            .aggregate(m=Max("updated_at"))["m"] or None
        ),
        "knowledge_chunks_created": (
            KnowledgeChunk.objects.filter(document__universe=uni)
            .aggregate(m=Max("created_at"))["m"] or None
        ),
        "narrative_memories": (
            NarrativeMemory.objects.filter(universe=uni)
            .aggregate(m=Max("updated_at"))["m"] or None
        ),
        "compositions": (
            Composition.objects.filter(episode__universe=uni)
            .aggregate(m=Max("updated_at"))["m"] or None
        ),
    },
    "narrative_memory_ids": sorted(
        str(m.id) for m in NarrativeMemory.objects.filter(universe=uni)
    ),
    "knowledge_document_ids": sorted(
        str(d.id) for d in KnowledgeDocument.objects.filter(universe=uni)
    ),
    "teammate_ids": sorted(
        str(t.id) for t in Teammate.objects.filter(universe=uni)
    ),
    "episode_ids": sorted(
        str(e.id) for e in Episode.objects.filter(universe=uni)
    ),
}
for k, v in list(snap["max_updated_at"].items()):
    snap["max_updated_at"][k] = v.isoformat() if v else None

with open(
    "../docs/design/session_266_experiment_data/10_production_snapshot_after.json",
    "w",
) as fh:
    json.dump(snap, fh, indent=2)

# Compare
with open(
    "../docs/design/session_266_experiment_data/01_production_snapshot_before.json"
) as fh:
    before = json.load(fh)

drift = []
for k in ("teammates", "episodes", "knowledge_documents",
          "knowledge_chunks", "narrative_memories",
          "narrative_memories_active", "compositions"):
    if before["counts"][k] != snap["counts"][k]:
        drift.append(f"count.{k}: {before['counts'][k]} → {snap['counts'][k]}")

for k in before["max_updated_at"]:
    if before["max_updated_at"][k] != snap["max_updated_at"][k]:
        drift.append(
            f"max_updated_at.{k}: {before['max_updated_at'][k]} → "
            f"{snap['max_updated_at'][k]}"
        )

for k in ("narrative_memory_ids", "knowledge_document_ids",
          "teammate_ids", "episode_ids"):
    if before[k] != snap[k]:
        drift.append(f"{k}: SET DIFFERS")

if drift:
    print("!!! DRIFT DETECTED !!!")
    for d in drift:
        print(f"  {d}")
else:
    print("=== PRODUCTION UNTOUCHED ===")
    print("All counts, timestamps, and ID sets match pre-experiment snapshot.")

# Write comparison file
compare = {
    "before_timestamp": before["timestamp"],
    "after_timestamp": snap["timestamp"],
    "drift_items": drift,
    "clean": len(drift) == 0,
    "before_counts": before["counts"],
    "after_counts": snap["counts"],
    "before_max_updated_at": before["max_updated_at"],
    "after_max_updated_at": snap["max_updated_at"],
}
with open(
    "../docs/design/session_266_experiment_data/10_production_integrity_comparison.json",
    "w",
) as fh:
    json.dump(compare, fh, indent=2)
