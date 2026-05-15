---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`
> (5 verbs shipped after SESSION 125; ~12 per-primitive verbs
> sequenced V3-V14 in the video composition arc).
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — 9 contract rules, V0-V15 slice breakdown;
> K6.5 absorbed into V3; replaces the legacy "additional video
> kinds" queue items). V1 schema shipped same session.
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown; live two-way WebRTC conversations grounded in
> workspace knowledge; uses V1's Asset shape for transcript
> persistence).
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown; merges Spokespeople / Knowledge / Recipes into
> one workspace experience without adding persistence).
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_142_VIDEO_COMPOSITION_LOCK.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live in
real-mode (SESSION 136). Knowledge-layer scope-locked
(SESSION 137) — `docs/design/KNOWLEDGE_LAYER.md` is the new
contract.

**Phase 4 (two parallel arcs as of SESSION 142):**

- **Knowledge arc (K1-K10).** K1-K7 shipped + K4.1 + K4.2 +
  K6.2 cleanups landed SESSION 142. Remaining: K8/K9
  conversation pipeline + REST/SPA, K10 onboarding seed.
- **Video composition arc (V0-V15).** Scope-locked SESSION
  142 — `docs/design/VIDEO_COMPOSITION_V1.md`. **K6.5 absorbed
  into V3** — the talking-head render rewire ships as the
  first step primitive (`generate_avatar_speech`) inside the
  new Asset+Composition architecture, not as a one-off
  endpoint swap. Replaces "additional video kinds" queue.
  V1 (schema only) is next.
- **Realtime avatar arc (R0-R10).** R0 scope lock shipped
  SESSION 142 (`docs/design/REALTIME_AVATAR_V1.md`). 10
  contract rules locked, two-table data model
  (RealtimeSession + RealtimeToolInvocation) sharing V1's
  Asset shape, provider abstraction registry, knowledge
  one-way bridge (Runway documents composed FROM
  KnowledgeDocument rows). R1 (schema) is the next slice.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0 | Knowledge-layer scope lock                      | DONE (SESSION 137) |
| K1 | Postgres + pgvector migration                   | DONE (SESSION 138) |
| K2 | KnowledgeDocument + KnowledgeChunk + retrieval skeleton | DONE (SESSION 138) |
| K3 | Ingestion pipeline (paste + upload + PDF)       | DONE (SESSION 138) |
| K4 | Workspace knowledge route (SPA + REST)          | DONE (SESSION 138) |
| K4.1 | Knowledge document detail view (chunks)       | DONE (SESSION 141) |
| K4.2 | Dedup-restore bug fix                          | DONE (SESSION 142) |
| K5 | Spokesperson "Knowledge" tab                    | DONE (SESSION 138) |
| K6 | Render flow integration (synthesis only)        | DONE (SESSION 139) |
| K6.2 | Pre-render validation (portrait/avatar required) | DONE (SESSION 142) |
| K7 | URL ingestion + serper discovery                | DONE (SESSION 140) |
| V0 | Video composition scope lock                    | DONE (SESSION 142) |
| V1 | Asset + Composition + CompositionStep schema   | DONE (SESSION 142) |
| V2 | Composition runtime + state machine + resume   | DONE (SESSION 142) |
| V3 | `generate_avatar_speech` primitive + `talking_head` starter (absorbs K6.5) | DONE (SESSION 143) |
| V4 | `generate_visual_clip` primitive (`gen4_turbo`/`gen4.5`) + `cinematic_visual` starter | DONE (SESSION 143) |
| V5 | `split_script` + `concat_clips` + `long_form_ad` starter — launch differentiator | DONE (SESSION 143) |
| V6 | Backwards-compat shim (`Video` → `talking_head` composition wrapper) | DONE (SESSION 143) |
| V7 | Composite primitives (`composite_video` + `mix_audio`) + 5 layout-modifier starters | DONE (SESSION 143) |
| V8 | First multi-step starter: `talking_head_with_backdrop` | DONE (SESSION 143) |
| V9 | Polish + format primitives: captions / intro+outro / trim / reformat + 2 starters | DONE (SESSION 143) |
| V10 | Voice flows: `design_voice` + `dub_audio` + 2 starters (restores 29-lang hackathon dubbing) | DONE (SESSION 143) |
| V11 | `style_remix` (Aleph, chunked path) + `style_remix_pass` starter | DONE (SESSION 143) |
| V12 | `transcribe` (Whisper) + `add_captions` auto mode + `recut_teaser` (FIRST NET-NEW) | DONE (SESSION 143) |
| V13 | `generate_image` + `storyboard_ad` starter (storyboard_voiced deferred to V14) | DONE (SESSION 143) |
| V14 | `dialogue_scene` starter + `audio_extract` primitive (unblocks deferred storyboard_voiced) | DONE (SESSION 143) |
| V15.0 | Backend foundation: recipe registry + REST surface (`/api/recipes/`, `/api/compositions/`) | DONE (SESSION 144) |
| V15.1 | SPA gallery shell + 3 simplest recipes live (`talking_head`, `cinematic_visual`, `talking_head_polished`) | DONE (SESSION 144) |
| V15.2 | Layout + format family forms live (7 recipes) + `GET /api/assets/` + asset_picker | DONE (SESSION 144) |
| V15.3 | Voice + style + long-form + storyboard + recut forms live (6 recipes) | DONE (SESSION 144) |
| V15.4 | Dialogue form + storyboard_voiced bonus + legacy CTA retirement — **V-ARC CLOSURE** | DONE (SESSION 144) |
| F0 | Workspace fabric scope lock — F1-F10 slice breakdown, 9 contract rules | DONE (SESSION 144) |
| F1 | Per-spokesperson recipe entry (`/recipes?spokesperson=<id>` hint propagation) | DONE (SESSION 144) |
| F2 | Persistent nav rail (Dashboard / Spokespeople / Knowledge / Recipes) | DONE (SESSION 144) |
| F3 | Workspace overview dashboard (activity feed + knowledge corpus stats + spokesperson badges + squarer cards) | DONE (SESSION 144) |
| F4 | Knowledge preview on recipe forms + brief-mode helper text (expanded scope; surfaces K6 LLM synthesis) | DONE (SESSION 144) |
| F5 | Asset lineage on composition status (Derived from / Used by) | DONE (SESSION 144) |
| F6 | Knowledge citations on composition status (resolve chunk_ids → docs) | DONE (SESSION 144) |
| F7 | Knowledge doc → compositions reverse panel | DONE (SESSION 144) |
| F8 | Onboarding walkthrough (subsumes K10 onboarding seed) | **NEXT (SESSION 144)** |
| F9 | Legacy single-form SPA deletion (`/spokespeople/<id>/render` route) | Queued |
| F10 | Fabric arc closure + retro | Queued |
| R0 | Realtime avatar arc — scope lock                | DONE (SESSION 142) |
| R1 | RealtimeSession + RealtimeToolInvocation schema | Queued |
| R2 | Media-engine `/internal/realtime_sessions/` + provider abstraction | Queued |
| R3 | Django broker (`/api/realtime_sessions/`) + tier-limit gate | Queued |
| R4-R10 | Knowledge bridge, transcript persist, memory, tools, SPA, cost governance | Queued |
| K6.3 | Brief length cap in script synthesis           | Queued |
| K6.4 | Duration derived from script length            | Deprecated by V9 trim/reformat primitives (shipped SESSION 143) |
| K7.1 | Per-chunk cost telemetry surface in UI         | Queued |
| K8 | Conversation pipeline                           | Queued (parallel to V arc) |
| K9 | Conversation REST + SPA                         | Queued |
| K10 | Onboarding seed                                | Queued |
| W11.1 | Edit-spokesperson modal                      | Queued |
| W12 | Legacy single-form retirement                  | Folded into V15 |

**Cast roster in workspace `admins-workspace`:**

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - Sasha the Raccoon (sales) — id `79d48883-...`
  - Donny the Sloth (user stories) — id `f30b2980-...`
  - Maya the Panda (educator) — id `9410f23f-...`

Cast can render *informed* videos now (K6 shipped SESSION 139)
— `build_render_brief` runs RAG + gpt-5-mini synthesis at video
create time, citations persist on the Video row. Operators
attach workspace docs to spokespeople via K4/K5; renders draw
on those docs automatically.

---

## SESSION 140 status — K7 shipped

**K7 (URL ingestion + serper discovery):** the last
*ingestion-side* slice. Operators can now bring in workspace
knowledge four ways: paste, PDF upload, URL paste, or
web-search discovery.

* New `shell/apps/embeddings/url_fetch.py` — httpx GET +
  `trafilatura.bare_extraction` for HTML main-content
  extraction. Snapshot-at-ingest semantics (no re-fetch).
  Size cap 10 MB, timeout 15s, polite UA. Surfaces 4xx/5xx,
  paywall / empty extract, connection errors as
  `UrlFetchError`.
* New `shell/apps/embeddings/serper.py` — serper.dev wrapper
  ported from u-d-b's `core/tools/web_search.py:WebSearchTool`.
  Returns `[SearchResult(title, url, snippet, position)]`.
  Django cache (Redis db 2) by `sha256(query|top_k)` with
  1-hour TTL. **Fourth force-mock flag:** `SERPER_FORCE_MOCK=1`
  matches the other three; returns deterministic stubs.
* Extended `ingestion.ingest_url()` and the serializer's
  three-way XOR — exactly one of `text_content` /
  `pdf_data_uri` / `source_url_input` is required on create.
  `via_serper=True` flag drives `ingested_via='serper'`.
* New `@action(detail=False, methods=["post"], url_path="search")`
  on the viewset. Body: `{"q", "top_k"}` → returns serper
  results. Authenticated-only; not workspace-scoped (search
  results aren't documents yet).
* SPA: added "URL" and "Search" tabs to the
  `/workspace/knowledge` upload panel. Search tab UX: type
  query → submit → results list → per-row "Ingest" button
  flows the URL through the same fetch+extract path with
  `via_serper=true`.
* Title becomes optional on URL ingests — falls back to the
  page's `<title>` tag (via trafilatura) or hostname.
* **32 K7 backend tests** (9 url_fetch + 11 serper + 12 API)
  + **3 K7 e2e specs** (tab switchability + URL form
  validation + search results render).

**Test counts (cumulative): 99 K-tests** across the embeddings +
videos apps. Plus 46 prompts pytest = **145 backend tests**.
**38 e2e specs** (35 prior + 3 K7).

### SESSION 142 outcome summary

Five commits landed this session, all on `main` (not pushed):

1. **`4321fdb`** — K4.2 dedup-restore + K6.2 portrait
   validation cleanups (3 new K-tests).
2. **`ab3610c`** — V0 video composition scope lock
   (`docs/design/VIDEO_COMPOSITION_V1.md`, 9 contract rules,
   16 slices V0-V15).
3. **`68561fd`** — V1 schema: `apps.compositions` app with
   Asset / Composition / CompositionStep models, signals,
   admin, and 13 V-tests.
4. **`0e01493`** — R0 realtime scope lock
   (`docs/design/REALTIME_AVATAR_V1.md`, 10 contract rules,
   11 slices R0-R10).
5. **`a8692aa`** — V2 composition runtime: registry pattern,
   3 mock primitives, `execute_composition` + `retry_step`
   Celery tasks, partial-failure resume, cost aggregation,
   18 V2 tests (133 backend total).

Also locked late-session: **V5 slice promoted from V7
position** (long-form ad). Long-form is a launch
differentiator — no AI provider ships single-call video
longer than ~20s, so every long-form AI video in the wild
is stitched. Bringing it forward to the third capability
slice (after V3 + V4) positions the platform's distinctive
selling point as early as possible. Change log in
`docs/design/VIDEO_COMPOSITION_V1.md` §"Change log".

### SESSION 143 — V3 through V14 shipped (twelve capability slices)

Thirteen commits landed (twelve feature commits + one
mid-session reorder), all on `main`, not pushed:

| Slice | Commit | Capability |
|---|---|---|
| V3 | `54032c2` | `generate_avatar_speech` + `talking_head` (absorbs K6.5) |
| V4 | `1251def` | `generate_visual_clip` + `cinematic_visual` |
| V5 | `c2c4ba2` | `split_script` + `concat_clips` + `long_form_ad` (launch differentiator) |
| V6 | `7c968a5` | Video backwards-compat shim |
| (reorder) | `7782c34` | V9 → V7 reorder (composite ahead of talking_head_with_backdrop) |
| V7 | `3af1c28` | `composite_video` + `mix_audio` + 5 layout starters |
| V8 | `545f991` | `talking_head_with_backdrop` |
| V9 | `ec130a9` | captions / intro_outro / trim / reformat + 2 starters |
| V10 | `f237ac7` | `design_voice` + `dub_audio` + 2 starters (29-lang dubbing) |
| V11 | `cfe9214` | `style_remix` (Aleph, chunked path) + `style_remix_pass` |
| V12 | `8b24465` | `transcribe` (Whisper) + `recut_teaser` (FIRST NET-NEW) |
| V13 | `43be57b` | `generate_image` + `storyboard_ad` |
| V14 | (TBD) | `dialogue_scene` starter + `audio_extract` primitive (first doc-with-commit slice) |

**Test progression:** 133 → 358 backend tests (+225
across the slice run). Media-engine: 109 → 123 routes
(+14 new `/internal/*` endpoints).

**Architecture surface after SESSION 143:**
* 13 step primitives registered (3 mock + 10 real V3-V14).
* 13 starter compositions across talking-head, long-form,
  cinematic, polish, voice, style, teaser, storyboard,
  dialogue, + 5 layout modifiers.
* 14 sanctioned media-engine `/internal/*` routes for the
  composition arc (audio_extract added in V14).
* `Video` model wraps a `talking_head` composition under
  the hood; SPA contract unchanged.

**Three calibration moments worth carrying forward:**
* The V9→V7 reorder pattern is the rule, not the
  exception. After two consecutive reorders (V7-from-V5,
  V9-from-V7) the discipline is: **check the dependency
  graph of every prior slice's data shape before locking
  the next slice's scope, not just the immediate
  predecessor.**
* "We already had this" from the operator (V10, V11, V13)
  is the most valuable signal. The right framing is
  restoration of shipped hackathon capability under new
  architecture, not "first-time net-new."
* Doc discipline gap surfaced at end of session: V3-V13
  shipped 11 feature commits without paired context-kit
  refreshes. Resolved with this catch-up + the SESSION
  143 handoff + new CLAUDE.md rule that ties context-kit
  updates to feature commits.

**Deferred from V-arc:**
* `storyboard_voiced` — needs an `audio_extract` primitive
  to extract the audio track from an avatar_speech CLIP so
  it can be mixed under the storyboard. Scheduled for
  V14+.

### Next: V14 — `dialogue_scene` + optional `audio_extract`

V14 is the last hackathon-shipped capability port. The
`dialogue_scene` starter ports the hackathon's
`dialogue_service.py` — a multi-character skit with N
stitched avatar lines (each line a `generate_avatar_speech`
call alternating across the cast).

Two flavors:
* **`dialogue_scene` straight stitch** — N speech steps
  concatenated in script order. Matches the hackathon's
  shipped output shape exactly.
* **`audio_extract` primitive** (optional V14 extension) —
  CLIP → AUDIO via ffmpeg `-vn`. Unblocks the deferred
  `storyboard_voiced` starter (storyboard → avatar_speech
  → audio_extract → mix_audio with storyboard as base).

**Reference reads before V14:**
1. `runway-hackathon/backend/app/services/dialogue_service.py`
   — the script-to-lines parsing + stitching pattern.
2. V5's `long_form_ad` starter (the closest precedent for
   "N speech steps + 1 concat" pre-computation).

### After V14

* **V15** — SPA recipe gallery. Operator picks from
  starter compositions in a card UI; form maps to step
  inputs. Retires the legacy single-form video create
  UI. Likely the last V-slice.

### Alternative next slice: R1 — RealtimeSession schema

Unblocked since V1 shipped. Mirrors V1's pattern: new
`apps.realtime` app, two models, cross-workspace signal +
`clean()`, repo-level isolation test, admin registration.
Schema only; broker is R3.

R1 is a viable next session if you want to advance the
realtime arc in parallel — V2's runtime patterns inform
R3's broker design but R1 doesn't require V14 to ship
first.

---

## SESSION 139 status — K6 shipped

**K6 (render flow integration):** the load-bearing slice where
knowledge starts *informing* renders.

* New `shell/character_os/script_synthesis.py` —
  `build_render_brief(spokesperson, operator_prompt) ->
  ScriptResult(brief, chunk_ids, used_knowledge, model,
  tokens_*)`. Calls `retrieve_for_spokesperson(top_k=5)`,
  injects chunks into a `gpt-5-mini` Responses-API call
  (NOT chat-completions — gpt-4o-mini is deprecating).
  System prompt anchored to `tone_archetype` +
  `business_brief`. `reasoning_effort='low'`.
* `RENDER_SCRIPT_FORCE_MOCK=1` env / settings override
  mirrors `RUNWAY_FORCE_MOCK` + `EMBEDDING_FORCE_MOCK`.
  Returns deterministic
  `"{business_brief}\n\n{prompt}\n\n[knowledge: N chunks: <ids>]"`
  for dev/test.
* Graceful degradation everywhere: empty knowledge → operator
  brief; retrieval failure → operator brief; missing
  OPENAI_API_KEY → operator brief (with chunk_ids still
  logged for audit); OpenAI failure → operator brief (with
  chunk_ids still logged). Render never fails because of
  synthesis.
* `Video.knowledge_chunk_ids` JSONField (migration 0002)
  persists which chunks fed which render. No UI in v1 —
  audit data only.
* Wired into `apps/videos/views.py:perform_create` between
  brief resolution and `MediaEngineClient.create_video`.
  Media-engine contract unchanged.
* **11 K6 tests** in `apps/videos/tests/test_script_synthesis.py`
  (8 unit) + `test_render_with_knowledge.py` (3 integration).
  Covers force-mock, degradation, real-mode without key, OpenAI
  failure, retrieval failure, citation persistence, the no-avatar
  short-circuit (synthesis correctly skipped).

**Calibration carried into the session memory:**

The earlier-saved feedback memory `feedback_openai_gpt5_responses_api.md`
now anchors every future LLM call site in shell. Operator caught
me mid-plan trying to reach for `gpt-4o-mini` + chat-completions
— the right answer was `gpt-5-mini` + Responses API, with the
shape already documented in u-d-b's
`core/services/llm_provider_registry.py:122`. Same pattern as
the K3 cost-cap correction: when adding infrastructure that
u-d-b already has, READ u-d-b first.

**Test counts (cumulative): 64 K-tests** across the embeddings +
videos apps. Plus 46 prompts pytest = **113 backend tests**.
**35 e2e specs** (unchanged from SESSION 138 — K6 has no
user-visible UI beyond the existing render flow, so no new e2e).

### Next: K7 — URL ingestion + serper discovery

K7 was deferred from K3 (scope was paste + PDF only). Adds:

* `apps/embeddings/url_extract.py` — `trafilatura` fetch +
  main-content extraction. Snapshot-at-ingest semantics (no
  re-fetch; URL freshness contract from scope-lock).
* `apps/embeddings/serper.py` — serper.dev search client port
  from u-d-b's `core/tools/web_search.py:WebSearchTool`.
  Returns `{title, url, snippet}` triples. Redis-cached.
* `ingestion.ingest_url(url) -> IngestResult` — fetch +
  extract → through the same `_persist` path.
* New `pdf_data_uri`-shaped field: `url` (just a URL string)
  on the create endpoint. Or new sibling endpoint
  `POST /api/knowledge/url/` — settle in slice planning.
* SPA: new "Search" tab on `/workspace/knowledge` upload
  panel. Operator types a query → serper returns candidates
  → operator picks → fetch + ingest pipeline runs.
* `SERPER_API_KEY` env var. Add to `.env.example`.
* Tests cover: URL fetch (mocked httpx), extraction
  (mocked trafilatura), idempotent re-ingest of the same
  URL (content_hash dedup still works), 4xx/5xx URL
  handling, serper API mocking.

### What's NOT K7

- Active crawling (follow links, traverse subdomains) —
  explicitly out of scope per K0 contract rule.
- Auto re-fetch on a schedule — out of scope. Operator
  deletes + re-ingests if they want fresh content.
- Conversation surface — K8/K9.
- Onboarding seed — K10.

**K1 (Postgres + pgvector):** infra-only swap. sqlite → Postgres,
pgvector extension installed via
`apps.embeddings.migrations.0001_install_pgvector`. All 2,718
sqlite rows migrated successfully. Details in
`docs/POSTGRES_MIGRATION.md`. Two `post_save` signals
(`accounts.signals`, `billing.signals`) gained `raw=True`
guards so future `loaddata` runs don't collide on
auto-created rows. Pre-K1 unblocker (`RUNWAY_FORCE_MOCK=1`)
also shipped.

**K2 (Knowledge schema + retrieval skeleton):** the load-bearing
privacy guarantees. `KnowledgeDocument` + `KnowledgeChunk` in
`apps.embeddings.models`; `ConversationMessage` +
`ConversationEmbedding` in `apps.conversations.models`. Single
retrieval surface at `apps/embeddings/retrieval.py` with two
named functions. `m2m_changed` signal vetoes cross-workspace
spokesperson attaches.

**K3 (ingestion pipeline):** operator input → KnowledgeDocument.
* `apps/embeddings/text_splitter.py` — paragraph-aware,
  sentence-fallback splitter (chunk_size=1000, overlap=200).
* `apps/embeddings/embedding_service.py` — OpenAI
  `text-embedding-3-small` (1536-dim), Redis cache via
  Django CACHES on db 2, `EMBEDDING_FORCE_MOCK=1` env/settings
  override mirroring the `RUNWAY_FORCE_MOCK` pattern.
* `apps/embeddings/pdf.py` — `pdfminer.six` text extraction
  (text-based PDFs only; OCR is out of scope).
* `apps/embeddings/ingestion.py` — `ingest_text()` +
  `ingest_pdf()` orchestrators with content-hash dedup.
* `apps/embeddings/tasks.py` — `embed_document` Celery task,
  idempotent, retries on network errors.
* `apps/embeddings/management/commands/smoke_ingest.py` — full
  end-to-end smoke (`ingest_text → embed_document → retrieve`).

**K4 (workspace knowledge route):** end-to-end CRUD surface.
* REST: `KnowledgeDocumentViewSet` at `/api/knowledge/`
  (list/create/detail/patch/destroy), workspace-scoped via
  `?workspace=<uuid>` query param + `IsWorkspaceMember`
  permission. Soft delete sets `is_active=False` (chunks stay
  for admin audit).
* `apps/embeddings/serializers.py` — `KnowledgeDocumentSerializer`
  with `text_content` + `pdf_data_uri` write-only fields
  (exactly one required on create). Auto-detects markdown vs
  plain text via heading-prefix heuristic.
* `apps/embeddings/views.py` + `apps/embeddings/urls.py` —
  wired into `character_os/urls.py`.
* SPA: `/workspace/knowledge` route at
  `web/src/routes/workspace/knowledge.tsx`. List + paste +
  PDF upload tabs + status pills + soft delete + 3s polling
  while any doc is mid-pipeline.
* SPA API client: `web/src/lib/api/knowledge.ts` — zod
  schemas, React Query hooks, helper to convert a `File` to
  the `data:application/pdf;base64,...` data URI.
* Dashboard now has a "Knowledge" link in the masthead
  (`nav-knowledge` testid).
* **16 K4 API tests** in `apps/embeddings/tests/test_api.py`
  cover create paths, validation, scoping, M2M veto, soft
  delete. **3 K4 e2e specs** in
  `web/e2e/workspace-knowledge.spec.ts` cover the full
  user-visible flow.

---

## SESSION 138 status — K1 through K5 all shipped

**K5 (spokesperson "Knowledge" panel):** per-spokesperson view.
* Backend: `?spokesperson=<uuid>` filter on the list endpoint
  (visibility = empty M2M OR M2M includes them — mirrors
  `retrieve_for_spokesperson`). Two custom actions:
  `POST /api/knowledge/<id>/attach/` and `.../detach/` with
  `{spokesperson_id}` payload. Both idempotent;
  cross-workspace attaches rejected.
* SPA: `web/src/components/knowledge-panel.tsx` — new
  reusable component. Filtered list view + per-row toggle
  ("Make {name}-only" / "Detach") + empty state + status
  pills + 3s polling while docs are mid-pipeline. Wired into
  `routes/spokespeople/$id.tsx` as a panel section.
* SPA API client: `useSpokespersonKnowledge` hook +
  `useToggleSpokespersonAttachment` mutation in
  `lib/api/knowledge.ts`.
* **10 K5 backend tests** in `test_api_k5.py` + **2 K5 e2e
  specs** in `web/e2e/spokesperson-knowledge.spec.ts`.

**SESSION 138 test counts: 56 K-tests** in
`apps/embeddings/tests/` (7 privacy + 6 splitter + 6 embedding
service + 10 ingestion + 16 K4 API + 10 K5 API + 1 grep). Plus
46 prompts pytest = 102 backend tests at SESSION 138 ship.

### How to run all K tests (now spans embeddings + videos)

```bash
cd shell && source .venv/bin/activate
python -m pytest apps/embeddings/tests/ apps/videos/tests/ -v   # 67 K-tests
EMBEDDING_FORCE_MOCK=1 python manage.py smoke_ingest  # ingestion smoke
python manage.py smoke_video                          # render smoke (uses K6 path)

cd ../web
pnpm test                                       # 3 SPA unit
pnpm e2e --grep 'knowledge'                     # K4 + K5 specs (5 tests)
```

If any of these fail during K7+, the load-bearing privacy,
ingestion, or render contract has broken. Fix the
implementation, not the tests.

**To run Celery + Django with all three mocks active for local
SPA + render dev:**

```bash
EMBEDDING_FORCE_MOCK=1 \
RENDER_SCRIPT_FORCE_MOCK=1 \
python manage.py runserver 8000

EMBEDDING_FORCE_MOCK=1 \
RENDER_SCRIPT_FORCE_MOCK=1 \
celery -A character_os worker --pool=solo
```

The three `*_FORCE_MOCK` flags mirror each other. Without
them, the corresponding pipeline step needs the relevant API
key (`OPENAI_API_KEY` for embedding + render-script;
`RUNWAY_API_KEY` for the media-engine — but `RUNWAY_FORCE_MOCK`
is the media-engine's setting, set when starting `uvicorn`).

---

## Queued investigations (priority-ordered)

Knowledge-layer arc (K-prefixed) is locked in
`docs/design/KNOWLEDGE_LAYER.md` §Slice breakdown. Everything
else is ordered by independence + priority.

1. **K6.5 — Talking-head render rewire** (route through
   `/v1/avatar_videos` instead of `gen4_turbo`; the real
   spokesperson speech pipeline). See "Next" section above.
2. **K4.2 — Dedup-restore bug** (~15 min). Soft-deleted
   docs block re-ingestion; should restore + re-embed.
3. **K6.2 — Pre-render validation** (~10 min). Shell
   viewset should fail fast when avatar_id/portrait is
   missing; better operator-facing error than the current
   opaque 400 from media-engine.
4. **K6.3 — Brief length cap** in `script_synthesis.py`.
   Truncate to <=2000 chars before sending to media-engine.
5. **K6.4 — Duration matching**. Default `duration=5s`
   doesn't fit a 30-second synthesized script; derive from
   script word count.
6. **K7.1 — Cost telemetry surface**. Per-chunk
   `embedding_cost_micros` is stored but no UI shows it.
7. **K8 — Conversation pipeline** (message + embedding +
   reply synthesis on top of the K2 schema).
8. **K9 — Conversation REST + SPA.**
9. **K10 — Onboarding seed.**
10. **First marketing video** — unlocked once K6.5 ships
    real talking-head renders. Attach Character-OS knowledge
    to the admin workspace, render Sasha (or any cast
    member) actually speaking the script.
11. **Voice preset audit** — listen to the four cast members
    with real talking-head renders post-K6.5.
12. **E2e detritus cleanup** — Postgres carries ~495+
    e2e-generated workspaces; `Workspace.objects.filter(slug__startswith='e2e-').delete()`.
13. **OpenAI client factory port** — u-d-b has
    `core/services/openai_client_factory.py` that
    centralises timeout/retry config. K3 + K6 + K8 will be
    three call sites; the factory pattern is worth porting.
14. **W11.1 — Edit-spokesperson modal.**
15. **W12 — Legacy form retirement.**
16. **Cast sync command** — pull updates from
    `spokesperson_templates.py` into existing rows.
17. **Tier 2 prompt helpers** — likely subsumed by K6's
    `build_render_brief` synthesis.
18. **Stuck-row janitor.**
19. **Additional video kinds** — cinematic / dialogue / long_ad
    (depend on K6.5 patterns).
20. **Act-Two performance capture.**
21. **`lesson` video kind.**
22. **Real Google OAuth + dj-stripe.**
23. **Allauth legacy-settings cleanup.**
24. **smoke_voice / smoke_avatar transaction discipline.**
25. **Drift verifier** (`verify_doc_claims --only-drift`).
26. **Brand Identity v2 + dark mode.**

---

## How to bring the stack up locally

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

Postgres details + troubleshooting in
`docs/POSTGRES_MIGRATION.md` (SESSION 138 / K1 shipped).

**Real-mode vs. mock-mode:** the media-engine reads
`<repo-root>/.env` for `RUNWAY_API_KEY`. With the key present
(real-mode), Runway calls take 15-30s each — fine for CLI use
(`seed_cast`, manual wizard runs) but breaks the e2e suite which
expects sub-second responses. For deterministic mock-mode without
stashing the real `.env`:

```bash
# Either set in shell before starting media-engine:
RUNWAY_FORCE_MOCK=1 uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# Or export for the session:
export RUNWAY_FORCE_MOCK=1
```

The override forces `Settings.runway_mock=True` regardless of
`RUNWAY_API_KEY` presence. Landed SESSION 138 as the pre-K1
unblocker.

Smoke checks:

```bash
# Backend (from shell/)
python manage.py inventory
python manage.py smoke_headless_auth
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_portrait
python -m pytest character_os/prompts/        # 46 tests
python -m pytest apps/embeddings/tests/ apps/videos/tests/  # 67 K-tests
EMBEDDING_FORCE_MOCK=1 python manage.py smoke_ingest    # end-to-end ingest → embed → retrieve

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e            # full lifecycle ~50s (35 specs), single-shot
```

Cast management CLIs:

```bash
# Generate cast portrait PNGs to disk for preview
python manage.py generate_cast
python manage.py generate_cast --key maya

# Seed the cast as Spokesperson rows + bind avatars
python manage.py seed_cast --workspace-slug admins-workspace
python manage.py seed_cast --workspace-slug admins-workspace --key maya --force
```

---

## AI / assistant context

- Last session: SESSION 141 — **K4.1 shipped** (knowledge
  document detail view at `/workspace/knowledge/:id`) +
  **major audit finding**: K6's render path uses
  `gen4_turbo` (image-to-video) instead of `/v1/avatar_videos`
  (talking-head). Cast members render as silent animated
  portraits, not speaking. K6.5 (rewire) is the next slice.
  Also shipped a `prompt_image` fix in `apps/videos/views.py`
  so renders against real Runway don't 400 on missing image.
  Five smaller fixes queued (K4.2, K6.2-K6.4, K7.1) from
  the audit. Stack now has all four real API keys
  (RUNWAY, OPENAI, SERPER, plus pre-existing) so end-to-end
  real-mode testing works for everything except K6's
  output (the wrong endpoint). **Cumulative tests: 145
  backend pytest, 38 e2e specs, all green.**
- **Calibration carried forward:**
  - **Cast is example data, not product shape.** When
    discussing capabilities, ask "is this true of every
    spokesperson, or just this one's framing?" Capabilities
    live on the model; framing lives in `business_brief`.
  - **Ask for prior art before grading severity on
    hypotheticals.** Already caught three times (cost-cap
    math, Maya tutor-mode axis, gpt-5 vs gpt-4o-mini). When
    adding infrastructure that u-d-b already has, READ
    u-d-b first.
  - **OpenAI gpt-5 family uses the Responses API, not
    chat.completions.** New memory captures the shape from
    u-d-b's `llm_provider_registry`.
  - **Push back when framing looks wrong.** Convergence
    happens through pushback, not in spite of it.
- **The knowledge layer is K1-K10. Six shipped, four to go.**
  Don't try to ship the remainder in one session. K7 (URL +
  serper) is the next user-visible win; K8/K9 (conversation)
  is the deepest behavioral arc.
- **Privacy guarantees from K0 are load-bearing.** All seven
  tests in `apps/embeddings/tests/test_retrieval_privacy.py`
  must keep passing — they're the contract, not the
  implementation detail.
- **Three force-mocks now exist.** `RUNWAY_FORCE_MOCK`,
  `EMBEDDING_FORCE_MOCK`, `RENDER_SCRIPT_FORCE_MOCK` — same
  shape. Set all three for fully-offline local dev.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
