---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` — what to build
> (845 lines, screens S-01 to S-19 + admin).
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` —
> Django ↔ FastAPI boundary, feature-complete.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md` —
> stack + auth client + API client + first three slices.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory`.
> **Last handoff:** `docs/handoffs/SESSION_115_SPA_SCOPE_LOCK.md`.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django DRF shell scaffold:** DONE (SESSION 107).
**Phase 2 — Media data model migration:** MOSTLY DONE.
**Phase 3 — Build new UI:** **IN PROGRESS.**
  Foundation done: `allauth.headless` wired (SESSION 114) +
  SPA architecture scope-locked (SESSION 115). First SPA slice
  starts SESSION 116.

What's working end-to-end after SESSION 115:

  - Everything from SESSIONS 107-114.
  - `docs/design/SPA_ARCHITECTURE.md` locks the SPA's shape —
    Vite + React + TS + shadcn/ui + Tailwind, TanStack Query +
    zod, session-cookie auth via `/_allauth/`, React Router,
    Playwright e2e tests.
  - Folder structure under `web/`, contract rules, and the
    first three slices are all documented before any code
    lands.

---

## SESSION 116 — first SPA slice (sign-up + sign-in)

The narrowest implementable slice that exercises the auth
contract end-to-end. Roughly maps to S-03 + S-04 of the design
lock.

### Recommended scope

1. **Scaffold `web/`** with the locked stack:
   - `pnpm init` + Vite React-TS template.
   - Install pinned deps (TanStack Query, React Router,
     react-hook-form, zod, Tailwind, shadcn/ui CLI, lucide-react,
     Vitest, Playwright).
   - Set up `vite.config.ts` with the documented proxy paths
     (`/api`, `/_allauth`, `/accounts`).
   - Set up `tailwind.config.ts` + shadcn/ui init.
   - Set up tsconfig strict mode + eslint + prettier.
   - Commit the lockfile.
2. **`src/lib/api/client.ts`** — fetch wrapper with CSRF + JSON.
3. **`src/lib/api/auth.ts`** — `getSession()`,
   `signup({email, password})`, `signin(...)`, `signout()`.
   zod schemas for each response shape.
4. **`src/lib/auth/use-session.ts`** — TanStack Query hook.
   `<RequireAuth>` router guard component.
5. **`/sign-up` and `/sign-in` routes** — react-hook-form +
   zod-validated forms. Submit → mutation → invalidate session
   → router pushes to a placeholder `/dashboard` (just a
   "you're authed" page in this slice; the real dashboard is
   SESSION 117).
6. **Tailwind + shadcn primitives** — install `button`,
   `input`, `label`, `card`. Nothing custom yet.
7. **`web/e2e/auth.spec.ts`** — Playwright spec that:
   - Starts from `/sign-up`
   - Fills + submits the form
   - Asserts the URL is `/dashboard` and the placeholder text
     renders
   - Asserts a teardown query reverts the test user
8. **Verification:** `pnpm build` clean, `pnpm test` (Vitest)
   passes, `pnpm exec playwright test` passes. Backend smoke
   tests still pass.

### Critical constraints (from SPA_ARCHITECTURE.md)

- Stay strict-mode TypeScript. No `any` without a comment.
- No state library other than TanStack Query + React hooks.
- No form library other than react-hook-form.
- All API responses parsed through zod before they hit the
  cache.
- Errors surface; no silent fallbacks.

### Out of scope for SESSION 116

- Real dashboard (SESSION 117, Slice 2).
- Google OAuth button (queued; needs operator credentials).
- Forgotten-password flow (allauth has it; not in slice 1).
- Account settings, billing, anything S-11+.
- Toasts, theme, error tracking — see "Open questions" in
  SPA_ARCHITECTURE.md.

---

## Alternative slices if SPA scaffold feels premature

Three options remain available, in priority order:

- **A — Stuck-row janitor.** `celery beat`-scheduled re-enqueue
  for Video rows in `rendering` longer than 5 min. ~30-line
  slice. Operational hardening pre-real-traffic.
- **B — Real Google OAuth (headless flow).** Adds Google as a
  `/_allauth/browser/v1/auth/provider/redirect` option once
  operator-supplied OAuth credentials arrive. Backend-only;
  unblocks the OAuth button in the SESSION 116 scaffold.
- **C — Real Stripe Checkout / dj-stripe wiring.** Pending
  operator-supplied Stripe credentials. Unblocks S-17 (billing)
  later in Phase 3.

If A is the choice, do A and then SESSION 117 starts the SPA
scaffold. If B or C, the operator needs to supply credentials
first.

---

## Queued investigations (priority-ordered)

1. **Phase 3 SPA slice 1** — sign-up + sign-in scaffold
   (SESSION 116 recommendation).
2. **Phase 3 SPA slice 2** — workspace dashboard (SESSION 117+).
3. **Phase 3 SPA slice 3** — spokesperson detail (SESSION 118+).
4. **Stuck-row janitor** — operational hardening.
5. **Real Google OAuth** — operator gate.
6. **dj-stripe install** — operator gate.
7. **Campaigns→Django backfill script** — pending Phase 2
   deliverable. Defer until SPA renders legacy artefacts.
8. **Tag `v-final-pre-migration` on runway-hackathon** — safe
   any time. Recommended once SESSION 116 confirms the new
   surface works for real.
9. **Legacy doc rename** — cosmetic.
10. **Numbered handoff gap** (`SESSION_053`) — cosmetic.
11. **Smoke-test helper consolidation** — 4 backend commands +
    incoming Playwright specs.
12. **Drift verifier** — `verify_doc_claims --only-drift`.
13. **Find-missing-paths in `context-kit orient`**.
14. **Extend `python manage.py inventory` to count SPA routes**
    once the SPA stabilises.
15. **Brand Identity doc** — colors, typography, component
    style. Multiple open questions in SPA_ARCHITECTURE.md
    defer to it.

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

# (new terminal — once web/ is scaffolded)
cd web && pnpm dev                         # Vite :5173, proxies to :8000
```

Smoke checks:

```bash
cd shell && source .venv/bin/activate
python manage.py inventory                # regen the runtime anchor
python manage.py smoke_avatar             # SESSION 108
python manage.py smoke_voice              # SESSION 110
python manage.py smoke_video              # SESSION 109 (needs Celery worker)
python manage.py smoke_headless_auth      # SESSION 114
```

Manual headless probe:

```bash
curl http://127.0.0.1:8000/_allauth/browser/v1/config
curl http://127.0.0.1:8000/_allauth/browser/v1/auth/session
```

---

## AI / assistant context

- Last session: SESSION 115 — doc-only, ~25 minutes. SPA
  architecture scope-locked. Same pattern as the Phase 2
  contract doc.
- Calibration carried forward: this operator prefers right-
  shaping foundations early. SESSION 116 is the first SPA slice;
  resist the temptation to add anything beyond what
  `SPA_ARCHITECTURE.md` locks. The "real" looking thing is the
  locked thing — don't invent new shapes.
- Meta-lesson from SESSION 113 still applies: when a doc
  references a file path or component, sanity-check it exists
  during the same session. SESSION 116 must verify Vite + shadcn
  + each dep actually install + boot before claiming a slice
  done.
- Open questions Q1-Q7 in `SPA_ARCHITECTURE.md` will surface as
  decisions during SESSION 116-119. Defer answering them until
  the relevant slice actually needs the answer; that prevents
  invention.
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
