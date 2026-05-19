---
title: "Asset Library — Workspace Inventory + Taxonomy"
status: locked
proposed: 2026-05-19 (SESSION 184)
locked: 2026-05-19 (SESSION 185)
companion_docs:
  - VIDEO_COMPOSITION_V1.md
  - WORKSPACE_FABRIC_V1.md
  - CHARACTER_OS_INVENTORY.md
---

# Asset Library — Workspace Inventory + Taxonomy

> **Status: LOCKED (SESSION 185).** 9 contract rules merged
> into `VIDEO_COMPOSITION_V1.md` as rules 14-22. Slices A0-A8
> sequence the implementation. Mirrors the V17 proposal
> pattern (`VIDEO_COMPOSITION_V17_PROPOSAL.md`).

---

## TL;DR

Workspaces accumulate Assets fast — 119 CLIPs + 9 IMAGE +
N AUDIO + N TRANSCRIPT after ~10 dogfood sessions. The
production primitives stamp `source_spec.primitive_kind`
(generate_visual_clip, generate_avatar_speech,
composite_video, …) on every output, but that records *how
the asset was produced*, not *what role it plays*. Today
the operator has no UI surface to BROWSE workspace
assets, no way to filter by intended use (backdrop vs
talking-head vs composite output vs intro/outro vs
reference image vs transcript), and no way to know which
assets will still work next week (HTTPS JWT links expire;
local cache files persist).

This arc ships:

1. **A `role` taxonomy** on Asset (BACKDROP / TALKING_HEAD
   / COMPOSITE_OUTPUT / POLISH_OUTPUT / REFERENCE_IMAGE
   / B_ROLL / TRANSCRIPT / AUDIO_TRACK / RAW_UPLOAD /
   EXPERIMENT — **10 roles**). Stamped at primitive-emit
   time. Backfilled for existing rows via primitive_kind
   heuristics.
2. **A read-only browse REST surface** with role / kind /
   date / storage-health filters.
3. **A workspace SPA route** (`/workspace/assets`) that
   renders the browse surface + per-asset detail (lineage,
   prompts, source steps, related compositions, storage
   status badge).
4. **Storage-health awareness** — HTTPS JWT links flagged
   with expiry; local-only paths flagged as non-portable;
   missing-file detection.

Out of scope for v1: asset upload UI (queued separately
from SESSION 181), asset deletion / archival, free-form
tagging beyond the role enum, Avatar / Voice / Portrait
as first-class Assets.

---

## Why now

Surfaced in SESSION 184 V18 dogfood. The operator selected
a backdrop_clip from the asset_picker dropdown that turned
out to be the gen3a_turbo keyframe smoke output — a
5-second clip showing two visibly different "founder"
portraits drifting (the Q-v17-3 finding made concrete).
The expectation was "pick a backdrop scene"; the reality
was "pick whatever CLIP happens to be in the workspace,
mixed-bag." The operator's reaction:

> "Right now we have a mess of everything, we need a way
> to not only create videos and combine them but track
> what types of videos have been created and how they
> are stored."

The mess is structural, not procedural. The asset_picker
already exists (since V15.2-V15.3) and works correctly —
it filters by `asset_type` (CLIP / IMAGE / AUDIO /
TRANSCRIPT). But asset_type is the *medium*, not the
*intended use*. A talking-head MP4 and a cinematic
backdrop MP4 are both `asset_type=CLIP` — indistinguishable
in any filter. The operator picks a clip by trying to
infer role from the composition name + creation date,
which works for 5 assets and fails at 119.

Adjacent symptom: the V18 finding that a 5-second backdrop
truncates a 9-second speech is also a categorization
problem — the recipe form has no way to filter the
asset_picker to "backdrops with duration ≥ speech
estimate." Asset Library is the foundation for that
filter to exist.

---

## Contract rules (load-bearing)

These extend V1's nine contract rules. The arc holds all
nine V1 rules unchanged. At scope-lock the nine A1-A9
rules below become V1 rules 14-22 (same merge pattern V16
and V17 used).

1. **Role is a closed enum, not free-form tags.** v1 ships
   **ten** roles (see §Taxonomy). Operator-defined free-form
   tags are out of scope for v1 — adding tag plumbing on
   top of an unsettled role enum is harder than adding
   tags later. New roles require a migration + scope
   discussion.

2. **Role is stamped at primitive-emit time, not derived.**
   Every primitive that produces an Asset sets the role on
   the output. The role is queryable directly
   (`Asset.objects.filter(role=...)`); never reconstructed
   from `source_spec.primitive_kind` at query time. Same
   discipline as `asset_type` today.

3. **Role is workspace-scoped.** No global taxonomy, no
   cross-workspace role sharing. Each workspace's role
   enum is the same closed set, but role assignments live
   on Asset rows which honor V1 rule 1 (workspace
   isolation).

4. **Backfill is heuristic-driven but verifiable.** A
   one-time management command maps existing
   `primitive_kind` values to roles (e.g., every
   `generate_avatar_speech` output is `TALKING_HEAD`,
   every `composite_video` output is `COMPOSITE_OUTPUT`,
   etc.). Ambiguous rows (e.g., the 13 `composite_video`
   outputs that could be intermediate OR final) get a
   review flag. Operator approves the backfill plan
   before it commits.

5. **Browse surface is read-only.** v1 ships
   `GET /api/workspace/assets/` only. No write endpoints,
   no delete, no archive. Mutations come in a later arc
   (deletion needs FK guarding; archival needs status
   field). Same pattern F-arc used (read-only browse
   first, mutation deferred).

6. **Storage-health is computed, not stored.** A reusable
   helper inspects `Asset.file_path` and returns one of
   {HTTPS_LIVE, HTTPS_EXPIRED, LOCAL_PRESENT,
   LOCAL_MISSING, DATA_URI, UPLOAD_PENDING}. Live
   computation against the JWT exp claim + the filesystem
   means the operator sees current state, not a stale
   snapshot. Cached for browse-list performance (60s TTL).

7. **No new primitive emits assets without a role.** Same
   shape as V1 rule 5's no-DAG enforcement: any new
   primitive added post-scope-lock MUST stamp role. A
   migration test enforces every primitive_kind in
   `apps.compositions.primitives` has a registered
   default role.

8. **Asset Library does not replace Composition lineage
   (F-arc).** The F-arc workspace fabric ships per-
   Composition lineage views; this arc ships per-Asset.
   The two surfaces co-exist — one is "what did this
   composition produce?" the other is "what's in my
   workspace, regardless of which composition produced
   it?" Cross-link both: each asset detail view shows
   producing composition; each composition lineage shows
   produced assets.

9. **Asset Library is a read foundation, not a
   replacement for the asset_picker.** The existing
   asset_picker in recipe forms (V15.2-V15.3) keeps its
   current contract — filter by `asset_type` + optional
   workspace scope. The picker MAY gain a `role` filter
   in a future slice (A6 or A7), but v1's browse surface
   is a separate workspace-level concern. Backdrop-vs-
   talking-head pickers in V18 / V8 / V13 stay
   unchanged in v1.

---

## Taxonomy (v1 roles)

**Ten roles.** Picked to cover every existing primitive
output and distinguish *intent* (production deliverable vs
experiment) from *medium* (asset_type) and *production
method* (primitive_kind):

| Role | Meaning | Producing primitives (v1) |
|---|---|---|
| `TALKING_HEAD` | Avatar speaking; lip-sync; usually composite foreground | `generate_avatar_speech`, `remove_avatar_background` |
| `BACKDROP` | Cinematic scene; no speech; usually composite background | `generate_visual_clip`, `extend_visual_clip`, `concat_clips` |
| `COMPOSITE_OUTPUT` | Final render; talking head over scene; deliverable | `composite_video`, `mix_audio` |
| `POLISH_OUTPUT` | Post-composite polished render; captions / intro-outro / trimmed / reformatted | `add_captions`, `add_intro_outro`, `trim_clip`, `reformat_clip`, `style_remix` |
| `REFERENCE_IMAGE` | Image input for image-to-video or keyframe interpolation | `generate_image`, future uploads |
| `B_ROLL` | Cutaway scene clip for `broll_splice` layout | (operator-uploaded; rare in v1) |
| `TRANSCRIPT` | Text artifact from realtime session or `transcribe` | `transcribe`, `RealtimeSession.transcript_asset` |
| `AUDIO_TRACK` | Standalone audio (music bed, voice-over, dubbed) | `design_voice`, `dub_audio`, `audio_extract` |
| `RAW_UPLOAD` | Operator-uploaded file with role-unspecified intent | (future asset upload UI) |
| `EXPERIMENT` | Sandbox / smoke / model-comparison output; not for production picking | `smoke_keyframes`, future `smoke_*` commands |

Notes:
* `TALKING_HEAD` covers both the raw `generate_avatar_speech`
  output AND the `remove_avatar_background`-matted
  variant. The latter is still a talking-head, just
  matted. They share role.
* `COMPOSITE_OUTPUT` vs `POLISH_OUTPUT` distinction is
  load-bearing: v1's `composite_video` is the rough
  combiner; polish primitives are downstream refinements
  (subtitles, intros, etc.). A composite that's then
  trimmed for vertical-format reels is POLISH_OUTPUT, not
  COMPOSITE_OUTPUT. Note that role is stamped per-asset by
  the *producing primitive* — the underlying composite
  keeps its `COMPOSITE_OUTPUT` role; the polish primitive
  emits a new asset tagged `POLISH_OUTPUT`.
* `mix_audio` resolved (Q-a-1, SESSION 185) → primary role
  `COMPOSITE_OUTPUT`. It's an audio-track-onto-composite
  operation; the output is a composite with mixed audio,
  not a standalone audio track. `AUDIO_TRACK` is reserved
  for primitives whose output is *only* audio.
* **`EXPERIMENT` is intent, not medium.** Smoke /
  comparison / sandbox outputs go here regardless of
  whether they're CLIP / IMAGE / AUDIO. Keeps `BACKDROP`
  semantically pure: a `BACKDROP`-tagged asset is meant for
  composite background use. The smoke_keyframes outputs
  (`c21fdeec` veo3.1_fast, `89a1ce5f` gen3a_turbo) backfill
  as `EXPERIMENT` even though they're technically scene
  clips by content — the operator's V18 finding
  (SESSION 184 calibration #6) was that re-using them as
  backdrops dragged identity-drift into production output.
  `EXPERIMENT` keeps them browseable but hides them from
  the future A7 role-filtered asset_picker.

---

## Storage-health categories

Computed by `apps.compositions.assets.compute_storage_health(asset)`:

| Status | Meaning | Operator action |
|---|---|---|
| `HTTPS_LIVE` | Runway/CDN URL with JWT exp > now + 24h | Usable everywhere |
| `HTTPS_EXPIRING_SOON` | JWT exp within 24h | Download / re-host before expiry |
| `HTTPS_EXPIRED` | JWT exp < now | Re-render or fetch fresh URL |
| `LOCAL_PRESENT` | `/data/_internal/...` path exists on disk | Usable in compositions; not portable |
| `LOCAL_MISSING` | `/data/...` path doesn't exist (cache cleared) | Re-render |
| `DATA_URI` | `data:image/...;base64,...` inline | Usable; bulky |
| `UPLOAD_PENDING` | Future upload UI placeholder | n/a v1 |

JWT exp parsed from the `_jwt=eyJ...` query parameter
(standard JWT payload `exp` field, seconds-since-epoch).

---

## New / extended models

* **`Asset.role`** — new `CharField(max_length=24, choices=...,
  null=False, default='RAW_UPLOAD')`. Ten-value TextChoices
  enum. Indexed for filter queries. Existing rows default to
  `RAW_UPLOAD` at A0 migration time; A1 backfill replaces
  with primitive_kind-derived role.
* **No new table.** Tags / extended metadata deferred.

---

## New / extended endpoints

* **`GET /api/workspace/assets/`** (new) — Paginated list.
  Query params:
  * `role=BACKDROP,TALKING_HEAD,...` (comma-list, optional)
  * `asset_type=CLIP,IMAGE,...` (existing categorization)
  * `primitive_kind=...` (production-method filter)
  * `storage=HTTPS_LIVE,LOCAL_PRESENT,...` (computed)
  * `q=...` (full-text against prompt / composition name)
  * `created_after`, `created_before` (ISO date)
  * Standard `page` / `page_size` pagination
  Returns each asset with computed `storage_health` field,
  producing step's prompt (when available), producing
  composition's name + id.
* **`GET /api/workspace/assets/<id>/`** (new) — Per-asset
  detail. Includes full lineage (producing composition,
  producing step, inputs to that step, downstream
  compositions that consumed this asset).

Both endpoints honor existing workspace membership +
owner-only-write surface (read for any member). Same
pattern as `/api/workspace/overview/` shipped in F-arc.

---

## Slice breakdown (9 slices, A0-A8)

Same shape as V15 / V16 / V17 — narrow scope, opt-in
defaults, no SPA changes per slice unless explicitly
called out. Each slice ships behind a migration where
applicable.

| Slice | What ships | Estimated effort | Status |
|---|---|---|---|
| **A0** | `Asset.role` enum field + migration. Default `RAW_UPLOAD` for new rows. Existing rows get `RAW_UPLOAD` until A1 backfill. | ½ session | **✓ SHIPPED (SESSION 185)** |
| **A1** | Backfill management command (`python manage.py backfill_asset_roles`, with `--commit` to apply, `--workspace NAME` to scope). Heuristic-driven from `source_spec.primitive_kind` + known-smoke-UUID special case. Operator reviews dry-run report before committing. | ½ session | **✓ SHIPPED (SESSION 185)** |
| **A2** | Every primitive in `apps.compositions.primitives` stamps role on its output. Migration test enforces no primitive emits without a role. | 1 session | **✓ SHIPPED (SESSION 186)** |
| **A3** | Storage-health helper + cached property. JWT exp parser. Filesystem existence check. | ½ session | **✓ SHIPPED (SESSION 187)** |
| **A4** | `GET /api/workspace/assets/` + `GET /api/workspace/assets/<id>/` read-only endpoints with filters. | ½ session | **✓ SHIPPED (SESSION 188)** |
| **A5** | SPA route `/workspace/assets` — list view with filter chips (role / asset_type / storage). Pagination. | 1 session | pending |
| **A6** | SPA per-asset detail view at `/workspace/assets/<id>` — lineage graph, prompts, downstream compositions, storage badge, copy-URL action. | 1 session | pending |
| **A7** | asset_picker gains optional `role` filter on the field metadata. V18's `backdrop_clip_id` picker filters to `role=BACKDROP`. Same shape for V8 broll_splice / pip_layout / cohost_layout. | ½ session | pending |
| **A8** | Composition-lineage cross-link (per F-arc): each composition's overview shows produced assets with role badges. | ½ session | pending |

Roughly **5-6 sessions** end-to-end across **9 slices
(A0-A8 inclusive)**. A0-A2 are foundational; A3-A4 unblock
A5-A6 frontend; A7 is the operator-visible payoff (V18's
backdrop_clip dropdown finally shows ONLY backdrops, not
119 mixed CLIPs, and `EXPERIMENT`-tagged smoke outputs are
hidden); A8 ties Asset Library back to the F-arc lineage
surface.

**Dependency tree:**

```
A0 (Asset.role migration)
  └─ A1 (backfill)
       └─ A2 (primitives stamp role at emit)
            └─ A3 (storage health helper)
                 └─ A4 (browse + detail endpoints)
                      ├─ A5 (SPA list view)
                      ├─ A7 (asset_picker role filter)
                      └─ A8 (F-arc lineage cross-link)
                          A5 also unblocks:
                            └─ A6 (SPA detail view)
```

A5 and A7 can ship in parallel after A4. A8 depends on
A5 surface only minimally.

---

## In-scope clarifications

* **The 13 existing `composite_video` outputs are split.**
  Backfill heuristic: composites that ARE another
  composition's `final_asset` get `COMPOSITE_OUTPUT`;
  composites consumed by downstream polish steps get
  `COMPOSITE_OUTPUT` too (they're still composites,
  intermediate or final). The polish *outputs* are
  `POLISH_OUTPUT`. Final-or-intermediate is orthogonal to
  role.
* **The 9 IMAGE assets backfill as `REFERENCE_IMAGE`.**
  All current V13 `generate_image` outputs fit (operator
  uploads will too once that UI lands).
* **`smoke_keyframes` outputs backfill as `EXPERIMENT`**
  (resolved SESSION 185 — see §Taxonomy notes). Backfill
  command recognizes `source_spec.primitive_kind ==
  'smoke_keyframes'` AND the two known smoke-emitted
  Asset IDs (`c21fdeec`, `89a1ce5f`) as `EXPERIMENT`.
  Future `smoke_*` commands default to `EXPERIMENT` at
  emit time.
* **`mix_audio` outputs backfill as `COMPOSITE_OUTPUT`**
  (resolved Q-a-1, SESSION 185). The output is a composite
  with mixed audio; `AUDIO_TRACK` is reserved for
  audio-only outputs.

---

## Out of scope

* **Asset upload UI** (operator-uploaded audio / image /
  video). Queued separately since SESSION 181;
  intersects this arc but ships under its own scope-lock.
* **Asset deletion / archival.** Mutation surface deferred
  to a later arc; FK to Composition + Spokesperson +
  RealtimeSession needs analysis first. v1 read-only.
* **Free-form tags.** Future possibility; v1 ships closed
  enum. The role enum can absorb new categories via
  migration if missing.
* **Avatar / Voice / Portrait as first-class Assets.**
  Today these live on Spokesperson directly
  (`runway_avatar_id`, `runway_voice_id`,
  `portrait_path`). Modeling them as Assets is a
  bigger refactor — defer.
* **Cross-workspace asset visibility / sharing.** V1
  rule 1 holds; no shared library.
* **Auto-refresh of expired JWT URLs.** Storage-health
  flags expired URLs but doesn't re-fetch. Operator
  decides whether to re-render or fetch a fresh task
  URL.
* **Bulk operations** (download, archive, retag).
  Deferred; v1 is browse-only.

---

## Open questions

| ID | Question | Resolution | Status |
|---|---|---|---|
| **Q-a-1** | Does the role enum land as 9 values or do we accept that some primitives have ambiguous roles (e.g., `mix_audio` could be COMPOSITE or AUDIO)? | **Resolved SESSION 185.** Enum lands at **10 values** (`EXPERIMENT` added for smoke / sandbox outputs). `mix_audio` → primary role `COMPOSITE_OUTPUT`. All ambiguity resolved at scope-lock, not deferred to A2. | resolved |
| **Q-a-2** | Backfill: auto-commit on `--commit`, or always show dry-run + require explicit operator OK? | **Resolved SESSION 185.** Always dry-run by default. Operator reviews the report, then re-runs with `--commit` to apply. No silent backfills. | resolved |
| **Q-a-3** | Storage health: do we cache the computed value (with 60s TTL) or compute live per request? | **Resolved SESSION 185.** Live per request for v1. JWT exp parse + filesystem stat is microseconds; correctness wins. Add cache only if A5 perf demands it. | resolved |
| **Q-a-4** | Asset detail view: do we re-use F-arc's composition lineage component (per-composition) or build a new per-asset variant? | **Resolved SESSION 185.** Extend the F-arc lineage component to accept both entry points. One component, two callers. | resolved |
| **Q-a-5** | `asset_picker` role-filter (A7): does the recipe form metadata add a `role_filter` field on `RecipeField`, or is it a per-recipe override? | **Resolved SESSION 185.** First-class `RecipeField.role_filter` field. Same shape as `asset_type` already is. Per-recipe override is whack-a-mole. | resolved |
| **Q-a-6** | Avatar / Voice / Portrait modeling — should V2 of this arc fold these into Assets, or keep them on Spokesperson? | **Deferred to v2 (as proposed).** v1 read-only inventory ships against the existing Asset table only. A4 endpoint MUST explicitly NOT return Spokesperson-attached media, and the SPA list view (A5) carries an honest gap note ("Avatars, voices, and portraits live on Spokesperson — not shown here in v1"). | deferred |

---

## Change log

* **2026-05-19 (SESSION 184)** — Initial scope proposal.
  Triggered by SESSION 184 V18 dogfood feedback (operator
  noticed the gen3a_turbo smoke output got picked as a
  backdrop because the picker had no way to distinguish
  scene clips from person-interpolation clips). Status:
  proposed. Scope-lock pending operator review.
* **2026-05-19 (SESSION 185)** — **LOCKED.** Operator
  review resolved Q-a-1 through Q-a-5; Q-a-6 deferred to
  v2 as proposed. Taxonomy expanded from 9 → 10 roles
  (`EXPERIMENT` added) to capture intent-vs-medium
  distinction surfaced by the V18 smoke-output dogfood.
  9 contract rules merged into `VIDEO_COMPOSITION_V1.md`
  as rules 14-22. Slice A0 opens immediately.
* **2026-05-19 (SESSION 185)** — **A0 SHIPPED.** `AssetRole`
  TextChoices enum (10 values) + `Asset.role` field
  (max_length=24, default=`RAW_UPLOAD`, indexed via new
  `workspace+role` Meta.Index). Migration
  `0009_a0_asset_role`. 4 new tests in
  `apps/compositions/tests/test_models.py` covering enum
  count, default, filter query, and round-trip for every
  enum value. Compositions suite: 484 → 488 (+4).
* **2026-05-19 (SESSION 185)** — **A1 SHIPPED.**
  `backfill_asset_roles` management command. Dry-run by
  default; `--commit` to apply; `--workspace NAME` to scope.
  Heuristic table covers all 20 known primitive_kind values
  (rule 20). Special-case for the 2 known smoke-emitted UUID
  prefixes (`c21fdeec`, `89a1ce5f`). 9 new tests in
  `test_backfill_asset_roles.py`. ALLOWED_FILES entry added
  to `test_isolation.py` (sanctioned writer note: role-only
  update, workspace anchor untouched). Dev-DB dry-run:
  **136 candidates / 128 mappable / 8 needs-review** (2
  audio + 6 image legacy rows pre-dating primitive_kind
  discipline). Compositions suite: 488 → 497 (+9); full
  shell suite 915 → 928 (+13 = A0+A1).
* **2026-05-19 (SESSION 186)** — **A2 SHIPPED.** Every
  primitive in `apps.compositions.primitives` now stamps
  `role` on its `PrimitiveResult` at emit time. New module
  `apps/compositions/asset_roles.py` hosts the canonical
  `PRIMITIVE_TO_ROLE` mapping + `KNOWN_EXPERIMENT_UUID_PREFIXES`
  + `derive_role` helper (moved from the A1 management command;
  command re-exports for backwards-compat). `PrimitiveResult`
  dataclass gained a `role: str = ""` field; the runner's
  `_persist_output_asset` passes it through to
  `Asset.objects.create(..., role=result.role)` AND raises
  `PrimitiveError("Contract rule 20")` if the role is empty
  (defense-in-depth runtime backstop). Realtime
  `capture_transcript` stamps `role=AssetRole.TRANSCRIPT.value`
  on its direct emit. New `test_primitive_role_coverage.py` —
  8 tests across 3 layers: AST scan of every primitive_kind
  literal vs `PRIMITIVE_TO_ROLE`; AST scan that every
  `PrimitiveResult(...)` constructor passes `role=`; runtime
  proofs for mock primitives + the runner's round-trip + the
  raise-on-missing backstop + the realtime transcript path.
  Two new sanctioned-writer entries in
  `test_isolation.py` files (compositions + realtime —
  coverage test seeds its own Composition/RealtimeSession
  rows). Compositions suite: 497 → 505 (+8); full shell suite
  928 → 936 (+8 = A2 coverage tests).
* **2026-05-19 (SESSION 188)** — **A4 SHIPPED.** New endpoints
  `GET /api/workspace/assets/` (paginated browse) +
  `GET /api/workspace/assets/<id>/` (per-asset detail with
  full lineage). `WorkspaceAssetViewSet` lives in
  `apps/compositions/views.py`; URLs mounted in
  `apps/compositions/urls.py` (path-based, not router,
  because A4 has only list+retrieve). Filters: `role` /
  `asset_type` / `primitive_kind` / `storage` / `q` /
  `created_after` / `created_before` (all comma-list where
  applicable). `storage_health` attached to every row via
  A3's `compute_storage_health`. Producing composition
  surfaces inline; producing step + downstream consumers
  surface on retrieve (inverted F5 lineage shape — F5
  walks composition→composition; A4 walks
  asset→compositions on both sides). Pagination
  via `WorkspaceAssetPagination` (page_size 25, max 100).
  Storage filter is post-query (storage_health is computed,
  not a DB column) with a 1000-row cap on the candidate
  set — acceptable for v1's paginated reads; A5 perf
  testing may motivate an annotated column later.
  Workspace resolution mirrors F-arc's `workspace_overview`
  (explicit `?workspace=` if provided + member, else
  `default_workspace_for(user)`). Distinct from existing
  `/api/assets/` (V15.2 picker) — A7 extends THAT endpoint
  with role-filter; A5/A6 build against THIS one.
  `test_workspace_assets_api.py` — 24 tests across auth +
  scoping + cross-workspace leakage + all filters + storage
  post-filter + pagination + retrieve lineage + 404
  paths. ALLOWED_FILES entry added to `test_isolation.py`
  (sanctioned writer; constructs its own Composition +
  Step + Asset rows for endpoint exercise). Compositions
  suite: 525 → 549 (+24); full shell suite 956 → 980 (+24).
* **2026-05-19 (SESSION 187)** — **A3 SHIPPED.** New module
  `apps/compositions/assets.py` hosts `StorageHealth` (7
  string constants) + `parse_jwt_exp(url)` + `compute_storage_health(asset)`.
  Live per request per Q-a-3 (no model field, no caching).
  Classifier branches: empty `file_path` → `UPLOAD_PENDING`;
  `data:` URI → `DATA_URI`; HTTPS/HTTP → JWT-aware classifier
  (`HTTPS_LIVE` / `HTTPS_EXPIRING_SOON` within 24h /
  `HTTPS_EXPIRED`); leading-slash path → filesystem existence
  check against `settings.MEDIA_ENGINE_DATA_ROOT` (default
  `<repo>/media-engine/`) → `LOCAL_PRESENT` / `LOCAL_MISSING`;
  unknown scheme → `UPLOAD_PENDING`. JWT parser handles
  Runway's Cloudfront-signed URL shape (`?_jwt=<header>.<payload>.<sig>`,
  base64url-decoded payload's `exp` claim in unix-seconds);
  malformed JWTs (bad encoding, missing exp, non-numeric exp,
  wrong segment count) fall through to `HTTPS_LIVE` rather
  than crash. New `test_storage_health.py` — 20 tests covering
  all 7 states + JWT parser edge cases + filesystem
  override-via-settings pattern (`MEDIA_ENGINE_DATA_ROOT`).
  ALLOWED_FILES entry added to `test_isolation.py` (sanctioned
  reader; only constructs its own Asset rows for the
  classifier). Compositions suite: 505 → 525 (+20); full shell
  suite 936 → 956 (+20 = A3 tests).
