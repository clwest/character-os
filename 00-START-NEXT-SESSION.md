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
> **Last handoff:** `docs/handoffs/SESSION_134_HIDE_ON_COMPLETION.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
arc complete (W1-W11). Legacy form retirement + content polish +
new feature arcs ahead.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W9 | Create-spokesperson wizard end-to-end        | DONE (SESSIONS 124-132) |
| W10   | Template tiles (Riggs / Sasha / Donny / Maya) | DONE (SESSION 133) |
| W11   | Hide-on-completion detail page rework        | DONE (SESSION 134) |
| W12   | Retire legacy single-form                    | After Runway real-mode validation |
| W11.1 | Edit-spokesperson modal                      | Queued (deferred from W11) |

**The wizard arc is complete.** What's working end-to-end after
SESSION 134:

  - Everything from SESSIONS 107-133.
  - Detail page hides the setup checklist when fully configured
    (brief + avatar bound + voice set); shows only the unfinished
    items otherwise.
  - "Ready to render" badge in the masthead signals fully-configured.
  - Done items disappear from the checklist (not struck-through).
  - Videos panel takes full width on fully-configured detail pages.
  - 30 of 30 Playwright specs pass in one shot.

---

## SESSION 135 — Four options

The wizard arc is finished. No single dominant "next slice" —
pick by priority:

### Option A — Template content refinement (operator-collaborative)

**Quarter-session of operator time.** The four briefs in
`shell/character_os/templates/spokesperson_templates.py` are first
drafts. An hour of operator voice would replace them with the real
thing. No code changes; no spec changes (specs check structure +
proper-noun matches, not exact strings).

### Option B — Edit-spokesperson modal (W11.1)

**Half-to-full session.** Adds an "Edit" button on the detail
page masthead → modal with name + brief + tone + visual_subject
fields → PATCH `/api/spokespeople/{id}/`. The DRF viewset already
supports PATCH (`ModelViewSet`), so this is UI-only.

Out of scope for this slice: portrait re-generation, voice
re-clone (both have existing affordances).

### Option C — Legacy form retirement (W12)

**Half-session, but defer until real-mode Runway validation.**
The legacy `?legacy=1` single-form is the cheapest insurance
against wizard-introduced bugs. Don't retire until the wizard
has been exercised against real Runway calls.

When ready: delete `LegacyCreateForm`, drop the `?legacy=1` gate,
rewrite/delete `create-spokesperson.spec.ts` +
`portrait-camera.spec.ts` + the legacy parts of
`make-video.spec.ts`.

### Option D — Tier 2 prompt helpers (DynamicPromptBuilder)

**Full session at minimum.** Larger port from u-d-b. Tier 1 ported
in SESSION 122 (sharpening + brand palettes + creative principles +
tone heuristic). Tier 2 is the prompt composer that takes a
structured spec and emits a rendered prompt — useful for richer
video script composition when the make-video flow grows beyond
the current minimal brief→prompt path.

### Recommendation: **A** (content refinement, quick win), then
**D** (Tier 2 helpers, next big arc) once content is dialed.

Reasoning: the wizard is operational; the lowest-hanging fruit
left is template voice. **D** is the natural next big arc —
unblocks richer scripts which is where the operator's product
voice will start showing on every render. **B** + **C** are
queued but not blocking anything.

---

## Queued investigations (priority-ordered)

1. **Template content refinement** — operator-collaborative pass
   on `shell/character_os/templates/spokesperson_templates.py`.
2. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
3. **W11.1 — Edit-spokesperson modal.**
4. **W12 — Legacy form retirement** — after real-mode Runway
   validation.
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
12. **Drift verifier** — `verify_doc_claims --only-drift`. Covers
    `SUPPORTED_VOICE_PRESETS`, `SUPPORTED_PORTRAIT_TEMPLATES`,
    and `TONE_ARCHETYPES` mirrors in one pass.
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
pnpm e2e            # full lifecycle ~47s (30 specs), single-shot
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new
```

The wizard ships end-to-end. Click **Maya** to see the tutor /
educator use case fully pre-filled. After submit, the detail
page shows the "Ready to render" badge + no setup checklist —
just the identity panel + the (empty) render history.

---

## AI / assistant context

- Last session: SESSION 134 — wizard slice 11 (hide-on-completion).
  Detail page now branches by completion: fully-configured rows
  hide the checklist + show a Ready badge; partial rows show only
  the unfinished items. **The wizard arc (W1-W11) is complete.**
- **Calibration carried forward:** the wizard arc spanned 11 slices
  (W1-W11) across SESSIONS 124-134. Pattern that worked: scope-
  lock-first → foundation slices → scaffold-before-bodies →
  one-slice-at-a-time commits. No big-bang rewrites; every gate
  run green at slice close. The pattern is the calibration — keep
  it for the next big arc (likely Tier 2 prompt helpers).
- **Template content** is the cheapest remaining work item.
  Operator-collaborative pass on
  `shell/character_os/templates/spokesperson_templates.py`. Quick
  win that benefits every new-operator first-impression.
- **Don't retire the legacy form yet.** Wait for real-mode Runway
  validation.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
