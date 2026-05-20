---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`.
> **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V2.md`.
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
> B1.0-B1.7 COMPLETE + REAL-MODE VALIDATED (SESSION 202).
> **Personalized Video (B-3):** `docs/design/PERSONALIZED_VIDEO_V1.md`.
> **B3.0-B3.9 COMPLETE + REAL-MODE VALIDATED (SESSION 203).**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Publish Bundle (B-14):** `docs/design/PUBLISH_BUNDLE_V1.md`.
> **B14.0-B14.5 COMPLETE + REAL-MODE VALIDATED (SESSION 205).**
> **Auto-Scripting (B-2):** `docs/design/AUTO_SCRIPTING_V1.md`.
> **B2.0 LOCKED + B2.1-B2.5 SHIPPED (SESSION 206); B2.6 (dogfood) queued.**
> **Last handoff:** `docs/handoffs/SESSION_206_E_ARC_LANDS.md`.

---

## SESSION 206 outcome — E-arc Auto-Scripting shipped (lock + 5 of 7 slices)

Fifth strategic-axis arc. Scope-lock cadence **now proven
5-for-5** (A SESSIONS 185-192 → B SESSION 202 → C SESSION
203 → D SESSION 205 → E SESSION 206). Six commits this
session; one dogfood slice pulled at operator request to
preserve real-mode validation quality.

### Slices shipped (6 of 7)

| # | Slice | Commit |
|---|---|---|
| B2.0 | Scope lock — 10 contract rules, 7 slices, 11 open Qs resolved | `47d73b1` |
| B2.1 | `apps.scripts` Django app + Script model + migration + signal | `66068e8` |
| B2.2 | `apps.scripts.synthesis.draft_script` adapter + revision helpers | `b9e095a` |
| B2.3 | `ScriptViewSet` REST + `check_drafts_per_month` + `auto_script` starter | `e0f5139` |
| B2.4 | Recipe-gallery `auto_script` registration + `script_picker` field type | `67f309d` |
| B2.5 | SPA `/workspace/scripts` list + create + detail + recipe-gallery extension (subagent) | `a4bc3c9` |
| **B2.6** | **Real-mode dogfood + arc close** | **← FIRST THING SESSION 207** |

### Real-mode validation — pulled to SESSION 207

Pulled at operator request to avoid same-day fatigue.
Pattern: prior arcs (B-1, B-3, B-14) all rode the dogfood
to its own focused block. The cadence is **"open the arc
+ ship the slices same day; dogfood gets its own session
when needed."**

### Tests at SESSION 206 close

| Suite | Count |
|---|---|
| Django | 1320 (+51 vs SESSION 205) |
| - apps.scripts.tests.test_models | 9 (new) |
| - apps.scripts.tests.test_synthesis | 12 (new) |
| - apps.scripts.tests.test_api | 21 (new) |
| - apps.scripts.tests.test_recipe | 9 (new) |
| Media-engine | 214 (unchanged) |
| SPA vitest | 405 (+34) |

Real-mode spend SESSION 206: **$0** (B2.6 dogfood deferred).

### Calibration (2 new — 39 total)

1. **Scope-lock cadence is now 5-for-5.** Five
   consecutive strategic-axis arcs landed in single-
   session blocks. Pattern is no longer aspirational —
   it's the design default for any new strategic axis.
   Dogfood can ride into the next session when same-day
   fatigue would degrade validation quality.

2. **K6 refactor via adapter pattern preserved zero
   regressions across an existing 600-test surface.**
   The adapter-wraps-callable shape (new module calls
   existing function, remaps result) is strictly safer
   than move-and-shim when the original function has
   mock-patch test fixtures pinned to its import path.
   Generalizes: when motivation is "new feature on top
   of existing function," not "consolidate two
   equivalent paths," reach for the adapter first.

---

## FIRST THING (SESSION 207): B2.6 — E-arc dogfood + close

Close out the auto-scripting arc with real-mode validation.
Plan:

1. **Drift sweep**: `context-kit doctor` (mandatory per
   CLAUDE.md §"Session-start drift sweep").
2. **Pre-fire check**: SESSION 206 committed
   `apps.compositions.starters.auto_script` + a new
   billing function (`check_drafts_per_month`) +
   `apps.compositions.recipes` registry change. **Restart
   Celery** before any real-mode fire (per SESSION 200
   codified rule + SESSION 202/203 extensions). New
   stale-worker-blast-zone path to watch:
   `shell/apps/compositions/recipes.py` (registry-import
   path — recipe-gallery additions don't show up in a
   stale worker's RECIPES dict).
3. **Bring up the HARD REQUIREMENTS stack** with .env
   sourced (Django + SPA + Redis + Celery + media-engine).
4. **Operator drives the SPA** at
   `/workspace/scripts/new` — pick Marcus (Roman tutor
   spokesperson with knowledge attached), type a topic
   ("teach the difference between BC and BCE dates"),
   submit. AI tails Django + Celery + media-engine logs
   in parallel.
5. **Review the draft** in the detail page. Check:
   * `draft_text` populated with synthesized brief
   * `cited_documents` shows the right doc titles
   * `verification_status` = `verified` or `warned`
     (operator decides whether to regenerate or approve)
6. **Approve.** Confirm DRAFT → READY transition;
   `approved_at` set.
7. **Render.** Composition fires; Script flips to
   RENDERED.
8. **Validate the lineage**:
   * Rendered Asset's `source_spec.knowledge_chunk_ids`
     matches the Script's persisted chunks
   * `Composition.synthesized_brief` matches Script's
     `draft_text`
   * F-arc brief-mode panel on the Asset detail
     surfaces the right citations
9. **Operator-noticed quality findings** get captured as
   v2 axes (mirror the SESSION 205 dogfood pattern).
10. **Close the arc**: handoff + TRUST_CALIBRATION
    entries + start-here update for SESSION 208.

Real-mode cost target: **~$0.25** for one auto_script
render against Marcus + Clara. Plus ~$0.001 LLM cost for
the draft itself.

---

## After B2.6 closes — operator picks

Three candidates for the next strategic-axis session:

1. **B-14 v2 `offset_x` knob** (½ session) — addresses
   SESSION 205 dogfood finding while it's fresh.
2. **Asset upload UI** (1-2 sessions) — operator-content
   bottleneck; unblocks B-1 v2.
3. **B-2 ↔ B-3 composition** — Script becomes
   `PersonalizedCampaign.template`. Composes E-arc with
   C-arc; "composition is the moat" framing makes this
   high-leverage.
4. **B-1 v2 slices** — external transcript ingestion,
   batch mining, highlight chaining.
5. **`auto_script_polished` + `auto_script_cinematic`
   variants** — deferred from B2.4 scope. Each is ~½
   session.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete.
**V-arc 18/18 real-mode validated + UX polish complete**.
**Asset Library v1 COMPLETE + DOGFOOD VALIDATED**.
**Transcript Miner (B-1) v1 COMPLETE + REAL-MODE VALIDATED**.
**Personalized Video (B-3) v1 COMPLETE + REAL-MODE VALIDATED.**
**Publish Bundle (B-14) v1 COMPLETE + REAL-MODE VALIDATED.**
**Auto-Scripting (B-2) v1 — backend + SPA COMPLETE; dogfood queued.**
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
| Transcript Miner v1 (B1.0-B1.7) | DONE + REAL-MODE VALIDATED |
| Personalized Video v1 (B3.0-B3.9) | DONE + REAL-MODE VALIDATED |
| Publish Bundle v1 (B14.0-B14.5) | DONE + REAL-MODE VALIDATED |
| **Auto-Scripting v1 (B2.0-B2.6)** | **B2.0 LOCKED + B2.1-B2.5 SHIPPED; B2.6 dogfood = FIRST THING SESSION 207** |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI | Queued |
| B-14 v2 offset_x knob | Queued (½ session; SESSION 205 dogfood finding) |
| B-2 v2 auto_script_polished + auto_script_cinematic | Queued (each ~½ session) |

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

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**HARD REQUIREMENTS** (promoted SESSIONS 193 + 200):

1. **Django dev server** — `python manage.py runserver` from
   `shell/` **with .env sourced**.
2. **SPA dev server** — `pnpm dev` from `web/`. :5174 (binds
   IPv6 localhost; `127.0.0.1:5174` may fail — use
   `localhost:5174`).
3. **Redis** — `cd infra && docker compose up -d`.
4. **Celery worker** — required for any composition fire
   **with .env sourced**.
5. **Media-engine** — required for real-mode renders.

**Pre-fire check (codified SESSION 200, extended SESSION 202+203+206)**:
restart Celery before any real-mode fire when the last commit
against ANY of these is newer than worker start:
* `shell/apps/compositions/primitives/`
* `shell/apps/compositions/starters.py`
* `shell/apps/compositions/recipes.py` (registry; SESSION 206 added)
* `shell/apps/*/signals.py` (includes
  `apps/transcripts/signals.py`,
  `apps/campaigns/signals.py`,
  `apps/scripts/signals.py`)
* `shell/character_os/clients/media_engine.py`

Signals + registry imports register only at
`apps.py::ready()`; a stale worker silently doesn't fire
them.

**Smoke checks** (counts as of SESSION 206 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1320 tests

# Media-engine (from media-engine/)
python -m pytest                              # 214 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 405 vitest tests
```

**New surfaces from SESSION 206 (E-arc / B-2):**

* `apps.scripts` Django app — `Script` model (UUID PK, FK
  Workspace + Spokesperson, prompt + opener + draft_text +
  knowledge_chunk_ids + verification_status +
  verification_warnings + verifier_mode + revision_history
  JSONField + 4-state machine DRAFT/READY/RENDERED/ARCHIVED).
  Migration `0001_initial`. Cross-workspace pre_save signal.
* `apps.scripts.synthesis` — `draft_script` adapter over
  K6 + `snapshot_to_revision_history` + `apply_draft_to_script`
  helpers. Strict-mode `ClaimVerifierError` caught + persisted
  as `verification_status='blocked'` (rule 4).
* `apps.compositions.starters.auto_script` — single-step
  Composition starter that reads a Script's persisted
  `draft_text` + sets `use_knowledge=False` (rule 7 — K6
  in-primitive synthesis skipped because draft already
  synthesized at draft-time).
* `/api/scripts/` — `ScriptViewSet` with 8 actions
  (create / list / retrieve / regenerate / approve /
  render / clone / destroy).
* `TIER_LIMITS["*"]["drafts_per_month"]`: Starter=10,
  Pro=100, Agency=None. `check_drafts_per_month` billing
  gate. `Usage.drafts_used` counts initial-create + each
  regenerate (via JSON revision_history ts filtering).
* `auto_script` recipe registered in
  `apps.compositions.recipes.RECIPES` (gallery count
  19 → 20) with new `script_picker` form field type.
* `/workspace/scripts` + `/workspace/scripts/new` +
  `/workspace/scripts/:id` SPA routes.
* `web/src/lib/api/scripts.ts` — Zod schemas + 8 React
  Query hooks (`useScripts`, `useScript`,
  `useCreateScript`, `useRegenerateScript`,
  `useApproveScript`, `useRenderScript`, `useCloneScript`,
  `useDeleteScript`). All mutations invalidate every
  dependent query.
* Recipe-gallery `script_picker` field type + ScriptPicker
  component (filters to status=READY scripts).

---

## AI / assistant context

- **Last session: SESSION 206 — E-arc lock + 5 of 7 slices
  shipped.** Six commits B2.0-B2.5. Django 1269 → 1320
  (+51). SPA 371 → 405 (+34). 2 new TRUST_CALIBRATION
  entries (39 total). $0 real-mode spend.

- **Prior session: SESSION 205 — D-arc shipped in one
  session.** Seven slices B14.0-B14.5 including dogfood.
  Django 1245 → 1269 (+24). SPA 284 → 371 (+87).

- **Prior session: SESSION 204 — videos_per_month migration.**
  Cleanup between arcs. Django 1207 → 1215 (+8).

- **Scope-lock cadence is now 5-for-5** (A/B/C/D/E arcs).
  Pattern: 8-10 contract rules + 7-10 slices + per-slice
  tests + real-mode dogfood closing. Each arc lands in one
  extended session; dogfood can ride into the next session
  when same-day fatigue would degrade validation quality
  (SESSION 206 made this call).

- **Calibration carried forward (39 total — +2 SESSION 206:
  scope-lock cadence 5-for-5 + K6 refactor adapter pattern)**:
  V-arc 100% real-mode closure; operator-noticed-during-
  dogfood loop; mix_audio + intro_outro silent-base shapes;
  real-mode finds bugs in EVERY recipe (6-for-6 with
  SESSION 205's UX limitation finding); Celery worker
  doesn't auto-reload (3rd hit); mock-mode hides
  stream-shape drift (4th hit); forward-defense audits
  surface latent bugs cheaply; gpt-5 reasoning eats output
  budget; scope-lock pattern compresses build phase
  (5-for-5 now); React Query mutation onSuccess must
  invalidate every dependent query; tier-gated batch caps
  work as designed via forecast preview surface;
  aspect-changing crop is a recurring shape (NEW SESSION 205);
  **K6 refactor via adapter pattern preserved zero
  regressions (NEW SESSION 206); scope-lock cadence 5-for-5
  (NEW SESSION 206).**

- **The "real-mode finds bugs in every recipe" pattern is
  6-for-6.** Every dogfood across SESSIONS 195/197/200/202/
  203/205 surfaced at least one finding (bug or UX
  limitation). SESSION 207's B2.6 dogfood is the next test.

- **Operator pushback on AI's premature "sign-off" framing
  surfaced SESSION 206 early.** The 4-for-4 cadence biased
  the AI toward closure pressure; operator recalibrated to
  "we're just getting started for the day." Calibration:
  cadence is *opportunity*, not *obligation*; let the
  operator set the lock cue.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
