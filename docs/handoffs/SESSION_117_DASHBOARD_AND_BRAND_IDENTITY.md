---
title: "Session 117 — Workspace dashboard + Brand Identity v1"
date: 2026-05-13
status: complete
session: 117
previous_handoff: ./SESSION_116_SPA_AUTH_SCAFFOLD.md
---

# Session 117 — Phase 3 Slice 2 + editorial-warm aesthetic lock

## TL;DR

- **What shipped:** Slice 2 of Phase 3 — the real `/dashboard` route.
  Replaces SESSION 116's placeholder with a populated editorial-warm
  workspace dashboard (S-09 of the design lock): masthead with the
  workspace name in display serif, primary "Make a video" CTA panel,
  spokespeople grid with empty-state, recent renders numbered list,
  hairline usage meter. Auth screens (sign-up + sign-in) reskinned
  to match. **4 Playwright specs pass end-to-end.**
- **What also shipped:** `docs/design/BRAND_IDENTITY_V1.md` — the
  v1 aesthetic lock. Fraunces (variable serif display) + Geist Sans
  (body) + JetBrains Mono (mono), paper bg `#f5efe5`, deep ink fg,
  oxblood `#84231e` accent for primary actions. Light-mode only;
  dark mode + brand logomark deferred.
- **What's blocking next:** Nothing. SESSION 118 ships Slice 3
  (spokesperson detail, S-10).
- **What's in a weird state:** The "Make a video" button is disabled
  until S-12 (make-a-video flow) lands. The empty-state copy on
  the spokespeople panel reads "you'll set up the first one in the
  next slice" — that's literal: S-06 (create first spokesperson)
  is its own future slice.

---

## What changed (file-by-file)

### `docs/design/BRAND_IDENTITY_V1.md` (new)

The v1 aesthetic lock. Editorial-warm direction, all color tokens
in HSL, font choices justified, motion language ("restrained"),
spatial composition (8px rhythm, 1152px container max), explicit
out-of-scope list. Companion to UI_REDESIGN_V2.md + SPA_ARCHITECTURE.md;
single-file override path documented.

The key bet: the audience (solo creators + non-marketer SMBs) is
served better by *"this is for people who run a business, not a
hobby"* than by enterprise blue or trendy purple. Paper-and-ink
typography signals craft without signaling "expensive enterprise
tool." The oxblood accent is the **one thing someone will
remember** — a singular decisive color in an otherwise quiet
surface.

### `web/index.html`

Preconnect + Google Fonts stylesheet for Fraunces (variable, full
axes), Geist (300-700), and JetBrains Mono (400, 500). `display=swap`
so the page paints with fallbacks while fonts load — Geist falls
back to system sans cleanly, Fraunces to serif.

### `web/src/styles/globals.css`

Token rewrite. New HSL values for the paper/ink/oxblood palette,
Fraunces variable-axis setup (`opsz`, `SOFT`, `WONK` via
`font-variation-settings`), JetBrains Mono code/kbd/samp/pre
override, ::selection rule using oxblood at 18% alpha, body
background with two soft radial gradients for warm paper texture.

New `.reveal` utility class + `@keyframes reveal` for the staggered
card entrance. Cards set `--reveal-delay` inline; CSS handles the
rest. Pure CSS, no JS animation library.

### `web/tailwind.config.ts`

Added `fontFamily` (`sans`, `serif`, `mono`, `display`) and
`boxShadow` (`paper`, `paper-hover`). Tokens still pull from CSS
variables so dark mode + future re-themes are a one-file change.

### `web/src/lib/api/workspaces.ts` (new)

`getMe()` + `useMe()` wrap `GET /api/me/`; `getSubscription()` +
`useSubscription()` wrap `GET /api/billing/subscription/`. Each
zod-parsed at the boundary. TanStack Query staleTime tuned: 5min
for identity (rarely changes), 60s for tier+usage (refreshes
more often). Both backends shipped pre-SESSION 117 — no Django
changes needed.

### `web/src/lib/api/spokespeople.ts` (new)

`listSpokespeople()` + `useSpokespeople()`. Tolerates either a
DRF paginated envelope (`{count, results}`) or a bare array, so
when pagination flips on later the SPA doesn't break.

### `web/src/lib/api/videos.ts` (new)

Same shape as spokespeople. `listVideos({limit, spokesperson})`
accepts the recent-N or by-spokesperson filtering the SPA needs
in this and future slices.

### `web/src/components/spokesperson-card.tsx` (new)

Editorial tile. Initials-in-Fraunces portrait until real avatars
land (kicks in `portrait_path` is empty), display-serif name,
muted body copy snippet, hairline-divided footer with status
pill + monospace video count. Hover lifts via `shadow-paper-hover`.
Accepts `revealDelay` for staggered entrance.

### `web/src/components/video-row.tsx` (new)

"Magazine numbered list" form. Zero-padded display-font index
(01, 02, 03), display-serif title, monospace kicker line
(spokesperson · kind · relative time), status dot at right.

### `web/src/components/usage-meter.tsx` (new)

Hairline progress with display-font count + tier-name kicker.
Three states: under-limit (foreground/60 fill), warning ≥80%
(primary/oxblood fill), over-limit (destructive fill). Unlimited
tier shows a "Unlimited on agency" caption instead of a meter.

### `web/src/routes/dashboard/index.tsx`

Full rewrite. Five vertical sections (masthead → primary action
→ spokespeople grid + usage meter → recent renders), each with
its own reveal delay so the page assembles itself over ~300ms.
Loading skeletons matching the final layout. Error rows in
oxblood-tinted boxes. Empty states with editorial copy.

Composes `useSession + useMe + useSubscription + useSpokespeople +
useVideos` — five parallel TanStack Query calls, fired on mount,
cached independently.

### `web/src/routes/_layout.tsx`

Outer chrome added: SiteHeader (Character / OS wordmark) + content
well + SiteFooter (monospace caption). Auth routes get a narrow
centered container; dashboard gets the full 1152px max. Still
fires `useSession()` at the root for CSRF cookie bootstrap.

### `web/src/routes/sign-up.tsx` + `sign-in.tsx`

Reskinned. Display-font headers ("Start your workspace." / "Sign in.")
with kicker labels above them. Custom Field rendering with uppercase
tracked-out labels above each input. Submit buttons in oxblood. Same
form validation + mutation logic; just dressed for the new aesthetic.

### `web/e2e/dashboard.spec.ts` (new)

Two specs:
- **Empty-state dashboard** — fresh signup → masthead with auto-
  derived workspace name, primary action panel headline, both
  empty-state callouts, usage meter showing "0 / 10" + "Starter"
  + "Trialing".
- **Sign-out flow** — signup → sign-out → /sign-in, and a
  protected-route probe (`/dashboard` after sign-out) bounces
  back to /sign-in.

### `web/e2e/auth.spec.ts`

Trimmed. The happy-path test no longer asserts on the placeholder's
`auth-confirm` testid (gone). Now just asserts the redirect to
`/dashboard`; the dashboard's own spec is the authoritative test
for what lands there.

### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated.

---

## Verification gates

- `pnpm build` — clean. Bundle ~16 KB CSS / ~402 KB JS (gzip
  ~4.4 KB / ~122 KB).
- `pnpm test` — 3 vitest passes (auth schema smoke).
- `pnpm e2e` — **4 passes** (2 auth + 2 dashboard).
- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — clean.
- `python manage.py smoke_headless_auth` — PASSES (cascade still
  fires through headless flow).
- `python manage.py inventory` — clean regen.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The frontend-design plugin earned its keep

The plugin's load surface is a single skill that injects strong
aesthetic guidance: "commit to a BOLD aesthetic direction," "avoid
generic AI-generated aesthetics like Inter / purple gradients /
Space Grotesk," "match implementation complexity to vision."
Without it, the natural pull would have been a default shadcn
neutral + Inter dashboard — competent, generic, AI-flavored.

With it, the slice committed early to editorial-warm and executed
through. Net cost: ~5 minutes of "pick the aesthetic" framing.
Net win: a dashboard that doesn't look like every other Tailwind/
shadcn app.

### Why land BRAND_IDENTITY_V1 now and not later

SPA_ARCHITECTURE.md Q5 explicitly deferred theme + brand to a
future doc. SESSION 117 forced the question — you can't build the
dashboard without making a color decision. The shadcn-default
gray was placeholder; landing real choices now gives every
SESSION 118+ slice a coherent surface to inherit. Revisiting is
a single-file override (documented at the bottom of the doc), so
the lock is cheap to undo.

### The empty-state IS the first-run UX

A fresh signup lands on a dashboard with two empty states + a
disabled primary action. That sounds bad, but it's the correct
state: the user has no spokespeople and no videos yet. The empty
states do real work — the spokespeople empty-state explicitly
sells what a spokesperson is ("a portrait, a voice, a one-paragraph
business brief") and the recent-renders empty-state explains the
~60-120s rendering time. By the time S-06 (create first spokesperson)
ships, this empty-state copy doubles as a first-run preview.

### Five parallel API calls is fine

The dashboard composes `useSession`, `useMe`, `useSubscription`,
`useSpokespeople`, `useVideos`. All fire on mount, parallel. With
HTTP/1.1 dev proxy, 5 sub-100ms requests land in <200ms total.
Each cached independently — re-rendering a section doesn't refetch.
TanStack Query was the right choice.

### Skeletons > spinners, confirmed

Every loading state in the dashboard uses a structural skeleton
that mirrors the final layout. The page never reflows on load;
content swaps in place. Spinners would have been ~10 lines less
code, but every user-perceived load would have a layout shift +
a "where's my data" microsecond. The skeleton pattern is now the
project default (documented in BRAND_IDENTITY_V1.md §Motion).

---

## SESSION 118 — entry point

See `00-START-NEXT-SESSION.md`. Slice 3: spokesperson detail
(S-10). Renders one spokesperson + their videos, with inline edit
affordances and the first real surface where the avatar/voice
status pills do work.

---

## AI notes

- This was the most aesthetically ambitious slice in the project
  so far. The frontend-design plugin's guidance was directly
  load-bearing — without "commit to bold direction" + "avoid
  generic AI aesthetics" as explicit instructions, the default
  pull would have been bland.
- The hour from "lets do it" to "all 4 specs pass" was tight
  because:
  1. BRAND_IDENTITY_V1 was written *first*, before any component
     code. Every component referenced tokens, not hex.
  2. TS error count was 2, both fixed in one edit (`unknown &&
     ReactNode` → `unknown ? ReactNode : null`).
  3. Backend was already complete — no Django changes needed.
  4. Playwright specs were written against testids defined while
     writing the components, not bolted on after.
- The "five sections, five reveal delays" composition is a real
  pattern. The dashboard assembles itself in ~300ms via pure CSS
  + inline `--reveal-delay` style props. Worth flagging in
  BRAND_IDENTITY_V1.md's motion section if a fourth use-site
  appears.
- The skill description literally says: "Bold maximalism and
  refined minimalism both work — the key is intentionality, not
  intensity." I went refined-with-character (paper + serif +
  one bold accent). That choice was the right one for this
  audience; another product (gaming, social, kids) would
  warrant the other end of the dial.
