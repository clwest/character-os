---
title: "SPA Architecture — scope lock for Phase 3"
status: active (scope-locked, no code yet)
generated: 2026-05-13
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "MEDIA_ENGINE_INTERNAL_API.md"
phase: 3
---

# SPA Architecture — Phase 3 scope lock

> **Read first:** `docs/design/UI_REDESIGN_V2.md` §5 (screen
> inventory) + §6.1 (stack decisions). This doc is the **SPA**
> companion to `MEDIA_ENGINE_INTERNAL_API.md`: same role on the
> frontend boundary as that doc plays on the Django ↔ FastAPI
> boundary. It locks shape, not implementation. Implementation
> happens against this contract starting SESSION 116.

---

## Purpose

The design lock (`UI_REDESIGN_V2.md`) answered *what* to build —
9 customer-facing screens + 3 admin screens, on a React+Vite SPA
talking to Django DRF. SESSION 113 imported the design lock;
SESSION 114 wired `allauth.headless`. This doc answers *how* the
SPA itself is shaped, before any frontend code lands.

### Why scope-lock first

The operator's calibration profile
(`docs/TRUST_CALIBRATION.md`, 2026-05-13) leans toward right-
shaping foundations early. Phase 3 is the biggest scope expansion
in the project to date — a sloppy SPA scaffold is a far more
expensive retrofit than a sloppy Django app, because the SPA's
implicit decisions (state management, routing, data fetching,
forms, CORS strategy) compound across every screen. Locking the
shape now means SESSION 116 onwards is execution, not invention.

---

## Contract rules (load-bearing)

These bind every new SPA slice the same way the
`MEDIA_ENGINE_INTERNAL_API.md` rules bind every new internal
endpoint. Breaking any of them requires a deliberate amendment
to this doc, not an in-PR drift.

1. **Same-origin in production.** Django serves the built SPA
   static assets. The SPA hits `/_allauth/*` and `/api/*` on the
   same origin. No CORS in prod. (Dev uses Vite's proxy to
   localhost:8000.)
2. **Session-cookie auth, not bearer tokens.** Matches
   `HEADLESS_CLIENTS = ("browser",)` (SESSION 114). The SPA never
   sees an access token — the browser holds the session cookie,
   the SPA reads `/_allauth/browser/v1/auth/session` to learn
   auth state.
3. **Server state via TanStack Query, local state via React.**
   Anything fetched from Django lives in TanStack Query's cache.
   Component-local state (form drafts, UI toggles) uses normal
   React hooks. No Redux / Zustand / Recoil. If two screens need
   to share state, the answer is either "lift to a parent" or
   "fetch via TanStack Query."
4. **Forms via react-hook-form + zod.** shadcn/ui's form examples
   assume this combination; the rest of the form ecosystem is
   compatible but introduces an extra layer.
5. **Routing via React Router v6.** Vite + React Router is the
   defacto SPA stack. File-based routing (Next.js-style) is out
   of scope — Next.js is not.
6. **No global error boundary suppression.** Errors bubble; the
   user sees a real error UI. No silent fallbacks. Per-screen
   loading + error states are mandatory.

---

## Stack lock

### Framework + bundler

- **Vite 5+** — bundler / dev server. Same-origin proxy to
  Django in dev.
- **React 18+** with the new JSX transform.
- **TypeScript** in strict mode. `strict: true`,
  `noUncheckedIndexedAccess: true`. No `any` without an `eslint-
  disable-next-line` and a comment explaining why.

### UI

- **Tailwind CSS** — utility CSS. Required by shadcn/ui.
- **shadcn/ui** — copy-paste component library on top of Radix.
  Not an npm package; components are added via
  `npx shadcn-ui@latest add <name>` and live in
  `web/src/components/ui/`. Owned by us, modifiable.
- **lucide-react** — icon set shadcn/ui uses.

### Data layer

- **TanStack Query v5** (`@tanstack/react-query`) — server-state
  cache. Handles polling, refetch-on-focus, mutations, optimistic
  updates. Pairs perfectly with the SESSION 109 fire-then-poll
  video pipeline (the `Video` row polls naturally via TQ's
  `refetchInterval`).
- **`fetch` directly** — no axios, no ky. Browser fetch is
  enough; a tiny wrapper handles CSRF + JSON envelope.
- **zod** — schema validation at the API boundary. Every
  response parsed through a zod schema before it enters
  TanStack Query's cache. Catches contract drift loud.

### Forms

- **react-hook-form** — form state.
- **zod + @hookform/resolvers/zod** — validation. Same schemas
  used for API responses (DRY).

### Routing

- **react-router-dom v6** — declarative routes,
  `<Outlet>`-based layouts, loader/action pattern available
  (we won't use loaders/actions — TanStack Query handles
  fetching; routing is just URL → component).

### Testing

- **Vitest** — unit tests.
- **@testing-library/react** — component tests.
- **Playwright** — end-to-end smoke tests. The mirror of the
  Django `manage.py smoke_*` pattern; lives in `web/e2e/`.

### Tooling

- **pnpm** — package manager. Faster install, stricter
  dependency resolution than npm. Lockfile committed.
- **eslint + @typescript-eslint** — linting.
- **prettier** — formatting. Same rules as the project Python
  ruff config (line length 100, no opinions beyond that).
- **Node 20 LTS minimum.** Lock via `.nvmrc` and `package.json`
  `engines`.

---

## Folder structure under `web/`

```
web/
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.ts
├── .eslintrc.cjs
├── .nvmrc
├── index.html
├── public/
│   └── (static assets — favicons, manifests)
├── src/
│   ├── main.tsx                     # entry; mounts <App />
│   ├── App.tsx                      # router root
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts            # fetch wrapper, CSRF, JSON
│   │   │   ├── auth.ts              # /_allauth/* probes
│   │   │   ├── workspaces.ts        # /api/workspaces/, /api/me/
│   │   │   ├── spokespeople.ts      # /api/spokespeople/
│   │   │   ├── videos.ts            # /api/videos/
│   │   │   └── schemas.ts           # zod schemas, shared
│   │   ├── auth/
│   │   │   ├── use-session.ts       # TQ hook → /auth/session
│   │   │   ├── require-auth.tsx     # router guard component
│   │   │   └── csrf.ts              # cookie reader
│   │   └── utils/                   # tiny, generic helpers
│   ├── routes/
│   │   ├── _layout.tsx              # outer chrome (nav, footer)
│   │   ├── sign-in.tsx              # S-04
│   │   ├── sign-up.tsx              # S-03
│   │   ├── dashboard/
│   │   │   ├── _layout.tsx          # authed layout
│   │   │   └── index.tsx            # S-09
│   │   └── spokespeople/
│   │       └── $id.tsx              # S-10
│   ├── components/
│   │   ├── ui/                      # shadcn-installed primitives
│   │   ├── spokesperson-card.tsx
│   │   ├── video-row.tsx
│   │   └── usage-meter.tsx
│   └── styles/
│       └── globals.css              # Tailwind directives + tokens
├── e2e/
│   ├── playwright.config.ts
│   ├── auth.spec.ts                 # signup → dashboard
│   └── dashboard.spec.ts            # workspace data loads
└── README.md                        # how to dev, build, test
```

Two conventions worth flagging:

- **Routes mirror URL paths.** A file at
  `src/routes/dashboard/index.tsx` renders `/dashboard`. A file
  at `src/routes/spokespeople/$id.tsx` renders
  `/spokespeople/:id`. This isn't file-based routing — `App.tsx`
  still declares the routes — but the file layout mirrors them so
  the file you're looking for matches the URL you're looking at.
- **`lib/api/` per-resource.** One file per Django resource
  surface, exporting typed functions that wrap `fetch` + zod
  parsing. TanStack Query hooks live next to the components
  that use them (`use-spokespeople.ts` in the dashboard folder,
  for example), not in `lib/`.

---

## Auth client shape

The Phase 3 auth flow rides entirely on `allauth.headless`
(SESSION 114). The SPA never persists tokens — session cookies
do all the work.

### Session bootstrapping

On every page load, the SPA fires
`GET /_allauth/browser/v1/auth/session`. TanStack Query caches
the result indefinitely (the cookie either is or isn't valid;
no time-based expiry). All authed routes consult this cache via
a `useSession()` hook:

```ts
// pseudo-code; real implementation lives in src/lib/auth/use-session.ts
function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      const resp = await fetch("/_allauth/browser/v1/auth/session");
      // allauth returns 200 when authed, 401 when not — both are
      // expected; only network errors throw.
      if (resp.status === 401) return { is_authenticated: false, flows };
      if (!resp.ok) throw new Error(`session: ${resp.status}`);
      return resp.json();
    },
    staleTime: Infinity,  // session doesn't drift; invalidated on auth mutations
    retry: false,
  });
}
```

### CSRF

Django's CSRF middleware is on. `allauth.headless` exempts its
own routes via `@csrf_exempt`, but `/api/*` does NOT. The
fetch wrapper reads the `csrftoken` cookie and sets the
`X-CSRFToken` header on every non-GET request to `/api/*`:

```ts
// src/lib/api/client.ts pseudo-code
async function apiFetch(url, init = {}) {
  const csrf = readCookie("csrftoken");
  const headers = new Headers(init.headers);
  if (init.method && init.method !== "GET") {
    if (csrf) headers.set("X-CSRFToken", csrf);
    headers.set("Content-Type", "application/json");
  }
  return fetch(url, { ...init, credentials: "same-origin", headers });
}
```

### Auth state machine

Three states the SPA cares about:

1. **Loading** — `useSession()` is fetching for the first time.
   Render a loading skeleton.
2. **Unauthenticated** — `data.meta.is_authenticated === false`.
   Redirect to `/sign-in` (or render the public route).
3. **Authenticated** — `data.meta.is_authenticated === true`.
   Render the requested route.

The `<RequireAuth>` component wraps protected routes and
implements (1)+(2). No need for context providers; TanStack
Query's cache is the source of truth.

### Sign-up flow

`POST /_allauth/browser/v1/auth/signup` with `{ email, password }`.
On 200, invalidate the session query — TQ refetches and the
guard flips to authenticated. On non-2xx, surface the JSON
error (allauth returns structured `{ errors: [...] }` payloads).

### Sign-out flow

`DELETE /_allauth/browser/v1/auth/session`. On 200, invalidate
the session query; the guard flips back to unauthenticated.

---

## API client shape

The DRF surface (`/api/*`) is consumed via per-resource modules
in `src/lib/api/`. One module per Django app's router. Each
module exports:

- Typed request functions (e.g. `listSpokespeople()`,
  `createSpokesperson(input)`).
- zod schemas for the response shapes (e.g.
  `spokespersonSchema`).
- Optionally, TanStack Query hooks that wrap them (e.g.
  `useSpokespeople()`).

Example shape:

```ts
// src/lib/api/spokespeople.ts (pseudo)
const spokespersonSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  business_brief: z.string(),
  status: z.enum(["setup_needed", "ready", "archived"]),
  runway_avatar_id: z.string(),
  runway_avatar_status: z.string(),
  video_count: z.number().int().nonnegative(),
  created_at: z.string().datetime(),
  // ...
});

export type Spokesperson = z.infer<typeof spokespersonSchema>;

export async function listSpokespeople(): Promise<Spokesperson[]> {
  const resp = await apiFetch("/api/spokespeople/");
  if (!resp.ok) throw new ApiError(resp);
  const json = await resp.json();
  return z.array(spokespersonSchema).parse(json.results ?? json);
}

export function useSpokespeople() {
  return useQuery({
    queryKey: ["spokespeople"],
    queryFn: listSpokespeople,
  });
}
```

### Polling pattern (Video render status)

The video pipeline (SESSION 109) takes 60-120 s in real mode.
The SPA polls `GET /api/videos/{id}/` via TanStack Query's
`refetchInterval`:

```ts
useQuery({
  queryKey: ["video", id],
  queryFn: () => fetchVideo(id),
  refetchInterval: (data) =>
    data?.status === "rendering" ? 2000 : false,
});
```

When the row hits a terminal state (`ready` / `failed`), the
interval returns `false` and polling stops. No manual cleanup.

---

## First three screens (SESSION 116 scope)

Mapping to `UI_REDESIGN_V2.md` §5:

### Slice 1 — Sign-up + sign-in (`S-03` + `S-04`)

- Two route components: `/sign-in` and `/sign-up`.
- Email + password form (react-hook-form + zod).
- Submit → `POST /_allauth/browser/v1/auth/signup` or
  `.../login`.
- On success: invalidate the session query; router pushes to
  `/dashboard`.
- On failure: surface the structured allauth error.
- **Out of slice 1:** Google OAuth button. Lock the route
  shape so OAuth lands as a sibling commit when credentials
  arrive (queued investigation).

### Slice 2 — Workspace dashboard (`S-09`)

- `/dashboard` route, protected by `<RequireAuth>`.
- Header: workspace name + signed-in user + sign-out button.
- Section A: spokespeople grid. Loads via
  `useSpokespeople()`. Empty state: "Create your first
  spokesperson" CTA.
- Section B: recent videos. Loads via `useVideos()` with a
  `?limit=10` query param.
- Section C: usage meter. Reads from
  `GET /api/billing/subscription/` (SESSION 107). Renders
  "8 of 10 videos this month, Starter trial."
- **Out of slice 2:** "Make a video" CTA wiring (covered in
  Slice 4+); spokesperson creation (Slice 5+).

### Slice 3 — Spokesperson detail (`S-10`)

- `/spokespeople/:id` route, protected.
- Loads via `useSpokesperson(id)` (one-off query) and
  `useVideos({ spokesperson: id })`.
- Sections: identity (portrait + voice + business brief),
  videos library (list view), edit affordances inline.
- **Out of slice 3:** conversation threads, memory, voice-
  clone UI (each gets its own slice).

### What slice 4+ looks like

The remaining S-screens (S-05 through S-19) each land as one
slice once the foundation above is shipped. Each follows the
**same pattern as Phase 2 commits**: cross-stack atomic commit
including any necessary backend tweaks + the SPA additions +
the smoke test. Slice order will follow whatever the operator
prioritises — likely S-06/S-08 (first-spokesperson + first-
video flow) since that's the activation path.

---

## Smoke test pattern

End-to-end via Playwright. Same role as the `manage.py smoke_*`
commands play on the backend.

```
web/e2e/auth.spec.ts          # signup → dashboard renders
web/e2e/dashboard.spec.ts     # spokespeople list loads
web/e2e/spokesperson.spec.ts  # detail page loads
```

Each spec:

1. Starts a fresh Django + media-engine + Redis stack (or
   asserts they're already up).
2. Drives the SPA in a real browser context (Chromium).
3. Asserts on rendered DOM + final URL.
4. Cleans up created rows on teardown via the same
   `--keep`-aware pattern the Django smokes use (probably
   exposed via an `/api/_testing/cleanup` endpoint gated to
   `DEBUG=True` only).

Naming follows the backend convention: `*.spec.ts`.

---

## Dev workflow

```bash
# One-time setup
cd web && pnpm install

# Run alongside the backend stack
cd infra && docker compose up -d         # Redis
cd media-engine && uvicorn app.main:app --port 8001 &
cd shell && python manage.py runserver &
cd web && pnpm dev                       # Vite on :5173, proxies to :8000

# Browse http://localhost:5173
```

Vite's `server.proxy` in `vite.config.ts`:

```ts
server: {
  proxy: {
    "/api": "http://localhost:8000",
    "/_allauth": "http://localhost:8000",
    "/accounts": "http://localhost:8000",
  },
}
```

The SPA itself runs at `:5173`; everything Django-shaped is
proxied. Same-origin in dev *and* prod.

### Production build

`cd web && pnpm build` → `web/dist/`. Django serves it via
`WhiteNoise` (or similar) when Phase 3 deploy lands. The
backend gets a single new URL pattern that catches everything
not under `/api/`, `/accounts/`, `/_allauth/`, `/admin/` and
serves `index.html` for client-side routing.

---

## Out of scope (explicitly)

These are NOT being decided here. Each gets its own scope-lock
when its time comes:

- **State management beyond TQ + local state.** If we need a
  real client-side cache (Zustand etc.), it's a deliberate
  amendment, not a "well I added it for screen X."
- **Marketing site / landing page (S-01, S-02).** Likely lives
  in a sibling Next.js app or a static-site generator. Out of
  Phase 3 SPA scope.
- **Activation video library (S-19).** Player + content
  pipeline. Phase 3 sub-deliverable but not in the first three
  slices.
- **Account / billing screens (S-15 to S-18).** Land after the
  Phase 3 first-three are stable.
- **Realtime conversation (S-13).** WebRTC + WebSocket flow
  inherits the an earlier hackathon prototype implementation; needs its own
  port.
- **Admin (A-01 to A-03).** Django admin handles it for v1.
- **i18n.** English-only at launch (design lock §10).
- **Native mobile apps.** Deferred indefinitely (design lock).
  The `HEADLESS_CLIENTS = ("app",)` flag remains unset until
  this changes.
- **Service worker / PWA.** Phase 4+.
- **GraphQL.** REST is what we built; switching transports is
  not the highest-leverage Phase 3 work.

---

## Open questions (resolve as they land)

- **Q1 — Bootstrapping the dashboard before the user has any
  spokespeople.** Empty state is documented in the design lock
  (§5.2 first-run onboarding screens S-05 → S-08). The first
  three slices stop at the dashboard's empty state and skip
  the onboarding flow. When do we wire onboarding? Likely
  Slice 4 or 5 once the dashboard's empty CTA needs a
  destination.
- **Q2 — Form-level error display convention.** Field errors
  inline + a top-of-form banner for non-field-specific errors
  is shadcn's default. Confirm with the operator on the first
  real form.
- **Q3 — Loading skeleton vs. spinner.** Both are fine; pick
  one and stick with it. Recommend skeletons (less jarring on
  fast networks).
- **Q4 — Toast / notification surface.** Render mutations
  (e.g. "Spokesperson created") with toasts? shadcn ships a
  `<Toaster>` component. Likely yes; confirm when first mutation
  ships.
- **Q5 — Theme.** Dark mode default? Both modes? Brand colors?
  Defer to a "Brand Identity" doc that doesn't exist yet
  (design lock §10 explicitly defers).
- **Q6 — Sentry / error tracking.** Pre-launch; not in first
  three slices.
- **Q7 — Analytics.** PostHog vs. Plausible vs. Mixpanel.
  Design lock §9 references "analytics scaffolding" for
  activation metrics. Defer to Phase 3 deploy.

---

## Relationship to other locks

- **`UI_REDESIGN_V2.md`** (design lock) — what to build. This
  doc is its technical companion.
- **`MEDIA_ENGINE_INTERNAL_API.md`** — Django ↔ FastAPI
  contract. Untouched by the SPA; the SPA never talks to
  FastAPI directly.
- **`CHARACTER_OS_WHAT_IT_IS.md`** — narrative anchor. Add a
  Phase 3 paragraph when the first SPA slice ships.
- **`CHARACTER_OS_INVENTORY.md`** — runtime anchor. The
  inventory generator (SESSION 112) currently introspects
  Django + FastAPI only. **TODO for SESSION 117+:** extend
  the generator to count SPA routes + components when the
  shape stabilises.

---

## Change log

- 2026-05-13 (SESSION 115) — Initial scope lock. No code yet;
  SESSION 116 starts implementation.
