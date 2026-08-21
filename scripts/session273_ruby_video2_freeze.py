"""SESSION 273 §29 — freeze Ruby's second successful production render.

Read-only. Full forensic evidence for Composition 5052035e-... plus a
mechanical grounding audit against Ruby's approved Fox & Flour KD.
"""

from __future__ import annotations

import hashlib
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
from apps.embeddings.models import (  # noqa: E402
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeDocumentSpokesperson,
)
from apps.memory.models import NarrativeMemory  # noqa: E402
from apps.spokespeople.models import Teammate  # noqa: E402
from apps.universe.models import EpisodeCast, Episode  # noqa: E402


COMP_ID = "5052035e-f07e-4b42-bd3f-f4c3e0168a8f"
COMP1_ID = "2d50f101-8a92-439a-bcff-d12853c9dd3f"
RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
UNIVERSE_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
KD_ID = "74e7f18f-5b77-459c-bc36-b4ab617d8aca"

# Chris-listed cake claims to check.
CAKE_CLAIMS = [
    "vanilla-bean chiffon",
    "brown-butter almond",
    "chocolate devil's food",
    "olive oil citrus",
    "hummingbird",
    "swiss meringue buttercream",
    "fresh curd",
    "curd",
    "whipped ganache",
    "ganache",
    "seasonal fruit compote",
    "compote",
    "fondant",
    "buttercream",
    "5-day",
    "five days",
    "10-day",
    "ten days",
    "sculpted",
    "heavily decorated",
    "spring weddings",
    "december holidays",
    "50% deposit",
    "50 percent deposit",
    "half deposit",
    "72 hours",
    "seventy-two hours",
    "pickup",
    "does not deliver",
    "no delivery",
    "birthday",
    "wedding",
    "shower",
]


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


def _grounding_scan(brief_text: str, kd_text: str, claims: list[str]) -> dict:
    """For each claim, report whether it appears in the brief and whether it
    appears (case-insensitively) in the KD text. Neither is a full semantic
    check — but a claim that appears in the brief and not in the KD is a
    material flag."""
    brief_lower = (brief_text or "").lower()
    kd_lower = (kd_text or "").lower()
    result = {}
    for claim in claims:
        claim_lower = claim.lower()
        result[claim] = {
            "in_brief": claim_lower in brief_lower,
            "in_kd": claim_lower in kd_lower,
        }
    return result


def _serialize_step(s):
    return {
        "id": str(s.id),
        "position": s.position,
        "primitive": s.primitive,
        "status": s.status,
        "started_at": _iso(s.started_at),
        "completed_at": _iso(s.completed_at),
        "elapsed_ms": s.elapsed_ms,
        "cost_actual_micros": s.cost_actual_micros,
        "cost_estimate_micros": s.cost_estimate_micros,
        "media_engine_task_id": str(s.media_engine_task_id) if s.media_engine_task_id else None,
        "output_asset_id": str(s.output_asset_id) if s.output_asset_id else None,
    }


def main():
    c = Composition.objects.get(id=COMP_ID)
    c1 = Composition.objects.get(id=COMP1_ID)
    kd = KnowledgeDocument.objects.get(id=KD_ID)
    ruby = Teammate.objects.get(id=RUBY_ID)

    ep = Episode.objects.get(id=c.episode_id)

    kd_text = kd.raw_content or kd.processed_content or ""

    # Chunks used
    chunks_used = []
    if c.knowledge_chunk_ids:
        by_id = {str(k.id): k for k in KnowledgeChunk.objects.filter(id__in=c.knowledge_chunk_ids)}
        for cid in c.knowledge_chunk_ids:
            k = by_id.get(cid)
            if k:
                chunks_used.append({
                    "chunk_id": str(k.id),
                    "document_id": str(k.document_id),
                    "document_title": k.document.title,
                    "document_universe_id": str(k.document.universe_id) if k.document.universe_id else None,
                    "chars": len(k.chunk_text or ""),
                    "preview_first_300": (k.chunk_text or "")[:300],
                })

    # Hint verification
    hint = c.corrective_hint or ""
    hint_checks = {
        "contains_EXPAND_YOUR_SCRIPT": "EXPAND YOUR SCRIPT" in hint,
        "contains_AT_LEAST_1080_CHARACTERS": "AT LEAST 1080 CHARACTERS" in hint,
        "contains_aim_for_1350": "aim for ~1350" in hint,
        "contains_do_not_exceed_1620": "do not exceed 1620" in hint,
        "contains_Target_is_90s": "Target is 90s" in hint,
        "absent_AT_LEAST_972_CHARACTERS": "AT LEAST 972 CHARACTERS" not in hint,
        "absent_Target_is_81s": "Target is 81s" not in hint,
        "absent_REWRITE_THE_SAME_NARRATIVE_ABOVE": "REWRITE THE SAME NARRATIVE ABOVE" not in hint,
        "sha256_first_12": hashlib.sha256(hint.encode()).hexdigest()[:12],
        "byte_length": len(hint),
    }

    # Grounding scan on accepted brief
    grounding = _grounding_scan(c.synthesized_brief or "", kd_text, CAKE_CLAIMS)

    # Final asset details
    actual_media_seconds = None
    final_asset_details = None
    if c.final_asset_id:
        try:
            fa = Asset.objects.get(id=c.final_asset_id)
            if fa.duration_ms:
                actual_media_seconds = round(fa.duration_ms / 1000.0, 1)
            final_asset_details = {
                "id": str(fa.id),
                "role": fa.role,
                "asset_type": fa.asset_type,
                "duration_ms": fa.duration_ms,
                "cost_micros": fa.cost_micros,
                "file_path": fa.file_path,
                "actual_media_seconds": actual_media_seconds,
            }
        except Asset.DoesNotExist:
            pass

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "composition_id": COMP_ID,
        "composition": {
            "id": str(c.id),
            "template_kind": c.template_kind,
            "status": c.status,
            "created_at": _iso(c.created_at),
            "updated_at": _iso(c.updated_at),
            "target_duration_seconds": c.target_duration_seconds,
            "writing_contract_version": c.writing_contract_version,
            "synthesis_attempt_count": c.synthesis_attempt_count,
            "synthesis_predicted_seconds": c.synthesis_predicted_seconds,
            "validation_failure_reason": c.validation_failure_reason,
            "verification_status": c.verification_status,
            "verification_warnings": c.verification_warnings,
            "render_dispatched_at": _iso(c.render_dispatched_at),
            "cost_actual_micros": c.cost_actual_micros,
            "final_asset_id": str(c.final_asset_id) if c.final_asset_id else None,
            "audience_hint": c.audience_hint,
            "operator_topic": c.operator_topic,
            "mock_mode": c.mock_mode,
            "knowledge_chunk_ids": c.knowledge_chunk_ids,
            "memory_ids": c.memory_ids,
        },
        "episode": {
            "id": str(ep.id),
            "title": ep.title,
            "operator_topic": ep.operator_topic,
            "universe_id": str(ep.universe_id),
            "cast": list(EpisodeCast.objects.filter(episode=ep).values_list("teammate__name", "teammate_id")),
        },
        "scripts": {
            "first_pass_synthesis": {
                "chars": cc(c.first_pass_synthesis),
                "words": wc(c.first_pass_synthesis),
                "predicted_seconds": round(cc(c.first_pass_synthesis) / 15.0, 1) if c.first_pass_synthesis else 0,
                "full": c.first_pass_synthesis,
            },
            "corrective_pass_synthesis": {
                "chars": cc(c.corrective_pass_synthesis),
                "words": wc(c.corrective_pass_synthesis),
                "predicted_seconds": round(cc(c.corrective_pass_synthesis) / 15.0, 1) if c.corrective_pass_synthesis else 0,
                "full": c.corrective_pass_synthesis,
            },
            "synthesized_brief": {
                "chars": cc(c.synthesized_brief),
                "words": wc(c.synthesized_brief),
                "predicted_seconds": round(cc(c.synthesized_brief) / 15.0, 1) if c.synthesized_brief else 0,
                "full": c.synthesized_brief,
            },
        },
        "corrective_hint": {
            "value": c.corrective_hint,
            "checks": hint_checks,
        },
        "chunks_used": chunks_used,
        "chunks_used_count": len(chunks_used),
        "final_asset": final_asset_details,
        "steps": [_serialize_step(s) for s in CompositionStep.objects.filter(composition=c).order_by("position")],
        "grounding_scan": grounding,
        "comparison_with_video1": {
            "video1": {
                "id": str(c1.id),
                "topic": c1.operator_topic,
                "attempts": c1.synthesis_attempt_count,
                "first_pass_chars": cc(c1.first_pass_synthesis),
                "corrective_chars": cc(c1.corrective_pass_synthesis),
                "brief_chars": cc(c1.synthesized_brief),
                "brief_words": wc(c1.synthesized_brief),
                "predicted_seconds": c1.synthesis_predicted_seconds,
                "cost_micros": c1.cost_actual_micros,
                "audience_hint": c1.audience_hint,
                "memory_ids": c1.memory_ids,
                "verification_status": c1.verification_status,
                "chunk_count": len(c1.knowledge_chunk_ids or []),
            },
            "video2": {
                "id": str(c.id),
                "topic": c.operator_topic,
                "attempts": c.synthesis_attempt_count,
                "first_pass_chars": cc(c.first_pass_synthesis),
                "corrective_chars": cc(c.corrective_pass_synthesis),
                "brief_chars": cc(c.synthesized_brief),
                "brief_words": wc(c.synthesized_brief),
                "predicted_seconds": c.synthesis_predicted_seconds,
                "cost_micros": c.cost_actual_micros,
                "audience_hint": c.audience_hint,
                "memory_ids": c.memory_ids,
                "verification_status": c.verification_status,
                "chunk_count": len(c.knowledge_chunk_ids or []),
            },
        },
        "side_effect_invariants": {
            "ruby_universe_id": str(ruby.universe_id) if ruby.universe_id else None,
            "ruby_updated_at": _iso(ruby.updated_at),
            "kd_content_hash": kd.content_hash,
            "kd_m2m_spokespeople": list(KnowledgeDocumentSpokesperson.objects.filter(knowledgedocument=kd).values_list("teammate__name", "teammate_id")),
            "narrative_memory_count_universe": NarrativeMemory.objects.filter(universe_id=UNIVERSE_ID).count(),
        },
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs" / "design" / "session_273_experiment_data"
        / "11_slice_beta_video2_forensics.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    print(f"=== COMPOSITION 5052035e ===")
    print(f"  status={c.status} attempts={c.synthesis_attempt_count} predicted={c.synthesis_predicted_seconds}s")
    print(f"  fp={cc(c.first_pass_synthesis)}/{wc(c.first_pass_synthesis)}w corr={cc(c.corrective_pass_synthesis)}/{wc(c.corrective_pass_synthesis)}w brief={cc(c.synthesized_brief)}/{wc(c.synthesized_brief)}w")
    print(f"  dispatched={c.render_dispatched_at} cost=${c.cost_actual_micros/1000000:.2f}")
    print(f"  final asset actual media: {actual_media_seconds}s")
    print(f"  ep={c.episode_id} operator_topic={c.operator_topic!r} audience_hint={c.audience_hint!r}")
    print()
    print(f"=== §25 HINT VERIFICATION ===")
    for k, v in hint_checks.items():
        marker = "✓" if v is True or isinstance(v, (str, int)) else "✗"
        print(f"  {marker} {k}: {v}")
    print()
    print(f"=== CHUNKS USED ({len(chunks_used)}) ===")
    for i, k in enumerate(chunks_used):
        print(f"  #{i+1} doc={k['document_title'][:40]} uni={k['document_universe_id'][:8] if k['document_universe_id'] else 'NULL'} preview={k['preview_first_300'][:120]!r}")
    print()
    print(f"=== CAKE-CLAIM GROUNDING SCAN ===")
    for claim, hit in grounding.items():
        if hit["in_brief"]:
            marker = "✓" if hit["in_kd"] else "✗ (in brief but NOT in KD)"
            print(f"  brief mentions {claim!r}: kd={hit['in_kd']} {marker}")
    print()
    unmentioned_grounded = [c for c, h in grounding.items() if h["in_kd"] and not h["in_brief"]]
    print(f"KD claims not mentioned in brief: {len(unmentioned_grounded)}")


if __name__ == "__main__":
    main()
