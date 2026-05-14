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
> **Last handoff:** `docs/handoffs/SESSION_118_SPOKESPERSON_DETAIL.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3 — Build new UI:** First three locked slices SHIPPED.

| Slice | Screens                              | Status |
|-------|--------------------------------------|--------|
| 1     | Sign-up + sign-in (S-03 + S-04)      | DONE (SESSION 116) |
| 2     | Workspace dashboard (S-09)           | DONE (SESSION 117) |
| 3     | Spokesperson detail (S-10)           | DONE (SESSION 118) |

What's working end-to-end after SESSION 118:

  - Everything from SESSIONS 107-117.
  - `/spokespeople/:id` detail page with identity panel, status
    pills, setup checklist, renders panel, back-to-dashboard
    link.
  - Spokesperson cards on the dashboard are clickable via the
    stretched-link pattern.
  - 5 Playwright e2e specs pass: 2 auth + 2 dashboard + 1
    spokesperson detail.

---

## SESSION 119 — Two parallel-safe options

The first three locked slices are done. The next move is between
**SPA forward motion** (S-06 → create-spokesperson flow makes the
detail page reachable in real use) and **backend cleanup** (custom
email-as-PK User model replaces the SESSION 116 band-aid).

Both are parallel-safe. Doing the User model first means S-06's
signup-adjacent code paths test against the real model. Doing
S-06 first means a more clickable demo for the operator sooner.

### Option A — Custom email-as-PK User model (recommended pre-work)

The overdue replacement of `apps.accounts.adapter.WorkspaceAccountAdapter`
(the SESSION 116 band-aid). Currently every signup creates a row
with `username = "u_" + sha256(email)[:24]` because Django's stock
`auth.User` requires a unique username. The proper fix:

1. **`apps/accounts/models.User`** — subclass `AbstractBaseUser` +
   `PermissionsMixin`. `email` is `unique=True`,
   `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`. No
   `username` column at all.
2. **`AUTH_USER_MODEL = "accounts.User"`** in settings (must land
   before any migrations run against a fresh DB).
3. **Migration** — single migration that creates the new model.
   Django doesn't love swapping `AUTH_USER_MODEL` mid-project, so
   the cleanest path is:
   - Stop the dev servers
   - Drop `shell/db.sqlite3`
   - Run `python manage.py migrate` against the new model
   - Re-run smoke_headless_auth to confirm
4. **Delete `WorkspaceAccountAdapter`** + remove the
   `ACCOUNT_ADAPTER` setting. The signal handler in
   `apps/accounts/signals.py` already works against any
   `AUTH_USER_MODEL` (it reads `instance.email` /
   `instance.username` with fallbacks).
5. **Update `smoke_headless_auth`** assertions if needed.

Scope: ~1 model + 1 migration + adapter deletion + smoke
verification. Half-session at most.

### Option B — S-06: Create-spokesperson flow

The missing piece between "fresh dashboard" and "spokesperson
detail." Maps to S-06 of the design lock. Form-driven with the
same editorial-warm aesthetic:

1. **`/spokespeople/new` route** — form with name +
   business_brief + portrait upload (drag-and-drop or click). All
   fields editable, validation via react-hook-form + zod.
2. **POST handler** — converts the portrait `File` → base64
   `data:image/...;base64,...` URI in JavaScript, calls
   `POST /api/spokespeople/` with the existing `portrait_data_uri`
   field. The SESSION 116 `SpokespersonViewSet.perform_create`
   already does the right thing (fires the media-engine avatar
   call if a portrait is supplied).
3. **Empty-state CTA** on the dashboard's spokespeople panel
   becomes a real button linking to `/spokespeople/new`.
4. **Loading state** during the avatar create (the media-engine
   call is synchronous in mock mode, ~50ms; real-mode is ~20s).
5. **Success state** redirects to `/spokespeople/{id}` (the
   detail page already exists).
6. **Playwright spec** — fresh signup → dashboard empty state →
   click "Create" → fill form → submit → land on detail page
   with avatar bound (mock mode).

Scope: roughly a session.

### Recommendation: **A first, then B**

Reasoning: Option A is overdue, smaller in lines, and its absence
is a known product risk (multi-customer signup currently relies
on a hash-based username collision avoider rather than a clean
model). Option B inherits the User model regardless — doing A
first means B's form code paths exercise the real model.

That said: if the operator wants to keep the demo clickable for
external eyes, B first is defensible (the band-aid is functional
for single-tenant use, and tens of test signups before A lands is
not a real risk).

### Out of scope for SESSION 119

- Voice clone UI (separate slice; backend supports it since
  SESSION 110).
- Make-a-video flow (S-12; the biggest remaining slice).
- Video detail page (S-11).
- Account/billing screens (S-15 to S-17).

---

## Alternative slices

- **Stuck-row janitor** (`celery beat`). Operational hardening.
- **Real Google OAuth** (operator gate).
- **dj-stripe** (operator gate).
- **`<Stretched-link>` component extraction** — if a third use
  lands (e.g. on `<VideoRow>` for video detail page).

---

## Queued investigations (priority-ordered)

1. **Custom email-as-PK User model** — Option A above.
2. **S-06 Create-spokesperson flow** — Option B above.
3. **S-12 Make-a-video flow** — the big one. Calls fire-then-poll
   video pipeline (already shipped backend-side).
4. **Voice clone UI** — backend ready since SESSION 110.
5. **S-11 Video detail** — playback + status + variants.
6. **Stuck-row janitor** — operational hardening.
7. **Real Google OAuth + dj-stripe** — operator gates.
8. **`<StretchedLink>` component** — if a third use lands.
9. **Tag `v-final-pre-migration` on runway-hackathon** — safe.
10. **Smoke-test helper consolidation** — 5 backend smokes + 5
    Playwright specs share patterns.
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
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_headless_auth

# SPA (from web/)
pnpm test
pnpm e2e
```

To seed a test spokesperson for live UI poking:

```bash
cd shell && source .venv/bin/activate
python manage.py smoke_avatar --keep
# Note: smoke_avatar picks the first workspace by created_at,
# which may not be your most recent signup. To target a specific
# workspace: --workspace-slug <slug>
```

---

## AI / assistant context

- Last session: SESSION 118 — Slice 3 (spokesperson detail).
  Smoothest slice in the project. Wrote route + API wrapper +
  Playwright spec + card-link change in one pass with zero TS
  errors and one e2e pass on first run. The aesthetic + scope
  lock pays off.
- Calibration: this operator prefers right-shaping foundations
  early. **For SESSION 119:** if you have to choose between
  Option A (User model cleanup) and Option B (S-06 flow), A is
  the foundation pass. The band-aid works but is real product
  risk if multiple test signups happen.
- Setup-panel pattern from SESSION 118 (numbered checklist
  with explicit "ships in S-06" references) is worth reusing
  whenever empty-state UI predates the underlying flow.
- The stretched-link pattern landed once in SESSION 118; if it
  shows up again, extract `<StretchedLink>` to avoid drift.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
