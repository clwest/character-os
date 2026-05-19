---
title: "Asset Library — Workspace Inventory + Taxonomy"
status: proposed
proposed: 2026-05-19 (SESSION 184)
companion_docs:
  - VIDEO_COMPOSITION_V1.md
  - WORKSPACE_FABRIC_V1.md
  - CHARACTER_OS_INVENTORY.md
---

# Asset Library — Workspace Inventory + Taxonomy

> **Status: PROPOSED.** Scope-lock pending operator review.
> If approved, scope-lock becomes 9 contract rules merged
> into V1 as the "Asset Library" sub-arc, and slices A0-A7
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
   / COMPOSITE_OUTPUT / INTRO_OUTRO_CARD / REFERENCE_IMAGE
   / B_ROLL / TRANSCRIPT / AUDIO_TRACK / RAW_UPLOAD).
   Stamped at primitive-emit time. Backfilled for existing
   rows via primitive_kind heuristics.
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
   nine roles (see §Taxonomy). Operator-defined free-form
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

Nine roles. Picked to cover every existing primitive
output without forcing ambiguity:

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
  COMPOSITE_OUTPUT.
* The smoke_keyframes outputs (`c21fdeec` veo3.1_fast,
  `89a1ce5f` gen3a_turbo) backfill as `BACKDROP` — they
  were produced as scene/motion experiments, fit the
  backdrop role even though produced via a smoke command
  rather than the standard `generate_visual_clip` path.

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
  null=False, default='RAW_UPLOAD')`. Indexed for filter
  queries.
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

## Slice breakdown (proposed)

Same shape as V15 / V16 / V17 — narrow scope, opt-in
defaults, no SPA changes per slice unless explicitly
called out. Each slice ships behind a migration where
applicable.

| Slice | What ships | Estimated effort | Status |
|---|---|---|---|
| **A0** | `Asset.role` enum field + migration. Default `RAW_UPLOAD` for new rows. Existing rows get `RAW_UPLOAD` until A1 backfill. | ½ session | pending |
| **A1** | Backfill management command (`python manage.py backfill_asset_roles --dry-run / --commit`) — heuristic-driven from `source_spec.primitive_kind`. Operator reviews dry-run report before committing. | ½ session | pending |
| **A2** | Every primitive in `apps.compositions.primitives` stamps role on its output. Migration test enforces no primitive emits without a role. | 1 session | pending |
| **A3** | Storage-health helper + cached property. JWT exp parser. Filesystem existence check. | ½ session | pending |
| **A4** | `GET /api/workspace/assets/` + `GET /api/workspace/assets/<id>/` read-only endpoints with filters. | ½ session | pending |
| **A5** | SPA route `/workspace/assets` — list view with filter chips (role / asset_type / storage). Pagination. | 1 session | pending |
| **A6** | SPA per-asset detail view at `/workspace/assets/<id>` — lineage graph, prompts, downstream compositions, storage badge, copy-URL action. | 1 session | pending |
| **A7** | asset_picker gains optional `role` filter on the field metadata. V18's `backdrop_clip_id` picker filters to `role=BACKDROP`. Same shape for V8 broll_splice / pip_layout / cohost_layout. | ½ session | pending |
| **A8** | Composition-lineage cross-link (per F-arc): each composition's overview shows produced assets with role badges. | ½ session | pending |

Roughly **5-6 sessions** end-to-end. A0-A2 are
foundational; A3-A4 unblock A5-A6 frontend; A7 is the
operator-visible payoff (V18's backdrop_clip dropdown
finally shows ONLY backdrops, not 119 mixed CLIPs); A8
ties Asset Library back to the F-arc lineage surface.

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
* **`smoke_keyframes` outputs** backfill as `BACKDROP`.
  Even though produced outside the primitive system, they
  occupy the backdrop role. The backfill command
  recognizes `source_spec.primitive_kind ==
  'smoke_keyframes'` as a BACKDROP heuristic.

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

| ID | Question | Resolution path | Status |
|---|---|---|---|
| **Q-a-1** | Does the role enum land as 9 values or do we accept that some primitives have ambiguous roles (e.g., `mix_audio` could be COMPOSITE or AUDIO)? | Slice A2 mapping table review — defer to operator at A2 slice-open. | open |
| **Q-a-2** | Backfill: auto-commit on `--commit`, or always show dry-run + require explicit operator OK? | A1 slice-open. Lean toward dry-run-required. | open |
| **Q-a-3** | Storage health: do we cache the computed value (with 60s TTL) or compute live per request? | A3 slice-open; cache is the obvious answer if browse list is paginated 50+. | open |
| **Q-a-4** | Asset detail view: do we re-use F-arc's composition lineage component (per-composition) or build a new per-asset variant? | A6 slice-open; lean toward extending F-arc since the graph shape is similar. | open |
| **Q-a-5** | `asset_picker` role-filter (A7): does the recipe form metadata add a `role_filter` field on `RecipeField`, or is it a per-recipe override? | A7 slice-open. | open |
| **Q-a-6** | Avatar / Voice / Portrait modeling — should V2 of this arc fold these into Assets, or keep them on Spokesperson? | Defer to V2 scope discussion. | deferred |

---

## Change log

* **2026-05-19 (SESSION 184)** — Initial scope proposal.
  Triggered by SESSION 184 V18 dogfood feedback (operator
  noticed the gen3a_turbo smoke output got picked as a
  backdrop because the picker had no way to distinguish
  scene clips from person-interpolation clips). Status:
  proposed. Scope-lock pending operator review.
