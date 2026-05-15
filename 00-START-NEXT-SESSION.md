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
> breakdown). **R1-R6 + R7.0 + R7.1 + R7.2 shipped; R7.3, R8, R9, R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_151_R7_ASYNC.md`.

---

## SESSION 151 outcome — R7.2 async dispatch + render_video + INVENTORY fix

Single-slice session with one bundled bug fix. Three
things shipped under R7.2:

| Commit | What it shipped |
|---|---|
| `e8564f9` | R7.2 feat — QUEUED status (migration `0003`) + generic `execute_tool_invocation` Celery task + dispatcher async wiring + approve enqueues Celery + `render_video` tool ($0.08, over threshold) + INVENTORY Celery undercount fix (drift backlog item 5) + 14 tests + 2 ALLOWED_FILES additions |
| (this commit) | SESSION 151 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md updates (Phase 4 row + drift-sweep section pointing at `context-kit doctor`) |

**`attach_memory` split out to R7.3** (was originally
part of R7.2). Reason: end-to-end attach_memory requires
R6's query to widen — R6 currently filters by
`status=ENDED` which excludes the in-progress session's
transcript snapshot. R7.3 pairs R6.1 (R6 widen) +
`attach_memory` tool.

**Tool catalog now**:

| Tool | Tier | Cost | Sync/Async | Slice |
|---|---|---|---|---|
| `show_videos_tab` | starter | $0 | sync | R7.0 |
| `recall_knowledge` | starter | ~$0.001 | sync | R7.1 |
| `recall_recent_conversations` | starter | $0 | sync | R7.1 |
| `handoff_to_spokesperson` | pro | $0 | sync | R7.1 |
| `render_video` | starter | $0.08 | **async** | R7.2 |
| `attach_memory` | pro | TBD | async | R7.3 (queued) |

**Test totals**: Django 613 → 627 (+14). Migrations
50/50 → 51/51. INVENTORY Celery count correctly reads
**8** now (was 5 because of lazy autodiscovery).

**Drift sweep tool**: per operator clarification this
session, `context-kit doctor` IS the drift tool
(replaces what was originally scoped as a separate
`drift` subcommand). CLAUDE.md's session-start
drift-sweep section updated to point there.

**Stack restarted mid-session** at operator's request
after the SPA returned 502s — killed three stale
processes (Django May 14, Celery May 14, uvicorn May
15) + restarted fresh. New R7.0 + R7.1 + R7.2 routes
verified to respond (403 auth-required, not 404).

Full handoff at
`docs/handoffs/SESSION_151_R7_ASYNC.md`.

### FIRST THING (SESSION 152): R7.3 (`attach_memory` + R6.1 prerequisite)

Two parts paired in one slice:

**R6.1 — widen R6 to include in-progress sessions**.
Lean Option A: change R6's query from
`status=ENDED` to "any session with `transcript_asset`,
excluding the current session by pk." Crash-state
sessions surfacing in memory is acceptable (avatar
references a partial earlier conversation; SPA can
frame it as "earlier today").

**R7.3 — `attach_memory` tool**:

* Fires `fetch_transcript_for_session.delay(session_id)`
  on the CURRENT session (R5's existing task is
  idempotent and works on non-ENDED sessions).
* Async; cost ~$0.001.
* Pro tier (power-user feature — discrete checkpoints
  during long planning calls).
* Returns `{event: "memory_committed", asset_id, message}`.
* Resolves Q-r-8 (cross-session tool side effects —
  composition is idempotent + last-write-wins).

Estimated scope: ~10 new tests, no migrations, 1 new
tool, ~20 lines of R6 widen.

### After SESSION 152

* **R8 (SPA)** — `/spokespeople/:id/talk` route +
  `@runwayml/avatars-react` SDK + cost forecasting UI
  + tool-approval modal + live cost ticker. The
  operator-visible moment. After R7.3 lands, R8 ships
  against the complete 6-tool v1 catalog.
* **R9 (cost governance)** — per-workspace minutes
  budget + live cost ticker.
* **R10 (provider hardening)** — drift verifier test
  for the registry pattern.

### Drift-prevention backlog status

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | **Superseded** — operator clarified `doctor` IS the drift tool |
| 2 | Auto-bump `last_revised` on handoff write | Queued |
| 3 | Promote calibration entries to TRUST_CALIBRATION at handoff-write | Queued |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done SESSION 147; updated SESSION 151 to point at `doctor` |
| 5 | Fix INVENTORY's two known generator bugs | **Done SESSION 151** (Celery undercount fix). Working-tree-dirty flag still pending. |

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live
in real-mode (SESSION 136).

**Phase 4 (four arcs in flight, two complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped. K10 → F8.1
  queued. K7.x YouTube ingest fix queued.
- **Video composition arc (V0-V15). COMPLETE**
  (SESSIONS 142-144).
- **Workspace fabric arc (F0-F10). COMPLETE**
  (SESSION 144). F8.1 K10 seed corpus queued.
- **Realtime avatar arc (R0-R10).** R1-R6 + R7.0 +
  R7.1 + R7.2 shipped (SESSIONS 146-151). R7.3 is next.
  R8 (SPA) + R9 + R10 remain.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0-K9 | Knowledge layer end-to-end                    | DONE (SESSIONS 137-145) |
| V0-V15 | Video composition arc + recipe gallery     | DONE (SESSIONS 142-144) |
| F0-F10 | Workspace fabric arc                       | DONE (SESSION 144) |
| R0-R5 | Realtime arc (schema → broker → docs → transcripts) | DONE (SESSION 146) |
| R6 | Cross-session memory projection                | DONE (SESSION 148) |
| R7.0 | Tool dispatch foundation                       | DONE (SESSION 149) |
| R7.1 | Three sync tools + tier-aware filtering        | DONE (SESSION 150) |
| R7.2 | Async dispatch + `render_video` + INVENTORY fix | DONE (SESSION 151) |
| R7.3 | R6.1 R6 widen + `attach_memory` tool          | Next (SESSION 152) |
| R8 | SPA `/spokespeople/:id/talk` + SDK integration   | Queued |
| R9 | Cost governance: minutes budget + live ticker    | Queued |
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
hold text conversations (K8/K9 / SESSION 145), hold
live realtime sessions grounded in workspace knowledge
that remember prior conversations (R1-R6), invoke
five tools mid-session (R7.0 + R7.1 + R7.2 across
SESSIONS 149-151) including **`render_video` which
actually fires the V-arc composition chain via Celery**
(R7.2 / SESSION 151).

---

## Queued investigations (priority-ordered)

1. **R7.3 — `attach_memory` + R6.1 R6 widen** (next
   session's primary slice).
2. **R8 — SPA realtime route.**
3. **R9 — Cost governance.**
4. **Drift-prevention backlog item 2 + 3** (auto-bump
   `last_revised` + TRUST_CALIBRATION promotion).
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
14. **R10 — Multi-provider hardening.**
15. **Cast sync command.**
16. **Stuck-row janitor.**
17. **Act-Two performance capture.**
18. **`lesson` video kind.**
19. **Real Google OAuth + dj-stripe.**
20. **Allauth legacy-settings cleanup.**
21. **smoke_voice / smoke_avatar transaction discipline.**
22. **INVENTORY working-tree-dirty flag fix** (the
    other half of drift backlog item 5; not blocking).
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

**Session-start drift sweep** (per CLAUDE.md, updated
this session):

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

Doctor is the primary drift-detection tool. Manual
spot-checks remain for stale processes + INVENTORY
git_sha (categories doctor doesn't yet cover).

**Six force-mocks** (RUNWAY on media-engine;
EMBEDDING + RENDER_SCRIPT + CONVERSATION_REPLY + SERPER
+ REALTIME_MEMORY on Django). Set all six for fully-
offline local dev.

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait
python -m pytest                              # 627 tests
python -m pytest apps/realtime/tests/         # 118 tests (R1-R6 + R7.0 + R7.1 + R7.2)

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e
```

---

## AI / assistant context

- **Last session: SESSION 151 — R7.2 shipped.** Async
  dispatch + `render_video` + INVENTORY Celery fix.
  Original R7.2 scope split: `attach_memory` → R7.3
  (needs R6.1 prerequisite). 627 backend tests pass.
  Migration 51/51.
- **Calibration carried forward:**
  - **Doctor is the drift tool**, not a separate
    `drift` subcommand. CLAUDE.md drift-sweep section
    updated to point at `context-kit doctor`.
  - **Splitting a scope-locked slice mid-
    implementation is fine** when dependencies
    surface late. Better than half-shipping.
  - **Fast bug fixes can ride feature commits** when
    the operator agrees + scope is small (R7.2's
    Celery undercount fix was ~3 lines, bundled
    naturally with the feat).
  - **Pyright in this repo is noisy on Django/DRF**
    — same false-positives every session
    (FK auto-attrs, UserManager.create_user, DRF
    queryset narrowing). Filter for novel ones.
  - **Cross-arc isolation guards add 1-3 whitelist
    edits per new test file.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **R7.3 / R8 / R9 / R10 = ~4 more sessions to close
  the realtime arc.** R7.3 closes the tool catalog at
  v1 spec (6 tools); R8 makes everything
  operator-visible.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end (codified SESSION 143;
  reinforced SESSION 147; honored SESSIONS 148-151).
