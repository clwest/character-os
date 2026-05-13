---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_116_SPA_AUTH_SCAFFOLD.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3 — Build new UI:** Slice 1 SHIPPED (SESSION 116).
Slice 2 (workspace dashboard) is next.

What's working end-to-end after SESSION 116:

  - Everything from SESSIONS 107-115.
  - `web/` SPA scaffold: Vite + React + TS strict + Tailwind +
    shadcn/ui + TanStack Query + React Router + react-hook-form +
    zod + Vitest + Playwright. Sign-up + sign-in routes live
    against `/_allauth/`. Placeholder dashboard surfaces the
    authed user.
  - **Playwright e2e auth smoke passes** (`pnpm e2e` — happy path
    + invalid-creds path).
  - Backend follow-ons: custom `WorkspaceAccountAdapter` fills
    `auth_user.username` from email hash (fixes latent UNIQUE
    bug); `CSRF_TRUSTED_ORIGINS` includes the dev SPA origin.

---

## SESSION 117 — Slice 2: workspace dashboard (S-09)

Per SPA_ARCHITECTURE.md §"First three screens" → Slice 2. The
real `/dashboard` route. Replaces SESSION 116's placeholder card.

### Recommended scope

1. **`src/lib/api/workspaces.ts`** — typed wrapper for
   `GET /api/me/` (returns the authed user's workspace + tier
   + usage). zod schemas.
2. **`src/lib/api/spokespeople.ts`** — typed wrapper for
   `GET /api/spokespeople/`. zod schemas + TanStack Query hook.
3. **`src/lib/api/videos.ts`** — typed wrapper for
   `GET /api/videos/?limit=10`. zod + TQ hook.
4. **`src/components/spokesperson-card.tsx`** — tile component
   for the dashboard grid.
5. **`src/components/video-row.tsx`** — row component for the
   recent-videos list.
6. **`src/components/usage-meter.tsx`** — tiny "N of M videos this
   month" bar; reads from the workspace/me response.
7. **`src/routes/dashboard/index.tsx`** — rewrite the placeholder.
   Sections: workspace header (name + user + sign-out), spokesperson
   grid (empty state CTA when empty), recent videos, usage meter.
8. **Playwright spec extension** — extend `e2e/auth.spec.ts` or
   add `e2e/dashboard.spec.ts` for "authed user sees empty state"
   + "authed user with seeded spokesperson sees the tile."
9. **One backend tweak likely needed:** `GET /api/me/` should
   include a tiny `workspaces` projection (id, name, current
   tier + usage). If it's missing, this slice adds it. The
   schema in `apps/accounts/serializers.py` is the natural home.

### Critical constraints

- Stay strict-mode TypeScript. No `any` without comment.
- All API responses parsed through zod before they hit TQ's cache.
- Use TanStack Query for everything fetched; no local state for
  server data.
- Errors surface; no silent fallbacks.

### Out of scope for SESSION 117

- "Create a spokesperson" flow (S-06; lands as its own slice).
- Make-a-video CTA wiring (S-12; later slice).
- Account settings, billing screens (S-15 to S-17).
- The custom User model migration (see below — separate slice).

---

## Recommended parallel slice (or pre-work): custom User model

SESSION 116 surfaced a latent bug: `auth_user.username` has
`unique=True`, but allauth signs users up with `username=""` when
email-only mode is on. The custom `WorkspaceAccountAdapter`
(SESSION 116) papers over it by populating username from an email
hash. The proper fix is a custom User model with email as the
primary identifier.

**Scope:**

- Create `apps.accounts.User` (subclass `AbstractBaseUser` or
  `AbstractUser`) with email as `USERNAME_FIELD`, no username
  field.
- `AUTH_USER_MODEL = "accounts.User"` in settings.
- Migration to swap the User model — has to be carefully
  sequenced (Django doesn't love swapping User models mid-project;
  this needs a single migration that creates the new model
  + copies data + flips the FK references).
- Delete the `WorkspaceAccountAdapter` band-aid + update
  `smoke_headless_auth` assertions.

**When to land:** before Phase 3 sees real customer signups.
Could happen before, during, or after SESSION 117 — it's
parallel-safe with the dashboard work since it doesn't touch the
SPA. Operator's call.

---

## Alternative slices

- **Stuck-row janitor** (`celery beat`). Operational hardening.
  ~30-line slice.
- **Real Google OAuth** (operator gate).
- **dj-stripe** (operator gate).

---

## Queued investigations (priority-ordered)

1. **Custom email-as-PK User model** — see above. Real fix for
   the SESSION 116 band-aid.
2. **Phase 3 Slice 2** — workspace dashboard. SESSION 117
   recommendation.
3. **Phase 3 Slice 3** — spokesperson detail. SESSION 118+.
4. **Stuck-row janitor** — operational hardening.
5. **Real Google OAuth** — operator gate.
6. **dj-stripe install** — operator gate.
7. **Tag `v-final-pre-migration` on runway-hackathon** — still
   safe any time.
8. **Smoke-test helper consolidation** — 5 commands now share
   the stub-request pattern; extract a shared helper.
9. **Drift verifier** — would have caught the SESSION 116
   latent username bug.
10. **Brand Identity doc** — color, type, component style. Open
    questions Q2-Q5 in SPA_ARCHITECTURE.md defer to it.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# (new terminal)
cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

# (new terminal — only for video pipeline)
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

# (new terminal — SPA)
cd web && pnpm dev                          # :5174, proxies to :8000
```

Smoke checks (backend):

```bash
cd shell && source .venv/bin/activate
python manage.py inventory                # regen runtime anchor
python manage.py smoke_avatar             # SESSION 108
python manage.py smoke_voice              # SESSION 110
python manage.py smoke_video              # SESSION 109 (needs Celery)
python manage.py smoke_headless_auth      # SESSION 114
```

SPA tests:

```bash
cd web
pnpm test                                  # Vitest, hermetic, fast
pnpm e2e                                   # Playwright (needs Django up)
```

---

## AI / assistant context

- Last session: SESSION 116 — Slice 1 of Phase 3 shipped end-
  to-end with Playwright passing. Bumpiest slice yet (5 dev-env
  papercuts) but each had a clean documented fix. Surfaced a
  latent username UNIQUE bug that 5 previous sessions of smoke
  tests missed.
- Calibration carried forward: operator prefers right-shaping
  foundations early. **For SESSION 117 specifically:** the
  custom User model is a foundation question. Consider landing
  it before more SPA work piles features on the band-aid.
- Meta-lesson from SESSION 116: end-to-end browser tests catch a
  different class of bug than unit/integration smokes. Worth
  running Playwright on every Phase 3 slice (not just the
  first).
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
