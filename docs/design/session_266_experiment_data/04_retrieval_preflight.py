"""SESSION 266 — Retrieval preflight against the locked test topic.

For each Universe:
  * Confirm the eligible-memory count = 1.
  * Call retrieve_universe_memory(top_k=1) with the locked topic.
  * Capture the cosine distance of the winning row.
  * Confirm the winning row is the intended variant memory.

No writes. No retrieval changes.
"""
import inspect
import json
import os

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from apps.memory.models import NarrativeMemory
from apps.embeddings.retrieval import retrieve_universe_memory

# Sanity re-check
sig = inspect.signature(retrieve_universe_memory)
assert sig.parameters["top_k"].default == 1, (
    f"top_k default drifted: {sig.parameters['top_k'].default!r}"
)
# Also verify no unexpected mock env
assert not os.environ.get("EMBEDDING_FORCE_MOCK", "").strip().lower() in {
    "1", "true", "yes", "on"
}

with open(
    "../docs/design/session_266_experiment_data/02_setup_manifest.json"
) as fh:
    setup = json.load(fh)
with open(
    "../docs/design/session_266_experiment_data/03_memory_manifest.json"
) as fh:
    memory = json.load(fh)

LOCKED_TOPIC = setup["locked_test_topic"]
print(f"Locked topic: {LOCKED_TOPIC!r}")

preflight: dict = {"locked_topic": LOCKED_TOPIC, "sides": {}}

for side in ("WEAK", "STRONG"):
    print(f"\n=== {side} preflight ===")
    workspace = Workspace.objects.get(pk=setup["sides"][side]["workspace_id"])
    universe = Universe.objects.get(pk=setup["sides"][side]["universe_id"])
    cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
    expected_mem_id = memory["sides"][side]["memory_id"]
    print(f"  cast: {[t.name for t in cast]}")

    # Eligible count
    eligible = NarrativeMemory.objects.filter(
        universe=universe,
        status="remembered",
        archived_at__isnull=True,
        embedding_vector__isnull=False,
    )
    print(f"  eligible memories: {eligible.count()}")
    assert eligible.count() == 1, (
        f"expected 1 eligible memory, got {eligible.count()}"
    )

    # Preflight retrieval — default top_k=1 (no override)
    rows = retrieve_universe_memory(
        workspace=workspace,
        universe=universe,
        cast=cast,
        query=LOCKED_TOPIC,
    )
    print(f"  retrieved rows: {len(rows)}")
    assert len(rows) == 1
    row = rows[0]
    distance = float(row.distance)
    print(f"  memory id={row.id} distance={distance:.6f}")
    print(f"    body: {row.body!r}")
    assert str(row.id) == expected_mem_id, (
        f"got {row.id} expected {expected_mem_id}"
    )

    preflight["sides"][side] = {
        "workspace_id": str(workspace.id),
        "universe_id": str(universe.id),
        "cast_names": [t.name for t in cast],
        "eligible_memory_count": eligible.count(),
        "retrieved_memory_id": str(row.id),
        "retrieved_memory_body": row.body,
        "cosine_distance": distance,
        "embedding_model": row.embedding_model,
        "embedding_dimension": row.embedding_dimension,
    }

# Also do a defensive top_k=3 call to see the full ranking landscape
# (there's only 1 memory per Universe, so top_k=3 should still return 1;
# this proves no cross-side contamination via workspace filter).
print("\n=== Cross-side isolation check ===")
for side in ("WEAK", "STRONG"):
    workspace = Workspace.objects.get(pk=setup["sides"][side]["workspace_id"])
    universe = Universe.objects.get(pk=setup["sides"][side]["universe_id"])
    cast = list(Teammate.objects.filter(universe=universe).order_by("name"))
    rows = retrieve_universe_memory(
        workspace=workspace,
        universe=universe,
        cast=cast,
        query=LOCKED_TOPIC,
        top_k=3,  # call-time override; not a code change
    )
    ids = [str(r.id) for r in rows]
    print(f"  {side}: top_k=3 returned {len(rows)} memory ids={ids}")
    assert len(rows) == 1, (
        f"{side}: expected exactly 1 eligible memory across all topk, got {len(rows)}"
    )

with open(
    "../docs/design/session_266_experiment_data/04_preflight.json",
    "w",
) as fh:
    json.dump(preflight, fh, indent=2)

print("\n=== PREFLIGHT COMPLETE ===")
print(json.dumps(preflight, indent=2))
