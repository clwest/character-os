---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`
> (locked SESSION 178). **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V2.md`
> (locked SESSION 178 — supersedes V1).
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer:** `docs/design/KNOWLEDGE_LAYER.md`.
> **Video composition:** `docs/design/VIDEO_COMPOSITION_V1.md`.
> V0-V18 COMPLETE + 18/18 RECIPES REAL-MODE VALIDATED.
> **V-arc UX polish COMPLETE (SESSION 200).**
> **Forward-defense audit COMPLETE (SESSION 201).**
> **Realtime avatar:** `docs/design/REALTIME_AVATAR_V1.md`.
> R0-R10 + R6.1 COMPLETE + REAL-MODE HARDENED.
> **Workspace fabric:** `docs/design/WORKSPACE_FABRIC_V1.md`.
> F0-F10 COMPLETE; F8.1 queued.
> **Media generation:** `docs/design/MEDIA_GENERATION_V1.md`.
> W11.6.0-W11.6.5 + sub-slices 1/2/3 COMPLETE.
> **Asset Library:** `docs/design/ASSET_LIBRARY_V1.md`.
> A0-A8 COMPLETE (SESSION 192) + DOGFOOD VALIDATED (SESSION 193).
> **Transcript Miner (B-1):** `docs/design/TRANSCRIPT_MINER_V1.md`.
> **B1.0-B1.7 COMPLETE + REAL-MODE VALIDATED (SESSION 202).**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_202_B_ARC_LANDS.md`.

---

## SESSION 202 outcome — B-1 Transcript Miner shipped + real-mode validated

First strategic-axis arc after the V-arc + Asset Library +
forward-defense audit close-out. **Eight slices in one
extended session** (B1.0 scope-lock through B1.7 real-mode
dogfood). The structural moat thesis from
CONTENT_FORMAT_BACKLOG.md §B-1 is now demonstrable:
per-workspace realtime avatar → per-workspace transcripts →
per-workspace highlight clips. No LLM-video competitor has the
same data to mine.

### Slices shipped

| # | Slice | Effort |
|---|---|---|
| B1.0 | Scope lock — 8 contract rules, 7 slices, 8 open Qs resolved | ½ session |
| B1.1 | `select_transcript_highlights` LLM helper + 20 tests | ½ session |
| B1.2 | `TranscriptHighlight` model + migration + signal + 12 tests | ½ session |
| B1.3 | REST mine/list/retrieve viewset + 13 tests | ½ session |
| B1.4 | approve/reject + render dispatch + completion signal + 13 tests | 1 session |
| B1.5 | SPA `/workspace/transcripts` list + mining trigger (subagent) | 1 session |
| B1.6 | SPA approval UX + char-range hover-highlight (subagent) | 1 session |
| B1.7 | Real-mode dogfood + LLM contract reshape + arc close | ½ session |

### Real-mode validation

Composition `b4ab9ea6-60b5-4478-85c8-df75595b9ed8`:

- **status: completed** ✓
- 19.3s wall-time, **$0.25 spend**
- Spokesperson Marcus resolved via reverse-FK from
  `RealtimeSession.transcript_asset` (Q-b-7)
- Highlight text "They saw it as a necessary act to save the
  Republic." re-baked as 5s avatar speech
- **Completion signal fired correctly** — highlight status
  flipped APPROVED → RENDERED automatically (the load-bearing
  test of B1.4's cross-app `post_save` receiver)

### B1.7 mid-arc contract reshape

Real-mode dogfood surfaced the recurring "gpt-5 reasoning eats
output budget" pattern. The original LLM contract asked
gpt-5-mini to return char_start + char_end alongside text +
reasoning. At reasoning_effort="low" the model burned the
entire output budget (1984 of 2000 tokens) computing offsets,
emitting zero visible output.

**Architectural fix shipped same-session** (commit `d69d291`):
the LLM returns text + reasoning only; the parser locates each
quote via `body.find(text)`. Rule 3 audit shape preserved
end-to-end. Token usage dropped from 0/1984 to 459/658 on the
same task.

### Tests at SESSION 202 close

| Suite | Count |
|---|---|
| Django | 1097 |
| - compositions | 608 (unchanged) |
| - transcripts (new) | 38 (12 model + 13 API + 13 approve) |
| - character_os.test_transcript_miner | 20 |
| Media-engine | 209 (unchanged) |
| SPA vitest | 188 (+54: 30 B1.5 + 24 B1.6) |

Real-mode spend SESSION 202: **$0.25**.

### Calibration (2 new — 31 total)

1. **gpt-5 reasoning eats output budget — char-offset math is
   a recurring trigger.** Asking the model to identify a
   substring + its offsets in a longer body silently blows
   the reasoning budget. Architectural fix beats budget bumps:
   ask for text only; locate offsets server-side via
   `find()`. Forward defense: add a real-mode smoke test for
   any new gpt-5 caller — mock-mode tests don't catch the
   budget burn.

2. **B-arc landed in a single session — scope-lock pattern
   pays off.** Eight contract rules + seven sequenced slices
   + per-slice test coverage produced a one-session arc with
   one surface bug. Same shape as the A-arc (SESSIONS
   185-192). Careful upfront scoping compresses the build
   phase.

---

## FIRST THING (SESSION 203): operator picks

Strategic-axis arc cadence is now proven (V-arc closed
SESSION 197, A-arc closed SESSION 193, B-arc closed
SESSION 202). Natural next moves:

### New-arc candidates (top priority per CONTENT_FORMAT_BACKLOG.md)

1. **B-3 Personalized Video** — biggest revenue unlock; the
   "Hi {firstName}, saw {company} just {triggerEvent}…"
   shape. Requires CSV ingest UX, per-recipient batch
   dispatch, per-recipient asset naming. 10+ slices.
2. **B-14 Multi-Platform Variants** — distribution
   stickiness. One render → reformatted variants for IG /
   TikTok / YT Shorts / LinkedIn. Builds on V9's
   `reformat_clip` + an orchestration layer. 5-6 slices.

### Asset upload UI (B-1 v2 enabler)

* **Asset upload UI for AUDIO / IMAGE / TRANSCRIPT** (1-2
  sessions). Unblocks B-1 v2 (external transcript ingestion)
  + the 8 legacy RAW_UPLOAD rows from the SESSION 185
  backfill.

### Deferred parity slices

* **W12 legacy form retirement** (1 session). The old
  single-form recipe path still rides on the V6 shim.
* **K6.4 v3 architectural fix** (1 session). Verifier surface
  design lock — see K-arc scope doc.
* **K7.x v3 YouTube oEmbed** (½ session).

### B-1 v2 candidates (v1 scope-lock §"Out of scope")

* External transcript ingestion (.srt upload, paste-text)
* Original-session-audio extraction (clean re-bake vs
  authentic noisy)
* Auto-fire approve without operator gate (tier-based bypass)
* Batch mining across N transcripts at once
* Highlight chaining / montage (concat N approved highlights)
* Per-platform fan-out on approve (uses V9 `reformat_clip`)

Each B-1 v2 candidate is ~½ to 1 session; they're all
optional.

### Recommended next direction

If the operator wants another strategic-axis arc, **B-3
Personalized Video** is the highest-revenue candidate. If the
operator wants to unblock B-1 v2 + clear queued backlog,
**Asset upload UI** is the single most impactful 1-2 session
investment.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete.
**V-arc 18/18 real-mode validated + UX polish complete**.
**Asset Library v1 COMPLETE + DOGFOOD VALIDATED**.
**B-arc (Transcript Miner v1) COMPLETE + REAL-MODE VALIDATED.**
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent.

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 + V17 + V18 | DONE + REAL-MODE VALIDATED |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED |
| W11.6.0-W11.6.5 | DONE |
| Asset Library v1 (A0-A8) | DONE + DOGFOOD VALIDATED |
| **Transcript Miner v1 (B1.0-B1.7)** | **DONE + REAL-MODE VALIDATED** |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI | Queued |
| B-3 Personalized Video | New-arc candidate |
| B-14 Multi-Platform Variants | New-arc candidate |

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
celery -A character_os worker --loglevel=info --pool=solo

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host localhost --port 8001 --reload

cd web && pnpm dev                          # :5174
```

**SESSION 202 finding — env file must be sourced for Django
+ Celery**. The `.env` at the repo root holds `OPENAI_API_KEY`
+ `RUNWAY_API_KEY` etc., but Django doesn't auto-load it. The
helper modules (`realtime_memory`, `script_synthesis`,
`transcript_miner`) all read `os.environ["OPENAI_API_KEY"]`
directly. Use `set -a && source ../.env && set +a` before
`python manage.py runserver` / `celery` to export the keys.
Without this, gpt-5 callers degrade silently to empty
results.

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**HARD REQUIREMENTS** (promoted SESSION 193 + 200):

1. **Django dev server** — `python manage.py runserver` from
   `shell/` **with .env sourced**.
2. **SPA dev server** — `pnpm dev` from `web/`. :5174 (binds
   IPv6 localhost; `127.0.0.1:5174` may fail — use
   `localhost:5174`).
3. **Redis** — `cd infra && docker compose up -d`.
4. **Celery worker** — required for any composition fire
   **with .env sourced**.
5. **Media-engine** — required for real-mode renders.
   Optional for mock-mode.

**Pre-fire check (codified SESSION 200)**: when last commit
against `shell/apps/compositions/primitives/` is newer than
Celery worker start time, restart Celery first. Generalizes
to `shell/apps/*/signals.py` files too — signals only register
at `apps.py::ready()`.

**Smoke checks** (counts as of SESSION 202 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1097 tests

# Media-engine (from media-engine/)
python -m pytest                              # 209 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 188 vitest tests
```

**New surfaces from SESSION 202 (B-arc):**

* `apps.transcripts` Django app — single model
  `TranscriptHighlight` with 4-state machine + cross-workspace
  signal + DB CheckConstraint. Migration `0001_initial`.
* `character_os/transcript_miner.py` — `select_transcript_highlights()`
  + 7th force-mock flag (`TRANSCRIPT_MINER_FORCE_MOCK`).
* `/api/transcript_highlights/` — `TranscriptHighlightViewSet`
  with `mine` / list / retrieve / approve / reject actions.
* `/workspace/transcripts` + `/workspace/transcripts/:id` SPA
  routes with the char-range hover-highlight + approval UX.
* `web/src/lib/api/transcripts.ts` — Zod schemas + 4 React
  Query hooks (`useHighlightsForTranscript`,
  `useMineTranscript`, `useApproveHighlight`,
  `useRejectHighlight`).
* Cross-app `post_save` receiver on Composition flips
  TranscriptHighlight status APPROVED → RENDERED on
  composition completion.

---

## AI / assistant context

- **Last session: SESSION 202 — B-arc shipped in one session.**
  Eight slices B1.0 through B1.7. Django 1039 → 1097 (net +58
  across the arc). SPA 134 → 188 (+54). 2 new
  TRUST_CALIBRATION entries (gpt-5 offset-math budget burn;
  scope-lock pattern paying off). $0.25 real-mode spend.

- **Prior session: SESSION 201 — forward-defense audit.**
  Media-engine 204 → 209 (+5). 2 latent silent-base bugs
  fixed pre-real-mode.

- **Calibration carried forward (31 total — +2 SESSION 202)**:
  V-arc 100% real-mode closure; operator-noticed-during-
  dogfood loop; mix_audio + intro_outro silent-base shapes;
  real-mode finds bugs in EVERY recipe (4-for-4); Celery
  worker doesn't auto-reload (3rd hit); mock-mode hides
  stream-shape drift (4th hit); forward-defense audits
  surface latent bugs cheaply; **gpt-5 reasoning eats output
  budget (5th hit; recurring pattern across K6 + B-1)**;
  **scope-lock pattern compresses build phase (A-arc + B-arc
  both shipped in single sessions)**.

- **B-arc validates the strategic-axis arc cadence.** Same
  shape as the A-arc: lock scope → 7-9 slices → real-mode
  dogfood close. Future axes (B-3 Personalized Video, B-14
  Multi-Platform Variants) should follow the same pattern.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
