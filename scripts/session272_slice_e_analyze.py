"""SESSION 272 Slice E — 3-condition aggregate analysis.

Reads `04_slice_e_ablation_evidence.json` and scores each trial using
the Slice C 3-category classifier (canonical / paraphrase-supplied /
accessible model-generated). Aggregates per condition and prints a
comparison table.

Also produces a factual-grounding audit:
  * K6.4 verifier warning counts per Draft B
  * Rivet identity marker counts
  * Attractor `where the behavior first becomes incorrect` freq
  * Cross-condition qualitative flags (invented facts / dropped facts)

Writes:
  docs/design/session_272_experiment_data/05_slice_e_aggregate_analysis.json
  docs/design/session_272_experiment_data/05_slice_e_aggregate_summary.txt
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

# Reuse the Slice C classifier — same concept table, same regex catalog.
from session272_slice_c_analyze import CONCEPTS, RIVET_IDENTITY_MARKERS, _score_text, _score_identity  # noqa: E402


EVIDENCE_PATH = Path("docs/design/session_272_experiment_data/04_slice_e_ablation_evidence.json")
ANALYSIS_PATH = Path("docs/design/session_272_experiment_data/05_slice_e_aggregate_analysis.json")
SUMMARY_PATH = Path("docs/design/session_272_experiment_data/05_slice_e_aggregate_summary.txt")

CONDITION_KEYS = ["BASELINE_trials", "NO_KNOWLEDGE_REF_trials", "CORRECT_ANCHOR_trials"]
CONDITION_LABELS = {
    "BASELINE_trials": "BASELINE",
    "NO_KNOWLEDGE_REF_trials": "NO_KNOWLEDGE_REF",
    "CORRECT_ANCHOR_trials": "CORRECT_ANCHOR",
}


def _totals(per_concept: dict) -> dict:
    return {
        "canonical_total": sum(v["canonical"] for v in per_concept.values()),
        "paraphrase_total": sum(v["paraphrase"] for v in per_concept.values()),
        "accessible_total": sum(v["accessible"] for v in per_concept.values()),
        "attractor_where_incorrect": per_concept["where_incorrect"]["canonical"],
    }


def analyze():
    with open(EVIDENCE_PATH) as fh:
        ev = json.load(fh)
    aggregate = {}
    for key in CONDITION_KEYS:
        label = CONDITION_LABELS[key]
        aggregate[label] = []
        for i, trial in enumerate(ev[key], start=1):
            syn = trial["synthesis"]
            draft_a = syn["first_pass_brief"]
            draft_b = syn["accepted_brief"]
            score_a = _score_text(draft_a)
            score_b = _score_text(draft_b)
            totals_a = _totals(score_a)
            totals_b = _totals(score_b)
            identity_a = _score_identity(draft_a)
            identity_b = _score_identity(draft_b)
            retrieval = trial["retrieval"]["scored_chunks"][0] if trial["retrieval"]["scored_chunks"] else None
            aggregate[label].append({
                "trial": i,
                "provenance": trial.get("provenance", "unknown"),
                "attempt_count": syn["attempt_count"],
                "verification_status": syn["verification_status"],
                "verification_warnings_count": len(syn.get("verification_warnings", [])),
                "draft_a_len": len(draft_a),
                "draft_b_len": len(draft_b),
                "retrieval_distance": retrieval["distance"] if retrieval else None,
                "hint_emitted_sha256": trial.get("hint_capture", {}).get("emitted_hint_sha256", []),
                "draft_a": {"per_concept": score_a, "totals": totals_a, "identity_markers": identity_a},
                "draft_b": {"per_concept": score_b, "totals": totals_b, "identity_markers": identity_b},
            })

    def dist(label, draft_key, field):
        return [t[draft_key]["totals"][field] for t in aggregate[label]]

    def identity_count(label, draft_key):
        return [len(t[draft_key]["identity_markers"]) for t in aggregate[label]]

    def attractor_freq(label, draft_key):
        return sum(1 for t in aggregate[label] if t[draft_key]["totals"]["attractor_where_incorrect"] > 0)

    def warnings(label):
        return [t["verification_warnings_count"] for t in aggregate[label]]

    def verified_count(label):
        return sum(1 for t in aggregate[label] if t["verification_status"] == "verified")

    def draft_len(label):
        return [(t["draft_a_len"], t["draft_b_len"]) for t in aggregate[label]]

    summary = {"trials_per_condition": len(aggregate["BASELINE"]), "distributions": {}, "verdict_inputs": {}}
    for label in ("BASELINE", "NO_KNOWLEDGE_REF", "CORRECT_ANCHOR"):
        summary["distributions"][label] = {
            "draft_a_canonical": dist(label, "draft_a", "canonical_total"),
            "draft_b_canonical": dist(label, "draft_b", "canonical_total"),
            "draft_a_accessible": dist(label, "draft_a", "accessible_total"),
            "draft_b_accessible": dist(label, "draft_b", "accessible_total"),
            "draft_b_paraphrase": dist(label, "draft_b", "paraphrase_total"),
            "identity_markers_draft_b": identity_count(label, "draft_b"),
            "verification_warnings": warnings(label),
            "draft_lens": draft_len(label),
            "verified": verified_count(label),
        }
        summary["verdict_inputs"][label] = {
            "attractor_where_incorrect_freq_draft_a": attractor_freq(label, "draft_a"),
            "attractor_where_incorrect_freq_draft_b": attractor_freq(label, "draft_b"),
        }

    ANALYSIS_PATH.write_text(json.dumps({"trials": aggregate, "summary": summary}, indent=2))

    lines = []
    lines.append("SESSION 272 Slice E — 3-condition aggregate summary")
    lines.append("=" * 72)
    lines.append(f"Trials per condition: {summary['trials_per_condition']}")
    lines.append("")
    for label in ("BASELINE", "NO_KNOWLEDGE_REF", "CORRECT_ANCHOR"):
        d = summary["distributions"][label]
        v = summary["verdict_inputs"][label]
        lines.append(f"--- {label} ---")
        lines.append(f"  Draft A canonical:            {d['draft_a_canonical']}   mean={statistics.mean(d['draft_a_canonical']):.2f} median={statistics.median(d['draft_a_canonical'])}")
        lines.append(f"  Draft B canonical (ACCEPTED): {d['draft_b_canonical']}   mean={statistics.mean(d['draft_b_canonical']):.2f} median={statistics.median(d['draft_b_canonical'])}")
        lines.append(f"  Draft A accessible:           {d['draft_a_accessible']}   mean={statistics.mean(d['draft_a_accessible']):.2f} median={statistics.median(d['draft_a_accessible'])}")
        lines.append(f"  Draft B accessible (ACCEPTED):{d['draft_b_accessible']}   mean={statistics.mean(d['draft_b_accessible']):.2f} median={statistics.median(d['draft_b_accessible'])}")
        lines.append(f"  Draft B paraphrase-supplied:  {d['draft_b_paraphrase']}   mean={statistics.mean(d['draft_b_paraphrase']):.2f} median={statistics.median(d['draft_b_paraphrase'])}")
        lines.append(f"  Attractor 'where the behavior first becomes incorrect' freq in Draft B: {v['attractor_where_incorrect_freq_draft_b']}/{summary['trials_per_condition']}")
        lines.append(f"  Attractor freq in Draft A: {v['attractor_where_incorrect_freq_draft_a']}/{summary['trials_per_condition']}")
        lines.append(f"  Identity markers per Draft B: {d['identity_markers_draft_b']}   mean={statistics.mean(d['identity_markers_draft_b']):.2f}")
        lines.append(f"  Verification warnings (K6.4): {d['verification_warnings']}   sum={sum(d['verification_warnings'])}  mean={statistics.mean(d['verification_warnings']):.2f}")
        lines.append(f"  Draft lengths (A, B): {d['draft_lens']}")
        lines.append(f"  Verified: {d['verified']}/{summary['trials_per_condition']}")
        lines.append("")

    lines.append("--- Cross-condition comparisons ---")
    def delta(cond_a, cond_b, field):
        a = statistics.mean(summary["distributions"][cond_a][field])
        b = statistics.mean(summary["distributions"][cond_b][field])
        return (a, b, b - a)
    for field in ("draft_b_canonical", "draft_b_accessible", "identity_markers_draft_b"):
        a1, a2, delta1 = delta("BASELINE", "NO_KNOWLEDGE_REF", field)
        b1, b2, delta2 = delta("BASELINE", "CORRECT_ANCHOR", field)
        c1, c2, delta3 = delta("NO_KNOWLEDGE_REF", "CORRECT_ANCHOR", field)
        lines.append(f"  {field}:")
        lines.append(f"    BASELINE mean={a1:.2f}  NO_KNOWLEDGE_REF mean={a2:.2f}  delta(NKR-BL)={delta1:+.2f}")
        lines.append(f"    BASELINE mean={b1:.2f}  CORRECT_ANCHOR mean={b2:.2f}  delta(CA-BL)={delta2:+.2f}")
        lines.append(f"    NKR mean={c1:.2f}  CA mean={c2:.2f}  delta(CA-NKR)={delta3:+.2f}")
    lines.append("")

    lines.append("--- Attractor frequency (Draft B) cross-condition ---")
    for label in ("BASELINE", "NO_KNOWLEDGE_REF", "CORRECT_ANCHOR"):
        lines.append(f"  {label}: {summary['verdict_inputs'][label]['attractor_where_incorrect_freq_draft_b']}/{summary['trials_per_condition']}")
    lines.append("")

    lines.append("--- K6.4 verifier warnings (per Draft B) cross-condition ---")
    for label in ("BASELINE", "NO_KNOWLEDGE_REF", "CORRECT_ANCHOR"):
        w = summary["distributions"][label]["verification_warnings"]
        lines.append(f"  {label}: total={sum(w)}  mean={statistics.mean(w):.2f}  values={w}")

    out = "\n".join(lines)
    SUMMARY_PATH.write_text(out)
    print(out)


if __name__ == "__main__":
    analyze()
