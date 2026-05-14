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
> **Last handoff:** `docs/handoffs/SESSION_126_VOICE_TABS_SCAFFOLD.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-3. Wizard slices 4-11 ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1    | Camera capture for `<PortraitUpload>`        | DONE (SESSION 124) |
| W2    | `POST /internal/portrait/` backend           | DONE (SESSION 125) |
| W3    | Voice tabs scaffold + clone-voice preset path | DONE (SESSION 126) |
| W4    | Tone archetype field + helper                | NEXT |
| W5    | Wizard scaffold (4 steps, empty shells)      | (parallel-safe with W4) |
| W6-9  | Wizard steps 1-4 individually                | Future |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future (foundations landed in W3) |

What's working end-to-end after SESSION 126:

  - Everything from SESSIONS 107-125.
  - `POST /api/spokespeople/{id}/clone-voice/` accepts either
    `{preset}` or `{audio_data_uri}` — preset wins if both.
  - `GET /api/spokespeople/voice-presets/` — alpha-sorted list of
    the 30 supported Runway voice presets.
  - `<VoiceCapture>` component with three tabs (Preset / Upload /
    Record) wired into the spokesperson detail page's setup
    checklist. Hides on completion (voice_id set → ✓).
  - Portrait camera capture: now flake-free across 3 consecutive
    runs (waits for `loadeddata` before flipping to live).
  - 12 of 12 Playwright specs pass (was 10/10 — slice added two).

---

## SESSION 127 — Three parallel-safe options

### Option A — Wizard slice 4: Tone archetype field (recommended start)

Half-session. Pure backend + zod schema.

1. **`Spokesperson.tone_archetype` CharField** with 5 choices
   (`tutor / authority / friend / expert / performer`).
   Migration. Default: `expert`.
2. **`suggest_tone_from_brief(brief: str) -> str`** in
   `character_os/prompts/brand.py` (mirrors
   `suggest_palette_from_brief` shape). Pytest cases per
   archetype.
3. Surface in `SpokespersonSerializer` (read + write).
4. Surface in zod schemas on the SPA (`spokesperson.ts`).
5. No UI changes yet — Wizard Step 1 picks this up when slice 6
   lands.

### Option B — Wizard slice 5: Wizard scaffold

Session-sized. Build the 4-step wizard shell now, fill in steps
later.

1. **`web/src/components/spokesperson-wizard.tsx`** — `<Wizard>`
   container + `<WizardStep>` slots + step navigation
   (`onNext`, `onPrev`, `canAdvance` per step).
2. **`web/src/routes/spokespeople/new.tsx`** — switch from the
   current single-form to the wizard. Steps:
   - 1. Identity (name + brief + tone)
   - 2. Portrait (`<PortraitUpload>` already exists)
   - 3. Voice (`<VoiceCapture>` already exists)
   - 4. Confirm + create
3. **State shape** — `useReducer` for wizard state (each step
   commits to a slice of the create-spokesperson payload).
4. **Existing flow stays working** — gate the wizard behind a
   feature flag or query param if needed, so SESSION 121's existing
   create-spokesperson specs don't break mid-slice.
5. **Playwright spec** — `e2e/wizard-shell.spec.ts`. Step
   navigation + back-button preserves state.

### Option C — Pair both (A → B in one session)

Plausible: slice 4 is half-session, slice 5 is session-sized. If
A lands quickly, B is the natural next step (the wizard scaffold
will need the tone archetype field surfaced anyway).

### Recommendation: **A → B**.

Reasoning: A is the smaller foundation piece; landing it first means
the wizard's Step 1 has a real field to bind to when slice 6 lands.
B then has a stable shape to build against. Both ship in one session
if the operator wants it; split across two sessions otherwise.

### Out of scope for SESSION 127

- Wizard steps 1-4 individually (slices 6-9).
- Template content (slice 10).
- Hide-on-completion full rework (foundations already landed in W3).
- Act-Two performance capture.
- Real Runway calls / credentials.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 4 — Tone archetype field** (SESSION 127 part 1).
2. **Wizard slice 5 — Wizard scaffold** (SESSION 127 part 2).
3. **Wizard slices 6-9 — wizard steps individually.**
4. **Wizard slice 10 — Template content** (Riggs / Sasha /
   Donny / Maya; operator-collaborative content work).
5. **Wizard slice 11 — Hide-on-completion full rework.**
6. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
7. **Stuck-row janitor** — operational hardening.
8. **Additional video kinds** — cinematic / dialogue / long_ad.
9. **Act-Two performance capture** — deferred until Runway
   credits land.
10. **`lesson` video kind** for James-shaped educators.
11. **Real Google OAuth + dj-stripe** — operator gates.
12. **Allauth legacy-settings cleanup.**
13. **smoke_voice / smoke_avatar transaction discipline** —
    tiny fix that's bitten us 3 times now (did not bite SESSION 126,
    but conditions for recurrence still present).
14. **Drift verifier** — `verify_doc_claims --only-drift`. Could
    cover the new `SUPPORTED_VOICE_PRESETS` mirror between Django
    and the media-engine.
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
python -m pytest character_os/prompts/        # 31 tests

# SPA (from web/)
pnpm test
pnpm e2e            # full lifecycle ~26s (12 specs)
```

---

## AI / assistant context

- Last session: SESSION 126 — wizard slice 3 (voice tabs scaffold).
  Three-mode `<VoiceCapture>` component + clone-voice preset path
  on the backend + 2 new Playwright specs. Camera capture flake
  fix landed as a side-quest (wait for `loadeddata` before live).
  All gates clean; 12/12 specs.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 127's recommendation (slice 4
  → slice 5) keeps that shape — small foundation field first, then
  the wizard scaffold structure.
- Templates (Riggs / Sasha / Donny / Maya) still need real content
  work — operator-collaborative pass, queued at slice 10.
- **Watch:** the smoke_voice / smoke_avatar transaction discipline
  issue didn't bite SESSION 126 but it's queued #13. Worth landing
  the fix soon (it's tiny).
- **Watch:** if Django runserver gets started with `--noreload`,
  view changes won't be picked up. The local-dev section above
  notes this; the canonical command is `runserver` without flags.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
