"""SESSION 266 §17 — Read-only audit of two real Compositions:
  * eb48611f  ("An unrelated workshop disaster happens.")
  * e6b3f132  ("The Agent does something again.")

Extracts full observability for each, resolves memories, and
reproduces the retrieval landscape (top_k=N override; production
default remains top_k=1) to explain the winning memory in each.

Also reports the current active-memory landscape for real Patch's
Workshop.
"""
import json
from datetime import datetime, timezone

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from apps.spokespeople.models import Teammate
from apps.compositions.models import Composition, CompositionStep
from apps.memory.models import NarrativeMemory
from apps.embeddings.retrieval import retrieve_universe_memory

PROD_UNIVERSE_ID = "56d16b63-652e-4f54-bc7e-39114bbfc4c5"
PROD_WORKSPACE_ID = "4ce5486d-35a4-4bee-8745-38004adb33bc"
COMP_PREFIXES = ["eb48611f", "e6b3f132"]

workspace = Workspace.objects.get(pk=PROD_WORKSPACE_ID)
universe = Universe.objects.get(pk=PROD_UNIVERSE_ID)
cast = list(Teammate.objects.filter(universe=universe).order_by("name"))


def _resolve_memory(mid: str) -> dict:
    try:
        m = (
            NarrativeMemory.objects.select_related("episode")
            .prefetch_related("witnessed_by").get(pk=mid)
        )
        return {
            "id": str(m.id),
            "body": m.body,
            "kind": m.kind,
            "source_episode_title": m.episode.title if m.episode_id else None,
            "source_composition_id": (
                str(m.source_composition_id) if m.source_composition_id else None
            ),
            "witnesses": [w.name for w in m.witnessed_by.all()],
            "witness_scope": (
                "whole-cast" if m.witnessed_by.count() == 0
                else "[" + ", ".join(w.name for w in m.witnessed_by.all()) + "]"
            ),
            "status_now": m.status,
            "archived_at_now": (
                m.archived_at.isoformat() if m.archived_at else None
            ),
        }
    except NarrativeMemory.DoesNotExist:
        return {"id": mid, "resolved": False}


def _summarize_comp(comp: Composition) -> dict:
    steps = list(
        CompositionStep.objects.filter(composition=comp).order_by("position")
    )
    dispatches = sum(
        1 for s in steps
        if s.primitive == "generate_avatar_speech" and s.status == "succeeded"
    )
    cast_names = (
        list(comp.episode.cast.values_list("name", flat=True).order_by("name"))
        if comp.episode_id else []
    )
    resolved_memories = [_resolve_memory(mid) for mid in comp.memory_ids]
    final_duration_ms = None
    if comp.final_asset_id:
        final_duration_ms = getattr(comp.final_asset, "duration_ms", None)

    # Reproduce the retrieval landscape at audit time (top_k=high).
    # Deterministic OpenAI embeddings → same distances retrieval saw
    # at synthesis time (assuming memories in universe are the same
    # set now as at synthesis time; note if landscape changed since).
    landscape_rows = retrieve_universe_memory(
        workspace=workspace,
        universe=universe,
        cast=cast,
        query=comp.operator_topic or "",
        top_k=10,  # >= any current-active-count
    )
    landscape = []
    for i, r in enumerate(landscape_rows, 1):
        witnesses = [w.name for w in r.witnessed_by.all()]
        landscape.append({
            "rank": i,
            "memory_id": str(r.id),
            "body_short": r.body[:90] + ("…" if len(r.body) > 90 else ""),
            "body": r.body,
            "cosine_distance": float(r.distance),
            "witness_scope": (
                "whole-cast" if len(witnesses) == 0
                else "[" + ", ".join(witnesses) + "]"
            ),
            "source_episode_title": r.episode.title if r.episode_id else None,
        })

    return {
        "id": str(comp.id),
        "name": comp.name,
        "status": comp.status,
        "verification_status": comp.verification_status,
        "verification_warnings": comp.verification_warnings,
        "verification_warning_count": len(comp.verification_warnings or []),
        "mock_mode": comp.mock_mode,
        "workspace_id": str(comp.workspace_id),
        "spokesperson_name": comp.spokesperson.name if comp.spokesperson_id else None,
        "cast": cast_names,
        "episode_id": str(comp.episode_id) if comp.episode_id else None,
        "episode_title": comp.episode.title if comp.episode_id else None,
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
        "step_count": len(steps),
        "provider_dispatch_count_speech": dispatches,
        "cost_actual_micros": comp.cost_actual_micros,
        "render_dispatched_at": (
            comp.render_dispatched_at.isoformat()
            if comp.render_dispatched_at else None
        ),
        "created_at": comp.created_at.isoformat(),
        "updated_at": comp.updated_at.isoformat(),
        "final_asset_duration_ms": final_duration_ms,
        "audit_landscape_now": landscape,
        "top1_matches_persisted": (
            landscape[0]["memory_id"] == comp.memory_ids[0]
            if landscape and comp.memory_ids else False
        ),
    }


report = {
    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    "universe_id": PROD_UNIVERSE_ID,
    "cast": [{"id": str(t.id), "name": t.name} for t in cast],
    "compositions": {},
}

for prefix in COMP_PREFIXES:
    comp = (
        Composition.objects
        .filter(id__istartswith=prefix)
        .select_related("workspace", "spokesperson", "episode",
                        "episode__universe", "final_asset")
        .first()
    )
    if comp is None:
        report["compositions"][prefix] = {"resolved": False}
        print(f"\n!!! Composition prefix {prefix} not found !!!")
        continue
    print(f"\n=== Composition {prefix} → {comp.id} ===")
    summary = _summarize_comp(comp)
    report["compositions"][prefix] = summary
    print(f"  status: {summary['status']} verification: {summary['verification_status']}")
    print(f"  ep: {summary['episode_title']!r}")
    print(f"  topic: {summary['operator_topic']!r}")
    print(f"  cast: {summary['cast']}")
    print(f"  memory_ids: {summary['memory_ids']}")
    print(f"  target={summary['target_duration_seconds']}s "
          f"predicted={summary['synthesis_predicted_seconds']}s "
          f"attempts={summary['synthesis_attempt_count']}")
    print(f"  final_asset_duration_ms: {summary['final_asset_duration_ms']}")
    print(f"  dispatches={summary['provider_dispatch_count_speech']} "
          f"cost=${summary['cost_actual_micros']/1_000_000:.4f}")
    print(f"  verification_warnings: {summary['verification_warning_count']}")
    print(f"  top1 matches persisted: {summary['top1_matches_persisted']}")
    print("  Landscape (top_k=10, deterministic OpenAI):")
    for row in summary["audit_landscape_now"]:
        print(f"    rank {row['rank']} d={row['cosine_distance']:.4f} "
              f"{row['witness_scope']} — {row['body_short']}")

# Current active-memory landscape (universe-wide)
active = list(
    NarrativeMemory.objects.filter(
        universe=universe, status="remembered",
        archived_at__isnull=True, embedding_vector__isnull=False,
    ).prefetch_related("witnessed_by").order_by("created_at")
)
active_list = [
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
    for m in active
]
report["current_active_memories"] = active_list
report["current_active_memory_count"] = len(active_list)

print(f"\n\n=== CURRENT ACTIVE MEMORY COUNT: {len(active_list)} ===")
for m in active_list:
    print(f"  {m['id']} | {m['witness_scope']} | from ep={m['source_episode']!r}")
    print(f"    body: {m['body'][:100]!r}")

with open(
    "../docs/design/session_266_experiment_data/19_two_compositions.json",
    "w",
) as fh:
    json.dump(report, fh, indent=2)
