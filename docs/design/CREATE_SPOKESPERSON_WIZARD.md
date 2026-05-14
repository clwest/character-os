---
title: "Create-Spokesperson Wizard — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-05-13 (SESSION 123)
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "SPA_ARCHITECTURE.md"
  - "BRAND_IDENTITY_V1.md"
  - "MEDIA_ENGINE_INTERNAL_API.md"
  - "PROMPT_HELPERS.md"
phase: 3
---

# Create-Spokesperson Wizard

> **Read first:** `UI_REDESIGN_V2.md` §5.2 (first-run onboarding
> screens S-05 → S-08), `SPA_ARCHITECTURE.md` §"First three
> screens" (the slice this doc supersedes), and the SESSION 122
> handoff (Tier 1 prompt helpers + the discussion that produced
> this doc's locked decisions).

---

## Purpose

The current `/spokespeople/new` route (SESSION 120) collects
three fields: name, business brief, optional portrait upload.
It works — but it leaves voice + tone + animated motion to be
configured later, on the detail page. After SESSION 122's
research + a discussion with the operator about real customer
use cases (James the high-school history teacher, who wants a
battle unicorn that dresses up in historical garb per lesson),
a richer **one-time setup wizard** is the right shape.

This doc locks the wizard's surface area: step inventory,
per-step backend calls, archetype model, voice flow shape,
hide-on-completion pattern, and the prompt-helper wiring points.
It plays the same role for the wizard that
`SPA_ARCHITECTURE.md` plays for the SPA as a whole — locks
shape, not implementation.

### Why scope-lock first

Per the operator's calibration profile
(`docs/TRUST_CALIBRATION.md`), foundations get right-shaped
early. The wizard's surface area touches multiple existing
slices — `POST /api/spokespeople/`, `/internal/avatars/`,
`/internal/voices/`, the SESSION 117 dashboard masthead, the
SESSION 118 spokesperson detail's setup-checklist — and
introduces new shapes (camera capture, audio capture,
two-axis archetypes). Locking the contract now keeps the
implementation slices clean.

---

## Contract rules (load-bearing)

These bind every wizard-related slice the same way
`SPA_ARCHITECTURE.md`'s 6 rules bind every SPA slice.

1. **Wizard is for new spokespeople only.** Editing an existing
   spokesperson happens on the detail page (SESSION 118), not by
   re-running the wizard. The wizard's destination is creation.
2. **The v1 floor is name + business_brief + portrait.** Any
   other field can be skipped. The detail page surfaces "ready to
   set up" callouts for skipped optionals.
3. **Pure JSON in, pure JSON out.** Same rule as
   `MEDIA_ENGINE_INTERNAL_API.md` rule 1. Camera + audio + video
   capture all encode to base64 data URIs in the JSON request
   body. No multipart uploads.
4. **No conversational chat.** Linear form-driven. Each step is a
   single screen with form fields + suggestions. Operator can go
   Back, Next, Skip per-step (where allowed). No follow-up
   questions from the system mid-step.
5. **Templates pre-fill; archetypes default.** Picking Sasha
   pre-fills every field; the operator can override anything.
   Picking an archetype (fresh path) sets sensible defaults that
   the operator overrides on each step.
6. **No silent failure.** Skipping is explicit (button:
   "Skip — set up later"). Skipped steps surface as setup-pending
   callouts on the detail page so the operator never "loses"
   work.

---

## Step inventory (locked)

Four steps. Identity is always first; the rest's order is locked
for predictability.

### Step 1 — Identity (always required)

Entry-point branches the rest of the wizard:

- **Template pick path:** 3–4 named template spokespeople
  rendered as tiles (Riggs / Sasha / Donny + possibly a Tutor —
  see §"Templates" below). Operator clicks a tile → all
  subsequent fields pre-fill from the template's defaults.
- **Fresh path:** operator clicks "Start from scratch" → fills
  in name + business_brief + (optional) tone archetype.

Inputs collected on this step:
- `name` (text, required) — display name.
- `business_brief` (textarea, required) — one paragraph. Wired
  through `clean_business_brief()` (SESSION 122) on save to
  strip fillers without mangling voice.
- `tone_archetype` (dropdown, optional) — 5 options:
  - `tutor` — patient, explanatory, classroom-friendly
  - `authority` — direct, decisive, expert
  - `friend` — warm, conversational, peer-level
  - `expert` — precise, detail-oriented, credentialed
  - `performer` — energetic, memorable, persuasive

When operator types in `business_brief`, the SPA calls
`suggest_palette_from_brief()` (SESSION 122) client-side via a
new helper endpoint OR with the helpers ported to TypeScript;
the inferred palette + tone surface as inline suggestions
("looks like an `eco_natural` brief — we'll suggest a palette
on the next step").

Backend calls on Step 1: **none** — the wizard accumulates state
client-side until Confirm.

### Step 2 — Portrait (required)

Three input modes (tabbed UI):

- **Upload** — extends the SESSION 120 `<PortraitUpload>`
  component. PNG / JPEG / WebP, 5 MB cap. FileReader → base64.
- **Camera capture** — `getUserMedia({video: true})` → `<video>`
  preview → `<canvas>.toDataURL("image/png")`. Operator can
  re-take. HTTPS required in production; localhost works for dev.
- **Generate** (fresh path only) — pick a visual archetype
  (4 options from inherited `PORTRAIT_TEMPLATES`):
  - `mascot` — anthropomorphic brand character (James's battle
    unicorn lives here)
  - `founder` — polished business spokesperson
  - `coach` — energetic motivator
  - `local_guide` — welcoming local-business face
  Operator types a subject hint into the `visual_subject` input
  ("battle unicorn warrior" / "fifty-something accountant" /
  "neon-pink raccoon in a denim jacket"); SPA POSTs to a new
  `/internal/portrait/` endpoint (see §"Backend additions");
  Runway gen4_image generates a portrait; operator approves or
  regenerates. The subject text persists on the row as
  `Spokesperson.visual_subject` so later regenerations + the
  detail-page "edit visual" affordance can reuse it.

Backend calls on Step 2:
- **Camera + Upload:** none yet. Image data accumulated
  client-side.
- **Generate:** `POST /internal/portrait/` → returns a hosted
  image URL or data URI; not persisted until Confirm.

The picked image gets cached client-side as a data URI for the
Confirm step. The visual archetype (if used) is stored
alongside; future re-generation on the detail page can reuse it.

### Step 3 — Voice (optional, defaults to preset)

Three input modes (tabbed UI):

- **Preset** — dropdown of `SUPPORTED_VOICE_PRESETS` from the
  media-engine (`vincent`, `marina`, etc.). Picking a preset
  stores the preset name on `Spokesperson.voice_id`; no Runway
  clone fires.
- **Upload** — audio file picker. Same shape as PortraitUpload
  but `accept="audio/mp3,audio/wav,audio/m4a,audio/webm"`. 15 MB
  cap (matches backend's `MAX_AUDIO_BYTES`).
- **Record** — `MediaRecorder` API → WebM/Opus capture →
  playback preview → "Use this clip" commits. Safari/iOS may
  not support `MediaRecorder` in all configurations; we **hide
  the Record tab** when `typeof MediaRecorder === 'undefined'`
  and surface a "Your browser doesn't support recording — try
  upload instead" tooltip on the disabled tab.

Skip button visible on this step. Skipping = use the
spokesperson's `voice_preset` default (set on Step 1 from the
tone archetype, or `"vincent"` if no archetype was picked).

Backend calls on Step 3:
- **Preset:** none — picked preset name stored client-side.
- **Upload / Record:** none yet. Audio data accumulated as
  base64.

(The actual `POST /internal/voices/` call fires on Confirm —
see §"Confirm-step orchestration" below.)

### Step 4 — Confirm (always required)

Review screen. Shows everything the operator's about to create:

- Portrait thumbnail (or generated preview)
- Name + business_brief + tone_archetype
- Voice mode (preset name OR audio waveform / playback for
  uploaded/recorded clips)
- Visual archetype (if fresh path + generated portrait)
- Optional brand palette suggestion (from
  `suggest_palette_from_brief`)

Operator clicks "Create spokesperson." The Confirm step
**orchestrates the actual creation:**

1. `POST /api/spokespeople/` with name + business_brief +
   `portrait_data_uri` + `voice_preset` → creates the row +
   fires `/internal/avatars/` to bind the Runway avatar
   (existing SESSION 116 backend flow).
2. **If Upload or Record on Step 3:** the SPA also POSTs
   `/api/spokespeople/{id}/clone-voice/` with the
   `audio_data_uri` → fires `/internal/voices/` → updates
   `Spokesperson.voice_id`.
3. Once both calls return ready/mock, navigate to
   `/spokespeople/{id}`.

Failures on individual steps surface as inline errors on the
Confirm screen with retry affordances. Partial success (avatar
ready, voice clone failed) commits the row with what worked +
leaves the voice as "ready to set up" on the detail page —
the operator can retry from the detail page's setup callouts.

---

## Templates (3–4 named spokespeople)

Per `UI_REDESIGN_V2.md` §5.2: "Three template picks (Riggs /
Sasha / Donny) OR start from scratch." This wizard locks that
shape and may extend to 4 templates if a Tutor is added.

Each template ships with:

- **Name** (display name)
- **Portrait** — pre-generated PNG, stored in
  `web/public/templates/{slug}.png` OR generated on-demand from
  a locked subject + visual archetype combo (cleaner — the
  template is just a recipe).
- **Voice preset** — picked from `SUPPORTED_VOICE_PRESETS`
- **business_brief** — written content, ~2-3 sentences
- **tone_archetype** — pre-assigned
- **visual_archetype** — pre-assigned

Operator picking a template = the wizard pre-fills every field
across all 4 steps with the template's values. Operator can
override anything before clicking Create on Step 4.

### Provisional template slate

(For sign-off when we move from doc to design content.)

| Template | Visual | Tone | Voice preset | Audience |
|---|---|---|---|---|
| **Riggs** | `founder` | `authority` | TBD | SMB owners — coffee shops, retail, professional services |
| **Sasha** | `coach` | `friend` | TBD | Creators — coaches, course-sellers, lifestyle brands |
| **Donny** | `local_guide` | `expert` | TBD | Local businesses — bike shops, restaurants, contractors |
| **Maya?** (placeholder) | `mascot` | `tutor` | TBD | Educators — teachers, course-creators (added per James's use case) |

The names + voices + briefs need real design work — operator-
led content pass, not code. The data model + storage shape is
the wizard's job to lock; the actual identities are content.

---

## Two-axis archetype model

The wizard separates **visual** archetypes from **tone**
archetypes, treating them as orthogonal axes. This came out of
discussion about James's battle unicorn use case — the visual
form (mascot-shaped) and the persona (tutor-shaped) are
genuinely different decisions.

### Visual archetypes (4)

Already exist in inherited `media-engine/app/services/character_studio_client.py::PORTRAIT_TEMPLATES`.
Drive `gen4_image` portrait generation:

| Key | Default subject | Expression cue |
|---|---|---|
| `mascot` | a friendly brand mascot | Calm confident expression |
| `founder` | a polished founder spokesperson, mid-30s | Direct trustworthy gaze with a soft natural smile |
| `coach` | an energetic coach spokesperson, mid-30s | Confident bright expression |
| `local_guide` | a welcoming local-business spokesperson | Welcoming friendly expression |

The visual archetype is stored implicitly via the resulting
portrait — there's no `Spokesperson.visual_archetype` field
(the *category* lives only in the portrait that got generated).
**However**, we **do** store `Spokesperson.visual_subject` — a
free-text description of the subject ("armored battle unicorn",
"neon-pink raccoon in a denim jacket"). This is the field
operators were asking for after SESSION 126 ("where do I say my
spokesperson is a raccoon?"). Landed ahead of slice 4 as **slice
3.5** — see `docs/handoffs/SESSION_127_*` once it ships.

`visual_subject` is `blank=True` — empty means "use the template's
built-in default subject" (e.g. `mascot` template's default is
"a friendly brand mascot"). When set, it's threaded into
`/internal/portrait/`'s `subject` parameter on portrait
generation.

### Tone archetypes (5)

NEW concept. Drives voice selection + future render-flow prompt
augmentation.

| Key | Voice character | Script tone |
|---|---|---|
| `tutor` | patient, measured, gentle pacing | explanatory, scaffolded, "let me show you" |
| `authority` | direct, confident, low-pitched | decisive, opinionated, "here's the truth" |
| `friend` | warm, conversational, mid-pitched | peer-level, casual, "between you and me" |
| `expert` | precise, articulate, controlled | detail-oriented, evidence-based, credentialed |
| `performer` | energetic, dynamic, varied pitch | persuasive, memorable, "wait until you see this" |

**Stored as:** new `Spokesperson.tone_archetype` CharField with
`choices = [Tone.choices]`. ~10-line migration. Queryable +
indexable for future tone-aware filters in the dashboard.

Tone defaults to `expert` if not picked (the safest neutral for
SMBs). Templates set it explicitly.

---

## Hide-on-completion pattern

Once the wizard finishes, the spokesperson detail page (SESSION
118) extends to support an "either / or" surface:

- **Fully configured spokesperson** (portrait + voice clone +
  tone + brief + Act-Two when shipped): detail page renders
  the identity panel + render history + a small "Edit" affordance
  that surfaces a modal with the wizard's fields for in-place
  modification.
- **Partially configured spokesperson** (portrait + some
  combination of skipped voice / Act-Two / tone): detail page
  renders the SESSION 118 setup-checklist for **just** the
  skipped/optional items, with CTAs that route to focused
  flows (e.g., "Clone a voice → upload OR record" without
  re-running the whole wizard).

The setup-checklist pattern from SESSION 118 already supports
this — we extend its item-builder (`buildSetupItems`) to
include "voice clone" + "tone archetype" + future "Act-Two
performance" rows.

Operators who completed everything in the wizard see a clean,
focused detail page. Operators who skipped see a small "ready
to enhance" callout. Nobody feels nagged.

---

## Backend additions (new endpoints)

Two new `/internal/*` endpoints required for the wizard. Both
follow `MEDIA_ENGINE_INTERNAL_API.md`'s 5 contract rules.

### `POST /internal/portrait/`

Generate a portrait via Runway `gen4_image`. Wraps the
inherited `character_studio_client.generate_portrait()` with
the `/internal/*` JSON contract.

Request:
```json
{
  "template": "mascot",
  "subject": "armored battle unicorn warrior",
  "style": "editorial illustration"
}
```

Response (sync, ~10-20 s real-mode, instant in mock):
```json
{
  "portrait_data_uri": "data:image/png;base64,...",
  "template": "mascot",
  "mock_mode": true
}
```

Mock-mode short-circuits to a deterministic placeholder per
the existing `character_studio_client` mock branch. Real-mode
calls Runway `gen4_image`, downloads the result, returns as
data URI for the SPA to commit on Confirm.

### `POST /api/spokespeople/{id}/regenerate-portrait/`

(Detail page action, deferred to a post-wizard slice — but
worth flagging here.) Same shape as Step 2 Generate but for
existing spokespeople. Allows the operator to re-roll the
portrait without re-creating the spokesperson row. Needs
`/internal/portrait/` already shipped.

---

## Prompt-helper wiring points

The Tier 1 helpers landed SESSION 122 are wired in at four
points:

1. **Step 1 brief save:** `clean_business_brief(brief)` strips
   fillers from operator-typed text before storing on
   `Spokesperson.business_brief`. Idempotent — running twice
   doesn't change the output.

2. **Step 1 inline suggestion (palette):**
   `suggest_palette_from_brief(brief)` returns a palette name;
   the SPA shows it as a swatch beneath the brief textarea
   ("looks like an `eco_natural` brief — preview the palette
   →"). Operator can ignore.

3. **Step 1 inline suggestion (tone):** when the operator
   doesn't pick a tone archetype, a similar keyword heuristic
   suggests one ("warm + classroom + history" → `tutor`).
   **New helper needed:** `suggest_tone_from_brief(brief)` in
   `character_os/prompts/`. Mirrors `suggest_palette_from_brief`
   shape; same keyword-hints table approach.

4. **Step 4 confirm summary:** `principles_for_kind('spokesperson_ad')`
   surfaces the top key_principle in editorial copy on the
   Confirm screen ("Your spokesperson is ready to do
   spokesperson ads — direct address, one claim, one CTA.").

The `sharpen_prompt()` aggressive pass is **not** used in the
wizard — that's for internal system prompts only (render-flow
script generation). The wizard never sends operator text to a
model that aggressive sharpening would benefit.

---

## Camera + audio capture: Browser API contract

The wizard introduces two new browser-API-heavy components.
Both have well-known cross-browser quirks.

### Camera capture (Step 2)

```ts
const stream = await navigator.mediaDevices.getUserMedia({
  video: { facingMode: "user", width: { ideal: 1024 } },
  audio: false,
});
```

- **Permission:** browser prompts on first call. Decline →
  surface inline "Camera access needed — or upload a portrait
  instead" copy with the Upload tab as the fallback.
- **HTTPS required in production.** Localhost works for dev.
  Vite proxy preserves the secure context.
- **iOS Safari:** requires user-gesture trigger; capture
  triggers on button click, not on tab focus.
- **Capture:** `<video srcObject={stream}>` for preview;
  `<canvas>` with `drawImage(video, 0, 0)` for the freeze
  frame; `canvas.toDataURL("image/png")` for the base64 result.
- **Cleanup:** `stream.getTracks().forEach(t => t.stop())` on
  unmount + after capture commits, so the camera light goes
  off promptly.

### Audio capture (Step 3 Record)

```ts
const stream = await navigator.mediaDevices.getUserMedia({
  audio: { echoCancellation: true, noiseSuppression: true },
});
const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
```

- **`MediaRecorder` availability check:**
  `typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported("audio/webm")`.
  When unsupported: hide the Record tab entirely, surface
  Upload as the primary path.
- **Recording controls:** Start / Stop / Discard / Use this
  clip. Playback preview via `<audio src={URL.createObjectURL(blob)}>`.
- **Format:** WebM/Opus output. Backend `voice_clone_client`
  accepts via `SUPPORTED_AUDIO_MIMES` ({audio/webm}).
- **Length:** enforce 10-second minimum (matches Runway's
  voice clone documented minimum) + 5-minute maximum.
  Disable Stop until 10 s elapsed.
- **Cleanup:** Stop the MediaRecorder + close the stream on
  commit OR navigation OR unmount.

---

## Out of scope (explicitly)

- **Act-Two performance capture.** Deferred to a future detail-
  page slice when real Runway credentials land. Wizard ships
  4 steps; Act-Two would have been step 5.
- **Conversational wizard UX.** Linear form locked. Multi-turn
  chat is a Phase 4 user-research-driven upgrade.
- **AI-generated voice tone descriptions.** The tone archetype
  list is locked at 5. No "describe a custom tone in words"
  field — defer to Phase 4.
- **Per-video costume / styling fields on the Spokesperson
  model.** Costumes live in the per-video `brief`. James's
  unicorn changes outfits via the render flow's brief textarea,
  not via the wizard.
- **Multi-spokesperson templates** (e.g., "Sasha + Donny as a
  dialogue pair"). Templates are single-spokesperson; the
  `dialogue_scene` kind ships its own multi-spokesperson UX in
  a future slice.
- **Mobile / responsive optimization.** Wizard is desktop-first
  for v1. The form layout responds, but the wizard doesn't
  optimize for phone-camera capture specifically (the iPhone
  user uploads from photos.app instead).

---

## Open questions (resolve before implementation)

These are smaller decisions the implementation slice can default
on, but worth surfacing in case the operator has opinions:

- **Q-wiz-1 — Template portrait storage.** Pre-render the four
  template portraits and check them into `web/public/templates/`
  (binary in git — small files, but adds friction), OR generate
  on-demand from the locked subject + template combo and cache
  the result (no binary in git, but adds wizard latency on
  first-pick). **Recommendation:** pre-render + commit.
- **Q-wiz-2 — Tone archetype label text.** The labels in §"Tone
  archetypes (5)" are placeholder copy. Likely worth a content
  pass before ship.
- **Q-wiz-3 — Wizard step persistence.** If the operator
  refreshes mid-wizard, do we restore in-flight state from
  `sessionStorage` or start over? **Recommendation:** start
  over for v1. SessionStorage adds complexity for an unusual
  case.
- **Q-wiz-4 — `regenerate-portrait` placement.** Detail page
  action that re-fires `/internal/portrait/`. Should it live in
  the wizard's edit-mode (modal) or as its own affordance on
  the detail page identity panel? **Recommendation:** detail
  page identity panel as an inline edit affordance — feels
  natural alongside the existing identity metadata.

---

## Implementation order (recommended)

The wizard isn't a single slice — it's a sequence of slices
that can land independently. Recommended order:

1. **Camera capture for existing `<PortraitUpload>`** (half
   session). Lands the camera-API foundation before the
   wizard. Adds "Take a picture" mode to the SESSION 120
   create-spokesperson flow as-is. Pure SPA work.
2. **`/internal/portrait/` backend endpoint** (half session).
   Wraps the inherited `character_studio_client.generate_portrait()`
   with the `/internal/*` JSON contract. New
   `MediaEngineClient.create_portrait()` wrapper. Smoke test.
3. **Voice tabs scaffold** (session). The three-mode voice
   input (Preset / Upload / Record) as a reusable component.
   Lands on the existing `/spokespeople/{id}/clone-voice/`
   action (SESSION 110 backend) without yet integrating into
   the wizard. Used immediately on the detail page setup
   checklist.
4. **Tone archetype model field + suggest_tone_from_brief**
   (half session). Migration + helper in
   `character_os/prompts/`.
5. **Wizard scaffold** (session). Multi-step state, navigation,
   template-pick-vs-fresh entry point. No content yet.
6. **Wizard Step 1 wired** (session). Identity step with all
   helpers + suggestions. Persists nothing yet.
7. **Wizard Step 2 wired** (session). Portrait step with three
   input modes.
8. **Wizard Step 3 wired** (session). Voice step with three
   input modes.
9. **Wizard Step 4 wired** (session). Confirm step with full
   backend orchestration.
10. **Template content** (out-of-session, content work). Riggs /
    Sasha / Donny / Maya designed + portraits generated + briefs
    written.
11. **Hide-on-completion detail page rework** (session). Extends
    SESSION 118's setup-checklist to handle the new fields.

Roughly 6–8 sessions of work from start to wizard-fully-shipped.
Slices 1–4 are foundational + parallel-safe — operators can pick
which to land first.

---

## Change log

- 2026-05-13 (SESSION 123) — Initial scope lock. No code yet.
