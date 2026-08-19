"""SESSION 267 §00 — Orientation snapshot of Patch's Workshop
NarrativeMemory state.

READ-ONLY. Confirms the SESSION 267 handoff's 6-active-memory claim
by re-querying live production DB. Also captures per-memory
witness scope so we can verify:
  * the Rivet-only memory `cd73d52f` is still active with
    witnessed_by=[Rivet];
  * the three whole-cast Agent-thread memories A/B/C are intact;
  * the two relationship memories `a34cc005` and `d98962e2` are
    intact.

No writes. No embedding calls. No provider calls.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.universe.models import Universe
from apps.memory.models import NarrativeMemory

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

report = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "prod_universe_id": PROD_UNIVERSE_ID,
    "prod_universe_name": uni.name,
    "active_memory_count": len(active),
    "memories": [],
}

for m in active:
    witnesses = [
        {"id": str(w.id), "name": w.name} for w in m.witnessed_by.all()
    ]
    report["memories"].append({
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
    })

out_path = Path(
    "../docs/design/session_267_experiment_data/00_orient_memory_state.json"
)
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, indent=2))

print(f"Active memories in {uni.name}: {len(active)}")
for m in report["memories"]:
    scope = "whole-cast" if m["whole_cast_convention"] else \
        "[" + ", ".join(w["name"] for w in m["witnessed_by"]) + "]"
    print(f"  {m['id'][:8]}  {scope:14s}  kind={m['kind']:10s}  "
          f"{m['body'][:70]}")

print(f"\nWrote {out_path}")
