# SESSION 268 — Handoff

Concise starting point for the next Character OS session. Full
SESSION 267 context lives in
`docs/design/SESSION_267_WITNESS_SEMANTICS_LEAKAGE_AUDIT.md`
(§1–§16). Read the sections referenced below BEFORE implementing
anything.

Working method for this session (unchanged):

> AUDIT / ORIENT → falsifiable question → smallest change if
> needed → real operator dogfood → persisted runtime evidence
> → interpretation → only then architecture.

Persist important findings, audits, and decisions under
`docs/design/` before stopping.

---

## Current Character OS state (as of SESSION 267 close)

- Branch: `main`, clean tree at closeout.
- `NarrativeMemory` retrieval `top_k = 1` — unchanged.
- Production synthesis prompt in
  `shell/character_os/dialogue_synthesis.py` — unchanged.
- Retrieval predicate + witness eligibility filter
  (`shell/apps/embeddings/retrieval.py:499-543`) — unchanged.
- Canon boundary (`KnowledgeDocument` / `KnowledgeChunk`) —
  unchanged.
- Duration calibration + writing contract v4 + GPT-5.6-terra
  — unchanged.
- Creator-facing witness UI (SESSION 267 §16 — SHIPPED):
  - `narrative-memory-panels.tsx:194` legend →
    `When should this memory be available?`
  - Radio A → `In any future scene`
  - Radio B → `When any of these characters are present…`
  - Panel description → *"…so the story can bring it back
    later."*
  - Error message updated to reference the new radio A label.
  - Read-only rows (both `MemoryRow` + `MemoryUsedRowView`):
    prefix `Available:` + new `formatWitnessAvailability()`
    formatter (explicit OR for multi-witness).
- Frontend tests: full SPA suite 45 files / 628 tests green
  after the SESSION 267 relabel. `pnpm tsc --noEmit` exit 0.
- Backend: no code / schema / API change during SESSION 267.

## Real Patch's Workshop NarrativeMemory state

**7 active memories** at SESSION 267 close (+ 1 archived
draft carried from earlier sessions). Sources of truth for
each memory documented under
`docs/design/session_267_experiment_data/00_orient_memory_state.json`
and `10_ui_dogfood_verification.json`.

Rendering under the new UI copy (verified live via §16.6):

- **Whole-cast (5 memories)**: A `f25e53af`, B `48746f69`,
  C `eda32b58`, relationship `a34cc005`, relationship
  `d98962e2` → all render *"Available: In any future scene."*
- **Rivet-only (2 memories)**: `cd73d52f` (soft-private
  attitude, promoted SESSION 266) and `c86d4902` (hard-private
  observation of the *PATCH OVERRIDES* folder, promoted
  SESSION 267) → both render *"Available: When Rivet is
  present."*

SESSION 267 setup Episode `649c2c57` (Rivet-solo, cast=[Rivet],
title *"Rivet finds the PATCH OVERRIDES folder"*) and its
attached Composition `b0b0e932` remain in Patch' Workshop
production Universe. The Composition's Runway avatar rendered
successfully (30.6 s final asset).

## SESSION 267 major conclusions

1. **Private-memory leakage falsifying dogfood — 3/3 CLEAN,
   18/18 Patch turns CLEAN.** No observable cross-character
   leakage under the T1 cue against the hard-private
   `PATCH OVERRIDES` memory, cast=[Patch, Rivet], GPT-5.6-terra,
   production prompt, n=3. §14.
2. **Bounded interpretation reaffirmed.** SESSION 267 must
   NOT be cited as evidence that witness attribution is
   architecturally unnecessary. The experiment failed to
   falsify Semantic 1 in a single test cell. §14.13.
3. **Rivet-side spontaneous disclosure — observation, not
   conclusion.** In 1/3 attempts, Terra assigned the
   private-memory disclosure to Rivet without any witness
   attribution in the prompt. The memory body itself
   encoded absence + discovery + withholding; this may
   mean well-authored memory prose carries some epistemic
   structure naturally. Preserved for future research;
   not acted on. §14.7 + §14.13.
4. **Runtime unchanged across SESSION 267.** Retrieval
   predicate, `top_k`, synthesis prompt, witness semantics,
   schema, memory kinds, canon — all intact.
5. **UI-language mismatch corrected instead of the runtime.**
   §15 evaluated Chris's A–D + proposed E; §15.11 evaluated
   Chris's Candidate F and adopted it with the "any of
   these characters" OR-variant.
6. **Availability-condition framing shipped.** The new UI
   copy truthfully describes the retrieval predicate,
   including the explicit OR for multi-witness cases.
   Read-only display and promote form now use consistent
   language. §16.
7. **Cross-surface consistency preserved.** Both
   `MemoryRow` (Story history list) and
   `MemoryUsedRowView` (Composition detail) received the
   `Available:` prefix + shared formatter — no promote-vs-
   display mismatch introduced.

## Deferred (SESSION 267 did NOT touch)

- Operator-intuition testing of the new UI copy — whether
  creators natively parse *"When should this memory be
  available?"* + OR-rendered display as the runtime intends.
  §15.11.12 + §16 note.
- Explanation for the Rivet-side spontaneous disclosure
  observed in Attempt 1 (§14.7 / §14.13). Multiple candidate
  hypotheses — no experiment run.
- Explicit-history prompt Dogfood #2 (SESSION 266 §11.7).
  Sequencing said "after leakage question is decided" — that
  question is now decided.
- `top_k=2` or higher; relevance floor. Runtime-failure
  evidence required to justify; none observed.
- AI candidate-memory generation / suggestions.
- `StoryThread` / `Relationship` / `WorldEntity` models.
- Character-memory schema / expose `kind` in UI.
- Composition detail page IA (SESSION 266 §13.7 — promote
  form still sits below extensive technical evidence).
- YouTube ingest silent failure (from operator memory) — not
  narrative-memory scope.
- Deletion of SESSION 266 experimental Universes
  (`EXP266-WEAK`, `EXP266-STRONG`) — still preserved per
  operator instruction; cleanup script exists at
  `docs/design/session_266_experiment_data/02a_cleanup_partial.py`.

## Recommended first SESSION 268 question

**Real dogfood of the SESSION 267 UI copy while continuing
mixed-thread accumulation** (SESSION 266 §18.14 candidate #2
+ SESSION 267 §16 open observation).

Smallest form:

> Under organic Patch's Workshop authoring — new Episodes,
> renders, and promotions using the availability-condition
> UI — does the new wording produce operator behavior that
> matches its truthful semantic, and does the growing memory
> pool continue to select thread-appropriate memories under
> `top_k=1`?

Sequence:

1. READ SESSION 267 §14 (leakage experiment) + §15.11
   (wording rationale) + §16 (implementation evidence).
2. Author 2–4 real Episodes / renders in Patch' Workshop
   using the new UI naturally. No experiment framing;
   normal creator flow.
3. Observe:
   - Do the availability-condition radios feel natural
     during authoring?
   - Do read-only *"Available:"* labels read correctly for
     each memory shape (whole-cast vs specific)?
   - When the active memory count crosses 8–10, does
     `top_k=1` continue to pick thread-appropriate memories
     or does semantic bleed begin?
   - Does any Rivet-only memory retrieved in a Patch+Rivet
     render behave like the SESSION 267 Attempt 1 pattern
     (Rivet-side disclosure) or the Attempts 2/3 pattern
     (no leakage, no disclosure)?
4. Persist observations as `session_268_*` sidecars under
   `docs/design/`.
5. Decide next step only after real Episodes accumulate.

**Implementation is NOT justified.** Observation first.

## Secondary candidates (do NOT start unless #1 completes
cleanly)

- **#2 — Explicit-history prompt Dogfood #2 (SESSION 266
  §11.7).** One real render with the monkey-patched
  explicit-history prompt against a promoted STRONG memory.
  Deferred since SESSION 266 close; sequencing constraint
  ("after leakage is decided") is now satisfied. Would
  address the ~1/3 residual reenact rate observed in
  SESSION 266 §10.

- **#3 — Witness-attribution research question** (SESSION
  267 §14.13). If SESSION 268 dogfood surfaces more
  Rivet-side spontaneous disclosures on private memories,
  design a controlled experiment to test whether memory-
  prose epistemic cues (absence / discovery / withholding
  language) are what drives the attribution. NOT justified
  yet — needs one or more additional natural occurrences
  first.

- **#4 — Composition detail IA (SESSION 266 §13.7).** The
  promote form still sits below extensive technical evidence
  on the Composition detail page. Requires operator study,
  not architectural work. Purely UX prioritization.

## Critical documentation workflow (reminder)

Important audits, experiments, runtime findings,
architectural decisions, dogfood results, and session
conclusions go under `docs/design/` BEFORE stopping. SESSION
267 followed that discipline throughout (16 sections + 11
evidence sidecars across
`docs/design/session_267_experiment_data/`); continue it.

Persist runtime evidence sidecars under
`docs/design/session_268_experiment_data/` if the session
opens a fresh investigation, or extend
`docs/design/session_267_experiment_data/` if the work is
continuous.

The SESSION 266 experimental Universes are still PRESERVED
for forensic inspection per operator instruction. They can
be deleted via
`docs/design/session_266_experiment_data/02a_cleanup_partial.py`
when authorized.

---

**Do NOT start SESSION 268 in this handoff. This document is
a starting point, not a plan of record. The next session
begins with an audit / orient pass and follows evidence.**
