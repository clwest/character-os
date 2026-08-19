# SESSION 267 §5.5 — Disposition

## Aggregate result

3 attempts, 18 total Patch turns, **0 LEAK / 0 AMBIGUOUS / 18 CLEAN**.

Retrieval verified pre-attempt (preflight snapshot) and post-attempt
(DialogueResult.memory_ids) for every attempt: `c86d4902` won
`top_k=1` on every run, distance 0.3144 (matches §13.10 landscape
exactly — the T1 topic is deterministic in cosine geometry).

Full per-turn scoring: `08_scoring.md`. Raw per-attempt outputs:
`07_attempt_1.json`, `07_attempt_2.json`, `07_attempt_3.json`.

## Pre-registered §5.5 decision rule application

Rule verbatim (Chris's SESSION 267 experiment message):

> 0/3 LEAK + 3/3 CLEAN → Semantic 1 sufficient in practice for
> this stress test; proceed toward UI relabel analysis.

**Applies.** Zero Patch turns demonstrated knowledge of any of the
four locked leak surfaces (`"PATCH OVERRIDES"` name, folder existence,
tracking-of-ignored-recommendations, Rivet's discovery/withholding)
in advance of legitimate in-scene disclosure by Rivet.

## What the experiment actually settled

**The falsifiable question (Q267.1 from §4):**

> *Given a Rivet-only NarrativeMemory that encodes an observation
> Patch cannot plausibly have witnessed, does a subsequent
> Patch+Rivet render — under the current production prompt,
> retrieval, and top_k=1 — cause Patch to narrate, quote, or act
> on the memory's content as if he knew it?*

**Answer, bounded by n=3 on the T1 cue against `c86d4902`:** NO —
Patch never leaked in any attempt.

## What the experiment did NOT settle

- Whether leakage would occur on a different cue topic (T2–T5
  untested; ChatGPT + Chris explicitly approved T1 only).
- Whether leakage would occur under a different private memory
  body wording.
- Whether operators intuitively read *"Who remembers this?"* as
  Semantic 1 or Semantic 2 (SESSION 266 §14.10 item 2 remains
  open — this experiment addresses the runtime side of the
  mismatch, not the operator-intuition side).
- Whether the writer's emergent character-attribution instinct
  (Attempt 1's Rivet-side disclosure — §"Notable secondary
  finding" below) is reliable at scale.

## Notable secondary finding — Rivet-side disclosure

Attempt 1 ended with Rivet spontaneously disclosing two of the
four private surfaces verbatim:

> *"Then you may want to inspect its folder called 'PATCH
> OVERRIDES.' It appears to have opinions about which suggestions
> you ignored."*

This is not a Patch leak (Patch has no reaction turn — Rivet
gets the last word). It IS an interesting emergent behavior:
even under Semantic 1's cast-wide prompt framing (§14.2 code
trace confirmed the prompt carries no witness attribution), the
writer picked the WITNESS to voice the memory content in 1/3
attempts.

Interpretation options for this observation (not chosen by this
disposition; documented for later analysis):

- **Emergent story-sense.** The writer inferred from context
  (Rivet's voice, workshop-audit content, "ignored
  recommendations" phrasing that fits Rivet's methodical
  observing role) that Rivet should be the one to voice this.
  Under this reading, Semantic 1 works in practice because good
  writers naturally attribute in-scene.
- **Coincidence / sampling.** 1/3 is not statistically decisive.
  Attempts 2 and 3 had Rivet not disclose at all. The writer's
  behavior is stochastic; the observation says nothing about
  what would happen with a different memory or cue.
- **Confirmatory rather than causal.** Rivet-side disclosure may
  happen for reasons unrelated to witness attribution —
  narrative rhythm, scene-ending punch line, etc.

These interpretations are OPEN. Not resolved by the SESSION 267
data.

## Downstream implications (per pre-registered branch)

The 0/3-LEAK-3/3-CLEAN branch of §5.5 says: "*proceed toward UI
relabel analysis.*" That analysis is:

- The UI label *"Who remembers this?"* implies Semantic 2
  (character-specific knowledge / character attribution).
- The runtime delivers Semantic 1 (visibility/eligibility
  filter) — verified by SESSION 266 §14.2 code trace + this
  experiment's runtime evidence.
- Under the T1 stress test, Semantic 1 was sufficient — Patch
  never violated the private-knowledge boundary in 18 Patch
  turns.
- Therefore the **UI relabel is the smallest correction that
  aligns advertised semantics with delivered runtime behavior**
  — cheaper and safer than a prompt/schema change that this
  experiment did not justify.

**No implementation authorized by this disposition.** UI relabel
analysis is a subsequent session's work; this disposition only
records that the leakage-fix branch (prompt change) is no longer
justified by evidence, and the relabel branch is now the
supported next investigation.

## Scope-lock adherence

All SESSION 267 scope locks (§8 of the audit doc) held throughout
this experiment:

- `top_k` unchanged (production 1).
- Retrieval predicate unchanged.
- Production synthesis prompt unchanged (no monkey-patch overrode
  the prompt this experiment; the "harness" bypassed only the
  Celery/media pipeline, not the prompt).
- Witness semantics unchanged.
- UI copy unchanged.
- Canon unchanged.
- No modifications to any of the 7 active memories.
- No new schema, no new models, no new memory kinds.
- No Runway dispatch (synthesis-only path, real GPT-5.6-terra
  only).

## STOP point

Per Chris's SESSION 267 experiment message:

> Do NOT implement any correction yet, regardless of outcome.
> STOP after scoring + disposition and report the results to
> Chris.
> Do not commit/push or close SESSION 267 yet. Chris + ChatGPT
> will review the evidence first.

**Halted here.** SESSION 267 evidence is complete; waiting on
Chris + ChatGPT review of the raw dialogues, per-turn scoring,
this disposition, and the audit-doc §14 update before any
follow-up action.
