---
title: "Session 205 — D-arc Publish Bundle shipped + real-mode validated"
date: 2026-05-20
status: complete
session: 205
previous_handoff: ./SESSION_204_VIDEOS_CAP_MIGRATION.md
---

# Session 205 — B-14 Publish Bundle arc landed end-to-end

## TL;DR

Fourth strategic-axis arc. The scope-lock cadence is now
**proven 4-for-4** (A-arc SESSIONS 185-192 → B-arc SESSION 202
→ C-arc SESSION 203 → D-arc SESSION 205). 8 contract rules +
7 slices + real-mode dogfood all landed in one extended
session.

**B-14 Publish Bundle shipped all 7 slices.** Operator can
now select a CLIP source from the workspace, pick from a
5-platform catalog (Reels / Shorts / TikTok / X / LinkedIn),
preview the $0 cost + wall-time forecast, launch the
bundle, watch progress live via 5s polling, and retry
failed variants. All ffmpeg — **zero Runway spend, ~1.5s
wall-time per variant**.

One operator-noticed quality finding surfaced during dogfood
(not a bug; documented as a v1 UX limitation). Pattern now
6-for-6 on "real-mode finds bugs in EVERY recipe" across
SESSIONS 195/197/200/202/203/205 — except this one's a
UX limitation, not a bug.

Tests at close: Django **1245 → 1269 (+24)**; SPA vitest
**284 → 371 (+87)**; media-engine unchanged at 214.

## What landed

Seven slices across the day:

### B14.0 — scope lock (`docs/design/PUBLISH_BUNDLE_V1.md`)

Eight contract rules + seven implementation slices. All 11
open questions resolved with proposed defaults; operator
accepted as-proposed.

### B14.1 — platform catalog + `publish_variant` recipe + cap exclusion

* `apps/compositions/platform_catalog.py` — closed v1
  catalog (Reels/Shorts/TikTok/X/LinkedIn) with `Platform`
  dataclass, `get_platform()` / `all_platform_keys()` /
  `all_platforms()` helpers, `MAX_PLATFORMS_PER_BUNDLE=10`
  defense-in-depth cap, `PUBLISH_VARIANT_TEMPLATE_KIND`
  constant.
* `apps/compositions/starters.py` — new `publish_variant`
  starter: 2-step (trim_clip → reformat_clip). Trim window
  = `min(source.duration_ms, max_duration_ms)`.
  `template_kind="publish_variant"` enables SESSION 204's
  cap-exclusion (rule 5).
* `apps/billing/services.py` — `get_usage()` extended to
  exclude `template_kind=publish_variant` from
  `videos_per_month` count. The 1-line addition the
  SESSION 204 cleanup made structurally clean.
* 18 tests.

### B14.2 — `PublishBundle` + `PublishVariant` models

* New `apps.publish` Django app.
* 6-state bundle machine (DRAFT/LAUNCHING/IN_FLIGHT/
  COMPLETED/PARTIAL/FAILED); 5-state variant machine.
* Cross-workspace guards at 2 layers (`clean()` +
  `pre_save` signal).
* UniqueConstraint on `(bundle, platform_key)`.
* Snapshotted `target_ratio` + `max_duration_ms` on variant
  rows (rule 7 — old bundles render at original specs).
* 12 tests.

### B14.3 — REST + completion signal + per-variant retry

* `PublishBundleViewSet` with 8 actions: create / list /
  retrieve / destroy / variants / forecast / launch /
  retry_variant.
* `apps.publish.services` — `check_bundle_platforms`,
  `estimate_bundle_wall_time_s(~5s/variant)`,
  `rollup_bundle_status`.
* Cross-app `post_save` Composition receiver flips variants
  + rolls up bundle. Mirrors C-arc's pattern.
* `_resolve_source_spokesperson` helper walks
  `Asset.produced_by_step → Composition.spokesperson`
  lineage; falls back to workspace's first spokesperson.
* 24 tests.

### B14.4 — SPA list + create + detail + launch (subagent)

* Three new routes: `/workspace/bundles`,
  `/workspace/bundles/new`, `/workspace/bundles/<id>`.
* `web/src/lib/api/bundles.ts` with 9 hooks +
  `PLATFORM_CATALOG` hardcoded (closed catalog v1 per
  rule 7).
* Asset detail (A6) extended: "Publish bundle" CTA on
  CLIP-type assets links to
  `/workspace/bundles/new?source_clip_id=<id>` for the
  source-clip-first entry point per Q-d-8.
* 5s polling on LAUNCHING/IN_FLIGHT; inline LaunchModal
  (no Radix) mirroring B3.8 exactly.
* **Triple-invalidation explicitly tested** per the
  SESSION 203 calibration about React Query mutation
  invalidation requiring every dependent query.
* +87 vitest tests via react-web-delivery subagent.

### B14.5 — real-mode dogfood + arc close

Two bundles fired against the SESSION 197 storyboard_voiced
output (`8abd8a1f`, 18.1s 16:9 cinematic w/ Dog Food Coffee
House outro):

| Bundle | Platform | Target | Wall-time | Cost | Result |
|---|---|---|---|---|---|
| 89a98aa8 | TikTok | 720×1280 | 1.5s | $0.0001 | ✓ ran; **off-center crop on source** |
| 9e0bb0df | LinkedIn | 1280×720 | 1.5s | $0.0001 | ✓ ran; same-aspect = trim only = perfect |

**Pipeline validated end-to-end**:
- `template_kind=publish_variant` ✓ (cap exclusion works)
- 2-step composition (trim + reformat) ✓
- Output dimensions correct for both target ratios ✓
- Completion signal auto-rolled both bundles to COMPLETED ✓
- $0 real spend (ffmpeg-only per rule 5) ✓

**Operator-noticed UX finding** (not a bug — documented as
v1 limitation): TikTok variant from a 16:9 cinematic source
center-cropped, losing the off-center subjects (coffee
maker + person). The LinkedIn variant (16:9 → 16:9) was
perfect because no aspect change. Captured as **v2 axis**:
per-variant `offset_x` knob (-100..+100) to nudge the crop
window.

## Tests at session close

| Suite | Count | Delta vs SESSION 204 |
|---|---|---|
| Django | **1269** | +24 |
| - publish (new app) | 36 | new (12 model + 24 API) |
| - test_publish_variant | 18 | new |
| Media-engine | 214 | unchanged |
| SPA vitest | **371** | +87 |

`pnpm build` clean. Real-mode spend: **$0** (both bundles
ffmpeg-only).

## Calibration moments worth carrying

**Two new TRUST_CALIBRATION entries (37 total)**:

1. **Scope-lock cadence is now 4-for-4.** Same shape across
   A/B/C/D arcs. Future strategic axes (B-2, B-1 v2,
   B-14 v2 offset_x) should plan around the proven shape:
   8-10 contract rules + 7-10 slices + closing dogfood +
   real-mode validation, all in one extended session.

2. **Aspect-changing crop is a recurring shape.** B-14 v1
   center-crops on aspect change; avatar talking-head
   sources are pre-centered by Runway so this works fine,
   but cinematic / storyboard sources need a way to nudge
   the crop window. **v2 axis** (½ session): per-variant
   `offset_x` knob on PublishVariant + the SPA picker +
   ffmpeg crop parameterization. Pattern generalizes:
   primitives with "centered default" assumptions
   (composite_video pip, intro_outro card placement) are
   audit candidates when cinematic sources land.

## What's still queued

### Bigger backlog items (unchanged)

* **Asset upload UI** (1-2 sessions) — operator-content
  bottleneck.
* **B-1 v2 slices** — external transcripts, batch mining,
  highlight chaining.
* **B-2 Knowledge-driven auto-scripting** — strategic axis;
  removes the "blank page" friction.
* **B-14 v2 offset_x** — ½ session; addresses the SESSION
  205 dogfood finding.
* **B-3 ↔ B-14 composition** (auto-fire bundles from a
  personalized campaign launch) — Q-d-5 deferred from
  scope-lock.

### Architectural debt (none surfaced this session)

### Recommended next direction

The D-arc validates that **every primitive a customer
touches now has a polished operator workflow**. Natural
next moves:

1. **B-2 Knowledge-driven auto-scripting** — closes the
   strategic-axis trifecta (B-1 mines, B-3 personalizes,
   B-14 distributes; B-2 *generates* the input). 6-8 slices.
2. **B-14 v2 `offset_x`** — addresses the dogfood
   finding while it's fresh. ½ session.
3. **B-1 v2** — original-audio extraction, batch mining,
   highlight chaining.
4. **Asset upload UI** — operator-content bottleneck.

## Operational notes for the next session

* Dev DB now carries 2 PublishBundle rows + 2 PublishVariant
  rows from the dogfood. Browseable via
  `/workspace/bundles`.
* The 2 new platform-variant assets (`f7586e66`,
  `d2400234`) are in `/workspace/assets` with
  `role=POLISH_OUTPUT` (since reformat_clip stamps that
  role on its output).
* `apps.publish` carries 36 backend tests + 87 SPA tests.
* Pre-fire Celery restart rule still applies — any
  primitive / signals change in any of:
  `shell/apps/compositions/primitives/`,
  `shell/apps/*/signals.py`,
  `shell/character_os/clients/media_engine.py` needs
  a worker restart before real-mode fires.
