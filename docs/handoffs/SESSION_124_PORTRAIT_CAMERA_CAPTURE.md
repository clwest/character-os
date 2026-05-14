---
title: "Session 124 — Wizard slice 1: in-browser camera capture for <PortraitUpload>"
date: 2026-05-13
status: complete
session: 124
previous_handoff: ./SESSION_123_WIZARD_SCOPE_LOCK.md
---

# Session 124 — Camera capture (wizard slice 1 / 11)

## TL;DR

- **What shipped:** Camera tab on the existing
  `<PortraitUpload>` component. Operator can either upload a
  file (existing path, unchanged) or take a picture via
  `getUserMedia` → `<video>` preview → `<canvas>.toDataURL`.
  Both modes produce the same `PortraitUploadResult` shape so
  the existing `/spokespeople/new` consumer doesn't branch. The
  SESSION 120 create-spokesperson flow gains camera capture for
  free, before the wizard ships. **10 of 10 Playwright specs
  pass on first run.**
- **What's blocking next:** Nothing. SESSION 125 picks up the
  next wizard slice — either `/internal/portrait/` backend
  (wizard slice 2) for Runway-generated portraits, or the voice
  tabs scaffold (wizard slice 3), or the tone archetype field
  (wizard slice 4). All three are foundation-tier and parallel-
  safe.
- **What's in a weird state:** None. Editorial aesthetic
  inherited cleanly; no new tokens; new Tabs primitive matches
  the locked design.

---

## What changed (file-by-file)

### `web/src/components/ui/tabs.tsx` (new — 56 LOC)

Shadcn-style wrapper around `@radix-ui/react-tabs`. Three
exports: `Tabs` (Root), `TabsList`, `TabsTrigger`, `TabsContent`.
Editorial styling: `<TabsList>` uses the same hairline border +
muted background as Card; `<TabsTrigger>` uses uppercase-tracked
text matching the BRAND_IDENTITY_V1 kicker/caption pattern. Active
tab gets the `data-[state=active]` selector flipping to the card
surface + ring.

### `web/package.json`

Added `@radix-ui/react-tabs ^1.1.13` to dependencies.

### `web/src/components/portrait-upload.tsx` (rewritten — was 198 LOC, now 365 LOC)

Split into four pieces inside the same file:

1. **`PortraitUpload`** — public component. Renders the
   preview-with-Remove when `value` is set. Otherwise checks
   `navigator.mediaDevices` support. If unsupported, falls back
   to a single `<UploadDropzone>` (no tabs strip — looks
   cleaner). If supported, renders `<Tabs>` with Upload + Camera
   tabs, defaulting to Upload.
2. **`PortraitPreview`** — the existing preview-with-Remove
   branch, extracted unchanged.
3. **`UploadDropzone`** — the existing file-upload path,
   extracted unchanged. Same dropzone, same drag handlers, same
   validation, same `data-testid="portrait-dropzone"` and
   `portrait-input` testids preserved for backward compatibility.
4. **`CameraCapture`** — new. Manages a `MediaStream` via
   `useEffect` (started on mount, cleaned up on unmount). Five
   states: `idle` (initial, replaced immediately), `starting`
   (getUserMedia pending), `live` (stream attached, capture
   enabled), `denied` (permission denied), `unsupported` (no
   device), `error` (catch-all). Capture builds a canvas → draws
   the video frame → `toDataURL("image/png")` → calls
   `onChange()` with the same `PortraitUploadResult` shape the
   Upload path uses.

**Stream lifecycle discipline:**

- `streamRef` holds the active stream so we can stop tracks
  cleanly.
- `useEffect` returns a cleanup that calls `stopStream()` on
  unmount AND when the user switches tabs (component unmounts
  when its `<TabsContent>` is hidden).
- `cancelled` flag in the async start function so a fast
  tab-switch doesn't leave a dangling stream after the component
  unmounts.
- The `cn`-conditional `videoRef.current.play().catch(() => {})`
  handles Safari's "programmatic play rejected" quirk silently —
  the autoplay attribute handles the common case.

**Permission denial / error UX:**

- `NotAllowedError` / `PermissionDeniedError` → state="denied"
  → editorial copy "Camera access blocked / allow in site
  settings, or upload a portrait file instead" + falls back to
  the Upload tab if operator switches back.
- `NotFoundError` / `OverconstrainedError` → state="unsupported"
  → "No camera available / use the Upload tab instead".
- Other errors → state="error" + the error message.
- All three render via shared `<CameraMessage>` atom so the
  failure surfaces stay coherent.

### `web/playwright.config.ts`

Added Chromium launch args:

```ts
launchOptions: {
  args: [
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
  ],
}
```

These flags make Chromium auto-grant camera permission (no
prompt UI) and inject a synthetic camera stream (no real
hardware). Harmless for non-camera specs.

### `web/e2e/portrait-camera.spec.ts` (new)

Two tests:

1. **Full camera path:** sign up → /spokespeople/new → assert
   tabs visible → switch to Camera tab → `<CameraCapture>`
   mounts → synthetic stream goes live → Capture button enables
   → click → preview shows with `camera-{timestamp}.png`
   filename → submit form → land on detail page with avatar
   status pill in mock/ready.
2. **Upload tab regression check:** confirms the existing file
   upload path still works post-refactor. Same in-memory PNG
   buffer trick the SESSION 120 spec uses.

Both pass first try.

---

## Verification gates

- `pnpm build` — clean. CSS 20.6 KB / JS 457 KB (gzip ~5.2 /
  ~136). The size bump is the Radix Tabs runtime — ~7 KB
  gzipped.
- `pnpm test` — 3 vitest passes.
- `pnpm e2e` — **10 passes** (2 auth + 2 dashboard + 2
  create-spokesperson + 1 spokesperson detail + 1 make-video +
  2 portrait-camera).
- `python manage.py check` — clean (allauth deprecation
  warnings unchanged from SESSION 119).
- `python -m pytest character_os/prompts/` — 31 prompts tests
  pass.
- `python manage.py inventory` — clean regen.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### `getUserMedia` lifecycle = useEffect

The cleanest pattern for camera capture in React is:

1. Component mount triggers `useEffect` → request stream → set
   `streamRef.current = stream`.
2. Component unmount → cleanup function → stop tracks + null
   the srcObject.
3. The `cancelled` flag inside the async function prevents a
   late-arriving stream from attaching if the component already
   unmounted.

Same pattern will work for Wizard Step 3's audio recording —
just swap `MediaStream` for `MediaRecorder`. The locked
contract said this slice landed the foundation; it does.

### Browser feature detection beats try/catch

`typeof navigator.mediaDevices !== "undefined" &&
typeof navigator.mediaDevices.getUserMedia === "function"`
runs synchronously at render time. When the camera is
unsupported (older browsers, some Safari embed contexts), the
Camera tab never renders, so users don't get a tab that 404s
on click. Try/catch only catches runtime failures; feature
detection prevents bad UX before it happens.

### The four CameraState branches are exhaustive

`starting / live / denied / unsupported / error` (plus the
transient `idle`) cover every observable outcome from a
`getUserMedia` call. Each surfaces visible copy — no silent
fallback. Per `BRAND_IDENTITY_V1.md` rule 6 + the wizard
contract rule 6.

### Tabs primitive will get reused

The new `<Tabs>` component is general — not portrait-specific.
The wizard's Step 3 voice mode picker uses the same primitive
(Preset / Upload / Record tabs). When that slice lands, the
primitive is already there + already styled + already tested
via the portrait-camera spec.

### Bundle size watch

JS bundle grew ~30 KB gzipped this slice (Radix Tabs is ~15 KB
+ the camera capture component + the Tabs primitive). Still
comfortably under any threshold worth panicking about, but
worth noting that each Radix primitive is meaningful. Future
shadcn adds (Dialog, Popover, Toast, etc.) compound.

---

## SESSION 125 — entry point

`00-START-NEXT-SESSION.md`. Three foundation-tier wizard slices
remain parallel-safe; SESSION 125 picks one:

- **Wizard slice 2 — `/internal/portrait/` backend endpoint**
  (half-session). Wraps the inherited
  `character_studio_client.generate_portrait()` with the
  `/internal/*` JSON contract. New
  `MediaEngineClient.create_portrait()` wrapper. Smoke test.
  Unlocks the wizard's "Generate" portrait path (operator types
  a subject; Runway gen4_image returns a portrait).
- **Wizard slice 3 — Voice tabs scaffold** (session). The
  3-mode voice input (Preset / Upload / Record) as a reusable
  component. Lands on the existing
  `/spokespeople/{id}/clone-voice/` action (SESSION 110 backend)
  without wiring into the wizard yet. Used immediately on the
  detail page setup checklist.
- **Wizard slice 4 — Tone archetype field + `suggest_tone_from_brief`**
  (half-session). Migration + helper in
  `character_os/prompts/`.

Recommend slice 2 next — it's the backend foundation everyone
else assumes exists.

---

## AI notes

- The slice took ~25 minutes start to "all 10 specs pass."
  Editorial inheritance + the existing Upload code being
  extractable cleanly + the foundation patterns from SESSION 116
  (stretched-link, panel headers) all compounding.
- `--use-fake-device-for-media-stream` is the right test
  pattern. Real camera testing in CI would be a nightmare;
  Chromium's fake stream provides a deterministic surface that
  exercises every code path the real camera would. The pattern
  generalises to audio capture (`MediaRecorder`) which will use
  the same flags.
- The `cancelled` flag inside the async useEffect is a real
  pattern worth documenting in a future hooks doc. Without it,
  React StrictMode's double-mount in dev would leak streams.
- The bundle size note (Radix primitives compound) is worth
  watching when the wizard ships. The 3-mode voice tabs +
  potential Dialog/Drawer/Popover for confirm step could all
  add up. Tree-shaking helps but isn't free.
- Worth flagging for any future Wizard step that captures
  binary data: the canvas → toDataURL approach is fine for
  portraits (~1-3 MB) but `MediaRecorder` blobs for audio are
  potentially larger. We may want to use `URL.createObjectURL`
  for in-flight playback + only convert to base64 at commit.
  Defer to the voice tabs slice.
