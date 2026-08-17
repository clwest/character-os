---
title: "Universe Substrate — SESSION 261 Implementation Report"
status: shipped — backend + SPA landed together, migrations applied
date: 2026-08-17
depends_on:
  - "design/UNIVERSE_SCHEMA_V1.md"
  - "design/UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md"
scope: >
  Durable record of the SESSION 261 Universe substrate vertical
  slice. Documents what shipped, migration filenames, test totals,
  contract deviations from UNIVERSE_SCHEMA_V1, deferred items, and
  the recommended first action for SESSION 262 (Episode).
---

# Universe Substrate — SESSION 261 Implementation Report

## What shipped

The **smallest deployable Universe substrate vertical slice** per
`docs/design/UNIVERSE_SCHEMA_V1.md`. Backend and SPA landed
together in one session; the schema and the SPA affordances are one
deployable slice as the contract mandated.

## Landed pieces (in commit order)

| SHA (before push) | Subject |
|---|---|
| `8f54bdb` | `feat(universe): SESSION 261 Phase 1 — Universe app + model + admin + API` |
| `ef10d4e` | `feat(spokespeople): SESSION 261 Phase 2 — Teammate.universe FK + move preview` |
| `ee2fc1d` | `feat(embeddings): SESSION 261 Phase 3 — KnowledgeDocument.universe FK + retrieval isolation` |
| `dd5bf37` | `feat(spa): SESSION 261 Phase 4 — Universe UI + explicit knowledge scope selection` |

Documentation + closeout commits follow (see git log).

## Migration filenames

Additive, nullable, no backfill (per UNIVERSE_SCHEMA_V1.md §"Migration classification"):

- `shell/apps/universe/migrations/0001_initial.py` — creates Universe model.
- `shell/apps/spokespeople/migrations/0012_universe_fk.py` — adds `Teammate.universe` nullable FK with `on_delete=RESTRICT`.
- `shell/apps/embeddings/migrations/0005_universe_fk.py` — adds `KnowledgeDocument.universe` nullable FK with `on_delete=RESTRICT`.

All three applied cleanly to the shared dev DB via `python manage.py migrate` (100/100 applied per inventory regen).

## Test totals

- **Universe-scope tests (this slice's own suites):** 62 passed
  - `apps/universe/tests/test_models.py` — 8 tests
  - `apps/universe/tests/test_api.py` — 12 tests
  - `apps/spokespeople/tests/test_teammate_universe_api.py` — 15 tests
  - `apps/embeddings/tests/test_retrieval_universe.py` — 10 tests (all 9 truth-table rows + the two-Universe cosine isolation test)
  - `apps/embeddings/tests/test_knowledge_universe_api.py` — 14 tests
  - `apps/embeddings/tests/test_retrieval_privacy.py` — 7 tests still green (K2 privacy grep updated to include the new truth-table file in ALLOWED_FILES)
- **Legacy regression (K2 + spokespeople + realtime + conversations + compositions + videos):** 249 passed after Universe changes vs the pre-Universe baseline.
- **Full backend suite (`pytest shell/`):** 2455 passed / 80 failed / 1 skipped. **The 80 failures are pre-existing and unrelated to Universe** — they all live in `apps/bootstrap_review/*` (fixture-path 404s + tampered-byte tests) and `character_os/clients/tests/test_media_engine_timeouts.py`. Verified via `git stash + rerun` at baseline.
- **SPA test suite:** 582 passed / 40 files.
- **SPA TypeScript:** clean (`pnpm tsc --noEmit` — no errors).

Test environment: `DB_PORT=5434 EMBEDDING_FORCE_MOCK=1 pytest ...` (the mock-embedding flag is a pre-existing dev-env convention — otherwise `test_ask.py` demands `OPENAI_API_KEY`).

## Doctor / drift

`python scripts/verify_doc_claims.py`:
- 2 ok, 1 medium drift (**pre-existing** — `docs/CHARACTER_OS_WHAT_IT_IS.md:44` says "14 Django apps" but even before Universe there were 16; now there are 17). Not introduced by this slice; not fixed by this slice.

Inventory (`docs/CHARACTER_OS_INVENTORY.md`) regenerated deliberately after all migrations applied. Reflects Universe substrate (17 apps, 38 models, 100/100 migrations, Django 5.2.16).

## Deviations from UNIVERSE_SCHEMA_V1

1. **Django version.** Design doc says Django 5.0.6; actual is Django 5.2.16 (verified via `python -c 'import django; print(django.VERSION)'`). Semantically equivalent — `on_delete=RESTRICT` and the shared-CASCADE-parent rule both landed in Django ≥ 3.1, and the newer version doesn't change any documented behavior. No implementation change needed.
2. **`universe-move-preview` M2M enumeration uses `getattr` fallback.** Universe move preview reads `getattr(doc, 'universe_id', None)` (rather than `doc.universe_id` directly on `.only("id", "title", "universe_id")`) so that Phase 2 could stand as an independent commit ahead of Phase 3's `KnowledgeDocument.universe` FK. After Phase 3 landed both the FK and its migration, this fallback is a no-op — but leaving it preserves defensive robustness if the FK is ever ripped out for any reason. No semantic difference; no test failures.
3. **Serializer create() vs update() PATCH universe path.** The design's §"Endpoints that MUST change" said the `KnowledgeDocumentSerializer` needs `universe` in `Meta.fields` and validation. The implementation goes a step further: `update()` runs an M2M-orphan preflight so a PATCH that would violate the Universe-M2M invariant returns a clean 400 with the offending spokesperson names instead of letting the m2m_changed signal raise generically. Tighter operator UX; strict superset of the contract.
4. **UniverseViewSet.unarchive lookup is manual, not `get_object()`.** The default `get_queryset` filters out archived rows unless `?include_archived=true`; the unarchive action would 404 on that path since its whole purpose is to act on an archived row. Implementation queries the Universe directly (workspace-scoped) and calls `check_object_permissions()`. Same net authorization; different plumbing.
5. **Ingestion functions plumb `universe=None` kwarg through.** Design specified where to add the FK; implementation added the passthrough kwarg to `_persist / ingest_text / ingest_pdf / ingest_url` so the serializer `create()` can hand the Universe scope in. Otherwise the `.objects.create(universe=universe)` line would need to move up into the serializer bypassing the ingest orchestrator. No semantic difference.

## What was NOT touched (explicit deferrals — carried forward for SESSION 262+)

Per UNIVERSE_SCHEMA_V1.md §"Explicit deferrals":

- Episode model, `Composition.episode` FK, Episode lifecycle (`EPISODE_VS_COMPOSITION_V1.md`, `EPISODE_LIFECYCLE_V1.md`).
- Relationship model (Character↔Character edges) — `RELATIONSHIP_BOUNDARY_V1.md`.
- WorldEntity model, `Episode.referenced_entities` M2M — `WORLD_ENTITY_BOUNDARY_V1.md`.
- Narrative memory / event log / promise ledger.
- Character↔WorldEntity edges; WorldEntity↔WorldEntity edges.
- Canon promotion mechanic.
- Educational curriculum substrate.
- Per-Universe palette / brand identity (extending CSS-var brand swap).
- Cross-Universe crossover primitive.
- Voice / POV versioning on Teammate.
- Non-human canonical identity via Character Presence Language (blocks Patch/Rivet/Biscuit fully-approved CharacterIdentity — named, not addressed).
- Legacy bulk cleanup / migration (per-Teammate bespoke ½-slices only).
- `Composition.universe` direct FK (transitive via `spokesperson.universe` suffices for v1).
- `Asset.universe` FK.
- Slug uniqueness reform on Workspace (SESSION 259 wart §8; unrelated).
- SPA workspace picker (pre-existing gap).
- Membership sub-scoping (per-Universe seats/roles).
- Universe visual identity.
- Universe-per-owner / cross-workspace Universe primitive.
- Bulk API for creating multiple Universes / assigning multiple Teammates at once.

## Orphaned legacy knowledge (informational)

Tulsi, TANK, Hearth & Hollow etc. remain `universe=NULL` — legacy workspace-wide semantics preserved exactly. Prospective Universe isolation makes the eventual per-item cleanup independent (not a blocker for this slice).

## SPA operator flow (as landed)

- `/workspace/universes` — list + create form (name + optional description; slug auto-derived per-workspace).
- `/workspace/universes/:id` — detail: edit, archive, unarchive, hard-delete (disabled if populated; backend returns 409 with blocking counts otherwise), plus lists of member teammates + docs.
- `/spokespeople/:id` — new `SpokespersonUniversePanel` between IdentityPanel and Videos/Setup panels: select Universe (or "None (legacy)"), Save fires `universe-move-preview` first, opens confirmation modal listing offending K2 attach rows if any, and only PATCHes on operator confirm.
- `/workspace/knowledge` — every upload tab (Paste / Upload PDF / URL / Search) requires the operator to pick a scope (Universe or explicit "None (legacy)") before Submit enables. Search-result Ingest button is likewise disabled until scope is picked. **The silent workspace-wide default is gone at the SPA layer** — the API stays backward-compatible (omitting `universe` still creates a legacy doc) so external callers are unbroken, but the SPA no longer offers an "upload without picking scope" path.
- Dashboard — "Worlds" link added next to the Knowledge tile's "View all" link, giving operators a discoverable entry point without a new nav-rail slot.

## Recommended first action for SESSION 262

Per `docs/design/UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md §"Model implementation sequencing"`: **`EPISODE_SCHEMA_V1`** — draft the Episode model contract on the substrate this slice landed. Episode is the narrative layer above render provenance; it depends on Universe existing but does NOT depend on Relationship / WorldEntity. Follow-on slices (Relationship, WorldEntity, narrative memory, canon promotion) then attach to Episode.

Before Episode implementation begins, the integration checkpoint's Composition observability backlog (verbatim `operator_topic`, per-attempt log, first-pass raw synthesis, corrective retry hints, retry count) should ideally land — Episode depends on those for the promise-ledger + event-log surfaces to work.

## Surprising discoveries

- **Django version drift.** Design docs cite Django 5.0.6 throughout; actual is 5.2.16. RESTRICT semantics are the same; documented for future reference.
- **Legacy grep test needed updating.** The K2 privacy grep test's `ALLOWED_FILES` list needed one new entry for the truth-table test — the test's `KnowledgeChunk.objects.create` call is a sanctioned writer path, but the guard rightly flags anything new by default.
- **Ingestion plumbing wasn't obvious.** `_persist` is the only place `KnowledgeDocument.objects.create` runs; adding `universe=` needed a passthrough all the way from serializer through the three `ingest_*` orchestrators. Straightforward once mapped, but not the shape a naive "just add the field to the serializer" read of the design would produce.
- **80 pre-existing backend test failures.** All in `apps/bootstrap_review/*` and `character_os/clients/tests/test_media_engine_timeouts.py`. Reproduce cleanly on baseline stash; not caused by Universe work; not fixed by Universe work (per the "do NOT fix unrelated pre-existing failures" guardrail).
