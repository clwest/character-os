"""SESSION 267 §5.2 — Capture the accepted synthesis from the Rivet-solo
setup Composition.

READ-ONLY. Persists full observability sidecar to
docs/design/session_267_experiment_data/03_setup_composition.json.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from apps.compositions.models import Composition, CompositionStep
from apps.memory.models import NarrativeMemory

COMP_ID = "b0b0e932-4e54-4b1b-b393-3c441aae93b7"

comp = (
    Composition.objects
    .select_related(
        "workspace", "spokesperson", "episode",
        "episode__universe", "final_asset",
    )
    .get(pk=COMP_ID)
)
steps = list(CompositionStep.objects.filter(composition=comp).order_by("position"))

cast_names = list(
    comp.episode.cast.values_list("name", flat=True).order_by("name")
) if comp.episode_id else []
cast_ids = list(
    comp.episode.cast.values_list("id", flat=True)
) if comp.episode_id else []

resolved_memories = []
for mid in (comp.memory_ids or []):
    try:
        m = NarrativeMemory.objects.get(pk=mid)
        resolved_memories.append({
            "id": str(m.id),
            "body": m.body,
            "witnessed_by": [w.name for w in m.witnessed_by.all()],
        })
    except NarrativeMemory.DoesNotExist:
        resolved_memories.append({"id": mid, "resolved": False})

payload = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "id": str(comp.id),
    "name": comp.name,
    "template_kind": comp.template_kind,
    "status": comp.status,
    "verification_status": comp.verification_status,
    "verification_warnings": comp.verification_warnings,
    "rejected_synthesis": comp.rejected_synthesis,
    "mock_mode": comp.mock_mode,
    "workspace_id": str(comp.workspace_id),
    "spokesperson_id": str(comp.spokesperson_id) if comp.spokesperson_id else None,
    "spokesperson_name": comp.spokesperson.name if comp.spokesperson_id else None,
    "episode_id": str(comp.episode_id) if comp.episode_id else None,
    "episode_title": comp.episode.title if comp.episode_id else None,
    "episode_operator_topic": (
        comp.episode.operator_topic if comp.episode_id else None
    ),
    "episode_universe_id": (
        str(comp.episode.universe_id) if comp.episode_id else None
    ),
    "episode_universe_name": (
        comp.episode.universe.name if comp.episode_id else None
    ),
    "cast_names": cast_names,
    "cast_ids": [str(c) for c in cast_ids],
    "patch_in_cast": any(n.lower() == "patch" for n in cast_names),
    "operator_topic": comp.operator_topic,
    "target_duration_seconds": comp.target_duration_seconds,
    "synthesis_predicted_seconds": comp.synthesis_predicted_seconds,
    "synthesis_attempt_count": comp.synthesis_attempt_count,
    "first_pass_synthesis": comp.first_pass_synthesis,
    "corrective_hint": comp.corrective_hint,
    "corrective_pass_synthesis": comp.corrective_pass_synthesis,
    "validation_failure_reason": comp.validation_failure_reason,
    "writing_contract_version": comp.writing_contract_version,
    "synthesized_brief": comp.synthesized_brief,
    "memory_ids": list(comp.memory_ids or []),
    "resolved_memories": resolved_memories,
    "knowledge_chunk_ids": list(comp.knowledge_chunk_ids or []),
    "knowledge_chunk_count": len(comp.knowledge_chunk_ids or []),
    "step_count": len(steps),
    "cost_estimate_micros": comp.cost_estimate_micros,
    "cost_actual_micros": comp.cost_actual_micros,
    "created_at": comp.created_at.isoformat(),
    "updated_at": comp.updated_at.isoformat(),
    "render_dispatched_at": (
        comp.render_dispatched_at.isoformat()
        if comp.render_dispatched_at else None
    ),
    "final_asset_id": str(comp.final_asset_id) if comp.final_asset_id else None,
    "final_asset_duration_ms": (
        getattr(comp.final_asset, "duration_ms", None)
        if comp.final_asset_id else None
    ),
    "steps": [
        {
            "position": s.position,
            "primitive": s.primitive,
            "status": s.status,
            "cost_actual_micros": s.cost_actual_micros,
            "params_keys": sorted((s.params or {}).keys()),
            "output_asset_id": (
                str(s.output_asset_id) if s.output_asset_id else None
            ),
        }
        for s in steps
    ],
}

out = Path(
    "../docs/design/session_267_experiment_data/03_setup_composition.json"
)
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, indent=2))

print(f"Composition {comp.id}")
print(f"  status={comp.status} verification={comp.verification_status!r}")
print(f"  cast={cast_names}  patch_in_cast={payload['patch_in_cast']}")
print(f"  memory_ids retrieved: {list(comp.memory_ids or [])}  (should be [])")
print(f"  synthesis_attempt_count={comp.synthesis_attempt_count} "
      f"predicted={comp.synthesis_predicted_seconds}s")
print(f"  verification_warnings: {len(comp.verification_warnings or [])}")
print(f"  cost_actual_micros={comp.cost_actual_micros}")
print(f"  final_asset_duration_ms={payload['final_asset_duration_ms']}")

print("\n=== ACCEPTED SYNTHESIS (synthesized_brief) ===")
print(comp.synthesized_brief)
print("=== END ===")
print(f"\nWrote {out}")
