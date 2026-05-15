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
> breakdown). **R-ARC COMPLETE.**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_158_FIRST_MARKETING_VIDEO.md`.

---

## SESSION 158 outcome — first real-Runway marketing video

Operator-mediated session. **Exercised the full Phase 4
stack end-to-end against real Runway for the first time.**
Two real renders. $0.50 total Runway spend. Second cut
publishable as-is.

Pipeline path validated end-to-end:

```
KnowledgeDocument (M2M-attached to spokesperson)
  ↓ K2 retrieval → K6 script synthesis (gpt-5-mini)
  ↓ V3 talking_head starter → V2 execute_composition (Celery)
  ↓ generate_avatar_speech primitive → MediaEngineClient
  ↓ /v1/avatar_videos (real Runway)
  ↓ Asset(CLIP) persisted with Runway CloudFront URL
```

All eight layers fired clean against real keys.

| | Donny (run 1) | Sasha (run 2) |
|---|---|---|
| Voice | `drew` | `clara` |
| Script | ~80 words / ~35s | ~30 words / ~10s |
| Render time | 57.6s | 34.2s |
| Cost | $0.25 | $0.25 |
| Output | **Dental artifacts** | **Publishable** |

**Publishable cut** (JWT expires ~Jun 14):

```
https://dnznrvs05pmza.cloudfront.net/051795d7-45f6-4d5e-b63f-24b1532c1344.mp4?_jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJrZXlIYXNoIjoiMTVhYzcyOGQ0MjhlN2VhYyIsImJ1Y2tldCI6InJ1bndheS10YXNrLWFydGlmYWN0cyIsInN0YWdlIjoicHJvZCIsImV4cCI6MTc3OTAyNzg1M30.czrxYRDZvpDd0XbQo-7JA24xRfvGwS7ljt3VslzhLTA
```

**No code changes this session** — operator-mediated
validation milestone. Three new TRUST_CALIBRATION
entries promoted:
1. AI overstated "shipped" before operator viewed
   output (Donny render).
2. Avatar voice × lip-sync quality is a real
   operational axis (`drew` artifacts vs `clara`
   clean).
3. R9 hardcoded placeholder accurate within ~5x —
   stub-and-refine pattern validated.

Full handoff at
`docs/handoffs/SESSION_158_FIRST_MARKETING_VIDEO.md`.

### FIRST THING (SESSION 159): pick one

R-arc closed; first marketing video shipped. Remaining
backlog is small + non-realtime.

**Recommendation — drift-prevention backlog items 2 + 3
(context-kit work, 1 session total)**:

* **Item 2** — `context-kit handoff write <N>`
  subcommand that re-stamps every anchor doc's
  frontmatter in one shot. Removes the forgetting
  surface that caused SESSION 147's drift audit.
  Half-session.
* **Item 3** — promote calibration entries from
  handoffs to TRUST_CALIBRATION at handoff-write
  time. Depends on item 2. Half-session.

Together: closes the SESSION 147 drift audit
backlog fully (items 4 + 5 already done; item 1
superseded by `doctor`).

### Alternatives

**More real-Runway exposure**:
* **Re-bake Donny's avatar** — Runway avatar create
  is slow + costly but recovers Donny for production.
* **`talking_head_polished` retake of Sasha** —
  V9 adds captions + intro/outro for a more
  marketing-ready cut.
* **`long_form_ad` end-to-end smoke test** — V5's
  launch differentiator. Cost $0.50-$2.00. Proves
  the splitting + concat path against real Runway.

**Non-realtime cleanups**:
* **F8.1** (blocked on operator-authored markdown).
* **K7.x** YouTube ingest fix.
* **K6.3** brief length cap (~15 min).
* **K7.1** cost telemetry surface.
* **W11.1** edit-spokesperson modal.

### Drift-prevention backlog status

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | **Superseded** by `doctor` |
| 2 | Auto-bump `last_revised` on handoff write | Queued — RECOMMENDED next |
| 3 | Promote calibration entries to TRUST_CALIBRATION | Queued — depends on item 2 |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done; doctor-based SESSION 151 |
| 5 | Fix INVENTORY's two known generator bugs | Celery undercount done SESSION 151; working-tree-dirty flag pending |

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live
in real-mode (SESSION 136). **First marketing video
shipped against real Runway** (SESSION 158).

**Phase 4 (four arcs, three complete; R-arc complete):**

- **Knowledge arc (K1-K10).** K1-K9 shipped.
- **Video composition arc (V0-V15). COMPLETE.**
- **Workspace fabric arc (F0-F10). COMPLETE.**
- **Realtime avatar arc (R0-R10). COMPLETE.**

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE |
| F0-F10 | DONE |
| **R0-R10 + R6.1** | **DONE** (SESSIONS 142-157) |
| **First marketing video** | **DONE** (SESSION 158) |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| K7.x (YouTube ingest fix) | Queued |
| K6.3 / K7.1 / W11.1 | Queued |
| Drift-prevention items 2 + 3 | Recommended next |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - **Sasha the Raccoon** (sales) — id `79d48883-...` — **first known-good real-render voice (`clara`)**
  - Donny the Sloth (user stories) — id `f30b2980-...` — dental artifacts on `drew` voice; needs re-bake
  - Maya the Panda (educator) — id `9410f23f-...` — untested in real-mode

---

## Queued investigations (priority-ordered)

1. **Drift-prevention items 2 + 3** (closes
   SESSION 147 audit backlog).
2. **More real-Runway exposure** — re-bake Donny,
   polished Sasha retake, long_form_ad smoke.
3. **F8.1 — K10 seed corpus** (blocked).
4. **K7.x — YouTube ingest fix.**
5. **K6.3 — Brief length cap (~15 min).**
6. **K7.1 — Cost telemetry surface.**
7. **W11.1 — Edit-spokesperson modal.**
8. **Voice preset audit** — smoke-test other voices
   (`drew` flagged; others unknown).
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
+ REALTIME_MEMORY on Django). With `RUNWAY_API_KEY` set
in `.env`, media-engine runs in real mode by default.

**Real-mode validation** (SESSION 158): cast members
configured in workspace `admins-workspace` can fire
real-Runway renders via the `talking_head` starter +
K6 RAG synthesis. ~30-60s per render, ~$0.25-$0.50
each. Sasha (`clara` voice) is the known-good
spokesperson; Donny (`drew` voice) shows dental
artifacts.

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
```

---

## AI / assistant context

- **Last session: SESSION 158 — first marketing video
  shipped against real Runway.** Two renders, $0.50,
  one publishable cut. R-arc + V-arc + K-arc all
  validated end-to-end against real keys.
- **Calibration carried forward:**
  - **AI's "shipped" framing belongs to the operator
    after review** for any model-output deliverable.
    The pipeline returning 2xx is system success, not
    deliverable success.
  - **Avatar voice × lip-sync quality is a real
    operational axis.** Smoke-test future
    voices/avatars with a 10s render before declaring
    them production-ready.
  - **R9 placeholder accurate to ~5x** — stub-and-
    refine validated. Track placeholder constants
    explicitly; refine after first real-data event,
    not before.
  - **Drift verifiers belong as early scaffolding**
    (SESSION 157).
  - **Milestone-level doc refresh has its own cadence**
    (SESSION 156).
  - **Mock-mode is first-class UX** (SESSION 153).
  - **Doctor is the drift tool** (SESSION 151).
  - **OpenAI gpt-5 family uses the Responses API.**
- **Realtime arc complete.** Phase 4's four arcs all
  shipped + first end-to-end real-Runway render
  validated.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` + per-slice doc updates
  required at session end.
