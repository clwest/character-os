"""SESSION 273 — Pre-dogfood Ruby/Mason substrate audit.

Read-only. Dumps mechanical evidence to a JSON sidecar. Does NOT modify data.

Usage (from character-os/shell/ with .env sourced):
  DJANGO_SETTINGS_MODULE=character_os.settings python3 ../scripts/session273_substrate_audit.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from django.db.models import Q  # noqa: E402

from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import Universe, Episode, EpisodeCast  # noqa: E402
from apps.compositions.models import Composition, Asset  # noqa: E402
from apps.embeddings.models import KnowledgeDocument, KnowledgeChunk  # noqa: E402
from apps.memory.models import NarrativeMemory  # noqa: E402


RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
MASON_ID = "28b9a7ea-8230-4463-8b0d-4ebfabfe11ec"
RUBY_MASON_WORKSPACE = "4ce5486d-35a4-4bee-8745-38004adb33bc"


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _serialize_teammate(t):
    return {
        "id": str(t.id),
        "name": t.name,
        "workspace_id": str(t.workspace_id),
        "universe_id": str(t.universe_id) if t.universe_id else None,
        "status": t.status,
        "created_at": _iso(t.created_at),
        "updated_at": _iso(t.updated_at),
        "seconds_between_create_and_update": (
            (t.updated_at - t.created_at).total_seconds() if t.updated_at and t.created_at else None
        ),
        "business_brief": t.business_brief,
        "who_you_help": t.who_you_help,
        "what_you_sell": t.what_you_sell,
        "desired_feeling": t.desired_feeling,
        "tone_archetype": t.tone_archetype,
        "personality": t.personality,
        "character_point_of_view": t.character_point_of_view,
        "always_emphasize": t.always_emphasize,
        "never_say": t.never_say,
        "voice_energy": t.voice_energy,
        "voice_humor": t.voice_humor,
        "voice_directness": t.voice_directness,
        "voice_signature_phrases": t.voice_signature_phrases,
        "voice_avoid_phrases": t.voice_avoid_phrases,
        "runway_avatar_id": t.runway_avatar_id,
        "runway_avatar_status": t.runway_avatar_status,
        "voice_id": t.voice_id,
        "visual_subject": t.visual_subject,
        "visual_template": t.visual_template,
        "portrait_path": t.portrait_path,
    }


def _serialize_composition(c):
    return {
        "id": str(c.id),
        "name": c.name,
        "template_kind": c.template_kind,
        "status": c.status,
        "created_at": _iso(c.created_at),
        "updated_at": _iso(c.updated_at),
        "workspace_id": str(c.workspace_id),
        "spokesperson_id": str(c.spokesperson_id) if c.spokesperson_id else None,
        "episode_id": str(c.episode_id) if c.episode_id else None,
        "final_asset_id": str(c.final_asset_id) if c.final_asset_id else None,
        "writing_contract_version": c.writing_contract_version,
        "operator_topic": c.operator_topic,
        "target_duration_seconds": c.target_duration_seconds,
        "synthesis_attempt_count": c.synthesis_attempt_count,
        "audience_hint": c.audience_hint,
        "mock_mode": c.mock_mode,
        "cost_actual_micros": c.cost_actual_micros,
        "knowledge_chunk_ids_len": len(c.knowledge_chunk_ids or []),
        "memory_ids_len": len(c.memory_ids or []),
        "verification_status": c.verification_status,
        "verification_warnings_len": len(c.verification_warnings or []),
        "first_pass_synthesis_len": len(c.first_pass_synthesis or ""),
        "corrective_hint_present": bool(c.corrective_hint),
        "corrective_pass_synthesis_len": len(c.corrective_pass_synthesis or ""),
        "synthesized_brief_len": len(c.synthesized_brief or ""),
        "render_dispatched_at": _iso(c.render_dispatched_at),
        "error_message": c.error_message,
    }


def _serialize_asset(a):
    return {
        "id": str(a.id),
        "role": a.role,
        "type": a.type,
        "created_at": _iso(a.created_at),
        "workspace_id": str(a.workspace_id) if getattr(a, "workspace_id", None) else None,
        "spokesperson_id": str(a.spokesperson_id) if getattr(a, "spokesperson_id", None) else None,
    }


def _serialize_kd(k):
    return {
        "id": str(k.id),
        "title": k.title,
        "workspace_id": str(k.workspace_id) if k.workspace_id else None,
        "universe_id": str(k.universe_id) if k.universe_id else None,
        "created_at": _iso(k.created_at),
        "updated_at": _iso(k.updated_at),
        "chunk_count": KnowledgeChunk.objects.filter(document=k).count(),
        "status": k.status,
        "document_type": k.document_type,
        "source_url": k.source_url,
        "ingested_via": k.ingested_via,
    }


def _serialize_narrative_memory(m):
    return {
        "id": str(m.id),
        "workspace_id": str(m.workspace_id) if m.workspace_id else None,
        "universe_id": str(m.universe_id) if m.universe_id else None,
        "episode_id": str(m.episode_id) if m.episode_id else None,
        "source_composition_id": str(m.source_composition_id) if m.source_composition_id else None,
        "created_at": _iso(m.created_at),
        "kind": m.kind,
        "weight": m.weight,
        "status": m.status,
        "body_len": len(m.body or ""),
        "body_preview": (m.body or "")[:120],
    }


def _serialize_universe(u):
    return {
        "id": str(u.id),
        "name": u.name,
        "workspace_id": str(u.workspace_id),
        "created_at": _iso(u.created_at),
    }


def _serialize_episode(e):
    return {
        "id": str(e.id),
        "title": e.title,
        "operator_topic_len": len(e.operator_topic or ""),
        "universe_id": str(e.universe_id) if e.universe_id else None,
        "created_at": _iso(e.created_at),
    }


def _audit_teammate(t):
    direct_kds = list(t.knowledge_documents.all())
    cast_rows = list(EpisodeCast.objects.filter(teammate=t).select_related("episode"))
    ep_ids = {c.episode_id for c in cast_rows}
    eps = list(Episode.objects.filter(id__in=ep_ids)) if ep_ids else []
    # Compositions where t is spokesperson
    comps = list(Composition.objects.filter(spokesperson=t).order_by("created_at"))
    comp_ids = {c.id for c in comps}
    # NarrativeMemories whose source_composition.spokesperson = t
    mems_via_comp = list(NarrativeMemory.objects.filter(source_composition__spokesperson=t))
    # Witnessed memories (m2m defined on Teammate as witnessed_narrative_memories)
    witnessed = list(t.witnessed_narrative_memories.all()) if hasattr(t, "witnessed_narrative_memories") else []

    universe = None
    universe_kds = []
    universe_mems = []
    if t.universe_id:
        try:
            universe = Universe.objects.get(id=t.universe_id)
            universe_kds = list(KnowledgeDocument.objects.filter(universe=universe))
            universe_mems = list(NarrativeMemory.objects.filter(universe=universe))
        except Universe.DoesNotExist:
            pass

    campaigns = list(t.personalized_campaigns.all()) if hasattr(t, "personalized_campaigns") else []
    assets = list(t.related_assets.all()) if hasattr(t, "related_assets") else []

    return {
        "teammate": _serialize_teammate(t),
        "universe_scope": _serialize_universe(universe) if universe else None,
        "direct_knowledge_documents_count": len(direct_kds),
        "direct_knowledge_documents": [_serialize_kd(k) for k in direct_kds],
        "universe_scoped_knowledge_documents_count": len(universe_kds),
        "universe_scoped_knowledge_documents": [_serialize_kd(k) for k in universe_kds],
        "universe_scoped_narrative_memories_count": len(universe_mems),
        "episode_cast_rows_count": len(cast_rows),
        "episodes": [_serialize_episode(e) for e in eps],
        "compositions_count": len(comps),
        "compositions": [_serialize_composition(c) for c in comps],
        "narrative_memories_via_source_composition_count": len(mems_via_comp),
        "narrative_memories_via_source_composition": [_serialize_narrative_memory(m) for m in mems_via_comp],
        "witnessed_narrative_memories_count": len(witnessed),
        "witnessed_narrative_memories": [_serialize_narrative_memory(m) for m in witnessed],
        "personalized_campaigns_count": len(campaigns),
        "related_assets_count": len(assets),
        "related_assets_sample": [_serialize_asset(a) for a in assets[:20]],
    }


def _workspace_retrieval_env(workspace_id):
    kds = list(KnowledgeDocument.objects.filter(workspace_id=workspace_id))
    mems = list(NarrativeMemory.objects.filter(workspace_id=workspace_id))
    return {
        "workspace_id": workspace_id,
        "total_knowledge_documents": len(kds),
        "knowledge_document_summary": [
            {
                "id": str(k.id),
                "title": k.title,
                "universe_id": str(k.universe_id) if k.universe_id else None,
                "status": k.status,
                "document_type": k.document_type,
            }
            for k in kds
        ],
        "total_narrative_memories": len(mems),
        "narrative_memory_summary": [
            {
                "id": str(m.id),
                "universe_id": str(m.universe_id) if m.universe_id else None,
                "episode_id": str(m.episode_id) if m.episode_id else None,
                "kind": m.kind,
                "status": m.status,
            }
            for m in mems
        ],
    }


def main():
    now_utc = datetime.now(timezone.utc)
    ruby = Teammate.objects.get(id=RUBY_ID)
    mason = Teammate.objects.get(id=MASON_ID)

    out = {
        "generated_at": now_utc.isoformat(),
        "ruby_id": RUBY_ID,
        "mason_id": MASON_ID,
        "workspace_id": RUBY_MASON_WORKSPACE,
        "ruby": _audit_teammate(ruby),
        "mason": _audit_teammate(mason),
        "shared_workspace_retrieval_env": _workspace_retrieval_env(RUBY_MASON_WORKSPACE),
        "workspace_universes": [
            _serialize_universe(u)
            for u in Universe.objects.filter(workspace_id=RUBY_MASON_WORKSPACE).order_by("created_at")
        ],
        "runtime_invariants_at_audit": {
            "experiment_env_vars_present": {
                k: os.environ.get(k) for k in os.environ if "EXPERIMENT" in k.upper()
            },
            "mock_env_vars_present": {
                k: os.environ.get(k) for k in os.environ if "_MOCK" in k.upper()
            },
        },
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "design"
        / "session_273_experiment_data"
        / "01_ruby_mason_substrate_audit.json"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
