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
> **Last handoff:** `docs/handoffs/SESSION_177_DRIFT_SWEEP_TITLE_DISAMBIG_K10_REFRAME.md`.

---

## SESSION 177 outcome — drift sweep + title disambiguation + K10 reframe

Three commits + one data-only fix. Short session that closed out
the loose ends from SESSION 176 plus two task-board items.

* **`f5f49e4`** — SESSION 177 boot drift sweep (commit-count
  typo across handoff/start-here/R-arc change log, narrative
  anchor staleness, gitignore for `.claude/scheduled_tasks.lock`).
* **`bdc6b6c`** — multi-step composition asset titles get
  per-step `— step N/M (<primitive>)` suffix.
* **`e1caee8`** — fix K10 FIRST THING menu paraphrase +
  TRUST_CALIBRATION entry on lossy menu drift from scope
  locks.

Plus task #13 (voice swap re-persist): no code change. Verified
the `change_voice` endpoint works end-to-end, fired it
programmatically against Sasha (vincent → felix) and Donny
(drew → vincent) — both DB + Runway now in sync. SESSION 175
handoff had overclaimed swap completion without verifying.

Tests: Django **816** (+2). SPA + media-engine unchanged.

**SESSION 177 pushed to `origin/main`** — 13 local commits
ahead at session-end (10 from SESSION 176 wrap-and-restamp +
3 from SESSION 177).

### Calibration moments worth carrying

* **Lossy paraphrase of scope locks in menu copy.** FIRST
  THING bullets that paraphrase slice work can drift from
  the scope lock; operator reads the menu not the scope lock
  in session-start decisions, so menu drift is load-bearing
  confusion. Pattern: cross-check FIRST THING wording against
  the slice's description in the relevant design lock doc.
* **SESSION 175 voice-swap handoff overclaimed.** Variant of
  the existing "AI's 'shipped' framing belongs to the operator
  after review" calibration: handoffs that say "swapped" or
  "edited" must reference a verifiable post-action state (DB
  query, not just intent). SESSION 177's roster check caught
  this 2 sessions later.

### Final state at session close

* SESSION 177 complete + pushed.
* Operator flagged a **branding / name change** for immediate
  attention before further build work. SESSION 178 opens on
  that conversation, not on the regular FIRST THING menu.
* Stack-up healthy. Celery worker pid 5625 (still holds the
  SESSION 176 `spokespeople.sync_personality_to_runway`
  registration).

### FIRST THING (SESSION 178): branding / name change

Hold any further build work until the operator's branding
decision is resolved. Likely scope:

1. **Naming change** — Character OS may rename. "24/7
   Global AI" surfaced in the email-signature card built
   SESSION 176 is one candidate. Scope of mechanical
   changes if the rename is a 1:1 swap: package names,
   repo name, README + design lock doc titles, SPA UI
   strings, INVENTORY frontmatter, handoff doc titles,
   wizard greetings, dashboard headings, conversation
   defaults, signature card. Bigger surgery if the
   product framing also changes.
2. **Domain / DNS** — new domain (if any) may affect CORS
   configs, public URLs, Runway / OpenAI rate-limit
   allowlists tied to referrer URLs, email signatures.
3. **Operator-facing copy** — full pass on user-visible
   strings.

After the branding decision is clear, return to the
queued backlog:

4. **F8.1 K10 seed corpus** — platform-shipped markdown
   about Character OS (or whatever the renamed product is)
   in `docs/seeds/<app>/*.md`, auto-ingested into every
   new `is_operator=True` workspace. 5-10 short files +
   `seed_workspace_knowledge` task wiring.
5. **R6 memory phrasing polish** — needs real-mode session
   quota (4/5 used; check status at session start).
6. **K6.4 v3 architectural fix** — generalize sentence-
   position-aware imperative-verb detection beyond
   stoplist curation. ~1 session.
7. **Thruman cleanup** — workspace has a stale "Thruman"
   spokesperson (voice=marcus) at `9410f23f-...` that
   may have shadowed Maya; verify + remove.

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
| **Multi-step composition title disambiguation** | **DONE** (SESSION 177) |
| **Sasha + Donny voice re-persist** | **DONE** (SESSION 177, data-only) |
| F8.1 (K10 seed corpus) | Queued (platform-authored markdown) |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued (amortization) |
| Branding / name change | **SESSION 178 FIRST THING** |
| W12 legacy form retirement | Queued |
| Thruman stale spokesperson cleanup | New (SESSION 177 surfaced) |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
  - **Sasha the Raccoon — id `79d48883-...` — voice `felix`**
    (re-persisted SESSION 177)
  - **Donny the Sloth — id `f30b2980-...` — voice `vincent`**
    (re-persisted SESSION 177)
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (note: workspace also has a "Thruman" with same UUID
    prefix and voice `marcus` — stale row, cleanup queued)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (W11.y personality + voice both confirmed
    Runway-side SESSION 176)

Marcus is the most dogfooded — 4 real-mode ENDED sessions +
1 successful render_video composition with a real CloudFront-
hosted MP4.

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

**SESSION 178 stack-up note**: Celery worker was last
restarted at SESSION 176 close (pid 5625, picked up
`spokespeople.sync_personality_to_runway`). If SESSION 178
touches `apps/spokespeople/` OR `apps/realtime/`
tasks / signals / models, restart again.

**Smoke checks** (counts as of session close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 816 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 177 — drift sweep + multi-step
  title disambiguation + K10 reframe.** Three commits + one
  data-only fix (Sasha + Donny voice re-persist). Tests:
  Django **816**; SPA **95**; media-engine **133**.

- **Calibration carried forward (NEW SESSION 177)**:
  - **FIRST THING menu drift from scope locks** — cross-
    check bullet wording against the slice's design lock
    description before writing the menu.
  - **Handoff "swapped/edited" claims need verification** —
    quote a post-action DB state, not intent.

- **Calibration carried forward (from earlier sessions)**:
  - **Runway DELETE poisons the conversation.** Don't use
    explicit DELETE for normal end.
  - **Mock-only test coverage hides upstream drift.** Tests
    that mock the wire never assert the wire.
  - **Operator framing unlocks AI blockers.**
  - **gpt-5 reasoning eats output budget silently** — 800+
    token ceiling for visible-text surfaces.
  - **Tool descriptions need narration scaffolding.**
  - **Real-mode dogfood after operator-facing slices.**
  - **Celery worker restart for any model-extending session.**
  - **SPA gates need both `pnpm test` AND `pnpm build`.**
  - **Distinct request boundaries for distinct side-effects.**
  - **Hook order across early returns** (SESSION 169).
  - **AI's "shipped" framing belongs to the operator after
    review.**
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
  SESSION 176 close. SESSION 177 closed out loose ends + 2
  task-board items. **Branding / name change is the next
  conversation** before further build.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
  **End-of-session `context-kit handoff write` runs
  alongside the handoff commit.**
