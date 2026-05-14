---
title: "Session 139 — K6 render flow integration"
date: 2026-05-14
status: complete
session: 139
previous_handoff: ./SESSION_138_K1_THROUGH_K5.md
---

# Session 139 — K6: knowledge informs renders

## TL;DR

- **What shipped:** K6 — the knowledge layer stops being inert
  storage and starts *informing* video renders. At video
  create time, `build_render_brief()` runs RAG against the
  spokesperson's visible knowledge, calls `gpt-5-mini` via the
  Responses API to synthesize a paragraph-length script, and
  persists which chunks fed the render onto
  `Video.knowledge_chunk_ids`. Media-engine contract is
  unchanged — it still receives a finished `brief` string,
  just a richer one.
- **What's blocking next:** Nothing. SESSION 140 is K7 — URL
  ingestion + serper-backed search discovery.
- **What's in a weird state:**
  - The synthesis path needs `OPENAI_API_KEY` to actually
    call gpt-5-mini in real mode. Without it, the render
    degrades gracefully — operator brief flows through
    unchanged, citation IDs still log for audit. For local
    dev without the key, set `RENDER_SCRIPT_FORCE_MOCK=1`
    (same shape as `EMBEDDING_FORCE_MOCK` and
    `RUNWAY_FORCE_MOCK`).
  - Three force-mock flags now exist. Setting all three
    (`RUNWAY_FORCE_MOCK=1`, `EMBEDDING_FORCE_MOCK=1`,
    `RENDER_SCRIPT_FORCE_MOCK=1`) gives fully-offline,
    deterministic local dev.

## Cumulative test counts

| Surface | Count |
|---|---|
| Backend `pytest character_os/prompts/` | 46 |
| Backend `pytest apps/embeddings/tests/` | 56 |
| Backend `pytest apps/videos/tests/` | 11 |
| Backend smoke commands | 6 |
| SPA `pnpm test` (unit) | 3 |
| SPA `pnpm e2e` (Playwright) | 35 |
| **Total backend tests** | **113** |
| **Total e2e specs** | **35** |

All green.

---

## What changed

### `shell/apps/videos/models.py`

Added `Video.knowledge_chunk_ids = JSONField(default=list)`.
List of `KnowledgeChunk` UUIDs (as strings) that fed the
synthesized brief. No UI in v1 — audit data only.

### `shell/apps/videos/migrations/0002_video_knowledge_chunk_ids.py` (new)

The schema migration. Default `[]` keeps it backward-compatible
with existing rows.

### `shell/character_os/script_synthesis.py` (new)

The K6 core. ~250 lines. Three operating modes:

1. **`RENDER_SCRIPT_FORCE_MOCK=1`** (env or
   `settings.RENDER_SCRIPT_FORCE_MOCK=True`): no LLM call.
   Deterministic brief shape:
   `f"{business_brief}\n\n{operator_prompt}\n\n[knowledge: {N} chunks: {csv-of-ids}]"`.
   Mirrors `RUNWAY_FORCE_MOCK` / `EMBEDDING_FORCE_MOCK`.
2. **Empty knowledge**: graceful degradation per scope-lock
   contract rule 6. No chunks visible → return operator
   prompt verbatim, no LLM call, `chunk_ids=[]`,
   `used_knowledge=False`.
3. **Real mode**: one `client.responses.create()` call with
   `model="gpt-5-mini"`, `max_output_tokens=500`,
   `reasoning={"effort": "low"}`. System prompt anchored to
   `spokesperson.tone_archetype` + `business_brief`. User
   message includes the chunks with citation markers.

Returns `ScriptResult(brief, chunk_ids, used_knowledge,
model, tokens_input, tokens_output)`. Always returns a usable
`brief`; never raises. Multiple degradation paths:

* `retrieve_for_spokesperson` raises → degrade
* No `OPENAI_API_KEY` set + real mode → degrade
  (citation IDs still logged for audit)
* OpenAI call raises → degrade (citation IDs still logged)

### `shell/apps/videos/views.py`

Three lines inserted between brief resolution and the
`MediaEngineClient.create_video()` call:

```python
script = build_render_brief(spokesperson, operator_brief)
instance.knowledge_chunk_ids = script.chunk_ids
instance.save(update_fields=["knowledge_chunk_ids", "updated_at"])
brief = script.brief
```

The citation is persisted *before* the media-engine call so
that a later media-engine failure still leaves a record of
which chunks were intended to feed the render.

### `shell/apps/videos/tests/__init__.py` + `test_script_synthesis.py` + `test_render_with_knowledge.py` (new)

**11 K6 tests** total:

* 8 unit tests in `test_script_synthesis.py` covering:
  force-mock with knowledge, force-mock empty knowledge,
  empty-everything fallback, real-mode without key
  (degrades), real-mode without key + no knowledge,
  OpenAI failure (degrades with citations), successful
  real-mode synthesis (mocked OpenAI), retrieval failure
  (degrades cleanly).
* 3 integration tests in `test_render_with_knowledge.py`
  covering: end-to-end POST /api/videos/ flow with
  citation persistence, degraded path with no knowledge,
  pre-K6 fail-fast path (no avatar → synthesis skipped).

### `~/.claude/projects/-Users-donkeyking-development-character-os/memory/feedback_openai_gpt5_responses_api.md` (new)

Captures the calibration: `gpt-4o-mini` is being deprecated;
gpt-5 family uses the Responses API, not chat-completions.
References u-d-b's
`core/services/llm_provider_registry.py:122` for the shape.
Plus a follow-up note about porting u-d-b's
`openai_client_factory` once a third call site lands.

### `00-START-NEXT-SESSION.md`

Phase table updated (K6 DONE, K7 NEXT). SESSION 138 section
preserved verbatim above the new SESSION 139 section.
Updated calibration / queued investigations / three-force-mock
guidance.

### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated against Postgres post-K6.

---

## Calibration carried forward

- **The biggest mistake of the session was almost reaching
  for `gpt-4o-mini` + `chat.completions`.** Operator caught
  it immediately: "Don't use gpt-4o-mini, that model is about
  to be deprecated and the new gpt-5 models have different
  endpoints. All of the things you need about setting them
  up is in u-d-b." I went to u-d-b's `llm_provider_registry`
  and found the Responses-API shape in 60 seconds. Saved as
  feedback memory — future LLM calls in shell should default
  to `gpt-5-mini` + Responses API without re-checking.

- **Same calibration as SESSION 137's cost-cap math:** when
  proposing infrastructure that has prior art in u-d-b,
  READ u-d-b first. This has now caught three out of three
  hypotheticals (cost-cap, Maya tutor-mode, gpt-5-mini). The
  pattern is robust.

- **The `poll_video_until_terminal.delay()` trap in
  integration tests.** With `CELERY_TASK_ALWAYS_EAGER=True`,
  the poll task fires inline immediately after `create_video`
  returns. The fake media-engine task ID isn't recognised by
  the poll endpoint → video flips to `failed` mid-test. Fix
  was to patch the `.delay()` call to a no-op in the
  integration tests; the unit tests already cover the
  synthesis path without going near Celery. **Future
  pattern:** for integration tests against view-layer
  Celery-task-firing paths, always patch the downstream
  `.delay()` calls unless you're specifically testing the
  full chain.

- **Three mock flags, one mental model.** `RUNWAY_FORCE_MOCK`
  (media-engine), `EMBEDDING_FORCE_MOCK` (shell embedding
  service), `RENDER_SCRIPT_FORCE_MOCK` (shell script
  synthesis). All read env + settings, settings beats env,
  all use the same truthy parsing. Pattern is now load-
  bearing — any future external-API integration in shell
  should follow the same shape so dev/test can fully
  offline-mock the stack.

---

## Queued investigations (priority-ordered)

K-prefixed slices remain in `docs/design/KNOWLEDGE_LAYER.md`
§"Slice breakdown."

1. **K7 — URL ingestion + serper discovery.** `trafilatura`
   fetch + extract via the same ingestion path. Serper
   search tab on the workspace upload UI. Both flow into
   the same `embed_document` task.
2. **K8 — Conversation models** (message + embedding pipeline
   on top of the K2 schema already in place).
3. **K9 — Conversation REST + SPA.**
4. **K10 — Onboarding seed.**
5. **First marketing video** — now possible. Attach
   Character-OS knowledge to the operator workspace, render
   a real video about the product. Validates the K6 path
   end-to-end with real Runway credits.
6. **Voice preset audit** — listen to the four cast members
   with real-mode knowledge-informed renders.
7. **E2e detritus cleanup** — Postgres carries ~495+
   e2e-generated workspaces.
8. **OpenAI client factory port** — u-d-b has
   `core/services/openai_client_factory.py`. K3 + K6 are
   two call sites; the factory is worth porting when the
   third lands.
9. **W11.1 — Edit-spokesperson modal.**
10. **W12 — Legacy form retirement.**
11. **Cast sync command.**
12. **Tier 2 prompt helpers** — likely subsumed by K6's
    `build_render_brief`.
13. **Stuck-row janitor.**
14. **Additional video kinds** — cinematic / dialogue /
    long_ad.
15. **Act-Two performance capture.**
16. **`lesson` video kind.**
17. **Real Google OAuth + dj-stripe.**
18. **Allauth legacy-settings cleanup.**
19. **smoke_voice / smoke_avatar transaction discipline.**
20. **Drift verifier** (`verify_doc_claims --only-drift`).
21. **Brand Identity v2 + dark mode.**

---

## AI Notes

- **One slice, one session — the right pace.** SESSION 138
  shipped K1-K5 in a marathon. SESSION 139 deliberately
  shipped only K6 + the handoff. K6 needed more care than the
  others (real LLM integration, async failure modes,
  citation persistence) and benefited from undivided focus.
  Future slices that introduce *behavior change to existing
  flows* (rather than purely new surfaces) should default to
  one-per-session pacing.

- **The integration-test failure (`poll_video_until_terminal`
  firing eagerly) is exactly the kind of thing fresh eyes
  catch.** Mid-marathon I might have papered over it; with a
  scoped K6-only focus I traced it to the right cause in
  ~30 seconds. Validation for the pacing instinct.

- **What I'd tell SESSION 140 (K7) at the start:** read u-d-b's
  `core/tools/web_search.py:WebSearchTool` *before* writing
  the serper client. Same pattern as SESSION 137 with the
  scope-lock and SESSION 138 with the TextSplitter / ingestion
  port — prior art exists, READ it first. The memory already
  flags this; trust it.

- **The render path is now structurally complete.** What
  goes in (operator prompt + workspace knowledge) and what
  comes out (informed script → Runway → video) form a closed
  loop. K7-K10 add new INPUT shapes (URLs, conversation
  turns, seed corpus) but the K6 synthesis step is the
  bottleneck everything flows through. Worth treating the
  contract `build_render_brief` exposes as load-bearing as
  the K2 retrieval surface.
