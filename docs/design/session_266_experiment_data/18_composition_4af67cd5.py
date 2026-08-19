"""SESSION 266 §16 — Read-only audit of Composition 4af67cd5.

Resolves the full ID, extracts full observability + accepted dialogue,
verifies retrieved NarrativeMemory, reports current active-memory
landscape, and inspects Rivet's K2 chunks so we can distinguish
K2-methodology vs NarrativeMemory-relationship contributions.
"""
import json
from datetime import datetime, timezone

from apps.universe.models import Universe
from apps.compositions.models import Composition, CompositionStep
from apps.embeddings.models import KnowledgeChunk
from apps.memory.models import NarrativeMemory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"

comp = (
    Composition.objects
    .filter(id__istartswith="4af67cd5")
    .select_related("workspace", "spokesperson", "episode",
                    "episode__universe", "final_asset")
    .first()
)
assert comp is not None, "Composition 4af67cd5 not found"
print(f"Resolved: {comp.id}")

steps = list(CompositionStep.objects.filter(composition=comp).order_by("position"))
dispatch_count = sum(
    1 for s in steps
    if s.primitive == "generate_avatar_speech" and s.status == "succeeded"
)
cast_names = (
    list(comp.episode.cast.values_list("name", flat=True).order_by("name"))
    if comp.episode_id else []
)

# Retrieved memories (resolved)
resolved_memories = []
for mid in comp.memory_ids:
    try:
        m = (
            NarrativeMemory.objects.select_related("episode")
            .prefetch_related("witnessed_by").get(pk=mid)
        )
        resolved_memories.append({
            "id": str(m.id),
            "body": m.body,
            "kind": m.kind,
            "source_episode_title": m.episode.title if m.episode_id else None,
            "source_composition_id": (
                str(m.source_composition_id) if m.source_composition_id else None
            ),
            "witnessed_by": [w.name for w in m.witnessed_by.all()],
            "status_now": m.status,
            "archived_at_now": (
                m.archived_at.isoformat() if m.archived_at else None
            ),
        })
    except NarrativeMemory.DoesNotExist:
        resolved_memories.append({"id": mid, "resolved": False})

# Current active NarrativeMemory landscape (universe-wide)
uni = Universe.objects.get(pk=PROD_UNIVERSE_ID)
all_active = list(
    NarrativeMemory.objects.filter(
        universe=uni, status="remembered",
        archived_at__isnull=True, embedding_vector__isnull=False,
    ).prefetch_related("witnessed_by").order_by("created_at")
)
landscape = [
    {
        "id": str(m.id),
        "body": m.body,
        "witnesses": [w.name for w in m.witnessed_by.all()],
        "witness_scope": (
            "whole-cast" if m.witnessed_by.count() == 0
            else "[" + ", ".join(w.name for w in m.witnessed_by.all()) + "]"
        ),
        "source_episode": m.episode.title if m.episode_id else None,
        "source_composition_id": (
            str(m.source_composition_id) if m.source_composition_id else None
        ),
        "created_at": m.created_at.isoformat(),
    }
    for m in all_active
]

# Retrieved chunks (Rivet + shared) — resolve chunk text so we can
# distinguish K2 methodology contributions from NarrativeMemory.
rivet_chunks_resolved = []
if comp.knowledge_chunk_ids:
    id_set = list(comp.knowledge_chunk_ids)
    chunks = list(
        KnowledgeChunk.objects.filter(id__in=id_set)
        .select_related("document").order_by("chunk_index")
    )
    for c in chunks:
        rivet_chunks_resolved.append({
            "id": str(c.id),
            "doc_title": c.document.title,
            "chunk_index": c.chunk_index,
            "text_short": (c.chunk_text[:220] +
                           ("…" if len(c.chunk_text) > 220 else "")),
            "text_len": len(c.chunk_text),
        })

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
    "episode_universe_name": (
        comp.episode.universe.name if comp.episode_id else None
    ),
    "operator_topic": comp.operator_topic,
    "target_duration_seconds": comp.target_duration_seconds,
    "synthesis_predicted_seconds": comp.synthesis_predicted_seconds,
    "synthesis_attempt_count": comp.synthesis_attempt_count,
    "first_pass_synthesis": comp.first_pass_synthesis,
    "corrective_hint": comp.corrective_hint,
    "corrective_pass_synthesis": comp.corrective_pass_synthesis,
    "writing_contract_version": comp.writing_contract_version,
    "synthesized_brief": comp.synthesized_brief,
    "memory_ids": list(comp.memory_ids),
    "resolved_memories": resolved_memories,
    "knowledge_chunk_ids": list(comp.knowledge_chunk_ids),
    "knowledge_chunk_count": len(comp.knowledge_chunk_ids),
    "resolved_chunks": rivet_chunks_resolved,
    "step_count": len(steps),
    "provider_dispatch_count_speech": dispatch_count,
    "cost_actual_micros": comp.cost_actual_micros,
    "cost_estimate_micros": comp.cost_estimate_micros,
    "render_dispatched_at": (
        comp.render_dispatched_at.isoformat()
        if comp.render_dispatched_at else None
    ),
    "created_at": comp.created_at.isoformat(),
    "updated_at": comp.updated_at.isoformat(),
    "final_asset_id": str(comp.final_asset_id) if comp.final_asset_id else None,
    "final_asset_duration_ms": (
        getattr(comp.final_asset, "duration_ms", None)
        if comp.final_asset_id else None
    ),
    "current_active_memory_landscape": landscape,
    "current_active_memory_count": len(landscape),
}

print(f"\n=== Composition {comp.id} ===")
print(f"  status: {comp.status} verification: {comp.verification_status}")
print(f"  episode: {comp.episode.title if comp.episode_id else '<none>'!r}")
print(f"  operator_topic: {comp.operator_topic!r}")
print(f"  cast: {cast_names}")
print(f"  memory_ids: {list(comp.memory_ids)}")
print(f"  target={comp.target_duration_seconds}s "
      f"predicted={comp.synthesis_predicted_seconds}s "
      f"attempts={comp.synthesis_attempt_count}")
print(f"  final asset duration ms: "
      f"{getattr(comp.final_asset, 'duration_ms', None) if comp.final_asset_id else None}")
print(f"  dispatches={dispatch_count} cost=$"
      f"{comp.cost_actual_micros/1_000_000:.4f}")
print(f"  active memory count now: {len(landscape)}")
for m in resolved_memories:
    print(f"\n  Retrieved memory {m.get('id')}:")
    print(f"    body: {m.get('body')!r}")
    print(f"    from Ep: {m.get('source_episode_title')!r}")
    print(f"    witness_scope: {m.get('witnessed_by')}")

with open(
    "../docs/design/session_266_experiment_data/18_composition_4af67cd5.json",
    "w",
) as fh:
    json.dump(payload, fh, indent=2)

print("\n=== ACCEPTED DIALOGUE ===")
print(comp.synthesized_brief)

# Also show Rivet K2 chunks (methodology candidates) so we can
# distinguish K2 vs NarrativeMemory contribution.
print("\n=== RETRIEVED CHUNK TEXTS (first 220 chars each) ===")
for c in rivet_chunks_resolved:
    print(f"  [{c['doc_title']}#{c['chunk_index']}] {c['text_short']}")
