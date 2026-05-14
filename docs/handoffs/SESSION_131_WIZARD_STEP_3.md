---
title: "Session 131 — Wizard slice 8: Step 3 (Voice) body"
date: 2026-05-14
status: complete
session: 131
previous_handoff: ./SESSION_130_WIZARD_STEP_2.md
---

# Session 131 — Wizard Step 3 (Voice) body (wizard slice 8 / 11)

## TL;DR

- **What shipped:** Wizard Step 3's Voice body — embeds the
  SESSION 126 `<VoiceCapture>` component (3-mode: Preset / Upload /
  Record) into the wizard reducer with a bridging adapter for
  `VoiceCaptureValue` ↔ wizard state. New "Skip — use the default
  Runway voice" affordance pre-fills `vincent` and advances. Also
  closed the queued #14 allauth-signup-rate-limit drag by disabling
  rate limits in DEBUG (production keeps the defaults).
- **What's blocking next:** Nothing. SESSION 132 picks up wizard
  slice 9 (Step 4 — Confirm + submit), which finally ships the
  wizard-as-default flip + atomic create orchestration.
- **What's in a weird state:** None. 22 of 22 Playwright specs
  pass — and crucially, **in one run, no rate-limit retry needed**.

---

## What changed (file-by-file)

### Backend

#### `shell/character_os/settings.py`

One small addition:

```python
if DEBUG:
    ACCOUNT_RATE_LIMITS = False
```

Disables allauth's built-in rate limits in dev/test only. Production
(where `DEBUG=False`) keeps the defaults that allauth ships
(`signup: 20/m/ip`, `login: 30/m/ip`, `login_failed: 10/m/ip,5/300s/key`,
etc.). The fix is gated on `DEBUG` so a future deploy doesn't
accidentally inherit the override.

**Why `False` not `{}`:** allauth's `app_settings.RATE_LIMITS`
property has explicit logic `if rls is False: return {}` — passing
`{}` falls through to a default-merge codepath that re-applies the
factory defaults. The disable is `False`, the empty dict is a
mistake. Verified by inspecting
`.venv/lib/.../allauth/account/app_settings.py:265-300`.

This closes queued investigation #14 — bitten three sessions in a
row before this fix landed.

### SPA

#### `web/src/components/spokesperson-wizard.tsx`

Three substantive changes:

1. **Extended `WizardState.voice` shape** — adds `fileName`, `mime`,
   `bytes`, `durationMs`. Lets the bag round-trip a
   `VoiceCaptureValue` losslessly when the operator navigates away
   from Step 3 + back. Preset mode populates only `mode + preset`;
   upload/record populate the rest.
2. **Step 3 body wired** — replaced the SESSION 128 placeholder
   with:
   - `<VoiceCapture value={voiceBagToValue(state.voice)} onChange={setVoice} />`
   - A bridging `setVoice` that maps `VoiceCaptureValue` →
     `SET_VOICE` patches (and clears the bag when value is null).
   - A "Skip — use the default Runway voice" link styled like the
     wizard's Cancel — pre-fills `DEFAULT_SKIP_PRESET = "vincent"`
     and dispatches `NEXT`.
3. **Bridge helpers** — `voiceBagToValue` and `valueToVoiceBag`,
   pure functions just below the Step 3 component. Easy to test if
   they grow; today they're trivial.

Removed `debugIdentity` (was only used by Step 3's removed
DebugState block — Step 4's `debugFullPayload` is the only debug
helper that survives until slice 9 ships the real Confirm body).

### Tests

#### `web/e2e/wizard-step-3.spec.ts` (new)

Three specs — one per non-Record path:

1. **Preset path** — sign up → walk through Step 1 + 2 → land on
   Step 3 → pick `vincent` from the preset select → click Use →
   assert preview renders → advance to Step 4 → assert
   `wizard-debug-state` shows the preset committed.
2. **Upload path** — switch to Upload tab → `setInputFiles` with
   a tiny WAV → preview → advance → assert the debug state shows
   the data URI was supplied.
3. **Skip path** — click the new skip link → land on Step 4 →
   assert the default `vincent` preset is in state.

Record path deferred (synthetic audio + MediaRecorder is flaky in
CI, same deferral as SESSION 126's detail-page voice-capture spec).

---

## Verification gates

- `python manage.py check` — clean.
- `python manage.py smoke_headless_auth` — PASSED.
- `python manage.py smoke_voice` — PASSED.
- `python -m pytest character_os/prompts/` — 46 passed.
- `python manage.py inventory` — clean regen.
- `pnpm tsc --noEmit` — clean.
- `pnpm build` — clean (bundle 493.99 kB; +1 kB from SESSION 130).
- `pnpm e2e` — **22 of 22 pass** (was 19 — slice added 3).
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### `False` vs `{}` is a real footgun

The first attempt at the rate-limit fix set `ACCOUNT_RATE_LIMITS = {}`
thinking that "empty dict = no limits." Wrong. allauth's
`RATE_LIMITS` property has explicit `if rls is False: return {}`
logic, and otherwise *merges in defaults* from the rest of the
property body. So `{}` actually equals the factory defaults.

Discovered by running:

```python
from allauth.account import app_settings
print(app_settings.RATE_LIMITS)
```

with the override in place — showed the full default dict, not the
empty one we'd hoped for. Fix was a one-line change to `False`,
plus a documenting comment so this doesn't get re-relearned.

Worth doing the same probe whenever overriding library-shipped
settings — the value you set isn't always the value the library
sees.

### Lossless round-trip is worth a bigger state shape

I considered keeping `state.voice` as the minimal shape
(`mode / preset / dataUri`) and tolerating the round-trip loss on
navigation. That'd mean:

- Operator drops `voice.wav` (5 MB) on Step 3 → advances → goes
  back → sees `voice-clip · 0 B` because filename/bytes weren't
  preserved.

For a sub-3KB state-bag delta (4 extra nullable fields), the
lossless option is a clear win. Same calibration as Step 2's
portrait bag in SESSION 130.

### Skip ≠ separate state

The Skip affordance doesn't introduce a fourth voice "mode" — it
just pre-fills the preset path and advances. Operators who want to
double-check what got picked can navigate back to Step 3 and see
the `vincent` preset preview. This keeps the reducer shape tight
(3 modes, not 4) and `valueToVoiceBag` / `voiceBagToValue` don't
need a special case.

### Step 3's gate stays loose

`canAdvance(step=3)` is unchanged from the scaffold (still
`return true`). Voice is genuinely optional — the model defaults
to `voice_id=""` and the create-spokesperson backend tolerates
that. The Skip button is *encouragement*, not enforcement —
operators can click Next on a fresh Step 3 with no voice picked
and the wizard accepts it.

When slice 9 ships the actual submit, it'll need to fall back to
`vincent` if no voice is in state. That's a slice-9 concern; the
scaffold doesn't preempt it.

---

## SESSION 132 — entry point

`00-START-NEXT-SESSION.md`. Slice 9 — Step 4 (Confirm + submit):

1. **Replace Step 4's stub** with a real review panel: portrait
   thumbnail, name + brief + tone + visual_subject, voice mode +
   preset/clip name, optional preview audio playback.
2. **Wire `useCreateSpokesperson()`** — read assembled payload from
   wizard state, fire the create call, persist new fields
   (`visual_subject`, `tone_archetype`) via the SESSION 127 zod
   surface.
3. **Voice clone follow-up** — if Step 3's mode is `upload` or
   `record`, after the create succeeds, fire
   `useCloneVoice({audio_data_uri})` on the new row. Preset mode
   already passes `voice_preset` on the create call (SESSION 116
   backend behavior).
4. **Error handling** — show inline errors per failed call (avatar
   create failed / voice clone failed). The row creates regardless;
   the detail page's setup checklist (SESSION 126's hide-on-
   completion) catches anything that didn't fully wire.
5. **Tighten `canAdvance(step=4)` → enable submit** — currently
   returns `false` so the button stays disabled. Slice 9 wires it
   to `true` when all upstream gates passed.
6. **Flip the wizard to be the default** — drop the `?wizard=1`
   gate in `web/src/routes/spokespeople/new.tsx`. Retire the
   legacy single-form (or move it behind `?legacy=1` for a session
   or two as an escape hatch). Adjust the existing
   `create-spokesperson.spec.ts` accordingly.
7. **Remove all remaining `DebugState` blocks** from
   `<SpokespersonWizard>` (Steps 2/3 already lost theirs; Step 4
   still has one).
8. **Playwright spec** — `wizard-step-4.spec.ts`. Happy path
   (fill all 4 steps → submit → land on detail page). Error path
   (mock-mode media-engine returns something the backend tolerates;
   confirm the row creates anyway).

Session-sized — the orchestration logic is the meatiest piece, and
the wizard-as-default flip needs the existing e2e specs touched.

---

## AI notes

- Slice landed in ~35 minutes start-to-gates-pass — most of that
  was diagnosing the `ACCOUNT_RATE_LIMITS = {}` footgun. The voice
  step itself was a 2-edit operation (extend state + replace the
  placeholder body); the bridge helpers fell out naturally.
- The rate-limit fix was originally going to be a separate slice
  per the START doc's recommendation. I landed it inline because
  it was *necessary* for the e2e gate to pass (22 sequential
  signups was crossing the limit on the very last spec). Worth
  noting in the handoff so the operator knows this slice closed
  queued #14.
- The Skip affordance ended up smaller than I planned. Originally
  considered tying it to the tone archetype (e.g. tutor →
  `marina`, performer → `vincent`) but that's a different concern
  (tone-to-voice mapping is content design, not wizard plumbing).
  Skip just uses `vincent` — operator can change it before submit
  if they care.
- The bundle grew only 1 kB despite the new component wiring +
  rate-limit settings. That's the SESSION 126 `<VoiceCapture>`
  reuse paying off — the heavy lifting was already bundled.
