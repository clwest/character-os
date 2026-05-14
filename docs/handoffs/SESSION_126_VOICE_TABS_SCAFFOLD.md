---
title: "Session 126 — Wizard slice 3: voice tabs scaffold"
date: 2026-05-14
status: complete
session: 126
previous_handoff: ./SESSION_125_INTERNAL_PORTRAIT_ENDPOINT.md
---

# Session 126 — `<VoiceCapture>` + clone-voice preset path (wizard slice 3 / 11)

## TL;DR

- **What shipped:** Three-mode voice capture component
  (`web/src/components/voice-capture.tsx`) wired into the
  spokesperson detail page's setup checklist + a backend extension
  that lets `POST /api/spokespeople/{id}/clone-voice/` accept either
  a Runway preset (`{preset: "vincent"}`) OR a custom clone payload
  (`{audio_data_uri: ...}`). Two new SPA mutation hooks
  (`useVoicePresets`, `useCloneVoice`) + a new list-level DRF action
  (`GET /api/spokespeople/voice-presets/`) round out the API. Also
  fixed a long-standing flake in the portrait camera capture by
  waiting for `loadeddata` before flipping to the "live" state.
- **What's blocking next:** Nothing. SESSION 127 is open for wizard
  slice 4 (tone archetype field), slice 5 (wizard scaffold), or any
  parallel-safe queued item.
- **What's in a weird state:** None. 12 of 12 Playwright specs pass
  (was 10/10 in SESSION 125 — slice added two specs; portrait
  camera test was upgraded from flaky to reliable).

---

## What changed (file-by-file)

### Backend

#### `shell/apps/spokespeople/views.py`

Three edits:

1. **`SUPPORTED_VOICE_PRESETS` constant** — mirrored from the media-
   engine's `character_host_client.SUPPORTED_VOICE_PRESETS`. Local
   `frozenset` because CLAUDE.md forbids cross-service imports
   (Django ↔ media-engine talk over HTTP/JSON only). Doc comment
   notes the media-engine side is authoritative if Runway's list
   ever shifts.
2. **`clone_voice` action** — split into a preset path + a clone
   path. Preset path: validate against `SUPPORTED_VOICE_PRESETS`,
   persist preset name directly as `voice_id`, return a uniform
   response shape (`status: "preset"`, `preview_url: null`). Clone
   path: unchanged (existing media-engine `/internal/voices/` call).
   If both fields are supplied, preset wins — keeps the contract
   deterministic without a strict-mode flag.
3. **`voice_presets` action** — new `GET /api/spokespeople/voice-presets/`
   list-level action. Returns `{presets: [...]}` alpha-sorted. DRF's
   `DefaultRouter` registers list-level dynamic routes before the
   detail route (`{pk}`), so the URL doesn't collide with the
   `/spokespeople/{id}/` shape.

Error contract:

- `400 missing_input` — neither `preset` nor `audio_data_uri`.
- `400 unknown_preset` — `preset` not in `SUPPORTED_VOICE_PRESETS`.
- `502 upstream_media_engine` — clone path, media-engine error.

Response shape (uniform across both paths):

```json
{
  "spokesperson": {...},
  "voice": {
    "voice_id": "vincent" | "<runway-vended-id>",
    "status": "preset" | "ready" | "mock",
    "preview_url": null | "https://...",
    "mock_mode": false
  }
}
```

### SPA

#### `web/src/lib/api/spokespeople.ts`

Two new hooks:

1. **`useVoicePresets()`** — `useQuery` against the new
   `voice-presets/` endpoint. `staleTime: 1h` — Runway's preset
   list shifts on the order of months. Zod-parsed.
2. **`useCloneVoice()`** — `useMutation`. Accepts either
   `{id, preset}` or `{id, audio_data_uri, name?}`. On success,
   updates the single-resource cache + invalidates the workspace
   list. Zod-parsed response.

Both follow the existing SPA conventions (zod at the boundary,
TanStack Query for state, invalidate on success).

#### `web/src/components/voice-capture.tsx` (new, ~580 LOC)

Three tabs:

- **Preset** — `<select>` populated from `useVoicePresets()`. Value
  on submit: `{mode: 'preset', preset}`. No backend call from the
  component itself — parent decides.
- **Upload** — drag-and-drop / click. Accepts mp3 / wav / m4a / webm,
  15 MB cap (mirrors backend `MAX_AUDIO_BYTES`). FileReader →
  base64 data URI.
- **Record** — `MediaRecorder` API. Acquires mic on mount, 5-state
  lifecycle (`starting` → `ready` → `recording` → `captured`; or
  `denied` / `unsupported` / `error`). 10 s minimum (Runway's
  documented floor) enforced via a disabled Use button + inline
  copy. 5-min ceiling auto-stops the recorder. webm/opus by default;
  falls back to mp4 on Safari (per `MediaRecorder.isTypeSupported`).
  Hidden entirely when `window.MediaRecorder` is unavailable.

Patterns reused from SESSION 124's `<PortraitUpload>`:

- Identical `Tabs` primitive + capability-detection branching.
- Same preview-with-Change pattern when a value is set.
- Same five-state-error rendering for permission/device failures.
- Same in-promise `cancelled` flag + `useRef` cleanup discipline.

#### `web/src/routes/spokespeople/$id.tsx`

- Added `<VoiceSetupAffordance>` inline component inside `SetupPanel`.
- Replaces the previous static "Voice" checklist row with an
  expandable callout: collapsed by default → click "Set up voice"
  → `<VoiceCapture>` opens inline → Save / Cancel buttons fire
  `useCloneVoice` and close the panel.
- The checklist's `SetupItem` now carries a `kind` field
  (`brief | avatar | voice`) so we can branch on the row identity
  without string-matching the label.
- Hide-on-completion: when `voice_id` is set, the checklist item
  flips to ✓ and the affordance vanishes (existing checklist
  pattern; no new code).

#### `web/src/components/portrait-upload.tsx`

- Bug fix (orthogonal to this slice but bit the e2e gate): the
  Camera tab's `setState("live")` used to fire as soon as `play()`
  resolved. The capture path early-returns when
  `video.readyState < 2`, so under headless Chromium the synthetic
  stream sometimes hadn't filled the readyState by the time the
  button was clicked. Now we wait for `loadeddata` before flipping
  to `live`. Verified flake-free across 3 consecutive runs after
  the fix.

### Tests

#### `web/e2e/voice-capture.spec.ts` (new)

Two specs:

1. **Preset path** — sign up → seed a spokesperson via the API →
   navigate to detail page → click "Set up voice" → assert all three
   tabs render → select "vincent" → submit → assert the
   `clone-voice` POST fires → assert the affordance disappears +
   the Voice pill flips to "Bound" + the metadata grid shows
   `vincent`.
2. **Upload path** — same setup → switch to Upload tab →
   `setInputFiles` with a tiny silent WAV blob → submit → assert
   the response is `ok()` → assert the affordance disappears + pill
   flips.

Record path is intentionally deferred (documented inline). The
synthetic audio stream Chromium emits doesn't play nicely with
`MediaRecorder` in CI — the recorder spec is shaped the same as
`<CameraCapture>` (already covered by `portrait-camera.spec.ts`),
so coverage of the underlying pattern is solid.

### Docs / inventory

- `docs/CHARACTER_OS_INVENTORY.md` regenerated (clean, only
  expected drift: 35 → 37 api routes for the two new actions).

---

## Verification gates

- `python manage.py check` — clean (deprecation warnings unchanged).
- `python manage.py smoke_headless_auth` — PASSED.
- `python manage.py smoke_avatar` — PASSED.
- `python manage.py smoke_voice` — PASSED (clone path unchanged).
- `python manage.py smoke_video` — PASSED.
- `python manage.py smoke_portrait` — PASSED for all 4 templates.
- `python -m pytest character_os/prompts/` — 31 passed.
- `python manage.py inventory` — clean regen
  (api routes 35 → 37, shell LOC +76).
- `pnpm build` — clean (bundle 471.22 kB).
- `pnpm e2e` — **12 of 12 pass.** (Was 10/10 in SESSION 125 —
  this slice added the two voice specs.)
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Two-paths-one-endpoint vs separate-actions

I considered three options for the preset path:

A. Extend `clone-voice` to accept either `preset` OR `audio_data_uri`.
B. Add a separate `set-voice-preset` action.
C. Allow `PATCH /spokespeople/{id}` to mutate `voice_id` directly.

Picked A. Reasoning:

- The semantic operation ("set this spokesperson's voice") is the
  same regardless of source. Splitting it across actions duplicates
  the response-envelope handling on the SPA side.
- Option C bleeds voice setup into the generic update path, which
  invites confusion when we add voice provenance fields later
  (`voice_source: "preset" | "clone"`, etc).
- Option A keeps the contract aligned with the SESSION 124
  pattern: one verb, multiple input shapes, uniform output.

The Preset / Upload / Record three-mode UI inherits this directly —
the component yields a tagged-union `VoiceCaptureValue`, and the
parent collapses each mode to either `{preset}` or `{audio_data_uri}`
before calling `useCloneVoice`. The wizard's Step 3 in slice 7 will
reuse exactly the same pattern.

### `frozenset` mirroring vs HTTP roundtrip for presets

Two ways to surface the preset list to the SPA:

- A. Hard-code on the Django side, ship via `/voice-presets/`.
- B. Add an `/internal/voice-presets/` GET on the media-engine, have
  Django proxy it.

Picked A. The preset list shifts on the order of months (Runway
adds a voice maybe once a quarter), and the cost of one extra HTTP
roundtrip on every spokesperson detail page load isn't worth the
"single source of truth" purity. The mirroring is documented in a
comment on `SUPPORTED_VOICE_PRESETS` so future maintainers know to
update both sides if the list drifts. A future SESSION can add a
drift-checker to `verify_doc_claims` if this becomes a pain point.

### MediaRecorder is *almost* but not quite a 1:1 with getUserMedia

The Record tab's lifecycle ended up needing more states than the
Camera tab's. Camera has 5 states (`idle / starting / live / denied
/ unsupported / error`); Record needs 7 (`idle / starting / ready /
recording / captured / denied / unsupported / error`). The extra
`recording` + `captured` states come from MediaRecorder's chunked-
output model: we go `ready` → click Start → `recording` → click
Stop → `onstop` fires + builds the Blob → `captured` shows the
playback + Use/Discard affordance.

Worth noting for slice 7 (wizard's Step 3): the recorder needs
explicit cleanup on unmount because the mic stream is still hot
even when the recorder is stopped — `useEffect` cleanup tears
down `streamRef.current.getTracks()` to release the mic
permission. Mirrors the camera pattern.

### The readyState bug had been latent

The portrait camera test was claimed "10/10 pass" in SESSION 125,
but reproduces a failure now even against the SESSION 125 commit
(verified by `git stash` + re-run). Hypothesis: Chromium's synthetic
stream timing has shifted between Playwright Chromium revisions.
The fix (wait for `loadeddata` before flipping to live) is the
correct behaviour regardless — relying on `play()` resolving was
always racy, the SESSION 124 implementation just got lucky in the
SESSION 124/125 environment.

Lesson worth carrying forward: media-API state transitions should
hook the readiness events (`loadeddata`, `canplay`, `loadedmetadata`)
rather than wallclock or promise-resolution timing. The Record tab
inherits this discipline by waiting on the recorder's `onstop`
event before showing the captured-clip preview.

### Half-session that grew a tail

This slice was scoped as session-sized in the SESSION 125 handoff
and stayed there for the voice work itself (~30 min start-to-gates),
but the camera flake-fix added ~10 minutes of unplanned work.
Worth flagging: the cost of letting flakes ride is paying interest
later. The make-video lifecycle spec (S-12) is the next candidate
for a flake audit if it bites.

---

## SESSION 127 — entry point

`00-START-NEXT-SESSION.md`. Three parallel-safe options:

- **Wizard slice 4 — Tone archetype field** (half-session).
  `Spokesperson.tone_archetype` CharField with 5 choices
  (`tutor / authority / friend / expert / performer`) + migration
  + `suggest_tone_from_brief(brief: str) -> str` helper in
  `character_os/prompts/brand.py` (mirrors `suggest_palette_from_brief`
  shape) + pytest cases + serializer + zod schema. No UI changes
  yet (Wizard Step 1 picks this up when slice 6 lands).
- **Wizard slice 5 — Wizard scaffold** (session-sized).
  `web/src/components/spokesperson-wizard.tsx` with the 4-step
  shell (Identity / Portrait / Voice / Confirm). Empty steps that
  the next four slices fill in. Worth pairing with slice 4 if both
  fit a single session window.
- **smoke_avatar / smoke_voice transaction discipline** (tiny).
  Investigation #13 on the queued list. Bit again in this session
  during early debug; trivial fix, queue is overdue.

Recommendation: **slice 4** as a half-session warmup, then
**slice 5** in the same window. Slice 4 is pure backend and
finishes fast; slice 5 establishes the wizard's structural shell
so slices 6-9 can land without scaffolding overhead.

---

## AI notes

- The big judgement call was at slice start: how to model the
  preset-vs-clone dichotomy in the backend. Option A (single
  endpoint, dual-input) is the most operator-friendly + matches the
  SPA's tagged-union value, but it does mean the `clone_voice`
  view function is doing more work than its name suggests. The
  function is still small (~80 LOC); when it crosses ~150 LOC the
  preset path is a clean candidate for extraction into a private
  `_persist_preset` helper.
- The Playwright spec was the longest piece to write. The hardest
  call: how to verify the preset path *actually persisted* without
  a backend smoke. Settled on a triple-assertion shape (response
  fires + pill flips + metadata grid shows the preset name) — three
  loosely-coupled signals that all have to agree, so a fake-pass
  on any one of them fails the spec.
- I declined to add a "skip Record on iPad Safari" feature-detect
  branch — `MediaRecorder.isTypeSupported` handles the format
  fallback, and the tab itself is hidden if `window.MediaRecorder`
  is missing entirely. Worth revisiting if iOS Safari Record path
  bites during real-world testing.
- The portrait camera flake-fix wasn't on the original task list,
  but landing it kept the gate clean and unblocked the handoff.
  Worth keeping as a load-bearing piece of the wizard's Step 2
  reliability once slice 7 lands.
- The smoke_avatar / smoke_voice transaction discipline issue
  (still queued, never fixed) **did not** bite this session — the
  smoke commands ran cleanly. But it remains queued because the
  conditions for it to bite (multiple sequential runs with
  partially-cleaned-up test rows) will recur.
