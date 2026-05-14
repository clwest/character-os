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
> **Last handoff:** `docs/handoffs/SESSION_138_K1_THROUGH_K5.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete (W1-W11). Cast went live in
real-mode (SESSION 136). Knowledge-layer scope-locked
(SESSION 137) — `docs/design/KNOWLEDGE_LAYER.md` is the new
contract.

**Phase 4 (knowledge arc):** K6 — render flow integration.
K1-K5 all shipped SESSION 138. K6 is where knowledge starts
*informing* video renders rather than just sitting in
storage.

| Slice | Deliverable                                  | Status |
|-------|----------------------------------------------|--------|
| W1-W11 | Create-spokesperson wizard end-to-end       | DONE (SESSIONS 124-134) |
| Cast Live | generate_cast + seed_cast + bugs fixed   | DONE (SESSION 136) |
| K0 | Knowledge-layer scope lock                      | DONE (SESSION 137) |
| K1 | Postgres + pgvector migration                   | DONE (SESSION 138) |
| K2 | KnowledgeDocument + KnowledgeChunk + retrieval skeleton | DONE (SESSION 138) |
| K3 | Ingestion pipeline (paste + upload + PDF)       | DONE (SESSION 138) |
| K4 | Workspace knowledge route (SPA + REST)          | DONE (SESSION 138) |
| K5 | Spokesperson "Knowledge" tab                    | DONE (SESSION 138) |
| K6 | Render flow integration                         | **NEXT** |
| K3 | Ingestion pipeline (paste + upload + PDF)       | Queued |
| K4 | Workspace knowledge route (SPA + REST)          | Queued |
| K5 | Spokesperson "Knowledge" tab                    | Queued |
| K6 | Render flow integration                         | Queued |
| K7 | URL ingestion + serper discovery                | Queued |
| K8 | ConversationMessage + ConversationEmbedding     | Queued |
| K9 | Conversation REST + SPA                         | Queued |
| K10 | Onboarding seed                                | Queued |
| W12 | Legacy single-form retirement                  | Whenever (now ungated) |
| W11.1 | Edit-spokesperson modal                      | Queued |

**Cast roster in workspace `admins-workspace`:**

  - Riggs the Donkey (founder voice) — id `06bf999f-...`
  - Sasha the Raccoon (sales) — id `79d48883-...`
  - Donny the Sloth (user stories) — id `f30b2980-...`
  - Maya the Panda (educator) — id `9410f23f-...`

Cast can render videos right now. After K6 ships they'll
render *informed* videos — script synthesis with RAG-injected
knowledge instead of LLM hallucination from the brief alone.

---

## SESSION 138 status — K1 through K5 all shipped

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

**Test counts: 56 K-tests** (7 privacy + 6 splitter + 6
embedding service + 10 ingestion + 16 K4 API + 10 K5 API + 1
grep). Plus 46 prompts pytest = **102 backend tests**.
**35 e2e specs** (30 wizard/etc + 3 K4 + 2 K5).

### Next: K6 — render flow integration

K6 is where the knowledge layer stops being inert storage
and starts *informing* video renders. Per the scope-lock doc
§"Render flow integration":

- New `shell/character_os/script_synthesis.py` (or similar):
  `build_render_brief(spokesperson, operator_prompt) -> str`.
  Calls `retrieve_for_spokesperson` with the operator's
  prompt, injects top-k chunks into an LLM call, returns a
  synthesized brief string.
- Wire `build_render_brief` into `apps/videos/views.py`
  (or the equivalent ingestion path) just before the
  `MediaEngineClient.create_video()` call. The
  media-engine contract stays unchanged — it still
  receives a finished `brief` string.
- LLM provider — figure out what shell already uses
  (probably OpenAI gpt-4o-mini per media-engine's default).
  Add `RENDER_SCRIPT_FORCE_MOCK=1` for dev (deterministic
  brief = `f"{spokesperson.business_brief}\n\n{prompt}\n\n[knowledge: {len(chunks)} chunks]"`).
- Graceful degradation: if `retrieve_for_spokesperson`
  returns 0 chunks, skip the synthesis step entirely and
  use the existing `brief or business_brief` fallback.
  Contract rule 6.
- Citation logging: persist which chunks fed which render
  on the `Video` row (probably a new
  `Video.knowledge_chunk_ids = JSONField`). No UI in v1.

### What's NOT K6

- URL/serper discovery — K7.
- Conversation surface — K8/K9.
- Onboarding seed — K10.

### How to run all K tests

```bash
cd shell && source .venv/bin/activate
python -m pytest apps/embeddings/tests/ -v   # 56 K-tests
EMBEDDING_FORCE_MOCK=1 python manage.py smoke_ingest  # end-to-end

cd ../web
pnpm test                                       # 3 SPA unit
pnpm e2e --grep 'knowledge'                     # K4 + K5 specs (5 tests)
```

If any of these fail during K6+, the load-bearing privacy or
ingestion contract has broken. Fix the implementation, not
the tests.

**To run Celery + Django with the embedding mock active for
local SPA development:**

```bash
EMBEDDING_FORCE_MOCK=1 python manage.py runserver 8000
EMBEDDING_FORCE_MOCK=1 celery -A character_os worker --pool=solo
```

The `EMBEDDING_FORCE_MOCK` flag was added in K3 — same shape
as `RUNWAY_FORCE_MOCK`. Without it, the embedding step needs
`OPENAI_API_KEY`.

---

## Queued investigations (priority-ordered)

Knowledge-layer arc (K-prefixed) is locked in
`docs/design/KNOWLEDGE_LAYER.md` §Slice breakdown. Everything
else is ordered by independence + priority.

1. **K6 — Render flow integration.** Knowledge starts
   *informing* renders here.
2. **K7 — URL ingestion + serper discovery.**
3. **K8 — Conversation models.**
4. **K9 — Conversation REST + SPA.**
5. **K10 — Onboarding seed.**
6. **E2e detritus cleanup** — Postgres carries 495
   e2e-generated workspaces; `Workspace.objects.filter(slug__startswith='e2e-').delete()`
   when the operator decides the window is right.
7. **Voice preset audit** — naturally happens post-K6.
8. **First marketing video** — naturally happens post-K6.
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
python -m pytest apps/embeddings/tests/       # 46 K-tests (privacy + ingestion + splitter + embedding service + API)
EMBEDDING_FORCE_MOCK=1 python manage.py smoke_ingest    # end-to-end ingest → embed → retrieve

# SPA (from web/, in mock mode only)
pnpm test
pnpm e2e            # full lifecycle ~50s (30 specs), single-shot
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

- Last session: SESSION 138 — **K1 + K2 + K3 + K4 + K5** all
  shipped same session. Pre-K1 `RUNWAY_FORCE_MOCK=1` unblocker
  and two `raw=True` signal guards (`accounts.signals`,
  `billing.signals`) rode along. K3 added the
  `EMBEDDING_FORCE_MOCK=1` flag mirroring the runway-mock
  pattern. K4 shipped `/workspace/knowledge` (paste + PDF
  upload, polling, soft delete, dashboard link). K5 shipped
  the per-spokesperson Knowledge panel on the detail page with
  attach/detach toggles. **Cumulative tests: 102 backend
  pytest, 35 e2e specs, all green.**
- **Calibration carried forward:**
  - **Cast is example data, not product shape.** When
    discussing capabilities, ask "is this true of every
    spokesperson, or just this one's framing?" Capabilities
    live on the model; framing lives in `business_brief`.
  - **Ask for prior art before grading severity on
    hypotheticals.** The operator caught two of my
    hypotheticals (cost-cap concern, "Maya tutor-mode" axis)
    with concrete prior knowledge. Default forward to: surface
    a concern, ask "is this hypothetical or have you seen
    this happen," then size accordingly.
  - **Push back when framing looks wrong.** Three times in
    SESSION 137 this caused convergence rather than friction.
    Continue.
- **The knowledge layer is K1-K10.** Don't try to ship in one
  session. Wizard was 11 slices; knowledge layer is on par.
  Pace accordingly.
- **K1 ships nothing visible.** That's by design. Don't try
  to bundle a "small UI improvement" into the migration slice
  — keep K1 surgical.
- **Privacy guarantees from K0 are load-bearing.** When K2
  lands the schema, the three named tests
  (`test_cross_workspace_chunk_isolation`,
  `test_cross_thread_conversation_isolation`,
  `test_only_retrieval_module_queries_chunk_tables`) are part
  of the deliverable, not optional.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
