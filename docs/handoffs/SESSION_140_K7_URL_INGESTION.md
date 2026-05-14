---
title: "Session 140 — K7 URL ingestion + serper discovery"
date: 2026-05-14
status: complete
session: 140
previous_handoff: ./SESSION_139_K6_RENDER_INTEGRATION.md
---

# Session 140 — K7: knowledge ingestion is feature-complete

## TL;DR

- **What shipped:** K7 — the fourth ingestion path. Operators
  can now bring workspace knowledge in four ways: paste, PDF
  upload, URL paste, or web-search discovery (serper.dev).
  All four flow through the same `embed_document` Celery task
  and land as `KnowledgeDocument` rows with the same dedup,
  spokesperson-visibility, and retrieval semantics established
  by K2-K6. **Knowledge ingestion is feature-complete for v1.**
- **What's blocking next:** Nothing. SESSION 141 is K8 — the
  conversation pipeline. K2 already shipped the schema
  (`ConversationMessage` + `ConversationEmbedding`); K8 adds
  the message-receive → embed → retrieve → reply-synthesize
  pipeline.
- **What's in a weird state:**
  - **Fourth force-mock landed.** `SERPER_FORCE_MOCK=1` joins
    `RUNWAY_FORCE_MOCK`, `EMBEDDING_FORCE_MOCK`, and
    `RENDER_SCRIPT_FORCE_MOCK`. Setting all four gives fully-
    offline deterministic dev.
  - `SERPER_API_KEY` env var is not yet documented in
    `.env.example` (none exists in this repo). Operator
    should add it to the local `.env` when ready to use
    real serper.

## Cumulative test counts

| Surface | Count |
|---|---|
| Backend `pytest character_os/prompts/` | 46 |
| Backend `pytest apps/embeddings/tests/` | 88 |
| Backend `pytest apps/videos/tests/` | 11 |
| Backend smoke commands | 6 |
| SPA `pnpm test` (unit) | 3 |
| SPA `pnpm e2e` (Playwright) | 38 |
| **Total backend tests** | **145** |
| **Total e2e specs** | **38** |

All green.

---

## What changed

### `shell/apps/embeddings/url_fetch.py` (new)

httpx-based URL fetch + `trafilatura.bare_extraction`-based
main-content extraction. ~180 lines.

- `fetch_url(url, *, timeout=15.0) -> ExtractedUrl`
- `ExtractedUrl(url, title, text, metadata={author, date,
  sitename, hostname, fetched_chars, extracted_chars})`
- Caps: 10 MB raw HTML, 15s wall-clock timeout.
- Polite UA: `Mozilla/5.0 (compatible; CharacterOS-Bot/1.0; ...)`.
- Snapshot semantics: no re-fetch, no link-following, no
  authentication. Per K0 scope-lock §"Out of scope."
- `UrlFetchError` surfaces every failure path: malformed URL,
  non-http scheme, no host, DNS / TLS / connection errors,
  4xx / 5xx, oversized response, empty HTML, trafilatura
  returning `None` (paywall / login wall / pure-JS), empty
  extracted text.

### `shell/apps/embeddings/serper.py` (new)

serper.dev search client. Port of u-d-b's
`core/tools/web_search.py:WebSearchTool._search_text` shape.
~140 lines.

- `search(query, *, top_k=8) -> list[SearchResult]`
- `SearchResult(title, url, snippet, position)` (1-indexed).
- HTTP POST to `https://google.serper.dev/search` with
  `X-API-KEY` header. 10s timeout.
- Django cache (Redis db 2 — same cache backend as K3's
  embedding service) keyed by `sha256(query|top_k)` with
  1-hour TTL. The same query within an hour skips the API.
- `SERPER_FORCE_MOCK=1` env / settings: deterministic stub
  results. Same shape as the other three force-mocks. No
  API key required in mock mode.
- `SerperError` raised on missing key, 4xx/5xx response,
  connection errors, non-JSON response.
- `MAX_TOP_K = 20` ceiling; `DEFAULT_TOP_K = 8`.

### `shell/apps/embeddings/ingestion.py` (extended)

New orchestrator `ingest_url(workspace, url, title="",
created_by=..., spokespeople=[], source_metadata={},
ingested_via=PASTE)`:

1. Calls `url_fetch.fetch_url(url)`.
2. Title falls back to extracted page title or hostname.
3. trafilatura metadata merges into `source_metadata`.
4. Routes through the existing `_persist` path — same dedup
   via `(workspace, content_hash)`, same M2M signal
   validation.

`ingested_via` is `PASTE` for operator-typed URLs, `SERPER`
when the SPA flags `via_serper=true` (i.e., the URL came
from a serper search result the operator clicked).

### `shell/apps/embeddings/serializers.py` (extended)

Three new write-only fields + three-way XOR validation:

- `source_url_input: URLField(write_only=True, required=False)`
- `via_serper: BooleanField(write_only=True, default=False)`
- `title: CharField(required=False, allow_blank=True)` — was
  required; URL ingest can derive it from page metadata.
  PDF / paste paths fall back to `"Untitled"` via `_persist`.

`validate()` now enforces: **exactly one** of `text_content`,
`pdf_data_uri`, `source_url_input` must be supplied. Both
or all three is a 400; none is a 400.

`create()` adds the URL branch — calls `ingest_url` with
`ingested_via=SERPER` when `via_serper=True`. URL fetch
failures surface as a 400 with the error on
`source_url_input`.

### `shell/apps/embeddings/views.py` (extended)

New `@action(detail=False, methods=["post"], url_path="search")`
on the viewset:

- Body: `{"q": <query>, "top_k": <int>}`.
- Returns: `{"query": str, "results": [{title, url, snippet,
  position}]}`.
- 502 BAD GATEWAY when serper API errors out; clean 400 on
  missing query.
- Authenticated-only (`IsWorkspaceMember` from the parent
  viewset — first half of `has_permission` is just auth
  check; the per-object membership check doesn't apply to
  detail=False actions).

### `web/src/lib/api/knowledge.ts` (extended)

- `CreateKnowledgePayload` gains `source_url_input?` and
  `via_serper?`; `title?` becomes optional.
- New `SearchResult` zod schema + `searchKnowledge(query)`
  helper + `useKnowledgeSearch()` mutation hook (mutation
  because search fires on submit, not on render).

### `web/src/routes/workspace/knowledge.tsx` (extended)

Upload panel now has four tabs:

- **Paste** (K3) — unchanged
- **Upload PDF** (K3) — unchanged
- **URL** (K7) — new. Title is optional (falls back to page
  `<title>`); URL is required. "Snapshot at ingest"
  reminder copy.
- **Search** (K7) — new. Operator types query → submit →
  results list with per-row "Ingest" button. Each ingest
  fires `POST /api/knowledge/` with `via_serper=true`. After
  successful ingest the result removes itself from the
  visible list.

### `web/e2e/workspace-knowledge-k7.spec.ts` (new)

Three e2e specs:

1. Search tab returns force-mock results + ingest button.
2. URL tab is reachable; submit-disabled until URL is filled.
3. All four tabs render + are switchable.

The K7 ingest path itself (URL fetch + trafilatura extract)
is covered by backend unit + API tests — the e2e doesn't
trigger real network calls.

### `shell/pyproject.toml` (extended)

Added `trafilatura>=1.10` + `lxml_html_clean>=0.4`
(transitive — trafilatura → justext → lxml needs the shim
after lxml 5.x split `lxml.html.clean` into a separate
package).

### `00-START-NEXT-SESSION.md`

K7 row in the phase table marked DONE. New "SESSION 140
status" section above the SESSION 139 + 138 sections.
Queued investigations renumbered. K8 brief at the top of
the doc.

### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated against Postgres post-K7.

---

## Calibration carried forward

- **The carried-forward calibration paid out again, fourth
  time.** The SESSION 139 AI Notes said: "What I'd tell
  SESSION 140 (K7) at the start: read u-d-b's
  `core/tools/web_search.py:WebSearchTool` before writing
  the serper client." Did exactly that — found the serper
  payload shape in 60 seconds. The full pattern is now four
  for four: SESSION 137 cost-cap math, SESSION 137 Maya
  framing, SESSION 139 gpt-5-mini, SESSION 140 serper.
  **Pattern is fully load-bearing**: when adding integration
  with an external service, READ u-d-b first.

- **`@dataclass(slots=True)` doesn't have `__dict__`.** Tried
  to cache serper results as `[r.__dict__ for r in results]`
  — `AttributeError`. Fix: `dataclasses.asdict(r)`. Slot
  classes opt out of `__dict__` for memory savings; the
  cost is dict-style access patterns break. Worth noting
  for any future dataclass-cache patterns in shell.

- **Title becomes optional but the serializer still has to
  accept the legacy required-title flows.** The cleanest fix
  was overriding `title = CharField(required=False,
  allow_blank=True)` at the serializer level rather than
  changing the model's blank=True. The model still expects
  non-empty at the DB level; `_persist` substitutes
  "Untitled" and `ingest_url` substitutes the page's
  `<title>` tag. Three different defaults at three different
  layers — works because each layer has progressively more
  context about the source.

- **The four force-mock flags now form a pattern, not three
  one-offs.** Any future external-API integration in shell
  should follow the same shape:
  1. `<SERVICE>_FORCE_MOCK=1` env var, with `settings.<SERVICE>_FORCE_MOCK`
     beating env.
  2. Deterministic mock path that echoes inputs into outputs
     so tests can assert "inputs carried through."
  3. Real-mode requires the relevant API key; raises rather
     than degrading silently when the key is missing.
  4. Cached responses where the API is read-mostly (embeddings,
     serper — yes; render synthesis — no, output varies per
     spokesperson).

- **trafilatura's transitive lxml dependency was a surprise.**
  `lxml 5.x` split `lxml.html.clean` into a separate
  `lxml_html_clean` package; trafilatura → justext still
  imports from the old path, so a fresh install fails with
  an `ImportError` on first call. Pinned `lxml_html_clean>=0.4`
  in pyproject.toml so future installs work without manual
  fix. Worth flagging if similar splits happen in other
  trees later.

---

## Queued investigations (priority-ordered)

K-prefixed slices remain in `docs/design/KNOWLEDGE_LAYER.md`
§"Slice breakdown."

1. **K8 — Conversation pipeline** (message + embedding +
   reply synthesis on top of the K2 schema).
2. **K9 — Conversation REST + SPA.**
3. **K10 — Onboarding seed.**
4. **First marketing video** — now possible. Operators with
   real Runway + OpenAI keys can ingest real content via
   any of the four K3+K7 paths and render an informed
   video that draws from it.
5. **Voice preset audit** — listen to the four cast members
   with real-mode knowledge-informed renders.
6. **E2e detritus cleanup** — ~495+ e2e workspaces in
   Postgres.
7. **OpenAI client factory port** — K3 + K6 are two call
   sites; the third (K8 + K9 conversation reply synthesis)
   is coming. Worth porting u-d-b's
   `openai_client_factory.py` before K9 lands.
8. **W11.1 — Edit-spokesperson modal.**
9. **W12 — Legacy form retirement.**
10. **Cast sync command.**
11. **Tier 2 prompt helpers** — likely subsumed by K6's
    `build_render_brief`.
12. **Stuck-row janitor.**
13. **Additional video kinds** — cinematic / dialogue /
    long_ad.
14. **Act-Two performance capture.**
15. **`lesson` video kind.**
16. **Real Google OAuth + dj-stripe.**
17. **Allauth legacy-settings cleanup.**
18. **smoke_voice / smoke_avatar transaction discipline.**
19. **Drift verifier** (`verify_doc_claims --only-drift`).
20. **Brand Identity v2 + dark mode.**

---

## AI Notes

- **One-slice-per-session pacing held.** SESSION 138 (5
  slices) was a marathon; SESSIONS 139 + 140 (one slice each)
  felt sustainable and produced cleaner work. The K7
  diagnostics (the `__dict__` slot-class bug, the trafilatura
  import chain, the title-optionality cascade) all surfaced
  early because focus stayed narrow.

- **The "knowledge ingestion is feature-complete" milestone
  matters.** K1-K7 ship the *what* of the knowledge layer:
  the schema, the retrieval surface, the four ingestion
  paths, the render integration, the per-spokesperson
  visibility filter. K8-K10 are now about the *conversation*
  surface — a different product motion entirely. The next
  user (or first marketing video, or first real customer
  workspace) doesn't need K8-K10 to be useful. Worth marking
  in the start-here so future sessions can prioritize
  accordingly.

- **What I'd tell SESSION 141 (K8) at the start:** read
  u-d-b's `core/conversation_memory.py` *and*
  `core/services/agent_llm_router.py` *before* writing the
  conversation pipeline. Conversation reply synthesis is
  shaped a lot like K6's `build_render_brief` (RAG + LLM
  call + persist citation), but with two differences: (1)
  retrieval is `retrieve_for_thread` not
  `retrieve_for_spokesperson`, and (2) the reply needs to
  account for the thread's full message history, not just
  the latest user input. The pattern in u-d-b is worth
  reading. Also: now is the right time to port u-d-b's
  `openai_client_factory.py` — K8 will be the third LLM
  call site (after embeddings + render synthesis), and the
  factory pattern was flagged in the
  `feedback_openai_gpt5_responses_api.md` memory as the
  inflection point.

- **K8 will surface the Q-k-1 chunk-size decision from the
  K0 scope-lock.** Conversation chunks are shorter than
  document chunks (chat turns are 50-200 chars, not
  paragraphs). My instinct: 500 chars / 0 overlap. Verify
  against real Maya-style turns during K8 implementation.
