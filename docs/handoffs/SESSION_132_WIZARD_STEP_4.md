---
title: "Session 132 — Wizard slice 9: Step 4 (Confirm + submit) + wizard-as-default"
date: 2026-05-14
status: complete
session: 132
previous_handoff: ./SESSION_131_WIZARD_STEP_3.md
---

# Session 132 — Wizard Step 4 + wizard-as-default flip (wizard slice 9 / 11)

## TL;DR

- **What shipped:** The wizard's final body — Step 4 (Confirm)
  with a full editorial review panel, atomic submit
  orchestration (`useCreateSpokesperson` + follow-up
  `useCloneVoice` when needed), tier-limit 402 callout, inline
  error rendering, and the wizard-as-default flip at
  `/spokespeople/new`. The legacy single-form lives behind
  `?legacy=1` as a temporary escape hatch. **The 4-step create
  flow that's been the central thread of W1-W9 is now end-to-end.**
- **What's blocking next:** Nothing. The wizard ships. SESSION 133
  picks up slice 10 (template content — operator-collaborative)
  or slice 11 (hide-on-completion detail-page rework).
- **What's in a weird state:** None. 25 of 25 Playwright specs
  pass (was 22 — slice added 2 wizard-step-4 + 1 wizard-shell
  "wizard is default" + restructured wizard-step-3 to use the new
  review rows instead of the removed DebugState).

---

## What changed (file-by-file)

### SPA

#### `web/src/components/spokesperson-wizard.tsx`

This file took the biggest hit — Step 4's stub became the
culminating slice. Changes:

1. **Imports** — added `useCreateSpokesperson`, `useCloneVoice`,
   `ApiError`. Pulled the existing legacy-form `extractTierLimit` +
   `extractMessage` helpers into the wizard.
2. **Tightened `canAdvance(step=4)`** — returns true when
   name + brief + portrait are all set (defensive re-check; Step 4
   is only reachable through the upstream gates, but the operator
   can navigate back + clear fields).
3. **Wizard parent `onSubmit`** — assembles the payload from
   `state.identity` + `state.portrait` + `state.voice`. Fires
   `useCreateSpokesperson.mutateAsync()`. On success, if voice
   mode is `upload` or `record`, fires a follow-up
   `useCloneVoice.mutateAsync()` with the data URI. Navigates to
   `/spokespeople/{id}` on success. Errors during create stay on
   Step 4 with the error rendered inline; errors during
   clone-voice navigate anyway (the row is real — the detail page's
   SESSION 126 setup checklist catches the missing voice).
4. **`Step4Confirm` body** — replaced the stub with a real review
   panel: portrait thumbnail (or initials fallback), Name,
   Business brief, Tone, Visual subject, Voice. Tier-limit callout
   + general error renderer both render inline below the review.
5. **`Navigation` component** — now takes `pending` + `onSubmit`
   props. On Step 4, the primary button label becomes "Create
   spokesperson" (or "Creating…" while pending) and clicking it
   fires `onSubmit` instead of `onNext`. Cancel + Back disable
   during pending so the operator can't interrupt mid-flight.
6. **Removed scaffolding** — `ScaffoldBlock`, `SliceCallout`,
   `DebugState`, `debugFullPayload`. None of them have callers
   any more.
7. **Helpers** — added `describeVoice` (turns the voice bag into
   "Runway preset · vincent" / "Uploaded · clip.wav" / "Recorded ·
   12s clip" / "Default Runway voice"). Added local `deriveInitials`
   for the portrait-fallback avatar.
8. **Masthead** — dropped the "· wizard" suffix from the New
   spokesperson kicker (the wizard IS the create flow now).

#### `web/src/routes/spokespeople/new.tsx`

Flipped the route gate. `searchParams.get("legacy") === "1"` →
legacy form; otherwise the wizard. Comment updated to document the
retirement plan: a follow-up slice removes the legacy form +
`LegacyCreateForm` function entirely.

### Tests

#### `web/e2e/wizard-step-4.spec.ts` (new)

Two specs:

1. **Happy path** — `dashboard CTA → wizard → submit → detail page`.
   Sign up → dashboard empty-state CTA navigates to the wizard
   (no flag now) → fill identity (name + brief + accept tone
   suggestion) → upload portrait → pick vincent voice preset →
   review panel renders all values → Create button enabled → click
   → POST /api/spokespeople/ fires + waits for response → navigate
   to detail page → assert all fields persisted including tone
   (`tutor`, accepted from suggestion) + voice (`vincent`) in the
   MetadataGrid + mock-ready avatar pill.
2. **Defensive gate** — fills all 4 steps, then navigates back to
   Step 1, clears the brief, asserts Next disables on Step 1 (the
   gate refuses to walk forward without a brief).

#### `web/e2e/wizard-shell.spec.ts`

Two changes:

1. The "4-step navigation" spec's Step 4 assertion flipped: button
   reads "Create spokesperson" + is **enabled** (was disabled in
   the scaffold). Doesn't click submit — wizard-step-4 covers that.
2. Replaced "legacy form still serves /spokespeople/new without the
   flag" with two specs:
   - "wizard is the default at /spokespeople/new (no flag)"
   - "legacy form still serves ?legacy=1 (escape hatch)"

#### `web/e2e/wizard-step-3.spec.ts`

The three specs assert state via Step 4 review rows now
(`wizard-confirm-voice` testid) instead of the removed
`wizard-debug-state` block. Same coverage, real rendering.

#### `web/e2e/{create-spokesperson, portrait-camera, make-video}.spec.ts`

Each `goto("/spokespeople/new")` updated to
`goto("/spokespeople/new?legacy=1")` since they all drive the
legacy single-form's testids (`create-submit`, `getByLabel("Name")`,
etc.). These specs serve as legacy-form regression tests until the
legacy form is retired in a follow-up slice.

In `create-spokesperson.spec.ts`'s first spec, replaced the
empty-state CTA click with a direct `goto` since the CTA now
navigates to the wizard by default (and we want to test the legacy
form here).

#### `web/e2e/wizard-step-{1,2}.spec.ts`

Bulk-stripped the now-redundant `?wizard=1` query param from
gotos (the wizard is the default).

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated. Minimal drift —
  no Django changes this slice.

---

## Verification gates

- `python manage.py check` — clean.
- `python manage.py smoke_headless_auth` — PASSED.
- `python manage.py smoke_avatar` — PASSED.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 496.76 kB; +3 kB from SESSION 131).
- `pnpm e2e` — **25 of 25 pass** (was 22 — slice added 3 net).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### One submit handler, two endpoints, three modes

The wizard's submit is the only place in the SPA that orchestrates
*two* sequential API calls. Worth tracing the flow:

1. `useCreateSpokesperson.mutateAsync({...payload, voice_preset?})`
   - If voice mode is `preset`, the preset name rides on the create
     payload. The backend's `perform_create` writes it directly to
     `instance.voice_id` (SESSION 116 behavior). No second call
     needed.
2. If voice mode is `upload` or `record`:
   - `useCloneVoice.mutateAsync({id, audio_data_uri})` fires
     after create succeeds.
   - Failure here doesn't roll back the row. The user lands on the
     detail page; SESSION 126's voice-setup affordance picks up
     where it left off.

This is the right shape for a complex multi-step create:
**atomicity isn't at the API level, it's at the UX level.** A
half-created spokesperson with a missing voice is still useful;
the operator's not stranded.

### `pending` is the right state to gate Back/Cancel on

When the submit's in flight (potentially 10-20s in real mode while
Runway processes the avatar), the operator shouldn't be able to
navigate away. The wizard's nav now disables Back + Cancel +
Submit during `pending`. That's three buttons all reading the same
state, which would have been a footgun if the wizard had a more
complex submit. As-is the prop drilling is fine.

### "Why not auto-redirect on canAdvance=false?"

Step 4's `canAdvance` re-checks upstream gates defensively. If the
operator navigates back and clears the brief, the Create button
disables. Could we auto-bounce them to Step 1 with an error
toast? Yes, but:

- It removes operator agency. Maybe they're clearing the brief to
  rewrite it.
- It introduces a "navigation-while-typing" race condition.
- It hides why the button is disabled.

The current shape (button disables + tooltip explains) is more
honest UX. The operator chooses to navigate back to Step 1, fills
the missing field, and walks forward again.

### The legacy form is on a one-session retirement timer

The flip is the operational milestone, but the legacy form lingers
behind `?legacy=1` as an escape hatch in case the wizard has a
problem in production. Plan:

- **Next 1-2 sessions:** wizard is default; legacy form is
  reachable but not linked. Existing regression specs prove it
  still works.
- **Once real Runway calls have exercised the wizard:**
  delete `LegacyCreateForm`, retire the `?legacy=1` gate, delete
  the legacy specs. Probably part of slice 11 (hide-on-completion)
  since both clean up wizard-adjacent code.

### What slices 10 + 11 still need

The wizard ships end-to-end, but:

- **Slice 10 — Template content** — the "Start from template"
  tile picker on Step 1 was deferred from SESSION 129 because the
  template content (Riggs / Sasha / Donny / Maya) needs
  operator-collaborative design work. The mechanism is small;
  the content is the hard part.
- **Slice 11 — Hide-on-completion detail-page rework** — the
  foundations landed in SESSION 126 (the voice-setup affordance
  hides when voice_id is set). The full rework is similar
  treatment for every setup item + a polished "ready to render"
  affirmation when all are done.

---

## SESSION 133 — entry point

Two parallel-safe options:

### Option A — Wizard slice 11: Hide-on-completion full rework

The detail page's setup-checklist currently shows partially. Make
it the explicit "either / or" surface from the wizard scope-lock:

- Fully configured: clean identity panel + render history + small
  "Edit" affordance.
- Partially configured: focused setup callouts for *just* the
  skipped items.

Half-to-full session depending on how deep the "Edit" modal goes.

### Option B — Wizard slice 10: Template content

Operator-collaborative session — design the 3-4 named templates
(Riggs / Sasha / Donny / Maya) with real briefs + tone +
visual_subject defaults. Then wire the tile picker on Step 1.

### Option C — Retire the legacy form

Small standalone slice. Delete `LegacyCreateForm`, drop the
`?legacy=1` gate, delete `create-spokesperson.spec.ts` +
`portrait-camera.spec.ts` (or rewrite them to drive the wizard) +
`make-video.spec.ts`'s legacy form usage. **Defer until the
wizard's been exercised against real Runway calls** —
mock-mode is too forgiving to catch all the subtle real-mode
failure modes.

### Recommendation: **B first** (operator-collaborative content),
then **A**, then **C**.

Reasoning: B unblocks the "tutorials/handholding" UX for new
operators. A polishes the existing detail page. C is best done
after real-mode validation, which probably needs Runway credits to
arrive first.

---

## AI notes

- Slice landed in ~45 minutes — the biggest one in a while. Two
  meaningful pieces (Step 4 body + submit orchestration) plus the
  flip + spec migrations. Half the time was spec updates
  (DebugState removal forced wizard-step-3 specs to find a new
  signal; the legacy-vs-wizard route flip touched 5 spec files).
- The defensive `canAdvance(step=4)` re-check pattern is worth
  carrying forward. Trusting "they couldn't have reached this
  step without satisfying upstream gates" is true at the moment of
  Next click, but state can change after — the operator can
  navigate back + clear fields. Re-check at the moment of
  decision.
- The follow-up clone-voice's catch-and-swallow felt wrong at
  first (errors should surface!) but the calibration is right:
  the row is real, the operator can complete voice setup on the
  detail page, and a noisy "voice clone failed, but spokesperson
  created" alert is worse UX than just landing them where they
  can fix it.
- I considered showing a per-step progress toast during submit
  ("Creating spokesperson…", "Cloning voice…") but the "Creating…"
  button label + disabled state already signals progress. Toast
  was scope-creep.
- The wizard-step-3 specs were the trickiest part of this slice.
  They asserted state via `wizard-debug-state`, which the slice
  removes. Rewriting them to check Step 4 review rows worked —
  same coverage via the real UI affordance.
- One judgement call: the dashboard empty-state CTA still points
  to `/spokespeople/new` (no flag). After the flip, that lands on
  the wizard, which is the right production UX. The
  `create-spokesperson.spec.ts` first test used to test that flow
  end-to-end with the legacy form; I converted it to a direct
  `goto("?legacy=1")` so it remains legacy-form regression
  coverage without false dependency on the dashboard CTA.
