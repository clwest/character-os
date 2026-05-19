---
title: "Session 186 — A2 primitives stamp role at emit + contract rule 20 coverage"
date: 2026-05-19
status: complete
session: 186
previous_handoff: ./SESSION_185_DRIFT_SWEEP_ASSET_LIBRARY_LOCK_A0_A1.md
---

# Session 186 — A2 primitives stamp role

## TL;DR

Clean session — single slice, real-mode-not-required (no
Runway / Stability spend). One feature commit lands: A2
ships, every primitive in `apps.compositions.primitives`
stamps `role` on its output Asset at emit time, the runner
asserts the contract at runtime, and a new coverage test
file enforces rule 20 statically (AST scan) + dynamically
(runtime backstop + round-trip + realtime path). Plus this
handoff close.

Test totals climbed **928 → 936 (+8)** — all 8 new tests
live in `apps/compositions/tests/test_primitive_role_coverage.py`.
Compositions suite **497 → 505**; full shell suite **928 →
936**. Media-engine + SPA vitest unchanged. Contract rule
20 now structurally enforced across three layers.

## Session arc

### Slice — A2 (every primitive stamps role)

The largest A-arc slice by surface area (14 primitive modules
+ 3 mock primitives + 1 realtime emit site + the runner +
the shared mapping module + new coverage test file).

#### Architectural decision

Production code + backfill share **one canonical mapping
table**. Three options on the table at slice-open:

* **A) Centralized in the runner.** `_persist_output_asset`
  looks up role from `extra_source_spec.primitive_kind`.
  Rejected — doesn't enforce "every primitive stamps role";
  it just looks one up at persist time.
* **B) Each primitive imports the table.** Primitive sets
  `role=PRIMITIVE_TO_ROLE["..."]`. Rejected as the default —
  too indirect at the emit site (the reader chases an
  import to find the literal).
* **C) Each primitive stamps an explicit `AssetRole.X.value`.**
  Chosen. The emit site is readable in isolation. The
  coverage test enforces that the literal stamped matches
  what PRIMITIVE_TO_ROLE says, so the two stay aligned by
  test rather than by indirection.

Same source of truth (PRIMITIVE_TO_ROLE) for backfill +
coverage; explicit role literals at every emit site.

#### What landed

* **New module `apps/compositions/asset_roles.py`** —
  hosts `PRIMITIVE_TO_ROLE` (20 entries), `KNOWN_EXPERIMENT_UUID_PREFIXES`
  (the 2 SESSION 184 smoke UUIDs), and `derive_role(asset)`.
  Moved from `apps.compositions.management.commands.backfill_asset_roles`
  so production primitive emit sites + backfill share one
  definition. Backfill command re-exports for backwards-compat
  with existing test imports.
* **`PrimitiveResult` gained `role: str = ""`** field on the
  dataclass. Defaults to empty so the runner's defense-in-depth
  raise has something to catch.
* **14 primitive modules patched** (28+ emit sites total):
  * `avatar_speech` → `TALKING_HEAD` (mock + real)
  * `visual_clip` → `BACKDROP` (mock + real)
  * `extend_visual_clip` → `BACKDROP` (mock + real)
  * `concat_clips` → `BACKDROP` (mock + real)
  * `composite_video` → `COMPOSITE_OUTPUT` (mock + real)
  * `mix_audio` → `COMPOSITE_OUTPUT` (mock + real)
  * `polish.py` 4 sub-primitives × 2 emit sites = 8 →
    `POLISH_OUTPUT`
  * `style_remix` → `POLISH_OUTPUT` (mock + real)
  * `transcribe` → `TRANSCRIPT` (mock + real)
  * `split_script` → `TRANSCRIPT` (single emit; CPU-only,
    no mock branch)
  * `generate_image` → `REFERENCE_IMAGE` (mock + real)
  * `audio_extract` → `AUDIO_TRACK` (mock + real)
  * `remove_avatar_background` → `TALKING_HEAD` (mock + real)
  * `voice.py` 2 sub-primitives × 2 emit sites = 4 →
    `AUDIO_TRACK`
* **3 mock primitives** (mock.py) → `EXPERIMENT` (sandbox
  shape — same role the backfill assigns to smoke outputs).
  MockFailure has no emit (raises only).
* **Realtime `capture_transcript`** (apps/realtime/tasks.py)
  creates `Asset(TRANSCRIPT)` directly — stamps
  `role=AssetRole.TRANSCRIPT.value` on the create call.
* **Runner backstop** in
  `apps/compositions/tasks.py::_persist_output_asset` —
  raises `PrimitiveError("Contract rule 20: ...")` if
  `result.role` is empty before creating the Asset row.
  Passes `role=result.role` through to
  `Asset.objects.create(...)`.

#### Coverage test (`test_primitive_role_coverage.py`)

Three enforcement layers, 8 tests:

* **Layer 1 — AST primitive_kind scan.** Walks every
  `apps/compositions/primitives/*.py` and collects
  `"primitive_kind": "<literal>"` string literals.
  Asserts every literal is in `PRIMITIVE_TO_ROLE` (rule 20
  static enforcement); asserts no orphan mappings (every
  table key has a literal in code OR is on the
  `EMITTED_ELSEWHERE` allowlist — `realtime_transcript` +
  `smoke_keyframes`).
* **Layer 2 — AST emit-site scan.** Walks every
  `PrimitiveResult(...)` constructor call in the primitives
  package; asserts each passes a `role=` keyword arg. A new
  primitive that forgets to stamp role fails here statically.
* **Layer 3 — runtime backstop.**
  * Mock primitives execute → result.role == EXPERIMENT.
  * Builds a PrimitiveResult with `role=TALKING_HEAD`,
    calls `_persist_output_asset`, asserts the Asset row's
    role column reflects it (end-to-end proof of the
    PrimitiveResult → Asset.role pipe).
  * Builds a PrimitiveResult with `role=""`, calls
    `_persist_output_asset`, asserts `PrimitiveError` with
    "Contract rule 20" message — the defense-in-depth
    backstop.
  * Patches `MediaEngineClient`, fires
    `fetch_transcript_for_session`, asserts the persisted
    Asset has `role=TRANSCRIPT`. Proves the realtime
    direct-emit path is also covered.

#### Isolation test updates

Two `test_isolation.py` files (compositions + realtime)
gained `apps/compositions/tests/test_primitive_role_coverage.py`
in their ALLOWED_FILES sets — the coverage test seeds its
own Composition/RealtimeSession rows. Per the SESSION 185
A1 pattern, both entries carry an explicit code-review note
explaining the role-only write + the workspace-anchor
preservation.

## Calibration moments worth carrying

Single calibration entry this session — to append to
`docs/TRUST_CALIBRATION.md`:

1. **One-runner-emit, many-callers** is the cleanest shape
   for cross-cutting Asset metadata. The compositions
   runtime has one `Asset.objects.create` site
   (`_persist_output_asset`); the realtime arc has its own
   single `Asset.objects.create` site (`capture_transcript`).
   Adding `role` as a `PrimitiveResult` field + threading
   through the one runner site covered 28+ primitive emit
   paths with two file edits. Pattern: when a new
   cross-cutting field lands, find the funnel point first,
   add the field there, then push to the source-of-truth
   producers. The producers stamp explicitly (readable),
   the funnel enforces (defense-in-depth).

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **936** | +8 (928 → 936) |
| - compositions | **505** | +8 (497 → 505) |
| Media-engine | 194 | unchanged |
| SPA vitest | 95 | unchanged |

No real-mode spend this session (no Runway / Stability /
OpenAI API calls — pure backend / static + runtime testing).

## Phase 4 / Asset Library arc status

| Slice | Status |
|---|---|
| **A0** Asset.role enum + migration | **✓ SHIPPED (SESSION 185)** |
| **A1** backfill_asset_roles command | **✓ SHIPPED + COMMITTED on dev DB (SESSION 185)** |
| **A2** every primitive stamps role at emit | **✓ SHIPPED (SESSION 186)** |
| A3 storage-health helper | pending (next; ½ session) |
| A4 read-only `/api/workspace/assets/` endpoints | pending (½ session) |
| A5 SPA `/workspace/assets` list view | pending (1 session) |
| A6 SPA per-asset detail view | pending (1 session) |
| A7 asset_picker role-filter | pending (operator-visible payoff; ½ session) |
| A8 F-arc composition-lineage cross-link | pending (½ session) |

A2 closes the foundational layer. **A3 + A4 unblock A5/A6
frontend work**; A7 is where the operator visibly benefits
from the role taxonomy.

## Operational notes for SESSION 187

* **Celery worker restart required** if any composition
  fires next session — `_persist_output_asset` shape
  changed (passes `role=...` now). The worker holds stale
  module imports until bounced. "Worker stop-state is
  silent" calibration still applies.
* **All new Asset rows from this point forward carry a
  real role** (not RAW_UPLOAD) by construction. The 8
  needs-review legacy rows from SESSION 185's A1 backfill
  remain at RAW_UPLOAD — deferred to the eventual upload
  UI / mutation surface per the SESSION 185 close.
* **No regression risk** — full shell suite passes
  936/936; coverage test will fail if a future primitive
  is added without stamping role (rule 20 enforced by
  test rather than by docs).
