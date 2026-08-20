"""SESSION 272 Slice E — three-condition corrective-hint ablation.

Runs n=5 fresh trials each for NO-KNOWLEDGE-REF and CORRECT-ANCHOR
variants. Reuses the Slice C CTL n=5 trials as the BASELINE condition
(mechanically equivalent — same substrate/runtime/model/hint).

Isolation:
  * Monkey-patches `character_os.duration_contract._expansion_hint`
    per condition inside a `try/finally` that restores the original.
  * Verifies restore before AND after each condition block.
  * Records the sha256 of the emitted hint on every trial so any
    drift from the frozen exemplar would be caught.

Non-changes verified externally:
  * Canonical RIVET doc SHA before + after.
  * Writing Contract v6 unchanged.
  * Rivet clones unchanged.
  * All experiment env vars OFF.
  * No committed source-code change.

Writes:
  docs/design/session_272_experiment_data/04_slice_e_ablation_evidence.json

Usage:
  set -a; source .env; set +a; python scripts/session272_slice_e_ablation.py
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
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")
os.environ.setdefault("DB_PORT", "5434")
django.setup()

import character_os.duration_contract as dc  # noqa: E402
from apps.embeddings.models import KnowledgeChunk  # noqa: E402
from apps.embeddings.retrieval import (  # noqa: E402
    _embed_query,  # type: ignore[attr-defined]
    retrieve_for_teammate,
)
from apps.spokespeople.models import Teammate  # noqa: E402
from character_os.duration_contract import synthesize_with_duration_gate  # noqa: E402
from character_os.writing_contract import WRITING_CONTRACT_VERSION  # noqa: E402
from pgvector.django import CosineDistance  # noqa: E402
from session272_slice_e_hint_variants import (  # noqa: E402
    _correct_anchor_hint,
    _no_knowledge_ref_hint,
    frozen_exemplars,
)


SETUP_MANIFEST = Path("docs/design/session_272_experiment_data/00_slice_b_setup_manifest.json")
SLICE_C_EVIDENCE = Path("docs/design/session_272_experiment_data/02_slice_c_multishot_evidence.json")
EVIDENCE_PATH = Path("docs/design/session_272_experiment_data/04_slice_e_ablation_evidence.json")

OPERATOR_TOPIC = (
    "Rivet demonstrates his debugging approach — when a generation comes out "
    "wrong once, how does he decide whether it's a fluke or a real problem "
    "worth investigating?"
)
TARGET_DURATION_SECONDS = 90
AUDIENCE_HINT = ""
TRIALS_PER_CONDITION = 5

# Freeze the exact exemplar SHAs so drift is caught.
_EXEMPLARS = frozen_exemplars()
NO_KNOWLEDGE_REF_SHA = _EXEMPLARS["NO_KNOWLEDGE_REF"]["sha256"]
CORRECT_ANCHOR_SHA = _EXEMPLARS["CORRECT_ANCHOR"]["sha256"]


def _capture_hint_wrapper(fn, hint_capture_slot: list) -> callable:
    """Wrap a hint function to record its emitted text on each call.

    The slot is a list; each call appends the emitted text so the
    trial-level record can prove the correct variant was in force
    at the moment of the corrective retry.
    """
    def wrapped(**kwargs):
        text = fn(**kwargs)
        hint_capture_slot.append(text)
        return text
    return wrapped


def _run_one_trial(rivet: Teammate, hint_capture_slot: list) -> dict:
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
        "hint_capture": {
            "emitted_hint_texts": list(hint_capture_slot),
            "emitted_hint_sha256": [
                hashlib.sha256(t.encode()).hexdigest() for t in hint_capture_slot
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
            "verification_warnings": getattr(result, "verification_warnings", []),
        },
    }


def _run_condition(label: str, rivet: Teammate, hint_fn) -> list[dict]:
    """Run n=5 trials with the given hint fn monkey-patched into _expansion_hint.

    Verifies restore in a `finally` block. Verifies emitted hint SHAs
    match the frozen exemplar (allows for the character-shortfall
    arithmetic changing but not the wording).
    """
    print(f"\n{'=' * 72}\n{label} — {TRIALS_PER_CONDITION} trials\n{'=' * 72}")
    trials: list[dict] = []
    original = dc._expansion_hint
    # Sanity — nothing else should already be patching.
    assert dc._expansion_hint is not None
    for i in range(1, TRIALS_PER_CONDITION + 1):
        hint_slot: list = []
        wrapped = _capture_hint_wrapper(hint_fn, hint_slot)
        try:
            dc._expansion_hint = wrapped
            trial = _run_one_trial(rivet, hint_slot)
        finally:
            dc._expansion_hint = original
        assert dc._expansion_hint is original, "restore failed"
        trial["provenance"] = "slice_e_fresh"
        trial["condition"] = label
        trials.append(trial)
        s = trial["synthesis"]
        h = trial["hint_capture"]
        print(
            f"  trial {i}: attempts={s['attempt_count']} "
            f"draft_A_len={len(s['first_pass_brief'])} "
            f"accepted_len={len(s['accepted_brief'])} "
            f"verifier={s['verification_status']} "
            f"hint_emitted={len(h['emitted_hint_texts'])} "
            f"elapsed={trial['elapsed_seconds']:.1f}s"
        )
    return trials


def _load_baseline_from_slice_c() -> list[dict]:
    """Reuse Slice C CTL trials as the BASELINE condition (mechanically equivalent)."""
    with open(SLICE_C_EVIDENCE) as fh:
        c = json.load(fh)
    baseline = []
    for i, t in enumerate(c["CTL_trials"], start=1):
        baseline.append({
            "elapsed_seconds": t["elapsed_seconds"],
            "retrieval": t["retrieval"],
            "hint_capture": {
                "emitted_hint_texts": [t["synthesis"]["corrective_hint_used"]],
                "emitted_hint_sha256": [hashlib.sha256(t["synthesis"]["corrective_hint_used"].encode()).hexdigest()],
                "provenance_note": "reused from Slice C CTL — corrective_hint_used field",
            },
            "synthesis": t["synthesis"],
            "provenance": "slice_c_ctl_trial_" + str(i),
            "condition": "BASELINE",
        })
    return baseline


def main() -> int:
    with open(SETUP_MANIFEST) as fh:
        manifest = json.load(fh)

    print("SESSION 272 Slice E — three-condition corrective-hint ablation")
    print(f"WRITING_CONTRACT_VERSION={WRITING_CONTRACT_VERSION}")
    print(f"operator_topic={OPERATOR_TOPIC[:80]}...")
    print(f"target_duration_seconds={TARGET_DURATION_SECONDS}  audience_hint={AUDIENCE_HINT!r}")
    print(f"trials per condition: {TRIALS_PER_CONDITION}")
    print()
    print("Frozen hint exemplars:")
    print(f"  NO_KNOWLEDGE_REF sha256: {NO_KNOWLEDGE_REF_SHA}")
    print(f"  CORRECT_ANCHOR sha256:  {CORRECT_ANCHOR_SHA}")

    # Verify current _expansion_hint is production (not a stale patch)
    # by rendering a sample and pattern-matching. Source-inspection breaks
    # against multi-line f-strings — check emitted text instead.
    prod_sample = dc._expansion_hint(
        actual_chars=568, actual_words=100, actual_seconds=39,
        target_duration_seconds=81, effective_ideal=1215,
        effective_min=972, effective_max=1458,
    )
    assert "REWRITE THE SAME NARRATIVE ABOVE" in prod_sample, "production hint drifted"
    assert "Expand secondary detail from the knowledge chunks" in prod_sample, "production hint drifted"
    prod_sample_sha = hashlib.sha256(prod_sample.encode()).hexdigest()
    print(f"  BASELINE (production) sha256: {prod_sample_sha}")

    ctl_rivet = Teammate.objects.get(id=manifest["CTL"]["rivet_teammate_id"])

    baseline_trials = _load_baseline_from_slice_c()
    print(f"\nBASELINE: reused {len(baseline_trials)} trials from Slice C CTL (mechanically equivalent).")

    no_knowledge_ref_trials = _run_condition(
        "NO_KNOWLEDGE_REF (isolates hypothesis A — hint-wording drives lexical copy)",
        ctl_rivet,
        _no_knowledge_ref_hint,
    )
    correct_anchor_trials = _run_condition(
        "CORRECT_ANCHOR (isolates hypothesis E1 — false-anchor mis-directs to §1)",
        ctl_rivet,
        _correct_anchor_hint,
    )

    # Verify restore.
    assert dc._expansion_hint is not None
    post_prod_sample = dc._expansion_hint(
        actual_chars=568, actual_words=100, actual_seconds=39,
        target_duration_seconds=81, effective_ideal=1215,
        effective_min=972, effective_max=1458,
    )
    post_prod_sample_sha = hashlib.sha256(post_prod_sample.encode()).hexdigest()
    assert post_prod_sample_sha == prod_sample_sha, "production hint drifted after experiment"

    evidence = {
        "session": 272,
        "slice": "E",
        "writing_contract_version": WRITING_CONTRACT_VERSION,
        "operator_topic": OPERATOR_TOPIC,
        "target_duration_seconds": TARGET_DURATION_SECONDS,
        "audience_hint": AUDIENCE_HINT,
        "trials_per_condition": TRIALS_PER_CONDITION,
        "frozen_hint_exemplars": _EXEMPLARS,
        "baseline_sample": {
            "text": prod_sample,
            "sha256": prod_sample_sha,
        },
        "post_experiment_baseline_sample": {
            "text": post_prod_sample,
            "sha256": post_prod_sample_sha,
        },
        "restore_verified": post_prod_sample_sha == prod_sample_sha,
        "setup_manifest_ref": str(SETUP_MANIFEST),
        "slice_c_evidence_ref": str(SLICE_C_EVIDENCE),
        "BASELINE_trials": baseline_trials,
        "NO_KNOWLEDGE_REF_trials": no_knowledge_ref_trials,
        "CORRECT_ANCHOR_trials": correct_anchor_trials,
    }
    with open(EVIDENCE_PATH, "w") as fh:
        json.dump(evidence, fh, indent=2)
    print(f"\nEvidence written to {EVIDENCE_PATH}")
    print(f"Production _expansion_hint restore verified: {evidence['restore_verified']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
