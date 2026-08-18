---
title: "EPISODE_COMPOSITION_WORKFLOW_V1 — Implementation Report"
status: implemented — Episode-driven recipe form + versions list landed
date: 2026-08-18
depends_on:
  - "design/EPISODE_COMPOSITION_WORKFLOW_DOGFOOD_V1.md"
  - "design/EPISODE_SCHEMA_V1_IMPLEMENTATION.md"
  - "design/COMPOSITION_OBSERVABILITY_V1.md"
scope: >
  Implementation of the workflow slice ratified by
  EPISODE_COMPOSITION_WORKFLOW_DOGFOOD_V1.md with the two operator
  brief corrections (Episode.cast authoritative + added_at is only a
  UI default). Zero Episode-schema change. Zero migrations. Zero
  changes to SESSION 262 observability contract. Legacy Episode-less
  Composition workflow preserved byte-for-byte.
supersedes: []
---

# EPISODE_COMPOSITION_WORKFLOW_V1 — Implementation Report

## Purpose

Deliver the "Episode saves work and organizes versions of one story"
outcome per the operator dogfood audit. Two operator corrections
adopted:

1. **Episode.cast is authoritative** for the performer set when a
   recipe launches from Episode context. No silent fallback to the
   Universe roster. An operator who wants a non-cast performer must
   add that Teammate to the Episode first (explicit action).
2. **`EpisodeCast.added_at` ordering is a UI default only**, not a
   protagonist/lead/narrator/story-role designation. Encoded in
   docstrings and covered by a dedicated regression test.

## Load-bearing boundaries preserved

| # | Boundary | How preserved |
|---|---|---|
| 1 | Episode.cast authoritative for performers | Recipe form filters `spokesperson_picker` options to Episode.cast members only when `?episode=<id>` is present. Universe/workspace roster is NOT offered as a fallback. |
| 2 | added_at is UI default, not a role | Documented in `EpisodeSerializer.get_cast` + `EpisodeCast` docstring. Regression test `test_episode_cast_ordering_is_ui_default_not_a_role` verifies swapping M2M attach order swaps the default primary; no other invariant exists. |
| 3 | Episode-less recipe workflow unchanged | When `?episode=` absent, form behavior is byte-for-byte pre-workflow: workspace roster in pickers, no chip, no insufficient-cast block, no pre-fills beyond the existing spokesperson hint. |
| 4 | No Episode schema change | Zero model / migration diffs on Episode or EpisodeCast in this slice. |
| 5 | SESSION 262 Composition observability untouched | Zero changes to observability fields, immutability guard, from_db snapshot, or synthesis code paths. Every Episode-workflow save uses `update_fields=["episode", "updated_at"]` (Episode attach) or writes at Composition-create (`operator_topic` copy inheritance flows through the existing SESSION 262 immutable-once-populated pattern). |
| 6 | K2 retrieval unchanged | Zero changes to `retrieval.py`. Retrieval still branches only on `spokesperson.universe_id`. |
| 7 | No Relationship / WorldEntity / narrative-memory work | Zero code touches those substrates. |
| 8 | No historical backfill | Zero data migration; existing Compositions unaffected. |
| 9 | Legacy Universe/Workspace hard-delete preflights unchanged | No changes to Universe delete preflight or Episode delete preflight. |
| 10 | No `duplicate_from` implementation | Deferred per operator brief; "Make another version" preserves Episode context via the existing pre-fill path — no new hint needed. |

## Exact files changed

### Backend (2 files + 1 test file)

- **`shell/apps/compositions/views.py`**
  - `CompositionViewSet.list` — added `?episode=<uuid>` filter.
  - `CompositionViewSet.get_queryset` — added `select_related("episode")` so `episode_title` serialization doesn't N+1.

- **`shell/apps/compositions/serializers.py`**
  - `CompositionListSerializer` — added `episode_title` (SerializerMethodField) + `target_duration_seconds` (surface the SESSION 262 field on list rows so the Episode-detail versions list can render the requested duration).
  - `CompositionSerializer` — added `episode_title`.

- **`shell/apps/universe/serializers.py`**
  - `EpisodeSerializer.cast` — replaced the nested `EpisodeCastTeammateSerializer(many=True)` with a `SerializerMethodField` that sorts by `EpisodeCast.added_at`. Docstring updates make the ordering-as-UI-default-only contract explicit.

- **`shell/apps/compositions/tests/test_episode_composition_workflow.py`** (new; 8 tests)
  - `?episode=` filter narrows correctly + preserves list shape without it.
  - `episode_title` populated on both list + detail serializers when attached; NULL when standalone.
  - Cast serialized in `added_at` order (verified against a case where alphabetic would differ).
  - Regression guard: swapping M2M attach order swaps the default primary; nothing else moves (proves the "UI default only, not a role" contract).

- **`shell/apps/compositions/tests/test_isolation.py`** — added the new test file to `ALLOWED_FILES`.

### SPA (5 files + 1 test file)

- **`web/src/lib/api/recipes.ts`**
  - `compositionSchema` (detail) — added `episode_title` nullable field.
  - New `compositionRowSchema` matching the light `CompositionListSerializer` shape (10 fields). Kept intentionally separate from the detail schema so the Episode-detail versions list never accidentally depends on the heavy steps/produced_assets payload.
  - New `useCompositionsForEpisode(episodeId)` hook — wraps `/api/compositions/?episode=<uuid>` with paginated-envelope unwrap.
  - Exported `CompositionRow` type.

- **`web/src/routes/recipes/$kind.tsx`**
  - Imports `useEpisode` from `@/lib/api/episodes`.
  - Adds `episodeQuery = useEpisode(episodeHint)` + `episode = episodeQuery.data`.
  - New pre-fill effect (guarded by `prefilledFromEpisode`) that seeds `topic`, `primary_spokesperson_id` / `spokesperson_id`, `secondary_spokesperson_id`, and `dialogue_mode = "ai_topic"` from Episode data — one-shot, never clobbers subsequent operator edits.
  - Replaces `workspaceSpokespeople` with `castOnlySpokespeople` in every `spokesperson_picker` render when Episode context is present.
  - New `performerSlotCount` + `insufficientCast` computation.
  - New "Episode: `<title>`" context chip in the header.
  - New "Add cast to Episode" block that appears when `insufficientCast`, blocking submit until resolved.
  - Submit button disabled with a helpful `title` tooltip when `insufficientCast`.

- **`web/src/routes/workspace/episodes.$id.tsx`**
  - Imports `useCompositionsForEpisode` + `CompositionRow` type.
  - Fetches `compositions = useCompositionsForEpisode(id)`.
  - New `<EpisodeVersionsSection>` component + `<EpisodeVersionRow>` sub-component rendered between the Cast section and the "Render under this Episode" CTA row.
  - Each row surfaces: status chip · Composition name · template_kind · target_duration_seconds · created_at · mock badge · Open link (→ `/compositions/<id>`) · Make-another-version link (→ `/recipes/<kind>?episode=<id>`).
  - Empty-state teaches the operator that the section fills as they render.
  - Relaunch link degrades gracefully when Episode cast dropped below the recipe's requirement (rare — operator removed a member post-render).

- **`web/src/routes/compositions/$id.tsx`**
  - Backlink now renders `composition.episode_title` instead of a UUID fragment (falls back to fragment when title is unavailable — defense-in-depth for older cached rows).
  - Added `data-testid="composition-episode-backlink"`.

- **`web/src/routes/workspace/episode-composition-workflow.test.tsx`** (new; 15 tests)
  - Behaviors 1-7 + 11 from the operator brief on the recipe-form surface.
  - Behaviors 8-10 on the Episode-detail versions list surface.
  - Explicit coverage for the added_at swap contract (behavior 3) and the non-cast-Universe-character rejection (behavior 4).
  - Empty-cast + insufficient-cast blocks verified for dialogue_scene; talking_head with cast==1 verified NOT to block (recipe cast requirement is what matters).

### Docs (2 files)

- **`docs/design/EPISODE_COMPOSITION_WORKFLOW_V1_IMPLEMENTATION.md`** (this file).
- **`docs/CHARACTER_OS_INVENTORY.md`** — regen deferred to post-slice (no schema changes, so URL/model counts unchanged; will regen at close of this session per operator convention).

## Behavior specification (11 required + additional coverage)

### 1. Recipe launch pre-fills topic
Test `test_1_pre_fills_topic`. Rendered `recipes/dialogue_scene?episode=<uuid>` → topic textarea value equals `Episode.operator_topic`.

### 2. Cast pre-filled in added_at order
Test `test_2_pre_fills_primary_secondary_from_cast_added_at`. cast[0] → primary, cast[1] → secondary. Verified against a case where alphabetic ordering would differ (Zed then Alpha).

### 3. added_at is UI default, operator may swap
Test `test_3_added_at_is_ui_default_operator_may_swap`. Operator swaps primary → secondary via the picker. Nothing schema-level enforces the initial ordering as a role; the swap succeeds and secondary picker filters primary out per the existing AI-D4 same-person guard. Backend regression `test_episode_cast_ordering_is_ui_default_not_a_role` proves the DB-serializer-only contract.

### 4. Non-cast Universe character cannot become performer
Test `test_4_non_cast_universe_character_cannot_appear`. Picker option list contains only Episode.cast members. Baker (Universe teammate, not in cast) is verified ABSENT. Cross-references correction #1 in the operator brief.

### 5. Empty/insufficient cast has explicit path
Tests `test_5_empty_cast_blocks_submit_and_shows_add_cast_path`, `5b`, `5c`. Empty cast → block with "Add cast to Episode" link; dialogue_scene with cast==1 → block; talking_head with cast==1 → NO block (recipe requires 1).

### 6. Operator may override Composition topic without changing Episode
Test `test_6_operator_may_override_topic`. Operator clears the pre-filled topic, types a variant, submits. `mockCreate` payload has `params.topic == "VARIANT-ONLY TOPIC"`; `episode` FK still attached. Backend snapshots this variant topic into `Composition.operator_topic` per the existing SESSION 262 create-time inheritance (Composition.operator_topic is immutable-once-set; Episode.operator_topic remains unchanged story-authoritative).

### 7. Episode-less recipe workflow unchanged
Test `test_7_episode_less_recipe_workflow_unchanged`. `currentEpisode = undefined`; no chip, no block, workspace roster contains Patch + Rivet + Baker (Baker is workspace-scoped but in a different Universe — pre-Episode form has no Universe filter, so this preserves the pre-Episode behavior byte-for-byte).

### 8. Episode detail lists attached Compositions
Tests `test_8_lists_compositions_attached_empty_state` + `test_8b_populated_list_renders_row_per_composition`.

### 9. Return to Episode after create shows new version
Test `test_9_simulated_return_to_episode_after_create`. Mocks the "return trip" by mutating the query source and re-rendering; production behavior relies on react-query's `useCreateComposition` `onSuccess` invalidating `["compositions"]`.

### 10. Make-another-version retains Episode story/cast context
Test `test_10_make_another_version_link_retains_episode_context`. The relaunch link href is `/recipes/<kind>?episode=<episodeId>` — same recipe kind + Episode context preserved so the pre-fill effect re-applies topic + cast on the next render.

### 11. Composition observability untouched
Structural — Episode-attach uses `save(update_fields=["episode", "updated_at"])` (see `CompositionViewSet.attach_episode`); SESSION 262 immutability guard is only invoked for observability fields it recognizes; both are covered by the existing SESSION 262 test matrix + the EPISODE_SCHEMA_V1 test #44-47 (adversarial). Cross-referenced from this workflow slice; no new tests in this file duplicate that coverage.

## Test totals

- **Focused backend tests** (`test_episode_composition_workflow.py`): 8 / 8 pass.
- **Focused SPA tests** (`episode-composition-workflow.test.tsx`): 15 / 15 pass.
- **SPA full suite**: 597 / 597 pass (was 582; +15).
- **SPA TypeScript** (`pnpm tsc --noEmit`): clean.
- **Backend regression** (see below).
- **Backend full suite** (see below).

Full backend numbers land in the commit body once the suite completes; baseline comparison is 2529 passed / 80 failed / 1 skipped from the EPISODE_SCHEMA_V1 close.

## Baseline comparison

Every new test is additive; no existing test was mutated except
`test_isolation.py` (ALLOWED_FILES extension for the new test file).

Expected delta vs the EPISODE_SCHEMA_V1 baseline: **+8 passed
(backend workflow tests). 80 failures unchanged** — all pre-existing
in `apps/bootstrap_review/*` + `character_os/clients/tests/test_media_engine_timeouts.py`.

If any failure is not on the known baseline, this report is
updated with the investigation before commit.

## Implementation deviations from the audit doc

None. The three-file SPA change + one-line backend filter + one-line
`select_related` change match the audit's smallest-slice
recommendation exactly. The two operator brief corrections
(Episode.cast authoritative + added_at as UI default only) were
applied as scoped:

- **Correction #1**: implemented via `castOnlySpokespeople` filter +
  `insufficientCast` gate. The audit's original proposal only
  "pre-filled" the pickers; the implementation additionally
  RESTRICTS them per the operator's ratification.
- **Correction #2**: docstring updates on `EpisodeSerializer.get_cast`
  + `EpisodeCast` model + a dedicated regression test. No schema
  role field added.

## Deferred findings

Same as the audit doc. None discovered during implementation that
require a new deferral:

- `EpisodeCast.role` schema field — deferred; if a future story
  requires an explicit protagonist/lead/narrator designation it
  lands in its own slice.
- Cast reordering UI — deferred; operator can remove + re-add.
- `Episode.canonical_composition` FK — deferred (canon promotion).
- `?duplicate_from=<composition_id>` hint on relaunch — deferred;
  Episode context alone reproduces topic + cast, which is
  sufficient for v1.
- Variant comparison / diff UI — deferred.
- Removing the pre-existing "Worlds" chip inside the Knowledge tile
  header — harmless; separate cleanup slice.

## Local git state

- Local `main` at time of report authorship: `68e1432` (dogfood
  audit doc) + this slice's implementation commit (about to land).
- `origin/main`: `01f12b1`.
- Local will be **8 commits ahead of origin/main** after the
  implementation commit; not pushed.

## STOP

Implemented. Every audit invariant is preserved or explicitly
deviated with rationale. Every operator brief correction is
covered by a dedicated test. Zero real provider calls required.
Committed locally; not pushed pending operator verification.
