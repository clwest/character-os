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
> **Last handoff:** `docs/handoffs/SESSION_119_CUSTOM_USER_MODEL.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3 — Build new UI:** Slices 1-3 SHIPPED + custom User model
landed (SESSION 119). Auth foundation is now production-shape.

| Slice | Screens                              | Status |
|-------|--------------------------------------|--------|
| 1     | Sign-up + sign-in (S-03 + S-04)      | DONE (SESSION 116) |
| 2     | Workspace dashboard (S-09)           | DONE (SESSION 117) |
| 3     | Spokesperson detail (S-10)           | DONE (SESSION 118) |
| —     | Custom email-as-PK User model        | DONE (SESSION 119) |

What's working end-to-end after SESSION 119:

  - Everything from SESSIONS 107-118.
  - `apps.accounts.User` is the real model. No more
    `WorkspaceAccountAdapter` band-aid.
  - 5 Playwright specs pass + 4 backend smokes pass against the
    new User model with effectively zero SPA changes (one zod
    field dropped).
  - Fresh DB. Test users from earlier sessions are gone.

---

## SESSION 120 — Option B: S-06 create-spokesperson flow

The missing piece between "fresh dashboard" and "spokesperson
detail." With Option A (User model) shipped, signups now flow
through the real model, so this slice's form code paths
exercise the canonical surface.

### Recommended scope

1. **`web/src/routes/spokespeople/new.tsx`** — new route. Form
   with three fields: name (text), business_brief (textarea),
   portrait (file upload, drag-and-drop or click). Validated via
   react-hook-form + zod.
2. **Portrait → base64 conversion** in the SPA. The
   `POST /api/spokespeople/` endpoint already supports
   `portrait_data_uri` (SESSION 116 backend wiring); on form
   submit, read the file via `FileReader`, encode as
   `data:image/...;base64,...`, send.
3. **Submit handler** — TanStack Query mutation. On success,
   invalidate the `spokespeople` query (so the dashboard refreshes
   when the user navigates back) and redirect to
   `/spokespeople/{id}`.
4. **Loading state** during avatar create — synchronous in mock
   mode (~50ms), ~20s in real mode. Show a skeleton state on the
   form during the submission.
5. **Error states** — tier limit (HTTP 402), validation errors
   per field, network errors. Surface allauth-style structured
   error copy.
6. **Dashboard wiring** — the empty-state "Create your first
   spokesperson" callout becomes a real `<Link to="/spokespeople/new">`.
   The dashboard masthead grows a small "+ New" button at the
   right side too.
7. **Playwright spec** — `e2e/create-spokesperson.spec.ts`. Fresh
   signup → dashboard empty state → click "Create" → fill form →
   submit → land on detail page with avatar bound (mock mode).

### Critical constraints

- Stay strict-mode TypeScript. No `any` without comment.
- All API responses zod-parsed before TQ cache.
- File-upload size cap on the SPA side (mirror backend's 5 MB
  decoded cap) so we don't ship oversized base64 over the wire.
- Editorial-warm aesthetic inheritance: reuse panel headers, card
  surfaces, oxblood primary button. No new tokens.

### Out of scope for SESSION 120

- Voice clone UI on the detail page (separate slice).
- Make-a-video flow (S-12; biggest remaining slice).
- Video detail page (S-11).
- Profile / account settings (S-15).

---

## Alternative slices

- **S-12: Make-a-video flow.** The biggest remaining slice in the
  Phase 3 plan. Operator types brief → SPA fires
  `POST /api/videos/` → polls `GET /api/videos/{id}/` for terminal
  state. The fire-then-poll backend (SESSION 109) is ready; this
  slice is roughly a full session of frontend work.
- **Stuck-row janitor** (`celery beat`). Operational hardening
  for the video pipeline.
- **Voice clone UI** for the spokesperson detail page. Backend
  ready since SESSION 110.

---

## Queued investigations (priority-ordered)

1. **S-06 Create-spokesperson flow** — SESSION 120 recommendation.
2. **S-12 Make-a-video flow** — biggest remaining slice.
3. **Voice clone UI** — detail-page sub-action.
4. **S-11 Video detail** — playback + status + variants.
5. **Stuck-row janitor** — operational hardening.
6. **Real Google OAuth + dj-stripe** — operator gates.
7. **Allauth legacy-settings cleanup** — `ACCOUNT_AUTHENTICATION_METHOD`,
   `ACCOUNT_USERNAME_REQUIRED`, `ACCOUNT_EMAIL_REQUIRED` are still
   set alongside their newer counterparts. Remove when allauth
   drops the legacy keys entirely.
8. **`<StretchedLink>` component extraction** — if third use lands.
9. **Tag `v-final-pre-migration` on runway-hackathon** — safe any
   time.
10. **smoke_voice / smoke_avatar transaction discipline** — the
    auto-create-spokesperson helpers persist rows across runs in
    smoke_voice (outside transaction.atomic) but rollback in
    smoke_avatar (inside transaction.atomic). Asymmetric;
    smoke_voice should match smoke_avatar's pattern. Tiny fix
    when convenient.
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
celery -A character_os worker --loglevel=info --pool=solo   # video pipeline only

cd web && pnpm dev                          # :5174, proxies to :8000
```

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth      # SESSION 119: against custom User
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video

# SPA (from web/)
pnpm test
pnpm e2e
```

**To create a Django admin superuser** (now that the User model is
custom, `createsuperuser` prompts for email + password instead of
username):

```bash
cd shell && source .venv/bin/activate
python manage.py createsuperuser
```

---

## AI / assistant context

- Last session: SESSION 119 — custom email-as-PK User model
  shipped. Replaces the SESSION 116 band-aid. 5 Playwright specs
  + 4 backend smokes pass against the new model. SPA needed
  effectively zero changes.
- Calibration carried forward: this operator prefers right-shaping
  foundations early. SESSION 119 was a foundation pass; SESSION
  120 (S-06) is back to forward motion on the SPA.
- Meta-lesson from SESSION 119: when doing settings cleanups,
  don't trust `manage.py check` alone — also run `manage.py
  runserver` since their check tag sets can differ. The allauth
  legacy-vs-modern settings overlap is the canonical example.
- Allauth deprecation warnings on `ACCOUNT_AUTHENTICATION_METHOD`
  + `ACCOUNT_USERNAME_REQUIRED` + `ACCOUNT_EMAIL_REQUIRED` are
  intentional. Don't remove without testing both `check` and
  `runserver`.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
