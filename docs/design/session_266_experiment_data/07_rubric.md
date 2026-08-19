# SESSION 266 — Locked scoring rubric

Locked per §7.6 of `SESSION_266_NARRATIVE_MEMORY_PROMOTION_QUALITY_AUDIT.md`.
**Do not modify after seeing scored outputs.**

Locked test topic (identical across all six attempts):

> *"Patch runs a small experiment on the workshop agent."*

Retrieved memory body: **HIDDEN** during scoring. The scorer must
not consult `06_blind_manifest.json` or `05_attempt_*.json` files.

Each attempt is scored under six criteria on a tri-value scale:

- **0.0** = FAIL
- **0.5** = PARTIAL
- **1.0** = PASS

Maximum per attempt = 6.0.

| # | Criterion | PASS (1.0) | PARTIAL (0.5) | FAIL (0.0) |
|---|---|---|---|---|
| C1 | **Assumes prior events rather than re-explaining them** | Opens without recap; treats the memory event as background the cast already knows happened; no "as I told you earlier" / "I gave the agent…" setup restatement | Some assumption, some restatement | Explicit restatement / recap of the memory event as if the reader hasn't seen it |
| C2 | **Current conflict is motivated by remembered history** | Patch's frustration or Rivet's question is directly caused by a specific prior event | Conflict is present but caused by generic character behavior (Patch is scattered / Rivet is methodical) | Conflict is unrelated to any prior event |
| C3 | **Progresses/escalates rather than merely repeats the remembered event** | Introduces a genuinely new beat downstream of the retrieved memory (new agent behavior, new investigation step, new information revealed) | Elaborates the memory event with more detail but doesn't advance it | Restates the memory event in different words |
| C4 | **Preserves Patch/Rivet character behavior** | Patch's energetic-frustration + colorful naming voice ✓ AND Rivet's hypothesis-first + methodology voice ✓ | One of the two voices lands; the other feels generic | Neither voice lands |
| C5 | **Introduces no contradiction with canon or remembered history** | No line contradicts the retrieved memory OR any Universe canon fact | Ambiguous line that could be read as contradiction | Explicit contradiction |
| C6 | **Feels like the next Episode rather than an isolated sketch** | Reads as continuation; "again", "still", "this time" or equivalent carry-forward language present or clearly implied | Self-contained follow-up feel; carry-forward implied but not signaled | Reads as a standalone scene with no prior-Episode dependency |

## Scoring procedure

1. Read `06_blind_dialogues.md`. Do NOT read `06_blind_manifest.json`
   or any `05_attempt_*.json`.
2. Score each attempt A–F under all six criteria. Record concrete
   textual evidence (line-level quotes) supporting the score.
3. Record scores in `08_blind_scores.md`. Include reasoning per
   criterion.
4. Once all six attempts are scored, `08_reveal_and_aggregate.py`
   opens the blind manifest and computes per-variant aggregates.

## Decision rules (also locked per §7.6)

Let `W_mean` = mean of the three Weak attempt total scores;
`S_mean` = mean of the three Strong attempt total scores. Each ∈
[0.0, 6.0].

1. **Provisionally supported:** `S_mean - W_mean >= 1.5` AND the
   difference holds direction-consistently (S >= W) on ≥ 4 of 6
   criteria.
2. **Provisionally rejected under this condition:**
   `|S_mean - W_mean| < 0.5` AND no criterion shows a
   direction-consistent gap ≥ 1.0.
3. **Inconclusive:** neither of the above → expand sample size per
   §7.4 trigger.

## Retrieval-geometry cosine distances (informational only)

Captured pre-experiment in `04_preflight.json`:

- WEAK memory ↔ locked topic: **0.4490**
- STRONG memory ↔ locked topic: **0.4576**
- Δ = 0.009 (W marginally closer)

Reported separately from synthesis contribution. Since each Universe
contains exactly one eligible memory, top_k=1 retrieves the intended
variant in either case regardless of distance.
