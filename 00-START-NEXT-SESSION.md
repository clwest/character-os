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
> **Last handoff:** `docs/handoffs/SESSION_175_VOICE_TELEMETRY_YOUTUBE_PERSONALITY.md`.

---

## SESSION 175 outcome — voice telemetry follow-up + YouTube extractor + personality split

Five feature commits. Two natural dogfood-driven fixes
following from SESSION 174's voice-telemetry slice. One
full arc-close on K7.x YouTube ingest. One operator-
insight slice — the personality / business_brief split.

* **`edff9f2`** — W11.x.1 voice swap never auto-closes.
  SESSION 174 dogfood found banners unmounting in the
  same React tick they rendered.
* **`1577ce4`** — K6.4 v2.2 sentence-opener stoplist
  expansion. Donny K6 dogfood "Respect HTML" false-
  positive closed; 17 new verb families added.
* **`6f9d5b4`** — K7.x v2 proper YouTube transcript
  extractor. Replaces v1's rejection with actual
  ingestion via youtube-transcript-api.
* **`0b56bd9`** — W11.x.2 voice preview surface in
  wizard. Operators hear cloned voice before committing
  via inline audio player.
* **`47f5166`** — W11.y personality / business_brief
  split. Independently swappable HOW (personality) vs
  WHAT (business_brief) across model + K6 + K6.5 +
  Runway avatar + R-arc realtime document + wizard +
  edit modal.

Tests: Django **782 → 814** (+32). Media-engine **133**
unchanged. SPA vitest **91 → 95** (+4). Migrations 54 → 55.

Real-mode spend this session: ~$0.06 OpenAI (K6.6
multi-cast dogfood). $0 Runway / $0 Stability.

### Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended:

1. **Vitest atomic assertions mask render → unmount flashes.**
   When `setVoicePatch` + `onClose()` fire in the same
   React tick, jsdom asserts both ends true. Human eye
   sees only the second. Pattern: any "X exists AND
   onClose called" assertion without a timing gate is
   suspect.
2. **Source greps don't match operator UI text → suspect
   stale browser first.** Hard refresh (Cmd+Shift+R) is
   the first move, not an afterthought. SPA bundle
   freshness via `pnpm build` for Django :8000 path; HMR
   usually for Vite :5174 but glitches.
3. **K6.4 stoplist curation trickle suggests v3.** v2 +
   v2.1 + v2.2 cumulatively added ~58 verbs. Each K6
   dogfood surfaces 1-2 more. v3 (sentence-position-aware
   imperative-verb detection beyond stoplist) amortizes
   the maintenance.

### Final state at session close

* **W11.y backfill verified**: all 5 cast spokespeople in
  Admin's workspace have personality populated identically
  to business_brief. K6 + Runway produce same output until
  operator splits.
* **Cast voice swaps from dogfood**: Marcus → `david`,
  Sasha → `felix`, Donny → `vincent`. Maya + Riggs
  unchanged.
* **Maya knowledge attachment**: trafilatura test doc
  attached for K6.6 dogfood. Operator may detach if not
  intended for Maya's use case.
* Stack-up healthy. Celery worker restarted once
  (W11.y, pid 74011).

### FIRST THING (SESSION 176): pick by mood

1. **W11.y operator dogfood** — edit Marcus's modal, split
   his backfilled personality from business_brief, re-fire
   K6. ~$0.05, ~10 min. **High-value** first move because
   it validates W11.y against real operator content.
2. **Voice preview dogfood** — W11.x.2 ships but the
   preview-after-clone flow hasn't been operator-driven
   yet. Requires upload/record path. ~$0.05.
3. **Cost panel polish** — credit ↔ dollar mode toggle
   for Stability, per-day chart, per-recipe breakdown.
   ~1 session.
4. **K6.4 v3 architectural fix** — generalize sentence-
   position-aware imperative-verb detection beyond
   stoplist curation. ~1 session. Amortizes the trickle.
5. **K7.x v3 YouTube oEmbed** — populate doc title with
   real video title instead of "YouTube · {video_id}"
   placeholder. ~30 min.
6. **Multi-step composition title disambiguation** —
   ~30 min surgical fix.
7. **F8.1 K10 seed corpus** — blocked on operator markdown.
8. **TRANSCRIPT + VOICE asset titles** — verify W11.6.5.3
   covers all asset types. ~15 min.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete. Operator-facing edit
surfaces include voice swap, rebake, voice telemetry,
voice preview, personality split.
**Phase 4:** All four arcs (K / V / F / R) complete.
W11.6 sub-arc complete. K7.x v2 extractor complete.

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE** (SESSIONS 142-157) |
| **W11.6.0-W11.6.5 (media gen arc)** | **DONE** (SESSIONS 172-173) |
| **W11.x voice telemetry** | **DONE** (SESSION 174 + 175 fix) |
| **W11.x.2 voice preview surface** | **DONE** (SESSION 175, `0b56bd9`) |
| **W11.y personality split** | **DONE** (SESSION 175, `47f5166`) |
| **K7.1 cost telemetry** | **DONE** (SESSION 174) |
| **K6.4 v2.2 stoplist** | **DONE** (SESSION 175, `1577ce4`) |
| **K7.x v2 YouTube extractor** | **DONE** (SESSION 175, `6f9d5b4`) |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued (amortization) |
| Multi-step title disambiguation | Queued (small fix) |
| W12 legacy form retirement | Queued |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
  - **Sasha the Raccoon** — id `79d48883-...` — voice `felix` (swapped SESSION 175 dogfood)
  - Donny the Sloth — id `f30b2980-...` — voice `vincent` (swapped SESSION 175)
  - Maya the Panda — id `9410f23f-...` — voice `victoria` (trafilatura doc attached for K6.6 dogfood)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice `david` (swapped SESSION 175)

All 5 cast members have `personality` populated identically
to `business_brief` post-W11.y backfill. Operator splits
per-spokesperson over time.

**Workspace image library** (3 images, all titled):

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
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**SESSION 176 stack-up note**: Celery worker was restarted
once in SESSION 175 (W11.y model change, pid 74011 at
session-close). If SESSION 176 touches
`apps/spokespeople/` models OR `apps/compositions/`
models / tasks / primitives, restart again. **ANY
model-extending session needs a worker restart** —
SESSION 174 carry-forward, reinforced in 175.

**Smoke checks** (counts as of session close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 814 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 175 — voice telemetry follow-up
  + YouTube extractor + personality split.** Five
  feature commits across dogfood-driven UX fixes (W11.x.1,
  K6.4 v2.2) + a long-queued backlog arc-close (K7.x v2)
  + an operator-insight slice (W11.y). Tests: Django
  **814**; SPA **95**; media-engine **133**.

- **Calibration carried forward (NEW SESSION 175)**:
  - **Vitest atomic assertions can mask real UX bugs.**
    Render → unmount in one React tick passes jsdom but
    invisible to humans. Pattern to watch: "X exists AND
    onClose called" without a timing gate.
  - **Stale browser before stale code.** When source
    greps don't match operator UI text, hard refresh
    first. Save 5-10 min of source-spelunking.
  - **K6.4 stoplist curation trickle.** Every K6 dogfood
    surfaces 1-2 new verb gaps. v3 architectural fix
    amortizes the maintenance.

- **Calibration carried forward (from earlier sessions)**:
  - **Real-mode dogfood after operator-facing slices.**
    Mock-mode tests miss real-world shape mismatches.
    Saved as memory entry
    `feedback_real_mode_dogfood_after_operator_slices.md`.
  - **Celery worker restart for any model-extending
    session.** Not just LLM flows.
  - **SPA gates need both `pnpm test` AND `pnpm build`.**
    vitest's esbuild skips full TS check.
  - **Distinct request boundaries for distinct
    side-effects.**
  - **Hook order across early returns** (SESSION 169).
  - **AI's "shipped" framing belongs to the operator
    after review.**
  - **Doctor is the drift tool** + **handoff write at
    session-end.**
  - **OpenAI gpt-5 family uses the Responses API.**
  - **lru_cached `get_settings()` bypasses FastAPI
    dependency_overrides.**
  - **Radix UI primitives need `userEvent` under jsdom.**
  - **Scope-lock reviews should distinguish operator
    input from LLM input.**
  - **Don't rationalise "somewhat readable" — look at
    what the operator-facing surface actually renders.**

- **All Phase 4 arcs + W11.6 sub-arc + voice telemetry
  + personality split all live.** Platform is in
  operator-facing polish + dogfood-driven refinement
  phase.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
  **End-of-session `context-kit handoff write` runs
  alongside the handoff commit.**
