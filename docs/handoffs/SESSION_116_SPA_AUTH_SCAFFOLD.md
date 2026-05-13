---
title: "Session 116 — SPA scaffold + sign-up/sign-in slice"
date: 2026-05-13
status: complete
session: 116
previous_handoff: ./SESSION_115_SPA_SCOPE_LOCK.md
---

# Session 116 — Phase 3 Slice 1: SPA scaffold + auth screens

## TL;DR

- **What shipped:** First real SPA slice. `web/` is now a populated
  Vite + React 19 + TypeScript strict project with the full stack
  locked by SPA_ARCHITECTURE.md: Tailwind + shadcn/ui primitives
  (button/input/label/card), TanStack Query v5, React Router v7,
  react-hook-form + zod, Vitest, Playwright. Sign-up + sign-in
  routes + placeholder dashboard wired against `/_allauth/`.
  **Playwright e2e auth smoke passes** end-to-end (fresh email →
  signup → dashboard renders authenticated).
- **What also shipped (backend follow-on):** A custom allauth
  account adapter that backfills `username` from a hash of the
  email — Phase 1 had a latent UNIQUE constraint bug on
  `auth_user.username` that the e2e suite surfaced. Plus a tiny
  `CSRF_TRUSTED_ORIGINS = ["http://localhost:5174"]` entry so the
  Vite dev proxy can POST to Django.
- **What's blocking next:** Nothing. SESSION 117 ships Slice 2 —
  workspace dashboard (S-09 of design lock).
- **What's in a weird state:** A handful of dev-environment papercuts
  collected in the handoff below (pnpm 11 build-script approval
  dance, port collisions, csrftoken cookie domain, Origin header
  check). All documented inline in the relevant files.

---

## What changed (file-by-file)

### `web/` — new scaffold

```
web/
├── .gitignore .npmrc .nvmrc .prettierrc.json
├── package.json (pnpm@11.1.1 packageManager; ~25 deps)
├── pnpm-lock.yaml pnpm-workspace.yaml
├── vite.config.ts (port 5174, cookieDomainRewrite proxy)
├── tsconfig*.json (strict + noUncheckedIndexedAccess)
├── tailwind.config.ts + postcss.config.js
├── vitest.config.ts + playwright.config.ts
├── index.html
├── src/
│   ├── main.tsx (QueryClient + StrictMode)
│   ├── App.tsx (router + route map)
│   ├── styles/globals.css (Tailwind + shadcn tokens)
│   ├── lib/
│   │   ├── utils.ts (shadcn cn() helper)
│   │   ├── api/client.ts (fetch wrapper + CSRF + JSON envelope)
│   │   ├── api/auth.ts (zod schemas + getSession/signup/signin/signout)
│   │   ├── api/auth.test.ts (vitest schema smoke — 3 tests)
│   │   ├── auth/use-session.ts (TanStack Query hooks)
│   │   └── auth/require-auth.tsx (router guard)
│   ├── components/ui/ (button, input, label, card — shadcn primitives)
│   └── routes/
│       ├── _layout.tsx
│       ├── sign-up.tsx (S-03)
│       ├── sign-in.tsx (S-04)
│       └── dashboard/index.tsx (placeholder; S-09 lands next session)
├── e2e/auth.spec.ts (Playwright)
└── README.md
```

### `shell/character_os/settings.py`

- Added `CSRF_TRUSTED_ORIGINS = ["http://localhost:5174",
  "http://127.0.0.1:5174"]` so Django accepts the dev SPA's POSTs.
  Documented inline with the why (Django 4+ Origin-header check
  rejects cross-origin POSTs even with valid CSRF cookie + header).
- Added `ACCOUNT_ADAPTER = "apps.accounts.adapter.WorkspaceAccountAdapter"`.

### `shell/apps/accounts/adapter.py` (new)

`WorkspaceAccountAdapter` overrides `save_user` to populate
`username` from a `sha256(email)[:24]` hash. Without it, allauth
creates users with `username=""` and the second signup hits
`UNIQUE constraint failed: auth_user.username`. This bug was
latent in SESSIONS 107-115 because `smoke_headless_auth` only
ever creates one user at a time + cleans up; Playwright keeps
test rows around, which exposed it.

When we eventually migrate to a custom email-as-PK User model
(queued investigation), this adapter goes away.

### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated. URL routes still 169 (no Django URL changes this
session — only settings).

---

## Verification gates

- `pnpm build` — clean.
- `pnpm test` — 3 passed (auth schema smoke).
- `pnpm e2e` — **2 passed** (`signup → dashboard` + `invalid
  credentials → error`).
- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — clean (no schema changes;
  the adapter is settings-only).
- `python manage.py smoke_headless_auth` — still PASSES (backend
  unaffected; the adapter applies to it too, but the smoke
  generates a fresh email per run + cleans up so the bug never
  triggered).
- `python manage.py inventory` — regen clean, FastAPI routes 93.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Five dev-environment papercuts in one slice

This was the bumpiest slice in the project so far. Each
papercut was small but had to be solved in sequence:

1. **pnpm 11's build-script approval dance.** pnpm 11 refuses to
   run post-install scripts (like esbuild's) without explicit
   approval. Solved with `pnpm-workspace.yaml`'s `allowBuilds:
   esbuild: true` plus a `.npmrc` with `verify-deps-before-run:
   false` so subsequent `pnpm build` calls don't re-trigger the
   pre-script deps check.
2. **Port collision on :5173.** Operator keeps the runway-hackathon
   Vite running there. Same fix as the Redis port-shift in
   SESSION 109: dodge with :5174. Documented inline.
3. **csrftoken cookie on wrong origin.** Vite proxies Django ↔ SPA
   transparently, but Django's `Set-Cookie: csrftoken=...` lands
   on the upstream origin (`:8000`) instead of the SPA's (`:5174`).
   `document.cookie` then can't see it. Fixed with
   `cookieDomainRewrite: ""` in the Vite proxy config.
4. **Django's Origin-header check.** Even with cookie + X-CSRFToken
   correct, Django 4+ rejects POSTs whose `Origin` doesn't match
   the request's `Host` and isn't in `CSRF_TRUSTED_ORIGINS`. Added
   `:5174` to the trusted list.
5. **Latent UNIQUE constraint on `auth_user.username`.** Surfaced
   above — fixed via custom adapter.

The reassuring takeaway: each papercut had a clean,
well-documented fix. Future sessions doing this kind of
cross-stack work should expect ~1 of these per layer (transport,
cookie domain, CSRF origin, model invariants).

### The two-test Playwright pattern is right

The auth spec has exactly two tests:

- **Happy path** — fresh email signup → dashboard renders.
- **Failure path** — invalid creds → error visible, still on
  `/sign-in`.

This is the right minimum: the happy path proves the contract
works; the failure path proves errors surface to the user
without crashing the SPA. Future slices follow the same shape —
one happy path + one failure path per slice — until coverage
needs grow.

### The latent username bug is a real product concern

SESSIONS 107-115 had `auth.User` with stock `unique=True` on
username + allauth configured for email-only signup. This works
for one user. Two breaks. We dodged it because every smoke test
cleaned up before the next one ran.

Phase 3 lands real customers signing up. The custom adapter is
a band-aid; the proper fix is a **custom User model with email
as the unique identifier** (and no username column at all).
Queued — see SESSION 117 entry point.

### React 19 + Router 7 + TS 6 — all latest

The Vite scaffold gave us React 19 (we'd locked "18+") and
TypeScript 6 (we'd locked "strict"). Both satisfy the scope-lock
constraints; landed without amendment. React Router 7 is also
newer than the locked v6 — same compatibility, same APIs for
what we use. The point of the scope lock is direction, not
exact version numbers; these are all forward-compatible.

---

## SESSION 117 — entry point

Slice 2: workspace dashboard (S-09). See `00-START-NEXT-SESSION.md`.

Plus a real follow-up: custom email-as-PK User model. The latent
username bug deserves a proper fix before Phase 3 sees real
traffic, and it's a small enough slice (~1 model + migration +
backfill).

---

## AI notes

- The bumpy slice taught me that "scope-lock first" is necessary
  but not sufficient. SPA_ARCHITECTURE.md locked stack and shape,
  but couldn't predict the dev-environment papercuts (pnpm 11
  behavior, port collision, cookie origin, Django origin check).
  Those compound — fixing each one in sequence took longer than
  writing the actual code. Next time a similar slice lands,
  bring up the full local stack and run a smoke EARLY rather
  than after all the code is written.
- The latent username bug is the most interesting find of this
  session. SESSIONS 107-115 all "passed" their smoke tests but
  the underlying invariant was wrong. A drift-verifier check on
  "is `auth_user.username` actually unique across our auth flow?"
  would have caught it. Worth thinking about for the verifier
  slice.
- Five sessions of trusting `manage.py smoke_*` as the
  authoritative correctness gate — and four of those would have
  let this through. Playwright's first run found it. Good
  reminder that end-to-end browser tests catch a different
  class of bug than unit/integration smokes.
- The `_layout.tsx` trick of calling `useSession()` at the
  router root so every page gets the csrftoken cookie set
  early — that's a real pattern, worth flagging in
  SPA_ARCHITECTURE.md as the canonical answer to "where does
  CSRF bootstrapping live."
