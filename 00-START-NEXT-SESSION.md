---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`
> (locked SESSION 178 — 10 contract rules, B0-B10 slice
> breakdown). **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V2.md`
> (locked SESSION 178 — supersedes V1). Premium enterprise
> dark + gold; Geist + JetBrains Mono.
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — **22 contract rules** total: V1's 9 + V17's
> 4 merged as rules 10-13 + Asset Library's 9 merged as rules 14-22;
> V0-V15 + V16 slice breakdown).
> **V16 POST-CLOSE SHIPPED (SESSION 179) — remove_avatar_background.**
> **V17 LOCKED (SESSION 182) — extend + keyframes.**
> V17.0 + V17.1 + V17.2 + V17.5 SHIPPED + REAL-MODE VALIDATED.
> **V17.3 DEFERRED (SESSION 184)** — see Q-v17-6 in
> `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`.
> **V18 SHIPPED + REAL-MODE VALIDATED (SESSION 184).**
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE + REAL-MODE HARDENED
> (SESSION 176).**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5 sub-slices 1/2/3 COMPLETE.**
> **Asset Library scope lock:** `docs/design/ASSET_LIBRARY_V1.md`
> (locked SESSION 185). **10 roles**, 9 contract rules merged
> into V1 as rules 14-22, **9 slices A0-A8** (~5-6 sessions).
> **A0+A1+A2+A3+A4 SHIPPED — backend layer complete. A5
> (SPA list view) next.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_188_A4_WORKSPACE_ASSETS_API.md`.

---

## SESSION 188 outcome — A4 workspace assets API

Clean single-slice session. One feature commit + handoff
close. **A4 ships:** `GET /api/workspace/assets/` (paginated
browse with role / asset_type / primitive_kind / storage / q
/ created_after / created_before filters) +
`GET /api/workspace/assets/<id>/` (per-asset detail with
producing step + downstream consumers). `storage_health`
attached to every row live via A3. **Backend layer
complete (A0+A1+A2+A3+A4)** — A5 can start the SPA against
a live endpoint.

Test totals **956 → 980 (+24)** — all 24 new tests in
`test_workspace_assets_api.py`. Compositions suite **525 →
549**. No real-mode spend.

### A4 — workspace assets read endpoints

* **`WorkspaceAssetViewSet`** in `apps/compositions/views.py` —
  GenericViewSet with custom `list` + `retrieve`. Inline
  serialization (matches existing pattern from `AssetViewSet` /
  `ImageViewSet`).
* **`WorkspaceAssetPagination`** — PageNumberPagination
  subclass; `page_size=25`, `max_page_size=100`.
* **URLs**: two paths added to `apps/compositions/urls.py`:
  `workspace/assets/` (list) +
  `workspace/assets/<uuid:pk>/` (retrieve). Mounted by
  hand (not router) because A4 has only list + retrieve.
* **Workspace resolution mirrors F-arc's
  `workspace_overview`** — explicit `?workspace=` if
  provided + member, else `default_workspace_for(user)`.
  Same exception shapes for consistent SPA error handling.
* **Storage filter is post-query** — `storage_health` is
  computed, not a DB column. Filter narrows the
  query-time-filtered candidate set with a 1000-row cap
  before applying storage filter. A5 perf testing may
  motivate an annotated column later.
* **Lineage inverted from F5** — `/api/compositions/<id>/lineage/`
  walks composition→composition; A4 retrieve walks
  asset→compositions on both sides (producing composition +
  producing step + downstream consumers via step inputs
  scan).
* **Distinct from existing `/api/assets/`** — V15.2
  asset_picker stays at the old URL; A7 will extend it
  with role filter. A5/A6 build against the new endpoint.
* **`test_workspace_assets_api.py`** — 24 tests across
  auth + scoping + cross-workspace leakage + all filters
  individually + pagination + retrieve lineage + 404
  paths.
* **`test_isolation.py` ALLOWED_FILES** entry added.

### Tests at SESSION 188 close

| Suite | Count | Delta |
|---|---|---|
| Django | **980** | +24 (956 → 980) |
| - compositions | **549** | +24 (525 → 549) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

Real-mode spend SESSION 188: **$0** (endpoint + tests
only).

---

## FIRST THING (SESSION 189): slice A5

A4 closed the backend. **A5 is the SPA list view that consumes
the new endpoint — first operator-visible Asset Library
surface.**

**A5 deliverable: SPA route `/workspace/assets` — paginated
list with filter chips.** Per scope lock §"Slice breakdown":

1. **Route**: `web/src/routes/workspace/assets/index.tsx` (or
   wherever the SPA's React Router config registers it).
2. **API client**: new `web/src/lib/api/workspace-assets.ts`
   with Zod schemas mirroring the A4 endpoint shape
   (`_serialize_list_asset` in `apps/compositions/views.py`),
   React Query hooks for list (paginated) + retrieve.
3. **Filter chips**: role / asset_type / storage as visible
   toggles; q / created_after / created_before behind a
   "More filters" disclosure. Multi-select where the API
   takes comma-lists.
4. **Per-row card**: thumbnail (or icon for non-IMAGE/CLIP),
   title + subject + role badge + storage-health badge,
   primitive_kind chip, producing composition link.
5. **Pagination controls**: page number + page size
   selector (25 / 50 / 100). Use the API's `next` / `previous`
   URLs from DRF's PageNumberPagination response shape.
6. **Honest gap note**: visible disclosure that "Avatars,
   voices, and portraits live on Spokesperson — not shown
   here in v1" per Q-a-6 deferral.

A5 estimated effort: 1 session. Larger than A1-A4 (each
½ session) — spans Zod schemas + React Query hooks + page
route + filter chips + pagination + per-row card.

### Alternative paths for SESSION 189

If A5 feels too large for one session:

* **Path B — A5 + A6 split across two sessions.** Ship the
  list view + filters in SESSION 189; per-asset detail (A6)
  in SESSION 190.
* **Path C — A7 first (½ session).** Smaller payoff but
  faster: extend the existing `/api/assets/` picker
  endpoint with `role` filter so V18's `backdrop_clip_id`
  dropdown filters to `role=BACKDROP`. The asset_picker
  scope-lock (Q-a-5) says first-class `RecipeField.role_filter`.
  Lands the structural fix that motivated the whole
  arc — even if A5/A6 land later.

The `react-web-delivery` agent (`@/.claude/agents/react-web-delivery`)
is the default tool for A5 — Vite / Tailwind / shadcn/ui
pattern matches the SPA scope lock.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete +
R-arc real-mode validated (SESSION 176); V-arc real-mode
validation **near-complete** (16 of 18 recipes). V16
post-close shipped (SESSION 179); **V17 scope-locked
SESSION 182, V17.0/1/2/5 shipped + real-mode validated**;
**V17.3 + V17.4 deferred (SESSION 184)**.
**V18 shipped + real-mode validated SESSION 184.**
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent
(SESSION 178 B-arc).
**Asset Library v1 arc IN FLIGHT (SESSION 185-188):**
A0 + A1 + A2 + A3 + A4 SHIPPED — backend layer complete.
Every new Asset carries a role by construction; rule 20
enforced by test; storage-health classifier attached to
every row by the new `/api/workspace/assets/` endpoint.
**A5 (SPA list view) opens next.**

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); 16/18 real-mode validated |
| V17.0 + V17.1 + V17.2 + V17.5 | DONE + REAL-MODE VALIDATED |
| **V18 (backdrop_clip on V8)** | DONE + REAL-MODE VALIDATED (SESSION 184) |
| V17.3 (keyframes) + V17.4 | DEFERRED (SESSION 184) — Q-v17-6 |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED |
| W11.6.0-W11.6.5 (media gen) | DONE |
| W11.x voice telemetry + W11.y personality split | DONE |
| K7.1 cost telemetry | DONE |
| K7.x v2 YouTube extractor | DONE |
| Multi-step composition title disambig | DONE |
| Sasha + Donny voice re-persist | DONE |
| B0-B5 brand ecosystem pivot | DONE |
| V16 remove_avatar_background | DONE |
| V9 polish form shorthands + intro_outro fixes | DONE |
| V7/V11/V13 dogfood fixes + 11 recipes validated | DONE |
| V17.2 cinematic_visual_extended + 4 dogfood fixes | DONE + REAL-MODE VALIDATED |
| V17.5 V8 opt-in extend | DONE + REAL-MODE VALIDATED |
| Polish slice 1 (duration fallback + null guard) | DONE + REAL-MODE VALIDATED (SESSION 184) |
| smoke_keyframes management command | DONE + REAL-MODE VALIDATED (SESSION 184) |
| Asset Library v1 — A0 enum + migration | DONE (SESSION 185) |
| Asset Library v1 — A1 backfill command + dev-DB --commit | DONE (SESSION 185) |
| **Asset Library v1 — A2 primitives stamp role at emit** | **DONE (SESSION 186)** |
| **Asset Library v1 — A3 storage-health helper** | **DONE (SESSION 187)** |
| **Asset Library v1 — A4 workspace assets API** | **DONE (SESSION 188)** |
| Asset Library v1 — A5 SPA list view | **NEXT (SESSION 189)** |
| Asset Library v1 — A6 / A7 / A8 | Queued |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI (AUDIO / IMAGE) | Queued (SESSION 181); intersects Asset Library arc |
| V18 duration-mismatch starter warning | Queued (SESSION 184) |
| Cast rebuild via fresh gen4_image portraits | Queued (SESSION 184) |
| Smoke `--save-assets` default opt-in | Queued (SESSION 184) |
| 2 of 18 V-arc recipes unvalidated | `storyboard_voiced` + `dialogue_scene`; deferrable now that V17 is deferred |

**Cast roster in workspace `admins-workspace`** (unchanged
SESSION 186):

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice `david`

**SESSION 185 dev-DB backfill (--commit applied, unchanged
SESSION 186):**

* 128 of 136 RAW_UPLOAD candidates updated across 8 roles.
* 8 needs-review legacy rows remain at RAW_UPLOAD (2
  audio + 6 image in `Admin's workspace`, pre-dating
  primitive_kind discipline). Per-asset tagging deferred
  to post-v1 upload-UI / mutation surface.
* **From SESSION 186 forward, every new Asset row carries
  a real role by construction.** The runner's
  defense-in-depth raise + the AST coverage test together
  mean a primitive cannot ship without stamping role.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host localhost --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174 — V2 dark navy + gold
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**SESSION 189 stack-up notes:**

* **SPA stack required.** A5 is frontend work. `pnpm dev`
  for the SPA at :5174; Django shell at :8000 to serve
  the live `/api/workspace/assets/` endpoint A5 consumes.
* **No backend changes expected.** A5 should not require
  backend edits; if it does, the A4 endpoint shape needs
  a follow-up doc decision before reshaping. Backend
  endpoint shape is in `_serialize_list_asset` /
  `_serialize_detail_asset` in
  `apps/compositions/views.py`.
* **Use the `react-web-delivery` agent** for the SPA
  slice. Vite / Tailwind / shadcn/ui pattern matches the
  SPA scope lock.
* Uvicorn `--reload` window — wait for "Application
  startup complete" between rapid edits per SESSION 180
  TRUST_CALIBRATION.

**Slice-open checklist (codified SESSION 182, hardened SESSION 184):**

For any new recipe or primitive that wraps a third-party API:

1. **Live-doc check** the API surface the slice
   depends on. Now 2-for-2 hit rate on V17 surface
   area (Q-v17-1, Q-v17-6) — non-optional.
2. **String choice values** in recipe `select` fields
   per the SPA Zod schema.
3. **`LIVE_RECIPE_KINDS` opt-in** in
   `web/src/lib/api/recipes.ts` for new recipes.
4. **Default-aware form submission** verified.
5. **Unit fixtures shaped after a sample of provider
   output**, not the easiest-to-construct shape.
6. **For starter changes consuming workspace Assets:**
   validate workspace, type, AND `duration_ms` non-null
   BEFORE Composition rows are created (V18 pattern).

**A-arc primitive contract checklist (SESSION 186):**

For any new step primitive added after A2:

1. **Add a row to `PRIMITIVE_TO_ROLE`** in
   `apps/compositions/asset_roles.py`.
2. **Stamp `role=AssetRole.X.value`** on every
   `PrimitiveResult(...)` constructor call in the
   primitive module (mock + real branches).
3. **Run `test_primitive_role_coverage.py`** — three
   layers of static + runtime assertions will fail
   loudly if either step was skipped.
4. **Register the primitive** in
   `apps/compositions/primitives/__init__.py::_REGISTRY`.

**Smoke checks** (counts as of SESSION 188 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 980 tests (compositions: 549)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 188:**

* `GET /api/workspace/assets/` — paginated browse.
  Filters: `role` / `asset_type` / `primitive_kind` /
  `storage` / `q` / `created_after` / `created_before`
  (all optional, comma-list where applicable). Pagination
  via `?page=` / `?page_size=` (default 25, max 100).
* `GET /api/workspace/assets/<uuid:id>/` — per-asset
  detail with producing step + downstream consumers.
* Live `storage_health` field attached to every row by
  the serializer (A3's `compute_storage_health` invoked
  inline).
* `WorkspaceAssetViewSet` + `WorkspaceAssetPagination` +
  inline `_serialize_list_asset` / `_serialize_detail_asset`
  in `apps/compositions/views.py`.

**New surfaces from SESSION 187:**

* `apps/compositions/assets.py` — `StorageHealth` constants
  (7 values) + `parse_jwt_exp(url)` + `compute_storage_health(asset)`.
  Pure stateless functions; live per request. The A4 endpoint
  consumes this directly.
* `settings.MEDIA_ENGINE_DATA_ROOT` — optional override for the
  filesystem-existence-check root. Default `<repo>/media-engine/`.

**New surfaces from SESSION 186:**

* `apps/compositions/asset_roles.py` — canonical
  `PRIMITIVE_TO_ROLE` mapping table + `derive_role` +
  `KNOWN_EXPERIMENT_UUID_PREFIXES`. Importable from
  primitives + backfill + future A4 endpoint.
* `PrimitiveResult.role` — required (in practice) field
  on every emit. Empty value raises `PrimitiveError` at
  persist time.
* `Asset.role` now reliably populated for every new row
  (was: RAW_UPLOAD until backfill; is: real role from
  emit moment forward).
* `apps/compositions/tests/test_primitive_role_coverage.py`
  — three-layer enforcement of contract rule 20. Failing
  this test means rule 20 is broken; the fix is one of:
  add a `PRIMITIVE_TO_ROLE` entry, add a `role=` kwarg
  to a PrimitiveResult constructor, drop an orphan
  mapping, or update the `EMITTED_ELSEWHERE` allowlist.

**New surfaces from SESSION 185 (unchanged):**

* `AssetRole` TextChoices enum (10 values) in
  `apps.compositions.models`.
* `Asset.role` CharField — default `RAW_UPLOAD`, indexed
  via `(workspace, role)`.
* `python manage.py backfill_asset_roles` management
  command.
* `docs/CONTEXT_KIT_INVENTORY.md` — context-kit-managed
  inventory companion to `CHARACTER_OS_INVENTORY.md`.

---

## AI / assistant context

- **Last session: SESSION 188 — A4 workspace assets API.**
  One feature commit + handoff. Clean session, no deferrals.
  Backend layer of Asset Library v1 complete
  (A0+A1+A2+A3+A4). Tests 956 → 980. No new TRUST_CALIBRATION
  entries (A4 used established F-arc patterns + A3 helper).

- **Prior session: SESSION 187 — A3 storage-health helper.**
  One feature commit + handoff. Tests 936 → 956. No new
  TRUST_CALIBRATION entries.

- **Calibration carried forward (16 total — unchanged SESSION 188)**:
  - One-runner-emit, many-callers is the cleanest shape for
    cross-cutting Asset metadata.
  - (from SESSION 185 — 2 entries)
  - Walk a proposal's mechanism through its motivating
    calibration event before locking.
  - Doctor heuristics over-match on project-shape naming
    conventions.
  - (from SESSION 184 — 6 entries)
  - Live-doc-check discipline 2-for-2 on V17.
  - V18 + duration mismatch needs starter-time guard.
  - Asset taxonomy gap is structural.
  - Smoke commands without `--save-assets` produce orphans.
  - Celery worker stop-state is silent.
  - Re-using smoke outputs as backdrops is a testing-shape mismatch.
  - (from SESSION 182-183 — 7 entries unchanged)

- **Calibration carried forward (from earlier sessions)**:
  - Operator "are we using X?" framing surfaces capability gaps.
  - Asset upload UI is a recurring gap.
  - External API validation tightens over time —
    re-dogfood periodically.
  - "200 OK + plausible byte count" doesn't mean correct output.
  - Uvicorn `--reload` has stale-during-restart window.
  - drawtext `text=` footgun once `fontfile=` joins.
  - Celery worker doesn't auto-reload.
  - ffmpeg can't infer muxer from double-extension tempfile names.
  - Real-mode dogfood finds bugs in every recipe.
  - PostCSS `@import` order.
  - Operator catches premature extraction.
  - DevTools computed-style snippet for visual bugs.
  - Lossy paraphrase of scope locks.
  - Runway DELETE poisons conversation.
  - Mock-only test coverage hides upstream drift.
  - Operator framing unlocks AI blockers.
  - gpt-5 reasoning eats output budget silently.
  - Tool descriptions need narration scaffolding.
  - SPA gates need both `pnpm test` AND `pnpm build`.
  - Doctor is the drift tool + handoff write at session-end.
  - OpenAI gpt-5 family uses Responses API.

- **V-arc growth template (SESSION 179-184)**: V16 + V17
  + V18 follow the same shape. Narrow scope, opt-in
  defaults, one primitive + one knob + one endpoint per
  slice, real-mode validated before handoff.

- **A-arc growth template (SESSION 185-188)**: Asset
  Library v1 ships in 9 narrow slices. A0 (enum) + A1
  (backfill) + A2 (primitives stamp role) + A3 (storage
  health) + A4 (read endpoints) form the **backend
  layer — now complete**. A5/A6/A7/A8 open the SPA
  surface; A7 is the operator-visible payoff
  (role-filtered asset_picker).

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Deferrable since V17 is also
  deferred — pick up if a clean dogfood session opens up.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
