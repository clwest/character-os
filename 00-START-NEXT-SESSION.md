---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — 9 contract rules, V0-V15 slice breakdown).
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0-W11.6.4 COMPLETE; W11.6.5
> deferred to W11.7+.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_173_W11_6_MEDIA_GENERATION.md`.

---

## SESSION 173 outcome — W11.6 media generation arc

Built and shipped four W11.6 implementation slices end-to-end
(W11.6.1 → W11.6.2 → W11.6.3 → W11.6.4), closed with real-
Stability dogfood validated by operator on the SPA.

* **W11.6.1** (commit `e7c565a`) — Asset model gained 7
  optional image fields + spokesperson FK + migration 0006.
  New `POST /internal/image_stability/` endpoint on
  media-engine with `VALID_PURPOSES` enum (avatar / scene /
  broll / product / ad) threaded through
  `stability_portrait.py`. Backwards-compat with the
  SESSION 170 rebake call site preserved (avatar purpose +
  default template). 22 new media-engine tests.
* **W11.6.2** (commit `708ba1f`) — Django REST API:
  `ImageViewSet` (POST/GET list/retrieve/DELETE) +
  `StyleLibraryViewSet` (GET) co-located in
  `apps.compositions` (Q-img-A resolved). `purpose=avatar`
  rejected with 400 in v1 per Contract rule 2; SPA-facing
  enum is the 4 non-avatar purposes. New `/internal/styles/`
  on media-engine. 24 new Django tests.
* **W11.6.3** (commit `ca6df3b`) — SPA route + form:
  `/images` registered as 5th nav item (F0 contract rule 7
  satisfied via W11.6 scope-lock). `useGenerateImage` /
  `useImages` / `useImage` / `useDeleteImage` /
  `useStyleLibrary` hooks. Locked hint copy for 6 models +
  6 aspect ratios + 4 purposes (Contract rule 9).
  Categorized style preset picker for the 42 presets.
  Generation form defaults to scene + sd3-large + 16:9.
  17 new vitests.
* **W11.6.4** (commit `29a4824`) — SPA library + detail
  modal. **Scope-lock omission resolved**: added 8th Asset
  field `subject` (migration 0007). The Regenerate CTA
  needs the pre-composition subject — re-firing with the
  composed prompt would double-apply purpose framing
  ("A detailed scene illustration of A detailed scene
  illustration of…"). Library grid with filters
  (purpose/model/style), filter-aware empty state, 200-cap
  hint. Detail modal with Regenerate (uses subject) +
  Delete (confirm tap). 12 new vitests + 1 new Django test.
* **Real-Stability dogfood** — ~12 Stability credits total
  (~$0.012) across 4 renders. 3 Asset(image) rows now live
  in `Admin's workspace` (scene/product/broll). Operator
  confirmed visual on the SPA library tab.

Tests: Django **727 → 752** (+25). Media-engine **111 →
133** (+22). SPA vitest **53 → 82** (+29). Migrations 51 →
53. Media-engine routes 130 → 132. Django URL patterns +5.

### Calibration moments worth carrying

1. **lru_cached `get_settings()` bypasses FastAPI
   `app.dependency_overrides`** — service-direct call sites
   need `monkeypatch.setattr("module.path.get_settings",
   lambda: fake)`, OR pass settings down from the endpoint.
   Cost of finding out: 6.5 Stability credits when the first
   W11.6.1 test run accidentally hit real Stability. New
   TRUST_CALIBRATION entry.
2. **Radix UI primitives need userEvent under jsdom** —
   `fireEvent.click` on a TabsTrigger doesn't reliably flip
   the active panel. Use `userEvent.setup() + await
   user.click()`. Pattern now established for the SPA test
   suite. New TRUST_CALIBRATION entry.
3. **Scope-lock should distinguish operator input from LLM
   input** for any composition-step surface. W11.6
   scope-lock missed the subject/prompt distinction; caught
   at W11.6.4 modal implementation. New TRUST_CALIBRATION
   entry; apply the lens proactively in future scope-locks.

### Final state at session close

* Cast roster: unchanged (Riggs / Sasha / Donny / Maya /
  Marcus).
* **New: 3 Stability images in `Admin's workspace`** image
  library (brewery owner / glass mug / vineyard hills).
* All Phase 4 arcs (K / V / F / R) + W11.6 sub-arc closed.
* Stack-up healthy at session close: media-engine + Django
  + SPA all running; uvicorn auto-reload picked up
  changes; no Celery worker restart needed this session
  (no Celery surfaces touched).

### FIRST THING (SESSION 174): pick by mood

W11.6.5 (recipe inline image-picker) deferred at scope-lock
to W11.7+, gated on "image library has enough material to
be useful for recipes." Library has 3 images — probably not
enough yet. Realistic candidates:

1. **W11.6 polish / variety renders** — drive sd3-large or
   ultra models for quality comparison vs the cheap `core`
   model used today. Different style presets (cyberpunk /
   watercolor / ghibli) surface dramatically different
   aesthetics. ~$0.005-0.01 per render.
2. **F8.1 — K10 seed corpus** — still blocked on operator
   markdown.
3. **K6.4 v3 — embedding-similarity fallback** — still
   holds for a real paraphrase miss.
4. **K7.x — YouTube ingest fix** — silent-failure mode
   noted in MEMORY.
5. **K6.3 — Brief length cap** — likely moot now, ~15 min
   cleanup.
6. **K7.1 — Cost telemetry surface in SPA**.
7. **W11.x — surface `voice_patch.status` in edit modal**
   (calibration from SESSION 171).
8. **More cast variety renders** — test other voice
   presets beyond `marcus` / `clara` / `drew`.

Each candidate is ~30 min to ~1 session in scope. Operator
preference: pick at session start.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11; W11.1 + W11.2
+ W11.6 ship operator-facing edit + voice + re-bake +
workspace image library). Cast went live in real-mode
(SESSION 136). **First marketing video shipped against real
Runway** (SESSION 158). **First Stability images shipped to
operator workspace** (SESSION 173).

**Phase 4 (four arcs all complete; W11.6 sub-arc complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped.
- **Video composition arc (V0-V15). COMPLETE.**
- **Workspace fabric arc (F0-F10). COMPLETE.**
- **Realtime avatar arc (R0-R10). COMPLETE.**
- **Media generation sub-arc (W11.6.0-W11.6.4). COMPLETE.**

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE** (SESSIONS 142-157) |
| **First marketing video** | **DONE** (SESSION 158) |
| **Drift-prevention items 2+3** | **DONE** (SESSION 159; context-kit) |
| **K6.4 (claim verifier)** | **DONE (SESSION 160)** |
| **K6.4.1 (stoplist widen + strict forensics)** | **DONE (SESSION 161)** |
| **K6.5 (conversation verifier parity)** | **DONE (SESSION 162)** |
| **K6.4 v1.1 (SPA toggle + warning surface)** | **DONE (SESSION 163)** |
| **K6.4 v1.2 (verification_status + recipe rollout)** | **DONE (SESSION 164)** |
| **K6.4 stoplist watchdog** | **DONE (SESSION 165)** |
| **K6.4 v2 (semantic-match surgical fixes)** | **DONE (SESSION 166)** |
| **K6.4 v2.1 (real-Runway dogfood + CTA verbs)** | **DONE (SESSION 167)** |
| **K6.6 (script structure + opener + brief persist)** | **DONE (SESSION 168)** |
| **Marcus end-to-end + W11.1 edit modal** | **DONE (SESSION 169)** |
| **Portrait JWT refresh + hook-order fix** | **DONE (SESSION 169 close, commit `2cdcd26`)** |
| **W11.2 voice swap + avatar re-bake** | **DONE (SESSION 170)** |
| **W11.2 dogfood + Tier 1 visual_template fix** | **DONE (SESSION 171)** |
| **K6.6.1 system prompt leak fix** | **DONE (SESSION 171)** |
| **gpt-5 family migration (K6 / K9 / R6)** | **DONE (SESSION 171)** |
| **W11.3 — Stability port (reframed for W11.6)** | **DONE — Stability is non-avatar image gen (SESSION 171)** |
| **Mascot anthropomorphic auto-inject (Tier 1)** | **DONE (SESSION 171)** |
| **W11.6.0 — Media gen scope lock** | **DONE (SESSION 172)** |
| **W11.6.1 — Asset image fields + /internal/image_stability/** | **DONE (SESSION 173, commit `e7c565a`)** |
| **W11.6.2 — Django REST API /api/images/ + /api/styles/** | **DONE (SESSION 173, commit `708ba1f`)** |
| **W11.6.3 — SPA route + generation form + 5th nav item** | **DONE (SESSION 173, commit `ca6df3b`)** |
| **W11.6.4 — SPA library + detail modal + subject persistence** | **DONE (SESSION 173, commit `29a4824`)** |
| **W11.6 real-Stability dogfood (3 images in admin workspace)** | **DONE (SESSION 173)** |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| K7.x (YouTube ingest fix) | Queued |
| K6.3 / K7.1 | Queued |
| W11.6.5 (recipe inline image-picker) | Deferred to W11.7+ |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - **Sasha the Raccoon** (sales) — id `79d48883-...` — known-good real-render voice (`clara`)
  - Donny the Sloth (user stories) — id `f30b2980-...` — dental artifacts on `drew` voice; eligible for voice swap or re-bake
  - Maya the Panda (educator) — id `9410f23f-...` — untested in real-mode
  - **Marcus the Battle Unicorn** (AP history tutor) — id `b6a00dd8-...` — `marcus` voice; Nerva–Antonine doc attached; 2 verified strict-mode renders shipped

**Workspace image library** (new SESSION 173):

  - Scene 16:9 photorealistic — brewery owner at sunrise (`f46b94fc-...`)
  - Product 1:1 minimalist — hand-blown glass coffee mug (`f4d5f119-...`)
  - Broll 21:9 concept_art — rolling vineyard hills (`10d1b6b3-...`)

---

## Queued investigations (priority-ordered)

1. **W11.6 polish renders** — sd3-large / ultra quality
   comparison; style preset variety. ~$0.005-0.01 each.
2. **More real-Runway exposure on other recipes** —
   `talking_head_polished` Sasha retake;
   `long_form_ad` smoke. Real-Runway renders so far:
   **3 renders at $0.75** (SESSION 167 + 168 probes) +
   **2 renders at $0.50** (SESSION 169 Marcus end-to-end
   + dogfood loop) + **1 first marketing video at $0.50**
   (SESSION 158). Stability renders: **4 at ~$0.012**
   (SESSION 173 dogfood).
3. **K6.4 v3 — embedding-similarity fallback.** Holds
   until a real paraphrase miss surfaces in operator
   dogfood.
4. **Run the watchdog periodically.** `python manage.py
   stoplist_watchdog --days=14` weekly.
5. **Older backlog**: F8.1 (blocked on operator
   markdown), K7.x (YouTube ingest silent failure), K6.3
   (brief length cap — likely moot), K7.1 (cost
   telemetry surface).
6. **Voice preset audit** — smoke-test other voices
   beyond `marcus` / `clara` / `drew`. W11.2 makes this
   cheap (no re-bake required for preset swaps).
7. **E2e detritus cleanup.**
8. **OpenAI client factory port.**
9. **Cast sync command.**
10. **Stuck-row janitor.**
11. **Act-Two performance capture.**
12. **`lesson` video kind.**
13. **Real Google OAuth + dj-stripe.**
14. **Allauth legacy-settings cleanup.**
15. **smoke_voice / smoke_avatar transaction discipline.**
16. **INVENTORY working-tree-dirty flag fix.**
17. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000 — DO NOT pass --noreload

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**SESSION 174 stack-up note**: Celery worker was untouched
in SESSION 173 (W11.6 work doesn't fire Celery — all
synchronous Stability calls). If the worker has been
running continuously from SESSION 172's restart it's still
holding the gpt-5 family imports + prompt-composer
auto-inject + W11.6.0 scope-lock state. Restart only if
SESSION 174 touches K6 / K9 / R6 / R7.2 / render_video
flows.

**Session-end anchor re-stamp + calibration audit**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py \
    handoff write <NNN> --project .
```

**Six force-mocks** (RUNWAY on media-engine;
EMBEDDING + RENDER_SCRIPT + CONVERSATION_REPLY + SERPER
+ REALTIME_MEMORY on Django). With `RUNWAY_API_KEY` set
in `.env`, media-engine runs in real mode by default.
**Stability** runs in real mode whenever
`STABILITY_API_KEY` is set; no separate force-mock flag
yet (deferred — SESSION 173 calibration: tests need to
use `monkeypatch` on `app.services.stability_portrait.get_settings`
to avoid burning credits in CI).

Smoke checks (counts as of session close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 752 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 82 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 173 — W11.6 media generation
  arc (W11.6.1-W11.6.4).** 4 commits shipped; Stability
  AI now operator-facing via the `/images` route. ~$0.012
  in dogfood spend. 3 real images now live in the admin
  workspace library. Tests: SPA **53 → 82**; Django
  **727 → 752**; media-engine **111 → 133**.
- **Calibration carried forward (NEW SESSION 173)**:
  - **`lru_cached get_settings()` bypasses FastAPI
    `app.dependency_overrides`.** Service-direct call
    sites need `monkeypatch.setattr(
    "module.path.get_settings", lambda: fake)`, OR pass
    settings down from the endpoint. Don't trust the
    dependency override to flow through `lru_cache`'d
    accessors.
  - **Radix UI primitives need `userEvent.setup() +
    await user.click()` under jsdom.** `fireEvent.click`
    on TabsTrigger / DialogTrigger / etc. doesn't
    reliably flip the active state.
  - **Scope-lock reviews should distinguish operator
    input from LLM input** for any composition-step
    surface. Composed prompts can't round-trip as
    operator subjects (double-framing). Apply the lens
    proactively.
- **Calibration carried forward (from earlier sessions)**:
  - **Distinct request boundaries for distinct
    side-effects** — when an SPA save spans a DB write
    + an external-system call, model them as two
    requests, not one bundled PATCH.
  - **Mock-fetch should route-switch from day one**
    once a component hits more than one endpoint.
  - **Hook order across early returns** (SESSION 169) —
    pattern held; new state hooks live above the
    loading/error/not-found returns.
  - **AI's "shipped" framing belongs to the operator
    after review** for any model-output deliverable.
  - **Avatar voice × lip-sync quality is a real
    operational axis.** W11.2 makes the smoke-test loop
    cheap.
  - **R9 placeholder accurate to ~5x** — stub-and-refine
    validated.
  - **Drift verifiers belong as early scaffolding**
    (SESSION 157).
  - **Milestone-level doc refresh has its own cadence**
    (SESSION 156).
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Doctor is the drift tool** (SESSION 151). **Now
    paired with `handoff write` at session-end**
    (SESSION 159).
  - **OpenAI gpt-5 family uses the Responses API.**
  - **Backend write-guards are load-bearing.** Adding a
    test file that creates Asset rows requires an
    ALLOWED_FILES entry. The guard fires on first
    full-suite run.
- **Realtime + W-arc + W11.6 all closed.** Phase 4's four
  arcs + the W11.6 sub-arc all shipped.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
  **End-of-session `context-kit handoff write` runs
  alongside the handoff commit.**
