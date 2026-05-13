---
title: "Session 115 — SPA architecture scope-locked"
date: 2026-05-13
status: complete
session: 115
previous_handoff: ./SESSION_114_ALLAUTH_HEADLESS.md
---

# Session 115 — Phase 3 SPA scope-locked, no code yet

## TL;DR

- **What shipped:** `docs/design/SPA_ARCHITECTURE.md` — a scope-
  lock companion to `MEDIA_ENGINE_INTERNAL_API.md`, in the same
  load-bearing role. Locks the Phase 3 SPA's stack, auth client
  shape, API client shape, folder structure, smoke pattern, and
  the **first three slices** (sign-in/up, workspace dashboard,
  spokesperson detail). Updated the narrative anchor to reference
  it.
- **What's blocking next:** Nothing. SESSION 116 starts the first
  SPA slice (sign-up + sign-in screens) against the locked
  contract.
- **What's in a weird state:** None. Doc-only slice; no Django,
  FastAPI, or SPA code changed.

---

## What changed (file-by-file)

### `docs/design/SPA_ARCHITECTURE.md` (new)

The scope-lock doc. Six load-bearing **contract rules** at the
top, parallel to the rules in `MEDIA_ENGINE_INTERNAL_API.md`:

1. Same-origin in production (no CORS).
2. Session-cookie auth (no bearer tokens).
3. Server state via TanStack Query; local state via React.
4. Forms via react-hook-form + zod.
5. Routing via React Router v6.
6. No silent error suppression.

Stack lock pins concrete versions and tooling:

- Vite 5+, React 18+, TypeScript strict mode
- Tailwind + shadcn/ui + lucide-react
- TanStack Query v5 + native fetch + zod
- react-hook-form + zod validators
- React Router v6
- Vitest + Testing Library + Playwright
- pnpm + eslint + prettier
- Node 20 LTS

Folder structure under `web/` is explicit (routes/, lib/api/,
components/, e2e/) — no in-PR invention of conventions.

Auth client design walks through session bootstrapping, CSRF
handling, the auth state machine, and sign-up/sign-out flows
with pseudo-code so the implementation in SESSION 116 has a
target shape.

API client design pins per-resource modules in `lib/api/`,
zod-schema parsing at the boundary, TanStack Query hooks for
server state, and the polling pattern for video status
(`refetchInterval: data?.status === "rendering" ? 2000 : false`).

First three slices map directly to design-lock §5 screens:

- Slice 1: S-03 + S-04 (sign-up + sign-in).
- Slice 2: S-09 (workspace dashboard).
- Slice 3: S-10 (spokesperson detail).

Out-of-scope section is **explicit** about what is NOT being
decided here: state management beyond TQ + React, marketing site
(S-01/S-02), activation videos (S-19), account/billing screens
(S-15 to S-18), realtime conversation (S-13), admin (A-01 to
A-03), i18n, native apps, GraphQL.

Seven open questions captured at the bottom for resolution as
they actually surface (form error display, loading skeletons,
toasts, theme, Sentry, analytics, dashboard onboarding wiring).

### `docs/CHARACTER_OS_WHAT_IT_IS.md`

Two updates:

1. The Layer 3 SPA paragraph now reflects locked scope instead
   of "empty scaffold + missing design doc."
2. The navigation table cites the new architecture doc.
3. Frontmatter bumped: `last_revised: 2026-05-13 (SESSION 115)`,
   `covers_sessions: "106-115"`.

---

## Verification gates

Doc-only slice; standard runtime gates not applicable. What was
checked:

- `docs/design/SPA_ARCHITECTURE.md` exists at the documented path.
- Internal cross-references resolve (Markdown links to
  `UI_REDESIGN_V2.md` and `MEDIA_ENGINE_INTERNAL_API.md` — both
  files exist).
- No code changes; no runtime gates needed.
- `git status` reflects only the expected additions.

---

## Architectural notes worth remembering

### The contract pattern compounds

Phase 2's `MEDIA_ENGINE_INTERNAL_API.md` made the Django ↔ FastAPI
boundary load-bearing — every internal endpoint inherited the
five contract rules without rediscovering them. SPA_ARCHITECTURE.md
plays the same role for the SPA boundary. Six rules at the top
bind every future SPA slice; the operator (or a future AI) can
push back on any in-PR drift with "this violates rule N of the
scope lock" instead of having to relitigate fundamentals.

### Why TanStack Query, why not Redux

The SPA's state shape is overwhelmingly server-state (workspaces,
spokespeople, videos, sessions). Client-only state (form drafts,
UI toggles, navigation) is local to one component. Redux solves
a problem we don't have — client-side state shared across
components that's NOT derived from the server. Picking TQ now
saves a "we have three sources of truth" cleanup pass later.

### Why session cookies, not tokens

Three reasons, in priority order:

1. **`allauth.headless` (SESSION 114) is configured for the
   `browser` client.** Switching to tokens means flipping to
   the `app` client, which means a different URL surface, a
   different signup flow, and explicit token persistence in the
   SPA. Out of scope for Phase 3.
2. **Same-origin deploy.** Django serves the built SPA; cookies
   work without `SameSite=None` gymnastics.
3. **CSRF is already wired.** Django's CSRF middleware + a thin
   fetch wrapper that reads the `csrftoken` cookie is less code
   than a token-management layer.

The tradeoff: native mobile apps can't use this. That's fine —
design lock §10 explicitly defers native mobile. When mobile
lands, enable `HEADLESS_CLIENTS = ("browser", "app")` and add
the app client; the browser client doesn't change.

### What this doc deliberately doesn't lock

Theme + brand identity (Q5). Form error UX (Q2). Loading
skeleton vs spinner (Q3). All deferred to a "Brand Identity"
doc that doesn't exist yet (and that the design lock §10
explicitly deferred too). The SPA architecture doesn't need
these locked to start building; they get decided when the first
screen needs them.

---

## SESSION 116 — entry point

First SPA slice. Sign-up + sign-in screens (S-03, S-04 in the
design lock). See `00-START-NEXT-SESSION.md` for the
recommended scope of that one slice — narrowly bounded so it
ships in one session.

---

## AI notes

- Doc-only slice, ~25 min start to finish. The lift was in
  framing — picking which decisions to lock, which to defer to
  open questions, which to leave for a future "Brand Identity"
  doc.
- This is the second contract-style doc this project has now
  (the first being `MEDIA_ENGINE_INTERNAL_API.md`). The pattern
  is now well-established enough that future ones can follow
  the same template: rules at the top, stack/decisions in the
  middle, scope+out-of-scope explicit, open questions deferred,
  change log at the bottom.
- The seven open questions are worth a second pass when the SPA
  has rendered its first form. The temptation to decide them now
  is strong but premature — you can't pick a "loading skeleton
  convention" without knowing what a loading state in this app
  actually looks like.
- The deliberate decision NOT to use Next.js was implicit in
  the design lock's "React+Vite SPA" mention. Worth flagging
  explicitly: Next.js's file-based routing, server components,
  and bundler tradeoffs are well-known wins, but the cost is a
  Node SSR server next to Django. Vite + same-origin Django is
  one less moving part for v1.
