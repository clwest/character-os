"""SESSION 273 §27 — freeze Ruby's first successful post-§25 render.

Read-only. Dumps all observability + hint verification + knowledge
forensics for Composition 2d50f101-... plus a mechanical scan for
cupcake / cake / frosting material in the Fox & Flour KD to support
the Episode-2 feasibility question.
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


COMP_ID = "2d50f101-8a92-439a-bcff-d12853c9dd3f"
RUBY_ID = "5875a7b4-cf39-433d-89b3-4e34a89a5208"
EPISODE_ID = "77b04b6b-110d-408d-82a3-a04e5ca66417"
UNIVERSE_ID = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"
KD_ID = "74e7f18f-5b77-459c-bc36-b4ab617d8aca"

# Cupcake / cake / decoration keywords for Episode-2 feasibility scan.
CUPCAKE_KEYWORDS = [
    "cupcake",
    "cupcakes",
    "buttercream",
    "swiss meringue",
    "frosting",
    "celebration cake",
    "custom cake",
    "tiered cake",
    "sculpted",
    "fondant",
    "chiffon",
    "hummingbird",
    "devil's food",
    "olive oil citrus",
    "brown-butter",
    "brown butter",
    "curd",
    "ganache",
    "compote",
    "decorator",
    "fillings",
    "pastry",
    "pastries",
]

# Pre-fix failures for the five-run comparison table.
PREFIX_FAILURES = [
    "35eace56-4611-4a0d-abdd-be5d764bb4b8",
    "21e25a2b-47ed-4abc-bcd8-9077fd42d217",
    "f99fe915-dcfb-4832-9f7f-d4e1e5c54a09",
    "fcc52ef6-8c3c-4614-81f9-9251960b0543",
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


def _measure(text):
    return {
        "chars": cc(text),
        "words": wc(text),
        "predicted_seconds": round(cc(text) / 15.0, 1) if text else 0,
    }


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
        "error_message": s.error_message,
    }


def main():
    c = Composition.objects.get(id=COMP_ID)

    # ---- KD chunks retrieved ----
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

    # ---- Corrective hint verification (§25 pins) ----
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

    # ---- Five-run table (4 pre-fix + this success) ----
    five_run = []
    for prev_id in PREFIX_FAILURES:
        pc = Composition.objects.get(id=prev_id)
        five_run.append({
            "composition_id": str(pc.id),
            "generation": "pre-§25",
            "created_at": _iso(pc.created_at),
            "first_pass_chars": cc(pc.first_pass_synthesis),
            "first_pass_words": wc(pc.first_pass_synthesis),
            "corrective_min_instructed": 972,  # pre-§25 baseline
            "corrective_chars": cc(pc.corrective_pass_synthesis),
            "corrective_words": wc(pc.corrective_pass_synthesis),
            "predicted_seconds": pc.synthesis_predicted_seconds,
            "status": pc.status,
            "provider_dispatched": bool(pc.render_dispatched_at),
            "actual_media_seconds": None,
            "cost_micros": pc.cost_actual_micros,
            "attempt_count": pc.synthesis_attempt_count,
        })

    # Successful row — pull actual media duration from Asset if we can
    actual_media_seconds = None
    if c.final_asset_id:
        try:
            fa = Asset.objects.get(id=c.final_asset_id)
            if fa.duration_ms:
                actual_media_seconds = round(fa.duration_ms / 1000.0, 1)
        except Asset.DoesNotExist:
            pass

    five_run.append({
        "composition_id": str(c.id),
        "generation": "post-§25",
        "created_at": _iso(c.created_at),
        "first_pass_chars": cc(c.first_pass_synthesis),
        "first_pass_words": wc(c.first_pass_synthesis),
        "corrective_min_instructed": 1080,  # post-§25
        "corrective_chars": cc(c.corrective_pass_synthesis),
        "corrective_words": wc(c.corrective_pass_synthesis),
        "predicted_seconds": c.synthesis_predicted_seconds,
        "status": c.status,
        "provider_dispatched": bool(c.render_dispatched_at),
        "actual_media_seconds": actual_media_seconds,
        "cost_micros": c.cost_actual_micros,
        "attempt_count": c.synthesis_attempt_count,
    })

    # ---- Side-effect invariants ----
    ruby = Teammate.objects.get(id=RUBY_ID)
    ep = Episode.objects.get(id=EPISODE_ID)
    kd = KnowledgeDocument.objects.get(id=KD_ID)

    # ---- Cupcake feasibility scan on the KD raw text ----
    kd_text = (kd.raw_content or kd.processed_content or "").lower()
    cupcake_hits = {}
    for kw in CUPCAKE_KEYWORDS:
        matches = [m.start() for m in re.finditer(re.escape(kw.lower()), kd_text)]
        if matches:
            cupcake_hits[kw] = {
                "count": len(matches),
                "excerpts": [kd_text[max(0, i - 40):i + len(kw) + 40] for i in matches[:3]],
            }

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
        "scripts": {
            "first_pass_synthesis": {
                **_measure(c.first_pass_synthesis),
                "full": c.first_pass_synthesis,
            },
            "corrective_pass_synthesis": {
                **_measure(c.corrective_pass_synthesis),
                "full": c.corrective_pass_synthesis,
            },
            "synthesized_brief": {
                **_measure(c.synthesized_brief),
                "full": c.synthesized_brief,
            },
        },
        "corrective_hint": {
            "value": c.corrective_hint,
            "checks": hint_checks,
        },
        "chunks_used": chunks_used,
        "chunks_used_count": len(chunks_used),
        "final_asset": (
            {
                "id": str(Asset.objects.get(id=c.final_asset_id).id),
                "role": Asset.objects.get(id=c.final_asset_id).role,
                "asset_type": Asset.objects.get(id=c.final_asset_id).asset_type,
                "duration_ms": Asset.objects.get(id=c.final_asset_id).duration_ms,
                "cost_micros": Asset.objects.get(id=c.final_asset_id).cost_micros,
                "file_path": Asset.objects.get(id=c.final_asset_id).file_path,
                "actual_media_seconds": actual_media_seconds,
            } if c.final_asset_id else None
        ),
        "steps": [_serialize_step(s) for s in CompositionStep.objects.filter(composition=c).order_by("position")],
        "five_run_comparison": five_run,
        "side_effect_invariants": {
            "ruby_universe_id": str(ruby.universe_id) if ruby.universe_id else None,
            "ruby_updated_at": _iso(ruby.updated_at),
            "episode_cast": list(EpisodeCast.objects.filter(episode=ep).values_list("teammate__name", "teammate_id")),
            "kd_universe_id": str(kd.universe_id) if kd.universe_id else None,
            "kd_m2m_spokespeople": list(KnowledgeDocumentSpokesperson.objects.filter(knowledgedocument=kd).values_list("teammate__name", "teammate_id")),
            "kd_content_hash": kd.content_hash,
            "narrative_memory_count_universe": NarrativeMemory.objects.filter(universe_id=UNIVERSE_ID).count(),
        },
        "cupcake_feasibility_scan": {
            "kd_id": str(kd.id),
            "kd_raw_content_chars": len(kd_text),
            "keyword_hits": cupcake_hits,
            "hit_keyword_count": len(cupcake_hits),
        },
    }

    dest = (
        Path(__file__).resolve().parents[1]
        / "docs" / "design" / "session_273_experiment_data"
        / "10_slice_beta_success_forensics.json"
    )
    dest.write_text(json.dumps(out, indent=2, default=str))
    print(f"WROTE {dest} ({dest.stat().st_size} bytes)")
    print()
    print("=== COMPOSITION ===")
    print(f"  id: {c.id}")
    print(f"  status={c.status} attempts={c.synthesis_attempt_count} predicted={c.synthesis_predicted_seconds}s")
    print(f"  fp={cc(c.first_pass_synthesis)}/{wc(c.first_pass_synthesis)}w corr={cc(c.corrective_pass_synthesis)}/{wc(c.corrective_pass_synthesis)}w brief={cc(c.synthesized_brief)}/{wc(c.synthesized_brief)}w")
    print(f"  dispatched={c.render_dispatched_at} cost=${c.cost_actual_micros/1000000:.2f}")
    print(f"  final asset actual media: {actual_media_seconds}s")
    print(f"  audience_hint={c.audience_hint!r} memory_ids={c.memory_ids}")
    print()
    print("=== §25 HINT VERIFICATION ===")
    for k, v in hint_checks.items():
        marker = "✓" if v is True or isinstance(v, (str, int)) else "✗"
        print(f"  {marker} {k}: {v}")
    print()
    print("=== FIVE-RUN COMPARISON ===")
    for r in five_run:
        print(f"  [{r['generation']:8s}] {r['composition_id'][:8]} fp={r['first_pass_chars']:>4} corr_min={r['corrective_min_instructed']:>4} corr={r['corrective_chars']:>4} pred={r['predicted_seconds']}s status={r['status']:>10s} dispatched={r['provider_dispatched']} cost={r['cost_micros']}")
    print()
    print("=== KNOWLEDGE CHUNKS USED ===")
    for i, k in enumerate(chunks_used):
        print(f"  #{i+1} doc={k['document_title'][:40]} uni={k['document_universe_id'][:8] if k['document_universe_id'] else 'NULL'} preview={k['preview_first_300'][:120]!r}")
    print()
    print("=== CUPCAKE FEASIBILITY SCAN ===")
    print(f"  KD text length: {len(kd_text)} chars")
    print(f"  Keywords hit: {len(cupcake_hits)}/{len(CUPCAKE_KEYWORDS)}")
    for kw, hit in cupcake_hits.items():
        print(f"    '{kw}': {hit['count']}x")
    print()
    print("=== SIDE-EFFECT INVARIANTS ===")
    print(f"  Ruby.universe_id: {ruby.universe_id}")
    print(f"  Ruby.updated_at: {ruby.updated_at}")
    print(f"  Episode cast: {list(EpisodeCast.objects.filter(episode=ep).values_list('teammate__name', flat=True))}")
    print(f"  KD content_hash: {kd.content_hash[:16]}...")
    print(f"  NarrativeMemory in Fox & Flour: {NarrativeMemory.objects.filter(universe_id=UNIVERSE_ID).count()}")


if __name__ == "__main__":
    main()
