---
title: "Session 128 — Wizard slice 5: wizard scaffold"
date: 2026-05-14
status: complete
session: 128
previous_handoff: ./SESSION_127_FOUNDATION_FIELDS.md
---

# Session 128 — `<SpokespersonWizard>` scaffold (wizard slice 5 / 11)

## TL;DR

- **What shipped:** A pure structural shell for the create-
  spokesperson wizard: 4-step indicator (Identity / Portrait /
  Voice / Confirm), a `useReducer`-shaped state bag matching the
  eventual create-spokesperson payload, forward/back navigation
  with per-step `canAdvance` gating, and placeholder step bodies
  that document which slice will fill each one in. Gated behind
  `?wizard=1` so the existing single-form `/spokespeople/new`
  continues serving and the 12 prior Playwright specs stay green.
- **What's blocking next:** Nothing. SESSION 129 picks up wizard
  slice 6 (Step 1 — Identity body: name + business_brief +
  tone_archetype with `suggest_tone_from_brief` inline suggestion).
- **What's in a weird state:** None. 15 of 15 Playwright specs
  pass (was 12 — slice added 3). All Django smokes green.

---

## What changed (file-by-file)

### SPA

#### `web/src/components/spokesperson-wizard.tsx` (new, ~420 LOC)

The wizard scaffold. Sections:

- **State shape (`WizardState`)** — matches `CreateSpokespersonInput`
  + the SESSION 126 `VoiceCaptureValue` shape, loose enough that
  slices 7-8 can plug in `<PortraitUpload>` + `<VoiceCapture>`
  results without changing the reducer.
- **Reducer (`reducer` + `WizardAction`)** — `SET_STEP`, `NEXT`,
  `PREV`, three field-bag setters (`SET_IDENTITY` / `SET_PORTRAIT`
  / `SET_VOICE`), and `RESET`. The setters use spread-patch shape
  (`{ ...state.identity, ...action.patch }`) so partial updates
  don't clobber unrelated fields.
- **Per-step gating (`canAdvance`)** — Step 1 requires a non-empty
  name (the placeholder input today; slice 6 tightens to also
  require `business_brief`). Steps 2/3 advance unconditionally
  (slices 7/8 tighten). Step 4 stays `false` — the Create button
  is disabled until slice 9 wires the submit.
- **Step indicator** — 4 numbered pills with active highlight
  (`aria-current="step"`) + done-state checkmark + connector
  hairlines between them.
- **Step bodies** — each step renders a kicker / title / body
  paragraph + a `<ScaffoldBlock>` placeholder + a
  `<SliceCallout>` describing what the next slice lands. Step 1
  is the only one with a real input (a single `<Input>` for
  `name`) — enough to prove state preservation across navigation.
- **Navigation** — Cancel (back to dashboard), Back (disabled on
  Step 1), Next (disabled on Step 4 or when `canAdvance` is false).
  Tooltip on Next explains why it's disabled.
- **Debug surface** — each step renders a collapsed `<details>`
  block with the current state JSON. Useful during slice 6-9
  development; can stay or be removed when the wizard ships as
  default.

#### `web/src/routes/spokespeople/new.tsx`

Top-level `CreateSpokespersonRoute` now checks `?wizard=1` via
`useSearchParams`. Wizard or legacy form, mutually exclusive. The
legacy `CreateSpokespersonRoute` body got extracted into a
`LegacyCreateForm` function — same logic, just renamed so the
top-level router can dispatch.

This is the cleanest minimal-disruption shape: the existing 12
specs keep driving the legacy form; the new spec drives the
wizard via the flag. When slice 9 finishes the wizard end-to-end,
we flip the default in a single small follow-up.

### Tests

#### `web/e2e/wizard-shell.spec.ts` (new)

Three specs:

1. **4-step navigation + state preservation** — visits the wizard,
   confirms all 4 steps render, walks forward to Step 4, walks back
   to Step 1, verifies the name input retains its value, verifies
   the indicator pill highlights track the current step (via
   `aria-current="step"`), and verifies the Create button on Step
   4 stays disabled (slice 9 wires the real submit).
2. **Cancel returns to the dashboard** — clicks the Cancel
   affordance from Step 1 → asserts `/dashboard` URL.
3. **Legacy form still serves** — visits `/spokespeople/new`
   without the flag → asserts the wizard isn't rendered + the
   legacy `create-submit` button is visible.

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
- `pnpm build` — clean (bundle 481.41 kB; +10 kB from SESSION 127).
- `pnpm e2e` — **15 of 15 pass** (was 12 — slice added 3).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The reducer matches the eventual payload, not the UI

The state shape (`WizardState`) is grouped by *what the backend
will receive* (identity / portrait / voice), not by *what the UI
displays per step*. This was deliberate:

- Slice 9's Confirm submit reads from one consistent bag. No
  remapping between UI grouping and API grouping.
- A field like `visual_subject` lives in `identity` (it's part of
  the create-spokesperson payload), even though the Step 2 UI
  surfaces it next to the portrait picker. Slice 7 wires it via
  `SET_PORTRAIT` if that ergonomically makes more sense — the
  setter takes a patch, not a fixed field list.

If the UI and the backend payload ever genuinely diverge, the
reducer is the right place to encode the mapping (slice 9). No
need to invent it now.

### The `?wizard=1` gate vs feature flag service

I considered three ways to keep the legacy form alive:

A. Query-param gate (`?wizard=1`) — what landed.
B. Environment variable / build-time flag.
C. Server-side per-workspace feature flag.

A is the right shape for slice-5-only because:

- No backend changes (B/C both need a flag plumbing layer).
- Trivial e2e split: legacy specs land on bare URL, wizard spec
  hits `?wizard=1`.
- Zero risk of accidentally shipping a half-finished wizard to
  production — the flag is explicit and ephemeral.

When slice 9 finishes, the wizard becomes the default — we delete
the gate in one tiny commit. No flag-service cleanup needed.

### Step indicator design choice

The pill shape mirrors the editorial aesthetic: small numbered
circle + uppercase-tracked label, connector hairline between
pills on desktop. I considered a horizontal progress bar, but
the numbered pills do two jobs at once — current step + done
state (checkmark on completed pills) — without needing a separate
"X of 4" caption anywhere.

`aria-current="step"` on the active pill is the load-bearing
accessibility signal. The e2e spec asserts it directly, so any
future refactor of the indicator can't silently drop it.

### Debug-state details block

Each step has a collapsed `<details>` showing the current state
JSON. This is *intentional* during the W6-9 development window —
when slice 7 wires `<PortraitUpload>` into `SET_PORTRAIT`, the
operator/developer can verify the dispatch wired correctly by
expanding the panel.

**Plan to remove:** when slice 9 ships the real submit, the debug
block goes away (the assembled-payload preview moves into the
Confirm step's actual review panel). Tracked as a small followup
in the slice-9 scope.

### What slice 5 didn't ship that the scope-lock mentioned

The wizard scope-lock (`CREATE_SPOKESPERSON_WIZARD.md`) mentions a
"Start from template" path on Step 1 (Riggs / Sasha / Donny /
Maya tiles that pre-fill the rest of the wizard). I deferred this
to slice 6 (Step 1 body) — the tiles are part of the Identity step,
not the scaffold.

The scope-lock also covers `suggest_tone_from_brief` integration
as inline suggestions on Step 1. That's also slice 6's territory.

---

## SESSION 129 — entry point

`00-START-NEXT-SESSION.md`. Slice 6 — Step 1 (Identity) body:

1. **Name + business_brief inputs** — replace the placeholder name
   input with proper form fields (use `react-hook-form` + `zod`
   like the legacy form).
2. **Tone archetype select** — 5-option dropdown bound to
   `state.identity.tone_archetype`.
3. **Inline tone suggestion** — when the operator types into the
   brief, call `suggest_tone_from_brief` (server-side via a tiny
   `GET /api/prompts/suggest-tone/?brief=...` endpoint OR
   client-side via a TypeScript port — either way, a quick
   under-the-input "looks like a *tutor* brief — pick that?"
   affordance).
4. **Template-tile picker** — optional 4 named templates that
   pre-fill the Identity payload. Skip if scope creeps; defer the
   tile content to slice 10.
5. **Tighten `canAdvance`** — require name AND brief (>= 8 chars,
   matching the legacy form's `createSchema`).
6. **Playwright spec** — extend `wizard-shell.spec.ts` or add a
   new `wizard-step-1.spec.ts` that types real identity values
   and asserts they survive navigation.

Half-to-full session depending on how deep the tone-suggestion
endpoint goes. If the operator wants to defer the template tiles,
it's a clean half-session.

---

## AI notes

- Slice landed in ~25 minutes start-to-gates-pass. The scaffold-
  only scope was the right shape: every architectural decision
  (reducer state, step indicator, navigation, gating) gets
  validated end-to-end via the e2e spec before any individual
  step's UI work begins.
- The `?wizard=1` gate is a small bet that the operator wants to
  see the wizard live before slices 6-9 fully ship. If you'd
  rather hide it entirely until done, change `searchParams.get
  ("wizard") === "1"` to a build-time check — but the cost of
  leaving it accessible is zero (it doesn't break the legacy form,
  and it's not linked from anywhere).
- The `DebugState` details block was a judgement call — it shows
  current state JSON inline on each step. Useful during W6-9
  build-out; ugly if shipped to production. Slated for removal in
  slice 9.
- The smoke_voice / smoke_avatar transaction discipline (queued
  #12) didn't bite SESSION 128. Still queued.
- The bundle grew 10 kB (471 → 481). Reasonable for ~420 LOC of
  new component code. If it grows beyond ~600 kB without
  proportional functionality, time to look at lazy routes.
