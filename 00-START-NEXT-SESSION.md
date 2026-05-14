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
> **Last handoff:** `docs/handoffs/SESSION_132_WIZARD_STEP_4.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slices 1-9. Slices 10-11 + legacy retirement
ahead.

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
| W10   | Template content (Riggs / Sasha / Donny / …) | NEXT (operator-collaborative) |
| W11   | Hide-on-completion detail page rework        | Future |
| W12   | Retire legacy single-form                    | After Runway real-mode validation |

**The wizard ships.** What's working end-to-end after SESSION 132:

  - Everything from SESSIONS 107-131.
  - `/spokespeople/new` serves the 4-step wizard by default.
  - Full happy-path: Sign up → dashboard → wizard → Step 1
    (identity + tone) → Step 2 (portrait: upload/camera/generate)
    → Step 3 (voice: preset/upload/record + skip) → Step 4
    (review + create) → POST /api/spokespeople/ + optional
    POST /clone-voice/ → detail page with everything bound.
  - Tier-limit 402 surfaces as an upgrade callout.
  - Inline error renderer for general create failures.
  - Legacy single-form at `/spokespeople/new?legacy=1` as an
    escape hatch until real-mode validation.
  - 25 of 25 Playwright specs pass.

---

## SESSION 133 — Three parallel-safe options

### Option A — Wizard slice 10: Template content (recommended)

**Operator-collaborative.** Design 3-4 named template
spokespeople with real content, then wire the tile picker on
Step 1.

The mechanism is small. The content is the hard part:

| Template | Visual archetype | Tone archetype | Brief (TBD) | Audience |
|----------|------------------|----------------|-------------|----------|
| **Riggs** | `mascot` | `friend` | TBD | Casual-friendly SMBs |
| **Sasha** | `founder` | `authority` | TBD | Premium / authoritative brands |
| **Donny** | `local_guide` | `expert` | TBD | Local businesses |
| **Maya** | `mascot` | `tutor` | TBD | Educators (James's use case) |

**Recommended scope:**

1. **`character_os/templates/spokesperson_templates.py`** — new
   module. Static dict of templates with `name / business_brief /
   tone_archetype / visual_subject / visual_template /
   voice_preset` per entry.
2. **`GET /api/spokespeople/templates/`** — thin DRF action
   returning the list. Same shape as `voice-presets/`.
3. **`useSpokespersonTemplates()`** SPA hook + zod schema.
4. **Tile picker on Step 1** — 4 clickable tiles at the top.
   Clicking dispatches `SET_IDENTITY` with the template's content.
   "Start from scratch" stays as an alternative.
5. **Playwright spec** — `wizard-templates.spec.ts`. Click a tile,
   advance to Step 2, confirm Step 1's fields are pre-filled.

This is operator-led on content + AI-led on mechanism. Ideal
session shape.

### Option B — Wizard slice 11: Hide-on-completion detail page

Half-to-full session. The detail page's setup-checklist becomes
the explicit "either / or" surface:

- Fully configured: clean identity panel + render history + small
  "Edit" affordance (modal with wizard fields).
- Partially configured: focused setup callouts for *just* the
  skipped items.

### Option C — Retire the legacy form

**Defer to after real-mode validation.** Delete `LegacyCreateForm`,
drop the `?legacy=1` gate, delete `create-spokesperson.spec.ts` +
`portrait-camera.spec.ts` + the legacy parts of `make-video.spec.ts`.

Don't do this until the wizard's been exercised with real Runway
calls — mock-mode is too forgiving.

### Recommendation: **A**.

Templates are the highest-leverage operator-collaborative work
left. They unblock the "I want to start with a known shape, not a
blank wizard" UX for new operators. B + C can come after.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 10 — Template content** (SESSION 133;
   operator-collaborative).
2. **Wizard slice 11 — Hide-on-completion full rework.**
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
    fix that's bitten us 3+ times now.
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
pnpm e2e            # full lifecycle ~42s (25 specs), single-shot
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new
```

It's the default now. End-to-end create flow works against
mock-mode (no Runway credits needed). Try a tutor-shaped brief
("high school history teacher building lesson plans") + the
mascot template + "armored battle unicorn warrior" subject to
see James's full use case land.

Legacy form available at `/spokespeople/new?legacy=1` as an
escape hatch.

---

## AI / assistant context

- Last session: SESSION 132 — wizard slice 9 (Confirm + submit
  + wizard-as-default flip). The 4-step create flow that's been
  the central thread of W1-W9 is now end-to-end. Real review
  panel + atomic submit orchestration + tier-limit handling +
  inline errors + legacy form behind `?legacy=1`.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. The 9 wizard slices (W1-W9) were a
  long arc; **the wizard ships**. SESSION 133's recommendation
  (templates) is the natural next step — content work that
  unblocks "I want a known-shape spokesperson" UX.
- Templates (Riggs / Sasha / Donny / Maya) need real
  operator-collaborative content design. The slice mechanism is
  small; the content is the hard part.
- **Don't retire the legacy form yet.** Wait for real-mode Runway
  validation. Mock-mode passes everything; real Runway calls
  surface subtle failures that the wizard hasn't been pressure-
  tested against.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
