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
> **Personalized Video (B-3):** `docs/design/PERSONALIZED_VIDEO_V1.md`.
> B3.0-B3.9 COMPLETE + REAL-MODE VALIDATED (SESSION 203).
> **Publish Bundle (B-14):** `docs/design/PUBLISH_BUNDLE_V1.md`.
> **B14.0-B14.5 COMPLETE + REAL-MODE VALIDATED (SESSION 205).**
> **Auto-Scripting (B-2):** `docs/design/AUTO_SCRIPTING_V1.md`.
> **B2.0 LOCKED + B2.1 + B2.2 SHIPPED (SESSION 206); B2.3 opens next.**
> **Last handoff:** `docs/handoffs/SESSION_205_D_ARC_LANDS.md`.

---

## SESSION 205 outcome — D-arc Publish Bundle shipped + real-mode validated

Fourth strategic-axis arc. Scope-lock cadence now **proven
4-for-4** (A/B/C/D arcs all landed in one extended session
including dogfood). Seven slices B14.0–B14.5; 8 contract
rules; 11 open questions all resolved as-proposed; one
operator-noticed UX limitation surfaced + documented as v2
axis (not a bug).

### Real-mode validation — two bundles, $0 spend

* Bundle 89a98aa8 (TikTok 720:1280): 1.5s ffmpeg wall-time;
  output dimensions correct; **operator-noticed off-center
  crop on a 16:9 cinematic source** (center-crop chopped
  off-center subjects).
* Bundle 9e0bb0df (LinkedIn 1280:720, same source): same
  wall-time; same-aspect target = trim-only = perfect output.

Both bundles auto-rolled to COMPLETED via the B14.3
cross-app `post_save` Composition signal. The cap-exclusion
mechanic (template_kind="publish_variant" filter in
get_usage) validated end-to-end — neither variant counted
against the monthly cap.

### Tests at SESSION 205 close

| Suite | Count |
|---|---|
| Django | 1269 (+24 vs SESSION 204) |
| - publish (new app) | 36 |
| - test_publish_variant | 18 |
| Media-engine | 214 (unchanged) |
| SPA vitest | 371 (+87) |

Real-mode spend SESSION 205: **$0** (both bundles
ffmpeg-only per rule 5).

### Calibration (2 new — 37 total)

1. **Scope-lock cadence now 4-for-4.** Cadence is
   load-bearing assumption, not aspirational. Strategic
   arcs ship in 4-10 hours of focused work + one dogfood
   pass.

2. **Aspect-changing crop is a recurring shape.** v1
   center-crops fine for avatar talking-head sources
   (subject pre-centered by Runway); cinematic /
   storyboard sources lose off-center subjects on
   aspect-changing variants. **v2 axis** (½ session):
   per-variant `offset_x` knob (-100..+100) to nudge the
   crop window. Pattern generalizes — primitives with
   "centered default" assumptions are audit candidates
   when cinematic sources arrive.

---

## SESSION 204 outcome — videos_per_month accounting migration

Cleanup session between strategic-axis arcs. SESSION 203's
B3.5 surfaced a latent seam: `videos_used` read the legacy
V6 Video shim, missing every Composition from V-arc / B-arc
/ C-arc. The per-month cap was effectively disabled for
modern callers.

**Single-function change** in `apps.billing.services.get_usage()`:
swap `Video.objects.filter(...)` for
`Composition.objects.filter(...).exclude(status=DRAFT)`.
Period + workspace filters unchanged. The V6 backwards-compat
shim itself stays — only the usage-counting read was migrated.

Updated 3 test sites that seeded Video rows to exercise the
cap (B3.5's 2 tests + R7.2's tier-limit test) and added 8 new
billing tests pinning the include/exclude semantics.

### Real-mode probe — concrete impact

Dev workspace before fix: `videos_used=2` (only 2 Video shim
rows in period). After fix: `videos_used=72` (correct count
of in-period non-DRAFT Compositions). The Starter cap of 10
was 62 under-counting reality. Any new launch from this
workspace will now correctly trip `video_limit_reached` until
period rolls over or tier upgrades.

### Tests at SESSION 204 close

| Suite | Count |
|---|---|
| Django | 1215 (+8 vs SESSION 203) |
| - billing (new file) | 8 |
| Media-engine | 214 (unchanged) |
| SPA vitest | 284 (unchanged) |

Real-mode spend SESSION 204: **$0**.

### Calibration (1 new — 35 total)

**`videos_per_month` was reading the wrong table.** Cleanup
between strategic arcs paid off — migration was ~1 hour of
focused work + 9 test updates + 8 new pinning tests. General
pattern: when a slice surfaces architectural debt that's
fixable in ~1 session AND would compound with the next
planned arc, doing the cleanup first beats pushing forward.

---

## SESSION 203 outcome — B-3 Personalized Video shipped + real-mode validated

Third strategic-axis arc in three consecutive sessions. The
scope-lock cadence (A-arc SESSIONS 185-192 → B-arc SESSION 202
→ C-arc SESSION 203) is now **proven 3-for-3**: 8-10 contract
rules + 7-10 slices + real-mode dogfood closing all land in
one extended session.

### Slices shipped

| # | Slice | Effort |
|---|---|---|
| B3.0 | Scope lock — 9 contract rules, 10 slices, 9 open Qs resolved | ½ session |
| B3.1 | `template_renderer` LLM-free helper + 24 tests | ½ session |
| B3.2 | `PersonalizedCampaign` + `PersonalizedRecipient` models + 11 tests | ½ session |
| B3.3 | CSV parser helper + 20 tests | ½ session |
| B3.4 | `CampaignViewSet` read + draft-edit surface + 20 tests | 1 session |
| B3.5 | `forecast` + `launch` endpoints (load-bearing) + 19 tests | 1 session |
| B3.6 | completion signal + per-recipient retry + 16 tests | ½ session |
| B3.7 | SPA `/workspace/campaigns` list + create + paste-CSV (subagent) | 1 session |
| B3.8 | SPA launch + forecast + recipient grid + retry + polling (subagent) | 1 session |
| B3.9 | Real-mode dogfood + arc close | ½ session |

Plus one post-close hotfix (`ffabde1`) for the B3.8
forecast cache-invalidation miss.

### Real-mode validation

Campaign `158dbe3f-...` ("B-3 smoke test") — 2 recipients
(Bob @ Acme, Carol @ Initech) against Marcus:

- **status: completed** ✓
- 36.2s wall-time, **$0.50 spend** (2 × $0.25)
- Both compositions completed in parallel
- B3.6 completion signal flipped both recipients +
  auto-rolled up the campaign to COMPLETED

All nine contract rules held end-to-end. The structural
moat is now demonstrable: per-workspace avatars rendering
"Hi {firstName}, saw {company} just hit {milestone}!" with
on-brand spokesperson identity — competitors with generic
LLM video can't deliver this.

### B3.8 post-close hotfix

Dogfood surfaced one bug at the SPA layer:
`useParseCsv` invalidated `campaign-recipients` + `campaign`
but missed `campaign-forecast`. Operator pasted CSV;
recipients persisted server-side; forecast panel kept
showing "0 recipients $0.00 total". One-line fix in
`useParseCsv.onSuccess` (`ffabde1`). Backend contract was
correct end-to-end.

### Tests at SESSION 203 close

| Suite | Count |
|---|---|
| Django | 1207 |
| - campaigns (new) | 66 |
| - character_os.test_template_renderer | 24 |
| - character_os.test_csv_recipients | 20 |
| Media-engine | 214 |
| SPA vitest | 284 |

Real-mode spend SESSION 203: **$0.50**.

### Calibration (3 new — 34 total)

1. **Scope-lock cadence proven 3-for-3.** Same shape across
   A/B/C arcs. Future strategic axes should plan around the
   same shape: ½-1 session per slice, 6-10 sessions total,
   scope-lock-first.

2. **React Query mutation onSuccess must invalidate EVERY
   dependent query.** Surfaced by B3.8 forecast bug. When a
   new query depends on a mutation's output, audit every
   existing mutation that affects the same underlying data.
   Forward-defense template added.

3. **Tier-gated batch caps work as designed — operator
   validation pre-launch.** Two-dimension gating (per-batch +
   per-month) pays off in the forecast modal. Generalizes:
   any new gate should land with a forecast / preview surface
   showing current usage + limit + projected outcome.

---

## FIRST THING (SESSION 206): operator picks

Three consecutive strategic-axis arcs landed (A: SESSIONS
185-192; B: SESSION 202; C: SESSION 203). The pattern is
proven cheap and reliable. Three natural next directions:

### New-arc candidates

1. **B-14 Multi-Platform Variants** — distribution
   stickiness. One render → reformatted variants for IG /
   TikTok / YT Shorts / LinkedIn. Builds on V9's
   `reformat_clip`. Composes naturally with B-3 (one
   personalized batch → 4 platform variants per recipient).
   5-6 slices estimated. **Recommended** as the natural
   composition with the just-shipped C-arc.
2. **B-1 v2 slices** — external transcript ingestion (.srt
   upload), batch mining, highlight chaining. Each is ~½ to
   1 session.
3. **A new B-* axis** from `CONTENT_FORMAT_BACKLOG.md` —
   B-2 (knowledge-driven auto-scripting), B-4 (audiogram /
   podcast clip), B-5 (kinetic typography). Each is its own
   arc.

### Asset upload UI (B-1 v2 enabler)

* **Asset upload UI for AUDIO / IMAGE / TRANSCRIPT** (1-2
  sessions). Unblocks B-1 v2 (external transcript
  ingestion) + the 8 legacy RAW_UPLOAD rows from SESSION
  185 backfill.

### Architectural debt cleared SESSION 204

* ~~`videos_per_month` count migration~~ — **DONE SESSION 204.**
  Migration shipped + 8 pinning tests. The per-month cap
  now reads Composition rows correctly.

### Deferred parity slices (unchanged)

* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).

### Recommended next direction

The strategic-axis trifecta is nearly complete:
* **B-1 (mine)** — done
* **B-3 (personalize)** — done
* **B-14 (distribute)** — done
* **B-2 (auto-script)** — the missing piece. Removes the
  "blank page" friction. Composes with B-1 (mine input
  context) + B-3 (auto-script the campaign template) +
  B-14 (distribute the result).

**B-2 Knowledge-driven auto-scripting** is the cleanest
next strategic-axis pick. ~6-8 slices per the proven
cadence.

Alternatives:
* **B-14 v2 `offset_x`** — ½ session; addresses the
  SESSION 205 dogfood finding while it's fresh.
* **Asset upload UI** — operator-content bottleneck;
  unblocks B-1 v2 external transcript ingestion.
* **B-1 v2** — incremental on already-shipped B-1.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete.
**V-arc 18/18 real-mode validated + UX polish complete**.
**Asset Library v1 COMPLETE + DOGFOOD VALIDATED**.
**Transcript Miner (B-1) v1 COMPLETE + REAL-MODE VALIDATED**.
**Personalized Video (B-3) v1 COMPLETE + REAL-MODE VALIDATED.**
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
| **Personalized Video v1 (B3.0-B3.9)** | **DONE + REAL-MODE VALIDATED** |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI | Queued |
| `videos_per_month` count migration | **DONE (SESSION 204)** |
| **Publish Bundle v1 (B14.0-B14.5)** | **DONE (SESSION 205) + REAL-MODE VALIDATED** |
| B-14 v2 offset_x knob | Queued (½ session; SESSION 205 dogfood finding) |
| **Auto-Scripting v1 (B2.0-B2.6)** | **B2.0 LOCKED + B2.1-B2.2 SHIPPED (SESSION 206); B2.3-B2.6 queued** |

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

**Pre-fire check (codified SESSION 200, extended SESSION 202+203)**:
restart Celery before any real-mode fire when the last commit
against ANY of these is newer than worker start:
* `shell/apps/compositions/primitives/`
* `shell/apps/*/signals.py` (now includes
  `apps/transcripts/signals.py`,
  `apps/campaigns/signals.py`)
* `shell/character_os/clients/media_engine.py`

Signals register only at `apps.py::ready()`; a stale worker
silently doesn't fire them.

**Smoke checks** (counts as of SESSION 203 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1269 tests

# Media-engine (from media-engine/)
python -m pytest                              # 214 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 371 vitest tests
```

**New surfaces from SESSION 203 (C-arc):**

* `apps.campaigns` Django app — `PersonalizedCampaign` +
  `PersonalizedRecipient` models, cross-workspace signal +
  Composition completion receiver. Migration `0001_initial`.
* `character_os/template_renderer.py` — `parse_placeholders`
  + `render_template` + `TemplateError`.
* `character_os/csv_recipients.py` — `parse_csv` +
  `derive_label`.
* `apps.campaigns.cost` — `PER_RECIPIENT_COST_MICROS=$0.25`
  + `estimate_campaign_cost_micros`.
* `apps.campaigns.services` — `check_personalized_batch`
  (two-dim tier gate) + `rollup_campaign_status` (campaign
  terminal-state rollup helper).
* `/api/campaigns/` — `CampaignViewSet` with create / list /
  retrieve / destroy / parse_csv / recipients / forecast /
  launch / retry_recipient actions.
* `/workspace/campaigns` + `/workspace/campaigns/new` +
  `/workspace/campaigns/:id` SPA routes with full launch
  flow + 5s polling + per-recipient retry.
* `web/src/lib/api/campaigns.ts` — Zod schemas + 9 React
  Query hooks (`useCampaigns`, `useCampaign`,
  `useCreateCampaign`, `useDeleteCampaign`, `useParseCsv`,
  `useRecipients`, `useCampaignForecast`,
  `useLaunchCampaign`, `useRetryRecipient`).
* `TIER_LIMITS["*"]["personalized_batch_max"]` extended:
  Starter=5, Pro=30, Agency=200.

---

## AI / assistant context

- **Last session: SESSION 205 — D-arc shipped in one session.**
  Seven slices B14.0–B14.5. Django 1215 → 1269 (+54).
  SPA 284 → 371 (+87). 2 new TRUST_CALIBRATION entries.
  $0 real-mode spend. Scope-lock cadence now 4-for-4.

- **Prior session: SESSION 204 — videos_per_month migration.**
  Cleanup between arcs. Django 1207 → 1215 (+8).

- **Prior session: SESSION 203 — C-arc shipped in one session.**
  Ten slices B3.0 through B3.9 + B3.8 post-close hotfix.
  Django 1097 → 1207 (+110). SPA 188 → 284 (+96). 3 new
  TRUST_CALIBRATION entries. $0.50 real-mode spend.

- **Scope-lock cadence is now 3-for-3** (A-arc, B-arc,
  C-arc). Pattern: 8-10 contract rules + 7-10 slices + per-
  slice tests + real-mode dogfood closing. Each arc lands in
  one extended session.

- **Calibration carried forward (37 total — +2 SESSION 205:
  scope-lock cadence 4-for-4 + aspect-changing crop is a
  recurring shape)**:
  V-arc 100% real-mode closure; operator-noticed-during-
  dogfood loop; mix_audio + intro_outro silent-base shapes;
  real-mode finds bugs in EVERY recipe (5-for-5 now —
  SESSIONS 195/197/200/202/203 all surfaced at least one);
  Celery worker doesn't auto-reload (3rd hit); mock-mode
  hides stream-shape drift (4th hit); forward-defense audits
  surface latent bugs cheaply; gpt-5 reasoning eats output
  budget (5th hit); scope-lock pattern compresses build
  phase (3-for-3 now); **React Query mutation onSuccess must
  invalidate every dependent query (NEW SESSION 203);**
  **tier-gated batch caps work as designed via the forecast
  preview surface (NEW SESSION 203).**

- **The "real-mode finds bugs in every recipe" pattern is
  now 5-for-5.** C-arc's bug was at the SPA cache layer
  (B3.8 forecast invalidation miss), not the backend.
  Generalizes: even when the backend pipeline is clean,
  expect at least one SPA-layer issue at dogfood time —
  often around cache invalidation, polling, or modal state.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
