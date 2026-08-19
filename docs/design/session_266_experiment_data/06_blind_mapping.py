"""SESSION 266 — Create the blind evaluation manifest.

Reads the six raw attempt sidecars, randomizes their order under a
documented seed, and writes two files:

* 06_blind_manifest.json  — hidden mapping A..F → (variant, attempt_no).
  This file is the reproducibility anchor; it exists BEFORE scoring
  but must not be consulted during scoring.
* 06_blind_dialogues.md   — the six dialogues under neutral labels
  A..F only. Contains the synthesized_brief text, target duration,
  and cast names — but hides variant, memory body, memory id,
  cosine distance, universe id, and any label that could leak W/S.

Randomization seed is fixed so the mapping is reproducible.
"""
import glob
import json
import random

SEED = 266_20260818  # deterministic; documented in the manifest
RNG = random.Random(SEED)

paths = sorted(glob.glob(
    "../docs/design/session_266_experiment_data/05_attempt_*.json"
))
attempts = []
for p in paths:
    with open(p) as fh:
        data = json.load(fh)
    if data.get("outcome") != "accepted":
        print(f"  SKIPPING rejected attempt: {p}")
        continue
    attempts.append(data)

assert len(attempts) == 6, f"expected 6 accepted attempts, got {len(attempts)}"

# Shuffle
order = list(range(len(attempts)))
RNG.shuffle(order)
labels = ["A", "B", "C", "D", "E", "F"]

manifest = {
    "seed": SEED,
    "created_by": "docs/design/session_266_experiment_data/06_blind_mapping.py",
    "note": (
        "Hidden W/S provenance. DO NOT open this file during scoring. "
        "Scorer works from 06_blind_dialogues.md and 07_rubric.md only."
    ),
    "mapping": [],
}

for label, idx in zip(labels, order):
    a = attempts[idx]
    manifest["mapping"].append({
        "label": label,
        "variant": a["variant"],
        "attempt_no": a["attempt_no"],
        "source_file": f"05_attempt_{a['variant']}_{a['attempt_no']}.json",
        "universe_id": a["universe_id"],
        "workspace_id": a["workspace_id"],
        "memory_id": a["memory"]["memory_id"],
        "cosine_distance": a["preflight_cosine_distance"],
        "attempt_count": a["attempt_count"],
        "predicted_seconds": a["predicted_seconds"],
        "total_chars": a["total_chars"],
        "n_turns": len(a["turns"]),
        "verification_status": a["overall_verification_status"],
    })

with open(
    "../docs/design/session_266_experiment_data/06_blind_manifest.json",
    "w",
) as fh:
    json.dump(manifest, fh, indent=2)

# Write the neutral, variant-stripped dialogue set
md_lines = [
    "# SESSION 266 — Blinded dialogues for scoring",
    "",
    "Six attempts, order randomized under seed documented in "
    "`06_blind_manifest.json`. Each attempt is presented under a "
    "neutral label (A–F). W/S provenance is hidden; do not open "
    "`06_blind_manifest.json` until scoring is complete.",
    "",
    "Locked test topic (identical for all six attempts):",
    "",
    "> *\"Patch runs a small experiment on the workshop agent.\"*",
    "",
    "Target duration: 90 s. Cast: Patch, Rivet. Writing contract v4. "
    "Model: gpt-5.6-terra. NarrativeMemory retrieval: top_k=1 "
    "(unchanged).",
    "",
    "Score each attempt against the rubric in "
    "`07_rubric.md`. Do NOT modify the rubric after seeing outputs.",
    "",
    "---",
    "",
]

for label, idx in zip(labels, order):
    a = attempts[idx]
    md_lines.append(f"## Attempt {label}")
    md_lines.append("")
    md_lines.append(a["synthesized_brief"])
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

with open(
    "../docs/design/session_266_experiment_data/06_blind_dialogues.md",
    "w",
) as fh:
    fh.write("\n".join(md_lines))

print(f"Wrote blind manifest with {len(labels)} entries")
print(f"Blinded label order (variants hidden):")
for label in labels:
    print(f"  {label}: <hidden>")
