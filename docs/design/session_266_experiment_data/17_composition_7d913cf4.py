"""SESSION 266 §15 — Read-only audit of real Composition 7d913cf4.

Resolves full ID, extracts full observability, checks §14.7 prediction.
"""
import json
from datetime import datetime, timezone

from apps.compositions.models import Composition, CompositionStep
from apps.memory.models import NarrativeMemory

comp = (
    Composition.objects
    .filter(id__istartswith="7d913cf4")
    .select_related("workspace", "spokesperson", "episode",
                    "episode__universe", "final_asset")
    .first()
)
assert comp is not None, "Composition 7d913cf4 not found"
print(f"Resolved: {comp.id}")

steps = list(
    CompositionStep.objects.filter(composition=comp).order_by("position")
)
dispatch_count = sum(
    1 for s in steps
    if s.primitive == "generate_avatar_speech" and s.status == "succeeded"
)

cast_names = list(
    comp.episode.cast.values_list("name", flat=True).order_by("name")
) if comp.episode_id else []

# Resolve retrieved memories
resolved_memories = []
for mid in comp.memory_ids:
    try:
        m = (
            NarrativeMemory.objects.select_related("episode")
            .prefetch_related("witnessed_by")
            .get(pk=mid)
        )
        resolved_memories.append({
            "id": str(m.id),
            "body": m.body,
            "source_episode_title": m.episode.title if m.episode_id else None,
            "witnessed_by": [w.name for w in m.witnessed_by.all()],
            "kind": m.kind,
            "status_now": m.status,
            "archived_at_now": (
                m.archived_at.isoformat() if m.archived_at else None
            ),
        })
    except NarrativeMemory.DoesNotExist:
        resolved_memories.append({"id": mid, "resolved": False})

# Elapsed / actual duration derived from final_asset if present
final_asset_duration_ms = None
if comp.final_asset_id:
    final_asset_duration_ms = getattr(comp.final_asset, "duration_ms", None)

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
    "cast": cast_names,
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
    # per-attempt observability
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
    "memory_ids": list(comp.memory_ids),
    "knowledge_chunk_ids": list(comp.knowledge_chunk_ids),
    "knowledge_chunk_count": len(comp.knowledge_chunk_ids),
    "step_count": len(steps),
    "provider_dispatch_count_speech": dispatch_count,
    "cost_estimate_micros": comp.cost_estimate_micros,
    "cost_actual_micros": comp.cost_actual_micros,
    "render_dispatched_at": (
        comp.render_dispatched_at.isoformat()
        if comp.render_dispatched_at else None
    ),
    "created_at": comp.created_at.isoformat(),
    "updated_at": comp.updated_at.isoformat(),
    "final_asset_id": str(comp.final_asset_id) if comp.final_asset_id else None,
    "final_asset_duration_ms": final_asset_duration_ms,
    "resolved_memories": resolved_memories,
}

# Prediction check per §14.7
PREDICTED_MEMORY_ID = "eda32b58-a9fa-4048-bc03-c65596a631a7"
RIVET_ONLY_ID = "cd73d52f-6bce-443e-afa5-e24cddd53e78"
actual_ids = list(comp.memory_ids)
payload["prediction_check"] = {
    "predicted_memory_id": PREDICTED_MEMORY_ID,
    "actual_memory_ids": actual_ids,
    "prediction_matched": actual_ids == [PREDICTED_MEMORY_ID],
    "rivet_only_memory_id": RIVET_ONLY_ID,
    "rivet_only_retrieved": RIVET_ONLY_ID in actual_ids,
}

print(f"\n=== Composition {comp.id} ===")
print(f"  status: {comp.status} verification: {comp.verification_status}")
print(f"  episode: {comp.episode.title if comp.episode_id else '<none>'!r}")
print(f"  operator_topic: {comp.operator_topic!r}")
print(f"  cast: {cast_names}")
print(f"  memory_ids: {actual_ids}")
print(f"  predicted memory (§14.7): {PREDICTED_MEMORY_ID}")
print(f"  prediction matched: {payload['prediction_check']['prediction_matched']}")
print(f"  rivet-only cd73d52f in results: "
      f"{payload['prediction_check']['rivet_only_retrieved']}")
print(f"  target={comp.target_duration_seconds}s "
      f"predicted={comp.synthesis_predicted_seconds}s")
print(f"  attempts={comp.synthesis_attempt_count} "
      f"corrective_fired={bool(comp.corrective_hint)}")
print(f"  speech dispatches: {dispatch_count} cost: "
      f"${comp.cost_actual_micros/1_000_000:.4f}")
print(f"  final_asset_duration_ms: {final_asset_duration_ms}")

with open(
    "../docs/design/session_266_experiment_data/17_composition_7d913cf4.json",
    "w",
) as fh:
    json.dump(payload, fh, indent=2)

print(f"\n=== ACCEPTED DIALOGUE ===\n{comp.synthesized_brief}")
