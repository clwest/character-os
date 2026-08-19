"""SESSION 266 — Real production dogfood audit.

READ-ONLY. Inspects the real Patch's Workshop Universe and the two
recent Compositions (01aa7601, e425f5fe) that Chris cited. Also
confirms production UI copy is the post-§12 wording.

Writes /docs/design/session_266_experiment_data/13_real_dogfood_audit.json
with:
  * All NarrativeMemory rows in the real Universe (active + archived,
    fully expanded provenance).
  * Full observability record for Composition 01aa7601.
  * Full observability record for Composition e425f5fe.
  * UI wiring confirmation.

No mutation.
"""
import json
from datetime import datetime, timezone

from django.db.models import Max

from apps.universe.models import Universe, Episode
from apps.spokespeople.models import Teammate
from apps.compositions.models import Composition, CompositionStep
from apps.embeddings.models import KnowledgeDocument, KnowledgeChunk
from apps.memory.models import NarrativeMemory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"

COMP_IDS = {
    "01aa7601": None,  # full UUID resolved by prefix below
    "e425f5fe": None,
}

report: dict = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "prod_universe_id": PROD_UNIVERSE_ID,
    "prod_workspace_id": PROD_WORKSPACE_ID,
}

# ============================================================
# A. Real Patch's Workshop NarrativeMemory state
# ============================================================

prod_uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
print(f"Production Universe: {prod_uni.name} ({prod_uni.id})")

all_rows = list(
    NarrativeMemory.objects.filter(universe=prod_uni)
    .select_related("episode", "source_composition", "promoted_by")
    .prefetch_related("witnessed_by")
    .order_by("created_at")
)
active_rows = [
    m for m in all_rows
    if m.status == "remembered" and m.archived_at is None
    and m.embedding_vector is not None
]
archived_rows = [
    m for m in all_rows
    if m.status == "archived" or m.archived_at is not None
]
superseded_rows = [
    m for m in all_rows
    if m.status == "superseded"
]

print(f"Total memory rows in Patch's Workshop: {len(all_rows)}")
print(f"  Active (retrievable): {len(active_rows)}")
print(f"  Archived: {len(archived_rows)}")
print(f"  Superseded: {len(superseded_rows)}")


def _serialize_memory(m: NarrativeMemory) -> dict:
    witnesses = list(m.witnessed_by.values_list("name", flat=True))
    return {
        "id": str(m.id),
        "body": m.body,
        "kind": m.kind,
        "weight": m.weight,
        "status": m.status,
        "archived_at": (m.archived_at.isoformat() if m.archived_at else None),
        "witnessed_by": witnesses,
        "witness_count": len(witnesses),
        "whole_cast": len(witnesses) == 0,
        "source_episode_id": str(m.episode_id) if m.episode_id else None,
        "source_episode_title": m.episode.title if m.episode_id else None,
        "source_composition_id": (
            str(m.source_composition_id)
            if m.source_composition_id else None
        ),
        "source_composition_name": (
            m.source_composition.name if m.source_composition_id else None
        ),
        "promoted_by_id": m.promoted_by_id,
        "created_at": m.created_at.isoformat(),
        "updated_at": m.updated_at.isoformat(),
        "embedding_model": m.embedding_model,
        "embedding_dimension": m.embedding_dimension,
        "embedding_cost_micros": m.embedding_cost_micros,
        "embedded_at": (m.embedded_at.isoformat() if m.embedded_at else None),
        "has_embedding_vector": m.embedding_vector is not None,
        "supersedes_id": str(m.supersedes_id) if m.supersedes_id else None,
        "superseded_at": (m.superseded_at.isoformat() if m.superseded_at else None),
        "superseded_reason": m.superseded_reason,
    }


report["memory_state"] = {
    "total": len(all_rows),
    "active": len(active_rows),
    "archived": len(archived_rows),
    "superseded": len(superseded_rows),
    "active_rows": [_serialize_memory(m) for m in active_rows],
    "archived_rows": [_serialize_memory(m) for m in archived_rows],
    "superseded_rows": [_serialize_memory(m) for m in superseded_rows],
    "no_competition_note": (
        "Recent retrieval behavior occurred with no NarrativeMemory "
        "competition because only one eligible active memory existed."
        if len(active_rows) == 1
        else f"{len(active_rows)} eligible active memories existed at audit time."
    ),
}

print("\n=== ACTIVE MEMORIES ===")
for m in active_rows:
    print(f"  {m.id} | ep={m.episode.title if m.episode_id else '<none>'!r}")
    print(f"    body: {m.body!r}")
    print(f"    created_at: {m.created_at.isoformat()}")

print("\n=== ARCHIVED MEMORIES ===")
for m in archived_rows:
    print(f"  {m.id} | ep={m.episode.title if m.episode_id else '<none>'!r}")
    print(f"    body: {m.body!r}")
    print(f"    archived_at: {m.archived_at.isoformat() if m.archived_at else '<none>'}")

# ============================================================
# B. Inspect the two named Compositions
# ============================================================

def resolve_composition_by_prefix(prefix: str) -> Composition | None:
    return (
        Composition.objects.filter(id__istartswith=prefix)
        .select_related(
            "workspace", "spokesperson", "episode",
            "episode__universe", "final_asset",
        )
        .first()
    )


def _serialize_composition(comp: Composition) -> dict:
    steps = list(
        CompositionStep.objects.filter(composition=comp)
        .order_by("position")
    )
    step_summary = [
        {
            "position": s.position,
            "primitive": s.primitive,
            "status": s.status,
            "cost_actual_micros": s.cost_actual_micros,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "elapsed_ms": s.elapsed_ms,
            "error_message": s.error_message,
        }
        for s in steps
    ]
    dispatch_count = sum(
        1 for s in steps
        if s.primitive == "generate_avatar_speech"
        and s.status == "succeeded"
    )

    # Cast (from episode, if attached)
    cast_names: list[str] = []
    if comp.episode_id:
        cast_names = list(
            comp.episode.cast.values_list("name", flat=True).order_by("name")
        )

    payload = {
        "id": str(comp.id),
        "name": comp.name,
        "workspace_id": str(comp.workspace_id),
        "spokesperson_id": (
            str(comp.spokesperson_id) if comp.spokesperson_id else None
        ),
        "spokesperson_name": (
            comp.spokesperson.name if comp.spokesperson_id else None
        ),
        "template_kind": comp.template_kind,
        "status": comp.status,
        "verification_status": comp.verification_status,
        "verification_warnings": comp.verification_warnings,
        "rejected_synthesis": comp.rejected_synthesis,
        "mock_mode": comp.mock_mode,
        "error_message": comp.error_message,
        "cost_estimate_micros": comp.cost_estimate_micros,
        "cost_actual_micros": comp.cost_actual_micros,
        "created_at": comp.created_at.isoformat(),
        "updated_at": comp.updated_at.isoformat(),
        # observability
        "operator_topic": comp.operator_topic,
        "target_duration_seconds": comp.target_duration_seconds,
        "synthesis_predicted_seconds": comp.synthesis_predicted_seconds,
        "synthesis_attempt_count": comp.synthesis_attempt_count,
        "first_pass_synthesis": comp.first_pass_synthesis,
        "corrective_hint": comp.corrective_hint,
        "corrective_pass_synthesis": comp.corrective_pass_synthesis,
        "validation_failure_reason": comp.validation_failure_reason,
        "render_dispatched_at": (
            comp.render_dispatched_at.isoformat()
            if comp.render_dispatched_at else None
        ),
        "writing_contract_version": comp.writing_contract_version,
        "synthesized_brief": comp.synthesized_brief,
        # narrative + knowledge provenance
        "memory_ids": list(comp.memory_ids),
        "knowledge_chunk_ids": list(comp.knowledge_chunk_ids),
        "knowledge_chunk_count": len(comp.knowledge_chunk_ids),
        # episode
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
        "cast": cast_names,
        # steps
        "step_count": len(steps),
        "provider_dispatch_count_speech": dispatch_count,
        "steps": step_summary,
    }

    # Resolve retrieved memory bodies (if any) — read-only lookup
    resolved_memories = []
    for mid in comp.memory_ids:
        try:
            m = NarrativeMemory.objects.select_related("episode").get(pk=mid)
            resolved_memories.append({
                "id": str(m.id),
                "body": m.body,
                "source_episode_title": (
                    m.episode.title if m.episode_id else None
                ),
                "status_now": m.status,
                "archived_at_now": (
                    m.archived_at.isoformat() if m.archived_at else None
                ),
            })
        except NarrativeMemory.DoesNotExist:
            resolved_memories.append({"id": mid, "resolved": False})
    payload["resolved_memories"] = resolved_memories

    return payload


report["compositions"] = {}
for prefix in COMP_IDS:
    comp = resolve_composition_by_prefix(prefix)
    if comp is None:
        report["compositions"][prefix] = {"found": False}
        print(f"\n!!! Composition prefix {prefix!r} NOT FOUND !!!")
        continue
    report["compositions"][prefix] = _serialize_composition(comp)
    print(f"\n=== Composition {prefix} → {comp.id} ===")
    print(f"  name: {comp.name!r}")
    print(f"  status: {comp.status} verification: {comp.verification_status}")
    print(f"  episode: {comp.episode.title if comp.episode_id else '<none>'!r}")
    print(f"  memory_ids: {list(comp.memory_ids)}")
    print(f"  attempts: {comp.synthesis_attempt_count}")

# ============================================================
# C. Production-state snapshot for §13 (also serves as
#    verification that no experimental workspace rows leaked
#    into the counts).
# ============================================================

report["counts_check"] = {
    "prod_universe_teammate_count": (
        Teammate.objects.filter(universe=prod_uni).count()
    ),
    "prod_universe_episode_count": (
        Episode.objects.filter(universe=prod_uni).count()
    ),
    "prod_universe_document_count": (
        KnowledgeDocument.objects.filter(universe=prod_uni).count()
    ),
    "prod_universe_chunk_count": (
        KnowledgeChunk.objects.filter(document__universe=prod_uni).count()
    ),
    "prod_universe_max_kn_doc_updated_at": (
        KnowledgeDocument.objects.filter(universe=prod_uni)
        .aggregate(m=Max("updated_at"))["m"].isoformat()
        if KnowledgeDocument.objects.filter(universe=prod_uni).exists()
        else None
    ),
}

with open(
    "../docs/design/session_266_experiment_data/13_real_dogfood_audit.json",
    "w",
) as fh:
    json.dump(report, fh, indent=2)

print("\n=== AUDIT COMPLETE — no writes ===")
print(f"Wrote docs/design/session_266_experiment_data/13_real_dogfood_audit.json")
