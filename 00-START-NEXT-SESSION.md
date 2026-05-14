---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md` (NEW SESSION 123).
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_123_WIZARD_SCOPE_LOCK.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Five SPA slices shipped + Custom User model +
Prompt-helper Tier 1 + Wizard scope-lock doc. Wizard
implementation begins SESSION 124.

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
| 6+    | Wizard implementation slices         | NEXT (SESSION 124) |

What's working end-to-end after SESSION 123:

  - Everything from SESSIONS 107-122.
  - `docs/design/CREATE_SPOKESPERSON_WIZARD.md` locks 4-step
    wizard, two-axis archetype model, 3-mode voice input,
    hide-on-completion, prompt-helper wiring, camera + audio
    capture browser-API contract.
  - No code added this session (doc-only slice).

---

## SESSION 124 — Camera capture for `<PortraitUpload>`

Recommended first wizard-related slice. Pure SPA work; pure
foundation; no backend changes.

### Why this slice first

The wizard scope-lock (SESSION 123 §"Implementation order")
recommends 11 ordered slices. Slice 1 is camera capture for the
existing `<PortraitUpload>` component. Three reasons it goes
first:

1. **Pure SPA + reusable immediately.** The existing SESSION
   120 `/spokespeople/new` create-spokesperson flow gains
   camera capture without any other slice landing. Operator can
   demo it end-to-end.
2. **Browser-API foundation for the rest of the wizard.** The
   wizard's Step 2 portrait camera capture + Step 3 audio
   recording share the same shape: `getUserMedia` permission
   flow, error/fallback handling, stream cleanup. Landing the
   pattern here pays off twice.
3. **Smallest natural slice.** Half a session. Zero backend
   risk.

### Recommended scope

1. **Extend `web/src/components/portrait-upload.tsx`** —
   replace the single dropzone state with a tabbed UI: **Upload
   / Take a picture**. The existing drag-and-drop file path
   stays as the Upload tab.
2. **Camera tab implementation:**
   - On tab activate: `navigator.mediaDevices.getUserMedia(
     { video: { facingMode: "user", width: { ideal: 1024 } },
     audio: false })`.
   - Render the `MediaStream` in a `<video>` preview element.
   - "Take picture" button → `<canvas>.drawImage(video, ...)`
     → `canvas.toDataURL("image/png")` → commit as the same
     `PortraitUploadResult.dataUri` value the Upload path
     already produces.
   - "Re-take" affordance to discard and re-capture.
   - Cleanup on commit / unmount / tab switch:
     `stream.getTracks().forEach(t => t.stop())`.
3. **Permission denial handling:** if `getUserMedia` rejects,
   show inline copy ("Camera access needed — or upload a file
   instead") with the Upload tab as the fallback. No app-level
   error state.
4. **Browser feature detection:** if `navigator.mediaDevices`
   is undefined (older browsers / Safari in some contexts),
   hide the Take a picture tab entirely.
5. **Playwright spec** — `e2e/portrait-camera.spec.ts`.
   Playwright's Chromium ships with a fake video stream
   (`--use-fake-device-for-media-stream` and
   `--use-fake-ui-for-media-stream`) so e2e tests can drive
   `getUserMedia` deterministically without a real camera.
   Test asserts: sign up → /spokespeople/new → switch to
   Take a picture tab → camera permission auto-grants → click
   Take picture → preview shows → submit → land on detail
   page with avatar bound (mock mode).

### Critical constraints

- Stay strict-mode TypeScript. No `any`.
- The data shape returned by the camera path must be IDENTICAL
  to the file-upload path (same `PortraitUploadResult` type) so
  consumers don't branch on input mode.
- Editorial-warm aesthetic inheritance: tabs use the same
  pattern as future wizard tabs will. shadcn doesn't ship a
  Tabs primitive in our current install; add via
  `pnpm dlx shadcn@latest add tabs` or write a tiny one inline.
- Permission denial / browser-not-supported are NOT silent
  failures (per BRAND_IDENTITY_V1.md rule 6 + wizard contract
  rule 6). Both surface visible copy.

### Out of scope for SESSION 124

- The wizard itself (slices 5-9 of the implementation order).
- Audio recording (SESSION 124's pattern informs it but doesn't
  ship it).
- Runway-generated portraits via `/internal/portrait/` (slice 2
  of the implementation order).
- Tone archetype field + helper (slice 4).
- Voice tabbed UI (slice 3).

---

## Alternative slices

If you'd rather not start with camera, three other
foundation-tier wizard slices are parallel-safe:

- **`/internal/portrait/` backend endpoint** (slice 2). Wraps
  the inherited `character_studio_client.generate_portrait()`
  with the `/internal/*` JSON contract. New
  `MediaEngineClient.create_portrait()` wrapper. Half-session.
  Unlocks the wizard's "Generate" portrait path.
- **Voice tabs scaffold** (slice 3). The 3-mode voice input
  (Preset / Upload / Record) as a reusable component. Lands on
  the existing `/spokespeople/{id}/clone-voice/` action (SESSION
  110 backend) without wiring into the wizard. Session-sized.
- **Tone archetype field + suggest_tone_from_brief** (slice 4).
  Migration + helper in `character_os/prompts/`. Half-session.

---

## Queued investigations (priority-ordered)

1. **Wizard slice 1 — Camera capture** (SESSION 124
   recommendation).
2. **Wizard slice 2 — `/internal/portrait/` endpoint.**
3. **Wizard slice 3 — Voice tabs scaffold.**
4. **Wizard slice 4 — Tone archetype field.**
5. **Wizard slices 5-9 — wizard scaffold + steps.**
6. **Wizard slice 10 — Template content** (Riggs / Sasha /
   Donny / Maya; operator-collaborative content work).
7. **Wizard slice 11 — Hide-on-completion detail page rework.**
8. **Tier 2 prompt helpers** (`DynamicPromptBuilder` from
   u-d-b). Defer until make-a-video flow needs richer scripts.
9. **Stuck-row janitor** — operational hardening.
10. **Additional video kinds** — cinematic / dialogue /
    long_ad. `CREATIVE_PRINCIPLES` is ready for them.
11. **Act-Two performance capture** — deferred to a future
    detail-page slice when Runway credits land.
12. **`lesson` video kind** for James-shaped educators. Phase 4
    content addition.
13. **Real Google OAuth + dj-stripe** — operator gates.
14. **Allauth legacy-settings cleanup** — when allauth drops
    the legacy keys.
15. **smoke_voice transaction discipline** — tiny fix.
16. **Drift verifier** — `verify_doc_claims --only-drift`.
17. **Brand Identity v2 + dark mode** — when user-testing
    happens.

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
pnpm e2e            # full lifecycle ~22s
```

---

## AI / assistant context

- Last session: SESSION 123 — wizard scope-lock doc. ~25
  minutes. Came out of a discussion-heavy series of decisions
  about archetypes (visual + tone separated after the unicorn
  anecdote), UX (form-driven, no chat), and scope (Act-Two
  deferred, voice all-3-modes, hide-on-completion).
- **Calibration carried forward:** this operator prefers right-
  shaping foundations early. Three scope-lock docs in a row
  (SPA architecture, prompt helpers, wizard) is the right
  shape for a project with this much remaining surface area.
- The wizard is 11 slices, 6-8 sessions estimated.
- Templates (Riggs / Sasha / Donny / Maya) need real content
  work — operator-collaborative pass, separate from
  implementation sessions.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
