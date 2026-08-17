---
title: "Episode Lifecycle v1 — When Does an Episode Come Into Existence?"
status: research — Episode boundary challenge (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"  # this slice CHALLENGES its auto-creation proposal
scope: >
  Answer one question — when does an Episode row come into existence?
  Take a position. Correct the prior slice where it was wrong. Do not
  design Universe, Location, Relationship, Cast, or Narrative Memory
  except where absolutely necessary to establish the Episode boundary.
---

# Episode Lifecycle v1 — When Does an Episode Come Into Existence?

## Purpose

`EPISODE_VS_COMPOSITION_V1.md` decided **Option B — Episode wraps
Composition, two models, Episode above**. That decision stands and is
not revisited here. The prior slice then made a secondary claim it did
not stress-test:

> "New Compositions after Episode ships MUST belong to an Episode. An
> Episode is auto-created at Composition-create time if the operator
> did not explicitly pick one — but this Episode is operator-visible,
> editable, and can be titled / merged / split later. Auto-creation is
> a UX convenience; it never means 'silent.'"
> — EPISODE_VS_COMPOSITION_V1.md §Q16, echoed in §Legacy, §Lifecycle,
> and §Unresolved-Q6.

This slice challenges that claim against the same argument
`UNIVERSE_BOUNDARY_V1.md` §Q8 used to reject auto-default Universe:

> "Auto-creating a 'default Universe' per workspace … re-creates the
> exact overload the audit surfaced. Nothing improves. The correct
> posture is Universe is opt-in and prospective."
> — UNIVERSE_BOUNDARY_V1.md §Q8, §Corrections-to-hypothesis (1).

If the same operator-facing argument holds for Episode, the prior
slice is wrong by its own precedent, and this doc says so plainly.

## Load-bearing principle (legacy ≠ Universe semantics)

> **Legacy character data informs compatibility; it does not define
> Universe semantics.**

Corollaries carried through this slice:

- Patch and Rivet are the first *intentional* recurring-Universe
  dogfood. They set the Episode-worthy shape.
- Ruby the Fox and Mason the Bear can live in a Universe *despite
  currently having little or no knowledge*. A character exists in a
  Universe; knowledge is available *to* the character; knowledge is
  not what defines the character's existence.
- Mike-the-plumber, Repo Red, Tulsi are *compatibility evidence*, not
  Universe-semantics inputs. Their historical talking-head cadence
  must survive Episode's arrival — but their workflow must not be
  what determines whether Episode auto-creates.
- Historical Compositions may remain Episode-less indefinitely
  (mirrors `UNIVERSE_BOUNDARY_V1.md` §Q6 "prospective introduction,
  no bulk migration"; already ratified in
  `EPISODE_VS_COMPOSITION_V1.md` §Q16 first paragraph).

## Scope (and what's deferred)

**In scope.** The single question **"when does an Episode row come
into existence?"** and its immediate consequences: retry semantics,
revision semantics, `operator_topic` placement, the minimum Episode
v1 boundary, and the correction to `EPISODE_VS_COMPOSITION_V1.md`
auto-creation.

**Deferred (unchanged from prior slices).** Schema DDL, migrations,
Django field additions; narrative-memory substrate; canon promotion
mechanic; relationship-history persistence; unresolved-thread
tracking; educational-objective / audience fields on Episode;
Location / Scene / Set entity; Cast as a first-class shared row;
SPA UX beyond the ½-slice affordance for "attach to Episode";
cross-Universe crossover primitive; cascade-policy resolution on
`Composition.episode` delete.

## Hypotheses (H1–H5) stated

**H1 — Episode is created ON TOPIC.**
The moment the operator expresses topic intent in the SPA (types a
premise, picks a cast, picks a recipe, before pressing render), an
Episode row is written. Composition follows and FKs it.

**H2 — Episode is created ON RENDER.**
The Episode row is written at the same moment the Composition row
is written (i.e. `POST /compositions/`, before or inside the same
transaction as `Composition.objects.create()`). The two rows are
co-created; the operator does not see an Episode-picker upstream.

**H3 — Episode is created EXPLICITLY.**
The operator has a first-class "New Episode" action separate from
"New video." Episodes never come into existence as a byproduct of
generation. Composition can be attached to an existing Episode at
render-time, or can remain Episode-less if the operator does not
attach it.

**H4 — Episode is created LAZILY / RETROSPECTIVELY.**
Composition always comes into existence first. An Episode row is
materialized only when the operator later says "these renders belong
to a story" — either by picking a second Composition as "part of the
same story" or by clicking "promote to Episode" on a single
Composition.

**H5 — Episode is AUTO-CREATED per Composition (the prior slice's
proposal).**
Every new Composition (after Episode ships) auto-creates an Episode
row if the operator did not explicitly pick one. The Episode is
"always visible, never silent" but the operator did not consciously
author it. This is the proposal `EPISODE_VS_COMPOSITION_V1.md` §Q16
made and that this slice challenges.

## Product examples (P1–P5) stated

- **P1 — Ruby-the-Fox self-intro.** One talking-head video. Not a
  story. Low knowledge on the character. Operator intent: "make a
  video of Ruby introducing herself." Success = one clip.
- **P2 — Mike-the-plumber weekly TikTok.** Legacy spokesperson
  cadence. Operator uploads talking-head roughly every week. There
  is no arc, no callback, no continuity. Success = 52 clips per
  year, indexable and findable, not "52 Episodes."
- **P3 — Patch + Rivet, "AI took over the lab."** Genuine story.
  First synthesis fails (Strict K6.4 rejects an unsupported claim).
  Operator inspects rejected synthesis, tweaks the topic, retries;
  second synthesis passes; renders successfully. Later, operator
  asks for a 30s cutdown of the same story.
- **P4 — Ruby + Mason, "meets at the ravine" (future).** Genuine
  story. Both characters have low personal knowledge corpora. The
  Episode's premise, cast, and continuity carry the story — not a
  large knowledge base.
- **P5 — "Continue what happened last episode with Patch + Rivet"
  (future).** Operator returns and asks for a new story that
  references Episode 1's ending. The system must be able to say
  "which Episode do you mean" and load the prior Episode's identity.
  Narrative memory / callback design is deferred, but the Episode
  boundary must not preclude this.

## Hypothesis × Example matrix

Cells describe outcome under each hypothesis; **bold** cells flag
regressions or false-story creation.

| Hypothesis | P1 Ruby intro (1 video, no story) | P2 Mike weekly (52 videos, no story) | P3 Patch+Rivet retry + cutdown | P4 Ruby+Mason ravine (future story) | P5 "continue last episode" |
|---|---|---|---|---|---|
| **H1 On topic** | Episode created before render even though no story exists. **Ruby's intro becomes an "Episode" with no continuity meaning.** | **52 Episodes/year of one-video each.** Same overload UNIVERSE §Q8 rejected. | Episode created on topic entry; retry & cutdown FK the same Episode. Clean. | Episode created on topic; renders follow. Clean. | Operator picks prior Episode from a list; new Episode created on new topic entry, callback edge to prior. Clean. |
| **H2 On render** | Episode co-created at Composition-create. Same problem as H1. **Ruby's intro is an Episode.** | **52 Episodes/year.** Identical overload to H1/H5. | Composition + Episode co-created on first attempt. Retry creates NEW Composition FKing existing Episode. Cutdown same. Works, but the operator never got a chance to say "this is a story." | Same. Works but conflates. | Prior Episode must be picked at render-time; UX pressure to attach or auto-create-new. Ambiguous. |
| **H3 Explicit** | No Episode. Composition stands alone with `operator_topic` on itself. **Zero cognitive overhead on the operator.** Correct. | No Episodes; 52 Compositions, each with `operator_topic`. Findable by search/tag. Correct. | Operator creates Episode "AI took over the lab" first, then generates. Retry & cutdown attach. Explicit intent matches explicit story. Correct. | Operator creates Episode "Ravine encounter" first, then generates. Correct. | Operator picks the existing Episode as parent for a new Composition, OR creates a new Episode "Ravine, part 2" with a callback FK to Episode 1. Correct. |
| **H4 Lazy** | No Episode ever. Correct — but requires per-Composition `operator_topic` regardless of Episode. | No Episodes. Correct. | Composition 1a fails → Composition 1b succeeds → operator says "these two are the same story" → Episode materializes with both attached. **Fragile:** if operator forgets, story never groups. Also: what does "cast" mean on an Episode assembled after the fact? Reconstructed from `CompositionStep.params` (already fragile per prior audit §13). | Operator generates one video, then another, then says "these are the same story." Works but the story-ness is retroactive. Not how storytellers plan. | Operator has to first materialize an Episode from prior Compositions before referencing it. Two-step; friction. |
| **H5 Auto per Composition (prior slice)** | **Ruby's intro auto-gets an Episode.** Permanent noise; the Episode is never meaningful. | **52 auto-Episodes per year of one-Composition each.** Exact overload UNIVERSE §Q8 rejected for Universe. | Composition 1a auto-gets Episode. Composition 1b (retry) must FK that Episode. Composition for cutdown FKs the same Episode. Works — but the same shape H2 achieves with less scaffolding. | Same as P3 pattern; works but auto. | Auto-created Episodes are unnamed / operator-titled defaults; picking "the right one to continue" is fuzzy because dozens of auto-Episodes exist. |

**Reading the matrix.** H3 is the only hypothesis that handles P1
and P2 without inventing story rows, AND handles P3–P5 correctly.
H1, H2, and H5 all fail P1 + P2 the same way `UNIVERSE_BOUNDARY_V1`
§Q8 said auto-default Universe would fail — by creating permanent
noise for the simple case. H4 handles P1/P2 correctly but is fragile
on P3–P5 (retroactive grouping is not how operators plan a story).

## Challenge to auto-creation (mirror UNIVERSE_BOUNDARY §Q8)

`UNIVERSE_BOUNDARY_V1.md` §Q8 rejected auto-default Universe with:

> "The correct posture is Universe is opt-in and prospective. Legacy
> Teammates without a Universe continue to use today's semantics.
> New teammates land in an explicitly chosen Universe (created at
> teammate-create time if none exists, but chosen — not
> auto-assigned to a default)."

Apply that identical reasoning to Episode:

| §Q8 argument (Universe) | Same argument applied to Episode |
|---|---|
| Auto-default Universe recreates the workspace overload — one bucket per tenant. | Auto-per-Composition Episode recreates a render-job overload — one bucket per render. Same operator-facing "which one is real" problem, at 50–100x the row count. |
| The operator sees one Universe in the SPA and repeats the pattern. Nothing improves. | The operator sees N Episodes (one per Composition), can't tell which are stories vs which are Ruby's intro / Mike's weekly, and treats Episodes as noise. Nothing improves; it's worse because there are more rows. |
| Legacy Teammates without a Universe continue to work under legacy semantics. | Legacy Compositions without an Episode continue to work under legacy semantics — already ratified in `EPISODE_VS_COMPOSITION_V1.md` §Q16 first paragraph. Good. |
| New Teammates land in an *explicitly chosen* Universe. | New Compositions attach to an *explicitly chosen* Episode, or stand alone with `operator_topic` on the Composition. |
| Universe is *opt-in and prospective*. | Episode should be *opt-in and prospective*, for the same reasons. |

**The prior slice's auto-creation proposal is wrong by its own
precedent.** It re-introduces exactly the overload
`UNIVERSE_BOUNDARY_V1.md` rejected. If a Universe should not be
auto-created every time a Teammate is created, then an Episode
should not be auto-created every time a Composition is created — and
for the operator-facing reason (noise, indistinguishability, "which
one is real"), not for a technical reason. This slice **corrects
`EPISODE_VS_COMPOSITION_V1.md` §Q16 auto-creation and §Lifecycle
step 2** (see "Correction" section below).

## Q1–Q12 answered

### Q1. Should Episode exist as soon as the operator expresses intent/topic, or only once generation begins?

**Neither, when the operator hasn't opted in.** Episode is
explicit-only (H3). When the operator explicitly creates an Episode
(via a "New Episode" action or by attaching a render to an existing
Episode), it exists as soon as they say so — which is *before*
generation begins (giving Episode the durable home for
`operator_topic` in the story case). When the operator did not
explicitly create an Episode, no Episode row is written at all; the
Composition carries `operator_topic` on itself.

### Q2. If synthesis fails before any provider/render steps execute, should the failed attempt still belong to the same Episode?

**Yes — if the Composition was attached to an Episode when created.**
Today, dialogue AI-Topic mode raises `DialogueSynthesisFailedError`
before any avatar_video primitive fires, and the view creates the
FAILED Composition row *outside* the atomic (`shell/apps/compositions/
views.py:502–563`). The failed row is a real Composition. Under H3,
if the operator attached the render to Episode E when submitting,
the failed Composition's `episode` FK is set the same way a
successful Composition's would be. Failed-before-render is still
one attempt within the Episode's attempt history. When there was no
Episode attachment, the failed row stands alone with its
`operator_topic` — exactly like the successful case.

### Q3. If the operator retries the exact same topic, does that create another Composition under the existing Episode, or a new Episode?

**New Composition under the existing Episode.** Retry semantics were
already ratified in `EPISODE_VS_COMPOSITION_V1.md` §Q7, §Q8, §Q14
and §Product-example A. This slice preserves them: Episode 1 gains
Composition 1b (retry) FKing the same Episode 1 row. The Episode
is unchanged. Same for aspect variant, cutdown, translation,
alternate backdrop. See §Retry decision table below.

### Q4. If the operator modifies the topic after a failed attempt, what distinguishes: revision of the same Episode / a new Episode / a new Composition variant?

**Three cases, three outcomes:**

1. **Small clarification** ("add: Rivet mentions the lab robot"):
   the Episode's `operator_topic` may evolve *iff* the operator is
   editing the Episode's story-level intent. Composition 1b renders
   from the updated topic. Same Episode. (This is a
   deliberate-editing gesture on Episode; not a byproduct of retry.)
2. **Substantial rewrite** ("actually, make it Rivet warning Patch
   about the coffee machine instead"): operator creates a new
   Episode with a new title and `operator_topic`. Old Episode still
   holds Composition 1a; new Episode holds Composition 1b. The two
   are distinct story events; both are legal.
3. **Same story, alternate render treatment** (different backdrop,
   different aspect, different length): new Composition FKing the
   same Episode with different kwargs. Episode's `operator_topic`
   unchanged. Story happened once; render executed N times.

The SPA is the arbiter — the operator's UI action ("edit topic" vs
"new Episode" vs "new render variant") drives the outcome. There is
no heuristic that infers "small vs substantial" from text-diff. See
§Retry decision table.

### Q5. Is the Episode the operator's creative intent/story unit, or merely a container automatically created around Compositions?

**Creative intent unit.** Under H3, Episode's *existence* is itself
the operator saying "this is a story." An automatically-created
Episode is a container, not an intent — which is why H5 fails P1 and
P2. Episode = intent. No Episode = "just a video." This is the load-
bearing distinction; the entire Episode primitive is worth nothing
if it doesn't preserve this split.

### Q6. Should Episode creation be explicit in UI/domain workflow, implicit/automatic, or hybrid?

**Explicit. Not hybrid.** Hybrid was the prior slice's proposal
("auto but visible") and it fails P1/P2 identically to fully
automatic. There is no meaningful UX difference between "auto-created
but shown" and "auto-created and hidden" once N=52; both drown the
operator in unhelpful rows. The two clean paths are:

- Operator clicks "New video" → Composition only, `operator_topic`
  on the Composition. (P1, P2.)
- Operator clicks "New Episode" → Episode row exists first; when
  the operator generates from within the Episode context, the
  resulting Composition is auto-FK'd to that Episode. (P3, P4, P5.)

The second path *does* auto-populate the FK on the Composition —
that's not auto-creation of Episode, it's auto-attachment when the
operator is already inside an Episode context. Different action.

### Q7. What is the smallest Episode state needed BEFORE generation?

Questioning each field the prior slice named:

- **Universe FK** — YES, required, NOT NULL. Episode is a
  Universe-scoped narrative primitive (`EPISODE_VS_COMPOSITION_V1.md`
  §Universe-scoping-implications, §Isolation-invariants 3).
- **Workspace FK** — YES, denormalized for privacy defense-in-depth,
  must equal `episode.universe.workspace` (invariant 3 same doc).
- **`operator_topic` (verbatim)** — YES. Story intent is
  meaningless without the operator's original words. See §
  operator_topic placement below.
- **Title** — YES, but may derive from `operator_topic` at create
  time and be operator-editable later. Not load-bearing pre-render.
- **Cast (M2M → Teammate, subset of Universe)** — **CHALLENGED.**
  The prior slice named cast at Episode-creation time. Reconsidering
  against P4 (Ruby + Mason with low knowledge) and P1/P2 (which don't
  reach Episode at all under H3): cast is arguably a *first*
  Composition concern; the Episode's cast is the union of casts
  across its Compositions. **Position:** in v1, Episode.cast M2M
  is present but MAY be empty at Episode-create; it is populated
  from the first Composition's cast if not explicitly set. This
  preserves "an Episode can exist before any render" (§Q10 of prior
  slice) without forcing the operator to enumerate cast upfront when
  the story is still forming. If the operator wants to nail down
  cast first, they can; the field accepts it.
- **Recipe kind / `template_kind`** — NO. Recipe is a render
  concern. One Episode can have multiple Compositions with different
  `template_kind`s (a `dialogue_scene` main render + a
  `talking_head` recap). Keep on Composition.
- **Status** — Deferred; see §Lifecycle states below. v1 Episode
  needs at most `active` / `archived` — not a full render-state
  machine (the render state stays on Composition).
- **Sequence marker** — NO in v1. Monotonic sequence assumes a
  linear arc; Episodes may be non-linear (parallel plotlines,
  flashbacks). Prior slice named it "sequence = next in Universe."
  Deferred — creation order and `created_at` are enough for v1.
- **Educational objective / audience / purpose** — deferred (already
  deferred by prior slice).

**Smallest v1 Episode state before generation:** Universe FK,
Workspace FK, `operator_topic`, title (may derive from topic),
`created_by`, `created_at`, `updated_at`, cast M2M (may be empty).
That's it.

### Q8. Which fields currently on Composition actually describe the creative event and might belong on Episode?

Only **`operator_topic`** (which does not currently exist —
SESSION 259 backlog §37–46). It describes the story intent, not the
render attempt. Move it to Episode when Episode exists; keep it as
a durable per-Composition field for legacy / Episode-less rows.

Every other narrative-content field named in
`EPISODE_VS_COMPOSITION_V1.md` §Q3 (`synthesized_brief`,
`rejected_synthesis`, `knowledge_chunk_ids`, `verification_*`,
`writing_contract_version`, `template_kind`) stays on Composition —
they describe what THIS render authored/attempted, not what the
story is. Prior slice's §Q3 position is preserved.

### Q9. Which Composition fields must remain execution-specific?

All of them except `operator_topic`. Enumeration:

- Workspace FK, spokesperson FK (performer role), `status`,
  `error_message`, `final_asset`, `cost_estimate_micros`,
  `cost_actual_micros`, `mock_mode`, `created_by`, timestamps,
  every `CompositionStep`, `template_kind`, `synthesized_brief`,
  `rejected_synthesis`, `knowledge_chunk_ids`, `verification_status`,
  `verification_warnings`, `writing_contract_version`.
- New (SESSION 259 backlog): `first_pass_output`,
  `corrective_hint`, `retry_count`, `retrieval_snapshot_on_failure`,
  and Composition-local `operator_topic` (the render-attempt
  provenance copy).

All of these describe attempts; none belong on Episode.

### Q10. Can this lifecycle be supported cleanly WITHOUT duplicating story state or corrupting history: `Universe → Episode intent → Composition attempt #1 fails → Composition attempt #2 renders → alternate Composition #3 renders`?

Yes, under H3. Concretely:

1. Operator creates Episode E in Universe U with `operator_topic
   = "AI took over the lab"`, cast may be empty.
2. Operator triggers generation from within Episode E's context.
   Composition C1 is created with `episode = E`, cast populated
   from the selected primary + secondary spokespeople; C1 goes
   through synthesis; synthesis fails; Composition rescue path in
   `views.py:538–563` persists C1 with `status=FAILED`,
   `rejected_synthesis` populated, `episode = E`.
3. Operator retries. Composition C2 is created with `episode = E`
   (inherited from Episode context or explicit attach); synthesis
   passes; render succeeds; `final_asset` set.
4. Operator asks for a 30s cutdown. Composition C3 is created with
   `episode = E`, `target_duration_seconds=30`, different
   `template_kind` variant if applicable; render succeeds.

Episode E is written once and never modified. Its
`operator_topic` is the durable story intent. Its Composition set
grows from 0 → 1 (failed) → 2 → 3 across the sequence. No
duplicated story state; no corrupted history; Composition-level
per-attempt provenance is preserved on C1 (rejected_synthesis,
verification_warnings), C2 (synthesized_brief, verification_status),
and C3 (its own synthesized_brief).

### Q11. What happens when an operator returns tomorrow and says "make another version of that episode"?

Operator navigates to Episode E in the SPA and clicks a "new
render / variant" action. Composition C4 is created with
`episode = E`, kwargs chosen by the operator (aspect, backdrop,
duration, cast override). Renders. `episode = E` on C4. No new
Episode row. No modification to E. Retrieval, synthesis, etc.
operate under E's Universe scoping and E's `operator_topic`.

### Q12. What happens when an operator says "continue what happened in the last episode"?

Explicit callback. Operator either (a) creates a new Episode E'
in the same Universe with `operator_topic` describing the
continuation and, in a future callback-substrate slice, an edge
`E' → E` marking the reference, OR (b) attaches Compositions
directly under E as "further scenes in the same story" if the
operator's mental model is one long story. v1 supports (a) as a
plain new Episode (the callback edge is deferred to
narrative-memory substrate); it supports (b) trivially because
Episode → Composition is already 1:N.

**What must Episode persist NOW to support future callback
without redesign?** Only what H3 already requires: `Universe FK`,
`operator_topic`, `title`, `created_by`, `created_at`. Any
future callback substrate resolves references through Episode.id —
so as long as Episode.id is stable and Episode.universe never
migrates cross-Universe, the substrate can be layered on later
without touching Episode itself. **Do NOT design narrative memory
here** (deferred per §Scope) — just confirm that H3's minimum
does not preclude it.

## Correction to `EPISODE_VS_COMPOSITION_V1.md`

**YES — this slice corrects the prior slice's auto-creation
proposal.**

**Where the prior slice was wrong:**

- §Q16 second bullet: "New Compositions created after Episode ships
  MUST belong to an Episode. An Episode is auto-created at
  Composition-create time if the operator did not explicitly pick
  one." — *Wrong.* This recreates UNIVERSE_BOUNDARY §Q8's rejected
  auto-default overload for exactly the reasons §Q8 named.
- §Lifecycle step 2: "Episode row is created … before any render
  fires" — *Wrong when applied to every Composition.* Correct only
  when the operator has explicitly created an Episode.
- §Legacy fifth bullet: "New Compositions … MUST belong to an
  Episode. The Episode may be auto-created …" — *Wrong,* same
  reason.
- §Unresolved-Q6: "Does auto-creating an Episode at Composition
  create-time (Q16) ever surface as a silent default in the SPA?"
  — This question is dissolved by rejecting auto-creation entirely.
  H3 has no silent default because it has no default at all.

**Where the prior slice was right and this slice preserves:**

- Option B (Episode wraps Composition, two models) — unchanged.
- Episode : Composition = 1:N; Composition : Episode = N:1 with
  optional (nullable) FK — unchanged.
- Historical Compositions remain Episode-less indefinitely
  (§Q16 first paragraph) — unchanged and reinforced.
- Composition retains all per-attempt content-provenance fields —
  unchanged.
- `operator_topic` on Episode when Episode exists — unchanged.
- Composition also carries `operator_topic` for legacy /
  Episode-less rows (§Unresolved-Q1) — unchanged; H3 makes this
  the *primary* home for the P1/P2 workflow and the *shadow* copy
  when Episode owns the story-level intent.

**Net correction, one line:** "MUST belong to an Episode
(auto-created if operator doesn't pick one)" → "MAY belong to an
Episode (only when the operator explicitly attached it or is
inside an Episode context)."

## Recommended Episode definition

> **Episode** — a Universe-scoped narrative event *conceived and
> named by the operator as a story*. Owns the story's verbatim
> `operator_topic`, its title, and its cast (as a subset of the
> Universe's Teammates; may be empty until first Composition
> attaches). Referenced by zero or more Compositions, each of
> which is one render attempt or variant of the story.
> **Episode's existence is itself the operator saying "this is a
> story."** No Episode is ever auto-created around a Composition.
> A Composition with no Episode is not a broken Episode — it is a
> video that is not part of a story.

## Recommended Episode lifecycle (states + transitions in prose)

Episode v1 has a minimal state model — deliberately narrower than
Composition's render-state machine because Episode is a
creative-intent primitive, not a job.

**States.**

- **DRAFT** — Episode exists (operator created it) but has zero
  attached Compositions. `operator_topic`, title, cast may be
  populated; no render has been attempted.
- **ACTIVE** — Episode has ≥1 attached Composition (successful or
  failed). This is the default working state through the Episode's
  whole life; retries, variants, and rerenders all leave the
  Episode ACTIVE.
- **ARCHIVED** — Operator explicitly retired the Episode. Its
  Compositions remain intact (SET_NULL or PROTECT policy deferred
  to schema slice); the Episode no longer surfaces in the default
  operator view. Reversible.

**Deferred states** (future slices, not v1): CANONICAL (canon
promotion mechanic — `EPISODE_VS_COMPOSITION_V1.md` §Q15);
RETIRED / DELETED (cascade policy — same doc §Q15, §Failure).

**Transitions.**

- `∅ → DRAFT` — operator clicks "New Episode" in a Universe.
- `DRAFT → ACTIVE` — first Composition attaches (either the
  operator generates from Episode context, or explicitly attaches
  an existing Composition).
- `ACTIVE → ACTIVE` — every retry, variant, cutdown, alternate
  backdrop, translation. No state change. This is the invariant
  that "rerender does not duplicate narrative history"
  (`EPISODE_VS_COMPOSITION_V1.md` §Isolation invariant 7).
- `ACTIVE → ARCHIVED` — explicit operator action.
- `ARCHIVED → ACTIVE` — explicit operator action (un-archive).

**No implicit transitions.** No auto-creation. No auto-archive.
No auto-promotion. Every transition is operator-initiated.

## Episode vs Composition responsibility table

Only the rows that this slice touches or reframes vs the prior
slice's responsibility matrix.

| Concern | Composition | Episode | Notes |
|---|---|---|---|
| `operator_topic` (verbatim) | own — always | own when Episode exists | Composition carries it always (legacy + per-attempt provenance); Episode carries it only when the operator declared a story. Two copies when both exist; Episode's is the story-authoritative one. |
| Cast | primary + secondary from render params | own M2M — may be empty at create | May be populated from first Composition's cast if empty. Never inferred; explicit attach. |
| Story intent | — | own (by virtue of being an Episode row) | Episode = "there is a story here." |
| Recipe kind (`template_kind`) | own | — | One Episode can render at multiple `template_kind`s. |
| Render state (`status`, `error_message`, etc.) | own | — | Unchanged from prior slice. |
| Attach to Episode | own FK (nullable) | — | Composition's FK is optional; NULL means "not part of a story." |
| Episode existence | — | driven by explicit operator action | H3, not H5. |
| Sequence within Universe | — | deferred v1 | `created_at` is enough for v1; explicit sequencing is a future slice. |

## Retry / revision / new-Episode decision table

Input events (rows) × current state (columns) → outcome. "In Episode
context" means operator explicitly attached the current Composition
to Episode E, or is working from within Episode E's UI surface.

| Input event | No Episode attached | In Episode E, unmodified topic | In Episode E, topic tweaked slightly | In Episode E, topic rewritten substantially | Reference prior Episode E' |
|---|---|---|---|---|---|
| **First "generate"** | New Composition C, `episode=NULL`, `operator_topic` on C. | New Composition C, `episode=E`, `operator_topic` inherited from E. | Update E.operator_topic (explicit "edit topic" action) → C created with new topic. | Operator prompted "new Episode or new Composition?" → new Episode E' recommended; C attaches to E'. | New Episode E' created; C attaches to E'; callback edge deferred substrate. |
| **Retry after failure** | New Composition C', `episode=NULL`, own `operator_topic`. Same story lost across the two rows unless operator groups later (H4-fallback for legacy). | New Composition C', `episode=E`. Original failed C stays FKing E. | New Composition C' after edit; E.operator_topic reflects latest. | Operator prompted (see above). | (Not applicable — retry, not new story.) |
| **Cutdown / aspect variant / alternate backdrop / translation** | New Composition C'', `episode=NULL`. Grouping possible only via `derived_from` / `used_by` lineage (`views.py:390–432`). | New Composition C'', `episode=E`. Kwargs differ; topic unchanged. | Same story, updated intent — treat as variant of E, not new Episode. | Operator prompted (see above). | (N/A.) |
| **Same-topic-again after long gap** | New Composition, `episode=NULL`, own `operator_topic`. No grouping. | Ambiguous — is this "another take" or "a new Episode"? SPA prompts. Default: new Composition on E. | Same. | Operator prompted; likely new Episode. | Operator picks explicitly. |
| **"Continue" (future callback)** | Not supported without Episode; operator must first attach one or both Compositions to Episodes. | Composition attaches to E; callback edge to E' deferred substrate. | Same. | Same. | New Episode E'' with edge to E' (substrate deferred). |

**Load-bearing property of this table:** the "No Episode attached"
column is *always a legal, non-broken outcome*. P1 and P2 live in
that column forever. It is not a degraded state; it is the correct
state for content that is not a story.

## Smallest proposed Episode v1 boundary

Absolute minimum. Everything else is deferred.

- `id` (UUID)
- `universe` FK (NOT NULL) — the Universe this story lives in.
- `workspace` FK (NOT NULL, denormalized) — must equal
  `universe.workspace`. Defense-in-depth per
  `UNIVERSE_BOUNDARY_V1.md` §Isolation-invariants.
- `title` (short string, operator-editable, may derive from topic).
- `operator_topic` (verbatim, longer text) — the story intent.
- `cast` M2M → Teammate (may be empty; must be subset of
  `universe`'s teammates when non-empty; validated at `clean()` /
  `m2m_changed pre_add` per prior slice §Isolation-invariant 5).
- `state` (enum: `DRAFT` / `ACTIVE` / `ARCHIVED`).
- `created_by` FK → User (SET_NULL).
- `created_at`, `updated_at` timestamps.

**Not in v1:** `sequence` / order, canon flag, canonical
Composition FK, callback edges, educational objective, audience,
Location FK, primary Composition designation, cascade policy on
Composition delete (deferred to schema slice — the *design* v1
recommendation is SET_NULL to preserve render provenance).

**Constraint invariants v1 must enforce** (paraphrased from prior
slice, unchanged):

- `Episode.workspace == Episode.universe.workspace`.
- `Episode.cast[*].universe == Episode.universe` when M2M non-empty.
- Attached Compositions: `composition.workspace == episode.workspace`
  and (when spokesperson.universe non-NULL)
  `composition.spokesperson.universe == episode.universe`.
- Legacy Compositions with `episode=NULL` never participate in
  Episode-scoped invariants (mirrors `UNIVERSE_BOUNDARY_V1.md` §Q9
  legacy-isolation rule).

## Where `operator_topic` lives

**Position: on Composition ALWAYS; on Episode when Episode exists.**

Reasoning:

- Composition needs `operator_topic` regardless of Episode
  (SESSION 259 backlog §37–46). Every P1/P2 render must persist
  the operator's verbatim topic for observability, retry-shaping,
  and per-attempt provenance — even when no Episode exists.
- When an Episode exists, its `operator_topic` is the *story-level
  authoritative* intent — inherited by attached Compositions at
  create-time and re-inherited on retry unless the operator
  explicitly modifies the render's topic.
- Composition's local `operator_topic` is the *per-attempt*
  record of what topic actually drove THIS render (which may
  differ from Episode's story-level topic if the operator tweaked
  it just for one variant).
- Two copies is correct because they answer different questions:
  Episode's answers "what is the story about?"; Composition's
  answers "what did we try to render this time?"

This is a light strengthening of `EPISODE_VS_COMPOSITION_V1.md`
§Unresolved-Q1 (which floated both copies as an option). This
slice takes the position: yes, both copies, always.

## Unresolved questions

Beyond the deferred items above, this slice creates or leaves open:

1. **What does the SPA show for Universe-scoped operators who
   have not yet created any Episodes?** H3 requires a "New
   Episode" surface distinct from "New video." UX slice.
2. **Does "attach existing Composition to Episode" require the
   operator to reconcile mismatched `operator_topic` values?** If
   Composition C already has `operator_topic="X"` and the operator
   attaches C to Episode E with `operator_topic="Y"`, what
   happens? Position: no reconciliation; both persist; Episode's Y
   is story-authoritative, Composition's X is per-attempt
   provenance. Confirm in UX slice.
3. **What is the operator-facing name for Episode?** Prior slice
   §Unresolved-Q9 raised this. H3 makes the naming more consequential
   because the operator now *actively chooses* to create one. If the
   term "Episode" biases operators toward TV-shaped thinking, the
   P4/P5 storytellers may over-use; if the term is too plain
   ("Story," "Beat"), P3's operator may not recognize when to reach
   for it. UX slice.
4. **How does `Episode.cast` M2M evolve when a Composition attaches
   with a new cast member not previously on Episode?** Position:
   auto-add to Episode.cast (subject to Universe-consistency
   invariant). Confirm.
5. **Can a Composition be *detached* from an Episode after render?**
   E.g. operator realizes "actually, this cutdown isn't part of the
   story after all." Position: yes, `episode` FK is nullable, so
   detach is a legal edit. Cascade side-effects TBD.
6. **Retry vs "new Episode" prompting.** The retry table names
   "Operator prompted" for the "topic rewritten substantially" case
   — but nothing in v1 code diffs old vs new topic. UX slice must
   design when/how to prompt without inventing a text-similarity
   heuristic on the backend.
7. **Does the "attach existing legacy Composition to a new Episode"
   ½-slice path (from `EPISODE_VS_COMPOSITION_V1.md` §Q16 and
   `UNIVERSE_BOUNDARY_V1.md` §Q6) need any Episode-side
   validation beyond the Universe-consistency invariants?**
   Probably not; deferred to schema slice.

## Risks if we get this boundary wrong

1. **Auto-creating Episodes (H5 as prior slice proposed).** The
   operator drowns in Episode rows that don't correspond to
   stories. P1 and P2 create noise permanently. The Episode
   primitive loses its meaning; the UI has to invent visual
   filters ("is this a real Episode or an auto-Episode?") that
   re-introduce the exact "which one is real" problem
   `UNIVERSE_BOUNDARY_V1` §Q8 rejected.
2. **Making Episode implicit on topic entry (H1).** Same as (1)
   but earlier — every operator who ever types a video prompt
   creates an Episode row. Worst-case fires on abandoned drafts
   (operator types a topic, closes the tab). Row count balloons.
3. **Delaying Episode until first successful render (variant of
   H2/H4).** Loses the case where synthesis fails on attempt #1
   and the operator wants attempt #2 to belong to "the same
   story." Reintroduces the SESSION 259 observability gap for
   `operator_topic` on failed renders.
4. **Not persisting `operator_topic` on Composition (Episode-only
   home).** Legacy / Episode-less renders (P1, P2, all 81 historical
   compositions) have no durable topic record. SESSION 259 backlog
   §37–46 remains open. Retry-shape, feedback-shape, and post-hoc
   audit all remain guessing games.
5. **Requiring cast to be fully populated at Episode create.**
   Overloads the "New Episode" affordance. P4 (Ruby + Mason low
   knowledge) discourages upfront cast enumeration; the story
   should be conceivable before the cast is finalized.
6. **Confusing "attach to Episode" (auto on generate-from-Episode)
   with "create Episode" (explicit action).** UX conflation of
   the two re-introduces H5's problem through the back door: the
   operator hits "generate" and an Episode magically appears
   because the "attach to current Episode" default was set to a
   just-created empty Episode. Guard the SPA against this.
7. **Migrating historical Compositions in bulk.** Mirrors
   `UNIVERSE_BOUNDARY_V1.md` §Q6 rejection; would create 81
   noise-Episodes in `chriss-workspace` for zero gain. Preserved
   from prior slice §Q16 — reinforced here.

## STOP

Research only. No schema. No migrations. No code. Every
load-bearing claim is cited to `EPISODE_VS_COMPOSITION_V1.md`,
`UNIVERSE_BOUNDARY_V1.md`, `CAPABILITY_INVENTORY_SESSION_261.md`,
`SESSION_259_OBSERVABILITY_BACKLOG.md`, or to a file:line in
`shell/apps/compositions/`.
