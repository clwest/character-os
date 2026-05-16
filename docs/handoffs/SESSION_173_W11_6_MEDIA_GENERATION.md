---
title: "Session 173 — W11.6 media generation arc (W11.6.1-W11.6.4)"
date: 2026-05-16
status: complete
session: 173
previous_handoff: ./SESSION_171_DOGFOOD_W11_3_STABILITY_PROMPT_FIXES.md
---

# Session 173 — W11.6 media generation arc (W11.6.1-W11.6.4)

## TL;DR

Built and shipped four W11.6 implementation slices end-to-end:
the Asset model extension + media-engine endpoint (W11.6.1),
Django REST API (W11.6.2), SPA generation form (W11.6.3), and
SPA library + detail modal (W11.6.4). Closed with real-Stability
dogfood — 4 real images now live in `Admin's workspace`,
operator confirmed they render in the SPA library.

Pre-existing SESSION 172 work: W11.6.0 scope-lock
(`MEDIA_GENERATION_V1.md`) was the foundation.

**W11.6 arc state**: W11.6.0 ✓ → W11.6.1 ✓ → W11.6.2 ✓ →
W11.6.3 ✓ → W11.6.4 ✓. W11.6.5 (recipe inline image-picker)
already deferred to W11.7+ at scope-lock. **Arc complete.**

Tests: Django **727 → 752** (+25). Media-engine **111 → 133**
(+22). SPA vitest **53 → 82** (+29). Migrations 51 → 53.
Media-engine routes 130 → 132. Django URL patterns +5. New
SPA route + 5th nav item.

## What shipped — slice by slice

### W11.6.1 — Asset model extension + media-engine endpoint (commit `e7c565a`)

Wired Stability AI from a SESSION 171 in-tree port into an
addressable media-engine endpoint + extended the Asset model
so non-avatar images can persist per workspace.

* `media-engine/app/services/stability_portrait.py` —
  `VALID_PURPOSES` enum (avatar / scene / broll / product / ad)
  threaded through `build_stability_prompt` /
  `build_stability_negative_prompt` /
  `generate_stability_portrait`. Avatar purpose keeps the
  SESSION 171 template-driven prefix + tight-portrait framing
  (backwards-compat with the rebake call site). Non-avatar
  purposes get their own prefixes + framing + negatives + cache
  dir (`data/_internal/images_stability/`). Contract rule 5:
  no mascot-anatomy auto-inject outside the avatar surface.
* `media-engine/app/routers/internal.py` — new
  `POST /internal/image_stability/` (130 → 131 routes).
  Validates purpose / aspect_ratio (6 allowed) / model (6
  allowed). Mock-mode short-circuit honors the *injected*
  settings so dependency overrides work in tests even when
  the lru_cached `get_settings()` sees a populated
  `STABILITY_API_KEY`.
* `shell/apps/compositions/models.py` — Asset gains 7 optional
  image fields (purpose / model / style_preset / prompt /
  negative_prompt / aspect_ratio / spokesperson FK) +
  `(workspace, purpose)` index for the W11.6.4 library filter.
* Migration `0006_w11_6_1_asset_image_fields.py` — additive
  only; existing Asset rows stay valid.
* `media-engine/tests/test_stability_image.py` — 22 new tests
  covering prompt routing per purpose, negative prompt routing,
  style preset fallback, subject required, endpoint happy path
  for every purpose + 3 validation 400s + 1 pydantic 422 +
  backwards-compat for the SESSION 170 rebake call site via
  monkeypatch.

**Calibration moment**: lru_cached `get_settings()` inside
service code bypasses `app.dependency_overrides`. Fix is
`monkeypatch.setattr("module.path.get_settings", lambda: fake)`
OR pass settings down from the endpoint (the endpoint does
the latter; the unit test uses monkeypatch). Cost of finding
out: 6.5 Stability credits (~$0.0065) when the first test
run accidentally hit real Stability.

### W11.6.2 — Django REST API (commit `708ba1f`)

Resolves Q-img-A: co-located in `apps.compositions` rather
than splitting `apps.images`. Fewer moving parts; Asset
already lives there; extract later if the surface grows.

* `shell/character_os/clients/media_engine.py` —
  `StabilityImageResult` dataclass + `create_stability_image`
  wrapper (POST `/internal/image_stability/`) + `list_styles`
  wrapper (GET `/internal/styles/`). Standard
  MediaEngineClient pattern.
* `shell/apps/compositions/serializers.py` —
  `ImageAssetSerializer` surfaces all 7 W11.6.1 image fields
  alongside the shared Asset fields. Distinct from the
  compact `AssetSerializer` (composition responses use that)
  to keep SPA payload shapes clean.
* `shell/apps/compositions/views.py` — `ImageViewSet`
  (POST/GET list/retrieve/DELETE) + `StyleLibraryViewSet`
  (GET). Workspace isolation via `IsWorkspaceMember` +
  queryset filtering on `workspace__memberships__user`.
  Owner-only writes (mirrors composition + spokesperson
  patterns). `purpose=avatar` rejected with 400 in v1 per
  Contract rule 2 — avatar wizard owns that path; error
  message points to `scene` + creature-anatomy preset for
  Journey 5 ("iterate cheaply before baking"). Stability
  cost in credits → micros via the canonical 1 credit = 1000
  micros factor (Contract rule 7). Image bytes returned as a
  data URI from media-engine are stored directly in
  `Asset.file_path` (matches spokesperson portrait pattern;
  media-engine retains the sha-keyed disk cache).
* `shell/apps/compositions/urls.py` — registered `images` +
  `styles` routes on the existing DRF router.
* `media-engine/app/routers/internal.py` — added
  `GET /internal/styles/` (read-only proxy for the
  42-preset style library; Pydantic-typed response so the
  contract is explicit). 131 → 132 media-engine routes.
* `shell/apps/compositions/tests/test_isolation.py` —
  allowlisted the new test file with a code-review note.
  The write-guard caught my test file on first full-suite
  run — load-bearing safety mechanism.
* `shell/apps/compositions/tests/test_images_api.py` — 24
  new tests covering create per purpose, persistence shape,
  validation, workspace isolation, owner-only writes, list
  filters, retrieve, delete, styles proxy, upstream 502.

### W11.6.3 — SPA route + generation form (commit `ca6df3b`)

The `/images` route lands as a sibling of `/recipes` in the
workspace fabric nav. F0 contract rule 7 (nav stability)
satisfied via the W11.6 scope-lock per
`MEDIA_GENERATION_V1.md` §"Surface inventory" —
"sibling to /recipes in workspace fabric nav".

* `web/src/lib/api/images.ts` — Zod schemas + TanStack hooks
  for `/api/images/` + `/api/styles/`. Mirrors recipes.ts /
  videos.ts patterns. Constants table for the 6 Stability
  models with locked hint copy + credit costs (Contract
  rule 9), 6 aspect ratios with locked hint copy, 4
  non-avatar purposes. Avatar deliberately excluded per
  Contract rule 2 — avatar wizard owns that path.
  `useStyleLibrary` caches aggressively (1h staleTime,
  24h gcTime) since the library is a code-level constant on
  media-engine.
* `web/src/components/style-preset-picker.tsx` —
  Categorized tab gallery of the 42 presets. Each card
  surfaces display_name + description + mood; `best_for`
  industries land as hover-text (Contract rule 9). Selection
  state, Clear button, selection summary pill.
* `web/src/components/image-generation-form.tsx` —
  Purpose / Subject / Model / Aspect ratio / Style preset
  pickers. Defaults to scene + sd3-large + 16:9 per
  scope-lock. Advanced disclosure for the negative-prompt
  override (Q-img-E v1 resolution). Result lands inline;
  error banner on failure.
* `web/src/routes/images/index.tsx` — `/images` route with
  two tab sub-views (generate / library). On successful
  generation auto-switches to library so the fresh image
  lands in front of the operator.
* `web/src/App.tsx` — registered `/images` route under
  RequireAuth.
* `web/src/components/nav-rail.tsx` — 5th nav entry for
  Images. Docstring updated.
* Tests: `style-preset-picker.test.tsx` (8) +
  `image-generation-form.test.tsx` (9). 17 new vitests.

**Calibration moment**: Radix Tabs need real pointer events
to flip the active panel under jsdom — `fireEvent.click` on
the trigger doesn't always work. `userEvent.setup() + await
user.click()` is the right tool. Caught on the first
preset-onChange test for a preset in the inactive tab.

### W11.6.4 — SPA library view (commit `29a4824`)

**Scope-lock omission resolved**: scope-lock listed the 7
image Asset fields but missed `subject`. The Regenerate
CTA needs the original (pre-composition) subject — re-firing
with the composed prompt as the new subject would
double-apply the purpose framing ("A detailed scene
illustration of A detailed scene illustration of…"). Added
an 8th field. Migration 52 → 53.

* `shell/apps/compositions/models.py` — Asset.subject
  TextField, optional. Pre-W11.6.4 image rows leave it empty
  and the SPA disables Regenerate for them (tooltip points
  to Generate tab).
* Migration `0007_w11_6_4_asset_subject.py` — additive only.
* `shell/apps/compositions/views.py` — ImageViewSet.create
  persists subject onto the row.
* `shell/apps/compositions/serializers.py` — surface subject.
* `shell/apps/compositions/tests/test_images_api.py` — one
  new test (`test_create_image_persists_original_subject_for_regenerate`).
* `web/src/lib/api/images.ts` — schema gains subject with
  `.default("")` so older rows parse cleanly.
* `web/src/components/image-library-grid.tsx` — workspace
  image grid + filter bar (purpose / model / style_preset).
  Filter selections re-trigger `useImages` via queryKey
  change. Empty state is filter-aware. 200-newest cap hint
  surfaces when backend cap is hit; pagination defers to
  W11.7+.
* `web/src/components/image-detail-modal.tsx` — full image +
  composed prompt + metadata grid. Regenerate fires
  `useGenerateImage` with the asset's `subject` + same
  params + same negative override + same spokesperson FK.
  Delete requires a confirm tap then fires `useDeleteImage`.
  Esc / backdrop / X dismiss when no async op is in flight.
  Same minimal inline-modal pattern as
  `tool-approval-modal.tsx` (no Radix dependency).
* `web/src/routes/images/index.tsx` — wires grid + modal;
  parent owns `selectedAssetId`. `useImage` keeps the modal
  in sync with server-side state across regenerate. Removed
  the inline `LibraryPreview` from W11.6.3 (subsumed).
* Tests: `image-library-grid.test.tsx` (6) +
  `image-detail-modal.test.tsx` (6). 12 new vitests.

### Real-Stability dogfood (post-W11.6.4)

Operator confirmed the end-to-end pipeline against real
Stability + real Django + real React. ~12 Stability credits
spent total (~$0.012) across 4 images:

* **Probe** (`core` / 1:1 / photorealistic / scene) — direct
  `curl POST /internal/image_stability/` smoke. 3.4MB PNG
  returned in the data URI. Cost: 3 credits.
* **3 workspace images** in `Admin's workspace` (slug
  `admins-workspace`, owner `admin@mail.com`) via the full
  Django ImageViewSet code path:
  - scene 16:9 photorealistic — brewery owner at sunrise
  - product 1:1 minimalist — hand-blown glass coffee mug
  - broll 21:9 concept_art — rolling vineyard hills

All 8 image Asset fields populated correctly. Operator
confirmed they render in the SPA library tab. Composed
prompts have the purpose framing baked in
("A detailed scene illustration of…", "A high-quality product
image of…", "A supplementary establishing shot of…") —
distinct from the subject text, which proves the
W11.6.4 Regenerate flow won't double-apply framing.

## Calibration moments worth carrying

These belong in `TRUST_CALIBRATION.md` (appended this
session); listed here for handoff narrative.

1. **lru_cached `get_settings()` bypasses FastAPI
   `app.dependency_overrides`** — when service code calls
   `get_settings()` directly (not via `Depends`), tests that
   set `app.dependency_overrides[get_settings]` don't reach
   it. Solution: monkeypatch the module-level reference, OR
   pass settings down from the endpoint to the service.
   Cost of discovering this: 6.5 Stability credits when the
   first W11.6.1 test run accidentally hit real Stability.

2. **Radix Tabs + jsdom**: `fireEvent.click` on a TabsTrigger
   doesn't reliably flip the active panel. Use
   `userEvent.setup() + await user.click()`. Caught at the
   first style-preset-picker test for a preset in the
   inactive tab.

3. **Scope-lock prompt-vs-subject distinction**: the W11.6
   scope-lock listed 7 image Asset fields and described
   Regenerate as "re-fires with same params, new seed" — but
   didn't distinguish *what the operator types* (subject)
   from *what the LLM sees* (composed prompt with purpose
   framing baked in). The omission only became visible when
   implementing the modal; the W11.6.4 Asset.subject field is
   the resolution. Worth surfacing in future scope-lock
   reviews — wherever an LLM-bound surface has a composition
   step, distinguish operator input from model input.

4. **Backend write-guard is load-bearing**:
   `test_only_composition_module_writes_composition_tables`
   in `apps/compositions/tests/test_isolation.py` caught my
   W11.6.2 test file on first full-suite run. Adding a new
   test file that seeds Asset rows requires an explicit
   ALLOWED_FILES entry with a justification. The guard is the
   structural enforcement of the cross-workspace privacy
   contract — bypassing it via raw ORM creates would silently
   break invariants.

## Cast roster state

Unchanged from SESSION 171:

  - Riggs the Donkey (founder voice) — natural-looking bake
  - **Sasha the Raccoon** (sales) — voice `clara`,
    "nailed it" operator verdict
  - Donny the Sloth (user stories) — dental artifacts on
    `drew` voice, eligible for voice swap or rebake
  - Maya the Panda (educator) — untested in real-mode
  - **Marcus the Battle Unicorn** (AP history tutor) — voice
    `marcus`, Nerva–Antonine doc attached, 2 verified
    strict-mode renders shipped

New in workspace as of SESSION 173: 3 Stability images
(brewery, mug, vineyard) in the `Admin's workspace` image
library.

## Final state at session close

* **Phase 4 status**: All four arcs (K / V / F / R) plus
  W11.6 sub-arc all closed. K1-K9 + V0-V15 + F0-F10 + R0-R10
  + W11.6.0-W11.6.4 all shipped.
* **Operator-facing surfaces complete**: spokesperson
  wizard (W1-W11) + voice swap + rebake (W11.1-W11.2) +
  workspace image library (W11.6) all live.
* **Test totals**: Django **752** · Media-engine **133** ·
  SPA vitest **82**. Migrations 53. Media-engine routes 132.
* **Real-mode cost ledger this session**: ~12 Stability
  credits (~$0.012). Cheap calibration.
* **Stack-up**: media-engine + Django + SPA all running
  cleanly. Uvicorn auto-reload picked up all media-engine
  changes during the session.
* **Hygiene**: clean. No untracked secrets / media files.

## FIRST THING (SESSION 174): pick by mood

W11.6.5 (recipe inline image-picker) is the natural next
step but was deferred to W11.7+ at scope-lock, gated on
"image library has enough material to be useful for
recipes." The dogfood library has 3 images — probably not
enough yet. Realistic candidates:

1. **W11.6 polish**: real-Runway dogfood the full
   Generate → Library → Regenerate → Delete loop. Try a
   higher-tier model (sd3-large or ultra) for quality
   comparison vs the cheap `core` model used today.
   ~$0.005-0.01 per render.
2. **F8.1 — K10 seed corpus** — still blocked on operator
   markdown.
3. **K6.4 v3 — embedding-similarity fallback** — still holds
   for a real paraphrase miss.
4. **K7.x — YouTube ingest fix** — silent-failure mode noted
   in MEMORY.
5. **K6.3 — Brief length cap** — likely moot now, ~15 min
   cleanup.
6. **K7.1 — Cost telemetry surface in SPA**.
7. **W11.x — surface `voice_patch.status` in edit modal**
   (calibration carried from SESSION 171).
8. **More cast renders** against the new sd3-large /
   ultra models for variety + quality data points.

Operator preference: pick by mood at session start. Each
candidate is ~30 min to ~1 session in scope.

## Stack-up boilerplate

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000 — DO NOT pass --noreload

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**Smoke checks** (counts as of session close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 752 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 82 vitest tests
```

## Carry-forward calibration (assistant context)

* **`lru_cached get_settings()` requires monkeypatch in
  service-direct call sites.** When writing media-engine
  tests, prefer explicit settings parameter passing in new
  service code; existing direct-call patterns need
  monkeypatch on the module-level reference.
* **Radix UI primitives + jsdom need userEvent**, not
  `fireEvent.click` — pattern now established for the SPA
  test suite.
* **Scope-lock reviews should distinguish operator input
  from LLM input** for any composition-step surface. W11.6
  scope-lock missed the subject/prompt distinction; the
  Asset.subject field caught it after the fact.
* **Backend write-guards are load-bearing.** Adding a test
  file that creates Asset rows requires an ALLOWED_FILES
  entry. The guard fires on first full-suite run; budget
  for that catch.
* **Doc-with-commit discipline held this session**: each of
  the 4 feature commits updated its slice's row in
  `MEDIA_GENERATION_V1.md` inline. No catch-up pass needed.
* **Real-Stability cost calibration**: `core` model at
  3 credits ≈ $0.003 is cheap enough to dogfood freely.
  `sd3-large` at 6.5 credits ≈ $0.0065 is the recommended
  default for production-quality output. `ultra` at 8
  credits ≈ $0.008 is hero-image territory.
