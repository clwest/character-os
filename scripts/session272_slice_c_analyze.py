"""SESSION 272 Slice C — aggregate analysis.

Loads the multi-shot evidence sidecar and computes per-concept:

  1. Raw canonical enumeration matches (verbatim substrings from the
     canonical DEBUGGING chunk).
  2. Supplied Option D paraphrase matches (verbatim substrings from
     the paired paraphrase paragraph — only physically present in EXP).
  3. Model-generated accessible expressions (regex-defined semantic
     equivalents that appear in NEITHER the canonical enumeration
     NOR the Option D paraphrase text).

For each Draft A and each Draft B in each trial, records per-concept
counts + Rivet identity markers + retrieval distance + verification
outcome. Emits an aggregate JSON sidecar + a plaintext summary table.

Rationale for category 3: Slice B §16.5 flagged that EXP Draft B contains
`What did I expect?` / `What actually appeared?` / `What changed since the
last result that looked right?` — accessible but neither canonical nor
supplied-paraphrase verbatim. Testing whether EXP substrate raises the
FREQUENCY of these third-form expressions is the emerging hypothesis
Slice C evaluates.

Usage:
  python scripts/session272_slice_c_analyze.py
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

EVIDENCE_PATH = Path("docs/design/session_272_experiment_data/02_slice_c_multishot_evidence.json")
ANALYSIS_PATH = Path("docs/design/session_272_experiment_data/03_slice_c_aggregate_analysis.json")
SUMMARY_PATH = Path("docs/design/session_272_experiment_data/03_slice_c_aggregate_summary.txt")


# Per-concept classifier.
# For each canonical enumeration concept, list:
#   canonical  — verbatim substrings from the canonical DEBUGGING chunk
#   paraphrase — verbatim substrings from the Option D paired paraphrase
#                paragraph (EXP-only)
#   accessible — regex patterns that catch model-generated third-form
#                accessible expressions. These MUST NOT overlap with
#                canonical or paraphrase substrings (verified below).
CONCEPTS: list[dict] = [
    {
        "id": "what_changed",
        "canonical": ["what changed"],
        "paraphrase": ["what changed since it worked"],
        "accessible": [
            r"\bwhat has changed\b",
            r"\bwhat did (we|i|you) change\b",
            r"\bwhat changed since\b",
            r"\bsince the last (result|run|time)\b",
        ],
    },
    {
        "id": "what_expected",
        "canonical": ["what was expected"],
        "paraphrase": ["what should have happened"],
        "accessible": [
            r"\bwhat (did|do) (i|we|you) expect\b",
            r"\bwhat was (i|we|you) expecting\b",
            r"\bwhat was supposed to happen\b",
            r"\bwhat did we think would happen\b",
            r"\bwhat outcome (i|we) expected\b",
        ],
    },
    {
        "id": "what_actually_happened",
        "canonical": ["what actually happened"],
        "paraphrase": ["what actually did"],
        "accessible": [
            r"\bwhat actually appeared\b",
            r"\bwhat did happen\b",
            r"\bwhat actually shows up\b",
            r"\bwhat we (got|saw) instead\b",
            r"\bwhat came out\b",
            r"\bwhat we ended up with\b",
        ],
    },
    {
        "id": "reproducibility",
        "canonical": ["whether the behavior can be reproduced"],
        "paraphrase": ["whether you can reproduce it"],
        "accessible": [
            r"\bcan (it|we|you) (make|do) (it|this) (happen )?again\b",
            r"\bcan (it|we|you) reproduce (it|this)\b",
            r"\bdoes it (happen|repeat) again\b",
            r"\bcan we make it happen again\b",
            r"\bwill it (happen|come out) again\b",
            r"\brun it again\b",
            r"\bhappen again\b",
        ],
    },
    {
        "id": "where_incorrect",
        "canonical": ["where the behavior first becomes incorrect"],
        "paraphrase": ["where the trouble starts"],
        "accessible": [
            r"\bwhere (it|things) (goes|go) wrong\b",
            r"\bwhere the problem (starts|begins)\b",
            r"\bat what point\b",
            r"\bwhere (it|the) (thing )?breaks\b",
            r"\bat which step\b",
            r"\bwhere (it|the) fail(s|ure) (starts|first)\b",
        ],
    },
    {
        "id": "evidence",
        "canonical": ["what evidence exists"],
        "paraphrase": ["what evidence you have"],
        "accessible": [
            r"\bwhat evidence (i|we|do i|do we) (have|see)\b",
            r"\bwhat evidence is there\b",
            r"\bhow much evidence\b",
            r"\bwhat proof (do i|do we) have\b",
        ],
    },
    {
        "id": "assumption",
        "canonical": ["what assumption might be wrong"],
        "paraphrase": ["what assumption might be wrong"],  # identical
        "accessible": [
            r"\bwhich assumption might be wrong\b",
            r"\bwhich of (my|our|your) assumptions\b",
            r"\bwhat (am i|are we) assuming\b",
            r"\bwhich assumption is off\b",
        ],
    },
    {
        "id": "smallest_test",
        "canonical": ["what smallest test would separate two possible explanations"],
        "paraphrase": ["what small test would settle it"],
        "accessible": [
            r"\b(smallest|one small|a small) test\b",
            r"\brun (the smallest|a small) test\b",
            r"\bthe (smallest|small) test\b",
        ],
    },
    # Non-question-item concepts that are still enumeration-adjacent:
    {
        "id": "one_variable_at_a_time",
        "canonical": [
            "one meaningful variable",
            "changing ten things at once",
        ],
        "paraphrase": [],  # not in paraphrase paragraph
        "accessible": [
            r"\bone (thing|variable) at a time\b",
            r"\bchange (just )?one (variable|thing)\b",
        ],
    },
    {
        "id": "evidence_beats_guessing",
        "canonical": ["evidence beats guessing"],
        "paraphrase": [],
        "accessible": [
            r"\bevidence (over|beats) guess",
            r"\blet the evidence\b",
        ],
    },
]

# Rivet identity markers (voice/worldview + signature phrasing).
RIVET_IDENTITY_MARKERS = [
    "evidence beats guessing",
    "meaningful variable",
    "reduce the problem",
    "smallest test",
    "one small test",
    "small test",
    "not a diagnosis",
    "dramatic hat",
    "suspicious hat",
    "decorative mysteries",
    "wearing a dramatic hat",
    "Patch",  # cross-character reference to Rivet's counterpart
    "workshop",
    "test again",
    "fluke",
]


def _score_text(text: str) -> dict:
    """Return {concept_id: {canonical, paraphrase, accessible}} for one draft.

    Blank-out order (highest specificity first) prevents double-counting:
      1. count canonical substrings → mask them
      2. count paraphrase substrings → mask them
      3. count accessible regex hits on the masked text → guaranteed
         disjoint from canonical + paraphrase
    """
    if text is None:
        text = ""
    per_concept: dict = {}
    # Work on a mutable copy that we blank out as we accumulate hits.
    residual = text
    # First: collect canonical + paraphrase hits + mask them, per concept.
    for concept in CONCEPTS:
        c_hits = 0
        for seed in concept["canonical"]:
            pattern = re.compile(re.escape(seed), re.IGNORECASE)
            c_hits += len(pattern.findall(residual))
            residual = pattern.sub(" _MASKED_ ", residual)
        p_hits = 0
        for seed in concept["paraphrase"]:
            pattern = re.compile(re.escape(seed), re.IGNORECASE)
            p_hits += len(pattern.findall(residual))
            residual = pattern.sub(" _MASKED_ ", residual)
        per_concept[concept["id"]] = {"canonical": c_hits, "paraphrase": p_hits, "accessible": 0}
    # Second: accessible regexes run on the residual (canonical + paraphrase already masked).
    for concept in CONCEPTS:
        a_hits = 0
        for regex in concept["accessible"]:
            a_hits += len(re.findall(regex, residual, flags=re.IGNORECASE))
        per_concept[concept["id"]]["accessible"] = a_hits
    return per_concept


def _score_identity(text: str) -> dict:
    text_low = (text or "").lower()
    return {m: text_low.count(m.lower()) for m in RIVET_IDENTITY_MARKERS if text_low.count(m.lower())}


def _totals(per_concept: dict) -> dict:
    return {
        "canonical_total": sum(v["canonical"] for v in per_concept.values()),
        "paraphrase_total": sum(v["paraphrase"] for v in per_concept.values()),
        "accessible_total": sum(v["accessible"] for v in per_concept.values()),
        # Attractor of interest — appears verbatim in the canonical chunk.
        "attractor_where_incorrect": per_concept["where_incorrect"]["canonical"],
    }


def _fmt_num(seq):
    if not seq:
        return "-"
    return f"{statistics.mean(seq):.2f} med={statistics.median(seq)} vals={seq}"


def analyze():
    with open(EVIDENCE_PATH) as fh:
        ev = json.load(fh)
    aggregate = {"CTL": [], "EXP": []}
    for cond in ("CTL", "EXP"):
        for i, trial in enumerate(ev[f"{cond}_trials"], start=1):
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
            aggregate[cond].append({
                "trial": i,
                "provenance": trial.get("provenance", "unknown"),
                "attempt_count": syn["attempt_count"],
                "verification_status": syn["verification_status"],
                "draft_a_len": len(draft_a),
                "draft_b_len": len(draft_b),
                "retrieval_distance": retrieval["distance"] if retrieval else None,
                "retrieval_chunk_id": retrieval["id"] if retrieval else None,
                "draft_a": {"per_concept": score_a, "totals": totals_a, "identity_markers": identity_a},
                "draft_b": {"per_concept": score_b, "totals": totals_b, "identity_markers": identity_b},
            })

    # Compute distributions
    def dist(cond, draft_key, field):
        return [t[draft_key]["totals"][field] for t in aggregate[cond]]

    def identity_count(cond, draft_key):
        return [len(t[draft_key]["identity_markers"]) for t in aggregate[cond]]

    def rd(cond):
        return [t["retrieval_distance"] for t in aggregate[cond]]

    def attempts(cond):
        return [t["attempt_count"] for t in aggregate[cond]]

    def verified_count(cond):
        return sum(1 for t in aggregate[cond] if t["verification_status"] == "verified")

    def attractor_freq(cond, draft_key):
        return sum(1 for t in aggregate[cond] if t[draft_key]["totals"]["attractor_where_incorrect"] > 0)

    def paraphrase_adoption_freq(cond, draft_key):
        return sum(1 for t in aggregate[cond] if t[draft_key]["totals"]["paraphrase_total"] > 0)

    summary = {
        "trials_per_condition": len(aggregate["CTL"]),
        "distributions": {},
        "verdict_inputs": {},
    }
    for cond in ("CTL", "EXP"):
        summary["distributions"][cond] = {
            "draft_a_canonical": dist(cond, "draft_a", "canonical_total"),
            "draft_b_canonical": dist(cond, "draft_b", "canonical_total"),
            "draft_a_paraphrase": dist(cond, "draft_a", "paraphrase_total"),
            "draft_b_paraphrase": dist(cond, "draft_b", "paraphrase_total"),
            "draft_a_accessible": dist(cond, "draft_a", "accessible_total"),
            "draft_b_accessible": dist(cond, "draft_b", "accessible_total"),
            "identity_markers_draft_b": identity_count(cond, "draft_b"),
            "retrieval_distance": rd(cond),
            "attempts": attempts(cond),
            "verified": verified_count(cond),
        }
        summary["verdict_inputs"][cond] = {
            "attractor_where_incorrect_freq_draft_a": attractor_freq(cond, "draft_a"),
            "attractor_where_incorrect_freq_draft_b": attractor_freq(cond, "draft_b"),
            "supplied_paraphrase_adoption_freq_draft_b": paraphrase_adoption_freq(cond, "draft_b"),
        }

    ANALYSIS_PATH.write_text(json.dumps({
        "trials": aggregate,
        "summary": summary,
    }, indent=2))

    # Human-readable summary
    lines = []
    lines.append("SESSION 272 Slice C — aggregate summary")
    lines.append("=" * 72)
    lines.append(f"Trials per condition: {summary['trials_per_condition']}")
    lines.append("")
    for cond in ("CTL", "EXP"):
        d = summary["distributions"][cond]
        v = summary["verdict_inputs"][cond]
        lines.append(f"--- {cond} ---")
        lines.append(f"  DRAFT A canonical (per-trial):     {d['draft_a_canonical']}   mean={statistics.mean(d['draft_a_canonical']):.2f} median={statistics.median(d['draft_a_canonical'])}")
        lines.append(f"  DRAFT A paraphrase-supplied:       {d['draft_a_paraphrase']}   mean={statistics.mean(d['draft_a_paraphrase']):.2f} median={statistics.median(d['draft_a_paraphrase'])}")
        lines.append(f"  DRAFT A accessible (model-gen):    {d['draft_a_accessible']}   mean={statistics.mean(d['draft_a_accessible']):.2f} median={statistics.median(d['draft_a_accessible'])}")
        lines.append(f"  DRAFT B canonical (per-trial):     {d['draft_b_canonical']}   mean={statistics.mean(d['draft_b_canonical']):.2f} median={statistics.median(d['draft_b_canonical'])}")
        lines.append(f"  DRAFT B paraphrase-supplied:       {d['draft_b_paraphrase']}   mean={statistics.mean(d['draft_b_paraphrase']):.2f} median={statistics.median(d['draft_b_paraphrase'])}")
        lines.append(f"  DRAFT B accessible (model-gen):    {d['draft_b_accessible']}   mean={statistics.mean(d['draft_b_accessible']):.2f} median={statistics.median(d['draft_b_accessible'])}")
        lines.append(f"  Attractor 'where the behavior first becomes incorrect' freq in Draft B: {v['attractor_where_incorrect_freq_draft_b']}/{summary['trials_per_condition']}")
        lines.append(f"  Attractor freq in Draft A: {v['attractor_where_incorrect_freq_draft_a']}/{summary['trials_per_condition']}")
        lines.append(f"  Supplied-paraphrase adoption freq (Draft B): {v['supplied_paraphrase_adoption_freq_draft_b']}/{summary['trials_per_condition']}")
        lines.append(f"  Identity markers per Draft B:      {d['identity_markers_draft_b']}   mean={statistics.mean(d['identity_markers_draft_b']):.2f}")
        lines.append(f"  Retrieval distance:                {[f'{x:.4f}' for x in d['retrieval_distance']]}   mean={statistics.mean(d['retrieval_distance']):.4f}")
        lines.append(f"  Attempts per trial:                {d['attempts']}")
        lines.append(f"  Verified: {d['verified']}/{summary['trials_per_condition']}")
        lines.append("")

    # Per-concept breakdown Draft B
    lines.append("--- Per-concept DRAFT B canonical hits (rows=CTL/EXP, cols=trials) ---")
    header = "  " + " ".join(f"{c['id']:<24}" for c in CONCEPTS)
    lines.append(header)
    for cond in ("CTL", "EXP"):
        cells = []
        for c in CONCEPTS:
            per_trial = [t["draft_b"]["per_concept"][c["id"]]["canonical"] for t in aggregate[cond]]
            cells.append(f"{sum(per_trial)}/{len(per_trial)}({','.join(str(x) for x in per_trial)})".ljust(24))
        lines.append(f"  {cond} " + " ".join(cells))
    lines.append("")

    lines.append("--- Per-concept DRAFT B accessible (model-gen) hits ---")
    lines.append(header)
    for cond in ("CTL", "EXP"):
        cells = []
        for c in CONCEPTS:
            per_trial = [t["draft_b"]["per_concept"][c["id"]]["accessible"] for t in aggregate[cond]]
            cells.append(f"{sum(per_trial)}/{len(per_trial)}({','.join(str(x) for x in per_trial)})".ljust(24))
        lines.append(f"  {cond} " + " ".join(cells))
    lines.append("")

    lines.append("--- Per-concept DRAFT B supplied-paraphrase hits (EXP-only if physical) ---")
    lines.append(header)
    for cond in ("CTL", "EXP"):
        cells = []
        for c in CONCEPTS:
            per_trial = [t["draft_b"]["per_concept"][c["id"]]["paraphrase"] for t in aggregate[cond]]
            cells.append(f"{sum(per_trial)}/{len(per_trial)}({','.join(str(x) for x in per_trial)})".ljust(24))
        lines.append(f"  {cond} " + " ".join(cells))
    lines.append("")

    out = "\n".join(lines)
    SUMMARY_PATH.write_text(out)
    print(out)


if __name__ == "__main__":
    analyze()
