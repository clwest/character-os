"""SESSION 272 Slice C — multi-shot replicate of the Slice B RIVET DEBUGGING A/B.

Reuses the Slice B disposable substrates (workspaces
`session272-rivet-debug-ctl` / `session272-rivet-debug-exp`) verbatim.
Runs 4 additional independent synthesis trials per condition so the
final dataset is CTL n=5, EXP n=5. Slice B evidence becomes trial 1.

Everything else identical to Slice B:
  * same Rivet clones, docs, chunks
  * same operator topic
  * target_duration_seconds=90
  * audience_hint=""
  * target_shape="solo_scene"
  * Writing Contract v6
  * canonical corrective hint
  * retrieval top_k=5 (default)
  * no NarrativeMemory rows attached
  * gpt-4o-mini via OpenAI (per media-engine health)
  * all experiment env vars OFF

Writes evidence sidecar:
  docs/design/session_272_experiment_data/02_slice_c_multishot_evidence.json

Cost: ~8 synthesis calls with potential corrective retries ⇒ up to 16
LLM calls total. Expected ~$0.10 on gpt-4o-mini.

Usage:
  set -a; source .env; set +a; python scripts/session272_slice_c_multishot.py
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


SETUP_MANIFEST = "docs/design/session_272_experiment_data/00_slice_b_setup_manifest.json"
SLICE_B_EVIDENCE = "docs/design/session_272_experiment_data/01_slice_b_ab_render_evidence.json"
EVIDENCE_PATH = "docs/design/session_272_experiment_data/02_slice_c_multishot_evidence.json"

# Byte-identical to Slice B.
OPERATOR_TOPIC = (
    "Rivet demonstrates his debugging approach — when a generation comes out "
    "wrong once, how does he decide whether it's a fluke or a real problem "
    "worth investigating?"
)
TARGET_DURATION_SECONDS = 90
AUDIENCE_HINT = ""
TRIALS_PER_CONDITION = 5


def _run_one_trial(rivet: Teammate) -> dict:
    """One synthesis pass — captures everything Slice B captured."""
    query_vector = _embed_query(OPERATOR_TOPIC)
    scored = list(
        KnowledgeChunk.objects.filter(
            document__workspace=rivet.workspace,
            document__is_active=True,
            document__status="processed",
        )
        .annotate(distance=CosineDistance("embedding_vector", query_vector))
        .order_by("distance")[:5]
    )
    retrieved = retrieve_for_teammate(
        rivet, query=OPERATOR_TOPIC, top_k=5, _query_vector=query_vector,
    )
    t0 = time.time()
    result = synthesize_with_duration_gate(
        rivet,
        OPERATOR_TOPIC,
        target_duration_seconds=TARGET_DURATION_SECONDS,
        target_shape="solo_scene",
        audience_hint=AUDIENCE_HINT,
    )
    elapsed = time.time() - t0
    return {
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
                    "sha256_16": hashlib.sha256(
                        (c.chunk_text or "").encode()
                    ).hexdigest()[:16],
                }
                for c in scored
            ],
        },
        "synthesis": {
            "attempt_count": getattr(result, "attempt_count", 1),
            "first_pass_brief": getattr(result, "first_pass_brief", "") or "",
            "corrective_hint_used": getattr(result, "corrective_hint_used", "") or "",
            "corrective_pass_brief": getattr(result, "corrective_pass_brief", "") or "",
            "accepted_brief": result.brief,
            "chunk_ids": result.chunk_ids,
            "memory_ids": result.memory_ids,
            "verification_status": result.verification_status,
            "used_knowledge": result.used_knowledge,
            "model": result.model,
        },
    }


def _load_slice_b_as_trial1(condition_key: str) -> dict:
    """Reshape the Slice B evidence into the Slice C trial shape so trial 1
    is preserved verbatim."""
    with open(SLICE_B_EVIDENCE) as fh:
        b = json.load(fh)
    src = b[condition_key]
    return {
        "elapsed_seconds": src["elapsed_seconds"],
        "retrieval": src["retrieval"],
        "synthesis": src["synthesis"],
        "provenance": "slice_b_trial_1_verbatim",
    }


def _run_condition(label: str, condition_key: str, rivet_teammate_id: str) -> list[dict]:
    rivet = Teammate.objects.get(id=rivet_teammate_id)
    print(f"\n{'=' * 72}\n{label} — 5 trials (trial 1 preserved from Slice B)\n{'=' * 72}")
    trials = [_load_slice_b_as_trial1(condition_key)]
    print(f"  trial 1: preserved from Slice B (attempts={trials[0]['synthesis']['attempt_count']}, accepted_len={len(trials[0]['synthesis']['accepted_brief'])})")
    for i in range(2, TRIALS_PER_CONDITION + 1):
        t0 = time.time()
        trial = _run_one_trial(rivet)
        trial["provenance"] = "slice_c_fresh"
        trials.append(trial)
        elapsed = time.time() - t0
        s = trial["synthesis"]
        print(
            f"  trial {i}: attempts={s['attempt_count']} "
            f"draft_A_len={len(s['first_pass_brief'])} "
            f"accepted_len={len(s['accepted_brief'])} "
            f"verifier={s['verification_status']} elapsed={elapsed:.2f}s"
        )
    return trials


def main() -> int:
    with open(SETUP_MANIFEST) as fh:
        manifest = json.load(fh)
    print(f"SESSION 272 Slice C — multi-shot replicate")
    print(f"WRITING_CONTRACT_VERSION={WRITING_CONTRACT_VERSION}")
    print(f"operator_topic={OPERATOR_TOPIC[:80]}...")
    print(f"target_duration_seconds={TARGET_DURATION_SECONDS}  audience_hint={AUDIENCE_HINT!r}")
    print(f"trials per condition: {TRIALS_PER_CONDITION}")
    ctl_trials = _run_condition(
        "CTL (canonical enumeration only)",
        "CTL",
        manifest["CTL"]["rivet_teammate_id"],
    )
    exp_trials = _run_condition(
        "EXP (canonical + Option D paired paraphrase)",
        "EXP",
        manifest["EXP"]["rivet_teammate_id"],
    )
    evidence = {
        "session": 272,
        "slice": "C",
        "writing_contract_version": WRITING_CONTRACT_VERSION,
        "operator_topic": OPERATOR_TOPIC,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "audience_hint": AUDIENCE_HINT,
        "trials_per_condition": TRIALS_PER_CONDITION,
        "setup_manifest_ref": SETUP_MANIFEST,
        "slice_b_evidence_ref": SLICE_B_EVIDENCE,
        "CTL_trials": ctl_trials,
        "EXP_trials": exp_trials,
    }
    with open(EVIDENCE_PATH, "w") as fh:
        json.dump(evidence, fh, indent=2)
    print(f"\nEvidence written to {EVIDENCE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
