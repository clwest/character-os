---
title: "Media Generation V1 — workspace-wide image surface (W11.6)"
status: scope-locked
locked: 2026-05-16 (SESSION 172)
companion_docs:
  - UI_REDESIGN_V2.md
  - WORKSPACE_FABRIC_V1.md
  - VIDEO_COMPOSITION_V1.md
  - CREATE_SPOKESPERSON_WIZARD.md
---

# Media Generation V1

> **Sub-arc of W11.** Where W11.1 + W11.2 closed the
> spokesperson-editing loop, W11.6 opens the *workspace-wide
> image generation* surface — every operator can produce
> b-roll, scene illustrations, product shots, ad imagery, and
> hero visuals without leaving character-os.
>
> Two providers, one operator-facing surface:
>
> * **Runway gen4_image** — the existing avatar-portrait path,
>   unchanged. Runway's avatar rig requires Runway-generated
>   portraits for clean lip-sync
>   (SESSION 171 calibration:
>   `feedback_runway_avatar_rig_needs_runway_portraits.md`).
> * **Stability AI (sd3-large / ultra / sdxl / core)** — the
>   new non-avatar image provider. Uses unused Stability credit
>   budget (10K+); 42 style presets ported from u-d-b's
>   `style_library.py` (SESSION 171). Works for any
>   image-generation use case where the output is NOT fed into
>   Runway's avatar pipeline.

---

## Purpose

SESSION 171 ported the Stability service + style library into
media-engine but the surfaces aren't reachable from the SPA or
the Django REST API. Operators can't generate images today
*except* through the spokesperson wizard's portrait step.

W11.6 fixes that. The operator-facing capabilities V1 unlocks:

* **B-roll generation for video composition** — operators
  generate supporting visuals (locations, props, abstract
  imagery) without leaving the platform. Recipes that consume
  imagery can browse-and-pick from the operator's library
  (W11.6.5, deferred).
* **Hero imagery for marketing surfaces** — landing page
  banners, blog headers, social-media-ready visuals (with
  ratio selection: 16:9 for landing, 1:1 for posts, 9:16 for
  Reels).
* **Product / ad imagery** — square product shots, lifestyle
  shots, ad creative.
* **Reference imagery for spokesperson design** — operators
  generate concept images BEFORE committing to a $5-10 Runway
  avatar bake. Stability iterates at ~6.5 credits in ~9
  seconds.
* **Style exploration** — 42 presets across 8 categories
  surface immediately. Operators pick a style; the system
  composes the prompt deterministically. No prompt-engineering
  knowledge required.

The product story is "character-os is the place you make
characters AND the visual world they live in." Avatars + voice
+ video + image generation, all under one workspace,
cost-tracked, library-stored.

---

## Contract rules (load-bearing)

These are the rules each W11.6.x slice must respect. Numbered
1-10 for cross-reference from slice docs.

### 1. Single image surface, purpose-routed.

One Django endpoint — ``POST /api/images/`` — accepts an
``purpose`` field. Backend routes to the appropriate provider:

* ``purpose="avatar"`` → Runway gen4_image (existing
  ``/internal/portrait/`` media-engine path)
* ``purpose="scene"`` → Stability
* ``purpose="broll"`` → Stability
* ``purpose="product"`` → Stability
* ``purpose="ad"`` → Stability (initial v1 set; expandable)

Operators don't pick providers — they pick *what the image is
for*. Provider routing is implementation detail. If we add
DALL-E or Replicate later, the purpose API doesn't change.

### 2. Avatar flow stays untouched.

The existing `/api/spokespeople/generate-portrait/` wizard
path is NOT migrated to `/api/images/`. The avatar wizard
keeps its dedicated path because it's tightly coupled to the
spokesperson creation flow (subject, template, voice setup).
W11.6 is for *new* image surfaces.

Future work (W11.7+) MAY migrate the avatar wizard path to
route through `/api/images/?purpose=avatar` if there's a
durable simplification gain. For v1 it doesn't.

### 3. Images persist as Asset rows.

Existing ``apps.compositions.models.Asset`` already has
``asset_type`` with ``clip`` as the v1 variant. W11.6 adds
``image`` as a new ``asset_type`` variant. No new model.

Asset row carries:

* ``asset_type="image"``
* ``file_path`` — local path or CDN URL (Stability returns
  bytes; we cache + persist)
* ``mime_type="image/png"`` (or jpeg/webp depending on
  Stability output_format)
* ``cost_micros`` — Stability credit cost converted to micros
  (rough: 1 Stability credit ≈ $0.001 → 1000 micros)
* ``workspace`` — required, workspace-scoped from F-arc
  contract rule 1
* New optional fields on Asset:
  * ``purpose`` — mirrors the request purpose enum
  * ``model`` — Stability model name (sd3-large / ultra /
    sdxl / core / etc.)
  * ``style_preset`` — selected preset name from
    ``style_library``
  * ``prompt`` — the composed prompt sent to Stability
  * ``negative_prompt`` — composed negative prompt
  * ``aspect_ratio`` — output ratio (1:1 / 16:9 / 9:16 / etc.)
  * ``spokesperson`` — optional FK; "this image was generated
    for spokesperson X's video" linkage

### 4. Style presets are first-class.

The 42-preset library (SESSION 171 port of
``style_library.py``) is the operator-visible surface for
*how the image should look*. Operators pick from the library;
the picker categorizes by 8 groups (photography / animation /
digital_art / traditional_art / artistic_movements / genre /
3d_rendering / cultural / special).

Each preset has:

* ``name`` — slug used in API
* ``display_name`` — human label in the picker
* ``description`` — short hover-text
* ``best_for`` — list of industries / use cases
* ``mood`` — emotional feel (one word)
* ``example_prompt_suffix`` — the prompt fragment appended to
  the operator's typed subject

### 5. Stability is the only non-avatar provider for v1.

DALL-E + Replicate from u-d-b's broader `image_generation.py`
are deferred. Reasons:

* Operator has 10K+ unused Stability credits — cost
  arbitrage is real.
* One provider keeps the v1 implementation tight.
* DALL-E / Replicate ports are mechanical when we want them.

`stability_portrait.py` extends to non-avatar use cases by
making the template prefix configurable. v1 supports the
existing 4 templates (mascot / founder / coach / local_guide)
PLUS the new W11.6 purposes (scene / broll / product / ad).

### 6. No prompt-assistant LLM routing in v1.

u-d-b's ``core/agents/image_agent.py`` (580 lines of
GPT-routed parameter selection — "you said 'product shot' so
let me pick model + style + size for you") is deferred. v1
operators pick model + style + aspect ratio directly via the
SPA picker. The orchestrator (``stability_portrait.py``)
composes the prompt deterministically from those inputs.

GPT-routed parameter selection becomes interesting when:

* SPA gets a "describe what you want" freeform input that
  parses to provider/model/style/ratio
* Recipes auto-pick image parameters based on the recipe
  context (e.g. "this is a product video, use 1:1 + product
  photography preset")

Both are W11.7+ work.

### 7. Cost telemetry per-image.

``Asset.cost_micros`` carries the Stability credit cost in
micros. Aggregate per-workspace spend is queryable via the
existing workspace overview surface (F3 dashboard).

Cost rates (per Stability model, in credits — micros conversion
treats 1 credit = $0.001 ≈ 1000 micros):

| Model | Credits | Micros |
|---|---|---|
| core | 3.0 | 3,000 |
| sdxl | 3.0 | 3,000 |
| sd3-medium | 3.5 | 3,500 |
| sd3-large-turbo | 4.0 | 4,000 |
| sd3-large | 6.5 | 6,500 |
| ultra | 8.0 | 8,000 |

(Conversion factor is approximate — actual Stability
dollar-per-credit varies by purchase tier. Telemetry uses
credits-as-micros as the load-bearing unit; dollar conversion
is a display-only multiplier.)

### 8. Tier limits deferred to W11.6.x.

Spokespersons (W-arc), videos (V-arc), and realtime sessions
(R-arc) all have per-tier caps in
``apps.billing.services``. W11.6 v1 deliberately does NOT add
an image cap. Rationale:

* No usage data yet — we don't know what reasonable per-tier
  caps look like.
* Stability credits are pre-purchased; running out is a hard
  ceiling that operators feel directly.
* Easier to add a cap once we have data than to walk one back.

W11.6.x will add per-tier image caps after 30+ days of usage
data lands.

### 9. Operator-facing explanations are first-class.

Every operator-facing choice — model, aspect ratio, style
preset, purpose — surfaces a short explanation in the SPA
picker (hover-text, inline description card, or both). Pattern
matches ``PORTRAIT_TEMPLATE_HINTS`` from the wizard's visual
template tiles.

Operators don't need to know that "ultra" is more expensive
than "core" — the UI tells them via the hint copy below.
Operators don't need to know what "concept_art" looks like —
the picker shows the preset's display name, description,
mood, and (ideally, in a future polish slice) a thumbnail.

**Model hint copy (locked)**:

* ``core`` — *"Fastest + cheapest (3 credits). Good for quick
  concepting and scratchpad iterations."*
* ``sdxl`` — *"Balanced speed and quality (~3 credits).
  General-purpose workhorse."*
* ``sd3-medium`` — *"Detailed mid-tier (3.5 credits). Good
  default for most production images."*
* ``sd3-large-turbo`` — *"SD3 quality at faster speeds (4
  credits). When you want SD3 detail but in a hurry."*
* ``sd3-large`` — *"Best SD3 quality (6.5 credits).
  Recommended default for final-use images."*
* ``ultra`` — *"Premium flagship (8 credits). Use for hero
  images and marketing-quality results."*

**Aspect ratio hint copy (locked)**:

* ``1:1`` — *"Square. Social posts, profile images, product
  shots."*
* ``16:9`` — *"Landscape widescreen. Video backdrops, banners,
  web headers."*
* ``9:16`` — *"Vertical / tall. Reels, TikTok, Stories,
  mobile-first content."*
* ``4:3`` — *"Traditional landscape. Slide decks, blog
  headers."*
* ``3:4`` — *"Portrait. Profile photos, character art."*
* ``21:9`` — *"Cinematic ultrawide. Dramatic scenes,
  panoramas."*

### 10. Style preset library is the picker contract.

The 42 ported presets in ``style_library.py`` are the
canonical picker contents. New presets are added by
appending to ``style_library.STYLE_LIBRARY[<category>]``;
the picker auto-discovers them via ``get_all_styles()`` and
``get_styles_by_category()``. No SPA code change required to
add a style.

Removed presets must keep their slug in the library as a
deprecated marker (or the Asset rows referencing them break);
hide them from the picker but preserve the lookup for
historical rows.

---

## Operator journeys

Five concrete journeys V1 supports. Numbered to cross-
reference from slice docs.

### Journey 1 — "I need a hero image for the landing page"

1. Operator opens `/images` in the SPA, clicks "New image."
2. Picker shows: model selector (defaults to ``sd3-large``),
   aspect ratio (defaults to ``16:9``), purpose selector
   (defaults to ``scene``), style preset gallery (categorized,
   defaults to no selection).
3. Operator picks ``ultra`` (premium quality) + ``16:9`` +
   ``scene`` purpose + ``cinematic`` style preset.
4. Operator types subject: "a small craft brewery owner
   tapping a fresh keg at sunrise"
5. Submits → blocks ~10s → image appears with full prompt
   shown + cost displayed (8 credits / $0.008 estimated).
6. Operator can "Save to library" (already done) or
   "Regenerate" (re-fires with same params, different seed)
   or "Adjust" (returns to the form with values pre-filled).

### Journey 2 — "I need b-roll for a video"

1. Operator is on a recipe page (e.g. ``cinematic_visual``)
   in the recipe gallery. The recipe takes an image input.
2. Recipe form has an "Image source" field with two options:
   "Generate new" (W11.6.5, deferred) or "Pick from library"
   (W11.6.4).
3. Operator picks "Pick from library" → modal opens with a
   filtered grid of workspace images (filter:
   ``purpose=broll``).
4. Operator selects an image → recipe pre-fills with the
   asset URL.
5. Submits recipe → composition runs.

### Journey 3 — "I want to build a library over time"

1. Operator opens `/images` in the SPA — sees a grid of all
   their workspace images, sorted by recency, filterable by
   purpose / model / style preset.
2. Each thumbnail shows: image, purpose tag, model tag, cost,
   created date.
3. Clicking a thumbnail opens detail view with: full prompt,
   negative prompt, model, style preset, aspect ratio, cost,
   "Regenerate" CTA (re-fires with same params, new seed).
4. Operator can delete an image; deletion clears the Asset
   row (workspace storage doesn't grow unbounded).

### Journey 4 — "I want product shots for my ad campaign"

1. Operator picks ``product`` purpose + ``1:1`` ratio +
   ``photography → photorealistic`` style preset + ``ultra``
   model.
2. Subject: "a single hand-blown glass coffee mug on a
   wooden table, soft morning light, minimal styling"
3. Generates → reviews → maybe re-generates with style preset
   ``photography → product_photography`` (if added later) for
   a different anchor.

### Journey 5 — "I want to design a spokesperson before
committing to a Runway bake"

1. Operator picks ``avatar`` purpose (routes to Runway) OR
   ``scene`` purpose with a creature-anatomy preset (routes
   to Stability) to iterate cheaply on concept.
2. Generates ~3-5 candidate images at ``core`` (cheap) model.
3. Picks the design they like.
4. Switches over to the spokesperson wizard, types a subject
   that captures the chosen design, fires the real avatar
   bake.

(Journey 5 doesn't require new W11.6 functionality beyond the
library — operator just uses the existing surface to iterate
visuals before committing.)

---

## Surface inventory — existing vs new

### Existing surfaces W11.6 leverages

| Surface | Where | What W11.6 uses |
|---|---|---|
| `Asset` model | `apps.compositions.models` | Adds ``image`` to ``asset_type`` enum; adds optional fields (purpose / model / style_preset / prompt / negative_prompt / aspect_ratio / spokesperson FK). |
| `media-engine` `httpx` client + `MediaEngineClient` Django wrapper | `media-engine/app/` + `shell/character_os/clients/` | Django side calls new media-engine endpoint via the existing client. |
| `stability_ai_service.py` + `stability_portrait.py` + `style_library.py` | `media-engine/app/services/` | Already in-tree (SESSION 171). W11.6.1 extends `stability_portrait.py` to support non-avatar purposes (drops the mascot-anatomy auto-inject for `scene`/`broll`/etc.; adjusts negative prompts; supports more aspect ratios). |
| Workspace overview (F3) | F-arc | Cost aggregation surface — image costs roll up alongside video / realtime costs. |

### New surfaces W11.6 introduces

| Surface | Slice | Shape |
|---|---|---|
| `POST /internal/image_stability/` | W11.6.1 | media-engine endpoint. Body: `(purpose, subject, model, style_preset, aspect_ratio, negative_prompt_override)`. Returns: `(image_data_uri, prompt, mime_type, cost_credits, model)`. |
| Migration adding ``image`` asset_type + image-specific fields | W11.6.1 | `apps/compositions/migrations/0XXX_asset_image_type.py`. |
| `POST /api/images/` | W11.6.2 | Django REST. Body: `(workspace, purpose, subject, model, style_preset, aspect_ratio, spokesperson?)`. Routes by purpose (`avatar` → Runway via existing portrait path; others → Stability via new internal endpoint). Persists Asset. Returns: serialized Asset. |
| `GET /api/images/` | W11.6.2 | List + filter by purpose / model / style_preset / spokesperson. Pagination. |
| `GET /api/images/<id>/` | W11.6.2 | Detail (same shape as create response). |
| `DELETE /api/images/<id>/` | W11.6.2 | Workspace-scoped delete. |
| `GET /api/styles/` | W11.6.2 | Style library snapshot — categories + 42 presets, used by SPA picker. |
| `/images` route | W11.6.3 + W11.6.4 | New SPA route as a sibling to `/recipes` in workspace fabric nav. Two sub-views: (a) generate (form + picker), (b) library (grid + filters). |
| Image generation form component | W11.6.3 | Model selector + aspect ratio selector + purpose selector + style preset gallery + subject textarea. All choices have hover-text per Contract rule 9. |
| Image library view | W11.6.4 | Grid of workspace images, filters, detail-view modal. |
| Recipe inline image-picker (deferred) | W11.6.5 → W11.7 | For recipes that consume image inputs (cinematic_visual etc.). |

---

## Slice breakdown

### W11.6.0 — Scope-lock doc (this slice)

* This document.
* No code changes.
* Closes when committed.

### W11.6.1 — Asset model extension + media-engine endpoint ✓ SHIPPED (SESSION 173)

**Files touched**:

* `shell/apps/compositions/models.py` — Asset already had
  `IMAGE` in `asset_type` choices (V2). W11.6.1 added the 7
  optional image fields (purpose / model / style_preset /
  prompt / negative_prompt / aspect_ratio / spokesperson FK)
  + a `(workspace, purpose)` index for the library view filter.
* `shell/apps/compositions/migrations/0006_w11_6_1_asset_image_fields.py` — NEW
  (additive only; nullable / blank-default fields keep
  existing Asset rows valid).
* `media-engine/app/services/stability_portrait.py` — added
  `VALID_PURPOSES` enum + `purpose` kwarg on
  `build_stability_prompt` / `build_stability_negative_prompt` /
  `generate_stability_portrait`. Avatar purpose keeps the
  SESSION 171 template-driven prefix + tight-portrait framing
  (backwards-compat); scene / broll / product / ad use
  purpose-specific prefix + framing with no mascot-anatomy
  auto-inject (Contract rule 5). Non-avatar cache lands under
  `data/_internal/images_stability/`.
* `media-engine/app/routers/internal.py` — NEW
  `POST /internal/image_stability/` endpoint. Body:
  `(purpose, subject, model, style_preset, aspect_ratio,
  negative_prompt_override, template?)`. Returns:
  `(image_data_uri, prompt, mime_type, cost_credits, model,
  purpose, style_preset, aspect_ratio, mock_mode)`. Endpoint
  honors the injected `settings.stability_mock` for the
  short-circuit so tests using `app.dependency_overrides` get
  the right branch even when the lru_cached `get_settings()`
  inside services would see a populated `STABILITY_API_KEY`.
  Validates `purpose ∈ VALID_PURPOSES`,
  `aspect_ratio ∈ _STABILITY_ASPECT_RATIOS` (6 ratios),
  `model ∈ _STABILITY_MODELS` (6 models).
* `media-engine/tests/test_stability_image.py` — NEW
  (22 tests covering prompt routing per purpose, negative
  prompt routing, style preset fallback, subject required,
  endpoint happy path for every non-avatar purpose +
  avatar-on-endpoint Journey 5, three 400 validation paths,
  one 422 pydantic path, backwards-compat for the
  SESSION 170 rebake call site via monkeypatch).

**Test totals after SESSION 173**: Media-engine **133**
(111 → 133, +22). Django **727** (unchanged — endpoint
+ model surface unit-tested at media-engine layer; Django
ViewSet ships W11.6.2). Media-engine route count **131**
(130 → 131; one new `/internal/image_stability/`).
Migration count: 51 → 52.

**Acceptance**: media-engine tests pass; Django migration
applies cleanly; new endpoint exercised end-to-end in mock
mode for all 5 purposes. Real-Stability dogfood deferred
to W11.6.2 (Django REST API) when the operator-facing
surface lands.

### W11.6.2 — Django REST API ✓ SHIPPED (SESSION 173)

**Implementation choice (Q-img-A resolved)**: co-located in
``apps.compositions`` rather than splitting out an
``apps.images`` package. Fewer moving parts; Asset already
lives in compositions; extract later if the surface grows.

**Files touched**:

* `shell/character_os/clients/media_engine.py` — added
  `StabilityImageResult` dataclass, `create_stability_image`
  wrapper (POST `/internal/image_stability/`), and
  `list_styles` wrapper (GET `/internal/styles/`).
* `shell/apps/compositions/serializers.py` — new
  `ImageAssetSerializer` surfaces the W11.6.1 image fields
  alongside the shared Asset fields. Distinct from the
  existing compact `AssetSerializer` (which composition
  responses use) to keep the SPA payload shapes clean.
* `shell/apps/compositions/views.py` — new `ImageViewSet`
  (POST `/api/images/` + GET list/retrieve + DELETE) and
  new `StyleLibraryViewSet` (GET `/api/styles/`). Workspace
  isolation enforced via `IsWorkspaceMember` permission +
  queryset filtering on `workspace__memberships__user`.
  Owner-only writes (mirrors composition + spokesperson
  patterns). `purpose=avatar` rejected with 400 in v1
  (Contract rule 2 — avatar wizard owns that surface). All
  4 non-avatar purposes route through the W11.6.1 media-engine
  endpoint. Stability cost in credits → micros via the
  1 credit = 1000 micros canonical factor (Contract rule 7).
  Image bytes returned as a data URI from media-engine are
  stored directly in `Asset.file_path` (matches spokesperson
  portrait pattern; media-engine retains the sha-keyed disk
  cache).
* `shell/apps/compositions/urls.py` — registered `images` +
  `styles` routes on the existing DRF router.
* `shell/apps/compositions/tests/test_isolation.py` —
  added the new test file to `ALLOWED_FILES` with a code-
  review note (tests need to seed Asset(IMAGE) rows directly
  for list/retrieve/delete coverage without firing per-row
  generation).
* `media-engine/app/routers/internal.py` — added
  `GET /internal/styles/` (read-only proxy for the
  42-preset style library; Pydantic-typed response so the
  contract is explicit). 131 → 132 media-engine routes.
* `shell/apps/compositions/tests/test_images_api.py` — NEW
  (24 tests):
  - happy path for each non-avatar purpose (scene/broll/
    product/ad) — Asset persistence + media-engine call
    shape;
  - optional spokesperson FK linkage;
  - negative_prompt_override persists;
  - 400 paths: avatar purpose rejected (with pointer to
    wizard), unknown purpose, invalid aspect_ratio,
    unsupported model, missing subject/workspace, cross-
    workspace spokesperson;
  - 403 paths: non-member, non-owner (editor role);
  - 401/403 path: unauthenticated;
  - 502 path: media-engine error → no Asset row created;
  - list filters (purpose / model / style_preset) +
    workspace isolation + clip exclusion;
  - retrieve cross-workspace 404; delete success then 404;
    delete non-owner 403;
  - styles endpoint: proxy through, auth required, 502 on
    upstream failure.

**Test totals after SESSION 173 (W11.6.2)**:
Media-engine **133** (unchanged — `/internal/styles/` is
exercised via Django mocks; a dedicated media-engine test
for the new endpoint is queued for W11.6.3 when the SPA
picker consumes it). Django **751** (727 → 751, +24).
Media-engine route count **132** (131 → 132). Django
URL count: +5 image / styles patterns.

**Acceptance**: Django test suite passes (751 tests).
`POST /api/images/`, `GET /api/images/`,
`GET /api/images/<id>/`, `DELETE /api/images/<id>/`, and
`GET /api/styles/` all registered + workspace-scoped. SPA
client wiring + real-Stability dogfood land in W11.6.3.

### W11.6.3 — SPA route + generation form ✓ SHIPPED (SESSION 173)

**Files touched**:

* `web/src/lib/api/images.ts` — NEW. Zod schemas + hooks
  (`useGenerateImage` / `useImages` / `useImage` /
  `useDeleteImage` / `useStyleLibrary`). Mirror constants:
  4 non-avatar purposes, 6 Stability models with locked
  hint copy + credit costs, 6 aspect ratios with locked
  hint copy. Avatar purpose deliberately excluded from the
  SPA enum per Contract rule 2.
* `web/src/components/style-preset-picker.tsx` — NEW.
  Categorized tab gallery of the 42 presets sourced from
  `useStyleLibrary`. Each preset card shows
  display_name + description + mood; `best_for` lands as
  hover-text (Contract rule 9). Selection control + Clear
  button + selection summary pill.
* `web/src/components/image-generation-form.tsx` — NEW.
  Purpose / Subject / Model / Aspect ratio / Style preset
  pickers with hover-text per Contract rule 9. Defaults to
  scene + sd3-large + 16:9 per scope-lock §"Operator
  journeys". Advanced disclosure for the negative-prompt
  override (Q-img-E). Mutation surfaces result inline +
  error banner on failure.
* `web/src/routes/images/index.tsx` — NEW. `/images` route
  with two tab sub-views (generate / library). Library
  preview shows recent workspace images via `useImages`;
  full filters + regenerate + delete land in W11.6.4. On
  successful generation, auto-switches to library so the
  fresh image lands in front of the operator.
* `web/src/App.tsx` — registered `/images` route under
  RequireAuth.
* `web/src/components/nav-rail.tsx` — added Images entry
  (5th nav item; F0 contract rule 7 satisfied via this
  scope-lock per §"Surface inventory" — "sibling to /recipes
  in workspace fabric nav"). Docstring updated.
* `web/src/components/style-preset-picker.test.tsx` — NEW
  (8 tests: categories render, presets render with
  description + mood, hover-text presence, onChange callback
  with userEvent for Radix tabs, controlled value
  selection state, Clear button fires undefined, selection
  summary, error banner on library load failure).
* `web/src/components/image-generation-form.test.tsx` — NEW
  (9 tests: defaults match scope-lock, model + ratio hover
  copy, avatar purpose absent from SPA picker, Submit
  gating by subject, POST shape, result card render,
  error banner, negative_prompt_override threading).

**Test totals after SESSION 173 (W11.6.3)**: SPA vitest
**70** (53 → 70, +17). Django **751** (unchanged). Media-
engine **133** (unchanged). SPA build clean (bundle size
warning pre-existing).

**Calibration moment carried into next session**: Radix
Tabs need real pointer events to flip the active panel
under jsdom — `fireEvent.click` doesn't always work.
`userEvent.setup()` + `await user.click()` is the right
tool. Caught on the first preset-onChange test for a
preset in the inactive tab.

**Acceptance**: SPA build green; vitest green. Real-
Stability dogfood (operator clicks Generate, real image
arrives, lands in library) deferred to W11.6.4 — that
slice expands the library with filters / delete /
regenerate, which is what the dogfood loop exercises.

### W11.6.4 — SPA library view

**Files touched**:

* `web/src/components/image-library-grid.tsx` — NEW. Grid +
  filters + pagination.
* `web/src/components/image-detail-modal.tsx` — NEW. Full
  prompt + metadata + regenerate / delete CTAs.
* `web/src/routes/images/index.tsx` — wire library sub-view.
* Tests (vitest) — 4-6 unit tests.

**Acceptance**: operator can browse workspace's generated
images + filter + regenerate + delete.

### W11.6.5 — Recipe integration (deferred to W11.7)

Recipes that consume an image input (e.g. `cinematic_visual`
takes an optional `backdrop_image_url`) get an inline
"Pick from library" modal. Out of scope for v1 to keep
W11.6 contained.

Marked as `W11.7+ candidate` — promote when image library
has enough material to be useful for recipes.

---

## Out of scope (explicitly)

These belong to future work, NOT to W11.6 v1:

* **DALL-E / Replicate providers.** Stability only for v1.
* **GPT-routed prompt assistant** (`image_agent.py` from
  u-d-b — 580 lines). v1 operators pick parameters directly.
* **Image editing operations** (u-d-b's upscale / remove
  background / search-and-replace / creative_upscale).
  Generation-only for v1.
* **Per-tier image caps.** Contract rule 8.
* **Recipe integration** (W11.6.5 → W11.7).
* **Animation of generated images** (image-to-video, image-
  to-avatar workflows). Stability images bake into Runway
  avatars cleanly but rig poorly — see SESSION 171 memory.
* **FLUX + LoRA trained character styles** (u-d-b's
  `character_model_name` plumbing). Deferred.
* **Multi-image generation per request.** Stability supports
  `num_images > 1`; v1 fires one image per request to keep
  cost-per-call predictable.
* **Public sharing surfaces.** Images are workspace-private.
* **AI-assisted prompt refinement.** "Try this instead"
  suggestions — deferred to W11.7+.

---

## Open questions (defer to implementation slices)

### Q-img-A — `apps/images/` or extend `apps/compositions/`?

Asset already lives in `apps.compositions`. Two options:

* **Co-locate**: extend `apps.compositions` with image views
  + serializers. Smaller change; Asset already lives there.
* **New app**: `apps.images` with its own URLs, views,
  serializers. Cleaner separation but adds boilerplate.

**Resolution timing**: W11.6.2 implementation. Lean: co-locate
in `apps.compositions` (fewer moving parts; we can extract
later if the surface grows).

### Q-img-B — Image storage path on disk

Stability returns image bytes. We cache them under
`media-engine/data/_internal/images/<sha>.png` (mirrors the
existing portrait cache pattern) and serve them via the
existing `file_path` field on Asset (which can be a local
path OR a CDN URL).

For production deployment, images may need S3-style
persistence. Out of scope for v1 (local-only).

### Q-img-C — Aspect ratio enforcement

Stability's v2beta API supports a fixed set of aspect ratios
(at minimum: 1:1, 16:9, 4:3, 9:16, 3:4). Some models support
more (21:9, 5:4, 2:3, etc.). v1 advertises 6 aspect ratios in
the SPA picker:

| Ratio | Pixel proxy | Common use |
|---|---|---|
| 1:1 | 1024×1024 | Social, products |
| 16:9 | 1280×720 | Web, video |
| 9:16 | 720×1280 | Mobile, Reels |
| 4:3 | 1024×768 | Slides, blog |
| 3:4 | 768×1024 | Portrait |
| 21:9 | 1536×640 | Cinematic |

If a chosen model rejects a chosen ratio, surface the error
clearly + suggest the closest supported ratio. (v1: trust
Stability's `aspect_ratio` parameter to do the right thing
per model; no client-side validation.)

### Q-img-D — Streaming generation vs. blocking

Generation takes 3-10s depending on model. v1 blocks the
SPA submit button until the image arrives (matches the
existing portrait flow). Streaming would be nicer UX but
adds WebSocket plumbing; defer.

### Q-img-E — Negative prompt UI

`stability_portrait.py` has purpose-specific default negative
prompts. v1 hides them entirely (operator just picks subject
+ purpose + style + model + ratio). The system uses the
default negative prompt for the selected purpose.

W11.7+ could add "Advanced" disclosure showing the negative
prompt + allowing edits. Not v1.

### Q-img-F — Spokesperson FK semantics

Optional `spokesperson` FK on Asset for "this image was
generated for spokesperson X's video." Means:

* When set: image appears in spokesperson detail page's
  related media (future work).
* When unset: image is workspace-general.

v1 always sets to NULL by default. Recipe-integration work
(W11.6.5+) can wire the FK when a recipe is fired for a
specific spokesperson.

### Q-img-G — Cost telemetry display

Image cost in micros → display as Stability credits in the
SPA (`6.5 credits` for sd3-large). Dollar conversion is
operator-confusing without a clear rate; show credits-only
in v1.

W11.7+ could add a workspace settings panel for the credit
↔ dollar conversion rate (operator-set, since real rate
depends on Stability purchase tier).

---

## How to verify the surface

### Slice-level acceptance

* **W11.6.1**: media-engine tests green; new endpoint
  generates real Stability image via curl probe.
* **W11.6.2**: Django tests green; `POST /api/images/`
  end-to-end with curl (auth + workspace scope).
* **W11.6.3**: SPA build green; vitest green; operator
  generates an image via SPA.
* **W11.6.4**: operator can list / filter / regenerate /
  delete workspace images via SPA.

### Arc-level acceptance (W11.6 closes)

* All 5 operator journeys (1-4 above; journey 5 doesn't
  require new features) demonstrable end-to-end against
  real Stability + real Runway.
* No tier-limit logic for images (deferred).
* All Contract rules 1-10 hold.
* Asset rows survive a full migration / fresh-clone cycle
  (no orphaned references; deleted styles still resolvable).

---

## Companion docs and where they intersect

* **`UI_REDESIGN_V2.md`** (design lock) — fabric nav model;
  workspace as the container.
* **`WORKSPACE_FABRIC_V1.md`** (F-arc) — sets the workspace-
  scoped storage pattern + cross-cut dashboard that W11.6
  rolls cost telemetry into.
* **`VIDEO_COMPOSITION_V1.md`** (V-arc) — image-consuming
  recipes (cinematic_visual etc.) become the W11.6.5
  integration targets.
* **`CREATE_SPOKESPERSON_WIZARD.md`** (W-arc) — avatar
  portrait flow stays untouched per Contract rule 2.
* SESSION 171 memory entries:
  * `feedback_runway_avatar_rig_needs_runway_portraits.md`
  * `feedback_openai_gpt5_responses_api.md` (gpt-5 split for
    K6/K9/R6; W11.6 doesn't add new LLM call sites yet)

---

## Naming

* **Arc name in handoffs**: W11.6 (sub-arc of W11).
* **Slice names**: W11.6.0 … W11.6.5.
* **Doc file**: `docs/design/MEDIA_GENERATION_V1.md`.
* **Django app** (if extracted): `apps.images` —
  defer decision per Q-img-A.
* **Model**: existing `Asset` extended (no new model
  per Contract rule 3).
* **Endpoint paths**:
  * Django: `/api/images/` + `/api/styles/`
  * media-engine: `/internal/image_stability/`
* **SPA route**: `/images`

---

## Sign-off

* **Scope locked**: 2026-05-16 (SESSION 172).
* **Locked by**: operator + Claude (this session).
* **Resolved at lock-time**:
  * Q-img-1 (SPA surface): dedicated `/images` route,
    workspace-fabric nav sibling.
  * Q-img-2 (default model): all selectable, hint-copy
    locked, no enforced default (operator chooses).
  * Q-img-3 (scope): workspace-bound + optional
    spokesperson FK.
  * Q-img-4 (aspect ratios): 6 ratios advertised, hint-copy
    locked.
* **Resolved during implementation**: Q-img-A through
  Q-img-G (above).

---

*Scope-locked SESSION 172 (W11.6.0). Implementation slices
W11.6.1-W11.6.4 to follow; W11.6.5 deferred to W11.7+.*
