---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` is canonical for
> what we're building.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` is
> canonical for Phase 2's Django↔FastAPI boundary.
> **Last handoff:**
> `docs/handoffs/SESSION_109_VIDEO_PIPELINE_CELERY_REDIS.md` — fire-
> then-poll video pipeline complete + Celery/Redis foundation pulled
> in early.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django shell scaffold + monetization layer:** DONE.
**Phase 2 — Media-engine data model migration:** IN PROGRESS.

What's working end-to-end after SESSION 109:

  - Everything from SESSION 107 + 108 (24 REST endpoints, signup →
    workspace → tier-gated CRUD, `POST /internal/avatars/`,
    `MediaEngineClient.create_avatar`).
  - Fire-then-poll video pipeline:
    - `POST /api/videos/` returns 201 immediately with
      `status=rendering` + `media_engine_task_id`.
    - Celery worker polls `GET /internal/videos/{task_id}/` on a
      2 s loop with a 10-min deadline, writes terminal state to
      the row.
    - SPA can poll `GET /api/videos/{id}/` for live status.
  - Celery + Redis foundation:
    - Redis runs in Docker on `:6381` (`infra/docker-compose.yml`).
    - Broker (`db=0`) + result backend (`db=1`).
    - `apps.videos.tasks.poll_video_until_terminal` is the first
      consumer; autodiscovery picks up future `apps/*/tasks.py`.
  - `python manage.py smoke_video` — end-to-end test, passes in
    ~13 s against mock-mode media-engine.

---

## SESSION 110 — Phase 2 continuation

Three natural next slices. Operator picks first; all three are
single-session-sized.

### Slice A — `POST /internal/voices/` (recommended)

The remaining major `/internal/*` verb. Voice cloning is needed
for the Pro / Agency tiers (the Starter happy path uses the
Runway voice preset that ships with each avatar). Shape mirrors
the avatar slice closely:

- Request: `{audio_data_uri: "data:audio/wav;base64,...", name}`.
- Response: `{voice_id, status: "ready" | "mock", mock_mode}`.
- Inline / synchronous (Runway's voice clone returns in <10 s
  even in real mode — no Celery needed).
- Wraps the existing `voice_clone_client.clone_voice_from_audio`
  service so behaviour matches the legacy
  `POST /api/characters/{id}/clone-voice` route.

Django-side: a new `POST /api/spokespeople/{id}/clone-voice/`
action endpoint that takes the audio data URI, calls the media-
engine, and persists `voice_id` onto the Spokesperson.

### Slice B — Additional video kinds

SESSION 109 shipped `kind="spokesperson_ad"` only. Three remain:

- `cinematic_video` — text-to-video without an avatar (gen4.5
  text-only path). Simplest of the three.
- `dialogue_scene` — two avatars + a script. Needs a second avatar
  field in the contract.
- `long_ad` — multi-scene composition. Heaviest; wraps
  `long_ad_service` on the media-engine side.

Each kind is a separate slice; don't try to land all three in one
session. Cinematic is the obvious first because it doesn't change
the contract shape.

### Slice C — Stuck-row janitor

The SESSION 109 known failure mode: a Celery worker dies mid-poll
and the Video row stays in `rendering` indefinitely. The fix is a
`celery beat`-scheduled task that re-enqueues
`poll_video_until_terminal` for every Video in `rendering` older
than ~5 minutes. Small slice — ~30 lines of code + a beat
schedule entry. Worth landing soon because it removes the only
operational footgun on the current pipeline.

### Recommendation: **Slice A (voice clone)**.

Reasoning: it closes the last major `/internal/*` verb, which
makes the contract feature-complete enough to begin Phase 3 (SPA
work) without further backend changes. Slice B is more frontend-
shaped work that can defer until the SPA is rendering videos.
Slice C is an operational hardening that defers nicely until
production traffic creates the actual stuck-row pressure.

### Out of scope for SESSION 110

- Real Runway calls. Mock mode is still the right path until the
  SPA + auth + the contract are all stable.
- Frontend / SPA work (Phase 3).
- The campaigns-to-django migration script.
- `celery beat` (defer with Slice C).

---

## Queued investigations (not blocking SESSION 110)

- **`shell/pyrightconfig.json`** — silences the cross-app import +
  `GenericAPIView.get_queryset` "Never" return warnings. Three
  sessions in a row have flagged this; please land it soon. 2-line
  slice.
- **Inventory generator** (`python manage.py inventory`) — emits
  runtime truth as JSON for `docs/CHARACTER_OS_INVENTORY.md`.
- **dj-stripe install** — when operator has Stripe credentials.
- **Real Google OAuth** — when operator creates the OAuth client.
- **`allauth.headless`** — JSON signup/login for the SPA. Defer
  until Phase 3 starts.
- **Tag `v-final-pre-migration` on runway-hackathon** (Q6 of design
  doc). Operator decision; nothing in SESSION 108-109 touched the
  legacy `/api/*` surface so the tag remains safe to apply.
- **Numbered handoff gap** — `SESSION_053` still missing. Drop a
  placeholder when convenient to silence the orient warning.
- **Stuck-row janitor** (Slice C above) — operational hardening
  for the Celery polling pattern.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# (new terminal)
cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

# (new terminal)
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo
```

Smoke check after each change:

```bash
cd shell && source .venv/bin/activate
python manage.py smoke_avatar   # SESSION 108 path
python manage.py smoke_video    # SESSION 109 path
```

---

## AI / assistant context

- Last session: SESSION 109 — fire-then-poll video pipeline + Celery/
  Redis foundation. Operator opted in to Celery early, ahead of the
  Phase 4 plan, after a quick tradeoff discussion.
- Calibration note (worth remembering): this operator prefers
  right-shaping foundations early over deferring. When the option
  is "smallest thing now" vs. "real thing now", lean toward the
  real thing if it'll merge as the project grows.
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
- `docs/TRUST_CALIBRATION.md` still empty — the Celery decision
  is calibration-worthy; consider populating it next session.
