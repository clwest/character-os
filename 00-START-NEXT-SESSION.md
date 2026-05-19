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
> V17.0 + V17.1 + V17.2 SHIPPED SESSION 182. V17.2
> **REAL-MODE VALIDATED** end-to-end at session-close.
> V17.3-V17.5 pending.
> See `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`.
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
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_182_PART_2_V17_2_REAL_MODE_DOGFOOD.md`.

---

## SESSION 182 outcome — V17 scope-lock + V17.0/1/2 shipped + real-mode validated

Eight feature/fix commits across two parts.

**Part 1 (closes at `0a82bbb`):** V17 went from
`status: proposed` (SESSION 181) to `status: locked` with
four contract rules merged into V1 as rules 10-13. V17.0
(media-engine `/internal/clips/extend/` endpoint) +
V17.1 (Django `extend_visual_clip` primitive) shipped.
Q-v17-1 surfaced + resolved mid-slice: Runway's
`/v1/video_to_video` only accepts `gen4_aleph`; pivot to
last-frame extraction + `/v1/image_to_video` (gen4_turbo)
+ ffmpeg concat. Endpoint became synchronous (mirrors V11
style_remix).

**Part 2 (this close):** V17.2 shipped + **real-mode
validated end-to-end**. Four dogfood-surfaced bugs fixed
inline:

* **`02f9f70` feat(V17.2):** `cinematic_visual_extended`
  recipe + 18 tests. Chain: 1 generate (10s gen4.5) + N
  extend (5s gen4_turbo each). target ∈ {15, 20, 25, 30,
  40, 50}.
* **`bfbbe55` fix(V17.2):** target_duration choice values
  must be strings per SPA Zod schema.
* **`1ce6788` fix(V17.2):** opt
  `cinematic_visual_extended` into `LIVE_RECIPE_KINDS`.
* **`01ea94d` fix(recipes):** form-renderer renders
  defaults but the submission path drops them. Latent
  bug across all recipes; V17.2 was first to trigger.
* **`9fac2b3` fix(V17.0):** ffmpeg concat exit 234 on
  silent-input case. Runway outputs have no audio;
  unit-test fixtures used audio-padded lavfi clips so
  this never surfaced before real-mode.

### End-to-end real-mode pass

```
comp 4d3670dd → completed
  step 0 generate_visual_clip → SUCCEEDED (10s base, gen4.5)
  step 1 extend_visual_clip   → SUCCEEDED (15.08s total)
    output: /data/_internal/extends/ac5d402a34935b5e.mp4
cost_actual: $0.75 ($0.50 base + $0.25 extend)
```

Prompt: *"steam rising slowly from a ceramic coffee cup on
a sunlit windowsill, soft morning light, locked-off camera"*.

**Q-v17-1 pivot validated end-to-end.** First operator-
visible V17 capability is live in the product.

Tests: Django **891** (compositions **460**). Media-engine
**194**. SPA vitest **95**. Real-mode spend this session:
**$0.75**.

### Four new TRUST_CALIBRATION entries

1. **Recipe choice values must be strings** per SPA Zod
   schema. Add to slice-open checklist for recipes with
   non-text choices.
2. **New recipes need three SPA touchpoints, not one** —
   string choices + `LIVE_RECIPE_KINDS` opt-in + default-
   aware submission.
3. **Form-renderer renders defaults but drops them on
   submission** — latent across all recipes. Default in
   render = default in submit, no exceptions.
4. **Unit test fixtures must mirror provider output
   shape** — Runway outputs are silent; lavfi fixtures
   with audio padding don't catch this. Shape fixtures
   after a sample of the API's actual output.

### Final state at session close

* V17 **scope-locked with 13 contract rules**. V17.0 +
  V17.1 + V17.2 shipped + real-mode validated; V17.3-V17.5
  pending.
* Q-v17 resolution: Q-v17-1 RESOLVED + REAL-MODE
  VALIDATED; Q-v17-2/3/4 RESOLVED at lock; Q-v17-5 open
  (resolves V17.5 slice-open).

### FIRST THING (SESSION 183): V17.5 — V8 talking_head_with_backdrop opt-in extend

Operator-recommended direction. V17.5 closes the SESSION
179 multi-backdrop concat seam workaround — currently
V8 lays down N separate 10s backdrops + concats them
(visible seams every 10s); the extend chain grows ONE 10s
backdrop to N×5+10s with last-frame conditioning at every
boundary. Concrete operator-visible win.

1. **Read** `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`
   §V17.5 row + V8's existing
   `talking_head_with_backdrop` starter to understand the
   current multi-backdrop math.

2. **Decide on the opt-in shape.** V17 rule 12: V13/V8 keep
   current behaviour; new recipes / new optional kwargs only.
   V8 gets a `use_extend_for_backdrop: bool = False` knob.
   When True, backdrop chain becomes 1 generate + N extend
   instead of N generates + concat.

3. **Ship V17.5** — starter branch + tests + real-mode
   dogfood. Lower-risk than V17.2 because V17.0 + V17.1
   are now real-mode validated.

Alternative: **V17.3 (keyframes track).** Independent of
V17.5 per the dependency graph. ~1 session. Higher-risk
since keyframes API isn't real-mode validated yet — likely
surfaces its own Q-v17-style finding before code lands.

Alternative: defer V17 + work F8.1 K10 seed corpus, asset
upload UI, or other queued items.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete +
R-arc real-mode validated (SESSION 176); V-arc real-mode
validation **near-complete** (16 of 18 recipes, SESSIONS
158 + 179 + 180 + 181). V16 post-close shipped (SESSION
179); **V17 scope-locked SESSION 182, V17.0/1/2 shipped
+ V17.2 real-mode validated end-to-end**. V17.3-V17.5
pending.
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent
(SESSION 178 B-arc).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); **16/18 real-mode validated** |
| **V17.0 + V17.1 + V17.2** | **DONE + V17.2 REAL-MODE VALIDATED (SESSION 182)** |
| **V17.3 (keyframes) / V17.4 / V17.5** | **pending** |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED (SESSION 176) |
| W11.6.0-W11.6.5 (media gen) | DONE (SESSIONS 172-173) |
| W11.x voice telemetry + W11.y personality split | DONE |
| K7.1 cost telemetry | DONE (SESSION 174) |
| K7.x v2 YouTube extractor | DONE (SESSION 175); real-mode unverified |
| Multi-step composition title disambig | DONE (SESSION 177) |
| Sasha + Donny voice re-persist | DONE (SESSION 177, data-only) |
| B0-B5 brand ecosystem pivot | DONE (SESSION 178) |
| V16 remove_avatar_background | DONE (SESSION 179) |
| V9 polish form shorthands + intro_outro fixes | DONE (SESSION 180) |
| V7/V11/V13 dogfood fixes + 11 recipes validated | DONE (SESSION 181) |
| **V17.2 cinematic_visual_extended + 4 dogfood fixes** | **DONE + REAL-MODE VALIDATED (SESSION 182)** |
| B6-B10 brand arc | Deferred (product #2 reality) |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI (AUDIO / IMAGE) | Queued (SESSION 181) |
| 2 of 18 V-arc recipes unvalidated | storyboard_voiced + dialogue_scene; deferred until V17 closes |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
    (SESSION 179-181 hero — most-validated avatar)
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (stale "Thruman" record at same prefix queued for cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (most-dogfooded — 4 ENDED realtime sessions + 1
    rendered MP4 SESSION 176)

**SESSION 182 workspace artifacts (part 2):**

* 2 `Composition` rows of kind `cinematic_visual_extended`:
  - `cd72ebd5...` — first attempt, `partial` (forensic
    record of silent-input bug)
  - `4d3670dd...` — retry, `completed` (first end-to-end
    V17 success)
* 2 CLIP Assets: Runway CDN URL for the 10s base + local
  merged 15s clip at
  `/data/_internal/extends/ac5d402a34935b5e.mp4`

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

**SESSION 183 stack-up notes:**

* **Celery worker** was restarted by AI mid-SESSION 182
  part 2 to pick up V17.1 + V17.2 primitive + recipe
  registrations. If SESSION 183 touches
  `apps/compositions/primitives/` OR `apps/*/tasks.py`,
  restart again.
* The `cd72ebd5...` partial composition is harmless but
  visible in admin / lineage queries. Operator's call to
  keep as forensic record or delete.
* Uvicorn `--reload` window — wait for "Application
  startup complete" between rapid edits per SESSION 180
  TRUST_CALIBRATION.

**Slice-open checklist (codified SESSION 182):**

For any new recipe that wraps a third-party API:

1. **Live-doc check** the API surface the slice depends
   on. (Q-v17-1 was a 3rd-recurrence of the API-docs-from-
   skim trap.)
2. **String choice values** in recipe `select` fields per
   the SPA Zod schema.
3. **`LIVE_RECIPE_KINDS` opt-in** in
   `web/src/lib/api/recipes.ts`.
4. **Default-aware form submission** verified (the
   `01ea94d` fix is the single source of truth now).
5. **Unit fixtures shaped after a sample of provider
   output**, not the easiest-to-construct shape.

**Smoke checks** (counts as of SESSION 182 part 2 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 891 tests (compositions: 460)

# Media-engine (from media-engine/)
python -m pytest                              # 194 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 182:**

* `POST /internal/clips/extend/` — media-engine. V17.0.
* `extend_visual_clip` Django primitive — V17.1.
* `cinematic_visual_extended` recipe — V17.2. Live in V15
  gallery; produces 15-50s clips.
* `MediaEngineClient.extend_clip()` — Python client.
* `_has_audio_stream` helper in media-engine internal.py
  (probes audio before concat).

---

## AI / assistant context

- **Last session: SESSION 182 — V17 scope-lock + V17.0 +
  V17.1 + V17.2 + real-mode validation.** Eight commits
  across two parts. V17 went `proposed → locked`; rules
  10-13 merged into V1. V17.0 (endpoint) + V17.1 (Django
  primitive) + V17.2 (recipe) shipped. Q-v17-1 surfaced +
  resolved at slice-open with a clean pivot. Four dogfood-
  surfaced bugs (3 SPA, 1 silent-input concat) fixed
  inline. End-to-end real-mode pass: `cinematic_visual_extended`
  produced a 15.08s clip at $0.75 spend.

- **Calibration carried forward (NEW SESSION 182 — 7 total)**:
  - API claim in design doc = hypothesis until live-doc
    verified (3rd recurrence).
  - Pre-implementation pause when a finding shifts scope.
  - Sync vs async endpoint contract is a design-time
    decision.
  - Recipe choice values must be strings (SPA Zod).
  - New recipes need three SPA touchpoints, not one.
  - Form-renderer renders defaults but drops them on
    submission (latent across all recipes).
  - Unit test fixtures must mirror provider output shape.

- **Calibration carried forward (from earlier sessions)**:
  - Operator "are we using X?" framing surfaces capability
    gaps (SESSION 181).
  - Asset upload UI is a recurring gap (SESSION 181).
  - External API validation tightens over time —
    re-dogfood periodically (SESSION 181).
  - "200 OK + plausible byte count" doesn't mean correct
    output (SESSION 180).
  - Uvicorn `--reload` has stale-during-restart window
    (SESSION 180).
  - drawtext `text=` footgun once `fontfile=` joins
    (SESSION 180).
  - Celery worker doesn't auto-reload (SESSION 179).
  - ffmpeg can't infer muxer from double-extension
    tempfile names (SESSION 179).
  - Real-mode dogfood finds bugs in every recipe
    (SESSIONS 179-182 — now 19+ bugs across 17 recipes).
  - PostCSS `@import` order (SESSION 178).
  - Operator catches premature extraction (SESSION 178).
  - DevTools computed-style snippet for visual bugs
    (SESSION 178).
  - Lossy paraphrase of scope locks (SESSION 177).
  - Handoff "swapped/edited" claims need verification
    (SESSION 177).
  - Runway DELETE poisons conversation (SESSION 176).
  - Mock-only test coverage hides upstream drift
    (SESSION 176).
  - Operator framing unlocks AI blockers (SESSION 176).
  - gpt-5 reasoning eats output budget silently
    (SESSION 176).
  - Tool descriptions need narration scaffolding
    (SESSION 176).
  - Real-mode dogfood after operator-facing slices.
  - SPA gates need both `pnpm test` AND `pnpm build`.
  - Distinct request boundaries for distinct side-effects.
  - Hook order across early returns (SESSION 169).
  - AI's "shipped" framing belongs to operator after
    review.
  - Doctor is the drift tool + handoff write at
    session-end.
  - OpenAI gpt-5 family uses Responses API.
  - lru_cached `get_settings()` bypasses FastAPI
    dependency_overrides.
  - Radix UI primitives need `userEvent` under jsdom.
  - Scope-lock reviews should distinguish operator
    input from LLM input.
  - Don't rationalise "somewhat readable" — look at
    operator-facing surface.
  - Vitest atomic assertions can mask real UX bugs.
  - Stale browser before stale code.
  - K6.4 stoplist curation trickle.

- **V-arc growth template (SESSION 179-182)**: V16 + V17
  follow the same shape. Narrow scope, opt-in defaults,
  one primitive + one knob + one endpoint per slice, real-
  mode validated before handoff. **V17.2 is the first
  multi-slice extension that real-mode validated**
  end-to-end at session-close, not in a follow-up session.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Both deferred until V17 closes per
  operator-locked direction.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
