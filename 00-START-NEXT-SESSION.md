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
> **Last handoff:** `docs/handoffs/SESSION_129_WIZARD_STEP_1.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-6. Slices 7-11 ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1    | Camera capture for `<PortraitUpload>`        | DONE (SESSION 124) |
| W2    | `POST /internal/portrait/` backend           | DONE (SESSION 125) |
| W3    | Voice tabs scaffold + clone-voice preset path | DONE (SESSION 126) |
| W3.5  | `visual_subject` field — "battle unicorn" etc | DONE (SESSION 127) |
| W4    | Tone archetype field + helper                | DONE (SESSION 127) |
| W5    | Wizard scaffold (4 steps, empty bodies)      | DONE (SESSION 128) |
| W6    | Wizard Step 1 — Identity body                | DONE (SESSION 129) |
| W7    | Wizard Step 2 — Portrait body (incl. Generate) | NEXT |
| W8    | Wizard Step 3 — Voice body                   | Future |
| W9    | Wizard Step 4 — Confirm + submit             | Future |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future (foundations landed in W3) |

What's working end-to-end after SESSION 129:

  - Everything from SESSIONS 107-128.
  - Wizard Step 1 — real Identity form with name + brief +
    tone_archetype select + inline tone suggestion (powered by
    `GET /api/prompts/suggest-tone/?brief=...`).
  - `canAdvance` for Step 1 gates on name AND brief (≥ 8 chars,
    matches the legacy form's createSchema).
  - 17 of 17 Playwright specs pass (was 15 — slice added 2).
  - 46 of 46 pytest prompt tests.

---

## SESSION 130 — Wizard slice 7: Step 2 (Portrait) body (recommended)

Session-sized — this is the largest remaining slice. Brings together
SESSION 124 (`<PortraitUpload>`), SESSION 125
(`POST /internal/portrait/`), and SESSION 127's `visual_subject`
foundation into a three-mode portrait input.

**Recommended scope:**

1. **Three-mode input** — wire `<PortraitUpload>` (Upload + Camera
   tabs) into the Step 2 body. Each mode commits via
   `SET_PORTRAIT` dispatches.
2. **Generate tab** — third option alongside Upload + Camera.
   Inputs:
   - **Visual template select** — 4 options from inherited
     `PORTRAIT_TEMPLATES` (`mascot / founder / coach /
     local_guide`).
   - **`visual_subject` text input** — free-text "what they look
     like." Wires to the SESSION 127 model field.
   - **Optional `style` text** — passes to the
     `/internal/portrait/` `style` param.
   - **Submit** — POSTs to a new
     `POST /api/spokespeople/generate-portrait/` endpoint that
     wraps `MediaEngineClient.create_portrait()`. Returns
     `{portrait_data_uri, prompt}`. The SPA renders a preview +
     a "Use this portrait" CTA + a "Regenerate" CTA.
3. **State threading** — the chosen mode + the
   `portrait_data_uri` + the typed `visual_subject` text all
   route through the reducer (`SET_PORTRAIT` carries the data;
   `SET_IDENTITY` already accepts `visual_subject`). Slice 9 reads
   from both bags on submit.
4. **Tighten `canAdvance` for Step 2** — require a portrait
   chosen (any mode). Today it's `true` unconditionally.
5. **Remove ScaffoldBlock + SliceCallout from Step 2** (keep on
   Steps 3 + 4 until slices 8 + 9 ship).
6. **Playwright spec** — `web/e2e/wizard-step-2.spec.ts`. Upload
   path + Generate path (mock-mode is deterministic; same shape
   as the SESSION 126 voice-capture Upload spec).

### Out of scope for SESSION 130

- Wizard Step 3 body (slice 8) — Voice capture.
- Wizard Step 4 body (slice 9) — Confirm + submit + atomic
  create-spokesperson orchestration.
- Template content (slice 10).
- Hide-on-completion full rework (slice 11).
- Flipping the wizard to be the default (lands with slice 9).

---

## Queued investigations (priority-ordered)

1. **Wizard slice 7 — Step 2 (Portrait) body** (SESSION 130).
   Includes the deferred-from-SESSION-127 visual_subject →
   /internal/portrait/ → /internal/avatars/ orchestration.
2. **Wizard slice 8 — Step 3 (Voice) body.**
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
14. **Allauth signup rate-limit override for tests** — SESSION 129
    hit the 20/m default on a full e2e sweep. Worth a tiny
    `ACCOUNT_RATE_LIMITS = {}` override gated on a test settings
    flag.
15. **Drift verifier** — `verify_doc_claims --only-drift`.
    Could cover both `SUPPORTED_VOICE_PRESETS` and
    `TONE_ARCHETYPES` mirrors.
16. **Brand Identity v2 + dark mode.**

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
pnpm e2e            # full lifecycle ~32s (17 specs). Note: allauth
                    # signup rate limits at 20/m per IP, so
                    # back-to-back runs may need a 60s wait.
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new?wizard=1
```

---

## AI / assistant context

- Last session: SESSION 129 — wizard slice 6 (Step 1 Identity
  body). Form + inline tone suggestion + tighter gate. Template
  tile picker deferred to slice 10 (operator-collaborative
  content).
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 130's recommendation
  (Step 2 / Portrait body) is the biggest remaining wizard slice
  because it brings together three prior foundations (camera,
  /internal/portrait/, visual_subject).
- **Watch:** the allauth signup rate-limit (20/m) bit during
  SESSION 129's first full e2e run. Queued #14 for a test-settings
  override; for now, back-to-back e2e runs may need a 60s wait.
- **Watch:** the `DebugState` blocks still live on Steps 2-4 — by
  design (visible progress signal). Slated for removal in slice 9.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
