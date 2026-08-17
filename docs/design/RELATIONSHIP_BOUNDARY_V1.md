---
title: "Relationship Boundary v1 — Persistent Continuity Between Characters"
status: research — relationship substrate boundary (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"
scope: >
  Answer one question — what persistent relationship / continuity
  substrate does a Universe need for recurring characters? Take
  positions. Do not design narrative memory, Location, Cast, or
  WorldEntity beyond what is essential to establish the Relationship
  boundary.
---

# Relationship Boundary v1 — Persistent Continuity Between Characters

## Purpose

Prior slices established: **Workspace = tenant, Universe = world**
(UNIVERSE_BOUNDARY_V1.md); **Episode wraps Composition, 1:N**
(EPISODE_VS_COMPOSITION_V1.md); **Episode is created explicitly by the
operator, never auto-created** (EPISODE_LIFECYCLE_V1.md). The
CAPABILITY_INVENTORY_SESSION_261.md §8 audit confirmed that
**character-to-character relationships are ABSENT** — no
`Relationship`, `Bond`, `Edge`, `Kinship`, `Link`, or `Connection`
model exists anywhere in `shell/apps`; no `Teammate → Teammate`
FK/M2M exists; no `apps/relations` app exists. The `memory` and
`agents` app scaffolds are 0-line files
(CAPABILITY_INVENTORY_SESSION_261.md §9; confirmed by
`wc -l shell/apps/memory/models.py shell/apps/agents/models.py` → 0).

This slice answers **exactly one question**: what persistent
relationship / continuity substrate does a Universe need for
recurring characters? It walks the operator's Ruby/Mason/Patch/Rivet
stress-test end-to-end, evaluates five options R1–R5, and takes a
position on the smallest v1 boundary that does not block future
narrative memory.

## Scope (and what's explicitly deferred)

**In scope.**

- The semantic separation between a **durable relationship** (Patch
  and Rivet exist in a working relationship regardless of any
  Episode) and a **historical event** (Episode B mentions the project
  for Mason).
- Direction, type, and payload positions.
- Off-screen relevance mechanism (how Episode B knows Mason matters
  when Mason is not in its cast).
- Minimum v1 Relationship boundary that does not block later
  narrative memory.
- Three-membership distinction: Character-in-Universe vs
  Character-in-Episode.cast vs Character-in-Relationship.
- Whether the bakery / coffee shop force a WorldEntity primitive.
- Legacy behavior (Mike-the-plumber, Repo Red, Tulsi).

**Explicitly deferred.**

- Any schema DDL, migration plan, or Django field addition.
- Narrative-memory substrate design (event log / promise ledger /
  callback edges). Referenced only where needed to prove Relationship
  boundary.
- Location / Place / Scene / Set entity design in detail. This slice
  takes a minimal stance where the Relationship boundary depends on
  one and names it as a dependency, but does not design the primitive.
- Organization / Business entity design in detail. Same posture.
- Cast / Ensemble grouping design (deferred per
  UNIVERSE_BOUNDARY_V1.md §D4).
- Canon promotion mechanic for Relationships.
- Relationship archival / soft-delete lifecycle.
- SPA UX for Relationships.
- Cross-Universe relationship crossovers.
- Relationship strength / weight / intensity numeric fields.
- Automatic relationship inference from Episode co-occurrence.

## Load-bearing principles carried forward

Restated from the operator brief and prior slices; they gate every
answer below.

1. **Legacy character data informs compatibility; it does not define
   Universe semantics** (SESSION 259 memory; carried through
   UNIVERSE_BOUNDARY_V1.md, EPISODE_LIFECYCLE_V1.md).
2. **Character knowledge must NOT define whether a relationship can
   exist.** Ruby with a low K2 corpus can have a relationship with
   Mason. Knowledge is *available to* a character; it does not
   *constitute* the character.
3. **Patch and Rivet are the intentional recurring-Universe
   dogfood** — the first characters designed to have durable
   relationships and continuity from day one. They set the shape.
4. **Historical business spokespeople (Mike, Repo Red, Tulsi) are
   compatibility evidence, not semantics inputs.** Their historical
   talking-head cadence must survive Relationship's arrival; their
   workflow must not determine whether Relationship is required.
5. **Legacy stays legacy** (UNIVERSE_BOUNDARY_V1.md §Q6). No bulk
   migration. No auto-defaults (UNIVERSE_BOUNDARY_V1.md §Q8,
   EPISODE_LIFECYCLE_V1.md §H5 rejection). Prospective introduction.
6. **No implicit cross-Universe access, ever** (UNIVERSE_BOUNDARY
   invariant 5). Relationships are Universe-scoped; a Patch↔Rivet
   edge lives in the workshop Universe and cannot leak into another.
7. **Episode existence is a first-class operator decision.** A
   Composition can exist without an Episode, and Episode with zero
   Compositions is legal (EPISODE_LIFECYCLE_V1.md §Q10). Relationship
   design must not force Episode existence.

## Stress-test scenario (operator-supplied)

- **Universe**: `patch-rivet-workshop` (Patch and Rivet dogfood).
- **Ruby the Fox** owns a bakery.
- **Mason the Bear** owns a coffee shop.
- **Patch + Rivet** have an established working relationship. It
  long predates any Episode.
- **Episode A**: Mason approaches Patch about building an AI agent
  for the coffee shop. Cast = {Patch, Mason}.
- **Episode B (later)**: Patch and Rivet discuss the work being done
  for Mason. **Mason does not appear in Episode B's cast.** Cast =
  {Patch, Rivet}.
- **Episode C (still later)**: Mason may return; the prior
  project/history should matter. Cast = {Mason, Patch} probably.

Additional walk-throughs:

- **Ruby self-intro** (X5). Ruby is created; she has zero prior
  relationships. What does that look like?
- **Mike-the-plumber legacy talking-head** (X6). Should Relationship
  substrate touch him at all?

## Options R1–R5 stated

**R1 — Relationships are projections of Episodes.**
No separate substrate. Queries derive relationships from cast
co-occurrence and event history. "Patch and Rivet have a
relationship" ≡ "they have co-appeared in ≥N Episodes."
"Mason is Patch's client" ≡ "Episode A joined them, no counter-event
severed them."

**R2 — Relationships are Universe-owned canonical facts.**
Durable rows. Exist pre-Episode. Edited independently.
Referenced by Episodes but not derived from them. Patch↔Rivet
exists the day the Universe is created; Mason↔Patch exists the
moment the operator declares a prospect relationship, potentially
before Episode A even fires.

**R3 — Relationships are Universe canon + narrative overlay.**
Canonical row (R2) plus Episode-appended history events (memory
substrate). The row itself only changes on explicit operator/canon
promotion; history events accrete freely as Episodes fire.

**R4 — There is no Relationship model in v1.**
Character-side annotations only — freeform notes on Teammate,
narrative context injected via K2 documents, no first-class edge.
Wait until narrative memory forces the decision.

**R5 — Something the evidence dictates that isn't R1–R4.**

## Current-state search — what exists in the codebase today

Full read-only search performed. Findings by category:

| Search | Result | Cite |
|---|---|---|
| `Relationship`, `Relation`, `Bond`, `Edge`, `Kinship`, `Link`, `Connection`, `Trust`, `Affinity`, `Family`, `Parent`, `Child`, `Sibling`, `Mentor`, `Apprentice`, `Follows` class definitions in `shell/apps` | **ABSENT** | CAPABILITY_INVENTORY_SESSION_261.md §8; special-question 7; confirmed by grep for `class \w+\s*\(` in `spokespeople/models.py` (only `Teammate`, `Status`, `Tone`, `VisualTemplate`, `VoiceEnergy`, `VoiceHumor`, `VoiceDirectness`) |
| `Teammate` M2Ms (self-referential or to another Teammate) | **NONE.** `Teammate` model in `shell/apps/spokespeople/models.py:26–…` has exactly one FK — `workspace` → `Workspace` (line 65–69). No `ManyToManyField` anywhere in the model. No `related_to`, `related_teammates`, `mentors`, `apprentices`, `partners`, `parent_teammate` field | `shell/apps/spokespeople/models.py:26–70`; grep `ManyToManyField\|ForeignKey.*Teammate` in that file returns only `related_name="teammates"` on the workspace FK |
| Grep `ForeignKey.*Teammate\|ForeignKey.*Spokesperson\|ManyToManyField.*Teammate\|ManyToManyField.*Spokesperson` across `shell/apps` | **NO matches** for cross-Teammate FKs. Every FK named `spokesperson` targets `Teammate` from a *non-Teammate* row (Composition, Asset, Script, Campaign, ConversationThread, RealtimeSession, Video). None are Teammate→Teammate | grep across `shell/apps` |
| `IdentityReferenceKind` enum | Six values including `ENVIRONMENT_REFERENCE` (dormant). None of them are relational | `shell/apps/identity/models.py:344–361`; only `PORTRAIT_REFERENCE` is exercised in round-one benchmark |
| `apps/memory` scaffold | **0-line models.py, 0-line views.py, 0-line urls.py.** App registered (`apps/memory/apps.py:MemoryConfig`), migrations dir exists with `__init__.py` only | `shell/apps/memory/models.py` (empty); confirmed by `wc -l` |
| `apps/agents` scaffold | **0-line models.py, 0-line views.py, 0-line urls.py.** Same shape as `apps/memory` | `shell/apps/agents/models.py` (empty); confirmed by `wc -l` |
| Weak relational adjacencies | (a) `KnowledgeDocument.spokespeople` M2M — sharing semantic, not relational (`embeddings/models.py:135–140`). (b) `dialogue_scene` recipe `primary_spokesperson_id` + `secondary_spokesperson_id` — per-scene wiring, no persistence (`compositions/recipes.py:337–340, 1527`). (c) `handoff_to_spokesperson` realtime tool — audit row only, no relationship persistence (`shell/apps/realtime/tools/handoff_to_teammate.py:1–80`) | as cited |
| `CharacterIdentity.teammate` FK | Ownership (identity → teammate), not relationship | `shell/apps/identity/models.py:117` |

**Conclusion of search:** the substrate for character-to-character
relationships is **completely absent**. There is no dormant model to
reuse, no half-written enum to extend, no M2M whose semantics could
be re-purposed. This is not a Chesterton's-fence situation; it is a
genuine greenfield decision.

The `apps/memory` and `apps/agents` scaffolds are reserved
namespaces. Relationships could conceivably land in `apps/memory`
(if we treat continuity substrate as one thing) or in a new
`apps/relationships` or `apps/universe`. Choice of home is deferred
to a schema slice; **this doc does not decide the app-name
question**.

## Options × Stress-test matrix

Rows = options R1–R5. Columns = the stress-test walkthroughs
X1–X6 (defined below in "Product examples"). Cells describe how
each option handles the case; **bold** flags where the option fails
or corrupts state.

| Option | X1 Patch+Rivet baseline (pre-Episode) | X2 Episode A (Mason approaches Patch) | X3 Episode B (Patch+Rivet discuss Mason; Mason absent from cast) | X4 Episode C (Mason returns; history matters) | X5 Ruby self-intro (no prior relationships) | X6 Mike legacy talking-head |
|---|---|---|---|---|---|---|
| **R1 Projections** | **No relationship visible** until Patch and Rivet co-appear in a first Episode. **Contradicts operator: the relationship long predates any Episode.** | Mason↔Patch inferred from Episode A cast. Type/direction ("prospect client") not representable — projection sees only "they co-appeared." | **Fails.** Mason is not in Episode B's cast. Projection has no way to surface Mason as relevant. Rivet only knows Mason through the *content of Episode B*, but the projection layer sees zero co-occurrence involving Mason and Rivet — because there is none. | Episode C's cast (Mason, Patch) revives projection of their relationship — but Episode A's project context is lost unless narrative-memory substrate carries it separately. Projection can't distinguish "past client" from "current client." | Zero co-occurrences ⇒ zero projected relationships. Fine for X5 in isolation. | No Episodes ⇒ no projections. Fine for X6. |
| **R2 Universe-canon rows** | Patch↔Rivet row exists in Universe pre-Episode. Type `partners` or similar. Correct. | Mason↔Patch row created (or updated from `prospect` to `client`) by the operator at Episode-A time. Independent edit — not tied to Episode's existence. | Mason↔Patch row exists as a fact. Episode B's synthesis can load "Patch has a client relationship with Mason" via the Relationship row, without adding Mason to cast. Correct. | Episode C's synthesis loads Mason↔Patch relationship + prior Episode-A project context via narrative-memory substrate keyed on Mason↔Patch or on Mason (deferred substrate, but Relationship row is the anchor). Correct. | Zero Relationship rows. Fine — Ruby's row-count-of-zero IS her relational state. | No Universe ⇒ no Relationship rows possible. Fine. |
| **R3 Canon + history** | Patch↔Rivet canonical row + zero history events pre-Episode. Correct. | Mason↔Patch canonical row created; Episode A appends a history event ("Mason approaches Patch about AI agent for coffee shop") to that edge's history. | Mason↔Patch row loaded during Episode B synthesis; recent history events describing the AI-agent project are surfaced. Rivet gets the context. Correct. | Episode C loads the row + full history; "past project" is distinguishable from "current project" because history events carry state markers. Correct. Requires narrative-memory substrate (deferred). | Zero rows, zero history. Fine. | Same. |
| **R4 No model** | No representation. Patch↔Rivet baseline lives in K2 docs / personality strings. **Fragile** — must be re-injected into every synthesis prompt manually. Contradicts "knowledge does not define relationships" principle. | Mason↔Patch nowhere. Episode A cast → operator hopes synthesis infers "they're building something." No durable state. | **Fails.** No way to surface Mason to Episode B unless operator hand-writes "Patch is working with Mason" into the topic. Load-bearing operator scenario collapses. | Episode C has to hand-write history back into topic. No durable prior state. | Fine. | Fine. |
| **R5 Named refinement** | See "Recommended Relationship substrate" — a narrowed R3 where the v1 row is intentionally sparse and the history side is postponed to the memory substrate slice | | | | | |

**Reading the matrix.**

- R1 (projections) fails X1 (relationship predates Episode) and X3
  (Mason absent from cast). Both are load-bearing operator
  requirements. R1 is out.
- R4 (no model) fails X1 in principle (violates the knowledge-does-
  not-define-relationships principle) and X3 in practice (no way to
  surface Mason to Episode B). R4 is out.
- R2 handles X1–X6 correctly for the **relationship-as-fact** axis,
  but leaves X3's "recent project context" unrepresented — the row
  itself says "Mason is Patch's client," not "the AI-agent project
  started in Episode A."
- R3 handles all six correctly but requires narrative memory
  substrate, which is deferred.
- **R5 (recommended)**: adopt R2's Universe-canon rows in v1, with
  the Relationship row's SHAPE designed so that R3's history overlay
  can layer on later without redesigning the row. Explicitly: the
  v1 row owns the durable "who → who, what type" fact; the history
  events are deferred to the memory substrate slice, keyed on
  Relationship.id (and/or on the pair of Teammate ids). This is
  R3-shaped but R2-scoped for v1.

## Q1–Q12 answered

### Q1. What is a durable Character Relationship vs an event/history fact created by an Episode?

- **Durable relationship** = a persistent fact about how two
  characters relate in the Universe. Answers *"what are they to each
  other?"* Examples: `partners` (Patch, Rivet), `client` (Mason,
  Patch), `mentor / apprentice` (future). Lives on a Relationship
  row on the Universe. Exists whether or not any Episode has fired.
  Changes only on **explicit operator edit** or explicit canon
  promotion — never as a byproduct of an Episode rendering.
- **Event / history fact** = something that *happened* in a specific
  Episode. Answers *"what did they do?"* Examples: "Mason approached
  Patch in Episode A about the AI agent." "Rivet warned Patch in
  Episode X about the coffee machine." Lives on the future
  narrative-memory substrate (out of scope this slice), keyed on
  Episode + optionally on the relevant Relationship row(s).

The row is *the state.* Events are *the history.* Same distinction
`EPISODE_VS_COMPOSITION_V1.md` §Q15 already articulated for
narrative memory; this slice preserves and extends it.

### Q2. Should relationships exist BEFORE two characters ever share an Episode?

**Yes.** Patch↔Rivet is the load-bearing case: the operator's brief
states "Patch and Rivet have an established working relationship (long
predates any Episode)." Under R1 (projection), this relationship has
no representation until they co-appear in an Episode — which is
wrong. Under R2/R3/R5, the row is created when the operator declares
it (probably at Universe / Teammate creation time), regardless of
Episode existence.

Corollary: Mason↔Patch may exist as a `prospect` relationship *before*
Episode A fires. If the operator has "Mason is Ruby's neighbor and a
potential AI-agent customer for Patch" in their head before authoring
the Episode, they should be able to write that down.

### Q3. Can Episodes create or modify relationships without rewriting historical relationship state?

**Episodes create HISTORY EVENTS. Episodes do NOT modify the
Relationship row.** Same discipline as
`EPISODE_VS_COMPOSITION_V1.md` §Isolation-invariant 7 ("rerender does
not duplicate narrative history"): Episodes append; they do not
mutate canon.

Concretely:

- Episode A adds a history event ("Mason approached Patch") that
  references the Mason↔Patch Relationship row. The row itself is
  not written by Episode A. If the row didn't exist, the operator is
  prompted at Episode-A creation time to declare "this establishes a
  new relationship" — which promotes the row explicitly.
- Episode C references the same row; adds another history event
  ("Mason returned"). Row unchanged.
- **Type / status changes** (e.g., `prospect` → `client`) require
  explicit operator action, not implicit Episode inference. The
  operator can be prompted at Episode-close time ("Should Mason↔Patch
  advance from prospect to client?"), but the change is a *promotion*
  UX gesture — not a byproduct of Episode existence.

This preserves the operator's authorship over canon. It also allows
retry/rerender of Episode A to happen without re-mutating the
Relationship row (same protection Episode gives narrative continuity
against Composition retry).

### Q4. How should Episode B know Patch has previously worked with Mason when Mason is not in its cast?

**Load-bearing question.** Answer:

Episode B's synthesis loads Universe-scoped Relationship context for
its cast — specifically, the union of all Relationship rows involving
any cast member. For Episode B (cast = {Patch, Rivet}):

- Patch↔Rivet — direct, self-evident, adds partner context.
- Patch↔Mason — **loaded because Patch is in cast**, even though
  Mason is not. This surfaces "Patch has a client relationship with
  Mason" to the synthesis prompt, plus (once memory substrate
  arrives) the recent history events describing the project.
- Rivet↔Mason — probably empty in this Universe; nothing loaded.

**Mechanism (design position, not schema):** synthesis's context
assembly step queries `Relationship WHERE universe = episode.universe
AND (from_teammate IN cast OR to_teammate IN cast)`. It does not
query `WHERE both endpoints IN cast`. This is the difference between
"who's in the scene" and "who matters to who's in the scene." The
distinction is load-bearing for X3.

**Off-screen relevance is native to R2/R3/R5.** R1 (projection) has
no answer here without inventing "co-occurrence-of-1" heuristics that
degrade into R2 with worse ergonomics. R4 (no model) has no answer at
all.

### Q5. Is relationship state directional?

**Yes, but v1 stores ONE ROW per pair with a normalized ordering
and represents direction/asymmetry via TYPED FIELDS on the row.**

Reasoning:

- The operator's example is asymmetric: Patch sees Mason as `client`;
  Mason sees Patch as `service_provider` (or `friend`, or whatever
  the operator declares). These are two different views of the same
  edge.
- Two-row-per-pair (one per direction) doubles the row count and
  creates a synchronization burden — if the operator promotes
  Patch→Mason from `prospect` to `client`, the reverse Mason→Patch
  edge must move from `prospect_of` to `service_provider_of` in
  lockstep.
- One-row-per-pair with `from_teammate`, `to_teammate`,
  `type_from_to`, `type_to_from` (or a single `type` field for
  symmetric relationships plus an optional `type_reverse` when
  asymmetric) captures direction in one place and one write.

**Position: v1 = one row per pair; row carries a normalized ordering
(`from_teammate.id < to_teammate.id`, or similar deterministic rule);
the row's type field(s) encode direction/asymmetry.** The exact
column shape (single `type` vs paired `type_from_to`/`type_to_from`)
is a schema-slice decision; this doc's position is only that
one-row-per-pair is the correct v1 shape.

Corollary: uniqueness constraint `unique(universe, teammate_a,
teammate_b)` with normalized ordering enforced at `clean()` /
service layer. Deferred to schema slice.

### Q6. Do relationships need type, strength, status, history, or freeform description — or would those over-model v1?

Answer field-by-field (positions):

- **Type** — **YES in v1.** Without a type, a Relationship row says
  only "these two are somehow related," which is barely more useful
  than R1's projection. The type is what makes the row useful to
  synthesis. **Freeform text** in v1 (not enum) — the vocabulary is
  operator-authored and product-domain-specific (`partners`,
  `client`, `mentor`, `apprentice`, `sibling`, `rival`, `spouse`,
  `boss`). Constraining to an enum locks in premature choices.
  Length-cap and lower-casing enforced at service layer.
- **Strength / weight** — **NO in v1.** Numeric intensity is
  narrative-memory territory ("Rivet's trust in Patch decreased in
  Episode X"). v1 has no way to update it non-manually; a static
  "strength = 0.7" row is worse than not having the field.
- **Status** — **YES, minimal.** `active` / `archived` / (optional)
  `former`. Distinguishes "current spouse" from "ex-spouse," "current
  client" from "past client." Without this, X4 (Mason returns after
  a completed prior project) can't distinguish present from past.
- **History** — **NO in v1 on the row itself.** Deferred to memory
  substrate. The row's `updated_at` and (optionally) `established_at`
  are enough for v1 to answer "when did this relationship start."
  Detailed history events belong on the deferred substrate.
- **Freeform description** — **YES.** One notes / description field
  (short text, operator-authored). Captures nuance the type field
  can't ("Patch built Rivet as a toolbox that grew a mind"). Not
  parsed by synthesis at v1 — surfaced verbatim to the prompt as
  additional context.

**Smallest useful v1 row (position):** `universe` FK, `teammate_a`
FK, `teammate_b` FK, `type` (freeform text), optional
`type_reverse` (freeform text; asymmetric edges), `status` (enum:
`active`/`archived`/`former`), `notes` (freeform text), `created_by`,
`created_at`, `updated_at`, optional `established_at`.

Everything else (strength, history events, canon flag, callback
edges) is deferred.

### Q7. What belongs in static Universe canon vs Relationship vs Episode/narrative history?

Three-layer separation:

- **Static Universe canon** = facts about the world that aren't
  edges between characters. "The Universe is a small-business
  workshop world where Patch and Rivet help other small-business
  characters." "Locations exist" (if Location primitive lands).
  Attaches to the Universe row itself (or to a future
  `UniverseCanon` sub-row); NOT to Relationship.
- **Relationship (this slice)** = durable edges between two
  characters. "Patch and Rivet are partners." "Mason is Patch's
  client." Universe-scoped rows. Owned semantically by the operator.
- **Episode / narrative history** = events that happened in a
  specific Episode. "Mason approached Patch about AI agent in
  Episode A." "Rivet warned Patch about the coffee machine in
  Episode X." Deferred substrate keyed on Episode.

The bakery / coffee shop belong to a fourth category — **character-
owned facts or shared WorldEntity canon** — see Q10.

### Q8. Does the existing codebase already contain models/substrates that could support any of this?

**No, but the reserved namespaces exist.**

Enumerated:

- `Teammate` M2Ms → NONE (`shell/apps/spokespeople/models.py:65–69`
  has only the workspace FK). No self-referential M2M, no
  `related_teammates`. Confirmed by grep.
- `IdentityReferenceKind` enum
  (`shell/apps/identity/models.py:344–361`) → six values, none
  relational. `ENVIRONMENT_REFERENCE` is dormant but scoped to
  identity substrate, not relationships.
- `apps/agents/models.py` → **0 lines**. Reserved namespace.
- `apps/memory/models.py` → **0 lines**. Reserved namespace.
- Grep `class \w+\(` in every `shell/apps/*/models.py` for
  `Relation`, `Bond`, `Edge`, `Link`, `Connection`, `Kinship`,
  `Trust`, `Affinity`, `Family`, `Parent`, `Child`, `Sibling`,
  `Follows`, `Mentor`, `Apprentice` → **zero matches** (also
  CAPABILITY_INVENTORY_SESSION_261.md §8 confirmed).
- Grep for cross-Teammate FKs / M2Ms across `shell/apps` → **zero
  matches**. Every `spokesperson`-shaped FK targets Teammate from a
  non-Teammate row (Composition, Asset, Script, Campaign,
  ConversationThread, RealtimeSession, Video), never from another
  Teammate row.

**Practical implication:** Relationships must be authored fresh.
There is no reuse path. App-name decision (`apps/relationships` vs
`apps/universe` vs extending `apps/memory`) is deferred to schema
slice. The existing `apps/memory` scaffold is a plausible home if
we treat continuity substrate as one thing (Relationship + narrative
memory in one app); a separate `apps/relationships` is defensible
if we want each substrate to be independently deletable and
independently versioned. This doc does not decide.

### Q9. Stress-test relationships involving characters with little/no K2. Character knowledge must not define whether a relationship can exist.

Ruby has minimal K2 (per operator brief). She can still:

- Have a Relationship row with Mason (`friend`, `neighbor`, whatever
  the operator declares) — nothing in the Relationship row requires
  K2 content.
- Be added to Episode A cast (Universe scope + Teammate.universe
  membership is what gates cast eligibility, not K2).
- Have Patch↔Ruby Relationship rows regardless of Patch's or Ruby's
  K2 corpora.

**Design invariant:** Relationship creation MUST NOT read from or
require any K2 content on either Teammate. The row's fields are
Teammate FKs, freeform text, and an operator-authored type. No
K2 check anywhere in the write path.

This is a corollary of principle 2 above. Explicitly stated to
prevent a schema-slice implementation from silently gating on
`teammate.knowledge_documents.exists()` or similar.

### Q10. Is Ruby-owns-a-bakery / Mason-owns-a-coffee-shop character knowledge, shared Universe canon, a Relationship (Character↔Location edge), or evidence that the future world model needs a persistent Place / Organization / WorldEntity concept?

**Position: this is evidence a WorldEntity concept is EVENTUALLY
needed, but v1 punts by storing it as CHARACTER-OWNED FACTS on the
Teammate row (business_brief / personality), and Relationship v1
does NOT model Character↔Location or Character↔Organization edges.**

Reasoning:

- "Owns a bakery" is a **fact about Ruby.** It fits naturally on
  `Teammate.business_brief` (which per
  `shell/apps/spokespeople/models.py:71–82` is "WHAT the business
  does — facts the teammate grounds their claims in").
- "The bakery" as a shared world entity that could recur across
  Episodes, be visited, be described, and be independently
  referenced by other characters — is a **WorldEntity / Place /
  Organization primitive.** That primitive does not exist
  (CAPABILITY_INVENTORY_SESSION_261.md §12; §11: "No `Entity` /
  `Object` / `Prop` / `Product` catalog model. Assets are
  output-media records.").
- For v1, the pragmatic answer is: the bakery lives on Ruby's
  `business_brief`. If Episode B needs to talk about the bakery,
  Ruby's business_brief already carries the fact. Same for Mason
  and the coffee shop.
- **What breaks in the interim?** Two things: (a) shared-world
  facts that neither character owns (a landmark park, a public
  building, a business that changes hands between characters) have
  no home; (b) queries like "which characters own businesses in this
  Universe" require scraping `business_brief` text. Both are
  acceptable for v1 given the operator's actual near-term dogfood
  is Patch + Rivet + a handful of characters where character-owned
  facts on `business_brief` cover the case.

**The Episode A "AI agent project" is a different question.** That's
neither a character-owned fact nor a location — it's a *project*
that exists across Episodes. Two options for representing it in v1:

- **Option (a):** load-bearing history event on the (deferred)
  narrative-memory substrate, keyed on the Mason↔Patch Relationship
  row. The Relationship row says "client"; the memory events say
  "AI-agent project started in Episode A, status in-progress." Row
  = state; events = history.
- **Option (b):** freeform text on the Relationship row's `notes`
  field. "Patch is building an AI agent for Mason's coffee shop
  (started Episode A)." Ugly, but v1-shippable without a memory
  substrate.

**Position:** v1 uses (b) as a stopgap. (a) is the correct answer
once narrative memory lands.

**Naming the dependency:** if the operator ever wants "the AI-agent
project" to be a first-class row (queryable, addressable, referenced
by multiple Episodes as `subject`), we need a WorldEntity primitive.
This slice takes NO POSITION on when that primitive lands; it only
names the dependency and confirms Relationship v1 does not require
it.

### Q11. Can an off-screen character remain narratively relevant to an Episode without being added to `Episode.cast`?

**Yes, and this is the mechanism from Q4.**

Relationship substrate is the answer. Episode B's synthesis loads
Relationship rows involving cast members. Mason is loaded via
Patch↔Mason without being in Episode B's cast. The operator does
NOT add Mason to Episode B's cast solely to surface his existence
to the prompt — that would over-couple cast (a UI/render concern)
with narrative relevance (a story concern).

**Distinguishing three memberships (per the operator's ask):**

- **Character-in-Universe** = `Teammate.universe` FK
  (UNIVERSE_BOUNDARY_V1 §Q12.3). "Mason belongs to the workshop
  world." Broadest membership.
- **Character-in-Episode.cast** = M2M on Episode
  (EPISODE_LIFECYCLE_V1 §Q7 smallest state). "Mason is a
  performing/on-screen character in Episode A." Narrower — the
  set actively participating in this story event.
- **Character-in-Relationship** = presence in a Relationship row
  as `teammate_a` or `teammate_b` (this slice). "Mason has an edge
  to Patch." Orthogonal — a character can have many relationships
  without being in any single Episode's cast.

All three memberships must be tracked separately. `Universe` is the
outer container; `Relationship` is the persistent-edge fact;
`Episode.cast` is the per-story participant list. Merging any two
(e.g., "Episode.cast = union of Universe.characters with active
Relationships") is wrong — the operator authors each independently.

### Q12. What is the smallest relationship primitive we actually need NOW that won't block later narrative memory?

**Answer: R2-scoped, R3-shaped.**

Smallest v1 row:

- `id`
- `universe` FK (NOT NULL) — Relationship is Universe-scoped
- `workspace` FK (NOT NULL, denormalized, `== universe.workspace`)
  — defense-in-depth per UNIVERSE_BOUNDARY_V1 §Isolation-invariants
- `teammate_a` FK, `teammate_b` FK — both must be in
  `universe.teammates`; ordering normalized to prevent duplicates
- `type` — freeform text (short cap); operator vocabulary
- `type_reverse` — optional freeform text; asymmetric edges
- `status` — enum: `active` / `archived` / `former`
- `notes` — freeform text
- `created_by`, `created_at`, `updated_at`
- optional `established_at`

**Not in v1:** strength, canon flag, history events on the row,
callback edges, Character↔Location edges, Character↔Organization
edges, WorldEntity references, Episode co-occurrence M2Ms, automatic
inference, per-relationship voice / prompt overrides, cross-Universe
mirrors.

**Invariants (paraphrased):**

- `Relationship.universe.workspace == Relationship.workspace`.
- `teammate_a.universe == teammate_b.universe == Relationship.universe`.
- `teammate_a != teammate_b` (no self-loops; self-relationship is
  either a nonsense case or a nonobvious refinement — either way,
  keep out of v1).
- Normalized `(teammate_a, teammate_b)` ordering; unique
  `(universe, teammate_a, teammate_b)`.
- No cross-Universe attach (mirrors UNIVERSE_BOUNDARY_V1 §Q9
  cross-Universe M2M rejection).
- No implicit creation by Episode / Composition / synthesis paths.
  Rows are created only by explicit operator action.

**Why this doesn't block narrative memory:**

- Memory substrate (deferred) can attach history events keyed on
  Relationship.id (an edge event) or keyed on Episode + Teammate ids
  (an episode event that involves a character regardless of
  edge). The Relationship row shape supports both.
- Canon promotion mechanic (deferred) can add a `canonical_from`
  Episode FK later — the Relationship row's existence pre-dates it.
- Strength / weight / decay (deferred) can layer on as additional
  columns or a sidecar model — the row's edge identity is stable.
- Character↔Location / Character↔Organization edges (deferred) will
  need a different endpoint model — but that's a NEW model, not a
  reshape of Relationship.

## Q10 sub-slice — WorldEntity/Place forcing function (take a v1 position)

The bakery, the coffee shop, and the "AI-agent project" (Episode A's
subject) are three data points on the same question: **does v1 need
a WorldEntity primitive?**

**Position: NO in v1. YES eventually.**

Rationale:

- **Bakery / coffee shop as ownership facts:** Ruby's business_brief
  and Mason's business_brief carry them. Composition and Episode
  synthesis already read `Teammate.business_brief`. This is the
  path of least resistance and doesn't require a new primitive.
- **Bakery / coffee shop as recurring shared entities:** the risk
  is a bakery description drifting between characters (Ruby says
  "corner bakery on Main St"; Mason says "the bakery on Fifth").
  For v1 with Patch/Rivet + a small cast, operator discipline
  handles this; if it becomes a real problem, WorldEntity is the
  answer.
- **AI-agent project as a persistent thing across Episodes:** the
  cleanest home is on the deferred narrative-memory substrate
  (history events referencing the Mason↔Patch Relationship row).
  Stopgap: Relationship.notes.

**What breaks if we don't have WorldEntity in v1:**

1. Shared-world facts owned by no character have no home (a public
   library, a landmark park, a rival business). Operator can put
   them in Universe-scoped K2 docs; workable but not queryable.
2. Cross-character reference to "the same thing" is by name-match
   only. Two characters can drift on the description.
3. Episodes have no way to say `location = <bakery entity>`; scenes
   are described in prose only. Backdrop asset picking remains an
   operator-discipline convention (CAPABILITY_INVENTORY_SESSION_261
   §12).

None of these break the Patch+Rivet+Ruby+Mason near-term dogfood.
All are acceptable v1 gaps that WorldEntity will close later.

**Dependency named:** Relationship v1 does NOT require WorldEntity.
WorldEntity slice, when it lands, will introduce Character↔Location
and Character↔Organization edges as new models — NOT by reshaping
Relationship.

## Direction, type, and payload — take positions

Consolidating positions from Q5, Q6:

- **Direction:** one row per pair; row carries direction via
  paired type fields (`type_from_to` and optionally `type_to_from`)
  OR a single `type` field for symmetric edges. Schema-slice
  decides the exact shape; **this slice's position is one-row-per-
  pair.**
- **Type:** freeform text in v1, operator-authored vocabulary. Not
  an enum. Short length cap and lower-cased at service layer.
- **Payload:** `status` (`active`/`archived`/`former`) + `notes`
  (freeform text) + `established_at` (optional). No strength, no
  numeric fields, no history events on the row.

## Recommended Relationship substrate (R1–R5 chosen)

**Chosen: R5, a narrowed R3 — "R2 scope, R3 shape."**

The row is a Universe-owned canonical fact (R2). Its shape and
Universe attachment are designed so that the deferred narrative
memory substrate can layer history events keyed on the row without
reshaping it (R3-shape without R3-scope).

**Rejected:**

- R1 fails X1 (pre-Episode relationships) and X3 (off-screen
  Mason). Wrong.
- R2 alone is *right* for v1 but loses the shape hint that history
  will layer here. Adopting R5 (which is R2 in v1 with a documented
  R3 trajectory) prevents a future reshape.
- R3 pure is right long-term but requires the memory substrate to
  ship simultaneously. Deferred substrate blocks R3 pure.
- R4 fails principle 2 (knowledge must not define relationships)
  and fails X1/X3. Wrong.

## Recommended Relationship semantics

- **Existence = fact.** A Relationship row exists because the
  operator declared it. It does not exist because two characters
  co-appeared in an Episode.
- **Type / status changes = explicit operator action.** No implicit
  inference. Episode does not mutate. Composition does not mutate.
  Synthesis does not mutate. Only the operator (via SPA edit) or
  an explicit promotion mechanic (future, deferred) mutates.
- **Directionality = paired type fields.** One row; direction in
  the type columns.
- **Universe-scoped.** Both endpoints in the same Universe as the
  row. No cross-Universe edges.
- **Legacy-invisible.** Teammates without a Universe FK cannot
  participate in Relationships (there is no Universe to attach to).
  Their historical talking-head cadence is unchanged; Relationship
  substrate does not touch them (X6).
- **Load-bearing on synthesis prompts.** Episode's context assembly
  loads Relationships involving any cast member. This surfaces
  off-screen relevance (X3) natively.

## Character-in-Universe vs Character-in-Episode-cast vs Character-in-Relationship — three distinct memberships

| Membership | Where stored | Semantic | Cardinality |
|---|---|---|---|
| **Character-in-Universe** | `Teammate.universe` FK (per UNIVERSE_BOUNDARY_V1 §Q12.3) | "This character belongs to this world at all." Broadest. Gates cast eligibility and Relationship eligibility. | Teammate : Universe = N : 1 (nullable for legacy per UNIVERSE_BOUNDARY_V1 §Q6). |
| **Character-in-Episode.cast** | `Episode.cast` M2M (per EPISODE_LIFECYCLE_V1 §Q7) | "This character performs / is on-screen in this specific Episode." Narrower. Per-story. | Episode : Teammate = N : N; cast subset of Universe teammates. |
| **Character-in-Relationship** | Relationship row as `teammate_a` or `teammate_b` (this slice) | "This character has an edge to another character." Orthogonal. | Teammate : Relationship = 1 : N (a character may have many relationships). |

**Load-bearing:** each membership is authored independently. A
character can be in the Universe with zero Relationships (X5,
Ruby-self-intro). A character can have many Relationships and appear
in zero Episodes (a background character). A character can appear in
an Episode's cast and have zero Relationships (uncommon but legal —
a one-off scene partner). A character can have a Relationship and
be off-screen in an Episode that involves the other endpoint (X3,
Mason in Episode B).

**Corollary:** `Episode.cast` MUST NOT be derived from
Relationships. `Relationship` MUST NOT be derived from `Episode.cast`
co-occurrence. Each is operator-authored.

## Off-screen relevance: how Episode B loads Mason context without cast

Restated as a concrete design position (no code, no schema):

- Episode B has `cast = {Patch, Rivet}`.
- At synthesis time, the context-assembly step queries:
  `Relationship WHERE universe = episode.universe AND
  (teammate_a IN cast OR teammate_b IN cast)`.
- For Patch, this returns Patch↔Rivet (both in cast; trivially
  loaded) AND Patch↔Mason (Mason is not in cast; loaded because
  Patch is).
- The synthesis prompt then includes: "Patch's relationships: Rivet
  (partners); Mason (client, notes: 'building AI agent for coffee
  shop, started Episode A')."
- No M2M lookup on Episode.cast to check "is Mason in scope" —
  Mason is loaded through the Patch↔Mason edge.
- Deferred narrative-memory substrate (when it arrives) additionally
  surfaces recent history events on the Patch↔Mason edge to the
  prompt.

**Mechanism at v1 minimum:** the query above plus surfacing the
Relationship row's `type` + `notes` verbatim in the prompt. That is
enough for Episode B to know Mason exists and matters. No memory
substrate required for the minimal case.

## Relationship v1 responsibility table

Only rows this slice touches. All other primitive responsibilities
carry through from UNIVERSE_BOUNDARY_V1 / EPISODE_VS_COMPOSITION_V1
/ EPISODE_LIFECYCLE_V1 unchanged.

| Concern | Relationship (v1) | Episode | Universe | Teammate | Deferred memory substrate |
|---|---|---|---|---|---|
| Edge existence between two characters | own | — | — | — | — |
| Edge type (partners, client, mentor, ...) | own (freeform text) | — | — | — | — |
| Direction / asymmetric type | own (paired type fields) | — | — | — | — |
| Status (active / archived / former) | own | — | — | — | — |
| Freeform notes / description | own | — | — | — | — |
| Universe scoping | direct FK | direct FK | self | direct FK (nullable, legacy) | keyed on Relationship / Episode |
| Character-in-Universe membership | — | — | (via `Teammate.universe`) | own FK | — |
| Cast (per-Episode participation) | — | own M2M | — | — | — |
| Off-screen relevance load into Episode synthesis | queried by cast intersection | reads Relationships | — | — | reads history events |
| Bakery / coffee shop (ownership fact) | — | — | — | own on `business_brief` | — |
| AI-agent project (Episode A subject) | v1 stopgap in `notes` | Episode A is where it started | — | — | eventual home |
| History events ("Mason approached Patch in Episode A") | — | keyed on Episode | — | — | own |
| Canon promotion of Relationship | — | — | — | — | future slice |
| Strength / weight / decay | — | — | — | — | future slice |
| Character↔Location edge | — | — | — | — | new model when Location lands |
| Character↔Organization / Business edge | — | — | — | — | new model when WorldEntity lands |
| Cross-Universe relationships | forbidden | forbidden | — | — | forbidden |

## Relationship v1 minimum boundary (must be minimal)

Restated as a bullet list, minimum viable:

- `id`
- `universe` FK, NOT NULL, CASCADE
- `workspace` FK, NOT NULL, denormalized, `== universe.workspace`
- `teammate_a` FK → Teammate
- `teammate_b` FK → Teammate
- `type` — freeform text (short cap)
- `type_reverse` — optional freeform text (asymmetric edges)
- `status` — enum `active` / `archived` / `former`
- `notes` — freeform text
- `established_at` — optional date/datetime
- `created_by` FK → User (SET_NULL)
- `created_at`, `updated_at`

**Nothing else.** No strength, no canon flag, no callback edges, no
Location / Organization endpoints, no automatic inference, no
Episode M2M, no history events on the row, no per-character
overrides, no cross-Universe mirrors.

## Corrections to prior slices (if any)

**No corrections.** This slice is additive to
UNIVERSE_BOUNDARY_V1, EPISODE_VS_COMPOSITION_V1, and
EPISODE_LIFECYCLE_V1. Specifically:

- **UNIVERSE_BOUNDARY_V1 §Q12** listed Relationship as a future
  primitive to attach to Universe. This slice takes exactly that
  position — Relationship is Universe-scoped.
- **UNIVERSE_BOUNDARY_V1 §Isolation-invariants 1–8** all extend
  naturally to Relationship: cross-Universe forbidden, cross-
  Workspace forbidden, legacy isolation (no Universe ⇒ no
  Relationship), no implicit crossing primitive.
- **EPISODE_VS_COMPOSITION_V1 §Q15** deferred Relationship-history
  persistence to a future substrate and located it at Universe
  keyed on Episode. This slice preserves that (memory substrate is
  the history layer; Relationship row is the state layer) and adds
  the position that history events also key on the Relationship row.
- **EPISODE_LIFECYCLE_V1 §Q7** listed Episode.cast M2M with the
  refinement that cast may be empty until first Composition
  attaches. This slice preserves that AND adds the position that
  Relationship queries at synthesis time key on cast intersection,
  so an empty cast returns no off-screen Relationship context (a
  DRAFT Episode with no cast surfaces no Relationships to
  synthesis; only ACTIVE Episodes with populated cast benefit).

Where the operator's *stress-test framing* was slightly incomplete:

- The brief phrased "the persistent thing" for the AI-agent project
  as either "the project (a Universe-owned WorldEntity)," "a
  Relationship (Patch↔Mason with a project payload)," or "an
  Episode-linkage (Episode B references Episode A)." **All three
  are correct answers at different substrate maturities.** v1's
  best answer is Relationship.notes (stopgap). Once memory substrate
  lands, it becomes history events on the Patch↔Mason edge. Once
  WorldEntity lands, the project can additionally be a first-class
  subject referenced by multiple Episodes. The three answers are not
  mutually exclusive; they layer.

## Isolation invariants

Restated (some new, some extending prior slices):

1. **Workspace privacy invariant (existing, preserved).** No
   Relationship row crosses Workspace boundaries. Enforced via
   `Relationship.workspace == teammate_a.workspace ==
   teammate_b.workspace == universe.workspace`.
2. **Universe privacy invariant (existing, extended).** No
   Relationship row crosses Universe boundaries.
   `Relationship.universe == teammate_a.universe ==
   teammate_b.universe`. Both endpoints must be in the same Universe
   as the row. Cross-Universe attach rejected at `clean()` /
   `m2m_changed pre_add` per UNIVERSE_BOUNDARY_V1 §Q9 pattern.
3. **Legacy isolation invariant (existing, extended).** A Teammate
   with `universe=NULL` cannot participate in a Relationship (there
   is no Universe to attach to). Mike, Repo Red, Tulsi (legacy)
   have no Relationships. Their historical workflow is unchanged.
4. **No self-loop.** `teammate_a != teammate_b`. No relationship
   from a character to themselves.
5. **Uniqueness invariant.** At most one Relationship per
   `(universe, teammate_a, teammate_b)` normalized pair. Duplicate
   creation rejected.
6. **No implicit creation.** Relationship rows are created ONLY by
   explicit operator action (SPA gesture, API call). Episode
   creation, Composition creation, synthesis, cast-mutation, and
   retrieval MUST NOT create Relationship rows. Same discipline as
   `EPISODE_LIFECYCLE_V1 §H3` explicit-only Episode.
7. **No implicit mutation.** Relationship type / status / notes
   change ONLY by explicit operator edit or explicit promotion
   mechanic. Episode / Composition / synthesis / rerender MUST NOT
   mutate a Relationship row. Same discipline as Episode's
   "rerender does not duplicate narrative history"
   (EPISODE_VS_COMPOSITION_V1 §Isolation-invariant 7).
8. **Cast-independence invariant.** Relationship queries at
   synthesis time key on cast intersection
   (`teammate_a IN cast OR teammate_b IN cast`), NOT on both
   endpoints being in cast. This is the mechanism that makes
   off-screen relevance (X3) work.
9. **Deletion policy invariant.** Deletion of a Teammate must
   handle its Relationships explicitly (CASCADE or PROTECT — schema
   slice decides). Deletion of a Universe CASCADEs its Relationships.
   Deletion of an Episode does NOT touch Relationships (Episodes are
   history; Relationships are state).
10. **No implicit cross-Universe crossover primitive.** Same as
    UNIVERSE_BOUNDARY_V1 invariant 5. If cross-Universe relationships
    ever need to exist (crossover story), that's an explicit
    primitive with its own name and audit trail — not a nullable
    Universe FK or a bypass.

## Legacy behavior (Mike / Tulsi / Repo Red)

Mike-the-plumber, Tulsi, Repo Red, and every other pre-Universe
Teammate:

- Continue to have `Teammate.universe = NULL` (per
  UNIVERSE_BOUNDARY_V1 §Q6).
- Cannot participate in Relationships. There is no Universe to
  attach a Relationship row to. Relationship substrate does not
  touch them.
- Continue their workspace-scoped talking-head cadence (X6). Every
  render creates a Composition (per EPISODE_LIFECYCLE_V1 §H3, with
  `episode=NULL`). Composition carries its own `operator_topic`.
  No Episode, no Relationship, no continuity substrate — and this
  is the *correct* state for content that is not a story.
- Migration path: if the operator ever wants Mike to have
  Relationships, they first migrate Mike to a Universe (bespoke
  ½-slice per UNIVERSE_BOUNDARY_V1 §Q6 legacy policy), then
  Relationships become available. Bulk migration remains rejected.

**Do not touch legacy Teammates.** Every existing invariant about
their behavior remains untouched by this slice.

## Unresolved questions

New questions this slice creates or leaves open:

1. **App-name / home for Relationship.** `apps/relationships`,
   `apps/universe` (implying Universe primitive lives in the same
   app), or extend the dormant `apps/memory` to cover both
   relationship state and narrative memory events? Schema slice.
2. **Type vocabulary.** Freeform text with product-side conventions,
   or a bootstrapped enum with `OTHER` escape hatch? Position:
   freeform in v1; consider bootstrapped conventions in v2 based on
   observed operator vocabulary. UX slice.
3. **Direction encoding.** Single `type` field with an
   implicit-symmetric assumption + optional `type_reverse` when
   asymmetric, vs always-paired `type_from_to` + `type_to_from`?
   Schema slice.
4. **Ordering rule for `(teammate_a, teammate_b)` normalization.**
   Alphabetical on UUID? Alphabetical on name? Insertion order? The
   choice affects direction-encoding ergonomics. Schema slice.
5. **Cascade policy on Teammate delete.** CASCADE the Teammate's
   Relationships, PROTECT the delete, or SET_NULL one endpoint?
   Position: probably CASCADE (edges to a deleted character are
   meaningless) but a case exists for PROTECT (deletion of a
   Teammate with active Relationships is likely an operator
   mistake). Schema slice.
6. **Cascade policy on Universe delete.** CASCADE is natural
   (Universe deletion means the world is gone; edges within it are
   meaningless). Schema slice.
7. **`Episode.cast` interaction.** Does adding a Teammate to
   Episode.cast prompt the operator "create a Relationship?" Or
   is Relationship authorship strictly separate? Position: strictly
   separate. UX slice may layer prompts on top.
8. **Symmetric-only shortcut.** For symmetric edges (`spouses`,
   `siblings`, `partners`), do we need `type_reverse` at all? A
   single `type = 'partners'` is complete. Schema-slice cleanliness
   question.
9. **Implicit history event on first Episode co-occurrence.** When
   Patch and Mason first co-appear in Episode A, should the memory
   substrate (deferred) auto-log a "first co-appearance in Episode
   A" event? Position: yes (a memory-substrate concern, not a
   Relationship-substrate concern, so out of this slice). Confirm
   in the memory-substrate slice.
10. **SPA affordance for creating a Relationship.** Where in the
    Teammate detail UI does the operator create/edit Relationships?
    Inline on Teammate? Separate Universe > Relationships page? UX
    slice.
11. **Prompt formatting of Relationship context.** How does
    Episode's synthesis prompt render the Relationship rows and
    notes? Structured list vs freeform prose vs XML fence? K6
    contract slice.
12. **Relationship visibility M2M on knowledge.** Analogous to
    `KnowledgeDocument.spokespeople` — could a KnowledgeDocument be
    scoped to "characters with a Relationship of type X"? Deferred;
    probably premature; call out only.
13. **Business ownership as a "role" concept.** Ruby-owns-a-bakery
    could also be represented as `Teammate.role = business_owner`
    with a `business_name` field. This would generalize better once
    WorldEntity lands. Deferred to a Teammate-schema-refactor slice.
14. **Off-screen relevance loading limit.** If Patch has 47
    Relationships, does Episode B's synthesis load all 47? Position:
    yes v1 (small counts); pagination / relevance-scoring is a
    future performance concern.
15. **Whether `established_at` is inferred vs authored.** If the
    operator declares the Relationship at Universe creation, we know
    `established_at ≈ Universe.created_at`. If declared at Episode-A
    creation, `established_at ≈ Episode.created_at`. Position: leave
    optional and operator-authored; do not auto-populate.

## Risks if boundary is wrong

1. **Implicit Relationship creation from Episode cast.** If cast
   creation auto-creates Relationships, every incidental co-scene
   ("Mike answers a customer call in a background scene") mints a
   permanent Relationship. Row count balloons; type is undefined;
   canon corrupts. Mirror of UNIVERSE_BOUNDARY_V1 §Q8's rejected
   auto-default; do not repeat.
2. **Relationships derived from co-occurrence (R1).** X1 and X3
   fail. Off-screen relevance impossible without inventing
   projection heuristics that degrade into R2 with worse ergonomics.
3. **No Relationship model at all (R4).** X1 (pre-Episode
   relationships) has no representation; principle 2 (knowledge
   does not define relationships) is violated because K2 docs
   become the de-facto relationship home.
4. **Knowledge-gated Relationship creation.** If Relationship
   creation ever silently gates on K2 corpus existence, Ruby (low
   K2) can't have relationships. Violates principle 2. Explicitly
   forbidden by design invariant.
5. **Universe-crossing edges.** A Patch↔<character-in-another-Universe>
   edge leaks continuity across worlds. Every UNIVERSE_BOUNDARY_V1
   invariant this slice extends is designed to prevent this.
6. **Storing bakery/coffee-shop as a Relationship type.** Encoding
   `Ruby-owns-Bakery` as a Relationship (with `Bakery` as a
   Teammate) corrupts the Teammate model. Bakery is not a character.
   The v1 answer is `Teammate.business_brief`; the eventual answer
   is WorldEntity. Never Teammate.
7. **Episode mutating Relationship state on retry/rerender.** If
   Episode retry re-runs "Mason became client" mutations, canon
   corrupts. Explicitly forbidden by invariant 7 (no implicit
   mutation).
8. **Assuming symmetric direction always.** Encoding all edges as
   symmetric loses Patch-sees-Mason-as-client vs Mason-sees-Patch-
   as-service-provider distinction. Design has to support asymmetric
   from day one, even if v2 tightens the schema.
9. **Auto-creating Relationships when Universe is created.** Mirror
   of UNIVERSE_BOUNDARY_V1 §Q8's default-Universe rejection: silent
   defaults recreate the overload we're trying to break. Universe
   creation must NOT create Relationships.
10. **Coupling `Episode.cast` derivation to Relationships.** Making
    "cast = characters with active Relationships to primary
    spokesperson" is wrong. Cast is a per-story authorship gesture;
    Relationships are Universe-durable facts. Merging them
    over-constrains both.

## STOP

Research only. No schema. No migrations. No code. Every load-bearing
claim is cited to file:line in `shell/apps/`, to prior design docs
(UNIVERSE_BOUNDARY_V1.md, EPISODE_VS_COMPOSITION_V1.md,
EPISODE_LIFECYCLE_V1.md, CAPABILITY_INVENTORY_SESSION_261.md), or to
the operator's SESSION 261 brief.
