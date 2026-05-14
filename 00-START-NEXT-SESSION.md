---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_124_PORTRAIT_CAMERA_CAPTURE.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices + User model + Prompt Tier 1 + Wizard
scope lock + Wizard slice 1 (camera). Wizard slices 2-11 ahead.

| Slice | Deliverable                          | Status |
|-------|--------------------------------------|--------|
| 1     | Sign-up + sign-in (S-03 + S-04)      | DONE (SESSION 116) |
| 2     | Workspace dashboard (S-09)           | DONE (SESSION 117) |
| 3     | Spokesperson detail (S-10)           | DONE (SESSION 118) |
| —     | Custom email-as-PK User model        | DONE (SESSION 119) |
| 4     | Create spokesperson (S-06)           | DONE (SESSION 120) |
| 5     | Make-a-video (S-12) + status (S-11)  | DONE (SESSION 121) |
| —     | Prompt helpers from u-d-b (Tier 1)   | DONE (SESSION 122) |
| —     | Wizard scope-lock doc                | DONE (SESSION 123) |
| W1    | Wizard slice 1 — camera capture      | DONE (SESSION 124) |
| W2-11 | Wizard slices 2-11                   | NEXT |

What's working end-to-end after SESSION 124:

  - Everything from SESSIONS 107-123.
  - `<PortraitUpload>` has Upload + Camera tabs. Camera uses
    `getUserMedia` → canvas → data URI. Same
    `PortraitUploadResult` shape regardless of input mode.
  - `web/src/components/ui/tabs.tsx` — new shadcn-style Radix
    Tabs primitive. Future wizard Step 3 voice tabs use it too.
  - **10 Playwright specs pass** (8 existing + 2 new portrait-
    camera tests via Chromium's `--use-fake-device-for-media-stream`).

---

## SESSION 125 — Wizard slice 2: `/internal/portrait/` backend

Recommended next slice. Wraps the inherited
`character_studio_client.generate_portrait()` with the
`/internal/*` JSON contract so the wizard's Step 2 "Generate"
path (operator types a subject; Runway gen4_image returns a
portrait) has a real backend. Half-session, backend-only.

### Recommended scope

1. **`media-engine/app/routers/internal.py`** — extend with
   `POST /internal/portrait/`:
   - Request: `{template, subject, style?}` per
     `CREATE_SPOKESPERSON_WIZARD.md` §"Backend additions".
   - Validates `template ∈ PORTRAIT_TEMPLATES`.
   - Calls `studio_generate_portrait(record=..., portrait_path=...,
     settings=..., template=..., subject=..., style=...)`.
   - Returns `{portrait_data_uri, template, mock_mode}` — synchronous,
     ~10-20 s real mode, instant in mock.
   - Mock-mode short-circuits to a deterministic placeholder PNG
     (already what the legacy code does — just wire it through).
2. **`shell/character_os/clients/media_engine.py`** — add
   `MediaEngineClient.create_portrait()` wrapper. Same shape as
   the existing `create_avatar`. Errors normalise through
   `MediaEngineError`.
3. **Smoke test** — `shell/apps/spokespeople/management/commands/smoke_portrait.py`.
   Hits `POST /internal/portrait/` directly via the client.
   Asserts the response data URI starts with `data:image/png;base64,`.
   Mock-mode only — no Runway credits burned.
4. **Verify the contract spec** is up-to-date — `MEDIA_ENGINE_INTERNAL_API.md`
   already has the §"Backend additions" pre-spec; just confirm
   it matches what landed.

### Critical constraints

- Pure JSON in/out per `MEDIA_ENGINE_INTERNAL_API.md` rule 1.
- Mock-mode deterministic (same `template` + `subject` → same
  placeholder PNG).
- Reuses the legacy `character_studio_client.generate_portrait()`
  service — no duplication of Runway-side logic.
- Stateless: no CharacterStore touch, no spokesperson record
  kept on the media-engine.

### Out of scope for SESSION 125

- SPA wiring to consume the new endpoint (lands with wizard
  slice 7 — Step 2 implementation).
- `regenerate-portrait` detail-page action (deferred per
  `CREATE_SPOKESPERSON_WIZARD.md` Q-wiz-4).
- Real Runway calls (mock mode is the right surface until
  operator has credits).

---

## Alternative slices (parallel-safe)

- **Wizard slice 3 — Voice tabs scaffold** (session). 3-mode
  voice input as a reusable component. Lands on the detail
  page's setup checklist before wizard ships.
- **Wizard slice 4 — Tone archetype field** (half-session).
  `Spokesperson.tone_archetype` migration + `suggest_tone_from_brief`
  helper in `character_os/prompts/`.

Both are independent of slice 2. Pick whichever you want next.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 2 — `/internal/portrait/` backend** (SESSION
   125 recommendation).
2. **Wizard slice 3 — Voice tabs scaffold.**
3. **Wizard slice 4 — Tone archetype field.**
4. **Wizard slices 5-9 — wizard scaffold + steps.**
5. **Wizard slice 10 — Template content** (Riggs / Sasha /
   Donny / Maya; operator-collaborative content work).
6. **Wizard slice 11 — Hide-on-completion detail page rework.**
7. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from u-d-b).
8. **Stuck-row janitor** — operational hardening.
9. **Additional video kinds** — cinematic / dialogue / long_ad.
10. **Act-Two performance capture** — deferred until Runway
    credits land.
11. **`lesson` video kind** for James-shaped educators.
12. **Real Google OAuth + dj-stripe** — operator gates.
13. **Allauth legacy-settings cleanup.**
14. **smoke_voice transaction discipline.**
15. **Drift verifier** — `verify_doc_claims --only-drift`.
16. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

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
python -m pytest character_os/prompts/        # 31 tests

# SPA (from web/)
pnpm test
pnpm e2e            # full lifecycle ~24s (10 specs)
```

---

## AI / assistant context

- Last session: SESSION 124 — wizard slice 1 (camera capture
  for `<PortraitUpload>`). ~25 minutes; 10 Playwright specs
  pass first try; Radix Tabs primitive landed for reuse on
  future wizard steps.
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. The Tabs primitive + the
  CameraCapture lifecycle pattern (cancelled flag, stopStream
  cleanup, exhaustive state branches) are foundations that
  later slices inherit.
- Templates (Riggs / Sasha / Donny / Maya) still need real
  content work — operator-collaborative pass, separate from
  implementation sessions.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
