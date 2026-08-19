"""SESSION 267 §13 — Verify the six pre-existing NarrativeMemories in
Patch' Workshop were not mutated by the promotion of the private
memory c86d4902 (or by anything else in this session).

READ-ONLY. Compares live DB state against the §00 orient snapshot
byte-for-byte on every field the orient snapshot captured.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.memory.models import NarrativeMemory
from apps.universe.models import Universe

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PRIVATE_MEM_ID = "c86d4902-b11d-49a6-bb48-dea2a67afabc"

# Load the §00 baseline snapshot.
baseline_path = Path(
    "../docs/design/session_267_experiment_data/00_orient_memory_state.json"
)
baseline = json.loads(baseline_path.read_text())
baseline_by_id = {m["id"]: m for m in baseline["memories"]}

uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)

active = list(
    NarrativeMemory.objects.filter(
        universe=uni,
        status="remembered",
        archived_at__isnull=True,
        embedding_vector__isnull=False,
    )
    .prefetch_related("witnessed_by")
    .order_by("created_at")
)

# Comparable projection (matches the §00 shape).
def project(m: NarrativeMemory) -> dict:
    witnesses = [
        {"id": str(w.id), "name": w.name} for w in m.witnessed_by.all()
    ]
    return {
        "id": str(m.id),
        "body": m.body,
        "kind": m.kind,
        "weight": m.weight,
        "witness_count": len(witnesses),
        "whole_cast_convention": len(witnesses) == 0,
        "witnessed_by": witnesses,
        "created_at": m.created_at.isoformat(),
        "source_composition_id": (
            str(m.source_composition_id) if m.source_composition_id else None
        ),
    }

live_by_id = {str(m.id): project(m) for m in active}

# The private memory is expected to be NEW. Others must match baseline
# EXACTLY.
prior_ids = set(baseline_by_id.keys())
live_prior_ids = set(live_by_id.keys()) - {PRIVATE_MEM_ID}

report = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "baseline_snapshot": str(baseline_path.name),
    "baseline_count": len(baseline_by_id),
    "live_active_count": len(live_by_id),
    "expected_count_delta": 1,   # +1 for the new private memory
    "actual_count_delta": len(live_by_id) - len(baseline_by_id),
    "private_memory_present": PRIVATE_MEM_ID in live_by_id,
    "missing_from_live": sorted(prior_ids - live_prior_ids),
    "unexpected_new": sorted((live_prior_ids | {PRIVATE_MEM_ID}) - (prior_ids | {PRIVATE_MEM_ID})),
    "per_row_diffs": {},
}

for mid in sorted(prior_ids):
    if mid not in live_by_id:
        report["per_row_diffs"][mid] = {"error": "missing from live"}
        continue
    base = baseline_by_id[mid]
    live = live_by_id[mid]
    diffs = {}
    for k in base:
        if base[k] != live.get(k):
            diffs[k] = {"before": base[k], "after": live.get(k)}
    if diffs:
        report["per_row_diffs"][mid] = diffs

# Assert: no prior memory changed on any tracked field.
all_unchanged = all(
    not report["per_row_diffs"].get(mid) for mid in prior_ids
)
report["assertion_all_prior_unchanged"] = all_unchanged

out = Path(
    "../docs/design/session_267_experiment_data/05_prior_memories_diff.json"
)
out.write_text(json.dumps(report, indent=2))

print(f"baseline count : {report['baseline_count']}")
print(f"live active    : {report['live_active_count']}  "
      f"(delta {report['actual_count_delta']:+d} — expected +1)")
print(f"private memory : {'PRESENT' if report['private_memory_present'] else 'MISSING'}")
print(f"missing        : {report['missing_from_live'] or 'none'}")
print(f"unexpected new : {report['unexpected_new'] or 'none'}")
print(f"all prior unchanged: {report['assertion_all_prior_unchanged']}")
if not report["assertion_all_prior_unchanged"]:
    print("PER-ROW DIFFS:")
    for k, v in report["per_row_diffs"].items():
        print(f"  {k}: {v}")
print(f"\nWrote {out}")
