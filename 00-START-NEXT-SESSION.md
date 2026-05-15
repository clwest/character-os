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
> breakdown). **R1-R7 shipped (v1 tool catalog complete); R8, R9, R10 remain.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_152_R7_MEMORY_CLOSE.md`.

---

## SESSION 152 outcome — R7.3 + R6.1 + v1 tool catalog complete

Single-slice session shipped two paired changes in one
commit. **The realtime backend is now feature-complete
at v1**: six tools across starter + pro tiers, the full
memory loop including mid-session commits, every R
contract rule preserved.

| Commit | What it shipped |
|---|---|
| `b3f76cb` | R7.3 + R6.1 feat — `attach_memory` async tool + R6 query widen (drop `status=ENDED` filter) + new `capture_transcript` helper shared between R5 + R7.3 + 14 tests + 1 ALLOWED_FILES addition |
| (this commit) | SESSION 152 handoff + this start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md updates |

**v1 Tool Catalog (6 tools, complete)**:

| Tool | Tier | Cost | Sync/Async | Slice |
|---|---|---|---|---|
| `show_videos_tab` | starter | $0 | sync | R7.0 |
| `recall_knowledge` | starter | ~$0.001 | sync | R7.1 |
| `recall_recent_conversations` | starter | $0 | sync | R7.1 |
| `handoff_to_spokesperson` | pro | $0 | sync | R7.1 |
| `render_video` | starter | $0.08 | async | R7.2 |
| `attach_memory` | pro | ~$0.001 | async | R7.3 |

**Test totals**: Django 627 → 641 (+14). Migrations
51/51 (no schema change this slice). No new Celery
tasks, media-engine routes, or force-mock flags.

**Q-r-8 resolved**: `capture_transcript` is idempotent
+ last-write-wins; the race window is the standard
media-engine fetch delay, not a multi-write merge.

Full handoff at
`docs/handoffs/SESSION_152_R7_MEMORY_CLOSE.md`.

### FIRST THING (SESSION 153): R8 (SPA — operator-visible moment)

The backend has been feature-complete since
`attach_memory` landed. R8 is where the realtime arc
becomes *demonstrable* to the operator.

**Recommend sub-slicing** (per the SESSION 149-150
calibration on over-scoped slices):

* **R8.0** — SPA route `/spokespeople/:id/talk` +
  `@runwayml/avatars-react` SDK mount + basic session
  lifecycle (start / live indicator / end). The
  minimum viable demo.
* **R8.1** — Tool-approval modal (renders when
  `awaiting_approval` lands) + cost forecasting UI
  before session-start ("~$0.42 for a 5-min session").
* **R8.2** — Live cost ticker during the session +
  error paths (Q-r-9 WebRTC fallback messaging) +
  Q-r-2 rejection narration via `sendClientEvent`.

R8.0 alone is enough to demo the realtime arc end-to-
end. R8.1 + R8.2 are polish layers that ride on top.

### After SESSION 153

* **R9 (cost governance)** — per-workspace minutes
  budget enforcement + the per-minute estimation
  primitives. Backend slice; UI in R8.2.
* **R10 (provider hardening)** — drift verifier test
  for the registry pattern. Smaller; can ride any
  session.
* **Drift-prevention backlog items 2 + 3** —
  auto-bump `last_revised` on handoff write +
  TRUST_CALIBRATION promotion. Worth picking up
  between R8 sub-slices.
* **F8.1 / K7.x** — non-realtime cleanup slices.

### Drift-prevention backlog status

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | **Superseded** by `doctor` extensions (SESSION 151) |
| 2 | Auto-bump `last_revised` on handoff write | Queued |
| 3 | Promote calibration entries to TRUST_CALIBRATION | Queued |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done SESSION 147; doctor-based SESSION 151 |
| 5 | Fix INVENTORY's two known generator bugs | **Celery undercount done SESSION 151**; working-tree-dirty flag still pending |

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live
in real-mode (SESSION 136).

**Phase 4 (four arcs in flight, three complete-or-effectively-so):**

- **Knowledge arc (K1-K10).** K1-K9 shipped. K10 →
  F8.1 queued. K7.x YouTube ingest fix queued.
- **Video composition arc (V0-V15). COMPLETE**
  (SESSIONS 142-144).
- **Workspace fabric arc (F0-F10). COMPLETE**
  (SESSION 144).
- **Realtime avatar arc (R0-R10).** **R1-R7 shipped**
  (SESSIONS 146-152). v1 tool catalog complete. R8
  (SPA — operator-visible moment) is next. R9 + R10
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
| R6.1 | Widen R6 query (drop status=ENDED filter)     | DONE (SESSION 152) |
| R7.0 | Tool dispatch foundation                       | DONE (SESSION 149) |
| R7.1 | Three sync tools + tier-aware filtering        | DONE (SESSION 150) |
| R7.2 | Async dispatch + `render_video`                | DONE (SESSION 151) |
| R7.3 | `attach_memory` + capture_transcript helper    | DONE (SESSION 152) |
| R8 | SPA `/spokespeople/:id/talk` + SDK integration   | Next (SESSION 153) |
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
that remember prior conversations (R1-R6), invoke a
full v1 catalog of six tools mid-session including
**`attach_memory` for mid-session memory commits**
(R7.3 / SESSION 152) and **`render_video` that fires
the V-arc composition chain via Celery** (R7.2 /
SESSION 151).

---

## Queued investigations (priority-ordered)

1. **R8.0 — SPA route + SDK mount** (next session's
   primary slice; minimum viable demo).
2. **R8.1 — Tool-approval modal + cost forecasting UI.**
3. **R8.2 — Live cost ticker + error paths +
   rejection narration.**
4. **R9 — Cost governance backend.**
5. **R10 — Multi-provider hardening (drift verifier).**
6. **Drift-prevention backlog item 2 + 3** (auto-bump +
   TRUST_CALIBRATION promotion).
7. **F8.1 — K10 seed corpus** (blocked on
   operator-authored markdown).
8. **K7.x — YouTube ingest fix.**
9. **K6.3 — Brief length cap.**
10. **K7.1 — Cost telemetry surface.**
11. **W11.1 — Edit-spokesperson modal.**
12. **First marketing video.**
13. **Voice preset audit.**
14. **E2e detritus cleanup.**
15. **OpenAI client factory port.**
16. **Cast sync command.**
17. **Stuck-row janitor.**
18. **Act-Two performance capture.**
19. **`lesson` video kind.**
20. **Real Google OAuth + dj-stripe.**
21. **Allauth legacy-settings cleanup.**
22. **smoke_voice / smoke_avatar transaction discipline.**
23. **INVENTORY working-tree-dirty flag fix.**
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
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait
python -m pytest                              # 641 tests
python -m pytest apps/realtime/tests/         # 131 tests (R1-R7)

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e
```

---

## AI / assistant context

- **Last session: SESSION 152 — R7.3 + R6.1 shipped.**
  `attach_memory` async tool + R6 query widen +
  shared `capture_transcript` helper. The v1 tool
  catalog is now complete at six tools. 641 backend
  tests pass.
- **Calibration carried forward:**
  - **Ship the prerequisite with its consumer in one
    slice** when both live in the same codebase + the
    prereq is small. Half-shipping leaves the
    feature meaningless until the other half lands.
  - **Extract a helper between two code paths early**
    — don't wait for the third copy. R7.3's
    `capture_transcript` extraction was ~15 minutes
    and guarantees future "how transcripts are
    captured" changes stay coherent.
  - **Inverted-test pattern when changing semantics**
    — rewrite the existing test that asserts the OLD
    behavior to assert the NEW behavior on the same
    fixture, then add a sibling test for the part of
    the gate that didn't change.
  - **Doctor is the drift tool** (SESSION 151
    calibration).
  - **Splitting a scope-locked slice mid-implementation
    is fine** when deps surface late (SESSION 151).
  - **Pyright in this repo is noisy on Django/DRF** —
    same false positives every session.
  - **OpenAI gpt-5 family uses the Responses API.**
- **R8 / R9 / R10 = ~3 more sessions to close the
  realtime arc fully.** R8 (sub-sliced as R8.0 / R8.1
  / R8.2) brings everything operator-visible.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end (codified SESSION 143;
  reinforced SESSION 147; honored SESSIONS 148-152).
