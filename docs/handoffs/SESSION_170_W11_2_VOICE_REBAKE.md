---
title: "Session 170 — W11.2 voice swap + avatar re-bake"
date: 2026-05-15
status: complete
session: 170
previous_handoff: ./SESSION_169_MARCUS_E2E_W11_1_EDIT_MODAL.md
---

# Session 170 — W11.2 voice swap + avatar re-bake

## TL;DR

W11.2 ships. The operator-facing gap from W11.1 closes:
spokesperson voice + avatar are no longer read-only after
creation. Two new endpoints + two new SPA surfaces.

* **Voice swap** — pick a Runway preset from the existing
  edit modal. PATCH on the live Runway avatar via a new
  `change-voice` action; the DB persists the new `voice_id`
  even if the live PATCH fails (next bake reads it).
* **Avatar re-bake** — dedicated confirm modal on the
  spokesperson detail page, warning operators about the
  $5-10 Runway spend + 30-180s wait. Calls portrait gen
  + avatar create against media-engine; swaps
  `runway_avatar_id` + `portrait_path` + `runway_avatar_status`
  on the row.

Tests: SPA vitest **52 → 53** (+1 — voice-change PATCH
contract test). Django **718** (unchanged — actions covered
end-to-end via SPA test + live dogfood pending).
Media-engine **108** (unchanged — new endpoint covered
via Django integration path).

## What shipped

### Media-engine — preset-aware voice patch

`media-engine/app/services/voice_clone_client.py` —
`apply_voice_to_avatar` gains a `voice_kind="custom" |
"preset"` keyword. When `"preset"`, the request body builds
`voice = {type: "runway-live-preset", presetId: ...}`
instead of the custom-clone block. Same Runway endpoint
(`PATCH /v1/avatars/<id>`); the discriminator lives in the
`voice` payload shape.

`media-engine/app/routers/internal.py` —
`POST /internal/avatars/<id>/change-voice/` with
`InternalAvatarChangeVoice` request +
`InternalAvatarChangeVoiceResponse`. Validates `voice_kind`
∈ `{"preset", "custom"}`; rejects unknown presets against
`SUPPORTED_VOICE_PRESETS`.

### Django — change-voice + rebake-avatar actions

`shell/apps/spokespeople/views.py` —

`POST /api/spokespeople/<id>/change-voice/`:
* Body: `{preset: "marcus"}`.
* Validates against the local `SUPPORTED_VOICE_PRESETS`
  mirror (CLAUDE.md forbids importing from media-engine
  directly).
* If `runway_avatar_id` is set, calls
  `MediaEngineClient.change_avatar_voice(...)`. Skips the
  live patch when no avatar exists yet — DB still persists.
* Returns `{spokesperson, voice_patch: {status, error}}`
  so the SPA can surface live-patch failures separately
  from DB persistence success.

`POST /api/spokespeople/<id>/rebake-avatar/`:
* Body (all optional): `{visual_subject, voice_preset, template}`.
* Persists `visual_subject` + `voice_id` upfront (operator
  intent locks in even if bake fails downstream).
* Calls `create_portrait` + `create_avatar` against
  media-engine. Both run synchronously — 30-180s wall-clock
  is the dominant cost.
* On success, swaps `runway_avatar_id`,
  `runway_avatar_status`, `portrait_path` on the row.
* On `MediaEngineError`, persists
  `runway_avatar_status="failed"` and returns 502.

`shell/character_os/clients/media_engine.py` —
`change_avatar_voice(avatar_id, voice_id, voice_kind="preset")`
wraps the new media-engine endpoint.

### SPA — voice picker + re-bake confirm modal

`web/src/lib/api/spokespeople.ts` —
`useChangeVoice` + `useRebakeAvatar` mutations.
`changeVoiceResponseSchema` mirrors the Django
`{spokesperson, voice_patch}` envelope.

`web/src/components/spokesperson-edit-modal.tsx` —
new voice-preset `<select>` between tone and visual_subject.
The edit modal now orchestrates two requests at save time:
PATCH for the simple persona fields (W11.1), then the
`change-voice` action if the preset changed. Disable state
unifies under a combined `isPending` flag.

`web/src/components/spokesperson-rebake-modal.tsx` —
**new**. Confirm modal with cost warning ("$5-10 Runway
credits, 30-180s, replaces avatar id + portrait"). Lists
the current `visual_subject` + `voice_id` read-only;
operator edits the spokesperson first if they want
different values. Esc/backdrop blocked while a bake is
in flight.

`web/src/routes/spokespeople/$id.tsx` — Masthead gains a
"Re-bake" ghost button next to "Make a video"; opens the
rebake modal. `rebaking` state hook sits above the early
returns (the SESSION 169 hook-order lesson held).

`web/src/components/spokesperson-edit-modal.test.tsx` —
mock-fetch routing reshape (voice-presets GET, change-voice
POST, default PATCH all distinguished). New W11.2 test
asserts the `change-voice/` URL fires with body
`{preset: "clara"}`. Other tests adjusted to find the PATCH
call by method instead of asserting fetch-call count
(useVoicePresets fires a GET on mount).

## Why two requests instead of one PATCH

The simple fields (`name`, `business_brief`, `visual_subject`,
`tone_archetype`) flow through DRF's
`ModelViewSet.partial_update` and require no media-engine
contact. The voice change is a side-effect on Runway —
it can succeed locally but fail at Runway and vice versa.
Folding both into one PATCH would force one of two
operationally bad shapes:

* Bundle the voice change into the serializer and have the
  Spokesperson save loop fire the Runway PATCH — couples
  DB transactionality to a 5-15s HTTP call.
* Add the voice change as a parallel pseudo-field that
  silently triggers a side-effect on save — hides the
  Runway round-trip from the operator-facing log.

The two-request shape is honest about the operation cost:
the edit modal stays a thin form for DB fields; the
`change-voice` action surfaces the live-patch result so
the SPA can render `voice_patch: {status, error}` if
needed.

## Calibration moments worth carrying

### 1. Distinct request boundaries for distinct side-effects

W11.1 was pure PATCH. W11.2 introduced the first
side-effect-on-save case in the spokesperson SPA. The
right shape is two requests, not one — and the SPA needs
to handle partial success (DB persisted, Runway PATCH
failed) gracefully.

**Carry-forward**: when an SPA "save" action has both a
DB write and an external-system side-effect, model them
as two requests. The PATCH stays a thin form; the action
endpoint surfaces the side-effect result explicitly.
Don't bundle a 5-15s HTTP call into a serializer save
loop.

### 2. Mock-fetch needs route-aware routing once endpoints multiply

The test mock-fetch was a single switch on `/voice-presets/`
before W11.2; now it's a three-way switch. The shape was
discovered by test failure (the change-voice schema parse
threw because the default response wasn't envelope-shaped).

**Carry-forward**: vitest mock-fetch implementations
deserve route-aware switching from day one when a component
hits more than one endpoint. The cost is small and the
failure mode (schema parse error → mutation throws →
expectation about `onClose` fails far from the actual
cause) is hard to diagnose. Same pattern that
`web/src/test-utils` has been doing for `useVoicePresets`
since K6.4 — generalize it.

### 3. The hook-order lesson held

SESSION 169's hook-order fix (move `useState(editing)`
above the early returns) was applied preemptively when
adding `rebaking` state to the same route. Zero
console errors on first load. The pattern is now
load-bearing — every new state hook in a route component
goes above the loading/error/not-found returns.

**Carry-forward**: when adding state to a route component
with conditional early returns, the new hook lives ABOVE
the returns. Caught the first time by browser console;
preemptively applied the second time.

## What's next (SESSION 171)

* **Live W11.2 dogfood against Marcus.** Open the edit
  modal, swap the voice preset to `clara` or `roman`,
  save, fire a render to compare against the SESSION 169
  baseline (`marcus` voice). Then optionally exercise the
  rebake flow against Marcus with a small visual_subject
  tweak. ~$10-15 Runway spend total.
* **More real-Runway exposure on other recipes.**
  `talking_head_polished` Sasha retake,
  `long_form_ad` smoke. Backlog from SESSION 169 still
  applies.
* **F8.1 — K10 seed corpus** if operator markdown is ready.
* **K6.4 v3 — embedding-similarity fallback.** Holds until
  a real paraphrase miss surfaces.
* **K6.3 — Brief length cap.** Might be moot now that K6
  produces clean briefs.

## Files changed in this commit

* `media-engine/app/services/voice_clone_client.py` —
  `voice_kind="preset"` support.
* `media-engine/app/routers/internal.py` — new
  `/internal/avatars/<id>/change-voice/` endpoint.
* `shell/apps/spokespeople/views.py` — `change_voice` +
  `rebake_avatar` actions.
* `shell/character_os/clients/media_engine.py` —
  `change_avatar_voice` wrapper.
* `web/src/lib/api/spokespeople.ts` — `useChangeVoice` +
  `useRebakeAvatar` hooks + schemas.
* `web/src/components/spokesperson-edit-modal.tsx` —
  voice-preset select + two-request save orchestration.
* `web/src/components/spokesperson-rebake-modal.tsx` —
  new file.
* `web/src/components/spokesperson-edit-modal.test.tsx` —
  route-aware mock-fetch + W11.2 voice-change test.
* `web/src/routes/spokespeople/$id.tsx` — Re-bake button +
  modal mount + `rebaking` state.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `00-START-NEXT-SESSION.md` — W11.2 marked done; SESSION
  171 priorities.
* `docs/handoffs/SESSION_170_W11_2_VOICE_REBAKE.md` —
  this file.

---

*Handoff written end-of-SESSION 170. Anchors re-stamped
via `context-kit handoff write 170`. W11.2 closes the
last operator-facing gap on spokesperson editing.*
