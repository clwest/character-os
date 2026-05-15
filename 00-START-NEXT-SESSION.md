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
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — 9 contract rules, V0-V15 slice breakdown).
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R1-R7 + R8.0 shipped; R8.1, R8.2, R9, R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_153_R8_SPA_FOUNDATION.md`.

---

## SESSION 153 outcome — R8.0 SPA realtime foundation

Single-slice session. **The realtime arc is now
operator-visible.** Operator with a fully-configured
spokesperson clicks "Talk to {name}" CTA on the detail
page → lands at `/spokespeople/:id/talk` → walks
through the full lifecycle (idle → creating → ready →
live → ended) against the R3 broker + R4 doc composer
+ R6/R6.1 memory + R5 transcript capture.

| Commit | What it shipped |
|---|---|
| `7669007` | R8.0 feat — `@runwayml/avatars-react@0.16.0` SDK + `web/src/lib/api/realtime.ts` (createSession + poll + end with Zod schemas honoring contract rule 3) + `web/src/routes/spokespeople/talk.tsx` (lifecycle component) + route registration + "Talk to {name}" CTA + 7 vitest tests + 1 Playwright spec + jest-dom matchers wired into vitest |
| (this commit) | SESSION 153 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

**Mock-mode UX is load-bearing for the demo**:
`session.mock_mode === true` → SPA skips SDK mount,
renders "Live (demo mode)" pill + MockSessionPanel
(shows provider session id / document id). The whole
realtime arc is now demonstrable end-to-end locally
without real Runway creds.

**Test totals**: SPA vitest 3 → 10 (+7). Backend
unchanged at 641. SPA build clean (1768 modules).

**R8 sub-sliced** at proposal time (per SESSION 149-150
calibration): R8.0 / R8.1 / R8.2. R8.0 ships the
minimum viable demo; R8.1 + R8.2 add the
tool-approval modal + cost forecasting + live cost
ticker + error paths.

Full handoff at
`docs/handoffs/SESSION_153_R8_SPA_FOUNDATION.md`.

### FIRST THING (SESSION 154): R8.1 (tool-approval modal + cost forecasting)

Two visible pieces in one slice:

**Tool-approval modal**:
* When the avatar's LLM invokes a tool that returns
  `state=awaiting_approval` (today: `render_video`,
  $0.08 > $0.05 threshold), SPA renders a modal:
  "Sasha wants to render an ad — cost ~$0.08.
  Approve / Reject?"
* Approve → `POST /api/realtime_tool_invocations/<id>/approve/`
  → result feeds back to the avatar via the SDK's
  `sendClientEvent`.
* Reject → `POST .../reject/` with optional `reason`
  → narrated back via `sendClientEvent` so the
  avatar's LLM can apologetically pivot.
* The SDK's `useClientEvent` hook receives the
  tool-invocation event from the avatar's data
  channel; the SPA POSTs to `/invoke_tool/`, the
  dispatcher creates an audit row, and if cost > $0.05
  the modal fires.

**Cost forecasting**:
* Before session-start: "~$X for a 5-min session" pill
  next to the Start button. Uses
  `apps.billing.services.get_usage(workspace)` Usage
  shape (already returns the tier minutes cap; R3
  ships).
* R9 (cost governance backend) refines the
  per-minute estimate; R8.1 ships with a conservative
  hardcoded `$0.08/min` placeholder, upgrades to real
  data when R9 lands.

Estimated scope: ~6-8 unit tests + 1-2 Playwright
specs, no backend changes.

### After SESSION 154

* **R8.2** — live cost ticker during the session +
  WebRTC fallback messaging (Q-r-9) + tool-rejection
  narration via `sendClientEvent` (Q-r-2 full
  resolution).
* **R9** — cost governance backend (per-workspace
  minutes budget enforcement at session-create + the
  per-minute estimation primitives).
* **R10** — provider hardening (drift verifier test
  for the registry pattern).
* **Drift-prevention backlog items 2 + 3** —
  auto-bump `last_revised` + TRUST_CALIBRATION
  promotion. Small. Worth picking up between R8
  sub-slices.

### Drift-prevention backlog status

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | **Superseded** by `doctor` extensions |
| 2 | Auto-bump `last_revised` on handoff write | Queued |
| 3 | Promote calibration entries to TRUST_CALIBRATION | Queued |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done SESSION 147; doctor-based SESSION 151 |
| 5 | Fix INVENTORY's two known generator bugs | **Celery undercount done SESSION 151**; working-tree-dirty flag still pending |

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live
in real-mode (SESSION 136).

**Phase 4 (four arcs in flight, three complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped. K10 →
  F8.1 queued. K7.x YouTube ingest fix queued.
- **Video composition arc (V0-V15). COMPLETE**
  (SESSIONS 142-144).
- **Workspace fabric arc (F0-F10). COMPLETE**
  (SESSION 144).
- **Realtime avatar arc (R0-R10).** **R1-R7 + R8.0
  shipped** (SESSIONS 146-153). v1 tool catalog
  complete (R7.3 / SESSION 152); SPA foundation
  shipped (R8.0 / SESSION 153). R8.1 (tool-approval
  modal + cost forecast) is next. R8.2 + R9 + R10
  remain.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0-K9 | Knowledge layer end-to-end                    | DONE (SESSIONS 137-145) |
| V0-V15 | Video composition arc + recipe gallery     | DONE (SESSIONS 142-144) |
| F0-F10 | Workspace fabric arc                       | DONE (SESSION 144) |
| R0-R5 | Realtime arc backend (schema → broker → docs → transcripts) | DONE (SESSION 146) |
| R6 | Cross-session memory projection                | DONE (SESSION 148) |
| R6.1 | Widen R6 query                                 | DONE (SESSION 152) |
| R7.0 | Tool dispatch foundation                       | DONE (SESSION 149) |
| R7.1 | Three sync tools + tier-aware filtering        | DONE (SESSION 150) |
| R7.2 | Async dispatch + `render_video`                | DONE (SESSION 151) |
| R7.3 | `attach_memory` + capture_transcript helper    | DONE (SESSION 152) |
| R8.0 | SPA foundation (SDK + API client + TalkRoute + CTA) | DONE (SESSION 153) |
| R8.1 | Tool-approval modal + cost forecasting UI      | Next (SESSION 154) |
| R8.2 | Live cost ticker + WebRTC fallback + rejection narration | Queued |
| R9 | Cost governance backend                          | Queued |
| R10 | Multi-provider hardening (drift verifier test)  | Queued |
| K6.3 | Brief length cap in script synthesis           | Queued |
| K7.1 | Per-chunk cost telemetry surface in UI         | Queued |
| K10 | Onboarding seed                                | → F8.1 (needs operator-authored markdown) |
| W11.1 | Edit-spokesperson modal                      | Queued |

**Cast roster in workspace `admins-workspace`:**

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - Sasha the Raccoon (sales) — id `79d48883-...`
  - Donny the Sloth (user stories) — id `f30b2980-...`
  - Maya the Panda (educator) — id `9410f23f-...`

Cast can render *informed* videos (K6 / SESSION 139),
hold text conversations (K8/K9 / SESSION 145), and
now hold **live realtime sessions** end-to-end in the
SPA (R1-R8.0 / SESSIONS 146-153) — grounded in
workspace knowledge with cross-session memory and a
6-tool action catalog (only the approval modal +
cost UX remain before R8 closes).

---

## Queued investigations (priority-ordered)

1. **R8.1 — Tool-approval modal + cost forecasting**
   (next session's primary slice).
2. **R8.2 — Live cost ticker + error paths +
   rejection narration.**
3. **R9 — Cost governance backend.**
4. **R10 — Multi-provider hardening.**
5. **Drift-prevention backlog item 2 + 3.**
6. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
7. **K7.x — YouTube ingest fix.**
8. **K6.3 — Brief length cap.**
9. **K7.1 — Cost telemetry surface.**
10. **W11.1 — Edit-spokesperson modal.**
11. **First marketing video.**
12. **Voice preset audit.**
13. **E2e detritus cleanup.**
14. **OpenAI client factory port.**
15. **Cast sync command.**
16. **Stuck-row janitor.**
17. **Act-Two performance capture.**
18. **`lesson` video kind.**
19. **Real Google OAuth + dj-stripe.**
20. **Allauth legacy-settings cleanup.**
21. **smoke_voice / smoke_avatar transaction discipline.**
22. **INVENTORY working-tree-dirty flag fix.**
23. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000 — DO NOT pass --noreload

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**Six force-mocks** (RUNWAY on media-engine;
EMBEDDING + RENDER_SCRIPT + CONVERSATION_REPLY + SERPER
+ REALTIME_MEMORY on Django).

**Realtime demo path (mock mode)**:
1. Sign in / sign up.
2. Create a spokesperson via the wizard, fully
   configure it (avatar + portrait).
3. Navigate to the spokesperson detail page.
4. Click "Talk to {name}" CTA → lands at
   `/spokespeople/:id/talk`.
5. Click Start → mock session creates → "Live
   (demo mode)" pill shows.
6. Click End → transcript capture fires.

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait
python -m pytest                              # 641 tests
python -m pytest apps/realtime/tests/         # 131 tests (R1-R7)

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 10 vitest tests
pnpm e2e                                      # Playwright (in mock mode only)
```

---

## AI / assistant context

- **Last session: SESSION 153 — R8.0 shipped.** SPA
  realtime foundation — `/spokespeople/:id/talk`
  route + SDK + API client. The arc is now
  operator-visible. 641 backend + 10 SPA tests pass.
- **Calibration carried forward:**
  - **Mock-mode is a first-class UX state**, not a
    silent fallback. Six force-mock flags on the
    backend; the SPA renders each explicitly.
  - **React Router 7 static-beats-dynamic precedence
    is within-a-Route only.** Order sibling Routes:
    more specific first.
  - **Vitest setup files** are easy to forget until
    a SECOND test consumer arrives. Wire jest-dom +
    user-event globally, not per-test.
  - **Ship prerequisites with consumers in one slice**
    (SESSION 152).
  - **Extract helpers between two code paths early**
    (SESSION 152).
  - **Inverted-test pattern when changing semantics**
    (SESSION 152).
  - **Doctor is the drift tool** (SESSION 151).
  - **Splitting a scope-locked slice mid-
    implementation is fine** (SESSION 151).
  - **Pyright in this repo is noisy on Django/DRF**
    — same false positives every session.
  - **OpenAI gpt-5 family uses the Responses API.**
- **R8.1 / R8.2 / R9 / R10 = ~4 more sessions to close
  the realtime arc fully.** R8.1 makes the avatar's
  tool catalog actually demonstrable (currently
  invocations land but the modal doesn't fire).
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end (codified SESSION 143;
  reinforced SESSION 147; honored SESSIONS 148-153).
