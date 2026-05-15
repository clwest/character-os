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
> breakdown). **R1-R6 + R7.0 shipped; R7.1, R7.2, R8, R9, R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_149_R7_FOUNDATION.md`.

---

## SESSION 149 outcome — R7.0 tool dispatch foundation

Single-slice session. R7 was scope-locked at SESSION
142 as one slice but proved too large for the
one-slice-per-session discipline calibrated in
SESSION 148. Sub-sliced into R7.0 / R7.1 / R7.2
(foundation / sync tools / async tools), matching
V15.0-V15.4. R7.0 shipped end-to-end.

| Commit | What it shipped |
|---|---|
| `646c492` | feat R7.0 — `tools/` registry + `show_videos_tab` tool + `dispatch.py` + viewset action + new invocation viewset + `AWAITING_APPROVAL` status + migration + 22 tests + 2 `ALLOWED_FILES` additions + design-doc sub-slicing |
| (this commit) | SESSION 149 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row bump |

**The avatar's LLM can now invoke tools mid-session
via WebRTC data-channel events.** The SPA POSTs to a
dispatch endpoint; the server resolves from a
registry, gates on cost threshold, creates an audit
row, and either executes inline or returns
`awaiting_approval`. First tool — `show_videos_tab`
(UI-only nav event) — proves the round trip end-to-end.

**Test totals**: Django 574 → 596 (+22). Migration
count 49 → 50. No new media-engine routes; no new
Celery tasks (R7.2 adds those). Contract rules 1 + 6 +
9 preserved.

**Q-r-2 (tool rejection narration)** resolved
server-side; SPA wiring lands in R8.
**Q-r-4 (per-workspace tool catalog overrides)** —
`get_workspace_tools(workspace)` seam in place; tier
filtering lands in R7.1.

Full handoff at
`docs/handoffs/SESSION_149_R7_FOUNDATION.md`.

### FIRST THING (SESSION 150): R7.1 (sync tools)

Three sync tools on top of the R7.0 foundation, plus
tier-aware filtering in `get_workspace_tools`:

1. **`recall_knowledge`** — RAG against K2 via
   `retrieve_for_spokesperson(spokesperson, query,
   top_k=3)`. Avatar invokes with a query string;
   returns top hits as a structured payload. Cost:
   ~$0.001; sync.
2. **`recall_recent_conversations`** — read prior
   `Asset(TRANSCRIPT)` rows for this spokesperson
   (mirrors R6's query, returns individual summaries
   instead of a composed projection). Cost: $0; sync.
3. **`handoff_to_spokesperson`** — cross-spokesperson
   event in same workspace. Cross-workspace handoff
   rejected via workspace-scope check in the
   executor. Cost: $0; sync.

Plus: tier-based filtering in `get_workspace_tools`
(each tool gets a `tier_required` attribute;
function filters by `workspace.tier`). Resolves
Q-r-4 fully.

Estimated test count: ~15. Total after R7.1: ~611.

### After SESSION 150

**R7.2 (async tools)** — Celery-driven:
* `render_video` — fires a composition starter
  (default `talking_head`). The threshold-crossing
  tool that exercises the approval modal end-to-end.
* `attach_memory` — pulls partial transcript mid-
  session, composes via R6, pushes as a fresh
  Runway document, attaches to spokesperson.

**R8 (SPA)** — `/spokespeople/:id/talk` route +
`@runwayml/avatars-react` SDK + cost forecasting UI
+ tool-approval modal. The operator-visible moment.
R8 can ship after either R7.1 or R7.2 lands
(`show_videos_tab` alone is enough for the SPA's
minimum viable demo).

**R9 (cost governance)** — per-workspace minutes
budget + live cost ticker.

**R10 (provider hardening)** — drift verifier test.

### Drift-prevention backlog status (from SESSION 147)

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | In flight (parallel context-kit agent) |
| 2 | Auto-bump `last_revised` on handoff write | Queued |
| 3 | Promote calibration entries to TRUST_CALIBRATION at handoff-write | Queued |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done SESSION 147 |
| 5 | Fix INVENTORY's two known generator bugs (Celery undercount + dirty flag) | Queued; **R7.2 will make this more visible** when it adds at least one new Celery task |

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live in
real-mode (SESSION 136).

**Phase 4 (four arcs in flight, two complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped.
  K10 → F8.1 queued. K7.x YouTube ingest fix queued.
- **Video composition arc (V0-V15). COMPLETE**
  (SESSIONS 142-144). 13 step primitives, 18 starter
  recipes, SPA recipe gallery at `/recipes`.
- **Workspace fabric arc (F0-F10). COMPLETE**
  (SESSION 144). F8.1 K10 seed corpus queued.
- **Realtime avatar arc (R0-R10).** R1-R6 + R7.0
  shipped (SESSIONS 146-149). R7.1 (sync tools) is
  next. R7.2 (async tools) + R8 (SPA) + R9 + R10
  remain.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0-K9 | Knowledge layer end-to-end                    | DONE (SESSIONS 137-145) |
| V0-V15 | Video composition arc + recipe gallery     | DONE (SESSIONS 142-144) |
| F0-F10 | Workspace fabric arc                       | DONE (SESSION 144) |
| R0-R5 | Realtime arc (schema → broker → docs → transcripts) | DONE (SESSION 146) |
| R6 | Cross-session memory projection                | DONE (SESSION 148) |
| R7.0 | Tool dispatch foundation (registry + dispatch + first tool) | DONE (SESSION 149) |
| R7.1 | Three sync tools + tier-aware filtering         | Next (SESSION 150) |
| R7.2 | Two async tools via Celery (`render_video`, `attach_memory`) | Queued |
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
that remember prior conversations (R1-R6 /
SESSIONS 146 + 148), and **now invoke tools
mid-session** (R7.0 / SESSION 149).

---

## Queued investigations (priority-ordered)

1. **R7.1 — Sync tools** (next session's primary slice).
2. **R7.2 — Async tools** (`render_video` + `attach_memory`).
3. **R8 — SPA realtime route** (operator-visible
   moment).
4. **R9 — Cost governance.**
5. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
6. **K7.x — YouTube ingest fix.**
7. **K6.3 — Brief length cap.**
8. **K7.1 — Cost telemetry surface.**
9. **Drift-prevention backlog item 5 — INVENTORY
   generator bug fix.** R7.2 will likely surface the
   Celery undercount more visibly.
10. **W11.1 — Edit-spokesperson modal.**
11. **First marketing video** — render Sasha actually
    speaking a real script.
12. **Voice preset audit.**
13. **E2e detritus cleanup** —
    `Workspace.objects.filter(slug__startswith='e2e-').delete()`.
14. **OpenAI client factory port** — three call sites
    now (K6 + K9 + R6); factory pattern from u-d-b
    starts paying off.
15. **R10 — Multi-provider hardening.**
16. **Cast sync command.**
17. **Stuck-row janitor.**
18. **Act-Two performance capture.**
19. **`lesson` video kind.**
20. **Real Google OAuth + dj-stripe.**
21. **Allauth legacy-settings cleanup.**
22. **smoke_voice / smoke_avatar transaction discipline.**
23. **Drift verifier (the original).**
24. **Brand Identity v2 + dark mode.**

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
offline local dev. R7.0 doesn't add a seventh — the
dispatcher is provider-agnostic; tools handle their
own mock state internally.

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait
python -m pytest                              # 596 tests
python -m pytest apps/realtime/tests/         # 87 tests (R1-R6 + R7.0)

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e
```

---

## AI / assistant context

- **Last session: SESSION 149 — R7.0 shipped.**
  Tool dispatch foundation. The avatar can invoke
  tools mid-session; first tool is `show_videos_tab`
  (UI-only nav). 596 backend tests pass. Migration
  50/50.
- **Calibration carried forward:**
  - **Over-scoped slices get sub-sliced at proposal
    time.** R7 was scope-locked at SESSION 142 as one
    slice; SESSION 149 sub-sliced into R7.0/R7.1/R7.2
    before coding, mirroring V15.0-V15.4. Cost: zero.
    Cost of not doing it: SESSION 143-style catch-up
    pass.
  - **Test fixtures that touch singletons should
    snapshot + restore, not module-reload.** The
    `reset_registry` fixture's first iteration
    relied on `importlib.reload` and broke later
    tests. Snapshot at fixture entry + clear-and-
    update on teardown is the obvious pattern.
  - **Pyright in this repo is noisy on Django.** ~15
    false positives per slice on FK auto-attributes,
    UserManager methods, DRF queryset narrowing.
    Filter for novel diagnostics not seen in
    pre-existing code; tests are the ground truth.
  - **Cross-arc isolation guards add 1-3 whitelist
    edits per new test file.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **R7.1 / R7.2 / R8 / R9 / R10 = ~5 more sessions
  for the realtime arc to fully close.** R7.1 + R7.2
  + R8 together get the arc to feature-complete.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end (codified SESSION 143;
  reinforced SESSION 147; honored SESSION 148-149).
