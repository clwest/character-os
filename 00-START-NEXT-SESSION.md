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
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5.1-3 COMPLETE.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_174_OPERATOR_FACING_POLISH.md`.

---

## SESSION 174 outcome — operator-facing polish

Ten commits across one long session driven by the SESSION 173
mid-session inventory. Three operator-facing gaps closed +
real-mode embedding dogfood that corrected the inventory +
uncovered two real bugs no unit test would have caught.

* **`3ecb6fe`** — W11.x voice telemetry: edit modal surfaces
  `voice_patch: {status, error}` (ok/skipped/failed). Holds
  open on failure.
* **`5f52bb7`** — K7.1 workspace cost telemetry: dashboard
  panel with per-surface MTD + all-time. Three-band dollar
  formatter.
* **`62353ce`** — real-mode embedding dogfood. Inventory
  correction: all 32 chunks already had real OpenAI vectors.
  3 new TRUST_CALIBRATION entries.
* **`e9256e5`** — K6.4 v2.1: sentence-opener verifier fixes.
  "Today" + "Think Antoninus" no longer false-positive flagged.
* **`e4d5761`** — K7.x: YouTube + boilerplate URL rejection.
  Polluted YouTube doc deleted from admin workspace.
* **`8e0185b`** — W11.6.5: cinematic_visual recipe image-
  picker. Closes the W11.6 arc.
* **`cf8bb69`** — W11.6.5.1: Asset.title for picker labels.
  Image-only fix initially.
* **`40efbcf`** — W11.6.5.2: lift prompt_image max_length
  to 10 MB (real dogfood found 2048-char URL cap rejected
  4.5 MB data URI). Two bugs caught + fixed.
* **`a233d10`** — W11.6.5.3: runtime auto-titles output
  assets from composition.name. Backfilled 26 clip rows.

Plus the SESSION 173 close commit (`1271c77`) carried over.

Tests: Django **727 → 782** (+55). Media-engine **133**
unchanged. SPA vitest **53 → 91** (+38). Migrations 53 → 54.

Real-mode spend: ~$0.55 total (~$0.30 OpenAI for K6 brief
dogfoods + $0.25 Runway for one successful cinematic_visual
image-to-video render).

### Calibration moments worth carrying

Four new TRUST_CALIBRATION entries appended this session:

1. **W11.6.5.1 narrow-fix rationalisation** — said "clips
   somewhat readable" without looking; operator found
   backdrop_composite picker unusable in 15 min. Don't
   rationalise; look at what the operator-facing surface
   ACTUALLY renders.
2. **W11.6.5.2 cap-too-tight** — 2048-char cap caught only
   by real dogfood. When a slice adds a NEW input shape to
   an existing field, audit ALL downstream size guards.
3. **Stale Celery worker rule was too narrow** — SESSION 173
   close said "restart only for K6/R6/render flows." That
   missed `execute_composition`. ANY model-extending session
   needs a worker restart.
4. **Real-mode dogfood after every operator-facing slice**
   (AI right preemptive). Saved as memory entry
   `feedback_real_mode_dogfood_after_operator_slices.md`
   so the lane carries across sessions.

### Final state at session close

* All Phase 4 arcs + W11.6 sub-arc complete + the W11.x
  polish surfaces (voice telemetry, cost telemetry) live.
* Cast roster unchanged (Riggs / Sasha / Donny / Maya /
  Marcus).
* Admin workspace: 30 compositions (27 completed, 3 failed
  — the failures were the two W11.6.5.2 pre-fix dogfood
  attempts), 27 clip assets (all titled via W11.6.5.3
  backfill), 3 image assets (all titled via W11.6.5.1
  backfill), 2 knowledge docs (YouTube-polluted doc
  deleted in `e4d5761`), 31 chunks.
* Stack-up healthy at session close. Celery worker
  restarted TWICE this session (W11.6.5.2 + W11.6.5.3);
  current worker pid 27171 holds the W11.6.5.3 runtime.

### FIRST THING (SESSION 175): pick by mood

1. **Multi-step composition title disambiguation** — v1
   leaves the same title across all step outputs in a
   long_form_ad / storyboard_voiced composition. Operator
   picking from 3 hook/action/payoff clips will see the
   same label thrice. ~30 min surgical fix.
2. **W11.x voice swap dogfood at scale** — SESSION 171
   shipped voice swap, SESSION 174 added the telemetry.
   Real operator-driven swap on Marcus (clara → roman →
   marcus) with banner observation. ~$0.05, ~5 min.
3. **Cost panel polish** — credit-vs-dollar mode toggle
   (Stability credits ↔ dollars), per-day chart, per-
   recipe breakdown. ~1 session.
4. **K6.6 multi-cast dogfood** — second-render for Donny /
   Maya to verify gpt-5 family migration + verifier fixes
   land cleanly across multiple subjects. ~$0.50 spend.
5. **YouTube transcript extractor (K7.x v2)** — proper
   per-host extractor (youtube-transcript-api or oEmbed)
   instead of the W11.6.x reject-with-error stopgap.
   ~1 session.
6. **F8.1 — K10 seed corpus** — still blocked on
   operator-authored markdown.
7. **TRANSCRIPT + VOICE asset titles** — covered by the
   W11.6.5.3 runtime change but these don't surface in
   recipe pickers today. Worth verifying when they do.

Operator preference: pick at session start.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11; W11.1 + W11.2 +
W11.6 + W11.x voice telemetry ship the full operator-facing
spokesperson + image edit surfaces).
**Phase 4:** All four arcs (K / V / F / R) complete. W11.6
sub-arc + W11.6.5 image-picker complete.

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE** (SESSIONS 142-157) |
| **First marketing video** | **DONE** (SESSION 158) |
| **W11.2 voice swap + avatar re-bake** | **DONE** (SESSION 170) |
| **W11.6.0-W11.6.4 (media gen arc)** | **DONE** (SESSIONS 172-173) |
| **W11.x voice telemetry** | **DONE (SESSION 174, `3ecb6fe`)** |
| **K7.1 cost telemetry** | **DONE (SESSION 174, `5f52bb7`)** |
| **K6.4 v2.1 sentence-opener fixes** | **DONE (SESSION 174, `e9256e5`)** |
| **K7.x YouTube reject** | **DONE (SESSION 174, `e4d5761`)** |
| **W11.6.5 recipe image-picker** | **DONE (SESSION 174, `8e0185b`)** |
| **W11.6.5.1-3 picker labels** | **DONE (SESSION 174, `cf8bb69` / `40efbcf` / `a233d10`)** |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| K7.x v2 YouTube extractor | Queued |
| Multi-step title disambiguation | Queued (small fix) |
| W12 legacy form retirement | Queued |

**Cast roster in workspace `admins-workspace`** (unchanged):

  - Riggs the Donkey — id `06bf999f-...`
  - **Sasha the Raccoon** — id `79d48883-...` — voice `clara`
  - Donny the Sloth — id `f30b2980-...` — dental artifacts on `drew`
  - Maya the Panda — id `9410f23f-...` — untested in real-mode
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice `marcus`

**Workspace image library** (3 images, all titled via
W11.6.5.1):

  - "rolling vineyard hills at golden hour, cinematic depth of…"
  - "a single hand-blown glass coffee mug on a wooden table…"
  - "a small craft brewery owner tapping a fresh keg at…"

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

**SESSION 175 stack-up note**: Celery worker was restarted
TWICE in SESSION 174 (once for W11.6.5.2 / model fields,
once for W11.6.5.3 / tasks.py). Fresh worker holds the
W11.6.5.3 runtime. If SESSION 175 touches
`apps/compositions/` models OR `tasks.py` OR any primitive
in `apps/compositions/primitives/`, **restart the worker
again** — the SESSION 174 carry-forward TRUST_CALIBRATION
generalises the rule: ANY model-extending session needs a
worker restart, not just LLM flows.

**Smoke checks** (counts as of session close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 782 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 91 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 174 — operator-facing polish.**
  Ten commits closing 3 backlog gaps + dogfood-driven W11.6.5
  three-slice mini-arc. Real-mode embedding dogfood corrected
  the SESSION 173 inventory + caught real bugs unit tests
  missed. Test counts: Django **782**; SPA **91**;
  media-engine **133**.

- **Calibration carried forward (NEW SESSION 174)**:
  - **Real-mode dogfood after operator-facing slices.**
    Mock-mode tests miss real-world shape mismatches
    (max_length, data-URI size, stale worker imports).
    The operator's "dog food it and I will look at the
    results on the UI" pattern from SESSION 173 became
    the SESSION 174 default. Saved as memory entry
    `feedback_real_mode_dogfood_after_operator_slices.md`.
  - **Stale Celery worker rule is broader than LLM flows.**
    ANY model-extending session needs a worker restart.
    Specifically: migrations applied OR
    `apps/compositions/tasks.py` changed OR any primitive
    in `apps/compositions/primitives/` changed OR any
    model the worker creates rows for added/removed fields.
  - **When a slice adds a NEW input shape to an existing
    field, audit ALL downstream max_length / size guards.**
    grep field name across Django + media-engine; check
    every Pydantic Field constraint that mentions it.
  - **Don't rationalise "somewhat readable" — look at what
    the operator-facing surface ACTUALLY renders for every
    case being deferred.** Especially picker / dropdown
    surfaces where one shape (image data URI, clip CDN
    URL with JWT) can render as garbage even if another
    shape (file path) is fine.
  - **Read runtime FIRST when assessing capability.**
    INVENTORY exists for this reason. A 5-line shell query
    beats docs + grep for "what can we do today?" questions.
  - **SPA gates need both `pnpm test` AND `pnpm build`.**
    vitest's esbuild skips full TS check; tsc -b in build
    catches subtle issues like `unknown error prop as
    ReactNode` and `props.X ?? vi.fn()` Mock-type unions.

- **Calibration carried forward (from earlier sessions)**:
  - **Distinct request boundaries for distinct
    side-effects** — when an SPA save spans a DB write
    + an external-system call, model them as two
    requests, not one bundled PATCH.
  - **Mock-fetch should route-switch from day one**
    once a component hits more than one endpoint.
  - **Hook order across early returns** (SESSION 169).
  - **AI's "shipped" framing belongs to the operator
    after review.**
  - **Avatar voice × lip-sync quality is a real
    operational axis.**
  - **R9 placeholder accurate to ~5x** — stub-and-refine
    validated.
  - **Drift verifiers belong as early scaffolding.**
  - **Milestone-level doc refresh has its own cadence.**
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Doctor is the drift tool** (SESSION 151). **Now
    paired with `handoff write` at session-end**
    (SESSION 159).
  - **OpenAI gpt-5 family uses the Responses API.**
  - **Backend write-guards are load-bearing.**
  - **lru_cached `get_settings()` bypasses FastAPI
    `app.dependency_overrides`.** Use monkeypatch on the
    module-level reference or pass settings down from the
    endpoint.
  - **Radix UI primitives need `userEvent.setup() + await
    user.click()` under jsdom.**
  - **Scope-lock reviews should distinguish operator input
    from LLM input** for composition-step surfaces.

- **Realtime + W-arc + W11.6 + W11.6.5 all closed.** All
  arcs are now in operator-facing polish + dogfood phase.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
  **End-of-session `context-kit handoff write` runs
  alongside the handoff commit.**
