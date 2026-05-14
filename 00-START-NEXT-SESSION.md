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
> **Last handoff:** `docs/handoffs/SESSION_128_WIZARD_SCAFFOLD.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-5. Slices 6-11 ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1    | Camera capture for `<PortraitUpload>`        | DONE (SESSION 124) |
| W2    | `POST /internal/portrait/` backend           | DONE (SESSION 125) |
| W3    | Voice tabs scaffold + clone-voice preset path | DONE (SESSION 126) |
| W3.5  | `visual_subject` field — "battle unicorn" etc | DONE (SESSION 127) |
| W4    | Tone archetype field + helper                | DONE (SESSION 127) |
| W5    | Wizard scaffold (4 steps, empty bodies)      | DONE (SESSION 128) |
| W6    | Wizard Step 1 — Identity body                | NEXT |
| W7    | Wizard Step 2 — Portrait body (incl. Generate) | Future |
| W8    | Wizard Step 3 — Voice body                   | Future |
| W9    | Wizard Step 4 — Confirm + submit             | Future |
| W10   | Template content (Riggs / Sasha / Donny / …) | Operator-collaborative |
| W11   | Hide-on-completion detail page rework        | Future (foundations landed in W3) |

What's working end-to-end after SESSION 128:

  - Everything from SESSIONS 107-127.
  - `/spokespeople/new?wizard=1` renders the 4-step wizard
    scaffold. Forward/back nav, state preservation, per-step
    `canAdvance` gating.
  - `/spokespeople/new` (no flag) still serves the legacy
    single-form — zero breakage for SESSIONS 121's create flow.
  - 15 of 15 Playwright specs pass (was 12 — slice added 3).
  - 46 of 46 pytest prompt tests.

---

## SESSION 129 — Wizard slice 6: Step 1 (Identity) body (recommended)

Session-sized (or half-session if you defer the template tiles).
Wire the real Identity step over the placeholder.

**Recommended scope:**

1. **Form fields** — replace the single name placeholder input
   with proper `react-hook-form` + `zod` integration. Three
   fields:
   - `name` (required, max 120 chars)
   - `business_brief` (required, 8-4000 chars — matches the
     legacy form's `createSchema`)
   - `tone_archetype` (select, 5 options — defaults to `expert`
     from the SESSION 127 model default)
2. **Inline tone suggestion** — when the brief crosses ~30
   chars, show a small under-the-textarea suggestion
   ("looks like a *tutor* brief — pick that?"). Two ways:
   - **A.** Add `GET /api/prompts/suggest-tone/?brief=...` —
     thin Django view wrapping `suggest_tone_from_brief()` from
     SESSION 127's `character_os/prompts/brand.py`.
   - **B.** Port `_BRIEF_TONE_HINTS` + `suggest_tone_from_brief`
     to TypeScript (zero-roundtrip; mirrors the SESSION 122
     palette-suggestion pattern if we did the same there).
   Pick A — keeps Python the source of truth and the helper API
   gets a thin documented endpoint along the way.
3. **Template tile picker** (optional this slice) — 4 named
   templates as clickable tiles at the top of Step 1. Clicking
   one pre-fills all 3 form fields from the template's defaults.
   The actual content (template names, briefs) is slice 10
   territory — for SESSION 129 just wire the *mechanism* and
   put placeholder content in. If tiles slip, defer them
   entirely to slice 10.
4. **Tighten `canAdvance`** in `spokesperson-wizard.tsx`:
   require name (>= 1 char) AND business_brief (>= 8 chars).
5. **Remove the `DebugState` block from Step 1** (keep on Steps
   2-4 until slices 7-9 land their real bodies).
6. **Playwright spec** — extend `wizard-shell.spec.ts` or add a
   new `wizard-step-1.spec.ts`. Type a name + a brief that
   should trigger a known tone suggestion (e.g. "high school
   history teacher" → tutor), assert the suggestion renders,
   click it, assert the select flips to `tutor`.

### Out of scope for SESSION 129

- Wizard Step 2 body (slice 7) — Portrait Upload/Camera/Generate.
- Wizard Step 3 body (slice 8) — Voice capture.
- Wizard Step 4 body (slice 9) — Confirm + submit.
- Template content (slice 10).
- Hide-on-completion full rework (slice 11).
- Flipping the wizard to be the default (slice 9 + 1, separate
  small commit).

---

## Queued investigations (priority-ordered)

1. **Wizard slice 6 — Step 1 (Identity) body** (SESSION 129).
2. **Wizard slice 7 — Step 2 (Portrait) body.** Includes the
   visual_subject → /internal/portrait/ → /internal/avatars/
   orchestration that SESSION 127 deferred.
3. **Wizard slice 8 — Step 3 (Voice) body.**
4. **Wizard slice 9 — Step 4 (Confirm + submit).** When this
   ships, also flip the default + retire the legacy form +
   remove the `DebugState` block from `<SpokespersonWizard>`.
5. **Wizard slice 10 — Template content** (operator-
   collaborative content work).
6. **Wizard slice 11 — Hide-on-completion full rework.**
7. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
8. **Stuck-row janitor** — operational hardening.
9. **Additional video kinds** — cinematic / dialogue / long_ad.
10. **Act-Two performance capture** — deferred until Runway
    credits land.
11. **`lesson` video kind** for James-shaped educators.
12. **Real Google OAuth + dj-stripe** — operator gates.
13. **Allauth legacy-settings cleanup.**
14. **smoke_voice / smoke_avatar transaction discipline** — tiny
    fix that's bitten us 3 times now.
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
pnpm e2e            # full lifecycle ~30s (15 specs)
```

To poke the wizard scaffold:

```
http://localhost:5174/spokespeople/new?wizard=1
```

---

## AI / assistant context

- Last session: SESSION 128 — wizard slice 5 (scaffold). 4-step
  shell with useReducer state, indicator pills, navigation, gating,
  placeholder bodies. Behind `?wizard=1`. Legacy form untouched.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. SESSION 129's recommendation (Step 1
  body) is the natural next step — fills the first wizard step
  against the stable scaffold + the SESSION 127 tone foundation.
- Templates (Riggs / Sasha / Donny / Maya) still need real content
  work — operator-collaborative pass, queued at slice 10.
- **Watch:** the smoke_voice / smoke_avatar transaction discipline
  issue queued #14 didn't bite SESSION 128 (no Django row changes
  this slice). Worth landing soon.
- **Watch:** the `DebugState` blocks inside each wizard step show
  live state JSON. Useful while building slices 6-9; slated for
  removal in slice 9.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
