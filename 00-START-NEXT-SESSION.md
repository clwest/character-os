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
> (locked SESSION 185). **COMPLETE (SESSION 192) + REAL-MODE
> DOGFOOD VALIDATED (SESSION 193)** — all 9 slices A0-A8
> shipped across SESSIONS 185-192; end-to-end dogfood pass
> SESSION 193.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`
> (revised SESSION 192 — Asset Library v1 marked complete).
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_195_V_ARC_CLOSURE_2_BUGS_FOUND.md`.

---

## SESSION 195 outcome — V-arc closure attempt found 2 production bugs

Tried to close the V-arc to 100% by validating the last 2
unvalidated recipes real-mode. **One recipe completed
end-to-end (`dialogue_scene`); the other partial
(`storyboard_voiced`). Two distinct production bugs surfaced
in 2 recipes attempted — SESSION 158 calibration confirmed
2-for-2.**

### Bug 1 — `mix_audio` silent-base ffmpeg filtergraph bug

`storyboard_voiced` step 9 fails with 500 from
`/internal/audio/mix/`. ffmpeg filtergraph references `[0:a]`
(base audio) but the base is the silent visual concat —
`generate_visual_clip` outputs are video-only. V14 design
assumed base had audio (music_bed_pass shape); V15.4 added
audio_extract+mix_audio chain assuming same semantics.
Storyboard wants audio REPLACEMENT (`-map 1:a` from
overlay), not audio MIXING.

8/10 storyboard_voiced steps succeeded; upstream outputs
browseable in the Asset Library. $1.92 wasted on the partial.

### Bug 2 — `concat_clips` role semantics mismatch

`dialogue_scene` completes end-to-end ($1.25, 145s, 6
produced assets) **but the final concat output is stamped
`role=BACKDROP`** by A2's emit-time logic. Should be
`COMPOSITE_OUTPUT` (or similar). A2's static `primitive_kind
→ role` mapping breaks down because `concat_clips` serves
multiple recipes with different deliverable semantics. The
A7 role-filtered picker would now offer dialogue scene
finals as "backdrops" — nonsensical.

### Calibration

Three new TRUST_CALIBRATION entries — mix_audio silent-base,
concat_clips role mismatch, and **promoting SESSION 158's
"real-mode finds bugs in every recipe" from "high-yield" to
"expected behavior."** The A-arc growth template now needs a
9th step: arc-close ceremony must include a real-mode
validation pass for every recipe affected by the arc.

### Tests at SESSION 195 close

No code changes; suites unchanged.

| Suite | Count |
|---|---|
| Django | 1006 |
| - compositions | 575 |
| Media-engine | 194 |
| SPA vitest | 134 |

Real-mode spend SESSION 195: **~$3.17** ($1.92 storyboard
partial + $1.25 dialogue complete).

Workspace asset count: **138 → 153 (+15)** from the two
real-mode fires.

V-arc status: **17 of 18 recipes validated**. `dialogue_scene`
closed; `storyboard_voiced` pending mix_audio fix.

---

## SESSION 194 outcome — V18 polish double

Quick-wins session — two SESSION 184 dogfood calibrations
queued for 10 sessions shipped in one pass.

**Slice 1 — V18 duration-mismatch starter warning** (#2
from SESSION 184). `talking_head_with_backdrop` refuses at
creation time when the picked `backdrop_clip` is shorter
than the estimated speech duration. Uses the existing
`_estimate_avatar_speech_seconds` (2s buffered estimator),
so the check effectively requires `backdrop ≥ speech + 2s`.
Operator-actionable error names both durations, script
length, and the two remediation options (longer backdrop OR
target character count for a shorter script).

**Slice 2 — smoke_keyframes `--save-assets` default opt-in**
(#4 from SESSION 184). Smoke outputs now persist as
`Asset(role=EXPERIMENT)` rows by default so they land in
the Asset Library v1 UI. Operators who want throwaway smokes
pass `--no-save-assets`. New `--workspace NAME` flag
required when saving is on; fails fast with `CommandError`
before any Runway credit gets spent if the operator forgot.
New `persist_smoke_asset` helper extracted for testability
(the command itself makes real Runway calls + refuses
`RUNWAY_FORCE_MOCK`).

Backend tests **995 → 1006 (+11)**: 5 V18 polish + 6 smoke
helper. SPA **134** unchanged. No real-mode spend.

### Tests at SESSION 194 close

| Suite | Count | Delta |
|---|---|---|
| Django | **1006** | +11 (995 → 1006) |
| - compositions | **575** | +11 (564 → 575) |
| Media-engine | 194 | unchanged |
| SPA vitest | 134 | unchanged |

Real-mode spend SESSION 194: **$0**.

---

## SESSION 193 outcome — A-arc dogfood passed + Celery hard rule

No code changes. Real-mode dogfood pass against the dev DB
validated Asset Library v1 end-to-end. Operator browsed
(A5), exercised the role-filtered picker (A7 narrowed 119
CLIPs → 42 BACKDROP), and fired a
`talking_head_with_backdrop` composition that completed
with the A8 produced_assets panel rendering exactly as
designed (2 rows, role badges, Final pill on the composite
output).

**One real catch — promoted to hard stack-up rule:** the
SESSION 192 start-here claimed mock-mode doesn't need
Celery. Wrong. The composition hung silent at DRAFT for
104s with 65 backed-up envelopes in Redis until I started
a worker. SESSION 184 calibration #5 hit for the second
time. Starting SESSION 194: **Celery worker is required
for ANY composition fire, mock_mode or real-mode.**

Two new TRUST_CALIBRATION entries:
1. Celery worker is NOT optional for mock_mode — promote
   to hard stack-up rule.
2. Arc-close dogfood is high-yield even after every slice
   was test-validated. Generalizes: test passing ≠ dev
   stack usable.

Live state: Django + SPA + Celery worker still running.
Workspace asset count grew 136 → 138 from the dogfood
composition. No real-mode spend.

### Tests at SESSION 193 close

No code changes; suites unchanged from SESSION 192:

| Suite | Count |
|---|---|
| Django | 995 |
| - compositions | 564 |
| Media-engine | 194 |
| SPA vitest | 134 |

Real-mode spend SESSION 193: **$0**.

---

## SESSION 192 outcome — A8 + Asset Library v1 ARC CLOSED

**Asset Library v1 arc COMPLETE.** A8 ships as the final
slice: composition overview pages now list every Asset
emitted by the pipeline with role + storage-health badges +
a `Final` pill on the deliverable, each row linking to the
A6 detail view. Cross-link between Composition surface and
Asset surface structurally complete.

**Arc spanned 7 sessions** (185-192) for 9 slices. Zero
deferrals. **Django 915 → 995 (+80); SPA vitest 95 → 134
(+39)** across the arc. New TRUST_CALIBRATION entry
documenting the A-arc growth template.

### A8 — composition produced_assets cross-link

* **Backend** —
  `CompositionSerializer.produced_assets`
  `SerializerMethodField`. Light shape (id + asset_type +
  role + title + file_path + storage_health + is_final),
  ordered by `Asset.created_at` so the SPA panel reads
  top-to-bottom as the pipeline executed. Uses A3's
  `compute_storage_health` inline. Empty for draft
  compositions.
* **SPA** — `producedAssetSchema` Zod +
  `produced_assets` on `compositionSchema`
  (`default([])` for older composition rows).
  `ProducedAssetsPanel` component renders between
  `<FinalAsset>` and the F5 lineage panels in
  `routes/compositions/$id.tsx`. Each row is a
  `Link to=/workspace/assets/<id>`. Local
  `producedStorageTone(storage)` mirrors A5's tone
  palette without cross-route import coupling.
* **Tests** — 3 backend (produced_assets surfaces;
  is_final marks only the final; empty for draft) + 3 SPA
  vitest (all-fields parse; default empty array; mixed
  is_final).

### Asset Library v1 arc retrospective

| Session | Slice | Effort |
|---|---|---|
| 185 | scope-lock + A0 + A1 | 1 session |
| 186 | A2 (primitives stamp role) | 1 session |
| 187 | A3 (storage-health helper) | ½ session |
| 188 | A4 (read endpoints) | ½ session |
| 189 | A5 (SPA list — subagent) | 1 session |
| 190 | A7 (picker role-filter — the structural fix) | ½ session |
| 191 | A6 (SPA detail — subagent) | 1 session |
| 192 | A8 (composition cross-link) + arc close | ½ session |

### Tests at SESSION 192 close

| Suite | Count | Delta |
|---|---|---|
| Django | **995** | +3 (992 → 995) |
| - compositions | **564** | +3 (561 → 564) |
| Media-engine | 194 | unchanged |
| **SPA vitest** | **134** | **+3 (131 → 134)** |

Real-mode spend SESSION 192: **$0**.


---

## FIRST THING (SESSION 196): two fix slices to close V-arc 100%

Both bugs found SESSION 195. Both ½-session-sized. Both
operator-picked at SESSION 195 close.

### Slice 1 — mix_audio silent-base handling (media-engine, ½ session)

Detect missing base audio stream in `/internal/audio/mix/`
+ fall through to `-map 1:a` filtergraph. Backwards-compat
with existing music_bed_pass behavior (base has audio → amix
as today). New test fixture for silent-base shape.

When this lands, re-fire `storyboard_voiced` real-mode →
V-arc 100% closure (the SESSION 195 goal). Probably ~$0
additional spend if we re-use the existing partial
composition's upstream outputs, or ~$1.92 if we fire from
scratch.

### Slice 2 — combinator-primitive role override (½ session)

Add `result_role` param to `concat_clips` (and likely
`composite_video` + `mix_audio` too). Recipe starter passes
`result_role` per step; primitive reads + stamps. Backwards-
compat default keeps current BACKDROP stamp. Apply
override to `dialogue_scene.concat_clips` → COMPOSITE_OUTPUT
(plus review other combinator step calls per recipe).

### Recommended ordering

**Slice 1 first** — clears the V-arc 100% closure path.
Slice 2 is the cleanup that hardens the A-arc taxonomy
+ doesn't block anything.

If operator wants quick-win double (per the successful
SESSION 194 pattern): both slices in one SESSION 196.
Combined ~1 full session, $0 code-spend + maybe ~$0 if we
re-fire storyboard_voiced from the partial.

### Queued backlog (operator picks)

| Item | Effort | Notes |
|---|---|---|
| ~~V18 polish — duration-mismatch starter warning~~ | **DONE SESSION 194** | SESSION 184 #2 — shipped. |
| **F8.1 — K10 seed corpus** | Operator-blocked | Markdown seed for new workspaces. Operator-authored content; AI can scaffold the loader. |
| **Real-mode validation: `storyboard_voiced` + `dialogue_scene`** | 1 session | 2 of 18 V-arc recipes still unvalidated against real Runway. |
| **V17.3 keyframes (deferred SESSION 184)** | Blocked | Re-open criteria in `VIDEO_COMPOSITION_V17_PROPOSAL.md` §Q-v17-6: Runway adds keyframes to gen-4 family OR operator adopts `veo3.1_fast` as primary model. |
| **B6-B10 brand arc (deferred SESSION 178)** | Multi-session | Brand ecosystem v2; lower priority than feature work. |
| **K7.x v3 YouTube oEmbed** | ½ session | YouTube extractor v2 ships heuristic-based; v3 adds oEmbed for richer metadata. |
| **K6.4 v3 architectural fix** | 1 session | Verifier surface design lock — see K-arc scope doc. |
| **Asset upload UI (AUDIO / IMAGE)** | 1-2 sessions | The 8 needs-review legacy rows from SESSION 185 backfill stay at RAW_UPLOAD until this surface ships. Was queued SESSION 181. |
| ~~Smoke `--save-assets` default opt-in~~ | **DONE SESSION 194** | SESSION 184 #4 — shipped. |
| **W12 legacy form retirement** | 1 session | Old single-form recipe path still rides on the V6 shim. Retire after operator confidence in V15 form renderer. |
| **Thruman stale spokesperson cleanup** | ½ session | Dev DB tidy. |
| **CONTENT_FORMAT_BACKLOG.md picks** | Multi-session | 20 video formats/pipelines the V-arc's 18 recipes don't cover but primitives could ship. Strategic top-3 per the backlog doc: B-1 (realtime transcript → highlight clip miner), B-3 (personalized variable-substitution videos), B-14 (one render → many platform variants). |

### New arc candidates (operator-pick)

If the operator wants a structured arc rather than picking
backlog items, three candidates from CONTENT_FORMAT_BACKLOG
that align with the existing infrastructure:

1. **B-1 / Transcript Highlight Miner** — R-arc transcripts
   are currently captured (R5) but never mined. An arc
   that turns ENDED RealtimeSession transcripts into
   highlight clips would exploit existing R+V infrastructure
   without new external dependencies. Likely 6-8 slices.
2. **B-3 / Personalized Video** — variable-substitution at
   render time. Substantial scope (operator audience model
   + variable resolution + template authoring). 10+ slices.
3. **B-14 / Multi-Platform Variants** — one composition
   render → reformatted variants for IG / TikTok / YT
   Shorts / LinkedIn. Builds on V9's `reformat_clip` + an
   orchestration layer. 5-6 slices.

See `docs/design/CONTENT_FORMAT_BACKLOG.md` for the full
catalog.

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
**Asset Library v1 arc COMPLETE (SESSIONS 185-192) +
DOGFOOD VALIDATED (SESSION 193):**
All 9 slices A0-A8 shipped. End-to-end real-mode pass
against dev DB confirmed browse / picker / composition
cross-link all work; one stack-up bug caught + promoted
to hard rule (Celery is required for ALL composition
fires).

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
| **Asset Library v1 — A6 SPA detail view** | **DONE (SESSION 191)** |
| **Asset Library v1 — A8 lineage cross-link** | **DONE (SESSION 192) — ARC CLOSED** |
| **Asset Library v1 — real-mode dogfood pass** | **DONE (SESSION 193) — END-TO-END VERIFIED** |
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

**SESSION 194 stack-up — HARD REQUIREMENTS** (promoted SESSION 193):

1. **Django dev server** — `python manage.py runserver` from `shell/`.
2. **SPA dev server** — `pnpm dev` from `web/`. :5174.
3. **Redis** — `cd infra && docker compose up -d` (port 6381).
4. **Celery worker** — **REQUIRED for any composition fire,
   including mock-mode.** SESSION 193 caught this trap for the
   second time:
   ```bash
   cd shell && source .venv/bin/activate
   celery -A character_os worker --loglevel=info --pool=solo
   ```
   Without a worker, compositions hang silent at DRAFT
   (`error_message=""`, both steps `pending`) and queue
   envelopes stack in Redis. If a composition doesn't
   advance within 5 seconds in mock-mode, check
   `ps aux | grep celery` first.

**Optional** (depending on which next-item is picked):

* **Media-engine** — only for real-mode renders.
  `uvicorn app.main:app --host localhost --port 8001 --reload`
  from `media-engine/`. Mock-mode skips this entirely.

**Other operational notes:**

* Uvicorn `--reload` window — wait for "Application
  startup complete" between rapid edits per SESSION 180
  TRUST_CALIBRATION.
* For new-arc candidates: the A-arc growth template is now
  the proven shape (9 narrow slices, ½-session cadence,
  backend → SPA, `react-web-delivery` agent for SPA work).
* **Mock-mode storage_health quirk** (SESSION 193 dogfood
  finding): `mock://` URLs fall through the A3 classifier
  to `UPLOAD_PENDING`. That's correct, not a bug. Real-mode
  renders surface as `HTTPS_LIVE`.

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

**Smoke checks** (counts as of SESSION 195 close — no code change):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1006 tests (compositions: 575)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 134 vitest tests
```

**New surfaces from SESSION 192 (Asset Library v1 closure):**

* `CompositionSerializer.produced_assets` —
  `SerializerMethodField` listing every Asset emitted by
  the composition's pipeline. Light shape per row, ordered
  by `Asset.created_at`, with `is_final` marking the
  deliverable.
* `producedAssetSchema` Zod + `produced_assets` on
  `compositionSchema` in `web/src/lib/api/recipes.ts`.
* `ProducedAssetsPanel` component in
  `web/src/routes/compositions/$id.tsx` — renders the
  produced assets list between `<FinalAsset>` and the F5
  lineage panels. Each row links to A6's detail view.
* **Asset Library v1 arc closed** — design lock at
  `docs/design/ASSET_LIBRARY_V1.md` now `status:
  complete`.

**New surfaces from SESSION 191:**

* `GET /api/workspace/assets/<id>/` now includes
  `inline_content` for TRANSCRIPT bodies.
* `/workspace/assets/:id` SPA route.
* `web/src/lib/api/workspace-assets.ts` — extended with
  detail Zod schemas + `getWorkspaceAsset` +
  `useWorkspaceAsset`.

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

- **Last session: SESSION 195 — V-arc closure attempt.**
  No code changes. Real-mode validation of last 2 unvalidated
  recipes found 2 production bugs (mix_audio silent-base
  ffmpeg failure + concat_clips role semantics mismatch).
  3 new TRUST_CALIBRATION entries; 2 fix slices queued.
  Spend: $3.17. V-arc now 17/18 validated.

- **Prior session: SESSION 194 — V18 polish double.** Two
  SESSION 184 calibrations shipped; tests 995 → 1006.

- **Calibration carried forward (23 total — NEW SESSION 195)**:
  - **mix_audio assumes base has audio** — V14/V15.4 design
    oversight surfaced by storyboard_voiced real-mode.
  - **concat_clips role semantics are recipe-dependent** —
    A2's static mapping breaks for combinator primitives.
  - **Real-mode dogfood finds bugs in EVERY recipe** —
    SESSION 158 promoted from "high-yield" to "expected
    behavior." Mock test coverage is necessary but not
    sufficient. Arc-close ceremonies need real-mode validation
    pass across every affected recipe.
  - **Celery worker is NOT optional for mock_mode** —
    mock_mode controls primitive behavior, not the task
    wrapper. Required for ANY composition fire. (NEW
    SESSION 193.)
  - **Arc-close dogfood is high-yield even after full
    test coverage** — test passing ≠ dev stack usable.
    (NEW SESSION 193.)
  - A-arc growth template (SESSION 192).
  - Subagent-source-of-truth (SESSION 189).
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

- **A-arc COMPLETE (SESSIONS 185-192)**: Asset Library
  v1 shipped all 9 slices A0-A8 across 7 sessions.
  Backend (A0-A4) → SPA (A5/A6) → structural fix (A7) →
  cross-link (A8). 80 backend tests + 39 SPA tests added.
  Calibration entry captures the growth template for
  future arcs.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Deferrable since V17 is also
  deferred — pick up if a clean dogfood session opens up.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
