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
> breakdown). **R1-R8 shipped (operator-visible product
> complete); R9 + R10 remain (operational polish).**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_155_R8_CLOSE.md`.

---

## SESSION 155 outcome — R8.2 + R8 closes

Single-slice session shipped R8.2. **The
operator-visible product story for the realtime arc is
feature-complete.** R-arc state: R1-R8 done. R9 (cost
governance backend) + R10 (multi-provider drift
verifier) remain as operational polish.

| Commit | What it shipped |
|---|---|
| `5697269` | R8.2 feat — `AvatarSessionInner` (consumes SDK `useClientEvents` for native tool invocation) + `CostTicker` (1-second interval, tone-shifts at 3/4 min boundaries, mock-tagged) + WebRTC fallback panel with "Make a recorded video instead" CTA + SDK mock update for tests + 13 vitest tests |
| (this commit) | SESSION 155 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

**Q-r-2 partial v1 resolution**: Runway's SDK doesn't
expose a `sendClientEvent` for server-pushed narration.
v1 narration is operator-mediated — modal decision →
operator verbally continues. Audit row's
`error_message` captures the operator's reason
server-side. In-conversation backend-pushed narration
deferred to v2 or a Runway SDK feature request.
Documented in `AvatarSessionInner` module comment.

**Q-r-9 resolved**: `<AvatarCall onError>` routes to
the error panel; new "Make a recorded video instead"
CTA on the fallback panel.

**Test totals**: SPA vitest **35** (22 → 35, +13: 7
cost-ticker + 4 avatar-session-inner + 2 talk-route).
Backend unchanged at **641 backend tests**. SPA build
clean (1773 modules).

**Full operator demo path** (now end-to-end via the SPA):

1. Sign in / sign up.
2. Create + fully configure a spokesperson.
3. Click "Talk to {name}" CTA on detail page.
4. IdlePanel shows cost forecast pill ("~$0.40 for
   5 min").
5. Click Start → mock session creates → Live (demo
   mode) pill + cost ticker starts.
6. Tool invocation paths:
   - Mock-mode debug button "Fire `render_video`" → modal pops → Approve → backend Celery executes Composition → ToolResultPanel shows composition_id.
   - In real mode: avatar's LLM fires the tool over WebRTC data channel → AvatarSessionInner catches → same modal path.
7. Click End → transcript persists via R5's Celery task.
8. Next session opens → R6/R6.1 memory loop picks up
   the prior transcript.

Full handoff at
`docs/handoffs/SESSION_155_R8_CLOSE.md`.

### FIRST THING (SESSION 156): R9 (cost governance backend)

R8.1's IdlePanel forecast + R8.2's CostTicker both
use hardcoded `$0.08/min × 5 min = $0.40` placeholders.
R9 upgrades:

* **Per-provider micros-per-second lookups** in
  `apps/billing/services.py` (or new
  `apps/realtime/cost.py`). Same shape as V's
  per-primitive cost estimators.
* **Per-workspace minutes-budget enforcement** at
  session-create + session-end — R3's
  `check_realtime_session_limit` already counts
  sessions per month; R9 adds the live minutes-spent
  tracking + cap.
* **Cost-actual updates** to
  `RealtimeSession.cost_actual_micros` from the same
  per-minute table.
* **SPA hook** to fetch the real estimate — replaces
  hardcoded constants in IdlePanel + CostTicker.

Estimated scope: ~10 backend tests + ~3 SPA tests for
the new hook. Possibly a migration if we want
`realtime_minutes_used` on Subscription.

### After SESSION 156

* **R10 (multi-provider drift verifier)** — smallest
  remaining R slice. One test that imports the
  provider registry + asserts every `RealtimeProvider`
  method is implemented for Runway + the mock provider.
* **First marketing video** — flips RUNWAY_FORCE_MOCK
  off, walks through a real session with a cast
  spokesperson. Operator-mediated.
* **Drift-prevention backlog items 2 + 3.**
* **F8.1 / K7.x / K6.3 / K7.1 / W11.1.**

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
- **Realtime avatar arc (R0-R10).** **R1-R8 shipped
  — operator-visible product complete**
  (SESSIONS 146-155). R9 (cost governance) + R10
  (drift verifier) remain as operational polish.

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
| R8.0-R8.2 | SPA realtime UX (foundation + modal + ticker + native invocation + WebRTC fallback) | DONE (SESSIONS 153-155) |
| R9 | Cost governance backend                          | Next (SESSION 156) |
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

Cast can do everything an operator-visible v1 product
needs: render *informed* videos, hold text
conversations, hold live realtime sessions grounded in
workspace knowledge with cross-session memory, fire 6
tools mid-session including `render_video` (with
operator approval) and `attach_memory` (mid-session
commit). The SPA exposes all of this end-to-end with
a cost ticker + WebRTC fallback.

---

## Queued investigations (priority-ordered)

1. **R9 — Cost governance backend** (next session).
2. **R10 — Multi-provider hardening (drift verifier).**
3. **First marketing video** — exercises the whole
   stack against real Runway. Highest-value
   demonstration output.
4. **Drift-prevention backlog item 2 + 3.**
5. **F8.1 — K10 seed corpus** (blocked on operator
   markdown).
6. **K7.x — YouTube ingest fix.**
7. **K6.3 — Brief length cap.**
8. **K7.1 — Cost telemetry surface.**
9. **W11.1 — Edit-spokesperson modal.**
10. **Voice preset audit.**
11. **E2e detritus cleanup.**
12. **OpenAI client factory port.**
13. **Cast sync command.**
14. **Stuck-row janitor.**
15. **Act-Two performance capture.**
16. **`lesson` video kind.**
17. **Real Google OAuth + dj-stripe.**
18. **Allauth legacy-settings cleanup.**
19. **smoke_voice / smoke_avatar transaction discipline.**
20. **INVENTORY working-tree-dirty flag fix.**
21. **Brand Identity v2 + dark mode.**

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
pnpm test                                     # 35 vitest tests
pnpm e2e                                      # Playwright (in mock mode only)
```

---

## AI / assistant context

- **Last session: SESSION 155 — R8.2 shipped.** R8
  closes. R-arc state: R1-R8 done; operator-visible
  product complete. 35 SPA tests + 641 backend tests
  pass.
- **Calibration carried forward:**
  - **Fake timers + setSystemTime double-count** —
    when using `vi.useFakeTimers()`, pick ONE:
    `setSystemTime` for arbitrary jumps OR
    `advanceTimersByTime` for "elapse N ms + fire
    intervals." Mixing them double-counts because
    `advanceTimersByTime` also advances `Date.now`.
  - **SDK features are hypotheses until exercised** —
    `sendClientEvent` was named in the R0 scope-lock
    but doesn't exist in Runway's SDK. R8.2 confirmed.
    Treat unverified API names in scope-locks as
    intent, not contract.
  - **Mock test surfaces parallel production paths**
    — R8.1's mock debug buttons + R8.2's SDK native
    invocation feed the same `onToolInvocation`
    callback. Tests on the mock path indirectly
    exercise the production path.
  - **Voice modal copy in first person** (SESSION 154).
  - **Don't strand the operator mid-decision**
    (SESSION 154).
  - **Type-system + runtime config drift on testing
    plugins** (SESSION 154).
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Ship prerequisites with consumers** (SESSION 152).
  - **Doctor is the drift tool** (SESSION 151).
  - **Pyright in this repo is noisy on Django/DRF.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **R9 + R10 = ~2 more sessions to close the
  realtime arc fully.** R9 upgrades R8.1's hardcoded
  cost forecast + R8.2's ticker with real
  per-provider estimates; R10 is a one-test drift
  verifier.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end.
