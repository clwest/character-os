"""SESSION 272 Slice B — A/B synthesis render + evidence capture.

Runs `synthesize_with_duration_gate` directly against the two disposable
workspaces created by session272_slice_b_setup.py. Captures per-condition:

  * retrieved chunk ids + cosine distances
  * first-pass synthesis text
  * corrective hint used (if any)
  * corrective-pass synthesis text (if any)
  * accepted synthesized brief
  * attempt count
  * verification_status
  * duration + char + word measurements

Writes evidence sidecar JSON:
  docs/design/session_272_experiment_data/01_slice_b_ab_render_evidence.json

Does NOT fire Runway avatar_speech. Does NOT create Composition rows for the
render (evidence lives in the sidecar). Cost: 2 x LLM synthesis calls
(maybe 4 if both trigger a corrective retry) — total < $0.05 on gpt-4o-mini.

Usage:
  set -a; source .env; set +a; python scripts/session272_slice_b_render.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "shell"))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
os.environ.setdefault("DB_PORT", "5434")
django.setup()

from apps.embeddings.models import KnowledgeChunk  # noqa: E402
from apps.embeddings.retrieval import (  # noqa: E402
    _embed_query,  # type: ignore[attr-defined]
    retrieve_for_teammate,
)
from apps.spokespeople.models import Teammate  # noqa: E402
from character_os.duration_contract import synthesize_with_duration_gate  # noqa: E402
from character_os.writing_contract import WRITING_CONTRACT_VERSION  # noqa: E402
from pgvector.django import CosineDistance  # noqa: E402


MANIFEST_PATH = "docs/design/session_272_experiment_data/00_slice_b_setup_manifest.json"
EVIDENCE_PATH = "docs/design/session_272_experiment_data/01_slice_b_ab_render_evidence.json"

# Fresh, unsaturated Rivet substrate — a debugging topic that has NEVER been
# rendered before, and that is different from every SESSION 271 topic.
OPERATOR_TOPIC = (
    "Rivet demonstrates his debugging approach — when a generation comes out "
    "wrong once, how does he decide whether it's a fluke or a real problem "
    "worth investigating?"
)
TARGET_DURATION_SECONDS = 90
AUDIENCE_HINT = ""  # empty ⇒ v6 universal invariant fires alone


def _run_condition(label: str, condition: dict) -> dict:
    """Run synthesis for one condition + capture everything."""
    print(f"\n{'=' * 72}\n{label} — running synthesis\n{'=' * 72}")
    rivet_id = condition["rivet_teammate_id"]
    rivet = Teammate.objects.get(id=rivet_id)
    print(f"  Rivet teammate: {rivet.id} (ws={rivet.workspace_id})")
    # Compute what retrieval would return — for evidence provenance.
    query_vector = _embed_query(OPERATOR_TOPIC)
    retrieved = retrieve_for_teammate(
        rivet, query=OPERATOR_TOPIC, top_k=5,
        _query_vector=query_vector,
    )
    # Re-run with .distance annotation exposed for score capture.
    # (retrieve_for_teammate returns rows already-annotated but strips the
    # annotation from the return list; refetch with the same filter to keep
    # scores side-by-side.)
    scored = list(
        KnowledgeChunk.objects.filter(
            document__workspace=rivet.workspace,
            document__is_active=True,
            document__status="processed",
        )
        .annotate(distance=CosineDistance("embedding_vector", query_vector))
        .order_by("distance")[:5]
    )
    print(f"  retrieved chunks: {len(retrieved)} ; scored: {len(scored)}")
    for i, c in enumerate(scored):
        print(f"    [{i}] {c.id} idx={c.chunk_index} distance={c.distance:.4f}")
    t0 = time.time()
    result = synthesize_with_duration_gate(
        rivet,
        OPERATOR_TOPIC,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        target_shape="solo_scene",
        audience_hint=AUDIENCE_HINT,
    )
    elapsed = time.time() - t0
    first_pass = getattr(result, "first_pass_brief", "") or ""
    corrective_hint = getattr(result, "corrective_hint_used", "") or ""
    corrective_pass = getattr(result, "corrective_pass_brief", "") or ""
    attempts = getattr(result, "attempt_count", 1)
    accepted = result.brief
    print(f"  attempts={attempts} elapsed={elapsed:.2f}s")
    print(f"  first_pass_len={len(first_pass)}  corrective_pass_len={len(corrective_pass)}")
    print(f"  accepted_len={len(accepted)}")
    print(f"  verification_status={result.verification_status}")
    return {
        "label": label,
        "rivet_teammate_id": str(rivet.id),
        "workspace_id": str(rivet.workspace_id),
        "workspace_slug": condition["workspace_slug"],
        "doc_id": condition["doc_id"],
        "operator_topic": OPERATOR_TOPIC,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "target_shape": "solo_scene",
        "audience_hint": AUDIENCE_HINT,
        "writing_contract_version": WRITING_CONTRACT_VERSION,
        "elapsed_seconds": round(elapsed, 3),
        "retrieval": {
            "returned_chunk_count": len(retrieved),
            "scored_chunks": [
                {
                    "id": str(c.id),
                    "chunk_index": c.chunk_index,
                    "document_id": str(c.document_id),
                    "distance": float(c.distance),
                    "length": len(c.chunk_text or ""),
                    "sha256_16": hashlib.sha256((c.chunk_text or "").encode()).hexdigest()[:16],
                    "text": c.chunk_text,
                }
                for c in scored
            ],
        },
        "synthesis": {
            "attempt_count": attempts,
            "first_pass_brief": first_pass,
            "corrective_hint_used": corrective_hint,
            "corrective_pass_brief": corrective_pass,
            "accepted_brief": accepted,
            "chunk_ids": result.chunk_ids,
            "memory_ids": result.memory_ids,
            "verification_status": result.verification_status,
            "used_knowledge": result.used_knowledge,
            "model": result.model,
        },
    }


def main() -> int:
    with open(MANIFEST_PATH) as fh:
        manifest = json.load(fh)
    print("SESSION 272 Slice B — A/B render")
    print(f"WRITING_CONTRACT_VERSION={WRITING_CONTRACT_VERSION}")
    print(f"operator_topic={OPERATOR_TOPIC}")
    print(f"target_duration_seconds={TARGET_DURATION_SECONDS}  audience_hint={AUDIENCE_HINT!r}")

    ctl_result = _run_condition("CTL (canonical enumeration only)", manifest["CTL"])
    exp_result = _run_condition("EXP (canonical + Option D paired paraphrase)", manifest["EXP"])
    evidence = {
        "session": 272,
        "slice": "B",
        "writing_contract_version": WRITING_CONTRACT_VERSION,
        "operator_topic": OPERATOR_TOPIC,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "audience_hint": AUDIENCE_HINT,
        "setup_manifest": manifest,
        "CTL": ctl_result,
        "EXP": exp_result,
    }
    with open(EVIDENCE_PATH, "w") as fh:
        json.dump(evidence, fh, indent=2)
    print(f"\nEvidence written to {EVIDENCE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
