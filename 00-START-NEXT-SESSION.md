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
> **Last handoff:** `docs/handoffs/SESSION_120_CREATE_SPOKESPERSON.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3 — Build new UI:** Slices 1-4 SHIPPED + custom User model
landed. The spokesperson lifecycle is end-to-end in the SPA.

| Slice | Screens                              | Status |
|-------|--------------------------------------|--------|
| 1     | Sign-up + sign-in (S-03 + S-04)      | DONE (SESSION 116) |
| 2     | Workspace dashboard (S-09)           | DONE (SESSION 117) |
| 3     | Spokesperson detail (S-10)           | DONE (SESSION 118) |
| —     | Custom email-as-PK User model        | DONE (SESSION 119) |
| 4     | Create spokesperson (S-06)           | DONE (SESSION 120) |

What's working end-to-end after SESSION 120:

  - Everything from SESSIONS 107-119.
  - `/spokespeople/new` route — editorial form, optional portrait
    upload (drag-drop + click), client-side base64 conversion +
    validation, tier-limit error callout, redirect to detail page
    on success.
  - Dashboard empty-state has a real CTA → `/spokespeople/new`.
  - Spokespeople panel header has a `+ New` affordance.
  - 7 Playwright specs pass (auth × 2 + dashboard × 2 +
    spokesperson detail × 1 + create × 2).

---

## SESSION 121 — Recommended: S-12 Make-a-video flow

The biggest remaining slice in the Phase 3 plan. Closes the
core lifecycle: dashboard → create spokesperson → detail page →
**make a video** → render polls → playback.

### Recommended scope

1. **Make-video CTA wiring.** The dashboard's "Make a video"
   button (currently disabled) becomes a real action. Two
   entry points:
   - Dashboard panel CTA — opens a modal or navigates to
     `/spokespeople/{id}/render` for the user's first/active
     spokesperson.
   - Detail page CTA — opens the same flow scoped to the
     current spokesperson.

2. **`web/src/routes/spokespeople/[id]/render.tsx`** OR
   **make-video modal** — operator decision.
   Recommend a dedicated route for v1 (deep-linkable, browser-
   back works naturally, easier to test with Playwright). Modal
   can come later if onboarding demands it.

3. **Form contents:**
   - Title (text, optional) — for naming the resulting video.
   - Brief (textarea, required) — what this video says.
     Pre-fill from spokesperson's `business_brief`.
   - Kind picker — for SESSION 121 ship `spokesperson_ad` only
     (other kinds require additional backend slices). Hide the
     picker for v1, lock to `spokesperson_ad`.

4. **Submit flow** (`POST /api/videos/`):
   - 201 with `status: "rendering"` + `media_engine_task_id`.
   - Redirect to a **video detail / status page** that polls.

5. **Polling page** (new route, S-11 in design lock):
   - `useQuery({ queryKey: ["video", id], queryFn: getVideo,
     refetchInterval: data => data?.status === "rendering" ? 2000 : false })`.
   - Editorial status surface: display-font title, status pill,
     elapsed time, polling progress.
   - On `status === "ready"`: render `<video controls>` with
     the `output_path`.
   - On `status === "failed"`: surface the `error_message`.

6. **Backend tweaks if needed:**
   - `GET /api/videos/{id}/` already exists (DRF default).
   - The polling is hands-off — Celery worker (SESSION 109)
     writes the row asynchronously.

7. **Playwright spec:**
   - Sign up → create spokesperson with portrait → click "Make
     a video" → fill brief → submit → land on status page →
     poll completes → MP4 player visible.
   - Mock mode takes ~13 s; default the test timeout to 30 s.

### Critical constraints

- **Celery worker MUST be running** for the e2e test. Document
  in the spec's preamble + skip with a clear message if Redis
  isn't reachable.
- Stay strict-mode TypeScript. zod-parse at boundary.
- Editorial-warm inheritance: no new tokens. Reuse the
  status-pill family from spokesperson detail.
- The polling pattern is the canonical fire-then-poll
  reference for the entire SPA — handle it cleanly so future
  async surfaces inherit.

### Out of scope for SESSION 121

- Other video kinds (`cinematic_video`, `dialogue_scene`,
  `long_ad`). Each is its own slice.
- Variants (dubbed / remix / B-roll / etc. — the 10 finishing
  layers from the runway-hackathon).
- Sharing / download / regenerate CTAs.
- Voice clone UI (separate slice).
- Stuck-row janitor (operational hardening).

---

## Alternative slices

- **Voice clone UI** on the spokesperson detail page. Reuses
  `POST /api/spokespeople/{id}/clone-voice/` (SESSION 110).
  Smaller than S-12; about 1/2 a session.
- **Stuck-row janitor** (`celery beat`). ~30-line slice;
  operational hardening before S-12 lands real polling traffic.
- **Allauth legacy-settings cleanup** — currently 3 deprecated
  settings still set; revisit when allauth drops them.

---

## Queued investigations (priority-ordered)

1. **S-12 Make-a-video flow** — SESSION 121 recommendation.
2. **S-11 Video detail / status page** — lands with S-12.
3. **Voice clone UI** — backend ready since SESSION 110.
4. **Stuck-row janitor** — operational hardening.
5. **Other video kinds** (cinematic / dialogue / long_ad) —
   one slice each.
6. **Real Google OAuth + dj-stripe** — operator gates.
7. **Allauth legacy-settings cleanup** — when allauth drops keys.
8. **`<StretchedLink>` component extraction** — if third use lands.
9. **smoke_voice / smoke_avatar transaction discipline** — tiny fix.
10. **Tag `v-final-pre-migration` on runway-hackathon** — safe.
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
celery -A character_os worker --loglevel=info --pool=solo   # required for S-12

cd web && pnpm dev                          # :5174
```

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video                # needs Celery worker

# SPA (from web/)
pnpm test
pnpm e2e
```

To create a Django superuser (custom User model — email-keyed):

```bash
python manage.py createsuperuser
```

---

## AI / assistant context

- Last session: SESSION 120 — S-06 create-spokesperson flow.
  40 minutes start-to-tests-passing. 7 Playwright specs green
  on first run.
- Calibration carried forward: this operator prefers right-
  shaping foundations early. **For SESSION 121:** the polling
  pattern is the foundation for every future async UI surface
  (S-11 video detail, voice clone status, future spider
  dashboards). Lock the shape cleanly — use TanStack Query's
  `refetchInterval` function form to halt on terminal states.
- The portrait-upload component is the first shadcn-untracked
  primitive in `web/src/components/`. Worth keeping in mind:
  if S-12 needs a similar file/text input pair (e.g., the
  brief textarea wants a "load from file" affordance), reuse
  the dropzone shape rather than inventing.
- React Router v7 routing order matters — register static
  routes (`/spokespeople/new`) BEFORE dynamic ones
  (`/spokespeople/:id`). Easy to get wrong on the next add.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
