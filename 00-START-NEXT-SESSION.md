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
> **Last handoff:** `docs/handoffs/SESSION_135_TEMPLATE_CONTENT.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11) + content refined for
the Character OS marketing cast. Ready for real-mode validation,
Tier 2 prompt helpers, or render-flow polish.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Content | Cast refinement (Riggs/Sasha/Donny/Maya as Character OS animals) | DONE (SESSION 135) |
| W12   | Retire legacy single-form                    | After real-mode Runway validation |
| W11.1 | Edit-spokesperson modal                      | Queued |

**The four animals are now Character OS's first employees:**

  - **Riggs** the Donkey — founder voice ("why we built this")
  - **Sasha** the Raccoon — sales / hook videos for socials
  - **Donny** the Sloth — user stories / documentary interviews
  - **Maya** the Panda — product education + onboarding tutor
    (dual-mode: lessons + Q&A; the latter foreshadows surfacing
    the `ConversationThread` data model in a future slice)

James's classroom battle unicorn is *not* a template — it's the
demo of an operator using Character OS to build a fully-custom
spokesperson.

---

## SESSION 136 — Five options

The wizard arc + content polish are done. No single dominant
next slice — pick by priority:

### Option A — First real marketing video (recommended)

**Highest-information next step.** Use one of the cast members
(Sasha probably — sales is the natural launch shape) against
real Runway, end-to-end through the wizard + render flow. This
is the *real-mode validation* the legacy-form retirement
(W12) is waiting on.

Requires real Runway credits + likely some real-mode tuning of
the existing `/internal/*` pipeline. Outputs a real video asset
Chris can actually post somewhere.

### Option B — Voice preset audit

**Quarter-session.** Listen to vincent / clara / drew / victoria
against each character's personality. Swap any that don't fit.
The current assignments are name-fit intuition, not actual
hearing — the wrong voice on a character is uniquely jarring
because audio is unforgiving.

### Option C — Tier 2 prompt helpers (DynamicPromptBuilder)

**Full session.** Larger port from unified-donkey-betz. Tier 1
(sharpening + brand palettes + creative principles + tone
heuristic) ported in SESSION 122. Tier 2 is the composer that
takes a structured spec and emits a rendered prompt — useful
when render-flow scripts grow beyond the current minimal
brief→prompt path.

### Option D — Edit-spokesperson modal (W11.1)

**Half-session.** PATCH-shaped modal launched from the detail
page masthead. The DRF viewset already supports PATCH — UI-only
slice.

### Option E — Surface the conversational tutor mode

**Session+.** Maya's brief now mentions "answers the question
when the student is stuck" — a dual-mode that needs UI to
exist. The `ConversationThread` model has been scaffolded since
Phase 1 with no UI. This unlocks a *second product surface*
beyond video rendering (the chat-with-your-spokesperson
surface). Bigger arc than the others.

### Recommendation: **A** → **B** → **C** in that order.

Reasoning: A forces real-mode learnings the rest of the queue
benefits from. B follows naturally once you've heard the cast.
C is the next big arc with cleaner foundations afterward.

D + E are queued; both more discretionary.

---

## Queued investigations (priority-ordered)

1. **First real marketing video** — Sasha or Riggs against
   real Runway, end-to-end.
2. **Voice preset audit** — verify vincent/clara/drew/victoria
   against the new character personalities.
3. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
4. **W11.1 — Edit-spokesperson modal.**
5. **Surface the conversational tutor mode** — Maya's dual-mode
   brief implies a chat surface; `ConversationThread` model is
   ready.
6. **W12 — Legacy form retirement** — after real-mode validation.
7. **Stuck-row janitor** — operational hardening.
8. **Additional video kinds** — cinematic / dialogue / long_ad.
9. **Act-Two performance capture** — deferred until Runway
   credits land.
10. **`lesson` video kind** for James-shaped educators (pairs
    with the conversational tutor surface).
11. **Real Google OAuth + dj-stripe** — operator gates.
12. **Allauth legacy-settings cleanup** (deprecation warnings).
13. **smoke_voice / smoke_avatar transaction discipline** —
    tiny fix that's bitten 3+ times.
14. **Drift verifier** — `verify_doc_claims --only-drift`.
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
celery -A character_os worker --loglevel=info --pool=solo

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
pnpm e2e            # full lifecycle ~46s (30 specs), single-shot
```

To poke the wizard:

```
http://localhost:5174/spokespeople/new
```

Try **Riggs** (the donkey) — that's the founder voice video
you'd post about why Character OS exists. Or **Maya** (the
panda) for an onboarding "how do I make my first spokesperson"
tutorial video.

---

## AI / assistant context

- Last session: SESSION 135 — template content refinement.
  Reframed the four templates from generic archetypes into
  **Character OS's in-house marketing cast** (anthropomorphic
  animal characters in hoodies + tees). Riggs/Donkey =
  founder voice; Sasha/Raccoon = sales; Donny/Sloth = user
  stories; Maya/Panda = education + tutor.
- **Real-mode validation is the next big unlock.** Mock-mode
  has carried the wizard arc; real Runway calls surface failure
  modes that mock-mode can't.
- **Voice presets are unverified by ear.** Don't trust
  vincent/clara/drew/victoria as final until they've been
  heard against the new character personalities.
- **Maya's brief foreshadows a conversational tutor surface.**
  The `ConversationThread` model is ready; the UI doesn't
  exist. Queued as option E for future arc planning.
- **The templates are now load-bearing content, not starter
  material.** Future edits to
  `shell/character_os/templates/spokesperson_templates.py` are
  product-positioning changes; treat with the same care as
  website tagline edits.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
