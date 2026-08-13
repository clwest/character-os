---
title: "Bridge tools UI (C5) — non-realtime bridge invocation at /workspace/tools"
status: proposed
proposed: 2026-07-22 (SESSION 225, slice C5.0)
locked: null
closed: null
companion_docs:
  - ENGINE_BRIDGE_V1.md
  - WORKSPACE_FABRIC_V1.md
  - SPA_ARCHITECTURE.md
  - ../handoffs/SESSION_223_WORKSPACE_COORD_EB5_DOGFOOD.md
  - ../production-readiness/dogfood-eb5/DOGFOOD_REPORT.md
---

# Bridge tools UI — non-realtime invocation at /workspace/tools

> **Status: PROPOSED (SESSION 225).** First-customer surface for the
> three engine-bridge tools (`consult_engine`, `query_spider_data`,
> `agent_consult`) as a discoverable SPA route the operator can drive
> **without ever starting a live WebRTC realtime session**. Backend is
> already complete (EB.0–EB.3 SESSION 217 + C3 SESSION 222 for Asset
> persistence). C5 is the SPA layer only. Seven contract rules, five
> slices C5.0–C5.4. Estimated ~¾ session to ship.
>
> **Roadmap mapping:** C5 satisfies **P3 4.5** (non-realtime bridge
> invocation) in full and **P3 4.4 partially** — inline tier + cost
> hints on the tool picker address the "user doesn't know what tools
> cost" gap without pulling in a full catalog list-view or a
> "last-invoked" column. Full 4.4 catalog surface + last-invoked
> metadata lands with a follow-on slice (candidate C6) once 4.6's
> `RealtimeToolInvocation` activity feed exists to source the
> last-invoked timestamp from.

---

## TL;DR

SESSION 223's EB.5 dogfood proved the production `_execute_inline`
sync-dispatch code path works cleanly against a DRAFT-status
`RealtimeSession` — no live LLM, no Runway media, no WebRTC. Two
`Asset(BRIDGE_ANSWER)` rows persisted; sync-dispatch symmetry
verified. C5 turns that discovery into a first-class customer surface:

1. **Route `/workspace/tools`** — new SPA page inside the workspace
   fabric shell (alongside `/workspace/knowledge`, `/recipes`).
2. **Tool picker + question form** — three tools listed, pick one,
   type a question, submit. Auto-creates a DRAFT container session
   if none exists in the current page session; reuses within.
3. **Result panel** — renders the bridge answer text, links to the
   persisted `Asset(BRIDGE_ANSWER)` in the workspace asset library.
4. **Pro+ tier gate** — Starter workspaces see an upgrade nudge
   panel; resolver still enforces server-side.
5. **No new backend endpoints.** C5 consumes existing R7.0
   `POST /api/realtime_sessions/<id>/invoke_tool/` +
   R3 `POST /api/realtime_sessions/` + EB.3 `GET /api/engine_connections/`.

No new persistence. No new tools. No realtime protocol changes.
Cost per invocation ≈ $0.005 (under the $0.05 approval threshold —
no modal, feels instant).

---

## Why now

Four drivers converge post-EB.5 (SESSION 223):

1. **EB.5 dogfood produced product signal, not just verification.**
   `_execute_inline` against a DRAFT session was framed in the
   ratified plan as a *workaround for PD-1*. The dogfood proved it
   is a legitimate customer surface — identical persistent state
   (Asset shape + audit row shape + FK linking) to what a
   live-LLM-in-session invocation would produce. That flips C5
   from "discoverability polish" to "primary bridge-tool entry
   point for customers whose v1 workflow doesn't require WebRTC."

2. **First-customer surface is the missing half of the EB arc.**
   EB.4 shipped per-workspace *configuration* (`/settings/engine`).
   EB.0-EB.3 shipped the backend for *invocation*. No SPA route
   exists to actually *use* the bridge tools without starting a
   realtime avatar session. C5 closes that gap.

3. **PD-1 is fixed but latent-risk architecture remains.** SESSION
   224's P1 2.7 landed 14 per-method timeout overrides + regression
   test. C5 sidesteps the entire realtime timeout coordination
   surface — no `create_realtime_session` call means no
   cross-service timeout to coordinate. That's a real reduction in
   first-customer failure modes, not just a UX preference.

4. **Zero backend work required.** All persistence, dispatch,
   resolver, tier gating, and Asset creation surfaces exist and
   are production-tested. C5 is a straightforward SPA slice
   following patterns already established by K4 (`/workspace/knowledge`),
   V15 (`/recipes`), and R8 (`BridgeAnswerPanel` in `/spokespeople/:id/talk`).

---

## Contract rules (load-bearing)

Seven rules. Six inherit from EB-arc directly (all still in force
for C5); one is C5-specific.

1. **EB-arc rules 1, 2, 3, 4, 5, 8 apply unchanged.** Workspace
   scoping, resolve-by-workspace-not-env, env-var-fallback,
   token-write-only-over-API, `enabled=False` fails closed, Pro+
   gate at resolver. C5 introduces no new authentication or
   configuration paths — it only *consumes* the surfaces those
   rules protect.

2. **C5 never starts a live realtime session.** Every C5 dispatch
   goes through a DRAFT-status `RealtimeSession` container. The
   SPA never calls `create_realtime_session` on the media-engine;
   the DRAFT session is a Django-only row. This is the load-bearing
   architectural choice: C5's whole value proposition is
   sidestepping WebRTC (and the class-defect surface PD-1
   originated from) as a customer entry point.

   **P1 2.8-b hardening (SESSION 227, F-12 fix):** rule 2 is now
   server-enforced, not client-conventional. The `POST
   /api/realtime_sessions/` server default is DRAFT. Callers that
   want a paid Runway session must opt in with `real_mode=true`.
   Only R8 (`/spokespeople/:id/talk`) sends that flag. Pre-P1-2.8-b
   the server default was real-mode and C5 opted out via
   `draft_only=true`; F-12 showed this failed silently under a
   stale runserver (client sent the flag; running process ignored
   it because the pre-F-09-A code had no guard). The flip closes
   that recurrence class: any future process desync or missing
   client flag now defaults to $0 spend. `draft_only=true` is
   retained on the C5 payload as an explicit-intent marker
   (redundant but forward-compatible); sending both `real_mode`
   and `draft_only` as true → 400.

3. **DRAFT container sessions are page-session-scoped, not
   persistent-user-scoped.** SPA creates one DRAFT session on first
   invocation, reuses within the same page load, does not surface
   the session as a durable object in the workspace UI. Operator
   sees the *answers* (Assets), not the container sessions. Rule
   protects the workspace asset library from noise (a browsing
   operator does not want their "sessions" list flooded with
   throwaway DRAFT containers).

4. **v1 SPA picker ships `consult_engine` only** (SESSION 226,
   F-10-C ratification). `query_spider_data` and `agent_consult`
   remain backend-registered but excluded from the picker because
   the C5.1 single-question form does not send their required args
   (`topic` for `query_spider_data`; `agent_name` + `question` for
   `agent_consult`) — attempted dispatch returns
   `ValueError: <field> is required`. A follow-on slice
   (candidate C6, F-10-B pattern) ships a per-tool fields
   renderer + the `agent_consult` agent-picker UX design; that
   slice re-enables both. The tier framing survives unchanged:
   `consult_engine` = $0.005, Pro+ via EB rule 8's resolver gate
   (the backend `tier_required="starter"` is still misleading —
   Starter workspaces get `None` from `resolve_engine_connection`
   and the executor returns "engine not configured"). Historical
   Q-c5-3 D-verdict (all three tools same tier / cost class,
   all under approval threshold) still holds for the three
   backend tools; F-10-C narrows the SPA surface without
   changing the backend contract.

5. **DRAFT session auto-creation is one-click, not a separate
   step.** SPA form submit fires `POST /api/realtime_sessions/`
   silently if no DRAFT exists in page state, then chains
   `POST .../invoke_tool/`. Operator does not pick a session, does
   not name a session, does not see a "create session first"
   prompt. Q-c5-2 resolved D-verdict 2026-07-22.

6. **Cost estimation and question history are v1-out-of-scope.**
   No pre-submit cost estimate (Q-c5-6: costs negligible, avoids
   estimated-vs-actual confusion). No client-side question history
   dropdown (Q-c5-5: Assets already persist server-side; localStorage
   history is redundant with the asset library).

7. **The `_execute_inline` production code path is the only
   dispatch path.** C5 does not add a "non-realtime dispatch mode"
   flag to the API. It uses the same `POST .../invoke_tool/`
   endpoint the R7.0/R7.1/R7.2 avatar-triggered path uses; the
   only difference is the container session is DRAFT status instead
   of LIVE. Contract preservation matters here — if the dispatch
   code path diverges, R8's tool-approval and cost-forecast flows
   would silently skip on C5 invocations, which is a bug class.

---

## Data model additions

**None.** C5 is a pure SPA slice.

Existing surfaces C5 consumes:
- `RealtimeSession` (R1) — DRAFT status container.
- `RealtimeToolInvocation` (R7.0) — audit row per dispatch.
- `Asset` with `role=BRIDGE_ANSWER` (C3) — persisted answer row.
- `EngineConnection` (EB.1) — workspace config, read-only from C5.

Zero new migrations.

---

## Slice plan

C5.0 closes with this scope-lock commit. Four implementation
slices follow.

| Slice | What ships | Effort |
|---|---|---|
| C5.0 | This doc | ✓ SHIPPED (`bf24d68`) |
| C5.1 | SPA `/workspace/tools` route — tool picker, question form, DRAFT session auto-create, dispatch call, loading/error states + 13 vitest tests (target was ~11) | ✓ SHIPPED (`29a3aa0`) |
| C5.2 | `BridgeResultPanel` component — answer text render, "View in asset library" link, copy button (shadcn `CopyButton` pattern) + 5 vitest tests | ✓ SHIPPED |
| C5.3 | Pro+ tier gate at route level — hide form, render `BridgeUpgradeNudge` panel for Starter workspaces + 3 vitest tests | ✓ SHIPPED |
| C5.4 | Strict SPA-UI dogfood (real browser, real the sibling project, real Asset persistence round-trip) + arc-close handoff | ¼ session |

Total: ~1 session if C5.1 lands cleanly. C5.2 + C5.3 are small
enough to fold together if C5.1 leaves headroom.

C5.1 is the critical path. C5.2 and C5.3 are parallelizable
against C5.1's `useDispatchBridgeTool` hook once the form ships.
C5.4 is the acceptance gate.

---

## API surface

**No new endpoints.** C5 consumes:

| Verb | Path | Purpose |
|---|---|---|
| GET | `/api/engine_connections/` | Check whether workspace has any enabled connection; if not, render "engine not configured" state |
| POST | `/api/realtime_sessions/` | Create DRAFT container (auto, one-click) |
| POST | `/api/realtime_sessions/<id>/invoke_tool/` | Dispatch the bridge tool |
| GET | `/api/workspace/assets/?role=bridge_answer` | Deep-link target for "View in asset library" |

DRAFT session create body (minimal):

```json
{
  "spokesperson": "<uuid>",
  "provider": "runway",
  "tools": ["consult_engine", "query_spider_data", "agent_consult"]
}
```

Response state stays `DRAFT` (no media-engine session created because
the SPA does not follow up with `start_session`).

Dispatch body:

```json
{
  "tool_name": "consult_engine",
  "args": { "question": "<operator input>" }
}
```

Dispatch response (success):

```json
{
  "state": "succeeded",
  "invocation_id": "<uuid>",
  "tool_name": "consult_engine",
  "cost_micros": 5000,
  "result": {
    "asset_id": "<uuid>",
    "event": "<avatar narration hint>",
    "answer": "<text answer>"
  },
  "error_message": ""
}
```

---

## SPA surface

### Route

`web/src/routes/workspace/tools.tsx` — registered inside the
workspace fabric shell (F2 nav pattern). Sibling to
`workspace/knowledge.tsx`.

### Nav integration

Per F0 rule 7 (stable nav rail post-F2), C5 does **not** add a new
top-level nav item. Discovery via:

- Sub-link on the workspace dashboard (F1) — "Ask your engine"
  card in the tool row.
- Optional breadcrumb link from `/recipes` (defer to C5.2 polish).

### Component tree

```
routes/workspace/tools.tsx
├── useEngineConnections()          // EB.4 hook, reused
├── useWorkspaceSpokespeople()      // existing hook
├── useDispatchBridgeTool()          // NEW in C5.1
│   ├── ensureDraftSession()         // page-scoped memo
│   └── invokeTool()
├── <BridgeToolForm>                 // NEW in C5.1
│   ├── tool picker (Radix Select via shadcn)
│   │   └── option label format: "consult_engine — Pro · ~$0.005"
│   │       (tier + cost surfaced inline; partial P3 4.4 coverage)
│   ├── spokesperson picker
│   ├── question textarea
│   └── submit button (loading state via TanStack Query)
├── <BridgeResultPanel>              // NEW in C5.2
│   ├── answer text (formatted)
│   ├── <CopyButton>                 // shadcn pattern
│   └── link to /workspace/assets/?role=bridge_answer&highlight=<asset_id>
└── <UpgradeNudge>                   // NEW in C5.3, Starter-only
    ├── "Engine bridge is a Pro+ feature"
    └── link to /settings/billing
```

### State machine

`idle → dispatching → succeeded | failed → idle`

No pending-approval branch — all v1 bridge tools cost under
threshold, so `_execute_inline` returns SUCCEEDED synchronously.
If a future tool exceeds threshold, dispatch response
`state: "awaiting_approval"` would surface here — behavior TBD
per Q-c5-7 (deferred, not v1).

---

## Test plan

### Backend

**No new backend tests.** All consumed surfaces are already
covered by:

- R7.0 dispatch tests (22 tests, `apps/realtime/tests/test_dispatch.py`)
- EB.2 resolver tests (15 tests, `apps/realtime/tests/test_engine_bridge.py`)
- EB.3 viewset tests (10 tests, `apps/realtime/tests/test_engine_connections_viewset.py`)
- C3 Asset persistence tests (in bridge-tool executor tests)

### SPA vitest

Target: ~18 new tests across C5.1–C5.3.

**C5.1 — form + dispatch (~11 tests):**
- Route renders when authenticated + Pro+ tier
- Route redirects on unauthenticated
- Tool picker options populated
- Tool picker option labels include tier + cost hints (partial P3 4.4)
- Spokesperson picker populated from workspace
- Submit disabled while question empty
- Submit fires `POST /api/realtime_sessions/` on first invocation
- Submit reuses DRAFT session on second invocation (no re-create)
- Submit fires `POST .../invoke_tool/` with correct body shape
- Loading state renders spinner
- Error state renders error message

**C5.2 — result panel (~5 tests):**
- Answer text renders (basic markdown supported via existing utility)
- Copy button copies answer to clipboard
- "View in asset library" link points to correct URL
- Panel does not render before dispatch completes
- Multiple sequential dispatches update the panel

**C5.3 — tier gate (~3 tests):**
- Starter workspace sees `UpgradeNudge`, not the form
- Pro workspace sees form
- Agency workspace sees form

### E2E (Playwright, C5.4 dogfood)

- Fresh Pro workspace signup
- Navigate `/workspace/tools`
- Fill form with spokesperson + `consult_engine` + question
- Submit → assert answer text appears in result panel
- Click "View in asset library" → assert navigation to
  `/workspace/assets/?role=bridge_answer` with the new asset visible
- Repeat with `query_spider_data` and `agent_consult`
- Starter workspace at same route → assert `UpgradeNudge` renders

### Dogfood (C5.4)

**Real browser + real the sibling project + real Asset persistence.**

Prerequisites:
- Fresh Pro workspace with `EngineConnection` row pointing at live the sibling project
- SPA `:5174`, Django `:8010`, media-engine `:8001` (`runway_mock=true`),
  Postgres `:5434`, Redis `:6381`, the sibling project Daphne `:8000`

Evidence to capture at `docs/production-readiness/dogfood-c5/`:
- Preflight snapshots (SPA build sha, engine connection ping)
- Screenshot: form fill + submit
- Screenshot: result panel with real answer
- Screenshot: asset library filtered to `role=bridge_answer`
- SQL query: `SELECT id, workspace_id, role, created_at FROM assets_asset
  WHERE role='bridge_answer' ORDER BY created_at DESC LIMIT 5`

Success criterion: three dispatches (one per tool) produce three
`Asset(BRIDGE_ANSWER)` rows scoped to the correct workspace, all
visible in the asset library, all with non-empty answer text.

---

## Out of scope (v1)

- **Pre-submit cost estimation.** Costs are negligible; the
  estimated-vs-actual confusion is a real UX hazard. Q-c5-6.
- **Client-side question history dropdown.** Server-side Assets
  cover this need. Q-c5-5.
- **Tool approval modal for bridge tools.** All three tools cost
  ≈ $0.005, under the $0.05 threshold. If a future bridge tool
  crosses threshold, R8.1's `ToolApprovalModal` is reusable.
- **Multi-turn conversation UI.** Each invocation is single-shot.
  Multi-turn belongs in the realtime avatar surface, not here.
- **Custom `args` beyond `question` string.** Q-c5-4 accepted a
  simple textarea; JSON editor for advanced args is a v1.1 polish.
- **Engine-selector dropdown when multiple `EngineConnection`
  rows exist.** v1 assumes one enabled row per workspace (EB
  rule 6 makes this explicit). Multi-engine UI is a v2 concern.
- **Full tool catalog list-view with `last-invoked` column.** C5
  surfaces tier + cost inline on the picker (partial P3 4.4);
  the full catalog surface + last-invoked metadata belongs in a
  follow-on slice once P3 4.6 (`RealtimeToolInvocation` activity
  feed) has the query surface to source last-invoked from.

---

## Open questions

All six resolved D-verdict 2026-07-22 (SESSION 225 scope-lock ratification):

| ID | Question | Resolution |
|---|---|---|
| **Q-c5-1** | Live realtime session or DRAFT-only? | DRAFT-only. The whole point of C5 is sidestepping WebRTC. Codified in contract rule 2. |
| **Q-c5-2** | Auto-create DRAFT session or make operator pick one? | Auto-create, reuse within page session. Codified in contract rule 5. |
| **Q-c5-3** | Gate `agent_consult` further than others? | No. Same Pro+ tier, same cost. Codified in contract rule 4. |
| **Q-c5-4** | Copy button on answer? | Yes. shadcn `CopyButton` pattern. |
| **Q-c5-5** | Question history dropdown? | No in v1. Assets already persist. Codified in contract rule 6. |
| **Q-c5-6** | Cost estimate before submit? | No. Costs negligible; avoid estimated-vs-actual confusion. Codified in contract rule 6. |

One deferred:

| ID | Question | Status |
|---|---|---|
| **Q-c5-7** | If a future bridge tool exceeds the $0.05 approval threshold, how does C5 render the approval modal? | Deferred — no v1 tool crosses threshold; R8.1's `ToolApprovalModal` is reusable when needed. |

---

## Change log

| Date | Change | Commit |
|---|---|---|
| 2026-07-22 | C5.0 scope lock proposed (SESSION 225). Seven contract rules + five slices. Six Q-c5-N resolved, one deferred. | pending |
| 2026-07-22 | Roadmap mapping clarified — C5 = full P3 4.5 + partial P3 4.4 (inline tier+cost on picker; full catalog + last-invoked deferred to follow-on). D-verdict same session. | pending |
| 2026-07-22 | Rule 4 corrected during C5.1 opening — actual per-tool costs are 5k/5k/7.5k micros (agent_consult is +50%); prior "same cost" phrasing was inaccurate but "all under approval threshold" invariant holds. Also documented the misleading `tier_required="starter"` on the backend tool spec — effective tier is Pro+ via EB resolver rule 8. | pending |
| 2026-07-22 | C5.1 shipped — SPA `/workspace/tools` route + `tools.ts` catalog + 13 vitest tests. 491/491 SPA tests pass; type-check clean. Placeholder result panel included (C5.2 replaces with polished BridgeResultPanel + copy button). Placeholder upgrade nudge inline in route (C5.3 replaces with dedicated component). | `29a3aa0` |
| 2026-07-22 | C5.2 shipped — `BridgeResultPanel` extracted at `web/src/components/bridge-result-panel.tsx` with answer render + shadcn-pattern copy button (`tools-result-copy`) + "View in asset library" link. Placeholder deleted from `tools.tsx`; existing C5.1 testids preserved (`tools-result-panel` / `tools-result-answer` / `tools-result-asset-link`) so the tools.test.tsx suite passes untouched. 5 new vitest tests (496/496 pass; 491 → 496). Markdown-lite deferred — no SPA-side utility exists and adding one exceeded C5.2's budget; whitespace-pre-wrap covers the common case. C5.3 next. | `0308363` |
| 2026-07-22 | C5.3 shipped — `BridgeUpgradeNudge` extracted at `web/src/components/bridge-upgrade-nudge.tsx`. Inline Starter-tier branch deleted from `tools.tsx`; `tools-upgrade-nudge` testid preserved so tools.test.tsx tier-gate cases (Starter / Pro / Agency) pass untouched. New testid `tools-upgrade-nudge-cta` pins the settings link. 3 new vitest tests (499/499 pass; 496 → 499). CTA points at `/settings/engine-connections` — scope's `/settings/billing` was aspirational and no such SPA route exists today; noted inline for future refactor. C5.4 (dogfood + arc-close) next. | `bba0796` |
| 2026-07-22 | **C5.4 dogfood round 1 — F-09 (Sev-1) surfaced.** Attempted `POST /api/realtime_sessions/` from the SPA-equivalent code path (Django test client) unconditionally called `MediaEngineClient.realtime_document_create` + `realtime_session_create`, landing the session at `status=ready` with real Runway spend ($0.14). Contract rule 2 architecturally violated. Dogfood halted; incident session ended. Full evidence at `docs/production-readiness/dogfood-c5/`. | pending |
| 2026-07-22 | **F-09 fixed (F-09-A) + C5.4 dogfood round 2.** `draft_only=true` body flag added to `POST /api/realtime_sessions/`; backend skips media-engine calls + Runway-cost tier gates; SPA `tools.tsx` sends the flag; `tools.test.tsx` asserts it. 3 broker regression tests (`test_broker.py`: 18 → 21 pass; total Django 1461+ → 1464+); SPA 499/499. Round-2 dogfood verified end-to-end: 4 draft-only sessions all `status=draft`, `provider_session_*=""`, `cost_actual=0`; CREATE latency 12,387ms → 151ms. **`consult_engine` verified end-to-end** — real the sibling project round-trip, real `Asset(BRIDGE_ANSWER)` persisted. **F-10 (Sev-1) surfaced** on same dogfood — `query_spider_data` requires `topic`, `agent_consult` requires `agent_name`; C5.1 hard-codes `{args:{question}}`. 2 of 3 tools non-functional through the SPA form. C5.4 arc close deferred pending F-10 ratification. | `891de34` |
| 2026-07-22 | **F-10-C shipped — v1 SPA picker narrowed to `consult_engine` only.** `web/src/lib/api/tools.ts` catalog drops `query_spider_data` + `agent_consult` (both remain backend-registered; SPA-side exclusion only). `tools.test.tsx` option-count assertion updated to expect exactly `["consult_engine"]`; the "$0.0075 delta" assertion dropped since only one tool is visible. Contract rule 4 rewritten to match. Follow-on slice C6 (candidate) queued to ship a per-tool fields renderer (F-10-B pattern) + `agent_consult` agent-picker UX; C6 re-enables the other two. C5.5 (this slice) unblocks C5.6 (browser passes 1 + 4 + 5 + arc close). | pending |
| 2026-07-22 | **F-12 (Sev-1) surfaced during C5.6 pass 1.** A single browser click at `/workspace/tools` provisioned a real Runway realtime session ($1.01, 12.5 min). SPA HEAD sent `draft_only=true` correctly + regression tests passed on HEAD — but the running Django runserver held pre-F-09-A `views.py` in memory (`--noreload` started 15:09 local; F-09-A landed 17:54 local; click at 18:17 local). Twin finding F-11 (Sev-2): tools-page dispatch does NOT persist `Asset(BRIDGE_ANSWER)`, unlike R8's realtime path. Evidence at `docs/production-readiness/finding-f12-draft-only-regression/`. | pending |
| 2026-07-22 | **P1 2.8-a — F-12 localization.** Root cause H5 (stale `--noreload` runserver) — not any of the original H1-H4 hypotheses. Localized entirely from process timestamps + Django access log + F-09-A regression tests all passing on HEAD. Second orphan session (`5bd03800…`, $1.12) discovered live and ended via two-step teardown. Combined attributable spend: $2.13. F-12 §7 documents the full walk-through + refutes R9's Runway 5-min cap assumption a second time. | pending |
| 2026-07-22 | **P1 2.8-b (F-12 fix) shipped — server default flipped to DRAFT.** `POST /api/realtime_sessions/` no longer defaults to real-mode. New body flag `real_mode: true` is the only way to get a paid session. Backend: `views.py::create` inverts the default; `draft_only=true` retained as explicit intent; `real_mode + draft_only` both true → 400. Tests: 3 F-09-A regression tests + 3 new P1 2.8-b tests (`test_broker.py`: 21 → 23 pass; 6 existing tests updated to send `real_mode: true`). SPA: `talk.tsx` (R8) opts in explicitly; `CreateSessionInput.real_mode?: boolean`; `talk.test.tsx` pins the R8 payload; C5 tools.tsx unchanged. Contract rule 2 rewritten to note server-enforcement. Kills the H5 recurrence class: a future stale runserver or missing client flag now defaults to $0 spend rather than $$$. | pending |
