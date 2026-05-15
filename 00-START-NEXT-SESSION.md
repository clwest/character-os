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
> breakdown). **R1-R7 + R8.0 + R8.1 shipped; R8.2, R9, R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_154_R8_APPROVAL_MODAL.md`.

---

## SESSION 154 outcome — R8.1 tool-approval modal + cost forecasting

Single-slice session. **`render_video` is now
demonstrable end-to-end from the SPA in mock mode** —
the threshold-crossing tool fires the approval modal,
operator clicks Approve, backend Celery executes the
Composition, result lands in the tool-result panel.

| Commit | What it shipped |
|---|---|
| `aac6ee4` | R8.1 feat — `useInvokeTool` + `useApproveInvocation` + `useRejectInvocation` hooks + `ToolApprovalModal` (no Radix dep) + TalkRoute `pendingInvocation` + `lastToolResult` state + IdlePanel cost forecast pill (~$0.40 for 5 min, hardcoded placeholder) + MockSessionPanel debug buttons (fire render_video / show_videos_tab) + ToolResultPanel + tsconfig types fix (jest-dom matchers) + 12 vitest tests |
| (this commit) | SESSION 154 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

**Test totals**: SPA vitest **22** (10 → 22, +12 R8.1).
Backend unchanged at **641 backend tests**. SPA build
clean (1770 modules).

**The realtime arc demo path now exercises**:
1. Sign in / sign up.
2. Create + fully configure a spokesperson.
3. Click "Talk to {name}" CTA on detail page.
4. See cost forecast pill ("~$0.40 for 5 min") next to
   Start button.
5. Click Start → mock session creates.
6. Click "Fire `render_video`" debug button.
7. Approval modal pops ("Sasha wants to render a video
   for you. Estimated cost: $0.08").
8. Click Approve → backend Celery fires composition →
   tool-result panel renders success + composition_id.
9. Click End → transcript persists.

Full handoff at
`docs/handoffs/SESSION_154_R8_APPROVAL_MODAL.md`.

### FIRST THING (SESSION 155): R8.2 (last R8 piece)

Three pieces remaining to close R8:

**SDK inner-component wiring** — replace the mock-mode
debug buttons with the SDK's native invocation
surface:
* `useClientEvent` (consumed inside `<AvatarCall>`)
  receives tool-invocation events from the avatar's
  data channel.
* Inner component dispatches via R8.1's `useInvokeTool`.
* On `succeeded` / `failed` / `rejected` →
  `sendClientEvent` so the avatar's LLM narrates the
  outcome in-character. **Q-r-2 fully resolved.**

**Live cost ticker** — runs during the session.
Updates on a 1-second interval (`elapsed_seconds ×
cost_per_minute_micros`). Drives operator awareness
as sessions approach the 5-minute cap.

**WebRTC fallback messaging** — when
`<AvatarCall onError>` fires, show a clear error
panel + "fall back to recorded video" CTA. **Q-r-9
resolved.**

Estimated scope: ~6-10 unit tests + 1 Playwright spec
driving a fake `useClientEvent` through the flow. No
backend changes.

### After SESSION 155

* **R9 (cost governance backend)** — per-workspace
  minutes budget enforcement + per-provider
  micros-per-second lookups. Upgrades R8.1's
  hardcoded cost-forecast constants + R8.2's ticker.
* **R10 (provider hardening)** — drift verifier test
  for the registry pattern.
* **Drift-prevention backlog items 2 + 3** —
  auto-bump `last_revised` + TRUST_CALIBRATION
  promotion.
* **F8.1 / K7.x** — non-realtime cleanup.

### Drift-prevention backlog status

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | **Superseded** by `doctor` extensions |
| 2 | Auto-bump `last_revised` on handoff write | Queued |
| 3 | Promote calibration entries to TRUST_CALIBRATION | Queued |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done; doctor-based SESSION 151 |
| 5 | Fix INVENTORY's two known generator bugs | Celery undercount done SESSION 151; working-tree-dirty flag pending |

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
  + R8.1 shipped** (SESSIONS 146-154). v1 tool
  catalog complete (SESSION 152); SPA foundation +
  approval modal + cost forecast shipped
  (SESSIONS 153-154). R8.2 closes R8; R9 + R10
  remain.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0-K9 | Knowledge layer end-to-end                    | DONE (SESSIONS 137-145) |
| V0-V15 | Video composition arc + recipe gallery     | DONE (SESSIONS 142-144) |
| F0-F10 | Workspace fabric arc                       | DONE (SESSION 144) |
| R0-R5 | Realtime arc backend                          | DONE (SESSION 146) |
| R6 + R6.1 | Cross-session memory                      | DONE (SESSIONS 148, 152) |
| R7.0-R7.3 | Tool dispatch + 6-tool catalog            | DONE (SESSIONS 149-152) |
| R8.0 | SPA foundation (SDK + API client + TalkRoute) | DONE (SESSION 153) |
| R8.1 | Tool-approval modal + cost forecasting        | DONE (SESSION 154) |
| R8.2 | SDK inner-component wiring + cost ticker + WebRTC fallback | Next (SESSION 155) |
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

---

## Queued investigations (priority-ordered)

1. **R8.2 — SDK inner-component wiring + cost ticker
   + WebRTC fallback** (next session; closes R8).
2. **R9 — Cost governance backend.**
3. **R10 — Multi-provider hardening.**
4. **Drift-prevention backlog item 2 + 3.**
5. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
6. **K7.x — YouTube ingest fix.**
7. **K6.3 — Brief length cap.**
8. **K7.1 — Cost telemetry surface.**
9. **W11.1 — Edit-spokesperson modal.**
10. **First marketing video.**
11. **Voice preset audit.**
12. **E2e detritus cleanup.**
13. **OpenAI client factory port.**
14. **Cast sync command.**
15. **Stuck-row janitor.**
16. **Act-Two performance capture.**
17. **`lesson` video kind.**
18. **Real Google OAuth + dj-stripe.**
19. **Allauth legacy-settings cleanup.**
20. **smoke_voice / smoke_avatar transaction discipline.**
21. **INVENTORY working-tree-dirty flag fix.**
22. **Brand Identity v2 + dark mode.**

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

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 641 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 22 vitest tests
pnpm e2e                                      # Playwright (in mock mode only)
```

---

## AI / assistant context

- **Last session: SESSION 154 — R8.1 shipped.**
  Tool-approval modal + cost forecasting UI.
  `render_video` is demonstrable end-to-end from the
  SPA in mock mode. 22 SPA tests pass.
- **Calibration carried forward:**
  - **Type-system + runtime config drift on testing
    plugins** — wire jest-dom at both places (vitest
    setup + tsconfig types). One-test consumers paper
    over the gap until a second test hits it.
  - **Voice modal copy in first person** — surface
    tool intent as "Sasha wants to render a video
    for you," not "Approve tool `render_video`."
    Per-tool human translation in `formatToolLabel`.
  - **Don't strand the operator mid-decision** —
    modal dismiss is gated on idle state during
    async ops.
  - **Mock-mode UX is first-class** (SESSION 153).
  - **React Router 7 sibling-Route precedence**
    (SESSION 153).
  - **Vitest setup file gap** (SESSION 153).
  - **Ship prerequisites with consumers** (SESSION 152).
  - **Doctor is the drift tool** (SESSION 151).
  - **Pyright in this repo is noisy on Django/DRF.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **R8.2 / R9 / R10 = ~3 more sessions to close
  the realtime arc fully.** R8.2 makes the avatar
  natively fire tools (replaces mock debug buttons
  with the SDK's `useClientEvent`); R9 + R10 are
  operational polish.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end.
