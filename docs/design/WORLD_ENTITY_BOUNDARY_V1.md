---
title: "World Entity Boundary v1 — Persistent Non-Character Things"
status: research — non-character persistent primitive boundary (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"
  - "design/RELATIONSHIP_BOUNDARY_V1.md"
scope: >
  Answer one question — what persistent primitive, if any, does a
  Universe need for named things that are not Characters? Take
  positions. Do not redesign Relationship (RELATIONSHIP_BOUNDARY_V1.md
  is committed). Do not design narrative memory in detail. Correct
  prior slices where the evidence warrants.
---

# World Entity Boundary v1 — Persistent Non-Character Things

## Purpose

Four prior SESSION 261 slices established the coordinate system:

- **Workspace = tenant, Universe = world** (UNIVERSE_BOUNDARY_V1.md);
  Universe v1 owns only `Teammate.universe` and
  `KnowledgeDocument.universe`; cross-Universe access is never
  implicit; auto-defaulting is rejected (§Q8, §Isolation invariants
  1–5).
- **Episode wraps Composition, 1:N** (EPISODE_VS_COMPOSITION_V1.md);
  Episode is Universe-scoped; rerender does not duplicate narrative
  history.
- **Episode is created EXPLICITLY** (EPISODE_LIFECYCLE_V1.md);
  auto-creation was corrected out; no story is auto-materialized
  around a Composition.
- **Character↔Character Relationships are Universe-owned canon**
  (RELATIONSHIP_BOUNDARY_V1.md); R5 chosen ("R2 scope, R3 shape");
  off-screen character relevance solved via cast-intersection query;
  **WorldEntity flagged as a future dependency (Ruby-owns-bakery,
  Mason-owns-coffee-shop) and deferred to this slice**
  (RELATIONSHIP_BOUNDARY_V1.md §Q10, §Q10-sub-slice).

The CAPABILITY_INVENTORY_SESSION_261.md §11 ("Assets = output media,
not props/objects"), §12 ("No location substrate — 12a/12b/12c are
disjoint concepts sharing the word 'backdrop'"), §17 ("No Project /
Universe / World container above Workspace"), and §D5 ("In-world
persistent objects — GENUINELY MISSING") converge on a single gap:
**named non-character things that recur across Episodes have no
substrate today.**

This slice answers exactly one question — **what persistent
primitive, if any, does a Universe need for named things that are
not Characters?** — and takes a position on the smallest boundary
that does not block later slices while avoiding the "every noun
becomes an entity" failure mode.

## Load-bearing principle carried forward

> **Legacy character data informs compatibility; it does not define
> Universe semantics.**
>
> Corollary specific to this slice:
> **Knowledge may describe a WorldEntity; knowledge must not
> constitute its existence.**

Direct parallel to the Character rule in
RELATIONSHIP_BOUNDARY_V1.md principle 2 ("character knowledge must
NOT define whether a relationship can exist"). A WorldEntity row
exists because the operator declared it. The K2 corpus around it,
the K5 sharing of business briefs, the K7 web-ingest of a landing
page — all of these describe it. None of them constitute it.

## Scope (and what's explicitly deferred)

**In scope.**

- Whether the Universe needs a persistent non-character primitive at
  all in v1.
- If yes: minimum semantic shape (no schema DDL).
- The Character / Relationship / WorldEntity / Knowledge / Episode
  distinction — what each owns; what none may absorb.
- Naming-collision resolution position (three-way
  background/backdrop/environment plus new candidates).
- Promotion / canon ownership — who moves a thing into WorldEntity
  and how.
- Off-screen entity relevance mechanism (analog of the
  cast-intersection query for Characters).
- Adversarial edge cases: props, animals/pets, subjects, legacy
  talking-heads.
- Sequencing relative to Relationship (which primitive lands first).

**Explicitly deferred.**

- Schema DDL, migrations, Django field additions.
- Any Character↔WorldEntity edge model (Ruby→owns→Bakery); called
  out only as a future dependency.
- WorldEntity↔WorldEntity edges (Bakery→next-door→CoffeeShop).
- Narrative memory substrate — referenced only where needed to prove
  the WorldEntity boundary.
- Per-entity K2 subscoping (a doc "about the bakery" that only
  cast-members with an edge to the bakery can retrieve).
- Location / Scene / Set / Room specialized subtypes.
- Product catalog / SKU model for e-commerce operators.
- SPA UX (picker, promotion gesture, list surface).
- Cascade policy on Universe delete for entity rows.
- Cross-Universe entity sharing (a "the Sun" landmark referenced by
  many Universes).
- Educational subject / curriculum entity design — flagged in the
  adversarial tests but not resolved here.

## Prior decisions carried forward

Restated for the record; each is a load-bearing gate on the answer
below.

1. Universe is opt-in and prospective; no auto-defaults
   (UNIVERSE_BOUNDARY_V1.md §Q8).
2. Legacy Teammates with `universe=NULL` remain in the legacy
   workspace regime unchanged (UNIVERSE_BOUNDARY_V1.md §Q6, §Q9).
3. Episode is explicit-only; no auto-creation
   (EPISODE_LIFECYCLE_V1.md §H3, §Correction).
4. Relationship is explicit-only, Universe-scoped, one row per pair
   (RELATIONSHIP_BOUNDARY_V1.md §Q6, §Isolation invariant 6).
5. Cross-Universe crossings are never implicit
   (UNIVERSE_BOUNDARY_V1.md §Isolation invariant 5;
   RELATIONSHIP_BOUNDARY_V1.md §Isolation invariant 10).
6. No implicit crossing primitive of any kind — no bypass flags, no
   "see all worlds" debug switch.
7. `Teammate.business_brief` is the current home for "Ruby owns a
   bakery" (RELATIONSHIP_BOUNDARY_V1.md §Q10). This slice tests
   whether that answer remains adequate.

## Current-state repository audit

Read-only search across `shell/apps` (18 Django apps enumerated
by `ls shell/apps/`: accounts, agents, billing, bootstrap_review,
campaigns, compositions, conversations, embeddings, identity,
memory, publish, realtime, scripts, spokespeople, transcripts,
videos). Results below cite file:line or state ABSENT after search.

| Search | Result | Cite |
|---|---|---|
| Class definitions matching `Location`, `Place`, `Environment`, `Set`, `Scene`, `World`, `Entity`, `Object`, `Prop`, `Product`, `Project`, `Business`, `Organization`, `Subject`, `Topic`, `Agent`, `Pet`, `Animal`, `Landmark`, `Venue`, `Setting`, `Stage`, `Room` in every `shell/apps/*/models.py` | **ABSENT.** Grep `class \w*(?:Location|Place|Environment|Set|Scene|World|Entity|Object|Prop|Product|Project|Business|Organization|Subject|Topic|Agent|Pet|Animal|Landmark|Venue|Setting|Stage|Room)\w*\(` returned zero matches. Verified enumeration of every model class: `Subscription`, `Script`, `TranscriptHighlight`, `BootstrapEvidenceIndex`, `PromotionAudit`, `PersonalizedCampaign`, `PersonalizedRecipient`, `Teammate`, `KnowledgeDocumentSpokesperson`, `KnowledgeDocument`, `KnowledgeChunk`, `ConversationThread`, `ConversationMessage`, `ConversationEmbedding`, `User`, `Workspace`, `Membership`, `RealtimeSession`, `RealtimeToolInvocation`, `EngineConnection`, `Video`, `CharacterIdentity`, `CharacterIdentityVersion`, `IdentityReference`, `GenerationRecord`, `GenerationRecordInput`, `NormalizationManifest`, `CanonicalVoiceReference`, `CanonicalRealtimeReference`, `ApprovedRepresentationBundle`, `ImportProvenance`, `PrequalificationProvenance`, `PublishBundle`, `PublishVariant`, `Asset`, `Composition`, `CompositionStep`. No entity/place/object/business/project/pet/animal/subject/landmark model exists. | grep on `class \w+\(` across `shell/apps/*/models.py`; CAPABILITY_INVENTORY_SESSION_261.md §D5, §D6 |
| `IdentityReferenceKind` enum | Six values: `PORTRAIT_REFERENCE`, `MOTION_REFERENCE`, `SPEECH_REFERENCE`, `BODY_REFERENCE`, `ENVIRONMENT_REFERENCE`, `EXPRESSION_REFERENCE`. Docstring says: **"Only `portrait_reference` is exercised in round-one benchmark; the other classes are declared so the substrate accepts them as valid kinds without accepting any purpose value yet."** `ENVIRONMENT_REFERENCE` is **dormant** — no purpose schema defines any purpose values for it; no Django model uses it. Reserved namespace, unimplemented. | `shell/apps/identity/models.py:344–361`; CAPABILITY_INVENTORY_SESSION_261.md §5 special question |
| `NormalizationManifest.background_id` | `CharField(64)`, identifier from `docs/design/visual/portrait_qualification/schemas/background_family_v1.yaml`. Five round-one identifiers (`neutral_warm_studio`, `neutral_cool_studio`, `warm_material_surround`, `soft_environmental_depth`, `conversational_darker_surround`). **Portrait-normalization scope only** — the background the identity's canonical portrait sits against. Not a persistent entity, not operator-facing, not a rendering scene. | `shell/apps/identity/models.py:955–961`; consumed by `media-engine/app/services/normalization/stages/background_replacement.py`; CAPABILITY_INVENTORY_SESSION_261.md §12a |
| `Asset(role=BACKDROP)` | `AssetRole` enum value at `shell/apps/compositions/models.py:AssetRole` line ~62–65. Cinematic clip that plays behind a talking head, produced by `generate_visual_clip` primitive or picked from the library. Consumed by `composite_video` primitive layout kind `backdrop` (`_VALID_LAYOUT_KINDS = {"pip", "backdrop", "cohost", "broll"}`). Recipes: `talking_head_with_backdrop`, `backdrop_layout`, `cohost_layout`, `pip_layout`, `broll_splice`. **Composition-scope only**; no persistent identity beyond the asset row itself. | `shell/apps/compositions/models.py:AssetRole ~62`; `compositions/primitives/composite_video.py:56`; `compositions/recipes.py:604–616`; CAPABILITY_INVENTORY_SESSION_261.md §12b |
| Two-way naming collision `NormalizationManifest.background_id` vs `Asset(role=BACKDROP)` | Confirmed: identity substrate calls it "background" (identifier from a yaml family); composition calls it "backdrop" (an Asset row). Two orthogonal concepts sharing a near-identical word. Audit already flagged this as "the two-way collision that becomes three-way if Location lands." | CAPABILITY_INVENTORY_SESSION_261.md §12; §C4 "Backdrop naming collision"; UNIVERSE_BOUNDARY_V1.md §Unresolved question 8 |
| `apps/memory` dormant scaffold | 0-line `models.py`, `views.py`, `urls.py`. `apps.py` is 6 lines (config only). Registered but empty. | `wc -l shell/apps/memory/*.py` → all zero except `apps.py=6`; CAPABILITY_INVENTORY_SESSION_261.md §C6; RELATIONSHIP_BOUNDARY_V1.md §Current-state search |
| `apps/agents` dormant scaffold | 0-line `models.py`, `views.py`, `urls.py`. `apps.py` is 6 lines (config only). Registered but empty. | `wc -l shell/apps/agents/*.py`; same |
| `Teammate.business_brief` — how business identity is carried | `TextField(blank=True, help_text="WHAT the business does — facts the teammate grounds their claims in. Product, target market, pricing, key policies. The K6 system prompt treats this as factual context (alongside retrieved knowledge chunks). Pre-W11.y (SESSION 175) this field held both facts AND personality; they're split now — describe the BUSINESS here and put voice / character / mannerisms in ``personality``.")`. This is where "Ruby owns a bakery" and "Mason owns a coffee shop" currently live per RELATIONSHIP_BOUNDARY_V1.md §Q10. **Free-text; no structured business identity, no business-name column, no business-type enum.** | `shell/apps/spokespeople/models.py:71–82`; RELATIONSHIP_BOUNDARY_V1.md §Q10 |
| Adjacent Teammate identity slots that could describe entities | `who_you_help` (target audience), `what_you_sell` (offering shape, "not a catalog — deep product detail lives on the knowledge side"), `always_emphasize` (signature messages), `never_say` (guardrails), `desired_feeling` (emotional outcome). All free-text. **No `Teammate.location`, `Teammate.venue`, `Teammate.stage`, `Teammate.business`, `Teammate.project` fields.** | `shell/apps/spokespeople/models.py:186–231` |
| `Composition.template_kind` — any location-like discriminator? | `CharField` with values including `talking_head`, `talking_head_with_backdrop`, `dialogue_scene`, `long_form_ad`. **Not a location discriminator** — it's a recipe-shape hint. No `Composition.location`, no `Composition.setting`, no `Composition.venue`. | `shell/apps/compositions/models.py:395–403`; CAPABILITY_INVENTORY_SESSION_261.md §10 |
| Recipe metadata (`dialogue_scene`, `talking_head`, `long_form_ad`) — any location/setting/scene-identity fields? | **None persistent.** `dialogue_scene` has a `label="What's the scene about?"` prose textarea (`compositions/recipes.py:1539–1553`) — this is topic prose, not a location reference. `talking_head_with_backdrop` has `backdrop_prompt` (textarea) + `backdrop_clip_id` (asset_picker filtered to `AssetRole.BACKDROP`) + `backdrop_ratio` + `backdrop_duration` + `use_extend_for_backdrop` (`compositions/recipes.py:587–649`). None of these persist a location identity; they parameterize a per-render backdrop selection. No `scene_location_id`, no `venue_ref`, no `entity_id`. | `shell/apps/compositions/recipes.py:587–649, 1539–1596` |
| Any model with `location`, `place`, `venue`, `setting`, `stage` in its columns | Grep for those tokens in every `shell/apps/*/models.py` returned **only prose / help-text mentions** — none as column names. Examples: `campaigns/models.py:110–114` ("placeholders" field — CSV templating), `compositions/models.py:475` ("no place to land"), `videos/models.py:105` ("Media-engine integration placeholder"). Zero substrate columns for location/place/venue/setting/stage. | grep results |
| `Asset.purpose` field | `CharField(max_length=20, blank=True, default="", help_text="Image purpose: avatar / scene / broll / product / ad. Empty for non-image assets.")`. Free-text hint — not a link to a persistent product/place/subject; used by SPA library-filter view (`models.Index(fields=["workspace", "purpose"])`). | `shell/apps/compositions/models.py:249–257, 345–346` |
| `Asset.subject` field | `TextField(blank=True, default="", help_text="Operator's original subject text, before prompt composition. Empty for non-image assets and for pre-W11.6.4 image rows.")`. Prose, not an entity FK. | `shell/apps/compositions/models.py:286–299` |
| `handoff_to_spokesperson` realtime tool | Audit-row-only; no relationship or persistent-entity created. | `shell/apps/realtime/tools/handoff_to_teammate.py:1–80`; RELATIONSHIP_BOUNDARY_V1.md §Current-state search |

**Search conclusion.** The substrate for non-character persistent
entities is **completely absent** — mirrors the RELATIONSHIP audit
finding. No dormant model to reuse. No half-populated enum whose
semantics can be re-purposed (ENVIRONMENT_REFERENCE is dormant but
scoped to *identity* substrate — the "environment around this
character's portrait" — not to Universe-shared entities). No
partial column on Teammate, Composition, or Asset. This is a
greenfield decision on whether a primitive is *needed*, not on
which existing thing to extend.

## Existing concepts that look entity-like (but aren't)

Distinguishing actual semantic entities from media/assets or prose
fields — the "String location on Composition would be prose, not a
persistent entity" test from the operator brief.

| Candidate | Is it a persistent entity? | Why / why not |
|---|---|---|
| `Asset` (`compositions/models.py:132–354`) | **No.** | Output-media record + generation provenance. Twelve-value `AssetRole` enum, `source_spec` JSON, nullable `composition` FK for library reuse. "The pixels of a bakery photo" — not "the bakery." Audit §11 explicit: "Assets are output-media records. Wrong home for persistent in-world objects." |
| `Asset(role=BACKDROP)` | **No.** | Same. A cinematic background clip. If reused across three renders as "Ruby's bakery scene," that's operator-discipline convention, not substrate. Audit §12b. |
| `NormalizationManifest.background_id` | **No.** | Portrait-normalization background family identifier. Five round-one identifiers, benchmarking scope. Not user-facing, not per-Universe, not a place. Audit §12a. |
| `IdentityReferenceKind.ENVIRONMENT_REFERENCE` | **No.** | Dormant enum value in the identity substrate; scoped to the character's own portrait environment, not to shared world entities. Audit §12c. |
| `Teammate.business_brief` prose | **No** (as an entity). **Yes** as a *fact-carrying prose slot* on the character. | The bakery is currently described here on Ruby. This is a character-owned prose fact, not an addressable row. Audit §5; RELATIONSHIP_BOUNDARY_V1.md §Q10. |
| `Teammate.what_you_sell` prose | **No.** | "Offering described at the shape level. Not a catalog — deep product detail lives on the knowledge side." Explicitly not a product entity. |
| `KnowledgeDocument` | **No** (as an entity). Yes as knowledge *about* something. | A doc "about the bakery" describes it; the doc is not the bakery. Empty-M2M means "visible to every teammate in this workspace/Universe" (UNIVERSE_BOUNDARY_V1.md §Q9). Facts flow through knowledge, not through knowledge-as-identity. |
| `Composition` `dialogue_scene` prose "What's the scene about?" | **No.** | Per-render topic prose, per `compositions/recipes.py:1539–1553`. Not persisted as a scene identity. |
| `PublishBundle.source_clip` | **No.** | Distribution artifact keyed on an Asset. Never a place / product / project. |
| `PersonalizedCampaign` | **No.** | CSV-driven personalized-video batch (`campaigns/models.py:44+`) — one template + N recipients. Not a project / world entity; recipients are targets, not persistent entities. |

**Load-bearing observation.** The repository does not have a
persistent non-character entity today. Everything above either
(a) is a media/asset artifact, (b) is a per-render parameter, or
(c) is a prose field on Character or Composition. No addressable
row exists for "the bakery," "the workshop," or "the AI-agent
project" as a thing distinct from any character or any render.

## Naming collision map

Currently in the codebase, with meaning per site. This map goes
into every option evaluation below.

| Term | Site | Meaning | Scope |
|---|---|---|---|
| `background` | `NormalizationManifest.background_id` (`identity/models.py:955–961`) | Portrait-normalization background family identifier (`neutral_warm_studio`, etc.). The background the identity's canonical portrait sits against. | Identity substrate; per-generation. |
| `background_family_v1.yaml` | `docs/design/visual/portrait_qualification/schemas/background_family_v1.yaml` | Five identifiers + `tonal_environment_class_default_background` mapping + `reviewer_override`. | Portrait qualification benchmark; five values only. |
| `backdrop` | `Asset(role=BACKDROP)` (`compositions/models.py:AssetRole ~62`) | Cinematic clip that plays behind a talking head. Rendered by `generate_visual_clip` or picked by `backdrop_clip_id` asset-picker. | Composition; per-render. |
| `backdrop` (as recipe field) | `talking_head_with_backdrop.backdrop_prompt`, `.backdrop_clip_id`, `.backdrop_ratio`, `.backdrop_duration` (`compositions/recipes.py:587–649`) | Recipe kwargs parameterizing the backdrop Asset selection. | Recipe; per-render kwargs. |
| `environment` | `IdentityReferenceKind.ENVIRONMENT_REFERENCE` (`identity/models.py:359`) | Dormant enum value on the identity substrate. Reserved namespace; no purpose schema defined. | Identity substrate; unused. |
| `scene` | `dialogue_scene` recipe kind; `Asset.purpose="scene"`; `AssetRole` values include foreground/scene backdrop | Prose / hint / recipe name; not a persistent identity. | Composition & Asset; per-render / library-filter. |
| `location` | ABSENT from `shell/apps/*/models.py` as a column. Prose mentions only. | No meaning today. | — |
| `world` | ABSENT from `shell/apps/*/models.py`. Design docs use it interchangeably with `Universe`. | Design-doc term; no substrate. | — |
| `place` | ABSENT. Prose mentions only. | No meaning today. | — |
| `venue` | ABSENT. | No meaning today. | — |
| `setting` | ABSENT as a column. Prose in help_text only. | No meaning today. | — |
| `stage`, `room` | ABSENT. | No meaning today. | — |
| `Environment` (Django settings usage) | `settings.AUTH_USER_MODEL` etc. — unrelated to WorldEntity. | Framework term. | — |

**Collision analysis.**

- **Two-way today:** `background` (identity substrate) vs `backdrop`
  (composition Asset). Two orthogonal concepts, near-identical
  word. Already flagged as `C4` in the audit and as unresolved
  question 8 in UNIVERSE_BOUNDARY_V1.md.
- **Three-way if Location lands:** operator-facing "location"
  (a workshop, a bakery) would overlap with both `background`
  (portrait normalization) and `backdrop` (scene clip). The
  scene-selection UI would carry a Location picker distinct from
  the backdrop-Asset picker distinct from the portrait-normalization
  family. Three primitives, three names, none quite
  interchangeable.
- **Four-way if WorldEntity is generic:** if `WorldEntity` covers
  places AND businesses AND projects AND props, the
  operator-facing surface has to disambiguate ("is this a business
  or a place?") on top of the existing three-way collision. The
  naming complexity does not disappear by generalizing; it moves
  to a `WorldEntity.kind` field the operator has to think about.

**Resolution position taken later** (see "Recommended boundary").

## Options W1–W5 stated

- **W1 — No WorldEntity in v1.** Places / projects / businesses /
  props live in `Teammate.business_brief`, Universe canon / K2
  docs, and Episode prose (`operator_topic` field per
  EPISODE_LIFECYCLE_V1.md §Q7). Simplest. Accept the continuity
  leak — cross-character bakery-description drift, no
  cross-Episode entity addressability.
- **W2 — Specialized models.** `Location`, `Business`,
  `Organization`, `Project`, `Prop`, `Product`, etc. each as
  separate primitives from day one. Each with its own semantic
  ownership, its own operator-facing type, its own edge model.
- **W3 — Generic WorldEntity.** One Universe-scoped persistent
  entity with a `kind` / `type` discriminator (`place`, `business`,
  `project`, `prop`, `landmark`, `subject`, …). One model,
  operator-authored type vocabulary.
- **W4 — WorldEntity base + specialized future extensions.**
  Minimal shared identity now (name, kind, description, Universe
  FK) as one row; specialized sidecar models only when concrete
  evidence forces them (e.g., a real product catalog with SKUs
  would sidecar the base WorldEntity row).
- **W5 — Something else the repository/product evidence dictates.**
  Reserve for a narrowed refinement.

## Options × Stress-test matrix

**Setup (operator-supplied):**

- Universe: **Patch/Rivet recurring world**.
- Characters: Patch, Rivet, Ruby the Fox, Mason the Bear.
- Persistent non-character things: Patch/Rivet Workshop, Ruby's
  Bakery, Mason's Coffee Shop, AI Agent Project.
- Relationships (per RELATIONSHIP_BOUNDARY_V1.md): Patch↔Rivet
  (partners), Ruby↔Bakery (owns), Mason↔CoffeeShop (owns) — the
  last two are Character↔Location/Business edges that are
  explicitly **deferred** by that slice's §Q10 ("Relationship v1
  does NOT model Character↔Location or Character↔Organization
  edges").

Rows = options. Columns = the five operator Episodes. **Bold**
flags where the option fails, corrupts state, or forces ceremony.

| Option | Episode A: Mason approaches Patch at the coffee shop; Patch agrees to build an AI agent | Episode B: Patch + Rivet in the workshop discussing the AI Agent Project. Mason NOT in cast. Coffee shop NOT the location. | Episode C: Patch installs/tests the AI agent at Mason's coffee shop. Rivet may or may not appear. | Episode D: Ruby visits Mason's coffee shop. Neither Patch nor Rivet. Coffee shop must still be the SAME coffee shop. | Episode E: Months later, Patch references what happened with Mason's AI agent. Mason does not appear. |
|---|---|---|---|---|---|
| **W1 No WorldEntity** | Coffee shop lives on Mason's `business_brief`. Cast {Mason, Patch}. Episode.operator_topic carries "Mason approaches Patch at the coffee shop." Works. AI-agent project lives in Relationship.notes on Mason↔Patch (per RELATIONSHIP_BOUNDARY_V1.md §Q10). | Cast {Patch, Rivet}. Off-screen relevance of Mason: cast-intersection surfaces Patch↔Mason Relationship row (per RELATIONSHIP §Off-screen mechanism). AI-agent project surfaces via Relationship.notes on that row. **Coffee shop as a stable entity is NOT surfaced** — it's still on Mason's business_brief, which is loaded only if Mason is in cast OR via the Mason↔Patch relationship-notes stopgap. Fragile but shippable. | Cast {Patch}, maybe {Patch, Rivet}. "At Mason's coffee shop" is prose in operator_topic. Backdrop-Asset picking is operator-discipline convention. **No structural guarantee this is the same coffee shop as Episode A** — the operator has to remember to reuse the same backdrop clip. Continuity leaks. | Cast {Ruby, Mason}. "At Mason's coffee shop" prose in operator_topic. **Zero guarantee this is the same coffee shop as Episodes A/C** — different render, different backdrop, potentially different description if Mason's business_brief evolved between renders. Silent drift. | Cast {Patch}. "The AI agent project with Mason" surfaces via Patch↔Mason Relationship row + relationship-notes stopgap. **Works only because the notes carry the reference by prose.** No addressable "project" entity. |
| **W2 Specialized models** | `Business` row "Mason's Coffee Shop" (or `Location`; W2 forces the choice up-front). Episode.location = coffee-shop row. Cast {Mason, Patch}. `Project` row "AI Agent for Mason's Coffee Shop" created; Episode E's outcome edge references it. **Load: three new primitives (Business/Location/Project) up-front for a first-Episode.** | Coffee-shop `Business/Location` row loaded via Universe scope; off-screen entity relevance via a symmetric "entity-cast-intersection" query on the Business row (see §Off-screen entity relevance). Project row surfaced via reference-edge to Patch↔Mason. Works. | Episode.location = coffee-shop row. Same row as Episode A. Continuity guaranteed by construction — no operator-discipline required. | Episode.location = coffee-shop row. Same row again. Ruby↔coffee-shop edge (visits, patron, ...) as a Character↔Business edge — but this is a NEW edge type the slice deferred. Works IF the edge model lands. Otherwise the operator has "cast + location" but no relationship-shape. | Project row queryable by name; Patch's synthesis loads the project via a Character↔Project edge (again, new edge type). Works if edges land. |
| **W3 Generic WorldEntity** | WorldEntity `Coffee Shop` with `kind=place` (or `kind=business`) created. Episode.location or Episode.subjects M2M references it. Cast {Mason, Patch}. WorldEntity `AI Agent Project` with `kind=project` also created. **Two rows, one primitive, operator-authored kinds.** | WorldEntity loaded via Universe scope + entity-intersection with cast's relationships. Works if the entity-cast query lands. | Episode.location = same coffee-shop WorldEntity row. Continuity guaranteed. | Episode.location = same coffee-shop WorldEntity row. Ruby↔coffee-shop edge again a new edge type, but WorldEntity's `kind` doesn't matter — the edge model handles the referent. | Project WorldEntity loaded via off-screen entity relevance query. Works. |
| **W4 WorldEntity base + future specialization** | WorldEntity `Coffee Shop` (base row: name + description + kind hint + Universe FK). No specialized `BusinessDetails` sidecar yet. Episode references it. Cast {Mason, Patch}. WorldEntity `AI Agent Project` (base row). **Same rows as W3 without the kind discriminator being load-bearing.** | Same as W3. Off-screen relevance identical. | Same as W3. | Same as W3. Ruby↔WorldEntity edge is a new edge type. | Same as W3. |
| **W5 Named refinement** | See "Recommended boundary" below. | | | | |

**Reading the matrix.**

- **W1 handles Episodes A + B + E acceptably** because the
  RELATIONSHIP substrate already committed carries Patch↔Mason,
  and the coffee shop / project ride on relationship-notes prose
  (a documented stopgap). **W1 fails Episodes C + D on
  continuity** — the coffee shop's identity depends on
  operator-discipline backdrop reuse and prose consistency across
  characters. No structural guarantee.
- **W2 handles all five correctly** but forces multiple new
  primitives (Business, Location, Project, Prop, ...) up-front,
  each with its own semantic ownership, its own edge type, its
  own operator-facing surface. **Ceremony cost is high** for a
  Universe that today has three or four persistent things across
  a small dogfood.
- **W3 handles all five correctly** with one primitive + a `kind`
  discriminator. **Ceremony cost is one new primitive + a `kind`
  field.** Risk: the discriminator becomes load-bearing on
  operator UX ("is this a business or a place?") in exactly the
  way the naming collision map warned.
- **W4 handles all five correctly** with a base row that intentionally
  under-commits on `kind`. If a specialized `Business` sidecar is
  needed later, it attaches to the base row; if it never is, the
  base row remains sufficient. **Lowest ceremony that still
  addresses continuity.** Kind is a hint, not a load-bearing
  discriminator.
- **All of W2/W3/W4 depend on a Character↔WorldEntity edge model**
  that RELATIONSHIP_BOUNDARY_V1.md §Q10 explicitly deferred. Any
  option that adopts a WorldEntity primitive must also name
  whether/when Character↔WorldEntity edges land — see "Sequencing"
  below.

## Adversarial tests

Each test challenges the W3/W4 abstraction from a different angle.

### T1. Power-cutoff-switch prop.
Rivet moves a power cutoff switch closer to Patch's desk in one
Episode. Three Episodes later it's a running joke ("did you check
the cutoff?"). Does every prop become a WorldEntity?

- **Under W1**: prose in Episode.operator_topic ("the power
  cutoff Rivet moved") for each Episode that references it.
  Continuity drift risk if the switch's location changes; probably
  acceptable at low volumes.
- **Under W3/W4**: creating a `PowerCutoffSwitch` WorldEntity for
  every recurring prop would explode row count and turn Universes
  into inventory ledgers. **Promotion boundary required**: a prop
  becomes a WorldEntity only when the *operator* declares it
  narratively significant. No auto-promotion from Episode prose.
  Mirrors the Relationship principle "no implicit creation"
  (RELATIONSHIP §Isolation invariant 6).
- **Position**: the promotion boundary is *operator declaration*,
  same as Universe, Episode, Relationship. Recurrence frequency
  does not auto-promote. Row count under WorldEntity is bounded
  by operator effort — same discipline that keeps Episode count
  bounded (EPISODE_LIFECYCLE §Correction).

### T2. Vet-clinic recurring dog patient.
A dog appears repeatedly at a fictional vet clinic. Non-speaking
narrative identity. Teammate? WorldEntity? Character subtype?

- **Under W1**: no substrate at all. The dog lives in prose or in
  the vet's `business_brief`. Continuity drift is high.
- **Under Teammate (Character)**: `CharacterIdentity.kind` accepts
  `non_human` (`shell/apps/identity/models.py:106–108`); the dog
  could be a Teammate. But then it inherits the Teammate obligations
  (voice fields, K2 corpus, potentially a Runway avatar).
  **Overkill for a non-speaking narrative identity.** Also
  contradicts the CAPABILITY_INVENTORY_SESSION_261.md §6 special
  question that non-human canonicals require Character Presence
  Language to land first — a path not yet paved.
- **Under W3/W4 WorldEntity `kind=animal`**: the dog is an
  addressable, referenced-by-Episode entity without carrying
  Character weight. Continuity guaranteed. Description evolves
  under the WorldEntity row, not spread across characters.
- **Position**: WorldEntity is the correct home for a non-speaking
  narrative identity. If the dog is ever promoted to a speaking
  Character (voice, K2, Runway avatar), that's a separate
  operator gesture — Teammate creation — not a "promote WorldEntity
  to Teammate" mechanic (which does not exist and should not).

### T3. Educational subject "Fractions" or "the water cycle."
Subject of several Episodes but not a "world object" in the
bakery/coffee-shop sense. Does WorldEntity absorb semantic topics
improperly?

- **Under W1**: lives in Episode.operator_topic and in K2 docs.
  Works for teachers with a low count of subjects; drifts at
  scale (a first-grade teacher covering 40 subjects/year would
  benefit from an addressable subject).
- **Under W3/W4 with `kind=subject`**: technically works — subject
  becomes a Universe-scoped addressable entity. But **the risk
  identified in CAPABILITY_INVENTORY_SESSION_261.md §16
  ("EDUCATION / CURRICULUM / GOAL STRUCTURES — ABSENT")** is that
  educational objectives / audiences / curricula are a
  *different semantic category* than places/props/businesses.
  Absorbing them into WorldEntity conflates "what the story is
  about" with "what recurs in the world." The two are related but
  not identical.
- **Position**: **v1 WorldEntity should NOT absorb educational
  subjects.** Subject/topic/lesson/objective is a separate
  concept that will need its own primitive (or an extension of
  Episode) in the future EDUCATION slice. WorldEntity's `kind`
  vocabulary should NOT include `subject`, `topic`, `lesson`,
  `objective` — the operator's SPA UX should refuse those. Strong
  negative boundary; this is the "what is explicitly NOT a
  WorldEntity" test.

### T4. Legacy Mike-the-plumber talking-head.
Has no Universe. Should any of this touch him?

- **Answer**: **No.** Mirrors RELATIONSHIP_BOUNDARY_V1.md §Legacy
  behavior — legacy Teammates with `universe=NULL` cannot
  participate in Universe-scoped substrates. Mike, Repo Red, and
  Tulsi have no WorldEntities associated with them. Their
  `business_brief` continues to carry their business identity as
  free text; their talking-head cadence renders one Composition per
  video with no Episode, no Relationship, no WorldEntity, and this
  is the *correct* state for content that is not a story.
- No promotion is required. No migration is required. WorldEntity
  substrate silently ignores legacy Teammates.

## Q1–Q20 answered

### Q1. What non-character persistent concepts already exist in the codebase?

**None as first-class entities.** Enumerated in the current-state
audit above:

- `Asset` (with role variants BACKDROP, PORTRAIT, etc.) is an
  output-media artifact, not a persistent world entity.
- `NormalizationManifest.background_id` is a portrait-normalization
  family identifier (5 values), not a world entity.
- `IdentityReferenceKind.ENVIRONMENT_REFERENCE` is a dormant
  identity-substrate enum, not a world entity.
- `Teammate.business_brief` / `.what_you_sell` are prose fields on
  a character, not entities.
- `KnowledgeDocument` is knowledge *about* things, not the things.

Grep for `Location|Place|Environment|Set|Scene|World|Entity|Object|Prop|Product|Project|Business|Organization|Subject|Topic|Agent|Pet|Animal|Landmark|Venue|Setting|Stage|Room` as class name across `shell/apps/*/models.py` returned zero matches.

### Q2. Is "Ruby owns a bakery" character knowledge / Universe canon / Relationship / Character↔Place / other?

RELATIONSHIP_BOUNDARY_V1.md §Q10 took the v1 position: **the fact
lives on `Ruby.business_brief` (character-owned fact); the "Bakery"
as a shared entity does not exist in v1 substrate; when WorldEntity
lands, the fact remains on `Ruby.business_brief` AND a
Character↔WorldEntity edge (Ruby→owns→Bakery) becomes possible.**

This slice's position:

- **In v1 (this slice's boundary)**: "Ruby owns a bakery" remains
  on `Ruby.business_brief` as a character-owned fact, EVEN IF
  WorldEntity ships. The Bakery WorldEntity is created only when
  the operator declares narrative significance beyond
  Ruby-describes-her-business (e.g., the Bakery is referenced by
  other characters, appears in Episodes that don't feature Ruby,
  or needs a stable description across renders).
- **The Character↔WorldEntity edge (Ruby→owns→Bakery) is deferred**
  to a later slice. RELATIONSHIP_BOUNDARY_V1.md §Q10 named this
  explicitly. This slice preserves the deferral and confirms
  WorldEntity v1 does not require it.
- **Knowledge may describe (K2 doc about the bakery); knowledge
  must not constitute (the K2 doc is not the bakery).** This is
  the load-bearing corollary of the SESSION 261 principle.

### Q3. Can Ruby's Bakery exist and remain canonical when Ruby is absent from an Episode?

**Under W1: partially — via `Ruby.business_brief` loaded through
character-intersection-of-cast + Ruby↔Bakery Relationship prose
(which does not exist since Relationship v1 doesn't model
Character↔Place). Fails Episode D (Ruby visits Mason's coffee shop —
no coffee-shop identity survives Ruby's absence from an Episode
about the coffee shop).**

**Under W3/W4: yes, structurally.** The Bakery WorldEntity is
Universe-scoped; it is loaded via Universe-scoped canon / entity-
intersection queries, not via character-cast intersection. Its
identity does not depend on any character being in the cast.

This is the load-bearing argument for a WorldEntity primitive:
**an entity's canonical identity must survive the absence of its
owner-character from an Episode.** Without WorldEntity, coffee-shop
continuity depends on Mason being in cast (or a Character↔Place
edge from someone in cast to the shop) — which fails Episode D
(Ruby visits, Mason absent).

### Q4. Can Mason's Coffee Shop be referenced by multiple Characters/Episodes without duplicating its description?

**Under W1: no.** Its description lives on Mason's business_brief;
if Ruby describes it in Episode D from her perspective, her
description of it lives in Episode D's operator_topic / rendered
prose. Two descriptions of the same shop across two Episodes drift
independently. No canonical row.

**Under W3/W4: yes.** The Coffee Shop WorldEntity carries one
canonical description; Episodes reference the entity; character
perspectives on the entity are per-Episode content, not per-Episode
identity re-authoring.

This directly answers the load-bearing continuity concern: a
WorldEntity primitive is the mechanism that prevents description
drift across characters and Episodes.

### Q5. Is the Patch/Rivet Workshop the same KIND of persistent thing as Ruby's Bakery?

**Both are places-of-work owned by (or associated with) specific
characters. Same category.** Both:

- Recur across Episodes.
- Have a persistent identity independent of any given render.
- Can be visited by characters other than the owner-of-record.
- Are described by knowledge (K2 docs) but constituted by operator
  declaration.

W3 handles both under `kind=place` or `kind=business`. W2 would
force the operator to choose whether Bakery is a `Business` or a
`Location` (or create both a Business row and a Location row and
link them) — **W2's specialization ceremony is not justified by
any concrete difference** between Workshop and Bakery in the
operator's mental model.

**W4's answer**: both are WorldEntity rows; `kind` is a hint the
operator sets. If someone later needs `BusinessDetails` (hours,
menu, product catalog) as a sidecar, they can add it — but that's
an operator-driven need, not a base-primitive-forcing distinction.

### Q6. Is the AI Agent Project the same KIND as those places?

**No.** A place has spatial identity (you can visit it). A project
has temporal identity (it has a start, a milestone, an outcome; it
completes). This is the hardest test of W3's `kind` discriminator.

- **Under W1**: project lives in `Relationship.notes` on Mason↔Patch
  as a prose stopgap (RELATIONSHIP §Q10). Fragile but shippable.
- **Under W3 with `kind=project`**: project becomes an addressable
  entity. Episodes A, C, E all reference it. Episode B (Patch +
  Rivet discussing it, Mason absent) surfaces it via off-screen
  entity relevance.
- **Under W4**: same, `kind=project` is a hint; the base row
  carries name/description/Universe. If the operator later wants
  project-specific state (status: proposed / in-progress /
  complete; milestones; deliverables), a `ProjectDetails` sidecar
  is added — but the base row is enough to address it in v1.

**W3/W4 does NOT collapse the important difference** between place
and project because the operator's `kind` label preserves it in the
UI. **What W3/W4 DOES collapse** is the substrate cost of
representing both — one primitive with a hint, not two primitives
with distinct schemas.

**Position**: the `kind` field is a hint, not a load-bearing
discriminator. If the difference between place and project becomes
load-bearing (e.g., project-lifecycle state machine), that's a
sidecar on the base row, not a fork of the primitive. W4 handles
this cleanly; W3 handles it if the operator resists over-loading
`kind`.

### Q7. Physical recurring objects (power cutoff switch): does every prop become an entity? Where is the promotion boundary?

Answered in Adversarial Test T1 above.

- **Promotion boundary: explicit operator declaration.** Same as
  Universe (§Q8), Episode (§H3), Relationship (§Isolation
  invariant 6).
- **No auto-promotion from Episode prose.** Recurrence in
  `operator_topic` across Episodes does not mint a WorldEntity;
  the operator has to declare it.
- **Row count is bounded by operator effort.** The primitive is
  cheap when few things need it (Patch/Rivet dogfood: ~4 entities);
  expensive when the operator promotes everything (correct
  disincentive).
- **Props remain in Episode prose until the operator says
  otherwise.** This is the same discipline that keeps Episode
  count bounded — no story is auto-materialized.

### Q8. Animals/pets: recurring vet-clinic dog — Teammate / WorldEntity / Character subtype / other?

Answered in Adversarial Test T2 above.

- **WorldEntity `kind=animal`** is the correct home for a
  **non-speaking** narrative identity.
- **Teammate** with `CharacterIdentity.kind=non_human` is the
  correct home for a **speaking** character (voice, K2 corpus,
  Runway avatar). Contingent on Character Presence Language
  landing (CAPABILITY_INVENTORY_SESSION_261.md §6 special
  question).
- **No auto-promotion from WorldEntity to Teammate.** If the
  operator later decides the dog should speak, that's a new
  Teammate creation — separate operator gesture, separate
  substrate.

### Q9. Educational subjects ("Fractions", "water cycle"): does WorldEntity absorb semantic topics improperly?

Answered in Adversarial Test T3 above.

- **v1 position: WorldEntity does NOT absorb semantic topics.**
- Subject / topic / lesson / objective are a **separate
  semantic category** (CAPABILITY_INVENTORY_SESSION_261.md §16;
  §D8 GENUINELY MISSING) with distinct concerns (audience,
  curriculum, learning outcome, evaluation).
- **Strong negative boundary**: WorldEntity `kind` vocabulary
  should NOT include `subject`, `topic`, `lesson`, `objective`,
  `curriculum`, `learning_goal`. If the operator wants to
  represent "the water cycle" as a persistent thing, the
  substrate answer is **the deferred EDUCATION slice**, not
  overloading WorldEntity.
- Where does subject matter live *in v1*? On Episode. Episode
  already owns `operator_topic` (EPISODE_LIFECYCLE_V1.md §Q7);
  Episode's future `educational_objective` / `audience` /
  `purpose` fields (deferred there) will carry subject-matter
  semantics. WorldEntity is not the answer.

### Q10. Does WorldEntity need typed relationships (Ruby→owns→Bakery, Patch→works_at→Workshop, Project→for→Mason, Project→deployed_at→CoffeeShop)? Reuse the committed Character↔Character Relationship? Separate generalized edge substrate? No edges in v1? Take a position — do NOT redesign Relationship.

**Position: NO Character↔WorldEntity edges in v1. YES eventually,
via a NEW edge model — NOT by reshaping the committed Character↔Character
Relationship.**

Reasoning:

- The committed Relationship row shape
  (RELATIONSHIP_BOUNDARY_V1.md §Q12) is
  `teammate_a`/`teammate_b`/`type`/`type_reverse`/`status`/`notes`.
  Both endpoints are Teammate FKs. **Reshaping to allow WorldEntity
  endpoints would break the row's semantic identity** — the
  isolation invariants (self-loops rejected, cross-Universe rejected,
  normalized ordering) are all Teammate-typed.
- A **new** `CharacterEntityEdge` (or similar) model with
  `teammate` + `world_entity` endpoints is the correct future
  shape. RELATIONSHIP_BOUNDARY_V1.md §Q10 flagged this: "when
  Location/WorldEntity lands, it will introduce Character↔Location
  and Character↔Organization edges as NEW models — NOT by
  reshaping Relationship."
- **WorldEntity↔WorldEntity edges** (Project→deployed_at→CoffeeShop,
  Bakery→next-door→CoffeeShop) are a third edge model. Deferred.
- **v1 responsibility of THIS slice**: establish WorldEntity as a
  standalone Universe-scoped primitive. Do NOT introduce any edge
  model. Off-screen relevance (§Q12 below) uses a different
  mechanism.

**Explicit non-reshape of Relationship**: this slice does not
touch RELATIONSHIP_BOUNDARY_V1.md's committed row shape. Its
`teammate_a`/`teammate_b` FKs stay pointing to Teammate; no
generalized-endpoint refactor is proposed.

### Q11. Does Episode need `location` / `subjects` / `referenced_entities` / `featured_entities`? Or is that inferred from narrative memory?

**Position: v1 Episode gains an OPTIONAL `referenced_entities` M2M
to WorldEntity (may be empty). No `location` scalar field. No
`subjects` field.**

Reasoning:

- `location` as a scalar collapses W3/W4's `kind` distinction into
  Episode's schema — "the Episode's location is one place" is
  wrong for scenes that traverse multiple places (Patch travels
  from workshop to coffee shop in one Episode). If an Episode
  needs a primary location, that's an SPA affordance ("which of
  these referenced entities is the primary setting?") on top of
  the M2M, not a schema-level scalar. Deferred to schema slice.
- `subjects` is educational / curricular — deferred per §Q9.
- `referenced_entities` M2M matches the way `Episode.cast` M2M
  matches Teammates. Symmetric shape. Loads at synthesis time
  alongside cast.
- **Empty is legal.** An Episode with no referenced entities is
  the common case (a talking-head Episode about "why plants need
  sunlight"). The M2M is populated only when the operator
  explicitly attaches entities.
- **Cast-eligibility parallel:** just as `Episode.cast` members
  must be `teammate.universe == episode.universe` (EPISODE_LIFECYCLE
  §Constraint invariants), `Episode.referenced_entities` members
  must be `world_entity.universe == episode.universe`. Same
  invariant, extended to entities.

**Narrative-memory alternative:** eventually, "which entities
matter to this Episode" could be inferred from narrative-memory
events keyed on Episode. But the M2M is the durable operator-
authored surface; narrative memory augments, not replaces.

### Q12. How does synthesis know an off-screen ENTITY matters?

**Episode B is the load-bearing case**: Mason's coffee shop
matters but neither Mason nor the shop is on stage.

RELATIONSHIP_BOUNDARY_V1.md solved off-screen **character**
relevance via **cast-intersection query**: `Relationship WHERE
universe = episode.universe AND (teammate_a IN cast OR teammate_b
IN cast)`. This surfaces Patch↔Mason to Episode B (Mason absent,
Patch in cast).

**Entity analog (position): entity-intersection via
character-attached-entities and episode-referenced-entities.**

At synthesis time, load:

1. `WorldEntity WHERE universe = episode.universe AND id IN
   episode.referenced_entities` — the operator-declared entities
   for this Episode.
2. `WorldEntity WHERE universe = episode.universe AND id IN
   (SELECT world_entity_id FROM character_entity_edge WHERE
   teammate_id IN cast)` — the entities attached to cast members
   via Character↔WorldEntity edges. **Requires the deferred edge
   model.**
3. `WorldEntity WHERE universe = episode.universe AND id IN
   (SELECT referenced_entity_id FROM relationship_notes ...)` —
   entities referenced by prose in cast-intersection Relationship
   rows' notes. **This is the v1 stopgap** while
   Character↔WorldEntity edges are deferred.

**v1 (this slice) provides ONLY step 1** — the explicit
`Episode.referenced_entities` M2M. Steps 2 and 3 are deferred to
the edge-model slice.

For Episode B (Mason's coffee shop matters, Mason absent):

- **v1 answer**: the operator populates `Episode.referenced_entities
  = [Mason's Coffee Shop, AI Agent Project]` when authoring
  Episode B. Synthesis loads these entities' descriptions verbatim
  into the prompt.
- **Post-edges answer**: even if the operator forgets, Patch's
  Character↔WorldEntity edge to the coffee-shop (via the
  AI-agent project, or via a `works_with` edge to Mason's
  business) surfaces the coffee shop automatically. Belt and
  suspenders.
- **Off-screen entity is native to W3/W4 with an M2M.** W1 has no
  answer.

### Q13. Does K2 remain appropriate for any of this?

Four distinctions to make:

1. **Facts ABOUT an entity** ("Mason's coffee shop opens at 7am;
   serves cold brew; located near the park") → **K2**. Facts are
   knowledge. A KnowledgeDocument in the same Universe with M2M
   empty (or attached to Mason) carries these; retrieval scopes
   them appropriately.
2. **An entity's identity itself** ("Mason's Coffee Shop is a
   persistent place in this Universe") → **WorldEntity**. The
   name, the operator-authored description, the `kind` hint. This
   is what W3/W4 provides that K2 cannot — an addressable row.
3. **A character's knowledge ABOUT the entity** ("Ruby's view of
   Mason's coffee shop is that it's overpriced") → **either
   Character-owned prose (Ruby's `business_brief` / `personality`)
   or Character↔WorldEntity edge notes (deferred)**. Not K2 (K2 is
   factual, not perspectival) and not WorldEntity (the entity's
   identity is not shaped by any one character's view).
4. **Universe canon ABOUT the entity** ("The coffee shop's role in
   the Patch/Rivet Universe is as the small-business AI-agent
   pilot site") → **Universe canon** (via K2 doc with `M2M=empty`
   under UNIVERSE_BOUNDARY_V1.md §Q9, which makes the doc visible
   to every teammate in that Universe) OR **WorldEntity.description**
   field on the entity row. Both are legitimate; the position is
   that **operator-authored short description lives on the
   WorldEntity row**; **longer canonical prose lives in K2**.

**"Knowledge may describe; knowledge must not constitute" applied
here**: the K2 doc "About the Coffee Shop" is not the coffee shop.
Deleting the doc does not delete the coffee shop. Creating the doc
does not create the coffee shop. The WorldEntity row is what
constitutes the coffee shop's existence.

### Q14. What is the smallest useful WorldEntity primitive IF evidence supports one? Semantic minimums only — no schema. Challenge every candidate field.

Under **W4** (chosen; see "Recommended boundary"):

- **`id`** — row identity. YES; unavoidable.
- **`universe` FK** — YES, NOT NULL. Universe-scoped by construction
  (mirrors Relationship's Universe FK; mirrors Episode's Universe
  FK).
- **`workspace` FK** — YES, denormalized, must equal
  `universe.workspace`. Defense-in-depth per UNIVERSE_BOUNDARY_V1
  §Isolation invariants.
- **`name`** — YES, short string, operator-authored. Human-facing
  identifier. Uniqueness constraint deferred to schema slice
  (`(universe, name)` unique is a reasonable default; the audit
  already applies this pattern to Teammate).
- **`kind`** — YES, but as a **freeform text hint**, not an enum.
  Same posture as Relationship.type (RELATIONSHIP §Q6 "freeform
  text in v1; the vocabulary is operator-authored"). Constraining
  to an enum locks in premature choices. Length-cap and
  lower-cased at service layer. **Vocabulary discouraged from
  including educational subjects** (see negative boundary below).
- **`description`** — YES, freeform text. The operator-authored
  short canonical description. Surfaced verbatim to Episode
  synthesis when the entity is referenced.
- **`status`** — YES, minimal: `active` / `archived`. Distinguishes
  "current" from "retired" (Ruby's bakery burned down; still
  historically real; no longer active). Same shape as
  Relationship.status without the `former` complication (an entity
  is either active or archived; "former coffee shop" is a
  description question).
- **`created_by` / `created_at` / `updated_at`** — YES, standard.
- **`metadata` (JSON)** — CHALLENGED. **Position: NO in v1.** JSON
  metadata is where a primitive goes to become a swamp. If a
  specific sidecar is needed (BusinessDetails, ProjectDetails),
  add a sidecar model. Do not offer a `metadata` catch-all — the
  operator will fill it, the SPA will render it, and the semantic
  ownership blurs.
- **`slug`** — CHALLENGED. **Position: NO in v1.** URL routing
  is an SPA concern; if a per-Universe slug is needed, add it
  in the SPA slice. Row uniqueness via `(universe, name)` is
  enough.

**Rejected candidate fields** (each explicitly excluded):

- No FK to a "canonical Asset" or "canonical image" — coupling
  WorldEntity to Asset creates the "which backdrop is this bakery"
  question that the naming-collision map already fought.
  Post-hoc: an operator may want to associate a library
  Asset(role=BACKDROP) with a WorldEntity for scene-picker UX; do
  that in a later slice via a nullable back-ref or a picker
  affordance, not via a schema field on WorldEntity v1.
- No `owner_teammate` FK — the Character↔WorldEntity edge model
  (deferred) is the correct home for ownership.
- No `location` / spatial coords — v1 is not geographic.
- No `parent_entity` FK — a bakery inside a mall is a compound
  structure question deferred.
- No `first_referenced_episode` — that's provenance, deferred.

**Absolute v1 minimum: `id`, `universe` FK, `workspace` FK
(denormalized), `name`, `kind` (freeform text), `description`,
`status` (`active`/`archived`), `created_by`, `created_at`,
`updated_at`.** Nothing else.

### Q15. What should explicitly NOT become a WorldEntity? Strong negative boundary.

**Strong negative boundary** so LLMs and operators don't turn every
noun into persistent state:

1. **Characters** — go to Teammate (existing) + CharacterIdentity
   substrate. Non-speaking-but-recurring becomes WorldEntity
   `kind=animal` (or similar) only when explicitly non-speaking;
   a WorldEntity should never gain a voice. Promotion to
   Character is a new Teammate creation, not a WorldEntity
   "upgrade."
2. **Educational subjects / topics / lessons / curricula / learning
   objectives** — deferred EDUCATION slice per §Q9.
3. **Rendered media artifacts** — go to Asset (existing).
   A rendered clip of the coffee shop is an Asset; the coffee shop
   itself is a WorldEntity. Don't conflate.
4. **Portrait normalization backgrounds** — go to
   NormalizationManifest (existing). The five yaml families are
   substrate-scope, not world-scope. Don't extend
   `background_family_v1.yaml` to include operator entities.
5. **Per-render backdrop clips** — go to Asset(role=BACKDROP)
   (existing). The clip that plays behind Patch in Episode C is
   an Asset; if it happens to depict the coffee shop, that's
   operator-discipline convention (or a future WorldEntity↔Asset
   nullable back-ref).
6. **Facts / knowledge / documents** — go to KnowledgeDocument
   (existing). A PDF describing the coffee shop is a
   KnowledgeDocument; the coffee shop is a WorldEntity.
7. **Per-Episode narrative events** — go to the deferred narrative-
   memory substrate. "Rivet warned Patch at the coffee shop" is
   an event, not an entity.
8. **Per-render parameters** (aspect ratio, target duration,
   backdrop prompt) — go to Composition kwargs. Not entities.
9. **Teammate voice/POV/personality fields** — go to Teammate
   (existing, with voice-versioning as a separate deferred slice).
10. **Universe itself** — Universe is the container; WorldEntity
    is a thing within Universe. Do not attempt to model a
    Universe-as-a-WorldEntity self-reference; there is no case for
    it in the operator brief and it invites collapsing distinctions
    that must remain separate.
11. **Relationships between characters** — go to the committed
    Character↔Character Relationship (existing).
12. **Individual props not narratively significant** — remain in
    Episode prose. Promotion only on operator declaration
    (§Q7, T1).
13. **Real-world people, brand names, competitor references** —
    stay in `Teammate.business_brief` / K2 / operator prose. A
    WorldEntity is an in-fictional-world thing; if the operator's
    world IS the real world (business teammate), the "world" is
    thin and WorldEntity usage should be sparse.
14. **CSV recipient rows on PersonalizedCampaign** — go to
    PersonalizedRecipient (existing). Not world entities.

**Rule of thumb**: a WorldEntity is something the operator says
recurs across renders / Episodes as the SAME thing, is not a
character, and is not knowledge or media. The negative list is
larger than the positive definition — deliberately.

### Q16. Who creates/promotes: explicit operator only / auto-inferred from Episodes / LLM suggests → operator approves / auto for certain categories?

**Explicit operator only.** Mirrors UNIVERSE §Q8, EPISODE_LIFECYCLE
§H3, RELATIONSHIP §Isolation invariant 6.

- **No auto-inference from Episode prose.** Even if the same noun
  ("coffee shop") appears in five Episodes' `operator_topic`, no
  WorldEntity is created. The operator has to declare it.
- **No LLM-suggests → operator-approves in v1.** SPA affordances
  for suggesting entities from prose are a v2 concern; v1 is
  operator-authored.
- **No auto-promotion by category.** "Places auto-create; projects
  don't" is exactly the kind of implicit rule that leads to the
  overload UNIVERSE §Q8 rejected.
- **The three-way precedent holds**: Universe explicit (UNIVERSE
  §Q8), Episode explicit (EPISODE_LIFECYCLE §H3), Relationship
  explicit (RELATIONSHIP §Isolation invariant 6), WorldEntity
  explicit (this slice). Every persistent Universe-scoped primitive
  is operator-authored. No exceptions.

### Q17. Rivet spontaneously invents "I moved the power cutoff closer to your desk" — operator loves it. How does that eventually become canon without letting every LLM invention mutate the Universe? Establish OWNERSHIP not UX.

**Ownership answer:**

- The synthesized text lives on Composition (`synthesized_brief`
  per EPISODE_VS_COMPOSITION_V1.md §Q3). This is per-attempt
  content — the LLM output for THIS render.
- **No LLM output ever mutates a WorldEntity row directly.** Same
  discipline as Relationship: "Episode / Composition / synthesis
  MUST NOT mutate a Relationship row" (RELATIONSHIP §Isolation
  invariant 7). Extend to WorldEntity.
- If the operator loves the invention, the path to canon is
  **explicit operator promotion**: the operator navigates to the
  WorldEntity surface (or creates a new WorldEntity "Power Cutoff
  Switch"), types the description, hits save. Nothing about the
  Composition row mutates the WorldEntity.
- **No LLM-suggests → auto-canon.** Same as §Q16.
- Optional v2 UX: the SPA could highlight "Rivet mentioned 'power
  cutoff' in Composition X — promote to WorldEntity?" but this is
  UX sugar, not substrate. The substrate answer is: operator
  declares, WorldEntity row is written.

### Q18. Naming collision map. Take a resolution position.

Restated from the collision-map section above:

- **Two-way today**: `background` (identity substrate) vs
  `backdrop` (composition Asset).
- **Three-way if `Location` lands** in W2 or as a `kind=place`
  WorldEntity in W3/W4.

**Position (three-part):**

1. **Do NOT rename `background` or `backdrop`.** They are load-
   bearing in-code names with tests, migrations, and consumer
   code paths (`normalization/stages/background_replacement.py`;
   `composite_video.py:_VALID_LAYOUT_KINDS`; recipe kwargs; asset
   role enum). Renaming either is a defense-in-depth risk with
   near-zero semantic gain.
2. **Do NOT call the new primitive `Location`.** `Location` is
   spatially specific and would collide with the operator's
   mental model of "backdrop" AND with the identity substrate's
   "background." Instead, **use `WorldEntity`** as the primitive
   name — its generality (place / business / project / prop /
   animal / landmark) makes the collision less severe and its
   generality is warranted by the stress-test matrix.
3. **Do NOT reuse `Environment`.** The dormant
   `IdentityReferenceKind.ENVIRONMENT_REFERENCE` enum value
   (`identity/models.py:359`) already claims the word in the
   identity substrate, and its dormancy is a hazard — reactivating
   it under a new semantic (world-entity environment) would
   confuse whether it's an identity-substrate reference or a
   Universe-scoped entity.

**Resolution outcome:**

- `background` → identity substrate; unchanged.
- `backdrop` → composition Asset; unchanged.
- `environment` → dormant identity enum; leave dormant, or when it
  activates, keep its scope narrowly to "portrait environment"
  and never let it drift to "world environment."
- `WorldEntity.kind='place'` → the new operator-facing "location"
  concept. Operator UX may label it "Place" in the SPA; the
  substrate name stays `WorldEntity`.

**Three-way collision is contained** by naming the new primitive
`WorldEntity` (kind=place), not `Location` — the operator-facing
name for a Place row is "Place" (or "Location" in SPA copy), but
the substrate is `WorldEntity`, so grep across code stays
unambiguous.

### Q19. Semantic home: Universe / memory / identity / new substrate?

**Semantic home: Universe.** WorldEntity is Universe-scoped
by construction (mirrors Episode, mirrors Relationship). It is
not identity-substrate (identity is per-character-version), not
memory-substrate (memory events reference entities but don't own
them), not workspace-substrate (workspace is tenant, not world).

**App-name decision deferred** per the RELATIONSHIP §Q8 pattern.
Candidates: extend `apps/universe` (if that app materializes to
host Universe / Episode / Relationship together), extend
`apps/memory` (if continuity substrate consolidates), or a new
`apps/entities` (if per-substrate app separation is preferred).
This slice takes no position — schema/app decisions are downstream.

### Q20. Sequencing: does introducing WorldEntity NOW simplify upcoming Relationship implementation, or is it orthogonal enough that Relationship should land first?

**Position: Relationship lands first. WorldEntity lands second.
Character↔WorldEntity edges land third.**

Reasoning:

- Relationship v1 (RELATIONSHIP_BOUNDARY_V1.md §Q12) is
  fully specified without WorldEntity. Its row shape (`teammate_a`,
  `teammate_b`, `type`, ...) has no WorldEntity dependency. It
  ships standalone.
- WorldEntity v1 (this slice) is fully specified without
  Character↔WorldEntity edges. Its row shape (`name`, `kind`,
  `description`, ...) plus `Episode.referenced_entities` M2M covers
  the load-bearing continuity cases (Episode C, D). It ships
  standalone.
- Character↔WorldEntity edges (Ruby→owns→Bakery, Patch→works_at→
  Workshop) are the third slice. They require both Relationship
  and WorldEntity to exist and stable, and they introduce a new
  edge model that will look SIMILAR to Relationship but is not
  the same. Landing them third avoids the temptation to reshape
  Relationship to be polymorphic.
- If WorldEntity landed FIRST, it would sit unused (nothing
  references it) or force the edge model to land simultaneously.
- If WorldEntity landed with edges, RELATIONSHIP's committed
  invariants (self-loop rejected, normalized ordering, direction)
  would be under pressure to generalize prematurely.

**Sequencing verdict: Relationship (committed) → WorldEntity (this
slice) → Character↔WorldEntity edges (deferred).**

## Recommended boundary

**Chosen: W4 — WorldEntity base + specialized future extensions.**

**Load-bearing reason.** W4 addresses the load-bearing continuity
gap (Episodes C, D where a coffee shop's identity must survive its
owner-character's absence) with **one new primitive** — a Universe-
scoped row with name, kind (hint), description, status. No
specialized sub-models forced in v1. The `kind` field is a hint,
not a load-bearing discriminator, so it doesn't force operator UX
to disambiguate place-vs-business-vs-project on every entity
creation. Sidecar models (BusinessDetails, ProjectDetails,
LocationCoordinates) attach only when concrete operator need
surfaces — never speculatively.

**Rejected:**

- **W1 (no WorldEntity)** fails Episodes C, D on continuity. The
  coffee shop's identity depends on operator-discipline backdrop
  reuse and character-cast intersection to Mason — the latter
  breaks when neither Mason nor Patch is in the cast (Episode D:
  Ruby visits). This is the load-bearing failure mode of W1.
- **W2 (specialized models)** forces multiple new primitives
  (Business, Location, Project, Prop, Animal, Landmark) up-front
  with distinct schemas, distinct edge models, and distinct
  operator surfaces. High ceremony cost for a Universe with three
  or four persistent things. Also: forces up-front operator
  choice ("is Bakery a Business or a Location?") that the stress
  test proves is unnecessary at v1.
- **W3 (generic WorldEntity with kind discriminator)** would be
  chosen except that a load-bearing `kind` enum invites the
  educational-subject-absorption failure (§Q9 T3) and forces
  operator disambiguation on every creation. W4 differs from W3
  by treating `kind` as a hint (freeform text) and reserving
  specialization to sidecar models. In practice W3 and W4 look
  similar day-one; W4 preserves the option to specialize later
  without a schema reshape.

## Minimum v1 responsibility

WorldEntity v1 must own exactly these things and nothing more:

- **Identity** — name (short string, operator-authored), kind
  (freeform text hint), description (freeform text), status
  (`active` / `archived`).
- **Universe parent** — FK → Universe, NOT NULL, CASCADE.
- **Workspace denormalization** — FK → Workspace, NOT NULL,
  `== universe.workspace`, for defense-in-depth per UNIVERSE
  §Isolation invariants.
- **Authorship trail** — `created_by`, `created_at`, `updated_at`.
- **Nothing else.** No metadata JSON, no slug, no canonical Asset
  FK, no owner Teammate FK, no location coords, no parent-entity
  FK, no first-referenced-Episode.

Additional v1 responsibility on **Episode** (touching the prior
slice, not reshaping):

- **`Episode.referenced_entities` M2M** → WorldEntity. May be
  empty. Cross-Universe attach rejected at `clean()` /
  `m2m_changed pre_add` per the UNIVERSE / RELATIONSHIP pattern.

## Explicit negative boundary — what is NOT a WorldEntity

Restated as a list; each item is enforced by the operator, the
SPA, and (where applicable) documentation.

1. Characters (go to Teammate + CharacterIdentity).
2. Educational subjects / topics / lessons / curricula / learning
   objectives (deferred EDUCATION slice; not v1 WorldEntity).
3. Rendered media artifacts (go to Asset).
4. Portrait normalization backgrounds (go to NormalizationManifest).
5. Per-render backdrop clips (go to Asset(role=BACKDROP)).
6. Facts / knowledge / documents (go to KnowledgeDocument).
7. Per-Episode narrative events (go to deferred narrative-memory
   substrate).
8. Per-render parameters (go to Composition kwargs).
9. Teammate voice / POV / personality fields.
10. Universe itself.
11. Character↔Character Relationships.
12. Individual props not narratively significant (remain in
    Episode prose; promotion only on operator declaration).
13. Real-world people, brand names, competitor references (stay
    in business_brief / K2).
14. CSV recipient rows on PersonalizedCampaign.

**The negative list is deliberately larger than the positive
definition.**

## Character vs WorldEntity distinction

| Axis | Character (Teammate) | WorldEntity |
|---|---|---|
| Speaks? | YES (voice, K2, personality, POV, Runway avatar) | NO |
| Has an identity substrate version lifecycle? | YES (CharacterIdentity + version + spec + references + bundle) | NO |
| Belongs to which container? | Workspace + Universe (nullable, legacy) | Universe (NOT NULL) |
| Rendered by primitives? | YES (avatar_speech, portrait, etc.) | NO (rendered scenes may DEPICT it via Asset, but WorldEntity doesn't own render) |
| Casted into Episodes? | Episode.cast M2M | Episode.referenced_entities M2M (different M2M) |
| Participates in Character↔Character Relationship? | YES (RELATIONSHIP committed) | NO |
| Participates in Character↔WorldEntity edges? | YES (deferred, this slice does not create) | YES (deferred) |
| Auto-created by any code path? | NO (RELATIONSHIP §Isolation invariant 6, EPISODE_LIFECYCLE §H3) | NO (same principle extended) |
| Legacy pre-Universe rows exist? | YES (Mike, Repo Red, Tulsi) | NO (this is a v1 primitive; no legacy) |
| Promotion path from prose? | New Teammate creation | New WorldEntity creation |
| Promotion path between them? | **NONE. WorldEntity cannot become a Character; Character cannot become a WorldEntity.** Each is a new creation. | Same. |

**Load-bearing distinction**: Character speaks, WorldEntity does
not. If the operator wants the coffee shop to have a voice
("welcome to the coffee shop!"), that's a Character (Barista) —
not a WorldEntity that gained a voice. No path exists (and none
should) to upgrade a WorldEntity to a Character.

## Relationship vs WorldEntity-edge distinction

| Axis | Character↔Character Relationship (committed) | Character↔WorldEntity edge (deferred) | WorldEntity↔WorldEntity edge (deferred) |
|---|---|---|---|
| Endpoints | Both Teammate FKs | Teammate FK + WorldEntity FK | Both WorldEntity FKs |
| Row shape | `teammate_a`, `teammate_b`, `type`, `type_reverse`, `status`, `notes` (RELATIONSHIP §Q12) | Different shape (Teammate + WorldEntity + role) | Different shape |
| Model | Relationship (committed) | New model when it lands (RELATIONSHIP §Q10 named the dependency) | New model when it lands |
| Universe-scoped? | YES | YES | YES |
| Cross-Universe forbidden? | YES (RELATIONSHIP §Isolation invariant 2) | YES | YES |
| v1 status | Committed | Deferred to post-WorldEntity slice | Deferred |

**Do not reshape Relationship to be polymorphic on endpoints.**
Its committed row shape is Teammate-typed; changing that breaks
its invariants (self-loop rejected, normalized ordering, direction
via paired type fields). Character↔WorldEntity edges are a NEW
model.

## Knowledge vs WorldEntity distinction (knowledge may describe; knowledge must not constitute)

| Axis | KnowledgeDocument | WorldEntity |
|---|---|---|
| What is it? | Factual corpus (PDF, URL, prose) ingested and embedded | Addressable named thing in the Universe |
| Scope | Workspace + Universe (nullable, legacy) per UNIVERSE §Q9 | Universe (NOT NULL) |
| Purpose | Retrieved into synthesis prompts to ground character claims | Referenced by Episodes to preserve continuity across renders |
| Can be about the same thing? | YES — a K2 doc can describe a WorldEntity | YES — the WorldEntity IS the thing |
| Does one imply the other? | NO — a WorldEntity can exist without any K2 doc; a K2 doc doesn't create a WorldEntity | NO — creating a WorldEntity doesn't create a K2 doc |
| Deletion behavior | Deleting K2 doc: WorldEntity persists (description on the row remains) | Deleting WorldEntity: K2 docs about it survive (they're about the concept, not FK-bound) |
| Which is the source of truth for "the coffee shop is at Main and 5th"? | K2 doc (factual detail) | WorldEntity.description ("Mason's Coffee Shop, on Main St.") — short canonical description |

**Load-bearing rule**: knowledge may describe; knowledge must not
constitute. If the K2 doc "About the Coffee Shop" is deleted, the
coffee shop persists (via WorldEntity row). If the WorldEntity is
deleted, the K2 doc still exists but no longer has an anchor —
which is by design; the operator has to explicitly re-anchor or
delete the doc.

## Episode interaction

- **`Episode.referenced_entities` M2M → WorldEntity.** New M2M on
  Episode. May be empty. Operator-authored. Cross-Universe attach
  rejected at `clean()` / `m2m_changed pre_add`.
- **Universe-consistency invariant**: every WorldEntity in
  `Episode.referenced_entities` has `world_entity.universe ==
  episode.universe`. Same shape as `Episode.cast[*].universe ==
  episode.universe` (EPISODE_LIFECYCLE §Constraint invariants).
- **Not required for Episode existence**: an Episode with empty
  `referenced_entities` is legal — it's the common case (talking-
  head Episode with no world entities to reference).
- **Retrieval into synthesis**: at synthesis time, the context-
  assembly step loads each referenced WorldEntity's `name`,
  `kind`, `description` verbatim into the prompt. Same shape as
  Relationship's off-screen surfacing (RELATIONSHIP §Off-screen
  relevance mechanism), one primitive over.
- **Composition inherits transitively**: a Composition attached to
  an Episode transitively acquires the Episode's
  `referenced_entities` for synthesis. Composition itself gains
  no FK to WorldEntity.
- **Legacy Episode-less Compositions**: continue to have no
  WorldEntity linkage. Correct.

## Off-screen entity relevance mechanism (Episode B)

**Episode B**: Patch + Rivet in the workshop discussing the AI
Agent Project. Mason NOT in cast. Coffee shop NOT the location.
But Mason, project, coffee shop remain narratively relevant.

**v1 mechanism (this slice ships):**

1. Operator authors Episode B with:
   - `cast = {Patch, Rivet}`
   - `referenced_entities = [AI Agent Project, Mason's Coffee Shop]`
     (operator-declared)
2. Synthesis context assembly loads:
   - Cast members' identities (Patch, Rivet)
   - **Cast-intersection Relationships** (per RELATIONSHIP §Off-
     screen relevance): Patch↔Rivet + Patch↔Mason (Mason in the
     `teammate_a`/`teammate_b` even though not in cast)
   - **Referenced WorldEntities**: AI Agent Project + Mason's Coffee
     Shop, each with `name` / `kind` / `description` surfaced to
     the prompt
3. Prompt receives: "Patch's relationships: Rivet (partners); Mason
   (client, notes: 'building AI agent for coffee shop'). Referenced
   entities: AI Agent Project (project, 'the AI agent Patch is
   building for Mason's coffee shop, started Episode A'); Mason's
   Coffee Shop (place, 'Mason's coffee shop on Main St.')."

**Post-edge-model (deferred slice):**

- Character↔WorldEntity edges add automatic loading of entities
  attached to cast members even if the operator forgot to
  populate `referenced_entities`. Belt and suspenders.

**v1 is sufficient** for Episode B because the operator's authored
M2M carries the reference. The edge model adds robustness but is
not load-bearing.

## Canon / promotion ownership (Q16, Q17)

- **Explicit operator declaration.** Same as Universe, Episode,
  Relationship.
- **No auto-inference from prose.** Recurrence in `operator_topic`
  does not mint a WorldEntity.
- **No LLM-suggests → auto-canon.** SPA affordances for suggestions
  are v2 UX; v1 substrate is operator-authored.
- **LLM output NEVER mutates a WorldEntity row.** Same discipline
  as Relationship (RELATIONSHIP §Isolation invariant 7).
- **Promotion between primitives is explicit or forbidden:**
  - Character → WorldEntity: **forbidden** (a character does not
    demote to a WorldEntity; the character continues to exist).
  - WorldEntity → Character: **forbidden** (a coffee shop does not
    gain a voice; a Barista does — new Teammate).
  - WorldEntity → Knowledge: not a promotion; a K2 doc about the
    entity is a separate operator gesture.
  - Prose in Composition/Episode → WorldEntity: explicit operator
    gesture ("this recurring thing deserves a row").

## Legacy implications

- **No legacy WorldEntities.** This is a v1 primitive; no rows
  exist before it lands. No migration is required.
- **Legacy Teammates (Mike, Repo Red, Tulsi) with `universe=NULL`
  cannot reference WorldEntities.** There is no Universe to scope
  the entity to. Their historical talking-head cadence is
  unchanged; WorldEntity substrate silently ignores them.
- **Legacy Compositions (81 in `chriss-workspace`) with
  `episode=NULL` do not reference WorldEntities.** Their prose
  history is intact; no retro-attach.
- **Legacy K2 docs (14 in `chriss-workspace`) with `universe=NULL`
  continue to serve legacy Teammates under workspace-wide empty-
  M2M semantics** (UNIVERSE §Q9). Universe-scoped teammates never
  see them; WorldEntity doesn't touch them.
- **Migration path**: if the operator ever wants a legacy Teammate
  to have WorldEntities associated, they first migrate the Teammate
  to a Universe (bespoke ½-slice per UNIVERSE §Q6), then create
  WorldEntities in that Universe. Bulk migration remains rejected.

## Sequencing recommendation (Q20)

**Relationship (committed) → WorldEntity (this slice) → Character↔
WorldEntity edges (deferred slice).**

Reasoning: Relationship is fully specified without WorldEntity;
WorldEntity is fully specified without edges; edges require both
to exist. Reversing any order forces a primitive to sit unused or
forces a schema reshape mid-slice. See §Q20 above.

## Isolation invariants

1. **Workspace privacy invariant (existing, extended).** No
   WorldEntity row crosses Workspace boundaries. Enforced via
   `WorldEntity.workspace == WorldEntity.universe.workspace`.
2. **Universe privacy invariant (existing, extended).** No
   WorldEntity row crosses Universe boundaries. Enforced via
   `WorldEntity.universe` being its primary scope.
3. **Legacy isolation invariant (existing, extended).** Teammates
   with `universe=NULL` cannot reference WorldEntities (there is
   no Universe to scope the entity to). Same shape as
   RELATIONSHIP §Isolation invariant 3.
4. **Episode-entity Universe consistency (new).** Every WorldEntity
   in `Episode.referenced_entities` M2M has `world_entity.universe
   == episode.universe`. Cross-Universe attach rejected at
   `clean()` / `m2m_changed pre_add`.
5. **No implicit creation.** WorldEntity rows are created ONLY by
   explicit operator action. Episode creation, Composition creation,
   synthesis, cast mutation, retrieval, and prose parsing MUST NOT
   create WorldEntity rows. Same discipline as RELATIONSHIP §Isolation
   invariant 6 and EPISODE_LIFECYCLE §H3.
6. **No implicit mutation.** WorldEntity `name` / `kind` /
   `description` / `status` change ONLY by explicit operator edit.
   Episode / Composition / synthesis / rerender / LLM output MUST
   NOT mutate a WorldEntity row. Same discipline as RELATIONSHIP
   §Isolation invariant 7.
7. **Name uniqueness within Universe (v1 default).** `(universe,
   name)` unique — matches the Teammate `(workspace, name)`
   pattern (`spokespeople/models.py:334`). Deferred to schema
   slice, but the semantic invariant is stated here.
8. **No self-referential WorldEntity FKs.** No `parent_entity` FK
   in v1. Compound structures (a bakery inside a mall) are
   deferred.
9. **No cross-primitive polymorphism.** WorldEntity is a distinct
   primitive; it is not a subtype of Teammate, Asset, or
   KnowledgeDocument. Relationship endpoints stay Teammate-typed;
   WorldEntity endpoints (edge model) are a NEW model.
10. **No implicit cross-Universe crossover.** Same as UNIVERSE §Isolation
    invariant 5. If cross-Universe entity sharing ever needs to
    exist (a landmark referenced across worlds), it is an explicit
    primitive with its own name and audit trail — not a nullable
    Universe FK or a bypass.

## Corrections to prior reports

**Two minor corrections and one confirmation:**

1. **RELATIONSHIP_BOUNDARY_V1.md §Q10 sub-slice** stated the v1
   answer for Ruby-owns-Bakery is `Ruby.business_brief`. **This
   slice preserves that as the v1 answer for the FACT of
   ownership, but adds:** the Bakery-as-an-entity gains a
   WorldEntity row when the operator declares narrative
   significance beyond Ruby's own business_brief. The two are
   compatible — the fact stays on Ruby (character-owned), the
   entity is separately addressable (WorldEntity). The
   Character↔WorldEntity edge (Ruby→owns→Bakery) is still deferred
   past this slice. **No contradiction; refinement.**

2. **RELATIONSHIP_BOUNDARY_V1.md §Q10 sub-slice** stated
   "WorldEntity slice, when it lands, will introduce
   Character↔Location and Character↔Organization edges as new
   models — NOT by reshaping Relationship." **This slice preserves
   that principle** (Character↔WorldEntity edges are a new model,
   Relationship is not reshaped) **but defers the edge model itself
   to a later slice**, not concurrent with WorldEntity. Sequencing
   is Relationship → WorldEntity → edges. **Refinement to the
   deferral scope; no contradiction on the model boundary.**

3. **CAPABILITY_INVENTORY_SESSION_261.md §12 "Location / Scene /
   Set / Stage / Room"** listed no substrate for a "location"
   concept and named this as absent. **This slice confirms the
   audit finding** and specifies the primitive: `WorldEntity` with
   `kind` freeform text hint. The audit's naming warning
   ("three-way collision if Location lands") is addressed by naming
   the primitive `WorldEntity`, not `Location` — the collision is
   contained in the operator-facing SPA label ("Place"), not in
   the substrate class name.

**No prior slice is contradicted.** All three are refined or
confirmed.

## Unresolved questions

New questions this slice creates or leaves open:

1. **App-name / home for WorldEntity.** `apps/entities`,
   `apps/universe` (implying Universe / Episode / Relationship /
   WorldEntity share a home), or extend the dormant `apps/memory`?
   Schema slice.
2. **`WorldEntity.kind` vocabulary conventions.** Freeform text in
   v1 (§Q14); consider bootstrapping observed operator vocabulary
   in v2. UX slice.
3. **Uniqueness of `(universe, name)` — case-insensitive?** Match
   Teammate's `(workspace, name)` convention or diverge? Schema
   slice.
4. **Cascade policy on Universe delete.** CASCADE is natural
   (entities within a deleted world are meaningless). Schema slice.
5. **Cascade policy on WorldEntity delete when it's in
   `Episode.referenced_entities`.** SET_NULL from the M2M row (the
   entity is deleted; the Episode's reference goes away) or PROTECT
   (deletion of a referenced entity requires manual detach first)?
   Position: SET_NULL from the M2M through-table only (the
   through-row is removed; the Episode survives). Schema slice.
6. **Character↔WorldEntity edge model.** Row shape, direction,
   type vocabulary, and interaction with the committed
   Character↔Character Relationship. Deferred slice.
7. **WorldEntity↔WorldEntity edge model.** Same, further deferred.
8. **WorldEntity↔Asset back-ref for scene-picker UX.** If the
   operator wants "when I pick a backdrop, show me the WorldEntities
   this Asset has depicted," a nullable back-ref is needed. UX +
   schema slice.
9. **SPA affordance for creating a WorldEntity.** Where in the
   SPA does the operator create/edit WorldEntities? Under Universe?
   Inline in Episode authoring? UX slice.
10. **Prompt formatting of WorldEntity context in synthesis.** How
    does K6 render the entity row into the prompt? Structured list
    vs freeform prose vs XML fence? K6 contract slice.
11. **Educational subject / topic substrate.** Explicitly outside
    WorldEntity per §Q9; needs its own EDUCATION slice.
12. **Off-screen entity relevance loading limit.** If Episode B
    references 47 entities, do all 47 load into synthesis? v1
    position: yes; pagination / relevance-scoring is a future
    performance concern.
13. **Auto-populating `Episode.referenced_entities` from cast's
    Character↔WorldEntity edges.** Deferred to edge-model slice.
14. **Promotion of a Composition-mentioned entity to WorldEntity via
    SPA suggestion.** UX v2.
15. **Sidecar models** (BusinessDetails, ProjectDetails, ...) —
    what triggers their creation? Concrete operator need only.
16. **Multi-Universe sharing** (a real-world landmark like "the
    Grand Canyon" referenced by many Universes) — explicit
    cross-Universe primitive if ever needed. Deferred; likely
    never in v1 product scope.
17. **`WorldEntity.status = 'archived'` interaction with existing
    `Episode.referenced_entities` M2Ms.** Does an archived entity
    remain referenced by past Episodes? Position: yes; the M2M
    persists as historical reference. Schema slice confirms.

## Risks if boundary is wrong

1. **Auto-creating WorldEntities from Episode prose.** Recurrence
   of the same noun ("coffee shop") across Episodes mints a
   WorldEntity silently. Row count balloons; operator drowns in
   entities they didn't author. Same overload UNIVERSE §Q8 rejected.
2. **LLM-generates → auto-canon.** Any path that lets synthesis
   output mutate a WorldEntity row corrupts canon. Same class as
   RELATIONSHIP §Isolation invariant 7.
3. **Absorbing educational subjects into WorldEntity.** Overloads
   the primitive; conflates "what recurs in the world" with "what
   the story teaches." EDUCATION slice becomes harder to design
   because the naming space is already claimed. §Q9 T3 explicit.
4. **Reshaping Character↔Character Relationship to be
   polymorphic** (accepting WorldEntity endpoints). Breaks the
   committed row invariants (self-loop, normalized ordering,
   direction). §Q10.
5. **Character↔WorldEntity conflated with WorldEntity↔WorldEntity.**
   One edge model that accepts either Teammate or WorldEntity on
   either endpoint invites the same polymorphism trap. Two
   separate models when each edge type is needed.
6. **Naming the primitive `Location` instead of `WorldEntity`.**
   Amplifies the three-way `background`/`backdrop`/`environment`
   collision. §Q18.
7. **JSON metadata field on WorldEntity.** Becomes a swamp; every
   entity accretes ad-hoc JSON that the SPA has to render; semantic
   ownership blurs. §Q14 explicitly excluded.
8. **Cross-Universe entity sharing** without an explicit primitive.
   Same class as RELATIONSHIP §Isolation invariant 10.
9. **Promoting WorldEntity to Character.** Adds voice / K2 / avatar
   to what was declared as non-speaking; loses the semantic
   distinction that WorldEntity establishes. Correct path: new
   Teammate creation.
10. **Legacy Teammates gaining WorldEntity access.** Legacy
    Teammates with `universe=NULL` have no Universe to scope
    entities to; silent gap that violates isolation. Mirrors
    RELATIONSHIP §Legacy behavior. Explicitly forbidden.
11. **Requiring `Episode.referenced_entities` to be populated at
    Episode create.** Overloads the "New Episode" affordance
    identically to how EPISODE_LIFECYCLE §Q7 challenged the
    cast requirement. Empty is legal.
12. **Coupling WorldEntity identity to a specific Asset.** Freezes
    the entity's visual representation; violates the audit's
    finding that "identity and backdrop are independent axes"
    (CAPABILITY_INVENTORY_SESSION_261.md §12 special question 4).
13. **Introducing WorldEntity before Relationship ships.** WorldEntity
    is used by Episode.referenced_entities; without Relationship,
    off-screen character relevance is broken. Sequencing matters.

## STOP

Research only. No schema. No migrations. No code. Every load-
bearing claim is cited to `CAPABILITY_INVENTORY_SESSION_261.md`,
`UNIVERSE_BOUNDARY_V1.md`, `EPISODE_VS_COMPOSITION_V1.md`,
`EPISODE_LIFECYCLE_V1.md`, `RELATIONSHIP_BOUNDARY_V1.md`, or a
file:line in `shell/apps/`.
