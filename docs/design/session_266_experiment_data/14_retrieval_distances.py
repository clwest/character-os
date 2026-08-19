"""SESSION 266 — Reproduce retrieval distances for the two recent
real Compositions in Patch's Workshop.

Reproduces `retrieve_universe_memory(top_k=3)` against each Episode's
operator_topic to reveal the full cosine landscape at retrieval time.
This is READ-ONLY. The `top_k=3` call-time override does not change
the retrieval-lane default; production still uses `top_k=1`.

Caveat: the query embedding is regenerated at audit time, not
recovered from the original synthesis run. OpenAI text-embedding-3-small
is deterministic per text, so the recomputed vector matches what
retrieval computed at synthesis time.
"""
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from apps.compositions.models import Composition
from apps.embeddings.retrieval import retrieve_universe_memory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"

# Full UUIDs resolved during 13_
COMP_IDS = [
    "01aa7601-03d1-4263-98a2-4dd7689c5691",
    "e425f5fe-fab5-4ce9-9c73-0de4eaa55c2f",
]

workspace = Workspace.objects.get(pk=PROD_WORKSPACE_ID)
universe = Universe.objects.get(pk=PROD_UNIVERSE_ID)
cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
print(f"Universe: {universe.name}")
print(f"Cast: {[t.name for t in cast]}")

report: dict = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "universe_id": PROD_UNIVERSE_ID,
    "note": (
        "top_k=3 call-time override to reveal full landscape. "
        "Production default remains top_k=1; no code changed."
    ),
    "compositions": {},
}

for cid in COMP_IDS:
    comp = (
        Composition.objects.select_related("episode")
        .get(pk=cid)
    )
    topic = comp.operator_topic
    print(f"\n=== {cid} ===")
    print(f"  episode: {comp.episode.title!r}")
    print(f"  operator_topic: {topic!r}")
    print(f"  persisted memory_ids: {list(comp.memory_ids)}")

    rows = retrieve_universe_memory(
        workspace=workspace,
        universe=universe,
        cast=cast,
        query=topic,
        top_k=3,
    )
    landscape = []
    for i, r in enumerate(rows, 1):
        landscape.append({
            "rank": i,
            "memory_id": str(r.id),
            "body": r.body,
            "cosine_distance": float(r.distance),
            "source_episode_title": (
                r.episode.title if r.episode_id else None
            ),
            "embedding_model": r.embedding_model,
        })
        print(f"  Rank {i}: distance={r.distance:.6f} mem={r.id}")
        print(f"    body: {r.body!r}")

    persisted_id = comp.memory_ids[0] if comp.memory_ids else None
    matches = (
        landscape[0]["memory_id"] == persisted_id if landscape else False
    )
    report["compositions"][cid] = {
        "episode_title": comp.episode.title,
        "operator_topic": topic,
        "persisted_memory_ids": list(comp.memory_ids),
        "top_k3_landscape": landscape,
        "top1_matches_persisted": matches,
    }
    print(f"  top1 matches persisted memory_ids: {matches}")

with open(
    "../docs/design/session_266_experiment_data/14_retrieval_distances.json",
    "w",
) as fh:
    json.dump(report, fh, indent=2)

print("\n=== DISTANCES CAPTURED — no writes ===")
