"""SESSION 266 — Snapshot production Patch' Workshop before setup.

Records row counts + max(updated_at) fingerprints for every substrate
the experiment touches, so we can prove non-mutation post-experiment.
Read-only.
"""
import json
from datetime import datetime, timezone
from django.db.models import Max

from apps.universe.models import Universe, Episode
from apps.spokespeople.models import Teammate
from apps.compositions.models import Composition
from apps.embeddings.models import KnowledgeDocument, KnowledgeChunk
from apps.memory.models import NarrativeMemory

# Locate production Patch' Workshop by id (from SESSION 265 §11.1)
PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"

uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)

snap = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "universe_id": str(uni.id),
    "universe_name": uni.name,
    "universe_updated_at": uni.updated_at.isoformat(),
    "universe_archived_at": (
        uni.archived_at.isoformat() if uni.archived_at else None
    ),
    "workspace_id": str(uni.workspace_id),
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
            workspace_id=PROD_WORKSPACE_ID,
        ).filter(episode__universe=uni).count(),
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

# Convert datetimes to ISO strings
for k, v in list(snap["max_updated_at"].items()):
    snap["max_updated_at"][k] = v.isoformat() if v else None

with open(
    "../docs/design/session_266_experiment_data/01_production_snapshot_before.json",
    "w",
) as fh:
    json.dump(snap, fh, indent=2)

print(json.dumps(snap, indent=2))
