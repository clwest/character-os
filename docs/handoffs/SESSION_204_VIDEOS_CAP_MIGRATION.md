---
title: "Session 204 — videos_per_month accounting migration (V6 shim → Composition)"
date: 2026-05-20
status: complete
session: 204
previous_handoff: ./SESSION_203_C_ARC_LANDS.md
---

# Session 204 — videos_per_month migration

## TL;DR

Cleanup session between strategic-axis arcs. SESSION 203 (B-3
launch slice) surfaced a real seam: `videos_used` counted the
legacy V6 Video shim, not Composition rows. The V-arc, B-arc,
and C-arc all bypass the shim, so the per-month cap was
effectively disabled for everything except the few legacy
callers. This session fixes the seam in ~1 hour of focused work.

**Concrete impact** on the dev DB: pre-migration probe showed
`videos_used=2` (only 2 Video shim rows in period);
post-migration shows `videos_used=72` (the correct count of
in-period compositions excluding DRAFT). The Starter cap of 10
was effectively disabled.

Tests at close: **Django 1207 → 1215 (+8)**; SPA + media-engine
unchanged. No real-mode spend.

## What landed

### Migration: `apps.billing.services.get_usage()`

Replaced the Video shim query with a Composition query:

```python
# Before
videos_used = Video.objects.filter(
    spokesperson__workspace=workspace,
    created_at__gte=sub.current_period_start,
    created_at__lt=sub.current_period_end,
).count()

# After
videos_used = Composition.objects.filter(
    workspace=workspace,
    created_at__gte=sub.current_period_start,
    created_at__lt=sub.current_period_end,
).exclude(status=CompositionStatus.DRAFT).count()
```

Semantics:

* **Counts**: PLANNING / RUNNING / COMPLETED / PARTIAL / FAILED
  (any non-DRAFT). Operator pressed render → resources held →
  counts against the cap.
* **Excludes**: DRAFT (never fired).
* **Period filter**: same `current_period_start` / `current_period_end`
  semantics.
* **Workspace filter**: direct FK (Composition has its own
  workspace FK; no need to walk through spokesperson like the
  legacy Video query did).

The `apps.videos.Video` import was removed from `services.py`
(no other callers in that module). The Video shim model itself
stays — it's still used by the V6 backwards-compat path; only
the usage-counting read was migrated.

### Test updates

Three call sites that seeded Video rows to exercise the cap
were migrated to seed Compositions:

* `apps/campaigns/tests/test_launch.py` — 2 tests
  (`test_check_personalized_batch_under_batch_but_over_month_raises`
  + `test_launch_over_month_cap_returns_402`).
* `apps/realtime/tests/test_r7_2_async_tools.py` — 1 test
  (`test_render_video_tier_limit_exceeded_failed`).

### New pinning tests

`apps/billing/test_services.py` (new file, 8 tests):

1. Counts COMPLETED compositions in period.
2. Counts PLANNING/RUNNING/COMPLETED/PARTIAL/FAILED.
3. Excludes DRAFT.
4. Excludes out-of-period compositions.
5. Excludes cross-workspace compositions.
6. Legacy Video rows are NOT counted (deprecation pin).
7. `check_video_limit` raises at the new threshold (10 cap).
8. `check_video_limit` passes under cap.

### Isolation allowlist updated

Two new entries — `apps/billing/test_services.py` (seeds
Compositions directly) and `apps/realtime/tests/test_r7_2_async_tools.py`
(same test that now seeds Composition instead of Video).

## Real-mode validation

Direct probe of the dev workspace's usage after migration:

```
workspace: Admin's workspace
  tier: starter
  videos_used: 72       ← was 2 pre-migration
  videos_limit: 10
  period: 2026-05-14 → 2026-06-13
```

Correct count surfaced. The workspace is 62 OVER its Starter
cap from accumulated dogfood work — which is **the correct
behavior**. Any new C-arc launch from this workspace will
correctly trip `video_limit_reached` until the period rolls
over (or tier upgrades).

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1215** | +8 (1207 → 1215) |
| - billing (new file) | 8 | new |
| Media-engine | 214 | unchanged |
| SPA vitest | 284 | unchanged |

No real-mode spend.

## Calibration moments worth carrying

**One new TRUST_CALIBRATION entry (35 total)**:

**`videos_per_month` was reading the wrong table.** Migration
was a single-function change + test sweep. SESSION 203 close
explicitly suggested SESSION 204 do the cleanup before
opening B-14; this paid off. General pattern: when a slice
surfaces architectural debt that's fixable in ~1 session AND
would compound with the next arc, doing the cleanup first
beats pushing forward. "Tidy the house" between strategic
arcs pays compound interest.

## What's still queued

The B-14 / B-2 / Asset upload UI candidates remain. The
architectural-debt slot is now empty.

### Recommended next direction

**B-14 Multi-Platform Variants** — composes naturally with
the C-arc that just shipped (one personalized batch → N
recipients × 4 platform variants = dense per-month
accounting that now works correctly). The migration this
session made that composition safe.

Alternative: **Asset upload UI** if the operator wants a
quick operator-visible win before another strategic arc.

## Operational notes

* The dev workspace's reported `videos_used=72` is real and
  correct. Any composition fire from this workspace will now
  trip the Starter cap. For continued dogfood, either:
  * Upgrade the dev workspace's subscription to Pro (cap=30)
    or Agency (unlimited) via the admin.
  * Wait for the period rollover at `2026-06-13`.
  * Open a fresh workspace.
* The V6 backwards-compat path (Composition → Video shim
  signal) still runs at composition-create time; it just
  doesn't drive usage counting anymore. No deprecation of
  the shim itself yet.
* The pre-fire Celery restart check still applies for B-14
  (or any future arc) — `apps/campaigns/signals.py`
  needs Celery to know about it via `apps.py::ready()`.
