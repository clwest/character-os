---
title: "Video Composition Architecture — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-05-14 (SESSION 142)
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "MEDIA_ENGINE_INTERNAL_API.md"
  - "KNOWLEDGE_LAYER.md"
  - "SPA_ARCHITECTURE.md"
phase: 4
---

# Video Composition Architecture

> **Read first:** `KNOWLEDGE_LAYER.md` (the scope-lock pattern
> this doc follows — same load-bearing contract style),
> `MEDIA_ENGINE_INTERNAL_API.md` (the current `/internal/*`
> surface this doc extends), the SESSION 141 render audit
> (the bug that surfaced the architecture gap), and SESSION
> 142's runway-hackathon pipeline map (the inventory of what
> exists and what was wired up before).
>
> **Prior art:** `runway-hackathon/backend/app/services/*`
> (full directory imported into `character-os/media-engine/`
> as a git subtree — 5 distinct Runway endpoints, 15+ output
> kinds, ~2,000 lines of working composition logic, currently
> dormant). `runway-hackathon/backend/app/routers/campaigns.py`
> (30+ rich endpoints, none re-exposed in `/internal/*`).
> The `long_ad_service.py`, `dialogue_service.py`,
> `storyboard_service.py`, `scene_composite_client.py`,
> `polish_client.py`, `animated_pip_client.py`, `aleph_client.py`,
> `audio_client.py` modules are the seven load-bearing service
> files this architecture re-exposes as composable primitives.

---

## Purpose

The launch product needs a video pipeline that **composes** —
where a render can be "talking-head with a cinematic backdrop
the avatar is describing, captions burnt in, music bed under
the voice, polished intro card, exported as Reels." Today's
pipeline cannot express that, not because the capabilities are
missing (every one exists in `media-engine/app/services/`) but
because each capability is a **leaf endpoint**: it takes inputs
and produces a finished MP4. There is no notion of a clip being
an *input* to a larger composition.

The hackathon shipped 15+ video output kinds. Every one ends in
a single MP4. None of them know how to be a building block for
the next render. So even though `backdrop`, `animated-pip`,
`music-bed`, `long-ad`, `dialogue`, and `polish` all work
independently, the operator cannot ask for any combination of
two — because combination is not a concept the data model
holds.

This doc fixes that by introducing two primitives the system is
currently missing: **Asset** (a generated artifact that knows
how it was made and can be reused) and **Composition** (an
ordered sequence of steps that produce a final asset). Every
existing hackathon "kind" becomes a starter composition on top
of a small set of step primitives. Every future capability
slots in as one more primitive. The fan-out problem
(N output kinds × M modifiers = N×M endpoints) collapses to
"one set of primitives + a library of compositions."

### Why scope-lock first

This is the largest architectural change since the original
shell/media-engine split. It touches:

- The Django data model (new app: `apps.compositions`).
- The media-engine `/internal/*` contract (today's single
  `/internal/videos/` becomes ~12 per-primitive endpoints).
- The existing `Video` model (becomes a thin wrapper over a
  Composition's final asset — backwards-compatible with the
  current `/api/videos/` SPA surface).
- The knowledge layer's render integration (K6's
  `build_render_brief` becomes the script-synthesis step of
  the `generate_avatar_speech` primitive).
- Every spokesperson detail page (the "make a video" flow
  changes from one-shape-form to compose-from-recipe).
- Cost transparency (per-render cost estimation becomes
  feasible because each step has a known unit cost).

A bad architectural decision here locks in either fan-out
(N×M endpoints) or fan-in (one mega-endpoint with a huge
switch statement). Neither is recoverable cheaply. Locking the
surface area before any code lands matches the discipline that
made the knowledge layer ship without privacy regressions.

---

## Contract rules (load-bearing)

These bind every composition slice the same way
`KNOWLEDGE_LAYER.md`'s rules bind every knowledge slice.

1. **Every Asset has an explicit workspace anchor.**
   `Asset.workspace` is a required FK (DB-level NOT NULL).
   Workspace is never derivable through reverse relations or
   inferred from the requesting user. Same load-bearing rule
   as `KnowledgeDocument.workspace`.

2. **Every Composition has explicit workspace + spokesperson
   anchors.** Both required FKs. A Composition without a
   workspace is unrenderable by construction; a Composition
   without a spokesperson cannot reach K6's
   `build_render_brief` synthesis path.

3. **Cross-workspace asset references are rejected
   structurally.** A Composition can only reference Assets
   whose `workspace_id` matches its own. Enforced at save
   time + at step execution time (defense in depth — operator
   can't accidentally pull a competitor workspace's
   cinematic backdrop into their render).

4. **Step primitives are stateless.** Each step takes Assets
   + params, calls one media-engine `/internal/*` endpoint,
   writes one new Asset. No step holds private state between
   calls; all persistence lives on the Composition + Asset
   rows. Matches the media-engine stateless contract
   (`MEDIA_ENGINE_INTERNAL_API.md` rule 2).

5. **Linear ordering only in v1.** Compositions are an
   ordered list of steps, not a DAG. Each step's inputs are
   either Workspace assets or outputs of earlier steps.
   DAG support (parallel branches, conditional steps) is
   explicitly deferred to v2. Linear ordering covers every
   hackathon kind plus the seven new compositions
   §"Starter compositions" lists.

6. **Partial-failure resume is the default.** If step 4 of 7
   fails, the prior three Assets persist on the Composition.
   Operator can retry step 4 (with the same or different
   params) without re-running 1-3. Step status lives on the
   step row, not just on the composition.

7. **Cost is computed before render fires, not after.**
   Each step primitive exposes a unit-cost estimator
   (params → micros). Composition aggregates. Operator sees
   estimated total cost before clicking render. Actual cost
   gets recorded per-step after execution so reconciliation
   stays honest.

8. **Knowledge integration is one-way: composition reads
   knowledge, knowledge never reads composition state.**
   `generate_avatar_speech` step optionally pipes its script
   through `build_render_brief` (the existing K6 path) before
   firing `/internal/clips/avatar_speech/`. Compositions never
   query `KnowledgeChunk` rows directly — `KNOWLEDGE_LAYER.md`
   contract rule 2 (single retrieval surface) stands.

9. **Mock-mode is a composition-level concept.** A composition
   in mock-mode runs every step in mock mode. A composition in
   real-mode runs every step in real mode. Mixing is not
   supported in v1 — too many edge cases (mock avatar + real
   ffmpeg composite = a mock MP4 stitched over a real
   background, which is operator-confusing). Force-mock
   environment flag controls the whole composition.

---

## Framing corrections (carried from SESSION 142 conversation)

Two framings the queued investigations used that this doc
explicitly supersedes:

- **"Additional video kinds" is not a slice list.** Items 19
  + 21 in the start-here queue ("Additional video kinds —
  cinematic / dialogue / long_ad", "`lesson` video kind") read
  as new enum values to add. Under this architecture, no kinds
  get added — only step primitives. Existing kinds become
  starter compositions. Adding a "lesson" or "dialogue" output
  is no longer a backend slice; it's a row in
  `starter_compositions.py`.

- **"K6.5 — talking-head render rewire" is not a single
  rewire.** Treating it as "swap one endpoint" papers over the
  architectural debt. Under this doc, K6.5 becomes **V3** in
  the slice breakdown below — the first step primitive
  (`generate_avatar_speech`) lands behind a single-step
  composition. Functionally identical to the original K6.5
  scope (talking-head ad renders correctly via
  `/v1/avatar_videos`), but the data structure that lands is
  reusable for every later composition. Same delivery, better
  ground.

- **MoviePy is not a dependency. ffmpeg is.** The hackathon's
  composition layer is `ffmpeg subprocess` exclusively across
  ~2,000 lines. MoviePy wraps ffmpeg with a Python API but
  adds runtime weight and a second way to express filter
  graphs. v1 stays on raw ffmpeg subprocess (proven, already
  in `media-engine/app/services/`). Re-evaluate MoviePy only
  if a specific composition becomes painful to express in
  `ffmpeg -filter_complex`.

---

## Data model

### `Asset`

```python
class Asset(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)

    # The load-bearing anchor — required, never null
    workspace = ForeignKey(
        Workspace, on_delete=CASCADE,
        related_name='assets',
    )

    class AssetType(TextChoices):
        CLIP = 'clip', 'Video Clip'
        AUDIO = 'audio', 'Audio Track'
        IMAGE = 'image', 'Image'
        TRANSCRIPT = 'transcript', 'Transcript / Text'
        VOICE = 'voice', 'Runway Voice Resource'

    asset_type = CharField(max_length=20, choices=AssetType.choices)

    # Where the bytes live. For clips/audio/images: local file
    # path under media-engine/data/_assets/ OR external URL.
    # For voice: the Runway voice_id (no local file).
    # For transcript: empty (content lives in inline_content).
    file_path = TextField(blank=True, default='')

    # Inline content for small assets (transcripts, captions).
    # Empty for binary assets.
    inline_content = TextField(blank=True, default='')

    # How this asset was made — JSON record of the step
    # primitive name + input asset ids + params. Enables
    # provenance + idempotent re-runs.
    source_spec = JSONField(default=dict)

    # Type-specific metadata
    duration_ms = PositiveIntegerField(null=True, blank=True)
    width = PositiveIntegerField(null=True, blank=True)
    height = PositiveIntegerField(null=True, blank=True)
    mime_type = CharField(max_length=80, blank=True, default='')
    size_bytes = PositiveIntegerField(null=True, blank=True)

    # Cost provenance — what this asset cost to produce
    cost_micros = PositiveIntegerField(default=0)

    # Origin
    composition = ForeignKey(
        'Composition',
        on_delete=SET_NULL, null=True, blank=True,
        related_name='produced_assets',
    )  # null = "library asset" not tied to one render

    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=['workspace', 'asset_type']),
            Index(fields=['composition']),
        ]
        ordering = ['-created_at']
```

### `Composition`

```python
class Composition(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)

    # Required anchors — privacy + provenance
    workspace = ForeignKey(
        Workspace, on_delete=CASCADE,
        related_name='compositions',
    )
    spokesperson = ForeignKey(
        Spokesperson, on_delete=PROTECT,
        related_name='compositions',
    )

    # Operator-visible
    name = CharField(max_length=200)
    template_kind = CharField(
        max_length=80,
        blank=True, default='',
        help_text="Which starter composition this was forked from. "
                  "Empty for custom compositions.",
    )

    class Status(TextChoices):
        DRAFT = 'draft', 'Draft'
        PLANNING = 'planning', 'Planning'
        RUNNING = 'running', 'Running'
        PARTIAL = 'partial', 'Partial (some steps failed)'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    status = CharField(max_length=20, choices=Status.choices,
                        default=Status.DRAFT)

    # The deliverable. Null until a composition completes its
    # final step. Always an Asset of type CLIP (a composition's
    # deliverable is a video).
    final_asset = ForeignKey(
        Asset,
        on_delete=SET_NULL, null=True, blank=True,
        related_name='+',
    )

    # K6 carry-over — citation logging for renders informed by
    # knowledge chunks (per knowledge layer contract).
    knowledge_chunk_ids = JSONField(default=list, blank=True)

    # Cost transparency
    cost_estimate_micros = PositiveIntegerField(default=0)
    cost_actual_micros = PositiveIntegerField(default=0)

    # Mock-mode (per contract rule 9)
    mock_mode = BooleanField(default=False)

    error_message = TextField(blank=True, default='')

    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            Index(fields=['workspace', 'status']),
            Index(fields=['spokesperson', 'created_at']),
        ]
        ordering = ['-created_at']
```

### `CompositionStep`

```python
class CompositionStep(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    composition = ForeignKey(
        Composition, on_delete=CASCADE, related_name='steps',
    )

    # 0-indexed position in the composition's step list
    position = PositiveIntegerField()

    # Which primitive this step invokes — see §"Step primitives"
    primitive = CharField(max_length=80)

    # Inputs: list of {slot: str, asset_id: UUID|None,
    #                  from_step_position: int|None}
    # Either asset_id (workspace asset, library reuse) or
    # from_step_position (output of an earlier step).
    inputs = JSONField(default=list)

    # Params: primitive-specific JSON payload (script, ratio,
    # duration, ffmpeg filter spec, etc.)
    params = JSONField(default=dict)

    # Output of this step — populated by the executor when
    # the step succeeds. Null until then.
    output_asset = ForeignKey(
        Asset,
        on_delete=SET_NULL, null=True, blank=True,
        related_name='produced_by_step',
    )

    class Status(TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    status = CharField(max_length=20, choices=Status.choices,
                        default=Status.PENDING)

    # Telemetry
    cost_estimate_micros = PositiveIntegerField(default=0)
    cost_actual_micros = PositiveIntegerField(default=0)
    elapsed_ms = PositiveIntegerField(null=True, blank=True)
    error_message = TextField(blank=True, default='')

    # Media-engine task id, when the primitive is async
    media_engine_task_id = CharField(max_length=200,
                                      blank=True, default='')

    started_at = DateTimeField(null=True, blank=True)
    completed_at = DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['composition', 'position'],
                name='composition_step_unique_position',
            ),
        ]
        indexes = [
            Index(fields=['composition', 'position']),
            Index(fields=['status']),
        ]
        ordering = ['composition', 'position']
```

**Cross-workspace asset reference check** runs on
`CompositionStep.save()`: any input `asset_id` whose
`workspace_id` differs from the composition's raises
`ValidationError`. Same shape as
`KnowledgeDocument.clean()`'s cross-workspace check.

---

## Step primitives

A small, finite set. Each maps to one media-engine
`/internal/*` endpoint. Each is independently testable.
Adding a primitive is the only way to add capability;
adding a "kind" is no longer a backend operation.

| Primitive name | Inputs | Output | Backed by |
|---|---|---|---|
| `generate_avatar_speech` | spokesperson_avatar_id (param), script (param or transcript asset) | CLIP (talking-head, lip-synced) | Runway `/v1/avatar_videos` (`gwm1_avatars`) |
| `generate_visual_clip` | prompt (param), optional reference IMAGE, ratio + duration | CLIP (silent visual) | Runway `/v1/image_to_video` (`gen4_turbo`) OR `/v1/text_to_video` (`gen4.5`) |
| `generate_image` | prompt (param), optional reference IMAGE | IMAGE | Runway `/v1/text_to_image` (`gen4_image_turbo`) |
| `clone_voice` | audio_data_uri (param or AUDIO asset) | VOICE | Runway voice clone (already in `/internal/voices/`) |
| `design_voice` | description (param) | VOICE + AUDIO (preview) | Runway `/v1/voices` (`eleven_multilingual_ttv_v2`) |
| `dub_audio` | AUDIO asset, target_language (param) | AUDIO | Runway `/v1/voice_dubbing` |
| `style_remix` | CLIP, style_preset (param) | CLIP | Runway `/v1/video_to_video` (`gen4_aleph`) |
| `composite_video` | list[CLIP] + layout_spec (param) | CLIP | ffmpeg `-filter_complex` |
| `mix_audio` | CLIP + list[AUDIO] + mix_spec (param) | CLIP | ffmpeg audio filters |
| `add_captions` | CLIP, optional TRANSCRIPT (auto-generated if missing) | CLIP | ffmpeg subtitle burn + (Whisper for auto) |
| `add_intro_outro` | CLIP, intro_spec + outro_spec (params) | CLIP | ffmpeg title cards |
| `transcribe` | CLIP or AUDIO | TRANSCRIPT | OpenAI Whisper (new — not in hackathon) |
| `trim_clip` | CLIP, start_ms + end_ms (params) | CLIP | ffmpeg trim |
| `concat_clips` | list[CLIP] | CLIP | ffmpeg concat |
| `reformat_clip` | CLIP, target_ratio (param) | CLIP | ffmpeg scale + crop |
| `split_script` | TRANSCRIPT, chunk_target_chars (param) | list[TRANSCRIPT] | gpt-5-mini sentence-boundary split (mirrors hackathon's `long_ad_service.py` splitter logic) |

Sixteen primitives. Every existing hackathon service file
maps to at most two primitives. Most of the work in V3-V14
below is **wrapping** existing service code as a step
primitive, not writing new code.

The two primitives `split_script` + `concat_clips` ship
together in V5 (long-form ad) — they're co-dependent, and
neither stands alone outside that composition.

---

## Composition execution

A new Celery task in `apps.compositions.tasks`:

```python
@shared_task(name='compositions.execute', bind=True, max_retries=2)
def execute_composition(self, composition_id: str) -> dict:
    """Walk every step in position order, fire the matching
    media-engine endpoint, persist the output Asset, advance
    the step status. Stop on first failure (status=PARTIAL).
    Operator retries via a separate `retry_step` task.
    """
```

### Step-by-step state machine

```
composition.status:
  DRAFT ──► PLANNING ──► RUNNING ──┬──► COMPLETED
                                   ├──► PARTIAL  (some failed)
                                   └──► FAILED   (step 1 failed)

per-step status:
  PENDING ──► RUNNING ──┬──► SUCCEEDED
                        └──► FAILED
```

### Partial-failure resume

If step 4 of 7 fails:

- step 4 status → `FAILED`, error_message populated
- composition status → `PARTIAL`
- steps 5-7 stay `PENDING`
- steps 1-3 retain their `output_asset` references
- operator clicks "retry step 4" → `retry_step` task
  re-fires step 4 with the same inputs (or new params if
  operator edited them). On success, composition resumes
  from step 5 automatically.

### Asset lifecycle within a composition

Intermediate assets persist on the Asset table during
execution. When a composition completes:

- Final asset is marked on `composition.final_asset`.
- Intermediate assets stay attached via `composition` FK —
  operator can inspect "what fed this render."
- Garbage collection: deferred to V2. Cascade-on-delete keeps
  asset table size proportional to active compositions.

### Cost estimation up front

Before composition execution starts, the planner computes
`cost_estimate_micros` per step (params → micros via a
per-primitive estimator function). Composition's
`cost_estimate_micros` is the sum. SPA shows it to operator
before they click render. Per-primitive estimators ship as
small pure functions in `apps/compositions/cost.py`.

---

## Starter compositions

Every hackathon kind, re-expressed as a starter composition.
Plus seven new compositions that the hackathon couldn't build
because the kinds were terminal.

### Ports of hackathon kinds (one-to-one mapping)

| Composition name | Steps |
|---|---|
| `talking_head` | 1: `generate_avatar_speech` |
| `talking_head_polished` | 2: `generate_avatar_speech` → `add_intro_outro` |
| `cinematic_visual` | 1: `generate_visual_clip` |
| `cinematic_with_voiceover` | 3: `generate_visual_clip` + `generate_avatar_speech` → `composite_video`(audio-only overlay) |
| `long_form_ad` | 3+: `split_script` → N× `generate_avatar_speech` → `concat_clips` |
| `dialogue_scene` | N+1: N× `generate_avatar_speech` (alternating cast) → `concat_clips` |
| `storyboard_ad` | 4-7: 1-3× `generate_image` + 3× `generate_visual_clip` → `concat_clips` |
| `storyboard_voiced` | starter `storyboard_ad` → `generate_avatar_speech` → `mix_audio` |
| `style_remix_pass` | 1: `style_remix` (modifier — input is an existing CLIP) |
| `multi_lang_dub` | 2: `transcribe` (if needed) → `dub_audio` (modifier) |
| `polished_pack` | 2: `add_captions` → `add_intro_outro` (modifier) |
| `pip_layout` | 1: `composite_video` (PiP layout spec) (modifier) |
| `backdrop_layout` | 1: `composite_video` (backdrop layout — reverse PiP) (modifier) |
| `cohost_layout` | 1: `composite_video` (cohost layout — multi-avatar) (modifier) |
| `music_bed_pass` | 1: `mix_audio` (music spec) (modifier) |
| `broll_splice` | 1: `composite_video` (B-roll splice spec) (modifier) |
| `reels_format` | 1: `reformat_clip` (ratio 9:16) (modifier) |

### New compositions the hackathon couldn't build

These compose primitives in ways the terminal-endpoint model
couldn't express:

| Composition name | Steps | Why new |
|---|---|---|
| `talking_head_with_backdrop` | 3: `generate_visual_clip` (backdrop) + `generate_avatar_speech` → `composite_video` (avatar over backdrop, knowledge-informed via K6) | Hackathon's `backdrop` endpoint took an existing cinematic clip + an existing avatar clip — operator had to fire both separately, no knowledge integration |
| `talking_head_full_polish` | 5: `generate_visual_clip` + `generate_avatar_speech` → `composite_video` → `add_captions` (auto-transcribed) → `add_intro_outro` | Hackathon required 4 separate endpoint calls with manual asset wiring |
| `long_form_with_backdrop` | 5+: `generate_visual_clip` (backdrop) + `split_script` → N× `generate_avatar_speech` → `concat_clips` → `composite_video` (avatar over single backdrop, all clips) | Hackathon's long-ad was speech-only; no backdrop integration |
| `recut_teaser` | 4: `transcribe` (source) → `split_script` (pick strongest sentence via gpt-5) → `trim_clip` → `reformat_clip` (9:16) | Take a 60s render, produce a 15s vertical teaser. No hackathon equivalent — every output was from scratch. |
| `dialogue_with_shot_reverse_shot` | dynamic: per dialogue line, `generate_avatar_speech` + optional `generate_visual_clip` (cutaway), `concat_clips` with editor-chosen cut timings | AI editorial cuts — hackathon's dialogue was straight-stitched monologues |
| `seasonal_recolor` | 2: `style_remix` (preset) → `add_captions` | Reuse a finished ad as a holiday variant via Aleph remix |
| `knowledge_grounded_explainer` | 3: `build_render_brief` (K6 path, multi-chunk) → `generate_avatar_speech` (long-form) → `add_captions` (auto) | The "lesson" video kind from the queue, re-expressed honestly. Knowledge layer feeds it; no special-cased `lesson` enum. |

---

## Media-engine `/internal/*` extensions

Today the media-engine exposes 5 verbs (avatars, voices,
videos, portrait, polling). Under this architecture it
exposes ~12 per-primitive verbs, all stateless, all small.
Each can ship independently.

| Method | Path | Primitive | Status |
|---|---|---|---|
| POST | `/internal/clips/avatar_speech/` | `generate_avatar_speech` | ✓ SHIPPED V3 |
| POST | `/internal/clips/visual/` | `generate_visual_clip` | ✓ SHIPPED V4 |
| POST | `/internal/images/` | `generate_image` | ✓ SHIPPED V13 |
| POST | `/internal/voices/` | `clone_voice` | ALREADY SHIPPED (pre-V0) |
| POST | `/internal/voices/design/` | `design_voice` | ✓ SHIPPED V10 |
| POST | `/internal/audio/dub/` | `dub_audio` | ✓ SHIPPED V10 |
| POST | `/internal/clips/style_remix/` | `style_remix` | ✓ SHIPPED V11 (with chunked path) |
| POST | `/internal/clips/composite/` | `composite_video` | ✓ SHIPPED V7 |
| POST | `/internal/audio/mix/` | `mix_audio` | ✓ SHIPPED V7 |
| POST | `/internal/clips/captions/` | `add_captions` | ✓ SHIPPED V9 |
| POST | `/internal/clips/intro_outro/` | `add_intro_outro` | ✓ SHIPPED V9 |
| POST | `/internal/transcribe/` | `transcribe` | ✓ SHIPPED V12 |
| POST | `/internal/audio/extract/` | `audio_extract` | ✓ SHIPPED V14 |
| POST | `/internal/clips/trim/` | `trim_clip` | ✓ SHIPPED V9 |
| POST | `/internal/clips/concat/` | `concat_clips` | ✓ SHIPPED V5 |
| POST | `/internal/clips/reformat/` | `reformat_clip` | ✓ SHIPPED V9 |
| GET | `/internal/tasks/{task_id}/` | (generalised poll) | ✓ SHIPPED V3 |

### Generalised poll endpoint

The current `GET /internal/videos/{task_id}/` becomes
`GET /internal/tasks/{task_id}/`. Same state machine
(`pending → rendering → ready|failed`); just generalised so
every async primitive (avatar speech, visual clip, style
remix, transcribe) polls the same way. Mock-mode behaviour
unchanged.

### Asset-URL contract

Every async primitive's terminal `ready` response carries an
`output_url` that the shell can fetch + persist as an Asset's
`file_path`. Synchronous primitives (composite, trim, concat,
captions — all ffmpeg-local) return inline:

```json
{
  "status": "ready",
  "output_url": "/data/_assets/<hash>.mp4",
  "duration_ms": 12500,
  "width": 1280, "height": 720,
  "cost_micros": 0,
  "mock_mode": false
}
```

---

## Migration: V1 — schema only, no semantic change

V1 produces zero user-visible value. It is pure infra,
exactly like K1's Postgres swap. We name this explicitly so
neither operator nor AI gets demoralized mid-slice.

### Scope of V1

- New Django app `apps.compositions`.
- `Asset`, `Composition`, `CompositionStep` models +
  migration.
- Repo-level isolation test
  (`test_only_composition_module_writes_assets`) — analogous
  to K2's retrieval-isolation test.
- Cross-workspace asset reference test
  (`test_step_rejects_cross_workspace_assets`).
- Admin registration so we can inspect rows.
- The existing `Video` model + `apps/videos/views.py` stays
  untouched. No backwards-compatibility shim needed yet —
  V3 wires the first real composition.

V1 ships when `python manage.py check`, `migrate --check`,
the smoke commands, and every existing K-test still pass.
The new app has 4-5 tests of its own. No SPA changes.

---

## Slice breakdown

Like the wizard and knowledge layers, the composition arc is
a sequence of slices that can land independently. Each slice
is ~1-2 sessions.

| Slice | Deliverable | Subsumes |
|---|---|---|
| **V0** | Scope lock (this doc) | — |
| **V1** | `Asset` + `Composition` + `CompositionStep` schema, privacy guards, isolation tests | — |
| **V2** | Composition runtime: `execute_composition` Celery task + per-step state machine + partial-failure resume + retry-step. No primitives wired yet; runtime tested with a mock primitive. | — |
| **V3** ✓ | `generate_avatar_speech` primitive + `talking_head` starter. Talking-head renders work correctly via `/v1/avatar_videos`. Ships SESSION 143 (`54032c2`). **Closes K6.5.** | **K6.5** |
| **V4** ✓ | `generate_visual_clip` primitive (`gen4_turbo` image-to-video, `gen4.5` text-to-video) + `cinematic_visual` starter. Ships SESSION 143 (`1251def`). | "Additional video kinds — cinematic" |
| **V5** ✓ | `split_script` + `concat_clips` primitives + `long_form_ad` starter. Ports hackathon's `long_ad_service.py`. Operator can render multi-minute talking-head ads. **Promoted from V7 SESSION 142** — long-form is a launch differentiator (no AI provider ships >20s in one call; everything long-form is stitched). Ships SESSION 143 (`c2c4ba2`). | "Additional video kinds — long_ad" |
| **V6** ✓ | Backwards-compat shim — existing `Video` model becomes a thin wrapper that creates a `talking_head` composition on `Video.create`. `/api/videos/` SPA surface unchanged. Composition→Video sync via post_save signal. Ships SESSION 143 (`7c968a5`). | — |
| **V7** ✓ | Composite primitives: `composite_video` (4 layouts: pip/backdrop/cohost/broll) + `mix_audio` (music_bed). 5 layout-modifier starters (`pip_layout`, `backdrop_layout`, `cohost_layout`, `music_bed_pass`, `broll_splice`). **Reordered from V9 SESSION 143** — V8 structurally depends on `composite_video`. Ships SESSION 143 (`3af1c28`). | — |
| **V8** ✓ | First multi-step starter: `talking_head_with_backdrop` (3 steps: `generate_visual_clip` + `generate_avatar_speech` → `composite_video` kind=backdrop). Demonstrates the composition architecture's payoff — zero new primitives, zero new endpoints. Ships SESSION 143 (`545f991`). | — |
| **V9** ✓ | Polish + format primitives: `add_captions` (script-driven), `add_intro_outro`, `trim_clip`, `reformat_clip`. Adds `talking_head_polished` + `reels_format` starters. Ships SESSION 143 (`ec130a9`). | "Cast sync command" priority shift |
| **V10** ✓ | Voice flows: `design_voice` + `dub_audio` primitives + `voice_design` + `multi_lang_dub` starters. Restores hackathon-shipped 29-language dubbing (the operator confirmed live production usage). Ships SESSION 143 (`f237ac7`). | "Voice preset audit" |
| **V11** ✓ | `style_remix` primitive (Aleph `gen4_aleph` with full chunked-path support — split→parallel remix→concat for sources >5.5s) + `style_remix_pass` starter. 5 style presets (noir/anime/chrome/watercolor/cyberpunk). Ships SESSION 143 (`cfe9214`). | — |
| **V12** ✓ | `transcribe` primitive (OpenAI Whisper) + `add_captions` auto mode (reads TRANSCRIPT input) + `recut_teaser` composition. **First net-new capability beyond what the hackathon shipped.** Ships SESSION 143 (`8b24465`). | — |
| **V13** ✓ | `generate_image` primitive (Runway `gen4_image`) + `storyboard_ad` starter (7-step Hook/Action/Payoff with reference-image coherence chain). `storyboard_voiced` deferred — requires an `audio_extract` primitive scheduled for V14+. Ships SESSION 143 (`43be57b`). | "Additional video kinds — cinematic" (storyboard arc) |
| **V14** ✓ | `dialogue_scene` starter (ports hackathon's `dialogue_service.py`) + `audio_extract` primitive (unlocks the deferred `storyboard_voiced`). Ships SESSION 143 (`6f61e4b`). | "Additional video kinds — dialogue" |
| **V15.0** ✓ | Backend foundation for the SPA gallery — `apps/compositions/recipes.py` registry of 17 recipe metadata entries + REST surface (`GET /api/recipes/`, `POST /api/compositions/`, `GET /api/compositions/{id}/`). 24 V15.0 backend tests. Ships SESSION 144 (`1781cb1`). | "W12 — Legacy form retirement" |
| **V15.1** ✓ | SPA gallery shell + first three live recipes (`talking_head`, `cinematic_visual`, `talking_head_polished`); other 14 cards "coming soon". Dashboard CTA flips to `/recipes`. New routes: `/recipes`, `/recipes/:kind`, `/compositions/:id`. Ships SESSION 144 (`74a70d7`). | — |
| **V15.2** ✓ | Layout + format family forms live (7 recipes: `pip_layout`, `backdrop_layout`, `cohost_layout`, `broll_splice`, `music_bed_pass`, `reels_format`, `talking_head_with_backdrop`). Adds `GET /api/assets/` + SPA `asset_picker` field renderer. Ships SESSION 144 (`c9a5d8c`). | — |
| **V15.3** ✓ | Voice + style + long-form + storyboard + recut family forms live (6 recipes: `voice_design`, `multi_lang_dub`, `style_remix_pass`, `long_form_ad`, `storyboard_ad`, `recut_teaser`). One-line `LIVE_RECIPE_KINDS` flip — the form renderer + asset_picker shipped in V15.1-V15.2 already cover all field types these recipes need. Ships SESSION 144 (`8530a08`). | — |
| **V15.4** ✓ | Dialogue (`dialogue_scene`) form with dynamic line-list editor + ships `storyboard_voiced` bonus recipe (10 steps; V14 `audio_extract` unblocked it) + flips spokesperson detail "Make a video" CTA to `/recipes` (soft-retires legacy single-form UI). Closes the V-arc. Ships SESSION 144 (`68ab5d2`). | — |

Roughly 16 slices, ~12-18 sessions. V0 ships on commit of
this doc. V1-V4 is the "ground re-laid" arc (architecture +
two foundational primitives, no user-visible compositions
yet). **V5 is the first slice that gives operators a
capability the legacy flow cannot match** — long-form
talking-head ads via script-chunk-and-stitch. V6
backfills backwards-compat so the legacy `/api/videos/`
surface keeps working while the SPA migrates. V7-V15 is
the capability roll-out for the remaining starter
compositions.

### Critical-path framing

Three slices are load-bearing for the rest of the work:

- **V1** establishes the data shape. Every later slice
  depends on this.
- **V2** establishes the execution model. Every primitive
  beyond V3 plugs into this runtime.
- **V6** establishes backwards-compat. Without it, the SPA
  has to ship V15 the same session V3 ships, which is too
  much in one slice.

Everything from V7 onward is parallelizable in principle.
V5 (long-form) sits ahead of V6 deliberately — long-form
is the first launch-differentiating capability and it
doesn't depend on the backwards-compat shim (operators can
drive it via the new Composition surface during the
transition; the legacy `/api/videos/` flow stays unchanged
until V6 + V15).

---

## Out of scope (explicitly)

- **DAG compositions.** Linear ordering only in v1.
  Parallel branches, conditional steps, fan-out/fan-in are
  v2 work. The handful of compositions that *might* want
  DAG (e.g., `talking_head_with_backdrop` could in principle
  fire the backdrop + speech in parallel) ship as
  sequential in v1; the latency hit is tolerable.

- **Composition marketplace / sharing across workspaces.**
  Same rule as the knowledge layer: each workspace owns its
  compositions. No global library, no public templates,
  no operator-published recipes. v2 might add an
  operator-only "official starters" surface; v1 keeps it
  per-workspace.

- **Operator-authored custom step primitives.** No way to
  write new Python in v1. Step primitives are a fixed
  finite set defined in `apps/compositions/primitives/`.
  Adding one is a backend change (slice), not a runtime
  configuration.

- **Real-time conversation video is its OWN arc, not this
  arc.** WebRTC realtime avatar (hackathon's
  `/v1/realtime_sessions` + `realtime_avatar_client.py`)
  ships under a parallel scope lock — `REALTIME_AVATAR_V1.md`
  (R0, pending). Compositions in *this* arc produce
  *recorded* video deliverables. The shared boundary: a
  realtime session may capture transcripts / generated
  clips that get persisted as `Asset` rows so they're
  addressable by recorded-video compositions later. That
  shared dependency is why V1's data model has to ship
  before R0 can lock — the Asset shape needs to handle both
  arcs' artifacts without forking.

- **DaVinci Resolve template integration.** The hackathon's
  `resolve_client.py` is local-only (requires Resolve
  installed on the operator's machine). Stays out of SaaS
  scope. Operator-facing DaVinci handoff (export → load in
  Resolve manually) is fine but not orchestrated.

- **Per-frame timeline editing UI.** No scrubbing, no
  keyframes, no manual cut adjustment. Recipe gallery
  (V15) is the v1 UX ceiling. The "full editor" mental
  model is v3+ work.

- **Auto-generated music (compose original score).** Music
  beds come from operator-supplied audio assets. No "AI
  composes a 30-second royalty-free track" feature.

- **AI-driven editorial cuts without human approval.**
  V14's `dialogue_with_shot_reverse_shot` uses AI to
  *propose* cut timings, but the operator approves the
  cut list before render. No fully-autonomous editorial
  decisions in v1.

- **Asset library re-use UI.** The data model supports it
  (Asset.composition can be null = "library asset"), but
  the SPA only shows assets within their composition in
  v1. A dedicated "workspace asset library" surface is v2.

---

## Open questions (resolve in implementation slices)

- **Q-v-1 — Asset garbage collection.** Compositions accrue
  intermediate assets. When a composition is deleted (soft
  or hard), what happens to its asset rows + files? Lean:
  cascade delete in v1, with a soft-delete flag added in v2
  if operators ask for "trash bin" recovery. Resolve in V1.

- **Q-v-2 — Step retry counts.** Network blip on
  step 4 — retry inline or surface a manual retry button?
  Lean: 2 automatic retries inline (matches K3's embedding
  pattern), then surface manual retry. Resolve in V2.

- **Q-v-3 — Step input schema validation.** Each primitive
  has its own input shape. Lean Pydantic models in
  `apps/compositions/primitives/<name>.py:InputSchema` —
  same pattern as DRF serializers. Resolve in V3.

- **Q-v-4 — Per-primitive cost estimators.** Concrete unit
  costs per primitive (gpt-5-mini ~$0.0001/call, avatar
  speech ~$0.05/sec at 1280x720, etc.). Lean: hardcoded
  estimators in `apps/compositions/cost.py` with
  per-primitive functions. Resolve in V2 + tighten
  per-slice.

- **Q-v-5 — Whisper provider.** OpenAI Whisper API or
  self-hosted whisper.cpp? OpenAI is wire-consistent with
  K6's gpt-5-mini call site; self-hosted is cheaper at
  scale but adds operational complexity. Lean OpenAI for
  v12; revisit if cost becomes load-bearing.

- **Q-v-6 — Recipe SPA shape.** v15 ships the recipe
  gallery — gallery of cards (Pinterest-style) or
  category-sectioned list (talking-head / cinematic /
  long-form / modifiers)? Resolve in V15 planning with the
  brand identity doc.

- **Q-v-7 — Tier-gated compositions.** Some starter
  compositions are expensive (`long_form_with_backdrop` =
  10+ API calls). Tier limits today are "videos per month"
  (count-based). Under composition, they need to be
  "cost-based" (micros per month). Resolve when billing
  hits the agency tier (Phase 5) — for now, count-based
  works.

- **Q-v-8 — Cross-composition asset reuse.** Operator's
  cinematic backdrop generated for ad #1 — can it be
  reused in ad #2? Data model supports it (Asset.composition
  is nullable). SPA-side UX deferred to v2 (per "out of
  scope"). Resolve when the asset library UI ships.

- **Q-v-9 — Mock-mode for non-Runway primitives.** ffmpeg
  primitives (concat, trim, composite) run locally — no
  mock-mode needed in theory. But for hermetic e2e tests
  we may want them to short-circuit too. Lean: ffmpeg
  primitives respect `RUNWAY_FORCE_MOCK` and return
  deterministic stub outputs (a 1-frame black MP4) when
  set. Resolve in V7 (composite primitive slice, was V9
  before SESSION 143 reorder).

---

## How to verify the composability guarantee

Before V6 closes, four test cases must pass:

1. **`test_cross_workspace_asset_reference_rejected`**:
   create workspaces A and B; create an Asset in B; try to
   reference it from a Composition in A; assert
   `ValidationError`.

2. **`test_partial_failure_resumes_from_failed_step`**:
   create a 4-step composition; force step 3 to fail;
   assert steps 1-2 retain their assets, step 3 is FAILED,
   step 4 is PENDING; retry step 3; assert composition
   completes.

3. **`test_starter_composition_clones_to_workspace`**: pick
   a starter composition (`talking_head_with_backdrop`);
   instantiate it in workspace A with new params; assert
   the resulting CompositionSteps are workspace-A-scoped
   and the starter row itself is untouched.

4. **`test_cost_estimate_matches_actual_within_tolerance`**:
   execute a composition in mock mode; assert
   `cost_actual_micros` is within ±10% of
   `cost_estimate_micros` for every step (mock mode has
   deterministic stub costs).

The four tests are the contract. Implementation can vary;
the tests cannot fail.

---

## Change log

- 2026-05-14 (SESSION 142) — Initial scope lock. Triggered
  by SESSION 141's render-pipeline audit finding (K6
  routes to wrong Runway endpoint) plus SESSION 142's
  runway-hackathon pipeline mapping (15+ output kinds
  existed but never composed). Architecture choice: Asset
  + Composition model (option B from the SESSION 142
  conversation), rejecting recipe-template flat list
  (option A — combinatorial fan-out) and project-as-
  timeline editor (option C — too heavy for v1). Nine
  load-bearing contract rules locked. Sixteen step
  primitives identified, all but one (`transcribe`)
  mappable to existing hackathon service files. Sixteen
  slices V0-V15 sequenced; K6.5 absorbed into V3.
  MoviePy explicitly rejected in favor of raw ffmpeg
  subprocess. DaVinci Resolve + DAG + operator-authored
  primitives ruled out of scope. Real-time WebRTC reframed
  mid-session: confirmed in-scope but as a separate parallel
  arc (R0+) under its own scope lock, not part of V0-V15.
  Shared dependency: V1's Asset shape must support realtime
  artifacts so the two arcs don't fork the data model.

- 2026-05-14 (SESSION 142, late-session) — Slice reorder:
  promoted long-form to V5 (was V7); demoted backwards-
  compat to V6 and `talking_head_with_backdrop` to V7.
  Trigger: operator's realization that no AI provider
  ships single-call video longer than ~20 seconds, so
  every long-form AI video output in the wild is stitched
  from short clips. Long-form (`split_script` + `concat_clips`
  + `long_form_ad`) is the first launch-differentiating
  capability — most SaaS competitors sell 5-15 second
  outputs because that's what the providers ship.
  Bringing it forward to the third capability slice
  (right after the two foundational primitives V3 + V4)
  positions the platform's distinctive selling point as
  early as possible. The reorder is safe: V5's only
  dependency is V3 (`generate_avatar_speech`) for pure
  talking-head long-form; V4 is independent. The legacy
  `/api/videos/` flow stays functional during the gap
  between V5 and V6 (backwards-compat) because V3 fixed
  the underlying media-engine endpoint routing as part
  of K6.5 absorption.

- 2026-05-14 (SESSION 143, post-V6) — Second slice reorder:
  promoted composite primitives to V7 (was V9); demoted
  `talking_head_with_backdrop` to V8 (was V7) and polish
  primitives to V9 (was V8). Trigger: V8's
  `talking_head_with_backdrop` recipe is "avatar over
  cinematic backdrop", which structurally requires the
  `composite_video` primitive. The original sequence had
  V7 depending on a slice (V9) that was scheduled after
  it — a latent dependency the V5-promotion reorder
  exposed (V5 was already in the right place, V7's
  hidden need was the next thing to surface).
  Resolution: composite primitives land first so V8 is
  unblocked structurally. Polish primitives (captions /
  intro / outro / trim / reformat) shift to V9 — they
  remain independent of composite and could in principle
  parallelize with V8. V10-V15 unchanged. Same "land the
  dependency before the consumer" discipline as V1 →
  V3 (schema before primitive) and V2 → V3 (runtime
  before primitive).

- 2026-05-14 (SESSION 143, end of session) — V3-V13
  capability buildout shipped. Eleven slices in one
  session, each a per-commit feature drop on `main`:

    V3  (`54032c2`) — generate_avatar_speech + talking_head
    V4  (`1251def`) — generate_visual_clip + cinematic_visual
    V5  (`c2c4ba2`) — split_script + concat_clips + long_form_ad
    V6  (`7c968a5`) — Video backwards-compat shim
    V7  (`3af1c28`) — composite_video + mix_audio + 5 layout starters
    V8  (`545f991`) — talking_head_with_backdrop
    V9  (`ec130a9`) — captions + intro_outro + trim + reformat + 2 starters
    V10 (`f237ac7`) — design_voice + dub_audio + voice_design + multi_lang_dub
    V11 (`cfe9214`) — style_remix (Aleph, chunked path) + style_remix_pass
    V12 (`8b24465`) — transcribe (Whisper) + recut_teaser (first net-new
                       capability beyond hackathon)
    V13 (`43be57b`) — generate_image + storyboard_ad

  Plus the V9→V7 reorder commit (`7782c34`) between V6 and
  V7 to clear the latent composite_video dependency.

  Test count progression: 199 (V6 start) → 222 (V7) → 233
  (V8) → 257 (V9) → 276 (V10) → 293 (V11) → 318 (V12) →
  339 (V13). Media-engine routes: 113 → 122. 14 new
  `/internal/*` endpoints, 8 new step primitives, 12 new
  starter compositions.

  Three calibration moments worth carrying:

  - **The V9→V7 reorder pattern repeated.** First V0
    reorder was V5 from V7 (SESSION 142); this session's
    reorder was V9 to V7. Both surfaced the same way: a
    "next slice" turned out to have a latent dependency on
    something scheduled later. After two repetitions this
    is now the rule, not the exception: **when planning
    the next slice, check it against the dependency graph
    of every prior slice's data shape, not just the
    immediate predecessor.**
  - **"We already had this" is the operator's most
    valuable signal.** V10 (29-language dubbing), V11
    (Aleph style remix), V13 (storyboard) were all
    framed in the V0 doc as "ports" but the operator
    flagged each one with "I used this in production at
    the hackathon." The correct framing is restoration of
    shipped capability under a new architecture, not
    "first-time-shipping new features."
  - **storyboard_voiced deferred to V14+.** The V0 design
    listed it under V13; implementing it requires an
    `audio_extract` primitive (CLIP → AUDIO) that doesn't
    exist yet. Calling out the deferral in V13's commit
    so V14 picks it up.

  Doc discipline gap caught at end of session: V3-V13
  shipped 11 feature commits without paired context-kit
  refreshes. This change log entry + the SESSION 143
  handoff + the inventory regen close that gap.
  Going-forward discipline codified in CLAUDE.md:
  feature commits SHOULD include or be immediately
  followed by context-kit doc updates (slice table mark
  + change log entry); end-of-session handoff aggregates
  the per-slice updates.

- 2026-05-14 (SESSION 143, V14, `6f61e4b`) —
  `dialogue_scene` starter + `audio_extract` primitive
  shipped. First slice exercising the new doc-with-commit
  discipline — slice table mark + this change log entry +
  start-here update + CLAUDE.md Phase 4 refresh all rode
  in the same commit as the feature code.

  `audio_extract` primitive: CLIP → AUDIO via ffmpeg
  `-vn` through new `POST /internal/audio/extract/`
  endpoint. Supports mp3 / aac / wav. Unblocks the
  deferred `storyboard_voiced` recipe from V13 (the
  hackathon-shipped storyboard with avatar narration
  mixed under).

  `dialogue_scene` starter: ports the hackathon's
  `dialogue_service.py` multi-character skit pattern.
  Operator supplies an ordered list of
  `{"spokesperson": <Spokesperson>, "text": "..."}`
  turns; the starter creates N `generate_avatar_speech`
  steps (each overriding the avatar via the V3
  primitive's existing `spokesperson_avatar_id` params
  knob — no V3 changes needed) + 1 `concat_clips` step.
  Same pre-computation + degenerate-single-line pattern
  as V5's `long_form_ad`.

  Composition holds one `primary_spokesperson` FK
  (audit + permission owner); per-line spokespeople
  flow through step params for the actual avatar
  rendering. All per-line spokespeople validated
  workspace-scoped + avatar-bound at starter time.

  +19 tests (test_v14_dialogue.py). 358 backend tests
  total. Media-engine: 123 routes (+1 audio/extract).
  V15 (SPA recipe gallery) is the last V-arc slice.

- 2026-05-14 (SESSION 144, V15.0, `1781cb1`) — backend
  foundation for the SPA gallery. V15 split into 5 staged
  sub-slices (V15.0 backend, V15.1-V15.4 SPA family
  rollouts) at operator request so each slice can be
  tested + tweaked before the next.

  `apps/compositions/recipes.py` — single source of truth
  for the 17 starter compositions. Each entry carries
  `kind`, `display_name`, `family`, `description`, and a
  `fields` list (text / textarea / checkbox / select /
  number / spokesperson_picker / asset_picker /
  dialogue_lines). The SPA reads metadata via
  `GET /api/recipes/`. `resolve_kwargs` maps form params
  to starter kwargs, resolving spokesperson + asset ids
  to ORM rows scoped to the request workspace.
  `dialogue_scene` opts into a custom resolver because
  its `lines` field is dict-of-dicts; everything else
  uses the default resolver + per-recipe `param_map` for
  starter kwarg name differences.

  REST surface — three endpoints. `GET /api/recipes/` +
  `GET /api/recipes/<kind>/` are read-only metadata, no
  workspace scoping (gallery is global). `POST
  /api/compositions/` accepts `{kind, workspace, params}`,
  validates owner membership, resolves params, calls the
  recipe's starter, fires `execute_composition.delay()`.
  `GET /api/compositions/<id>/` + list view return
  workspace-scoped status/poll data with nested steps +
  final_asset.

  Workspace isolation is structural — Spokesperson /
  Asset lookups go through `Model.objects.get(pk=...,
  workspace=ws)`, so foreign ids raise `DoesNotExist`
  the view turns into 400. V1's cross-workspace signal
  is the second line of defense at save time.

  Family vocabulary for the gallery: talking_head,
  cinematic, layout, polish, voice, style, creative,
  dialogue. V15.1 will use these to group recipe cards.

  +24 tests (test_v15_api.py): registry shape
  invariants (every kind matches a starters function,
  every select has choices, every asset_picker has
  asset_type), happy paths for talking_head /
  reels_format / dialogue_scene (covers default + asset
  + custom resolver), failure paths for unknown kind /
  cross-workspace ids / non-member / non-owner /
  missing required field / unauthenticated. 382 backend
  tests total. Media-engine routes unchanged (V15 is
  shell-only).

- 2026-05-14 (SESSION 144, V15.1, `74a70d7`) — SPA
  gallery shell + three live recipes. Operator can now
  drive `talking_head`, `cinematic_visual`, and
  `talking_head_polished` end-to-end from the UI (no more
  Postman / curl). The other 14 recipes show as "coming
  soon" cards in the gallery and lead to a placeholder
  detail page (forms land V15.2-V15.4).

  New SPA routes (web/src/App.tsx):
    /recipes              — recipe gallery (all 17 cards)
    /recipes/:kind        — per-recipe form (3 live;
                            placeholder for the other 14)
    /compositions/:id     — status/poll page mirroring
                            the /videos/:id pattern (2s
                            refetch until terminal)

  Recipe gallery cards group by family
  (talking_head / cinematic / layout / polish / voice /
  style / creative / dialogue), each family heading +
  per-card sparkle/lock icons. Live cards open the form;
  locked cards show a "Coming soon" panel.

  Form rendering is metadata-driven — the per-recipe page
  reads `GET /api/recipes/<kind>/`, walks the fields list,
  and renders one of 7 input types
  (text/textarea/checkbox/select/number/spokesperson_picker;
  asset_picker + dialogue_lines remain placeholders for
  V15.2 / V15.4). Submit posts to
  `POST /api/compositions/`, then navigates to
  `/compositions/:id`.

  Dashboard "Make a video" CTA flipped from disabled to a
  link to `/recipes` (was "Coming in the next slice
  (S-12)" — that slice is V15.1).

  API client: web/src/lib/api/recipes.ts is the single
  module — recipe schema + composition schema + 4 hooks
  (useRecipes, useRecipe, useCreateComposition,
  useComposition with 2s polling until terminal status).

  No SPA tests in V15.1 — playwright e2e specs land at
  V15.4 after all 17 recipes have live forms. tsc + vite
  build green; 382 backend tests still pass.

- 2026-05-14 (SESSION 144, V15.2, `c9a5d8c`) —
  Layout + format family forms live. Seven more recipes
  flip from "coming soon" to fully driveable in the
  gallery: `pip_layout`, `backdrop_layout`,
  `cohost_layout`, `broll_splice`, `music_bed_pass`,
  `reels_format`, `talking_head_with_backdrop`.
  Ten of seventeen recipes (V15.1's three + V15.2's
  seven) now have live forms; six more land V15.3, the
  last (dialogue) V15.4.

  Backend addition: new `AssetViewSet` exposing
  `GET /api/assets/?workspace=<id>&asset_type=<type>`.
  Read-only, workspace-scoped via `IsWorkspaceMember`
  + queryset filter (same shape as
  `KnowledgeDocumentViewSet`). Output cap 200 newest;
  no pagination yet. Cross-workspace ids drop out of
  the queryset cleanly (no auth leak).

  SPA addition: `asset_picker` field renderer
  (web/src/routes/recipes/$kind.tsx) — one query per
  distinct `asset_type` declared by a recipe's fields,
  using a new `useAssets` hook in
  web/src/lib/api/recipes.ts. Empty-state panel when a
  workspace has zero assets of the needed type
  ("Run a producing recipe first…") + a single top-level
  hint above the form summarizing the same point so
  operators new to the gallery don't get stuck on a
  silent disabled dropdown.

  V0 contract holds — asset uploads are still out of
  scope (operators feed the layout recipes with assets
  produced by prior compositions). That is the
  intended v1 flow: render with talking_head /
  cinematic_visual first, then layer with the
  layout family.

  +5 backend tests (asset list filters by workspace +
  asset_type, cross-workspace exclusion, auth gate,
  end-to-end pip_layout create with two CLIP inputs).
  387 backend tests total. tsc + vite build green.

- 2026-05-14 (SESSION 144, V15.3, `8530a08`) — Voice
  / style / long-form / storyboard / recut family
  forms live. Six more recipes flip from "coming soon"
  to driveable: `voice_design`, `multi_lang_dub`,
  `style_remix_pass`, `long_form_ad`, `storyboard_ad`,
  `recut_teaser`. Sixteen of seventeen recipes have
  live forms after V15.3; `dialogue_scene` lands V15.4
  with the dialogue-lines field renderer.

  This slice is structurally trivial — one
  `LIVE_RECIPE_KINDS` addition in
  web/src/lib/api/recipes.ts. The form renderer
  (V15.1) + asset_picker (V15.2) + spokesperson_picker
  already cover every field type these six recipes
  need: text, textarea, checkbox, select, number,
  asset_picker, spokesperson_picker. Worth noticing —
  V15.2's investment in the metadata-driven form
  renderer paid off here.

  +4 backend regression tests for the six recipes'
  creation paths: voice_design minimal, storyboard_ad
  produces 7 steps, long_form_ad chunks a ~500-char
  script into N+1 steps, style_remix_pass takes a CLIP
  + preset. 391 backend tests total.

  Operator note on `multi_lang_dub`: it needs an AUDIO
  Asset as input, but V15.0-V15.3 produces no AUDIO
  assets in a fresh workspace (voice_design produces a
  VOICE asset, not AUDIO; audio_extract is a V14
  primitive but not exposed as a starter recipe). The
  asset_picker's empty-state hint covers this; the
  natural producer of AUDIO assets in v1 will be
  `storyboard_voiced` (V15.4) which uses audio_extract
  on a narration clip.

- 2026-05-14 (SESSION 144, V15.4, `68ab5d2`) — V-arc
  closure. Three pieces ship together:

  1. **`dialogue_scene` form live.** New
     `DialogueLinesEditor` component renders the
     dynamic line list — per-line spokesperson dropdown
     + text input + add/remove buttons. Lone "Need 2+
     spokespeople" empty state when the workspace has
     fewer than two cast members (dialogue scenes
     don't make sense with one). All 18 recipes are
     now driveable from the gallery.

  2. **`storyboard_voiced` bonus recipe shipped.**
     New 10-step starter — three image generations +
     three image-to-video clips + concat + avatar
     speech + audio_extract + mix_audio. The V13
     deferral finally lands; V14's audio_extract was
     the blocker. `mix_audio` is called with
     `music_gain_db=0` so the narration sits at full
     level (the music_bed default of -18 dB would
     bury it). The "wasted" talking-head render in
     step 7 is the cleanest way to use the
     spokesperson's bound voice + the existing
     avatar_speech primitive; the clip survives as a
     reusable Asset in the workspace.

  3. **Legacy single-form CTA retired.** The
     "Make a video" button on `/spokespeople/:id` now
     links to `/recipes` instead of
     `/spokespeople/:id/render`. The legacy
     `MakeVideoRoute` + `/api/videos/` route
     intentionally stay functional (V6 backwards-
     compat shim) — only the SPA CTA is rewired. The
     small UX regression (operator re-picks the
     spokesperson in the recipe form) is captured in
     the new project memory
     `project_workspace_fabric_merge.md` and will be
     resolved by the eventual workspace-fabric arc.

  E2e: replaced `make-video.spec.ts` (tested the
  retired flow) with new `recipes.spec.ts` covering
  dashboard CTA → gallery → 18 cards + form-opens
  smoke check. Backend tests: +2 (storyboard_voiced
  10-step plan + dialogue_scene registry happy path).
  393 backend tests total.

  Registry counts after V15.4:
    starters.py:    18 starter functions
    recipes.py:     18 RECIPES entries
    primitives:     13 (mock × 3 + real × 10; unchanged
                    since V14 — V15 added no new
                    primitives)
    media-engine:   123 routes (unchanged since V14)

### V-arc closure — what V0-V15 delivered

Sixteen sequential slices spanning SESSIONS 142-144.
Started from a hackathon backend with five `/internal/*`
verbs and one rigid talking-head endpoint; closed with
a metadata-driven SPA gallery, 18 starter compositions
backed by 13 step primitives, 14 sanctioned
`/internal/*` routes, and a runtime that walks
arbitrary linear step plans through partial-failure
resume.

Three load-bearing architectural shifts the V-arc
established as platform conventions:

* **Recipe = metadata, not code.** Every starter has a
  registry entry describing its form fields; the SPA
  renders forms from that metadata, not from
  hand-written per-recipe components. Adding a new
  recipe is a starter function + a registry entry —
  no SPA changes. V15.3 demonstrated this — six
  recipes flipped live with a one-line constant
  change.
* **Workspace isolation is structural, not procedural.**
  Asset / Spokesperson / Composition lookups go through
  `.objects.get(pk=..., workspace=ws)` so foreign ids
  raise `DoesNotExist` at the ORM layer. V1's cross-
  workspace signal is the second line of defense; the
  isolation test enforces the write surface.
* **Mock-mode propagates through composition.** V0
  rule 9 — mock_mode is a composition-level flag that
  every primitive honors at execute time. End-to-end
  test runs without provider credits; the operator
  toggle on every recipe form gives the same control
  in production.

The deferred legacy form retirement (full deletion of
`MakeVideoRoute` + the legacy single-form code path)
sits in the queue under the workspace-fabric arc, not
the V-arc. The V-arc closes here.
