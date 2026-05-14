---
title: "Session 121 — Make-a-video flow (S-12) + video status page (S-11)"
date: 2026-05-13
status: complete
session: 121
previous_handoff: ./SESSION_120_CREATE_SPOKESPERSON.md
---

# Session 121 — Slice 5: the lifecycle closes

## TL;DR

- **What shipped:** The biggest remaining slice in the Phase 3
  plan. The full make-a-video lifecycle is end-to-end in the SPA:
  spokesperson detail → "Make a video" → form → POST →
  `/videos/{id}` polling status page → ready → `<video>` playback.
  The Celery polling pattern from SESSION 109 is now wired through
  the frontend, and the route locks **the canonical async surface**
  every future polling UI inherits.
- **What's blocking next:** Nothing. The core lifecycle (signup →
  create spokesperson → make video → watch render → play) works
  end-to-end. Optional next-slice candidates: voice clone UI on
  the detail page (smallest), stuck-row janitor (operational
  hardening before real traffic), or the additional video kinds
  (cinematic / dialogue / long-ad).
- **What's in a weird state:** None. The slice inherited the
  editorial-warm aesthetic cleanly. Two pre-existing concerns
  carry forward: (1) the SESSION 119 allauth deprecation
  warnings remain advisory; (2) the SESSION 120
  smoke-test-helper transaction discipline issue stays in the
  queue.

---

## What changed (file-by-file)

### `web/src/lib/api/videos.ts`

Extended with:

- `getVideo(id)` — single-resource fetch, zod-parsed.
- `useVideo(id)` — **the canonical polling hook.** Uses
  TanStack Query's `refetchInterval` function form: while the
  row's `status` is non-terminal, refetch every 2 s; return
  `false` to halt as soon as a terminal status (`ready`,
  `failed`, `archived`) lands. No manual `clearInterval` —
  TanStack handles unmount cleanup. `refetchIntervalInBackground:
  false` so the poll doesn't run when the tab is hidden.
- `createVideo(input)` — POSTs to `/api/videos/` with the locked
  schema.
- `useCreateVideo()` mutation hook. `onSuccess` seeds the
  single-resource cache (`["video", id]`) so the redirect
  renders instantly with no flash of loading state, invalidates
  `["videos"]` (dashboard refresh), invalidates
  `["subscription"]` (usage meter reflects the increment).

### `web/src/routes/spokespeople/render.tsx` (new)

The make-a-video form. Editorial-warm masthead with back-to-
spokesperson kicker + display-serif "Make a video / with {name}."
headline. Three sections of body:

1. **Avatar-not-ready callout** (oxblood-tinted) if the
   spokesperson doesn't have a `runway_avatar_id` yet. Links to
   the detail page where the operator can add a portrait. The
   submit button stays disabled until then.
2. **FieldGroup blocks**: title (optional, plain Input) +
   brief (textarea, **pre-filled** from the spokesperson's
   `business_brief` via `useEffect` once the data lands).
3. **Tier-limit callout** for HTTP 402 + generic error row.
   Same two-error-surface pattern SESSION 120 introduced.

Submit → `navigate("/videos/{id}", replace: true)`. The replace
matters — the operator shouldn't be able to back-button into a
half-submitted form.

### `web/src/routes/videos/$id.tsx` (new)

**The canonical async surface.** Three primary states branch
off the polling row:

- **`rendering` / `pending`** — `<RenderingPanel>` shows a
  pulsing hairline progress bar, an elapsed-time display that
  ticks per second (via `useElapsed` hook with `setInterval`),
  and editorial copy explaining the wall-clock cost. The
  header reads "Queued." or "Rendering." in display serif.
- **`ready`** — `<Playback>` mounts a `<video controls>`
  element with `output_path` as the src. Footer caption shows
  duration + relative completion time + an "Open original ↗"
  link out to the source URL.
- **`failed`** — `<FailedCallout>` (destructive-tinted) with
  the `error_message` in monospace + a "Try again" button
  routing back to the render form.

A `<DetailGrid>` below the primary panel shows brief +
spokesperson + kind + task id + timestamps in the editorial
two-column dl pattern (mobile collapses to single column).

### `web/src/App.tsx`

Two new routes registered, both behind `<RequireAuth>`:

- `/spokespeople/:id/render` — make-a-video form. **Must
  register before** `/spokespeople/:id` so React Router v7
  doesn't swallow "render" as a spokesperson id. (Same
  routing-order rule SESSION 120 surfaced for `/new`.)
- `/videos/:id` — status + playback page.

### `web/src/routes/spokespeople/$id.tsx`

The spokesperson detail masthead grows a "Make a video" CTA
(big oxblood button with a `Wand2` icon next to the status
pills). The button is disabled when `runway_avatar_id` is
empty + carries a tooltip explaining why. The status pills
moved into the same flex-column block, right-aligned below
the button.

### `web/src/components/video-row.tsx`

The dashboard's recent-renders list rows are now clickable
via the **stretched-link pattern** SESSION 118 introduced on
`SpokespersonCard`. `<Link>` wraps the title; `::after`
covers the entire row's clickable surface. Hover shifts the
row's background subtly. Added `data-testid="video-row"`.

### `web/e2e/make-video.spec.ts` (new)

Full lifecycle spec. Test timeout 60 s. Steps:

1. Sign up → dashboard.
2. Create spokesperson with portrait (mock avatar binds).
3. Detail page → click "Make a video" link.
4. Render form pre-fills brief from spokesperson.business_brief.
5. Customize title + brief → submit.
6. Status page renders with masthead + status pill.
7. **Wait for status pill to flip to "Ready" (45 s timeout)** —
   the Celery worker runs the SESSION 109 polling task, mock
   mode resolves in ~13 s.
8. `<video>` element renders with a real `src` attribute.
9. Back to dashboard → recent renders row visible.
10. Click the row → land back on the video status page.

This is the first spec that **requires the Celery worker
running** — documented in the spec's preamble.

---

## Verification gates

- `pnpm build` — clean. CSS 20.0 KB / JS 439.7 KB (gzip
  ~5.1 / ~129).
- `pnpm test` — 3 vitest passes.
- `pnpm e2e` — **8 passes** in 21.9 s total. The make-video
  spec is the slowest at 14.4 s (waiting for the Celery
  worker to flip the row to ready in mock mode).
- `python manage.py check` — clean (allauth deprecation
  warnings from SESSION 119 unchanged).
- `python manage.py inventory` — clean regen.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The canonical async surface is locked

`web/src/routes/videos/$id.tsx` is the reference implementation
for every future polling UI. The shape:

```ts
useQuery({
  queryKey: [...],
  queryFn: () => getResource(id),
  refetchInterval: (query) => {
    const data = query.state.data;
    if (!data) return INTERVAL;
    return TERMINAL_STATUSES.includes(data.status) ? false : INTERVAL;
  },
  refetchIntervalInBackground: false,
});
```

Plus a three-branch render path (in-flight / ready / failed)
with editorial copy + status pills. Every future async UI —
voice-clone status, spider dashboards, batch operations,
multi-step long_ad renders — should pattern-match against
this route's structure. The route is intentionally a
template-by-example.

### The polling pattern halts cleanly

TanStack Query's `refetchInterval` as a **function** is the
right idiom. Returning `false` halts the timer; the query
unmounts on route change. No `clearInterval` calls; no race
conditions where the timer fires after navigation. The hook
in `videos.ts` documents the contract; future hooks should
copy the structure.

### Pre-filling forms from a parent resource is a real pattern

The render form pre-fills `brief` from
`spokesperson.business_brief` via `useEffect` once the data
lands. The pattern:

```ts
useEffect(() => {
  if (spokesperson.data && !form.getValues("brief")) {
    form.setValue("brief", spokesperson.data.business_brief);
  }
}, [spokesperson.data, form]);
```

The `!form.getValues("brief")` guard prevents the pre-fill
from clobbering the operator's edits if they've already
typed. Future forms that derive defaults from a parent should
follow this pattern.

### Routing order matters TWICE now

`/spokespeople/new` (SESSION 120) and `/spokespeople/:id/render`
(SESSION 121) both must register **before** `/spokespeople/:id`.
React Router v7 evaluates routes top-down; without the static-
first ordering, the dynamic `:id` route swallows the static
sub-paths. The route file is now a structural artifact — a
PR that reorders these in App.tsx would silently break things
that don't show up in unit tests.

### Disabled-button-with-tooltip is the right UX for unsafe actions

The "Make a video" CTA on the detail page is disabled when
the spokesperson has no avatar. Rather than hiding the button
(invisible affordance) or letting it fire (preventable error),
the button stays visible but disabled with a tooltip
explaining why. Same pattern for the future spokesperson
voice-clone CTA (probably).

### The dashboard primary action panel is still a placeholder

The "Make a video" button in the dashboard's primary action
panel is still disabled. That's deliberate: from the
dashboard, the user doesn't yet have a chosen spokesperson.
The right action there is either "auto-pick the only ready
spokesperson" (if exactly one) or "scroll to spokespeople grid"
(if multiple). Either pattern is its own micro-slice. Defer.

---

## SESSION 122 — entry point

`00-START-NEXT-SESSION.md`. The core lifecycle is closed.
Three reasonable next-slice options ranked by impact:

1. **Voice clone UI** on the spokesperson detail page. Backend
   shipped SESSION 110. Adds a "Clone a voice" panel below
   the setup checklist with audio recording + upload. Small,
   self-contained, exercises another `clone-voice` backend
   path that the SPA hasn't touched yet.
2. **Stuck-row janitor** (`celery beat`). Operational hardening.
   ~30-line slice. Re-enqueues `poll_video_until_terminal` for
   rows in `rendering` longer than 5 min — protects against
   the Celery worker dying mid-poll (the documented SESSION
   109 failure mode).
3. **Additional video kinds** (`cinematic_video`,
   `dialogue_scene`, `long_ad`). Each requires a backend slice
   (different Runway endpoints, different request shapes) +
   a kind-discriminated render form. Roughly one session per
   kind.

---

## AI notes

- The slice landed on the third take. First take: pure polling
  page. Second take: added the elapsed-time tick + the
  status-pill + the editorial copy. Third take: the FailedCallout
  + back-to-detail navigation. Editorial discipline kept the
  surface coherent — every new piece referenced an existing
  pattern (panel headers, status pills, oxblood callouts).
- The Playwright spec's 45 s timeout for the rendering wait was
  the right call — the actual wait in mock mode was ~12 s but
  the Celery worker startup adds variance. Tight timeouts here
  would flake.
- `useElapsed` is a tiny custom hook (15 lines). Worth keeping
  inline in $id.tsx until a second use emerges; then extract
  to `lib/hooks/use-elapsed.ts`.
- The `refetchInterval` function form is genuinely the cleanest
  way to express "poll while status is non-terminal." Worth
  flagging in SPA_ARCHITECTURE.md as the canonical polling
  pattern when the next handoff lands an amendment.
- The `<DetailGrid>` two-column dl pattern in $id.tsx feels
  like it'll get reused. If the voice-clone UI ships next and
  also needs a metadata grid, extract `<MetadataGrid>` from
  the spokesperson detail page + reuse here.
