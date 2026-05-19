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
> **A0+A1+A2+A3+A4+A5+A7 SHIPPED — operator-visible payoff
> (role-filtered picker) closed. A6 + A8 remain.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_190_A7_PICKER_ROLE_FILTER.md`.

---

## SESSION 190 outcome — A7 asset_picker role-filter

Clean single-slice session. One feature commit + handoff
close. **A7 ships — the structural fix that motivated the
whole arc.** V18's `backdrop_clip_id` dropdown (plus three
sibling V8 pickers) now narrows to their semantically-
correct role; smoke / talking-head / composite clips no
longer pollute the backdrop picker. SESSION 184 V18 dogfood
"two random people" finding is now structurally prevented.

Backend tests **980 → 990 (+10)**; SPA vitest **120 → 125
(+5)**. Backend + SPA + recipe registry all touched in a
½-session-sized slice. No real-mode spend.

### A7 — role-filtered asset_picker

* **`RecipeField.role_filter: str | None = None`** on the
  dataclass; `to_json()` emits the key only when set
  (omits for fuzzy pickers — backwards-compat with
  existing SPA Zod `optional()`).
* **Four picker fields tagged**:
  * V18 `talking_head_with_backdrop.backdrop_clip_id` →
    `BACKDROP` (prime motivating case).
  * V8 `backdrop_layout.background_clip_id` → `BACKDROP`.
  * V8 `broll_splice.broll_clip_id` → `B_ROLL`.
  * V8 `music_bed_pass.music_asset_id` → `AUDIO_TRACK`.
* **Fuzzy pickers stay unfiltered** (`pip_clip_id`,
  `cohost_clip_id`, `foreground_clip_id`, layout
  `base_clip_id`s). Genuine v2 design question, not
  oversight.
* **`AssetViewSet.list()`** accepts `?role=` comma-list
  matching A4's shape. Unknown values match zero rows
  (correct behavior — typo'd recipe registry produces
  empty picker, not crash).
* **SPA**: `recipes.ts` Zod `recipeFieldSchema` adds
  `role_filter: z.string().optional()`;
  `ListAssetsOptions.role?: string` flows through;
  `AssetPicker` component reads `field.role_filter` and
  forwards to `useAssets`.
* **Bug caught during build**: TS strict-mode flagged
  `apiJsonMock.mock.calls[0][0]` and `recipe.fields[0].role_filter`
  as "Object is possibly undefined". Fixed with helper +
  non-null assertion after `expect(field).toBeDefined()`
  guards. **Recurring across A4+A5+A7 sessions** — TS
  strict bites at `pnpm build`, not at `pnpm test`. The
  existing "SPA gates need both pnpm test AND pnpm build"
  calibration covers this; no new entry needed.

### Tests at SESSION 190 close

| Suite | Count | Delta |
|---|---|---|
| Django | **990** | +10 (980 → 990) |
| - compositions | **559** | +10 (549 → 559) |
| Media-engine | 194 | unchanged |
| **SPA vitest** | **125** | **+5 (120 → 125)** |

Real-mode spend SESSION 190: **$0** (registry + endpoint
change + tests; no API calls).


---

## FIRST THING (SESSION 191): A6 (detail view) or A8 (lineage cross-link)

A7 closed the operator-visible payoff. **Two slices remain
in the arc; operator picks at slice-open.**

### Option A — A6 SPA per-asset detail view (1 session)

Mirror `web/src/routes/workspace/knowledge.$id.tsx`. The
A4 retrieve endpoint already returns the full lineage shape
(producing step + downstream consumers).

* **Route**: `web/src/routes/workspace/assets.$id.tsx`.
* **API client extension**: add `getWorkspaceAsset(id)` +
  `useWorkspaceAsset(id)` to
  `web/src/lib/api/workspace-assets.ts`. Zod schema for
  detail shape (list schema + `producing_step` +
  `downstream_compositions`).
* **Detail panel**: thumbnail preview (image or video
  player for IMAGE/CLIP; audio player for AUDIO/VOICE; text
  for TRANSCRIPT), full metadata table (every field from
  the list shape), copy-URL action, download-file action.
* **Lineage section**: producing composition link +
  producing step expand (primitive name, params, inputs),
  downstream consumer compositions list.
* **Back-to-list affordance**: preserves the list's filter
  state via URL search params.
* Use the `react-web-delivery` agent.

### Option B — A8 F-arc composition-lineage cross-link (½ session)

Composition overview pages get a "Produced assets" section
showing each output Asset with its role badge + a link to
the A6 detail view. Backend already has the data
(`composition.produced_assets` reverse relation); the slice
is mostly SPA + a small backend serializer addition.

* **Backend**: extend
  `apps/compositions/serializers.py::CompositionSerializer`
  to include a `produced_assets` field with id + role +
  asset_type + title (light shape — full detail lives in
  A4's retrieve).
* **SPA**: extend `web/src/routes/compositions/$id.tsx` (or
  wherever the composition overview lives) to render the
  new section. Role badges follow the A5 storage-health
  badge tone pattern.
* **Tests**: backend serializer test + SPA render test.

### Recommendation

**Default to A6** for arc continuity — it's the natural
next step from A5's list view, and the detail page is where
operators will spend the most time browsing. A8 is a
cross-link polish slice; it lands cleaner after A6 is in.

After A6 + A8, the arc closes. **Arc-close ceremony**:
- Regen INVENTORY one more time.
- TRUST_CALIBRATION entry summarizing the A-arc growth
  template (similar to V-arc and R-arc closures).
- Mark Asset Library v1 complete in
  `docs/CHARACTER_OS_WHAT_IT_IS.md` + start-here.

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
**Asset Library v1 arc IN FLIGHT (SESSION 185-190):**
A0 + A1 + A2 + A3 + A4 + A5 + A7 SHIPPED. Backend +
browse SPA + role-filtered picker (the structural fix that
motivated the arc) complete. **A6 (detail view) or A8
(lineage cross-link) opens next — operator picks; A6
recommended for arc continuity.**

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
| **Asset Library v1 — A5 SPA list view** | **DONE (SESSION 189)** |
| **Asset Library v1 — A7 picker role-filter** | **DONE (SESSION 190)** |
| Asset Library v1 — A6 SPA detail view | **NEXT (SESSION 191, option A)** |
| Asset Library v1 — A8 lineage cross-link | **NEXT (SESSION 191, option B)** |
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

**SESSION 191 stack-up notes:**

* **A6 (Option A)** — SPA-only work. `pnpm dev` at :5174;
  Django shell at :8000 for the live retrieve endpoint
  `/api/workspace/assets/<id>/`. No backend changes
  expected. Use the `react-web-delivery` agent — mirror
  `web/src/routes/workspace/knowledge.$id.tsx` shape.
* **A8 (Option B)** — Backend serializer + SPA.
  CompositionSerializer gains a `produced_assets` field;
  composition overview page renders the new section.
* **Real-mode dogfood newly possible from A7.** Open
  `http://localhost:5174` and start a V18
  `talking_head_with_backdrop` composition — the
  `backdrop_clip_id` dropdown should now only show
  BACKDROP-tagged clips (42 in dev DB per SESSION 185
  backfill). Worth a quick visual spot-check before
  opening A6/A8 to confirm the wiring is correct
  end-to-end.
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

**Smoke checks** (counts as of SESSION 190 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 990 tests (compositions: 559)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 125 vitest tests
```

**New surfaces from SESSION 190:**

* `RecipeField.role_filter: str | None` — first-class
  field on the recipe metadata dataclass; `to_json()`
  emits the key only when set (omits for fuzzy pickers).
* `GET /api/assets/?role=<csv>` — V15.2 picker endpoint
  gained a comma-list `role` query param matching A4's
  shape. Unknown values match zero rows (correct typo
  behavior).
* SPA `recipeFieldSchema.role_filter` (Zod optional)
  + `ListAssetsOptions.role` + `AssetPicker` component
  forwards `field.role_filter` to `useAssets`.
* Four picker fields tagged: V18 `backdrop_clip_id` →
  `backdrop`; V8 `backdrop_layout.background_clip_id` →
  `backdrop`; V8 `broll_splice.broll_clip_id` → `b_roll`;
  V8 `music_bed_pass.music_asset_id` → `audio_track`.

**New surfaces from SESSION 189:**

* `/workspace/assets` SPA route — paginated browse with
  filter chips for role / asset_type / storage + "More
  filters" disclosure (q + date range + primitive_kind).
  URL search params drive filter state.
* `web/src/lib/api/workspace-assets.ts` — Zod schemas,
  `useWorkspaceAssets(params)` hook, `buildAssetsQueryString`,
  display helpers (`assetRoleLabel`, `assetTypeLabel`,
  `storageHealthLabel`, `storageHealthTone`, `relativeTime`).
* `web/src/routes/workspace/assets.tsx` — page component.
* Backend `AssetType` / `AssetRole` / `StorageHealth` values
  confirmed lowercase in SPA (`clip`, `talking_head`,
  `https_live` — not `CLIP`, `TALKING_HEAD`, `HTTPS_LIVE`).

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

- **Last session: SESSION 190 — A7 asset_picker role-filter.**
  The structural fix that motivated the whole arc. One
  feature commit + handoff. Clean session, no deferrals.
  Backend tests 980 → 990 (+10); SPA vitest 120 → 125 (+5).
  No new TRUST_CALIBRATION entries — A7 used established
  patterns; the recurring "TS strict bites at build, not at
  test" finding is already covered by the existing "SPA
  gates need both pnpm test AND pnpm build" entry.

- **Prior session: SESSION 189 — A5 SPA list view.**
  Delegated to `react-web-delivery` subagent. SPA vitest
  95 → 120. One new TRUST_CALIBRATION entry
  (subagent-source-of-truth).

- **Calibration carried forward (17 total — unchanged SESSION 190)**:
  - Subagent went to source-of-truth and caught an upstream
    brief error. Lesson: write subagent briefs as pointers
    to source-of-truth, not restatements of it. (NEW
    SESSION 189.)
  - (from SESSION 186 — 1 entry)
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

- **A-arc growth template (SESSION 185-190)**: Asset
  Library v1 ships in 9 narrow slices. **7 of 9 shipped**:
  A0 (enum) + A1 (backfill) + A2 (primitives stamp role) +
  A3 (storage health) + A4 (read endpoints) + A5 (SPA
  list) + A7 (role-filtered picker — the structural fix
  that motivated the arc). A6 (detail view) + A8 (lineage
  cross-link) remain — arc closes in 1-2 sessions.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Deferrable since V17 is also
  deferred — pick up if a clean dogfood session opens up.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
