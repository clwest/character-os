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
> **Last handoff:** `docs/handoffs/SESSION_130_WIZARD_STEP_2.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-7. Slices 8-11 ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1    | Camera capture for `<PortraitUpload>`        | DONE (SESSION 124) |
| W2    | `POST /internal/portrait/` backend           | DONE (SESSION 125) |
| W3    | Voice tabs scaffold + clone-voice preset path | DONE (SESSION 126) |
| W3.5  | `visual_subject` field — "battle unicorn" etc | DONE (SESSION 127) |
| W4    | Tone archetype field + helper                | DONE (SESSION 127) |
| W5    | Wizard scaffold (4 steps, empty bodies)      | DONE (SESSION 128) |
| W6    | Wizard Step 1 — Identity body                | DONE (SESSION 129) |
| W7    | Wizard Step 2 — Portrait body (incl. Generate) | DONE (SESSION 130) |
| W8    | Wizard Step 3 — Voice body                   | NEXT |
| W9    | Wizard Step 4 — Confirm + submit             | Future |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future (foundations landed in W3) |

What's working end-to-end after SESSION 130:

  - Everything from SESSIONS 107-129.
  - Wizard Step 2 — three-mode Portrait input (Upload / Camera /
    Generate) wired through the reducer + a new
    `POST /api/spokespeople/generate-portrait/` action.
  - `visual_subject` field has a UI write site (Generate tab's
    subject input) — closes the SESSION 127 loop.
  - 19 of 19 Playwright specs pass (was 17 — slice added 2).
  - 46 of 46 pytest prompt tests.

---

## SESSION 131 — Wizard slice 8: Step 3 (Voice) body (recommended)

Half-session. Wire the SESSION 126 `<VoiceCapture>` component into
Step 3.

**Recommended scope:**

1. **Embed `<VoiceCapture>`** — render in Step 3 body. Component
   already supports all three modes (Preset / Upload / Record) +
   shared preview pattern. Same testids as the detail-page wiring.
2. **State threading** — `SET_VOICE` reducer action takes the
   tagged-union `VoiceCaptureValue` shape:
   - `{mode: "preset", preset}` → wizard stores `preset` in
     `state.voice.preset` (and the Step 4 submit fires
     `voice_preset` on the create call).
   - `{mode: "upload", dataUri, ...}` or `{mode: "record", ...}` →
     wizard stores `dataUri` in `state.voice.dataUri` (and Step 4
     fires the create + a follow-up `POST /clone-voice/` with
     `audio_data_uri`).
3. **Skip option** — wizard's voice step is optional per the
   scope-lock. Add a "Skip this step" affordance on Step 3 that
   sets `state.voice.mode = "preset"` + `state.voice.preset =
   "vincent"` (Runway's default) and advances. `canAdvance(step=3)`
   stays loose (any state advances) but the skip is explicit so
   the operator knows.
4. **Remove Step 3's ScaffoldBlock + SliceCallout + DebugState.**
5. **Playwright spec** — `web/e2e/wizard-step-3.spec.ts`. Preset
   path (pick vincent → advance). Upload path (drop tiny wav →
   advance). Skip path (click Skip → state.voice has the default
   preset). Defer the Record path (synthetic-audio flake; same
   deferral as SESSION 126's voice-capture spec).

### Out of scope for SESSION 131

- Wizard Step 4 body (slice 9) — Confirm + submit orchestration.
- Template content (slice 10).
- Hide-on-completion full rework (slice 11).
- Flipping the wizard to be the default (lands with slice 9).
- Allauth rate-limit override (queued #14; consider as a
  small standalone slice between W8 and W9 since it's bitten
  three sessions in a row now).

---

## Queued investigations (priority-ordered)

1. **Wizard slice 8 — Step 3 (Voice) body** (SESSION 131).
2. **Allauth signup rate-limit override for tests** — consider
   between W8 and W9. Default 20/m has bitten SESSIONS 129 + 130.
   Small standalone slice: tiny `ACCOUNT_RATE_LIMITS = {}`
   override gated on a test settings flag.
3. **Wizard slice 9 — Step 4 (Confirm + submit).** When this
   ships, also flip the default + retire the legacy form +
   remove the `DebugState` blocks from `<SpokespersonWizard>`.
4. **Wizard slice 10 — Template content** (operator-
   collaborative content work; the slice-6 deferred tile picker
   lands here).
5. **Wizard slice 11 — Hide-on-completion full rework.**
6. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
7. **Stuck-row janitor** — operational hardening.
8. **Additional video kinds** — cinematic / dialogue / long_ad.
9. **Act-Two performance capture** — deferred until Runway
   credits land.
10. **`lesson` video kind** for James-shaped educators.
11. **Real Google OAuth + dj-stripe** — operator gates.
12. **Allauth legacy-settings cleanup.**
13. **smoke_voice / smoke_avatar transaction discipline** — tiny
    fix that's bitten us 3 times now.
14. **Drift verifier** — `verify_doc_claims --only-drift`. Could
    cover `SUPPORTED_VOICE_PRESETS`, `SUPPORTED_PORTRAIT_TEMPLATES`,
    and `TONE_ARCHETYPES` mirrors in one pass.
15. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000 — DO NOT pass --noreload

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
python manage.py smoke_portrait
python -m pytest character_os/prompts/        # 46 tests

# SPA (from web/)
pnpm test
pnpm e2e            # full lifecycle ~34s (19 specs). Note: allauth
                    # signup rate limits at 20/m per IP, so
                    # back-to-back runs may need a 60s wait.
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new?wizard=1
```

Step 2 is the new playground — try the Generate tab with a
mascot template + "armored battle unicorn warrior" subject.

---

## AI / assistant context

- Last session: SESSION 130 — wizard slice 7 (Step 2 Portrait
  body). Three-mode tabbed UI: Upload + Camera (both reuse
  `<UploadDropzone>` / `<CameraCapture>` exports from SESSION 124),
  Generate (new — wraps the SESSION 125 `/internal/portrait/`
  endpoint via a thin Django proxy action). `visual_subject`
  field has a UI write site for the first time.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 131's recommendation
  (Step 3 / Voice body) is the smallest remaining body slice —
  most of the work is plumbing the existing `<VoiceCapture>`
  component into the reducer.
- **Watch:** the allauth signup rate-limit bit again on the first
  full e2e run. **Worth landing the override as a tiny standalone
  slice** between W8 and W9. Two sessions in a row noting it now.
- **Watch:** the `DebugState` blocks still live on Steps 3-4 — by
  design (visible progress signal). Slated for removal in slice 9.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
