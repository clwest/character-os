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
> **Publish Bundle (B-14):** `docs/design/PUBLISH_BUNDLE_V1.md`.
> **B14.0-B14.5 COMPLETE + REAL-MODE VALIDATED (SESSION 205).**
> **Auto-Scripting (B-2):** `docs/design/AUTO_SCRIPTING_V1.md`.
> **B2.0-B2.6 COMPLETE + REAL-MODE VALIDATED (SESSION 207).**
> **B-2 ↔ B-3 Composition:** `docs/design/B2_B3_COMPOSITION_V1.md`.
> **BC0-BC4 SHIPPED (SESSION 208); BC5 dogfood queued.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_208_BC_ARC_LANDS.md`.

---

## SESSION 208 outcome — first composition arc lands

The B-2 ↔ B-3 composition arc shipped lock + 4 of 6
implementation slices in one extended session. Five BC-arc
commits + two SESSION 207 close-out commits:

| # | Slice | Commit |
|---|---|---|
| BC0 | Scope lock — 9 contract rules, 6 slices, 9 open Qs proposed | `de2d92e` |
| BC1 | `source_script` FK on PersonalizedCampaign + workspace guard | `e97b06f` |
| BC2 | `talking_head_polished` starter accepts optional lineage kwargs | `863d374` |
| BC3 | REST + launch propagation + `derived_campaigns` endpoint | `5ada363` |
| BC4 | SPA picker + derived campaigns surface (via `react-web-delivery`) | `e76e173` |
| **BC5** | **Real-mode dogfood + arc close** | **← FIRST THING SESSION 209** |

**All 9 open questions resolved** across BC1-BC4. The arc
backend is complete; SPA is complete; real-mode dogfood is the
last slice.

### Tests at SESSION 208 close

| Suite | Count | Delta |
|---|---|---|
| Django | **1343** | +23 (BC1+BC2+BC3) |
| SPA vitest | **426** | +21 (BC4) |
| Media-engine | **214** | unchanged |

Real-mode spend SESSION 208: **$0** (BC5 dogfood deferred).

### What composition is now queryable

Operator can (in principle, via curl + SPA):

1. Draft a knowledge-grounded Script in `/workspace/scripts/new`
   → K6.4 verifies → operator approves.
2. Create a Campaign in `/workspace/campaigns/new` → pick the
   approved Script via the new picker → `draft_text` copies
   verbatim → operator edits to add `{placeholders}`.
3. Paste CSV + Launch → every per-recipient Composition
   inherits the Script's `knowledge_chunk_ids` +
   `verification_status` + `verification_warnings`. Each
   per-recipient `synthesized_brief` = the template-substituted
   text.
4. Each per-recipient Asset's F-arc brief-mode panel surfaces
   the same citations the Script's detail page shows. Campaign
   detail surfaces "Derived from script" block. Script detail
   surfaces "Derived campaigns (N)" panel.

BC5 validates this end-to-end against real Runway spend.

---

## FIRST THING (SESSION 209): BC5 — composition arc dogfood + close

Close out the B-2 ↔ B-3 composition arc with real-mode
validation against the SESSION 207 "Five Good Emperors" Script.
Plan:

1. **Drift sweep**: `context-kit doctor` (mandatory per
   CLAUDE.md §"Session-start drift sweep").
2. **Pre-fire check**: SESSION 208 committed BC1's model field +
   BC2's starter signature + BC3's view changes — all in the
   stale-worker blast zone. **Restart Celery** before any
   real-mode fire (per SESSION 200 codified rule + the
   recurring SESSION 206/207 reminder). New blast-zone path
   for SESSION 209's pre-fire check:
   * `shell/apps/campaigns/views.py` (BC3 — launch lineage)
   * `shell/apps/compositions/starters.py` (BC2 — kwargs)
   * `shell/apps/campaigns/models.py` (BC1 — FK field)
   * `shell/apps/campaigns/signals.py` (BC1 — workspace guard
     extension)
3. **Bring up the HARD REQUIREMENTS stack** with `.env` sourced
   (Django + SPA + Redis + Celery + media-engine).
4. **Operator drives the SPA** at `/workspace/campaigns/new`:
   * Pick **Marcus** as spokesperson.
   * Click "Use approved Script as starting template" picker.
   * Pick **Five Good Emperors** (Script
     `0f837a40-9226-4244-a743-067361cc2b93` from SESSION 207).
   * Confirm verbatim `draft_text` lands in textarea.
   * Edit template to add `{first_name}` placeholder and
     reframe (e.g. "Hi {first_name}, today we're tackling the
     Five Good Emperors...").
   * Submit → DRAFT campaign.
   * Paste 2-recipient CSV (e.g. `first_name\nBob\nCarol`).
   * Click Launch → forecast → confirm fan-out (~$0.50).
5. **AI tails** Django + Celery + media-engine logs in
   parallel (same as SESSION 207 pattern).
6. **Validate per-recipient lineage** in DB:
   * Each per-recipient `Composition.knowledge_chunk_ids`
     matches Script's chunks
   * Each per-recipient `Composition.synthesized_brief` is the
     substituted text (with the recipient's `{first_name}`)
   * Each per-recipient `Composition.verification_status`
     carries from Script
7. **Validate via SPA**:
   * Each per-recipient Asset's F-arc brief-mode panel renders
     the citation breakdown (the load-bearing rule 4 payoff)
   * Campaign detail surfaces "Derived from script" block
   * Script's "Derived campaigns (1)" panel updates
8. **Operator-noticed quality findings** captured as
   TRUST_CALIBRATION entries (mirror SESSION 207 pattern;
   real-mode-finds-bugs is 7-for-7 going in; expect at least
   one finding).
9. **Close the arc**:
   * Handoff `SESSION_209_BC_ARC_DOGFOOD.md`.
   * Mark BC5 ✓ SHIPPED in design lock.
   * TRUST_CALIBRATION entries for findings + the
     "composition arc shipped 6-for-6 in one session block"
     pattern.
   * Regenerate INVENTORY.
   * Overwrite this doc for SESSION 210 priorities.

Real-mode cost target: **~$0.50** (2 × $0.25 per
`talking_head_polished` per the C-arc baseline).

---

## After BC5 closes — operator picks

Three high-leverage candidates for SESSION 210:

1. **Composition-detail verifier panel polish** (~½ session) —
   SESSION 207 v2 finding: Composition detail page shows
   "Warn — 2 flags" for `trusted_passthrough` status. Same
   bug-class as the Script detail patch in `8a1aa49` but
   opposite direction. ~10 LOC in
   `web/src/routes/compositions/$id.tsx`. Combine with the
   B-2 v2 polish slice from SESSION 207's findings list.

2. **B-2 v2 polish slice** (~½ session) — fix the
   Composition-detail panel + add Script-detail vitest for the
   B2.6 patch + optionally `Asset.spokesperson` back-link in
   `auto_script` starter.

3. **Asset upload UI** (1-2 sessions) — unblocks B-1 v2 + the
   Marcus re-bake workflow + the operator-content bottleneck.

4. **B-14 v2 `offset_x` knob** (½ session) — SESSION 205
   dogfood finding while still fresh.

5. **B-1 v2 slices** — external transcript ingestion, batch
   mining, highlight chaining.

6. **Marcus rig re-bake** — cosmetic; SESSION 207 calibration
   noted mouth/portrait artifacts as a quality finding. Pair
   with the Asset upload UI work.

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
**Auto-Scripting (B-2) v1 COMPLETE + REAL-MODE VALIDATED.**
**B-2 ↔ B-3 Composition v1 — backend + SPA COMPLETE; dogfood queued.**
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
| Auto-Scripting v1 (B2.0-B2.6) | DONE + REAL-MODE VALIDATED |
| **B-2 ↔ B-3 Composition v1 (BC0-BC5)** | **BC0-BC4 SHIPPED; BC5 dogfood = FIRST THING SESSION 209** |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI | Queued |
| B-14 v2 offset_x knob | Queued (½ session; SESSION 205 dogfood finding) |
| B-2 v2 polish slice | Queued (~½ session; SESSION 207 findings) |
| B-2 v2 auto_script_polished + auto_script_cinematic | Queued |
| Composition-detail verifier panel polish | Queued (~½ session; SESSION 207 finding) |
| Marcus rig re-bake | Queued (cosmetic; SESSION 207 finding) |

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

**Pre-fire check** (codified SESSION 200, extended SESSION
202+203+206+208): restart Celery before any real-mode fire
when the last commit against ANY of these is newer than worker
start:

* `shell/apps/compositions/primitives/`
* `shell/apps/compositions/starters.py` (BC2 extended)
* `shell/apps/compositions/recipes.py`
* `shell/apps/*/signals.py` (incl. `apps/campaigns/signals.py`
  — BC1 extension)
* `shell/apps/*/models.py` (BC1 — `source_script` FK)
* `shell/apps/campaigns/views.py` (BC3 — launch lineage)
* `shell/character_os/clients/media_engine.py`

Signals + registry imports register only at
`apps.py::ready()`; a stale worker silently doesn't fire them.

**Smoke checks** (counts as of SESSION 208 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1343 tests

# Media-engine (from media-engine/)
python -m pytest                              # 214 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 426 vitest tests
```

**New surfaces from SESSION 208 (BC arc):**

* `PersonalizedCampaign.source_script` (FK to Script,
  null=True, blank=True, on_delete=PROTECT,
  related_name='derived_campaigns'). Migration
  `0002_bc1_source_script`. Cross-workspace guard at clean()
  + pre_save signal.
* `talking_head_polished()` starter accepts optional
  `knowledge_chunk_ids` / `synthesized_brief` /
  `verification_status` / `verification_warnings` kwargs
  (defaults None preserve current behavior).
* `POST /api/campaigns/` accepts optional `source_script_id`
  body field.
* `GET /api/campaigns/<id>/` includes `source_script` block
  when set.
* `GET /api/scripts/<id>/derived_campaigns/` returns
  workspace-filtered paginated list (100-row cap).
* SPA picker at `/workspace/campaigns/new` ("Use approved
  Script as starting template") with spokesperson+status
  default filter and "Show all workspace scripts" toggle.
* `SourceScriptPanel` on `/workspace/campaigns/:id` detail.
* `DerivedCampaignsPanel` on `/workspace/scripts/:id` detail.

---

## AI / assistant context

- **Last session: SESSION 208 — BC arc lock + 4 of 6 slices
  shipped.** Five BC commits B0-B4 + two SESSION 207 close-out
  commits. Django 1320 → 1343 (+23). SPA 405 → 426 (+21). 9
  open questions all resolved. $0 real-mode spend.

- **Prior session: SESSION 207 — E-arc B2.6 dogfood + close.**
  Two commits (B2.6 patch + close bundle). $0.25 real-mode
  spend. 10 findings (1 patched, 6 v2, 2 calibration, 1 win).

- **Prior session: SESSION 206 — E-arc lock + 5 of 7 slices
  shipped.** Six commits B2.0-B2.5. $0 real-mode spend.

- **Scope-lock cadence is 5-for-5 strategic-axis (A/B/C/D/E)
  + 1-for-1 composition (BC).** Composition arcs ship in ~6
  slices (vs 10-13 for strategic-axis arcs) because the
  upstream work is done — they add an FK, propagate optional
  kwargs through a starter, and wire a SPA picker.

- **Calibration carried forward (41 total — no new entries
  SESSION 208; BC arc was pure integration over validated
  layers)**: V-arc 100% real-mode closure; operator-noticed-
  during-dogfood loop; mix_audio + intro_outro silent-base
  shapes; real-mode finds bugs in EVERY arc (7-for-7);
  Celery worker doesn't auto-reload (3rd hit); mock-mode
  hides stream-shape drift (4th hit); forward-defense audits
  surface latent bugs cheaply; gpt-5 reasoning eats output
  budget; scope-lock pattern compresses build phase (5-for-5
  strategic-axis); React Query mutation onSuccess must
  invalidate every dependent query; tier-gated batch caps
  work as designed via forecast preview surface; aspect-
  changing crop is a recurring shape; K6 refactor via adapter
  pattern preserved zero regressions; real-mode-finds-bugs
  streak 7-for-7; avatar rig quality has three axes —
  portrait, voice × lip-sync, script-persona fit.

- **The "real-mode finds bugs in every arc" pattern is
  7-for-7.** Every dogfood across SESSIONS 195/197/200/202/
  203/205/207 surfaced at least one finding. SESSION 209's
  BC5 dogfood is the next test — composition-arc dogfood is
  a different shape than strategic-axis dogfood (two upstream
  arcs already validated; integration layer being tested
  for the first time end-to-end).

- **Composition arcs are the new shape.** First example: BC
  (B-2 ↔ B-3). Future composition candidates: B-2 ↔ B-14
  (Script-grounded publish bundles), B-1 ↔ B-3 (transcript-
  mined recipients → personalized batch), B-3 ↔ B-14 (per-
  recipient platform fan-out). When you see "X ↔ Y" in
  start-here candidates, plan ~½ the slice count of a
  strategic-axis arc.

- **Subagent delivery on tight contract briefs is reliable.**
  Two for two now (B2.5 + BC4). Pattern that works:
  exhaustive backend contract (request/response/status codes),
  enumerated test requirements, explicit constraints. The
  subagent doesn't need to make architectural decisions when
  the brief is tight enough.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- Collaboration conventions: AI drafts, human edits. Handoff
  `## Calibration moments worth carrying` + per-slice doc
  updates required at session end.
