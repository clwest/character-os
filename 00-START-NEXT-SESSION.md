---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`
> (5 verbs shipped after SESSION 125).
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_125_INTERNAL_PORTRAIT_ENDPOINT.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1 & 2. Wizard slices 3-11 ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1    | Camera capture for `<PortraitUpload>`        | DONE (SESSION 124) |
| W2    | `POST /internal/portrait/` backend           | DONE (SESSION 125) |
| W3    | Voice tabs scaffold                          | NEXT |
| W4    | Tone archetype field + helper                | (parallel-safe with W3) |
| W5-9  | Wizard scaffold + steps 1-4                  | Future |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future |

What's working end-to-end after SESSION 125:

  - Everything from SESSIONS 107-124.
  - `POST /internal/portrait/` live on the media-engine.
    Synchronous, mock-safe, content-addressed temp-file cache.
  - `MediaEngineClient.create_portrait()` Django-side wrapper.
  - `python manage.py smoke_portrait` covers all 4 templates
    (mascot / founder / coach / local_guide) — passes in mock
    mode.
  - 10 Playwright specs still pass (no SPA changes this slice).

---

## SESSION 126 — Two parallel-safe options

### Option A — Wizard slice 3: Voice tabs scaffold (recommended)

Session-sized. Builds the 3-mode voice capture component
(`<VoiceCapture>`) and wires it into the spokesperson detail
page's setup checklist BEFORE the wizard itself ships.

**Why this slice next:** the SESSION 110 backend already
supports voice cloning; the SESSION 124 Tabs primitive + camera
capture pattern is now well-rehearsed. Operators get visible
voice-clone UI immediately, and the wizard's Step 3 inherits
the component when it lands.

**Recommended scope:**

1. **`web/src/components/voice-capture.tsx`** — new component.
   Three tabs (`Preset` / `Upload` / `Record`):
   - **Preset** — `<select>` populated from a small set of
     Runway voice presets (`vincent`, `marina`, etc.). When
     picked, `value` is `{mode: 'preset', preset: 'vincent'}`.
     No backend call yet — the parent decides what to do.
   - **Upload** — drag-and-drop OR file picker for an audio
     file. `accept="audio/mp3,audio/wav,audio/m4a,audio/webm"`,
     15 MB cap (matches backend `MAX_AUDIO_BYTES`). FileReader
     → base64 data URI. Value: `{mode: 'upload', dataUri,
     fileName, bytes, mime}`.
   - **Record** — `MediaRecorder` API. Permission flow (same
     5-state branching as `<CameraCapture>`: starting / live /
     denied / unsupported / error). Start/Stop/Discard/Use
     buttons. 10-second minimum enforced (Runway's documented
     floor), 5-min cap. Playback preview via
     `<audio src={URL.createObjectURL(blob)}>`. Final value:
     `{mode: 'record', dataUri, bytes, mime: 'audio/webm'}`.
   - **Browser feature detection:** if `MediaRecorder` is
     unavailable, hide the Record tab + show inline "your
     browser doesn't support recording — try Upload" copy on
     the disabled tab.

2. **`useCloneVoice()` mutation hook** in
   `web/src/lib/api/spokespeople.ts`. POSTs to
   `/api/spokespeople/{id}/clone-voice/` (SESSION 110 backend
   action). zod-parsed response. onSuccess invalidates
   `["spokesperson", id]`.

3. **Wire into the spokesperson detail page.** Replace the
   current setup-checklist's "Voice" row with a real "Set up
   voice →" callout that expands to `<VoiceCapture>` inline.
   Operator picks a mode, submits, sees the result.

4. **Playwright spec** — `e2e/voice-capture.spec.ts`. Three
   tests, one per tab:
   - Preset path: pick `vincent` → submit → assert voice_id
     persists on the spokesperson.
   - Upload path: `setInputFiles` with an in-memory silent WAV
     buffer (same trick `smoke_voice` uses) → submit → assert
     voice_id persists.
   - Record path: tricky in Playwright — `MediaRecorder` may
     not work with the synthetic stream. **Defer to a manual
     test** OR find a Playwright recipe (e.g., use Chrome's
     `--use-fake-device-for-media-stream` audio variant). If
     no quick win, skip and document.

### Option B — Wizard slice 4: Tone archetype field

Half-session. Pure backend.

1. `Spokesperson.tone_archetype` CharField with 5 choices
   (`tutor / authority / friend / expert / performer`).
   Migration. Default: `expert`.
2. `suggest_tone_from_brief(brief: str) -> str` in
   `character_os/prompts/brand.py` (mirrors
   `suggest_palette_from_brief` shape). Pytest cases per
   archetype.
3. Surface in `SpokespersonSerializer` (read + write).
4. Surface in zod schemas on the SPA (`spokesperson.ts`).
5. No UI changes yet — wizard Step 1 picks this up when slice 6
   lands.

### Recommendation: **A** (voice tabs).

Reasoning: A unblocks a more visible feature (operators see a
real voice-clone affordance on the detail page). B is
foundation-only — important, but invisible until the wizard
ships. The operator's calibration prefers right-shaping
foundations, but A is also a foundation (the voice-capture
component is the most complex remaining wizard step). Doing A
first means the wizard's Step 3 is mostly already built when
the wizard scaffold lands in slice 5.

If you'd rather land both, A → B in the same session is
plausible if A ships small. Doing A alone is the cleaner
default.

### Out of scope for SESSION 126

- Wizard scaffold (slice 5).
- Wizard steps 1-4 individually (slices 6-9).
- Template content (slice 10).
- Hide-on-completion (slice 11).
- Act-Two performance capture.
- Real Runway calls / credentials.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 3 — Voice tabs scaffold** (SESSION 126
   recommendation).
2. **Wizard slice 4 — Tone archetype field.**
3. **Wizard slices 5-9 — wizard scaffold + steps.**
4. **Wizard slice 10 — Template content** (Riggs / Sasha /
   Donny / Maya; operator-collaborative content work).
5. **Wizard slice 11 — Hide-on-completion detail page rework.**
6. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
7. **Stuck-row janitor** — operational hardening.
8. **Additional video kinds** — cinematic / dialogue / long_ad.
9. **Act-Two performance capture** — deferred until Runway
   credits land.
10. **`lesson` video kind** for James-shaped educators.
11. **Real Google OAuth + dj-stripe** — operator gates.
12. **Allauth legacy-settings cleanup.**
13. **smoke_voice / smoke_avatar transaction discipline** —
    tiny fix that's bitten us 3 times now.
14. **Drift verifier** — `verify_doc_claims --only-drift`.
15. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo   # required for video pipeline

cd web && pnpm dev                          # :5174
```

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait              # SESSION 125
python -m pytest character_os/prompts/        # 31 tests

# SPA (from web/)
pnpm test
pnpm e2e            # full lifecycle ~24s (10 specs)
```

---

## AI / assistant context

- Last session: SESSION 125 — wizard slice 2 (`/internal/portrait/`
  backend). Half-session; pattern-matched against SESSIONS
  108/109/110 (extract from legacy service, wrap in `/internal/*`
  contract, write smoke). All gates clean.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 126's recommendation
  (voice tabs) is foundation-shaped — the most complex wizard
  step landing before the wizard's outer scaffold.
- Templates (Riggs / Sasha / Donny / Maya) still need real
  content work — operator-collaborative pass.
- **Watch:** the smoke_voice / smoke_avatar transaction
  discipline issue bit again this session. Three sessions in a
  row noting it. Worth landing the fix soon (it's tiny).
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
