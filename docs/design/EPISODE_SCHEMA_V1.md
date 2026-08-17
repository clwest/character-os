---
title: "Episode Schema v1 — Universe-scoped narrative primitive"
status: design — no schema DDL, no migrations, no code, no state changes
date: 2026-08-17
depends_on:
  - "design/UNIVERSE_SCHEMA_V1.md"
  - "design/UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md"
  - "design/UNIVERSE_BOUNDARY_V1.md"
  - "design/EPISODE_VS_COMPOSITION_V1.md"
  - "design/EPISODE_LIFECYCLE_V1.md"
  - "design/COMPOSITION_OBSERVABILITY_V1.md"
  - "design/COMPOSITION_OBSERVABILITY_SCHEMA_V1.md"
  - "handoffs/SESSION_261_UNIVERSE_SUBSTRATE_IMPLEMENTATION.md"
scope: >
  Exact Episode v1 schema, lifecycle, API, SPA workflow, isolation
  invariants, and vertical-slice proof, evaluated against the
  Universe substrate that SESSION 261 shipped and the Composition
  observability contract that SESSION 262 shipped. Design-only.
  No Episode model, no Composition.episode FK, no migration, no code.
supersedes:
  - "portions of EPISODE_VS_COMPOSITION_V1.md that named Episode.workspace"
    "as a denormalized FK — this doc drops it; see §Field-contract Q2."
  - "prior draft ordering that mentioned a `state` enum — this doc"
    "collapses to `archived_at` alone; see §State-model decision."
---

# Episode Schema v1 — Universe-scoped narrative primitive

## Current-state evidence

### Universe substrate as landed (SESSION 261)

Verified against `shell/apps/universe/models.py:33–195`,
`shell/apps/spokespeople/models.py:80–90, 395–410`,
`shell/apps/embeddings/models.py:130–150, 279–303`,
`shell/apps/embeddings/retrieval.py:182–214`,
`shell/apps/universe/views.py:74–157`:

- `Universe(id UUID, workspace FK CASCADE, name Char(120),
  slug SlugField per-workspace unique, description Text blank,
  created_by SET_NULL, created_at, updated_at, archived_at)`.
- Constraint: `(workspace, slug)` unique per workspace
  (`universe_unique_slug_per_workspace`).
- `Teammate.universe = ForeignKey(Universe, on_delete=RESTRICT,
  null=True)` — legacy `universe=NULL` fully supported.
- `KnowledgeDocument.universe = ForeignKey(Universe,
  on_delete=RESTRICT, null=True)` — legacy `universe=NULL`
  fully supported.
- Retrieval isolation is a **branching** predicate at
  `retrieval.py:199–202`:

  ```python
  if spokesperson.universe_id is None:
      qs = qs.filter(document__universe__isnull=True)
  else:
      qs = qs.filter(document__universe_id=spokesperson.universe_id)
  ```

  Universe-scoped teammates NEVER see legacy `universe=NULL` docs,
  and legacy teammates NEVER see universe-scoped docs.
- `clean()` on Teammate + KnowledgeDocument enforces the
  workspace-consistency invariant: `universe.workspace_id ==
  self.workspace_id`.
- `m2m_changed` signal enforces cross-Universe / cross-workspace
  attachment invariants on `KnowledgeDocument.spokespeople`
  (`shell/apps/embeddings/signals.py`).
- Universe hard-delete goes through a preflight
  (`shell/apps/universe/views.py:74–123`): populated Universes
  return `409 Conflict` with blocking counts; empty Universes
  hard-delete via `on_delete=RESTRICT` (which permits deletion
  when there are no children).
- Universe soft-delete = `archived_at = timezone.now()`. Primary
  operator affordance.

### Composition observability as landed (SESSION 262)

Verified against `shell/apps/compositions/models.py:487–701`,
`shell/apps/compositions/starters.py`, `shell/apps/compositions/
primitives/avatar_speech.py`. The nine
`_IMMUTABLE_OBSERVABILITY_FIELDS` are enforced at `save()` against
a `from_db()` snapshot:

```
operator_topic, target_duration_seconds, synthesis_attempt_count,
first_pass_synthesis, corrective_hint, corrective_pass_synthesis,
validation_failure_reason, synthesis_predicted_seconds,
render_dispatched_at
```

Any Episode-attach / Episode-detach code that mutates these fields
would raise `ValidationError` at `save()` time. Attach / detach
therefore MUST only touch `Composition.episode_id` and use
`save(update_fields=["episode", "updated_at"])`, which the
immutability guard already permits (see `save()` at
`models.py:611–670`).

### Composition write paths as landed

`Composition.objects.create()` is the primary write path.
Runtime executor uses `save(update_fields=[...])` for lifecycle
transitions (status, error_message, final_asset, cost_actual,
knowledge_chunk_ids aggregation) — none touch immutable
observability fields. See `shell/apps/compositions/tasks.py:152,
226, 245, 572, 964, 994`.

Episode-attach will follow this pattern: an explicit `attach`
service call issues `save(update_fields=["episode", "updated_at"])`
after validating Universe/Workspace consistency.

## Ratified boundaries preserved

Restated for the record — this doc adds nothing beyond and
subtracts nothing from these:

- **Workspace** = tenant / privacy boundary (unchanged).
- **Universe** = persistent world boundary inside a Workspace
  (`UNIVERSE_SCHEMA_V1.md`; landed SESSION 261).
- **Episode** (this doc) = explicitly declared story / event /
  creative-intent unit inside a Universe.
- **Composition** = individual generation / render / execution
  attempt or variant.
- **Composition may exist without Episode.** Legacy path stays
  valid indefinitely.
- **An Episode is NOT auto-created around every Composition.**
  Explicit operator declaration is the ONLY creation path
  (per `EPISODE_LIFECYCLE_V1.md §H3` correction of the prior
  auto-creation proposal).
- **A failed Composition can belong to an Episode.** Episode
  existence is independent of render success.
- **Retry / rerender / cutdown / alternate visual treatment** =
  new Composition attached to the SAME Episode when the story
  hasn't changed.
- **Composition-level observability is Composition-local
  forever.** SESSION 262 fields never migrate to Episode.

## Field contract

The prior draft named:
`id, workspace, universe, title, operator_topic, state/status,
cast, created_by, created_at, updated_at`.

Re-evaluated against the landed Universe substrate, the field
contract is:

| Field | Type | Required | Mutable | Operator-facing | Reason for existence |
|---|---|---|---|---|---|
| `id` | UUIDField (pk) | yes | no | no (surfaces in URLs) | Row identity. Same pattern as every other primitive in the codebase. |
| `universe` | FK → Universe, NOT NULL, `on_delete=RESTRICT`, `related_name="episodes"` | yes | no | no | Episode is a Universe-scoped narrative primitive. Universe FK is the sole world anchor; workspace is derived transitively via `episode.universe.workspace`. See §Q2. |
| `title` | CharField(120), blank=False | yes | yes | yes | Operator-facing label. Distinct from `operator_topic`: title is short and identity-shaped; topic is prose intent. Derivable from `operator_topic[:60]` at SPA layer if operator declines to type one, but persisted as-is (never blank at row level). |
| `operator_topic` | TextField, blank=False | yes | yes | yes | Story-authoritative intent. Verbatim operator premise. See §Q3. Composition.operator_topic (SESSION 262) is a per-attempt COPY inherited at Composition-create time — distinct from this row. |
| `cast` | M2M → Teammate, `related_name="episodes"`, `through=EpisodeCast` | no | yes | yes | Operator-declared characters participating in the story. May be empty at creation. See §Q6. |
| `archived_at` | DateTimeField, null=True, blank=True | no | yes | yes | Soft-delete marker. NULL = active; non-NULL = archived. Mirrors `Universe.archived_at`. Primary operator lifecycle affordance. See §Q5. |
| `created_by` | FK → User, `on_delete=SET_NULL` | no | no | no | Audit anchor. Same pattern as `Universe.created_by`. |
| `created_at` | DateTimeField, auto_now_add=True | yes | no | no | Audit + ordering. |
| `updated_at` | DateTimeField, auto_now=True | yes | no | no | Audit. |

**Constraints:**

- `(universe, title)` unique per Universe — operator gets a clear
  409 on duplicate title within one world. Cross-Universe
  duplicates are legal (a "Founder Retrospective" Episode in the
  Workshop Universe and in the Bakery Universe are different
  stories).
- No global title uniqueness.

**Indexes:**

- `(universe, archived_at)` — mirrors `Universe`'s
  `universe_ws_archived_idx` pattern. Powers the "list active
  Episodes in this Universe" query.
- `(created_by, created_at)` — audit surfaces.

**Explicitly excluded from v1:**

- No `workspace` FK. See §Q2.
- No `slug` (Universe has one because the SPA URL includes it; a
  UUID URL suffices for Episode in v1).
- No `state` enum. See §Q5.
- No `description` field beyond `operator_topic` — `operator_topic`
  is the story intent, and Universe.description covers world-level
  operator prose.
- No `sequence` / `order_index` — episodes are `created_at`-ordered
  in v1; explicit sequencing deferred.
- No `canonical_composition` FK — canon promotion deferred.
- No `referenced_entities` M2M — WorldEntity substrate deferred.
- No `educational_objective` / `audience` / `purpose` — deferred.

### Q1 — Field-by-field justification

**`id` (UUID pk).**
- Why: identity.
- Source: `uuid.uuid4()` default.
- Mutable: no.
- Required: yes.
- Operator-facing: appears in URLs.
- Duplicates another model: no.

**`universe` FK.**
- Why: Episode is a story inside a world. Universe is the world.
- Source: operator picks at create time (must pick one Universe
  the caller belongs to).
- Mutable: NO. Episodes never move between Universes in v1. If an
  operator wants to move a story, they create a new Episode in
  the target Universe and attach compositions there. This is a
  load-bearing invariant: cross-Universe Episode migration is
  crossover-shaped and remains deferred per
  `UNIVERSE_BOUNDARY_V1.md` invariant 5.
- Required: yes (NOT NULL).
- Operator-facing: yes (Episode lives inside a Universe surface).
- Duplicates another model: no — Universe is the sole
  workspace-scoping mechanism (see §Q2).

**`title`.**
- Why: operator-facing identity string; distinct from
  `operator_topic`'s prose.
- Source: operator input at create; may be auto-derived from
  `operator_topic[:60]` at SPA layer when operator declines.
- Mutable: yes (rename supported).
- Required: yes at row level (blank=False); SPA may derive if
  operator leaves it blank in the form.
- Operator-facing: yes.
- Duplicates another model: no.

**`operator_topic`.**
- Why: story-authoritative creative intent — the verbatim premise
  the operator conceived.
- Source: operator input at create.
- Mutable: yes (operator may evolve the story-level intent).
- Required: yes (blank=False). No topic = no story to render;
  the operator must state the premise before Episode exists.
- Operator-facing: yes.
- Duplicates another model: **partially — by design.**
  Composition.operator_topic (SESSION 262) is a per-attempt copy;
  Episode.operator_topic is the story-level truth. They answer
  different questions ("what did we try to render this time?" vs
  "what is the story?"). Divergence is legal (operator tweaks one
  variant's topic without touching the story).

**`cast` M2M → Teammate.**
- Why: operator-declared characters in the story.
- Source: operator picks Teammates from the same Universe.
- Mutable: yes (add / remove).
- Required: no (may start empty; operator populates during story
  development).
- Operator-facing: yes.
- Duplicates another model: no. Distinct from
  Composition.spokesperson (which is the performer of one render)
  and Composition dialogue turns' per-speaker params (per-render
  execution detail). See §Q6.

**`archived_at`.**
- Why: soft-delete lifecycle. Mirrors Universe pattern.
- Source: `timezone.now()` on archive action.
- Mutable: yes (unarchive clears back to NULL).
- Required: no (NULL = active).
- Operator-facing: yes (visible in list UI as archived filter).
- Duplicates another model: no.

**`created_by`.**
- Why: audit anchor.
- Source: `self.request.user` in the view.
- Mutable: no (immutable after create; SET_NULL only on user
  deletion, preserving row).
- Required: no (nullable for SET_NULL to work).
- Operator-facing: no (surfaced only in admin / audit views).
- Duplicates another model: no.

**`created_at` / `updated_at`.**
- Why: audit + ordering.
- Source: Django's `auto_now_add` + `auto_now`.
- Mutable: no.
- Required: yes.
- Operator-facing: no directly (drives list ordering).
- Duplicates another model: no.

### Q2 — Workspace FK (decision: NO)

**Position: Episode does NOT carry a denormalized `workspace` FK.**

Reasoning against denormalization:

- `Episode.universe` is NOT NULL and non-mutable. Every Episode has
  a Universe. Every Universe has a Workspace. Workspace is
  derivable at zero-cost via one JOIN.
- Universe.workspace can NEVER change (`Universe.workspace` is
  CASCADE; universes are always born in one workspace and never
  migrate). The denormalized `Episode.workspace` invariant
  (`Episode.workspace == Episode.universe.workspace`) would be
  trivially true if set correctly at create — but adding a
  denormalized field means adding a `clean()` invariant check +
  another opportunity for drift.
- Authorization query: `Episode.objects.filter(
  universe__workspace__memberships__user=user)` — one join, well
  indexed via `Universe.workspace_id` (b-tree by default).
- Compare `Teammate` and `KnowledgeDocument`: those have BOTH
  workspace and universe FKs because Universe is OPTIONAL there
  (`universe=NULL` = legacy). Legacy rows have no universe, so
  workspace must be direct. Episode has no legacy shape;
  `universe` is always required.

Materially simplifies vs risk analysis:

- **Simpler:** one less field to keep in sync; one less `clean()`
  gate; one less migration column.
- **No performance loss:** the join is against `Universe`
  (small table; small-integer FK), fully covered by
  `Universe.workspace_id` index. Comparable query cost.
- **No authorization risk:** `IsWorkspaceMember` permission
  already handles workspace membership on any model that can
  derive a Workspace. The `episode.universe.workspace_id` path
  gives the same value as a denormalized copy.

Corrections to prior design docs:

- `EPISODE_VS_COMPOSITION_V1.md §Isolation-invariants #3` stated
  `Episode.workspace == Episode.universe.workspace`. That
  invariant becomes vacuously true when there is no
  `Episode.workspace` field. Preserved semantically; no
  denormalized field needed.
- `EPISODE_LIFECYCLE_V1.md §Smallest-proposed-Episode-v1-boundary`
  named `workspace` FK (denormalized). This doc drops it.

### Q3 — `operator_topic` semantics

- **Creation:** required at Episode create (blank=False). The
  operator's verbatim premise text.
- **Edit semantics:** operator may `PATCH` the topic. Editing
  changes only `Episode.operator_topic`. It **does NOT** touch
  `Composition.operator_topic` on any attached Composition —
  those are per-attempt records that SESSION 262 already made
  immutable-once-populated.
- **Effect on existing Compositions: none.** Zero backward
  propagation. The Episode-level topic represents "the story as
  currently understood"; per-Composition topics represent "what
  we tried to render at this attempt."
- **Inheritance on new Composition:** when a Composition is
  created under an Episode context, its `operator_topic` is
  populated by COPYING `Episode.operator_topic` verbatim at
  Composition-create time. Not a live reference.
- **Explicit override for one variant:** operator may pass an
  `operator_topic` override into the recipe kwargs (`POST
  /api/compositions/` body). The resulting Composition then has
  `Composition.operator_topic` = override string; Episode's
  `operator_topic` remains unchanged. Both persist; both are
  correct answers to different questions.
- **Divergence detection (SPA concern, not backend):** the SPA
  may warn the operator if a variant's override materially
  differs from the Episode topic ("Are you creating a variant or
  a new Episode?"). No backend heuristic infers "substantially
  different"; that judgement stays with the operator.

### Q4 — Title

- **Explicitly operator-authored** at Episode create.
- **Optionally SPA-derived** from `operator_topic[:60]` when the
  operator leaves the field blank at form submit — the SPA
  submits the derived string, so the backend still sees an
  operator-provided (or operator-endorsed) title. Backend never
  auto-derives.
- **Required at row level** (`blank=False`). No blank titles ever
  reach the database.
- **Mutable** via `PATCH`.
- **Never becomes story authority.** Story authority = the
  Episode's *existence* + its `operator_topic`. Title is a
  human-readable handle; it can be renamed freely without
  changing the story.

### Q5 — State model decision (`archived_at` only, no enum)

**Position: no `state` enum in v1. Only `archived_at` (nullable
DateTimeField).**

The prior sketches named DRAFT / ACTIVE / ARCHIVED. Reconsidering
each:

- **DRAFT** ("Episode exists, no Composition attached yet"). This
  is computable in constant time from
  `episode.compositions.exists()`. Storing it as a state adds
  synchronization risk (who flips DRAFT → ACTIVE when the first
  Composition attaches?). Same information is derivable.
- **ACTIVE** ("Episode has ≥1 Composition"). Same argument.
- **ARCHIVED** ("Operator retired the Episode"). Real operator
  action; not derivable. Needs persistence.
- **COMPLETED** / **PARTIAL** / **FAILED** / **RUNNING** — these
  are Composition execution states. Episode is NOT a render job.
  Bringing them onto Episode would be exactly the mixture prior
  design docs warned against (`EPISODE_VS_COMPOSITION_V1.md
  §Q1`).
- **CANONICAL** — canon promotion mechanic explicitly deferred
  (`EPISODE_VS_COMPOSITION_V1.md §Q15`).

Result: only `archived_at` needs persistence. DRAFT vs ACTIVE is
derivable and doesn't need a stored flag. This mirrors
`Universe.archived_at` exactly; API + admin surfaces already have
the pattern.

If a future slice needs `CANONICAL` or `PROMOTED` or
`RETIRED_BY_OWNER`, they can be added additively without changing
this decision.

### Q6 — Cast semantics

**Definition:** `Episode.cast` = the set of Teammates
**operator-declared** as participants in the story.

**Explicit non-definitions:**

- NOT every Character referenced in dialogue.
- NOT every Character with a Relationship edge to cast members.
- NOT every Character relevant to the world.
- NOT the union of Compositions' `spokesperson` fields.
- NOT the union of dialogue-scene per-speaker `params`.

**Cast may start empty.** An Episode conceived before the operator
has firmed the cast is a legal state. Cast is populated as the
story develops; the operator authors it explicitly.

**When cast MUST be populated: never automatically.** Even the
first Composition-attach does NOT auto-populate cast. The
operator's declaration is authoritative. Compositions may render
under Episodes with an empty cast — the SPA may warn ("This
Episode has no declared cast; is that intentional?") but the
backend accepts.

**Speakers outside cast:** a Composition attached to Episode E
may reference speakers (via `spokesperson` FK or dialogue-scene
per-turn spokesperson) who are not in `E.cast`. This is legal.
Rationale: an off-screen character (mentioned, not spoken) still
appears in dialogue prose; a narrator who isn't part of the story
proper may voice the render. **Backend logs a warning** at
Composition-attach for auditability but does not block the
attach.

**Stress test — Patch + Rivet discuss Mason's project.** Mason is
mentioned in dialogue but off-screen. Expected:
- `E.cast = {Patch, Rivet}`.
- Composition C rendered with `spokesperson=Patch` (or Rivet, or a
  narrator).
- Mason is neither in `E.cast` nor in the Composition's rendered
  turns.
- No warning fires (Mason isn't a speaker).
- Correct: Mason is a story object, not a story participant.

**Cast mutation rules:**

- Add: `POST /api/episodes/<id>/cast/` with `{teammate: UUID}`.
  Validates `teammate.universe_id == episode.universe_id`.
- Remove: `DELETE /api/episodes/<id>/cast/<teammate_id>/`.
  Removing a cast member does NOT retroactively affect any
  attached Composition (their spokesperson / dialogue-scene
  speakers are per-render immutable observability facts under
  SESSION 262).
- Universe change: not applicable (Episode.universe is
  immutable; cast never becomes cross-Universe).

**Universe consistency invariant:** every Teammate in
`Episode.cast` MUST have `teammate.universe_id ==
episode.universe_id`. Enforced at `clean()` and at
`m2m_changed pre_add` — mirrors the
`KnowledgeDocument.spokespeople` signal pattern in
`shell/apps/embeddings/signals.py`.

**Legacy Teammate (universe=NULL) attachment:** REJECTED. A
universe-scoped Episode cannot include a legacy Teammate in its
cast. This aligns with the retrieval-side invariant that legacy
and universe-scoped worlds are structurally isolated
(`retrieval.py:199–202`).

### Q7 — Composition linkage

**Field:** `Composition.episode = ForeignKey("universe.Episode",
null=True, blank=True, on_delete=models.PROTECT,
related_name="compositions")`.

**Nullable: yes.** Composition may exist without Episode. This is
the legacy shape and continues to be the default for any
Composition created without an explicit `episode` parameter.

**on_delete: PROTECT.** Deleting an Episode that has any attached
Composition is BLOCKED at the DB layer (raises
`ProtectedError`). The API surface preflights this and returns
`409 Conflict` with a helpful body — same pattern as
`Universe.destroy` at `shell/apps/universe/views.py:74–123`.
Rationale:

- SET_NULL would silently orphan Compositions and destroy the
  narrative-to-render linkage. Exactly the hazard the Universe
  design rejected (correction 75d17f5 for
  `KnowledgeDocument.universe`).
- CASCADE would delete rendered Compositions when the operator
  archives a story, destroying render provenance. Unacceptable.
- PROTECT forces explicit operator action to detach Compositions
  first, which is the desired workflow.

**Universe delete cascade:** `Episode.universe = RESTRICT` (see
below). A Universe with any Episode attached cannot hard-delete
without operator first archiving / reassigning Episodes. This
mirrors the existing Universe hard-delete preflight for Teammates
and KnowledgeDocuments (`shell/apps/universe/views.py:101–119`).

**Workspace cascade:** `Workspace.delete()` cascades through
`Universe.workspace` (CASCADE), `Universe → Episode`
(via CASCADE below — see paragraph on Universe cascade), and
`Composition.workspace` (CASCADE). Composition.episode is PROTECT,
but Django's shared-CASCADE-parent rule (>= 3.1) allows PROTECT
to succeed when the protected row is ALSO being deleted in the
same transaction — which is the case here (Composition cascades
from workspace, Episode cascades from workspace via universe).

**Actual Universe → Episode on_delete choice:** RESTRICT. Same
rationale as Teammate.universe and KnowledgeDocument.universe.
Universe hard-delete preflight (already present) needs to
additionally count Episodes and reject if any exist.

**Cross-Workspace validation** (Composition.episode):
`composition.workspace_id == episode.universe.workspace_id`.
Enforced at `clean()`.

**Cross-Universe validation:** if
`composition.spokesperson.universe_id` is non-NULL, it must equal
`episode.universe_id`. Enforced at `clean()`. Legacy
`spokesperson.universe=NULL` CANNOT attach to a Universe-scoped
Episode.

**Can an existing Episode-less Composition later be attached?**
YES. Explicit operator action via `POST
/api/compositions/<id>/attach-episode/` with `{episode: UUID}`.
The service call:
1. Validates cross-Workspace and cross-Universe invariants.
2. Sets `composition.episode_id = episode.pk`.
3. `save(update_fields=["episode", "updated_at"])` — which the
   SESSION 262 immutability guard permits because the observability
   fields are not in `update_fields`.

**Can a Composition move between Episodes?** YES, via the same
attach service (or a detach-then-attach). Cross-Universe move is
REJECTED at the invariant check.

**Provenance on attach / detach / move:** COMPLETELY UNTOUCHED.
Because the service only writes `composition.episode_id` and uses
`update_fields=["episode", "updated_at"]`, the SESSION 262
immutability guard skips every observability field (they aren't
in `update_fields`). All nine observability values remain
byte-for-byte identical across attach / detach / move cycles.

**Episode delete / archive semantics for attached Compositions:**
- Archive: Compositions retain their `episode` FK (Episode row
  still exists, just archived). List surfaces default-hide archived
  Episodes; the FK stays intact so audit history is preserved.
- Hard-delete (blocked by PROTECT when children exist): operator
  first detaches Compositions (`DELETE
  /api/compositions/<id>/attach-episode/` or `PATCH` to `null`).

### Q8 — Deletion / archive policy

**Universe SET_NULL mistake recap (do not repeat):** the original
Universe schema draft proposed `SET_NULL` on child FKs. Correction
`75d17f5` changed it to `RESTRICT` because SET_NULL would silently
demote populated Universe knowledge to legacy `universe=NULL`,
exactly the leakage hazard Universe existed to prevent.

**Episode deletion policy — three layers:**

1. **Archive (primary operator action).** `DELETE
   /api/episodes/<id>/` sets `archived_at = timezone.now()`.
   Idempotent. Reversible via `POST
   /api/episodes/<id>/unarchive/`. All attached Compositions
   retain their `episode` FK; audit trail preserved.

2. **Hard-delete "empty enough" Episode.** `DELETE
   /api/episodes/<id>/?hard=true` succeeds when
   `episode.compositions.exists() == False`. Cast membership
   alone does NOT block hard-delete — `EpisodeCast` M2M rows
   cascade away with the deleted Episode row (Django's default
   M2M cascade behavior). The load-bearing rule is:
   **attached Compositions block; cast does not.** `PROTECT` on
   `Composition.episode` remains the DB-level backstop; the
   API preflights so operators see a helpful 409 with
   `blocking.composition_count` instead of a raw
   `ProtectedError`.

3. **Hard-delete populated Episode.** BLOCKED — `PROTECT` on
   `Composition.episode` raises `ProtectedError` at DB level.
   Preflight returns:
   ```
   409 Conflict
   {
     "error": "Cannot hard-delete a populated Episode.
               Detach every Composition (or reassign to another
               Episode) first, or archive.",
     "code": "episode_populated",
     "blocking": {"composition_count": <N>}
   }
   ```

**Universe deletion consequences:**

- Universe hard-delete preflight already counts Teammates and
  KnowledgeDocuments (`views.py:101–119`). SCHEMA_V1
  implementation would ADD `episode_count` to the preflight and
  block when non-zero (Episode.universe = RESTRICT).
- Universe archive: does NOT cascade to Episodes. Episodes remain
  active by default when their parent Universe is archived. The
  SPA may hide them from the "active Episodes" list because their
  parent Universe is archived; the backend keeps the rows intact.

**Workspace delete cascade:**
Workspace CASCADE → Universe CASCADE → Episode CASCADE → cast M2M
auto-cleaned → Composition.episode PROTECT satisfied by shared-
CASCADE-parent rule (Composition cascades from Workspace too).

### Q9 — Episode creation workflow

Explicit-only. Prior slice's auto-creation proposal is
already-corrected by `EPISODE_LIFECYCLE_V1.md §H3` and
`§Correction`. This doc preserves the correction.

**Smallest operator workflow (SPA):**

1. Operator navigates to a Universe surface
   (`/workspace/universes/<uuid>`).
2. Clicks "New Episode" button (distinct from "New video").
3. Modal appears with fields: `title` (optional; derived from
   topic if left blank), `operator_topic` (required),
   `cast` (multi-select of Teammates in this Universe; may be
   left empty).
4. Submit → Episode row created.
5. Redirect to Episode detail (`/workspace/episodes/<uuid>`).
6. From Episode detail: "Create Composition under this Episode"
   opens the recipe form with `episode` pre-filled from URL
   context.

**Standalone Composition workflow (preserved unchanged):**

- Existing "Create video" flow at `/workspace/create` (or wherever
  the recipe form lives) does NOT change.
- The recipe form gains an OPTIONAL `episode` picker that defaults
  to "None (standalone)". Filled only if the operator explicitly
  wants to attach.
- Zero Episode-related friction for the operator who just wants a
  one-off video.

**SPA distinction between "Create a video" and "Create an
Episode":**

- **"Create a video"** = default recipe form. Result: Composition,
  possibly with `episode=NULL`.
- **"New Episode"** = distinct SPA surface. Result: Episode row.
  From there, "Create Composition" pre-fills the episode
  context.

These two surfaces are UI-distinct at their entry points. No
mixing; no confusion.

### Q10 — Retry / rerender / new-Episode decision

The decision boundary is **operator-explicit**, not
backend-inferred. Table:

| Input | Same Episode + new Composition | New Episode |
|---|---|---|
| Retry after failed synthesis (unchanged topic) | ✓ | — |
| 30-second cutdown of accepted 90s render | ✓ | — |
| Alternate backdrop / visual treatment | ✓ | — |
| Alternate cast lineup for the SAME story | ✓ | — |
| Translated version (same story, different language) | ✓ | — |
| Operator changes topic slightly ("add: Rivet mentions the lab robot") | ✓ (operator PATCHes Episode.operator_topic; new Composition inherits the updated topic) | — |
| Operator rewrites topic substantially ("actually, make it Rivet warning Patch about the coffee machine instead") | — | ✓ (operator explicitly clicks "New Episode") |

**Backend is passive:** it does not inspect topic strings, does not
compute similarity, does not decide "same story" vs "new story."
It accepts whatever `episode` FK the operator passed on the
Composition create request.

**Stress test walkthrough:**

- E1 = "AI took over the lab" (Patch + Rivet).
- C1: `episode=E1`. Synthesis rejected before steps. Persists as
  FAILED, all SESSION 262 observability fields populated,
  `episode=E1`.
- C2: `episode=E1`, operator retries. New Composition. Independent
  provenance from C1. Attached to same Episode.
- C3: `episode=E1`, 30s cutdown. New Composition with different
  `target_duration_seconds`. Same Episode.
- C4: `episode=E1`, alternate backdrop. New Composition with
  different backdrop_clip_id. Same Episode.
- C5: operator conceives a materially different story. Operator
  clicks "New Episode" in the SPA. E2 created. C5:
  `episode=E2`.

E1 remains unchanged across C1–C4. E1.operator_topic is
unchanged. C1–C4 each carry their own per-attempt observability.
The story happened once (E1); the renders happened four times
(C1–C4).

### Q11 — Failed-only Episodes

**Expected: yes, Episode can contain only failed Compositions.**

Verified against architecture:

- `Composition.episode` FK carries any status. There is no
  status-filter on the FK.
- The dialogue AI-Topic starter's rejection path
  (`shell/apps/compositions/starters.py:3454+`) and the
  long-form's rejection path (`starters.py:1245+`) both create a
  FAILED Composition. Attaching a FAILED Composition to an
  Episode via the standard attach service works identically to
  attaching a COMPLETED one.
- **Episode exists independently of whether any render
  succeeds.** An Episode with zero attached Compositions, zero
  successful Compositions, or N failed Compositions is a legal
  state. The operator conceived the story; that intent is
  durable.

### Q12 — Canon semantics

**Merely creating / rendering an Episode does NOT mutate Universe
canon.**

- Episode existence itself is durable — an Episode row persists in
  the Universe.
- But content produced by attached Compositions (dialogue text,
  K6-synthesized brief, LLM turns, verifier warnings) is NOT
  automatically canonical.
- Facts invented in generated dialogue do NOT flow into the
  Universe's knowledge substrate.
- Retrieval scope is still driven by `KnowledgeDocument.universe`
  membership; Compositions do not create retrieval-visible
  content.

**Canon promotion mechanic explicitly deferred.** A future slice
(`EPISODE_CANON_V1`?) may add a promotion action that lifts
selected Compositions to canonical status, seeding narrative
memory or promoting specific outputs into
`KnowledgeDocument` rows. This slice does NOT design that
mechanic.

### Q13 — Relationship / WorldEntity independence

Episode v1 must stand alone with only:
- Universe (parent world)
- Cast (participants)
- Story intent (operator_topic)
- Attached Compositions

Verified: none of the fields in this doc reference Relationship
or WorldEntity. Cast is a plain M2M to Teammate. Story intent is
plain text. Composition attachment is plain FK. No dependency.

**Deferred additive fields for future slices:**

- `referenced_entities` M2M → WorldEntity (when WorldEntity
  substrate lands per `WORLD_ENTITY_BOUNDARY_V1.md`).
- `narrative_events` reverse relation from a future
  `NarrativeEvent` row (event log / promise ledger substrate).
- `relationship_events` reverse relation from a future
  `RelationshipEvent` row (relationship-history substrate per
  `RELATIONSHIP_BOUNDARY_V1.md`).
- `canonical_composition` FK (canon promotion).
- `sequence` / `order_index` (explicit ordering).
- `educational_objective`, `audience`, `purpose` (curriculum
  substrate).

None of these are v1. Episode v1 is useful without them.

### Q14 — Legacy behavior

- Existing Episode-less Compositions (all 81 in
  `chriss-workspace` per SESSION 259 audit + all
  post-SESSION-261 Compositions created without Episode) remain
  valid **forever**. No historical wrapping.
- No bulk migration; no auto-attachment; no "Episode of one"
  auto-creation.
- Legacy business spokesperson workflows (Mike-the-plumber weekly
  TikTok, single talking-head renders, cinematic_visual, image
  generation) are entirely unaffected.
- `episode=NULL` continues to be the default for the standalone
  workflow.
- Mirrors `UNIVERSE_BOUNDARY_V1.md §Q6 "prospective introduction,
  no bulk-migration"` and `EPISODE_LIFECYCLE_V1.md §Q16
  paragraph 1` (already-ratified).

### Q15 — Composition-observability non-mutation

Load-bearing invariant: Episode attach / detach / move MUST NOT
mutate any of the nine SESSION 262 immutable observability fields
on any Composition.

- `operator_topic`
- `target_duration_seconds`
- `synthesis_attempt_count`
- `first_pass_synthesis`
- `corrective_hint`
- `corrective_pass_synthesis`
- `validation_failure_reason`
- `synthesis_predicted_seconds`
- `render_dispatched_at`

Verified against `shell/apps/compositions/models.py:611–670`. The
attach / detach service call issues:

```python
composition.episode_id = episode_pk  # or None to detach
composition.save(update_fields=["episode", "updated_at"])
```

Because `episode` and `updated_at` are the ONLY fields in
`update_fields`, the `save()` override's loop over
`_IMMUTABLE_OBSERVABILITY_FIELDS` finds none of them in
`update_fields` and skips the check for every one. No violation is
raised; no observability field is touched.

**Regression test (part of §Q19 test matrix):** create a
Composition with all nine observability fields populated;
snapshot them; attach to Episode E; assert all nine values are
byte-for-byte unchanged; detach; assert unchanged; attach to a
different Episode E'; assert unchanged; hard-delete E' (via
detach-then-hard-delete-empty-Episode); assert Composition's nine
values are still unchanged.

Also add an adversarial test that attempts to attach with a
save() that INCLUDES an observability field in `update_fields` —
must raise ValidationError to prove the guard fires.

### Q16 — API

Smallest Episode API surface:

**Resource: `/api/episodes/`.**

| Method | Path | Purpose | Body / Params |
|---|---|---|---|
| POST | `/api/episodes/` | Create Episode | `{universe: UUID, title: str, operator_topic: str, cast: [UUID]?}` |
| GET | `/api/episodes/?universe=<uuid>[&include_archived=true]` | List Episodes in a Universe | Query params |
| GET | `/api/episodes/<id>/` | Retrieve one | — |
| PATCH | `/api/episodes/<id>/` | Update `title` / `operator_topic` (cast via separate endpoints) | `{title?: str, operator_topic?: str}` |
| DELETE | `/api/episodes/<id>/[?hard=true]` | Archive (default) or hard-delete (empty only) | — |
| POST | `/api/episodes/<id>/unarchive/` | Un-archive | — |
| POST | `/api/episodes/<id>/cast/` | Add cast member | `{teammate: UUID}` |
| DELETE | `/api/episodes/<id>/cast/<teammate_id>/` | Remove cast member | — |

**Composition attach / detach — mounted on Composition, not Episode:**

| Method | Path | Purpose | Body |
|---|---|---|---|
| POST | `/api/compositions/<id>/attach-episode/` | Attach existing Composition to Episode (or move) | `{episode: UUID}` |
| DELETE | `/api/compositions/<id>/attach-episode/` | Detach Composition | — |

**Composition create with Episode:**

- Existing `POST /api/compositions/` accepts optional
  `episode: UUID` in the body.
- Backend validates cross-Workspace, cross-Universe.
- On success, Composition is created with `episode` FK set.

**NOT designed in v1:**

- No narrative-memory endpoints (no `POST
  /api/episodes/<id>/events/`, no `POST
  /api/episodes/<id>/promise/`, no `POST
  /api/episodes/<id>/canon/`).
- No cross-Universe operations.
- No batch attach / detach.
- No Episode search / query (list by universe is enough for v1).

**Serialization shape (illustrative):**

```json
{
  "id": "<uuid>",
  "universe": "<uuid>",
  "title": "AI took over the lab",
  "operator_topic": "Rivet warns Patch...",
  "cast": [
    {"id": "<uuid>", "name": "Patch"},
    {"id": "<uuid>", "name": "Rivet"}
  ],
  "composition_count": 4,
  "archived_at": null,
  "created_by": "<uuid or null>",
  "created_at": "2026-08-17T18:00:00Z",
  "updated_at": "2026-08-17T18:00:00Z"
}
```

`composition_count` is a computed read-only field
(`self.compositions.count()`), avoiding a full serialization
walk in list views.

### Q17 — SPA workflow

Smallest user-facing footprint that enables explicit Episode
without forcing every Composition into Episode mode:

**New routes:**

- `/workspace/universes/<uuid>/episodes` — list Episodes in a
  Universe.
  - Sections: "Active" (default), "Archived" (toggleable).
  - Actions: "New Episode" button.
- `/workspace/episodes/<uuid>` — Episode detail.
  - Displays: title, operator_topic (prose), cast (chips), attached
    Compositions with status + timestamps.
  - Actions: Edit title / topic, add / remove cast, "Create
    Composition under this Episode" (routes to recipe form
    prefilled with episode context), Archive.

**Modified existing routes:**

- Recipe form (wherever it lives, e.g.
  `/workspace/create` / `/spokespeople/<uuid>/create`) — adds an
  OPTIONAL "Episode" picker.
  - Default: "None (standalone)". Existing behavior preserved.
  - When operator opens the picker, shows Episodes in the
    selected spokesperson's Universe (or all Episodes in every
    Universe the operator belongs to, filtered as they type).
  - When operator picks an Episode, the Composition is created
    with that `episode` FK.
- Composition detail — if `composition.episode` is non-NULL,
  shows a link to the Episode detail. If NULL, shows nothing
  Episode-related.

**Dashboard tile:**

- Add "Episodes" tile alongside Universes tile. Clicking navigates
  to a per-workspace list (or to Universes → picks Universe → list
  episodes; either flow works).

**Never done in v1:**

- No mandatory Episode selection.
- No Episode-first onboarding.
- No forced migration of existing Compositions to Episodes.
- No smart Episode-suggestion ("You've made 3 similar
  Compositions; want to group them?").

**Rule of thumb:** if the operator has never clicked "New
Episode," the entire Episode primitive is invisible to them, and
their workflow is byte-for-byte identical to today's.

### Q18 — Isolation invariants

Enforced at model `clean()` (form / admin path) + `m2m_changed`
signal (M2M path) + service layer (attach / detach). Mirrors the
Universe substrate's defense-in-depth (see
`shell/apps/embeddings/signals.py`).

1. **Episode.universe belongs to requesting Workspace.**
   Every write path checks that the caller is a member of
   `episode.universe.workspace`. Query filter:
   `Episode.objects.filter(
   universe__workspace__memberships__user=request.user)`.
   Permission class: `IsWorkspaceMember` (existing).

2. **Cast Teammates must belong to Episode.universe.**
   `clean()`: reject when any `cast` M2M row has
   `teammate.universe_id != episode.universe_id`.
   `m2m_changed pre_add` signal on `Episode.cast`: same check.
   Legacy `teammate.universe=NULL` cannot be added to a
   Universe-scoped Episode's cast (mirrors retrieval isolation).

3. **Attached Compositions: same Universe, same Workspace.**
   `Composition.clean()` (extended in the implementation slice):
   when `composition.episode_id is not None`:
   - `composition.workspace_id == episode.universe.workspace_id`
   - If `composition.spokesperson_id and
     composition.spokesperson.universe_id`:
     `composition.spokesperson.universe_id == episode.universe_id`
   - If `composition.spokesperson.universe_id is None` (legacy
     spokesperson): REJECT.

4. **No cross-Universe Episode attachment.** Enforced by (3).

5. **Legacy `universe=NULL` Composition behavior:** explicit.
   - A Composition whose spokesperson is `universe=NULL` may NOT
     be attached to any Episode. Attempt returns 422 with
     `{"episode": "Legacy (universe=NULL) spokesperson cannot
     attach to a Universe-scoped Episode. Assign the spokesperson
     to a Universe first."}`
   - A Composition whose `episode` is NULL and whose spokesperson
     is Universe-scoped: still legal (Composition may exist
     without Episode; Universe scoping via spokesperson only).
   - Legacy `spokesperson.universe=NULL` + `episode=NULL`
     Composition: continues to work as today (pre-Universe
     legacy path).

6. **Episode is not workspace-portable.** Because
   `Episode.universe` is non-mutable and Universe.workspace is
   non-mutable, Episode is workspace-anchored at create time and
   never crosses.

7. **Cross-Universe crossover forbidden.** An Episode's
   Compositions and cast all sit in the same Universe. Crossover
   remains a deferred explicit primitive
   (`UNIVERSE_BOUNDARY_V1.md` invariant 5).

**Same defense-in-depth pattern already proven for the SESSION
261 Universe substrate:** `clean()` + serializer validation +
signal, backed by RESTRICT/PROTECT at the DB layer.

### Q19 — Deterministic test plan

Test file names (naming mirrors the SESSION 261 pattern):

- `shell/apps/universe/tests/test_episode_model.py`
- `shell/apps/universe/tests/test_episode_api.py`
- `shell/apps/universe/tests/test_episode_cast.py`
- `shell/apps/universe/tests/test_episode_composition_attach.py`
- `shell/apps/universe/tests/test_episode_deletion.py`
- `shell/apps/compositions/tests/test_episode_composition_field.py`
- `shell/apps/compositions/tests/test_episode_observability_isolation.py`

**Test matrix:**

**Schema / model.**
1. Episode row creates with required fields (universe, title,
   operator_topic).
2. Blank title rejected at `clean()`.
3. Blank operator_topic rejected at `clean()`.
4. `(universe, title)` uniqueness enforced.
5. Same title in two different Universes: legal.
6. `archived_at` defaults to NULL.
7. `created_by` SET_NULL when user deleted.
8. `Episode.universe` on_delete=RESTRICT: hard-delete of Universe
   with Episodes raises RestrictedError (or 409 via preflight).

**Validation / isolation.**
9. Cross-workspace cast rejected: Teammate from a different
   Workspace cannot be added.
10. Cross-Universe cast rejected: Teammate from a different
    Universe in the same Workspace cannot be added.
11. Legacy `teammate.universe=NULL` cast attachment rejected.
12. Empty cast at create: legal (may be populated later).
13. Cast add via `POST /api/episodes/<id>/cast/`: 201; audit-safe.
14. Cast remove via `DELETE /api/episodes/<id>/cast/<tm_id>/`:
    204; does NOT touch attached Compositions.

**API.**
15. `POST /api/episodes/` — happy path.
16. `POST` with wrong Universe (not caller's workspace): 403.
17. `POST` without operator_topic: 400.
18. `GET /api/episodes/?universe=<uuid>`: returns episodes in that
    Universe only; archived hidden unless `include_archived=true`.
19. `GET /api/episodes/<id>/`: full detail including cast +
    composition_count.
20. `PATCH /api/episodes/<id>/`: updates title + operator_topic;
    does NOT mutate any attached Composition's
    `operator_topic`.
21. `DELETE /api/episodes/<id>/`: archives.
22. `POST /api/episodes/<id>/unarchive/`: reverses.
23. `DELETE /api/episodes/<id>/?hard=true` on empty Episode:
    204.
24. `DELETE /api/episodes/<id>/?hard=true` on Episode with
    Compositions: 409 with `blocking.composition_count`.

**Composition linkage.**
25. `POST /api/compositions/` with `episode`: Composition created
    with FK set; observability fields populate as usual.
26. `POST /api/compositions/` with `episode` in a different
    Universe than the spokesperson: 422.
27. `POST /api/compositions/` with `episode` in a different
    Workspace: 422.
28. Attach via `POST /api/compositions/<id>/attach-episode/`:
    happy path.
29. Attach with cross-Universe episode: 422.
30. Attach a legacy `spokesperson.universe=NULL` Composition to
    Universe-scoped Episode: 422.
31. Detach via `DELETE /api/compositions/<id>/attach-episode/`:
    happy path.
32. Move (attach when already attached): re-attaches to the new
    Episode; original Episode's `composition_count` decrements.

**Retry / rerender.**
33. Two Compositions attached to the same Episode: `Episode.
    compositions` reverse-relation returns both.
34. Failed Composition attached to Episode: legal.
35. Only-failed-Compositions Episode: legal state (Episode
    survives).

**Deletion / archive.**
36. Archive Episode: `archived_at` set; Compositions retain FK.
37. Archive is idempotent.
38. Hard-delete blocked when Compositions attached.
39. After detach-all, hard-delete succeeds.
40. Workspace CASCADE deletes Universe → Episode →
    Composition.episode SET (via shared-CASCADE-parent).

**Legacy compatibility.**
41. Existing Composition with `episode=NULL` continues to work
    across every recipe flow.
42. Universe-scoped Teammate with an Episode-less Composition:
    legal; Composition renders as before.
43. Legacy `Teammate.universe=NULL` — cannot have an Episode
    ever (invariant #5).

**Observability non-mutation (SESSION 262 interaction).**
44. Attach existing Composition with all 9 observability fields
    populated: post-attach, all 9 values byte-for-byte
    unchanged.
45. Detach: same guarantee.
46. Move between Episodes: same guarantee.
47. Adversarial: any code path attempting
    `save(update_fields=[...])` that includes an observability
    field along with `episode` raises ValidationError (proves
    the guard fires; not a normal flow).

**Cross-Universe isolation.**
48. Episode in Universe A cannot list / retrieve / attach
    Compositions from Universe B.
49. Retrieval scope during synthesis under an Episode:
    unchanged — still driven by
    `spokesperson.universe_id`. Episode does NOT influence
    knowledge retrieval scope in v1.

**Immutability / migration verification.**
50. `Episode.universe` cannot be updated post-create (attempt
    raises validation error or is blocked at the model layer;
    even if permitted at the ORM level, it would break Universe
    isolation — the impl slice must decide model-level vs
    serializer-level enforcement).

Each test is deterministic (fixture-based, no provider calls,
no time-sensitive assertions beyond auto_now).

### Q20 — Smallest vertical slice

Proof-of-architecture vertical slice using Patch/Rivet-style
fixtures. No real provider calls; uses mock_mode or explicit
stubs.

**Setup:**

1. Create Workspace `test-ws`.
2. Create Universe `patch-rivet-workshop` in `test-ws`.
3. Create Teammates Patch and Rivet, both assigned to
   `patch-rivet-workshop`.

**Vertical slice:**

4. **Create Episode E1** in `patch-rivet-workshop`:
   `title="AI took over the lab"`, `operator_topic="Rivet warns
   Patch the AI will fire the humans; Patch is skeptical"`.
5. **Add cast**: Patch + Rivet.
6. **Create Composition C1** under E1: dialogue_scene, AI Topic
   mode, `mock_mode=True`, `episode=E1`. **Simulate synthesis
   failure** by patching `synthesize_dialogue` to raise
   `DialogueSynthesisError` (matching SESSION 262 test #3 style).
7. **Verify** C1: `status=FAILED`, `episode=E1`, all nine SESSION
   262 observability fields populated (`operator_topic`,
   `first_pass_synthesis`, `corrective_hint`, `corrective_pass_
   synthesis`, `synthesis_attempt_count`,
   `synthesis_predicted_seconds`, `validation_failure_reason`
   set; `render_dispatched_at=NULL`), zero CompositionSteps.
8. **Create Composition C2** under E1: same dialogue_scene, AI
   Topic mode, mock_mode. `synthesize_dialogue` returns a valid
   DialogueResult. **Succeeds.**
9. **Verify** C2: `status=COMPLETED`, `episode=E1`, all nine
   observability fields populated including
   `render_dispatched_at != NULL`, N CompositionSteps.
10. **Verify** E1: `E1.compositions.count() == 2`;
    `E1.compositions` contains {C1, C2}; C1.status=FAILED,
    C2.status=COMPLETED.
11. **Verify per-Composition provenance isolation**: C1's
    `operator_topic == C2's operator_topic == E1.operator_topic`
    (all three copies match at first-attach because C1 and C2
    inherited from E1 at create time). C1's
    `first_pass_synthesis` (a failed-attempt raw) differs from
    C2's `first_pass_synthesis` (accepted-attempt raw).
12. **Verify** E1's story intent unchanged: E1.title and
    E1.operator_topic byte-for-byte identical to their create-
    time values (no side effects from Composition attach).
13. **Adversarial**: attempt `E1.operator_topic = "different
    story"; E1.save()` — legal (Episode.operator_topic is
    mutable per §Q3). Verify C1 and C2's `operator_topic` remain
    unchanged (SESSION 262 immutability).
14. **Adversarial**: attempt `C1.operator_topic = "different";
    C1.save()` — raises ValidationError per SESSION 262 guard.
15. **Cross-Universe safety**: create Universe `bakery`, create
    Teammate `Baker` in `bakery`. Attempt to add `Baker` to
    E1.cast — rejected (universe mismatch). Attempt to create
    Composition with `spokesperson=Baker, episode=E1` — rejected
    (cross-Universe attach).

Everything runs against the local Postgres with
`EMBEDDING_FORCE_MOCK=1`. Zero Runway credits, zero OpenAI credits.

## Lifecycle

Episode has three transition points and one absorbing state:

```
∅ ── operator "New Episode" ──► ACTIVE (archived_at=NULL, N compositions ≥ 0)
                                    │
                                    ├─ operator archive ──► ARCHIVED (archived_at=now)
                                    │                             │
                                    │                             └─ operator unarchive ──► ACTIVE
                                    │
                                    └─ operator hard-delete (empty) ──► ∅ (row deleted)
```

- No implicit transitions. Every transition is operator-initiated.
- Composition-count changes do NOT trigger a state transition. An
  Episode with 0 attached Compositions is ACTIVE (not "DRAFT") —
  the state field doesn't distinguish, per §Q5.
- Cascade from Workspace / Universe delete counts as an implicit
  path but is the standard database-level cascade, not an Episode
  lifecycle transition.

## Composition-observability interaction

Detailed in §Q15. Summary:

| Operation | Composition.episode | Composition observability fields |
|---|---|---|
| Attach Episode-less Composition | NULL → E1 | Untouched (nine fields) |
| Move Composition to a different Episode | E1 → E2 | Untouched |
| Detach Composition | E1 → NULL | Untouched |
| Edit Episode.operator_topic | (unrelated field) | Untouched — Episode change never propagates to Composition |
| Archive Episode | (Composition.episode unchanged) | Untouched |
| Unarchive Episode | (Composition.episode unchanged) | Untouched |
| Delete Episode (blocked when populated) | Cannot happen without operator detach first | Untouched (block prevents mutation) |

**Load-bearing test coverage:** §Q19 items 44–47 assert this
guarantee.

## Migration classification

**Additive-only, no data migration, no bulk backfill.**

Two migrations required by the implementation slice (both
identical shape to the SESSION 261 Universe migrations):

1. **`apps/universe/migrations/000X_episode_initial.py`**
   - `CreateModel` for `Episode` (id, universe FK RESTRICT,
     title, operator_topic, archived_at, created_by SET_NULL,
     created_at, updated_at).
   - `CreateModel` for `EpisodeCast` through model
     (M2M Episode ↔ Teammate).
   - Constraints: `(universe, title)` unique.
   - Indexes: `(universe, archived_at)`,
     `(created_by, created_at)`.

2. **`apps/compositions/migrations/000Y_composition_episode_fk.py`**
   - `AddField` for `Composition.episode` (nullable, PROTECT,
     related_name="compositions").

Both migrations are additive; no data touched. Legacy
Compositions land with `episode=NULL` on the migrate; no bulk
attach.

## Implementation file map

Files the implementation slice will TOUCH or CREATE:

**Create:**
- `shell/apps/universe/models.py` — add `Episode` + `EpisodeCast`
  classes (append to existing file; keep Universe model in
  place).
- `shell/apps/universe/migrations/000X_episode_initial.py`
- `shell/apps/universe/serializers.py` — add `EpisodeSerializer`,
  `EpisodeListSerializer`.
- `shell/apps/universe/views.py` — add `EpisodeViewSet`,
  `EpisodeCastAdd` / `EpisodeCastRemove` actions, and
  `Composition.attach-episode` / `detach-episode` actions
  (potentially in `apps/compositions/views.py` for the latter —
  see the impl slice's routing decision).
- `shell/apps/universe/urls.py` — register the new endpoints.
- `shell/apps/universe/signals.py` (new) — `m2m_changed pre_add`
  for `Episode.cast` (Universe consistency check).
- `shell/apps/universe/admin.py` — Episode + EpisodeCast admin
  registration.
- `shell/apps/compositions/migrations/000Y_composition_episode_fk.py`
- `shell/apps/universe/tests/test_episode_model.py`
- `shell/apps/universe/tests/test_episode_api.py`
- `shell/apps/universe/tests/test_episode_cast.py`
- `shell/apps/universe/tests/test_episode_composition_attach.py`
- `shell/apps/universe/tests/test_episode_deletion.py`
- `shell/apps/compositions/tests/test_episode_composition_field.py`
- `shell/apps/compositions/tests/test_episode_observability_isolation.py`
- SPA scaffolding: new routes / components under `web/` for
  Episode list + detail + create modal.

**Modify:**
- `shell/apps/compositions/models.py` — add `Composition.episode`
  FK; extend `Composition.clean()` with the three Episode
  consistency invariants (§Q18 items 3-5).
- `shell/apps/compositions/serializers.py` — accept optional
  `episode` in Composition create.
- `shell/apps/compositions/views.py` — plumb `episode` through
  the create action; add `attach-episode` / `detach-episode`
  detail actions.
- `shell/apps/universe/views.py` — extend `Universe.destroy`
  hard-delete preflight to also count Episodes and reject when
  non-zero (add `episode_count` to the 409 body's `blocking`
  dict).
- SPA: extend recipe form with optional Episode picker;
  Composition detail with Episode link.
- `docs/CHARACTER_OS_INVENTORY.md` (regenerated post-migration).

**Do NOT touch:**
- Existing Composition observability code path (SESSION 262
  contract preserved by construction).
- Existing Universe substrate (SESSION 261).
- Retrieval code (`shell/apps/embeddings/retrieval.py`) — Episode
  does NOT influence retrieval scope in v1.
- K6 synthesis, dialogue synthesis, duration contract — unchanged.
- Writing Contract, verifier, media-engine — unchanged.

## Explicit deferrals

Same lifecycle discipline as prior slices — enumerated so no
future reader mistakes their absence for oversight:

- **Narrative memory** (event log, promise ledger, callback edges,
  unresolved threads).
- **Canon promotion mechanic** (`Episode.canonical_composition`
  FK, `Episode.state=CANONICAL`).
- **Relationship substrate** (`RELATIONSHIP_BOUNDARY_V1.md`).
- **WorldEntity substrate** (`WORLD_ENTITY_BOUNDARY_V1.md`).
- **`Episode.referenced_entities` M2M** (paired with WorldEntity).
- **`Episode.sequence` / `order_index`** (explicit sequencing).
- **`Episode.educational_objective` / `audience` / `purpose`**
  (curriculum substrate).
- **Voice / POV versioning on Teammate** (cross-Episode voice
  evolution).
- **Cross-Universe crossover primitive** (invariant 5 preserved;
  no design added here).
- **Cross-Episode Composition ownership** (rejected in
  `EPISODE_VS_COMPOSITION_V1.md §Q9`; one Composition belongs to
  at most one Episode).
- **Batch attach / detach APIs.**
- **Episode-level cost / metrics / analytics** (compositions
  carry cost; Episode may sum them in a future observability
  slice).
- **Universe slug reform / Episode slug** (v1 uses UUIDs in URLs
  for Episode).
- **Auto-derivation of cast from attached Compositions**
  (rejected in §Q6; operator-authoritative).
- **Cross-Universe Episode move** (Episode.universe is immutable
  in v1).
- **SPA warning heuristics** ("You're changing the topic
  substantially; new Episode?" — deferred to a UX slice).

## STOP/GO recommendation

**GO — proceed to implementation.**

Rationale:

1. **Universe substrate is landed** (SESSION 261) and stable.
   Episode.universe FK anchors cleanly against real code.
2. **Composition observability is landed** (SESSION 262) and
   stable. The immutability guard makes Episode-attach safe by
   construction; no observability code needs to change.
3. **All 20 design questions are resolved** with citations to
   file:line and prior design docs. No open architectural
   ambiguity remains.
4. **The schema is fully additive.** Two migrations, both
   nullable / RESTRICT / PROTECT. No data backfill. Legacy paths
   preserved without special-casing.
5. **The vertical slice (§Q20) is executable without provider
   calls.** Every fixture is deterministic; every assertion is
   observable in DB state alone.
6. **No dependency on Relationship or WorldEntity.** Episode
   stands alone.
7. **The 50-item test matrix (§Q19) is exhaustive** across
   schema, validation, API, cast, Composition linkage, retries,
   deletion, legacy, observability non-mutation, and
   cross-Universe isolation.
8. **The design corrections vs the prior slice
   (`EPISODE_VS_COMPOSITION_V1.md` /
   `EPISODE_LIFECYCLE_V1.md`)** are enumerated in the
   frontmatter's `supersedes` block and in §Q2 and §Q5. Nothing
   silent.

**Recommended implementation slice framing:**

- `EPISODE_SCHEMA_V1_IMPLEMENTATION` — single deploy.
- Two migrations (Episode initial + Composition.episode FK).
- One Django app change (`apps/universe/`) + one Composition-side
  extension.
- SPA lands with the backend (mirrors SESSION 261 discipline:
  Universe UI shipped with the Universe substrate to avoid the
  silent-default hazard).
- Full test matrix (~50 tests) as a single test-writing pass.
- Real-mode dogfood after implementation (per operator preference
  from user memory: "propose dogfood by default").

## STOP

Design-only. No schema DDL, no migrations, no code, no database
state changes. This document commits to the design; implementation
begins on operator instruction.
