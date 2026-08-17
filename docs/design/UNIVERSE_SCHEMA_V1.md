---
title: "Universe Schema v1 — Smallest Deployable Universe Substrate"
status: design — schema contract (no code, no migrations, no SPA changes)
date: 2026-08-17
depends_on:
  - "design/CAPABILITY_INVENTORY_SESSION_261.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"
  - "design/RELATIONSHIP_BOUNDARY_V1.md"
  - "design/WORLD_ENTITY_BOUNDARY_V1.md"        # agency-not-voice correction, 8f26d7e
  - "design/UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md"
scope: >
  Schema contract for the smallest deployable Universe substrate:
  one new `Universe` model, nullable `Teammate.universe` FK, nullable
  `KnowledgeDocument.universe` FK, Universe-aware retrieval + clean
  contracts, and the SPA vertical-slice affordances that MUST land with
  the schema so the operator cannot silently repeat the workspace-wide
  default failure mode. No code, no migrations, no Django field
  additions performed by this document — only the contract those
  eventual writes must honor.
---

# Universe Schema v1 — Smallest Deployable Universe Substrate

## Purpose / scope

Deliver a schema contract for the Universe substrate — the *inner
wall* that the six prior SESSION 261 slices converged on. Concretely,
the contract answers:

1. Where the `Universe` model lives in the Django app graph and why.
2. Field-by-field shape of `Universe`.
3. Nullable `Teammate.universe` + `KnowledgeDocument.universe` FKs and
   their exact deletion / cascade / validation behavior.
4. The retrieval predicate that structurally forbids a Universe-scoped
   Teammate from surfacing legacy `universe=NULL` chunks.
5. The `clean()` + `m2m_changed` contract that forbids cross-Universe
   M2M attachment.
6. The API surface the SPA depends on and the SPA affordances that
   land WITH the schema (never after) so the workspace-wide silent
   default fails safe.
7. Test matrix, legacy compatibility matrix, failure-mode analysis,
   and implementation sequencing.

**Non-goals.** No relationships, no episodes, no world entities, no
narrative memory, no canon promotion, no per-Universe palette, no
educational curriculum, no voice/POV versioning, no cross-Universe
crossover primitive, no non-human Character Presence Language. Those
have their own slices in the integration DAG (`UNIVERSE_ARCHITECTURE
_INTEGRATION_V1.md §Model implementation sequencing`).

**Nothing in this document creates or edits code, migrations, DDL,
Django fields, or SPA components.** It is a contract the next
implementation slice must honor.

## Vertical-slice mandate (SPA + backend together)

`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §Q29` names the
silent-workspace-wide-default risk as blast-radius #3: today the SPA's
knowledge upload never sends `spokesperson_ids`, which the backend
interprets as "empty M2M → visible to every teammate in the
workspace." Shipping schema WITHOUT the corresponding SPA change would
reproduce exactly this failure mode at Universe scope: operators would
create Universe-scoped docs whose empty M2M silently exposes every
character in the Universe (correct semantics) OR — worse — creates
Universe-NULL docs the operator *thinks* are Universe-scoped.

**Rule:** the schema slice and the SPA slice are one deployable slice.
They land in one Beat. Splitting them is forbidden by this contract.

Evidence: `web/src/lib/api/knowledge.ts:219–227` defines
`CreateKnowledgePayload` with `spokesperson_ids?: string[]`;
`web/src/routes/workspace/knowledge.tsx:198–213` (paste) and
`:288–300` (upload) never populate the field. The default is workspace
-wide by construction.

## Load-bearing principles carried forward

Restated once for the record (see prior slices for evidence):

1. **Workspace = tenant / privacy. Universe = world within tenant.**
   Outer wall is Workspace; inner wall is Universe. Cross-tenant is
   impossible; cross-Universe is possible only via explicit named
   primitive (none v1).
2. **Universe is opt-in and prospective.** No auto-default Universe.
   Legacy Teammates keep `universe=NULL` and behave exactly as today.
   No bulk migration.
3. **Explicit-only canon.** Universe rows are created only by
   operator action. No LLM auto-canon, no cast-co-occurrence
   inference, no prose-parsing auto-creation.
4. **Legacy character data informs compatibility; it does not define
   Universe semantics.** Mike, Repo Red, Tulsi, and every historical
   Composition continue to work under pre-Universe semantics.
5. **Knowledge may describe; knowledge must not constitute.** K2 is a
   factual corpus; it does not create characters, universes, or
   entities.
6. **Agency-not-voice (informational for this slice).** Character vs
   WorldEntity is agency-based, not voice-based, per operator
   correction committed as `8f26d7e` (`WORLD_ENTITY_BOUNDARY_V1.md`
   §Corrections). This slice does not create WorldEntity; the rule is
   named here so downstream readers converge on the corrected frame.

## Current-state repository evidence (with exact file:line citations)

### Teammate + Workspace surface

- `Teammate` — `shell/apps/spokespeople/models.py:26–370`. UUID PK,
  `workspace = FK(Workspace, on_delete=CASCADE, related_name=
  "teammates")` at line 65–69. Constraint
  `spokesperson_unique_name_per_workspace` on `(workspace, name)` at
  line 333–339. `db_table = "spokespeople_spokesperson"` at line 331
  is a persistence identifier and MUST NOT change.
- `Workspace` — `shell/apps/accounts/models.py:108–142`. UUID PK,
  globally-unique `slug` (`SlugField(max_length=140, unique=True)` at
  line 113 — pre-existing wart flagged in SESSION 259 audit §8; NOT
  reformed by this slice). `owner = FK(User, on_delete=PROTECT)` at
  line 114–118. Auto-slug at save time (line 133–142).
- `Membership` — `shell/apps/accounts/models.py:145–163`. `Role` enum
  `owner|admin|editor|viewer` at line 149–153. Only `owner` is used
  by v1 policy. Unique `(user, workspace)` at line 169.
- `default_workspace_for(user)` — line 176–188. Returns the user's
  primary Workspace; SPA reads it via `GET /api/me/`.
- `TeammateViewSet` — `shell/apps/spokespeople/views.py:242–1243`.
  `serializer_class = TeammateSerializer`,
  `permission_classes = [IsWorkspaceMember]`. `get_queryset` at line
  254–262 filters by `workspace__memberships__user=user`.
- `TeammateSerializer` — `shell/apps/spokespeople/serializers.py:11–
  116`. Field list at line 42–88 does NOT currently include a
  `universe` field; adding one is a v1 schema-slice deliverable.
- URLs — `shell/apps/spokespeople/urls.py:16` routes
  `/api/spokespeople/`; basename `spokesperson`; external contract per
  §17.1.b compatibility.

### KnowledgeDocument + retrieval surface

- `KnowledgeDocument` — `shell/apps/embeddings/models.py:111–245`.
  `workspace = FK(Workspace, on_delete=CASCADE)` at line 124–128.
  `spokespeople = M2M(Teammate, through=KnowledgeDocumentSpokesperson,
  blank=True)` at line 135–140. Unique `(workspace, content_hash)` at
  line 216–219. `KnowledgeDocument.clean()` at line 230–245 already
  rejects cross-workspace M2M attach post-save.
- `KnowledgeDocumentSpokesperson` — line 70–108. Explicit through
  model preserving the `spokesperson_id` DB column across the SESSION
  240 rename. `db_column="spokesperson_id"` at line 98 is a
  persistence identifier and MUST NOT change.
- `KnowledgeChunk` — line 248–321. 1536-dim `VectorField` + HNSW
  index. Only `apps.embeddings.retrieval` may query
  `KnowledgeChunk.objects` (K2 contract rule 2, asserted by
  `apps/embeddings/tests/test_retrieval_privacy.py::test_only_retrieval_module_queries_chunk_tables`).
- `retrieve_for_teammate` — `shell/apps/embeddings/retrieval.py:147–
  197`. Workspace filter derived unconditionally from
  `spokesperson.workspace` (line 184). Visibility clause at line 189–
  191: `Q(document__spokespeople__isnull=True) | Q(document__
  spokespeople=spokesperson)` — the empty-M2M workspace-wide default.
- `retrieve_for_thread` — line 200–250. Delegates workspace-scoped
  doc retrieval to `retrieve_for_teammate`; conversation embeddings
  live in a separate table so retrieval cannot cross.
- Signals — `shell/apps/embeddings/signals.py:31–79`. `m2m_changed
  pre_add` on `KnowledgeDocument.spokespeople.through` rejects
  cross-workspace attach in both forward and reverse directions.
- `KnowledgeDocumentViewSet` — `shell/apps/embeddings/views.py:48–
  373`. `permission_classes=[IsWorkspaceMember]` at line 52.
  `get_queryset` at line 62–97 filters
  `workspace__memberships__user=user, is_active=True`, plus optional
  `?workspace=`, `?spokesperson=`, `?document_type=` query filters.
  `attach`/`detach` actions at line 111–169.
- `KnowledgeDocumentSerializer` — `shell/apps/embeddings/serializers
  .py:39–401`. `create()` at line 220–297; consumes optional
  `spokesperson_ids` (`source="spokespeople"`) from the payload at
  line 61–66. `update()` at line 299–400 supports title +
  spokespeople M2M + text_content re-ingest.

### Retrieval callsites (all consumers of the retrieval surface)

Grep confirmed the sanctioned consumers of `retrieve_for_teammate`:

- `shell/character_os/script_synthesis.py:322`, `:337` — talking-head
  K6 synthesis.
- `shell/character_os/dialogue_synthesis.py:1298`, `:1302` — dialogue
  scene per-character retrieval (Rule 7).
- `shell/character_os/realtime_document.py:131` — realtime session
  document composition.
- `shell/character_os/teammate_ask.py:188`, `:213` — teammate-ask
  endpoint (mock and real).
- `shell/apps/embeddings/views.py:301` (preview action), `:302`
  (spokesperson resolver).
- Tests: `apps/embeddings/tests/test_retrieval_privacy.py`,
  `test_api_k5.py`, `test_preview.py`; `apps/compositions/tests/
  test_dialogue_synthesis.py`; `apps/realtime/tests/
  test_r4_knowledge_bridge.py`; `apps/spokespeople/tests/test_ask.py`.

**The predicate change proposed by this slice is a single-site change
inside `retrieve_for_teammate`.** No callsite requires a signature
change.

### Composition surface (informational — not touched by this slice)

- `Composition` — `shell/apps/compositions/models.py:357–548`.
  `workspace = FK(Workspace, on_delete=CASCADE)` at line 380–384.
  `spokesperson = FK(Teammate, on_delete=SET_NULL, null=True,
  blank=True)` at line 385–391 (SESSION 251 relaxation). `.clean()`
  at line 523–548 validates spokesperson-workspace consistency.
- `Composition.episode` FK / Episode model **do not exist**. Episode
  is a downstream slice (see `EPISODE_LIFECYCLE_V1.md`). This slice
  does NOT add `Composition.universe` and does NOT add
  `Composition.episode`; Universe reaches Composition transitively via
  `Composition.spokesperson.universe` in the intervening period,
  per `UNIVERSE_BOUNDARY_V1.md §Q4/§Q5` deferral position.

### SPA surface (routes, components, API client)

- SPA lives at `/Users/donkeyking/Donkey_Betz/character-os/web/`.
  Stack: Vite + React Router (route files under `web/src/routes/`),
  TanStack Query, Zod-validated API wrappers under `web/src/lib/api/`.
- No Universe route, no Universe component, no Universe API wrapper
  exists. `web/src/lib/api/workspaces.ts:16–43` is a thin wrapper on
  `GET /api/me/` returning `default_workspace`.
- Nav — `web/src/components/nav-rail.tsx`. Nine sections; no Universe
  section. Adding a new top-level section requires its own scope-lock
  event per F0 contract rule 7 (documented in nav-rail comment); the
  SPA affordances proposed by this slice attach WITHIN existing
  surfaces (spokesperson detail, workspace knowledge, workspace
  overview) rather than introducing a new nav section.
- Spokesperson detail — `web/src/routes/spokespeople/$id.tsx`. Reads
  a `Spokesperson` from `useSpokesperson(id)`; renders
  `SpokespersonEditModal`, `SpokespersonRebakeModal`, etc. This is
  where the "assign to Universe" affordance attaches (v1).
- Knowledge dashboard — `web/src/routes/workspace/knowledge.tsx`.
  Four upload forms (paste, upload, url, search). **None currently
  send `spokesperson_ids`.** Uploads silently workspace-wide. This is
  the load-bearing SPA change site.
- Knowledge API client — `web/src/lib/api/knowledge.ts:219–227`
  (`CreateKnowledgePayload`). `spokesperson_ids?: string[]` is
  optional; universe-scoped ingestion needs an additional
  `universe?: string` field on the payload.

### Existing test coverage that could regress

- `apps/embeddings/tests/test_retrieval_privacy.py` (7 tests) — the
  load-bearing K2 privacy contract. Cross-workspace isolation MUST
  survive the Universe FK addition unchanged.
- `apps/embeddings/tests/test_api_k5.py` (10 tests) — attach/detach
  M2M behavior. Existing cross-workspace 400 responses stay valid;
  new cross-Universe 400 responses added.
- `apps/embeddings/tests/test_api.py`, `test_api_k7.py`,
  `test_preview.py` (URL/serper/preview flows) — legacy paths must
  continue to work with `universe=None` payloads.
- `apps/embeddings/tests/test_m2m_through_column_contract.py` —
  asserts `spokesperson_id` DB column contract. Universe FK addition
  MUST NOT touch this constraint.
- `apps/embeddings/tests/test_f7_compositions_reverse.py` —
  compositions-that-used-this-doc reverse. Universe FK addition is
  orthogonal.
- `apps/spokespeople/tests/test_identity_fields.py`,
  `test_personality_sync.py`, `test_ask.py`, `test_delete.py`,
  `test_rebake_avatar.py`, `test_step4d_canonical_migration.py`,
  `test_voice_presets_endpoint.py` — Teammate CRUD + downstream
  identity substrate. Universe FK addition MUST NOT regress any of
  these.
- `apps/compositions/tests/test_dialogue_synthesis.py`,
  `test_v14_dialogue.py`, `test_dialogue_ai_topic_wiring.py`,
  `test_session260_dialogue_cps_calibration.py` — dialogue synthesis.
  Retrieval predicate change MUST NOT break these when both
  spokespeople are legacy (`universe=NULL`).
- `apps/realtime/tests/test_r4_knowledge_bridge.py`,
  `test_r6_session_memory.py`, `test_r7_3_attach_memory.py` —
  realtime session document composition. Universe scope MUST not
  break realtime memory projection for legacy Teammates.

## Proposed schema contract

### Universe model (fields, meta, indexes)

**Home:** new Django app `apps/universe/`. See §"App home decision"
below for reasoning.

Fields — proposed shape (documenting the eventual model definition;
this document does not create it):

- `id`: `UUIDField(primary_key=True, default=uuid.uuid4,
  editable=False)`.
- `workspace`: `FK(Workspace, on_delete=CASCADE,
  related_name="universes")`. NOT NULL. Cascade on Workspace deletion
  because Universe cannot outlive its tenant.
- `name`: `CharField(max_length=120)`. Operator-visible. Not required
  unique globally, only unique per-workspace via slug.
- `slug`: `SlugField(max_length=140)`. Derived from `name` at save
  time (mirror of Workspace's auto-slug pattern, `accounts/models.py:
  133–142`) but with per-workspace uniqueness rather than global.
- `description`: `TextField(blank=True, default="")`. Operator prose.
  Optional. Not consumed by synthesis.
- `created_by`: `FK(User, on_delete=SET_NULL, null=True, blank=True,
  related_name="created_universes")`. Audit anchor. NULL when creator
  user deleted.
- `created_at`: `DateTimeField(auto_now_add=True)`.
- `updated_at`: `DateTimeField(auto_now=True)`.
- `archived_at`: `DateTimeField(null=True, blank=True)`. Soft-delete
  marker. See §Deletion policy.

Meta:

- `db_table = "universe_universe"` — new table; no db_table
  preservation constraint.
- `constraints = [UniqueConstraint(fields=["workspace", "slug"],
  name="universe_unique_slug_per_workspace")]`.
- `indexes = [Index(fields=["workspace", "archived_at"])]` — powers
  the SPA's "active universes in this workspace" query.
- `ordering = ["workspace", "name"]`.

`__str__`: `f"{self.name} ({self.workspace.name})"`.

`clean()`: validates `slug` matches `slugify(name)`-derived form when
`slug` was auto-populated (no-op when operator provided a slug
override — deferred until v2 slug override affordance surfaces).

### Teammate.universe FK addition

- `universe`: `FK("universe.Universe", on_delete=SET_NULL, null=True,
  blank=True, related_name="teammates")`.
- **Nullable** — critical. NULL means "legacy teammate; use
  pre-Universe semantics."
- On-delete `SET_NULL` — deleting a Universe demotes its Teammates
  to legacy behavior rather than cascading a Teammate delete (a
  Teammate row carries CharacterIdentity substrate, Compositions,
  Assets, and history — never quietly destroy that).
- Related-name `"teammates"` mirrors the existing `Workspace.teammates`
  related-name pattern (see `accounts/models.py:108` reverse via
  `spokespeople/models.py:65–69 related_name="teammates"`).
- `Teammate.clean()` — see §clean contract below — validates
  `self.universe is None or self.universe.workspace_id == self.
  workspace_id`.

### KnowledgeDocument.universe FK addition

- `universe`: `FK("universe.Universe", on_delete=SET_NULL, null=True,
  blank=True, related_name="knowledge_documents")`.
- **Nullable** — critical. NULL means "legacy workspace-wide doc."
- On-delete `SET_NULL` — deleting a Universe demotes its docs to
  legacy visibility rather than cascade-deleting corpus content. This
  mirrors how Teammate delete relaxed from PROTECT to SET_NULL for
  Composition in SESSION 251 (`compositions/models.py:385–391`).
- Related-name `"knowledge_documents"` mirrors the existing
  `Workspace.knowledge_documents` related-name (`embeddings/models
  .py:127`).
- `KnowledgeDocument.clean()` — extended per §clean contract below.

Content_hash dedup key remains unchanged: `(workspace, content_hash)`
(line 216–219). Universe FK is orthogonal to dedup. A doc whose
content the operator later re-associates to a Universe is the SAME
row; the FK is repointed, chunks are unchanged, dedup collision does
not fire.

## Field-by-field semantics

### Universe

| Field | Type | Nullable | Meaning | Validation |
|---|---|---|---|---|
| `id` | UUID | No | Primary key. | Django default. |
| `workspace` | FK Workspace | No | Tenant parent. | `on_delete=CASCADE`. |
| `name` | Char(120) | No | Operator-visible label. | Non-empty; not globally unique. |
| `slug` | Slug(140) | No | Per-workspace routing key. | Unique with `workspace`; auto-derived from `name` at save; case-insensitive via `SlugField` semantics (all lowercase, ASCII-only). |
| `description` | Text | Yes (blank ok) | Operator prose about the world. | None. Not consumed by synthesis. |
| `created_by` | FK User | Yes | Audit. | `on_delete=SET_NULL`. |
| `created_at` | DateTime | No | Audit. | `auto_now_add`. |
| `updated_at` | DateTime | No | Audit. | `auto_now`. |
| `archived_at` | DateTime | Yes | Soft-delete marker. | NULL = active. Non-NULL = archived. See §Deletion policy. |

### Teammate.universe addition

| Field | Type | Nullable | Meaning | Validation |
|---|---|---|---|---|
| `universe` | FK Universe | Yes | World this character belongs to. NULL = legacy. | `on_delete=SET_NULL`; `.clean()` enforces `universe.workspace_id == workspace_id`. |

### KnowledgeDocument.universe addition

| Field | Type | Nullable | Meaning | Validation |
|---|---|---|---|---|
| `universe` | FK Universe | Yes | World this doc scopes to. NULL = legacy workspace-wide. | `on_delete=SET_NULL`; `.clean()` enforces `universe.workspace_id == workspace_id`; extended M2M check per §clean contract. |

## Invariants (integrated, numbered)

The following invariants MUST hold once this slice ships. They are a
strict subset of the isolation invariant list in
`UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §Isolation invariants` — this
slice ships #1, #2 (K2-only portion), #3, #4, #5, #6, #7, #8. The
other invariants belong to Episode / Relationship / WorldEntity
slices.

1. **Workspace privacy invariant (existing, preserved).** No data
   crosses Workspace boundaries. Every existing defense-in-depth
   mechanism stays in force unmodified.
2. **Universe consistency invariant (new).** For every
   `Teammate`, `KnowledgeDocument`, and `Universe` row: `universe IS
   NULL OR universe.workspace_id == self.workspace_id`. Enforced at
   `.clean()` AND at DB level via a CHECK-style predicate (validated
   in `.clean()`; Django CheckConstraint is not used because Django
   cannot express a cross-table workspace check in a CHECK — the
   defense is `.clean()` + M2M signal + retrieval predicate).
3. **Legacy isolation invariant (new).** A Teammate with
   `universe IS NOT NULL` NEVER retrieves from a KnowledgeDocument
   with `universe IS NULL`. See §Retrieval truth table for the exact
   ORM predicate.
4. **Universe M2M invariant (new).** `KnowledgeDocument.spokespeople`
   M2M cannot attach a Teammate whose `universe_id` differs from the
   document's `universe_id`. Rejected at `.clean()` and at
   `m2m_changed pre_add` in both forward and reverse directions.
5. **Empty-M2M invariant (tightened scope).** Empty
   `KnowledgeDocument.spokespeople` means "visible to every Teammate
   in the same Universe as this doc" (when
   `document.universe IS NOT NULL`) OR "every Teammate in the same
   Workspace with `universe IS NULL`" (when
   `document.universe IS NULL`).
6. **No implicit crossing primitive (new).** No workspace-override,
   Universe-bypass, "see all worlds" flag, or debug bypass. Retrieval
   MUST NOT expose a `universe=` parameter override analogous to the
   forbidden `workspace=` override on `retrieve_for_teammate`.
7. **Substrate immutability invariant (existing, preserved).**
   `GenerationRecord` / `NormalizationManifest` append-only behavior
   is unchanged. Identity substrate rows inherit Universe scope
   transitively via `identity.teammate.universe`; no Universe FK is
   added to identity models by this slice.
8. **Dedup invariant (existing, preserved).** `(workspace,
   content_hash)` remains the KnowledgeDocument dedup key. The
   Universe FK is orthogonal.

## Deletion / cascade policy

### Workspace deletion

- `Workspace` deletion → `Universe` deletion via CASCADE
  (`Universe.workspace on_delete=CASCADE`). This matches every
  existing workspace-child cascade (Teammate, KnowledgeDocument,
  Composition, Asset, etc.).
- Universe's own cascade behavior (see below) then unwinds Teammate
  and KnowledgeDocument Universe FKs to NULL under SET_NULL.
- Practical effect: deleting a Workspace deletes its Universes but
  the Teammates/KnowledgeDocuments within that Workspace are already
  being CASCADE-deleted from Workspace at the same time (they are
  workspace children). The SET_NULL from Universe deletion is a
  no-op in this path because the child rows are gone anyway. This is
  correct and desired — do not "protect" Workspace deletion via
  Universe.

### Universe deletion (direct)

- `on_delete=SET_NULL` on both `Teammate.universe` and
  `KnowledgeDocument.universe`. Deleting a Universe demotes its
  members to legacy behavior; it does not destroy them.
- Rationale: a Teammate row carries CharacterIdentity substrate,
  Compositions, historical Assets, threads, sessions. A K2 doc
  carries chunks, dedup, and downstream composition references
  (`Composition.knowledge_chunk_ids`). Neither should quietly vanish
  because the operator archived a world.
- The Universe row itself hard-deletes on this path (Django default
  when calling `Universe.delete()`).

### Universe soft-delete (archive)

- Preferred v1 posture: **soft-delete via `archived_at`**, not hard
  delete. Rationale: (a) preserves audit trail, (b) allows
  un-archive, (c) avoids the SET_NULL cascade on production data.
- Hard delete remains available for operator + admin actions but is
  gated by SPA UX ("archive" is the primary affordance; "delete
  permanently" is a secondary confirm-heavy action).
- Archived Universes: the API `list` endpoint (see §API contract)
  filters `archived_at__isnull=True` by default; an
  `?include_archived=true` query surfaces archived rows.
- Archived Universe children behavior: Teammates and Knowledge Docs
  retain their `universe_id` FK. Retrieval and synthesis continue to
  scope by Universe (an archived Universe is still THE Universe of
  its members; archive is a display concern, not a semantic
  regression). If the operator wants members to fall back to legacy,
  they explicitly reassign each member to `universe=None`.

### Teammate move between Universes

**v1 policy: permitted, but validated.** See §"Teammate move" below.

## Retrieval truth table

Rows enumerate every combination of `(Teammate.universe present/NULL)
× (KnowledgeDocument.universe present/NULL) × (spokespeople M2M state
for that doc)`. Result column names the retrieval outcome: **VISIBLE**
= chunk MAY be returned by `retrieve_for_teammate` (subject to cosine
distance); **NOT VISIBLE** = chunk is structurally unreachable.

Let `T` = the Teammate calling `retrieve_for_teammate(T, ...)`.
Let `D` = a candidate KnowledgeDocument in the same Workspace as `T`
(cross-workspace docs are already NOT VISIBLE by invariant #1).

| # | `T.universe` | `D.universe` | `D.spokespeople` M2M | Result | Rationale |
|---|---|---|---|---|---|
| 1 | NULL (legacy) | NULL (legacy) | empty | **VISIBLE** | Preserves today's legacy semantics exactly. |
| 2 | NULL (legacy) | NULL (legacy) | contains `T` | **VISIBLE** | Character-owned attach; today's semantics. |
| 3 | NULL (legacy) | NULL (legacy) | non-empty; excludes `T` | **NOT VISIBLE** | Doc scoped to other legacy characters. |
| 4 | NULL (legacy) | `U_X` | (any M2M) | **NOT VISIBLE** | Universe-scoped docs are unreachable to legacy teammates. Prevents leakage of new Universe content back into legacy contexts. |
| 5 | `U_X` | NULL (legacy) | (any M2M) | **NOT VISIBLE** | **Load-bearing legacy isolation.** A Universe-scoped teammate never retrieves from workspace-wide legacy docs. Closes the SESSION 259 audit §6 leak class. |
| 6 | `U_X` | `U_X` | empty | **VISIBLE** | Empty M2M means "visible to every teammate in this Universe" (invariant #5). |
| 7 | `U_X` | `U_X` | contains `T` | **VISIBLE** | Character-owned attach within the Universe. |
| 8 | `U_X` | `U_X` | non-empty; excludes `T` | **NOT VISIBLE** | Doc scoped to other characters in the same Universe. |
| 9 | `U_X` | `U_Y` (X ≠ Y) | (any M2M) | **NOT VISIBLE** | Universe boundary. Cosine distance is irrelevant. |

**Predicate expressing rows 1–9 in one ORM filter.** Applied inside
`retrieve_for_teammate`, following the existing workspace filter and
before the visibility M2M filter:

```
qs = (
    KnowledgeChunk.objects.filter(
        document__workspace=T.workspace,
        document__is_active=True,
        document__status="processed",
    )
    .filter(document__universe=T.universe)   # <-- new; NULL = NULL match
    .filter(
        Q(document__spokespeople__isnull=True)
        | Q(document__spokespeople=T)
    )
    .distinct()
    .annotate(distance=CosineDistance("embedding_vector", vector))
    .order_by("distance")
)
```

**Why `document__universe=T.universe` works for NULL=NULL match:**
Django's ORM emits `document.universe_id = NULL` when `T.universe` is
NULL, which SQL treats as NEVER true — the wrong behavior. The
implementation MUST use `Q(document__universe=T.universe) if T.
universe_id else Q(document__universe__isnull=True)` OR the ORM's
`.filter(document__universe_id=T.universe_id)` form, which does emit
`= NULL` incorrectly — same trap. **The load-bearing implementation
form** (this is the schema contract):

```
if T.universe_id is None:
    qs = qs.filter(document__universe__isnull=True)
else:
    qs = qs.filter(document__universe_id=T.universe_id)
```

This branching MUST be inside `retrieve_for_teammate` and MUST NOT
appear at any callsite. Callsites do not gain a new parameter.

## clean() / m2m_changed / signal contract

### `Universe.clean()`

- Validates `name.strip() != ""`.
- Validates `slug` matches `slugify(name)` when slug was
  auto-derived (v2 override affordance is deferred).

### `Teammate.clean()` — new addition

Extension to whatever `Teammate.clean()` looks like today (no
existing `clean` method per source review — this is a new one).

```
def clean(self):
    super().clean()
    if self.universe_id is not None and self.workspace_id is not None:
        if self.universe.workspace_id != self.workspace_id:
            raise ValidationError({
                "universe": (
                    f"Universe {self.universe.name!r} belongs to workspace "
                    f"{self.universe.workspace_id}, but this teammate is in "
                    f"workspace {self.workspace_id}."
                ),
            })
```

### `KnowledgeDocument.clean()` — extension of the existing method

Existing method at `embeddings/models.py:230–245` already validates
cross-workspace M2M. Extension adds two checks:

1. Universe-workspace consistency:

```
if self.universe_id is not None and self.workspace_id is not None:
    if self.universe.workspace_id != self.workspace_id:
        raise ValidationError({
            "universe": (
                f"Universe belongs to workspace "
                f"{self.universe.workspace_id}, but this document is in "
                f"workspace {self.workspace_id}."
            ),
        })
```

2. Universe-M2M consistency (for saved documents; the m2m_changed
   signal below catches the post-save attach case):

```
if self.pk and self.universe_id is not None:
    bad = self.spokespeople.exclude(universe_id=self.universe_id)
    if bad.exists():
        names = ", ".join(sp.name for sp in bad[:3])
        raise ValidationError({
            "spokespeople": (
                f"Spokespeople must belong to this document's Universe. "
                f"Bad: {names}"
            ),
        })
```

### `apps/embeddings/signals.py` — extension

Existing `reject_cross_workspace_spokesperson` receiver at line 31–79
extends to also reject cross-Universe attaches. **New receiver name
proposed:** `reject_cross_universe_spokesperson` (a peer receiver,
not a modification of the existing one — cleaner separation of
concerns, easier to test each invariant in isolation).

Contract (signal on `KnowledgeDocument.spokespeople.through`, action
`pre_add` only):

- Forward (`doc.spokespeople.add(sp)`): for every `sp` in `pk_set`, if
  `doc.universe_id is not None` and `sp.universe_id != doc.universe_id`,
  raise `ValidationError`.
- Reverse (`sp.knowledge_documents.add(doc)`): symmetric — for every
  `doc` in `pk_set`, if `sp.universe_id is not None` and
  `doc.universe_id != sp.universe_id`, raise `ValidationError`.
- Special case: `sp.universe IS NULL AND doc.universe IS NULL` is
  allowed (legacy pairing, invariant #5 row 2).
- Special case: `sp.universe IS NULL AND doc.universe IS NOT NULL` is
  **rejected** (attaching a legacy teammate to a Universe doc). To
  make this pairing legal, the operator must first assign the teammate
  to the same Universe.
- Special case: `sp.universe IS NOT NULL AND doc.universe IS NULL` is
  **rejected** (attaching a Universe teammate to a legacy doc). Same
  remediation.

The existing `reject_cross_workspace_spokesperson` receiver remains
unchanged and continues to fire first (workspace is the outer wall).

## API contract

### `GET /api/universes/`

Query params: `?workspace=<uuid>` (optional; defaults to all
Universes visible to the caller — i.e., in a Workspace the caller is
a Member of). `?include_archived=<bool>` (default `false`).

Response: DRF list envelope `{count, next, previous, results:
[UniverseSerializer, ...]}` or bare array (SPA client already handles
both, see `web/src/lib/api/knowledge.ts:79–92`).

`UniverseSerializer` shape:

```
{
  "id": "<uuid>",
  "workspace": "<uuid>",
  "workspace_name": "<str>",
  "name": "<str>",
  "slug": "<str>",
  "description": "<str>",
  "created_by": "<uuid|null>",
  "created_at": "<iso8601>",
  "updated_at": "<iso8601>",
  "archived_at": "<iso8601|null>",
  "teammate_count": <int>,
  "knowledge_document_count": <int>
}
```

Permission: `IsWorkspaceMember` (existing pattern).

### `POST /api/universes/`

Body:

```
{
  "workspace": "<uuid>",   // required; caller must be Member
  "name": "<str>",         // required; ≤ 120 chars
  "description": "<str>"   // optional
}
```

`slug` is derived server-side. `created_by` is derived from the
authenticated user.

Response: `201` + `UniverseSerializer`. Errors:
- `400` — missing/blank name; caller not a workspace member;
  workspace not found.
- `409` — slug collision with existing active Universe in workspace
  (auto-suffix like Workspace.save uses — mirror
  `accounts/models.py:133–142`). If auto-suffix succeeds, no 409;
  return `201`.

### `GET /api/universes/{id}/`

Detail view. Same serializer as list. `404` if archived and
`?include_archived=false` and caller is not admin.

### `PATCH /api/universes/{id}/`

Body: any subset of `{name, description}`. `slug` re-derives from
name only if `slug` is currently the auto-derived form; operator
overrides deferred to v2. `archived_at` updates via a dedicated
action (below), not PATCH — mirrors the K2 soft-delete pattern
(`embeddings/views.py:99–107`).

### `DELETE /api/universes/{id}/`

Soft-delete: sets `archived_at = now()`. Returns `204`. Hard-delete
via `?hard=true` param requires operator to be workspace `owner`; on
hard delete, Universe row goes away and children (Teammates,
KnowledgeDocuments) SET_NULL on `universe_id`.

### `POST /api/universes/{id}/unarchive/`

Sets `archived_at = NULL`. Returns updated serializer.

### `PATCH /api/spokespeople/{id}/`

**Existing endpoint** (`shell/apps/spokespeople/views.py:242`).
Serializer extended with optional `universe: UUID | null` field.
- `universe` payload MUST refer to a Universe in the same Workspace
  as the Teammate; validation via serializer + `Teammate.clean()`.
- Setting `universe: null` moves the Teammate to legacy state (see
  §Teammate move policy for guardrails).
- Setting `universe: "<uuid>"` moves the Teammate into that Universe
  (see §Teammate move policy for guardrails).

### `POST /api/knowledge/`

**Existing endpoint** (`shell/apps/embeddings/views.py:48`).
`CreateKnowledgePayload` extended with optional `universe: UUID |
null`.
- If `universe` omitted OR explicit `null`: doc created with
  `universe_id=NULL` (legacy).
- If `universe` present: doc created with that Universe, subject to
  clean() workspace-consistency check.
- Spokesperson-IDs list validation extended: if `universe` present,
  every teammate in `spokesperson_ids` MUST have `universe_id ==
  payload.universe`.
- The upload flow proposed in §SPA operator workflow ALWAYS sends
  the payload's `universe` explicitly (empty string treated as null;
  actual UUID otherwise) so the operator cannot accidentally skip
  it.

### `PATCH /api/knowledge/{id}/`

**Existing endpoint.** Serializer extended with optional `universe`
field. Reassigning a doc between Universes is legal if:
- Target Universe in same workspace.
- No existing spokespeople M2M row would become cross-Universe. If
  it would, the PATCH is rejected with `400` and a list of the
  offending M2M rows.

### `POST /api/knowledge/{id}/attach/`, `POST /api/knowledge/{id}/detach/`

**Existing endpoints** (line 111–169). No signature change. Attach
side gains Universe-consistency check (see §clean contract).

### Endpoints that MUST change (list explicitly)

1. `TeammateSerializer` — add `universe` write+read field.
2. `KnowledgeDocumentSerializer.Meta.fields` — add `universe`.
3. `KnowledgeDocumentViewSet.get_queryset` — accept optional
   `?universe=<uuid>` filter (mirrors `?spokesperson=<uuid>`).
4. `TeammateViewSet.get_queryset` — accept optional
   `?universe=<uuid>` filter (net-new filter surface).
5. `retrieve_for_teammate` — the branching predicate above; no
   signature change.
6. New URL routes for `/api/universes/`.

### Endpoints whose contract MUST NOT change (backward compatibility)

- `/api/me/` — no Universe context here (operator's default
  workspace remains the primary orient).
- `/api/spokespeople/` list without `?universe=` query param —
  returns all workspace-visible teammates including legacy AND
  Universe-scoped. Silent scoping to a specific Universe is
  forbidden — the operator picks.
- `/api/knowledge/` list without `?universe=` query param — returns
  all workspace-visible docs including legacy AND Universe-scoped.
- `POST /api/spokespeople/` create without `universe` payload —
  creates a legacy teammate (`universe=NULL`). Nothing implicit.
- `POST /api/knowledge/` create without `universe` payload — creates
  a legacy workspace-wide doc. **This is the failure mode the SPA
  vertical-slice must eliminate at the UX layer** — the backend
  behavior is deliberately preserved for API contract stability, but
  the SPA MUST NOT expose an "upload without picking scope" path.
- Every existing 4xx/5xx contract on
  `KnowledgeDocumentViewSet.attach/detach` — extends with a new
  400 case for cross-Universe attach; existing cases unchanged.

## SPA operator workflow

**Rule (restated):** SPA changes land in the same slice as the
schema. Splitting is forbidden.

### Create Universe

- **Route:** `/workspace/universes` (list) and
  `/workspace/universes/new` (create form).
- **Component:** `UniverseListRoute` + `UniverseCreateModal` (or
  dedicated route — either shape is acceptable; the load-bearing
  requirement is the operator can invoke create from at least one
  existing surface).
- **Form fields:** `name` (required), `description` (optional).
- **API:** `POST /api/universes/` with `{workspace: default_workspace
  .id, name, description}`.
- **Success:** navigate to `/workspace/universes/{new_id}` (detail
  view — see below).
- **Nav integration:** an entry point from `/dashboard` or
  `/workspace/knowledge` (a "Worlds" or "Universes" tile / link);
  full new nav-rail section deferred to a future scope-lock per F0
  contract rule 7. v1 lands the routes without a nav-rail slot.

### Assign Teammate to Universe

- **Route:** existing `/spokespeople/{id}` (`web/src/routes/
  spokespeople/$id.tsx`).
- **Component:** existing `SpokespersonEditModal` (or a dedicated
  `SpokespersonUniverseSection` panel below identity fields).
- **Control shape:** a labeled select — "World / Universe" — with
  options: "— None (legacy) —" plus every non-archived Universe in
  the Teammate's Workspace. Default = current value from the
  Spokesperson row.
- **API:** `PATCH /api/spokespeople/{id}/` with `{universe: "<uuid>"
  | null}`.
- **Load-bearing UX guard:** when the operator switches a Teammate
  from Universe A to Universe B (or A → null, or null → A), the SPA
  MUST run a pre-flight check via a new
  `GET /api/spokespeople/{id}/universe-move-preview/?target=<uuid|
  null>` endpoint (see §Teammate move policy below) that returns the
  list of KnowledgeDocument M2M rows that would become cross-Universe.
  If non-empty, the SPA shows a confirmation modal ("These K2 attach
  rows will be removed: ...") and the PATCH does not proceed until
  the operator confirms — because the PATCH itself will reject via
  `.clean()` if the pre-flight was skipped and there is an offending
  M2M.

### Upload Knowledge with Universe scope

- **Route:** `/workspace/knowledge` (existing). PLUS a new inbound
  path from the Teammate detail page "Add knowledge" affordance
  (already implied by `KnowledgePanel` at
  `web/src/components/knowledge-panel.tsx`; the panel gains a
  Universe defaulting rule described below).
- **Form fields:** existing (paste, upload, url, search) PLUS a new
  required field:
  - **"World"** — select control at the top of the upload form.
  - Options: `— None (legacy — visible to workspace-wide legacy
    teammates only) —` + every non-archived Universe in the current
    workspace.
  - When invoked from Teammate detail page (via `KnowledgePanel`),
    the default is the Teammate's current `universe` (Universe or
    "None").
  - When invoked from `/workspace/knowledge`, the default is
    **explicitly unset** — the operator MUST pick before submit. This
    is the load-bearing safeguard: it converts today's silent
    workspace-wide default into an explicit operator gesture.
- **API:** `POST /api/knowledge/` with `{workspace, universe, title,
  ..., spokesperson_ids}`.
- **Additional load-bearing SPA guard:** when the operator picks a
  Universe on the upload form, the visible list of teammates
  available for M2M attach is filtered to that Universe's teammates
  only. This mechanically prevents cross-Universe M2M attach.
- **Legacy path preserved:** the "None (legacy)" option keeps the
  workspace-wide behavior for operators who want it (Mike, Repo Red,
  Tulsi era). But it is now an explicit choice, not an accidental
  default.

### Where the workspace-wide silent default is REMOVED and what replaces it

- **REMOVED:** the current default at
  `web/src/routes/workspace/knowledge.tsx:203, 294, 377` — every
  `create.mutateAsync({workspace, ..., text_content|pdf_data_uri
  |source_url_input})` call currently omits `spokesperson_ids` AND
  will now be updated to require the operator to pick `universe`
  (or explicitly "None").
- **REPLACED WITH:** required select control on the upload form.
  Submit button disabled until the select is populated with either
  a Universe or the explicit "None" sentinel.
- **BACKEND STAYS BACKWARDS-COMPATIBLE:** an API caller that omits
  `universe` still gets a legacy doc created. This preserves external
  API stability while removing the SPA-side accident vector.

## Migration classification

Per `UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §Q28`:

- **Nullable-prospective (no backfill):**
  - `Universe` — new table; empty at introduction.
  - `Teammate.universe` — nullable FK; NULL for every existing row.
  - `KnowledgeDocument.universe` — nullable FK; NULL for every
    existing row.
- **No-backfill invariants:** no historical rows are moved. `chriss-
  workspace`'s seven teammates, fourteen docs, eighty-one
  compositions, three-hundred-twenty-two assets stay put and
  legacy-shaped.
- **Future cleanup (per-item bespoke ½-slices):** migrating specific
  historical Teammates into a Universe (Mike into a hypothetical
  "Riverstone" Universe; Patch/Rivet into a "Workshop" Universe;
  etc.). Each migration is a bespoke ½-slice per SESSION 259 audit
  §9 recommendation. Not shipped by this slice.

**Migration file names (proposed — this slice does not write them):**

- `shell/apps/universe/migrations/0001_initial.py` — creates the
  Universe model.
- `shell/apps/spokespeople/migrations/0012_universe_fk.py` — adds
  `Teammate.universe` nullable FK. Follows current head
  `0011_session253_backfill_voice_defaults.py`.
- `shell/apps/embeddings/migrations/0005_universe_fk.py` — adds
  `KnowledgeDocument.universe` nullable FK. Follows current head
  `0004_session251_pin_m2m_through_column.py`.

Each migration is additive; no data migration required.

## Implementation file map

### Backend

- `shell/apps/universe/` — new app.
  - `__init__.py`
  - `apps.py` — `UniverseConfig(default_auto_field="django.db.models
    .BigAutoField", name="apps.universe")`.
  - `models.py` — `Universe` model as specified above.
  - `serializers.py` — `UniverseSerializer`.
  - `views.py` — `UniverseViewSet` (DRF ModelViewSet) with
    `unarchive` custom action + `universe-move-preview` on
    `TeammateViewSet` (co-located per DRF convention — actually
    placed on `TeammateViewSet` since it operates on Teammate; see
    below).
  - `urls.py` — `router.register(r"universes", UniverseViewSet,
    basename="universe")`.
  - `admin.py` — `UniverseAdmin` with list/search on name+slug,
    filter on workspace and archived_at.
  - `migrations/__init__.py`, `migrations/0001_initial.py`.
  - `tests/` — see §Test matrix.
- `shell/character_os/settings.py` — add `"apps.universe"` to
  `INSTALLED_APPS` (position immediately after `"apps.identity"` or
  next to `"apps.accounts"` — either is fine; `"apps.accounts"`
  vicinity is preferable so `apps.universe` sits with its tenant
  parent).
- `shell/character_os/urls.py` — add `path("api/", include("apps.
  universe.urls"))`.
- `shell/apps/spokespeople/models.py` — add `universe` FK; extend
  `Teammate.clean` (new method).
- `shell/apps/spokespeople/serializers.py` — add `universe` to
  `TeammateSerializer.Meta.fields`; validate on
  `validate_universe`.
- `shell/apps/spokespeople/views.py` — add `?universe=` filter to
  `TeammateViewSet.get_queryset`; add `@action(detail=True,
  methods=["get"], url_path="universe-move-preview")`.
- `shell/apps/spokespeople/migrations/0012_universe_fk.py` — the
  migration.
- `shell/apps/embeddings/models.py` — add `universe` FK; extend
  existing `KnowledgeDocument.clean`.
- `shell/apps/embeddings/serializers.py` — add `universe` to
  `Meta.fields` + validation.
- `shell/apps/embeddings/views.py` — add `?universe=` filter.
- `shell/apps/embeddings/signals.py` — add
  `reject_cross_universe_spokesperson` receiver (peer to existing
  receiver).
- `shell/apps/embeddings/retrieval.py` — branching Universe predicate
  inside `retrieve_for_teammate`; no signature change.
- `shell/apps/embeddings/migrations/0005_universe_fk.py` — the
  migration.

### SPA

- `web/src/lib/api/universes.ts` — new; TanStack Query wrappers for
  `list`, `get`, `create`, `update`, `archive`, `unarchive`.
- `web/src/lib/api/spokespeople.ts` — extend `Spokesperson` schema
  with `universe: string | null`; add PATCH method for universe
  assignment + `useUniverseMovePreview` hook.
- `web/src/lib/api/knowledge.ts` — extend `KnowledgeDocument` schema
  with `universe: string | null`; extend `CreateKnowledgePayload`
  and `UpdateKnowledgePayload` with `universe`.
- `web/src/routes/workspace/universes.tsx` — new list route.
- `web/src/routes/workspace/universes.$id.tsx` — new detail route
  (member characters, member documents, archive action).
- `web/src/routes/workspace/knowledge.tsx` — upload form gains
  required Universe select at the top of each of the four tabs.
- `web/src/routes/spokespeople/$id.tsx` — Universe select control
  in the identity panel (or the edit modal — either shape is
  acceptable).
- `web/src/components/knowledge-panel.tsx` — when rendered on
  Teammate detail, the "Add knowledge" affordance passes the
  Teammate's Universe as the default upload scope.

## Test matrix

### Unit tests (models, clean, signals)

- `apps/universe/tests/test_models.py`
  - Create Universe with valid workspace/name; assert slug derived.
  - Slug collision auto-suffix within a workspace; slug uniqueness
    across workspaces (same slug in two workspaces is legal).
  - Slug uniqueness within a workspace is enforced.
  - `archived_at` default NULL; setting non-NULL then unarchiving.
- `apps/universe/tests/test_clean.py`
  - `Universe.clean()` rejects blank name.
- `apps/spokespeople/tests/test_teammate_universe.py`
  - `Teammate.clean()` rejects cross-workspace Universe FK.
  - `Teammate.clean()` accepts NULL Universe (legacy).
  - `Teammate.clean()` accepts matching-workspace Universe.
- `apps/embeddings/tests/test_document_universe.py`
  - `KnowledgeDocument.clean()` rejects cross-workspace Universe FK.
  - `KnowledgeDocument.clean()` rejects M2M spokespeople whose
    Universe differs from doc's Universe.
- `apps/embeddings/tests/test_signals_universe.py`
  - `reject_cross_universe_spokesperson` fires on forward attach
    (`doc.spokespeople.add(sp)`) with mismatched Universe.
  - Fires on reverse attach (`sp.knowledge_documents.add(doc)`).
  - Does NOT fire when both sides are NULL (legacy pairing).
  - Does NOT fire when both sides match.
  - Fires when doc.universe present but sp.universe NULL.
  - Fires when sp.universe present but doc.universe NULL.

### Integration tests (retrieval predicates)

- `apps/embeddings/tests/test_retrieval_universe.py`
  - Row 1: legacy T + legacy D + empty M2M → VISIBLE.
  - Row 2: legacy T + legacy D + M2M contains T → VISIBLE.
  - Row 3: legacy T + legacy D + M2M excludes T → NOT VISIBLE.
  - Row 4: legacy T + Universe D + any M2M → NOT VISIBLE.
  - Row 5 (**load-bearing**): Universe T + legacy D + any M2M →
    NOT VISIBLE.
  - Row 6: Universe T + same-Universe D + empty M2M → VISIBLE.
  - Row 7: Universe T + same-Universe D + M2M contains T → VISIBLE.
  - Row 8: Universe T + same-Universe D + M2M excludes T → NOT
    VISIBLE.
  - Row 9 (**load-bearing**): Universe T + other-Universe D + any
    M2M → NOT VISIBLE regardless of cosine distance.
- The existing `test_retrieval_privacy.py` cross-workspace tests
  MUST continue to pass verbatim.

### API tests (endpoints, authorization)

- `apps/universe/tests/test_api.py`
  - `POST /api/universes/` — create by workspace member succeeds.
  - `POST /api/universes/` — create by non-member 403.
  - `POST /api/universes/` — duplicate name auto-suffix slug; assert
    both rows exist with different slugs.
  - `GET /api/universes/?workspace=<uuid>` — returns only that
    workspace's Universes.
  - `GET /api/universes/?include_archived=true` — includes archived.
  - `PATCH` — rename Universe.
  - `DELETE` (soft) — sets `archived_at`.
  - `POST /api/universes/{id}/unarchive/` — clears `archived_at`.
  - `DELETE ?hard=true` — permanent delete; SET_NULL cascades to
    Teammate.universe and KnowledgeDocument.universe.
- `apps/spokespeople/tests/test_teammate_universe_api.py`
  - `PATCH /api/spokespeople/{id}/ {universe: "<uuid>"}` — success.
  - Same PATCH with cross-workspace Universe UUID — 400.
  - `PATCH ... {universe: null}` — reverts to legacy.
  - `GET /api/spokespeople/{id}/universe-move-preview/?target=<uuid>`
    — returns list of would-be-orphaned M2M rows.
- `apps/embeddings/tests/test_knowledge_universe_api.py`
  - `POST /api/knowledge/ {universe, ...}` — success.
  - `POST ... {universe, spokesperson_ids: [<cross-Universe sp>]}`
    — 400.
  - `POST /api/knowledge/{id}/attach/ {spokesperson_id: <cross-
    Universe>}` — 400 with signal-driven error message.
  - `?universe=<uuid>` filter — returns only that Universe's docs.

### SPA E2E tests (Workshop scenario + two-Universe isolation)

Playwright tests under `web/e2e/universe/`:

- **Test A — Workshop happy path (single Universe):**
  1. Log in as operator; navigate to
     `/workspace/universes/new`.
  2. Fill name = "Workshop"; submit; assert 201 and redirect to
     `/workspace/universes/{id}`.
  3. Navigate to Patch's detail; open Universe select; pick
     "Workshop"; save; assert PATCH 200.
  4. Navigate to `/workspace/knowledge`; on the Paste tab, verify
     the Universe select control exists AND submit is disabled
     until it's set; pick "Workshop"; fill title = "About the
     Workshop" + content; submit; assert 201.
  5. Trigger a talking-head Composition with Patch (using existing
     recipe UX); assert Composition completes.
  6. Inspect the resulting Composition's `knowledge_chunk_ids`;
     assert every chunk resolves to the "About the Workshop" doc.
  7. Retrieve TANK / Tulsi / Hearth&Hollow chunks are NOT among
     the surfaced set (they remain legacy, and Patch is now
     Universe-scoped — row 5 of the truth table).
  8. Confirm a legacy teammate (e.g., Mike or Tulsi) still renders
     with legacy retrieval semantics — pick Mike, trigger a
     Composition, assert legacy chunks surface as before.

- **Test B — Two-Universe cosine isolation:**
  1. Create Universe "Workshop" (already exists from Test A) and
     Universe "Bakery" in the same workspace.
  2. Assign Ruby the Fox to Bakery (create Ruby if not present).
  3. Upload two docs with **intentionally identical content** —
     one to Workshop ("About the Workshop"), one to Bakery ("About
     the Workshop-styled Bakery"). Verify docs land under
     different `universe_id`s.
  4. Trigger a Composition for Patch (Workshop) with a topic
     designed to cosine-match both docs' embeddings.
  5. Assert `Composition.knowledge_chunk_ids` includes ONLY the
     Workshop doc's chunks.
  6. Trigger the same Composition topic for Ruby (Bakery).
  7. Assert `Composition.knowledge_chunk_ids` includes ONLY the
     Bakery doc's chunks.
  8. Adversarial payload: attempt to attach the Bakery doc to
     Patch via `POST /api/knowledge/{bakery_id}/attach/
     {spokesperson_id: patch_id}`; assert 400 with cross-Universe
     error message.

### Legacy regression tests

Named because they carry the highest regression risk:

- `apps/embeddings/tests/test_retrieval_privacy.py` — every existing
  cross-workspace test.
- `apps/embeddings/tests/test_api_k5.py` — every attach/detach test.
- `apps/embeddings/tests/test_m2m_through_column_contract.py` — the
  `spokesperson_id` DB column contract.
- `apps/spokespeople/tests/test_ask.py`,
  `test_personality_sync.py`, `test_identity_fields.py`,
  `test_delete.py`, `test_rebake_avatar.py`,
  `test_step4d_canonical_migration.py`,
  `test_voice_presets_endpoint.py`.
- `apps/compositions/tests/test_dialogue_synthesis.py`,
  `test_v14_dialogue.py`, `test_dialogue_ai_topic_wiring.py`,
  `test_session260_dialogue_cps_calibration.py`.
- `apps/realtime/tests/test_r4_knowledge_bridge.py`,
  `test_r6_session_memory.py`, `test_r7_3_attach_memory.py`.
- `apps/conversations/tests/test_embed_message.py`,
  `test_k9_messages.py`.
- `apps/videos/tests/test_script_synthesis.py`.

Every one of these must pass unchanged after the Universe FK
addition. Any regression is a bug in the implementation slice.

## Legacy compatibility matrix

| Legacy behavior | Post-Universe behavior | Change? |
|---|---|---|
| Legacy Teammate created without `universe` payload | `universe=NULL`; retrieval + M2M behave as today (rows 1–3 of truth table) | None |
| Legacy KnowledgeDocument created without `universe` payload | `universe=NULL`; empty M2M = "workspace-wide visible to legacy teammates only" | Tightened: workspace-wide default now excludes Universe-scoped teammates (row 4). No regression for pure-legacy workspace. |
| `retrieve_for_teammate(legacy_T, ...)` returns legacy chunks | Unchanged (rows 1, 2 remain VISIBLE) | None |
| `retrieve_for_teammate(legacy_T, ...)` returning workspace-wide chunk from a Universe-scoped doc | NOT VISIBLE (row 4) | Regression **prevented**: if the operator has both regimes in the same workspace, legacy teammates cannot accidentally pick up Universe corpus. This is desired. |
| `doc.spokespeople.add(sp)` cross-workspace | 400 via existing signal | None |
| `doc.spokespeople.add(sp)` cross-Universe | 400 via new peer signal | New behavior (added invariant #4) |
| SPA knowledge upload silently sending `spokesperson_ids=[]` | Now requires operator to pick Universe explicitly | SPA behavior change; API remains backward-compatible |
| Composition provenance (spokesperson.workspace divergence) | Unchanged — Universe FK does not touch Composition | None |
| GenerationRecord / NormalizationManifest / IdentityReference cross-workspace guards | Unchanged | None |
| Workspace deletion CASCADE to all children | Unchanged, plus Universe CASCADEs with Workspace | Adds one more child cascade |
| Content_hash dedup `(workspace, content_hash)` | Unchanged | None |
| Teammate naming uniqueness `(workspace, name)` | Unchanged | None |
| `IsWorkspaceMember` permission on every viewset | Unchanged; extends to new `/api/universes/` | Extended, not changed |

## Failure modes / blast-radius analysis

Prioritized by likelihood × impact.

1. **SPA lands after backend, exposing silent workspace-wide default
   at Universe scope.** Highest blast radius. Every operator upload
   would default to legacy despite the operator's intent being
   Universe-scoped. Mitigation: this contract mandates SPA+backend
   are one deployable slice.
2. **`retrieve_for_teammate` NULL match implemented via
   `.filter(document__universe=T.universe)` instead of the branched
   form.** Django would emit `= NULL`, causing legacy retrieval to
   return zero rows silently. Mitigation: the branched form is
   spelled out in the retrieval truth table section and MUST be
   asserted by `test_retrieval_universe.py` row 1.
3. **Signal receiver name collides with existing receiver.**
   Existing receiver `reject_cross_workspace_spokesperson` uses
   `@receiver(m2m_changed, sender=KnowledgeDocument.spokespeople.
   through)`. A second `@receiver` on the same signal + sender is
   legal in Django (both fire in registration order). Mitigation:
   distinct receiver names; the test suite asserts BOTH fire on
   BOTH violations.
4. **Universe deletion cascades destroy Teammate/KnowledgeDocument
   rows.** Would happen if `on_delete=CASCADE` was chosen instead of
   `SET_NULL`. Mitigation: this contract mandates `SET_NULL` on both
   FKs. The test suite explicitly asserts hard-delete preserves
   child rows.
5. **Teammate move between Universes silently orphans K2 M2M rows.**
   Would happen if PATCH did not pre-validate. Mitigation:
   `universe-move-preview` endpoint + SPA confirmation modal + PATCH
   rejects on `.clean()`.
6. **Migration ordering wrong (embeddings migration references
   Universe before Universe app is created).** Django migration
   dependencies handle this if the FK is `"universe.Universe"`
   (string form) and the migrations declare
   `dependencies=[("universe", "0001_initial")]`. Mitigation: named
   in migration file map above.
7. **Universe row created but `apps.universe` not in
   `INSTALLED_APPS`.** Migration would not be discovered. Mitigation:
   INSTALLED_APPS addition named in the file map.
8. **Empty-M2M row 6 wrongly matches ALL universe-scoped teammates
   in the workspace including cross-Universe** if the retrieval
   predicate order is wrong. Mitigation: the retrieval predicate in
   the truth-table section applies the universe filter BEFORE the
   M2M visibility filter, so empty-M2M is scoped to `document.
   universe = T.universe`.
9. **Test fixture uses `Workspace.objects.create` but not
   `Universe.objects.create` and forgets to null-explicitly set
   `Teammate.universe`.** Fixture would fail with UNIQUE / NOT NULL
   errors if the FK was declared non-nullable. Mitigation: FK is
   nullable in the contract.
10. **DRF serializer coerces missing `universe` field to `null`
    silently on PATCH, wiping the Teammate's Universe FK.**
    Mitigation: use `serializers.PrimaryKeyRelatedField(
    allow_null=True, required=False)` and rely on DRF's "field
    absent" vs "field explicitly null" distinction; the API contract
    documents that absent means "no change" and explicit `null`
    means "detach."

## Explicit deferrals (what this slice does NOT do)

- Episode model, `Composition.episode` FK, Episode lifecycle
  (`EPISODE_VS_COMPOSITION_V1.md`, `EPISODE_LIFECYCLE_V1.md`).
- Relationship model (Character↔Character edges)
  (`RELATIONSHIP_BOUNDARY_V1.md`).
- WorldEntity model, `Episode.referenced_entities` M2M
  (`WORLD_ENTITY_BOUNDARY_V1.md`).
- Narrative memory / event log / promise ledger.
- Character↔WorldEntity edges.
- WorldEntity↔WorldEntity edges.
- Canon promotion mechanic.
- Educational curriculum substrate.
- Per-Universe palette / brand identity (extending CSS-var brand
  swap to per-Universe).
- Cross-Universe crossover primitive.
- Voice / POV versioning on Teammate.
- Non-human canonical identity via Character Presence Language
  (blocks Patch/Rivet/Biscuit fully-approved CharacterIdentity —
  named blocker, not addressed here).
- Legacy bulk cleanup / migration (per-Teammate bespoke ½-slices
  only).
- `Composition.universe` direct FK (transitive via
  `spokesperson.universe` suffices for v1 per
  `UNIVERSE_BOUNDARY_V1.md §Q4/§Q5`).
- `Asset.universe` FK — Assets remain workspace-scoped pixels/audio.
- Slug uniqueness reform on Workspace (SESSION 259 wart §8;
  unrelated to this slice).
- SPA workspace picker (SESSION 259 audit §2 — pre-existing gap;
  not addressed here).
- Membership sub-scoping (per-Universe seats/roles) — Workspace
  membership continues to govern.
- Universe visual identity (any Universe-specific styling).
- Universe-per-owner / cross-workspace Universe primitive.
- Bulk API for creating multiple Universes / assigning multiple
  Teammates at once.

## Implementation sequencing within this slice

Each step is deployable on its own (green tests + safe rollback);
the whole slice is not deployable until step 6.

1. **Create `apps/universe/` app skeleton + Universe model +
   migration + admin.** Register in INSTALLED_APPS and URLs. Ship
   with `test_models.py` + `test_clean.py` + `test_api.py`. Green
   tests. No downstream effect because no other model FKs to it
   yet.
2. **Add `Teammate.universe` nullable FK + migration + `Teammate.
   clean()` extension + serializer field + `?universe=` filter.**
   Ship with `test_teammate_universe.py`. Legacy regressions must
   pass. No retrieval change yet.
3. **Add `KnowledgeDocument.universe` nullable FK + migration +
   `KnowledgeDocument.clean()` extension + serializer field +
   `?universe=` filter + new signal receiver.** Ship with
   `test_document_universe.py` + `test_signals_universe.py`.
   Legacy regressions must pass. No retrieval change yet.
4. **Retrieval predicate change (`retrieve_for_teammate` branch).**
   Ship with `test_retrieval_universe.py` covering all nine truth-
   table rows. Legacy `test_retrieval_privacy.py` must pass
   unchanged.
5. **Teammate-move preview endpoint + PATCH validation.** Ship with
   `test_teammate_universe_api.py`. No SPA yet.
6. **SPA slice** — all UX changes named in §SPA operator workflow.
   Ship with the Playwright suite (Test A + Test B). E2E green.
   THIS is the moment the vertical slice is deployable end-to-end.

Steps 1–5 are safely additive; each is behind an API surface that
returns identical semantics for pure-legacy callers. Step 6 unlocks
operator UX. Steps 1–5 must land AS a group in one deploy window
(they build on each other); step 6 immediately follows in the same
deploy window.

## STOP/GO recommendation

**GO** on this slice, subject to two hard preconditions:

1. **Vertical-slice discipline.** Steps 1–6 above land in one deploy
   window. The backend does not ship to production without the SPA
   changes. If the SPA is not ready, the backend does not ship.
2. **`Teammate.clean()` addition MUST be net-new (not shadowing an
   existing one).** Source review confirmed `Teammate` has no
   `clean` method today. If a `clean` method is added between now
   and implementation, the addition MUST call `super().clean()` and
   MUST NOT redefine any invariant added between now and then.

**No contradictions with prior slices were discovered** during this
schema design pass. The integration checkpoint's GO verdict (with
sequencing steps 1+2) is confirmed at the schema-contract level.

### Named blocking dependencies (informational only — do NOT block
this slice on them)

- **Non-human Character Presence Language** — a substrate
  dependency for fully-approving Patch, Rivet, Biscuit as canonical
  CharacterIdentity. This slice does not require CPL because
  Universe FK sits on Teammate, not on CharacterIdentity. Patch and
  Rivet can be assigned to a Universe today via `Teammate.universe`
  without needing a canonical CharacterIdentity.
- **Composition observability backlog** (SESSION 259 observability)
  — verbatim `operator_topic`, per-attempt log, first-pass raw
  synthesis, corrective retry hints, retry count. These are named
  in the integration checkpoint's Composition backlog fix set; they
  are not blockers for this Universe schema slice but should ideally
  land BEFORE Episode work begins (which depends on them).

## Verification / commit log

- Repo evidence surveyed:
  - `shell/apps/spokespeople/models.py` (370 lines) — Teammate.
  - `shell/apps/spokespeople/serializers.py` (117 lines).
  - `shell/apps/spokespeople/views.py` (1243 lines) —
    `TeammateViewSet`.
  - `shell/apps/spokespeople/urls.py` (19 lines).
  - `shell/apps/spokespeople/migrations/*` — head at
    `0011_session253_backfill_voice_defaults.py`.
  - `shell/apps/embeddings/models.py` (322 lines) — Knowledge*.
  - `shell/apps/embeddings/serializers.py` (462 lines).
  - `shell/apps/embeddings/views.py` (373 lines).
  - `shell/apps/embeddings/retrieval.py` (251 lines).
  - `shell/apps/embeddings/signals.py` (80 lines).
  - `shell/apps/embeddings/urls.py` (19 lines).
  - `shell/apps/embeddings/migrations/*` — head at
    `0004_session251_pin_m2m_through_column.py`.
  - `shell/apps/accounts/models.py` (189 lines) — Workspace,
    Membership.
  - `shell/apps/compositions/models.py` (relevant range 357–711).
  - `shell/character_os/settings.py` INSTALLED_APPS.
  - `shell/character_os/urls.py` API routes.
  - `web/src/lib/api/knowledge.ts` — create payload shape and
    silent workspace-wide default.
  - `web/src/routes/workspace/knowledge.tsx` — upload forms (paste,
    upload, url, search) — none send `spokesperson_ids`.
  - `web/src/routes/spokespeople/$id.tsx` — Teammate detail.
  - `web/src/components/nav-rail.tsx` — nav sections.
  - `web/src/lib/api/workspaces.ts` — `/api/me/` default workspace.
- Prior committed slices consulted:
  - `CAPABILITY_INVENTORY_SESSION_261.md`
  - `UNIVERSE_BOUNDARY_V1.md`
  - `EPISODE_VS_COMPOSITION_V1.md`
  - `EPISODE_LIFECYCLE_V1.md`
  - `RELATIONSHIP_BOUNDARY_V1.md`
  - `WORLD_ENTITY_BOUNDARY_V1.md` (with 8f26d7e agency-not-voice
    correction)
  - `UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md`
- No contradictions found between prior slices and code.
- No writes performed to any file except this document.

## App home decision (with reasoning)

**Home = new `apps/universe/`.**

Alternatives considered and rejected:

- `apps/spokespeople/` — makes Universe a subordinate of Teammate,
  which inverts the ownership relation (Universe owns Teammates, not
  the other way around).
- `apps/embeddings/` — makes Universe subordinate to Knowledge, same
  inversion.
- `apps/accounts/` (adjacent to Workspace) — Universe would live
  next to its parent, which has appeal, but conflates the tenant
  layer with the world layer. `accounts` is about tenancy (User,
  Workspace, Membership); Universe is about narrative worlds, a
  distinct concern.
- `apps/identity/` — Identity is about CharacterIdentity substrate;
  Universe is orthogonal.
- Repurposing `apps/memory/` (0-line scaffold) or `apps/agents/`
  (0-line scaffold) — both are reserved namespaces the audit
  identified as Chesterton's-fence memory-adjacent stubs
  (CAPABILITY_INVENTORY §9); using either for Universe consumes a
  reserved slot for a different concept.

**`apps/universe/` is the correct home**: it establishes a
first-class namespace for the world-layer concept, it does not
crowd tenancy or identity, and it leaves the reserved memory/agents
scaffolds free for their intended future roles (narrative memory,
agent orchestration).

## STOP

Design contract complete. No code, no migrations, no schema DDL, no
API implementation, no SPA implementation performed. Every
load-bearing claim is cited to file:line or to the referenced prior
slice. Contradictions with prior slices: NONE.
