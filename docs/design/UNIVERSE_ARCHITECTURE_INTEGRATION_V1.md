---
title: "Universe Architecture Integration v1 — Integrated Boundary Checkpoint"
status: research — integration checkpoint (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"      # corrected EPISODE_VS_COMPOSITION_V1 auto-creation
  - "design/RELATIONSHIP_BOUNDARY_V1.md"
  - "design/WORLD_ENTITY_BOUNDARY_V1.md"  # partially corrected by this slice (agency-not-voice)
scope: >
  Integrate the six prior SESSION 261 slices into one coordinate
  system. Verify no contradictions between them; where prior slice
  language becomes misleading under the operator's agency-not-voice
  correction, name the exact language and prescribe the fix. No
  schema, no code, no migrations, no Django field proposals except
  where absolutely necessary to explain semantics.
---

# Universe Architecture Integration v1 — Integrated Boundary Checkpoint

## Purpose / scope

The SESSION 261 research arc produced six committed design slices
that each answered one boundary question at a time:

1. `CAPABILITY_INVENTORY_SESSION_261.md` — what exists in the
   repository today, model by model.
2. `UNIVERSE_BOUNDARY_V1.md` — Workspace = tenant, Universe = world,
   Universe v1 owns only `Teammate.universe` and
   `KnowledgeDocument.universe`, no auto-defaults.
3. `EPISODE_VS_COMPOSITION_V1.md` — Episode wraps Composition
   (1:N), Composition retains render provenance.
4. `EPISODE_LIFECYCLE_V1.md` — Episode is explicit-only; corrected
   the prior slice's auto-creation proposal.
5. `RELATIONSHIP_BOUNDARY_V1.md` — Character↔Character Relationship
   as Universe-owned canonical row (R5, "R2 scope, R3 shape"),
   off-screen relevance via cast-intersection.
6. `WORLD_ENTITY_BOUNDARY_V1.md` — WorldEntity for persistent
   non-character things (W4, base row + optional future sidecars);
   the slice originally used "does not speak" as the defining
   boundary between Character and WorldEntity.

**Load-bearing operator correction arrived AFTER the WorldEntity
slice landed:** voice is NOT the defining boundary between Character
and WorldEntity. Agency is. That correction is the primary reason
this integration slice exists — it names every place the WorldEntity
document's language becomes misleading and prescribes the fix.

This slice is an **integration checkpoint**, not another primitive
audit. Its output is (a) a corrected coordinate system, (b) an
explicit contradiction list, (c) a STOP/GO verdict for schema work.

**Out of scope for this slice** (unchanged from prior deferrals):
schema DDL, migrations, Django field additions, narrative memory
substrate, canon promotion mechanics, Character↔WorldEntity edges,
WorldEntity↔WorldEntity edges, educational curriculum substrate,
Location specialization, business/project sidecars, SPA UX design,
voice/POV versioning, cross-Universe crossover primitive.

## Load-bearing operator correction (agency-not-voice)

**Rule.**
> **Character = persistent narrative ACTOR with agency / identity /
> behavior / relationships.**
> **WorldEntity = persistent narrative THING that is not itself an
> actor.**
> Voice is NOT the defining boundary. A silent recurring character
> can still be a Character. A non-speaking dog / robot / creature may
> be a Character if it has narrative agency.

**Where this replaces prior WORLD_ENTITY_BOUNDARY_V1.md language.**
The document consistently used "speaks vs does not speak" as its
Character/WorldEntity discriminator. That framing is now misleading
and must be corrected in-place. See §Corrections required for the
exact sentences.

**Consequences of the correction (integrated).**

- The vet-clinic recurring dog with narrative agency is a
  **Character**, not a WorldEntity `kind=animal`. It uses the
  CharacterIdentity substrate's `non_human` branch
  (`identity/models.py:96–108`; branch schema currently the
  substrate-exercise-only `non_human_test_schema_v1.yaml`).
- A recurring silent character (a mute human sidekick with agency)
  is a **Character**, not a WorldEntity.
- A recurring prop with no agency (Rivet's wrench, a power cutoff
  switch that just sits there) may be a WorldEntity or remain in
  Episode prose per operator declaration.
- The prior "promotion between Character and WorldEntity is
  forbidden" invariant (`WORLD_ENTITY_BOUNDARY_V1.md` §Character-vs-
  WorldEntity table, last row) SURVIVES the correction. The distinction
  is still crisp: agency-bearing → Character, thing-only → WorldEntity.
  A dog upgraded from "silent WorldEntity" to "silent Character with
  agency" is not a WorldEntity gaining a voice — it is the operator
  discovering the entity is actually an actor, and the correct path
  is a new Character (Teammate) creation.
- The Character Presence Language dependency called out in
  `CAPABILITY_INVENTORY_SESSION_261.md §6` becomes more pressing:
  non-speaking-non-human Characters (silent dog with agency) need
  the substrate to accept them BEFORE they can be created. Until
  Character Presence Language lands, silent-agency creatures cannot
  land as Characters and remain in a temporary hold-state (prose
  in Episode, or the operator defers creation).

**No auto-detection.** The "does this creature have agency?" question
is operator-authored at creation time. No code path infers agency
from Episode co-occurrence, K2 content, or any other signal. Same
discipline as every other Universe primitive.

## Prior decisions carried forward (integrated)

Restated once, load-bearing across the whole system.

1. **Workspace = tenant/security boundary. Universe = world.** The
   outer wall is Workspace; the inner wall is Universe within a
   workspace. Cross-tenant is impossible; cross-Universe is possible
   only via explicit operator gesture, never implicit.
   (`UNIVERSE_BOUNDARY_V1.md` §Q1–§Q13.)
2. **Universe is opt-in and prospective.** No auto-default Universe.
   Legacy Teammates keep `universe=NULL` and behave exactly as
   today. (`UNIVERSE_BOUNDARY_V1.md` §Q6–§Q8.)
3. **Every canonical primitive (Universe, Episode, Relationship,
   WorldEntity, Character) is created by explicit operator action.**
   No auto-creation. No LLM-generates → auto-canon. No implicit
   creation from prose, cast, retrieval, or Composition submission.
   (`UNIVERSE_BOUNDARY_V1.md` §Q8; `EPISODE_LIFECYCLE_V1.md` §H3;
   `RELATIONSHIP_BOUNDARY_V1.md` §Isolation invariant 6;
   `WORLD_ENTITY_BOUNDARY_V1.md` §Isolation invariant 5.)
4. **Legacy character data informs compatibility; it does not define
   Universe semantics.** (SESSION 261 principle; every slice.) Mike,
   Repo Red, Tulsi, and the 81 historical Compositions in
   `chriss-workspace` continue to work.
5. **Knowledge may describe; knowledge must not constitute.** A K2
   doc about the bakery does not create the bakery. Deleting the doc
   does not delete the bakery. (`WORLD_ENTITY_BOUNDARY_V1.md`
   §Knowledge-vs-WorldEntity.) Applied to Characters: a low-K2
   character (Ruby) still fully exists.
6. **Episode wraps Composition (1:N).** Composition is a render
   attempt/variant; Episode is the narrative event. Rerender does
   not duplicate narrative history.
   (`EPISODE_VS_COMPOSITION_V1.md` §Decision.)
7. **Relationship = Character↔Character only in v1.** One row per
   pair, Universe-scoped. Off-screen relevance via cast-intersection.
   Character↔WorldEntity edges are a NEW model, deferred.
   (`RELATIONSHIP_BOUNDARY_V1.md` §Q10, §Q12, §Off-screen mechanism.)
8. **No implicit cross-Universe crossover primitive.** No bypass
   flags. If it ever exists, it's an explicit named primitive with
   audit trail. (`UNIVERSE_BOUNDARY_V1.md` §Isolation invariant 5.)

## Canonical architecture diagram (ASCII)

```
User
 │
 ├── owns ──▶ Workspace  (tenant boundary — outer wall)
 │             │
 │             ├── Membership (seats/roles; scaffold, only OWNER used)
 │             ├── Billing anchor / Engine connections (tenant)
 │             ├── Asset library  (pixels/audio; tenant-scoped)
 │             │
 │             ├── Universe *  (world boundary — inner wall; opt-in)
 │             │    │
 │             │    ├── Character *  (Teammate; ACTOR with agency)
 │             │    │    ├── CharacterIdentity (substrate, versioned)
 │             │    │    │     ├── CharacterIdentityVersion
 │             │    │    │     ├── IdentityReference *
 │             │    │    │     ├── ApprovedRepresentationBundle
 │             │    │    │     └── GenerationRecord * (append-only)
 │             │    │    ├── business_brief / personality / voice*
 │             │    │    └── Character-owned K2 attach (M2M)
 │             │    │
 │             │    ├── WorldEntity *  (THING without agency)
 │             │    │    └── name / kind (hint) / description / status
 │             │    │
 │             │    ├── Relationship *  (Character↔Character edge)
 │             │    │    ├── teammate_a / teammate_b (normalized pair)
 │             │    │    ├── type / type_reverse (freeform, directional)
 │             │    │    ├── status / notes / established_at
 │             │    │    └── [FUTURE: history events keyed on Relationship]
 │             │    │
 │             │    ├── KnowledgeDocument *  (world-scoped canon/facts)
 │             │    │    ├── KnowledgeChunk *
 │             │    │    └── KnowledgeDocumentSpokesperson M2M
 │             │    │
 │             │    ├── Episode *  (narrative EVENT; explicit)
 │             │    │    ├── operator_topic (verbatim; STORY-authoritative)
 │             │    │    ├── title / state (DRAFT/ACTIVE/ARCHIVED)
 │             │    │    ├── cast M2M → Character  (subset of Universe)
 │             │    │    ├── referenced_entities M2M → WorldEntity (may be ∅)
 │             │    │    └── Composition * (0..N render attempts/variants)
 │             │    │          ├── CompositionStep * (primitive pipeline)
 │             │    │          ├── synthesized_brief / rejected_synthesis
 │             │    │          ├── knowledge_chunk_ids / verification_*
 │             │    │          ├── template_kind / mock_mode / cost_*
 │             │    │          ├── operator_topic (PER-ATTEMPT copy)
 │             │    │          └── final_asset → Asset(role=CLIP)
 │             │    │
 │             │    └── [FUTURE deferred substrates]
 │             │         ├── Narrative memory (events keyed on Episode / Relationship)
 │             │         ├── Character↔WorldEntity edges
 │             │         ├── WorldEntity↔WorldEntity edges
 │             │         ├── Episode canon promotion / canonical_composition
 │             │         ├── Educational subject / curriculum substrate
 │             │         └── Per-Universe palette / brand identity
 │             │
 │             └── LEGACY PATH (universe = NULL, unchanged)
 │                  ├── Teammate (Mike, Repo Red, Tulsi, ...)
 │                  ├── KnowledgeDocument (workspace-wide empty-M2M)
 │                  ├── Composition (episode = NULL; render-only)
 │                  └── No Relationship / WorldEntity / Episode access
 │
 └── (PublishBundle: workspace-scoped; anchored on Asset(role=CLIP);
       transitively linked to Episode via Composition.final_asset)

Distribution / observability:
  Composition ─▶ Asset(role=CLIP) ─▶ PublishBundle ─▶ PublishVariant *
  RealtimeSession → transitive Universe via spokesperson.universe
  ConversationThread → transitive Universe via spokesperson.universe
```

## Primitive responsibility table (10 rows)

| Primitive | Owns | Does NOT own | Lifecycle owner | Isolation boundary | Required relationships |
|---|---|---|---|---|---|
| **Workspace** | owner, membership/seats, slug (URL routing), billing anchor, engine credentials, Asset library, KnowledgeDocument dedup namespace `(workspace, content_hash)`, Teammate naming namespace `(workspace, name)`. | World semantics (cast, canon, continuity), Universe count, per-world palette. | Owner user (PROTECT). | Tenant — nothing crosses. | 0..N Universes; 0..N legacy (universe=NULL) Teammates. |
| **Universe** | identity (name, per-workspace slug, created_at, archived_at), Workspace parent FK. **v1 owns ONLY the two anchor points** (`Teammate.universe`, `KnowledgeDocument.universe`) by virtue of those FKs pointing here. | Cast M2M (derived from Teammate.universe), K2 M2M (derived from KnowledgeDocument.universe), palette, engine credentials, billing, canon promotion mechanic. | Operator, explicit. Never auto-default. | World — within a workspace, nothing crosses Universe. | 1 Workspace parent; 0..N Characters (Teammates); 0..N KnowledgeDocuments; 0..N Episodes; 0..N Relationships; 0..N WorldEntities. |
| **Character (Teammate)** | name, business_brief, personality, voice fields, POV, `who_you_help`, `what_you_sell`, `always_emphasize`, `never_say`, `desired_feeling`, Universe FK (nullable = legacy), CharacterIdentity link. **Character = persistent narrative ACTOR with agency/identity/behavior/relationships.** | Relationships (row-owned by Relationship), Cast decisions (row-owned by Episode), World things (WorldEntity). Does not own the Universe's canon; owns only its own perspective/knowledge attach. | Operator, explicit. Universe FK is opt-in. | Universe (if assigned); Workspace (legacy). | 0..1 Universe (nullable); 0..1 CharacterIdentity (partial-unique); 0..N Relationships; 0..N KnowledgeDocument M2M attachments. |
| **Relationship** | edge between two Characters in the same Universe: `teammate_a`, `teammate_b`, `type` (freeform), optional `type_reverse` (asymmetric), `status` (`active`/`archived`/`former`), `notes`, `established_at`. | History events (deferred memory substrate). Strength/weight (deferred). Character↔WorldEntity edges (NEW model, deferred). Self-loops (forbidden). Cross-Universe edges (forbidden). | Operator, explicit. Never implicit from cast co-occurrence. Never mutated by Episode/Composition/synthesis. | Universe (both endpoints and row). | Requires 2 Characters in the same Universe. Referenced by Episode context assembly via cast-intersection. |
| **WorldEntity** | Universe-scoped THING identity: `name`, `kind` (freeform hint), `description`, `status` (`active`/`archived`), Universe FK, workspace denormalized. **WorldEntity = persistent narrative THING that is not itself an actor.** | Voice, K2 corpus of its own, Character↔WorldEntity edges (new model, deferred), owner-character FK (deferred), spatial coords, sidecar detail (BusinessDetails, ProjectDetails — deferred). No agency. | Operator, explicit. Never LLM-suggested. | Universe. | 0..N Episode M2M references (`Episode.referenced_entities`). |
| **Episode** | Universe-scoped narrative EVENT: `operator_topic` (verbatim; story-authoritative), `title`, `state` (DRAFT/ACTIVE/ARCHIVED), `cast` M2M → Character (subset of Universe; may be empty at create), `referenced_entities` M2M → WorldEntity (may be empty), Universe FK. Explicit-only. Episode is itself the operator saying "this is a story." | Render mechanics, per-attempt content (synthesized_brief, verification_*, knowledge_chunk_ids, template_kind — those are Composition's). Canon flag (deferred). Educational objective/audience (deferred). Sequence marker (deferred). Location scalar (deferred; use referenced_entities M2M). | Operator, explicit. `∅ → DRAFT` on operator "New Episode" gesture only. | Universe. | 1 Universe; 0..N Compositions; 0..N cast Characters; 0..N referenced WorldEntities. |
| **Composition** | render-attempt/variant: `status`, `error_message`, `final_asset`, `cost_estimate_micros`/`cost_actual_micros`, `mock_mode`, `template_kind`, `synthesized_brief`, `rejected_synthesis`, `knowledge_chunk_ids`, `verification_status`/`verification_warnings`, `writing_contract_version`, per-step CompositionStep pipeline, `operator_topic` (per-attempt copy), created_by/timestamps. | Story-level intent (Episode owns). Narrative events. Canon. Relationship/entity state. | Operator, explicit. `episode` FK is nullable (legacy) but never auto-populated with a freshly minted Episode. | Workspace (direct); Universe (transitive via Episode when attached). | 0..1 Episode; 0..N CompositionSteps; 0..1 Script (optional); 0..1 final_asset. |
| **Knowledge (KnowledgeDocument + KnowledgeChunk + M2M)** | corpus (PDF, URL, prose), embedding chunks, per-tenant dedup on `(workspace, content_hash)`, visibility M2M (`spokespeople`), Universe FK (nullable — legacy = workspace-wide). | Existence of things it describes (WorldEntity / Character / Relationship). Canon promotion. | Operator upload; auto-embedding after ingest. | Workspace (dedup); Universe (retrieval scope). | Referenced by Composition/synthesis via Universe-scoped retrieval; empty-M2M means "visible to every Character in the same Universe" (for Universe-scoped docs) OR "every Character in the workspace with universe=NULL" (for legacy docs). |
| **Asset** | rendered pixels/audio artifact; `asset_type` / `role` / `purpose` / `subject` prose, `source_spec` JSON, per-workspace scope. | World identity, character identity, entity identity. An Asset can DEPICT a WorldEntity/Character; it does not IS one. | Composition / library upload. | Workspace only. Universe soft-link (nullable back-ref) MAY be added later; not v1. | Referenced by Composition (`final_asset`, step inputs), PublishBundle (`source_clip`), IdentityReference. |
| **Narrative Memory (DEFERRED — not v1)** | event log / promise ledger / history events keyed on Episode and/or Relationship / callback edges. | Row identity (which lives on Episode/Relationship/WorldEntity). Canon promotion mechanic (separate deferred). | Deferred. | Universe. | Attaches keyed on Episode + Relationship + WorldEntity ids. Additive to those; does not reshape them. |

## Dependency DAG

```
Workspace
   │
   └── Universe
         │
         ├── Character (Teammate)  ─────────┐
         │      └── CharacterIdentity …     │
         │                                  │
         ├── KnowledgeDocument              │
         │      └── KnowledgeChunk          │
         │      └── KnowledgeDocumentSpokesperson (M2M → Character)
         │                                  │
         ├── WorldEntity                    │
         │                                  │
         ├── Relationship                   │  (both endpoints → Character)
         │      └── (teammate_a, teammate_b)◀
         │
         └── Episode
                ├── cast M2M                → Character  (subset of Universe)
                ├── referenced_entities M2M → WorldEntity
                └── Composition (0..N)
                       ├── CompositionStep *
                       ├── final_asset      → Asset  (Workspace)
                       └── Script  (optional)

Legacy (universe = NULL):
   Workspace ─▶ Teammate ─▶ Composition (episode = NULL)
   Workspace ─▶ KnowledgeDocument (empty M2M = workspace-wide)

DAG topology: acyclic. Every edge points "outward" from Workspace
toward leaves. No back-edges. Character has no FK to Relationship,
Episode, or WorldEntity — those primitives point AT Character.
Same for WorldEntity (Episode points at it, not the reverse).
Composition points at Episode (optional). No self-loops on any
primitive.
```

**No circular dependencies.** Verified by walking each primitive's
FK/M2M list. The only "graph-like" structure is Relationship (edges
between two Characters in the same Universe), which is a
Universe-owned M2M-with-payload — still a DAG at the primitive
level.

**Implementation order implication:** primitives can be introduced
strictly outward from Workspace (which already exists). See
§Model implementation sequencing.

## Decision rules

### Actor vs Thing (Character vs WorldEntity)

> **If it has narrative agency — makes decisions, holds relationships,
> exhibits behavior — it is a Character.** (Teammate + CharacterIdentity,
> possibly non-speaking.)
>
> **If it is a persistent narrative reference point but does not itself
> act — a place, a business, a project, a landmark, an inert prop —
> it is a WorldEntity.**
>
> Voice does NOT decide. A silent dog with agency is a Character. A
> speaking-loudspeaker prop (a jingle-emitting sign) with no agency is
> a WorldEntity. Agency is operator-declared at creation; no code
> path infers agency.

### Canon vs generated content

> **Canon rows** (Universe, Character, Relationship, WorldEntity,
> Episode) are created and mutated ONLY by explicit operator action.
> No LLM output, no synthesis, no rerender, no Composition submission,
> no retrieval, no cast mutation may create or mutate a canon row.
>
> **Generated content** (Composition.synthesized_brief,
> Composition.rejected_synthesis, Composition.knowledge_chunk_ids,
> render pixels/audio Assets, K6 prompt trace) is per-attempt
> evidence produced by the pipeline. It never mutates canon.
>
> **Promotion path**: LLM output the operator loves → operator
> explicitly promotes (writes to a canon row via SPA gesture) →
> canon row is the source of truth. No auto-canon.

### On-screen vs off-screen relevance

> **On-screen** = present in `Episode.cast` (Character) or
> `Episode.referenced_entities` (WorldEntity). Operator-declared per
> Episode.
>
> **Off-screen but relevant** = surfaced by cast-intersection queries
> at synthesis time. Relationships load where `teammate_a IN cast OR
> teammate_b IN cast` (surfaces Mason to Episode B when Patch is in
> cast). WorldEntity off-screen relevance ships v1 only via explicit
> `referenced_entities`; edge-based auto-surfacing is deferred to
> the Character↔WorldEntity edge slice.
>
> **Legal-empty**: `Episode.cast` may be empty at DRAFT (populated
> when first Composition attaches, or explicitly by operator).
> `Episode.referenced_entities` may be empty forever (talking-head
> Episode without entity references — legal and common).

### Story vs render

> **Story** = Episode. Owns `operator_topic` (verbatim story intent),
> title, cast, referenced entities. Rerender never duplicates story
> history.
>
> **Render** = Composition. Owns per-attempt state (synthesis output,
> verification, cost, template kind, mock mode, step pipeline, final
> asset). Retry/cutdown/aspect variant = new Composition FK'ing same
> Episode. A Composition without an Episode (legacy or standalone) is
> not broken — it is a video that is not part of a story.

### Knowledge vs existence

> **Existence** of a Character, Universe, Relationship, WorldEntity,
> or Episode is constituted by an operator-authored row. K2
> knowledge may describe any of them but does NOT constitute any of
> them. Deleting a K2 doc about Ruby's bakery does not delete the
> bakery WorldEntity (if promoted). Uploading a K2 doc about a
> "coffee shop" does not create a WorldEntity for it.
>
> **Character with low K2 is fully a Character.** Ruby the Fox exists
> regardless of corpus size. Knowledge-gated creation is explicitly
> forbidden.

### Legacy compatibility

> Legacy Teammates (`universe = NULL`) and legacy Compositions
> (`episode = NULL`) continue to work under pre-Universe workspace-
> wide semantics. They cannot participate in Relationships, WorldEntity
> references, or Universe-scoped Episode canon. Universe-scoped
> Characters never retrieve from workspace-wide (Universe=NULL) K2
> docs. Migration is per-Teammate bespoke; bulk migration is
> rejected.

## Load-bearing story-test walkthroughs

### T-A. Patch/Rivet + Ruby/Mason (Episodes A–E) — the full scenario

Universe: `patch-rivet-workshop`. Characters: Patch, Rivet, Ruby the
Fox, Mason the Bear. WorldEntities: Workshop, Bakery, Coffee Shop,
AI Agent Project. Relationships: Patch↔Rivet (partners); Ruby↔Mason
(neighbors, per operator); Patch↔Mason (prospect/client).

| Episode | Cast | referenced_entities | Off-screen loaded via cast-intersection | Outcome |
|---|---|---|---|---|
| **A** — Mason approaches Patch about AI agent | {Patch, Mason} | {Coffee Shop, AI Agent Project} | Patch↔Rivet (Rivet not in cast); Mason↔<any Mason edges>. | Clean. Episode intent = "Mason approaches Patch about building AI agent for coffee shop." Composition 1a synthesizes; if fails, Composition 1b retries under same Episode. |
| **B** — Patch + Rivet in workshop discussing Mason's project | {Patch, Rivet} | {AI Agent Project, Coffee Shop} (operator-declared) | Patch↔Mason (Mason absent but surfaced); Patch↔Rivet (both in cast). | Clean. Mason surfaces to synthesis via cast-intersection query on Relationship; Coffee Shop + Project surface via referenced_entities M2M. |
| **C** — Patch installs AI agent at Mason's coffee shop | {Patch, Mason} maybe {Patch, Rivet, Mason} | {Coffee Shop, AI Agent Project} | Patch↔Rivet if Rivet not in cast; Patch↔Mason (both in cast). | Clean. Same Coffee Shop WorldEntity row as Episode A — continuity guaranteed by construction, not operator-discipline. |
| **D** — Ruby visits Mason's coffee shop | {Ruby, Mason} | {Coffee Shop} | Ruby↔Mason (neighbors); Ruby↔<Ruby's edges>; Mason↔Patch (Patch absent but surfaced). | Clean. Same Coffee Shop row again. Ruby's business_brief carries "owns a bakery" fact. Ruby↔Coffee Shop edge is deferred (Character↔WorldEntity edge model); v1 relies on operator populating referenced_entities. |
| **E** — Months later, Patch references what happened with Mason's AI agent | {Patch} | {AI Agent Project} | Patch↔Mason surfaces via cast-intersection (Mason absent); Patch↔Rivet if Rivet not in cast. | Clean. Project WorldEntity carries the ongoing reference; history events are deferred to memory substrate (v1 uses Relationship.notes / Episode.operator_topic as stopgap). |

**All five Episodes are handled correctly** by the integrated
architecture. Load-bearing property: Coffee Shop identity survives
Mason's absence from Episode B/E and Ruby's visit in Episode D
because WorldEntity is Universe-scoped, not character-scoped.

### T-B. Standalone Patch talking-head, not intended as an Episode

Universe: `patch-rivet-workshop` (or none). Operator creates a
one-off Patch talking-head. No story context.

- **With Universe, no Episode:** Composition created with
  `episode = NULL`, `spokesperson = Patch`, `template_kind =
  talking_head`, `operator_topic` on the Composition itself.
  Universe-scoped retrieval on synthesis (Patch's Universe). No
  Relationship/WorldEntity references. Legal. Correct.
- **Without Universe (legacy):** same as above but Patch would need
  to be legacy (`universe = NULL`) — not this scenario, since Patch
  is Universe-scoped. In practice: if the operator wants a
  Universe-scoped Character to do a non-story render, `episode = NULL`
  is the affordance.
- **No auto-Episode** is minted. No noise row. Correct per
  `EPISODE_LIFECYCLE_V1.md §H3`.

### T-C. First-grade educational Universe

Universe: `mrs-alvarez-first-grade`. Character: Ms. Alvarez.
WorldEntities: classroom (kind=place, optional). Episodes: "why
plants need sunlight" (talking-head; cast = {Alvarez}; no
referenced_entities).

- Episode carries the intent. Composition 1a = 90s render. Composition
  1b = 30s cutdown (same Episode, different `target_duration_seconds`
  kwarg).
- **Educational objectives / audience / lesson** are DEFERRED per
  `WORLD_ENTITY_BOUNDARY_V1.md §Q9 T3` (strong negative boundary —
  WorldEntity does NOT absorb educational subjects). v1 ships without
  a curriculum substrate. Operator uses Episode.operator_topic and
  K2 docs for lesson content.
- **Gap acknowledged**: 40 subjects/year for one teacher have no
  first-class addressability. Operators with heavy education workflows
  will feel this. The EDUCATION slice is a named future dependency,
  not a v1 blocker.

### T-D. Plumbing-company Universe

Universe: `pipewise-plumbing`. Characters: Bea (senior), Ricky
(apprentice). WorldEntities: PipeWise (kind=business, optional).
Relationships: Bea↔Ricky (mentor/apprentice).

- Episode: "apprentice misdiagnoses low water pressure" —
  cast = {Ricky, Bea}, no referenced_entities needed. Composition
  1a renders with truck backdrop; Composition 1b (rerender) with
  shop-floor backdrop — same Episode, different `backdrop_clip_id`
  kwarg.
- Works cleanly. Mentor/apprentice relationship surfaces via
  cast-intersection on both Characters (both in cast).

### T-E. Veterinary Universe with recurring silent dog with agency

Universe: `vet-clinic`. Characters: Dr. Chen (vet), **Biscuit (the
recurring silent dog with narrative agency)**. WorldEntities:
Waiting room, Exam room (optional).

- **Under the corrected agency-not-voice rule: Biscuit is a
  Character.** Teammate row with `Universe = vet-clinic`;
  CharacterIdentity uses the `non_human` branch. Biscuit does not
  speak; Biscuit has agency (returns week after week, makes
  choices, forms relationships with Dr. Chen and other patients).
- Relationships: Chen↔Biscuit (`type = vet-patient`, or `caretaker`,
  freeform operator vocabulary).
- Episodes: cast = {Chen, Biscuit}. Biscuit participates as a cast
  member, not a referenced_entity.
- **Constraint acknowledged**: Biscuit currently CANNOT be
  fully created as a CharacterIdentity because the non-human branch
  schema is substrate-exercise-only (`non_human_test_schema_v1.yaml`
  purpose = `substrate_exercise_only`; deleted when Character
  Presence Language lands). Until CPL lands, Biscuit exists as a
  Teammate row without a fully approved CharacterIdentity — the
  substrate accepts him but the renderer may not have a canonical
  portrait/voice. This is a **named blocking dependency**, not a
  contradiction.
- Under the OLD "does not speak" rule, Biscuit would have been a
  WorldEntity `kind=animal`. That answer is now WRONG per the
  operator correction.

### T-F. Recurring silent character with agency

A mute human sidekick in some other Universe. Same as Biscuit: this
is a **Character**, not a WorldEntity. Depending on CharacterIdentity
substrate branch support for silent humans (the human branch requires
voice fields per `human_identity_schema_v1.yaml`), the character
may need special substrate accommodation — flagged as a downstream
question.

### T-G. Recurring prop with no agency

Rivet's wrench, a power cutoff switch that sits in place. No
agency. Either:

- **v1 answer**: remains in Episode prose per operator declaration.
  Promotion boundary: operator explicitly promotes to WorldEntity
  when narrative significance warrants a canonical row.
- **Or**: WorldEntity `kind = prop` with a description. Same
  primitive as the coffee shop.

Correct under integrated architecture. No auto-promotion.

### T-H. Legacy business spokesperson with universe=NULL

Mike-the-plumber, Repo Red, Tulsi. Every render:

- Composition created; `episode = NULL`; `spokesperson.universe = NULL`.
- Retrieval uses workspace-wide empty-M2M K2 semantics.
- No Relationship, no WorldEntity, no Episode-scoped canon.
- Correct pre-Universe behavior preserved unchanged.

**All eight scenarios pass** the integrated architecture. Story-test
result: **no breakage, no over-scope discovered.**

## Q1–Q30 answered

**Q1. Does Workspace remain purely the tenant/privacy boundary? Any
leftover world-boundary duties?**
Workspace remains the tenant/privacy boundary. Universe absorbs
world-boundary duties (cast membership, canon knowledge scope,
Relationships, WorldEntities, Episodes). Workspace continues to own:
ownership, membership/seats, slug, billing, engine credentials,
Asset library, KnowledgeDocument dedup namespace, Teammate naming
namespace. No leftover world-boundary duties on Workspace itself,
though Composition/Script/PublishBundle keep their direct
Workspace FK for tenant scoping (transitive Universe scope through
`Episode` / `spokesperson.universe`).

**Q2. Multi-Universe-in-one-Workspace safety across K2 / Relationship
/ WorldEntity / Episode cast / Composition.**
Safety holds structurally when every Universe-scoped primitive
enforces its Universe FK equality invariants at `clean()` /
`m2m_changed pre_add`. Enumeration:
- K2: `document.universe = teammate.universe` for retrieval;
  cross-Universe M2M rejected.
- Relationship: both endpoints and row Universe consistent.
- WorldEntity: Universe FK NOT NULL; Episode M2M cross-Universe
  rejected.
- Episode.cast: all Characters in Episode's Universe.
- Episode.referenced_entities: all WorldEntities in Episode's Universe.
- Composition.workspace = Episode.workspace = Episode.universe.workspace.
Cross-Universe access is possible only via explicit named primitive
(none v1). Safety confirmed.

**Q3. Does Universe need responsibilities beyond ownership +
isolation + shared canon for v1?**
No. Universe v1 owns identity (name, per-workspace slug, timestamps),
Workspace parent FK, and serves as the anchor for
`Teammate.universe`, `KnowledgeDocument.universe`,
`Relationship.universe`, `WorldEntity.universe`, `Episode.universe`
FKs. It does not own palette, cast M2M, canon M2M, or arc grouping.

**Q4. Does Character/Teammate cleanly represent the corrected
"agency not voice" definition? Which prior language needs
correction?**
Yes, cleanly — provided `WORLD_ENTITY_BOUNDARY_V1.md`'s "speaks vs
does not speak" framing is corrected in that document. Character is
"persistent narrative ACTOR with agency." A silent dog with agency
IS a Character. See §Corrections required for the exact lines.

**Q5. Does Relationship stay Character↔Character only? Ruby→owns→
Bakery must NOT force polymorphism.**
Yes. `RELATIONSHIP_BOUNDARY_V1.md §Q10` explicitly deferred
Character↔WorldEntity edges to a NEW model. This integration slice
confirms: Relationship stays Teammate-typed on both endpoints. Any
future Character↔WorldEntity edge model is separate, not a
polymorphic reshape of Relationship.

**Q6. Does WorldEntity stay narrative THINGS only? Walk: Workshop,
Bakery, Coffee Shop, AI Agent Project, recurring power switch,
recurring dog with agency (Character now), recurring dog without
agency.**
Yes. Workshop / Bakery / Coffee Shop / AI Agent Project = WorldEntity
(different `kind` hints: place, business, project). Recurring power
switch = WorldEntity (kind=prop) if operator promotes, else Episode
prose. **Recurring dog with agency = Character** (corrected).
Recurring dog without agency = WorldEntity `kind=animal`. Under the
corrected rule, "does the dog have agency?" is operator-declared;
"does the dog speak?" is irrelevant to the boundary.

**Q7. Is Character-vs-WorldEntity operationally understandable?
Ambiguous cases + decision rule.**
Yes. Decision rule: **agency, not voice.** Ambiguous cases:
- Silent-dog-with-agency (T2 in WORLD_ENTITY_BOUNDARY_V1 —
  RECLASSIFIED as Character under corrected rule).
- Speaking-jingle-sign (loudspeaker prop that "talks" but has no
  agency) — WorldEntity.
- AI-agent Project — pure THING, no agency — WorldEntity
  (kind=project).
- Rivet's wrench — prop, no agency — WorldEntity if promoted, else
  Episode prose.
Operator declares at creation. No auto-detection.

**Q8. Does Episode stay creative/story primitive, not container-
around-Composition?**
Yes. `EPISODE_LIFECYCLE_V1.md §H3` corrected the prior slice's
auto-creation to explicit-only. Episode exists because the operator
declared "this is a story." A Composition without an Episode is
legal (talking-head, legacy). Episode never wraps a render
retroactively without operator action.

**Q9. Does Episode.cast still mean "characters participating in the
story," not "everyone referenced"?**
Yes. Cast = on-screen/participating Characters (subset of Universe's
Characters). Off-screen but relevant Characters surface via
cast-intersection query on Relationship (never by silent cast
inclusion). This is the mechanism that makes T-A Episode B correct
(Mason relevant to Patch+Rivet dialogue without being in cast).

**Q10. Does Episode.referenced_entities correctly solve persistent
non-character relevance? Empty M2M legal? No scalar location field?**
Yes to all three. `Episode.referenced_entities` M2M → WorldEntity
carries "which entities matter to this Episode." Empty M2M is legal
(talking-head Episodes routinely have zero entities). No scalar
`Episode.location` field — a scene may traverse multiple places;
scalar collapses that. If a "primary setting" needs marking later,
that's an SPA affordance on top of the M2M, not a schema scalar.

**Q11. Does Composition contain only attempt/render-specific state?
Any leaked Episode/Universe fields to relocate?**
Composition contains render-specific state PLUS content-provenance
(synthesized_brief, rejected_synthesis, knowledge_chunk_ids,
verification_*, template_kind, writing_contract_version). Per
`EPISODE_VS_COMPOSITION_V1.md §Q3`, these are per-attempt content
records and stay on Composition. The one narrative field that
migrates to Episode is `operator_topic` (story-authoritative);
Composition retains a per-attempt copy (SESSION 259 backlog fix,
independent of Episode existence).
**One leaked field to acknowledge**: `Composition.spokesperson` has
been overloaded as both "performer of this render" and "character
the story is about" — with Episode.cast landing, `spokesperson`
becomes strictly "performer of THIS render" and cast M2M carries
"story characters." Both persist; disambiguation is now clean.

**Q12. Does Knowledge remain purely descriptive? Reconcile
Character-owned / Universe canon / WorldEntity description /
character POV / Episode history.**
Yes. Knowledge remains purely descriptive across all five sources:
- Character-owned K2 (M2M attached to specific Character(s)): "facts
  this character knows/grounds their claims in."
- Universe canon K2 (M2M empty, Universe-scoped): "facts visible to
  every Character in this Universe."
- WorldEntity description: short canonical operator-authored string
  ON the WorldEntity row (not a K2 doc). Longer canonical prose can
  additionally be a K2 doc with M2M empty in that Universe.
- Character POV: prose on Teammate (`personality`, `business_brief`,
  future POV versioning) — not K2.
- Episode history: DEFERRED to memory substrate; not K2.
None of these constitute existence. All describe. Deletion of any
K2 doc does not delete a Character/WorldEntity/Relationship/Episode.

**Q13. Are business_brief and K2 still overloaded post-Universe?
What SHOULD eventually migrate away (name only — do not design
migration).**
Yes, overloaded. `Teammate.business_brief` currently carries:
(a) the fact of Ruby owning a bakery, (b) the description of the
bakery-as-a-thing (currently on Ruby but semantically about the
Bakery WorldEntity), (c) business facts about Ruby's operations.
Post-WorldEntity: (b) migrates to `WorldEntity.description` (or a
K2 doc scoped to the Bakery via Character↔WorldEntity edge notes,
deferred). (a) stays on business_brief as a character-owned fact
about Ruby. (c) stays. **No migration is designed here.**

K2's overload: workspace-wide docs mixing multiple worlds is exactly
the leak Universe closes. Post-Universe, each doc has an explicit
`universe` FK; legacy docs stay `universe=NULL`. No forced migration.

**Q14. Ruby-owns-Bakery final home. Is character-fact-in-
business_brief + Bakery-as-WorldEntity + deferred edge coherent, or
dangerous duplication?**
Coherent, not dangerous. Three layers:
- Ruby.business_brief carries the FACT ("Ruby owns a corner bakery").
- Bakery WorldEntity carries the ENTITY (name, kind=business/place,
  description).
- Character↔WorldEntity edge (deferred) will carry the RELATIONSHIP
  (Ruby → owns → Bakery) as a first-class row.
Duplication is minimal (the fact appears twice: once as Ruby's
prose, once as Bakery's description). The two are compatible because
they answer different questions ("what does Ruby say about her
business?" vs "what is the Bakery in this Universe?"). Post-edge,
the operator can consult the edge as source-of-truth for ownership,
and the two prose slots become perspectival narrative fluff — still
useful, not authoritative.

**Q15. Character↔WorldEntity edges — genuinely separate future
primitive? Would one `CharacterEntityEdge` cover all cases without
becoming an untyped junk graph?**
Genuinely separate. A single `CharacterEntityEdge` with (Teammate,
WorldEntity, freeform `type`, notes) can cover Ruby→owns→Bakery,
Patch→works_at→Workshop, Chen→cares_for→Biscuit (wait — Biscuit is
now a Character, so that's a Relationship, not an edge). Cases that
belong on `CharacterEntityEdge`: Character↔Place, Character↔Business,
Character↔Project, Character↔inert Prop. To avoid junk-graph rot, the
edge row should mirror Relationship's discipline: explicit-only,
freeform type, status, notes, Universe-scoped, no self-loops (no
Character→same-Universe-WorldEntity-that-is-itself would be
meaningless).

**Q16. WorldEntity↔WorldEntity edges — deferrable? (Project
deployed_at CoffeeShop, Bakery next_to CoffeeShop, Project created_in
Workshop.)**
Deferrable. v1 uses:
- Episode.referenced_entities carrying BOTH entities → operator
  authors the co-occurrence per Episode.
- Freeform prose in WorldEntity.description ("AI Agent Project,
  building for Mason's Coffee Shop") to capture the reference.
Weak-link problem: two entities cannot cross-reference each other in
a queryable way. Deferred WorldEntity↔WorldEntity edge model is the
proper answer. Not v1.

**Q17. Narrative Memory before v1 — required or deferrable? Take a
firm position.**
**Deferrable.** v1 stopgaps:
- `Relationship.notes` carries "the AI-agent project started in
  Episode A" as prose.
- `Episode.operator_topic` carries verbatim story intent.
- `Composition.synthesized_brief` retains per-attempt authored text.
None of these persist structured events across Episodes. That
capability requires the deferred memory substrate. **v1 will NOT
provide** "continue what happened last Episode" as a structural
answer — see Q18.

**Q18. What "continue what happened last episode" behavior will v1
NOT yet provide? Make the gap explicit.**
v1 provides:
- Operator navigation to prior Episode E' (SPA affordance) and manual
  reference in the new Episode's `operator_topic`.
- New Episode E'' created with reference to E' in its operator_topic.
- Relationship.notes and WorldEntity.description carry loose state
  between Episodes.

v1 does NOT provide:
- Auto-loading of prior Episode's structured events into a new
  Episode's synthesis.
- Callback edges between Episodes (E'' → refs → E').
- State-machine of unresolved threads (promises, open questions).
- Canon promotion mechanic (which Episode is "official").
- Per-Character memory of what happened.

These are the memory-substrate slice. **v1 explicitly ships the
gap** — the operator's mental model needs to accept that continuity
in v1 is prose-mediated, not structural.

**Q19. Explicit-operator-authoring consistent across Universe /
Episode / Relationship / WorldEntity? Does Character creation
already follow the same philosophy?**
Consistent. All five are explicit-only. Character creation (Teammate)
already follows this — Teammates are created via the Bootstrap-review
admin surface or the SPA wizard; no auto-Teammate ever exists.
Explicit-only is the load-bearing principle across the whole
canon layer.

**Q20. What can the LLM create automatically? Sharp line between
generated prose, generated Composition, suggested canon, actual
canon mutation.**
LLM outputs:
- **Prose** (Composition.synthesized_brief, K6 first-pass text,
  corrective retries, Script.draft_text) → CREATED automatically as
  per-attempt evidence.
- **Composition rows** → created automatically as part of pipeline
  execution when the operator submits render; but the Composition
  itself is not canon.
- **Suggested canon** (SPA v2 UX: "Rivet mentioned 'power cutoff' —
  promote to WorldEntity?") → NOT v1. When it arrives, the LLM
  suggests; the OPERATOR promotes.
- **Actual canon mutation** (Universe/Character/Relationship/
  WorldEntity/Episode row create/update) → NEVER automatic.
  Operator-only, always.

Sharp line: **prose and per-attempt evidence flow automatically;
canon does not.**

**Q21. Any primitive that must be versioned immediately?
(Character identity is; POV/voice/description/notes are mutable.)
Flag; do NOT design versioning.**
Only CharacterIdentity is versioned immediately (it already is:
`CharacterIdentityVersion` with `revision` and `state` machine per
`identity/models.py:174–334`). Everything else v1 is mutable-in-place:
Universe name, Episode.operator_topic, Relationship.type/notes,
WorldEntity.description, Teammate.business_brief/personality/voice.
**Flagged for future versioning**: Teammate.voice / POV / personality
(`CAPABILITY_INVENTORY_SESSION_261.md §4` pre-Universe question 3);
Episode.operator_topic (if operator edits after render, prior renders
lose the topic that drove them — mitigated by Composition's per-
attempt operator_topic copy). No versioning designed here.

**Q22. Naming coherence map — freeze semantic meanings for Universe
/ Episode / Composition / Character / Relationship / WorldEntity /
Knowledge / Asset / background / backdrop / environment / scene /
location. Operator-facing labels vs backend names.**
See §Naming coherence map below.

**Q23. Circular dependencies among v1 models? Produce the DAG.**
None. See §Dependency DAG above. All edges point outward from
Workspace toward leaves. Relationship is the only "graph-like"
primitive but it's a Universe-owned M2M-with-payload — still DAG.

**Q24. Can the first implementation be delivered incrementally
without dead models? Evaluate the proposed order A–H and propose
better if the DAG shows one.**
Yes. See §Model implementation sequencing.

**Q25. Smallest end-to-end vertical slice that proves the
architecture. Challenge the candidate given.**
See §Smallest vertical slice below.

**Q26. What deliberately does NOT ship in the first vertical slice?**
See §Explicit deferral list below.

**Q27. Does the existing stale/orphan knowledge problem block
Universe implementation? Position: block / cleanup first / prospective
isolation makes cleanup independent.**
**Prospective isolation makes cleanup independent.** Legacy docs
with `universe=NULL` remain reachable only by legacy Teammates.
Universe-scoped Teammates never see them. Stale knowledge in the
legacy bucket cannot leak into Universe synthesis. Cleanup can
happen at any pace (bespoke ½-slices per doc) without blocking
Universe rollout. Confirmed by `UNIVERSE_BOUNDARY_V1.md §Q9`
load-bearing rule.

**Q28. Likely-unavoidable migrations/backfills — classify only
(nullable/prospective, no-backfill, future cleanup). Do NOT write
them.**
- **Nullable/prospective (no backfill)**: `Teammate.universe`,
  `KnowledgeDocument.universe`, `Composition.episode`. All nullable
  at introduction; NULL = legacy behavior. No data movement.
- **No-backfill invariants**: `Relationship`, `WorldEntity`,
  `Episode` are new tables; no rows exist pre-introduction. No
  backfill needed.
- **Future cleanup (per-item bespoke ½-slices)**: migrating specific
  historical Teammates into a Universe, migrating specific historical
  Compositions into an Episode, deleting stale legacy K2 docs. Each
  bespoke, no bulk.

**Q29. What existing behavior is most at risk when Universe lands?
Blast-radius priority list.**
1. **`retrieve_for_teammate`** (`embeddings/retrieval.py:150–197`)
   must switch on `teammate.universe` — highest blast radius; every
   synthesis path calls it.
2. **`KnowledgeDocument.clean()` + m2m_changed signal**
   (`embeddings/models.py:230–245`; `apps/embeddings/signals.py:31–79`)
   must extend to Universe cross-check. Every doc write goes through it.
3. **SPA knowledge-upload default visibility**
   (`web/src/lib/api/knowledge.ts:219–227`) currently silently
   defaults to workspace-wide; if Universe ships without a
   corresponding SPA change, the operator will accidentally create
   Universe-scoped docs as workspace-wide and mis-scope them.
   **SPA must land with schema.**
4. **Composition/Script/Campaign/RealtimeSession `.clean()` paths**
   must extend to Universe-consistency when Episode/spokesperson
   FKs are populated.
5. **Legacy synthesis paths** — must handle both regimes (Universe-
   scoped and Universe-NULL) in parallel until legacy is migrated.
   No new "everyone visible" bypass.

**Q30. Concrete testable acceptance criteria for "Universe
substrate v1 exists."**
- Create Universe row via operator gesture (API + SPA); reject
  cross-workspace parents.
- Assign Teammate to Universe (post-create edit); reject
  cross-workspace assignments.
- Assign KnowledgeDocument to Universe; empty-M2M means "visible to
  every Teammate in same Universe."
- `retrieve_for_teammate(patch)` with patch.universe = Workshop and
  a TANK doc in Motorcade universe returns ZERO TANK chunks even
  when cosine-similar. Regression test.
- Legacy Teammate (universe=NULL) retrieval unchanged — TANK/Tulsi
  legacy behavior preserved by test.
- Cross-Universe KnowledgeDocument M2M attach rejected at
  `clean()` + m2m_changed.
- Universe delete CASCADEs its Teammates/K2 docs (per schema-slice
  policy).
- SPA can create/edit Universes; assign Teammates; upload K2 into a
  Universe.

## Naming coherence map (backend name → operator label → meaning)

| Backend name | Operator-facing label | Meaning | Scope |
|---|---|---|---|
| `Workspace` | Workspace / Account | Tenant. Owner, seats, billing. | Root. |
| `Universe` | World (or Universe) | Persistent creative world within a workspace. | Child of Workspace. |
| `Teammate` (Character) | Character / Teammate / Spokesperson | Persistent narrative ACTOR with agency. May be non-human, may be silent (agency, not voice). | Universe (nullable = legacy). |
| `CharacterIdentity` | Canonical Identity | Versioned substrate for the character's approved representation. | Per-Teammate. |
| `Relationship` | Relationship | Edge between two Characters in the same Universe. Freeform type, directional via paired type fields. | Universe. |
| `WorldEntity` | Place / Business / Project / Thing (per `kind` hint) | Persistent narrative THING without agency. | Universe. |
| `Episode` | Episode / Story | Narrative event conceived and named by the operator as a story. Explicit-only. | Universe. |
| `Composition` | Video / Render / Take | Render attempt or variant. Not a story on its own. | Workspace (transitive Universe via Episode). |
| `KnowledgeDocument` | Knowledge / Document | Factual corpus. Describes; does not constitute. | Universe (nullable = workspace-wide legacy). |
| `Asset` | Media / Clip / Image / Voice | Rendered pixels/audio artifact. Not a world entity. | Workspace. |
| `Script` | Script | Authored words for a Character to speak. | Workspace (optional Episode FK). |
| `PublishBundle` | Publish / Package | Distribution artifact keyed on an Asset(role=CLIP). | Workspace. |
| `background` | (technical; not operator-facing) | Portrait-normalization background family identifier (5 yaml values). | Identity substrate; per-generation. |
| `backdrop` | Backdrop | Cinematic clip that plays behind a talking head. `Asset(role=BACKDROP)`. | Composition; per-render. |
| `environment` | (technical; dormant) | `IdentityReferenceKind.ENVIRONMENT_REFERENCE` — reserved namespace, dormant. | Identity substrate; unused. |
| `scene` | (recipe kind: `dialogue_scene`) | Per-render recipe shape hint. Not a persistent identity. | Composition; per-render. |
| `location` | Place (via `WorldEntity.kind='place'`) | No substrate column named `location`. Operator concept lives on WorldEntity. | Universe (via WorldEntity). |

**Rules:**
- `background` and `backdrop` are load-bearing in-code names; do
  NOT rename either (`WORLD_ENTITY_BOUNDARY_V1.md §Q18`).
- The new "place" primitive is `WorldEntity` (with `kind='place'`),
  NOT `Location`. Operator UX may label it "Place."
- `environment` stays dormant; if reactivated, its scope is
  "portrait environment," never "world environment."

## Contradictions discovered between prior slices

**Contradiction 1 (LOAD-BEARING, from operator correction).**
`WORLD_ENTITY_BOUNDARY_V1.md` uses "speaks vs does not speak" as its
Character/WorldEntity discriminator throughout. The operator's
agency-not-voice correction supersedes this. See §Corrections
required for exact language.

**Contradiction 2 (already resolved by `EPISODE_LIFECYCLE_V1.md`).**
`EPISODE_VS_COMPOSITION_V1.md §Q16` proposed auto-creation of an
Episode at Composition-create time. `EPISODE_LIFECYCLE_V1.md §H3`
corrected this to explicit-only. No further correction needed here;
the prior slice already carries the correction with the exact language
flagged.

**Contradiction 3 (minor terminology drift).**
`WORLD_ENTITY_BOUNDARY_V1.md §Character-vs-WorldEntity` table row
"Speaks? YES ... NO" is the same issue as Contradiction 1. Corrected
in §Corrections required.

**No other contradictions discovered.** The other five slices are
consistent with each other. `UNIVERSE_BOUNDARY_V1.md`,
`EPISODE_VS_COMPOSITION_V1.md` (with its `EPISODE_LIFECYCLE_V1.md`
correction), `RELATIONSHIP_BOUNDARY_V1.md`, and
`WORLD_ENTITY_BOUNDARY_V1.md` (with the agency-not-voice correction)
form a coherent coordinate system.

## Corrections required to prior committed docs (enumerated)

### `WORLD_ENTITY_BOUNDARY_V1.md` — agency-not-voice correction

The following sentences/sections use "speaks vs does not speak" as
the Character/WorldEntity discriminator and must be corrected in
place. This is the LOAD-BEARING correction.

1. **§Adversarial Test T2 (Vet-clinic recurring dog patient)**,
   lines around 346–369.
   - MISLEADING language: "**Under W3/W4 WorldEntity `kind=animal`**:
     the dog is an addressable, referenced-by-Episode entity
     without carrying Character weight." AND the concluding
     "**Position**: WorldEntity is the correct home for a
     non-speaking narrative identity."
   - **Corrected position**: **WorldEntity is the correct home for a
     non-speaking narrative identity ONLY IF THE ENTITY HAS NO
     AGENCY.** A silent dog with agency (returns week after week,
     forms relationships, makes choices) is a **Character** (Teammate
     with `CharacterIdentity.kind=non_human`), gated on Character
     Presence Language landing. A silent dog without agency (a
     one-off waiting-room extra with no continuing narrative role)
     is a WorldEntity `kind=animal`.
   - **Also correct**: the "no auto-promotion from WorldEntity to
     Teammate" invariant survives. The distinction is agency-authored
     at creation. If the operator later realizes the dog has agency
     and should be a Character, that is a NEW Teammate creation,
     never a "promote WorldEntity to Character" mechanic.

2. **§Q2 answer** ("Is 'Ruby owns a bakery' character knowledge /
   Universe canon / Relationship / Character↔Place / other?"),
   line 430ff. This answer is CORRECT under the correction (Ruby has
   agency; Bakery does not). No change needed for Q2 itself, but any
   downstream reader should read Q2 with the agency-not-voice frame,
   not the voice frame.

3. **§Character vs WorldEntity distinction table**, lines 1099–1117.
   - MISLEADING row: "Speaks? | YES (voice, K2, personality, POV,
     Runway avatar) | NO"
   - **Corrected row**: "Has narrative agency (makes decisions, holds
     relationships, exhibits behavior)? | YES | NO"
   - Also correct the trailing paragraph: "**Load-bearing
     distinction**: Character speaks, WorldEntity does not."
   - **Corrected**: "**Load-bearing distinction**: Character has
     agency, WorldEntity does not. Voice is one common signal of
     agency but is neither sufficient (a jingle-emitting sign speaks
     but has no agency) nor necessary (a silent recurring dog can
     have agency)."

4. **§Q8 answer** ("Animals/pets: recurring vet-clinic dog"),
   lines 566–579.
   - MISLEADING: "**WorldEntity `kind=animal`** is the correct home
     for a **non-speaking** narrative identity." "**Teammate** with
     `CharacterIdentity.kind=non_human` is the correct home for a
     **speaking** character."
   - **Corrected**: "**Teammate** with `CharacterIdentity.kind=
     non_human` is the correct home for any narrative identity with
     AGENCY (speaking or silent). **WorldEntity `kind=animal`** is
     the correct home for a non-speaking, non-agency narrative
     identity (a background extra, a one-off waiting-room dog with
     no continuing role)."

5. **§Q15 negative-boundary list item 1**, lines 819–824.
   - MISLEADING: "**Characters** — go to Teammate (existing) +
     CharacterIdentity substrate. Non-speaking-but-recurring becomes
     WorldEntity `kind=animal` (or similar) only when explicitly
     non-speaking; a WorldEntity should never gain a voice."
   - **Corrected**: "**Characters** — go to Teammate + CharacterIdentity
     substrate. Non-speaking-but-recurring becomes WorldEntity
     `kind=animal` (or similar) only when it has NO AGENCY; if it has
     agency (returns, holds relationships, makes choices) it is a
     Character regardless of voice. A WorldEntity should never gain
     agency (nor voice); promotion path is a new Teammate creation."

6. **§Canon / promotion ownership**, lines 1215–1234.
   - MISLEADING: "WorldEntity → Character: **forbidden** (a coffee
     shop does not gain a voice; a Barista does — new Teammate)."
   - **Corrected**: "WorldEntity → Character: **forbidden**. If the
     operator later realizes a WorldEntity should actually be a
     Character (has agency), the path is: (a) archive the WorldEntity,
     (b) create a new Teammate. The WorldEntity does not gain
     agency; a new Character emerges."

7. **§Risks-if-boundary-is-wrong item 9**, lines 1432–1435.
   - MISLEADING: "**Promoting WorldEntity to Character.** Adds voice
     / K2 / avatar to what was declared as non-speaking..."
   - **Corrected**: "**Promoting WorldEntity to Character.** Adds
     agency (and typically voice / K2 / avatar) to what was declared
     as non-agency; loses the semantic distinction that WorldEntity
     establishes. Correct path: new Teammate creation."

**Prescription**: apply corrections 1–7 in-place in
`WORLD_ENTITY_BOUNDARY_V1.md`. Do not silently reinterpret in
downstream slices; the document itself must carry the corrected
language so future readers converge on the same rule.

### No other corrections required

`UNIVERSE_BOUNDARY_V1.md`, `EPISODE_VS_COMPOSITION_V1.md` (with
`EPISODE_LIFECYCLE_V1.md`'s correction already applied),
`RELATIONSHIP_BOUNDARY_V1.md`, and `CAPABILITY_INVENTORY_SESSION_261.md`
require no corrections from this integration slice.

## Model implementation sequencing recommendation

The operator brief suggested an order A–H. Evaluating against the
DAG:

**Recommended order (integrated):**

1. **Universe model + `Teammate.universe` FK + `KnowledgeDocument.universe`
   FK** (nullable). Extend retrieval / clean / signals. **This is
   the whole `UNIVERSE_BOUNDARY_V1.md` v1 scope.**
2. **SPA affordance for Universe creation + Teammate/K2 assignment.**
   MUST land with (1) — see Q29 risk (silent workspace-wide default).
3. **Episode + Composition.episode nullable FK.** New Episode table
   with cast M2M; state machine DRAFT/ACTIVE/ARCHIVED; explicit-only
   creation per `EPISODE_LIFECYCLE_V1.md §H3`. Composition backlog
   fixes (operator_topic per-attempt, retry_count, first_pass_output,
   corrective_hint, retrieval_snapshot_on_failure) can land in the
   same slice or as a SESSION 259 backlog cleanup.
4. **Relationship model** — one row per pair, Universe-scoped,
   explicit-only, off-screen cast-intersection query in retrieval
   context assembly.
5. **WorldEntity model + `Episode.referenced_entities` M2M** — base
   row (name / kind hint / description / status), Universe-scoped,
   explicit-only. Note: `WORLD_ENTITY_BOUNDARY_V1.md §Q20` recommended
   Relationship before WorldEntity, which this order respects.
6. **[FUTURE — deferred, not v1] Character↔WorldEntity edge model.**
7. **[FUTURE — deferred, not v1] Narrative memory substrate.**
8. **[FUTURE — deferred, not v1] Canon promotion / educational
   subject / palette / WorldEntity↔WorldEntity edges / voice-POV
   versioning.**

**Why this order and not another:**
- Universe must land first — every subsequent primitive scopes to
  it.
- SPA must land WITH Universe — the silent-workspace-wide-default
  risk is Q29 #3.
- Episode-before-Relationship: Episode is used more heavily and
  operators need it earlier; Relationship is additive.
- Relationship-before-WorldEntity: `WORLD_ENTITY_BOUNDARY_V1.md
  §Q20` argued the case and it holds. Off-screen character relevance
  is a bigger need than off-screen entity relevance for the Patch/
  Rivet dogfood.
- WorldEntity + Episode.referenced_entities land together because
  the M2M is what makes WorldEntity useful.

**Delivery discipline**: each step is one deployable slice. Each
step's schema is nullable-at-introduction. Each step ships with SPA
affordance. No step assumes downstream steps.

## Smallest vertical slice

**Candidate**: end-to-end proof that Universe substrate works
without narrative primitives.

1. Operator creates a new Universe "Workshop" in their existing
   workspace via SPA.
2. Operator assigns Patch (existing Teammate) to Universe = Workshop.
3. Operator uploads a K2 doc "About the Workshop" assigned to
   Universe = Workshop (empty M2M).
4. Operator triggers a Composition (talking-head) with
   `spokesperson = Patch`, no Episode.
5. Retrieval scoped to Universe = Workshop; the Workshop K2 doc
   surfaces; TANK/Tulsi/Hearth&Hollow legacy workspace-wide docs
   do NOT surface.
6. Render succeeds. Composition row exists with
   `spokesperson.universe = Workshop`, `episode = NULL`.
7. Legacy Teammate (Mike) unaffected — legacy retrieval unchanged;
   Universe FK does not touch him.

**This proves:**
- Universe creation works.
- Universe scoping on Teammate works.
- Universe scoping on K2 retrieval works.
- Legacy fallback works.
- Composition ships without requiring Episode.

**This deliberately does NOT prove:**
- Episode/Relationship/WorldEntity (later slices).
- Cross-Universe safety with two Universes (add as second-slice
  regression test).
- SPA multi-Universe picker (second-slice UX).

**Second vertical slice (validates isolation):**
Two Universes in same workspace, cross-Universe retrieval attempt
(via K2 M2M cross-Universe) is rejected at clean() and m2m_changed.
Regression test asserts no cosine leak across the Universe boundary.

## Explicit deferral list (what v1 will NOT provide)

Enumerated per the operator brief Q26; each item was evaluated
against the integrated architecture and confirmed deferrable
without breaking v1.

1. **Narrative memory** (event log, promise ledger, callback edges,
   unresolved threads). Stopgap: prose in Relationship.notes,
   Episode.operator_topic, WorldEntity.description.
2. **Character↔WorldEntity edges** (Ruby→owns→Bakery, Patch→works_at→
   Workshop as first-class rows). Stopgap: business_brief prose +
   Episode.referenced_entities M2M.
3. **WorldEntity↔WorldEntity edges** (Project→deployed_at→CoffeeShop).
   Stopgap: prose in WorldEntity.description.
4. **Educational curriculum substrate** (subject, lesson, audience,
   learning objective). Explicit strong negative boundary in
   `WORLD_ENTITY_BOUNDARY_V1.md §Q9` — do NOT absorb into
   WorldEntity `kind`.
5. **Asset/entity visual binding** (canonical Asset FK on
   WorldEntity for scene-picker UX). Stopgap: operator-discipline
   backdrop reuse.
6. **Location specialization** (spatial coords, compound structures
   like "bakery inside a mall"). Not in v1.
7. **Business/project sidecars** (BusinessDetails, ProjectDetails).
   Only added when concrete operator need surfaces.
8. **Canon auto-suggestion** ("Rivet mentioned power cutoff —
   promote to WorldEntity?"). UX v2.
9. **Legacy cleanup** (bulk migration of Mike/Repo Red/Tulsi to
   Universes, bulk auto-wrap of 81 historical Compositions into
   Episodes). Per-item bespoke ½-slices, no bulk.
10. **Voice/context versioning** (Teammate.voice_energy / .voice_humor
    / etc. mutable-in-place today; SESSION 261 §4 flagged as future
    versioning). Not v1.
11. **Per-Universe palette / brand identity** (extend CSS-var brand
    swap to per-Universe). Not v1.
12. **Cross-Universe crossover primitive**. Not v1.
13. **Canon promotion mechanic on Episode/Relationship/WorldEntity**.
    Not v1.
14. **Backdrop naming disambiguation reform** (`background` vs
    `backdrop` vs `environment`). Do NOT rename; operator-facing
    label is "Place" for WorldEntity `kind=place`.
15. **Cast as a first-class shared row** (distinct from Episode.cast
    M2M). Deferred per `UNIVERSE_BOUNDARY_V1.md §D4`.
16. **Non-human Character Presence Language substrate** (`CAPABILITY_
    INVENTORY_SESSION_261.md §6`). Needed before Patch/Rivet/Biscuit
    can land as fully approved CharacterIdentities. Named blocker
    for T-E (vet-clinic dog with agency).
17. **`Episode.canonical_composition` designation**. Not v1.
18. **`Episode.sequence` marker** — v1 uses `created_at`.

## Isolation invariants (integrated)

Restated as one integrated set. Some existing (preserved), some
new (from downstream slices), all load-bearing.

1. **Workspace privacy invariant.** No data crosses Workspace
   boundaries. Every existing defense-in-depth mechanism
   (`KnowledgeDocument.clean()`, `apps/embeddings/signals.py`
   m2m_changed, `retrieve_for_teammate` unconditional workspace
   derivation, `Composition/Script/PersonalizedCampaign.clean()`,
   `IdentityReference.clean()`, `IsWorkspaceMember` permission)
   stays in force.
2. **Universe privacy invariant.** Within a Workspace, no data
   crosses Universe boundaries. Retrieval scoped by
   `teammate.universe`; K2 M2M cross-Universe attach rejected;
   Composition/Script/Campaign/RealtimeSession clean() paths
   extend to reject cross-Universe pairings.
3. **Legacy isolation invariant.** A Universe-scoped Teammate
   never retrieves from a workspace-wide (Universe=NULL) K2 doc. A
   workspace-wide (Universe=NULL) Teammate uses legacy semantics
   unchanged. Legacy Teammates cannot participate in Relationship /
   WorldEntity / Episode-scoped canon.
4. **Empty-M2M invariant (tightened scope).** Empty
   `KnowledgeDocument.spokespeople` means "visible to every
   Teammate in the same Universe as this doc" (or same workspace
   for legacy).
5. **No implicit crossing primitive.** No workspace-override,
   Universe-bypass, "see all worlds" flag, or debug bypass. Crossover
   (if ever needed) is an explicit named primitive with audit trail.
6. **Character/cast knowledge invariant.** Character-specific M2M
   attach is the finest-grained sharing; a doc attached to specific
   Teammates is visible only to those Teammates (all in the same
   Universe as the doc).
7. **Substrate immutability invariant.** GenerationRecord /
   NormalizationManifest append-only; inherit Universe scope
   transitively through identity_version.identity.teammate.universe.
8. **Dedup invariant.** `(workspace, content_hash)` remains the K2
   dedup key. Universe FK orthogonal.
9. **Episode-Composition consistency.**
   `Episode.workspace == Episode.universe.workspace`; every
   attached Composition's workspace matches; spokesperson.universe
   (when non-NULL) matches Episode.universe.
10. **Cast-Universe consistency.** Every Teammate in `Episode.cast`
    has `teammate.universe == episode.universe`.
11. **Referenced-entities-Universe consistency.** Every WorldEntity
    in `Episode.referenced_entities` has `world_entity.universe ==
    episode.universe`.
12. **Rerender does not duplicate narrative history.** Adding a
    Composition to an existing Episode is not a narrative event;
    Episode row unchanged; memory events (deferred) do NOT
    proliferate.
13. **Legacy-Composition isolation.** A Composition with
    `episode=NULL` never participates in Episode-scoped invariants.
14. **Relationship endpoints must be Characters in the same
    Universe.** No self-loop. Normalized ordering. Uniqueness
    `(universe, teammate_a, teammate_b)`. No cross-Universe edges.
15. **No implicit Relationship creation.** No cast co-occurrence
    inference; no LLM inference. Explicit operator only.
16. **No implicit Relationship mutation.** Episode / Composition /
    synthesis / rerender never mutate Relationship state.
17. **Cast-independence of Relationship queries.** Off-screen
    relevance keys on `teammate_a IN cast OR teammate_b IN cast`.
18. **WorldEntity Universe consistency.**
    `WorldEntity.universe.workspace == WorldEntity.workspace`.
19. **No implicit WorldEntity creation.** No prose-parsing
    auto-creation. Explicit operator only.
20. **No implicit WorldEntity mutation.** LLM output never mutates
    WorldEntity rows.
21. **No cross-primitive polymorphism.** Relationship endpoints
    stay Teammate-typed; WorldEntity endpoints (edge model, deferred)
    are a NEW model. Character never becomes WorldEntity or vice
    versa; each is a new operator-authored creation.
22. **Explicit-only across all canonical primitives.** Universe,
    Character, Relationship, WorldEntity, Episode — every one
    created only by operator action. No auto-defaults, no LLM
    auto-canon, no cast-co-occurrence auto-inference.

## Unresolved questions remaining AFTER integration

Some questions carry through from prior slices; some are new to
this integration.

1. **Non-human Character Presence Language substrate.** Blocks
   Biscuit (vet-clinic silent dog with agency) from landing as a
   fully approved CharacterIdentity. Named in
   `CAPABILITY_INVENTORY_SESSION_261.md §6` and reasserted here as
   a T-E blocker.
2. **App-name / home for new primitives.** `apps/universe`,
   `apps/relationships`, `apps/entities`, or extend the dormant
   `apps/memory` / `apps/agents`? Schema slice.
3. **Cascade policies** on Composition.episode delete (SET_NULL vs
   PROTECT), Teammate delete relative to Relationship (CASCADE vs
   PROTECT), Universe delete (CASCADE assumed but explicit
   confirmation needed for each child).
4. **SPA UX for Episode / Relationship / WorldEntity creation.** The
   explicit-only discipline requires operator gestures; if the SPA
   silently defaults (e.g., knowledge upload workspace-wide today
   per Q29 #3), the whole architecture collapses.
5. **`Composition.episode` cascade in relation to legacy migration.**
   If a legacy Composition is attached to a newly-created Episode
   later, what happens to it (per-item bespoke slice) — is any
   Composition-side validation needed?
6. **Slug uniqueness reform on Workspace** (pre-existing SESSION 259
   audit §8 wart). Not blocked by Universe; not addressed by Universe.
7. **Direction encoding in Relationship** (single `type` +
   optional `type_reverse` vs paired `type_from_to` /
   `type_to_from`). Schema slice.
8. **`WorldEntity.kind` vocabulary conventions** — freeform in v1;
   observed vocabulary may need normalization in v2.
9. **`Episode.referenced_entities` loading limit** in synthesis
   context assembly (performance).
10. **`WorldEntity.status='archived'` interaction with existing
    Episode.referenced_entities M2Ms.**
11. **Legacy Teammate migration into a Universe** — per-item bespoke
    slice policy is committed; the actual migration playbook is not
    written.
12. **`Episode.canonical_composition` designation** — SPA affordance
    needed to name "the primary render" of an Episode with multiple
    Compositions; v1 can use most-recent-successful.
13. **Prompt formatting of Relationship + WorldEntity context in K6
    synthesis.** How does the prompt render these rows into structured
    context? K6 contract slice.
14. **Character↔WorldEntity edge model design** — deferred; needs to
    land after WorldEntity and before compound scenarios.
15. **Educational curriculum substrate** — deferred; when it lands,
    must NOT absorb WorldEntity's `kind` vocabulary.

## Risks if implementation starts before those questions are resolved

Prioritized by blast radius.

1. **SPA lands after schema, causing silent workspace-wide upload
   default to mis-scope Universe K2 docs.** Q4 above; Q29 #3 in the
   schema-slice risk list. **BLOCKER — SPA must land WITH schema.**
2. **Non-human Character substrate not ready, blocking Biscuit-shaped
   Characters** (silent dog with agency). Q1 above. Non-blocker for
   Patch/Rivet/Ruby/Mason dogfood; blocks vet-clinic and similar
   worlds. Named dependency, not architectural failure.
3. **Cascade policy ambiguity** on Composition.episode /
   Teammate.relationships / Universe.children — decisions must be
   made in schema slice, not deferred to migration time.
4. **Prompt formatting undefined** for Relationship + WorldEntity
   context. K6 could silently drop the new context if the format
   isn't specified. Blocks the load-bearing off-screen relevance
   mechanism.
5. **App-name churn.** Placing Relationship + WorldEntity + Episode
   in `apps/memory` vs `apps/universe` vs `apps/entities` affects
   import paths across the code base; picking wrong requires large
   rename.
6. **Legacy migration playbook absent.** When the operator wants to
   migrate Mike to a Universe (per-item bespoke), the actual steps
   (detach M2Ms, verify clean(), reattach in new scope) are not
   documented. Risk of silent breakage on first attempt.

None of these are architectural contradictions. All are downstream
design/implementation decisions that must be made before or during
the schema slice.

## STOP/GO recommendation

**GO to schema/model design.**

The architecture is internally consistent after the agency-not-voice
correction is applied in-place to `WORLD_ENTITY_BOUNDARY_V1.md`. The
eight story tests pass. The DAG is acyclic. The primitive
responsibility table is coherent. The isolation invariants integrate
without conflict.

**Named preconditions before schema work begins:**

1. Apply corrections 1–7 (§Corrections required) in-place to
   `WORLD_ENTITY_BOUNDARY_V1.md`. Small in-doc edit; no other slice
   affected.
2. Confirm SPA design will land WITH schema for Universe (Q29 #3
   blocker).
3. Note the non-human Character Presence Language dependency as a
   named blocker for vet-clinic-shape worlds (not for Patch/Rivet
   dogfood).

**Next slice name**: **`UNIVERSE_SCHEMA_V1`** — model DDL for
`Universe`, `Teammate.universe` FK, `KnowledgeDocument.universe` FK,
retrieval / clean / signal extensions, SPA affordance for Universe
creation and Teammate/K2 assignment. This is the "step 1 + step 2"
from §Model implementation sequencing above, landed together to
avoid the SPA-lag blocker.

Downstream slices (in order): `EPISODE_SCHEMA_V1` (Episode +
`Composition.episode` + SPA), `RELATIONSHIP_SCHEMA_V1`,
`WORLD_ENTITY_SCHEMA_V1` (with `Episode.referenced_entities` M2M).

## Verification

- All six prior slices read in full (or in verified sections for
  WORLD_ENTITY_BOUNDARY_V1.md due to length).
- Eight story-test scenarios walked through the integrated
  architecture; all pass.
- DAG verified acyclic by walking each primitive's FK/M2M list.
- Agency-not-voice correction applied consistently across §Load-
  bearing operator correction, §Actor vs Thing rule, §Story tests
  T-E and T-F, §Q4 / Q6 / Q7 / Q8, §Character vs WorldEntity row
  in primitive table, and §Corrections required.
- Load-bearing invariants (Q2, Q22 explicit-only, Q17 memory-
  deferred, Q27 legacy-isolation) confirmed against each prior
  slice's language.

## STOP

Research only. No schema. No migrations. No code. Every load-bearing
claim is cited to `CAPABILITY_INVENTORY_SESSION_261.md`,
`UNIVERSE_BOUNDARY_V1.md`, `EPISODE_VS_COMPOSITION_V1.md`,
`EPISODE_LIFECYCLE_V1.md`, `RELATIONSHIP_BOUNDARY_V1.md`, or
`WORLD_ENTITY_BOUNDARY_V1.md` — or, where load-bearing on the
agency-not-voice correction, to the operator brief that arrived
AFTER `WORLD_ENTITY_BOUNDARY_V1.md` landed.
