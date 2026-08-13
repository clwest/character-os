# character-os SPA (`web/`)

Vite + React + TypeScript + Tailwind + shadcn/ui. Talks to the
Django shell at `http://localhost:8000`. Scope lock:
[`docs/design/SPA_ARCHITECTURE.md`](../docs/design/SPA_ARCHITECTURE.md).

## Quickstart

```bash
# One-time
corepack enable pnpm
pnpm install

# Day-to-day (assumes Django + Redis are up — see repo root docs)
pnpm dev          # Vite on :5174, proxies /api + /_allauth to :8000
pnpm build        # type-check + production bundle to dist/
pnpm test         # vitest, schema + unit smoke
pnpm e2e          # Playwright auth smoke (needs Django up on :8000)
pnpm e2e:install  # one-time browser download
```

## Layout

```
src/
  main.tsx               # entry; QueryClientProvider + StrictMode
  App.tsx                # router root
  lib/
    api/
      client.ts          # fetch wrapper + CSRF + JSON envelope
      auth.ts            # /_allauth/* operations + zod schemas
    auth/
      use-session.ts     # TanStack Query hooks (session, signup,
                          # signin, signout)
      require-auth.tsx   # router guard
    utils.ts             # shadcn `cn(...)` helper
  routes/
    _layout.tsx
    sign-up.tsx
    sign-in.tsx
    dashboard/
      index.tsx
  components/
    ui/                  # shadcn primitives (button, input, label, card)
  styles/
    globals.css          # Tailwind + shadcn tokens
e2e/
  auth.spec.ts           # Playwright smoke
```

## Contract rules (from SPA_ARCHITECTURE.md)

1. Same-origin in production. Django serves `dist/`.
2. Session-cookie auth via `/_allauth/browser/v1/*`. No tokens.
3. Server state via TanStack Query; local state via React.
4. Forms via react-hook-form + zod.
5. Routing via React Router v6.
6. No silent error suppression.

Amendments require updating `docs/design/SPA_ARCHITECTURE.md`,
not an in-PR drift.

## Stack-up

Backend (in separate terminals from this app):

```bash
cd infra && docker compose up -d           # Redis :6381
cd media-engine && uvicorn app.main:app --port 8001
cd shell && python manage.py runserver
cd shell && celery -A character_os worker --pool=solo  # video pipeline only
```

Then `pnpm dev` here.

## Tests

- **Vitest** (`pnpm test`) — schema + unit tests. Fast, hermetic.
- **Playwright** (`pnpm e2e`) — end-to-end through a real browser.
  Requires Django up on `:8000`.

`pnpm test` is what runs in CI; Playwright is local-only until the
deploy story lands.
