# SESSION 267 — Handoff

Concise starting point for the next Character OS session. Full
context lives in
`docs/design/SESSION_266_NARRATIVE_MEMORY_PROMOTION_QUALITY_AUDIT.md`
(§1–§18). Read that BEFORE implementing anything.

Working method for this session (unchanged):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Persist important findings, audits, and decisions under
`docs/design/` before stopping.

---

## Current Character OS state (as of SESSION 266 close)

- Branch: `main`, clean tree at closeout.
- `NarrativeMemory` retrieval `top_k = 1` — unchanged.
- Production synthesis prompt in
  `shell/character_os/dialogue_synthesis.py` — unchanged.
- Retrieval predicate + witness eligibility filter
  (`shell/apps/embeddings/retrieval.py:499-536`) — unchanged.
- Canon boundary (`KnowledgeDocument` / `KnowledgeChunk`) —
  unchanged. Production Patch's Workshop canon
  `updated_at` static since 2026-08-18 T03:20:33 Z.
- Duration calibration + writing contract v4 + GPT-5.6-terra
  — unchanged.
- Creator-facing promote UI copy:
  - `web/src/components/narrative-memory-panels.tsx:178` →
    `What changed?` (was `What happened?`)
  - `web/src/components/narrative-memory-panels.tsx:185` →
    placeholder swapped to a state-change example.
  - No other UI copy changed.

## Real Patch's Workshop NarrativeMemory state

**6 active memories** at SESSION 266 close (+ 1 archived draft).
Details in §17.8 of the SESSION 266 doc. Shapes span three
kinds of story facts:

- **Agent-state / belief:** `f25e53af` — *"the agent Patch
  wired to the workshop thinks it runs the place."*
- **Agent-behavior / judgment:** `48746f69` — *"began deciding
  which of Patch's projects it considers necessary."*
- **Agent-behavior / opaque criteria:** `eda32b58` — *"began
  rearranging the order of Patch's projects without explaining
  its criteria."*
- **Rivet-only character attitude:** `cd73d52f` — *"Because
  it had an opinion about our work. An uninvited opinion…"*
  (witnessed_by = [Rivet] only)
- **Relationship — Rivet learned recognition:** `a34cc005` —
  *"Rivet has learned to recognize Patch's excitement… as an
  early warning that Patch is about to start experimenting
  before the details are settled."*
- **Relationship — accepted lead:** `d98962e2` — *"Patch
  accepted Rivet taking the lead on an experiment and agreed
  to follow Rivet's more methodical process."*

Two Compositions from the final SESSION 266 dogfood
(`eb48611f`, `e6b3f132`) remain **NOT promoted** — this is
allowed under the "promotion optional" principle (§18.12).

## SESSION 266 major conclusions

1. `top_k=1` KEPT into SESSION 267. Four real Compositions
   under mixed-thread retrieval produced coherent output; no
   failure mode observed. `top_k>1` remains untested.
2. `What changed?` copy KEPT. No operator friction, no
   canon-shape leaks, aligns with the story-state decision
   Chris is actually making.
3. Canon ≠ NarrativeMemory invariant INTACT. Zero canon
   mutations across the entire session.
4. **"Durable unfinished state"** is the current authoring
   lens for NarrativeMemory — a product/UX model, NOT a
   schema constraint.
5. Temporal semantics (A: *did this happen?*) and narrative
   affordance (B: *what remains open?*) are DISTINCT
   responsibilities. Don't conflate.
6. Witness semantics: implementation provides
   **eligibility-filter only** (Semantic 1). UI language
   *"Who remembers this?"* implies **character-specific
   knowledge** (Semantic 2) — over-promises today.
7. Promotion optional per Episode; 3/6 real Episodes
   worked productively without one.

## Deferred (SESSION 266 did NOT touch)

- Explicit-history prompt production change (Dogfood #2
  designed in §11.7).
- AI candidate-memory generation / suggestions.
- `top_k=2` or higher; relevance floor.
- `StoryThread` / `Relationship` / `WorldEntity` models.
- Character-memory schema / expose `kind` in UI.
- Composition detail page information architecture
  (§13.7 — promote form sits below extensive technical
  evidence).
- Private-memory leakage fix — DESIGN exists (§14.8) but
  NOT run.

## Recommended first SESSION 267 question

**Witness / private-memory leakage falsifying dogfood**
(SESSION 266 §14.8 design, §18.14 candidate #1).

Smallest falsifiable form:

> Given a Rivet-only memory of a genuinely private
> observation (Patch not in source Episode's cast, no
> Patch presence), does a follow-up Patch+Rivet render
> narrate the memory content as if Patch knew it?

Sequence:

1. READ SESSION 266 §14 (semantic-gap trace) + §14.8
   (test design) + §18.9 (disposition).
2. Author the private-observation scenario per §14.8.
3. Render 3 attempts under production (or use the
   monkey-patch mechanism to keep it synthesis-only, per
   §9.8 / §10.1).
4. Inspect Patch turns for improper narration.
5. Decide implementation only after the run:
   - Leak observed → smallest correction (prompt
     wording that surfaces witnesses + restriction).
   - No leak observed → UI relabel to accurately
     describe Semantic 1 (eligibility filter).

**Implementation is NOT yet justified.** Design + run first.

## Secondary candidates (do NOT start unless #1 completes
cleanly)

- **#2** — Longer-arc / mixed-thread dogfood continuation.
  Observation only; no architecture change. Watch what
  breaks first as active memory count grows past 6.
- **#3** — Explicit-history prompt Dogfood #2 (§11.7). One
  real render with the monkey-patched prompt against a
  promoted STRONG memory. Deferred until #1 is decided.

## Critical documentation workflow (reminder)

Important audits, experiments, runtime findings,
architectural decisions, dogfood results, and session
conclusions go under `docs/design/` BEFORE stopping. This
session followed that discipline throughout SESSION 266;
continue it.

Persist runtime evidence sidecars under
`docs/design/session_266_experiment_data/` (or a fresh
`session_267_*` subdirectory if scope diverges).

The SESSION 266 experimental Universes (EXP266-WEAK,
EXP266-STRONG) are still PRESERVED for forensic inspection
per operator instruction. They can be deleted via
`docs/design/session_266_experiment_data/02a_cleanup_partial.py`
when authorized.

---

**Do NOT start SESSION 267 in this handoff. This document
is a starting point, not a plan of record. The next session
begins with an audit / orient pass and follows evidence.**
