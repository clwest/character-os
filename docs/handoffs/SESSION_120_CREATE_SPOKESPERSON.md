---
title: "Session 120 — Create-spokesperson flow (S-06)"
date: 2026-05-13
status: complete
session: 120
previous_handoff: ./SESSION_119_CUSTOM_USER_MODEL.md
---

# Session 120 — Phase 3 Slice 4: S-06 create-spokesperson flow

## TL;DR

- **What shipped:** The `/spokespeople/new` route — editorial form
  with name + business brief + optional portrait upload. POST to
  `/api/spokespeople/`, redirect to the detail page on success.
  Dashboard empty-state has a real "Create your first spokesperson"
  CTA now. **7 Playwright specs pass** on first run (2 auth + 2
  dashboard + 1 spokesperson detail + 2 create variants).
- **What's blocking next:** Nothing. The two big-leverage remaining
  slices are S-12 (make-a-video flow) and voice clone UI. The
  spokesperson lifecycle is now closed end-to-end: create →
  detail → (next) make-video.
- **What's in a weird state:** None. The slice inherited cleanly
  from SESSIONS 117 (aesthetic) + 118 (panel patterns) +
  119 (User model).

---

## What changed (file-by-file)

### `web/src/lib/api/spokespeople.ts`

Added `createSpokesperson(input)` + `useCreateSpokesperson()` hook.
The mutation:

- Wraps `POST /api/spokespeople/` with zod-parsed response.
- `onSuccess` invalidates `["spokespeople"]` (dashboard
  refreshes), seeds `["spokesperson", id]` (detail page
  renders instantly on redirect), and invalidates
  `["subscription"]` (usage meter reflects the new
  spokesperson count immediately).

### `web/src/components/portrait-upload.tsx` (new)

Drag-and-drop + click upload. Validates client-side:

- Allowed mimes: png, jpeg, webp.
- Size cap: 5 MB (matches backend's decoded cap).
- File → base64 via FileReader.

Two states: dropzone (dashed border, upload icon, hint text)
and preview (thumbnail + filename + size + Remove button).
Keyboard-accessible via Enter/Space on the dropzone wrapper.

### `web/src/routes/spokespeople/new.tsx` (new)

The route. Inherits SESSION 117/118 patterns:

- Editorial masthead with back-to-dashboard kicker, "New
  spokesperson" label, "Define / the spokesperson." display
  serif headline, short body copy explaining what's happening.
- Three FieldGroup blocks (name, business brief, portrait)
  with the SESSION 117 uppercase-tracked-out label pattern
  + per-field hint copy + per-field error display.
- Submit button on the right of a border-top footer; cancel
  link on the left.
- Two distinct error surfaces:
  - **Tier-limit callout** for HTTP 402 responses — uses the
    structured payload from the backend's
    `TierLimitExceeded.payload` (current_tier + suggested_tier +
    message). Editorial styling, oxblood-tinted, names the
    upgrade path.
  - **Generic error row** for everything else (network,
    validation, 5xx).

On success: `navigate(/spokespeople/${sp.id}, replace: true)`.

### `web/src/App.tsx`

Registers `/spokespeople/new` behind `<RequireAuth>`. Order
matters in React Router v7 — `/new` is registered BEFORE
`/:id` so it doesn't get swallowed by the dynamic route.

### `web/src/routes/dashboard/index.tsx`

Two changes:

1. `PanelHeader` got an optional `action` slot for right-aligned
   affordances. The spokespeople panel header now has a
   `+ New` link.
2. `EmptyState` got an optional `action` slot. The spokespeople
   empty-state now renders a real `Button` linking to
   `/spokespeople/new`. The placeholder copy ("you'll set up
   the first one in the next slice") is gone — replaced by the
   actual CTA.

### `web/e2e/create-spokesperson.spec.ts` (new)

Two tests:

- **No-portrait happy path** — fresh signup → empty-state CTA →
  fill name + brief → submit → land on detail page. Asserts the
  setup checklist reflects "no avatar yet."
- **With-portrait variant** — uploads a 1×1 transparent PNG via
  `setInputFiles` + `Buffer`. Asserts the preview state renders
  + the avatar status pill on the detail page shows mock/ready.

Both pass first-try.

---

## Verification gates

- `pnpm build` — clean. CSS 19.3 KB / JS 423 KB (gzip ~5 / ~127).
- `pnpm test` — 3 vitest passes.
- `pnpm e2e` — **7 passes** (the SESSION 119 set + 2 new).
- `python manage.py check` — clean (allauth deprecation warnings
  are the SESSION 119 intentional ones, unchanged).
- `python manage.py smoke_headless_auth` — PASS.
- `python manage.py inventory` — clean regen.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The spokesperson lifecycle is now end-to-end

Before SESSION 120, the detail page existed but the only way to
populate a spokesperson was via Django admin or a smoke test.
After SESSION 120, the SPA covers:

  dashboard empty state → /spokespeople/new → form → POST →
  redirect to /spokespeople/{id} → renders identity, setup
  checklist, empty videos list

The next slice (S-12 make-a-video) closes the loop again:
detail page → make-video CTA → render → poll → playback.

### Portrait upload is the first binary payload through the SPA

Up to this point the SPA only POSTed JSON. The portrait flow
introduces the first binary handoff: File → FileReader →
`data:image/...;base64,...` data URI → JSON body. The decision
to keep the contract pure-JSON (locked in SPA_ARCHITECTURE.md
rule 1) means the SPA does the base64 conversion, not the
server. Net cost: ~50 lines of FileReader/validation code.
Net reward: zero multipart parsing on the Django side, smaller
WAF/CORS surface, simpler dev proxy.

### Two error surfaces, not one

The form distinguishes "tier limit reached" (structured HTTP
402 payload) from generic errors. The tier-limit callout names
the suggested upgrade path. This is the pattern S-12 should
reuse for video-limit-reached + S-15 for billing screens.

### Inheriting the aesthetic was the work-multiplier

Zero new design tokens. Zero new color decisions. Zero new
font additions. Every component in this slice references
something already locked in BRAND_IDENTITY_V1 + the panel
patterns SESSION 117 established. The slice landed in roughly
40 minutes start-to-tests-passing, including writing this
handoff.

### PanelHeader + EmptyState slot extension

Both atoms got an optional `action` slot. This is a real React
component-evolution pattern — start with two args (title +
count for the header, headline + body for the empty state),
extend with optional slots when a third use surfaces. Resist
turning them into render-props or component-injection patterns
until 4+ uses share the structure.

---

## SESSION 121 — entry point

`00-START-NEXT-SESSION.md`. Recommended: **S-12 Make-a-video
flow.** The biggest remaining slice in the Phase 3 plan and the
last major lifecycle gap. The fire-then-poll backend (SESSION
109) is ready; this slice is a full session of frontend work.

Alternatively: voice clone UI on the detail page (backend ready
since SESSION 110, smaller scope), or the stuck-row janitor
(operational hardening before S-12 lands).

---

## AI notes

- 40-minute slice. The aesthetic lock + the panel patterns are
  doing their job — pattern matching against existing code is
  faster than invention.
- The portrait-upload component is the first slot where we
  ship something shadcn doesn't provide. It's still small +
  composable + uses only existing tokens. Worth checking if a
  shadcn/ui contributor pattern lands later that does the same;
  if so, swap.
- The Playwright `setInputFiles` + Buffer trick is the right
  way to test file uploads without fixture files. The same
  1×1 transparent PNG buffer the backend smokes use works
  identically through the SPA's FileReader path.
- React Router v7's static-first routing: `/spokespeople/new`
  must be registered before `/spokespeople/:id`. Otherwise
  React Router swallows "new" as an id and the detail page
  tries to fetch a spokesperson named "new" (404 from
  Django). Easy to get wrong; the test caught it immediately.
- The "two error surfaces" pattern (tier-limit callout + generic
  row) is genuinely worth keeping for future forms. Worth
  flagging in a future component-extraction pass if a third use
  appears.
