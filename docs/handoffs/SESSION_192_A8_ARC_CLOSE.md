---
title: "Session 192 — A8 produced_assets cross-link + Asset Library v1 arc closes"
date: 2026-05-19
status: complete
session: 192
previous_handoff: ./SESSION_191_A6_ASSET_DETAIL_VIEW.md
arc_close: ASSET_LIBRARY_V1
---

# Session 192 — A8 + Asset Library v1 ARC CLOSE

## TL;DR

**Asset Library v1 arc CLOSED.** A8 ships as the final slice:
composition overview pages now list every Asset emitted by
the pipeline with role + storage-health badges + a "Final"
pill on the deliverable, each row linking to the A6 detail
view. Cross-link between Composition surface and Asset
surface is structurally complete.

**Arc spanned 7 sessions** (185-192) for 9 slices, all
shipped without scope creep or deferrals beyond the Q-a-6
v2 punt that was already on the table at lock.

Three commits today: feat(A8) + arc-close ceremony + handoff
+ design lock close. Test deltas across the arc:
**Django 915 → 995 (+80); SPA vitest 95 → 134 (+39)**.

## Session arc

### Slice — A8 (composition produced_assets cross-link)

#### What landed

**Backend** (`shell/`):

* `apps/compositions/serializers.py::CompositionSerializer`
  gains `produced_assets` `SerializerMethodField`. Light
  shape per row: `id`, `asset_type`, `role`, `title`,
  `file_path`, `storage_health` (live via A3's
  `compute_storage_health`), `is_final` (boolean — `true`
  for the Asset wired to `composition.final_asset`).
  Ordered by `Asset.created_at` so the SPA panel reads
  top-to-bottom as the pipeline executed. Empty array
  for compositions with no produced assets yet (draft
  state).
* `"produced_assets"` added to the serializer's `fields`
  tuple.
* New import: `from .assets import compute_storage_health`.

**SPA** (`web/`):

* `web/src/lib/api/recipes.ts` extended with
  `producedAssetSchema` Zod shape + `produced_assets:
  z.array(producedAssetSchema).default([])` on
  `compositionSchema`. `ProducedAsset` TS type exported.
* `web/src/routes/compositions/$id.tsx`:
  * `ProducedAssetsPanel` component renders the new
    section. Mirror's the F5 lineage panels' shape (rounded
    border, muted bg, lucide icon + section label, list of
    Link rows). Each row shows title (with file_path
    fallback), asset_type chip, role badge (snake_case
    flattened to space-separated for display), storage-
    health badge with colored tone, and a `Final` pill
    when `is_final`. Each row is a `Link to=/workspace/assets/<id>`.
  * Local `producedStorageTone(storage)` helper mirrors
    A5's `storageHealthTone` palette (emerald / amber /
    destructive / muted) without importing across routes —
    keeps `routes/compositions/$id.tsx` decoupled from
    `routes/workspace/assets.tsx`.
  * `<ProducedAssetsPanel>` renders between `<FinalAsset>`
    and the lineage panels in the page layout.

**Tests**:

* 3 backend tests in `apps/compositions/tests/test_v15_api.py`:
  * `test_retrieve_composition_includes_produced_assets`
    — mock-mode `talking_head` round-trips with every
    required field on the produced_assets entry.
  * `test_produced_assets_marks_only_final_with_is_final`
    — when the composition has multiple produced assets,
    only the one wired to `composition.final_asset`
    carries `is_final=True`.
  * `test_produced_assets_empty_for_draft_composition` —
    new Composition row with no emitted assets returns
    `produced_assets: []`.
* 3 SPA vitest tests in
  `web/src/lib/api/recipes.test.ts`:
  * Parses produced_assets array with all required fields.
  * Defaults to empty array when missing
    (backwards-compat for older composition rows).
  * Parses multiple produced assets with mixed `is_final`.

## Arc retrospective — Asset Library v1 (SESSIONS 185-192)

Closing the arc with the metrics + a calibration entry on
the growth template.

### Slice cadence

| Session | Slice | Effort | Status |
|---|---|---|---|
| 185 | drift-sweep + scope-lock + A0 + A1 | 1 session | ✓ + dev-DB --commit |
| 186 | A2 (primitives stamp role) | 1 session | ✓ |
| 187 | A3 (storage-health helper) | ½ session | ✓ |
| 188 | A4 (read endpoints) | ½ session | ✓ |
| 189 | A5 (SPA list view) | 1 session | ✓ (subagent) |
| 190 | A7 (picker role-filter — the structural fix) | ½ session | ✓ |
| 191 | A6 (SPA detail view) | 1 session | ✓ (subagent) |
| 192 | A8 (composition cross-link) + arc close | ½ session | ✓ + ARC CLOSED |

7 sessions. 9 slices. Zero deferrals. One scope-lock-time
Q-a-6 punt to v2 (Avatar/Voice/Portrait modeling).

### Test deltas across the arc

| Suite | Pre-A0 (SESSION 184) | Post-A8 (SESSION 192) | Delta |
|---|---|---|---|
| Django | 915 | **995** | **+80** |
| - compositions | 484 | **564** | **+80** |
| Media-engine | 194 | 194 | unchanged |
| SPA vitest | 95 | **134** | **+39** |

Backend grew 8.7% (~80 tests across 7 sessions); SPA grew
41% (+39 tests, driven by the A5 list view's 25-test
fixture). Both numbers represent structural enforcement, not
just coverage padding — contract rule 20 (A2) and the
role-filter coverage (A7) are statically enforced via AST
scans + endpoint shape tests.

### What worked

(Captured as a new TRUST_CALIBRATION entry — see
`docs/TRUST_CALIBRATION.md` "A-arc growth template".)

* **Backend before SPA**: A0 → A4 covered the entire backend
  in 4 sessions. SPA started at A5 against a stable
  endpoint. No backend reshape after SPA started.
* **One-runner-emit, many-callers** (SESSION 186 A2
  calibration): adding `role` to `PrimitiveResult` covered
  28+ emit paths via the single
  `_persist_output_asset` funnel.
* **Subagent delegation for SPA slices** (A5 + A6):
  `react-web-delivery` agent succeeded with high precision
  once briefs pointed at source-of-truth files rather than
  restating values. Two new calibrations from this arc
  (subagent-source-of-truth, A-arc growth template).
* **Operator-visible payoff prioritized mid-arc**: A7
  jumped ahead of A6 at SESSION 190 slice-open. Arc
  continuity resumed for A6/A8.
* **CONTENT_FORMAT_BACKLOG.md tracked**: a parallel-agent
  research artifact that sat untracked across SESSIONS
  186-191 now landed in git as a permanent backlog
  reference (SESSION 191 commit `ea40bad`).

### What didn't surprise (but is worth noting)

* **TypeScript strict-mode bites at `pnpm build`, not
  `pnpm test`**: recurring across A4 + A5 + A7. The
  existing "SPA gates need both pnpm test AND pnpm build"
  calibration covers it; no new entry was needed.
* **Pyright Django-attribute noise is permanent ambient
  fog**: every session's `views.py`-touching slice triggers
  the same `workspace_id` / `composition_id` / `steps` /
  `produced_assets` "attribute unknown" warnings. They
  haven't blocked anything across the arc.

## Calibration moments worth carrying

One new TRUST_CALIBRATION entry appended at close —
**A-arc growth template** documenting the 9-slice /
½-session-each / backend-then-SPA shape that worked.
Generalizes to future arcs of similar shape.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **995** | +3 (992 → 995) |
| - compositions | **564** | +3 (561 → 564) |
| Media-engine | 194 | unchanged |
| **SPA vitest** | **134** | **+3 (131 → 134)** |

Real-mode spend SESSION 192: **$0** (serializer + SPA panel
+ tests; no API calls).

## Phase status

**Phase 4 + Asset Library v1 all complete.** Status table:

| Arc | Status |
|---|---|
| K (Knowledge layer) | K1-K9 done; K10 → F8.1 queued |
| V (Video composition) | COMPLETE + 16/18 recipes real-mode validated |
| F (Workspace fabric) | COMPLETE |
| R (Realtime avatar) | COMPLETE + real-mode validated |
| **A (Asset Library v1)** | **COMPLETE (SESSION 192)** |

The next layered arc / feature is operator-pick. Backlog
items queued in start-here remain unchanged: V18 polish,
F8.1 K10 seed corpus, V17.3 keyframes (deferred SESSION
184), B6-B10 brand arc, K7.x v3 YouTube oEmbed, K6.4 v3,
Thruman cleanup, W12 legacy form retirement, Asset upload
UI, smoke `--save-assets` opt-in. Plus the 20-item
`CONTENT_FORMAT_BACKLOG.md` catalog (tracked SESSION 191).

## Operational notes for SESSION 193

* **No arc in flight.** Start-here lists the queued
  backlog items + recommends the operator picks the next
  arc / feature direction.
* **Real-mode dogfood opportunity.** Asset Library v1 is
  end-to-end usable against the dev DB (128 backfilled
  assets). The arc-close dogfood pass per the SESSION 191
  start-here recommendation:
  1. Open `http://localhost:5174/workspace/assets` — see
     all 128 assets across 8 roles.
  2. Click any row → detail page (A6) with media preview
     + metadata + lineage.
  3. Open `/recipes/talking_head_with_backdrop` — the
     backdrop_clip_id picker shows only the 42
     BACKDROP-tagged clips (A7).
  4. Fire a composition. Its overview page lists the
     produced assets with role badges + Final pill (A8).
  End-to-end Asset Library v1 verification in one
  session, $0 real-mode spend if you use mock_mode.
* **No Celery worker concern** — A8 didn't touch primitive
  emit shape or any consumed-by-worker module.
