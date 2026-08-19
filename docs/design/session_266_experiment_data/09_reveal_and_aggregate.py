"""SESSION 266 — Reveal blind mapping and compute W/S aggregates.

Read scores from 08_blind_scores.md by parsing the totals table.
Read mapping from 06_blind_manifest.json.
Merge and compute per-variant aggregate against locked decision rules
in 07_rubric.md.
"""
import json
import re
from statistics import mean

# --- Blinded per-criterion scores (hardcoded from 08_blind_scores.md
#     to make this script self-checkable; verified against md by eye)
BLIND_SCORES = {
    "A": {"C1": 0.5, "C2": 1.0, "C3": 1.0, "C4": 1.0, "C5": 0.5, "C6": 1.0},
    "B": {"C1": 1.0, "C2": 1.0, "C3": 1.0, "C4": 1.0, "C5": 1.0, "C6": 1.0},
    "C": {"C1": 0.0, "C2": 0.0, "C3": 1.0, "C4": 1.0, "C5": 1.0, "C6": 0.5},
    "D": {"C1": 0.5, "C2": 0.5, "C3": 1.0, "C4": 1.0, "C5": 1.0, "C6": 0.5},
    "E": {"C1": 0.5, "C2": 0.0, "C3": 1.0, "C4": 1.0, "C5": 1.0, "C6": 0.0},
    "F": {"C1": 1.0, "C2": 1.0, "C3": 1.0, "C4": 1.0, "C5": 1.0, "C6": 1.0},
}

with open(
    "../docs/design/session_266_experiment_data/06_blind_manifest.json"
) as fh:
    manifest = json.load(fh)

# label → variant
label_to_variant: dict[str, dict] = {}
for entry in manifest["mapping"]:
    label_to_variant[entry["label"]] = entry

reveal_rows: list[dict] = []
for label in sorted(BLIND_SCORES):
    entry = label_to_variant[label]
    scores = BLIND_SCORES[label]
    total = sum(scores.values())
    reveal_rows.append({
        "label": label,
        "variant": entry["variant"],
        "attempt_no": entry["attempt_no"],
        "attempt_count": entry["attempt_count"],
        "n_turns": entry["n_turns"],
        "predicted_seconds": entry["predicted_seconds"],
        "total_chars": entry["total_chars"],
        "cosine_distance": entry["cosine_distance"],
        "scores": scores,
        "total": total,
    })

# Aggregates per variant
weak_totals = [r["total"] for r in reveal_rows if r["variant"] == "WEAK"]
strong_totals = [r["total"] for r in reveal_rows if r["variant"] == "STRONG"]

W_mean = mean(weak_totals)
S_mean = mean(strong_totals)
delta = S_mean - W_mean

# Per-criterion means
crit_means = {}
for crit in ["C1", "C2", "C3", "C4", "C5", "C6"]:
    w_c = mean(r["scores"][crit] for r in reveal_rows if r["variant"] == "WEAK")
    s_c = mean(r["scores"][crit] for r in reveal_rows if r["variant"] == "STRONG")
    crit_means[crit] = {"W": w_c, "S": s_c, "delta": s_c - w_c}

# Decision rules (locked in 07_rubric.md §Decision rules)
direction_consistent = sum(1 for c in crit_means.values() if c["delta"] > 0)
any_direction_consistent_ge_1 = any(abs(c["delta"]) >= 1.0 for c in crit_means.values())

if delta >= 1.5 and direction_consistent >= 4:
    disposition = "PROVISIONALLY SUPPORTED"
elif abs(delta) < 0.5 and not any_direction_consistent_ge_1:
    disposition = "PROVISIONALLY REJECTED under this condition"
else:
    disposition = "INCONCLUSIVE — expand sample size per §7.4 trigger"

# Ranking helpers
sorted_by_total = sorted(
    reveal_rows, key=lambda r: r["total"], reverse=True
)

report = {
    "seed": manifest["seed"],
    "per_attempt": reveal_rows,
    "W_totals": weak_totals,
    "S_totals": strong_totals,
    "W_mean": W_mean,
    "S_mean": S_mean,
    "delta_S_minus_W": delta,
    "criterion_means": crit_means,
    "direction_consistent_criteria": direction_consistent,
    "any_criterion_delta_ge_1": any_direction_consistent_ge_1,
    "disposition": disposition,
    "ranking_high_to_low": [
        {"label": r["label"], "variant": r["variant"],
         "attempt_no": r["attempt_no"], "total": r["total"]}
        for r in sorted_by_total
    ],
}

with open(
    "../docs/design/session_266_experiment_data/09_reveal.json",
    "w",
) as fh:
    json.dump(report, fh, indent=2)

# Human-readable markdown
lines = [
    "# SESSION 266 — Reveal & aggregate",
    "",
    f"Blind seed: `{manifest['seed']}`. Mapping opened at reveal time.",
    "",
    "## Per-attempt reveal",
    "",
    "| Label | Variant | Attempt | Turns | Chars | Predicted (s) | Attempts | Cosine | Total |",
    "|---|---|---|---|---|---|---|---|---|",
]
for r in reveal_rows:
    lines.append(
        f"| {r['label']} | **{r['variant']}** | {r['attempt_no']} | "
        f"{r['n_turns']} | {r['total_chars']} | {r['predicted_seconds']:.2f} | "
        f"{r['attempt_count']} | {r['cosine_distance']:.4f} | **{r['total']}** |"
    )

lines += [
    "",
    "## Per-criterion aggregate",
    "",
    "| Criterion | Weak mean | Strong mean | Δ (S − W) |",
    "|---|---|---|---|",
]
for crit, m in crit_means.items():
    lines.append(
        f"| {crit} | {m['W']:.3f} | {m['S']:.3f} | {m['delta']:+.3f} |"
    )

lines += [
    "",
    "## Aggregates",
    "",
    f"- **Weak totals:** {weak_totals}",
    f"- **Strong totals:** {strong_totals}",
    f"- **W_mean = {W_mean:.3f}**",
    f"- **S_mean = {S_mean:.3f}**",
    f"- **Δ (S − W) = {delta:+.3f}**",
    f"- Criteria where S ≥ W: **{direction_consistent} of 6**",
    f"- Any criterion with |Δ| ≥ 1.0: **{any_direction_consistent_ge_1}**",
    "",
    "## Disposition (locked decision rules from §7.6)",
    "",
    f"### **{disposition}**",
    "",
    "## Ranking",
    "",
    "| Rank | Label | Variant | Total |",
    "|---|---|---|---|",
]
for i, r in enumerate(sorted_by_total, 1):
    lines.append(
        f"| {i} | {r['label']} | {r['variant']} | {r['total']} |"
    )

with open(
    "../docs/design/session_266_experiment_data/09_reveal.md",
    "w",
) as fh:
    fh.write("\n".join(lines))

print("=== REVEAL COMPLETE ===")
print(f"W_totals: {weak_totals} → mean {W_mean:.3f}")
print(f"S_totals: {strong_totals} → mean {S_mean:.3f}")
print(f"Δ (S − W): {delta:+.3f}")
print(f"Direction-consistent criteria (S ≥ W): {direction_consistent}/6")
print(f"Any criterion |Δ| ≥ 1.0: {any_direction_consistent_ge_1}")
print(f"\nDISPOSITION: {disposition}")
print(f"\nRanking:")
for i, r in enumerate(sorted_by_total, 1):
    print(f"  {i}. {r['label']} ({r['variant']}#{r['attempt_no']}): {r['total']}")
