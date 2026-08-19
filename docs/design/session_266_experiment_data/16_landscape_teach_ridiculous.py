"""SESSION 266 §14 — Read-only retrieval landscape for the next
proposed lean topic.

Topic: "Patch tries to teach Rivet something ridiculous."

Uses production Patch's Workshop Universe + cast [Patch, Rivet].
Reports the full 4-memory landscape and predicts the top_k=1
winner before Chris generates the Episode.

READ-ONLY. Production `top_k=1` default unchanged. `top_k=N`
call-time override is the same technique used in §14_ and §13_.
"""
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from apps.memory.models import NarrativeMemory
from apps.embeddings.retrieval import retrieve_universe_memory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"
TOPIC = "Patch tries to teach Rivet something ridiculous."

workspace = Workspace.objects.get(pk=PROD_WORKSPACE_ID)
universe = Universe.objects.get(pk=PROD_UNIVERSE_ID)
cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
print(f"Universe: {universe.name}")
print(f"Cast: {[(str(t.id), t.name) for t in cast]}")
print(f"Topic: {TOPIC!r}")

# All eligible memories (base predicate)
eligible = list(
    NarrativeMemory.objects.filter(
        universe=universe,
        status="remembered",
        archived_at__isnull=True,
        embedding_vector__isnull=False,
    ).prefetch_related("witnessed_by").order_by("created_at")
)
print(f"Eligible base-predicate memories: {len(eligible)}")

# Retrieval at top_k=4 (>= eligible count) to see full landscape
rows = retrieve_universe_memory(
    workspace=workspace,
    universe=universe,
    cast=cast,
    query=TOPIC,
    top_k=4,
)
print(f"Retrieval returned: {len(rows)}")

landscape = []
for i, r in enumerate(rows, 1):
    witnesses = [w.name for w in r.witnessed_by.all()]
    witness_scope = (
        "whole-cast (empty M2M)" if len(witnesses) == 0
        else f"[{', '.join(witnesses)}]"
    )
    landscape.append({
        "rank": i,
        "memory_id": str(r.id),
        "body_short": r.body[:80] + ("…" if len(r.body) > 80 else ""),
        "body": r.body,
        "cosine_distance": float(r.distance),
        "witness_scope": witness_scope,
        "witnesses": witnesses,
        "source_episode_title": r.episode.title if r.episode_id else None,
        "kind": r.kind,
    })
    print(f"  Rank {i}: distance={r.distance:.6f}")
    print(f"    id: {r.id}  witness_scope: {witness_scope}")
    print(f"    body: {r.body}")
    print(f"    source Ep: {r.episode.title if r.episode_id else '<none>'!r}")

# Verify Rivet-only memory is eligible in this cast
rivet_only_id = "cd73d52f-6bce-443e-afa5-e24cddd53e78"
rivet_only_in_landscape = any(r["memory_id"] == rivet_only_id for r in landscape)
print(f"\nRivet-only memory {rivet_only_id} in landscape: {rivet_only_in_landscape}")

# top_k=1 prediction + margin
prediction = landscape[0] if landscape else None
margin = (
    landscape[1]["cosine_distance"] - landscape[0]["cosine_distance"]
    if len(landscape) >= 2 else None
)

report = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "topic": TOPIC,
    "universe_id": PROD_UNIVERSE_ID,
    "workspace_id": PROD_WORKSPACE_ID,
    "cast": [{"id": str(t.id), "name": t.name} for t in cast],
    "eligible_memory_count": len(eligible),
    "landscape_top_k4": landscape,
    "rivet_only_memory_id": rivet_only_id,
    "rivet_only_in_landscape": rivet_only_in_landscape,
    "prediction_top_k1": {
        "memory_id": prediction["memory_id"] if prediction else None,
        "body_short": prediction["body_short"] if prediction else None,
        "cosine_distance": prediction["cosine_distance"] if prediction else None,
        "witness_scope": prediction["witness_scope"] if prediction else None,
        "source_episode_title": (
            prediction["source_episode_title"] if prediction else None
        ),
        "margin_to_rank_2": margin,
    },
}

with open(
    "../docs/design/session_266_experiment_data/16_landscape_teach_ridiculous.json",
    "w",
) as fh:
    json.dump(report, fh, indent=2)

print(f"\n=== PREDICTION ===")
print(f"top_k=1 will retrieve: {prediction['memory_id']}")
print(f"  body: {prediction['body_short']}")
print(f"  witness_scope: {prediction['witness_scope']}")
print(f"  cosine distance: {prediction['cosine_distance']:.6f}")
print(f"  margin to rank 2: {margin:.6f}" if margin else "  (only one memory)")
