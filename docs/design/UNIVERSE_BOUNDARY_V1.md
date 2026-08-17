---
title: "Universe Boundary v1 — Semantic Layer Between Workspace and World"
status: design — boundary definition only (no schema, no code, no migrations)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "handoffs/SESSION_259_WORKSPACE_AUDIT.md"
  - "design/KNOWLEDGE_LAYER.md"
  - "design/WORKSPACE_FABRIC_V1.md"
scope: >
  Define the semantic boundary between Workspace and a proposed Universe
  layer. Take positions where the working hypothesis is weak. Do NOT
  design relationships, memory, locations, episodes, or cast in detail;
  identify only how they would attach relative to Workspace vs Universe.
---

# Universe Boundary v1 — Semantic Layer Between Workspace and World

## Purpose

The SESSION 259 workspace audit and the SESSION 261 capability inventory
converged on the same finding: `Workspace` today silently carries four
meanings — **tenant**, **universe**, **project**, and **studio** — and
the operator has never had a UI-level way to construct additional
workspaces or to scope knowledge below the workspace level. As a
result, seven teammates spanning at least four unrelated fictional
worlds (Patch/Rivet workshop, Riverstone Outdoor Adventures, Surgo
Automotive, Hearth & Hollow bookstore, plus Tulsi) cohabit
`chriss-workspace` and all six workspace-wide K2 docs are cosine-
retrievable to every dialogue synthesis call regardless of world
membership (CAPABILITY_INVENTORY_SESSION_261.md §6, §7, §17;
SESSION_259_WORKSPACE_AUDIT.md §3, §6).

This document defines exactly one thing: **what the semantic boundary
should be between Workspace and a new Universe layer**. It answers
which existing responsibilities stay on Workspace, which move
conceptually to Universe, and where every existing model would attach
under the recommended boundary. It does NOT design relationships,
memory, locations, episodes, or cast internals — those are downstream
slices, and this doc only identifies their conceptual attachment point.

## Scope of this slice (and what's explicitly deferred)

**In scope.**

- The semantic boundary between Workspace (tenant / ownership /
  security) and Universe (persistent creative world).
- Which existing model classes retain a Workspace FK, which would
  eventually need Universe awareness, and which should not gain either.
- Legacy-data behavior — can Universe be introduced prospectively
  without immediately migrating the 7 teammates / 14 docs / 81
  compositions / 322 assets currently in `chriss-workspace`.
- Isolation invariants that must survive the introduction of Universe.
- Take a position on the "default Universe per Workspace" question.
- Take a position on empty-M2M semantics under Universe.

**Explicitly deferred to later slices.**

- Any schema DDL, migration plan, or Django field addition.
- Relationship substrate design (character-to-character edges).
- Persistent narrative memory design.
- Location / Scene / Set entity design.
- Cast / Ensemble grouping design.
- Composition → Episode promotion or wrapping design.
- Voice / POV versioning strategy.
- Non-human canonical identity via Character Presence Language.
- Backdrop naming disambiguation between
  `NormalizationManifest.background_id` and `Asset(role=BACKDROP)`.
- SPA UX for Universe picking, creating, switching.
- Slug uniqueness reform (currently global on Workspace; wart flagged
  in SESSION_259_WORKSPACE_AUDIT.md §8).

Each deferred item is called out in "Unresolved questions" at the end.

## Working hypothesis

Restated for the record:

1. Workspace remains the tenant / ownership / security boundary.
2. Universe becomes a child of Workspace and represents one persistent
   creative world.
3. A Workspace may contain many Universes.
4. Characters, canon, relationships, locations, episodes, and shared
   world knowledge belong to a Universe.
5. Cross-Universe access must never occur implicitly.
6. Workspace-wide knowledge should NOT automatically become Universe
   knowledge.

## Evaluation against current architecture

The hypothesis is **substantially correct with three important
corrections**. Answers to Q1–Q13 below establish where it holds and
where it needs adjustment.

### Q1. What responsibilities does Workspace carry today?

Concrete, cited from `accounts/models.py:108–188` and every model FK
site enumerated in SESSION_259_WORKSPACE_AUDIT.md §1:

- **Ownership.** `Workspace.owner` FK → User (PROTECT). One user owns
  a workspace. Deletion of the owner is refused (`accounts/models.py:118`).
- **Multi-user membership.** `Membership` M2M-through with `Role` enum
  `OWNER|ADMIN|EDITOR|VIEWER` (`accounts/models.py:145–163`). Only
  `OWNER` is used in v1 by policy; the rest are scaffolding.
- **Slug identity.** Globally unique 140-char slug for URL routing
  (`accounts/models.py:113`, `133–142`). Wart flagged in the audit.
- **Tenant-scope security boundary.** Every content model FKs
  Workspace with `NOT NULL` + `CASCADE` and is filtered by
  `IsWorkspaceMember` (`character_os/permissions.py:18–64`) which
  restricts every viewset queryset to
  `workspace__memberships__user=user`.
- **Cross-workspace isolation enforcement.** Defense-in-depth: (a)
  `KnowledgeDocument.clean()` (`embeddings/models.py:230–245`); (b)
  `apps/embeddings/signals.py:31–79` `m2m_changed pre_add` on
  spokespeople; (c) `retrieve_for_teammate` derives workspace from
  `spokesperson.workspace` with no override
  (`embeddings/retrieval.py:150–197`); (d) `Composition.clean()`,
  `Script.clean()`, `Asset` and `PersonalizedCampaign` clean paths all
  reject cross-workspace pairings; (e) `IdentityReference.clean()`
  (`identity/models.py:476–494`).
- **Knowledge-visibility default.** Empty
  `KnowledgeDocument.spokespeople` M2M means "visible to every
  teammate in this workspace" — a workspace-wide default (`embeddings/
  retrieval.py:182–197`, SESSION_259_WORKSPACE_AUDIT.md §4).
- **Dedup namespace.** `KnowledgeDocument` unique on
  `(workspace, content_hash)` (`embeddings/models.py:216`).
- **Naming uniqueness namespace.** `Teammate` unique on
  `(workspace, name)` (`spokespeople/models.py:334`).
- **Composition / script / campaign roll-up.** Every render
  provenance row FKs Workspace with CASCADE.
- **Asset library.** Every generated media artifact FKs Workspace
  (`compositions/models.py:152–156`).
- **Realtime session / engine connection.** Session provenance FKs
  Workspace (`realtime/models.py:66–70`, `336–…`).
- **Billing anchor (implicit).** `apps/billing` models attach at
  workspace level (per audit §7 shorthand).
- **Character identity substrate scope.** `CharacterIdentity`,
  `CharacterIdentityVersion`, `GenerationRecord`,
  `NormalizationManifest`, `IdentityReference`,
  `ApprovedRepresentationBundle` all FK Workspace (`identity/
  models.py:111–115` and throughout).

The audit's table §1 enumerates this comprehensively; every model
listed in "Workspace-scoped resources" is carrying one or more of the
duties above.

### Q2. Which of those responsibilities should remain on Workspace permanently?

**Tenant / ownership / security duties stay on Workspace forever.**
Specifically:

- Ownership (`owner` FK).
- Membership / roles (multi-user seat model).
- Slug identity for URL routing (with the caveat that per-owner slug
  scoping is a good idea if multi-workspace-per-user ever ships).
- Billing anchor.
- Engine connection / provider credentials (an Engine connection is a
  tenant-billing concern, not a world concern).
- The **cross-tenant privacy boundary invariant** — no data crosses
  Workspace boundaries under any circumstance.
- Asset workspace-scoping (a rendered pixel or audio blob is still a
  tenant asset even if it depicts world content).
- The dedup namespace for KnowledgeDocument content_hash (dedup is a
  storage / cost concern, not a world concern; the same document
  ingested twice by the same tenant is still one document, even if it
  ends up used by two Universes).

### Q3. Which are actually creative-world / project responsibilities that should move conceptually to Universe?

- **Cast membership.** The set of teammates that "belong to this
  world" — currently expressed as "every teammate in the workspace,"
  which is exactly the failure mode motivating this doc.
- **Canon knowledge scope.** Which K2 docs the characters in this
  world may retrieve from. Today this is "every workspace-wide doc
  plus any doc attached via M2M," which is the mechanism through
  which Patch/Rivet dialogue synthesis can retrieve TANK, Tulsi, or
  bookstore chunks (audit §6).
- **Character-to-character relationships** (when they arrive) — Patch
  created Rivet, Mike hired Repo Red, Penny mentors Ruby. These are
  world facts, not tenant facts.
- **Locations / recurring places** (when they arrive) — the workshop
  is a workshop-world thing, not a tenant thing.
- **Cast / ensemble grouping** (when it arrives) — Patch + Rivet as
  a recurring pair, distinct from Mike + Repo Red as a different
  recurring pair, distinct from Penny solo.
- **Persistent narrative memory** (when it arrives) — "Rivet warned
  Patch three episodes ago" is a world event, not a tenant event.
- **Episodes / cross-composition narrative linkage** (when it arrives)
  — an arc groups renders inside one world, not across tenants.
- **In-world entity catalog** (when it arrives) — Rivet's wrench,
  Patch's workbench, Surgo's dealership lot. World objects, not
  tenant objects.
- **World-level style / palette identity** (when brand ecosystem
  extends this way) — the visual identity of the world (color palette
  via CSS-var brand swap, per `feedback_css_var_brand_swap.md`) is
  currently a tenant concern via workspace theming; conceptually the
  "look and feel" of Hearth & Hollow bookstore is a world concern
  that should be able to differ from Surgo Automotive without
  requiring a second tenant.

### Q4. Which existing models currently point directly to Workspace and would eventually need Universe awareness?

These carry FK sites that are **candidates for Universe scoping** in
some future slice. Listed with file:line of the current Workspace FK:

- `Teammate` — `spokespeople/models.py:65–69`. A teammate is a
  character; characters belong to a world.
- `CharacterIdentity` — `identity/models.py:111–115`. Identity is a
  world-level canonical record.
- `KnowledgeDocument` — `embeddings/models.py:124–128`. Canon
  knowledge is world-scoped.
- `Composition` — `compositions/models.py:380–384`. A rendered scene
  belongs to a world.
- `Script` — `scripts/models.py:83–87`. A written script belongs to
  a world.
- `PersonalizedCampaign` — `campaigns/models.py:77–81`. A campaign
  targeting real people using a world's spokesperson belongs to a
  world.
- `PublishBundle` — `publish/models.py:69–73`. A publish bundle
  belongs to a world (though the underlying source clip is a tenant
  asset — see Q5).
- `ConversationThread` — `conversations/models.py`. A conversation
  with a character belongs to that character's world.
- `RealtimeSession` — `realtime/models.py:66–70`. A live session with
  a character belongs to that character's world.
- `TranscriptHighlight` — `transcripts/models.py:75–79`. Derived from
  a world's session.
- Future: `Relationship`, `Location`, `Cast`, `Episode`, `Memory`,
  `WorldEntity`, `WorldPalette` (none exist yet; all should attach at
  Universe, never at Workspace).

### Q5. Which models should NOT gain Universe FKs because Workspace scope alone is still correct?

- `Membership` — a seat is a tenant relationship, not a world
  relationship. A viewer added to the workspace can see all worlds
  the workspace owns (subject to role); we are not designing
  per-Universe ACLs in v1.
- `Asset` — an asset is a pixel/audio blob. It's a tenant record. It
  MAY have optional soft-linkage to a Universe (a Backdrop asset used
  in a Hearth & Hollow scene), but its scoping FK is tenant. Adding a
  Universe FK to Asset creates ambiguity when an asset (a generic
  b-roll clip, a stock voice) is used across Universes. **Position:
  keep Asset workspace-scoped; if Universe soft-attachment matters,
  do it via nullable back-ref, not primary scope.**
- `KnowledgeDocument` (content_hash dedup) — the content_hash dedup
  key remains `(workspace, content_hash)`. If the same PDF is
  legitimately used by two Universes in the same tenant, it should
  dedup to one KnowledgeDocument row and be reachable from both,
  rather than being uploaded twice. See Q9 for the visibility model
  that makes this coherent.
- `GenerationRecord` — the identity-substrate append-only evidence
  chain. Its parent (`CharacterIdentity`) will carry Universe scope
  transitively; GenerationRecord itself does not need its own
  Universe FK.
- `NormalizationManifest` — same as above; inherits from its
  `GenerationRecord`.
- `IdentityReference` — same; inherits from its
  `CharacterIdentityVersion`.
- `ApprovedRepresentationBundle` — same.
- `CanonicalVoiceReference` / `CanonicalRealtimeReference` — same.
- `RealtimeEngineConnection` — a Runway/OpenAI/etc. account
  connection is a tenant billing concern.
- `PromotionAudit`, `BootstrapEvidenceIndex`, `ImportProvenance`,
  `PrequalificationProvenance` — these are substrate-level audit
  rows; they follow their subject's scoping.
- `Workspace` itself — self.

**Position on Composition and PublishBundle:** these MAY gain a
Universe FK once Universe exists as a first-class concept, since a
scene render is authored *for* a world. But if we want to keep the
first slice small, they can rely on transitive scope through their
`spokesperson` FK (whose CharacterIdentity is Universe-scoped) and
gain a direct Universe FK later when episodes / cast / arcs land.
Being explicit about this rather than fudging it is preferable.

### Q6. How should legacy / current data behave where every Teammate, KnowledgeDocument, Composition, and Asset currently lives directly under Workspace?

**Legacy data stays in place. Universe is a prospective concept.**

- The current `chriss-workspace` continues to exist with its 7
  teammates, 14 docs, 81 compositions, 322 assets.
- The current `Admin's workspace` continues to exist with its 2
  teammates, 46 docs, etc.
- No historical Teammate is moved. No historical KnowledgeDocument is
  reassigned. No historical Composition is re-parented.

The SESSION 259 audit §9 concluded exactly this — bulk migration of
teammates between workspaces incurs blocker and silent-breakage risk
(clean() rejects, m2m_changed rejects, composition provenance
divorce). The same reasoning applies with more force when the target
is a *new abstraction* (Universe) whose invariants have not been
proven in practice yet.

**Concrete rule:** if a Teammate has no Universe FK (or its FK is
NULL), it is considered "unassigned" and subject to today's
workspace-scoped behavior — literally the current world model with
zero regression. New teammates created after Universe ships MUST
belong to a Universe. Historical teammates MAY be assigned to a
Universe later as a bespoke ½-slice per character (audit §9's
"do not move historical teammates or content" recommendation).

### Q7. Can Universe be introduced prospectively without immediately migrating historical data?

**Yes, and this is the recommended posture.** Requirements for
prospective-only introduction:

- Universe FK on affected models is nullable at introduction (this is
  a schema decision deferred to a later slice; the design position
  here is that nullability must be permitted).
- Retrieval, synthesis, and every consumer path must handle "no
  Universe assigned" as legal — meaning "treat this exactly as
  today's workspace-wide behavior."
- The moment a Teammate is assigned to a Universe, its behavior
  changes: it can only see (a) knowledge attached to it directly, and
  (b) knowledge attached to the same Universe, and (c) NEVER
  workspace-wide docs (see Q9).
- Historical Teammates without a Universe stay in the legacy
  regime unchanged.

This means the schema and retrieval layer will have to carry both
regimes in parallel until legacy data is either migrated or deleted.
That is an acceptable cost — the alternative (bulk-move at
introduction) creates the very blockers §9 of the audit documented.

### Q8. Should every Workspace have a default Universe for backward compatibility, or is that likely to preserve the current semantic mistake?

**Position: NO auto-default Universe.** Take a stance.

Reason: auto-creating a "default Universe" per workspace and
migrating every teammate + doc into it re-creates the exact overload
we are trying to break. It converts "one workspace, all worlds mixed"
into "one workspace, one Universe, all worlds still mixed" — with
extra scaffolding. The operator would look at the SPA, see one
Universe, and repeat the pattern. Nothing improves.

The correct posture is the one from Q7: **Universe is opt-in and
prospective**. Legacy Teammates without a Universe continue to use
today's semantics (workspace-scoped, empty-M2M = workspace-wide). New
teammates land in an explicitly chosen Universe (created at teammate-
create time if none exists, but chosen — not auto-assigned to a
`"Default Universe"` row).

There is one narrow exception worth naming: a **workspace-onboarding
Universe** created for a specific new workspace (not retrofitted onto
`chriss-workspace`) is fine, as long as the SPA is honest about it
being one world among possible many — not "the" world.

### Q9. How should empty-M2M KnowledgeDocument teammate behavior behave once Universe exists?

Today: empty M2M = "visible to every teammate in the workspace"
(`embeddings/retrieval.py:182–197`).

**Position: once a KnowledgeDocument is Universe-attached, empty M2M
means "visible to every teammate IN THAT UNIVERSE" — not workspace-
wide.** Then:

- **Universe-scoped doc, empty M2M** → visible to every teammate in
  that Universe. This is the correct default and mirrors today's
  behavior at the smaller correct scope.
- **Universe-scoped doc, populated M2M** → visible only to the
  attached teammates (who must themselves be in that Universe;
  cross-Universe teammate attach is rejected).
- **Workspace-scoped doc (no Universe), empty M2M** → legacy
  behavior: visible to every teammate in the workspace WITH NO
  UNIVERSE ASSIGNED. Universe-scoped teammates do NOT see this doc.
- **Workspace-scoped doc (no Universe), populated M2M** → visible to
  the attached (legacy) teammates.

The load-bearing rule: **a teammate assigned to a Universe never
retrieves from a workspace-wide (no-Universe) doc, even if the doc
was uploaded before the Universe existed.** This is the invariant
that closes the "TANK chunks surfacing in Patch/Rivet dialogue" class
of leak — TANK stays legacy-workspace, Patch/Rivet become Universe-
scoped, and cosine similarity across the boundary is disallowed at
the retrieval-query level (not at ranking time; earlier).

**"Illegal" as a state to consider:** should we forbid a
KnowledgeDocument from being both Universe-scoped AND having its M2M
include a teammate from a different Universe? **Yes.** This mirrors
today's cross-workspace M2M rejection. The `clean()` method and the
m2m_changed signal already have the pattern; extending them to
Universe is a downstream slice, but the invariant belongs here.

### Q10. What isolation invariants must hold — workspace boundary, universe boundary, character / cast knowledge boundary?

Three concentric boundaries, each with its own guarantee:

1. **Workspace boundary (tenant).** Nothing crosses. Preserved
   exactly as today. Every existing defense-in-depth mechanism stays
   in place: clean() on cross-workspace M2M, m2m_changed pre_add
   guards, `retrieve_for_teammate` derives workspace unconditionally,
   `IsWorkspaceMember` filters every viewset. **This invariant does
   not weaken. It is the outer wall.**

2. **Universe boundary (world).** Within a workspace, Universe scope
   is enforced structurally the same way workspace scope is today:
   `retrieve_for_teammate` derives Universe from the teammate's
   Universe FK, and the retrieval query filters on
   `document__universe=teammate.universe` (or the legacy behavior if
   both sides are unassigned). Cross-Universe M2M attach is rejected.
   Composition / Script / Campaign / RealtimeSession clean() paths
   extend to reject cross-Universe pairings.

3. **Character / cast knowledge boundary.** Within a Universe, empty
   M2M means "visible to every teammate in this Universe" (Q9). This
   is the smallest boundary and mirrors today's finest-grained
   sharing. `KnowledgeDocument.spokespeople` M2M continues to be the
   character-specific visibility filter; cast/ensemble grouping is
   deferred to a later slice but would sit at this level.

**No implicit crossings ever.** A retrieval, synthesis, composition,
or realtime session call MUST NOT construct a workspace override, a
Universe bypass, or a "see all worlds" flag. If a specific scenario
needs cross-Universe reach in the future (e.g., a crossover episode),
it is an explicit primitive with its own name and its own audit trail
— never a bypass.

### Q11. What would Riggs/Tulsi retrieval have done differently if Universe scope already existed?

Riggs and Rigby live in `Admin's workspace` (SESSION 259 audit §3),
which has 46 KnowledgeDocuments. Tulsi is a Teammate in
`chriss-workspace` with a 3-chunk K2 doc. Cross-workspace leak is
already impossible (§5 of the audit) — that is not the regression
case.

The interesting case is **within `chriss-workspace`**: Patch/Rivet
dialogue synthesis retrieves TANK / Tulsi / Hearth & Hollow chunks
via cosine similarity because those docs have empty M2M and the
workspace filter alone doesn't discriminate world membership (audit
§6). If Patch, Rivet, TANK, Tulsi, and Hearth & Hollow were each
assigned to distinct Universes ("Workshop", "Motorcade", "Riverstone
lookalike", "Bookstore"), then:

- Patch/Rivet dialogue synthesis would derive Universe = "Workshop"
  from the primary spokesperson.
- The retrieval query would filter `document__universe = Workshop`.
- TANK (Motorcade), Tulsi (whichever), and Hearth & Hollow (Bookstore)
  chunks would be structurally unreachable regardless of cosine
  distance to the topic.
- Workspace-wide (no-Universe) legacy docs would ALSO be unreachable
  from Patch/Rivet (per Q9's load-bearing rule).

**This is the regression the Universe boundary directly closes.** Not
the cross-workspace leak (already impossible) — the *within-workspace,
cross-world* leak that the empty-M2M workspace-wide semantics
currently allow.

### Q12. What is the smallest coherent Universe v1 responsibility set?

Universe v1 must own exactly these things and nothing more:

1. **Identity.** A name, a slug (scoped per Workspace, not global — do
   not repeat the Workspace slug wart), a created_at.
2. **Workspace parent.** FK → Workspace, NOT NULL, CASCADE.
3. **Cast membership by construction.** Every Teammate that belongs to
   this Universe carries a FK back to it. Universe does not maintain a
   separate cast M2M — cast is derived from Teammate.universe.
4. **Knowledge scope by construction.** Every KnowledgeDocument that
   belongs to this Universe carries a FK back to it. Retrieval is
   scoped by that FK (Q9 rules).
5. **Nothing else.** No relationships, no locations, no episodes, no
   memory, no palette, no cast M2M, no arcs. All of those are
   downstream slices that will attach to Universe when they exist.

The smallness is deliberate. A Universe row that means "the world
these characters share knowledge and eventually memory / locations /
relationships within" is coherent and testable. A Universe row that
tries to also be a project or a brand or a campaign or an arc will
recreate the workspace overload.

### Q13. What should explicitly NOT belong to Universe?

- **Ownership / seats / billing.** Stay on Workspace. If two
  Universes need different billing, they need different workspaces.
- **Slug uniqueness across tenants.** Workspace-level.
- **Engine credentials.** Workspace-level (a Runway account is a
  billing artifact).
- **Asset workspace-scope.** The pixels are tenant records; if a
  Universe wants to reference them, it does so via primitive-level
  attachment (Composition step inputs / IdentityReference /
  KnowledgeDocument source_url), not by owning the Asset.
- **CharacterIdentity substrate mechanics.** Version lifecycle,
  spec validation, approval floor, reference kinds, canonical
  representation bundles — all substrate concerns that live on
  identity models. Universe is *what world does this identity
  belong to*, not *how identity versioning works*.
- **Composition step mechanics.** Primitives, recipe registry,
  writing contract, verifier state — all render-machinery concerns.
  A Composition may FK Universe eventually to declare "this scene is
  set in world X" but the step/primitive machinery is unchanged.
- **Voice / POV field content.** These stay on Teammate for now
  (SESSION 261 §4 flagged them as "wrong semantic home" for
  versioning reasons, but the fix is voice/POV versioning under the
  identity substrate — not moving them onto Universe). A world does
  not own how a character speaks; the character owns it.
- **Style / palette definitions.** Workspace-level today (via brand
  ecosystem CSS-var swap). A per-Universe palette is a plausible
  future — treat as deferred.

## Recommended boundary

**Workspace is the tenant. Universe is the world. Teammate belongs to
one Universe (or to Legacy). KnowledgeDocument belongs to one Universe
(or to Legacy). Retrieval, synthesis, and every consumer path filter by
Universe when the actor has one, and by Workspace-legacy when they do
not. Cross-Universe access is never implicit. Legacy data is not
migrated.**

Three corrections to the initial hypothesis:

1. **"Every Workspace has a default Universe" is REJECTED.** Universe
   is opt-in and prospective. Auto-defaulting recreates the overload
   (Q8).
2. **"Workspace-wide knowledge should NOT automatically become
   Universe knowledge" is CORRECT and STRONGER than stated.** A
   teammate assigned to a Universe never retrieves from a legacy
   workspace-wide doc, period. Legacy docs stay reachable only by
   legacy (unassigned) teammates (Q9).
3. **"Characters, canon, relationships, locations, episodes belong to
   Universe" — CORRECT for future scope, but v1 Universe owns ONLY
   the two anchors Teammate.universe and KnowledgeDocument.universe.**
   Relationships / locations / episodes / memory / cast are downstream
   slices; the boundary just says "when they arrive, they attach to
   Universe, never to Workspace." (Q12)

## Workspace responsibilities (permanent)

- Ownership (`owner` FK, PROTECT).
- Membership + role.
- Slug identity for URL routing (per-owner scoping is a nice-to-have,
  not a boundary requirement).
- Billing anchor.
- Engine / provider connections.
- Cross-tenant privacy boundary — the outer wall, unweakened.
- Asset library scope (pixels/audio are tenant records).
- KnowledgeDocument content_hash dedup namespace
  (`(workspace, content_hash)` stays).
- Teammate naming uniqueness namespace (`(workspace, name)` stays; a
  Universe-scoped namespace addition is deferred).
- Composition / Script / Campaign / PublishBundle direct workspace
  scope stays (Universe FK may be added later per Q4).

## Universe responsibilities (v1 minimum)

- Identity: name, per-workspace slug, created_at, archived_at.
- Workspace parent FK (NOT NULL, CASCADE).
- Cast membership by construction: `Teammate.universe` FK (nullable
  for legacy).
- Canon scope by construction: `KnowledgeDocument.universe` FK
  (nullable for legacy).
- Nothing else in v1.

## Ownership / scoping matrix

Column key:

- **Workspace FK today?** — does the model currently have a direct
  Workspace FK (Y/N).
- **Under recommended boundary** — where the primary scope FK lives
  after Universe is introduced. `Workspace` means "stays workspace-
  scoped, no Universe FK." `Universe (nullable, legacy=workspace)`
  means "primary scope is Universe once assigned; when Universe is
  NULL, model falls back to workspace-scoped legacy semantics."
  `Transitive via <parent>` means the model inherits scoping from a
  parent, no direct FK needed. `Neither` means the model has no
  tenant/world scope of its own (rare).

| Model | Workspace FK today? | Under recommended boundary | Notes |
|---|---|---|---|
| `Workspace` | Self | Self | Tenant root. No change. |
| `Membership` | Y | Workspace | Seat is a tenant relationship, not a world one. |
| `Teammate` | Y | Workspace + Universe (nullable) | Universe FK is the character-in-a-world assignment. NULL = legacy. |
| `CharacterIdentity` | Y | Workspace + Transitive via `teammate.universe` | Identity is per-teammate; universe rides through the teammate FK. Adding a direct Universe FK is redundant if we insist identity always tracks its owning teammate. |
| `CharacterIdentityVersion` | N (via `identity`) | Transitive via `identity` | Substrate mechanic, not a world axis. |
| `GenerationRecord` | N (via `identity_version`) | Transitive via `identity_version` | Append-only evidence. |
| `NormalizationManifest` | N (via `generation_record`) | Transitive via `generation_record` | Immutable per-generation record. |
| `IdentityReference` | N (via `identity_version`) | Transitive via `identity_version` | Reference-view lifecycle. |
| `ApprovedRepresentationBundle` | N (via `identity_version`) | Transitive via `identity_version` | Bundle lifecycle. |
| `CanonicalVoiceReference` | N (via `identity_version`) | Transitive via `identity_version` | — |
| `CanonicalRealtimeReference` | N (via `identity_version`) | Transitive via `identity_version` | — |
| `ImportProvenance` / `PrequalificationProvenance` / `PromotionAudit` / `BootstrapEvidenceIndex` | N | Transitive via subject | Substrate audit rows. |
| `KnowledgeDocument` | Y | Workspace + Universe (nullable) | Load-bearing addition. Dedup key stays `(workspace, content_hash)`. |
| `KnowledgeChunk` | N (via `document`) | Transitive via `document` | Reached only through the sanctioned `retrieve_for_teammate` path. |
| `KnowledgeDocumentSpokesperson` | N (through table) | Transitive via `document` | Visibility M2M; cross-Universe attaches rejected. |
| `Composition` | Y | Workspace + Universe (nullable, defer decision) | May gain direct Universe FK when Episode / arc concepts land. Until then, transitive via `spokesperson.universe` is acceptable. |
| `CompositionStep` | N (via `composition`) | Transitive via `composition` | — |
| `Asset` | Y | Workspace | Pixels/audio are tenant assets. Optional soft-linkage to Universe via nullable back-ref only if a real need surfaces. |
| `Script` | Y | Workspace + Universe (nullable, defer decision) | Same posture as Composition. |
| `PersonalizedCampaign` | Y | Workspace + Universe (nullable, defer decision) | Same posture. Recipient PII is tenant-scoped; content-of-campaign is world-scoped. |
| `PublishBundle` | Y | Workspace | Distribution artifact; source clip is a tenant asset. |
| `PublishVariant` | N (via `bundle`) | Transitive via `bundle` | — |
| `ConversationThread` | Y | Workspace + Transitive via `spokesperson.universe` | The character carries the world. |
| `ConversationMessage` | N (via `thread`) | Transitive via `thread` | — |
| `ConversationEmbedding` | N (via `message`) | Transitive via `message` | Separate embedding table so workspace/universe retrieval cannot reach it. |
| `RealtimeSession` | Y | Workspace + Transitive via `spokesperson.universe` | Session belongs to a character-world. |
| `RealtimeToolInvocation` | N (via `session`) | Transitive via `session` | Tool audit. |
| `RealtimeEngineConnection` | Y | Workspace | Tenant billing artifact. |
| `TranscriptHighlight` | Y | Workspace + Transitive via `session.spokesperson.universe` | Derived from a session. |
| `Video` (legacy) | Y | Workspace | Legacy shim; do not add work here. |
| `apps.memory` models (future) | — | Universe | Future memory substrate attaches at Universe, never at Workspace. |
| `apps.agents` models (future) | — | Workspace or Universe (TBD) | Depends on whether agents are per-tenant or per-world. Deferred. |
| `Relationship` (future) | — | Universe | Character-to-character edges belong to a world. |
| `Location` (future) | — | Universe | Recurring places belong to a world. |
| `Cast` / `Ensemble` (future) | — | Universe | N-character grouping belongs to a world. |
| `Episode` / `Arc` (future) | — | Universe | Narrative grouping belongs to a world. |
| `WorldEntity` (future in-world objects) | — | Universe | Props and in-world objects belong to a world. |
| `WorldPalette` (future) | — | Universe | Per-world visual identity attaches at Universe. |

## Legacy-data implications

- No historical Teammate is moved. `chriss-workspace`'s seven
  teammates stay put with NULL Universe FKs.
- No historical KnowledgeDocument is reassigned. All 14 docs in
  `chriss-workspace` stay with NULL Universe FKs.
- No historical Composition / Script / Campaign / Asset is
  re-parented.
- Legacy teammates continue to see legacy docs via today's
  workspace-wide empty-M2M semantics.
- Universe-assigned teammates never see legacy workspace-wide docs
  (Q9 load-bearing rule).
- Same-document dedup still works: `(workspace, content_hash)` stays
  the unique key, so a doc uploaded before Universe existed continues
  to be the one row for that content in that tenant, even if a new
  Universe wants to reference it via re-upload (dedup handles this;
  the doc gains a Universe FK on reassignment).
- Migration of a specific historical Teammate into a Universe is a
  bespoke ½-slice per SESSION 259 audit §9 — detach M2Ms, verify
  clean() and signal invariants at the new scope, reattach in new
  context. Not done in bulk.
- SPA silently defaulting knowledge upload to workspace-wide
  visibility (`web/src/lib/api/knowledge.ts:219–227`) is a pre-
  existing gap that the Universe introduction does not fix — but it
  becomes strictly worse if we ship Universe without a corresponding
  SPA change to pick a Universe at upload. The two must land
  together.
- Composition provenance divorce risk noted in audit §9 (moving a
  teammate makes historical `composition.workspace` diverge from
  `teammate.workspace`) does NOT arise for prospective Universe
  assignment, because prospective assignment does not change
  `teammate.workspace` — only sets `teammate.universe`.

## Isolation invariants

Restated as invariants to preserve (some existing, some new):

1. **Workspace privacy invariant (existing, preserved).** No data
   crosses Workspace boundaries. Every existing clean() / signal /
   permission mechanism stays in force.
2. **Universe privacy invariant (new).** Within a Workspace, no data
   crosses Universe boundaries. `retrieve_for_teammate` filters by
   `teammate.universe`. `KnowledgeDocument.clean()` and the
   spokespeople m2m_changed signal reject cross-Universe attaches.
   `Composition.clean()`, `Script.clean()`,
   `PersonalizedCampaign.clean()`, `RealtimeSession.clean()`,
   `Asset.spokesperson` validation, `IdentityReference.clean()` all
   extend to reject cross-Universe pairings.
3. **Legacy isolation invariant (new).** A Universe-scoped teammate
   never retrieves from a workspace-wide (Universe=NULL) doc. A
   workspace-wide (Universe=NULL) teammate retrieves under today's
   legacy semantics unchanged.
4. **Empty-M2M invariant (existing shape, tightened scope).** Empty
   `KnowledgeDocument.spokespeople` M2M means "visible to every
   teammate in the same Universe as this doc" (or "in the same
   workspace" when both doc and teammate are Universe=NULL).
5. **No implicit crossing primitive.** Retrieval, synthesis,
   composition, and realtime code paths MUST NOT expose any
   workspace-override, Universe-bypass, "see all worlds" flag, or
   debug bypass. Crossover, if ever needed, is an explicit primitive
   with a distinct name and audit trail.
6. **Character/cast knowledge invariant (existing, preserved).**
   Character-specific M2M attach continues to be the finest-grained
   sharing; a doc M2M-attached to specific teammates is visible only
   to those teammates (all of whom must be in the same Universe as
   the doc).
7. **Substrate immutability invariant (existing, preserved).**
   `GenerationRecord` / `NormalizationManifest` append-only behavior
   is unchanged; they inherit Universe scope transitively through
   `identity_version.identity.teammate.universe`.
8. **Dedup invariant (existing, preserved).**
   `(workspace, content_hash)` remains the KnowledgeDocument dedup
   key. Universe FK is orthogonal; the same content hash cannot
   exist twice in a tenant regardless of Universe membership.

## Unresolved questions deferred to later slices

1. Relationship substrate design — new `Relationship` model vs M2M on
   Teammate vs Universe-scoped graph edges (SESSION 261 §8 D.1).
2. Persistent narrative memory design — reuse `apps/memory` scaffold
   vs new home; event log vs promise ledger vs arc-marker shape
   (§9 D.2).
3. Location / Scene / Set entity design — resolves the three-way
   naming collision when it lands (§12 D.3).
4. Cast / Ensemble grouping design — N-character primitive shape
   (§13 D.4).
5. Composition → Episode promotion or wrapping — do we add
   `operator_topic`, `previous_composition`, `episode_id`,
   `scene_number` to Composition or create a wrapping Episode row
   (§10 special-question 9; D.12).
6. Voice / POV versioning — move to identity substrate or add
   `TeammateFieldVersion` (§4 CAPABILITY_INVENTORY_SESSION_261.md
   pre-Universe question 3).
7. Non-human canonical identity — Character Presence Language must
   land before Patch/Rivet get canonical substrate identities
   (§6 special question; pre-Universe question 2).
8. Backdrop naming disambiguation between
   `NormalizationManifest.background_id` and `Asset(role=BACKDROP)`
   — pre-Universe question 9; becomes three-way if Location arrives
   before it's resolved.
9. Per-Universe palette / brand identity — extend
   `feedback_css_var_brand_swap.md` per-workspace pattern to per-
   Universe.
10. SPA UX for Universe — picker, creator, switcher, knowledge-upload
    Universe assignment, teammate-create Universe assignment. Must
    land with the schema so the SPA does not silently repeat the
    workspace-wide default mistake.
11. Slug uniqueness reform on Workspace (pre-existing wart from
    SESSION 259 audit §8) — per-owner scoping if multi-workspace-
    per-user becomes real.
12. Should Composition / Script / PersonalizedCampaign gain a direct
    Universe FK in v1, or rely on transitive `spokesperson.universe`
    until Episode / arc concepts arrive? Q4/Q5 argues either is
    defensible; punt to the schema slice.
13. Optional soft-linkage of Asset to Universe (nullable back-ref)
    for cases where a Backdrop asset is world-specific — is that a
    real need or premature.
14. Membership sub-scoping — do we ever want a viewer/editor role
    scoped to a specific Universe within a Workspace, or is
    Workspace-level seat always sufficient. Q5 defers this.
15. Should the `apps/memory` and `apps/agents` scaffolds be renamed /
    scoped to Universe when they get populated, or stay tenant-level
    with per-Universe subscoping.

## STOP

Design-only. No schema. No migrations. No code. Every load-bearing
claim is cited to file:line or to the source audit documents.
