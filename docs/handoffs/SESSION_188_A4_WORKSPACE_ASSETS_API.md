---
title: "Session 188 — A4 workspace assets read API"
date: 2026-05-19
status: complete
session: 188
previous_handoff: ./SESSION_187_A3_STORAGE_HEALTH.md
---

# Session 188 — A4 workspace assets API

## TL;DR

Clean single-slice session. One feature commit + handoff close.
**A4 ships**: `GET /api/workspace/assets/` (paginated browse) +
`GET /api/workspace/assets/<id>/` (detail with full lineage).
All v1 backend layers for the Asset Library now complete (A0+A1
+A2+A3+A4) — A5 can start the SPA against a live endpoint.

Test totals **956 → 980 (+24)** — all 24 new tests in
`test_workspace_assets_api.py`. Compositions suite **525 → 549**.
INVENTORY grew by 52 bytes (2 new routes registered). No
real-mode spend.

## Session arc

### Slice — A4 (workspace assets read endpoints)

#### Architectural decisions

* **Distinct URL space from existing `/api/assets/`.** The V15.2
  asset_picker uses `/api/assets/` with a 200-row cap and no
  pagination. A4 ships at `/api/workspace/assets/` (matches the
  scope-lock URL). A7 will extend the picker endpoint with the
  role filter; A5/A6 build against A4.
* **Hand-mounted paths instead of DRF router.** The viewset has
  only `list` + `retrieve`, no other REST verbs. Two explicit
  `path()` entries are clearer than a DefaultRouter under a
  prefix.
* **Workspace resolution mirrors F-arc's `workspace_overview`.**
  Explicit `?workspace=<id>` if provided + member, else
  `default_workspace_for(user)`. Same `NotFound` / `PermissionDenied`
  /`ValidationError` shapes so SPA error handling lines up.
* **Storage filter is post-query.** `storage_health` is computed
  (no DB column), so the filter runs after query-time filters
  narrow the candidate set. 1000-row cap before storage filtering
  to stay sane on huge workspaces — A5 perf testing may motivate
  an annotated column later.
* **Lineage shape inverted from F5.** F5's
  `/api/compositions/<id>/lineage/` walks
  composition→composition; A4's retrieve walks
  asset→compositions on both sides. Producing composition +
  producing step + downstream consumers (compositions whose
  step inputs reference this asset's id).

#### What landed

* **`WorkspaceAssetViewSet`** in `apps/compositions/views.py` —
  GenericViewSet with custom `list` + `retrieve`. Inline
  serialization (no separate serializers module dep —
  matches existing pattern from `AssetViewSet` / `ImageViewSet`).
* **`WorkspaceAssetPagination`** — PageNumberPagination subclass.
  `page_size=25`, `max_page_size=100`, `page_size_query_param="page_size"`.
* **`_resolve_workspace(request)`** — workspace resolution
  helper mirroring `apps.accounts.views.workspace_overview`.
* **`_csv_param(request, name)`** — comma-list query param
  parser. Returns `None` when absent so callers can skip the
  filter cleanly.
* **`_producing_prompt(asset)`** — best-effort extraction of
  prompt/script/description text from `source_spec` (top-level
  → `params.*` fallback). Different primitives stash prompts
  under different keys; the helper handles the common shapes
  the SPA list view will care about.
* **`_serialize_list_asset(asset)`** + **`_serialize_detail_asset(asset)`** —
  inline serializers. List shape: id, asset_type, role, file_path,
  title, subject, duration_ms, width, height, mime_type,
  size_bytes, cost_micros, created_at, storage_health (A3),
  primitive_kind, producing_prompt, composition (id+name+status+kind).
  Detail shape adds producing_step (id, position, primitive,
  params, inputs, source_spec) + downstream_compositions.
* **URLs in `apps/compositions/urls.py`** — two new paths:
  `workspace/assets/` → list, `workspace/assets/<uuid:pk>/` →
  retrieve.
* **`test_workspace_assets_api.py`** — 24 tests across:
  * Auth gate (unauthenticated → 401/403).
  * Workspace scoping (non-member 403, unknown ws 404,
    cross-workspace leakage prevention, default workspace
    fallback).
  * List shape (storage_health attached, producing
    composition attached, producing_prompt falls through
    to params).
  * Each filter individually (role / asset_type /
    primitive_kind / storage with a valid state + with
    invalid state / q against composition name + asset
    title / created_after / created_before).
  * Pagination (default 25, page_size override, page
    navigation with disjoint result sets).
  * Retrieve (full lineage shape, downstream consumers
    via step inputs scan, cross-workspace 404, unknown id
    404).
* **`test_isolation.py` ALLOWED_FILES** — entry added for
  the new test (sanctioned writer; constructs Composition +
  Step + Asset rows for endpoint exercise; workspace anchor
  preserved at every create).

#### Bug caught during test run

The storage-filter branch with all-invalid-state values
short-circuited via `paginator.get_paginated_response([])`
without first calling `paginate_queryset` — the paginator
needs `self.page` set first. Fixed by routing both branches
(valid wanted set + all-invalid wanted set) through
`paginator.paginate_queryset(rows, ...)` with an empty
`rows` list in the all-invalid case. Caught by
`test_storage_filter_with_unknown_state_returns_empty` on
first run.

## Calibration moments worth carrying

No new calibration entries — A4 was a well-scoped endpoint
slice using established F-arc patterns (`workspace_overview`
shape) + the SESSION 187 storage_health helper.

The single bug caught (paginator's `self.page` requirement)
is a DRF API quirk, not a project-shape calibration —
not worth a TRUST_CALIBRATION entry.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **980** | +24 (956 → 980) |
| - compositions | **549** | +24 (525 → 549) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

Real-mode spend SESSION 188: **$0** (endpoint + tests only).

## Phase 4 / Asset Library arc status

| Slice | Status |
|---|---|
| **A0** Asset.role enum + migration | **✓ SHIPPED (SESSION 185)** |
| **A1** backfill_asset_roles command | **✓ SHIPPED + COMMITTED on dev DB (SESSION 185)** |
| **A2** every primitive stamps role at emit | **✓ SHIPPED (SESSION 186)** |
| **A3** storage-health helper | **✓ SHIPPED (SESSION 187)** |
| **A4** read-only `/api/workspace/assets/` endpoints | **✓ SHIPPED (SESSION 188)** |
| A5 SPA `/workspace/assets` list view | pending (next; 1 session) |
| A6 SPA per-asset detail view | pending (1 session) |
| A7 asset_picker role-filter | pending (operator-visible payoff; ½ session) |
| A8 F-arc composition-lineage cross-link | pending (½ session) |

**Backend layer complete (A0+A1+A2+A3+A4).** A5 can start the
SPA against a live endpoint. The operator-visible payoff lands
with A7 (role-filtered asset_picker dropdown) — but A5/A6 ship
the browse + detail surface the operator interacts with daily.

## Operational notes for SESSION 189

* **No backend stack changes** — A4 is additive (new endpoint,
  no schema migration, no Celery task touched). Worker can
  remain at SESSION 186's restart state.
* **Frontend stack-up required for A5.** `pnpm dev` for the
  SPA at :5174. SPA Zod schemas for the new endpoint will
  need fresh definitions per the SPA scope lock's per-route
  pattern; cf. `web/src/lib/api/` directory shape.
* **The endpoint is browsable now** —
  `curl -H "Cookie: sessionid=..." 'http://localhost:8000/api/workspace/assets/'`
  returns the live shape A5's Zod schema must mirror. Spot-
  check shape against `_serialize_list_asset` / `_serialize_detail_asset`
  in `apps/compositions/views.py`.
* **A5 estimated effort: 1 session.** Larger than A1-A4
  (each ½ session) because it spans Zod schemas + React Query
  hooks + page route + filter chips + pagination controls +
  per-row card. The SPA scope lock's `react-web-delivery`
  agent (`@/.claude/agents/react-web-delivery`) is the
  default tool for this kind of slice.
