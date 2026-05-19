---
title: "Session 190 — A7 asset_picker role-filter (structural fix that motivated the arc)"
date: 2026-05-19
status: complete
session: 190
previous_handoff: ./SESSION_189_A5_SPA_LIST_VIEW.md
---

# Session 190 — A7 asset_picker role-filter

## TL;DR

Clean single-slice session. One feature commit + handoff close.
**A7 ships — the structural fix that motivated the whole Asset
Library arc.** V18's `backdrop_clip_id` dropdown (and three
sibling V8 picker fields) now narrow to their semantically-
correct role; smoke / talking-head / composite clips no longer
pollute the backdrop picker.

Operator picked A7 over A6 per the SESSION 189 close
recommendation — operator-visible payoff over arc continuity.

Backend tests **980 → 990 (+10)**; SPA vitest **120 → 125
(+5)**. Backend + SPA + recipe registry all touched in a
half-session-sized slice. No real-mode spend.

## Session arc

### Slice — A7 (role-filtered asset_picker)

#### Architectural decisions

* **First-class `RecipeField.role_filter` field**, not a
  per-recipe override. Per Q-a-5 resolution at scope-lock
  (SESSION 185).
* **Apply conservatively.** Only four picker fields get
  tagged — the ones where the role is semantically
  unambiguous from the field name + label. Fuzzy pickers
  (`pip_clip_id`, `cohost_clip_id`, `foreground_clip_id`,
  layout `base_clip_id`s) stay unfiltered; they're genuine
  v2 design questions ("should the PiP overlay accept a
  composite or only a talking head?") not oversights.
* **Backend query param matches A4's shape.** Comma-list,
  `?role=backdrop` or `?role=backdrop,b_roll`. Unknown
  values match zero rows (the existing IN clause behavior
  is correct: a typo in the recipe registry produces an
  empty picker rather than a crash). Existing
  `?asset_type=...` continues to work alongside.
* **`to_json` omits the key when not set.** Backwards-compat
  with the SPA Zod schema's `optional()` (which means
  "not present", not "null"). Existing recipes' field
  metadata is shape-stable.

#### What landed

* **Backend (`shell/apps/compositions/recipes.py`)**:
  * `RecipeField.role_filter: str | None = None` field on the
    dataclass.
  * `to_json()` emits `"role_filter"` only when set (omits
    when None).
  * Four recipe fields tagged:
    * V18 `talking_head_with_backdrop.backdrop_clip_id` →
      `AssetRole.BACKDROP.value` (the prime motivating case
      from SESSION 184 V18 dogfood — operator picked a
      gen3a_turbo smoke output as backdrop because the
      dropdown had no way to distinguish scene clips from
      person-interpolation clips).
    * V8 `backdrop_layout.background_clip_id` →
      `AssetRole.BACKDROP.value`. `foreground_clip_id`
      stays unfiltered (foreground could be talking head
      OR composite).
    * V8 `broll_splice.broll_clip_id` →
      `AssetRole.B_ROLL.value`. `base_clip_id` stays
      unfiltered (avatar OR composite output).
    * V8 `music_bed_pass.music_asset_id` →
      `AssetRole.AUDIO_TRACK.value`. `base_clip_id` stays
      unfiltered.
* **Backend (`shell/apps/compositions/views.py`)**:
  * `AssetViewSet.list()` accepts optional `?role=` query
    param. Comma-list, whitespace-trimmed, empty entries
    skipped. Filter applied via `role__in=[...]`.
  * Docstring updated to reference the A7 contract.
* **SPA (`web/src/lib/api/recipes.ts`)**:
  * `recipeFieldSchema` adds `role_filter: z.string().optional()`.
  * `ListAssetsOptions.role?: string` + `listAssets` forwards
    as `?role=<value>`.
* **SPA (`web/src/routes/recipes/$kind.tsx`)**:
  * `AssetPicker` component takes `roleFilter?: string` prop
    and forwards to `useAssets({ workspace, assetType,
    role: roleFilter })`.
  * Render site reads `field.role_filter` and passes
    through. No other code paths changed.
* **Backend tests** (`apps/compositions/tests/test_v15_api.py`)
  — 10 new tests:
  * `test_list_assets_role_filter_single` — single role
    narrows the picker.
  * `test_list_assets_role_filter_comma_list` — comma-list
    pass-through via `role__in`.
  * `test_list_assets_role_filter_unknown_returns_empty` —
    typo'd role value produces empty list, not crash.
  * `test_list_assets_no_role_param_returns_everything` —
    backwards-compat: callers without `?role=` get the
    full list as before.
  * `test_list_assets_role_combines_with_asset_type` —
    `?role=` AND `?asset_type=` chain correctly.
  * `test_recipe_backdrop_clip_id_exposes_role_filter` —
    V18 backdrop_clip_id metadata exposes
    `role_filter="backdrop"`.
  * `test_recipe_broll_splice_exposes_role_filter` — V8
    broll_clip_id exposes `role_filter="b_roll"`;
    base_clip_id stays unfiltered.
  * `test_recipe_backdrop_layout_exposes_role_filter_on_background_only`
    — background_clip_id tagged; foreground_clip_id stays
    unfiltered.
  * `test_recipe_music_bed_pass_exposes_audio_role_filter` —
    AUDIO_TRACK on music_asset_id.
  * `test_unfiltered_pickers_omit_role_filter_key` — fuzzy
    pickers' `to_json` omits the key entirely (not
    `role_filter: null`).
* **SPA tests** (`web/src/lib/api/recipes.test.ts` — new file)
  — 5 vitest tests:
  * `listAssets` omits `?role=` when undefined.
  * `listAssets` includes `?role=` when supplied.
  * `listAssets` supports role without asset_type.
  * Zod parses `role_filter` when present.
  * Zod parses field without `role_filter` (backwards-compat).

#### Bug caught during build

The new vitest file failed TypeScript strict-mode checks
(`Object is possibly 'undefined'` on bare array index
access `apiJsonMock.mock.calls[0][0]` and
`recipe.fields[0].role_filter`). Fixed by adding a
`lastApiCallPath()` helper that asserts the call exists
+ using `field!.role_filter` after an `expect(field).toBeDefined()`
guard. Tests pass; `pnpm build` clean. **Recurring shape
from the A4 + A5 sessions — TypeScript strict checks bite
at the build step, not the test step. The vitest pass is a
necessary-but-not-sufficient gate.**

## Calibration moments worth carrying

One refinement of an existing calibration; no new entries.

The "TS strict bites at build, not at test" finding from
A5's react-web-delivery deviation is now confirmed across
multiple sessions. The existing **"SPA gates need both
pnpm test AND pnpm build"** calibration covers this; no
new entry needed. The shape: vitest happily runs through
`Object is possibly undefined` because the JavaScript
behavior is fine; tsc's `--noUncheckedIndexedAccess` (or
similar) makes it a build error.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **990** | +10 (980 → 990) |
| - compositions | **559** | +10 (549 → 559) |
| Media-engine | 194 | unchanged |
| **SPA vitest** | **125** | **+5 (120 → 125)** |

`pnpm build` clean (1789 modules transformed, 591ms,
gzip 332kB). Bundle-size warning pre-existing.

Real-mode spend SESSION 190: **$0** (registry + endpoint
change + tests; no API calls).

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
| **A7** asset_picker role-filter | **✓ SHIPPED (SESSION 190)** |
| A8 F-arc composition-lineage cross-link | pending (½ session) |

**A7 closes the operator-visible payoff that motivated the
whole arc** — V18's backdrop_clip_id picker now actually
filters to BACKDROP-tagged clips, no more "two random
people" dragged in as a backdrop (SESSION 184 V18 dogfood
calibration #6).

Two slices remain: **A6** (SPA per-asset detail) and **A8**
(F-arc composition-lineage cross-link). Both ~½ session
each. The arc closes in 1-2 more sessions.

## Operational notes for SESSION 191

* **No Celery worker concern.** A7 is metadata + query
  filter; the worker module is untouched.
* **Real-mode dogfood newly possible.** Bring up the
  full stack and open the V18
  `talking_head_with_backdrop` recipe form — the
  `backdrop_clip_id` dropdown should now only show
  BACKDROP-tagged clips from the SESSION 185 backfill
  (42 of them in dev DB). Worth a quick visual spot-check
  before opening A6/A8.
* **A6 estimated 1 session.** SPA-only; mirror
  `web/src/routes/workspace/knowledge.$id.tsx`. The A4
  detail endpoint already ships the full lineage shape.
* **A8 estimated ½ session.** Backend + SPA — F-arc's
  composition overview page gains an "Assets produced by
  this composition" section showing role badges on each.
  Mirror the F5 lineage pattern.
* **Arc-close ceremony** when A6 + A8 land: regen
  INVENTORY one more time (the A6 route adds nothing to
  inventory; A8 may add one endpoint depending on shape),
  drop a TRUST_CALIBRATION entry summarizing the arc's
  growth template, and update the brand-ecosystem table
  in start-here to mark Asset Library v1 complete.
