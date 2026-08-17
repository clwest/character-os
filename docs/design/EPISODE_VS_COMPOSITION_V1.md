---
title: "Episode vs Composition v1 — Narrative Layer Above Render Provenance"
status: design — semantic layering only (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "handoffs/SESSION_259_OBSERVABILITY_BACKLOG.md"
scope: >
  Decide whether Composition should absorb the narrative Episode role
  or whether Episode should be a distinct Universe-scoped record that
  references one-or-more Compositions. Take positions. Do not design
  narrative memory, canon promotion, relationship history, unresolved
  threads, or educational objectives — only identify which layer each
  belongs on.
---

# Episode vs Composition v1 — Narrative Layer Above Render Provenance

## Purpose

The SESSION 261 capability inventory established that `Composition`
today is a strong render-provenance shell but a partial narrative
record (CAPABILITY_INVENTORY_SESSION_261.md §10, §15, special
question 9). The SESSION 259 observability backlog documented that
`operator_topic`, per-attempt synthesis output, retry count,
corrective-hint, and retrieval snapshot on failed paths are all
missing — meaning even a single render cannot be reconstructed
narratively from the row (SESSION_259_OBSERVABILITY_BACKLOG.md).
The UNIVERSE_BOUNDARY_V1.md ratification then created a coherent
world-level home (Universe, child of Workspace) for narrative-scale
concepts, with the explicit ½-slice discipline that Universe v1 owns
only `Teammate.universe` and `KnowledgeDocument.universe`.

This document decides one thing: **should Composition become the
narrative Episode concept, or should Episode be a separate
Universe-level record that wraps one or more Compositions?** It takes
a position, justifies it against current-state code, walks four real
product examples through the recommended model, and identifies which
future narrative concerns attach at Episode versus Composition versus
elsewhere. It does not design any of those future concerns.

## Scope of this slice (and what's explicitly deferred)

**In scope.**

- Semantic separation between "the render job that produced this
  video" and "the story event that occurred in this world."
- Which existing Composition fields are production/execution concerns
  and which are already narrative/content concerns.
- Cardinality between Episode and Composition.
- Lifecycle: where operator topic lands, when Episode is created,
  when Composition is created, what retry / rerender do.
- Legacy behavior: whether historical Compositions ever get wrapped.
- Universe scoping implications for Episode and downstream models.
- Isolation invariants that must hold once Episode exists.

**Explicitly deferred.**

- Any schema DDL, migration plan, or Django field addition.
- Narrative memory substrate (event log / promise ledger shape).
- Canon promotion mechanic (what makes an Episode canonical).
- Relationship-history persistence.
- Unresolved-thread tracking.
- Educational / curriculum learning objectives.
- Cast / Ensemble grouping (deferred at UNIVERSE_BOUNDARY_V1.md §Q12).
- Location / Scene / Set entity (deferred at
  UNIVERSE_BOUNDARY_V1.md §D3).
- Voice / POV versioning strategy.
- Composition provenance-observability gaps (operator_topic,
  per-attempt log, retry count) — those are SESSION 259 backlog and
  should ship whether or not Episode ever ships. This doc does not
  block on them, but it does identify which of them are Composition
  concerns forever and which are actually Episode concerns
  misattributed to Composition.
- SPA UX for Episode.
- Cross-Universe crossovers.

## Working hypothesis

Restated for the record from the SESSION 261 brief:

1. Composition remains the render/execution/provenance primitive.
2. Episode becomes a Universe-scoped narrative primitive.
3. Episode may reference one or more Compositions.
4. A Composition is not automatically canon merely because it
   rendered.
5. Narrative events / history attach to Episode, not directly to
   render steps.
6. Re-rendering or adapting an Episode should not create a new
   canonical event unless the operator intentionally creates a new
   Episode.

## Current-state audit of Composition

### What Composition currently means

Per `shell/apps/compositions/models.py:357–548`, `Composition` is:

> "An ordered sequence of step primitives that combine Assets into a
> final deliverable Asset."

The docstring names it a render job. The field set confirms it: a
Composition owns `status` (draft/planning/running/partial/completed/
failed), `error_message`, `final_asset` (SET_NULL FK to the
deliverable clip), a `mock_mode` boolean captured at create time from
env flags "so the entire run is internally consistent," cost triple
(`cost_estimate_micros` + `cost_actual_micros`), and a linear
`CompositionStep` set with `(composition, position)` unique
(`compositions/models.py:551–711`). Every step carries its own
`primitive` name, `inputs`, `params`, `cost_actual_micros`,
`elapsed_ms`, `media_engine_task_id`, and `error_message`.

That is a render-job shell. It is NOT a narrative shell.

But Composition also carries fields that leaned "narrative content"
over the SESSION 253 / 168 / 161 sequence:

- `synthesized_brief` — the final assembled scene text
  (`compositions/models.py:460–478`).
- `rejected_synthesis` — the LLM output that Strict-mode verifier
  blocked (`compositions/models.py:441–447`).
- `knowledge_chunk_ids` — the K2 chunks that fed synthesis
  (`compositions/models.py:424–427`).
- `verification_status` + `verification_warnings` +
  `writing_contract_version` — content-verifier state
  (`compositions/models.py:429–487`).
- `template_kind` (free-text; `talking_head`,
  `talking_head_with_backdrop`, `dialogue_scene`, `long_form_ad`,
  …) — this is closer to "what shape of content is this" than "what
  render job is this."
- `name` (≤200 chars) — operator-facing identity, but per SESSION 259
  observability backlog, sometimes carries a truncated topic prefix
  (~40 chars) and sometimes carries a first-turn opener; the meaning
  is not disciplined.

The row is a hybrid. It is a mostly-correct render job that has
absorbed narrative-content fields because there was nowhere else for
them to live.

### Field-by-field: production vs narrative concerns

Reading `Composition` (`compositions/models.py:357–548`) with a
production/narrative lens:

**Pure production / execution concerns (belong on the render job
forever).**

- `id` (UUID) — row identity.
- `workspace` (FK, CASCADE, NOT NULL) — tenant scope.
- `spokesperson` (FK, SET_NULL) — primary character rendered. Kept
  even after teammate deletion so historical rows survive
  (SESSION 251).
- `status` — render-job state machine (draft/planning/running/
  partial/completed/failed).
- `error_message` — render-job failure detail.
- `final_asset` (FK, SET_NULL to Asset of type CLIP) — the produced
  file.
- `cost_estimate_micros` + `cost_actual_micros` — render cost.
- `mock_mode` — render-time execution mode.
- `created_by`, `created_at`, `updated_at` — audit.
- `CompositionStep` set — primitive-by-primitive execution log with
  step-level cost, elapsed, task IDs, errors.

**Narrative-content concerns currently on Composition.**

- `synthesized_brief` — the assembled scene text. This is content,
  not execution.
- `rejected_synthesis` — content that failed verification. Content,
  not execution.
- `knowledge_chunk_ids` — which knowledge fed the content. Content
  provenance, not execution.
- `verification_status` + `verification_warnings` +
  `writing_contract_version` — content-quality state, tied to the
  content authored, not to how it was rendered.
- `template_kind` — content shape (talking_head vs dialogue_scene vs
  long_form_ad). Content, not execution.
- `name` — arbitrary operator-facing string, currently used
  inconsistently for topic/opener/naming (SESSION 259 backlog).

**Ambiguous.**

- `spokesperson` — is this the character who performs in the render
  job (production), or the character whose story we are telling
  (narrative)? Today both meanings coexist. In a dialogue scene, the
  "spokesperson" is only the primary; the actual cast is
  reconstructed from `CompositionStep.params` via `_dialogue_resolver`
  (`compositions/recipes.py:271–355` per audit §13). Neither the
  primary-only view nor the params-scraping view is a durable cast
  primitive.

### Known gaps (SESSION 259 backlog + this doc's findings)

Confirmed by grep (`operator_topic|previous_composition|episode|
scene_number|retry_count|attempt_log|first_pass|corrective_hint`
returns nothing in `shell/apps/compositions/models.py`):

- No `operator_topic` — the operator's verbatim topic string is not
  persisted anywhere reliably (SESSION 259 backlog §37–46). Recovery
  is possible only from a truncated `name` prefix and only when the
  naming derives from topic vs opener.
- No per-attempt / per-pass log — first-pass synthesis output is not
  kept on success; corrective-retry hint and corrective-retry output
  are not persisted at all.
- No retry-count field.
- No retrieved-chunk-IDs snapshot on rejected/failed paths (only on
  success).
- No cast persistence for dialogue scenes beyond
  `CompositionStep.params` scraping.
- No `previous_composition` FK, no scene number, no episode ID, no
  arc grouping (audit §10).
- No canon flag — "this render is now part of world truth" has no
  representation.
- No unresolved-thread linkage — "this scene ended with a promise
  that must be paid off" has no representation.
- No prior-episode reference — "the character in this scene called
  back to a previous scene" has no representation.
- No location reference — because Location does not exist as a
  substrate (audit §12).

Some of those gaps are Composition-shaped (operator_topic on the
render job itself, per-attempt log, retry count — these describe THIS
render attempt). Others are Episode-shaped (scene number, previous
episode, canon flag, unresolved threads, location — these describe
the narrative event, not the render). The current model conflates
them because there is only one row.

## Q1–Q18 answered

### Q1. Is Composition fundamentally a render job, a creative artifact, a narrative event, or a mixture today?

**Mixture, weighted toward render job with parasitic narrative
fields.** The docstring and field set confirm it is primarily a
render job (`compositions/models.py:357–360`). But narrative-content
fields (`synthesized_brief`, `rejected_synthesis`,
`knowledge_chunk_ids`, `verification_*`, `template_kind`, and
overloaded `name`) attached to it because there was no other home.
The mixture is the source of the ambiguity this doc resolves.

### Q2. Which existing Composition fields are production/execution concerns?

Enumerated above: `id`, `workspace`, `spokesperson` (in its
"performer" reading), `status`, `error_message`, `final_asset`,
`cost_estimate_micros`, `cost_actual_micros`, `mock_mode`,
`created_by`, `created_at`, `updated_at`, and the entire
`CompositionStep` set (primitive, inputs, params, cost, elapsed,
task IDs). These stay on Composition forever.

### Q3. Which existing fields are already narrative/content concerns?

`synthesized_brief`, `rejected_synthesis`, `knowledge_chunk_ids`,
`verification_status`, `verification_warnings`,
`writing_contract_version`, `template_kind`, and the overloaded
`name`. In a two-model world these are content-of-this-render fields
— they describe what THIS render attempt authored, not what the
Episode-level story is. They stay on Composition as
per-render-attempt content provenance; the Episode-level view of
"what the story is about" lives on Episode.

Position: do NOT move `synthesized_brief` / `rejected_synthesis` /
`verification_*` / `knowledge_chunk_ids` / `writing_contract_version`
to Episode. They describe what THIS render produced, which is a
per-attempt record; the Episode is above the attempt.

### Q4. What information required for a persistent Episode is NOT currently stored?

- Verbatim operator topic / premise — **not stored** (SESSION 259
  backlog §37–46).
- Cast (N characters, not just primary) — **not stored** as a
  first-class field; reconstructable only from
  `CompositionStep.params` for dialogue_scene.
- Episode title (as distinct from a render job name) — not
  represented; `Composition.name` is the render job name.
- Sequence / order (scene number within a series) — not represented.
- Story outcome (what happened, in operator-authored or synthesized
  language) — partially in `synthesized_brief`, but that is content
  produced, not narrative summary.
- Events that occurred (structured, extractable) — not represented.
- State changes (Rivet learned a lesson; Mike acquired a customer)
  — not represented.
- Unresolved threads (promises, warnings, open questions) — not
  represented.
- Canon candidates / canon flag — not represented.
- Relationship changes — not represented (Relationship substrate
  does not exist; audit special question 7).
- Locations involved — not represented (Location substrate does not
  exist; audit §12).
- World objects involved — not represented (in-world object
  substrate does not exist; audit §11).
- Lesson / educational objective / audience / purpose — not
  represented (audit §16, ABSENT).
- Prior-Episode callbacks — not represented.

### Q5. Is operator topic currently persisted anywhere reliably?

**No.** Confirmed by SESSION 259 observability backlog and by grep of
`compositions/models.py` for `operator_topic|topic` — no such field.
Recovery today is best-effort: a truncated `name` prefix (~40 chars)
when the naming code path derived from topic, but that convention is
not enforced and cannot be assumed. This is a real gap independent of
Episode; it should be closed regardless (SESSION 259 backlog fix).

### Q6. What happens when synthesis fails before CompositionSteps exist? Would an Episode still be useful/valid?

Today, if synthesis fails before any CompositionStep row is created,
the Composition row can exist with `status=failed` and no steps —
but `operator_topic` is not persisted, `first_pass` output is not
persisted, and `retrieval snapshot on failure paths` is not
persisted (SESSION 259 backlog). The row is a rubble marker with
almost no diagnostic value.

An Episode row would still be useful in this case: the operator's
intent ("I want a scene where Patch and Rivet argue about the AI
takeover") is a narrative fact that exists BEFORE synthesis runs and
survives synthesis failure. Position: **Episode can exist without a
successful Composition.** An Episode with zero Compositions attached
is a legal, useful state — it says "the operator conceived this
story but no successful render exists yet." This distinguishes
"intent recorded" from "artifact rendered."

### Q7. What happens when a Composition is retried or rerendered? Does treating Composition == Episode create duplicate narrative history?

**Yes, treating them as one row creates duplicate narrative history
on every retry / rerender.** Concretely:

- Product example A: Patch + Rivet, "AI took over the lab" —
  synthesis rejected, later successful rerender. Under
  Composition == Episode, the world now has two Episodes ("AI took
  over the lab" appears twice) or the operator loses provenance of
  the rejected attempt. Neither is acceptable.
- Product example B: rerender for a different aspect ratio.
  Rerendering a working scene at 9:16 for shorts vs 16:9 for
  landing pages creates two Compositions — under Composition ==
  Episode the world thinks it happened twice.
- Product example C: rerender because provider failed / a backdrop
  looked wrong. Same problem.

This is the load-bearing argument against Composition == Episode.
Retry, rerender, aspect variant, translation, corrective rerun, and
alternate visual treatment are all real product needs. Every one of
them creates a new Composition. None of them should duplicate the
narrative event.

### Q8. Could one Episode reasonably produce multiple Compositions?

**Yes, in every product example that matters:**

- **A.** Rejected synthesis + successful rerender — one Episode
  ("AI took over the lab"), two Compositions (first failed, second
  succeeded).
- **B.** Master 90s scene + 30s recap cutdown — one Episode ("why
  plants need sunlight"), two Compositions with different
  target_duration and possibly different recipe.
- **C.** Rerender with different visual background — one Episode
  ("apprentice misdiagnosed low water pressure"), two Compositions
  with different backdrop asset.
- Additional real cases:
  - Alternate aspect ratio (9:16 short + 16:9 landing page).
  - Translated version (English render + Spanish render, same
    story).
  - Rerender after provider failure.
  - Alternate visual treatment (different asset preset, same
    script).
  - Rerender with corrected media (a bad frame, a mispronounced
    name).

Position: **one Episode → many Compositions is a first-class
cardinality.** Not an exceptional case; not an anti-pattern; the
common path.

### Q9. Could one Composition belong to more than one Episode?

Take a position: **NO. One Composition belongs to at most one
Episode.** Reasoning:

- Every real cross-Episode reuse pattern collapses to either
  (a) a new Composition or (b) explicit inter-Episode reference. A
  crossover between two Episodes (Patch's world visits Mike's
  world) is either a Universe-crossing primitive (deferred per
  UNIVERSE_BOUNDARY_V1.md invariant 5, "no implicit crossing
  primitive") or a new Episode co-attached to both narrative arcs
  by explicit reference. It is not a shared Composition row.
- Multi-Episode ownership creates cascade ambiguity: if Episode A
  is deleted, does the Composition survive because Episode B still
  references it? If Episode B rejects the Composition's script,
  does that reject it for Episode A? Ownership uncertainty on the
  narrative axis leaks into render-provenance uncertainty.
- Simple ownership makes canon promotion coherent: "this Composition
  became canonical" means "the Episode it belongs to became
  canonical," full stop. With multi-Episode ownership the canon
  question fragments per-Episode.

Simple ownership wins. Prefer clarity; if a real product need for
Composition-in-two-Episodes surfaces later, revisit.

### Q10. Should an Episode exist before synthesis/render starts, or only after a successful Composition exists?

**Before.** The operator's narrative intent — "I want Patch and
Rivet to argue about the AI takeover, ~90s, teachable moment about
skepticism vs curiosity" — is a narrative fact the moment the
operator types it. It exists whether or not synthesis succeeds
(Q6), whether or not the first render passes verification, and
whether or not the operator ever hits render again.

Creating Episode before render also gives us the durable home for
`operator_topic` that SESSION 259 has been searching for: it lands
on Episode, not on Composition. Composition inherits its topic
through its Episode FK; a per-Composition first-pass /
corrective-hint / retry-count log stays Composition-level (those
describe the RENDER attempt).

Corollary: an Episode with zero Compositions is a legal state. So
is an Episode with N Compositions all failed. So is an Episode with
1 Composition succeeded and 3 Compositions failed. Episode does not
require successful render.

### Q11. Should failed/rejected generation attempts belong to an Episode as attempts, or stay purely Composition-level execution history?

**Failed/rejected renders stay Composition-level rows that reference
the Episode.** A rejected/failed Composition is still a valid
Composition row (already the case today —
`Composition.status=failed` is legal). Under the recommended model,
that row FKs its Episode. This preserves:

- Per-attempt render provenance (which Composition row failed, at
  which step, with what error) — stays on Composition.
- Per-attempt content evidence (`rejected_synthesis`,
  `verification_warnings`, `writing_contract_version`) — stays on
  Composition.
- Narrative intent (`operator_topic`, cast, prior-Episode
  callbacks) — stays on Episode.

Retry-count / first-pass / corrective-hint gaps from SESSION 259
backlog are Composition-level fixes (they describe attempts), not
Episode-level fixes.

### Q12. Does Script belong conceptually to Episode, Composition, or both?

`Script` (`shell/apps/scripts/models.py:42+`) today owns:
`workspace` + `spokesperson` FKs, `name`, `prompt` (operator input
+ RAG query), `opener`, `draft_text`, `knowledge_chunk_ids`,
`model` / `tokens_input` / `tokens_output`, `verification_*` /
`verifier_mode`, `revision_history` (snapshot-on-regenerate JSON
list), `status` (draft/ready/rendered/archived).

Position: **Script belongs to the Episode conceptually, and can be
attached to zero or many Compositions.** Reasoning:

- Script's `prompt` is a rephrased `operator_topic`. Under the
  recommended model, `operator_topic` lives on Episode, so `Script`
  is a first-pass authored artifact of the Episode's intent.
- Script's `draft_text` is the authored words the Episode's cast
  will speak. That is narrative content — episodic.
- Script's `revision_history` snapshots iterations. That is the
  authoring log for an Episode's words, not for a specific render.
- Multiple Compositions can render from the same Script (rerender,
  aspect variant, translation-with-approved-source), so Script:
  Composition is 1:N, mirroring Episode: Composition.
- However, in the SESSION 168 model, Composition can also carry
  `synthesized_brief` without a preceding Script row (K6 synthesis
  from operator prompt directly). That path stays valid: Composition
  in isolation still carries its own content provenance.

In v1, Script's direct workspace/spokesperson FKs remain
(per UNIVERSE_BOUNDARY_V1.md Q4: Script gains Universe FK later,
transitively via spokesperson.universe for now). Once Episode
exists, Script gains an optional `Episode` FK. Legacy Scripts
without an Episode continue to function.

### Q13. Does PublishBundle belong to Episode, Composition, or remain independent?

`PublishBundle` (`shell/apps/publish/models.py:37+`) is
"one source CLIP → N platform-ready variants." Rule 1: single CLIP
source per bundle, enforced at `clean()` (asset_type=CLIP + same
workspace).

Position: **PublishBundle remains a distribution primitive
anchored to a source `Asset` (CLIP), NOT a first-class Episode
member.** Reasoning:

- PublishBundle is a delivery mechanic — take one produced clip,
  package it for N platforms. It doesn't participate in narrative
  history; it participates in distribution history.
- The source clip is an `Asset`, which is Workspace-scoped
  (UNIVERSE_BOUNDARY_V1.md §Q5: Assets stay workspace-scoped;
  pixels are tenant records).
- If narrative-level linkage is ever needed ("this bundle
  distributed the Episode with the AI-takeover story"), it rides
  through the chain: bundle.source_clip →
  clip.composition (already exists as `Asset.composition` SET_NULL
  FK) → composition.episode (proposed).
- PublishBundle does NOT gain a direct Episode FK in v1. It stays
  what it is: a distribution artifact keyed on an Asset.

### Q14. If Episode wraps Composition, what is the smallest useful cardinality?

**Episode : Composition is 1:N (one Episode → many Compositions),
Composition : Episode is N:1 (one Composition belongs to one
Episode).** Explicitly:

- Episode may have zero Compositions (intent recorded, no
  successful render).
- Episode may have one Composition (the common case).
- Episode may have many Compositions (retry, rerender, aspect
  variant, translation, alternate visual, corrected rerun).
- One Composition belongs to at most one Episode (Q9).
- Episode has no "primary Composition" designation in v1. Rank /
  primary-variant is a UI concern; if a durable primary needs to
  exist, add later. This keeps the primitive coherent.

Optional refinement to consider in a later slice, not v1: an
`Episode.canonical_composition` nullable FK to name the definitive
render. Deferred.

### Q15. How should Episode interact with future narrative memory / canon promotion / relationship history / unresolved threads / educational objectives?

Layer only — no design.

- **Narrative memory (event log / promise ledger):** attaches at
  Universe, keyed on Episode. A memory row says "in Episode X,
  Rivet warned Patch about Y." Deleting the Episode CASCADES the
  memory (canon-scale rewrite requires narrative-level intent).
  Substrate does not exist today (audit special question 8).
- **Canon promotion:** a flag / lifecycle on Episode. A Composition
  never becomes canonical on its own; the Episode does. Rerendering
  a canonical Episode does not un-canonicalize it. The canonical
  Episode's canonical render (if designated later per Q14) is the
  currently-blessed variant. Substrate does not exist today.
- **Relationship history:** attaches at Universe, keyed on Episode.
  "Patch's trust of Rivet decreased in Episode X" is a Universe-level
  Relationship-history row that references the Episode. Relationship
  substrate does not exist today (audit special question 7).
- **Unresolved threads:** attaches at Universe, keyed on Episode.
  "Episode X ended with an open promise: Mike will call the
  customer back tomorrow." Substrate does not exist today.
- **Educational objectives:** attaches at Episode directly (not
  Composition). The first-grade "why plants need sunlight" is a
  property of the Episode's intent, unchanged by which cutdown
  renders. Substrate does not exist today (audit §16).

All five are downstream slices. This doc identifies WHERE they
attach; it does not design them.

### Q16. Legacy behavior: can current Compositions remain Episode-less indefinitely?

**Yes, and this is the recommended posture.** Mirrors
UNIVERSE_BOUNDARY_V1.md §Q6–Q7 (prospective introduction, no
bulk-migration). Concretely:

- The 81 historical Compositions in `chriss-workspace` stay put with
  no Episode FK. They continue to function as today: render-job
  rows with a `spokesperson` FK, a `template_kind`, and the
  content-provenance fields already present.
- New Compositions created after Episode ships MUST belong to an
  Episode. An Episode is auto-created at Composition-create time if
  the operator did not explicitly pick one — but this Episode is
  operator-visible, editable, and can be titled / merged / split
  later. Auto-creation is a UX convenience; it never means "silent."
- Historical Compositions MAY be assigned to a new Episode later as
  a bespoke ½-slice per Composition (mirrors UNIVERSE_BOUNDARY_V1's
  audit §9 recommendation: no bulk migration).

Rejected alternative: auto-wrapping every historical Composition
into an "Episode of one" at Episode ship. Reasoning: this repeats
the workspace-default overload the Universe doc rejected in §Q8.
Auto-wrapping creates 81 meaningless "Episode 1" rows and the
operator would look at the SPA, see 81 unhelpful Episodes, and
struggle to identify which ones deserve narrative status.

### Q17. Does adding Episode require Composition to immediately gain a Universe FK?

**No.** Episode itself is Universe-scoped (see decision below). A
Composition that belongs to an Episode is transitively
Universe-scoped through `composition.episode.universe`. This is
consistent with UNIVERSE_BOUNDARY_V1.md's posture that Composition's
direct Universe FK is deferred (§Q4 / §Q5, "may gain direct Universe
FK when Episode / arc concepts land" — this is that slice, but
transitive scoping through Episode is sufficient for v1).

For a legacy Composition with no Episode: it stays Workspace-scoped
legacy, per UNIVERSE_BOUNDARY_V1's Q9 legacy-isolation rule. A
legacy Composition never becomes Universe-scoped by accident.

### Q18. What invariants must hold?

Enumerated below in "Isolation invariants." Key ones stated up front:

- `Episode.workspace == Episode.universe.workspace`.
- Every Composition attached to an Episode has
  `composition.workspace == episode.workspace` and
  `composition.spokesperson.universe == episode.universe`
  (when the spokesperson has a Universe assigned).
- No cross-Universe variants: an Episode's Compositions all sit in
  the same Universe.
- No cross-Workspace pairings anywhere (existing invariant,
  preserved).
- Rerendering / adding a variant Composition does NOT duplicate
  narrative history — the Episode row is the same; only the
  Composition set grows.
- Deleting a Composition does NOT delete its Episode (SET_NULL or
  PROTECT on the Composition side; Episode's other Compositions
  survive; the narrative event is unaffected).
- Deleting an Episode CASCADEs the narrative-memory rows attached to
  it (a canon rewrite is intentional and expensive); Compositions
  belonging to the Episode either detach (become legacy) or are
  also deleted, TBD by product policy in the schema slice.
- Cross-Universe crossovers, if ever needed, are an explicit
  primitive with their own name and audit trail
  (UNIVERSE_BOUNDARY_V1.md invariant 5, preserved).

## Decision

**B. Episode wraps Composition. Two models, Episode above.**

**Load-bearing reason.** One Episode routinely produces many
Compositions (Q8: retry, cutdown, aspect variant, translation,
rerender-with-corrected-media, alternate visual). Composition ==
Episode makes narrative history duplicate on every rerender (Q7),
which is unacceptable for any world with continuity. Two-model
separation is the smallest model that correctly represents the fact
that an operator's story is one thing and the render jobs that
produce it are a different thing. Episode also provides the durable
home for `operator_topic` that SESSION 259 has been searching for
(§Q5, §Q10), and it aligns cleanly with UNIVERSE_BOUNDARY_V1.md's
Universe scoping (Episode is a Universe-scoped narrative primitive;
Composition remains a Workspace-scoped render-provenance primitive
that transitively acquires Universe scope through its Episode).

The alternative Option A (Composition becomes Episode) fails on
retry/rerender semantics and cannot cleanly represent
Episode-without-successful-Composition (Q6, Q10). Option C (some
third model shape) has no evidence supporting it — the primitives
already carry cleanly separable production vs narrative concerns
(§Field-by-field above), and no repository evidence surfaces a
motive for a more exotic layering.

## Current Composition semantics → Recommended Episode semantics

**Composition (current, unchanged in role).**

> An ordered sequence of step primitives that combine Assets into a
> final deliverable Asset, with per-attempt cost, execution mode,
> content-verifier evidence, and citation logging.

Continues to own: workspace anchor, spokesperson FK (performer
role), `status` (render state machine), `error_message`,
`final_asset`, per-step primitives (`CompositionStep`),
cost triple, `mock_mode`, `synthesized_brief`, `rejected_synthesis`,
`knowledge_chunk_ids`, `verification_*`,
`writing_contract_version`, `template_kind`, `name`, `created_by`,
timestamps. Gains SESSION 259 backlog fixes at its own layer
(retry-count, per-attempt log, corrective-hint on failure paths).

**Episode (recommended, new).**

> A Universe-scoped narrative event conceived by the operator. Owns
> the story's intent (operator_topic), title, cast, sequence within
> its Universe, and the durable "what story is this" identity.
> Referenced by zero or more Compositions, each of which is one
> render attempt / variant of the Episode. Not automatically
> canonical; canon promotion is an explicit lifecycle.

Owns (in v1 minimum): Universe parent FK; operator-authored
`title`; verbatim `operator_topic` (SESSION 259's missing field
finds its home); cast (N-teammate reference, replaces the
single-spokesperson primary + params scraping); sequence marker
(monotonic per-Universe ordering, allowing operator reorder);
optional `location` reference when Location arrives; audience /
purpose fields when educational objectives arrive. Does NOT own in
v1: canon flag (deferred), narrative-memory rows (deferred to
memory substrate), relationship-history rows (deferred to
Relationship substrate), unresolved-thread rows (deferred), prior-
Episode-callback edges (deferred).

## Ownership / cardinality diagram

```
Workspace  (tenant)
  └── Universe  (world; UNIVERSE_BOUNDARY_V1.md)
        ├── Teammate            (cast members belong to Universe)
        ├── KnowledgeDocument   (world knowledge belongs to Universe)
        ├── Episode  (narrative event; NEW; wraps renders)
        │     ├── cast: M2M → Teammate (subset of Universe cast)
        │     ├── operator_topic (verbatim)
        │     ├── title, sequence, purpose/audience (future)
        │     └── Composition * (0..N render attempts / variants)
        │           ├── CompositionStep *
        │           ├── final_asset → Asset
        │           ├── synthesized_brief (per-attempt content)
        │           ├── verification_* (per-attempt content check)
        │           └── (Script → optional, 0..1 per Composition)
        │
        └── (future: narrative-memory rows keyed on Episode,
                     Relationship-history rows keyed on Episode,
                     unresolved-thread rows keyed on Episode)

Legacy path (unchanged):
Workspace
  └── Teammate (no Universe)
        └── Composition (no Episode) — historical, functions as today
```

Key cardinalities:

- Universe : Episode = 1 : N.
- Episode : Composition = 1 : N (0..N).
- Composition : Episode = N : 1 (0..1; NULL means legacy).
- Episode : Script = 1 : N (Script FK on Episode, optional).
- Script : Composition = 1 : N (Composition may render from a Script
  or from operator prompt directly).
- PublishBundle : Composition = N : 1 via
  `bundle.source_clip.composition` (transitive; no direct FK).

## Composition vs Episode responsibility matrix

Columns:
- **Composition** — the render-attempt/variant row (per-run scope).
- **Episode** — the narrative-event row (per-story scope).
- **Elsewhere** — attaches to a different primitive (Asset,
  Universe, Teammate, memory substrate, etc.).

| Concern | Composition | Episode | Elsewhere |
|---|---|---|---|
| Workspace tenancy | direct FK | direct FK | (existing everywhere) |
| Universe scope | transitive via Episode | direct FK | Teammate/KnowledgeDocument (per UNIVERSE_BOUNDARY_V1) |
| Operator topic (verbatim) | — | own | — |
| Episode title | — | own | — |
| Sequence / order within Universe | — | own | — |
| Cast (N teammates) | — | own (M2M) | — |
| Primary performer of THIS render | own (`spokesperson` FK) | — | — |
| Recipe kind (talking_head, dialogue_scene, long_form_ad, …) | own (`template_kind`) | — | — |
| Render state (draft/planning/running/completed/failed) | own (`status`) | — | — |
| Render error message | own (`error_message`) | — | — |
| Final Asset (produced clip) | own (`final_asset` FK) | — | Asset (row) |
| Per-step primitive log | own (`CompositionStep`) | — | — |
| Cost estimate / actual | own | — | — |
| Mock mode | own | — | — |
| Media-engine task IDs | own (per-step) | — | — |
| Synthesized brief (this render's assembled text) | own (`synthesized_brief`) | — | — |
| Rejected synthesis (this render's blocked text) | own (`rejected_synthesis`) | — | — |
| Knowledge chunk IDs used (this render) | own (`knowledge_chunk_ids`) | — | — |
| Verifier status / warnings (this render) | own | — | — |
| Writing-contract version (this render) | own | — | — |
| First-pass output (per-attempt) | own (SESSION 259 backlog fix) | — | — |
| Corrective-hint (per-attempt) | own (SESSION 259 backlog fix) | — | — |
| Retry count (per-attempt) | own (SESSION 259 backlog fix) | — | — |
| Retrieval snapshot on failure | own (SESSION 259 backlog fix) | — | — |
| Prompt trace (per-attempt LLM calls) | own (or via future LLMCallEvent, audit §15) | — | future observability model |
| Canon flag / canonical status | — | own (future slice) | — |
| Prior-Episode callback edges | — | own (future) | — |
| Location reference | — | own (future, when Location exists) | Universe (Location entity) |
| World-object references | — | own (future) | Universe (WorldEntity) |
| Story events (structured) | — | referenced from | memory substrate keyed on Episode |
| State changes (character learned X) | — | referenced from | memory substrate keyed on Episode |
| Unresolved threads / promises | — | referenced from | future thread-ledger keyed on Episode |
| Relationship changes | — | referenced from | Relationship substrate keyed on Episode |
| Educational objective / audience / purpose | — | own (future) | — |
| Script (authored words) | (rendered from) FK optional | (authored for) FK optional | Script (existing model, gains Episode FK) |
| PublishBundle | (source clip transitively via Asset.composition) | — | PublishBundle (Asset-anchored, unchanged) |
| PublishVariant | — | — | PublishBundle child (unchanged) |
| Created-by user | own | own | — |
| Timestamps | own | own | — |

## Lifecycle: operator topic → Episode → synthesis → Composition → render → publish

1. **Operator conceives topic.** In the SPA, the operator picks a
   Universe and types a topic ("Patch and Rivet argue about the AI
   takeover"), picks a cast (Patch + Rivet from that Universe's
   Teammates), optionally picks a recipe (`dialogue_scene`,
   `talking_head`, `long_form_ad`), optionally names it.
2. **Episode row is created** in the chosen Universe with
   `operator_topic` verbatim, cast M2M populated, title = operator
   input or derived, sequence = next in Universe. Episode is
   persisted BEFORE any render fires.
3. **Composition is created for this Episode.** The Composition
   inherits its recipe kind, its workspace (=Episode.workspace),
   its primary spokesperson (from cast — for `dialogue_scene` this
   is the primary/secondary the operator picked), and gains a
   nullable Episode FK. `template_kind`, `mock_mode`, `created_by`,
   cost estimate populated at create time.
4. **Synthesis runs.** K6 uses `episode.operator_topic` as the
   verbatim topic. Knowledge retrieval is Universe-scoped per
   UNIVERSE_BOUNDARY_V1 (retrieval filters on
   `document.universe = teammate.universe`; empty-M2M means
   "everyone in the same Universe as this doc"). Synthesis output
   lands in `composition.synthesized_brief`.
5. **Verifier runs.** `verification_status` + `verification_warnings`
   populated on the Composition. Strict-mode blocks the composition
   at `status=failed` with `rejected_synthesis` populated. Warn / off
   modes allow the render to proceed.
6. **Render runs.** CompositionSteps execute in order.
   `final_asset` is set when the last step lands.
   `cost_actual_micros` sums from steps.
7. **Publish** (optional). Operator creates a PublishBundle keyed on
   the `Asset(role=CLIP)` produced by the Composition. Bundle owns
   its variants; no Episode FK on the bundle.
8. **Retry / rerender / variant** (any of these):
   - Operator clicks retry after a failed synthesis or render → a
     NEW Composition is created FKing the SAME Episode.
   - Operator requests a 30s cutdown of a 90s Episode → a new
     Composition is created with a different `target_duration_seconds`
     kwarg, FKing the same Episode.
   - Operator requests a 9:16 aspect variant → a new Composition is
     created with a different aspect kwarg, FKing the same Episode.
   - Operator requests a rerender with a different backdrop → a new
     Composition is created with a different backdrop kwarg, FKing
     the same Episode.
   - Every one of these leaves `episode` unchanged. The story
     happened once; the render was executed N times.
9. **Canon promotion** (future). Operator explicitly marks the
   Episode canonical; the Episode's memory/relationship rows become
   authoritative. Not implemented in v1.

## Failure / retry behavior

- **Synthesis fails before render** — Composition is
  `status=failed`, `rejected_synthesis` populated (Strict-mode),
  `verification_warnings` populated (Warn/Strict). Episode still
  exists, unchanged. `operator_topic` is preserved because it lives
  on the Episode.
- **Render fails mid-pipeline** — Composition is `status=partial` /
  `failed`. Any completed step's `output_asset` and cost persist.
  Episode unchanged.
- **Operator retries** — new Composition row, FK to same Episode.
  No narrative duplication.
- **All Compositions for an Episode fail** — Episode exists with
  zero successful renders. Operator can inspect the failed
  Compositions individually to see what went wrong; the Episode's
  intent is still recorded.
- **Composition deleted** — SET_NULL or PROTECT on
  `composition.episode` FK (schema-slice call); Episode survives.
- **Episode deleted** — CASCADEs to future narrative-memory /
  relationship rows attached to it. Composition FKs SET_NULL (or
  PROTECT if operator policy demands narrative-history preservation
  block deletion of Episodes with successful renders — TBD in
  schema slice).
- **Universe deleted** — deferred; per UNIVERSE_BOUNDARY_V1 the
  Universe delete/archive lifecycle is not designed here.

## Product-example walkthrough

### A. Patch + Rivet — "AI took over the lab" (rejected then rerendered)

- Universe: `patch-rivet-workshop`.
- Operator types topic "AI took over the lab. Rivet warns Patch
  it'll fire the humans; Patch is skeptical." Cast: Patch + Rivet.
  Recipe: `dialogue_scene`.
- **Episode 1** created in `patch-rivet-workshop` Universe. Title:
  "AI took over the lab." `operator_topic` = verbatim above. Cast
  M2M = {Patch, Rivet}. Sequence = 1.
- **Composition 1a** created FKing Episode 1. K6 synthesizes;
  verifier flags a hallucinated claim (Strict mode).
  `rejected_synthesis` populated, `status=failed`,
  `verification_warnings` populated.
- Operator inspects the rejected synthesis, tweaks the topic
  slightly, hits retry.
- **Composition 1b** created FKing Episode 1. K6 synthesizes;
  verifier passes. Render runs; `final_asset` = the 90s dialogue
  clip.
- Result: **one Episode, two Compositions (one failed, one
  succeeded).** Narrative history correctly says "the AI takeover
  scene happened once" — not twice.

### B. First-grade teacher — "why plants need sunlight" (90s + 30s recap)

- Universe: `mrs-alvarez-first-grade`.
- Operator types topic "Ms. Alvarez explains why plants need
  sunlight; introduces chloroplasts at kid level." Cast:
  Ms. Alvarez. Recipe: `talking_head_with_backdrop`. Educational
  objective (future field): "photosynthesis intro."
- **Episode 1** created. `operator_topic` = verbatim above. Cast M2M
  = {Ms. Alvarez}. Sequence = 1.
- **Composition 1a** created for the 90s version. Renders. Success.
- A week later the operator wants a 30s recap for a follow-up
  lesson.
- **Composition 1b** created FKing Episode 1 with
  `target_duration_seconds=30` and possibly a different
  `template_kind` variant. Uses the same operator_topic (inherited
  from Episode). Renders. Success.
- Result: **one Episode ("photosynthesis intro"), two Compositions
  (90s + 30s).** The learning objective is a property of the Episode,
  unchanged.

### C. Plumbing company — "apprentice misdiagnosed low water pressure" (rerender with different visual background)

- Universe: `pipewise-plumbing`.
- Operator types topic "Ricky (apprentice) misdiagnoses low water
  pressure as a broken pump; Bea (senior) walks him through the
  diagnostic order." Cast: Ricky + Bea. Recipe: `dialogue_scene`.
- **Episode 1** created.
- **Composition 1a** renders with Backdrop Asset A (a truck cab).
- Later: operator decides the truck cab distracts from the
  educational content. Wants to rerender with a shop-floor backdrop.
- **Composition 1b** created FKing Episode 1 with a different
  `backdrop_clip_id`. Same synthesized brief may be reused (Script
  attached to Episode; Composition 1b renders from same Script);
  Runway generates the new render.
- Result: **one Episode, two Compositions (same story, different
  visual treatment).** The apprentice-lesson event happened once.

### D. Simple legacy spokesperson — single talking-head video, no continuity

- Universe: **NONE** (legacy). Teammate has no `Universe` FK.
  Composition created before Episode existed OR after Episode
  existed but operator declined to pick a Universe.
- Under the recommended model:
  - Legacy path: Composition has no Episode FK. Behaves as today
    (Workspace-scoped, `spokesperson` FK, `template_kind`,
    `synthesized_brief`, all the per-render content-provenance
    fields). Operator sees a normal talking-head render row.
  - Post-Episode default path (once Episode ships): operator picks
    a Universe. An auto-created Episode wraps the render, but with
    minimal ceremony — SPA UX may hide the Episode surface entirely
    for a single-Composition talking-head use case ("Just a video,
    no story continuity") if operator has never interacted with
    Episodes for this Universe. The Episode is created because it
    is the durable home for `operator_topic`, but it does not force
    the operator to think about world-building.

**Critical property preserved:** the simple talking-head-video
operator does NOT need to understand Episodes, canon, memory, or
narrative continuity. The Episode layer is opt-in visibility; every
render still produces a Composition + Asset the operator can watch,
publish, and forget. Episode surfaces as a first-class concept only
when the operator has multi-render or multi-variant patterns worth
grouping.

## Legacy behavior

- Historical Compositions (81 in `chriss-workspace`, per SESSION 259
  audit §3) stay put with `episode=NULL`. They function as today:
  Workspace-scoped render-provenance rows.
- Legacy `Composition.name` and `Composition.template_kind` retain
  their current inconsistent meaning; no rewrite.
- No bulk auto-wrap into per-Composition "Episode of one" rows
  (rejected as a mirror of UNIVERSE_BOUNDARY_V1 §Q8's rejection of
  auto-default Universe).
- Legacy Compositions MAY be assigned to a new Episode later as a
  bespoke per-Composition ½-slice by the operator (mirrors
  UNIVERSE_BOUNDARY_V1 legacy-migration posture).
- New Compositions created after Episode ships MUST belong to an
  Episode. The Episode may be auto-created at Composition-create
  time if the operator did not pick one, but it is a visible,
  editable row — not a silent default.
- Retrieval, synthesis, publish, and every consumer path must
  handle both regimes: `episode` present (Universe-scoped
  transitively) and `episode` absent (Workspace-scoped legacy).

## Universe scoping implications

- Episode carries a direct Universe FK (NOT NULL). Every new Episode
  lands in exactly one Universe (or the introduction of Episode is
  gated behind the operator first creating a Universe — TBD in the
  SPA slice).
- Composition acquires transitive Universe scope through its
  Episode FK. Composition's own direct Universe FK stays deferred
  (UNIVERSE_BOUNDARY_V1 §Q5 / Q17); Episode is the direct anchor.
- Legacy Compositions with `episode=NULL` remain Workspace-scoped
  legacy; they do NOT gain Universe scope by accident. Same rule
  as UNIVERSE_BOUNDARY_V1 §Q9 (legacy isolation invariant).
- Cast M2M on Episode must reference only Teammates in the same
  Universe as the Episode. Attaching a cross-Universe teammate is
  rejected at `clean()` and via `m2m_changed pre_add` signal
  (mirrors the workspace-cross-check patterns in
  `apps/embeddings/signals.py:31–79` and
  `KnowledgeDocument.clean()`).
- Knowledge retrieval during Episode's synthesis uses the
  Universe-scoped retrieval path (UNIVERSE_BOUNDARY_V1 §Q9):
  `document.universe = episode.universe`; empty-M2M docs in that
  Universe are default-visible; legacy Workspace-wide docs are
  NOT visible to Universe-scoped Episodes.
- Script (if attached to an Episode) inherits Universe scope
  transitively through the Episode.
- PublishBundle stays Workspace-scoped (Asset is the anchor); no
  Universe FK on PublishBundle in v1.

## Isolation invariants

Restated to preserve — some existing (from Workspace / Universe
boundaries), some new (from Episode):

1. **Workspace privacy invariant (existing, preserved).** No data
   crosses Workspace boundaries under any circumstance. Every
   existing defense-in-depth mechanism stays in force.
2. **Universe privacy invariant (existing, preserved).** No data
   crosses Universe boundaries within a Workspace. Extends to
   Episode: an Episode's Compositions, cast, script, and future
   memory/relationship rows are all Universe-consistent with the
   Episode.
3. **Episode-Workspace consistency (new).**
   `Episode.workspace == Episode.universe.workspace`. Enforced at
   `clean()`.
4. **Episode-Composition consistency (new).** For any Composition
   with a non-NULL Episode FK:
   `composition.workspace == episode.workspace` AND
   (when `composition.spokesperson.universe` is non-NULL)
   `composition.spokesperson.universe == episode.universe`.
5. **Cast-Universe consistency (new).** Every Teammate in
   `Episode.cast` M2M has `teammate.universe == episode.universe`.
6. **Cross-Universe crossover forbidden (existing, preserved).** An
   Episode cannot reference a Composition rendered by a teammate
   from another Universe. If crossover is ever required, it is an
   explicit primitive with its own name and audit trail
   (UNIVERSE_BOUNDARY_V1 invariant 5).
7. **Rerender does not duplicate narrative history (new).** Adding
   a new Composition to an existing Episode is not a narrative
   event. The Episode row is unchanged; only the Composition set
   grows. Narrative-memory / relationship-history rows attached to
   the Episode do NOT proliferate.
8. **Legacy-Composition isolation (new, mirrors UNIVERSE_BOUNDARY
   Q9).** A legacy Composition with `episode=NULL` never
   participates in Episode-scoped invariants. It functions under
   pre-Episode Workspace-scoped semantics.
9. **Per-attempt evidence isolation (existing, preserved).**
   `synthesized_brief`, `rejected_synthesis`,
   `verification_status`, `verification_warnings`,
   `writing_contract_version`, `knowledge_chunk_ids`,
   `cost_actual_micros` are per-Composition-attempt values. They
   never migrate to Episode. The Episode reads its narrative content
   through the currently-primary Composition (v1: whichever is
   most recent successful; future: an explicit
   `Episode.canonical_composition` FK).
10. **No implicit crossing primitive (existing, preserved).**
    Retrieval, synthesis, composition, and realtime code paths MUST
    NOT expose any workspace-override, Universe-bypass, Episode-
    bypass, "see all worlds" flag, or debug bypass.

## Intentionally deferred

- Schema DDL, migration plan, Django field additions.
- Canon promotion mechanic (Episode canonical lifecycle).
- Narrative-memory substrate (event log / promise ledger shape).
- Relationship-history persistence.
- Unresolved-thread tracking / promise ledger.
- Prior-Episode callback edges (graph model of cross-Episode
  references).
- Location / Scene / Set entity design (UNIVERSE_BOUNDARY_V1 §D3).
- Cast / Ensemble grouping design as a first-class shared row
  distinct from Episode.cast (UNIVERSE_BOUNDARY_V1 §D4).
- Educational objective / audience / purpose fields on Episode.
- `Episode.canonical_composition` FK to designate the definitive
  render variant.
- Composition observability backlog fixes (`operator_topic` on
  Composition itself, per-attempt log, retry count, corrective-hint,
  first-pass output). Those are SESSION 259 fixes that should ship
  independently — this doc identifies which are Composition-level
  (all of them, at the render-attempt layer) and which belong on
  Episode (only the semantic `operator_topic` field belongs on
  Episode; Composition may still carry a copy for legacy /
  Episode-less rows).
- SPA UX for Episode (creator, picker, list, canon promotion,
  merge/split, hiding Episode UI for simple single-render use
  cases per example D).
- Script's exact FK to Episode (schema slice; posture is optional
  FK).
- Cascade policy on `Composition.episode` delete (SET_NULL vs
  PROTECT).
- Cross-Universe crossover primitive design.
- Composition ordering within an Episode (creation-time monotonic
  vs operator-orderable vs primary-plus-variants).

## Unresolved questions created by this decision

1. Should Composition retain a copy of `operator_topic` for legacy
   (Episode=NULL) rows, or is the durable topic home ONLY the
   Episode? Position: Composition should ALSO gain `operator_topic`
   as a SESSION 259 backlog fix independent of Episode, so legacy
   rows and per-attempt provenance both carry it; Episode's
   `operator_topic` is the narrative-authoritative copy.
2. When the operator retries after a failed synthesis with a
   modified topic, does the Episode's `operator_topic` update
   (narrative intent evolved) or does a new Episode get created
   (story diverged)? Product decision: probably "update when small,
   fork when large" — SPA UX to prompt. Not resolved here.
3. What's the SPA affordance for creating an Episode implicitly vs
   explicitly? For the simple talking-head operator (example D),
   Episode must be near-invisible; for the storyteller (example A),
   it must be first-class. This is a UX slice.
4. Does `Episode.cast` M2M supplant `Composition.spokesperson`, or
   coexist? Position: coexist. Composition.spokesperson names the
   primary performer of THIS render (for cost, primary-anchoring in
   dialogue, single-character templates); Episode.cast names who
   the STORY is about. They usually overlap but not always
   (narrator vs on-screen character, off-screen voice, etc.).
5. What is the cascade policy on `Composition.episode` when Episode
   is deleted? SET_NULL preserves render provenance; PROTECT blocks
   Episode deletion if any Composition attached; a policy that
   requires the operator to detach or delete Compositions first is
   most operator-honest. Deferred to schema slice.
6. Does auto-creating an Episode at Composition create-time (Q16)
   ever surface as a silent default in the SPA? If yes, it repeats
   the UNIVERSE_BOUNDARY_V1 §Q8 mistake. SPA must always show the
   Episode row exists, even for single-Composition renders.
7. Do we need a "primary Composition" designation on Episode in v1
   for the SPA to show a canonical thumbnail, or is
   most-recent-successful a sufficient rule?
8. Should Script's `revision_history` (snapshot-on-regenerate)
   become an Episode-level draft history, or stay Script-level?
   Position: stay Script-level (Script is the authoring artifact,
   Episode is the narrative intent).
9. What is the operator-facing name for Episode in the SPA?
   ("Episode" carries TV-show connotations; some product surfaces
   might want "Story," "Beat," "Scene." Naming is a UX slice.)
10. When Cast becomes a first-class primitive (deferred), does
    `Episode.cast` M2M reference `Cast` rows or continue referencing
    `Teammate` rows directly?

## STOP

Design-only. No schema. No migrations. No code. Every load-bearing
claim is cited to file:line or to CAPABILITY_INVENTORY_SESSION_261.md
/ UNIVERSE_BOUNDARY_V1.md / SESSION 259 handoffs.
