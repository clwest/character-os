---
title: "Knowledge Layer — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-05-14 (SESSION 137)
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "SPA_ARCHITECTURE.md"
  - "MEDIA_ENGINE_INTERNAL_API.md"
  - "CREATE_SPOKESPERSON_WIZARD.md"
phase: 4
---

# Knowledge Layer

> **Read first:** `CREATE_SPOKESPERSON_WIZARD.md` (the prior
> scope-lock pattern this doc follows), `UI_REDESIGN_V2.md` §4
> (data model + Phase 1 scaffold), and the SESSION 136 handoff
> (cast went live; the framing problem this doc resolves).
>
> **Prior art:** `unified-donkey-betz/content/models.py` +
> `unified-donkey-betz/content/embeddings.py` —
> the production RAG pipeline this doc ports selectively.
> `unified-donkey-betz/core/conversation_memory.py` — the
> conversation-embedding pattern. `unified-donkey-betz/core/rag_integration.py` —
> the namespace-based scoping pattern we are explicitly **not**
> porting (separate-table is the character-os shape).

---

## Purpose

The cast went live in SESSION 136 — Riggs, Sasha, Donny, and Maya
exist in `admins-workspace` as real `Spokesperson` rows with
Runway-bound avatars and voice presets. They can render videos
right now, but they have **nothing to talk about**: each
spokesperson's `business_brief` describes *how* they sound, not
*what* they know about Character OS or any other product. Every
render today is the LLM hallucinating product details from the
operator's prompt plus the spokesperson's tone.

The knowledge layer fills that gap. It is the persistent,
queryable, per-workspace store of facts each spokesperson can
draw on at render time and at conversation time. It is the
foundation for two universal capabilities on every
spokesperson — **render** (the working video pipeline) and
**converse** (the `ConversationThread` shell that has no UI
yet).

### Why scope-lock first

The knowledge layer touches every load-bearing piece of the
platform: database engine (forces Postgres + pgvector), media
engine (changes what shell hands it), every spokesperson
detail page, a new workspace-level route, and the render
pipeline itself. Multi-tenant privacy guarantees must be
correct by construction — there is a real prior incident in
the runway-hackathon predecessor where an avatar leaked
context (referenced `context-kit` instead of staying on the
hackathon platform). Locking the surface area before any code
lands keeps the implementation slices honest.

This doc plays the same role for the knowledge layer that
`SPA_ARCHITECTURE.md` plays for the SPA and
`CREATE_SPOKESPERSON_WIZARD.md` plays for the wizard arc —
locks shape, not implementation.

---

## Contract rules (load-bearing)

These bind every knowledge-layer slice the same way
`MEDIA_ENGINE_INTERNAL_API.md`'s rules bind every media-engine
endpoint.

1. **Every knowledge artifact has an explicit workspace
   anchor.** `KnowledgeDocument.workspace` is a required FK
   (DB-level NOT NULL). Workspace is never derivable through
   M2M relations or inferred from the requesting user — it is
   stored on the row.

2. **Retrieval flows through exactly two named functions.**
   `apps/embeddings/retrieval.py` exposes
   `retrieve_for_spokesperson()` and `retrieve_for_thread()`.
   No code outside that module imports the chunk-level models.
   A repo-level test enforces this.

3. **Workspace scoping is unconditional.** Both retrieval
   functions take a `spokesperson` or `thread` argument and
   derive the workspace filter from it. There is no
   `workspace=None` opt-out parameter, no `bypass_filter`
   admin flag, no `is_superuser` shortcut. The leak shape is
   *any* code path that returns chunks without a workspace
   filter; that shape must not exist.

4. **Documents and conversation turns live in separate
   tables.** `KnowledgeDocument` + `KnowledgeChunk` for
   intentional uploaded knowledge. `ConversationMessage` +
   `ConversationEmbedding` for chat artifacts. The separation
   is structural, not discriminated — the leak shape (a
   conversation turn surfacing as workspace knowledge) is
   eliminated by schema, not by filter.

5. **Content-hash dedup at ingest.** Every document carries a
   SHA-256 of its processed content. Unique constraint on
   `(workspace, content_hash)` means re-ingesting the same
   content is idempotent. Re-embedding loops cost zero.

6. **Render degrades gracefully on empty knowledge.** If a
   spokesperson has no documents attached (and no workspace
   docs are visible to it), the render flow runs the
   pre-knowledge-layer path — operator's prompt plus
   `business_brief`, no RAG injection. Knowledge enhances
   renders; it does not gate them.

7. **No cross-workspace knowledge sharing in v1.** Each
   workspace has its own corpus. There is no "marketplace,"
   no "public knowledge base," no "templates that ship with
   pre-ingested docs across workspaces." The seed corpus
   (§"Onboarding seed") is per-workspace ingested at workspace
   creation, not a shared reference.

---

## Framing corrections (carried from SESSION 137 conversation)

Two framings the initial start-here doc used that this doc
explicitly supersedes:

- **The "Maya tutor-mode" framing is gone.** The cast members
  are example data, not product features. Every spokesperson
  has the same two universal capability surfaces: **render**
  (today) and **converse** (this arc). The knowledge layer
  feeds both uniformly. There is no Maya-specific code path,
  no "tutor mode" enum, no special-casing.

- **The "per-spokesperson vs per-workspace vs hybrid" framing
  is gone.** It read as three options; in practice only one
  shape doesn't fork the system: workspace-level
  `KnowledgeDocument`, optional per-spokesperson visibility
  via M2M. Empty M2M = visible to all spokespeople in the
  workspace.

---

## Data model

### `KnowledgeDocument`

```python
class KnowledgeDocument(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)

    # The load-bearing anchor — required, never null
    workspace = ForeignKey(
        Workspace, on_delete=CASCADE,
        related_name='knowledge_documents',
    )

    # Visibility filter — empty M2M = visible to all spokespeople in workspace
    spokespeople = ManyToManyField(
        Spokesperson, related_name='knowledge_documents', blank=True,
    )

    # Identity
    title = CharField(max_length=500)
    document_type = CharField(
        max_length=20,
        choices=[
            ('text', 'Plain Text'),
            ('markdown', 'Markdown'),
            ('pdf', 'PDF'),
            ('url', 'Web Page'),
        ],
    )

    # Content
    raw_content = TextField()           # as-ingested
    processed_content = TextField()     # cleaned, chunkable
    content_hash = CharField(max_length=64, db_index=True)
                                        # SHA-256 of processed_content

    # Ingestion provenance
    source_url = URLField(blank=True)   # for document_type='url'
    source_metadata = JSONField(default=dict)
                                        # serper search query, PDF page count, etc.
    ingested_via = CharField(
        max_length=20,
        choices=[
            ('paste', 'Paste'),
            ('upload', 'Upload'),
            ('serper', 'Serper Discovery'),
            ('seed', 'Onboarding Seed'),
        ],
    )

    # Lifecycle
    status = CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('processed', 'Processed'),
            ('failed', 'Failed'),
        ],
        default='pending',
    )
    error_message = TextField(blank=True)
    is_active = BooleanField(default=True)  # soft delete

    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['workspace', 'content_hash'],
                name='knowledge_unique_workspace_content',
            ),
        ]
        indexes = [
            Index(fields=['workspace', 'is_active']),
            Index(fields=['content_hash']),
            Index(fields=['workspace', 'document_type']),
        ]
```

**Cross-workspace spokesperson check** runs on save and on
M2M change. A spokesperson on the M2M whose `workspace_id`
differs from the document's raises `ValidationError`.

### `KnowledgeChunk`

```python
class KnowledgeChunk(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    document = ForeignKey(
        KnowledgeDocument, on_delete=CASCADE, related_name='chunks',
    )

    chunk_index = PositiveIntegerField()
    chunk_text = TextField()
    chunk_size = PositiveIntegerField()  # characters
    overlap_size = PositiveIntegerField(default=0)

    # pgvector — 1536 for text-embedding-3-small
    embedding_vector = VectorField(dimensions=1536)
    embedding_model = CharField(max_length=100,
                                 default='text-embedding-3-small')
    embedding_dimension = PositiveIntegerField(default=1536)

    # Cost tracking (per-chunk, summed in admin)
    embedding_cost_micros = PositiveIntegerField(default=0)
    processing_time_ms = PositiveIntegerField(null=True, blank=True)

    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('document', 'chunk_index')]
        indexes = [
            Index(fields=['document', 'chunk_index']),
            HnswIndex(
                name='knowchunk_vec_hnsw_idx',
                fields=['embedding_vector'],
                m=16, ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]
```

### `ConversationMessage`

The existing `apps/conversations/models.py` already has
`ConversationThread`. This adds messages.

```python
class ConversationMessage(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    thread = ForeignKey(
        ConversationThread, on_delete=CASCADE, related_name='messages',
    )
    role = CharField(
        max_length=20,
        choices=[('user', 'User'), ('spokesperson', 'Spokesperson')],
    )
    content = TextField()
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['thread', 'created_at']
        indexes = [
            Index(fields=['thread', 'created_at']),
        ]
```

### `ConversationEmbedding`

```python
class ConversationEmbedding(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    message = ForeignKey(
        ConversationMessage, on_delete=CASCADE, related_name='embeddings',
    )

    chunk_index = PositiveIntegerField()
    chunk_text = TextField()
    chunk_size = PositiveIntegerField()

    embedding_vector = VectorField(dimensions=1536)
    embedding_model = CharField(max_length=100,
                                 default='text-embedding-3-small')

    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('message', 'chunk_index')]
        indexes = [
            HnswIndex(
                name='convemb_vec_hnsw_idx',
                fields=['embedding_vector'],
                m=16, ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]
```

---

## Retrieval surface

`apps/embeddings/retrieval.py` exposes exactly two functions.
This is the entire RAG API for character-os.

```python
def retrieve_for_spokesperson(
    spokesperson: Spokesperson,
    query: str,
    top_k: int = 5,
) -> list[KnowledgeChunk]:
    """The ONE doc-retrieval entry point.

    Workspace filter is unconditional and derived from the
    spokesperson argument. No bypass parameter exists.
    """
    query_embedding = embedding_service.embed(query)
    return list(
        KnowledgeChunk.objects.filter(
            document__workspace=spokesperson.workspace,
            document__is_active=True,
            document__status='processed',
        ).filter(
            Q(document__spokespeople__isnull=True) |
            Q(document__spokespeople=spokesperson),
        ).distinct().annotate(
            distance=CosineDistance('embedding_vector', query_embedding),
        ).order_by('distance')[:top_k]
    )


def retrieve_for_thread(
    thread: ConversationThread,
    query: str,
    top_k_docs: int = 3,
    top_k_history: int = 5,
) -> tuple[list[KnowledgeChunk], list[ConversationEmbedding]]:
    """The ONE conversation-retrieval entry point.

    Returns (doc_chunks, history_chunks) so prompt assembly
    can present them visually separated in the LLM prompt.
    Conversation history is scoped to THIS thread only.
    """
    doc_chunks = retrieve_for_spokesperson(
        thread.spokesperson, query, top_k=top_k_docs,
    )

    query_embedding = embedding_service.embed(query)
    history_chunks = list(
        ConversationEmbedding.objects.filter(
            message__thread=thread,
        ).annotate(
            distance=CosineDistance('embedding_vector', query_embedding),
        ).order_by('distance')[:top_k_history]
    )

    return doc_chunks, history_chunks
```

### Repo-level enforcement test

```python
# tests/test_retrieval_isolation.py

def test_only_retrieval_module_queries_chunk_tables():
    """No code outside apps/embeddings/retrieval.py imports the
    chunk-level models. This is the privacy guarantee."""
    forbidden_imports = {'KnowledgeChunk', 'ConversationEmbedding'}
    allowed_files = {'apps/embeddings/retrieval.py',
                     'apps/embeddings/models.py',
                     'apps/embeddings/admin.py',
                     'apps/conversations/models.py'}
    # walk repo, grep for forbidden_imports, assert all hits in allowed_files
```

---

## Ingestion pipeline

Mirrors u-d-b's `content/embeddings.py:RAGSystem.process_document_for_rag_sync`
with the workspace-anchor + content-hash dedup gates added.

### Flow (one document)

1. Operator submits a doc (paste / upload / serper-pick / seed).
2. Server normalizes:
   - `text` / `markdown`: trim, normalize line endings.
   - `pdf`: extract text via `pdfminer.six`. Text-based PDFs
     only in v1; scanned PDFs / OCR is out of scope.
   - `url`: fetch via httpx, extract main content via
     `trafilatura` (or `readability-lxml` as fallback). Strip
     nav / ads / footer. Snapshot the extracted text at
     ingest time. **No re-fetch ever** (URL freshness
     contract — see below).
3. Compute `content_hash = sha256(processed_content)`.
4. Check `(workspace, content_hash)` uniqueness. If duplicate,
   return the existing document — idempotent.
5. Create `KnowledgeDocument` row with `status='pending'`.
6. Enqueue Celery task `embed_document(document_id)`.
7. Task: chunk with `TextSplitter(chunk_size=1000, chunk_overlap=200)`,
   embed each chunk via `embedding_service` (Redis-cached),
   persist `KnowledgeChunk` rows. On success, set
   `status='processed'`. On failure, set `status='failed'`
   with `error_message` populated.

### Conversation embedding flow

When a `ConversationMessage` is created (user OR spokesperson
role), a post-save signal enqueues `embed_conversation_message(message_id)`.
Task chunks the content (smaller chunks — `chunk_size=500` is
likely right for chat-length text, but lock the number in the
first slice that lands), embeds, persists `ConversationEmbedding`
rows. No content_hash dedup on conversation turns (every turn
is unique by definition).

### Embedding service

Port u-d-b's `core/services/embedding_service.py`:
- OpenAI `text-embedding-3-small` only in v1 (locked).
- Redis cache keyed by `sha256(text)` — same text never
  re-embedded across documents within cache TTL.
- Per-call cost tracked in `embedding_cost_micros` on the chunk.
- Graceful degradation: if the embedding API fails, the
  document goes to `status='failed'` with the error preserved
  — no half-embedded documents in the corpus.

---

## Operator surfaces

Two surfaces. The workspace route is the system-of-record;
the spokesperson tab is a filtered view.

### `/workspace/knowledge` (workspace-level)

The canonical CRUD surface for all knowledge in a workspace.

- **List**: all documents in this workspace, paginated,
  filterable by `document_type`, `ingested_via`, attached
  spokespeople. Shows: title, type, attached-spokesperson
  count, chunk count, ingested-at.
- **Upload**: tabbed input — Paste / Upload PDF / Paste URL /
  Search the web. Search tab uses serper; results render as a
  list of `{title, url, snippet}` with an Ingest button per
  row.
- **Detail**: read-only view of the processed content,
  per-spokesperson attach/detach controls (M2M editor),
  re-ingest button, soft-delete button.
- **Empty state**: prompts operator to seed (links to the
  Onboarding Seed control if eligible — see §"Onboarding seed").

### Spokesperson detail page — "Knowledge" tab

A new tab alongside the existing identity / video / voice
panels. Shows:

- Documents currently visible to *this* spokesperson (i.e.,
  workspace docs where `spokespeople__isnull=True` OR
  `spokespeople=this_spokesperson`).
- Per-row attach/detach affordance ("Make this Riggs-only" /
  "Make this workspace-wide").
- Inline "Attach existing doc" search (autocompletes against
  workspace knowledge).
- "Upload new doc" button that routes to the workspace upload
  flow with this spokesperson pre-attached.

The tab is a filtered view, not a separate store. Edits go
through the workspace API.

---

## Render flow integration

Today: shell builds `brief` = operator's typed input OR
spokesperson's `business_brief` fallback → sends to
`/internal/video/`. No LLM script-generation step.

After this arc: shell gains a script-generation step
**before** the media-engine call. The contract with
media-engine does not change.

### New step in shell (location TBD by implementation slice)

```python
def build_render_brief(spokesperson, operator_prompt: str) -> str:
    """Assemble the brief that gets sent to media-engine.
    Uses RAG when knowledge is available; falls back to
    pre-knowledge-layer behavior when empty."""

    chunks = retrieve_for_spokesperson(
        spokesperson, query=operator_prompt, top_k=5,
    )

    if not chunks:
        # Empty-knowledge graceful degradation (contract rule 6)
        return operator_prompt or spokesperson.business_brief

    # Otherwise: LLM-assemble a script using prompt + tone + chunks
    return script_synthesis.synthesize(
        operator_prompt=operator_prompt,
        spokesperson=spokesperson,
        knowledge_chunks=chunks,
    )
```

The synthesized brief gets logged as a citation record on
the video row (which chunks fed which render) — no UI in v1
but the audit data is captured.

### Why shell, not media-engine

Confirmed during scope-lock: `media-engine/app/routers/internal.py`
receives `body.brief` as a pre-built string and passes it to
Runway. Adding RAG + script synthesis in shell is an
**addition**, not a refactor of the contract. Media-engine
stays a dumb pipe to Runway.

---

## Conversation flow integration

`ConversationThread` exists; messages and an SPA surface do
not. This arc adds:

- `POST /api/conversations/threads/{thread_id}/messages/`
  with `role='user'` + `content`. Creates the message,
  enqueues its embedding, fires retrieval, synthesizes the
  spokesperson's reply via LLM, persists that as a second
  message with `role='spokesperson'`, returns both.
- WebSocket or SSE stream variant if the latency feels long
  — defer the streaming decision to the implementation slice.
- SPA surface: a "Conversations" tab on the spokesperson
  detail page, plus a `/conversations/{thread_id}` route for
  a focused chat view.

Same scope rules: messages exist in a thread, embeddings
exist on messages, retrieval filters by thread. Cross-thread
bleed is structurally impossible.

---

## URL freshness contract

- Snapshot extraction at ingest. Never re-fetch.
- If the operator wants fresh content from a URL, they
  delete and re-ingest. No "refresh" button in v1.
- The contract is documented next to the URL input ("we'll
  store the content of this page as it looks today —
  re-ingest later if it changes").

Rationale: re-fetch introduces non-determinism, anti-bot
failures over time, and silent knowledge drift (the
spokesperson saying different things on the same prompt week
to week). Snapshot is honest about its trade-off.

---

## Onboarding seed

When a workspace is created with `Workspace.is_operator=True`
(needs adding to the workspace model; defaults to False), a
post-save signal enqueues `seed_workspace_knowledge(workspace_id)`.
The task ingests a fixed set of markdown files into the
workspace as `ingested_via='seed'`.

- **Source**: `docs/seeds/character_os/*.md` — a curated set
  of Character OS reference docs (what the product is, how
  spokespeople work, pricing, etc.).
- **Trigger**: workspace creation only. Not on subsequent
  doc edits. If the seed corpus updates, operators
  re-ingest manually via the workspace knowledge UI.
- **Idempotent**: each seed doc has a stable content_hash;
  re-running the seed task is a no-op via the
  `(workspace, content_hash)` unique constraint.
- **Customer workspaces** (`is_operator=False`): no seed.
  Customers bring their own knowledge.

The seed corpus is hand-curated, not auto-generated from
the codebase. Treat each seed doc as a piece of marketing
+ product copy — the spokesperson's voice depends on this
quality.

---

## Migration: K1 — Postgres + pgvector

pgvector is non-negotiable. This forces character-os off
sqlite. K1 is the first knowledge-layer slice and produces
**zero user-visible value** — it is pure infra. We name this
explicitly so neither operator nor AI gets demoralized
mid-slice.

### Scope of K1

- Add `postgres:16` + `pgvector/pgvector:pg16` service to
  `infra/docker-compose.yml`.
- Switch Django `DATABASES['default']` to Postgres.
- Install `psycopg[binary]`, `pgvector`, `pgvector.django`.
- Apply pgvector extension as a Django migration.
- `dumpdata` from sqlite → `loaddata` into Postgres. Handle
  any type-coercion failures inline (the existing data is
  small — admin user, admins-workspace, 4 cast members,
  bound avatars/portraits/voices).
- Update smoke commands + e2e to point at Postgres.
- Update `00-START-NEXT-SESSION.md` "How to bring the stack
  up locally" with the new docker compose command.
- Documentation: a `docs/POSTGRES_MIGRATION.md` short note
  explaining the local-dev change.

K1 ships when `python manage.py check`, every smoke
command, the prompts test suite, and the e2e suite all pass
against Postgres. No knowledge-layer schema yet — that's K2.

---

## Slice breakdown

Like the wizard arc, the knowledge layer is a sequence of
slices that can land independently. Recommended order:

- **K1 — Postgres + pgvector migration.** Infra-only.
  Forcing function for everything downstream.
- **K2 — `KnowledgeDocument` + `KnowledgeChunk` models +
  retrieval module skeleton.** Schema + the two named
  retrieval functions (working, tested, but no ingestion
  pipeline yet). Repo-level isolation test lands here.
- **K3 — Ingestion pipeline (paste + upload + PDF).**
  Celery task, `TextSplitter`, embedding service, content-hash
  dedup. Admin-only CRUD endpoints — no SPA yet.
- **K4 — Workspace knowledge route (SPA + REST).**
  `/workspace/knowledge` page. Paste / Upload / Detail / Soft
  delete. M2M attach affordance.
- **K5 — Spokesperson "Knowledge" tab.** Filtered view of
  workspace docs visible to that spokesperson. Inline attach
  / detach.
- **K6 — Render flow integration.** `build_render_brief()`
  in shell. Citation logging on video rows. Graceful
  degradation when knowledge is empty.
- **K6.3 — Brief length cap (~15 min).** Truncate the
  synthesized brief to ≤2000 chars before it leaves
  `script_synthesis.py`. Currently queued.
- **K6.4 — Post-synthesis claim verifier. ✓ SHIPPED
  SESSION 160.** Discovered SESSION 159 via the SESSION
  158 Donny render fact-check (TRUST_CALIBRATION
  2026-05-15 entry "AI confidently wrong (K6
  hallucination)"). Problem: the K6 system prompt at
  `script_synthesis.py:249` says *"Use facts only from
  the knowledge chunks the user supplies. Do not invent
  product details, prices, or features. If a fact
  isn't in the chunks, leave it out."* — `gpt-5-mini`
  ignores this when it already knows the truth from
  training data. The Donny script confidently cited
  `trafilatura` and "Wikipedia is its absolute home
  turf" from a doc whose 22 chunks contained zero
  occurrences of either word.
    Slice scope:
    1. **Claim extraction.** After `build_render_brief()`
       returns, run a small Responses-API call (or a
       deterministic regex pass for named entities first)
       to enumerate the script's factual claims:
       proper-noun assertions, named libraries / products
       / companies, numeric claims (counts, prices,
       dates), superlative claims ("the best", "the
       cleanest", "the only").
    2. **Per-claim chunk check.** For each extracted
       claim, check whether at least one retrieved chunk
       supports it. v1: substring match on the named
       entity (case-insensitive). v2: small-model
       semantic similarity. The bar is "at least one
       chunk contains the entity / number / phrase the
       claim hinges on."
    3. **Decision.** Three modes (operator-configurable):
        * **Strict:** any unsupported claim → reject the
          synthesis. Composition status → `failed`,
          `error_message` lists the unsupported claims.
        * **Warn (default):** unsupported claims → log
          to a new `Composition.verification_warnings`
          field, allow the render to proceed. Operator
          sees warnings in the SPA.
        * **Off:** legacy behavior — `gpt-5-mini` is
          trusted on its honour-system contract.
    4. **Operator surface.** A "Verify before render"
       toggle in the SPA make-video flow + the
       `talking_head` starter signature (defaulting to
       Warn). Per-recipe defaults so a long-form ad can
       opt into Strict.
    5. **Same fix for conversation synthesis.**
       `character_os/conversation_synthesis.py` has
       the same prompt-only contract as
       `script_synthesis.py` — K6.4's verifier should
       run on conversation replies too. Could ship as
       K6.5 if K6.4 grows past one session.

    Open questions (Q-k):
    * **Q-k-N: Substring vs semantic** — v1 ships
      substring; when does the upgrade pay off?
      Probably when paraphrases start producing false
      positives (model says "PostgreSQL extension" when
      the chunk says "pgvector"). Defer until first
      false-positive event.
    * **Q-k-N: Pre-flight title sanity** — second
      attack surface from the Donny incident: the
      operator's custom title ("Wikipedia is
      trafilatura's home turf") biased the operator
      brief, which biased the model. Should K3
      ingestion warn (or refuse) when a custom title
      contains named entities not present in the
      document body? Cheap regex + named-entity diff.
      Probably K3.x rather than K6.4 — surface
      separately.

    Cost: ~1 session if substring-only v1 with the Warn
    default. Adds ~5-10s + $0.005-$0.01 per render
    (one extra `gpt-5-mini` Responses call). Strict
    mode + Off mode + SPA toggle adds half a session.

    **SESSION 160 ship notes:**
    * Implementation went lighter than the scope-lock
      estimated. Substring-v1 needed *zero* LLM calls —
      pure regex extraction + substring corpus match.
      Render latency / cost unchanged.
    * Three modes (`strict`/`warn`/`off`) ship at the
      backend level via `settings.K6_CLAIM_VERIFIER_MODE`.
      SPA toggle deferred to v1.1 — the operator can
      flip via env or settings today, which covers the
      v1 use case (dogfood with `warn` default, escalate
      to `strict` per-recipe later).
    * `KNOWN_PLATFORM_TERMS = ("Character OS",)` ships.
      Add to this list as new platform vocabulary
      emerges.
    * Conversation parity (Q-k-N "should the verifier
      run on conversation replies too?") deferred to
      **K6.5** once dogfooding stabilizes the regex
      extraction rules. The verifier module is reusable
      — when K6.5 ships, it'll plumb the same
      `claim_verifier.verify_claims` into
      `conversation_synthesis.py`.
    * **Donny regression smoke:** running v1 against
      the *actual* SESSION 158 Composition `e485d9f9`'s
      script + retrieved chunks flags `Wikipedia` (the
      original hallucination); allow-lists
      `Character OS` (legitimate via
      `KNOWN_PLATFORM_TERMS`); slips `trafilatura`
      (documented v1 limitation — lowercase tech name).
      Anchored as a regression test in
      `test_claim_verifier.py`.

- **K6.4.1 — Strict-mode dogfood follow-ups. ✓ SHIPPED
  SESSION 161.** Two calibration findings from running
  K6.4 in strict mode against the live system:
    1. **Stoplist widening.** First strict-mode render
       rejected on `'Modern'` — a capitalized common
       adjective at a sentence start, not a proper noun.
       Same class as `Cleanest`/`Welcome` from K6.4.
       Added: `modern, digital, smart, advanced, simple,
       basic, classic, premium, natural, easy, hard,
       normal, complete, full, partial, open, closed,
       small, large, tiny, huge, quick, slow, fast,
       rapid, instant, live, active, passive, main,
       primary, secondary, regular, standard, custom,
       special, general, specific, popular, common,
       rare, unique, free, paid, young, old, ancient,
       new, fresh, recent, early, late, final, initial,
       internal, external, online, offline, local,
       remote, public, private`. Locked in by a
       regression test that fires the SESSION 161 false-
       positive set as input.
    2. **Forensic persistence on strict failures.**
       Pre-K6.4.1, strict-mode rejection lost the
       synthesized text — only `composition.error_message`
       carried the summary. Operators couldn't see *what*
       the LLM said. K6.4.1 adds
       `Composition.rejected_synthesis: TextField` (new
       migration `0003_k6_4_1_rejected_synthesis`) and
       `ClaimVerifierError.synthesized_text`. Before
       re-raising as `PrimitiveError`,
       `_maybe_synthesize_script` persists
       `composition.verification_warnings` +
       `composition.rejected_synthesis` so the operator
       has the full forensic surface.
    3. **Live strict-mode dogfood proof:** the SESSION 161
       follow-up replay of the same prompt that flagged
       `'Modern'` in K6.4 now passes — K6 produces a
       script grounded in the chunks under the strict
       constraint. The render fires clean. The bypass
       case (no `OPENAI_API_KEY` → retrieval degrades →
       verifier skipped) is documented as expected v1
       behavior — operator-typed prompts are trusted.

    Test totals: Django 681 → 684 (+3 K6.4.1 tests).
    Migration count: 52 → 53.

- **K6.5 — Conversation-synthesis verifier parity. ✓ SHIPPED
  SESSION 162.** Mirrors K6.4 / K6.4.1 onto
  `conversation_synthesis.py` so `/api/conversations/<id>/messages/`
  replies are verified with the same machinery.
    Shape parity:
    * `ConversationMessage.verification_warnings: JSONField` +
      `ConversationMessage.rejected_synthesis: TextField`
      (migration `0003_k6_5_verification_warnings`). Same
      shape as `Composition.verification_warnings` /
      `Composition.rejected_synthesis`.
    * `ReplyResult.verification_warnings: list[dict]` — Warn
      mode populates; Strict mode raises
      `ClaimVerifierError` (same exception class K6.4 uses).
    * `build_corpus` extended with `extras=` so thread history
      chunks (which legitimately introduce terms via prior
      turns) are part of the allow-list haystack.
    * `ConversationMessageSerializer` exposes the two new
      fields so the SPA can surface them.

    API contract for `POST /api/conversations/<id>/messages/`:
    * Warn / Off / clean → **201** with normal payload,
      `spokesperson_message.verification_warnings` populated
      in Warn mode.
    * Strict + rejection → **422** with payload
      `{"verifier_rejection": {"mode": "strict",
      "rejected_synthesis": "...", "unsupported_claims": [...]},
      "spokesperson_message": <placeholder msg>, ...}`. The
      placeholder SPOKESPERSON message captures the rejection
      so thread continuity is maintained; the operator sees
      the full forensic surface in the response body and via
      the persisted `rejected_synthesis` field.

    **SESSION 162 dogfood finding — refusal-pattern false-
    positive class.** Live strict-mode dogfood probed the
    verifier with a hallucination-prone prompt ("What
    library do you use for parsing pages?"). K6 responded
    *honestly*: "the docs don't say which library we use…"
    The verifier rejected the **honest refusal** because the
    text started with words like `"Short"`, `"Which"`,
    `"HTML"` (used in clarification) that didn't appear in
    chunks. Punishing honest refusals is the opposite of
    what the verifier exists for. Stoplist widened with
    refusal-pattern words: `short, long, brief, quick, which,
    what, where, whose, whom, either, neither, both, many,
    lots, rather, instead, otherwise, frankly, honestly,
    actually, really, straight, plain, plainly, simply,
    fine, ok, okay`. Locked in by
    `test_extract_skips_refusal_pattern_starters_k6_5`.
    Same prompt now passes the verifier; honest refusal
    flows through.

    Test totals: Django 684 → 691 (+7 K6.5 tests: 6 in
    `apps/conversations/tests/test_k6_5_verifier.py` + 1
    refusal-pattern test in
    `apps/compositions/tests/test_claim_verifier.py`).
    Migration count: 53 → 54.

- **K6.4 v1.1 — SPA toggle + verifier surface. ✓ SHIPPED
  SESSION 163.** Surfaces the verifier in the SPA so the
  operator doesn't have to flip env vars to test modes.
    Backend:
    * Per-request ``verifier_mode`` override flows through
      ``build_render_brief(verifier_mode=...)`` and
      ``synthesize_spokesperson_reply(verifier_mode=...)``
      to ``claim_verifier.run_verifier(mode=...)``. ``None``
      falls back to ``settings.K6_CLAIM_VERIFIER_MODE``.
    * ``POST /api/conversations/<id>/messages/`` accepts
      ``verifier_mode`` in the request body; validated
      against ``{"strict", "warn", "off"}`` (400 on
      unknown).
    * ``talking_head(verifier_mode=...)`` starter stores
      the override into ``step.params["verifier_mode"]``,
      which the ``generate_avatar_speech`` primitive
      reads before calling ``build_render_brief``.
    * ``RECIPES["talking_head"]`` gains a
      ``_VERIFIER_MODE_FIELD`` (select). The recipe form
      auto-renders as a select via the metadata-driven
      form renderer; ``recipes.resolve_kwargs`` passes
      ``verifier_mode`` straight to the starter.
    * ``CompositionSerializer`` + ``ConversationMessageSerializer``
      expose ``verification_warnings`` + ``rejected_synthesis``.

    SPA:
    * Conversation chat view (`/conversations/<id>`) gains
      a Verifier select (Warn / Strict / Off) on the
      composer. Default Warn. On 422 strict-mode rejection,
      a ``VerifierRejectionPanel`` renders the unsupported
      claims + a collapsible "what the LLM almost said."
      Each persisted message bubble shows a
      "K6.4 flagged N claim(s)" badge when warnings exist.
    * Composition detail view (`/compositions/<id>`) gains
      a ``VerifierPanel`` section above citations when
      either ``verification_warnings`` or
      ``rejected_synthesis`` is populated.
    * Make-video form (recipe `talking_head`) renders the
      Strict/Warn/Off select automatically (the recipe
      registry now declares the field).

    Test totals: Django 691 → 693 (+2 v1.1 backend
    overrides). SPA vitest 37 → 40 (+3 v1.1 schema
    + UI smoke). Migrations unchanged at 54.

    **Live dogfood:** an HTTP POST with
    ``verifier_mode=strict`` and a patched
    fabrication-prone LLM returned 422 with the full
    ``verifier_rejection`` payload + ``spokesperson_message``
    persisted with ``verification_warnings`` +
    ``rejected_synthesis``. End-to-end SPA-facing surface
    confirmed.

- **K6.4 v1.2 — verification_status field + recipe
  rollout. ✓ SHIPPED SESSION 164.** Closes the SESSION 161
  bypass-case audit gap: an empty
  ``verification_warnings`` list was ambiguous between
  "verified clean" and "verifier didn't run." v1.2 adds an
  explicit four-state field on both ``Composition`` and
  ``ConversationMessage`` so the audit trail is honest.
    * ``apps.compositions.models.VerificationStatus``
      TextChoices: ``verified | trusted_passthrough |
      skipped | rejected``. Default empty for pre-v1.2 rows.
    * ``ScriptResult.verification_status`` +
      ``ReplyResult.verification_status`` populated by
      synthesizers based on which code path runs.
      ``trusted_passthrough`` for any non-LLM path (mock,
      retrieval fail, no chunks, no key, LLM call fail);
      ``verified`` for LLM+verifier ran in strict/warn;
      ``skipped`` for off mode; ``rejected`` set by the
      caller on strict-mode ``ClaimVerifierError``.
    * Migrations:
      ``0004_composition_verification_status`` +
      ``0004_conversationmessage_verification_status``.
    * Both serializers expose the field.
    * SPA: new
      ``web/src/components/verification-status-badge.tsx``
      renders a colored badge keyed off the four states
      (emerald check / muted info / amber alert / red
      shield). Rendered on composition detail page header
      + every spokesperson message bubble.
    * Recipe rollout: ``_VERIFIER_MODE_FIELD`` added to
      ``talking_head_with_backdrop``,
      ``talking_head_polished``, and ``long_form_ad``.
      Each starter grew a ``verifier_mode`` kwarg that
      threads onto every K6-synthesizing
      ``generate_avatar_speech`` step.

    Test totals: Django 693 → 697 (+4 v1.2 backend tests).
    SPA vitest 40 → 46 (+6 badge tests). Migrations 54 → 56.

    **Live dogfood:** synthesizer runs in warn-mode against
    a knowledge-attached Donny thread → returns
    ``verification_status="verified"`` (even with one Warn
    flag — `verified` means "the verifier saw the output").
    Same call with explicit ``verifier_mode="off"`` →
    ``verification_status="skipped"``, warnings=[]. The
    bypass-case audit gap is closed end-to-end.

- **K6.4 stoplist watchdog. ✓ SHIPPED SESSION 165.** Closes
  the dogfood-only stoplist-discovery loop. Every prior
  session has surfaced 1-3 new sentence-initial false-
  positive words via operator probes (`Cleanest`,
  `Welcome`, `Modern`, `Short`, `Alright`). The watchdog
  reports them as a scripted scan instead.
    Pieces:
    * ``is_sentence_initial(text, position)`` helper in
      ``character_os/claim_verifier.py``. Pure function.
      True when position is 0 OR preceded by a sentence-
      ending punctuation (``.!?:``) with optional
      whitespace. 7 unit tests anchor the edge cases.
    * ``python manage.py stoplist_watchdog [--days=N]
      [--limit=N] [--workspace=<slug>]`` scans
      `Composition.verification_warnings` +
      `ConversationMessage.verification_warnings` over a
      configurable window. Three output buckets:
        * **Sentence-initial candidates** — stoplist
          suggestions. Renders a markdown-ish table +
          a copy-pasteable Python set literal of the
          tokens (lowercased) for direct insertion into
          ``_COMMON_PROPER_NOUN_FALSE_POSITIVES``.
        * **Mid-sentence flags** — the verifier doing
          its job; surfaced for awareness, not action.
        * **Warn-mode composition flags (no text
          context)** — Warn-mode composition rejected
          synthesis is not persisted, so we can only
          tally the claim; the sentence-initial
          classification needs the source text.
        * **Regressions** — tokens already in the
          stoplist but flagging again (casing /
          inflection variant slipped through).
    * 5 integration tests cover the four buckets +
      ``--days`` windowing.

    **Live run** against the current DB surfaced 2 events
    from the SESSION 163 K6.5 API dogfood: `Wikipedia`
    (mid-sentence flag — verifier correct) and `Drop a
    Wikipedia` (sentence-initial multi-word flag — a
    real v2 calibration: the multi-word regex includes
    `a` as a joining word, which is too aggressive).

    Test totals: Django 697 → 709 (+12). SPA unchanged.
    Migrations unchanged at 56.

- **K6.4 v2 — surgical fixes to v1 limitations.
  ✓ SHIPPED SESSION 166.** Three changes, all
  driven by the watchdog's findings + the original
  SESSION 158 canonical case:

    1. **Tighter `_MULTIWORD_CAPS_RE`.** Dropped ``a``
       and ``an`` from the joining-word alternatives.
       The SESSION 165 watchdog surfaced ``"Drop a
       Wikipedia"`` as a multi-word match — ``Drop``
       (sentence-initial common verb) + lowercase
       ``a`` + ``Wikipedia`` parsed as one entity.
       After the tightening, the same input produces
       two single-token claims (``Drop`` filtered by
       stoplist + ``Wikipedia`` retained as the real
       entity).

    2. **New `KNOWN_TECH_TERMS` extractor.** Curated
       frozenset of ~40 lowercase tech / library
       names (``trafilatura``, ``pgvector``,
       ``django``, ``react``, ``pytorch``,
       ``celery``, ``openai``, ``anthropic``, ...).
       Case-insensitive regex extracts them as
       ``kind="tech_term"`` claims. **Closes the
       SESSION 158 canonical case**: Donny's script
       said ``"the library doing the work is called
       trafilatura"``; v1 missed it because
       lowercase doesn't trip the capitalized-only
       regex. v2 catches it; strict mode would have
       rejected the composition before Runway fired.

    3. **Lowercase casing dedupe.** Both the
       single-cap pass and the tech-term pass now
       dedupe by lowercase form, so script that
       writes ``"PyTorch"`` and ``"PYTORCH"``
       produces one claim, not two.

    Plus stoplist additions from the watchdog's data:
    ``alright, sure, yeah, yep, yup, nope, agreed,
    totally, absolutely, definitely, exactly,
    precisely, right, indeed, certainly, wow, wait``.

    **Donny regression replay against the live DB**:
    composition ``e485d9f9`` (the SESSION 158
    canonical hallucination) now flags BOTH
    ``Wikipedia`` AND ``trafilatura``. Strict mode
    would block the render.

    Test totals: Django 709 → 713 (+4 v2 tests, plus
    one existing v1-limitation test flipped to v2
    expected-catch). SPA + migrations unchanged.

- **K6.4 v2.1 — real-Runway dogfood + CTA-verb stoplist.
  ✓ SHIPPED SESSION 167.** First production fire of
  the K-arc verifier stack against real Runway under
  strict mode. Findings:
    * **Attempt 1** (strict-mode + "Describe how the
      knowledge layer ingests pages."): rejected on
      `Want` + `Reach`. K6 produced a chunk-grounded
      reply ending in `"Want to see this? Reach out
      and we'll demo."` — both verbs flagged as
      sentence-initial proper-noun-shaped tokens.
      Strict-mode pipeline contract worked end-to-end
      ($0.00 spent, render blocked, rejected_synthesis
      persisted) — but the rejection was on innocent
      CTA verbs, not real hallucinations.
    * **Calibration fix**: ~40 CTA-verb stoplist
      additions (`want, reach, need, learn, watch,
      click, sign, join, follow, subscribe, ...`)
      anchored by
      `test_stoplist_cta_verbs_k6_4_v2_dogfood`.
    * **Attempt 2** (same prompt, post-fix): real
      Runway render shipped at $0.25,
      `verification_status="verified"`,
      `verification_warnings=[]`. K6 under strict
      pressure produced a grounded reply about
      embeddings + vector databases + chunking
      strategies + retrieval — all anchored in the
      Wikipedia RAG doc chunks.
    * **Trafilatura env fix**: while running gates the
      embeddings test suite surfaced
      `ModuleNotFoundError: trafilatura`. The package
      was pinned in `pyproject.toml` but uninstalled
      somehow. Reinstalled
      `trafilatura>=1.10 lxml_html_clean>=0.4`.
      Full suite back to green.

    Test totals: Django 713 → 714 (+1 CTA-verb test).
    Total Runway spend for the dogfood: **$0.25**
    (one production render, status=verified).
- **K7 — URL ingestion + serper discovery.** `trafilatura`
  fetch+extract. Serper search tab on the workspace upload
  surface. Both flow into the same Celery embedding task.
- **K8 — `ConversationMessage` + `ConversationEmbedding`
  models + `retrieve_for_thread()`.** ✓ SHIPPED. Schema +
  retrieval landed during K2 (SESSION 138); the
  message-embedding pipeline completion shipped SESSION
  145 (`31af09d`) — new
  `apps/conversations/tasks.py:embed_message` Celery task
  + post-save signal in `apps/conversations/signals.py`.
  Conversation chunk size locked at **500 chars / 0
  overlap** (Q-k-1 resolved). Both USER and SPOKESPERSON
  roles trigger embedding so the LLM can rebuild context
  across both sides on the next turn. +11 backend tests
  (`apps/conversations/tests/test_embed_message.py`)
  covering short/long message chunking, empty-content
  no-op, idempotency, signal fires per-role, no refire
  on update, broker-down resilience, end-to-end
  `retrieve_for_thread` integration, cross-thread
  isolation.
- **K9 — Conversation REST + SPA.** ✓ SHIPPED SESSION
  145 (`865c7db`). Three pieces:

  Backend
  * `POST /api/conversations/<id>/messages/` —
    server-synchronous send. Creates user message
    (K8's signal embeds it), calls
    `synthesize_spokesperson_reply` to generate the
    spokesperson's reply, persists the reply (also
    embedded by signal), bumps
    `thread.last_activity_at`, returns both messages
    + chunk_ids in one round-trip.
  * `GET /api/conversations/<id>/messages/` —
    chronological message list.
  * `character_os/conversation_synthesis.py` —
    mirrors K6's `script_synthesis`. Uses
    `retrieve_for_thread` for docs + history, calls
    gpt-5-mini Responses API, degrades gracefully on
    missing key / retrieval failure / API error.
    `CONVERSATION_REPLY_FORCE_MOCK=1` env flag for
    dev determinism (third force-mock alongside
    `RUNWAY_FORCE_MOCK`, `EMBEDDING_FORCE_MOCK`,
    `RENDER_SCRIPT_FORCE_MOCK`).
  * `ConversationThreadSerializer` grew
    `message_count` + `last_message_preview` for the
    SPA's thread list.
  * Optional `?spokesperson=<id>` filter on the
    thread list for the SPA's "Conversations" panel.

  Frontend
  * `web/src/routes/conversations/$id.tsx` — focused
    chat view. Message list + composer with
    Cmd/Ctrl+Enter send. Auto-scroll on new
    messages. Pending bubble while synthesis runs.
  * `web/src/lib/api/conversations.ts` — typed
    hooks (`useThreads`, `useThread`,
    `useCreateThread`, `useMessages`,
    `useSendMessage`). Send mutation seeds the
    message cache so the SPA renders the reply
    instantly without a refetch.
  * Spokesperson detail page grew a `ConversationsPanel`
    (`web/src/routes/spokespeople/$id.tsx`) listing
    threads for that spokesperson + a "Start a chat"
    button.

  +14 backend tests in
  `apps/conversations/tests/test_k9_messages.py`
  covering thread CRUD, message GET/POST, empty/long
  content rejection, cross-workspace 404,
  last_activity bump, K8 ↔ K9 pipeline integration
  (sent messages produce ConversationEmbedding rows).
  463 backend tests total. SPA build green.

  Streaming/SSE deferred per Q-k-3 — POST-and-resolve
  is fast enough at gpt-5-mini latencies for v1.
  Revisit if operator feedback flags it.
- **K10 — Onboarding seed.** `seed_workspace_knowledge`
  task. `docs/seeds/character_os/*.md` corpus. Trigger on
  `is_operator=True` workspace creation.

Roughly 10 slices, 8–12 sessions of work. K1 → K6 is the
"render is informed" arc; K7 enables real customer corpora;
K8 → K10 is the conversational surface.

---

## Out of scope (explicitly)

- **Cross-workspace knowledge sharing.** No marketplace, no
  public KBs, no global templates with pre-ingested
  knowledge. Contract rule 7.
- **Active web crawling.** URL ingestion fetches the single
  URL the operator paste; it does not follow links, traverse
  subdomains, or schedule re-crawls. Serper discovery
  surfaces candidates but the operator picks each one.
- **OCR / scanned PDFs.** Text-based PDFs only in v1.
  `pdfminer.six` extraction. Scanned PDFs fail loudly.
- **Multi-language embeddings.** English-only v1. The
  embedding model is locked to `text-embedding-3-small`
  which handles multilingual content acceptably, but no
  language detection / per-language routing.
- **Multi-model embeddings.** Locked to
  `text-embedding-3-small` in v1. Switching models is a
  re-embed-all event; we defer that decision.
- **Risk-aware re-ranking.** u-d-b's `is_critical` boost,
  document_class taxonomy, and context-budget tiers from
  Session 949 are over-engineering for a launch product.
  Cosine similarity + top-k is sufficient.
- **Encryption-at-rest of chunk content.** Workspace ACL
  + the structural retrieval guarantee are the v1 protection.
  Field-level encryption is a v2 hardening.
- **URL re-fetch / freshness automation.** Snapshot at
  ingest. Operator re-ingests if they want fresh.
- **Citations rendered in video output.** Citation data is
  logged server-side per render; no on-screen attribution in
  the rendered video. Operator-facing audit UI is post-v1.
- **Knowledge versioning / history.** Editing a doc replaces
  its chunks; there is no version history. Re-ingest if you
  want a snapshot of an older version.

---

## Open questions (resolve in implementation slices)

- **Q-k-1 — Conversation chunk size.** Doc chunks are
  1000 chars / 200 overlap (u-d-b default). Conversation
  turns are typically much shorter (one message = a few
  hundred chars). Lock the conversation chunk size in K8.
  Likely 500 chars / 0 overlap, but verify against real
  Maya-style turns.
- **Q-k-2 — `script_synthesis.synthesize()` LLM choice.**
  K6 needs an LLM call. OpenAI? Anthropic? What's already
  wired in shell? Resolve in K6 planning — likely whatever
  the prompts module already uses.
- **Q-k-3 — Streaming vs. polling for conversation replies.**
  K9 decides: WebSocket / SSE stream, or POST-and-poll. Lean
  POST-and-poll for v1 simplicity; revisit if latency feels
  bad.
- **Q-k-4 — Cost tracking surface.** Per-chunk
  `embedding_cost_micros` is stored. Where does it surface?
  Admin-only stat? Per-workspace dashboard tile? Defer to
  post-v1 if no surfaces are urgent.
- **Q-k-5 — Conversation retention.** Conversations grow
  unboundedly. v1 default: keep forever. v1.1 likely
  introduces a per-workspace TTL or a manual "archive
  thread" action.
- **Q-k-6 — `pgvector.django` vs raw SQL for retrieval.**
  u-d-b uses `pgvector.django.CosineDistance`. We adopt the
  same. Verify it composes correctly with the
  `Q(spokespeople__isnull=True) | Q(spokespeople=...)`
  filter in K2.

---

## How to verify the privacy guarantee

Before K2 closes, three test cases must pass:

1. **`test_cross_workspace_chunk_isolation`**: create
   workspaces A and B, each with a spokesperson and a
   document. `retrieve_for_spokesperson(spokesperson_a, ...)`
   never returns workspace B's chunks even when querying for
   text that exists in both.
2. **`test_cross_thread_conversation_isolation`**: two
   threads in the same workspace. `retrieve_for_thread(thread_a, ...)`
   returns no embeddings from `thread_b`.
3. **`test_only_retrieval_module_queries_chunk_tables`**:
   the repo-level grep test from §"Retrieval surface."

The three tests are the contract. Implementation can vary;
the tests cannot fail.

---

## Change log

- 2026-05-14 (SESSION 137) — Initial scope lock. No code yet.
  Five decisions locked: M2M spokesperson visibility, shell
  does RAG, yes onboarding seed (operator workspaces only),
  Postgres+pgvector as K1, URL ingestion via paste OR serper
  → fetch+extract pipeline. Two high-severity privacy
  guarantees designed in: explicit `KnowledgeDocument.workspace`
  FK + single-named-retrieval-functions surface, and
  separate-table conversation embeddings (not discriminated
  rows in the docs table). Embedding cost concern dropped in
  favor of content-hash dedup discipline.
