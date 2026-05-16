---
title: "Session 174 — operator-facing polish (voice telemetry, cost surface, K6.4 v2.1, K7.x, W11.6.5)"
date: 2026-05-16
status: complete
session: 174
previous_handoff: ./SESSION_173_W11_6_MEDIA_GENERATION.md
---

# Session 174 — operator-facing polish

## TL;DR

Ten commits across one long session driven by the SESSION 173
mid-session inventory ("what can the platform actually do?").
Three concrete operator-facing gaps the inventory flagged got
fixed end-to-end, plus a real-mode embedding dogfood that
corrected the inventory itself + uncovered two real bugs no
unit test would have caught.

* **W11.x — voice telemetry surface** (`3ecb6fe`). SESSION 171
  calibration closed. Edit modal now shows green `ok` / muted
  `skipped` / destructive `failed` banner after a voice swap
  + holds open on failure so operators see the Runway error.
* **K7.1 — workspace cost telemetry** (`5f52bb7`). New dashboard
  panel with per-surface MTD + all-time spend (compositions /
  images / realtime). Three-band dollar formatter so $0.0065
  reads accurately while $42.50 doesn't sprawl.
* **K6.4 v2.1 — verifier sentence-opener fixes** (`e9256e5`).
  Closes the SESSION 174 real-mode K6 dogfood findings —
  "Today" + "Think Antoninus" no longer false-positive flagged.
  Stoplist additions + multi-word demotion when leader is
  sentence-initial + stoplisted. Re-dogfood: zero warnings.
* **K7.x — YouTube + boilerplate URL rejection** (`e4d5761`).
  Closes the silent-failure mode. Trafilatura on YouTube
  returns nav-bar boilerplate ("About Press Copyright…")
  which polluted retrieval at distance ~0.85 across the
  workspace. Now rejected up-front with operator-actionable
  message.
* **W11.6.5 — recipe inline image-picker** (`8e0185b`).
  cinematic_visual recipe gains optional reference image
  field. Resolver extracts data URI for IMAGE-type assets;
  clips + audio continue to flow as Asset rows.
* **W11.6.5.1 — Asset.title for picker labels** (`cf8bb69`).
  Adds operator-facing label cascade so dropdowns aren't
  showing raw data URIs / file_path tails.
* **W11.6.5.2 — lift prompt_image max_length** (`40efbcf`).
  Real-mode cinematic_visual dogfood found two bugs at once:
  the prompt_image field had max_length=2048 (URL-shape), too
  tight for 4-6 MB data URIs. Lifted to 10 MB.
* **W11.6.5.3 — runtime auto-titles output assets** (`a233d10`).
  Operator opened backdrop_composite right after W11.6.5.1
  shipped, clip pickers still showed CDN URL tails. The
  W11.6.5.1 fix only covered images; this commit extends to
  every Asset persisted by the composition runtime. Backfilled
  26 existing clip rows.

Plus two docs commits:
* SESSION 174 mid-session — real-mode embedding dogfood +
  3 TRUST_CALIBRATION entries (`62353ce`).
* SESSION 173 close + 3 TRUST_CALIBRATION entries (`1271c77`)
  (carried over from yesterday).

**Tests**: Django **727 → 782** (+55). Media-engine **133**
unchanged. SPA vitest **53 → 91** (+38). Migrations **53 →
54**.

**Real-mode spend this session**: ~$0.55 total (~$0.30
OpenAI for K6 brief synthesis dogfoods + K6.4 re-dogfood;
$0.25 Runway for one successful cinematic_visual
image-to-video render).

## What shipped — commit by commit

### `1271c77` — SESSION 173 close (carried)

Anchor restamps + 3 TRUST_CALIBRATION entries + handoff.
Doctor green. Already documented in SESSION_173_*.md.

### `3ecb6fe` — W11.x voice telemetry

Closes the SESSION 171 calibration ("SPA discards
`voice_patch: {status, error}` from change-voice action;
modal closes silently regardless of Runway outcome").

* `web/src/components/spokesperson-edit-modal.tsx` — captures
  `useChangeVoice` result into local state. New
  `VoicePatchBanner` component below the form. Three states:
  - `ok` (emerald): "Voice updated on the live avatar. The
    new preset takes effect on the next render."
  - `skipped` (muted): "Voice saved to the row. No live
    avatar exists yet — the next bake will use the new
    preset."
  - `failed` (destructive): "Runway rejected the voice
    change. The new preset is saved on the row (the next
    avatar bake will pick it up) but the live avatar still
    has the previous voice. Details: <error>." Modal
    **stays open** on failed; Cancel button relabels to
    "Close".
* `web/src/components/spokesperson-edit-modal.test.tsx` —
  4 new tests cover all three states + persona-only-edits
  fire no voice swap.

**Calibration moment caught + carried**: my W11.6.4 test
helpers had latent TS errors that `pnpm test` (esbuild) silently
passed but `pnpm build` (tsc) caught. The
`props.X ?? vi.fn()` pattern creates a union type that loses
the `.mock` property. Fix is `vi.fn(props.X)` which always
returns a Mock. SPA gates must include `pnpm build`, not just
`pnpm test`.

### `5f52bb7` — K7.1 workspace cost telemetry

Server-side cost data exists per-Asset, per-Composition, per-
RealtimeSession. Operators had no aggregate view. This adds it.

* `shell/apps/accounts/views.py` — `workspace_overview` extends
  the response with `cost_breakdown`:
  - per-surface dollar rollup (compositions / images /
    realtime sessions)
  - all-time `total_micros`
  - MTD rollup with calendar-month start (UTC; workspace tz
    deferred to W12)
  Zero new persistence — every field is a `Sum()` aggregate
  over existing models.
* `web/src/components/cost-panel.tsx` — new dashboard panel.
  Three-band dollar formatter:
  - sub-cent: 4 decimals (`$0.0065` for a single Stability
    image)
  - sub-dollar: 3 decimals (`$0.067` for typical MTD)
  - ≥$1: 2 decimals (`$2.50` for monthly figures)
  MTD + all-time pivot cards; per-surface breakdown rows
  with Film / Image / MessageCircle icons.
* `web/src/lib/api/overview.ts` — `overviewCostBreakdownSchema`
  added as optional (pre-K7.1 backends omit the field; SPA
  renders an "unavailable" note instead of failing schema
  parse).
* 5 new Django tests covering empty workspace zero-shape,
  per-surface aggregation, MTD-excludes-prior-month,
  workspace isolation, back-compat with existing
  `compositions.total_cost_micros` field.
* 5 new SPA vitests covering skeleton / unavailable / error /
  full data render / formatDollars precision bands.

### `62353ce` — Real-mode embedding dogfood + 3 TRUST_CALIBRATION

No code changes — pure documentation + dogfood correction.

The SESSION 173 mid-session inventory I wrote claimed
"mock-only embeddings — EMBEDDING_FORCE_MOCK is on by
default; real embeddings haven't been dogfood-validated at
scale." Wrong. Direct shell probe of `KnowledgeChunk.embedding_vector`
magnitude + `cost_micros` showed all 32 chunks in
`Admin's workspace` already had real OpenAI vectors
(unit-normalized magnitude ≈ 1.0, dense, cost_micros > 0,
model = `text-embedding-3-small` without "(mock)" suffix).

Three calibration entries appended:
1. **AI confidently wrong** — the embedding inventory claim.
   Lesson: read runtime FIRST when answering "what can we
   do today?", docs + code SECOND.
2. **Near-miss** — K6.4 verifier sentence-opener false-
   positives ("Today", "Think Antoninus"). Brief was clean
   and grounded; verifier flagged 2 non-claims due to
   sentence-position blindness.
3. **Near-miss** — YouTube ingest pollution. Off-topic
   "sourdough" query returned the YouTube doc's extracted
   nav-bar boilerplate at distance ~0.85, polluting retrieval
   across the workspace. The K7.x backlog item was higher-
   impact than "queued" framing suggested.

Dogfood confirmed at scale:
* Real-mode semantic retrieval: distance gradient cleanly
  separates literal/semantic/paraphrase (~0.22-0.41) from
  off-topic (~0.85+).
* Redis embedding cache hot: first embed 650ms+1μ, second
  embed 1ms+0μ.
* Full K6 pipeline (real embed → real pgvector → real
  gpt-5 → Warn verifier → ScriptResult) lands in ~10s
  at 1593 input + 759 output tokens, brief grounded, all
  named entities traceable.

### `e9256e5` — K6.4 v2.1 sentence-opener fixes

Closes the two false-positive classes the dogfood surfaced.

* `shell/character_os/claim_verifier.py` — stoplist additions:
  - Time adverbs: today, tomorrow, yesterday, tonight,
    lately, recently.
  - The `think` family (slipped through v2's CTA-verb sweep
    in SESSION 166).
  - Sentence-opener prepositions: from, with, without,
    through, throughout, between, among, across, around,
    within, beyond.
* `shell/character_os/claim_verifier.py` — multi-word
  demotion. When a `_MULTIWORD_CAPS_RE` match starts at
  sentence-initial AND its leading capitalized word is in
  the stoplist, drop the leader and re-extract the remainder.
  Preserves both shapes:
  - "Think Antoninus" → demote "Think", remainder
    "Antoninus" falls through to single-cap → corpus check
  - "The Federal Bureau of Investigation" → demote "The",
    remainder "Federal Bureau of Investigation" re-emits as
    multi_word at the new offset (preserves the existing
    FBI regression test)
* 4 new tests covering: time-adverb stoplist, the canonical
  "Think Antoninus" case, the mid-sentence invariant guard
  (demotion fires ONLY at sentence-initial), full SESSION 174
  brief regression.

**Calibration moment caught + carried**: my first demotion
attempt broke the existing FBI test. The fix needed to
re-extract the remainder as multi_word (when applicable),
not just block the leader span and let single-cap shred the
rest. Existing regression tests are load-bearing safety
mechanisms — they catch the failure mode where you fix one
false-positive class by silently breaking a different
correctness invariant.

Live K6 re-dogfood after fix: zero verification_warnings.
Brief starts "Today: Rome's 'Five Good Emperors.' From 96
to 180 AD, Nerva, Trajan, Hadrian, Antoninus Pius, and
Marcus Aurelius ruled... Want more? Tell me which emperor
to zoom in on next." — three formerly-problematic words
("Today", "From", "Tell"), one perfectly extracted real
proper noun ("Antoninus"), zero warnings.

### `e4d5761` — K7.x YouTube + boilerplate rejection

Two-layer defense against trafilatura's silent-failure mode.

* `shell/apps/embeddings/url_fetch.py` — host-based rejection.
  Any `youtube.com` / `m.youtube.com` / `music.youtube.com` /
  `youtu.be` / `youtube-nocookie.com` URL rejected up-front
  via `_is_youtube_url()` BEFORE the HTTP request fires.
  Error message: *"YouTube URLs can't be ingested via the
  generic trafilatura extractor — the page chrome is what
  gets returned, not the video. Paste the transcript or
  video description directly as text. (A proper YouTube
  transcript extractor is queued for a future slice.)"*
* `shell/apps/embeddings/url_fetch.py` — boilerplate signature
  detection. Post-extraction substring match on the verbatim
  `"about press copyright contact us creators"` sequence
  (case-insensitive). Catches non-YouTube sites that fool
  trafilatura the same way. Specific enough that legitimate
  articles mentioning "About" or "Press" individually still
  pass.
* 10 new tests (11 → 21) covering 6 parametrized YouTube URL
  variants (assertion: httpx.Client never instantiated),
  error-message actionability, boilerplate signature on
  non-YouTube host, case-insensitive matching, invariant
  guard for innocent substring use.

Workspace cleanup performed alongside (data only): deleted
the polluted "Create Your Own Character in 5 Minutes |
Runway" doc + its 1 chunk from `Admin's workspace`. Re-running
the SESSION 174 off-topic "sourdough" probe now returns
Nerva-Antonine chunks at distance 0.99-1.05 (correctly weak
match) instead of the misleading 0.85 the polluted doc was
scoring.

### `8e0185b` — W11.6.5 recipe inline image-picker

Closes the W11.6 arc's deferred final slice.

* `shell/apps/compositions/recipes.py` — cinematic_visual
  gains an optional `prompt_image_asset_id` field with
  `asset_type=IMAGE`. `param_map` remaps to the starter's
  existing `prompt_image` kwarg.
* `shell/apps/compositions/recipes.py` (`resolve_kwargs`) —
  when an asset_picker resolves an Asset with
  `asset_type=IMAGE`, pass its `.file_path` (data URI for
  W11.6.1 image rows) as the kwarg value instead of the
  Asset row. Clips + audio continue to flow as Asset rows
  because their consuming starters operate on metadata, not
  URL strings.
* `web/src/routes/recipes/$kind.tsx` — AssetPicker's empty
  state previously hardcoded clip/audio hints. Added an
  image case pointing operators to the `/images` tab.
* 5 new tests covering: recipe metadata exposes the field,
  end-to-end image data URI lands in step params,
  optional-field invariant (omitting it leaves prompt_image
  absent so the starter routes through gen4.5 text-to-video),
  cross-workspace image rejection (400), clip-picker
  invariant (still passes Asset rows).

### `cf8bb69` — W11.6.5.1 Asset.title for picker labels

Operator pointed out immediately after W11.6.5 shipped: the
new image picker dropdown showed each option as
"data:image/png;base64,iVBORw0KGgo…" — totally
indistinguishable.

* `shell/apps/compositions/models.py` — Asset gains optional
  `title` CharField (max 120, blank default). Migration 0008.
* `shell/apps/compositions/views.py` — `_derive_title_from_subject`
  helper does word-boundary truncation to 60 chars with
  sentence-aware sub-truncation. ImageViewSet.create accepts
  optional `title` body field; defaults to the helper's
  output when omitted so every new image gets a usable label
  for free. AssetViewSet inline list (recipe asset_picker
  data source) now returns `title` + `subject`.
* `shell/apps/compositions/serializers.py` —
  `ImageAssetSerializer` surfaces `title`.
* `web/src/components/image-generation-form.tsx` — new Title
  input field. Auto-fills from subject as the operator types
  with smart word-boundary truncation; freezes once the
  operator edits the title field themselves so re-editing
  subject doesn't clobber operator intent.
* `web/src/routes/recipes/$kind.tsx` — `assetLabel` cascade
  rewritten:
  1. `title` (W11.6.5.1+ images, operator-editable later)
  2. `subject` (W11.6.4+ image rows without title)
  3. `file_path` filename + duration (legacy fallback)
* 4 new Django tests covering: auto-derive from subject,
  long-subject truncation with ellipsis, explicit override
  wins, AssetViewSet returns title + subject.

Backfill: 3 existing dogfood image titles auto-derived from
their subjects.

### `40efbcf` — W11.6.5.2 lift prompt_image max_length

Real-mode cinematic_visual dogfood found this immediately.
`/internal/clips/visual/` + `/internal/videos/` both set
`prompt_image: Optional[str] = Field(default=None,
max_length=2048)`. Sized for URLs; the W11.6.5 resolver
passes ~4-6 MB data URIs. Pydantic rejected with 422.

Lifted both to `max_length=10_000_000` (~10 MB string ≈
7.5 MB raw bytes). Mirrors the existing portrait endpoint's
5 MB decoded cap.

**Operational bug surfaced + fixed alongside (no code change)**:
the Celery worker (pid 62107, started 2026-05-15 23:52)
predated all W11.6 migrations. Its in-process Asset model
class didn't know about the 8 new image fields. INSERT
built a column list omitting them; Postgres rejected with
`null value in column "aspect_ratio"... violates not-null
constraint`. Django's `default=""` is Python-level, not
column-level DEFAULT. Restarted the worker; re-fired
succeeded.

Real-mode result: 5-second 1280×720 image-to-video clip
from the brewery image, $0.25 Runway credits, ~28s wall-
clock. Routed through `gen4_turbo` (image-to-video) because
`prompt_image` was supplied.

### `a233d10` — W11.6.5.3 runtime auto-titles output assets

Operator opened backdrop_composite minutes after W11.6.5.1
shipped — clip picker still showed CDN URL tails like
`5cf5ab4e-0398-480c-b33b-f994f567ccc1.mp4?_jwt=eyJh…`.
W11.6.5.1 only set title for images created via the
W11.6.2 ImageViewSet; clips + audio produced by the
composition runtime had empty title.

* `shell/apps/compositions/tasks.py` — `_persist_asset` now
  sets `title=composition.name` (truncated to 120-char cap).
  Every CLIP / AUDIO / TRANSCRIPT / VOICE row the runtime
  persists inherits a readable label for free. Composition
  names are already operator-readable because every starter
  generates them ("Talking-head — Marcus", "Cinematic visual
  — sunrise brewery").
* 2 new tests covering inheritance + 120-char truncation.

Backfill: 26 existing clip/audio rows in `Admin's workspace`.
Operator confirmed the backdrop_composite picker now reads
"Talking-head — Marcus" / "Talking-head — Sasha" /
"W11.6.5 dogfood take 3 — brewery image-to-video" instead
of CDN URL tails.

Required Celery worker restart (the change is in the
worker-loaded `tasks.py`).

## Calibration moments worth carrying

These belong in `TRUST_CALIBRATION.md` (appended this
session); listed here for handoff narrative.

1. **The W11.6.5.1 narrow-fix lesson.** When I shipped
   W11.6.5.1 I said "clip + audio assets still leave title
   empty (their legacy filename-based labels are at least
   somewhat readable)." That was rationalisation. Operator
   opened backdrop_composite minutes later and the clip
   picker labels were clearly unusable (CDN URL tails look
   exactly like IDs). The right answer was to fix all asset
   types in W11.6.5.1, not split into two slices. **Don't
   rationalise "somewhat readable" — actually look at what
   the operator-facing surface renders.**

2. **The W11.6.5.2 cap-too-tight lesson.** Unit tests for
   W11.6.5 used `mock_mode=True` which short-circuits before
   hitting media-engine — that's why the 2048-char
   prompt_image cap wasn't caught at test time. **When a
   slice adds a NEW input shape (data URI to a previously-
   URL-only field), audit all downstream max_length / size
   guards before declaring success.** Real-mode dogfood is
   the only test that exercises the full type contract.

3. **The stale Celery worker rule.** SESSION 173 close said
   "restart only for K6 / R6 / R7.2 / render_video flows."
   That note missed `execute_composition` + `retry_step` +
   every primitive that creates Asset rows. **ANY model-
   extending session needs a Celery worker restart**, not
   just the LLM-using flows. Generalize the rule.

4. **Real-mode dogfood discipline.** Two slices in a row
   (W11.6.5.2 cap, W11.6.5.3 missing titles) had bugs unit
   tests missed but real dogfood caught immediately. The
   dogfood pattern (operator drives the UI, AI watches DB +
   logs + drives any shell-based verification) is load-
   bearing. **Plan for dogfood after every operator-facing
   slice ships; don't declare done until the operator
   confirms.**

5. **Read runtime FIRST when assessing capability.** SESSION
   173 mid-session inventory was wrong about embeddings
   because I synthesized from docs + grep instead of reading
   the database. INVENTORY exists for exactly this reason.
   A 5-line shell query against magnitude + cost_micros
   would have caught the "mock-only" misstatement before it
   became a candidate next-session task.

## Cast roster state (unchanged)

  - Riggs the Donkey (founder voice) — natural-looking bake
  - **Sasha the Raccoon** (sales) — voice `clara`,
    "nailed it" verdict
  - Donny the Sloth (user stories) — dental artifacts on
    `drew` voice
  - Maya the Panda (educator) — untested in real-mode
  - **Marcus the Battle Unicorn** (AP history tutor) — voice
    `marcus`, Nerva–Antonine doc attached

## Workspace state at session close

* Spokespeople: 5 (cast unchanged)
* Knowledge docs: 2 (3 → 2; YouTube-polluted doc deleted
  in `e4d5761`)
* Knowledge chunks: 31 (32 → 31; same doc deletion)
* Compositions: 30 (28 → 30; +2 dogfood cinematic_visual)
  - 27 completed · 3 failed (the failed = the two W11.6.5.2
    pre-fix dogfood attempts + 1 prior)
* Image assets: 3 (unchanged; all titled now via W11.6.5.1
  backfill)
* Clip assets: 27 (25 → 27; +2 dogfood, all backfilled with
  titles via W11.6.5.3)

## Final state — tests + routes

* **Django**: **782** (727 → 782, +55)
* **Media-engine**: **133** (unchanged — `/internal/styles/`
  is exercised via Django mocks; new max_length is metadata-
  only)
* **SPA vitest**: **91** (53 → 91, +38)
* **Migrations**: **54** (53 → 54; W11.6.5.1's Asset.title)
* **Media-engine routes**: **132** (unchanged)
* **Django URL patterns**: +0 this session (cost telemetry +
  voice telemetry extended existing endpoints)
* **Real-mode spend**: ~$0.55 total (~$0.30 OpenAI + $0.25
  Runway)

## Operational notes carried forward

1. **Celery worker restart is REQUIRED for any model-extending
   session.** Not just LLM flows. Two SESSION 174 bugs were
   caused by stale workers. See TRUST_CALIBRATION entry #3.
2. **SPA gates need both `pnpm test` AND `pnpm build`.**
   vitest uses esbuild which skips full TS check; tsc -b in
   build catches subtle issues. Already TRUST_CALIBRATION'd
   from `3ecb6fe` commit; reinforced.
3. **Doc-with-commit discipline held this session**: each
   feature commit updated its slice's documentation inline.
   No catch-up pass needed.
4. **Real-mode dogfood is the only complete test surface.**
   Mock-mode unit tests cover the happy path of the Python
   types but miss real-world shape mismatches (max_length,
   data-URI size, schema drift). Plan for operator-driven
   dogfood after every operator-facing slice.

## FIRST THING (SESSION 175): pick by mood

Inventory pass at session-start would surface the current
state. From SESSION 174's natural follow-ons:

1. **Multi-step composition title disambiguation** — v1
   leaves the same title across all step outputs in a
   long_form_ad / storyboard_voiced composition. Operator
   picking from 3 hook/action/payoff clips will see the
   same label thrice. ~30 min surgical fix.
2. **TRANSCRIPT + VOICE asset titles** — covered by the
   W11.6.5.3 runtime change but these don't surface in
   recipe pickers today. Worth verifying when they do.
3. **W11.x voice swap dogfood at scale** — SESSION 171
   shipped voice swap, SESSION 174 added the telemetry.
   Real operator-driven swap on Marcus (clara → roman →
   marcus) with banner observation. ~$0.05 spend, ~5 min.
4. **F8.1 — K10 seed corpus** — still blocked on
   operator-authored markdown.
5. **YouTube transcript extractor** — K7.x reject-with-
   actionable-message is the v1 stopgap. v2 would route
   YouTube URLs to youtube-transcript-api or oEmbed
   instead of trafilatura. ~1 session.
6. **Cost panel polish** — credit-vs-dollar mode toggle
   (Stability credits ↔ dollars), per-day chart, per-
   recipe breakdown. ~1 session.
7. **K6.6 — second-render dogfood for one cast member**
   to verify the gpt-5 family migration + verifier fixes
   land cleanly across multiple subjects.

Operator preference: pick at session start.

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

**SESSION 175 stack-up note**: Celery worker was restarted
TWICE in SESSION 174 (once for W11.6.5.2 / model fields,
once for W11.6.5.3 / tasks.py). Fresh worker holds the
W11.6.5.3 runtime. If SESSION 175 touches `apps/compositions/`
models OR `tasks.py` OR any primitive in
`apps/compositions/primitives/`, restart again.

**Smoke checks** (counts as of session close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 782 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 91 vitest tests
```
