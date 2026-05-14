---
title: "Session 118 — Spokesperson detail (S-10)"
date: 2026-05-13
status: complete
session: 118
previous_handoff: ./SESSION_117_DASHBOARD_AND_BRAND_IDENTITY.md
---

# Session 118 — Phase 3 Slice 3: spokesperson detail

## TL;DR

- **What shipped:** Slice 3 of Phase 3. The `/spokespeople/:id`
  route renders one spokesperson + their videos with status pills,
  identity metadata, a setup checklist for missing pieces (avatar /
  voice), and a back-to-dashboard link. Spokesperson cards on the
  dashboard are now clickable (stretched-link pattern). 5 Playwright
  specs pass.
- **What's blocking next:** Nothing. Next slice is either S-06
  (create-spokesperson flow — without it the detail page is
  hard to reach in real use) or the custom email-as-PK User model
  (overdue band-aid replacement; queued since SESSION 116).
- **What's in a weird state:** None this session. The slice
  inherited cleanly from SESSION 117's editorial-warm aesthetic —
  no new design surface area, no new tokens, no new color
  decisions.

---

## What changed (file-by-file)

### `web/src/lib/api/spokespeople.ts`

Added `getSpokesperson(id)` + `useSpokesperson(id)`. Reuses the
existing `spokespersonSchema`. `staleTime: 15s` (tighter than the
list's default) — the detail page is where operators watch
status pills change during avatar / voice / video transitions in
future slices.

### `web/src/routes/spokespeople/$id.tsx` (new)

The detail route. Four sections, all inheriting SESSION 117's
patterns:

1. **Masthead** — back-to-dashboard kicker link with `<ArrowLeft>`
   icon, name in display serif, three status pills (Status,
   Avatar, Voice) with tone mapping to the brand's primary/destructive/
   muted families.
2. **Identity panel** — `[14rem, 1fr]` grid: portrait (image or
   initials-in-Fraunces) + business brief + 4-row metadata grid
   (avatar id, voice id, created, updated) in monospace.
3. **Renders** + **Setup** side-by-side at `lg`. Renders panel
   reuses `<VideoRow>` and the same empty-state copy approach.
   Setup panel is a numbered editorial checklist: 3 items
   (business brief, Runway avatar, voice), each crossed-through
   when done. When all are done, the panel collapses to "Ready
   to render. Everything this spokesperson needs is in place."
4. **Error / loading states** — DetailSkeleton matches final
   layout; DetailError surfaces "back to workspace" CTA.

The setup panel is the first place the SPA explicitly names
**future slices** in the UI: avatar setup body reads "Ships with
create-spokesperson (S-06)", voice body reads "Voice clone UI ships
in a later slice." Honest scoping vs. mystery-meat "coming soon".

### `web/src/App.tsx`

Added `/spokespeople/:id` route, gated by `<RequireAuth>`.

### `web/src/components/spokesperson-card.tsx`

Card is now clickable via the **stretched-link pattern**:

- Card stays an `<article>` (semantic) with `relative`
  positioning.
- Name `<h3>` wraps a `<Link to={...}>` whose `::after`
  pseudo-element absolutely-covers the entire card. Result: the
  whole card surface is a click target, but the inner content
  (status pill, video count) keeps its semantics + is selectable.
- Hover state added: subtle `-translate-y-px` lift + the existing
  `shadow-paper-hover` shadow. Focus-within ring on the card
  matches the Brand Identity v1 oxblood ring color.
- `data-testid="spokesperson-card-link"` for Playwright.

### `web/e2e/spokesperson.spec.ts` (new)

End-to-end spec. Signs up a fresh user, reads the workspace id
from `/api/me/`, POSTs a spokesperson via `page.request` (shares
cookies + the page's csrftoken with `X-CSRFToken` header),
reloads the dashboard, clicks the card name, asserts the detail
page renders correctly. Cleanly tests the empty-state version
(no portrait → no avatar bound → setup checklist not-done rows).

---

## Verification gates

- `pnpm build` — clean. ~18.7 KB CSS / ~414 KB JS gzip-friendly.
- `pnpm test` — 3 vitest passes.
- `pnpm e2e` — **5 passes** (2 auth + 2 dashboard + 1 spokesperson).
- `python manage.py check` — 0 issues.
- `python manage.py smoke_headless_auth` — PASSES.
- `python manage.py inventory` — clean regen.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Editorial inheritance works

This is the first session where SPA work happened entirely inside
the locked aesthetic — no new tokens, no font additions, no color
choices, no spacing inventions. Every component referenced
something already established:

- `PanelHeader` + `EmptyState` patterns from SESSION 117 dashboard
- `VideoRow` component reused verbatim
- Status pill tone families (`primary/destructive/muted`) match
  the dashboard's `SpokespersonCard` badge
- Display-serif headers + uppercase-tracked kickers from the
  masthead pattern

This is what the BRAND_IDENTITY_V1 lock buys: subsequent slices
are mostly composition.

### Stretched-link beats wrapping everything in `<Link>`

Wrapping an entire card in `<Link>` works but loses semantics
(nested `<h3>` inside `<a>` confuses screen readers, and the
status pills can't have their own interactive behaviors later).
The stretched-link pattern keeps:

- The `<article>` semantic intact
- Each interactive child can still have its own focus state
- The card's entire surface stays clickable
- Hover + focus-within styles light up correctly

Pattern: `position: relative` on card, `position: absolute; inset: 0`
on `link::after`. Works in Tailwind via `after:absolute after:inset-0`.

### Setup checklist as scope-honesty

The setup panel literally tells the user "this lands in S-06" /
"this lands in a later slice." This is the right shape for a v1
where the SPA outpaces the underlying flow: rather than disable
the missing actions silently or invent placeholder UI, name what's
coming and let the user understand they're seeing genuine work-
in-progress. Removes the "is this product abandoned?" anxiety the
empty UI would otherwise create.

### The Playwright spec demonstrates the SPA-as-test-driver pattern

The spec uses `page.request.post` to create a spokesperson via
the SPA's own API surface (`/api/spokespeople/`). This is more
honest than seeding via Django ORM directly: it confirms the
endpoint accepts the SPA's request shape (CSRF cookie + header,
authenticated session, JSON body) end-to-end. When the
create-spokesperson UI ships (S-06), the underlying flow it
exercises is the same one this test already validates.

---

## SESSION 119 — entry point

See `00-START-NEXT-SESSION.md`. Two parallel-safe options ranked
by impact:

1. **S-06: Create-spokesperson flow.** The piece that makes the
   detail page reachable in real use. Form with name +
   business_brief + portrait upload, POST to `/api/spokespeople/`.
   Reuses the SESSION 116 backend (already supports portrait_data_uri).
2. **Custom email-as-PK User model.** Overdue band-aid replacement.
   Doesn't touch SPA. Cleanest landing window is **before**
   SESSION 119's UI work since it'll affect any new sign-up code
   paths.

Recommend (2) → (1) if scope allows both in one session. Doing
(1) first means signups still flow through the band-aid; doing
(2) first lets (1) test against the real path.

---

## AI notes

- Smoothest slice in the project. Wrote the route + the API
  wrapper + the Playwright spec + the card-link change in roughly
  one pass with zero TS errors and one e2e pass on first run.
  That's what an aesthetic + scope lock buys.
- The setup-panel pattern (numbered editorial checklist with
  cross-throughs, references to future slice names) is a real
  product idiom worth keeping. Removes the "what's this empty box
  for?" confusion that plagues empty-state UI.
- `useParams` + `Number(useParams().id)` patterns — wrapped via
  the `useSpokesperson(id)` hook's `enabled: Boolean(id)` flag
  so the query doesn't fire on invalid params. Belt + braces; if
  someone hits `/spokespeople/` without an id, the route never
  matches anyway.
- The stretched-link pattern is going to need its own component
  if a fourth use shows up (videos, conversations, etc all
  benefit). Add to the queued-investigations list.
- One thing I noticed mid-build: `data-testid="spokesperson-name"`
  on the masthead is unique to the detail page, but
  `data-testid="workspace-name"` on the dashboard is similarly
  named. Both work; consider a project-wide convention later
  ("dashboard-workspace-name" vs "detail-spokesperson-name") if
  testids start colliding.
