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
> **Last handoff:** `docs/handoffs/SESSION_127_FOUNDATION_FIELDS.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1, 2, 3, 3.5, and 4. Slices 5-11 ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1    | Camera capture for `<PortraitUpload>`        | DONE (SESSION 124) |
| W2    | `POST /internal/portrait/` backend           | DONE (SESSION 125) |
| W3    | Voice tabs scaffold + clone-voice preset path | DONE (SESSION 126) |
| W3.5  | `visual_subject` field — "battle unicorn" etc | DONE (SESSION 127) |
| W4    | Tone archetype field + helper                | DONE (SESSION 127) |
| W5    | Wizard scaffold (4 steps, empty shells)      | NEXT |
| W6-9  | Wizard steps 1-4 individually                | Future |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future (foundations landed in W3) |

What's working end-to-end after SESSION 127:

  - Everything from SESSIONS 107-126.
  - `Spokesperson.visual_subject` field — free-text "what they look
    like" — persists, surfaces on the detail page MetadataGrid.
  - `Spokesperson.tone_archetype` field — 5 archetype choices,
    default `expert`. Visible in MetadataGrid.
  - `suggest_tone_from_brief()` keyword helper — pairs with the
    SESSION 122 `suggest_palette_from_brief()`.
  - SPA zod surface for both fields + `TONE_ARCHETYPES` const.
  - 46 of 46 pytest prompt tests (was 31 — slice added 15).
  - 12 of 12 Playwright specs pass (unchanged).

---

## SESSION 128 — Wizard slice 5: Wizard scaffold (recommended)

Session-sized. Build the 4-step wizard shell that replaces the
current single-form `/spokespeople/new`. Empty step bodies — the
follow-up slices (6-9) fill each one in.

**Recommended scope:**

1. **`web/src/components/spokesperson-wizard.tsx`** — new component.
   - `<Wizard>` container + numbered step indicator
   - `<WizardStep>` slot for each step body
   - Navigation: `onNext`, `onPrev`, `canAdvance` per step
   - Persisted state shape via `useReducer` (one action per
     step's commit; each step writes a slice of the
     create-spokesperson payload)
2. **`web/src/routes/spokespeople/new.tsx`** — switch to the wizard.
   Steps:
   - **1. Identity** — name + brief + tone_archetype (binds to the
     SESSION 127 field; uses `suggest_tone_from_brief` for an
     inline suggestion if we expose it via a tiny endpoint).
   - **2. Portrait** — Upload / Camera / Generate (Generate path
     uses the SESSION 125 `/internal/portrait/` + the new
     `visual_subject` field).
   - **3. Voice** — `<VoiceCapture>` (SESSION 126 already shipped).
   - **4. Confirm** — review + submit. Fires the
     `POST /api/spokespeople/` + (if needed)
     `POST /clone-voice/` orchestration on submit.
3. **Keep the existing form working** — gate the wizard behind a
   feature flag (`?wizard=1`) OR ship the wizard as the default with
   the existing e2e specs updated to drive it. Pick whichever feels
   cleaner once you see the diff.
4. **Playwright spec** — `e2e/wizard-shell.spec.ts`. Navigate
   forward through all 4 steps, navigate backward, confirm state is
   preserved across navigation.

**Out of scope for SESSION 128:**

- Real step bodies for steps 1-4 (slices 6-9).
- Template content (slice 10).
- Hide-on-completion full rework (slice 11).
- Act-Two performance capture.
- Real Runway calls / credentials.

### Alternate: small queued items

If you'd rather not start the wizard scaffold in the same session,
consider:

- **smoke_voice / smoke_avatar transaction discipline** (tiny,
  queued #14). Did not bite SESSION 127 but conditions for
  recurrence remain.
- **Drift verifier** (queued #15). Could cover the new
  `TONE_ARCHETYPES` mirror (Django ↔ SPA) + the
  `SUPPORTED_VOICE_PRESETS` mirror.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 5 — Wizard scaffold** (SESSION 128).
2. **Wizard slices 6-9 — wizard steps individually.** Slice 7
   (Portrait step) takes the regenerate-portrait orchestration —
   the two-step (`/internal/portrait/` → `/internal/avatars/`)
   that SESSION 127 deferred.
3. **Wizard slice 10 — Template content** (Riggs / Sasha /
   Donny / Maya; operator-collaborative content work).
4. **Wizard slice 11 — Hide-on-completion full rework.**
5. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
6. **Stuck-row janitor** — operational hardening.
7. **Additional video kinds** — cinematic / dialogue / long_ad.
8. **Act-Two performance capture** — deferred until Runway
   credits land.
9. **`lesson` video kind** for James-shaped educators.
10. **Real Google OAuth + dj-stripe** — operator gates.
11. **Allauth legacy-settings cleanup.**
12. **smoke_voice / smoke_avatar transaction discipline** —
    tiny fix that's bitten us 3 times now.
13. **Drift verifier** — `verify_doc_claims --only-drift`. Could
    cover both the `SUPPORTED_VOICE_PRESETS` (Django ↔ media-engine)
    and `TONE_ARCHETYPES` (Django ↔ SPA) mirrors.
14. **Brand Identity v2 + dark mode.**

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
pnpm e2e            # full lifecycle ~27s (12 specs)
```

---

## AI / assistant context

- Last session: SESSION 127 — wizard slices 3.5 + 4 bundled
  (foundation fields: `visual_subject` + `tone_archetype` +
  `suggest_tone_from_brief` helper + 15 new pytest cases). Both
  fields surfaced in the SPA detail-page MetadataGrid even though
  no creation UI writes them yet — small validation surface ahead
  of W6/W7.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 128's recommendation
  (wizard scaffold) is the structural next step — the wizard shell
  exists before any individual step lands. Slices 6-9 then fill
  each step against a stable scaffold.
- Templates (Riggs / Sasha / Donny / Maya) still need real content
  work — operator-collaborative pass, queued at slice 10.
- **Watch:** the smoke_voice / smoke_avatar transaction discipline
  issue queued #12 didn't bite SESSION 127, but conditions for
  recurrence remain. Worth landing soon (tiny fix).
- **Watch:** if Django runserver gets started with `--noreload`,
  view changes won't be picked up. The canonical command is
  `runserver` without flags.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
