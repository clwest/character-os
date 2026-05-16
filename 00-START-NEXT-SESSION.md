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

## SESSION 159 outcome — drift-prevention items 2 + 3 closed

Both deferred drift-prevention items from the SESSION 147 audit
shipped this session, in the sibling `context-kit` repo.

**`context-kit handoff write <N>` subcommand** lands as
context-kit commit `9590737` ("Add context-kit handoff write
for session-end anchor re-stamp + calibration audit"). Two
side-effects under one verb:

* **Re-stamp anchor docs** (item 2). Atomically updates
  `last_revised:` (and bumps `covers_sessions:` upper bound
  when present) across `docs/*_WHAT_IT_IS.md`,
  `*_PIPELINE.md`, `*_BEHAVIOR_LAYER.md`,
  `*_TRANSLATION_LAYER.md`, and `*_SESSION_START.md`.
  `*_INVENTORY.md` is excluded (owned by `inventory --write`).
* **Calibration drift detection** (item 3). Parses the
  handoff for `## Calibration moments worth carrying` /
  `## AI Notes` subsections, fuzzy-matches their headlines
  against same-date `docs/TRUST_CALIBRATION.md` entries,
  reports `✓ promoted` / `⚠ MISSING`. **Read-only on
  TRUST_CALIBRATION** — the prose-to-canonical-format
  translation is operator judgment.

**Smoke-tested against this repo as the live target.** The
SESSION 158 run caught what the original drift audit was
worried about: four secondary anchors
(`CHARACTER_OS_PIPELINE.md`,
`CHARACTER_OS_BEHAVIOR_LAYER.md`,
`CHARACTER_OS_TRANSLATION_LAYER.md`,
`CHARACTER_OS_SESSION_START.md`) had been silently sitting
with `generated: 2026-05-13` and *no* `last_revised:` field
across 50+ sessions. The subcommand inserted
`last_revised: 2026-05-15 (SESSION 158)` on all four. Backfill
committed as `docs: SESSION 158 — backfill last_revised across
anchor docs (via context-kit handoff write)`. All 3 of
SESSION 158's calibration moments correctly matched their
same-date TRUST_CALIBRATION entries.

**Total context-kit test count: 1042 → 1076 (+34).**
character-os codebase is unchanged this session.

### Drift-prevention backlog status — CLOSED

| # | Item | Status |
|---|---|---|
| 1 | `context-kit drift` subcommand | Superseded by `doctor` |
| 2 | `handoff write` re-stamps anchor frontmatter | **Done (context-kit SESSION 17 / character-os SESSION 159)** |
| 3 | Promote calibration entries to TRUST_CALIBRATION | **Done (detect-and-report shape; context-kit SESSION 17)** |
| 4 | Codify session-start drift sweep in CLAUDE.md | Done (SESSION 151) |
| 5 | Fix INVENTORY's two known generator bugs | Celery undercount done SESSION 151; working-tree-dirty flag pending |

### FIRST THING (SESSION 160): pick one

Drift-prevention thread fully closed. Remaining backlog is
small + non-realtime. The chunky things left are real-Runway
exposure work (one stops being a code session and starts being
operator-facing) and the queued cleanups.

**Recommendation — pick by mood:**

* **Real-Runway exposure** if you want to keep validating the
  Phase 4 stack against real keys: re-bake Donny's avatar
  (recovers him for production); `talking_head_polished`
  retake of Sasha (V9 — adds captions + intro/outro);
  `long_form_ad` end-to-end smoke (V5 launch differentiator;
  proves splitting + concat against real Runway, ~$0.50-$2.00
  spend).
* **F8.1 — K10 seed corpus** if operator-authored markdown is
  ready. 30-60 minutes once the markdown lands.
* ~~**K6.4 — Post-synthesis claim verifier.**~~ **DONE
  SESSION 160.** Shipped substring-v1 with Warn default.
  Donny regression smoke confirms `Wikipedia` flagged,
  `Character OS` allow-listed, `trafilatura` slips
  through (documented v1 lowercase-tech limitation).
  See `docs/design/KNOWLEDGE_LAYER.md` K6.4 ship notes
  for next-step queue (K6.5 conversation parity, SPA
  toggle).
* **K7.x — YouTube ingest fix** if the silent-failure mode
  surfaces during any real-Runway work. ~1 session.
* **K6.3 — Brief length cap (~15 min)** — cheapest cleanup.
* **K7.1 — Cost telemetry surface** in the SPA. ~1 session.
* **W11.1 — Edit-spokesperson modal.** ~1-2 sessions.

### Workflow change SESSION 160 onward

The new session-end rhythm:

```bash
# At session end, after writing docs/handoffs/SESSION_NNN_*.md:
python3 /Users/donkeyking/development/context-kit/context_kit.py \
    handoff write <NNN> --project /Users/donkeyking/development/character-os
```

Pair this command with the handoff commit. It re-stamps
every anchor doc's frontmatter atomically and flags any
calibration moments that didn't make it to
`docs/TRUST_CALIBRATION.md`.

`--dry-run` previews changes; `--date YYYY-MM-DD` overrides
the handoff date if you need it.

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
| **Drift-prevention items 2+3** | **DONE** (SESSION 159; context-kit) |
| F8.1 (K10 seed corpus) | Queued (operator markdown) |
| **K6.4 (claim verifier)** | **DONE (SESSION 160)** |
| K6.5 (verifier parity for conversation_synthesis) | Queued (SESSION 160) |
| K7.x (YouTube ingest fix) | Queued |
| K6.3 / K7.1 / W11.1 | Queued |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - **Sasha the Raccoon** (sales) — id `79d48883-...` — **first known-good real-render voice (`clara`)**
  - Donny the Sloth (user stories) — id `f30b2980-...` — dental artifacts on `drew` voice; needs re-bake
  - Maya the Panda (educator) — id `9410f23f-...` — untested in real-mode

---

## Queued investigations (priority-ordered)

1. **K6.5 — Conversation synthesis verifier parity.**
   Plumb `claim_verifier.verify_claims` into
   `conversation_synthesis.py` so the same hallucination
   class can't leak through `/api/conversations/`
   replies. K6.4 module is already reusable; this is
   wiring + persistence (new field on
   `ConversationMessage`?) + tests. ~0.5 session.
2. **K6.4 SPA toggle (v1.1).** Surface
   `verification_warnings` in the SPA — make-video form
   gains a Strict/Warn/Off toggle (default Warn);
   composition detail page surfaces the warnings list
   alongside the rendered output. ~1 session.
3. **More real-Runway exposure** — re-bake Donny,
   polished Sasha retake, long_form_ad smoke.
4. **F8.1 — K10 seed corpus** (blocked).
5. **K7.x — YouTube ingest fix.**
6. **K6.3 — Brief length cap (~15 min).**
7. **K7.1 — Cost telemetry surface.**
8. **W11.1 — Edit-spokesperson modal.**
7. **Voice preset audit** — smoke-test other voices
   (`drew` flagged; others unknown).
8. **E2e detritus cleanup.**
9. **OpenAI client factory port.**
10. **Cast sync command.**
11. **Stuck-row janitor.**
12. **Act-Two performance capture.**
13. **`lesson` video kind.**
14. **Real Google OAuth + dj-stripe.**
15. **Allauth legacy-settings cleanup.**
16. **smoke_voice / smoke_avatar transaction discipline.**
17. **INVENTORY working-tree-dirty flag fix.**
18. **Brand Identity v2 + dark mode.**

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

**Session-end anchor re-stamp + calibration audit** (new in SESSION 159):

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py \
    handoff write <NNN> --project .
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

- **Last session: SESSION 159 — drift-prevention items 2 + 3
  closed in the sibling `context-kit` repo.** `context-kit
  handoff write <N>` shipped (commit `9590737`). Smoke-tested
  against this repo as the live target. character-os code
  unchanged; four anchor docs got their `last_revised:`
  frontmatter backfilled via the new subcommand.
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
  - **Doctor is the drift tool** (SESSION 151). **Now
    paired with `handoff write` at session-end**
    (SESSION 159).
  - **OpenAI gpt-5 family uses the Responses API.**
- **Realtime arc complete.** Phase 4's four arcs all
  shipped + first end-to-end real-Runway render
  validated.
- Collaboration conventions: AI drafts, human edits.
  Handoff `## AI Notes` (or `## Calibration moments
  worth carrying`) + per-slice doc updates required
  at session end. **End-of-session `context-kit handoff
  write` runs alongside the handoff commit.**
