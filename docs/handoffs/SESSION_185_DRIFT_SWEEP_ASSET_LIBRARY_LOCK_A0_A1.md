---
title: "Session 185 — drift sweep + Asset Library scope-lock + A0 + A1 shipped"
date: 2026-05-19
status: complete
session: 185
previous_handoff: ./SESSION_184_POLISH_V18_Q_V17_3_ASSET_LIBRARY_LOCK.md
---

# Session 185 — drift sweep + Asset Library lock + A0 + A1

## TL;DR

Clean session — no deferrals, no surprises, both planned
slices shipped + real-mode dogfooded. Five commits land:
boot drift-sweep + Asset Library scope-lock + A0 (model +
migration) + A1 (backfill management command) + this
close. **Asset Library v1 arc opens for real** — A0/A1
foundational layers shipped, 128 of 136 dev-DB assets
backfilled to role-tagged state in a live `--commit` run.

Five feature/docs commits + handoff. Test totals climbed
**915 → 928 (+13)**: 4 from A0, 9 from A1. Compositions
suite **484 → 497**.

## Session arc

### Slice 0 — drift sweep (`082ff8f`)

`context-kit doctor` exited with 3 warnings at session
start (carried from SESSION 172 doctor sweep — see that
session's reconstituted handoff). All three resolved before
opening A0:

* **Inventory file location.** Created
  `docs/CONTEXT_KIT_INVENTORY.md` (context-kit-managed
  inventory) via `context-kit inventory --write`. Added
  a clear header pointing readers to
  `docs/CHARACTER_OS_INVENTORY.md` as the real runtime
  anchor. They're complementary, not duplicates —
  context-kit's tracks CLI/guide/handoff shape; the
  project's tracks Django models, REST routes, Celery
  tasks, media-engine routes.
* **Version drift.** Root cause was doctor's regex
  `\b\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]*)?\b` greedy-matching
  the uvicorn host IP literal (in stack-up bash) AND the
  W-arc sub-slice ID format. Scrubbed both: uvicorn host
  → `localhost`; slice ID expanded as prose. No project
  semantics changed. Calibration entry filed.
* **Missing handoffs.** Backfilled `SESSION_053`
  (numbering gap on 2026-05-09 — PR BU closed 052, PR CA
  opened 054 same day, no work under 053) and
  `SESSION_172` (real drift-fix session that closed via
  commit `2eb3a8c`'s message body, no handoff file
  written; reconstituted from the commit content).

Doctor exits **0 blocking, 0 warnings** after the sweep.

### Slice 1 — Asset Library scope-lock (`0306b8b`)

Operator review against
`docs/design/ASSET_LIBRARY_V1.md` (status: proposed).
**Six open questions resolved** in a single batch
operator decision:

* **Q-a-1 — taxonomy.** Enum lands at **10 roles** (was
  proposed at 9). `EXPERIMENT` added to capture
  intent-vs-medium for smoke / sandbox outputs.
  Resolves the V18 dogfood finding (SESSION 184
  calibration #6) where the gen3a_turbo smoke output got
  picked as a backdrop. Pre-lock review caught that
  backfilling smoke outputs AS `BACKDROP` would
  re-trigger the exact bug A7 was supposed to fix —
  switched to `EXPERIMENT`. `mix_audio` → primary role
  `COMPOSITE_OUTPUT`.
* **Q-a-2 — backfill.** Always dry-run by default;
  explicit `--commit` to apply. No silent backfills.
* **Q-a-3 — storage health.** Live per request for v1;
  cache only if A5 perf demands.
* **Q-a-4 — detail view.** Extend F-arc lineage
  component; don't build a per-asset variant.
* **Q-a-5 — picker role-filter.** First-class
  `RecipeField.role_filter`, not per-recipe override.
* **Q-a-6 — Avatar/Voice/Portrait modeling.** Deferred
  to v2 as proposed; A4 endpoint explicitly excludes
  them with an honest SPA gap note at A5.

**9 contract rules merged into `VIDEO_COMPOSITION_V1.md`
as rules 14-22** (V16/V17 merge pattern). None of rules
1-13 change shape. Slice count corrected from "8" to
"9" — A0-A8 inclusive.

### Slice 2 — A0 Asset.role enum + migration (`235e21f`)

* `AssetRole` TextChoices class in
  `apps.compositions.models` with 10 values
  (TALKING_HEAD / BACKDROP / COMPOSITE_OUTPUT /
  POLISH_OUTPUT / REFERENCE_IMAGE / B_ROLL / TRANSCRIPT
  / AUDIO_TRACK / RAW_UPLOAD / EXPERIMENT).
* `Asset.role` field —
  `CharField(max_length=24, choices=AssetRole.choices,
  default=AssetRole.RAW_UPLOAD)`.
* New `Asset._meta.indexes` entry —
  `(workspace, role)`. Supports the future
  `GET /api/workspace/assets/` filter (A4).
* Migration `0009_a0_asset_role` — AddField + AddIndex.
* 4 new tests in `test_models.py`: enum count == 10,
  default applies to new rows, workspace+role filter
  + index existence, round-trip every enum value.

Compositions suite: 484 → 488 (+4).

### Slice 3 — A1 backfill_asset_roles command (`a9b21b3`)

Heuristic-driven backfill from
`source_spec.primitive_kind` → `Asset.role`. Operator
runs the command without `--commit` to see a per-role
plan, then re-runs with `--commit` to apply. Idempotent
— only `RAW_UPLOAD` rows are reconsidered.

* Heuristic table covers **all 20 known primitive_kind
  values** currently emitted in the codebase. Test
  `test_heuristic_table_covers_every_primitive_kind_in_codebase`
  enforces it (rule 20 guard at the A1 level; rule 20's
  full migration test variant lands at A2).
* Special case for SESSION 184 manual-shell smoke
  outputs: UUID prefixes (`c21fdeec`, `89a1ce5f`) →
  `EXPERIMENT` even without primitive_kind.
* `--workspace NAME` flag scopes to one workspace for
  staged rollout.
* `ALLOWED_FILES` entry added to `test_isolation.py`
  with a sanctioned-writer note (role-only `.update`
  on existing rows; workspace anchor untouched, so the
  cross-workspace isolation guarantee holds by
  construction).
* 9 new tests covering: heuristic-table coverage,
  every value is a valid AssetRole, smoke UUID
  handling, dry-run is default + writes nothing,
  `--commit` applies, unrecognized rows surface for
  review, idempotency, workspace scoping, unknown
  workspace raises `CommandError`.

Compositions suite: 488 → 497 (+9). Full shell:
915 → 928.

### Dev-DB real-mode dogfood

**DRY-RUN result:** 136 candidates / 128 mappable / 8
needs-review. Per-role plan:

| Role | Count |
|---|---|
| talking_head | 49 |
| backdrop | 42 |
| composite_output | 15 |
| polish_output | 11 |
| transcript | 4 |
| reference_image | 3 |
| audio_track | 2 |
| experiment | **2** ← the SESSION 184 smoke UUIDs land correctly |

**8 needs-review legacy rows:** 2 audio + 6 image assets
in `Admin's workspace` that pre-date the primitive_kind
stamping discipline. UUIDs:

* `03df5496-...` audio
* `42130570-...` audio
* `8c098019-...` image
* `1b1fdb78-...` image
* `dbdb2f4b-...` image
* `10d1b6b3-...` image
* `f4d5f119-...` image
* `f46b94fc-...` image

Operator chose to defer per-asset tagging of these to
the eventual upload-UI / mutation surface (post-v1).
They stay at `RAW_UPLOAD`.

**COMMIT applied** in the same session — 128 rows
updated across 8 roles. Re-running dry-run shows 8
candidates remaining (just the legacy needs-review
rows), 0 mappable. Idempotency confirmed live.

## Calibration moments worth carrying (2 new entries)

Both appended to `docs/TRUST_CALIBRATION.md`:

1. **Walk a proposal's mechanism through its motivating
   calibration before locking.** When scope is motivated
   by a specific prior calibration event, walk the
   proposed mechanism through the original failing
   scenario. If the mechanism doesn't fix the failure
   end-to-end, the proposal needs revision before lock.
   Same shape as the SESSION 182/184 "live-doc-check
   the API surface" discipline, applied to design
   proposals against their motivating evidence.
2. **Doctor heuristics over-match on project-shape
   naming conventions.** Two of three doctor warnings
   in the SESSION 185 boot sweep were heuristic false
   positives (regex matching IP-shaped literals and
   multi-component slice IDs as "versions"). Treat doctor warnings
   as guidance; investigate the actual heuristic before
   scrubbing state. Upstream fix sits with context-kit;
   pragmatic fix is to scrub matching literals from
   project docs.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **928** | +13 (915 → 928) |
| - compositions | **497** | +13 (484 → 497) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

No real-mode spend this session (no Runway / Stability
API calls — A0/A1 are pure backend / DB work).

## Phase 4 / Asset Library arc status

| Slice | Status |
|---|---|
| **A0** Asset.role enum + migration | **✓ SHIPPED** |
| **A1** backfill_asset_roles command | **✓ SHIPPED + COMMITTED on dev DB** |
| A2 every primitive stamps role at emit | pending (next) |
| A3 storage-health helper | pending |
| A4 read-only `/api/workspace/assets/` endpoints | pending |
| A5 SPA `/workspace/assets` list view | pending |
| A6 SPA per-asset detail view | pending |
| A7 asset_picker role-filter | pending (operator-visible payoff) |
| A8 F-arc composition-lineage cross-link | pending |

## Operational notes for SESSION 186

* **Celery worker** was not touched this session (no
  Celery-task code changed). If SESSION 186 opens A2
  (primitives stamp role at emit), restart Celery before
  firing any composition so the worker picks up the new
  primitive code.
* **8 needs-review assets** linger at `RAW_UPLOAD`.
  Decision deferred to post-v1 upload-UI / mutation
  surface. They'll show up in the future
  `/api/workspace/assets/?role=raw_upload` list — fine.
* **No regression risk visible** — full shell suite
  passes 928/928.
