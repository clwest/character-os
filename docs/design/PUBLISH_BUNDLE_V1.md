---
title: "Publish Bundle (B-14) — one render → many platform variants"
status: locked
proposed: 2026-05-20 (SESSION 205, slice B14.0)
locked: 2026-05-20 (SESSION 205, slice B14.0)
closed: null
companion_docs:
  - CONTENT_FORMAT_BACKLOG.md
  - VIDEO_COMPOSITION_V1.md
  - PERSONALIZED_VIDEO_V1.md
  - ASSET_LIBRARY_V1.md
---

# Publish Bundle — one source clip, N platform-ready variants

> **Status: PROPOSED (SESSION 205).** Third strategic-axis arc
> opening after B-1 (transcripts) + B-3 (personalized) +
> SESSION 204 cleanup. Per `CONTENT_FORMAT_BACKLOG.md` §B-14:
> "every customer ships to ≥3 platforms; right now they
> reformat manually. Owning publish-bundle is sticky."
> Eight contract rules; seven slices B14.0-B14.6. Lock target:
> SESSION 205.

---

## TL;DR

The V-arc shipped 18 recipes that produce **one polished video
per fire**. Every B2B customer who ships that video to Reels +
Shorts + TikTok + X + LinkedIn reformats it five times by
hand. **B-14 ships a `PublishBundle` that fans the source clip
into N platform-ready variants in one operator action** —
each at the right aspect ratio + duration cap. All ffmpeg, **~$0
incremental cost**.

This arc:

1. **A platform catalog** — five platforms ship in v1
   (Reels / Shorts / TikTok / X / LinkedIn) with explicit
   target_ratio + max_duration per platform.
2. **A `publish_variant` recipe** — `reformat_clip` +
   `trim_clip` (existing primitives). One Composition per
   variant.
3. **A `PublishBundle` + `PublishVariant` model pair** —
   mirrors C-arc's campaign + recipient shape. Status
   rollup; per-variant retry; per-platform error capture.
4. **A REST + SPA flow** — operator picks a source CLIP
   from the Asset Library → picks platforms → launches →
   watches variants render → browses produced platform-
   ready Assets.

Out of scope for v1: caption safe-zones (TikTok bottom UI /
Reels right-side actions); CSV-style batch source clips
(one source per bundle); auto-firing from B-3 personalized
campaigns; thumbnail / title / description generation
(separate B-15 axis); platform-direct distribution
(operator downloads + posts manually).

---

## Why now

Five drivers converge:

1. **All primitives ship + are real-mode validated.**
   `reformat_clip` (V9) supports the three aspect ratios
   we need (`1280:720`, `720:1280`, `960:960`); `trim_clip`
   (V9) handles arbitrary duration caps. B-14 is recipe +
   model + UI orchestration, not new ffmpeg work.
2. **Cost shape is genuinely $0.** Every variant is
   ffmpeg-only on already-rendered source bytes. The B-arc
   ($0.25/clip) and C-arc ($0.25/clip × N recipients) both
   cost real $; B-14 multiplies the value of every prior
   render at zero marginal spend.
3. **C-arc + SESSION 204 cleanup unblock dense fan-out.**
   The per-month videos cap now reads Composition rows
   correctly (SESSION 204). Without that cleanup, a bundle
   firing 5 variants would have inflated the count
   misleadingly. With it, variants can be tagged + excluded
   from the cap (Q-d-4).
4. **Distribution leverage is sticky.** Customers
   integrate with their content calendars; once they use
   "I render once, get 5 platform-ready clips," switching
   costs go up. Same composition stickiness rationale as
   the C-arc CSV ingest.
5. **Backlog priority.** §B-14 ranks 3rd among strategic
   axes in `CONTENT_FORMAT_BACKLOG.md` (after B-1 +
   B-3, both now shipped).

---

## Contract rules (load-bearing)

Eight rules. None overlap V1's existing 22 + B-1's 8 +
B-3's 9. D-arc rules become V1 rules 48-55 if a future
V-arc lock merges them.

1. **Single CLIP source per bundle.** Each PublishBundle
   takes exactly one `Asset(asset_type=CLIP)` as input.
   Multi-source bundles are v2. The source asset's
   workspace anchors the bundle.

2. **Workspace-scoped end-to-end.** Bundle + variant FKs
   to Workspace. Source CLIP must live in the same
   workspace as the bundle. Cross-workspace refs rejected
   at clean() + pre_save signal. Mirrors V1 rule 1 +
   B-1 rule 2 + B-3 rule 3.

3. **Per-platform variants are independent.** Each variant
   = one Composition firing the new `publish_variant`
   recipe. Per-variant failures don't block the bundle
   (mirrors B-3 rule 8). Operator retries failed variants
   individually.

4. **No new ffmpeg primitives.** v1 reuses `reformat_clip`
   + `trim_clip`. Captions deliberately deferred to v2 so
   the safe-zone work can land with the captioning
   primitive without complicating v1's surface (Q-d-3).

5. **Variants don't count against `videos_per_month`.**
   Each variant is pure ffmpeg on an already-rendered
   source; the source's Composition already counted at
   render time. SESSION 204's `get_usage()` is extended
   to exclude compositions whose `template_kind` is
   `publish_variant`. Tier gates on the SOURCE render,
   not on its packaging.

6. **Launch is operator-explicit.** Mirrors B-3 rule 6.
   Operator picks platforms, sees a $0 cost preview + the
   per-variant wall-time estimate, confirms.

7. **Platform catalog is closed in v1.** Five platforms
   (Reels / Shorts / TikTok / X / LinkedIn). Adding a new
   platform is a code change with operator-visible
   defaults, not a config knob. Avoids proliferation
   (every "what about Pinterest?" doesn't become a
   migration).

8. **Composition naming carries provenance.** Each
   variant's `Composition.name` follows
   `{bundle.name} — {platform_label}` (e.g.
   `"Q3 product launch — Reels"`). Asset Library filter-
   by-name-prefix surfaces a bundle's outputs as a group
   without new infrastructure. Same shape as B-3 rule 9.

---

## Platform catalog (v1)

Five platforms. `target_ratio` maps directly to the existing
`reformat_clip` ratios; `max_duration_ms` maps to `trim_clip`'s
end_ms.

| Platform key | Display | target_ratio | max_duration_ms | Notes |
|---|---|---|---|---|
| `reels` | Instagram Reels | `720:1280` | 60000 | 9:16 portrait, 60s |
| `shorts` | YouTube Shorts | `720:1280` | 60000 | 9:16 portrait, 60s |
| `tiktok` | TikTok | `720:1280` | 90000 | 9:16 portrait, 90s |
| `x_twitter` | X / Twitter | `1280:720` | 140000 | 16:9 landscape, 2:20 |
| `linkedin` | LinkedIn | `1280:720` | 30000 | 16:9 landscape, 30s (default) |

Q-d-2: LinkedIn supports both 16:9 and 1:1; v1 ships 16:9 as
the default. Per-bundle override deferred to a later slice if
operator demand surfaces.

The catalog lives in `apps.campaigns`... no, this is its own
arc — proposing `apps.publish` as the new app name to avoid
muddying the C-arc namespace. Q-d-10 for confirmation.

---

## Data model additions

### `apps.publish.models.PublishBundle`

Mirrors C-arc's `PersonalizedCampaign` shape closely.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `workspace` | FK Workspace | rule 2 isolation |
| `source_clip` | FK Asset | constrained to `asset_type=CLIP` via clean() |
| `name` | CharField(120) | operator-supplied |
| `selected_platforms` | JSONField (list[str]) | platform keys; snapshot at create |
| `status` | TextChoices | DRAFT / LAUNCHING / IN_FLIGHT / COMPLETED / PARTIAL / FAILED |
| `created_by` | FK User | |
| `launched_at` / `completed_at` / `created_at` / `updated_at` | DateTime | |

### `apps.publish.models.PublishVariant`

One row per `(bundle, platform)` pair.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `bundle` | FK PublishBundle | CASCADE |
| `platform_key` | CharField(40) | one of the catalog keys |
| `target_ratio` | CharField(20) | snapshotted from catalog at create |
| `max_duration_ms` | PositiveInteger | snapshotted from catalog at create |
| `status` | TextChoices | PENDING / QUEUED / RUNNING / COMPLETED / FAILED |
| `produced_composition` | FK Composition, nullable | set when launched |
| `error_message` | TextField, blank | populated on FAILED |
| `created_at` / `updated_at` | DateTime | |

Why snapshot platform values on the variant row? If the
catalog evolves (e.g. TikTok bumps to 120s in 2027), an
old bundle's variants still render at the original specs
they were created with. Idempotency for the audit trail.

Indexes:
- `(bundle, status)` — progress queries
- `(produced_composition)` — completion-signal reverse lookup
- `(workspace, status)` on PublishBundle — list view

Cross-workspace signal: post-save guard mirroring B-3.
PublishBundle's `source_clip.workspace` must match
`bundle.workspace`; `PublishVariant.produced_composition.workspace`
must match `bundle.workspace`.

---

## New / extended endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/publish_bundles/` | Body `{source_clip_id, name, selected_platforms[]}`. Creates a DRAFT bundle + 1 PublishVariant per platform. Returns the bundle. |
| `GET` | `/api/publish_bundles/` | List workspace bundles, filterable by `?status=`. |
| `GET` | `/api/publish_bundles/<id>/` | Detail + variant counts. |
| `GET` | `/api/publish_bundles/<id>/variants/` | Per-variant list ordered by platform. |
| `GET` | `/api/publish_bundles/<id>/forecast/` | `{variant_count, projected_cost_micros: 0, estimated_wall_time_s, ready_to_launch, blocking_reason?}`. |
| `POST` | `/api/publish_bundles/<id>/launch/` | Atomic fan-out: create N `publish_variant` compositions in a transaction; enqueue Celery after commit. |
| `POST` | `/api/publish_bundles/<id>/retry_variant/` | Body `{variant_id}`. Per-variant retry, mirroring B3.6's pattern. |
| `DELETE` | `/api/publish_bundles/<id>/` | DRAFT/terminal cascade; LAUNCHING/IN_FLIGHT refuses. |

Tier gate at launch: ONLY the per-bundle platform cap
(hard 10, can't exceed catalog size of 5 in v1). NO
per-month videos check (rule 5).

---

## New recipe

### `publish_variant`

| Field | Notes |
|---|---|
| `kind` | `publish_variant` |
| `template_kind` on Composition | `publish_variant` (used by SESSION 204's `get_usage()` exclusion per rule 5) |
| Inputs | `source_clip_id` (Asset CLIP), `target_ratio`, `max_duration_ms` |
| Steps | step 0: `reformat_clip` (target_ratio from variant); step 1: `trim_clip` (start=0, end=max_duration_ms, capped to source duration) |

The recipe is NOT operator-facing in the recipe gallery
(not added to `LIVE_RECIPE_KINDS`). It's invoked only
internally by the launch handler. Q-d-11 for confirmation.

The starter at `apps.compositions.starters.publish_variant`
takes `(source_clip, target_ratio, max_duration_ms,
spokesperson, workspace, name)` and creates the 2-step
composition. The spokesperson is the source clip's
spokesperson (recovered via the lineage; the variant doesn't
RE-bake the avatar, it just reformats the source clip's
existing avatar footage — same spokesperson by definition).

---

## Slice breakdown (7 slices, B14.0-B14.6)

| # | Slice | Effort |
|---|---|---|
| **B14.0** | This scope-lock doc | ½ session (current) |
| **B14.1** | Platform catalog + `publish_variant` recipe + starter + tests | ½ session. New file `apps/compositions/platform_catalog.py` (or `apps/publish/catalog.py` — Q-d-10). Recipe + starter in `apps.compositions`. Mark `template_kind="publish_variant"` for SESSION 204 cap exclusion. Add the exclusion to `get_usage()` (1-line change). |
| **B14.2** | `PublishBundle` + `PublishVariant` models + migration + cross-workspace signal | ½ session. New `apps.publish` app. |
| **B14.3** | REST + completion signal + per-variant retry | 1 session. `PublishBundleViewSet` with all 8 actions + the cross-app post_save receiver. Largest backend slice. |
| **B14.4** | SPA bundle list + create + detail + launch + grid (subagent) | 1 session. Routes: `/workspace/bundles` + `/workspace/bundles/new` + `/workspace/bundles/<id>`. Also: a "Publish bundle" button on the existing `/workspace/assets/<id>` (A6 detail) for the source-clip-first workflow. |
| **B14.5** | Real-mode dogfood + arc close | ½ session. Fire a bundle against one of the existing Marcus clips from the B-arc / C-arc dogfood. 5 platforms × 0 cost = clean validation. |

**Total: ~4-5 sessions** matching the backlog estimate.
Smaller than C-arc (10 slices) because no LLM helper, no
CSV parser, no template engine — just orchestration on top
of existing primitives.

---

## In-scope clarifications

* **Source CLIP must be in the workspace.** A6 Asset
  Library detail's "Publish bundle" button only enables
  for `asset_type=CLIP` rows. Operator can't publish an
  AUDIO or TRANSCRIPT asset.

* **Variants execute in parallel.** `execute_composition.delay()`
  per variant after the launch transaction commits. With 5
  variants × ~5s wall-time each on ffmpeg, end-to-end is
  ~5-10s for a 5-platform bundle.

* **Per-variant retry creates a new composition** —
  mirrors B3.6's Q-c-6 resolution. Old failed composition
  stays in the workspace as audit.

* **Bundle naming = composition naming prefix** (rule 8).
  Operator searches `/workspace/assets?q="Q3 product"` and
  sees all 5 variants grouped visually.

---

## Out of scope (v1)

* **Caption safe zones.** TikTok bottom UI overlap and
  Reels right-side action button overlap require knowing
  platform UI dimensions per render. v2 axis with its own
  primitive enhancement.
* **Multi-source bundles.** "Publish all 50 personalized
  videos to 5 platforms each" (B-3 ↔ B-14 composition) is
  v2. v1 is one bundle per source CLIP.
* **Automatic bundle firing from a B-3 launch.** Composing
  the two arcs end-to-end is a v2 axis — needs scope-lock
  conversation about per-recipient × per-platform
  economics + the SPA flow.
* **Per-platform captions** (separate text overlay /
  positioning per platform). v2.
* **Custom platform catalog** (operator adds Pinterest or
  whatever). Closed catalog v1 per rule 7.
* **Thumbnail + title + description generation** —
  separate B-15 axis.
* **Platform-direct distribution** (auto-upload to TikTok
  / IG / etc.). v2; needs each platform's auth + rate-
  limit + posting policy surface.
* **A/B variant per platform** (different captions /
  intros per recipient AND per platform). Separate B-18
  axis.

---

## Open questions (resolve in slices)

* **Q-d-1**: Confirm 5-platform v1 catalog (Reels /
  Shorts / TikTok / X / LinkedIn)? **Proposed**: yes. The
  big-5 social-video platforms; covers ~95% of B2B publish
  flows. Resolve at B14.0 lock.

* **Q-d-2**: LinkedIn default aspect ratio. **Proposed**:
  `1280:720` (16:9 landscape — most LinkedIn video is
  landscape in 2026). Per-bundle override deferred to v2.
  Resolve at B14.0 lock.

* **Q-d-3**: Captions in v1? **Proposed**: NO. Captions
  ship in v2 with platform-specific safe-zone handling so
  text doesn't overlap UI chrome. v1 is reformat + trim
  only. Resolve at B14.0 lock.

* **Q-d-4**: Variants count against `videos_per_month`?
  **Proposed**: NO (rule 5). Tag variant Compositions with
  `template_kind="publish_variant"` and exclude in SESSION
  204's `get_usage()` query. The 1-line change happens in
  B14.1. Resolve at B14.0 lock.

* **Q-d-5**: B-3 ↔ B-14 composition (auto-fire bundles
  from a personalized campaign launch)? **Proposed**: v2.
  v1 is operator-driven on a single source CLIP. Resolve
  at B14.0 lock.

* **Q-d-6**: Cost forecast shape. **Proposed**: show
  `projected_cost_micros: 0` + an estimated wall-time
  (5s × variant_count). The B-3 forecast UX template
  works; just swap the cost line for a wall-time line.
  Resolve at B14.3.

* **Q-d-7**: Tier gates on platform count? **Proposed**:
  hard cap 10 platforms per bundle (catalog size 5 makes
  this a defense-in-depth check); no tier-based cap
  because variants are ffmpeg-only. Source render is
  already tier-capped by the V-arc. Resolve at B14.0 lock.

* **Q-d-8**: Operator entry point — `/workspace/bundles/new`
  with a CLIP picker, or `/workspace/assets/<id>` with a
  "Publish bundle" button, or both? **Proposed**: BOTH.
  Asset-detail button is the natural "I just saw this clip,
  want to publish it" flow; the bundles route is the
  "campaigns / draft management" surface. Resolve at B14.4.

* **Q-d-9**: Re-running a bundle. **Proposed**: bundles
  are immutable after launch. Operator creates a new
  bundle (cheap; just creates the rows) if they want a
  different platform mix. Resolve at B14.0 lock.

* **Q-d-10**: App namespace — `apps.publish` (new) or
  extend `apps.campaigns`? **Proposed**: new `apps.publish`
  app. PublishBundle's shape mirrors PersonalizedCampaign
  closely but the entities are semantically different
  (campaigns are operator-authored content batches;
  bundles are platform-format derivatives of existing
  assets). Resolve at B14.0 lock.

* **Q-d-11**: Should `publish_variant` recipe appear in
  the `/recipes` SPA gallery? **Proposed**: NO. It's an
  internal recipe invoked by the bundle launch handler;
  surfacing it in the operator-facing gallery would
  encourage "manually publish one variant at a time"
  workflows that the bundle UX is designed to replace.
  Resolve at B14.1.

---

## Change log

* **2026-05-20 (SESSION 205, slice B14.0)** — Initial scope
  proposal. Third strategic-axis arc following B-1
  (transcripts, SESSION 202) + B-3 (personalized,
  SESSION 203) + SESSION 204 cleanup. Per
  `CONTENT_FORMAT_BACKLOG.md` §B-14 ranking. Eight
  contract rules; seven slices B14.0-B14.6.

* **2026-05-20 (SESSION 205, B14.0 LOCKED)** — Operator
  signed off as-proposed. All 8 contract rules accepted
  without revision. All 11 open questions accepted with
  proposed resolutions (5-platform catalog; LinkedIn
  1280:720; no captions v1; variants excluded from cap
  via template_kind tag; B-3↔B-14 composition deferred;
  $0 forecast + wall-time; hard cap 10 platforms; both
  entry points; immutable bundles; new apps.publish app;
  recipe not in operator gallery). Status flips proposed
  → locked. B14.1 (platform catalog + publish_variant
  recipe + cap exclusion) opens immediately.
