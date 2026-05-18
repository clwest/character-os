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
> **Last handoff:** `docs/handoffs/SESSION_176_R_ARC_REAL_MODE_HARDENING.md`.

---

## SESSION 176 outcome — R-arc real-mode hardening

Eight feature commits. The R-arc shipped 10 slices + R6.1 across
SESSIONS 142-157 with full mock-mode test coverage — today
proved every realtime surface real-mode against live Runway for
the first time. Found and fixed five distinct root causes that
hid behind the mock-only test pattern.

* **`d57013b`** — realtime end-to-end (4-layer initial fix:
  missing client method + Runway payload drift + SDK video
  render + DRAFT/FAILED quota leak).
* **`59bfd3d`** — K6/K9 catchphrase guard + bump
  `MAX_OUTPUT_TOKENS` 400 → 1000.
* **`70500b9`** — R5 transcript fix (parse drift + failed-status
  surfacing + webcam-request removed).
* **`a0b1843`** — R5 root cause: stop DELETE-ing Runway sessions
  on End (proven by operator's "maybe End button itself is
  causing it" framing → 3 hours of false leads collapsed).
* **`1b375fd`** — broker passes workspace tool catalog.
* **`c5cc648`** — R7 polish: narration-rich tool descriptions +
  session-create personality override.
* **`ec137e5`** — personality auto-sync to Runway via post_save
  signal + Celery task + SPA recall results panels.
* **`06351d7`** — IdlePanel polish (headphones tip + voice pill)
  + `/signature` route.

Tests: Django **814**, realtime suite **164** (+14). SPA vitest
**95** unchanged. Media-engine **133** unchanged. Real-mode
spend: ~$0.74 Runway + ~$0.03 OpenAI. Starter tier ended 4/5
sessions, 11/30 minutes.

### Real-mode artifacts created today

* 4+ `RealtimeSession` rows for Marcus (status: ended)
* 4+ `Asset(TRANSCRIPT)` rows (first project transcripts)
* 1 `Composition` `757eefda-...` (talking_head, completed)
* 1 `Asset(clip)` `61846ee2-...` — real CloudFront-hosted MP4
  of Marcus speaking his own composed script about why
  studying Rome matters today, rendered through the realtime
  `render_video` tool with operator approval

### Calibration moments worth carrying

Five new TRUST_CALIBRATION entries appended:

1. **Runway DELETE on /v1/realtime_sessions cancels the
   conversation** — DELETE poisons the linked
   /v1/avatar_conversations to `failed`. Natural WebRTC
   disconnect is the correct end signal.
2. **Mock-only test coverage hides real-mode contract drift.**
   Tests that mock the upstream wire never assert the upstream
   wire.
3. **Operator framing unlocks blockers AI alone misses.**
   "Maybe the End button itself is causing it" broke 3 hours
   of false leads in one test.
4. **gpt-5 reasoning silently eats output budget.** Need
   800-1000 token ceiling for visible-text surfaces.
5. **Tool descriptions need narration guidance, not just
   trigger conditions.** SAY ALOUD pattern + "keep the
   conversation going" rules keep the avatar from going
   silent around invocations.

### Final state at session close

* **R-arc real-mode validated end-to-end** — R5 transcripts
  + R6 cross-session memory + R7 tool dispatch (sync + async
  with approval) + R7 → V pipeline (render_video produces
  real Composition + Asset).
* **W11.y propagation complete** — Spokesperson.personality
  edits now auto-sync to Runway's avatar resource via Celery
  signal. Local DB + Runway-side stay in sync without operator
  intervention.
* **All 12 SESSION 176 task items completed.**
* Stack-up healthy. Celery worker last restarted at session-end
  (pid 5625, picked up `spokespeople.sync_personality_to_runway`).

### FIRST THING (SESSION 177): pick by mood

1. **F8.1 K10 seed corpus** — draft one piece of seed content,
   then K1-K7 ingest flow exercises against real operator
   knowledge instead of test fixtures. **High value** because
   it grounds K-arc + R-arc dogfood in operator-authored
   content.
2. **Sasha + Donny voice swap re-investigation** — SESSION 175
   swaps didn't persist on either spokesperson. ~30 min.
3. **R6 memory phrasing polish** — compare composition prompt
   output across 2-3 dogfood sessions for thread-pickup
   consistency.
4. **K6.4 v3 architectural fix** — generalize sentence-position-
   aware imperative-verb detection beyond stoplist curation.
   Amortizes the v2.x trickle. ~1 session.
5. **Multi-step composition title disambiguation** — small
   surgical fix from SESSION 175 backlog. ~30 min.
6. **Tool description iteration** — once 2-3 more real-mode
   sessions happen, calibrate SAY ALOUD lines to operator
   preference.
7. **Push to remote** — 9 commits ahead of `origin/main`;
   only with explicit operator approval.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete. Operator-facing edit
surfaces include voice swap, rebake, voice telemetry,
voice preview, personality split.
**Phase 4:** All four arcs (K / V / F / R) complete AND
real-mode validated end-to-end (R-arc proven SESSION 176).
W11.6 sub-arc complete. K7.x v2 extractor complete.

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE + REAL-MODE VALIDATED (SESSION 176)** |
| **W11.6.0-W11.6.5 (media gen arc)** | **DONE** (SESSIONS 172-173) |
| **W11.x voice telemetry** | **DONE** (SESSION 174 + 175 fix) |
| **W11.x.2 voice preview surface** | **DONE** (SESSION 175) |
| **W11.y personality split** | **DONE** (SESSION 175 + Runway-sync SESSION 176) |
| **K7.1 cost telemetry** | **DONE** (SESSION 174) |
| **K6.4 v2.2 stoplist** | **DONE** (SESSION 175) |
| **K7.x v2 YouTube extractor** | **DONE** (SESSION 175) |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued (amortization) |
| Sasha + Donny voice swap re-persist | New (from SESSION 176) |
| Multi-step title disambiguation | Queued (small fix) |
| W12 legacy form retirement | Queued |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
  - Sasha the Raccoon — id `79d48883-...` — voice `vincent`
    (SESSION 175 swap to `felix` did NOT persist; see backlog)
  - Donny the Sloth — id `f30b2980-...` — voice `drew`
    (SESSION 175 swap to `vincent` did NOT persist; see backlog)
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (W11.y personality + voice both confirmed Runway-side
    SESSION 176)

Marcus is the most dogfooded member of the cast — 4 real-mode
ENDED sessions + 1 successful render_video composition with a
real CloudFront-hosted MP4 today.

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

**SESSION 177 stack-up note**: Celery worker was restarted
at SESSION 176 close (pid 5625, picked up
`spokespeople.sync_personality_to_runway`). If SESSION 177
touches `apps/spokespeople/` OR `apps/realtime/`
tasks / signals / models, restart again.

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

- **Last session: SESSION 176 — R-arc real-mode hardening +
  W11.y propagation.** Eight feature commits proved every
  realtime surface real-mode against live Runway for the
  first time. Operator-clicked End now produces a transcript;
  cross-session memory injects properly; tools fire with
  narration; render_video → V-arc pipeline executes
  end-to-end. Personality edits auto-propagate to Runway.
  Tests: Django **814**; SPA **95**; media-engine **133**.

- **Calibration carried forward (NEW SESSION 176)**:
  - **Runway DELETE poisons the conversation.** Don't use
    explicit DELETE for normal end — let SDK / WebRTC
    disconnect handle it.
  - **Mock-only test coverage hides upstream drift.** Tests
    that mock the wire never assert the wire.
  - **Operator framing unlocks AI blockers.** When the AI
    burns iterations on increasingly specific theories,
    operator's plain-language reframing is the broader
    hypothesis worth testing first.
  - **gpt-5 reasoning eats output budget silently.** Set
    800-1000 token ceilings for visible-text surfaces.
  - **Tool descriptions need narration scaffolding.** SAY
    ALOUD + keep-the-conversation-going rules required.

- **Calibration carried forward (from earlier sessions)**:
  - **Real-mode dogfood after operator-facing slices.**
    Reinforced SESSION 176 — mock-only R-arc coverage
    masked 5 distinct real-mode root causes.
  - **Celery worker restart for any model-extending
    session.** SESSION 176 added `spokespeople` task module
    + signal; worker restarted at close.
  - **SPA gates need both `pnpm test` AND `pnpm build`.**
  - **Distinct request boundaries for distinct side-effects.**
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
  - **Vitest atomic assertions can mask real UX bugs.**
  - **Stale browser before stale code.**
  - **K6.4 stoplist curation trickle** suggests v3
    architectural fix.

- **All Phase 4 arcs real-mode validated end-to-end** as of
  SESSION 176 close. R-arc + W11.6 + voice telemetry +
  personality split + Runway sync all live and operator-
  exercised. Platform is in operator-facing polish +
  real-world content dogfood phase.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
  **End-of-session `context-kit handoff write` runs
  alongside the handoff commit.**
