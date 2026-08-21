"""SESSION 273 §23 — freeze Ruby's failed talking_head Composition.

Read-only. Dumps every observability field on Composition
35eace56-... plus side-effect invariants (Ruby persona, Episode
cast, KD scope, NarrativeMemory count, Fox & Flour Universe state)
so nothing lives only in terminal output.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SHELL_DIR = Path(__file__).resolve().parents[1] / "shell"
if str(SHELL_DIR) not in sys.path:
    sys.path.insert(0, str(SHELL_DIR))

import django  # noqa: E402

django.setup()

from apps.compositions.models import Composition, Asset, CompositionStep  # noqa: E402
from apps.embeddings.models import KnowledgeDocument, KnowledgeDocumentSpokesperson  # noqa: E402
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import EpisodeCast, Episode  # noqa: E402


COMP_ID = "35eace56-4611-4a0d-abdd-be5d764bb4b8"
RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
EPISODE_ID = "77b04b6b-110d-408d-82a3-a04e5ca66417"
UNIVERSE_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
KD_ID = "74e7f18f-5b77-459c-bc36-b4ab617d8aca"


def cc(s):
    return len(s or "")


def wc(s):
    return len(re.findall(r"\S+", s or ""))


def _iso(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _measure_script(s):
    return {
        "chars": cc(s),
        "words": wc(s),
        "head_180": (s or "")[:180],
        "tail_180": (s or "")[-180:],
    }


def main():
    c = Composition.objects.get(id=COMP_ID)

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "composition_id": COMP_ID,
        "composition": {
            "id": str(c.id),
            "template_kind": c.template_kind,
            "status": c.status,
            "created_at": _iso(c.created_at),
            "updated_at": _iso(c.updated_at),
            "spokesperson_id": str(c.spokesperson_id),
            "episode_id": str(c.episode_id) if c.episode_id else None,
            "workspace_id": str(c.workspace_id),
            "operator_topic": c.operator_topic,
            "audience_hint": c.audience_hint,
            "target_duration_seconds": c.target_duration_seconds,
            "writing_contract_version": c.writing_contract_version,
            "synthesis_attempt_count": c.synthesis_attempt_count,
            "synthesis_predicted_seconds": c.synthesis_predicted_seconds,
            "validation_failure_reason": c.validation_failure_reason,
            "mock_mode": c.mock_mode,
            "cost_actual_micros": c.cost_actual_micros,
            "cost_estimate_micros": c.cost_estimate_micros,
            "render_dispatched_at": _iso(c.render_dispatched_at),
            "final_asset_id": str(c.final_asset_id) if c.final_asset_id else None,
            "knowledge_chunk_ids": c.knowledge_chunk_ids,
            "memory_ids": c.memory_ids,
            "verification_status": c.verification_status,
            "verification_warnings": c.verification_warnings,
            "error_message": c.error_message,
        },
        "script_measurements": {
            "first_pass_synthesis": _measure_script(c.first_pass_synthesis),
            "corrective_pass_synthesis": _measure_script(c.corrective_pass_synthesis),
            "synthesized_brief": _measure_script(c.synthesized_brief),
            "rejected_synthesis": _measure_script(c.rejected_synthesis),
        },
        "corrective_hint": {
            "present": bool(c.corrective_hint),
            "chars": cc(c.corrective_hint),
            "value": c.corrective_hint,
        },
    }

    # steps
    steps = []
    for s in CompositionStep.objects.filter(composition=c).order_by("position"):
        step_fields = {
            "id": str(s.id),
            "position": s.position,
            "primitive": s.primitive,
            "status": s.status,
            "cost_actual_micros": s.cost_actual_micros,
            "cost_estimate_micros": s.cost_estimate_micros,
            "started_at": _iso(s.started_at),
            "completed_at": _iso(s.completed_at),
            "elapsed_ms": s.elapsed_ms,
            "error_message": s.error_message,
            "media_engine_task_id": str(s.media_engine_task_id) if s.media_engine_task_id else None,
            "output_asset_id": str(s.output_asset_id) if s.output_asset_id else None,
            "params": s.params,
            "inputs": s.inputs,
        }
        for attr in ():
            if hasattr(s, attr):
                v = getattr(s, attr)
                step_fields[attr] = str(v) if v else v
        steps.append(step_fields)
    out["steps"] = steps

    # assets created since composition (should be none for a failed step-0)
    assets = list(
        Asset.objects.filter(
            spokesperson_id=RUBY_ID, created_at__gte=c.created_at
        ).values("id", "role", "asset_type", "created_at")
    )
    out["assets_since_comp"] = [
        {**a, "id": str(a["id"]), "created_at": _iso(a["created_at"])} for a in assets
    ]

    # side-effect invariants
    ruby = Teammate.objects.get(id=RUBY_ID)
    ep = Episode.objects.get(id=EPISODE_ID)
    kd = KnowledgeDocument.objects.get(id=KD_ID)
    out["side_effect_invariants"] = {
        "ruby": {
            "universe_id": str(ruby.universe_id) if ruby.universe_id else None,
            "updated_at": _iso(ruby.updated_at),
        },
        "episode": {
            "id": str(ep.id),
            "title": ep.title,
            "cast": list(
                EpisodeCast.objects.filter(episode=ep).values_list(
                    "teammate__name", "teammate_id"
                )
            ),
        },
        "kd": {
            "id": str(kd.id),
            "universe_id": str(kd.universe_id) if kd.universe_id else None,
            "m2m_spokespeople": list(
                KnowledgeDocumentSpokesperson.objects.filter(
                    knowledgedocument=kd
                ).values_list("teammate__name", "teammate_id")
            ),
            "content_hash": kd.content_hash,
        },
        "narrative_memories_in_fox_flour": NarrativeMemory.objects.filter(
            universe_id=UNIVERSE_ID
        ).count(),
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs" / "design" / "session_273_experiment_data"
        / "08_slice_beta_ruby_failed_composition.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    print("=== KEY FIELDS ===")
    print(f"Composition:         {c.id} | status={c.status} | kind={c.template_kind}")
    print(f"target_duration_seconds: {c.target_duration_seconds}")
    print(f"writing_contract_version: {c.writing_contract_version}")
    print(f"synthesis_attempt_count: {c.synthesis_attempt_count}  ← was corrective pass invoked?")
    print(f"synthesis_predicted_seconds: {c.synthesis_predicted_seconds}")
    print(f"validation_failure_reason: {c.validation_failure_reason!r}")
    print(f"render_dispatched_at: {c.render_dispatched_at}")
    print(f"cost_actual_micros: {c.cost_actual_micros}")
    print(f"final_asset_id: {c.final_asset_id}  (should be None)")
    print(f"audience_hint: {c.audience_hint!r}")
    print()
    print(f"first_pass_synthesis: chars={cc(c.first_pass_synthesis)} words={wc(c.first_pass_synthesis)}")
    print(f"corrective_pass_synthesis: chars={cc(c.corrective_pass_synthesis)} words={wc(c.corrective_pass_synthesis)}")
    print(f"synthesized_brief: chars={cc(c.synthesized_brief)} words={wc(c.synthesized_brief)}")
    print(f"rejected_synthesis: chars={cc(c.rejected_synthesis)} words={wc(c.rejected_synthesis)}")
    print()
    print("=== corrective_hint (verbatim) ===")
    if c.corrective_hint:
        print(c.corrective_hint)
    else:
        print("(empty — corrective pass may not have fired)")
    print()
    print("=== error_message ===")
    print(c.error_message)
    print()
    print("=== assets since comp ===")
    print(out["assets_since_comp"])


if __name__ == "__main__":
    main()
