---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`
> (5 verbs shipped after SESSION 125; ~12 per-primitive verbs
> sequenced V3-V14 in the video composition arc).
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
> breakdown). **R1-R6 shipped; R7-R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_148_R6_MEMORY.md`.

---

## SESSION 148 outcome — R6 cross-session memory shipped

Single-slice session. R6 closed the realtime arc's
memory loop: prior `Asset(TRANSCRIPT)` rows from R5
get summarized via gpt-5-mini and projected into the
next session's Runway document as a
`## Recent Conversations` section. Returning-operator
warmth lands without any new persistence.

| Commit | What it shipped |
|---|---|
| `dbb22e0` | `realtime_memory.py` (`compose_session_memory`) + `realtime_document.py` extension + 14 R6 tests + 3 `ALLOWED_FILES` whitelist additions + `REALTIME_AVATAR_V1.md` slice-table + change-log update |
| (this commit) | SESSION 148 handoff + this start-here rewrite + back-filled SHA in design doc + CLAUDE.md Phase 4 row bump |

**Test totals**: Django 560 → 574 (+14). No new
media-engine routes; no migrations; no new Celery
tasks. Sixth `*_FORCE_MOCK` flag added —
`REALTIME_MEMORY_FORCE_MOCK` joins the family
(`RUNWAY`, `EMBEDDING`, `RENDER_SCRIPT`, `SERPER`,
`CONVERSATION_REPLY`, now this one).

**Contract rule alignment**: rules 1 (workspace
anchor) + 4 (Asset shape) + 5 (one-way knowledge) +
9 (mock mode) all preserved. **Q-r-7 resolved**:
returning-operator threshold = 1; any prior transcript
triggers projection. No operator opt-out in v1
(deferred to R8 SPA settings).

Full handoff at
`docs/handoffs/SESSION_148_R6_MEMORY.md`.

### FIRST THING (SESSION 149): inventory regen revisit + R7

Two ordered items:

1. **Revisit INVENTORY regen.** Operator's end-of-148
   ask. R6 didn't change models / routes / Celery
   tasks, so the CLAUDE.md regen trigger didn't fire.
   But INVENTORY's `git_sha` lags HEAD by ~5
   docs-only commits (3 from SESSION 147 + 2 from
   SESSION 148). Run `python manage.py inventory`
   from `shell/`; if the diff is purely `git_sha`,
   commit anyway as `docs: bump INVENTORY git_sha`
   (no model/route changes). If the diff also
   surfaces the two known generator bugs (Celery-task
   undercount; working-tree-dirty flag) that
   SESSION 147 deferred, **defer fixing them to
   backlog item 5** but commit the regen as-is so
   `git_sha` rolls forward.

2. **R7 (tool catalog).** Six workspace-scoped
   tools the avatar can invoke mid-session.
   `RealtimeToolInvocation` row already exists
   (R1). R7 ships:
   * `apps/realtime/tools/` registry + per-tool
     handlers (workspace-scoped routing).
   * WebRTC data-channel event handler in the broker.
   * Approval-threshold modal contract (server-side
     shape only; SPA in R8).

   Resolves Q-r-2 (tool rejection narration) +
   Q-r-4 (per-workspace tool catalog overrides).

### After SESSION 149

**Option A — R8 (SPA, the "feels real" moment).**
`/spokespeople/:id/talk` route +
`@runwayml/avatars-react` integration + cost
forecasting UI + tool-approval modal. Backend fully
ready (R1-R6 done, R7 lands next session). R8 is
where the realtime arc becomes operator-visible.

**Option B — R9 (cost governance).** Per-workspace
minutes budget + live cost ticker. R3's tier-limit
gate enforces session counts; R9 adds the
minutes-budget enforcement.

**Option C — F8.1 / K7.x.** Smaller follow-ups
(seed corpus + YouTube ingest fix).

### Drift-prevention backlog status (from SESSION 147)

The 5-item backlog the SESSION 147 drift audit
produced. Item 1 was handled by a **parallel
context-kit agent** during SESSION 148 (operator
flagged mid-session that a separate Claude instance
was working on the `context-kit drift` subcommand).
Once that lands, character-os will integrate it via
its own slice — update `CLAUDE.md`'s session-start
drift sweep to call `context-kit drift` instead of
the four manual checks.

Remaining items:

* **(2)** Auto-bump `last_revised` on handoff write
  — `context-kit handoff write <N>` subcommand.
* **(3)** Promote calibration entries to
  TRUST_CALIBRATION at handoff-write (depends on 2).
* **(4)** Codify session-start drift sweep in
  CLAUDE.md to call the new subcommand (10 min;
  lands after item 1).
* **(5)** Fix INVENTORY's two known generator
  bugs (Celery-task undercount, working-tree-dirty
  handling).

---

## SESSION 147 outcome — context-kit drift audit + boot fixes

Pre-feature housekeeping pass. Operator opened the
session asking for a drift audit before R6. Audit
found **5 drift items** — all closed in-session, no
feature work shipped.

Single commit: **`ac59aa9`** (`docs: SESSION 147 boot
— context-kit drift audit fixes`). Full handoff at
`docs/handoffs/SESSION_147_DRIFT_AUDIT.md`.

The handoff also defined a 5-item drift-prevention
backlog (now tracked above with item 1 in flight).

---

## SESSION 146 outcome — realtime arc R1-R5 buildout

Five sequential R-arc slices closed in one extended
session. The realtime avatar arc (scope-locked
SESSION 142) gained its first end-to-end smoke path:
live sessions work, grounded in workspace knowledge,
with post-session transcripts persisted as Assets.

* **R1** (`9299dcf`) — `apps.realtime` schema +
  cross-workspace guards + isolation test. 14 tests.
* **R2** (`e8eb7d1`) — Media-engine provider
  abstraction + Runway impl + mock + two endpoints.
  18 tests.
* **R3** (`26378e9`) — Django broker
  `/api/realtime_sessions/` + tier-limit gate
  (`realtime_sessions_per_month`: starter=5, pro=20,
  agency=unlimited) + state machine + 4-layer
  `provider_session_key` secrecy enforcement.
* **R4** (`6521451`) — Knowledge → Runway document
  bridge. `compose_realtime_document` + media-engine
  `/internal/realtime_documents/` + broker
  integration. K0 privacy holds end-to-end.
* **R5** (`885508d`) — Transcript capture. Runway
  `fetch_transcript` + media-engine
  `GET .../transcript/` + Celery task creates
  `Asset(TRANSCRIPT)` + wires
  `RealtimeSession.transcript_asset`.

Full handoff at
`docs/handoffs/SESSION_146_REALTIME_BUILDOUT.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live in
real-mode (SESSION 136). Knowledge-layer scope-locked
(SESSION 137) — `docs/design/KNOWLEDGE_LAYER.md` is the new
contract.

**Phase 4 (four arcs in flight, two complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped. K10
  (onboarding seed) → F8.1 queued (blocked on
  operator-authored markdown). K7.x YouTube ingest
  fix queued.
- **Video composition arc (V0-V15). COMPLETE**
  (SESSIONS 142-144). 13 step primitives, 18 starter
  recipes, SPA recipe gallery live at `/recipes`.
- **Workspace fabric arc (F0-F10). COMPLETE**
  (SESSION 144). F8.1 K10 seed corpus queued.
- **Realtime avatar arc (R0-R10).** R1-R6 shipped
  (SESSIONS 146 + 148). R7 (tool catalog) is next.
  R8 (SPA) is the operator-visible moment. R9 +
  R10 are smaller follow-ups.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0-K9 | Knowledge layer (paste/PDF/URL/search + render integration + conversation pipeline) | DONE (SESSIONS 137-145) |
| V0-V15 | Video composition arc + recipe gallery     | DONE (SESSIONS 142-144) |
| F0-F10 | Workspace fabric arc                       | DONE (SESSION 144) |
| R0 | Realtime avatar arc — scope lock                | DONE (SESSION 142) |
| R1 | RealtimeSession + RealtimeToolInvocation schema + isolation tests | DONE (SESSION 146) |
| R2 | Media-engine `/internal/realtime_sessions/` + provider abstraction | DONE (SESSION 146) |
| R3 | Django broker (`/api/realtime_sessions/`) + tier-limit gate | DONE (SESSION 146) |
| R4 | Knowledge → Runway document bridge (compose + push + persist citations) | DONE (SESSION 146) |
| R5 | Transcript capture (Asset(TRANSCRIPT) on session end) | DONE (SESSION 146) |
| R6 | Cross-session memory projection (`compose_session_memory` → `## Recent Conversations` in R4 doc body) | DONE (SESSION 148) |
| R7 | Tool catalog (6 tools, workspace-scoped) + WebRTC data-channel dispatch + approval-threshold modal contract | Next (SESSION 149) |
| R8 | SPA `/spokespeople/:id/talk` + `@runwayml/avatars-react` + cost forecasting UI + tool-approval modal | Queued |
| R9 | Cost governance: per-workspace minutes budget + live cost ticker | Queued |
| R10 | Multi-provider abstraction hardening (drift verifier test) | Queued |
| K6.3 | Brief length cap in script synthesis           | Queued |
| K7.1 | Per-chunk cost telemetry surface in UI         | Queued |
| K10 | Onboarding seed                                | Queued (→ F8.1 needs operator-authored markdown) |
| W11.1 | Edit-spokesperson modal                      | Queued |

**Cast roster in workspace `admins-workspace`:**

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - Sasha the Raccoon (sales) — id `79d48883-...`
  - Donny the Sloth (user stories) — id `f30b2980-...`
  - Maya the Panda (educator) — id `9410f23f-...`

Cast can render *informed* videos (K6 / SESSION 139),
hold text conversations (K8/K9 / SESSION 145), AND
hold live realtime sessions grounded in workspace
knowledge that remember prior conversations (R1-R6 /
SESSIONS 146 + 148).

---

## Queued investigations (priority-ordered)

1. **R7 — Tool catalog** (next session's primary slice).
2. **R8 — SPA realtime route.**
3. **R9 — Cost governance.**
4. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
5. **K7.x — YouTube ingest fix**
   (`project_youtube_ingest_silent_failure.md`).
6. **K6.3 — Brief length cap.**
7. **K7.1 — Cost telemetry surface.**
8. **W11.1 — Edit-spokesperson modal.**
9. **First marketing video** — attach Character-OS
   knowledge to the admin workspace, render Sasha
   actually speaking a real script.
10. **Voice preset audit** — listen to the four cast
    members with real renders.
11. **E2e detritus cleanup** — `Workspace.objects.filter(slug__startswith='e2e-').delete()`.
12. **OpenAI client factory port** — u-d-b's
    `core/services/openai_client_factory.py`
    centralises timeout/retry config. R6 brings the
    Responses-API call count to 3 (K6 + K9 + R6);
    factory pattern starts paying off.
13. **R10 — multi-provider hardening.**
14. **Cast sync command.**
15. **Stuck-row janitor.**
16. **Act-Two performance capture.**
17. **`lesson` video kind.**
18. **Real Google OAuth + dj-stripe.**
19. **Allauth legacy-settings cleanup.**
20. **smoke_voice / smoke_avatar transaction discipline.**
21. **Drift verifier** (the original — superseded
    in spirit by `context-kit drift` once that lands).
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

**Six force-mocks now exist** (after R6 SHIPPED in
SESSION 148). To run Celery + Django with all six
mocks active for fully-offline local dev:

```bash
EMBEDDING_FORCE_MOCK=1 \
RENDER_SCRIPT_FORCE_MOCK=1 \
CONVERSATION_REPLY_FORCE_MOCK=1 \
SERPER_FORCE_MOCK=1 \
REALTIME_MEMORY_FORCE_MOCK=1 \
python manage.py runserver 8000

EMBEDDING_FORCE_MOCK=1 \
RENDER_SCRIPT_FORCE_MOCK=1 \
CONVERSATION_REPLY_FORCE_MOCK=1 \
SERPER_FORCE_MOCK=1 \
REALTIME_MEMORY_FORCE_MOCK=1 \
celery -A character_os worker --pool=solo
```

(The sixth flag — `RUNWAY_FORCE_MOCK` — lives in the
media-engine's environment, not Django's. Set it
when starting `uvicorn`.)

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
python -m pytest apps/realtime/tests/         # 65 tests (R1-R6)

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e
```

---

## AI / assistant context

- Last session: SESSION 148 — **R6 shipped**.
  Cross-session memory composes prior
  `Asset(TRANSCRIPT)` rows via gpt-5-mini → injects
  as a `## Recent Conversations` section in the R4
  document body. Returning-operator loop closes.
  574 backend tests pass. **Test count progression**:
  560 → 574 (+14).
- **Calibration carried forward:**
  - **Cross-arc isolation guards add 1-3 whitelist
    edits per new test file.** Budget that into
    slice plans rather than discovering at test-
    run time.
  - **Synthetic-budget tests should land with the
    smallest budget that asserts the drop.** Larger
    budgets accidentally pass.
  - **Cast is example data, not product shape.**
  - **OpenAI gpt-5 family uses the Responses API,
    not chat.completions.** R6 is the third
    Responses-API call site (after K6 + K9). Factory
    pattern from u-d-b starts paying off; port queued.
  - **AI drafts, human edits. Push back when framing
    looks wrong.** Convergence happens through
    pushback, not in spite of it.
- **R7 / R8 / R9 / R10 = ~4 more sessions for the
  realtime arc to close.** R7 + R8 together are
  the operator-visible moment.
- **Six force-mocks now exist.** Set all six (plus
  `RUNWAY_FORCE_MOCK` on the media-engine) for
  fully-offline local dev.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` section + per-slice doc
  updates required at session end (codified SESSION
  143; reinforced SESSION 147).
