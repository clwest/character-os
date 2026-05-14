---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_121_MAKE_A_VIDEO_FLOW.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3 — Build new UI:** **The core lifecycle is closed end-
to-end.** Signup → create spokesperson → detail → make video →
poll → playback all works in the SPA against the real backend.

| Slice | Screens                              | Status |
|-------|--------------------------------------|--------|
| 1     | Sign-up + sign-in (S-03 + S-04)      | DONE (SESSION 116) |
| 2     | Workspace dashboard (S-09)           | DONE (SESSION 117) |
| 3     | Spokesperson detail (S-10)           | DONE (SESSION 118) |
| —     | Custom email-as-PK User model        | DONE (SESSION 119) |
| 4     | Create spokesperson (S-06)           | DONE (SESSION 120) |
| 5     | Make-a-video (S-12) + status (S-11)  | DONE (SESSION 121) |

What's working end-to-end after SESSION 121:

  - Everything from SESSIONS 107-120.
  - `/spokespeople/:id/render` — editorial form, brief pre-
    fills from spokesperson.business_brief, avatar-not-ready
    callout when the avatar isn't bound, tier-limit callout
    for HTTP 402.
  - `/videos/:id` — **the canonical async surface.** Polls every
    2 s via TanStack Query's `refetchInterval` function form,
    halts on terminal. Three render branches (rendering / ready
    / failed). `<video controls>` playback when ready.
  - "Make a video" CTA on the spokesperson detail page (disabled
    when no avatar). Dashboard's recent-renders rows are
    clickable links to the status page.
  - **8 Playwright specs pass** including the full lifecycle
    spec (14.4 s — Celery worker writes terminal state in mock
    mode after ~13 s).

---

## SESSION 122 — Three reasonable next slices

The core lifecycle is closed. Pick by what matters next:

### Option A — Voice clone UI (recommended)

Smallest scope. Backend shipped SESSION 110. Adds a "Clone a
voice" panel to the spokesperson detail page:

1. **Audio capture/upload component.** Mirrors the SESSION 120
   PortraitUpload pattern — drag-and-drop or click for file
   upload, mime + size validation, FileReader → base64. Plus
   browser `MediaRecorder` for record-in-place.
2. **`useCloneVoice()` mutation** on `spokespeople.ts`. POSTs to
   `/api/spokespeople/{id}/clone-voice/`. zod-parses the
   `{voice_id, status, preview_url}` response.
3. **Voice preview** — Runway-hosted preview MP3 in a tiny
   inline `<audio controls>` element.
4. **Detail page wiring** — replace the setup-checklist voice
   step with a real "Clone a voice" CTA + inline form.
5. **Playwright spec** — fresh signup → create spokesperson →
   upload audio (in-memory WAV buffer) → assert voice id
   persists + preview URL renders.

Half-session scope. Editorial inheritance trivial — the form
pattern is locked, the dropzone shape is locked.

### Option B — Stuck-row janitor

Operational hardening before any real traffic. ~30-line slice:

1. **`apps/videos/tasks.py::reenqueue_stuck_videos`** —
   scheduled Celery task. Queries `Video.objects.filter(
   status="rendering", updated_at__lt=now - 5min)`,
   re-enqueues `poll_video_until_terminal.delay(video.pk)`
   for each.
2. **`apps/videos/celery.py` beat schedule entry** — every
   60 seconds.
3. **Update `infra/docker-compose.yml`** if Celery beat needs
   its own process (it does — separate `celery -A character_os
   beat` worker).
4. **Smoke test** — set a video row to `rendering` + old
   `updated_at`, run the janitor, assert it got re-enqueued.

Worth landing **before** any real customers + before SESSION
124+ adds more polling surfaces.

### Option C — Additional video kinds

Each is a session: `cinematic_video` (text-only Runway), then
`dialogue_scene` (two spokespeople), then `long_ad` (multi-scene
composition). Backend slice + render form variant per kind. Defer
until Voice clone + Stuck-row janitor land.

### Recommendation: **A → B**

A is the natural next slice (closes the spokesperson detail's
setup checklist, exercises an existing backend). B is the
operational pre-launch hardening. C waits until the SPA exercises
all four kinds in real customer use.

### Out of scope for SESSION 122

- The 10 finishing-layer compositors from the runway-hackathon
  (PR FB → FI). Phase 4+ scope.
- Real Stripe Checkout / dj-stripe (operator gate).
- Real Google OAuth (operator gate).
- Profile / account settings.
- Marketing site (S-01, S-02).

---

## Queued investigations (priority-ordered)

1. **Voice clone UI** — recommended Slice 6.
2. **Stuck-row janitor** — operational hardening.
3. **Additional video kinds** (cinematic / dialogue / long_ad).
4. **Dashboard "Make a video" primary action wiring** — currently
   disabled placeholder. Auto-pick when exactly one ready
   spokesperson exists.
5. **`<MetadataGrid>` extraction** — the two-column dl pattern
   in `/videos/:id` + `/spokespeople/:id` is begging to be a
   shared component once a third use surfaces.
6. **`useElapsed` hook extraction** to `lib/hooks/` if a second
   tick-per-second consumer lands.
7. **Real Google OAuth + dj-stripe** — operator gates.
8. **Allauth legacy-settings cleanup** — when allauth drops
   the legacy keys.
9. **Tag `v-final-pre-migration` on runway-hackathon** — safe.
10. **smoke_voice transaction discipline** — small fix.
11. **Drift verifier** — `verify_doc_claims --only-drift`.
12. **Brand Identity v2 + dark mode** — when user-testing happens.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo   # required for video pipeline

cd web && pnpm dev                          # :5174, proxies to :8000
```

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video

# SPA (from web/)
pnpm test
pnpm e2e            # full lifecycle takes ~20 s
```

---

## AI / assistant context

- Last session: SESSION 121 — S-12 make-a-video + S-11 video
  status. **8 Playwright specs pass** including the lifecycle.
  The polling pattern in `/videos/:id` is the canonical async
  surface — future async UIs inherit it.
- Calibration carried forward: this operator prefers right-
  shaping foundations early. The polling pattern was that
  foundation pass. SESSION 122's voice clone UI inherits cleanly
  — don't invent a new polling shape; reuse `useVideo`'s
  `refetchInterval` function form when status transitions
  matter.
- React Router v7 routing order matters (twice now). Static
  routes (`/new`, `/:id/render`) MUST register before dynamic
  ones (`/:id`). Easy to miss on the next add.
- The `useEffect`-pre-fill-from-parent pattern (render form's
  brief pre-fills from spokesperson.business_brief once the
  data lands) is worth reusing for voice clone if the audio
  field has a "use the existing voice" pre-population case.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
