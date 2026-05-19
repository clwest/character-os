---
title: "Session 189 — A5 SPA asset library list view"
date: 2026-05-19
status: complete
session: 189
previous_handoff: ./SESSION_188_A4_WORKSPACE_ASSETS_API.md
---

# Session 189 — A5 SPA asset library list view

## TL;DR

Clean single-slice session. One feature commit + handoff close.
**A5 ships**: `/workspace/assets` SPA route with paginated list,
filter chips (role / asset_type / storage), "More filters"
disclosure (q + date range + primitive_kind), per-row cards
with thumbnails / storage-health badges / composition links,
and pagination controls. **First operator-visible Asset Library
surface.** Three new SPA files; one App.tsx wiring.

SPA vitest **95 → 120 (+25)**. Django + media-engine unchanged
(no backend changes this session). `pnpm build` clean. **One new
TRUST_CALIBRATION entry** — subagent went to source-of-truth and
silently corrected a brief error (uppercase vs lowercase enum
values).

## Session arc

### Slice — A5 (SPA list view)

#### Delegation decision

Per `00-START-NEXT-SESSION.md`'s explicit recommendation, A5 was
delegated to the **`react-web-delivery` subagent**. The agent's
description matches A5's shape exactly (Vite / Tailwind / shadcn /
TypeScript / vitest), and the SPA scope lock's per-route pattern
is well-established. Driving SPA work through Edit / Write tools
from the main thread is feasible but heavier on context window.

**Brief shape**: pointed at source-of-truth files (the A4
serializer, the existing `workspace/knowledge.tsx` template,
brand.ts conventions) rather than restating values inline. One
deliberate omission — let the agent verify enum values directly
against `apps/compositions/models.py` (which it did; my brief had
them uppercased, agent caught the error).

#### What landed

* **`web/src/lib/api/workspace-assets.ts`** (264 lines) —
  * Zod schemas mirroring backend `_serialize_list_asset` shape
    (id, asset_type, role, file_path, title, subject,
    duration_ms, width, height, mime_type, size_bytes,
    cost_micros, created_at, storage_health, primitive_kind,
    producing_prompt, composition).
  * Three exported enum constants (`ASSET_TYPES`, `ASSET_ROLES`,
    `STORAGE_HEALTH_VALUES`) keyed to backend TextChoices —
    **lowercase**, matching the actual API response (not the
    slice brief, which had them uppercased).
  * `useWorkspaceAssets(params)` React Query hook with
    20s staleTime and `placeholderData` for smooth
    pagination (no flicker on page change).
  * `buildAssetsQueryString` URL builder — joins
    comma-list filters, drops empty params.
  * Display helpers: `assetRoleLabel`, `assetTypeLabel`,
    `storageHealthLabel`, `storageHealthTone`, `relativeTime`.
* **`web/src/routes/workspace/assets.tsx`** (729 lines) —
  * Filter chips for role / asset_type / storage, always visible.
  * "More filters" disclosure (collapsed by default) for
    `q` text input + `created_after` / `created_before`
    date inputs + `primitive_kind` multi-select.
  * Active-filter pill strip with per-pill remove.
  * Per-row card: thumbnail for IMAGE assets, Film icon for
    CLIP (v1 doesn't extract poster frames), audio / voice /
    transcript icons. Primary line: title || subject ||
    "Untitled". Secondary: role badge + storage-health colored
    badge (green/amber/red/neutral) + primitive_kind chip +
    composition link to `/compositions/<id>`. Tertiary:
    truncated producing_prompt + relative created_at.
  * Pagination prev / next + page-size selector (25 / 50 / 100).
  * URL search params drive filter state — back-button +
    refresh preserve everything.
  * Loading skeleton + error retry + empty state with
    conditional clear-filters CTA.
  * Q-a-6 deferral notice in the page header ("Avatars,
    voices, and portraits live on Spokesperson — not shown
    here in v1").
* **`web/src/lib/api/workspace-assets.test.ts`** (191 lines,
  25 tests) — covers Zod schema validation against backend
  shapes, URL builder edge cases, React Query hook
  behavior under filter changes.
* **`web/src/App.tsx`** — added `WorkspaceAssetsRoute` import
  and `<Route path="/workspace/assets">` registration
  immediately after `/workspace/knowledge/:id`.

#### Deviation: `@/components/ui/badge` doesn't exist

Brief asked for shadcn `Badge` components for role / storage
labels. Agent discovered `web/src/components/ui/` doesn't
have `badge.tsx` installed (only `button`, `card`, `input`,
`label`, `tabs`). Inline Tailwind classes used instead —
matches how `web/src/routes/workspace/knowledge.tsx` handles
its `StatusPill`. Calibration note: only install shadcn
components on-demand; check `components/ui/` before
importing.

## Calibration moments worth carrying

One new TRUST_CALIBRATION entry (appended at session close):

**Subagent went to source-of-truth and caught an upstream
brief error.** The slice brief rendered AssetType enum values
in uppercase (CLIP / IMAGE / ...); actual backend values are
lowercase (`AssetType.CLIP = "clip"`). The subagent read
`apps/compositions/models.py` directly and used the correct
values without escalating. **Lesson: write subagent briefs as
pointers to source-of-truth, not restatements of it. When the
brief and source disagree, source wins — and the agent is the
right place to enforce that.**

Generalizes: any subagent delegation should treat the brief
as a pointer to ground truth, not a substitute. Pointing at
file paths > restating values inline.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | 980 | unchanged |
| - compositions | 549 | unchanged |
| Media-engine | 194 | unchanged |
| **SPA vitest** | **120** | **+25 (95 → 120)** |

`pnpm build` clean (1789 modules transformed, 606ms, gzip 332kB).
Bundle-size warning pre-existing (not regression).

Real-mode spend SESSION 189: **$0** (frontend + tests only).

## Phase 4 / Asset Library arc status

| Slice | Status |
|---|---|
| **A0** Asset.role enum + migration | **✓ SHIPPED (SESSION 185)** |
| **A1** backfill_asset_roles command | **✓ SHIPPED (SESSION 185)** |
| **A2** every primitive stamps role at emit | **✓ SHIPPED (SESSION 186)** |
| **A3** storage-health helper | **✓ SHIPPED (SESSION 187)** |
| **A4** read-only `/api/workspace/assets/` endpoints | **✓ SHIPPED (SESSION 188)** |
| **A5** SPA `/workspace/assets` list view | **✓ SHIPPED (SESSION 189)** |
| A6 SPA per-asset detail view | pending (next; 1 session) |
| A7 asset_picker role-filter | pending (operator-visible payoff; ½ session) |
| A8 F-arc composition-lineage cross-link | pending (½ session) |

**Backend + first SPA surface complete.** A6 + A7 + A8 remain.
A7 is the structural fix that motivated the arc (V18's
backdrop_clip picker filters to `role=BACKDROP`); A6 + A8 are
SPA / lineage polish.

## Operational notes for SESSION 190

* **No backend changes from A5.** Worker can stay at SESSION 186
  restart state.
* **SPA dev server still required for any frontend work.**
  `pnpm dev` in `web/` at :5174.
* **A6 next** — per-asset detail at `/workspace/assets/<id>/`.
  Backend endpoint already ships full lineage shape (producing
  step + downstream_compositions); A6 builds the page. Mirror
  `web/src/routes/workspace/knowledge.$id.tsx` for the detail
  pattern. Estimated 1 session.
* **Alternative A7 (½ session, smaller payoff but
  operator-visible faster).** Extend the existing
  `/api/assets/` picker endpoint with `role` filter so V18's
  `backdrop_clip_id` dropdown filters to `role=BACKDROP`.
  This is the structural fix that motivated the whole arc.
  Consider doing A7 BEFORE A6 if operator wants the picker
  improvement sooner.
* **Real-mode dogfood available.** A5 is browsable now at
  `http://localhost:5174/workspace/assets` against the live
  dev DB (128 backfilled assets across 8 roles per SESSION 185
  --commit run). First end-to-end visual check of the Asset
  Library arc.
