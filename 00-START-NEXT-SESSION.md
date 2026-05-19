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
> (locked SESSION 142 — **13 contract rules** total: V1's 9 + V17's
> 4 merged as rules 10-13; V0-V15 + V16 slice breakdown).
> **V16 POST-CLOSE SHIPPED (SESSION 179) — remove_avatar_background.**
> **V17 LOCKED (SESSION 182) — extend + keyframes.**
> V17.0 + V17.1 + V17.2 + V17.5 SHIPPED + REAL-MODE VALIDATED.
> **V17.3 DEFERRED (SESSION 184)** — Q-v17-6 documented
> live-doc-check finding: `gen4_turbo` doesn't support
> first+last keyframes (SDK only `position: "first"`).
> Re-open criteria: Runway adds keyframes to gen-4 family
> OR operator adopts `veo3.1_fast` as primary model in a
> separate arc. V17.4 also pending V17.3.
> See `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`
> §Q-v17-6.
> **V18 SHIPPED + REAL-MODE VALIDATED (SESSION 184)** —
> `backdrop_clip` on `talking_head_with_backdrop`; picked-
> clip path skips both V8 concat AND V17.5 extend chains.
> Mirror's V16/V17.5 opt-in pattern. UX gap surfaced:
> composite trims short input → when speech > backdrop,
> speech gets cut off mid-sentence. Queued for V18 polish.
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE + REAL-MODE HARDENED
> (SESSION 176).**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5.1-3 COMPLETE.**
> **NEW: Asset Library scope proposal (SESSION 184)** —
> `docs/design/ASSET_LIBRARY_V1.md` (`status: proposed`).
> 9 roles, 9 contract rules, 8 slices A0-A8 (~5-6 sessions).
> Pending operator review SESSION 185.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_184_POLISH_V18_Q_V17_3_ASSET_LIBRARY_LOCK.md`.

---

## SESSION 184 outcome — polish + V18 + Q-v17-3 + Asset Library proposal

Six feature commits + design doc + handoff. Three
planned slices: #1 (polish) + #2 (V18 backdrop library)
shipped + real-mode validated. #3 (V17.3 keyframes)
deferred at slice-open after live-doc check against
Runway's SDK surfaced an API-shape mismatch
(Q-v17-6). The deferral triggered an operator-driven
scope proposal for a new arc — **Asset Library** —
addressing the structural categorization gap that
became visible during the V18 dogfood.

### Slice 1 — polish (`7045270`)

* `generate_avatar_speech` falls back to a chars/sec
  estimate when Runway's poll returns `duration_seconds=None`.
  Stamps `duration_estimated=True` on extra_source_spec.
* `composite_video` refuses inputs with `duration_ms=None`
  before media-engine dispatch.
* +4 tests; **real-mode validated** in the V18 dogfood
  (step 0 output Asset showed `duration_estimated: True`,
  8818ms estimate).

### Slice 2 — V18 backdrop library (`b935acd`)

* `talking_head_with_backdrop` gains optional
  `backdrop_clip: Asset | None = None` kwarg. When set,
  short-circuits the concat / extend chains; uses picked
  Asset as composite background directly.
* Recipe field `backdrop_clip_id` (asset_picker, CLIP,
  optional). `backdrop_prompt` flipped to optional. XOR
  enforced in starter (clip wins when both supplied).
* No schema migration (CompositionStep.inputs already
  accepts asset_id shape).
* +11 tests; **real-mode validated** end-to-end via
  composition `b2188dcf` "Riggs-pre-background".

### Slice 3 — V17.3 deferred (`c10e311`, `2daef87`)

Live-doc check against
`runwayml/types/image_to_video_create_params.py`
(auto-generated from Runway's OpenAPI spec) revealed:

* No `keyframes: [str]` parameter exists. Conditioning
  is via `promptImage: str | Iterable[{position, uri}]`.
* `gen4_turbo` only accepts `position: "first"`.
* Only `gen3a_turbo` (ratio cliff to 768:1280 /
  1280:768) and `veo3.1_fast` (Google Veo brokered
  through Runway; 1280:720 supported) accept both first
  + last.

Operator picked dogfood-both. `smoke_keyframes`
management command shipped (with `--hook-asset-id` /
`--payoff-asset-id` flags + inline data: URI
conversion mirroring `gen4_turbo`'s SESSION 181 path).
Real-mode smoke fired both models on a V13 storyboard
Hook (founder at 3am) / Payoff (founder at sunrise)
pair. Findings:

* `veo3.1_fast` — ~40-50s render, accepted 1.75MB
  inline data: URI, 1280:720 / 6s output.
* `gen3a_turbo` — ~6-9s render (5-7× faster), same
  data: URI accepted, 1280:768 / 5s output.
* **Both models accept data: URIs** (removes that
  design risk).
* **gen3a_turbo identity drift on human keyframes
  was severe** — operator observed "two different AI
  generated people" across the 5s clip. Same Q-v17-3-
  shape drift the keyframes were supposed to fix.

**V17.3 deferred** with Q-v17-6 documented. Re-open
criteria in `VIDEO_COMPOSITION_V17_PROPOSAL.md`.

### V18 dogfood (composition `b2188dcf`)

Operator picked the gen3a_turbo smoke output as
`backdrop_clip`. Composition completed; Riggs
correctly rendered top-right. Three findings:

1. **Slice 1's avatar_speech fallback fired** —
   real-mode validated.
2. **V18 picked-clip path works** — 2-step plan,
   correct asset_id wiring, composite produced final.
3. **New V18 UX finding:** composite trimmed to the
   SHORTER input (5s backdrop), cutting Riggs's 9s
   speech off mid-sentence. Opposite shape of the
   SESSION 183 Sunset 2 finding. V18 needs a
   starter-time validation warning when
   `backdrop_clip.duration_ms < estimated_speech_duration`.

### Asset Library proposal (`docs/design/ASSET_LIBRARY_V1.md`)

Triggered by V18 dogfood's "two random people"
moment, which surfaced an operator-visible
categorization gap: the workspace has 119 CLIPs +
9 IMAGE + others with no role-level filtering, so
the asset_picker becomes a guessing game.

* 9-role closed enum stamped at primitive-emit time.
* 9 contract rules (carry V1's 9 unchanged).
* 8 slices A0-A8 (~5-6 sessions): role migration →
  backfill → primitive stamping → storage-health →
  browse REST → SPA list → SPA detail → asset_picker
  role filter → F-arc lineage cross-link.
* `status: proposed` — pending operator review.

### Calibration carried forward (six NEW entries)

1. **Live-doc-check discipline 2-for-2 on V17.**
   Both Q-v17-1 (SESSION 182) and Q-v17-6 (SESSION
   184) caught at slice-open. Discipline confirmed:
   third-party-wrapping slices MUST live-doc-check
   the API surface before writing code.
2. **V18 + duration mismatch needs starter-time
   guard.** When backdrop_clip is shorter than
   estimated speech, the composite trims speech and
   the operator sees cut-off mid-sentence. Queue for
   V18 polish slice.
3. **Asset taxonomy gap is structural.** 119 CLIPs
   in one workspace with no role-level filtering
   triggered the Asset Library scope proposal.
   Pattern: when metadata categorizes by production
   method but operator filters by intended use, the
   categorization is wrong shape.
4. **Smoke commands without `--save-assets` produce
   orphans.** `smoke_keyframes` was designed "no DB
   writes"; in practice the operator wanted to see
   outputs in UI. Future smokes should default to
   backfilling CLIP rows.
5. **Celery worker stop-state is silent.** A
   composition sat in `draft` for 8.5 minutes while
   no worker consumed. SPA / admin should surface
   "queued but no worker" as visible state.
6. **Re-using smoke outputs as backdrops is a
   testing-shape mismatch.** The gen3a_turbo smoke
   was a person-interpolation, not a scene. Wiring it
   into V18's backdrop slot dragged drift into V18's
   output. Asset Library A7 (role-filter on picker)
   is the structural fix.

### Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **915** | +15 (904 → 915) |
| - compositions | **484** | +15 (469 → 484) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

Real-mode spend this session: **~$2.50** (smoke ~$1.50-$3
+ V18 dogfood ~$0.50 avatar speech).

---

## FIRST THING (SESSION 185): operator review of Asset Library v1 scope

**Path A — lock the arc** (recommended):

1. Read `docs/design/ASSET_LIBRARY_V1.md` end-to-end.
2. Resolve or defer Q-a-1 through Q-a-6 (taxonomy
   choice, backfill strategy, storage-health caching,
   detail-view shape, picker filter mechanism,
   Avatar/Voice/Portrait modeling).
3. Lock — flip `status: proposed` → `status: locked`,
   merge contract rules into V1 as rules 14-22.
4. Open slice A0 (Asset.role migration).

**Path B — pivot:**

* Different taxonomy approach (free-form tags? hybrid?).
* Asset upload UI first (queued SESSION 181 gap that
  intersects).
* Cast rebuild first (fresh Riggs/Sasha/Donny avatars
  via `gen4_image`) — narrower dogfood task, doesn't
  require the new arc.

**Path C — small-win sidebars first** then return:

* V18 polish slice — add starter-time
  duration-mismatch warning (~½ session, addresses
  today's surfaced UX gap).
* F8.1 K10 seed corpus (queued).
* `storyboard_voiced` + `dialogue_scene` real-mode
  validation (last two unvalidated V-arc recipes,
  deferrable since V17 is now deferred).

Recommended sequence: **Path A** — the Asset Library
gap is the most-recent operator-visible friction, and
the design doc is already drafted. A0 + A1 ship cleanly
inside one session.

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
**NEW arc proposed (SESSION 184):** Asset Library v1
(`status: proposed`).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); 16/18 real-mode validated |
| V17.0 + V17.1 + V17.2 + V17.5 | DONE + REAL-MODE VALIDATED |
| **V18 (backdrop_clip on V8)** | **DONE + REAL-MODE VALIDATED (SESSION 184)** |
| V17.3 (keyframes) + V17.4 | **DEFERRED (SESSION 184) — Q-v17-6** |
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
| **Polish slice 1 (duration fallback + null guard)** | **DONE + REAL-MODE VALIDATED (SESSION 184)** |
| **smoke_keyframes management command** | **DONE + REAL-MODE VALIDATED (SESSION 184)** |
| **Asset Library v1 proposal** | **DRAFTED — pending review (SESSION 184)** |
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

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
    (SESSION 179-181 hero — most-validated avatar; portrait
    URL confirmed as donkey SESSION 184 after operator
    concern surfaced)
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (stale "Thruman" record at same prefix queued for cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (most-dogfooded — 4 ENDED realtime sessions + 1
    rendered MP4 SESSION 176)

**SESSION 184 workspace artifacts:**

* 2 new CLIP Assets backfilled from smoke (manual,
  via Django shell):
  - `c21fdeec...` — `veo3.1_fast` smoke output, 6s,
    1280:720, HTTPS Cloudfront
  - `89a1ce5f...` — `gen3a_turbo` smoke output, 5s,
    1280:768, HTTPS Cloudfront
* 1 `Composition` row of kind `talking_head_with_backdrop`:
  - `b2188dcf...` — V18 picked-clip dogfood
    "Riggs-pre-background", completed end-to-end with
    `89a1ce5f` as backdrop

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

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

**SESSION 184 stack-up notes:**

* **Celery worker** was stopped at session start; AI
  restarted mid-session to pick up the V18 dogfood. If
  SESSION 185 touches `apps/compositions/primitives/`,
  `apps/compositions/starters.py`, or `apps/*/tasks.py`,
  restart again. The "worker stop-state is silent"
  calibration (SESSION 184 #5) means no automatic
  signal will tell you the worker is down.
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

**Smoke checks** (counts as of SESSION 184 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 915 tests (compositions: 484)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 184:**

* `talking_head_with_backdrop(..., backdrop_clip=None)`
  — V18 starter kwarg. When set, picked Asset wires
  directly into composite background; both V8 concat
  and V17.5 extend chains are skipped.
* `backdrop_clip_id` RecipeField on
  `talking_head_with_backdrop` (asset_picker, CLIP,
  optional). `param_map={backdrop_clip_id: backdrop_clip}`.
* `_estimate_duration_ms_from_script(chars: int) → int`
  helper in `avatar_speech.py`. Fallback when Runway
  poll lacks `duration_seconds`.
* `composite_video` null-duration guard — raises
  `PrimitiveError` before media-engine dispatch.
* `shell/apps/compositions/management/commands/smoke_keyframes.py`
  — one-off comparison utility for keyframe-capable
  Runway models (`veo3.1_fast`, `gen3a_turbo`).
  Supports `--hook-asset-id` / `--payoff-asset-id` with
  inline data: URI conversion.

---

## AI / assistant context

- **Last session: SESSION 184 — polish + V18 + Q-v17-3 +
  Asset Library proposal.** Six feature commits + design
  doc + handoff. Two slices shipped + real-mode validated
  (polish + V18); slice 3 (V17.3) deferred at slice-open
  after live-doc check surfaced API-shape mismatch
  (Q-v17-6). Operator-driven scope proposal triggered for
  a new arc — Asset Library — addressing the asset
  categorization gap visible during V18 dogfood. Six new
  TRUST_CALIBRATION entries.

- **Prior session: SESSION 183 — V17.5 V8 opt-in extend
  shipped + real-mode validated.** One feature commit + 4
  real-mode renders ($6.25 spend). Ambient motion holds
  cleanly through extend chain; discrete-subject identity
  drifts at gen4.5 → gen4_turbo handoff. Two latent gaps
  surfaced (speech duration_ms, composite null guard) →
  shipped as SESSION 184 slice 1.

- **Calibration carried forward (NEW SESSION 184 — 13 total)**:
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
  slice, real-mode validated before handoff. **V18 is the
  first post-close addition that requires NO new endpoint
  or primitive** — pure starter + recipe wiring against
  existing infrastructure. Cheapest-shape post-close.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Now deferrable since V17 is
  deferred — pick up if a clean dogfood session opens up.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
