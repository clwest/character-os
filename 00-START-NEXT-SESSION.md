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
> breakdown). **R1-R9 shipped; R10 (drift verifier) is the last R slice.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_156_R9_COST_GOVERNANCE.md`.

---

## SESSION 156 outcome — milestone doc refresh + R9 cost governance backend

Two-phase session:

**Phase 1 — milestone doc refresh** (`a632aef`).
After R8 closed in SESSION 155, the narrative anchor
(`WHAT_IT_IS.md`) was 9 sessions stale (`last_revised:
SESSION 146`) and TRUST_CALIBRATION ended at SESSION
147's drift-audit entry. Refreshed both:
* `WHAT_IT_IS.md` — frontmatter bumped to SESSION
  155 / covers 106-155; "three parallel arcs"
  framing → "four parallel arcs (three complete,
  R-arc operator-visible)" with status table
  pointing at INVENTORY + start-here as canonical
  sources for per-slice detail; K/V/F/R arc sections
  refreshed.
* `TRUST_CALIBRATION.md` — 4 new entries promoted
  from per-session handoffs: R7+R8 sub-slicing
  discipline, sendClientEvent-doesn't-exist,
  jest-dom type-vs-runtime drift, fake-timer
  double-count.

**Phase 2 — R9 cost governance backend** (`d33b8cf`).
Closes the hardcoded-constants gap from R8.1 + R8.2.

| Commit | What it shipped |
|---|---|
| `a632aef` | docs: refresh WHAT_IT_IS for SESSIONS 148-155 + 4 TRUST_CALIBRATION entries |
| `d33b8cf` | R9 feat — cost.py module + realtime_minutes_per_month TIER_LIMITS + check_realtime_minutes_budget + broker cost stamps + cost_estimate endpoint + SPA useRealtimeCostEstimate hook + IdlePanel "X of Y min left" hint + 18 backend tests + 2 SPA tests |
| (this commit) | SESSION 156 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

**Three cost-governance layers now all active**:

1. **Per-workspace monthly minutes budget** —
   starter=30, pro=120, agency=unlimited. New
   `check_realtime_minutes_budget` fires alongside
   R3's session-count gate.
2. **Per-session length cap** — provider 5 min
   (Runway-enforced); CostTicker visualizes.
3. **Per-tool approval threshold** — R7.0
   ($0.05).

R8.1's IdlePanel cost forecast + R8.2's CostTicker no
longer use hardcoded constants — both pull from the
new `useRealtimeCostEstimate` hook backed by `GET
/api/realtime_sessions/cost_estimate/`. IdlePanel
gains a "X of Y min left this month" hint pill for
capped tiers.

**Test totals**: Django **659** (641 → 659, +18 R9).
SPA vitest **37** (35 → 37, +2 R9). SPA build clean.

**R-arc state: R1-R9 done.** R10 (multi-provider
drift verifier) is the last R slice — small
one-test follow-up.

Full handoff at
`docs/handoffs/SESSION_156_R9_COST_GOVERNANCE.md`.

### FIRST THING (SESSION 157): R10 (multi-provider drift verifier)

One-test slice. Verifies the provider abstraction
(scope-lock §"Provider abstraction" + R2's
`RealtimeProvider` Protocol) stays honored as new
providers land.

* New `apps/realtime/tests/test_r10_provider_drift.py`
  — imports the provider registry from
  `media-engine/app/services/realtime_provider/`,
  asserts every method on the Protocol is
  implemented by Runway + the mock provider.
* Fails when a new method lands on the Protocol
  without a Runway implementation, OR when a future
  provider lands without all methods.
* No new code beyond the test.

Estimated scope: ~30 minutes. Closes R-arc fully.

### After SESSION 157

* **First marketing video** — flips RUNWAY_FORCE_MOCK
  off, walks through a real session with a cast
  spokesperson against real Runway. Highest-value
  demonstrable output. Operator-mediated.
* **Drift-prevention backlog items 2 + 3** —
  auto-bump `last_revised` on handoff write +
  TRUST_CALIBRATION promotion at handoff-write.
  Context-kit work; small.
* **F8.1 — K10 seed corpus** (blocked on
  operator-authored markdown).
* **K7.x — YouTube ingest fix.**
* **K6.3 / K7.1 / W11.1.**

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
  F8.1 queued.
- **Video composition arc (V0-V15). COMPLETE**.
- **Workspace fabric arc (F0-F10). COMPLETE**.
- **Realtime avatar arc (R0-R10).** **R1-R9 shipped**
  (SESSIONS 146-156). R10 (drift verifier) is the
  last R slice.

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
| R8.0-R8.2 | SPA realtime UX                           | DONE (SESSIONS 153-155) |
| R9 | Cost governance backend                          | DONE (SESSION 156) |
| R10 | Multi-provider drift verifier (last R slice)    | Next (SESSION 157) |
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

1. **R10 — Multi-provider drift verifier** (one-test
   slice; closes R-arc fully).
2. **First marketing video** — exercises the whole
   stack against real Runway. Highest-value
   demonstrable output.
3. **Drift-prevention backlog item 2 + 3.**
4. **F8.1 — K10 seed corpus** (blocked).
5. **K7.x — YouTube ingest fix.**
6. **K6.3 — Brief length cap.**
7. **K7.1 — Cost telemetry surface.**
8. **W11.1 — Edit-spokesperson modal.**
9. **Voice preset audit.**
10. **E2e detritus cleanup.**
11. **OpenAI client factory port.**
12. **Cast sync command.**
13. **Stuck-row janitor.**
14. **Act-Two performance capture.**
15. **`lesson` video kind.**
16. **Real Google OAuth + dj-stripe.**
17. **Allauth legacy-settings cleanup.**
18. **smoke_voice / smoke_avatar transaction discipline.**
19. **INVENTORY working-tree-dirty flag fix.**
20. **Brand Identity v2 + dark mode.**

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
python -m pytest                              # 659 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 37 vitest tests
pnpm e2e                                      # Playwright (in mock mode only)
```

---

## AI / assistant context

- **Last session: SESSION 156 — R9 shipped + doc
  refresh.** Cost governance backend closes the
  hardcoded-constants gap. Three cost layers all
  active. 659 backend + 37 SPA tests pass.
- **Calibration carried forward:**
  - **Milestone-level doc refresh has its own
    cadence** — at arc closures, pair the
    slice-close commit with a refresh of WHAT_IT_IS
    + TRUST_CALIBRATION. Per-slice discipline
    handles INVENTORY + design docs + handoffs;
    these don't.
  - **Match exception payload shape when adding a
    gate to an existing gate's surface** — R9's
    `realtime_minutes_limit_reached` mirrored R3's
    `realtime_session_limit_reached`. SPA needs
    zero changes.
  - **Hardcoded UI constants that match a backend
    default are a smell** — placeholder is a TODO,
    not a contract. The backend endpoint that
    supplies the real value should ship before the
    second consumer of the constant.
  - **Fake timers double-count** (SESSION 155).
  - **SDK features are hypotheses until exercised**
    (SESSION 155).
  - **Type-system + runtime drift on testing-library**
    (SESSION 154).
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Doctor is the drift tool** (SESSION 151).
  - **Pyright in this repo is noisy on Django/DRF.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **R10 = 1 more session to close R-arc fully.** One
  test verifying the provider abstraction.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end.
