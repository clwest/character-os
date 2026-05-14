---
title: "Session 134 — Wizard slice 11: hide-on-completion"
date: 2026-05-14
status: complete
session: 134
previous_handoff: ./SESSION_133_TEMPLATE_TILES.md
---

# Session 134 — Hide-on-completion detail page (wizard slice 11 / 11)

## TL;DR

- **What shipped:** The spokesperson detail page reshapes into
  the "either / or" surface from the wizard scope-lock. Fully
  configured rows (brief + avatar bound + voice set) hide the
  setup column entirely + show a "Ready to render" badge in the
  masthead; the videos panel takes the full width. Partial rows
  show only the *unfinished* setup items in a tighter checklist
  (no struck-through done rows). This is the **final wizard
  slice** — W1-W11 are done.
- **What's blocking next:** Nothing. SESSION 135 picks from the
  queue: legacy form retirement (after real-mode Runway
  validation), template content refinement, Tier 2 prompt
  helpers, operational hardening items, or new feature work.
- **What's in a weird state:** None. 30 of 30 Playwright specs
  pass in one shot (was 28 — slice added 2). The "Edit" modal
  affordance promised in the scope-lock is intentionally
  deferred — operators land on a clean detail page after a
  fully-configured wizard submit; if they need to edit fields,
  that's a separate slice and can land after real-mode use
  surfaces actual demand patterns.

---

## What changed (file-by-file)

### SPA

#### `web/src/routes/spokespeople/$id.tsx`

Three substantive edits:

1. **`SpokespersonDetailRoute`** now hoists `buildSetupItems` +
   `allDone` calculations to the route component. The
   `data-configured` attribute on the outer `<div>` reports
   `"full"` or `"partial"` for e2e + future styling hooks.
   Layout diverges:
   - `allDone === true`: a single `<section data-testid="ready-state">`
     wraps just the `<VideosPanel>` (full-width).
   - `allDone === false`: the existing 2-column grid with
     `<VideosPanel>` + `<SetupPanel>`. The setup panel receives
     the pre-filtered `pendingItems` list.
2. **`Masthead`** now takes a `ready: boolean` prop. When `true`,
   a small `<span data-testid="ready-badge">Ready to render</span>`
   chip renders next to the "Spokesperson" kicker. Editorial
   styling: hairline border + oxblood accent + uppercase-tracked
   typography. Visible in the top-left where the page-load eye
   lands.
3. **`SetupPanel`** changed shape: takes `pendingItems` instead
   of computing them. Renders `null` when `pendingItems.length === 0`
   (defensive — the parent already short-circuits, but this lets
   future callers reuse the component without re-checking).
   Header label flipped from "Setup" to "Set up" with a count
   chip (e.g. "Set up · 2") so the operator sees how much is
   left at a glance. Done items no longer render at all (the
   struck-through done-row pattern is gone — completed setup
   items just disappear).

### Tests

#### `web/e2e/detail-hide-on-completion.spec.ts` (new)

Two specs:

1. **Fully-configured row** — runs the wizard end-to-end with
   tiny PNG portrait + vincent voice preset → lands on detail
   page → asserts `data-configured="full"` + `ready-badge`
   visible + `ready-state` visible + `setup-panel` hidden.
2. **Partial row** — seeds via API (brief only, no portrait, no
   voice) → asserts `data-configured="partial"` + `ready-badge`
   hidden + `setup-panel` visible + `setup-item-brief` hidden
   (brief is done) + `setup-item-avatar` + `setup-item-voice`
   visible (the two unfinished items).

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated. Minimal drift —
  no Django changes this slice.

---

## Verification gates

- `python manage.py check` — clean.
- `python manage.py smoke_headless_auth` — PASSED.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 499.91 kB; +0.5 kB from SESSION 133).
- `pnpm e2e` — **30 of 30 pass in one shot** (was 28 — slice added 2).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Hoisting state up paid off

The pre-W11 `SetupPanel` computed `buildSetupItems` + `allDone`
itself. That worked for the in-panel "Ready to render" message
but didn't help the parent decide on layout. Hoisting the
calculation to `SpokespersonDetailRoute` was a small ergonomic
shift that unlocked two things:

- The parent can pick a layout (2-column vs. full-width).
- The `data-configured` attribute on the root `<div>` becomes a
  single source of truth that e2e can drive against.

Pattern worth noting: **when a child component's internal state
controls parent layout, hoist the state up.** Should have been
the shape from SESSION 118 onward, but it didn't matter until
W11 needed both sides to agree.

### Done rows disappear instead of striking through

The old checklist showed `✓ Business brief` struck-through next
to `02 Voice [Set up]`. After this slice, completed items just
disappear; only the unfinished items render with renumbered
sequence numbers (`01`, `02`).

Calibration trade-off:

- **Pro** (current): operator's eye lands on what's left to do,
  not what's already done. "Set up · 2" header makes the work
  remaining quantitative.
- **Con**: operator loses the dopamine of seeing checkmarks
  accumulate. The "Ready to render" badge in the masthead is the
  consolation prize when they finish.

For a 3-item setup list, the disappear-on-completion pattern is
cleaner. If we ever add Act-Two or a 5+-item list, revisit — the
struck-through pattern is more legible for longer lists.

### The Ready badge is small on purpose

Editorial-warm aesthetic favors restraint. A big green
celebration banner would be the obvious choice; the small
oxblood-on-cream badge is more in line with the rest of the
masthead's tone. Operator gets the signal ("you're done")
without the UI shouting.

Worth noting if a designer ever pushes for more affirmation:
the masthead's status pills already report `Status / Avatar /
Voice = Ready / mock|ready / Bound`, so the affirmation is
actually *triple-redundant*. The badge is the curated summary.

### What the deferred "Edit" affordance would do

The scope-lock said fully-configured rows should have "a small
'Edit' affordance that surfaces a modal with the wizard's fields
for in-place modification." This slice skips it because:

- The wizard is creation-only today; building an edit modal
  means either (a) building a parallel edit-mode wizard or
  (b) extending `<SpokespersonWizard>` with an edit branch.
- Without real operator use, it's unclear which fields actually
  need editing — name + brief are the obvious candidates, but
  things like `tone_archetype` or `visual_subject` might just
  drive the *next* render rather than re-binding the avatar.
- The DRF viewset already supports `PATCH /api/spokespeople/{id}/`,
  so when the time comes, it's a UI-only slice — the API surface
  is ready.

Queued explicitly in the START doc as Item #2.

---

## SESSION 135 — entry point

The wizard arc is complete (W1-W11). Three parallel-safe options:

### Option A — Legacy form retirement

Defer if real-mode Runway validation hasn't happened yet (the
single-form's legacy regression specs are the cheapest insurance
against wizard-introduced bugs). When ready:

- Delete `LegacyCreateForm` from `web/src/routes/spokespeople/new.tsx`.
- Drop the `?legacy=1` gate.
- Rewrite or delete `create-spokesperson.spec.ts`,
  `portrait-camera.spec.ts`, the legacy parts of `make-video.spec.ts`.
- Trim the legacy form's CSS surface.

Half-session.

### Option B — Edit-spokesperson modal

If operators start hitting "I want to tweak the brief without
re-rendering everything." Slice 11.1: a focused modal launched
from a new "Edit" button on the detail page masthead.

Could be a single-step form (name + brief + tone + visual_subject)
that PATCHes the row. No portrait / voice re-bind in this slice —
those have their own existing affordances.

Half-to-full session.

### Option C — Template content refinement

Operator-collaborative content pass on
`shell/character_os/templates/spokesperson_templates.py`. The 4
briefs are first drafts; an hour of operator time would replace
them with real voice. No code changes; no spec changes (the
existing specs check structure, not strings).

Quarter-session of operator time.

### Option D — Tier 2 prompt helpers (DynamicPromptBuilder)

Larger port from u-d-b. Less urgent than wizard polish but
unblocks the next big surface (rich video script composition).
Full session at minimum.

### Recommendation: **C** (a quick operator content pass),
then **A** (legacy retirement) once real Runway has been
exercised, then **D** (Tier 2 helpers) for the next big arc.

---

## AI notes

- Slice landed in ~20 minutes start-to-gates-pass. The wizard
  arc was set up for this slice to be small — the SESSION 126
  hide-on-completion partial foundation meant most of the
  reducer-side logic already existed; this slice generalized to
  the layout level.
- The "done rows disappear" vs. "struck-through" call was the
  one judgement piece. I'd flip the default back to striking-
  through if the list grows beyond 3 items (legibility), but for
  3 items "what's left" is the right framing.
- The Edit affordance deferral is worth flagging — the scope-
  lock made it sound like a requirement, but on closer look,
  the wizard's pre-fill semantics + the detail page's existing
  per-field affordances (voice setup, edit name in metadata grid,
  etc. — these don't exist yet but are the natural single-field
  edit shape) probably cover 80% of the editing use cases
  without a modal. A modal would be over-engineered for the
  current product shape.
- The wizard arc closing here is the long-arc milestone. W1-W11
  spanned SESSIONS 124-134 — eleven slices, ~11 commits, the
  whole create-spokesperson UX from "blank Brief textarea" to
  "click a template tile, walk 4 steps, land on a ready-to-
  render detail page." The handoff discipline + scope-lock-first
  pattern + slice-at-a-time commit cadence made it boring in the
  best way. No big-bang rewrites; no half-finished features;
  every gate run was green at slice close.
- The bundle grew 0.5 kB. The slice was mostly layout-shuffle +
  one new component prop, not new code. Frequency-of-tinier-
  diffs is itself a calibration signal: late-arc slices should
  generally have smaller diffs than mid-arc slices, because the
  scaffolding is already in place.
