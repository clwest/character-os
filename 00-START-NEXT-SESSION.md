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
> **A0 + A1 + A2 + A3 SHIPPED — backend foundational layer
> complete. A4 next.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_187_A3_STORAGE_HEALTH.md`.

---

## SESSION 187 outcome — A3 storage-health helper

Clean single-slice session. One feature commit + handoff
close. **A3 ships:** new `apps/compositions/assets.py` module
exports `StorageHealth` (7 string constants) + `parse_jwt_exp(url)`
+ `compute_storage_health(asset)`. Live per request per
SESSION 185 Q-a-3 (no model field, no caching). **Asset
Library v1 backend foundational layer is now complete** —
A0+A1+A2+A3 give A4 everything it needs.

Test totals **936 → 956 (+20)** — all 20 new tests in
`test_storage_health.py`. Compositions suite **505 → 525**.
No real-mode spend.

### A3 — storage-health helper

* **New module `apps/compositions/assets.py`** —
  * `StorageHealth` class with 7 string constants
    (`HTTPS_LIVE` / `HTTPS_EXPIRING_SOON` / `HTTPS_EXPIRED` /
    `LOCAL_PRESENT` / `LOCAL_MISSING` / `DATA_URI` /
    `UPLOAD_PENDING`).
  * `parse_jwt_exp(url) -> int | None` — public JWT exp
    parser. Handles Runway's `?_jwt=<header>.<payload>.<sig>`
    shape with base64url-padded decoding; returns `None` on
    every malformed-input case (no crash).
  * `compute_storage_health(asset) -> str` — classifier with
    five branches (empty → UPLOAD_PENDING; `data:` →
    DATA_URI; HTTPS → JWT-aware classifier with 24h
    EXPIRING_SOON window; leading-slash → filesystem check
    against `settings.MEDIA_ENGINE_DATA_ROOT`; unknown →
    UPLOAD_PENDING).
* **`test_storage_health.py`** — 20 tests covering all 7
  states + JWT parser edge cases + filesystem
  override-via-settings.
* **`test_isolation.py` ALLOWED_FILES** gained the test
  file (sanctioned reader; constructs Asset rows for
  classifier exercise only).
* **`settings.MEDIA_ENGINE_DATA_ROOT`** override knob now
  recognized — tests use it via `override_settings(...)`
  with a tmpdir; production / staging can use it to point
  at non-default mount points.

### Tests at SESSION 187 close

| Suite | Count | Delta |
|---|---|---|
| Django | **956** | +20 (936 → 956) |
| - compositions | **525** | +20 (505 → 525) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

Real-mode spend SESSION 187: **$0** (helper + tests only).

---

## FIRST THING (SESSION 188): slice A4

A3 closed the storage-health helper. **A4 is the next slice
in the Asset Library arc — the read endpoint that surfaces
A0-A3's work to the SPA.**

**A4 deliverable: read-only `/api/workspace/assets/` +
`/api/workspace/assets/<id>/` endpoints.** Per scope lock
§"New / extended endpoints":

1. **List endpoint** (`GET /api/workspace/assets/`) —
   paginated. Query params:
   * `role=BACKDROP,TALKING_HEAD,...` (comma-list)
   * `asset_type=CLIP,IMAGE,...` (existing categorization)
   * `primitive_kind=...` (production-method filter)
   * `storage=HTTPS_LIVE,LOCAL_PRESENT,...` (computed)
   * `q=...` (full-text against prompt / composition name)
   * `created_after`, `created_before` (ISO date)
   * Standard `page` / `page_size` pagination
   Returns each asset with computed `storage_health` field,
   producing step's prompt (when available), producing
   composition's name + id.
2. **Retrieve endpoint**
   (`GET /api/workspace/assets/<id>/`) — per-asset detail
   with full lineage (producing composition + step + inputs
   to that step + downstream compositions that consumed
   this asset).
3. **Workspace-scoped reads** — same pattern as F-arc's
   `/api/workspace/overview/`. Authenticated; workspace
   membership required.
4. **Avatar / Voice / Portrait excluded** per Q-a-6
   (deferred to v2); A5 will carry an honest gap note.
5. **`storage_health` computed at serialize time** —
   `apps.compositions.assets.compute_storage_health(asset)`
   from A3 attached by the serializer's
   `SerializerMethodField`.

A4 estimated effort: ½ session.

After A4, **A5 + A6** are the operator-visible SPA work;
**A7** is the role-filtered asset_picker payoff that
triggered the arc.

### Alternative paths for SESSION 188

If A4 feels too small to fill a session:

* **Path B — A4 + A5 start.** A5 is 1 full session; the
  first half lays Zod schemas + query hooks + page
  scaffold against A4's freshly-shipped endpoint.
* **Path C — small-win sidebars.** V18 polish (duration-
  mismatch starter warning, ½ session); F8.1 K10 seed
  corpus; `storyboard_voiced` + `dialogue_scene` real-
  mode validation.

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
**Asset Library v1 arc IN FLIGHT (SESSION 185-187):**
A0 + A1 + A2 + A3 SHIPPED — backend foundational layer
complete. Every new Asset carries a role by construction;
rule 20 enforced by test; storage-health classifier ready
for A4 serializer to attach. **A4 opens next.**

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
| Asset Library v1 — A4 read endpoints | **NEXT (SESSION 188)** |
| Asset Library v1 — A5 / A6 / A7 / A8 | Queued |
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

**SESSION 188 stack-up notes:**

* **No Celery worker concern this session unless a
  composition is fired.** A4 adds a read endpoint only;
  it doesn't touch primitive emit shape or any
  consumed-by-worker module.
* **`settings.MEDIA_ENGINE_DATA_ROOT`** is the recognized
  override for the storage-health filesystem check
  (SESSION 187). Default `<repo>/media-engine/`. Production
  / staging deploys with non-default mounts can override
  via env.
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

**Smoke checks** (counts as of SESSION 187 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 956 tests (compositions: 525)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 187:**

* `apps/compositions/assets.py` — `StorageHealth` constants
  (7 values) + `parse_jwt_exp(url)` + `compute_storage_health(asset)`.
  Pure stateless functions; live per request. The A4 serializer
  attaches `storage_health` to each row via `SerializerMethodField`.
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

- **Last session: SESSION 187 — A3 storage-health helper.**
  One feature commit + handoff. Clean session, no deferrals.
  Asset Library v1 backend foundational layer complete
  (A0+A1+A2+A3). Tests 936 → 956. No new TRUST_CALIBRATION
  entries (A3 was a small, well-scoped helper using
  existing architectural patterns).

- **Prior session: SESSION 186 — A2 primitives stamp role.**
  One feature commit + handoff. Contract rule 20 now enforced
  statically (AST scans) AND at runtime (runner backstop +
  coverage tests). Tests 928 → 936. One new TRUST_CALIBRATION
  entry (one-runner-emit-many-callers).

- **Calibration carried forward (16 total — unchanged SESSION 187)**:
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

- **A-arc growth template (SESSION 185-187)**: Asset
  Library v1 ships in 9 narrow slices. A0 (enum) + A1
  (backfill) + A2 (primitives stamp role) + A3 (storage
  health) form the **backend foundational layer — now
  complete**. A4 (read endpoint) is the bridge slice.
  A5/A6/A7/A8 open the SPA surface.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Deferrable since V17 is also
  deferred — pick up if a clean dogfood session opens up.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
