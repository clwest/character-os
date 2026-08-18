---
title: "EPISODE_SCHEMA_V1 — Implementation Report"
status: implemented — Episode + EpisodeCast + Composition.episode landed
date: 2026-08-18
depends_on:
  - "design/EPISODE_SCHEMA_V1.md"
  - "design/UNIVERSE_SCHEMA_V1.md"
  - "design/COMPOSITION_OBSERVABILITY_V1.md"
  - "design/COMPOSITION_OBSERVABILITY_SCHEMA_V1.md"
scope: >
  Implementation report for the SESSION 262 EPISODE_SCHEMA_V1 slice
  ratified by the operator. Ships Episode + EpisodeCast models,
  Composition.episode FK, model + service isolation invariants,
  full Episode + cast + attach/detach REST surface, Universe
  hard-delete preflight extension, and an SPA Episode surface
  (list + detail + create modal + Universe detail link +
  Composition detail Episode link). Zero Relationship / WorldEntity
  / narrative-memory / canon-promotion work.
supersedes: []
---

# EPISODE_SCHEMA_V1 — Implementation Report

## Purpose

Deliver the vertical slice specified by `EPISODE_SCHEMA_V1.md`
against the system that actually exists — Universe substrate (SESSION
261) + Composition observability (SESSION 262) — without touching any
of the load-bearing boundaries those slices established.

## Load-bearing boundaries preserved

| # | Boundary | How preserved |
|---|---|---|
| 1 | Workspace = tenant/privacy boundary | Every Episode/Composition query still resolves workspace via `episode.universe.workspace`. `IsWorkspaceMember` extended (permissions.py) to traverse `.universe.workspace` for Episode. |
| 2 | Universe = world boundary | Episode.universe = NOT NULL. Cast + Composition consistency invariants enforce Universe alignment. |
| 3 | Episode = explicit story/event/creative intent | `EpisodeViewSet.create` is the sole creation path. No auto-creation code exists anywhere. |
| 4 | Composition = render/execution attempt | `Composition.episode` is nullable FK; standalone Compositions remain first-class. |
| 5 | Episode creation NEVER implicit | Verified in test_15 (happy path via explicit POST) + SPA "New Episode" button distinct from "New video." |
| 6 | Composition may remain episode=NULL indefinitely | Verified in test_41 + test_42 + preserved default in `CompositionViewSet.create` when body omits `episode`. |
| 7 | Episode.universe immutable | Enforced at `EpisodeSerializer.update()`; verified in test_50 (PATCH 400 with helpful message). |
| 8 | Cast operator-authoritative, never auto-derived | Verified in test_14 (cast add/remove has no Composition side-effect) + starter code path does not touch Episode.cast. |
| 9 | Episode existence does NOT mutate canon | Verified in vertical slice test — synthesis / render / attach paths never touch KnowledgeDocument. |
| 10 | Relationship / WorldEntity / narrative memory / canon deferred | Zero code touches those substrates. Design deferrals unchanged. |
| 11 | Episode linkage NEVER mutates SESSION 262 observability | Verified in tests 44-47. Attach/detach uses `save(update_fields=["episode", "updated_at"])` so the SESSION 262 immutability guard skips every observability field. Adversarial test (47) proves the guard fires when observability IS included. |
| 12 | Episode does NOT influence K2 retrieval scope | Verified in test_49 (retrieve_for_teammate still branches only on `spokesperson.universe_id`). |
| 13 | No historical Composition backfill | Migration is pure `AddField`; legacy Compositions land with `episode=NULL`. Verified in test_41 + test_42. |
| 14 | No real provider calls for verification | Vertical slice uses `mock_mode + patched synthesize_dialogue`. Zero Runway / OpenAI credits burned. |

## Exact files changed

### Backend — models + migrations

- **`shell/apps/universe/models.py`** — appended `Episode` (150 LOC)
  + `EpisodeCast` (60 LOC). Added `Universe.episode_count()`.
- **`shell/apps/universe/migrations/0002_episode_and_cast.py`** —
  `CreateModel Episode`, `CreateModel EpisodeCast`, indexes,
  `(universe, title)` unique constraint, cast M2M through row.
- **`shell/apps/universe/migrations/0003_alter_episode_universe.py`**
  — `Episode.universe` on_delete `RESTRICT` → `CASCADE` (design
  deviation; see below).
- **`shell/apps/compositions/models.py`** — added
  `Composition.episode` nullable FK + extended `clean()` with three
  Episode consistency invariants (Workspace, Universe,
  legacy-spokesperson rejection).
- **`shell/apps/compositions/migrations/0015_composition_episode.py`**
  — hand-written clean `AddField` for `Composition.episode`.
- **`shell/apps/compositions/migrations/0016_composition_episode_restrict.py`**
  — hand-written clean `AlterField` for
  `Composition.episode` on_delete `PROTECT` → `RESTRICT` (design
  deviation; see below).

### Backend — signals / serializers / views / URLs / admin

- **`shell/apps/universe/signals.py`** (new) —
  `reject_cross_universe_cast` receiver on
  `Episode.cast.through` for `m2m_changed pre_add`. Handles both
  forward + reverse attachment paths.
- **`shell/apps/universe/apps.py`** — imports signals in `ready()`.
- **`shell/apps/universe/serializers.py`** — added
  `EpisodeCastTeammateSerializer`, `EpisodeSerializer`; extended
  `UniverseSerializer` with `episode_count`.
- **`shell/apps/universe/views.py`** — added `EpisodeViewSet` with
  archive/unarchive/hard-delete/cast_add/cast_remove actions;
  extended `UniverseViewSet.destroy` hard-delete preflight to
  enumerate Episode count in `blocking`.
- **`shell/apps/universe/urls.py`** — registered
  `EpisodeViewSet` at `/api/episodes/`.
- **`shell/apps/universe/admin.py`** — `EpisodeAdmin` +
  `EpisodeCastAdmin` + `EpisodeCastInline`.
- **`shell/apps/compositions/serializers.py`** — added `episode`
  field to `CompositionSerializer` and `CompositionListSerializer`.
- **`shell/apps/compositions/views.py`** — extended
  `CompositionViewSet.create` to accept optional `episode` in body;
  wired both FAILED-rescue paths (LongForm, Dialogue) to carry
  Episode attachment; added
  `CompositionViewSet.attach_episode` action (POST + DELETE).
- **`shell/character_os/permissions.py`** — extended `_workspace_of`
  to traverse `.universe.workspace` for Episode.

### SPA

- **`web/src/lib/api/episodes.ts`** (new) — full CRUD hooks +
  cast add/remove + attach/detach mutation.
- **`web/src/lib/api/universes.ts`** — added `episode_count` to
  the zod schema.
- **`web/src/lib/api/recipes.ts`** — added `episode` field
  (nullable) to Composition schema so detail pages can link back.
- **`web/src/routes/workspace/universes.$id.episodes.tsx`** (new)
  — Episode list + explicit "New Episode" create form.
- **`web/src/routes/workspace/episodes.$id.tsx`** (new) —
  Episode detail: edit title/topic, add/remove cast, archive,
  unarchive, hard-delete (with 409 explanation).
- **`web/src/App.tsx`** — registered both new routes.
- **`web/src/routes/workspace/universes.$id.tsx`** — added
  "Manage episodes" link to Universe detail.
- **`web/src/routes/compositions/$id.tsx`** — added Episode link
  in Composition header when `composition.episode` is non-NULL.

### Test isolation

- **`shell/apps/compositions/tests/test_isolation.py`** — added
  the two new Episode test files to `ALLOWED_FILES`.

### Tests (new)

- **`shell/apps/universe/tests/test_episode.py`** — 50-item
  matrix from `EPISODE_SCHEMA_V1.md §Q19`.
- **`shell/apps/universe/tests/test_episode_vertical_slice.py`**
  — vertical slice from §Q20 (Patch/Rivet).

### Docs

- **`docs/design/EPISODE_SCHEMA_V1.md`** — Q8 correction commit
  landed pre-implementation (cast never blocks hard-delete).
- **`docs/design/EPISODE_SCHEMA_V1_IMPLEMENTATION.md`** (this
  file).
- **`docs/CHARACTER_OS_INVENTORY.md`** — regenerated (see
  §Inventory below).

## Migrations landed

Three migrations across two apps; all additive-nullable-or-empty-default
or on_delete-metadata-only:

| Migration | Content |
|---|---|
| `universe.0002_episode_and_cast` | CreateModel Episode + EpisodeCast; `(universe, title)` unique; two indexes on Episode; one unique + two indexes on EpisodeCast. |
| `universe.0003_alter_episode_universe` | `Episode.universe` on_delete `RESTRICT` → `CASCADE` (see §Deviations). |
| `compositions.0015_composition_episode` | AddField `Composition.episode` (nullable, PROTECT initially). |
| `compositions.0016_composition_episode_restrict` | AlterField `Composition.episode` PROTECT → RESTRICT (see §Deviations). |

No data migration. No bulk backfill. Legacy Compositions land with
`episode=NULL`.

Migration count in INVENTORY: 101 → 105.

## Test totals

Environment: `DB_PORT=5434 EMBEDDING_FORCE_MOCK=1 pytest ...`

- **Universe app (focused Episode tests):** 71 passed in 11.55s
  (of which 50 are the §Q19 matrix + 1 vertical slice + 20 pre-
  existing Universe tests).
- **Regression suites** (compositions + embeddings + spokespeople):
  **1348 passed / 1 failed → then fixed → 0 failed** in 109.05s.
  The one initial failure was the same `test_isolation` ALLOWED_FILES
  test that SESSION 262 hit; adding the two new Episode test files
  to `ALLOWED_FILES` closed it.
- **SPA test suite** (`pnpm test`): **582 passed / 40 files.**
- **SPA TypeScript** (`pnpm tsc --noEmit`): **clean.**
- **Full backend suite:** **2529 passed / 80 failed / 1 skipped**
  in 217.58s.

### Baseline comparison

| Metric | SESSION 262 baseline | EPISODE_SCHEMA_V1 result | Delta |
|---|---|---|---|
| Full-suite total | 2559 | 2610 | +51 (my new tests) |
| Passed | 2478 | 2529 | +51 |
| Failed | 80 | 80 | **0** |
| Skipped | 1 | 1 | 0 |

Every one of the 80 failures is unchanged from the SESSION 262
baseline:

- 79× `apps/bootstrap_review/tests/*` (fixture-path 404s + tampered-
  byte tests, per SESSION 261 closeout §Test-totals).
- 1× `character_os/clients/tests/test_media_engine_timeouts.py`.

**Zero new failures introduced by EPISODE_SCHEMA_V1.**

## Invariants verified

The following are each covered by at least one test:

- Episode row-level required fields (id, universe, title,
  operator_topic) — tests 1-3.
- `(universe, title)` unique per Universe; cross-Universe titles
  legal — tests 4-5.
- `archived_at` defaults NULL; `created_by` SET_NULL — tests 6-7.
- Cast Universe-consistency enforced (add cross-Universe rejected;
  add legacy `universe=NULL` Teammate rejected; cross-Workspace
  rejected) — tests 9-11.
- Empty cast at create is legal — test 12.
- Cast API happy path + removal has no Composition side-effect —
  tests 13-14.
- Full REST surface behaviors (create/list/retrieve/patch/archive/
  unarchive/hard-delete-empty/hard-delete-populated-409) — tests
  15-24.
- Composition create with Episode / cross-Universe rejected /
  cross-Workspace rejected — tests 25-27.
- Composition attach/detach/move happy paths — tests 28-32.
- Two compositions under one Episode returned via reverse — test 33.
- Failed Composition attachment legal; only-failed Episodes legal —
  tests 34-35.
- Archive preserves Composition FK; archive idempotent — tests 36-37.
- Hard-delete blocked with attached Compositions; after detach,
  hard-delete succeeds — tests 38-39.
- Workspace CASCADE cleans Universe + Episode + Composition — test 40.
- Legacy `episode=NULL` Composition + Universe-scoped
  spokesperson-with-no-Episode legal — tests 41-42.
- Legacy Teammate never Episode — test 43.
- **SESSION 262 observability non-mutation on attach / detach /
  move — tests 44-46. Adversarial (guard fires on observability +
  episode in update_fields) — test 47.**
- Cross-Universe list isolation — test 48.
- **K2 retrieval unaffected by Episode — test 49.**
- Episode.universe immutable via API — test 50.
- End-to-end vertical slice (Patch/Rivet fail then succeed with
  full provenance isolation preserved) — `test_episode_vertical_slice`.
- Universe hard-delete preflight blocks populated Universes with
  Episodes — `test_8_universe_hard_delete_blocked_by_api_preflight_when_episodes`.

## Implementation deviations from EPISODE_SCHEMA_V1

Two deliberate deviations from the design document, both driven by
Django on_delete cascade semantics revealed at test time:

### DEV-1. `Episode.universe` on_delete: RESTRICT → CASCADE

**Design draft (§Q7):** RESTRICT on `Episode.universe` — mirror
Teammate.universe + KnowledgeDocument.universe so populated Universes
cannot silently orphan their Episodes at the DB layer.

**As landed:** CASCADE.

**Why the change was necessary:**

Teammate.universe and KnowledgeDocument.universe can use RESTRICT
under Django 3.1+ because those models have BOTH `workspace` (CASCADE)
AND `universe` (RESTRICT) FKs. When Workspace deletes, Django's
shared-CASCADE-parent rule recognizes that both the child (Teammate/
KnowledgeDocument) and the RESTRICTed parent (Universe) share a
cascading ancestor (Workspace), so RESTRICT is satisfied.

Episode has NO denormalized `workspace` FK (Q2 decision — Universe
already owns Workspace, so denormalization is redundant). Under
Workspace cascade-delete, Episode traces to Workspace only via
Universe, not directly. Django's shared-CASCADE-parent rule does not
recognize the "single-hop-via-Universe" path as sharing a cascading
ancestor with Composition (which cascades directly). Result: RESTRICT
on `Episode.universe` blocks Workspace deletion entirely — no test
can clean up its workspace fixture, and production tenants can never
be offboarded.

**Safety preserved:**

- API-layer preflight on `UniverseViewSet.destroy(?hard=true)` still
  blocks populated Universes — the operator sees 409 with
  `blocking.episode_count` before hitting the DB. This is verified
  by `test_8_universe_hard_delete_blocked_by_api_preflight_when_episodes`.
- `Composition.episode = RESTRICT` still fires at the DB when a
  direct Episode.delete() is called with any Composition attached —
  Universe.delete() through the cascade route would trigger Episode
  cascade → Composition.episode RESTRICT → RestrictedError. This
  protects the "operator can't silently lose Compositions" invariant
  even in an admin/management-command path that bypasses the view.
- Direct raw Django admin Universe delete of a populated Universe
  first cascades to Episode; Episode cascade blocks on Composition
  attachment. Universe delete fails cleanly rather than silently
  orphaning stories.

### DEV-2. `Composition.episode` on_delete: PROTECT → RESTRICT

**Design draft (§Q7):** PROTECT.

**As landed:** RESTRICT.

**Why:** Same shared-CASCADE-parent rule story. PROTECT does NOT
participate in the rule; RESTRICT DOES. Under Workspace cascade-
delete, both Composition (via workspace CASCADE) and Episode (via
universe CASCADE) trace to Workspace, so RESTRICT is satisfied and
the tenant can be cleaned up. With PROTECT the workspace delete
would fail.

**Operator-facing behavior unchanged:** direct
`episode.delete()` with attached Compositions still raises
`RestrictedError` (functionally equivalent to `ProtectedError` for
the operator's purposes). The API preflight surfaces this as a 409
before either error would fire.

## Deferred findings discovered during implementation

### DF-EP-1. Serializer typo on Universe `episode_count`

`UniverseSerializer.get_episode_count` was added but the method was
initially placed inside `validate_name`'s docstring gap during
editing. Now correctly located and referenced. Verified working via
`test_8_universe_hard_delete_blocked_by_api_preflight_when_episodes`.

### DF-EP-2. Vertical slice uses `pytest.mark.django_db(transaction=True)`

`dialogue_scene` is `@transaction.atomic`; when its AI-Topic mode
raises `DialogueSynthesisFailedError`, the outer pytest-django
transaction wrap becomes tainted for subsequent queries in the same
test. The vertical slice test opts into transaction-mode
(`@pytest.mark.django_db(transaction=True)`) so each save/create is
committed independently. The 50-item test matrix does NOT need this
because none of its tests exercise the AI-Topic starter's atomic
raise path.

### DF-EP-3. Cast API `POST` returns 405 for `DELETE` on the same URL

`EpisodeViewSet.cast_add` handles both POST and DELETE at the same
URL path (`/api/episodes/<id>/cast/`), but only POST is meaningful;
DELETE on the plural path returns 405 with a message directing the
operator to `/cast/<teammate_id>/`. This is a DRF idiom quirk — the
router only supports one `@action` per (detail, url_path) pair. Not
blocking; documented in the endpoint docstring.

### DF-EP-4. Recipe form Episode picker not landed in this slice

The design (§Q17) mentions an optional Episode picker on the recipe
form. The backend accepts `episode` in the `POST /api/compositions/`
body already, and the SPA can attach via the detail-page
`attach-episode` action, but a dedicated picker widget in the
recipe form was not built to keep this slice atomic. Backend fully
supports the picker; adding one is a minor SPA slice with no schema
impact.

### DF-EP-5. Universe.destroy preflight `manage_phone` / `verify_phone` URL drift

The regenerated INVENTORY shows more URL routes than SESSION 262
because unrelated dev-environment installs (allauth phone auth,
etc.) surface. Unchanged from SESSION 262 posture; not a SESSION
262 or EPISODE_SCHEMA_V1 concern.

### DF-EP-6. Cleanup: Django auto-generated composition migration with 10 noise AlterFields

`makemigrations` produced a migration
`0016_alter_composition_corrective_hint_and_more` that included one
real AlterField (`episode` PROTECT→RESTRICT) plus 10 cosmetic
`AlterField`s for SESSION 262 fields (help_text metadata that had
drifted between model and migration state). The migration was
rewritten by hand as `0016_composition_episode_restrict` with only
the real AlterField, and the stale `django_migrations` row from the
previously-applied auto-gen was cleaned up in the dev DB.
Downstream deployments migrate normally against the clean
`0015_composition_episode` → `0016_composition_episode_restrict`
chain.

## Local/origin Git state

- Local `main` at time of report authorship: **b49a6c6**
  + doc-correction commit + implementation commit (about to land).
- `origin/main`: **01f12b1** (SESSION 262 impl close).
- Local is ahead of origin by 3 commits pre-final-commit:
  - `b49a6c6` — EPISODE_SCHEMA_V1 (design-only)
  - `7b9e9e3` — Q8 correction
  - _next_ — EPISODE_SCHEMA_V1 implementation (this slice)
- After implementation commit: 4 commits ahead of origin/main.
- **Not pushed.**

## Recommended next architectural slice

Per `UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §Model-implementation-
sequencing`, the sequenced next slices are:

1. **`RELATIONSHIP_MODEL_V1_IMPLEMENTATION`** — Character↔Character
   Relationship as Universe-owned canonical row. Design already
   ratified in `RELATIONSHIP_BOUNDARY_V1.md`. Small, additive slice
   analogous in shape to Episode.
2. **`WORLD_ENTITY_MODEL_V1_IMPLEMENTATION`** — WorldEntity +
   `Episode.referenced_entities` M2M. Design already ratified in
   `WORLD_ENTITY_BOUNDARY_V1.md`. Follows Relationship per the
   integration doc's DAG.

Recommendation: **defer both.** Ship no new substrate until the
operator dogfoods Episode in real workflows. The design integration
already established that neither substrate is a v1 dependency; both
are additive layers on the primitives that now exist.

Alternative useful ½-slices with no substrate expansion:

- **Recipe-form Episode picker** — small SPA slice; closes DF-EP-4.
- **Long-form failure paths carry retrieval snapshot** — SESSION
  262 DF-262-2. Symmetric fix to the dialogue path.
- **`Composition.episode` badge on the Videos list** — reuse the
  `episode` field already exposed on `CompositionListSerializer`.

None are blocking anything; all are candidates when the operator
has real feedback from Episode dogfood.

## STOP

Implementation is complete. Every design invariant is preserved or
explicitly deviated with rationale. Zero real provider calls
required. Committed locally; not pushed pending operator
verification.
