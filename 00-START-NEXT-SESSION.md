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
> breakdown). **R-ARC COMPLETE — all 10 slices + R6.1 shipped.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_157_R10_RARC_CLOSE.md`.

---

## SESSION 157 outcome — R10 + R-ARC CLOSES

Last R slice. **The realtime avatar arc is complete.**
All 10 slices + R6.1 shipped across SESSIONS 142-157
(16 commits, 12 sessions, zero scope-lock revisions).

| Commit | What it shipped |
|---|---|
| `0f71889` | R10 feat — multi-provider drift verifier (9 tests). Two drift surfaces guarded: Protocol method drift (AST-based stub detection) + registry drift (package-directory enumeration). R-arc closes. |
| (this commit) | SESSION 157 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

**Test totals after R-arc close**:
- **Media-engine**: 99 → **108** (+9 R10).
- **Django**: **659** (unchanged this session).
- **SPA vitest**: **37** (unchanged this session).

**The realtime arc shipped**:

| Slice | Session | Commit |
|---|---|---|
| R0 (scope lock) | 142 | `0e01493` |
| R1 (schema) | 146 | `9299dcf` |
| R2 (provider abstraction) | 146 | `e8eb7d1` |
| R3 (Django broker + tier gate) | 146 | `26378e9` |
| R4 (knowledge → Runway doc bridge) | 146 | `6521451` |
| R5 (transcript capture) | 146 | `885508d` |
| R6 (cross-session memory) | 148 | `dbb22e0` |
| R7.0 (tool dispatch foundation) | 149 | `646c492` |
| R7.1 (3 sync tools + tier filtering) | 150 | `611ae94` |
| R7.2 (async dispatch + render_video) | 151 | `e8564f9` |
| R7.3 + R6.1 (attach_memory + R6 widen) | 152 | `b3f76cb` |
| R8.0 (SPA foundation) | 153 | `7669007` |
| R8.1 (modal + cost forecast) | 154 | `aac6ee4` |
| R8.2 (SDK native + ticker + WebRTC fallback) | 155 | `5697269` |
| R9 (cost governance backend) | 156 | `d33b8cf` |
| R10 (provider drift verifier) | 157 | `0f71889` |

**Operator-visible product**: a fully-configured
spokesperson can hold a live realtime session with
knowledge grounding + cross-session memory + a 6-tool
catalog the avatar invokes mid-session + cost ticker
+ tool-approval modal + WebRTC fallback. All three
cost-governance layers active (R9). Provider
abstraction drift-verified (R10).

**Q-r questions** — 8 of 9 resolved; Q-r-2 (rejection
narration) is partial v1 (Runway SDK doesn't expose
`sendClientEvent`; v1 narration is operator-mediated).

Full handoff at
`docs/handoffs/SESSION_157_R10_RARC_CLOSE.md`.

### FIRST THING (SESSION 158): pick one

**Highest-value: First marketing video.** Flip
`RUNWAY_FORCE_MOCK` off on the media-engine. Walk
through a real session with a cast spokesperson
against real Runway. Render Sasha (or Riggs)
speaking a real script grounded in attached
Character OS knowledge. **Operator-mediated** — the
AI guides; the operator executes (real API budget,
real Runway render times).

This is the highest-value demonstration output now
that R-arc is closed. Exercising the full stack
once end-to-end against real Runway proves it
operationally.

**Alternative — drift-prevention backlog item 2 +
3** (context-kit work):
* **Item 2** — auto-bump `last_revised` on handoff
  write. New `context-kit handoff write <N>`
  subcommand. Half-session.
* **Item 3** — promote calibration entries to
  TRUST_CALIBRATION at handoff-write time
  (depends on item 2). Half-session.

Closes SESSION 147's drift audit backlog fully.

**Alternative — non-realtime cleanup**:
* F8.1 (K10 seed corpus) — blocked on
  operator-authored markdown.
* K7.x (YouTube ingest fix).
* K6.3 / K7.1 / W11.1.

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

**Phase 4 (four arcs, three complete-or-effectively-so):**

- **Knowledge arc (K1-K10).** K1-K9 shipped. K10 →
  F8.1 queued.
- **Video composition arc (V0-V15). COMPLETE.**
- **Workspace fabric arc (F0-F10). COMPLETE.**
- **Realtime avatar arc (R0-R10). COMPLETE.**
  (SESSIONS 146-157).

| Slice | Status |
|-------|--------|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE** (SESSIONS 142-157) |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| K7.x (YouTube ingest fix) | Queued |
| K6.3 / K7.1 / W11.1 | Queued |
| **First marketing video** | Queued (operator-mediated) |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - Sasha the Raccoon (sales) — id `79d48883-...`
  - Donny the Sloth (user stories) — id `f30b2980-...`
  - Maya the Panda (educator) — id `9410f23f-...`

---

## Queued investigations (priority-ordered)

1. **First marketing video** — exercises the whole
   stack against real Runway. Highest-value
   demonstration output.
2. **Drift-prevention backlog items 2 + 3** —
   auto-bump + TRUST_CALIBRATION promotion. Small.
3. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
4. **K7.x — YouTube ingest fix.**
5. **K6.3 — Brief length cap.**
6. **K7.1 — Cost telemetry surface.**
7. **W11.1 — Edit-spokesperson modal.**
8. **Voice preset audit.**
9. **E2e detritus cleanup.**
10. **OpenAI client factory port.**
11. **Cast sync command.**
12. **Stuck-row janitor.**
13. **Act-Two performance capture.**
14. **`lesson` video kind.**
15. **Real Google OAuth + dj-stripe.**
16. **Allauth legacy-settings cleanup.**
17. **smoke_voice / smoke_avatar transaction discipline.**
18. **INVENTORY working-tree-dirty flag fix.**
19. **Brand Identity v2 + dark mode.**

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

# Media-engine (from media-engine/)
python -m pytest                              # 108 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 37 vitest tests
pnpm e2e                                      # Playwright (in mock mode only)
```

---

## AI / assistant context

- **Last session: SESSION 157 — R10 shipped, R-arc
  closes.** Multi-provider drift verifier. 108
  media-engine + 659 backend + 37 SPA tests pass.
- **R-arc complete**: 16 commits, 12 sessions, R0 →
  R10. Operator-visible product complete + cost
  governance complete + provider abstraction
  drift-verified.
- **Calibration carried forward:**
  - **Drift verifiers belong as early scaffolding,
    not late closure** — R10 could have shipped
    alongside R2 to catch the NotImplementedError
    drift class across R3-R5. Place verifier slices
    early in future arcs.
  - **AST-based assertions on source are tractable**
    when verifying implementation shape across a
    registry. Duck-typed calls need meaningful args
    + might have side effects.
  - **Milestone-level doc refresh has its own
    cadence** (SESSION 156).
  - **Match exception payload shape across gates**
    (SESSION 156).
  - **Hardcoded UI constants are a smell**
    (SESSION 156).
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Doctor is the drift tool** (SESSION 151).
  - **Pyright in this repo is noisy on Django/DRF.**
  - **OpenAI gpt-5 family uses the Responses API.**
- **No realtime backlog remains.** Next sessions
  pick from: marketing video, context-kit drift
  backlog items 2/3, non-realtime cleanups (F8.1,
  K7.x, K6.3, K7.1, W11.1).
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end.
