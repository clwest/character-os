---
title: "Session 130 — Wizard slice 7: Step 2 (Portrait) body"
date: 2026-05-14
status: complete
session: 130
previous_handoff: ./SESSION_129_WIZARD_STEP_1.md
---

# Session 130 — Wizard Step 2 (Portrait) body (wizard slice 7 / 11)

## TL;DR

- **What shipped:** Wizard Step 2's three-mode Portrait input —
  Upload, Camera, and a new Generate tab that POSTs to a new
  `POST /api/spokespeople/generate-portrait/` action (thin proxy
  around the SESSION 125 `/internal/portrait/` endpoint). Generate
  flow: visual template select + free-text `visual_subject` + optional
  style → preview → Use / Regenerate. The chosen portrait threads
  through the wizard reducer as `state.portrait.dataUri`; the typed
  subject persists to `state.identity.visual_subject` (the SESSION
  127 field). `canAdvance(step=2)` now requires a chosen portrait.
- **What's blocking next:** Nothing. SESSION 131 picks up wizard
  slice 8 (Step 3 — Voice body), wiring `<VoiceCapture>` from
  SESSION 126.
- **What's in a weird state:** None. 19 of 19 Playwright specs
  pass (was 17 — slice added 2 + tightened the existing
  wizard-shell gate test).

---

## What changed (file-by-file)

### Backend

#### `shell/apps/spokespeople/views.py`

Two additions:

1. **`SUPPORTED_PORTRAIT_TEMPLATES`** constant — mirrors
   `PORTRAIT_TEMPLATES` in the media-engine's
   `character_studio_client.py`. Same rationale as the SESSION 126
   `SUPPORTED_VOICE_PRESETS` mirror (CLAUDE.md forbids cross-service
   imports). Drift guard: queued #15 verifier could cover both
   constants in one pass.
2. **`generate_portrait` action** — `@action(detail=False,
   methods=["post"], url_path="generate-portrait")`. Validates
   `template` against `SUPPORTED_PORTRAIT_TEMPLATES`, passes through
   `subject` + `style` (optional), calls
   `MediaEngineClient.create_portrait()`, returns
   `{portrait_data_uri, template, prompt, mock_mode}`. 400 for
   missing/unknown template, 502 for media-engine failure.

The endpoint is list-level (no Spokesperson row exists yet — the
wizard accumulates state until Confirm). Same `@action(detail=False)`
shape as `voice_presets`.

### SPA

#### `web/src/lib/api/spokespeople.ts`

Three additions:

1. **`PORTRAIT_TEMPLATES`** const (+ `PortraitTemplate` type) —
   mirrors the Django side, which mirrors the media-engine side.
2. **`PORTRAIT_TEMPLATE_LABELS` + `PORTRAIT_TEMPLATE_HINTS`** —
   short human-friendly strings per template. Drives the Generate
   panel's template select + the hint text under the template
   description. Bundling the strings here (instead of inlining in
   the component) keeps them findable + reusable for slice 10's
   template tiles when those land.
3. **`useGeneratePortrait()` mutation hook** — POSTs to the new
   endpoint, zod-parses the response. No cache invalidation
   (transient preview; no Spokesperson row).

#### `web/src/components/portrait-upload.tsx`

Two internal components exported:

- `UploadDropzone` (was the internal "Upload tab" component)
- `CameraCapture` (was the internal "Camera tab" component)

`PortraitUpload` (the convenience wrapper used by the legacy form)
is unchanged in external behavior. Existing testids preserved.

This is the cleanest minimal refactor: the wizard's Step 2 reuses
the same Upload + Camera implementations without duplicating ~250
LOC, and the legacy form still composes via `<PortraitUpload>`.

#### `web/src/components/wizard-portrait-step.tsx` (new, ~340 LOC)

Step 2's body. Top-level tabs (Upload | Camera | Generate):

- **Upload** — renders the exported `<UploadDropzone>`.
- **Camera** — renders `<CameraCapture>` if `MediaRecorder`/
  `getUserMedia` are supported; else shows a "use Upload or
  Generate" message.
- **Generate** — new panel:
  - Visual template select (`mascot / founder / coach /
    local_guide`) with an under-it hint string.
  - `visual_subject` text input (free-text, max 200, placeholder
    examples include James's battle unicorn + the neon-pink
    raccoon).
  - Optional style hint input.
  - "Generate portrait" button → POSTs to
    `/api/spokespeople/generate-portrait/`.
  - Preview panel after success: portrait thumbnail + prompt
    blurb + Use / Regenerate CTAs.
  - Inline error pill if the call fails (502, 400, etc.).

Once a portrait is committed (any of the three modes), the whole
component flips to a shared `<PortraitPreview>` with a Change
button — same pattern as the legacy `<PortraitUpload>`.

#### `web/src/components/spokesperson-wizard.tsx`

Three edits:

1. **`canAdvance(step=2)`** now requires
   `state.portrait.dataUri != null`. Step 3 still advances
   unconditionally (slice 8 wires its gate).
2. **`Step2Portrait`** body replaced. Composes
   `<WizardPortraitStep>` with two dispatchers: `SET_PORTRAIT`
   (carries dataUri / fileName / mime / bytes) and `SET_IDENTITY`
   (carries `visual_subject` text from the Generate tab). The
   wizard's reducer maps the loose `state.portrait` shape into
   the `PortraitUploadResult` the embedded component expects.
3. The `Step2Portrait` ScaffoldBlock + SliceCallout +
   DebugState are removed (per the slice plan — Step 2 is no
   longer scaffold).

### Tests

#### `web/e2e/wizard-step-2.spec.ts` (new)

Two specs:

1. **Upload path** — sign up + reach Step 2 + verify all 3 tabs
   render + verify Next gated until upload + `setInputFiles` with
   a tiny PNG + assert preview + assert Next enables + click Change
   → preview clears + Next disables.
2. **Generate path** — switch to Generate tab + pick mascot
   template + type "armored battle unicorn warrior" + click
   Generate + `waitForResponse` on the POST + assert preview
   renders + assert mock-mode tag + click "Use this portrait" +
   assert committed preview + advance to Step 3.

#### `web/e2e/wizard-shell.spec.ts`

Updated the 4-step navigation spec to also drop a tiny PNG on
Step 2 (the gate now requires it). Confirms Next disables until
upload + enables after.

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated. URL routes
  `/api/*` went from 38 to 39 (one new endpoint).

---

## Verification gates

- `python manage.py check` — clean.
- `python manage.py smoke_avatar` — PASSED.
- `python manage.py smoke_portrait` — PASSED for all 4 templates.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 493.05 kB; +8 kB from SESSION 129).
- `pnpm e2e` — **19 of 19 pass** (was 17 — slice added 2).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Three mirrors, one source of truth

`PORTRAIT_TEMPLATES` now lives in 3 places:

1. **Authoritative:** `media-engine/app/services/character_studio_client.py`
2. **Django mirror:** `shell/apps/spokespeople/views.py`
   (`SUPPORTED_PORTRAIT_TEMPLATES`)
3. **SPA mirror:** `web/src/lib/api/spokespeople.ts`
   (`PORTRAIT_TEMPLATES` + label/hint dicts)

Same shape as the `SUPPORTED_VOICE_PRESETS` mirror landed in SESSION
126. CLAUDE.md forbids cross-service imports, so the Django mirror
is unavoidable. The SPA mirror could come from a Django endpoint
(`GET /api/spokespeople/portrait-templates/`), same shape as
`voice-presets/` — but the templates list is *shorter* (4 vs 30)
and changes less often (the underlying Runway model templates are
stable on the order of years), so a static SPA-side mirror is
ergonomic without measurable drift risk.

Queued #15 (drift verifier) could cover both mirrors with one
pass over the source-of-truth file.

### "Decision deferred → land" pattern repeating

The SESSION 127 handoff explicitly deferred this slice's
orchestration (subject → /internal/portrait/) to W7. Landing it
here closes the loop. Worth keeping the pattern: when a slice
finishes, capture *exactly what's deferred + why* in the handoff,
so the next slice has a clear pickup point.

### Generate flow doesn't auto-commit

The Generate button fires the POST and the preview renders, but
the operator has to click "Use this portrait" to commit. Two
benefits:

- Lets the operator regenerate without losing the canvas (the
  template + subject + style inputs stay populated).
- Sets up slice 9's Confirm step naturally — the wizard knows
  exactly which portrait the operator accepted, not whichever one
  was last visible.

The mutation `data` lives on the hook itself (not in component
state). `generate.reset()` after "Use" clears it; "Regenerate"
just dispatches again without resetting. Simple state machine
without explicit useState.

### Three mirrors of "what does a portrait look like"

`PortraitUploadResult` (used by `<PortraitUpload>`),
`state.portrait` (used by the wizard reducer), and
`{dataUri, fileName, mime, bytes}` (the shape `<WizardPortraitStep>`
emits) are all slightly different. I considered unifying:

- A. Make the wizard's reducer use `PortraitUploadResult` directly.
- B. Make the components take the reducer's loose shape.

Picked **neither** — the wizard's loose `null`-friendly shape is
right for an in-progress accumulator; `PortraitUploadResult` is
right for a committed value. The wizard composes the bridge inline
in `Step2Portrait`. Slice 9's submit will read from
`state.portrait.dataUri` directly into `portrait_data_uri` on the
create payload.

### The visual_subject field finally has a write site

SESSION 127 landed `visual_subject` on the model with no UI to set
it. SESSION 130 closes that loop: the Generate tab's subject input
writes to `state.identity.visual_subject` via `SET_IDENTITY`. Once
slice 9 ships submit, the field will reach the row through
`CreateSpokespersonInput.visual_subject` (the field is already
surfaced in `SpokespersonSerializer`'s `fields` from SESSION 127).

Operators who use Upload or Camera modes don't set
`visual_subject` (it stays empty, which the model accepts).
Operators who use Generate are the natural audience for the field.

---

## SESSION 131 — entry point

`00-START-NEXT-SESSION.md`. Slice 8 — Step 3 (Voice) body:

1. **Embed `<VoiceCapture>`** (SESSION 126's component) in Step 3.
   The tabs (Preset / Upload / Record) work as-is. The wizard's
   reducer needs to ship a `SET_VOICE` patch that accepts the
   tagged-union shape `VoiceCaptureValue` returns.
2. **State threading** — when the operator picks Preset, the
   wizard knows + Step 4 fires `voice_preset` on the create call.
   When Upload / Record, the wizard holds the dataUri + Step 4
   fires `POST /clone-voice/` after the row lands (the SESSION
   126 backend handles both shapes).
3. **Tighten `canAdvance(step=3)`** — voice is optional today,
   so this could stay loose. Per the scope-lock, Step 3 has a
   Skip button (defaults to `vincent` preset). Implement the
   skip + stay loose.
4. **Remove Step 3's ScaffoldBlock + SliceCallout + DebugState.**
5. **Playwright spec** — `wizard-step-3.spec.ts`. Preset path
   (pick vincent → advance). Upload path (drop wav → advance).
   Defer Record (synthetic audio stream + MediaRecorder is flaky
   in CI; same deferral as SESSION 126's voice-capture spec).

Half-session — most of the work is plumbing the existing
`<VoiceCapture>` component. The Skip-button behavior is a small
addition.

---

## AI notes

- Slice landed in ~35 minutes start-to-gates-pass. Three substantial
  pieces (backend action + SPA hooks + new WizardPortraitStep
  component) but each had a clear shape locked from prior slices.
- The `<UploadDropzone>` + `<CameraCapture>` export refactor was
  done with two single-line edits (just adding `export` keywords).
  Existing testids preserved → portrait-camera.spec.ts unchanged.
- The full e2e run hit a 429 rate-limit again on the first attempt
  (allauth signup; 19 sequential signups now). Polled until clear +
  re-ran cleanly. Queued #14 (test-settings override) is overdue;
  worth doing as a tiny stand-alone slice between major wizard
  slices.
- The DebugState block on Step 2 was removed in this slice's edit
  (step is no longer scaffold). Steps 3 + 4 keep theirs until
  slices 8/9 ship. Clear progress signal.
- One small TypeScript build failure: an unused `data` parameter
  in the Generate panel's `onSuccess` callback. The fix was to
  drop the callback entirely (we read `generate.data` via the
  hook instead). Cleaner shape than the unused-param pattern.
