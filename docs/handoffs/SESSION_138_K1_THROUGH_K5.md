---
title: "Session 138 — Knowledge layer K1 through K5"
date: 2026-05-14
status: complete
session: 138
previous_handoff: ./SESSION_137_KNOWLEDGE_LAYER_SCOPE_LOCK.md
---

# Session 138 — K1 through K5

## TL;DR

- **What shipped:** six knowledge-arc deliverables in one
  session — a pre-K1 unblocker plus the first five locked
  slices from `docs/design/KNOWLEDGE_LAYER.md` §"Slice
  breakdown."
  1. `RUNWAY_FORCE_MOCK=1` env override
     (`media-engine/app/config.py`) — replaces the
     `mv .env .env.real` workaround.
  2. **K1** — Postgres + pgvector migration. sqlite → Postgres
     16, all 2,718 rows migrated. Details in
     `docs/POSTGRES_MIGRATION.md`. Two `post_save` signal
     guards (`accounts.signals`, `billing.signals`) added
     `raw=True` checks so future `loaddata` runs don't
     collide on auto-created rows.
  3. **K2** — Knowledge data model + retrieval skeleton.
     `KnowledgeDocument` + `KnowledgeChunk` (pgvector,
     HNSW) + `ConversationMessage` +
     `ConversationEmbedding`. Single retrieval surface at
     `apps/embeddings/retrieval.py` with two named functions.
     `m2m_changed` signal vetoes cross-workspace
     spokesperson attaches. **7 privacy tests** prove the
     contract.
  4. **K3** — Ingestion pipeline. `TextSplitter`,
     `embedding_service` (OpenAI + Redis cache +
     `EMBEDDING_FORCE_MOCK=1` mock path),
     `pdfminer.six`-based PDF extraction, ingestion
     orchestrator with content-hash dedup, Celery
     `embed_document` task, `smoke_ingest` management
     command. **23 unit tests + 1 end-to-end smoke.**
  5. **K4** — Workspace knowledge route. REST viewset
     (`/api/knowledge/`), SPA route
     (`/workspace/knowledge`) with paste + PDF upload tabs,
     status pills, polling, soft delete, dashboard masthead
     link. **16 API tests + 3 e2e specs.**
  6. **K5** — Spokesperson Knowledge panel. Filtered list
     (`?spokesperson=<uuid>`) + `attach` / `detach`
     viewset actions. New `KnowledgePanel` component on
     the spokesperson detail page with per-row toggles.
     **10 API tests + 2 e2e specs.**

- **What's blocking next:** Nothing. SESSION 139 is **K6 —
  render flow integration**. K6 is where the knowledge
  layer stops being storage and starts *informing* renders.

- **What's in a weird state:**
  - `EMBEDDING_FORCE_MOCK=1` must be set in the Django +
    Celery environment for the SPA's knowledge-create flow
    to succeed in local dev without `OPENAI_API_KEY`. The
    pattern matches `RUNWAY_FORCE_MOCK`. Both are
    documented in `00-START-NEXT-SESSION.md`.
  - Postgres carries 495 e2e-generated workspaces from the
    sqlite migration. Cleanup is queued (item #6) but not
    urgent — Postgres doesn't care, and the e2e suite
    creates new ones every run anyway.
  - Background processes left running from the session
    (Django :8000, Celery worker, media-engine :8001,
    Postgres + Redis via docker compose). Kill on
    workstation reboot or `docker compose down` when done.

## Cumulative test counts

| Surface | Count |
|---|---|
| Backend `pytest character_os/prompts/` | 46 |
| Backend `pytest apps/embeddings/tests/` | 56 |
| Backend smoke commands | 6 (incl. new `smoke_ingest`) |
| SPA `pnpm test` (unit) | 3 |
| SPA `pnpm e2e` (Playwright) | 35 (incl. 3 K4 + 2 K5) |
| **Total backend tests** | **102** |
| **Total e2e specs** | **35** |

All green.

---

## What changed (per slice)

### Pre-K1 unblocker — `RUNWAY_FORCE_MOCK=1`

#### `media-engine/app/config.py`

- Added `runway_force_mock: bool = False` to `Settings`.
  Pydantic-settings hydrates from `RUNWAY_FORCE_MOCK` env var
  with the usual truthy parsing (`1`/`true`/`yes`/`on`).
- Updated the `runway_mock` property to return `True` if
  either `runway_force_mock` is set OR `runway_api_key` is
  empty. Real-mode operators can flip mock on for tests
  without stashing `.env`.

#### `media-engine/tests/test_config.py` (new)

Four assertions cover the three Settings states (no key →
mock; key, no force → real; key + force → mock) + default
flag value.

#### `00-START-NEXT-SESSION.md`

The "Real-mode vs. mock-mode" section now documents the
`RUNWAY_FORCE_MOCK=1` override and drops the
`mv .env .env.real` workaround instructions.

### K1 — Postgres + pgvector migration

#### `infra/docker-compose.yml`

Added a `postgres` service using the `pgvector/pgvector:pg16`
image (Postgres 16 + pgvector preinstalled), host port `:5433`
to dodge collisions, persistent volume. Healthcheck via
`pg_isready`. Redis stays put on `:6381`.

#### `shell/pyproject.toml`

Uncommented `pgvector>=0.3`. `psycopg[binary]>=3.2` was
already declared from Phase 1 scaffold; needed re-install in
the venv (the listed packages in `pip list` had been
pyenv-system-installed, not venv-installed).

#### `shell/character_os/settings.py`

- Switched `DATABASES['default']` from sqlite to Postgres,
  reading `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` /
  `DB_PASSWORD` env vars with local-dev defaults matching
  the docker-compose config.
- Added `CACHES['default']` pointing at Redis db 2 via
  `django-redis`. The embedding service (K3) uses this for
  per-text-sha256 cache.
- The Celery broker (db 0) + result backend (db 1) + cache
  (db 2) all ride on the single Redis instance with logical
  DB isolation.

#### `shell/apps/embeddings/migrations/0001_install_pgvector.py` (new)

`CreateExtension('vector')`. Runs first against the embeddings
app, so the K2 schema migrations can use `VectorField`.

#### `shell/apps/conversations/migrations/0002_*.py`

Added explicit dependency on `("embeddings", "0001_install_pgvector")`
so the `vector` extension is available before
`ConversationEmbedding`'s `VectorField` lands. Django's
autodetector doesn't infer cross-app dependencies on its own.

#### `shell/apps/accounts/signals.py`

`ensure_default_workspace` receiver gained a `raw=False`
parameter. Returns early if `raw=True` (the `loaddata`
signal). Without this, loading the sqlite dump into Postgres
collides on `Workspace.slug` because the signal auto-creates
a workspace for every user before `loaddata` gets to insert
the workspace rows from the fixture.

#### `shell/apps/billing/signals.py`

Same `raw=True` guard added to `ensure_default_subscription`
for the same reason (Subscription auto-created on Workspace
post_save collides with the fixture's Subscription rows).

#### `docs/POSTGRES_MIGRATION.md` (new)

Records the K1 migration: what changed, how to bring the
stack up, the one-shot dumpdata/loaddata data path, what's
verified, follow-ups. The old sqlite file at
`shell/db.sqlite3` is untouched as a backup.

### K2 — Knowledge schema + retrieval skeleton

#### `shell/apps/embeddings/models.py` (new — was empty)

- `KnowledgeDocument`: workspace FK (required), spokespeople
  M2M (empty = visible to all), title, document_type
  (text/markdown/pdf/url), raw + processed content,
  content_hash (SHA-256 of processed), source_url,
  source_metadata, ingested_via, status, error_message,
  is_active (soft delete), created_by, timestamps.
  Unique constraint on `(workspace, content_hash)` for
  per-workspace dedup. Indexes on
  `(workspace, is_active)` and
  `(workspace, document_type)`.
  `clean()` validates cross-workspace M2M.
- `KnowledgeChunk`: document FK, chunk_index, chunk_text,
  chunk_size, overlap_size, embedding_vector
  (`VectorField(dimensions=1536)`), embedding_model,
  embedding_dimension, embedding_cost_micros,
  processing_time_ms, timestamps. Unique constraint on
  `(document, chunk_index)`. HNSW index on the vector
  column (`m=16`, `ef_construction=64`,
  `vector_cosine_ops`).
- Module-level constants `EMBEDDING_MODEL_DEFAULT =
  "text-embedding-3-small"` and `EMBEDDING_DIMENSION = 1536`.

#### `shell/apps/embeddings/signals.py` (new)

`m2m_changed` receiver on
`KnowledgeDocument.spokespeople.through`. Fires on `pre_add`
(both forward and reverse). Vetoes any attach where the
spokesperson's workspace differs from the document's
workspace. Raising at `pre_add` aborts the M2M write before
the join row commits. Wired in `apps.py`'s `ready()` hook.

#### `shell/apps/embeddings/retrieval.py` (new)

The single sanctioned consumer of the chunk tables. Two
public functions:

- `retrieve_for_spokesperson(spokesperson, query, top_k=5,
  *, _query_vector=None) -> list[KnowledgeChunk]` — workspace
  filter derived from `spokesperson.workspace`, no override.
  Visibility filter: `Q(spokespeople__isnull=True) |
  Q(spokespeople=spokesperson)`. Cosine distance ordering.
- `retrieve_for_thread(thread, query, top_k_docs=3,
  top_k_history=5, *, _query_vector=None) -> tuple[...]` —
  doc chunks delegated to `retrieve_for_spokesperson`,
  conversation chunks scoped via `message__thread=thread`.
  Returns the two lists separately so prompt assembly can
  visually divide them.

`_embed_query` (private) wires through to the K3 embedding
service when a vector isn't supplied. Tests use the
`_query_vector=...` kwarg to bypass embedding entirely.

#### `shell/apps/conversations/models.py` (extended)

Added `ConversationMessage` (thread FK, role enum
user/spokesperson, content, timestamps) and
`ConversationEmbedding` (message FK, chunk fields,
`VectorField(dimensions=1536)`, HNSW index). Separate
tables from KnowledgeChunk by design — privacy contract
rule 4.

#### `shell/apps/embeddings/admin.py` + `apps/conversations/admin.py`

Admin registrations for the new models. Read-mostly. Vector
columns surface as readonly to avoid huge form payloads.

#### `shell/apps/embeddings/tests/test_retrieval_privacy.py` (new)

The load-bearing 7 privacy tests:

1. `test_cross_workspace_chunk_isolation` — workspace A
   never sees workspace B's chunks even when the workspace-B
   chunk is a perfect vector match.
2. `test_spokesperson_m2m_narrows_visibility_within_workspace`
   — empty M2M = visible to all; M2M = visible only to
   attached spokespeople.
3. `test_cross_thread_conversation_isolation` — thread A
   never sees thread B's embeddings.
4. `test_workspace_anchor_required` — DB-level NOT NULL on
   `KnowledgeDocument.workspace`.
5. `test_m2m_blocks_cross_workspace_spokesperson_attach` —
   the signal vetoes the attach.
6. `test_content_hash_dedup_is_per_workspace` — same hash
   in different workspaces is fine; same hash in the same
   workspace is rejected.
7. `test_only_retrieval_module_queries_chunk_tables` —
   repo-level grep test. Walks `shell/`, flags any
   `KnowledgeChunk.objects` or `ConversationEmbedding.objects`
   usage outside a small `ALLOWED_FILES` list (models, admin,
   retrieval, ingestion, tasks, this test). The grep
   matches `\b(KnowledgeChunk|ConversationEmbedding)\.objects\b`
   — docstring mentions are fine; only actual queryset
   entry points are flagged.

### K3 — Ingestion pipeline

#### `shell/apps/embeddings/text_splitter.py` (new)

Paragraph-first, sentence-fallback splitter ported from
u-d-b's `content/embeddings.py:TextSplitter`. Locked v1
defaults: `chunk_size=1000`, `chunk_overlap=200`. Word-boundary
overlap. `TextChunk` dataclass with `(index, text, size)`.

#### `shell/apps/embeddings/embedding_service.py` (new)

The sole entry point for `text-embedding-3-small` calls.

- `embed(text) -> EmbedResult` with `(vector, model,
  dimension, cost_micros, cached, elapsed_ms)`.
- Redis cache keyed by `sha256(text)` with 30-day TTL.
- `EMBEDDING_FORCE_MOCK=1` env var or
  `settings.EMBEDDING_FORCE_MOCK=True` returns deterministic
  pseudo-vectors. Same shape as `RUNWAY_FORCE_MOCK`.
- Real mode raises `RuntimeError` if `OPENAI_API_KEY` is
  unset — silent fallback would mask production misconfig.
- Cost telemetry: 0.005 micros per character of input
  (text-embedding-3-small at $0.02 / 1M tokens, 4 chars/token).

#### `shell/apps/embeddings/pdf.py` (new)

`pdfminer.six` wrapper. `extract_text(payload)` accepts bytes
or `Path`, returns `(text, page_count)`. Raises
`PdfExtractionError` on empty extracts (scanned/image-only
PDFs — OCR is explicitly out of v1 scope).

#### `shell/apps/embeddings/ingestion.py` (new)

`ingest_text` + `ingest_pdf` orchestrators. Both:

1. Normalise input (Windows line endings, trailing whitespace).
2. Hash + check `(workspace, content_hash)` for dedup. Race
   handled — `IntegrityError` on duplicate insert returns
   the existing row.
3. Create `KnowledgeDocument` row in `status='pending'`.
4. M2M `.set(spokespeople)` — the signal vetoes
   cross-workspace attaches.
5. Return `(document, deduped)` — caller enqueues the
   `embed_document` task only on fresh ingests.

`ingest_pdf` enriches `source_metadata` with
`pdf_page_count` + `pdf_size_bytes`.

#### `shell/apps/embeddings/tasks.py` (new)

`embed_document(document_id, *, chunk_size, chunk_overlap)`
Celery task. Idempotent — re-running wipes existing chunks
and re-creates them. Network-flavored failures retry with
exponential backoff (`max_retries=2`). Permanent failures
flip the doc to `status='failed'` with `error_message`
populated.

#### `shell/apps/embeddings/management/commands/smoke_ingest.py` (new)

End-to-end smoke: `ingest_text` → `embed_document.apply()`
→ `retrieve_for_spokesperson` → assert processed + chunks
exist + retrieval hits the smoke doc + re-ingest dedups
to the same row. Wrapped in a savepoint rollback so the
workspace stays clean. Defaults to
`EMBEDDING_FORCE_MOCK=1`; `--real` flag for real OpenAI.

#### `shell/apps/embeddings/tests/test_text_splitter.py` (new)

6 unit tests covering empty input, short input, paragraph
splits, oversized paragraph sentence-fallback, chunk index
density, invalid init args, zero-overlap behavior.

#### `shell/apps/embeddings/tests/test_embedding_service.py` (new)

6 tests covering empty input, mock vector determinism +
cache hit, different text → different vectors, real-mode
key required, settings override beats env, model constant
locked to text-embedding-3-small.

#### `shell/apps/embeddings/tests/test_ingestion.py` (new)

10 tests covering ingest_text basics, dedup within and
across workspaces, empty content rejection, spokesperson
M2M attach, cross-workspace M2M rejection, full
embed_document pipeline + chunk dimension assertion +
idempotency + missing-doc handling.

### K4 — Workspace knowledge route

#### `shell/apps/embeddings/serializers.py` (new)

`KnowledgeDocumentSerializer` with:

- Write-only inputs: `text_content` (paste) +
  `pdf_data_uri` (base64 data URI) + `spokesperson_ids` (PK
  list for the M2M).
- Read-only outputs include `chunk_count`, `workspace_name`,
  `status`, `content_hash`, all metadata fields.
- `validate()` enforces exclusive-or on `text_content` vs
  `pdf_data_uri` on create; both/neither is a 400.
- Cross-workspace spokesperson check at validation time
  (surfaces a clean 400; the signal is the structural
  fallback).
- PDF data URI validation: strict `data:application/pdf;base64,`
  prefix, ≤10 MB after decode, ≥100 bytes (sanity).
- `create()` branches into `ingest_text` (auto-detecting
  markdown vs plain text via heading-prefix heuristic) or
  `ingest_pdf` based on which payload field is supplied.
  Fires `embed_document.delay()` on fresh ingests; refreshes
  the instance from DB after so eager-Celery test runs see
  the post-task state.
- `update()` only touches title + spokespeople. Content edit
  is reject-by-design — re-ingest if you want.

#### `shell/apps/embeddings/views.py` (new — extended in K5)

`KnowledgeDocumentViewSet(ModelViewSet)` with
`IsWorkspaceMember` permission. Queryset filters by
`workspace__memberships__user=request.user` AND `is_active`.
Supports `?workspace=<uuid>` + `?document_type=<type>` query
params for narrowing. `destroy()` soft-deletes (sets
`is_active=False`). K5 added the `attach`/`detach` actions
(see K5 below).

#### `shell/apps/embeddings/urls.py` (new) + `character_os/urls.py`

DRF router registers `KnowledgeDocumentViewSet` under
`/api/knowledge/`. Wired into the root urls.

#### `shell/apps/embeddings/tests/test_api.py` (new)

16 API integration tests with `EMBEDDING_FORCE_MOCK=True` +
`CELERY_TASK_ALWAYS_EAGER=True` via an autouse fixture.
Covers list scoping, workspace query param, paste create
(text + markdown auto-detect), PDF create (with
`pdfminer.high_level.extract_text` mocked so the test stays
hermetic), exclusive-or validation, PDF format/size
validation, spokesperson attach, cross-workspace
spokesperson rejection, detail get (member + outsider 404),
patch title, patch content edit rejection, soft delete.

#### `web/src/lib/api/knowledge.ts` (new)

zod schemas (`KnowledgeDocument`, list response with
paginated-or-bare tolerance), CRUD functions, React Query
hooks (`useKnowledgeList`, `useKnowledgeDocument`,
`useCreateKnowledge`, `useUpdateKnowledge`,
`useDeleteKnowledge`). Helper `pdfFileToDataUri(file)`
converts a browser `File` to the strict
`data:application/pdf;base64,...` shape. `statusTone()`
maps status enum to a color hint. (K5 added the spokesperson-
filter hook + attach/detach mutations — see K5.)

#### `web/src/routes/workspace/knowledge.tsx` (new)

Workspace knowledge page. Sections:

- Header with back-to-dashboard + title + sub-copy.
- `UploadPanel` with tabs (Paste / Upload PDF) — paste form
  has title + textarea; upload form has title + file input
  with size validation (≤10 MB) and an auto-prefill of the
  title from the filename.
- Documents list with per-row `KnowledgeRow` (icon + title
  + type/chunk-count metadata + error message when failed +
  status pill + soft-delete button with
  `window.confirm()`).
- Empty state when no docs.
- Status polling: list refetches every 3s while any doc is
  in `pending` or `processing`; stops polling once all
  settled.

#### `web/src/App.tsx`

Registered the `/workspace/knowledge` route under
`<RequireAuth>` + Layout.

#### `web/src/routes/dashboard/index.tsx`

Added a "Knowledge" link in the dashboard masthead
(`data-testid="nav-knowledge"`) for discoverability.

#### `web/e2e/workspace-knowledge.spec.ts` (new)

3 specs:

1. Full paste → ingest → status flips to processed →
   delete roundtrip.
2. Paste form submit-disabled when title or content blank.
3. Upload tab reachable + submit-disabled without a file.

### K5 — Spokesperson Knowledge panel

#### `shell/apps/embeddings/views.py` (extended)

- Queryset gained `?spokesperson=<uuid>` filter — visibility
  via `Q(spokespeople__isnull=True) | Q(spokespeople=sp)`.
  Same logic as `retrieve_for_spokesperson` so the SPA
  surface and the render-time RAG see the same docs.
- Two new `@action(detail=True, methods=["post"])`:
  `attach` and `detach`. Body: `{spokesperson_id}`.
  Idempotent. Cross-workspace attaches surface as a 400
  via `m2m_changed` signal translation. Returns the
  updated doc.

#### `shell/apps/embeddings/tests/test_api_k5.py` (new)

10 tests covering filter visibility, cross-workspace filter
exclusion, attach add + idempotent, detach remove +
idempotent, cross-workspace attach rejection, unknown
spokesperson 404, missing payload validation, outsider 404.

#### `web/src/lib/api/knowledge.ts` (extended)

- `useSpokespersonKnowledge(workspaceId, spokespersonId)`
  hook — queryKey scoped to both ids so K4's workspace list
  and K5's per-spokesperson list cache independently.
- `attachSpokesperson(documentId, spokespersonId)` +
  `detachSpokesperson(...)` REST helpers.
- `useToggleSpokespersonAttachment(workspaceId,
  spokespersonId)` mutation that branches on
  `{attach: true|false}` and invalidates all three
  affected query keys.

#### `web/src/components/knowledge-panel.tsx` (new)

Reusable per-spokesperson panel. Filtered list with per-row
`data-visibility` attribute (`workspace-wide` |
`restricted-includes-me` | `restricted-excludes-me` — the
last is defensive; shouldn't appear in this filtered view).
Toggle button label switches between "Make {name}-only"
and "Detach" based on the M2M state. Empty state links to
`/workspace/knowledge`. Same 3s polling pattern as K4.

#### `web/src/routes/spokespeople/$id.tsx`

Added a `<KnowledgePanel>` section to the detail page,
below the videos/setup panels (`--reveal-delay: "0.06s"`).
Visible whether or not the spokesperson is fully configured
— knowledge can attach to a setup-pending spokesperson too.

#### `web/e2e/spokesperson-knowledge.spec.ts` (new)

2 specs (legacy-form path via `?legacy=1` to skip the
wizard's portrait/voice steps):

1. Workspace doc appears in the spokesperson panel with
   `data-visibility="workspace-wide"`. Click "Make
   {name}-only" → flips to `restricted-includes-me`.
   Click Detach → flips back to `workspace-wide`.
2. Empty state visible when no knowledge ingested; link
   points at `/workspace/knowledge`.

---

## Calibration carried forward

- **The grep enforcement test caught real architecture bugs
  during K3.** When I added `ingestion.py` and `tasks.py`
  (which legitimately write `KnowledgeChunk` rows via
  `.objects.create()`), the privacy grep test failed because
  it was matching the bare class name in docstrings too. I
  tightened it to match `\b(<Model>)\.objects\b` and
  expanded `ALLOWED_FILES` for the sanctioned writers. The
  test was working correctly — my coarse pattern surfaced
  noise alongside real signal. **Lesson:** privacy / contract
  tests are valuable in proportion to their false-positive
  rate. Tighten the pattern when noise appears; don't disable
  the test.

- **Signal `raw=True` is mandatory for any auto-creating
  receiver.** Two signals (`accounts.signals` +
  `billing.signals`) silently created child rows on every
  User/Workspace save — fine in normal operation, fatal
  during `loaddata`. The fixture carries those rows already;
  re-creating them collides on unique constraints. Going
  forward: every new `@receiver(post_save)` that creates
  related rows must include `raw=False` in its signature and
  bail when `raw=True`. The signal pattern is invisible until
  loaddata exposes it.

- **`refresh_from_db()` after a `delay()` call inside a
  serializer create gives accurate state in tests + correct
  state in production.** In eager-Celery test mode, the
  embedding task completes inline; without the refresh, the
  serializer's instance reference is stale (status still
  `pending`). In real-Celery production, the refresh is a
  no-op — the worker hasn't picked the task up yet — but
  the cost is one extra SELECT, which is negligible. Pattern
  worth applying anywhere a serializer fires an async task
  that mutates the same row.

- **The migration cross-app dependency Django doesn't infer.**
  `apps.conversations.0002` uses `pgvector.VectorField` but
  `apps.embeddings.0001_install_pgvector` is what creates
  the `vector` Postgres type. Django's autodetector doesn't
  add cross-app migration dependencies for type-level
  uses — only for `ForeignKey`-style references. The test
  database failed mid-migration until I added an explicit
  `("embeddings", "0001_install_pgvector")` dependency to
  conversations 0002. Lesson: if app A's migrations depend
  on a Postgres extension app B installs, you must declare
  the dependency yourself.

- **Pacing observation: six slices in one session is the
  edge of sustainable.** Each slice added real surface area
  (models, tests, UI, e2e) but also benefited from the
  scope-lock work in SESSION 137 — the design was already
  done, so the implementation flowed without backtracking.
  The clear sequencing (K1 infra → K2 schema → K3 pipeline
  → K4 surface → K5 filtered view) meant later slices
  reused earlier work cleanly. **Future arcs**: scope-lock
  + slice breakdown the day before implementation, then
  execute. The compounding velocity comes from the design
  being locked, not from working faster.

---

## Queued investigations (priority-ordered)

Knowledge arc remains in `docs/design/KNOWLEDGE_LAYER.md`
§"Slice breakdown."

1. **K6 — Render flow integration.** Where knowledge starts
   *informing* renders. New `script_synthesis.py` with
   `build_render_brief(spokesperson, prompt) -> str`. RAG +
   LLM call. `RENDER_SCRIPT_FORCE_MOCK=1` flag for dev.
   Citation logging on `Video` row. Touches existing
   `apps/videos/views.py` — higher regression risk than
   K4/K5.
2. **K7 — URL ingestion + serper discovery.** `trafilatura`
   fetch+extract. Serper search tab on workspace upload.
   Both flow into the same Celery embedding task.
3. **K8 — Conversation models** (already shipped as part of
   K2; this slice adds the message-receive pipeline +
   conversation embedding signal handler).
4. **K9 — Conversation REST + SPA.** `POST messages`
   endpoint, thread view, spokesperson detail
   "Conversations" tab.
5. **K10 — Onboarding seed.** `seed_workspace_knowledge`
   task. `docs/seeds/character_os/*.md` corpus. Trigger
   on `is_operator=True` workspace creation.
6. **E2e detritus cleanup** — `Workspace.objects.filter(slug__startswith='e2e-').delete()`
   when the operator decides the window is right.
7. **Voice preset audit** — happens naturally once first
   real-mode knowledge-informed renders land (post-K6).
8. **First marketing video** — happens naturally once K6
   lands.
9. **W11.1 — Edit-spokesperson modal.**
10. **W12 — Legacy form retirement.**
11. **Cast sync command** — pull updates from
    `spokesperson_templates.py` into existing rows.
12. **Tier 2 prompt helpers** — likely subsumed by K6's
    `script_synthesis.synthesize()`.
13. **Stuck-row janitor.**
14. **Additional video kinds** — cinematic / dialogue / long_ad.
15. **Act-Two performance capture.**
16. **`lesson` video kind.**
17. **Real Google OAuth + dj-stripe.**
18. **Allauth legacy-settings cleanup.**
19. **smoke_voice / smoke_avatar transaction discipline.**
20. **Drift verifier** (`verify_doc_claims --only-drift`).
21. **Brand Identity v2 + dark mode.**

---

## AI Notes

- **Memory hits that informed this session:** SESSION 137
  saved `feedback_cast_is_example_data.md` (cast are seed
  examples, not product shape) and
  `project_hackathon_knowledge_leak.md` (the prior
  cross-context leak that motivated K2's privacy
  guarantees). Both stayed load-bearing throughout — when
  K5's M2M toggle UX was being designed, the
  "spokespeople are universal" framing kept me from
  writing per-cast-member logic.

- **The operator pushed back exactly once mid-session, on
  the embedding cost guard.** I had proposed a per-workspace
  upload cap as a "medium-severity" concern. Operator
  corrected with empirical data ("3-hour YouTube videos
  cost cents"). I re-did the math and was off by ~20×.
  Replaced the cost-cap concern with the
  port-the-content-hash-dedup requirement, which u-d-b
  already had and we needed anyway. **Pattern:** when
  pushing back, take the operator's "I've actually
  measured this" beats my "let me reason about the upper
  bound." The earlier calibration memory about asking for
  prior art continues to apply.

- **What made the velocity possible:** scope-lock had
  removed every meaningful design decision before
  implementation. Each slice was "build the thing the doc
  says" — no mid-slice debates about shape. Even where
  small decisions arose (M2M-via-`?spokesperson=` query
  param vs nested URL; tab UI vs panel section on the
  detail page), the project's existing conventions made
  the choice clear within seconds.

- **What I'd do differently next time:** the e2e specs
  added near the end of each slice would have caught some
  serializer + view issues earlier if written *before* the
  unit tests. K4's "PDF status was pending in response"
  bug, for instance, would have been caught by the e2e
  spec one assertion earlier than the unit-test
  refactor. Future arcs: write the e2e first, then unit
  tests, then implementation — the e2e is the contract
  the user sees.

- **The render flow integration (K6) is the most
  consequential slice in the arc.** Everything before it is
  storage. K6 is where Riggs starts saying things about
  *your* product because *you* taught him. Worth treating
  with the same care as K2's privacy guarantees — what
  goes into the LLM prompt at render time is the surface
  area an operator will judge the whole knowledge layer by.
