"""SESSION 266 §9.8 — Verify experimental setup still valid.

Read-only. Confirms both experimental Universes + memories still meet
the base predicate for retrieval and that production is untouched.
"""
import inspect
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from apps.memory.models import NarrativeMemory
from apps.embeddings.retrieval import retrieve_universe_memory
from character_os import dialogue_synthesis as ds

# 1. Re-verify preconditions
import os
assert not os.environ.get("EMBEDDING_FORCE_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}
assert not os.environ.get("DIALOGUE_SYNTHESIS_FORCE_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}
assert os.environ.get("OPENAI_API_KEY", "")
sig = inspect.signature(retrieve_universe_memory)
assert sig.parameters["top_k"].default == 1, (
    f"top_k drifted: {sig.parameters['top_k'].default!r}"
)
assert ds.DIALOGUE_MODEL == "gpt-5.6-terra", f"model drifted: {ds.DIALOGUE_MODEL}"
assert ds.WRITING_CONTRACT_VERSION == 4, f"contract drifted: {ds.WRITING_CONTRACT_VERSION}"

with open("../docs/design/session_266_experiment_data/02_setup_manifest.json") as fh:
    setup = json.load(fh)
with open("../docs/design/session_266_experiment_data/03_memory_manifest.json") as fh:
    mem_manifest = json.load(fh)

check: dict = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "sides": {},
    "production_untouched": None,
}

LOCKED_TOPIC = setup["locked_test_topic"]

for side in ("WEAK", "STRONG"):
    side_info = setup["sides"][side]
    ws = Workspace.objects.get(pk=side_info["workspace_id"])
    uni = Universe.objects.get(pk=side_info["universe_id"])
    cast = list(Teammate.objects.filter(universe=uni).order_by("name"))
    eligible = NarrativeMemory.objects.filter(
        universe=uni, status="remembered", archived_at__isnull=True,
        embedding_vector__isnull=False,
    )
    assert eligible.count() == 1
    rows = retrieve_universe_memory(workspace=ws, universe=uni, cast=cast, query=LOCKED_TOPIC)
    assert len(rows) == 1
    assert str(rows[0].id) == mem_manifest["sides"][side]["memory_id"]

    check["sides"][side] = {
        "workspace_id": str(ws.id),
        "universe_id": str(uni.id),
        "eligible_memory_count": eligible.count(),
        "retrieved_memory_id": str(rows[0].id),
        "cosine_distance": float(rows[0].distance),
        "memory_body": rows[0].body,
    }
    print(f"  {side}: distance={rows[0].distance:.4f} body={rows[0].body[:60]!r}...")

# Production untouched check
PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
prod_uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
with open("../docs/design/session_266_experiment_data/01_production_snapshot_before.json") as fh:
    before = json.load(fh)
prod_state = {
    "universe_updated_at": prod_uni.updated_at.isoformat(),
    "memory_count": NarrativeMemory.objects.filter(universe=prod_uni).count(),
}
untouched = (
    prod_state["universe_updated_at"] == before["universe_updated_at"]
    and prod_state["memory_count"] == before["counts"]["narrative_memories"]
)
check["production_untouched"] = untouched
check["production_state"] = prod_state
print(f"  Production untouched: {untouched}")

# Baseline re-verify: for each of the 6 baseline attempts, print first-line
# so we can independently confirm the first-pass classifications.
import glob
baseline_first_lines = {}
for p in sorted(glob.glob("../docs/design/session_266_experiment_data/05_attempt_*.json")):
    with open(p) as fh:
        d = json.load(fh)
    # First-pass first two turns (Patch line 0 + Rivet line 1)
    fp = d.get("first_pass_raw", "")
    if not fp:
        continue
    fp_obj = json.loads(fp)
    turns = fp_obj["turns"]
    baseline_first_lines[f"{d['variant']}-{d['attempt_no']}"] = {
        "attempt_count": d["attempt_count"],
        "patch_line_0": turns[0]["text"] if len(turns) > 0 else "",
        "rivet_line_1": turns[1]["text"] if len(turns) > 1 else "",
    }
check["baseline_first_lines"] = baseline_first_lines
print(f"\nBaseline first-line snapshot ({len(baseline_first_lines)} attempts):")
for k, v in baseline_first_lines.items():
    print(f"  {k}: patch=<{v['patch_line_0'][:80]}...> rivet=<{v['rivet_line_1'][:80]}...>")

with open("../docs/design/session_266_experiment_data/11_preflight_reuse.json", "w") as fh:
    json.dump(check, fh, indent=2)

print("\n=== PREFLIGHT PASS ===")
