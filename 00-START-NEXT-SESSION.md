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
> **A0 + A1 + A2 SHIPPED. A3 next.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_186_A2_PRIMITIVES_STAMP_ROLE.md`.

---

## SESSION 186 outcome — A2 primitives stamp role

Clean session. Single slice, no deferrals, no surprises.
One feature commit + handoff close. **A2 ships:** every
primitive in `apps.compositions.primitives` stamps `role`
on its output Asset at emit time; the runner asserts the
contract; new coverage test file enforces rule 20 across
three layers (AST primitive_kind scan + AST emit-site scan
+ runtime backstop including the realtime direct-emit
path). Test totals **928 → 936 (+8)** — all 8 new tests
in `test_primitive_role_coverage.py`. Compositions suite
**497 → 505**. No real-mode spend.

### A2 — primitives stamp role at emit

* **New module `apps/compositions/asset_roles.py`** — single
  source of truth for `PRIMITIVE_TO_ROLE` (20 entries) +
  `KNOWN_EXPERIMENT_UUID_PREFIXES` + `derive_role(asset)`.
  Backfill command re-exports for backwards-compat with
  existing test imports.
* **`PrimitiveResult.role: str = ""`** field on the
  dataclass. Defaults to empty so the runner can catch
  any missing-stamp at runtime.
* **14 primitive modules + 3 mocks + 1 realtime emit
  site stamp role explicitly.** Mocks → `EXPERIMENT`;
  realtime `capture_transcript` → `TRANSCRIPT`.
* **Runner backstop:** `_persist_output_asset` raises
  `PrimitiveError("Contract rule 20")` if
  `result.role` is empty; otherwise passes through to
  `Asset.objects.create(role=result.role)`.
* **`test_primitive_role_coverage.py`** — 8 tests, 3
  layers (AST primitive_kind, AST emit-site, runtime
  backstop). Future primitives that forget to stamp role
  fail statically.
* **2 isolation-test ALLOWED_FILES entries** —
  compositions + realtime test_isolation.py both gained
  the coverage test as a sanctioned writer.

### Calibration (1 new entry — 16 total)

**One-runner-emit, many-callers** — when a new
cross-cutting Asset field lands, find the funnel point
first (single `Asset.objects.create` site), add the field
there, then push to the producers (PrimitiveResult). The
producers stamp explicitly (readable in isolation); the
funnel enforces (defense-in-depth). A2 covered 28+ emit
paths with two architectural-layer edits + per-primitive
literal additions.

### Tests at SESSION 186 close

| Suite | Count | Delta |
|---|---|---|
| Django | **936** | +8 (928 → 936) |
| - compositions | **505** | +8 (497 → 505) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

Real-mode spend SESSION 186: **$0** (pure backend / DB
work; no Runway / Stability / OpenAI API calls).

---

## FIRST THING (SESSION 187): slice A3

A2 closed the foundational layer (every new Asset row
carries a real role by construction; rule 20 enforced by
test). **A3 is the next slice in the Asset Library arc.**

**A3 deliverable: storage-health helper + cached property
on `Asset`.** Per scope lock §A3:

1. **JWT exp parser** for Runway-hosted Cloudfront URLs.
   Runway signs CDN URLs with a JWT in the path; the
   `exp` claim tells you when the URL stops working.
   Parse it; expose as `Asset.cdn_expires_at` (cached
   property or computed field, operator decision at
   slice-open).
2. **Filesystem existence check** for local-path
   Assets (`/media-engine/data/...`). Optional —
   operator may decide to defer if cost is too high in
   per-request mode; the SESSION 185 Q-a-3 resolution
   says "live per request for v1; cache only if A5 perf
   demands".
3. **Three-state result**: `ok` / `expired` / `missing` /
   `unknown` (for the unknown-host case where neither
   JWT-bearing nor local-path apply).
4. **Used by A4** (read endpoint) + **A5** (SPA list
   view chip) + **A6** (per-asset detail).

A3 estimated effort: ½ session. Smallest of the A-arc
foundational slices.

After A3, **A4 + A5 + A6** open the operator-visible
surface; **A7** delivers the role-filtered asset_picker
payoff that triggered the arc.

### Alternative paths for SESSION 187

If A3 feels too small to fill a session:

* **Path B — A3 + A4 together.** A4 is also ½ session;
  combined they fit one full session. A4 is the read
  endpoint that surfaces both `role` (A0-A2) and storage
  health (A3) to the SPA.
* **Path C — small-win sidebars.** V18 polish (duration-
  mismatch starter warning, ½ session); F8.1 K10 seed
  corpus; `storyboard_voiced` + `dialogue_scene` real-
  mode validation. Asset Library parks while a smaller
  win lands.

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
**Asset Library v1 arc IN FLIGHT (SESSION 185-186):**
A0 + A1 + A2 SHIPPED. Every new Asset carries a role by
construction; rule 20 enforced by test. **A3 opens next.**

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
| Asset Library v1 — A3 storage-health helper | **NEXT (SESSION 187)** |
| Asset Library v1 — A4 / A5 / A6 / A7 / A8 | Queued |
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

**SESSION 187 stack-up notes:**

* **Celery worker** must be restarted if any composition
  fires next session — SESSION 186 changed the
  `_persist_output_asset` shape (passes `role=...` now).
  The worker holds stale module imports until bounced.
  "Worker stop-state is silent" calibration (SESSION 184
  #5) still applies.
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

**Smoke checks** (counts as of SESSION 186 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 936 tests (compositions: 505)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

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

- **Last session: SESSION 186 — A2 primitives stamp role.**
  One feature commit + handoff. Clean session, no deferrals.
  Contract rule 20 now enforced statically (AST scans) AND
  at runtime (runner backstop + coverage tests). Tests
  928 → 936. One new TRUST_CALIBRATION entry
  (one-runner-emit-many-callers).

- **Prior session: SESSION 185 — drift sweep + Asset Library
  scope-lock + A0 + A1.** Five commits + handoff. Doctor
  3 warnings → 0 at boot. Asset Library v1 locked with 10
  roles. A0 (model + migration) + A1 (backfill + dev-DB
  --commit applied to 128 of 136 candidates) shipped.
  Two new TRUST_CALIBRATION entries.

- **Calibration carried forward (NEW SESSION 186 — 16 total)**:
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

- **A-arc growth template (SESSION 185-186)**: Asset
  Library v1 ships in 9 narrow slices. A0 (enum) + A1
  (backfill) + A2 (primitives stamp role) form the
  foundational layer. A3 (storage health) + A4 (read
  endpoint) close out the backend. A5/A6/A7/A8 open
  the SPA surface.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Deferrable since V17 is also
  deferred — pick up if a clean dogfood session opens up.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
