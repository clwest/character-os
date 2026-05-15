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
> breakdown). **R1-R6 + R7.0 + R7.1 shipped; R7.2, R8, R9, R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_150_R7_SYNC_TOOLS.md`.

---

## SESSION 150 outcome — R7.1 sync tools + tier-aware filtering

Single-slice session. R7.1 shipped three sync tools on
top of R7.0's dispatch foundation, plus tier-aware
filtering that resolves **Q-r-4** (per-workspace tool
catalog overrides).

| Commit | What it shipped |
|---|---|
| `611ae94` | R7.1 feat — three sync tools + ToolSpec.tier_required + tier filtering + dispatcher defense-in-depth + `get_workspace_tier` helper + 17 tests + 3 ALLOWED_FILES + R7.0 test rename |
| (this commit) | SESSION 150 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row bump |

**Tool catalog now**:

| Tool | Tier | Cost | Notes |
|---|---|---|---|
| `show_videos_tab` | starter | $0 | UI nav (R7.0) |
| `recall_knowledge` | starter | ~$0.001 | RAG against K2 |
| `recall_recent_conversations` | starter | $0 | per-session previews |
| `handoff_to_spokesperson` | **pro** | $0 | cross-spokesperson nav |

**Test totals**: Django 596 → 613 (+17). No new
migrations, Celery tasks, media-engine routes, or
force-mock flags. Q-r-4 resolved.

Full handoff at
`docs/handoffs/SESSION_150_R7_SYNC_TOOLS.md`.

### FIRST THING (SESSION 151): R7.2 (async tools via Celery)

Two async tools that share `is_async=True`:

1. **`render_video`** — fires a composition starter
   via Celery (default `talking_head`). Pro tier
   (subject to per-month video cap). Cost:
   ~$0.05-0.50 depending on starter + duration.
   **The threshold-crossing tool** — exercises
   R7.0's `awaiting_approval` flow end-to-end
   (only synthetic high-cost test tools have
   exercised it before).
2. **`attach_memory`** — mid-session memory commit.
   Pro tier. Pulls partial transcript from
   media-engine, composes via R6's
   `compose_session_memory`, pushes as a fresh
   Runway document, attaches to spokesperson.
   Cost: ~$0.001. Resolves **Q-r-8** (cross-session
   tool side effects — composition is idempotent +
   last-write-wins).

R7.2 makes the `queued` dispatch state load-bearing
(R7.0 wired it; only R7.2 fills in the Celery
dispatch + result-polling shapes).

**Bundle with R7.2**: drift-prevention backlog item 5
(INVENTORY Celery undercount fix). R7.2 adds 1-2 new
Celery tasks; the undercount in INVENTORY becomes
more obvious. ~30 minutes; either inline or as a
follow-up `docs:` commit after R7.2's INVENTORY regen
surfaces the wrong number.

Estimated scope: ~2 new Celery tasks, ~15 tests, no
migrations.

### After SESSION 151

* **R8 (SPA)** — `/spokespeople/:id/talk` route +
  `@runwayml/avatars-react` SDK + cost forecasting
  UI + tool-approval modal + live cost ticker. The
  operator-visible moment.
* **R9 (cost governance)** — per-workspace minutes
  budget + live cost ticker.
* **R10 (provider hardening)** — drift verifier test.

### Drift-prevention backlog status (from SESSION 147)

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | In flight (parallel context-kit agent) |
| 2 | Auto-bump `last_revised` on handoff write | Queued |
| 3 | Promote calibration entries to TRUST_CALIBRATION at handoff-write | Queued |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done SESSION 147 |
| 5 | Fix INVENTORY's two known generator bugs | **Recommend bundling with R7.2** |

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live
in real-mode (SESSION 136).

**Phase 4 (four arcs in flight, two complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped.
  K10 → F8.1 queued. K7.x YouTube ingest fix queued.
- **Video composition arc (V0-V15). COMPLETE**
  (SESSIONS 142-144). 13 step primitives, 18 starter
  recipes, SPA recipe gallery at `/recipes`.
- **Workspace fabric arc (F0-F10). COMPLETE**
  (SESSION 144). F8.1 K10 seed corpus queued.
- **Realtime avatar arc (R0-R10).** R1-R6 + R7.0 +
  R7.1 shipped (SESSIONS 146-150). R7.2 (async tools)
  is next. R8 (SPA) + R9 + R10 remain.

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
| R7.2 | Two async tools via Celery (`render_video`, `attach_memory`) | Next (SESSION 151) |
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
tools mid-session (R7.0 / SESSION 149), and **now use
RAG + recall prior sessions + suggest handoffs live**
(R7.1 / SESSION 150).

---

## Queued investigations (priority-ordered)

1. **R7.2 — Async tools** (`render_video` +
   `attach_memory`; next session's primary slice).
2. **Drift-prevention backlog item 5** — INVENTORY
   generator bugs. Bundle with R7.2.
3. **R8 — SPA realtime route.**
4. **R9 — Cost governance.**
5. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
6. **K7.x — YouTube ingest fix.**
7. **K6.3 — Brief length cap.**
8. **K7.1 — Cost telemetry surface.**
9. **W11.1 — Edit-spokesperson modal.**
10. **First marketing video.**
11. **Voice preset audit.**
12. **E2e detritus cleanup.**
13. **OpenAI client factory port** — three call sites
    now (K6 + K9 + R6); factory pattern starts paying
    off.
14. **R10 — Multi-provider hardening.**
15. **Cast sync command.**
16. **Stuck-row janitor.**
17. **Act-Two performance capture.**
18. **`lesson` video kind.**
19. **Real Google OAuth + dj-stripe.**
20. **Allauth legacy-settings cleanup.**
21. **smoke_voice / smoke_avatar transaction discipline.**
22. **Drift verifier (the original).**
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

**Six force-mocks** (RUNWAY on the media-engine;
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
python -m pytest                              # 613 tests
python -m pytest apps/realtime/tests/         # 104 tests (R1-R6 + R7.0 + R7.1)

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e
```

---

## AI / assistant context

- **Last session: SESSION 150 — R7.1 shipped.** Three
  sync tools + tier-aware filtering. Q-r-4 resolved.
  613 backend tests pass.
- **Calibration carried forward:**
  - **Tier as a defense-in-depth axis.** Catalog
    filter is the primary gate; dispatcher tier
    check is the safety net. Pattern matches V's
    workspace-scoped guards (view-layer filter +
    model `clean()`).
  - **Per-item permission metadata over per-bucket
    lists.** Each tool's `tier_required` lives with
    its other declarative fields. Avoids the coupling
    of `STARTER_TOOLS = [...]` / `PRO_TOOLS = [...]`
    style.
  - **Privacy tests at slice boundaries are cheap
    insurance.** Each new tool/endpoint that reads
    workspace-scoped data gets one
    `..._other_workspace_excluded` test. None caught
    a bug this session but the next refactor will.
  - **Over-scoped slices get sub-sliced at proposal
    time** (R7 → R7.0/R7.1/R7.2).
  - **Test fixtures touching singletons: snapshot +
    restore, not module-reload.**
  - **Pyright in this repo is noisy on Django/DRF.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **R7.2 / R8 / R9 / R10 = ~4 more sessions to close
  the realtime arc.** R7.2 + R8 together make the arc
  operator-visible with the full tool set.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end (codified SESSION 143;
  reinforced SESSION 147; honored SESSIONS 148-150).
