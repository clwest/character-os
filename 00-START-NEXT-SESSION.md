---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` is canonical for
> what we're building.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` is
> canonical for the Django↔FastAPI boundary. **Feature-complete after
> SESSION 110** — all three core verbs (avatars, voices, videos) live.
> **Last handoff:**
> `docs/handoffs/SESSION_110_VOICE_CLONE_ENDPOINT.md`.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django shell scaffold + monetization layer:** DONE.
**Phase 2 — Media-engine data model migration:** MOSTLY DONE.

What's working end-to-end after SESSION 110:

  - 25 REST endpoints under `/api/` covering Workspace / Membership /
    Spokesperson / Video / ConversationThread CRUD + custom actions
    (`/workspaces/{id}/members/`, `/spokespeople/{id}/clone-voice/`)
    + `/me/` + `/billing/*`.
  - Three `/internal/*` verbs on the media-engine, all live:
    - `POST /internal/avatars/` (SESSION 108) — synchronous.
    - `POST /internal/videos/` + `GET /internal/videos/{task_id}/`
      (SESSION 109) — fire-then-poll via Celery.
    - `POST /internal/voices/` (SESSION 110) — synchronous.
  - Celery + Redis foundation (broker db=0, results db=1 on
    Redis :6381).
  - Three hermetic smoke commands:
    - `python manage.py smoke_avatar` (~1 s in mock mode).
    - `python manage.py smoke_video` (~13 s in mock mode).
    - `python manage.py smoke_voice` (~1 s in mock mode).

---

## SESSION 111 — Phase 2 wrap or Phase 3 start

Phase 2's load-bearing work is done. The next session sits at a
decision point.

### Option 1 — Land `pyrightconfig.json` (recommended pre-work)

**Five sessions in a row** have flagged the same cross-stack
pyright noise: `apps.* could not be resolved`,
`GenericAPIView.get_queryset` "Never" return drift, unreachable
code warnings after `sys.exit`. None of it is real — runtime is
clean. But the warnings cost cognitive bandwidth on every session
("is this a new bug or the same noise?") and they'll only get
louder as Phase 3 lands more files.

Scope: ~10 minutes. Create `shell/pyrightconfig.json` with:
- `extraPaths` for `shell/` so cross-app imports resolve.
- `reportIncompatibleMethodOverride` set to a milder level
  (DRF's typing stubs are upstream noise).
- `reportUnreachable` toned down (post-`sys.exit` noise).

Worth doing **before** Phase 3 starts so the next operator can
trust new warnings.

### Option 2 — Start Phase 3 (SPA scaffolding)

The contract surface is feature-complete. Phase 3 begins with the
SPA: `web/` is already on the repo (currently empty/stub). Phase
3 plans live in `docs/design/UI_REDESIGN_V2.md` §8. Starting Phase
3 work means:

1. Decide the SPA framework + bundler (likely Vite + React + the
   shadcn/ui pattern documented in the design doc).
2. Land the auth flow — `allauth.headless` JSON signup/login (one
   of the queued investigations from SESSION 107).
3. Scaffold the first screen: Workspace dashboard listing
   spokespeople + videos.

This is **the big one**. Multi-session, multi-slice. Worth
locking the scope explicitly before any code lands.

### Option 3 — Operational hardening (stuck-row janitor)

The SESSION 109 known failure mode: a Celery worker dying mid-poll
leaves the Video row in `rendering` indefinitely. The fix is a
`celery beat`-scheduled task that re-enqueues
`poll_video_until_terminal` for every Video in `rendering` older
than ~5 minutes. ~30 lines of code + a beat schedule entry. Worth
landing before Phase 3 stress-tests the polling pipeline.

### Option 4 — Additional video kinds

SESSION 109 shipped `kind="spokesperson_ad"` only. The other three
(`cinematic_video`, `dialogue_scene`, `long_ad`) each need their own
slice. **Defer until the SPA actually renders them** — each one is
a small slice that doesn't reshape anything, easy to land on
demand once Phase 3 tells us which kind matters first.

### Recommendation: **Option 1 (pyrightconfig.json), then Option 2
(Phase 3 kickoff).**

Five sessions of accumulated noise is enough — 10 minutes now buys
quiet for the rest of Phase 3. After that, the operator picks the
Phase 3 first slice.

### Out of scope for SESSION 111

- All four media-engine integration paths are real-mode-untested.
  Mock mode is fine for development; switching to real Runway is
  an environment-and-credentials step, not a code change. Defer
  until the operator has Runway credits to burn on a smoke run.
- The campaigns-to-django migration script. Equally valid in any
  future session; not blocking.
- dj-stripe install, real Google OAuth, `allauth.headless`. All
  still queued; the first two block real billing / login, the
  third blocks Phase 3 SPA auth.

---

## Queued investigations (priority-ordered)

1. **`shell/pyrightconfig.json`** — overdue. Five sessions in a row
   have flagged the same cross-stack drift. 10-minute slice.
2. **`allauth.headless`** — JSON signup/login for the SPA. Lands
   when Phase 3 starts; bumping in priority because Phase 3 is
   imminent.
3. **Stuck-row janitor** — `celery beat` scheduled re-enqueue for
   rows in `rendering` older than ~5 min.
4. **Inventory generator** (`python manage.py inventory`) — emits
   runtime truth as JSON for `docs/CHARACTER_OS_INVENTORY.md`.
   This is becoming a real gap — five sessions worth of state are
   not represented in the runtime anchor.
5. **dj-stripe install** — when operator has Stripe credentials.
6. **Real Google OAuth** — when operator creates the OAuth client.
7. **Tag `v-final-pre-migration` on runway-hackathon** — operator
   decision. Nothing in SESSION 108-110 touched the legacy
   `/api/*` surface so the tag remains safe to apply.
8. **Numbered handoff gap** — `SESSION_053` still missing.
9. **Smoke-test helper consolidation** — three smoke commands now
   share an in-line stub-request pattern. Worth extracting a
   shared `apps/_testing/stub_request.py` helper if a fourth
   command lands.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# (new terminal)
cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

# (new terminal — only needed for video pipeline)
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo
```

Smoke checks after each change:

```bash
cd shell && source .venv/bin/activate
python manage.py smoke_avatar    # SESSION 108
python manage.py smoke_voice     # SESSION 110
python manage.py smoke_video     # SESSION 109 (needs Celery worker)
```

---

## AI / assistant context

- Last session: SESSION 110 — voice clone endpoint. Smallest slice
  in the Phase 2 run; the contract pattern is well-established
  enough that voice clone landed in under half the lines of
  SESSION 108-109.
- Calibration note carried forward (SESSION 109): this operator
  prefers right-shaping foundations early over deferring. Apply
  this when sizing Phase 3 work — don't try to ship a "minimal"
  SPA if the real one is one cleanup pass away.
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
- `docs/TRUST_CALIBRATION.md` still empty — the Celery decision
  (SESSION 109) is calibration-worthy; consider populating it
  next session before Phase 3 starts.
