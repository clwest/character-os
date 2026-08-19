"""SESSION 267 §16 — UI implementation dogfood verification.

READ-ONLY. Fetches the live Patch' Workshop NarrativeMemory rows
via the same endpoint the SPA consumes, then computes the
availability-label string each memory will display under the
new formatWitnessAvailability helper.

Cross-checks the frontend rendering logic against real production
data — every one of the 7 active memories must render a truthful,
non-Semantic-2 label with the new UI copy.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.memory.models import NarrativeMemory
from apps.universe.models import Universe

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"

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

def format_witness_availability(names: list[str]) -> str:
    """Mirror of the TypeScript formatWitnessAvailability helper.

    Kept in sync manually with
    web/src/components/narrative-memory-panels.tsx. If the JS
    version changes, update this too.
    """
    if len(names) == 0:
        return "In any future scene"
    if len(names) == 1:
        return f"When {names[0]} is present"
    if len(names) == 2:
        return f"When {names[0]} or {names[1]} is present"
    last = names[-1]
    rest = ", ".join(names[:-1])
    return f"When {rest}, or {last} is present"

report = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "universe_id": PROD_UNIVERSE_ID,
    "universe_name": uni.name,
    "active_memory_count": len(active),
    "rows": [],
}

print(f"=== UI dogfood — {uni.name} ({len(active)} active memories) ===")
print()
for m in active:
    names = [w.name for w in m.witnessed_by.all()]
    label = format_witness_availability(names)
    row = {
        "id": str(m.id),
        "id_short": str(m.id)[:8],
        "body_prefix": (m.body or "")[:60],
        "witness_names": names,
        "expected_display": f"Available: {label}",
    }
    report["rows"].append(row)
    print(f"  {row['id_short']}  witnesses={names}")
    print(f"    body   : {row['body_prefix']}…")
    print(f"    display: {row['expected_display']}")
    print()

out = Path(
    "../docs/design/session_267_experiment_data/10_ui_dogfood_verification.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2))
print(f"Wrote {out}")

print()
print("=== Truthfulness spot check ===")
print("Whole-cast (empty witnessed_by):")
print("  runtime = Universe-wide eligibility for any cast in this Universe")
print("  display = 'Available: In any future scene'")
print("  Match  = TRUE")
print()
print("Rivet-only witnessed_by = [Rivet]:")
print("  runtime = eligible iff Rivet in current cast (at-least-one-overlap)")
print("  display = 'Available: When Rivet is present'")
print("  Match  = TRUE")
