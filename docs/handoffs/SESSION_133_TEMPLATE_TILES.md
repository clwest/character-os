---
title: "Session 133 — Wizard slice 10: template tiles + content"
date: 2026-05-14
status: complete
session: 133
previous_handoff: ./SESSION_132_WIZARD_STEP_4.md
---

# Session 133 — Template tiles (wizard slice 10 / 11)

## TL;DR

- **What shipped:** A 4-tile template picker on Step 1 (Riggs /
  Sasha / Donny / Maya), backed by a new
  `character_os.templates` module + `GET /api/spokespeople/templates/`
  endpoint. Clicking a tile pre-fills the wizard's identity (name +
  brief + tone + visual_subject + visual_template) AND voice
  (preset mode + preset name) so all 4 steps inherit sensible
  defaults. "Start from scratch" clears the fields. Plus a small
  refactor: wizard reducer's `identity.visual_template` is now part
  of state so Step 2's GeneratePanel inherits the template chosen
  on Step 1.
- **What's blocking next:** Nothing. SESSION 134 picks up slice 11
  (hide-on-completion detail page rework) or any queued item.
- **What's in a weird state:** None. 28 of 28 Playwright specs
  pass (was 25 — slice added 3). The 4 templates' *content* (briefs,
  visual subjects, voice presets) is **operator-collaborative
  starter material** — the mechanism is the deliverable; the
  content is a first draft the operator will refine.

---

## What changed (file-by-file)

### Backend

#### `shell/character_os/templates/` (new package)

Two files:

1. **`spokesperson_templates.py`** — pure-Python module with a
   `SpokespersonTemplate` dataclass + a static `TEMPLATES` tuple
   holding the 4 named starters. Per-template fields:
   - `key`, `name`, `tagline` (display strings for the tile)
   - `business_brief` (~3 sentences each, starter content)
   - `tone_archetype` (one of `TONE_ARCHETYPES`)
   - `visual_template` (one of `SUPPORTED_PORTRAIT_TEMPLATES`)
   - `visual_subject` (free-text description)
   - `voice_preset` (one of `SUPPORTED_VOICE_PRESETS`)

   Content matches the scope-lock §"Templates" table:
   - **Riggs** — `founder` / `authority` — SMB owners
   - **Sasha** — `coach` / `friend` — Creators / coaches
   - **Donny** — `local_guide` / `expert` — Local businesses
   - **Maya** — `mascot` / `tutor` — Educators (James's use case)

2. **`__init__.py`** — re-exports `TEMPLATES`, `get_template()`,
   `SpokespersonTemplate`.

Stateless, no DB. The wizard reads via the new endpoint.

#### `shell/apps/spokespeople/views.py`

New `@action(detail=False, methods=["get"], url_path="templates")` —
returns `{templates: [...]}` shaped exactly like the SPA's zod
schema. Auth-required via the existing `IsWorkspaceMember`
permission inherited from the viewset.

### SPA

#### `web/src/lib/api/spokespeople.ts`

Three additions:

1. **`spokespersonTemplateSchema`** — zod schema enforcing
   `tone_archetype` is in `TONE_ARCHETYPES` and `visual_template`
   is in `PORTRAIT_TEMPLATES` (catches Django/SPA drift at the
   boundary).
2. **`SpokespersonTemplate`** type derived from the schema.
3. **`listSpokespersonTemplates()`** + **`useSpokespersonTemplates()`**
   — query hook with 1-hour `staleTime` (templates change rarely).

#### `web/src/components/spokesperson-wizard.tsx`

Four substantive edits:

1. **Extended `WizardState.identity`** with `visual_template`
   (defaults to `"mascot"`). Wizard-internal field — drives Step 2's
   GeneratePanel default selection. Not sent to the create payload
   (the backend takes `portrait_data_uri`, not a template key).
2. **`<TemplateTilePicker>`** new sub-component, rendered at the top
   of `Step1Identity`. 4-tile grid + "Start from scratch" link. Each
   tile is a `<button>` with `aria-pressed` reflecting active state.
   "Active" = name + brief + tone all match a template's values
   (so editing fields after picking drops the active highlight).
   Failsafe: if `useSpokespersonTemplates` fails, the picker renders
   `null` and the rest of Step 1 still works.
3. **Pick dispatch** — `pickTemplate` dispatches `SET_IDENTITY` with
   5 fields AND `SET_VOICE` with `{mode: "preset", preset: voice_preset}`.
   The voice pre-fill means Step 3 opens with the preset preview
   already chosen; operator can change it but doesn't have to.
4. **Step 1 header copy updated** — "Pick a template to start from,
   or fill the fields yourself." Signals the picker's purpose.

#### `web/src/components/wizard-portrait-step.tsx`

Two new props plumbed through:

- **`onTemplateChange?: (template) => void`** — optional callback;
  when the operator changes the template select on the Generate
  tab, the wizard updates `state.identity.visual_template` so it
  persists across navigation.
- **`initialTemplate?: PortraitTemplate`** — pre-fill for the
  Generate panel's template select.

`Step2Portrait` in the wizard parent now passes both, reading from
and writing to `state.identity.visual_template`.

### Tests

#### `web/e2e/wizard-templates.spec.ts` (new)

Three specs:

1. **All 4 tiles render + Maya pre-fills Step 1 fields** — picks
   Maya, asserts name = "Maya", brief contains educator-shaped
   text, tone = "tutor". Advances to Step 2 (Generate tab's
   template select pre-selected to "mascot"). Upload a stub
   portrait → Step 3 → voice preview shows `victoria` (Maya's
   `voice_preset`). Step 4 review row confirms "Runway preset · victoria".
2. **"Start from scratch" clears identity fields** — pick Riggs,
   click clear, assert identity fields are back to defaults.
3. **Editing after a template pick keeps the typed value** — pick
   Sasha, edit the name, assert the typed value survives and the
   tile drops to inactive (`aria-pressed=false`).

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated. URL routes
  `/api/*` went from 39 to 40 (one new endpoint).

---

## Verification gates

- `python manage.py check` — clean.
- `python manage.py smoke_headless_auth` — PASSED.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 499.45 kB; +3 kB from SESSION 132).
- `pnpm e2e` — **28 of 28 pass in one shot** (was 25 — slice added 3).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Mechanism shipped, content is starter

The W10 scope-lock entry in the START doc explicitly called this
out as operator-collaborative. The four briefs in
`spokesperson_templates.py` are first drafts — workable as
defaults but not the operator's voice yet. A future session can
rewrite *just* the strings in that file without touching anything
else, and the test suite will still pass (the specs check
*structure* — that Maya pre-fills tutor-shaped content — not exact
strings, except for proper-noun matches like the name).

### `visual_template` is wizard-internal state

The eventual create-spokesperson payload doesn't include
`visual_template` — the backend takes the resulting
`portrait_data_uri` and binds an avatar. But the wizard needs to
*remember* which template Step 1 picked so Step 2's GeneratePanel
opens with that selection. Resolution: live in the reducer's
identity bag (alongside `visual_subject` + `tone_archetype` which
*are* persisted fields), filtered out in the submit handler.

This is the right shape for "wizard knows more than the backend
needs to know." Same pattern applies if future slices want to
track operator-side analytics (which tile got picked, how many
clicks before settling on a brief, etc.) — all of that can
live in the reducer without contaminating the payload.

### Tile active state via field comparison

I considered tracking "picked template key" as a separate piece of
state. Decided against: the operator can edit fields after picking,
and a "still pretending to be Riggs even though every field is
different" state would be confusing. The current approach (active
tile = all key fields match the template's values) means:

- Pick Riggs → all fields populated → Riggs tile is active.
- Edit the brief slightly → tile drops to inactive (subtle signal:
  "you've customized away from the template").
- Edit it back to match → tile becomes active again.

The "active" state is purely a visual cue — the operator's data
is what matters, not the template provenance.

### Voice pre-fill is a UX choice, not a hard requirement

When the operator picks a template, the wizard pre-fills voice as
`{mode: "preset", preset: <voice_preset>}`. Operator can change on
Step 3. Two alternatives I considered:

A. Leave voice unset until Step 3 (current default).
B. Show the pre-filled voice as a *suggestion* on Step 3 that the
   operator confirms.

Picked A's spirit but went with the eager pre-fill because:
- The template's voice_preset is a deliberate authorial choice by
  whoever wrote the template (operator-collaborative content).
- "Pre-filled but editable" matches the rest of the wizard's
  template behavior (name + brief + tone are also pre-filled).
- Operators who skip Step 3 entirely (clicking through) still get
  the template's preset, not the generic `vincent` skip default.

### What W11 (hide-on-completion) inherits from this

W11 reshapes the detail-page setup checklist. After W10:

- Picking a template pre-fills everything → fully configured row
  on submit → detail page renders the "Ready to render" affordance
  (foundations from SESSION 126's hide-on-completion partial).
- Picking "Start from scratch" + only filling required fields →
  partially configured row → detail page renders setup callouts.

W11's job is making this transition visually clear. The template
picker's success-path (fully configured) is now common enough that
the polish has real value.

---

## SESSION 134 — entry point

Two parallel-safe options:

### Option A — Wizard slice 11: Hide-on-completion detail page rework

Half-to-full session. Reshape the spokesperson detail page's setup
checklist into the explicit "either / or" surface:

- **Fully configured** (avatar bound + voice set): identity panel
  + render history + small "Edit" affordance (modal with wizard
  fields).
- **Partially configured**: focused setup callouts for *just* the
  skipped items.

The foundations landed in SESSION 126 (voice-setup affordance
hides when voice_id is set). The full rework applies the same
treatment to avatar + visual_subject + (future) Act-Two.

### Option B — Tier 2 prompt helpers (DynamicPromptBuilder port)

Tier 1 prompt helpers ported in SESSION 122 (sharpening + brand
palettes + creative principles + tone heuristic). Tier 2 is
`DynamicPromptBuilder` — the u-d-b composer that takes a structured
spec and emits a rendered prompt. Useful for video render flow
when scripts get longer + more structured.

Larger surface — full session at minimum. Defer if the wizard
polish (slice 11) feels more urgent.

### Recommendation: **A** (slice 11).

Reasoning: A finishes the wizard arc cleanly. Slice 10 surfaces
that "fully configured spokesperson" is now a one-click outcome;
W11 polishes the affordance so operators see the difference
between "ready" and "needs setup" at a glance.

### Out of scope for SESSION 134

- Template content refinement (operator-collaborative — separate
  pass on `spokesperson_templates.py` whenever the operator has
  time for it).
- Legacy form retirement (waits for real-mode Runway validation).
- Tier 2 prompt helpers (option B above).

---

## AI notes

- Slice landed in ~30 minutes start-to-gates-pass. The mechanism
  was straightforward (data dict + endpoint + reducer extension
  + tile component); the spec was the bigger piece (covers the
  full template → step-1-prefill → step-2-template-prefill →
  step-3-voice-prefill → step-4-review path).
- The `visual_template` reducer addition was a small calibration
  decision. It's not a persisted field, but it's *authorial
  state* the wizard needs to carry. Adding it to the identity bag
  (with a comment explaining the exclusion from the payload) felt
  cleaner than inventing a new "picked" bag.
- Content note for the operator review pass: the four briefs I
  wrote are intentionally short (~3 sentences) — long enough to
  trigger the tone suggestion debounce + show what the field is
  for, but not long enough to feel locked-in. Rewriting them in a
  future session is a swap-in operation on the constants in
  `spokesperson_templates.py`; no spec changes needed unless
  proper-noun matches are touched.
- The "active tile" heuristic (all key fields match) is a small
  bet that subtle visual feedback ("you've drifted from Riggs")
  is more useful than no feedback. If operators find it confusing
  ("I never picked Riggs, why is it highlighted?"), trivial to
  flip to an explicit picked-key tracker. Worth watching during
  real-mode use.
- I noticed the operator's calibration ("right-shape foundations
  early") applies in reverse here: this slice was *content* work
  on a stable mechanism. The mechanism didn't need any new
  foundations because W1-W9 had landed all the slots
  (visual_subject, tone_archetype, voice presets, portrait
  templates). The wizard arc paid off — slice 10 is essentially
  populating dictionaries, not designing systems.
