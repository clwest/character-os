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
> **Last handoff:** `docs/handoffs/SESSION_133_TEMPLATE_TILES.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-10. Slice 11 ahead + legacy retirement
later.

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
| W9    | Wizard Step 4 — Confirm + submit + flip      | DONE (SESSION 132) |
| W10   | Template tiles (Riggs / Sasha / Donny / Maya) | DONE (SESSION 133) |
| W11   | Hide-on-completion detail page rework        | NEXT |
| W12   | Retire legacy single-form                    | After Runway real-mode validation |

What's working end-to-end after SESSION 133:

  - Everything from SESSIONS 107-132.
  - 4-tile template picker on Step 1 (Riggs / Sasha / Donny / Maya).
    Click a tile → name + brief + tone + visual_subject +
    visual_template + voice_preset all pre-fill in one shot.
  - "Start from scratch" link clears the identity fields.
  - Template content is starter material — operator can rewrite the
    strings in `shell/character_os/templates/spokesperson_templates.py`
    without touching any spec or wiring.
  - 28 of 28 Playwright specs pass.

---

## SESSION 134 — Wizard slice 11: Hide-on-completion (recommended)

Half-to-full session. Reshapes the spokesperson detail page's
setup checklist into the explicit "either / or" surface promised
by the scope-lock.

**Recommended scope:**

1. **Two-state detail page** —
   - **Fully configured** (avatar bound + voice set): clean
     identity panel + render history + a small "Edit" affordance
     that surfaces a modal with wizard fields for in-place changes.
     No setup checklist visible at all.
   - **Partially configured**: setup callouts for *just* the items
     that aren't done. The SESSION 126 voice-clone affordance is
     already this shape — generalize to avatar + (future)
     Act-Two + (future) tone-update.
2. **`buildSetupItems` extension** in
   `web/src/routes/spokespeople/$id.tsx` — current items are
   `brief / avatar / voice`. Add a "ready to render" affirmation
   when all three are done; that state replaces the checklist
   with a single celebratory affordance.
3. **Edit modal** (optional this slice) — clicking "Edit" on a
   fully configured spokesperson opens a modal with wizard
   fields. Saves via PATCH `/api/spokespeople/{id}/`. If this
   slips, defer to a follow-up; the partially-configured surface
   is the priority.
4. **Playwright spec** — `web/e2e/detail-hide-on-completion.spec.ts`.
   Sign up + create a fully-configured spokesperson via the wizard
   → assert detail page shows the "ready" affordance + no
   checklist. Then create a partially-configured one → assert
   checklist appears with only the unfinished rows.

### Out of scope for SESSION 134

- Template content refinement (operator-collaborative — separate
  pass).
- Legacy form retirement (waits for real-mode validation).
- Tier 2 prompt helpers (`DynamicPromptBuilder`).
- Real Runway calls / credentials.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 11 — Hide-on-completion detail page rework**
   (SESSION 134).
2. **Template content refinement** — operator-collaborative pass
   on `shell/character_os/templates/spokesperson_templates.py`.
   Briefs are starter material; benefits from operator's voice.
3. **Legacy form retirement** — after real-mode validation.
4. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
5. **Stuck-row janitor** — operational hardening.
6. **Additional video kinds** — cinematic / dialogue / long_ad.
7. **Act-Two performance capture** — deferred until Runway
   credits land.
8. **`lesson` video kind** for James-shaped educators.
9. **Real Google OAuth + dj-stripe** — operator gates.
10. **Allauth legacy-settings cleanup** (deprecation warnings on
    every Django manage command).
11. **smoke_voice / smoke_avatar transaction discipline** — tiny
    fix that's bitten us 3+ times.
12. **Drift verifier** — `verify_doc_claims --only-drift`. Could
    cover the `SUPPORTED_VOICE_PRESETS`,
    `SUPPORTED_PORTRAIT_TEMPLATES`, and `TONE_ARCHETYPES` mirrors
    in one pass.
13. **Brand Identity v2 + dark mode.**

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
pnpm e2e            # full lifecycle ~45s (28 specs), single-shot
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new
```

Click **Maya** to see James's tutor-shaped use case fully pre-filled.

---

## AI / assistant context

- Last session: SESSION 133 — wizard slice 10 (template tiles).
  4-tile picker on Step 1 + new
  `character_os.templates.spokesperson_templates` module +
  endpoint + reducer extension to remember `visual_template`
  across steps.
- **Template content is starter material.** The mechanism is the
  deliverable; the four briefs are first drafts. Future sessions
  can rewrite *only the constants* in
  `shell/character_os/templates/spokesperson_templates.py`
  without touching the spec suite (the tests check structure, not
  exact strings — except for proper-noun matches like template
  names and the `victoria` voice_preset).
- **Calibration carried forward:** the wizard arc is essentially
  complete. W11 (hide-on-completion) is polish; W12 (legacy
  retirement) waits for real-mode validation. After SESSION 134,
  the next big arc is render-flow polish or real-Runway exercise.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
