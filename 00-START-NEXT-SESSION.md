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
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5 sub-slices 1/2/3 COMPLETE.**
> **Asset Library scope lock:** `docs/design/ASSET_LIBRARY_V1.md`
> (locked SESSION 185). **10 roles** (`EXPERIMENT` added for
> smoke / sandbox outputs), 9 contract rules merged into V1
> as rules 14-22, **9 slices A0-A8** (~5-6 sessions).
> Q-a-1 through Q-a-5 resolved at lock; Q-a-6 deferred to v2.
> **A0 OPEN (SESSION 185).**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_185_DRIFT_SWEEP_ASSET_LIBRARY_LOCK_A0_A1.md`.

---

## SESSION 185 outcome — drift sweep + Asset Library lock + A0 + A1

Clean session — no deferrals, no surprises. Five commits
land: boot drift-sweep + Asset Library scope-lock + A0
(model + migration) + A1 (backfill command) + close.
**Asset Library v1 opens for real.** 128 of 136 dev-DB
assets backfilled to role-tagged state via live
`--commit` run. Test totals **915 → 928 (+13)**.

### Slice 0 — drift sweep (`082ff8f`)

Doctor exited with 3 warnings at session start; all
three resolved before opening A0. Created
`docs/CONTEXT_KIT_INVENTORY.md` (context-kit-managed
inventory); scrubbed two regex false-positive literals
from start-here (uvicorn host IP literal → `localhost`,
W-arc sub-slice naming → expanded prose); backfilled
two missing handoffs (session 053 numbering gap +
session 172 reconstituted from commit `2eb3a8c`).
Doctor exits **0/0**.

### Slice 1 — Asset Library scope-lock (`0306b8b`)

Operator review resolved all 6 open questions in one
batch. **Taxonomy lands at 10 roles, not 9** —
`EXPERIMENT` added to capture intent-vs-medium for
smoke / sandbox outputs. Pre-lock review caught that
backfilling smoke outputs AS `BACKDROP` would re-trigger
the exact bug A7 was supposed to fix. `mix_audio` →
`COMPOSITE_OUTPUT`. Backfill: always dry-run; `--commit`
to apply. Storage-health: live per request (cache later
if A5 demands). Detail view: extend F-arc lineage.
Picker filter: first-class `RecipeField.role_filter`.
Avatar/Voice/Portrait: deferred to v2.

**9 contract rules merged into VIDEO_COMPOSITION_V1.md
as rules 14-22.** Slice count corrected to 9 (A0-A8).

### Slice 2 — A0 Asset.role enum + migration (`235e21f`)

`AssetRole` 10-value TextChoices + `Asset.role`
CharField + `(workspace, role)` index. Migration
`0009_a0_asset_role`. 4 new tests; compositions 484 →
488.

### Slice 3 — A1 backfill_asset_roles command (`a9b21b3`)

Heuristic-driven backfill from
`source_spec.primitive_kind` → `Asset.role`. 20 known
primitive_kind values mapped; 2 known smoke UUIDs
(`c21fdeec`, `89a1ce5f`) hard-coded as `EXPERIMENT`.
Dry-run by default; `--commit` to apply; `--workspace
NAME` to scope. ALLOWED_FILES entry added to
test_isolation.py (sanctioned writer: role-only update).
9 new tests; compositions 488 → 497.

**Real-mode --commit run on dev DB: 128 rows updated**
across 8 roles. 8 needs-review legacy rows (2 audio + 6
image pre-dating primitive_kind discipline) deferred to
post-v1 upload-UI / mutation surface. Idempotency
confirmed live (re-running dry-run shows 8 candidates,
0 mappable).

### Carried-forward content (SESSION 184 context, unchanged below)

#### Slice 1 (S184) — polish (`7045270`)

* `generate_avatar_speech` falls back to a chars/sec
  estimate when Runway's poll returns `duration_seconds=None`.
  Stamps `duration_estimated=True` on extra_source_spec.
* `composite_video` refuses inputs with `duration_ms=None`
  before media-engine dispatch.
* +4 tests; **real-mode validated** in the V18 dogfood
  (step 0 output Asset showed `duration_estimated: True`,
  8818ms estimate).

#### Slice 2 (S184) — V18 backdrop library (`b935acd`)

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

#### Slice 3 (S184) — V17.3 deferred (`c10e311`, `2daef87`)

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

### Calibration carried forward from SESSION 184 (six entries)

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

### Tests at SESSION 185 close

| Suite | Count | Delta |
|---|---|---|
| Django | **928** | +13 (915 → 928) |
| - compositions | **497** | +13 (484 → 497) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

Real-mode spend SESSION 185: **$0** (pure backend / DB
work; no Runway / Stability API calls).

---

## FIRST THING (SESSION 186): slice A2

A0 + A1 shipped in SESSION 185 + dev-DB backfill
committed. **A2 is the next slice in the Asset Library
arc.**

**A2 deliverable: every primitive in
`apps.compositions.primitives` stamps `role` on its
output Asset at emit time. Migration test enforces
contract rule 20** (no primitive emits assets without a
role).

1. Walk every primitive module in
   `shell/apps/compositions/primitives/` (avatar_speech,
   visual_clip, extend_visual_clip, concat_clips,
   composite_video, mix_audio, polish.py (5 sub-primitives),
   voice.py (2 sub-primitives), style_remix,
   transcribe, generate_image, audio_extract,
   remove_avatar_background, split_script). Each
   primitive's `Asset.objects.create(...)` (or
   `PrimitiveResult` construction) must include
   `role=AssetRole.X` per the heuristic table that A1
   established.
2. The realtime transcript task (`apps/realtime/tasks.py`
   `capture_transcript`) creates `Asset(TRANSCRIPT)`
   directly — must also stamp `role=AssetRole.TRANSCRIPT`.
3. Same source of truth for both production code +
   backfill heuristic: factor the
   `primitive_kind → role` mapping in
   `apps.compositions.management.commands.backfill_asset_roles.PRIMITIVE_TO_ROLE`
   to be importable as the single mapping table.
   Production code uses it at emit time; backfill uses
   it for legacy rows. Pre-existing test
   `test_heuristic_table_covers_every_primitive_kind_in_codebase`
   becomes the duplicate-prevention guard.
4. **New migration test for contract rule 20**: walk the
   set of registered primitives (from a primitive
   registry — likely needs creation, or AST-scan
   `*.py` files in `apps/compositions/primitives/` for
   `"primitive_kind": "..."` literals like the SESSION
   184 enumeration). For each, assert the mapping table
   has an entry. Test lives in
   `apps/compositions/tests/test_primitive_role_coverage.py`
   (new file).
5. Tests: per-primitive emit-time-role tests. Could go
   in the existing per-primitive test files (the V*-* +
   test_primitive_* files), or in a new dedicated
   `test_primitive_role_stamping.py`. Lean toward
   per-primitive tests since they read closer to the
   production code they cover.
6. Stack-up note: **restart Celery worker before any
   composition fires** so the worker picks up the new
   primitive code. The worker stop-state is silent
   (SESSION 184 calibration #5).

A2 estimated effort: 1 session (largest A-slice — 14+
primitives to touch). May naturally include the
primitive registry if one doesn't already exist (rule
20 needs an enumerable set of primitives at test time).

**After A2, the operator-visible payoff lies in A4
(read endpoint) + A5 (SPA list) + A7 (role-filtered
asset_picker). A3 (storage-health helper) is the
remaining foundational slice before frontend work.**

### Alternative paths for SESSION 186

If A2 feels too large for one session:

* **Path B — A3 first.** Storage-health helper +
  filesystem stat + JWT exp parser. Smaller (½
  session). A4 doesn't need A2 to ship; A3 is a clean
  parallel branch.
* **Path C — small-win sidebars.** V18 polish
  (duration-mismatch starter warning, ~½ session), F8.1
  K10 seed corpus, or `storyboard_voiced` +
  `dialogue_scene` real-mode validation. Asset Library
  parks while a smaller win lands.

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
**Asset Library v1 arc OPEN (SESSION 185):**
scope-locked + 9 contract rules merged into V1 as rules
14-22 + **A0 + A1 shipped + dev-DB backfill committed**
(128 of 136 rows). A2 opens next.

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
| **Asset Library v1 — A0 enum + migration** | **DONE (SESSION 185)** |
| **Asset Library v1 — A1 backfill command + dev-DB --commit** | **DONE (SESSION 185)** |
| Asset Library v1 — A2 primitives stamp role at emit | **NEXT (SESSION 186)** |
| Asset Library v1 — A3 / A4 / A5 / A6 / A7 / A8 | Queued |
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

**SESSION 185 dev-DB backfill (--commit applied):**

* 128 of 136 RAW_UPLOAD candidates updated across 8
  roles:
  - 49 talking_head
  - 42 backdrop
  - 15 composite_output
  - 11 polish_output
  - 4 transcript
  - 3 reference_image
  - 2 audio_track
  - 2 experiment (`c21fdeec` + `89a1ce5f`)
* 8 needs-review legacy rows remain at RAW_UPLOAD
  (2 audio + 6 image, all in `Admin's workspace`,
  pre-dating primitive_kind discipline). Per-asset
  tagging deferred to post-v1 upload-UI / mutation
  surface.

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

**SESSION 186 stack-up notes:**

* **Celery worker** must be restarted before SESSION
  186's A2 work fires any composition. A2 changes
  primitive emit shape (every primitive stamps role) —
  worker holds stale module imports if not bounced.
  "Worker stop-state is silent" calibration (SESSION 184
  #5) means no automatic signal will tell you the worker
  is down.
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

**Smoke checks** (counts as of SESSION 185 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 928 tests (compositions: 497)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 185:**

* `AssetRole` TextChoices enum (10 values) in
  `apps.compositions.models`. Imported as
  `from apps.compositions.models import AssetRole`.
* `Asset.role` CharField — default `RAW_UPLOAD`, indexed
  via `(workspace, role)`.
* `python manage.py backfill_asset_roles` management
  command — dry-run by default; `--commit` to apply;
  `--workspace NAME` to scope. Heuristic table at
  `apps.compositions.management.commands.backfill_asset_roles.PRIMITIVE_TO_ROLE`.
* `docs/CONTEXT_KIT_INVENTORY.md` — context-kit-managed
  inventory companion to `CHARACTER_OS_INVENTORY.md`.
  Distinct purposes; both maintained.

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

- **Last session: SESSION 185 — drift sweep + Asset
  Library scope-lock + A0 + A1.** Five commits + handoff.
  Clean session, no deferrals. Doctor went 3 warnings →
  0 at boot. Asset Library v1 locked with 10 roles
  (`EXPERIMENT` added at lock review) + 9 contract rules
  merged into V1 as rules 14-22. A0 (model + migration)
  + A1 (backfill command + dev-DB --commit applied to
  128 of 136 candidates) shipped. Tests 915 → 928. Two
  new TRUST_CALIBRATION entries (walk-proposal-mechanism
  + doctor-heuristic-false-positives).

- **Prior session: SESSION 184 — polish + V18 + Q-v17-3
  + Asset Library proposal.** Six feature commits + design
  doc + handoff. Two slices shipped + real-mode validated
  (polish + V18); slice 3 (V17.3) deferred at slice-open
  after live-doc check surfaced API-shape mismatch
  (Q-v17-6). Operator-driven scope proposal triggered for
  a new arc — Asset Library — addressing the asset
  categorization gap visible during V18 dogfood. Six new
  TRUST_CALIBRATION entries.

- **Calibration carried forward (NEW SESSION 185 — 15 total)**:
  - Walk a proposal's mechanism through its motivating
    calibration event before locking.
  - Doctor heuristics over-match on project-shape naming
    conventions.
  - (from SESSION 184 — 6 entries unchanged below)
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
