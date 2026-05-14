---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`
> (5 verbs shipped after SESSION 125).
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_141_K4_DETAIL_AND_RENDER_AUDIT.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live in
real-mode (SESSION 136). Knowledge-layer scope-locked
(SESSION 137) — `docs/design/KNOWLEDGE_LAYER.md` is the new
contract.

**Phase 4 (knowledge arc):** K6.5 — talking-head render
rewire. K1-K7 shipped + K4.1 (detail view) shipped, but
SESSION 141 surfaced that K6's render path hits the wrong
Runway endpoint (`gen4_turbo` image-to-video instead of
`/v1/avatar_videos` talking-head). The cast members can be
rendered as silent animated portraits today; K6.5 wires the
real talking-head pipeline so they actually *speak* the
synthesized scripts. Conversation pipeline (K8) deferred
until video processing is right.

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
| K5 | Spokesperson "Knowledge" tab                    | DONE (SESSION 138) |
| K6 | Render flow integration (synthesis only)        | DONE (SESSION 139) |
| K7 | URL ingestion + serper discovery                | DONE (SESSION 140) |
| K6.5 | Talking-head render rewire (avatar_videos)     | **NEXT (SESSION 142)** |
| K4.2 | Dedup-restore bug fix                          | Queued |
| K6.2 | Pre-render validation (portrait/avatar required) | Queued |
| K6.3 | Brief length cap in script synthesis           | Queued |
| K6.4 | Duration derived from script length            | Queued |
| K7.1 | Per-chunk cost telemetry surface in UI         | Queued |
| K8 | Conversation pipeline                           | Queued (after K6.5) |
| K9 | Conversation REST + SPA                         | Queued |
| K10 | Onboarding seed                                | Queued |
| W12 | Legacy single-form retirement                  | Whenever |
| W11.1 | Edit-spokesperson modal                      | Queued |

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

### Next: K6.5 — talking-head render rewire

**The bug surfaced in SESSION 141 UI testing.** K6 wired the
RAG + gpt-5-mini script synthesis correctly — the brief
synthesized from real workspace knowledge is good. But the
synthesized brief gets sent to Runway's `gen4_turbo` model
(image-to-video animation), which doesn't generate speech,
lip-sync, or audio. Result: a 5-second silent visual
animation of the spokesperson's portrait — the avatar moves
slightly but doesn't speak.

The **right** endpoint exists in
`media-engine/app/services/character_host_client.py:_generate_real`
— it calls `/v1/avatar_videos` with model `gwm1_avatars`,
shape:

```python
body = {
    "model": "gwm1_avatars",
    "avatar": {"type": "custom", "avatarId": avatar_id},
    "speech": {"type": "text", "text": script},
}
url = f"{settings.runway_api_base}/v1/avatar_videos"
```

The bound voice rides along automatically (voice presets are
bound at avatar-creation time per SESSION 134/136).

### K6.5 scope

The implementation gap is in **media-engine**, not shell —
shell already passes everything we need (kind, avatar_id,
brief, portrait_path). Media-engine needs to route
`kind=spokesperson_ad` through avatar_videos:

- In `media-engine/app/routers/internal.py:post_internal_video`,
  branch on `kind`. For `spokesperson_ad` (and likely several
  other speaking kinds), build the `/v1/avatar_videos` request
  shape and POST to that endpoint instead of going through
  `runway_client.create_task`.
- Same `task_id` response shape so the shell's poll task
  doesn't change.
- The polling endpoint (`GET /v1/tasks/{task_id}/`) is the
  same.
- The legacy `_generate_real` is wrapped around the
  `Campaign` model and hardcodes a single avatar/voice
  combo. The new path needs to accept the avatar_id from
  the request body (not from a Campaign lookup) — same
  three fields, just different lookup.

### What's NOT K6.5

- Brief length cap (K6.3) — separate slice.
- Pre-render avatar/portrait check (K6.2) — separate.
- Conversation pipeline (K8) — deferred until video is right.

### Pre-K6.5 cleanup recommended

The audit surfaced five queued fixes. Worth landing the
quick ones first so K6.5 has clean ground:

- **K4.2** — dedup-restore bug. ~15 min. Soft-deleted docs
  block re-ingestion of the same content; should restore
  + re-fire embed_document instead.
- **K6.2** — pre-render validation. ~10 min. Shell viewset
  should fail fast with a clear message if
  `spokesperson.runway_avatar_id` is empty, rather than
  letting media-engine return an opaque 400.

### Reference reads before K6.5

Per the carried calibration ("when adding integration with
an external service, READ u-d-b / the predecessor first"):

1. `media-engine/app/services/character_host_client.py:_generate_real`
   (lines 412-492) — the existing avatar_videos integration.
   This is what we're porting from Campaign-based to
   Spokesperson-based.
2. `media-engine/app/routers/internal.py:post_internal_video`
   (lines 286-329) — current implementation that hits the
   wrong endpoint. The branch lands here.
3. The K6 handoff
   (`docs/handoffs/SESSION_139_K6_RENDER_INTEGRATION.md`)
   for why the synthesis side is already correct.

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
