---
title: "Session 191 — A6 SPA per-asset detail view"
date: 2026-05-19
status: complete
session: 191
previous_handoff: ./SESSION_190_A7_PICKER_ROLE_FILTER.md
---

# Session 191 — A6 SPA per-asset detail view

## TL;DR

Clean single-slice session. One feature commit + handoff close.
**A6 ships**: `/workspace/assets/:id` detail page with media
preview, full metadata table, lineage section, copy + download
actions. Asset Library v1 arc now at **8 of 9 slices shipped**
— only A8 (composition lineage cross-link) remains.

Delegated to the `react-web-delivery` subagent. Agent made a
load-bearing backend tweak — added `inline_content` to
`_serialize_detail_asset` so TRANSCRIPT assets render their
text body in the detail view. Agent shipped 2 backend tests
covering the new field.

Backend tests **990 → 992 (+2)**; SPA vitest **125 → 131 (+6)**.
`pnpm build` clean. No real-mode spend.

## Session arc

### Slice — A6 (per-asset detail view)

#### Delegation decision

Same shape as A5 — SPA + Zod + React Query against a known
backend endpoint. Delegated to `react-web-delivery` per the
SESSION 190 start-here recommendation; agent succeeded with
one operator-decision flagged in advance (the `inline_content`
question) and resolved it correctly during the slice.

#### What landed

**Frontend** (`web/`):

* **`web/src/lib/api/workspace-assets.ts` extended**:
  * `producingStepSchema` — id, position, primitive, params
    (`z.record(z.string(), z.unknown())`), inputs
    (`z.array(z.unknown())`), source_spec (nullable record).
    The `source_spec` nullable came from spotting that the
    backend's `asset.source_spec` field allows null at the
    model level.
  * `downstreamCompositionSchema` — id, name, status,
    template_kind.
  * `workspaceAssetDetailSchema` — list schema + `producing_step`
    (nullable) + `downstream_compositions` (array) +
    `inline_content` (always present, defaults to `""` for
    non-TRANSCRIPT).
  * `getWorkspaceAsset(id, workspace?)` async + `useWorkspaceAsset`
    React Query hook. Query key `["workspace-asset", id,
    workspace ?? null]`; 20s staleTime matches list hook.
* **New page `web/src/routes/workspace/assets.$id.tsx`**:
  * Page header with back-link to `/workspace/assets`, title
    fallback chain (title → subject → "Untitled asset"),
    role badge + storage-health badge + asset_type chip.
  * Media preview switches on `asset_type`:
    * `image` → `<img src={file_path}>` (handles data URIs
      naturally).
    * `clip` → `<video controls src={file_path}>`.
    * `audio` → `<audio controls src={file_path}>`.
    * `voice` → small panel showing the Runway voice id +
      hint that previews live on the spokesperson edit modal
      (file_path isn't a URL for VOICE assets).
    * `transcript` → scrollable `<pre>` rendering
      `inline_content`.
    * `https_expired` storage state shows a warning overlay
      over a generic icon instead of trying to load a
      busted URL.
  * Metadata table with copy buttons for id + file_path.
    Formatted: duration ms → `12.5s` / `1m 23s`; size bytes
    → KB/MB; cost_micros / 1_000_000 → `$0.001`; created_at
    full date.
  * Lineage section — two sub-panels:
    * **Produced by**: composition card (link to
      `/compositions/<id>`) + producing step expand
      (primitive, position, params as small `<pre>` JSON,
      inputs as small `<pre>` JSON).
    * **Used downstream by**: cards for each downstream
      consumer composition. Empty state: "Not yet used in
      another composition."
  * Loading skeleton, error retry, 404 state.
* **`web/src/App.tsx`** — `WorkspaceAssetDetailRoute`
  registered at `/workspace/assets/:id` after the list
  route.
* **`web/src/routes/workspace/assets.tsx`** — A5's `AssetRow`
  title is now wrapped in a `Link` to the detail page. Row
  gains a hover state. No other A5 behavior changed.

**Backend** (`shell/`):

* **`apps/compositions/views.py`** — `_serialize_detail_asset`
  adds `base["inline_content"] = asset.inline_content`. The
  list serializer intentionally omits inline_content for
  performance; the detail path needs it for TRANSCRIPT
  rendering.

**Tests**:

* 6 SPA vitest in `web/src/lib/api/workspace-assets.test.ts`:
  detail schema parses well-formed payload, null
  producing_step, empty downstream_compositions, with
  inline_content; `getWorkspaceAsset` URL construction
  with + without workspace param.
* 2 backend tests in
  `apps/compositions/tests/test_workspace_assets_api.py`:
  TRANSCRIPT body surfaces in detail response; non-TRANSCRIPT
  returns empty string.

#### Operator decisions resolved in-slice

* **TRANSCRIPT `inline_content` exposure** — flagged in the
  brief with two options (backend serializer tweak vs link
  out). Agent chose the backend tweak per the operator hint;
  one line added + 2 backend tests + Zod field. Resolved.
* **Back-link filter preservation** — brief asked whether to
  preserve search params. Agent matched
  `knowledge.$id.tsx`'s plain `Link to="/workspace/assets"`
  pattern; browser Back restores filter URL state. No new
  state mechanism added. Right call.

## Calibration moments worth carrying

No new TRUST_CALIBRATION entries. A6 reused the
`react-web-delivery` delegation pattern that already
calibrated through A5; the operator-decision-resolved-in-slice
flow worked as intended (brief surfaces the ambiguity, agent
picks under the operator's stated preference).

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **992** | +2 (990 → 992) |
| - compositions | **561** | +2 (559 → 561) |
| Media-engine | 194 | unchanged |
| **SPA vitest** | **131** | **+6 (125 → 131)** |

Real-mode spend SESSION 191: **$0**.

## Phase 4 / Asset Library arc status

| Slice | Status |
|---|---|
| **A0** Asset.role enum + migration | **✓ SHIPPED (SESSION 185)** |
| **A1** backfill_asset_roles command | **✓ SHIPPED (SESSION 185)** |
| **A2** every primitive stamps role at emit | **✓ SHIPPED (SESSION 186)** |
| **A3** storage-health helper | **✓ SHIPPED (SESSION 187)** |
| **A4** read-only `/api/workspace/assets/` endpoints | **✓ SHIPPED (SESSION 188)** |
| **A5** SPA `/workspace/assets` list view | **✓ SHIPPED (SESSION 189)** |
| **A6** SPA per-asset detail view | **✓ SHIPPED (SESSION 191)** |
| **A7** asset_picker role-filter | **✓ SHIPPED (SESSION 190)** |
| A8 F-arc composition-lineage cross-link | pending (next; ½ session — arc closer) |

**8 of 9 slices shipped.** A8 closes the arc.

## Operational notes for SESSION 192

* **A8 is the arc-closer** — composition overview pages get
  a "Produced assets" section showing each output Asset
  with its role badge + a link to the A6 detail view.
  Backend: extend
  `apps/compositions/serializers.py::CompositionSerializer`
  with a `produced_assets` field. SPA: extend
  `web/src/routes/compositions/$id.tsx`. ½-session estimate.
* **Arc-close ceremony** when A8 ships:
  * Regen INVENTORY one final time.
  * TRUST_CALIBRATION entry summarizing the A-arc growth
    template (similar to V-arc and R-arc closures — narrow
    slices, opt-in defaults, real-mode validation between
    slices when feasible).
  * Mark Asset Library v1 complete in
    `docs/CHARACTER_OS_WHAT_IT_IS.md` + start-here.
  * Consider a real-mode dogfood pass — operator browses
    the 128 dev-DB assets in the new list view, drills into
    a couple of details, fires a V18 composition with a
    role-filtered backdrop picker, sees the produced
    assets land on the composition's overview page.
* **No Celery worker concern** — A6 didn't change any
  primitive emit shape or any consumed-by-worker module.
* **Real-mode dogfood newly possible**: open
  `http://localhost:5174/workspace/assets` and click any
  row to land on the new detail page. 128 dev-DB assets
  across 8 roles to browse.
