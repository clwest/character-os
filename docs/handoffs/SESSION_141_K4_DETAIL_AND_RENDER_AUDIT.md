---
title: "Session 141 — K4.1 detail view + render-pipeline audit"
date: 2026-05-14
status: complete
session: 141
previous_handoff: ./SESSION_140_K7_URL_INGESTION.md
---

# Session 141 — K4.1 + the render-pipeline audit

## TL;DR

Two outcomes:

1. **K4.1 shipped** — `/workspace/knowledge/:id` detail view
   with full chunk-by-chunk content + provenance metadata
   (author, date, hostname, char counts). List-view titles
   are now clickable. Closes a real UX gap surfaced during
   live testing: after ingest, operators couldn't tell what
   actually got captured.

2. **Critical audit finding** — K6's render path hits the
   wrong Runway endpoint. The synthesized brief is good
   (gpt-5-mini produced a clean 447-char RAG explainer from
   the Wikipedia article), but it's sent to `gen4_turbo`
   (image-to-video animation) instead of `/v1/avatar_videos`
   (talking-head). Result: a 5-second silent animation of
   the spokesperson's portrait — the avatar doesn't speak.
   The right pipeline exists in
   `media-engine/app/services/character_host_client.py:_generate_real`
   but is hardcoded against the legacy `Campaign` model.
   K6.5 (next session) ports it to the Spokesperson model.

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

No regression (knowledge specs all green; 3 wizard/voice
e2e specs time out against real-Runway media-engine — same
pre-existing flake, unrelated to K4.1).

---

## What shipped

### K4.1 — knowledge document detail view

#### `shell/apps/embeddings/serializers.py`

- New `KnowledgeChunkSerializer` — read-only view of one
  chunk (id, chunk_index, chunk_text, chunk_size,
  overlap_size, embedding_model, cost micros,
  processing_time_ms). Vector column deliberately omitted —
  huge + not human-readable.
- New `KnowledgeDocumentDetailSerializer(KnowledgeDocumentSerializer)`
  — inherits everything from the list serializer plus a
  `chunks` SerializerMethodField that calls
  `obj.chunks.all().order_by("chunk_index")`. Uses the
  reverse-FK accessor (not `KnowledgeChunk.objects`) so the
  K2 privacy-grep test stays happy.

#### `shell/apps/embeddings/views.py`

- `KnowledgeDocumentViewSet.get_serializer_class()` — returns
  `KnowledgeDocumentDetailSerializer` for `action == "retrieve"`,
  base serializer for list. Chunks would be a perf cliff if
  surfaced on every row of a long list; this keeps list lean.

#### `web/src/lib/api/knowledge.ts`

- New `KnowledgeChunk` zod schema + type export.
- `KnowledgeDocument.chunks` is now an optional array (only
  populated on detail responses, omitted on list).

#### `web/src/routes/workspace/knowledge.$id.tsx` (new)

The detail page. Sections:
- Back-to-knowledge link.
- Title + status pill in a flex header.
- Metadata grid: type, ingested-via, chunk count, source URL
  (clickable for URL docs), hostname, author, date,
  extracted/fetched char counts, PDF page count, created
  timestamp. All optional metadata fields collapse when
  empty.
- Error banner when `status='failed'` with `error_message`
  visible.
- Delete button (soft delete, navigates back to list).
- Chunks section — ordered list of chunks with the
  per-chunk index, size, overlap, embedding model, and
  the actual chunk text (whitespace preserved). Empty +
  pending/processing states handled.

3-second polling while doc is pending/processing — chunks
appear as soon as embedding finishes.

#### `web/src/App.tsx`

Registered the new `/workspace/knowledge/:id` route under
`<RequireAuth>` + Layout.

#### `web/src/routes/workspace/knowledge.tsx`

Wrapped the row title in a `<Link>` pointing at the detail
page. `data-testid="knowledge-row-link-<id>"`.

### Quick bugfix — render passes portrait as `prompt_image`

#### `shell/apps/videos/views.py`

The K6 render path was missing `prompt_image` in the
media-engine `create_video` call. Real-mode Runway
(`gen4_turbo`) requires it — the engine returns
`{"code": "invalid_settings", "error": "prompt_image is
required for model gen4_turbo. Use model=gen4.5 for
text-only generation."}` without it.

Fix: pass `prompt_image=spokesperson.portrait_path or None`.
The portrait URL was already populated by the avatar bind
in the wizard / seed_cast pipeline (SESSION 136); we just
needed to forward it.

After this fix, renders against real Runway return a video.
But — see the audit below — the video is not a talking-head;
it's just visual animation of the portrait.

### Stack reconfiguration

- Imported OpenAI + SERPER API keys from u-d-b's `.env`
  into character-os's `.env` (per operator direction).
  RUNWAY key was already present.
- After operator topped up $50 OpenAI credit, restarted
  Django + Celery WITHOUT mock flags so K3 (embeddings)
  and K6 (script synthesis) both hit real APIs.
- Hard-deleted 4 soft-deleted knowledge docs (44 rows
  including chunks) so the operator's re-ingest could
  start clean. The soft-delete dedup-restore bug is queued
  as K4.2.
- Operator re-ingested Wikipedia (22 chunks via paste-as-URL,
  105 micros = $0.000105) + did a serper search for "How to
  create an avatar using RunwayML" + ingested a top result
  (1 chunk, 1 micro). Both landed processed with real
  vectors.

---

## The audit (key finding)

When the operator made a video from the UI ("How RAG works
with AI" brief, Sasha as spokesperson), they got back a
5-second silent clip — just the portrait animated, no
speech, no audio. Investigation revealed:

### What worked

- `build_render_brief` ran correctly. 5 chunks were
  retrieved from the Wikipedia article (`Video.knowledge_chunk_ids`
  populated with the right UUIDs).
- gpt-5-mini synthesized a clean ~450-char brief drawing
  from those chunks: "RAG lets language models pull in
  real documents before answering. First, the system
  searches a set of documents..." — exactly what K6
  promised.

### What didn't

The synthesized brief was POSTed to
`/internal/videos/`, which calls
`runway_client.create_task` with the `gen4_turbo` model.
`gen4_turbo` is **image-to-video animation** — it
generates motion based on a text prompt + still image,
but does NOT generate speech, lip-sync, or audio.

The **right** endpoint is `/v1/avatar_videos` with model
`gwm1_avatars`:

```python
body = {
    "model": "gwm1_avatars",
    "avatar": {"type": "custom", "avatarId": avatar_id},
    "speech": {"type": "text", "text": script},
}
url = f"{settings.runway_api_base}/v1/avatar_videos"
```

This endpoint:
- Uses the spokesperson's bound custom avatar
- Performs TTS internally (voice is determined by the
  avatar's bound voice preset, set at avatar-creation time
  in SESSION 134/136)
- Produces a talking-head video with lip-sync

The wrapper for this endpoint already exists at
`media-engine/app/services/character_host_client.py:_generate_real`
(lines 412-492). It's hardcoded against the legacy
`Campaign` model. K6 needed to port it to accept the
`Spokesperson`'s `runway_avatar_id` directly, but didn't —
this is the K6.5 work.

### Other findings (queued)

1. **K4.2 — dedup-restore bug.** `_persist` returns a
   soft-deleted document as the "existing" row on dedup
   hit. When operators delete + re-ingest the same content,
   the second ingest returns the dead row with
   `is_active=False` and the list endpoint filters it out
   — so the operator sees nothing. Fix: in `_persist`,
   when an inactive dedup hit is found, flip
   `is_active=True` and re-fire `embed_document` to refresh
   chunks. Or scope the dedup uniqueness check to
   `is_active=True`. Latter is simpler.

2. **K6.2 — pre-render validation.** Shell viewset hits
   media-engine and gets back an opaque 400 when
   `spokesperson.portrait_path` or `runway_avatar_id` is
   empty. Should fail fast at the shell side with a
   clearer error message naming the missing field.

3. **K6.3 — brief length cap.** gpt-5-mini synthesis could
   exceed media-engine's 2000-char brief cap (today's
   synthesis was 447 chars, but a verbose prompt could push
   it past). Add a clamp + truncate-with-warning in
   `script_synthesis.py`.

4. **K6.4 — duration matching.** Media-engine defaults to
   `duration=5s`. A 30-second synthesized script needs a
   longer render. Should derive from script word count
   (~140 wpm ÷ 60 ≈ 2.3 wps, so 100 words → 43s).

5. **K7.1 — cost telemetry surface.** Per-chunk
   `embedding_cost_micros` is stored but no UI shows it.
   Operators can't see how much an ingest cost them.

---

## Calibration carried forward

- **Live UI testing surfaces issues that 145 passing tests
  miss.** The K6 render-path audit is the headline example.
  Every backend test was hitting the mock pipeline; every
  e2e was running mock-mode. The "5 second silent clip"
  problem was structurally impossible to catch without an
  operator actually rendering a real video and watching it.
  **Lesson for K6.5 and beyond:** when wiring external-API
  pipelines, the operator's eyeball on the output is the
  test that matters. Mock tests prove the wiring exists;
  only real-mode tests prove the wiring is correct.

- **The "read u-d-b / predecessor first" pattern paid out
  again — but this time *because* I didn't.** K6 (SESSION
  139) wired through `runway_client.create_task` because
  that was the most obvious media-engine path. I didn't
  read `character_host_client.py` carefully enough to
  notice `/v1/avatar_videos` existed as the talking-head
  endpoint. **Lesson:** when porting a pipeline, search
  the predecessor for the *output shape* you want
  ("talking head", "lip sync", "speech"), not just the
  *input shape* ("video render").

- **K4.1 was a small slice that earned its keep.** The user's
  framing was perfect: "I don't know exactly everything I
  just ingested." 30 minutes of work produced the
  audit-trail UI that exposed (a) what got extracted and
  (b) which chunks the spokesperson will see at retrieval.
  Without it, K6.5 testing will be substantially harder
  (operator needs to know which chunks contributed to a
  synthesis).

- **Three force-mock flags + four real API keys = the
  matrix of dev modes.** This session validated that
  EMBEDDING_FORCE_MOCK + RENDER_SCRIPT_FORCE_MOCK +
  SERPER_FORCE_MOCK can be flipped independently. The
  operator can run mostly-real (RUNWAY + SERPER + OpenAI)
  for high-fidelity testing, or all-mock for offline dev.
  Worth documenting this matrix in
  `docs/POSTGRES_MIGRATION.md` companion or a new
  `docs/DEV_MODES.md`. (Queued.)

---

## Queued investigations (top of the list — K6.5 + cleanups)

See `00-START-NEXT-SESSION.md` for the full priority list.
Top of stack:

1. **K6.5 — Talking-head render rewire** (avatar_videos
   pipeline). See "Next" section in start-here for the
   shape.
2. **K4.2 — Dedup-restore bug** (~15 min quick fix).
3. **K6.2 — Pre-render validation** (~10 min quick fix).

K6.5 will probably want K4.2 + K6.2 landed first as
ground-clearing.

---

## AI Notes

- **The audit was the highest-leverage moment of the
  session.** When the operator asked "let's do a double
  check for anything that might've been a 'known issue'
  that wasn't addressed before we got to this point," that
  was an invitation to be honest about K6's gap rather
  than charge into K8. I was about to suggest "let's go
  to K8 next" — the operator's framing of "we are about
  to go into the video processing phase" redirected to the
  right priority.

- **What I'd tell SESSION 142 (K6.5) at the start:**
  1. The pattern from SESSIONS 137/139/140 keeps holding:
     **read the predecessor wrapper first**. For K6.5 that
     means `media-engine/app/services/character_host_client.py`
     lines 412-492 (the `_generate_real` function).
  2. The shell side doesn't need changes — it already
     passes `kind`, `avatar_id`, `brief`, `prompt_image`.
     All the work is media-engine routing.
  3. Land K4.2 + K6.2 first (15 + 10 min). They're tiny but
     real, and K6.5 testing depends on them.
  4. Once K6.5 ships, **the operator should personally
     watch one real talking-head video** before declaring
     it shipped. The 145 passing tests didn't catch
     gen4_turbo being the wrong endpoint; only the
     operator's eyeball did.

- **Audit-then-fix is a real product motion.** Today
  surfaced 5 queued fixes alongside the headline K6.5
  rewire. Treating "what's broken that we don't know
  about" as a session goal in its own right — different
  from "ship the next feature" — gave us a clean
  punch-list for SESSION 142. Worth doing again
  periodically.
