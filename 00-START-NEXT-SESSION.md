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
> **Last handoff:** `docs/handoffs/SESSION_131_WIZARD_STEP_3.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-8. Slices 9-11 ahead.

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
| W8    | Wizard Step 3 — Voice body                   | DONE (SESSION 131) |
| W9    | Wizard Step 4 — Confirm + submit             | NEXT |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future (foundations landed in W3) |

What's working end-to-end after SESSION 131:

  - Everything from SESSIONS 107-130.
  - Wizard Step 3 — three-mode Voice input (Preset / Upload /
    Record) wired through the reducer + a "Skip" affordance that
    pre-fills the default Runway preset (`vincent`) and advances.
  - Allauth rate limits disabled in DEBUG — closes queued #14;
    full e2e suite runs in one shot, no 60s waits.
  - 22 of 22 Playwright specs pass (was 19 — slice added 3).
  - 46 of 46 pytest prompt tests.

---

## SESSION 132 — Wizard slice 9: Step 4 (Confirm + submit) (recommended)

Session-sized — the biggest remaining wizard slice. Wires the
atomic create + flips the wizard to be the default route.

**Recommended scope:**

1. **Replace Step 4's stub** with a real review panel:
   - Portrait thumbnail (from `state.portrait.dataUri`)
   - Identity summary (name + brief + tone + visual_subject)
   - Voice summary (mode + preset name or clip file/duration)
2. **Wire `useCreateSpokesperson()`** — assemble payload from
   `state.identity` + `state.portrait`. Fire create.
3. **Voice clone follow-up** — if `state.voice.mode === "upload"`
   or `"record"`, after create succeeds, fire `useCloneVoice` with
   the data URI. Preset mode is handled by passing `voice_preset`
   on the original create call (SESSION 116 backend behavior).
4. **Error handling** — inline errors per failed call. The row
   creates regardless; SESSION 126's hide-on-completion checklist
   on the detail page catches anything partial.
5. **`canAdvance(step=4)`** → enable when all upstream gates passed
   (today returns `false` because the submit isn't wired).
6. **Flip the default** — drop the `?wizard=1` gate in
   `web/src/routes/spokespeople/new.tsx`. Move the legacy form
   behind `?legacy=1` for an escape hatch (one-session retirement
   plan).
7. **Update e2e specs** — `create-spokesperson.spec.ts` currently
   drives the legacy form's `data-testid="create-submit"`. Either
   move it to drive the wizard or gate it on `?legacy=1`. Decide
   based on how the diff feels.
8. **Remove all remaining `DebugState` blocks** — Step 4's was the
   last one left.
9. **Playwright spec** — `wizard-step-4.spec.ts`. Happy path:
   fill all 4 steps, click Submit, assert navigation to
   `/spokespeople/{id}` with all fields persisted.

### Out of scope for SESSION 132

- Template content (slice 10) — operator-collaborative.
- Hide-on-completion full rework (slice 11).
- Tone-to-voice auto-mapping (a different content/design concern).
- Real Runway calls / credentials.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 9 — Step 4 (Confirm + submit) + wizard-default
   flip** (SESSION 132).
2. **Wizard slice 10 — Template content** (operator-collaborative;
   the slice-6 deferred tile picker lands here).
3. **Wizard slice 11 — Hide-on-completion full rework.**
4. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
5. **Stuck-row janitor** — operational hardening.
6. **Additional video kinds** — cinematic / dialogue / long_ad.
7. **Act-Two performance capture** — deferred until Runway
   credits land.
8. **`lesson` video kind** for James-shaped educators.
9. **Real Google OAuth + dj-stripe** — operator gates.
10. **Allauth legacy-settings cleanup** (the deprecation warnings
    on every Django manage command).
11. **smoke_voice / smoke_avatar transaction discipline** — tiny
    fix that's bitten us 3 times now.
12. **Drift verifier** — `verify_doc_claims --only-drift`. Could
    cover the `SUPPORTED_VOICE_PRESETS`, `SUPPORTED_PORTRAIT_TEMPLATES`,
    and `TONE_ARCHETYPES` mirrors in one pass.
13. **Brand Identity v2 + dark mode.**

(Queued #14 — allauth rate-limit override for tests — closed in
SESSION 131.)

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
pnpm e2e            # full lifecycle ~38s (22 specs), single-shot
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new?wizard=1
```

All 4 steps now navigate. Step 4 is still a stub — SESSION 132 wires
the submit.

---

## AI / assistant context

- Last session: SESSION 131 — wizard slice 8 (Step 3 Voice body).
  Embedded `<VoiceCapture>` (SESSION 126) with a Skip affordance.
  Also closed queued #14 by disabling allauth rate limits in
  DEBUG.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 132's recommendation
  (Step 4 / Confirm + submit + wizard flip) is the *culminating*
  wizard slice — every prior slice's foundation pays off here.
- Templates (Riggs / Sasha / Donny / Maya) still need real content
  work — operator-collaborative pass, queued at slice 10.
- **Watch:** the `DebugState` block on Step 4 is the only one
  left. Slated for removal in slice 9 alongside the
  wizard-as-default flip.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
