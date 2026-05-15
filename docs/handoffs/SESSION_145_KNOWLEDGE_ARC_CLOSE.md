---
title: "Session 145 — K8 + K9 (knowledge arc closes at K9)"
date: 2026-05-14
status: complete
session: 145
previous_handoff: ./SESSION_144_FABRIC_ARC.md
---

# Session 145 — K8 + K9: conversation pipeline lands

## TL;DR

Knowledge arc K1-K9 shipped. The two slices this session:

1. **K8** (`31af09d`) — `embed_message` Celery task +
   post-save signal that fires K8's embedding pipeline on
   every `ConversationMessage` create. Closes the loop K2
   opened in SESSION 138 (schema + retrieval landed then,
   ingestion was deferred). Conversation chunk size locked
   at 500 / 0 per Q-k-1.
2. **K9** (`865c7db`) — Conversation REST surface (`POST
   /api/conversations/<id>/messages/`) with server-
   synchronous LLM synthesis via gpt-5-mini Responses
   API, plus SPA chat route at `/conversations/<id>` and
   a "Conversations" panel on the spokesperson detail
   page. Fourth force-mock flag added
   (`CONVERSATION_REPLY_FORCE_MOCK`) for dev determinism.

Net effect: every spokesperson now exposes "talk to me" as
a top-level capability. The
`ConversationThread`/`ConversationMessage`/`ConversationEmbedding`
schema has existed since SESSION 117/138 but had no UI;
K9 closes that gap.

**Backend test progression**: 449 → 463 (+14 K9). K8 added
11 earlier this session for a net 438 → 463 (+25) across
SESSION 145.

## Commit log

| Commit | Slice | What it shipped |
|---|---|---|
| `31af09d` | **K8** | `embed_message` Celery task + post-save signal on `ConversationMessage` (mirrors K3's `embed_document`). Conversation chunk size 500 / 0 (Q-k-1 resolved). |
| `f8ff7f6` | (back-fill) | K8 commit ref in `KNOWLEDGE_LAYER.md` |
| `865c7db` | **K9** | REST `POST /messages` + GET messages, `conversation_synthesis.py`, SPA chat route at `/conversations/<id>`, Conversations panel on spokesperson detail, `CONVERSATION_REPLY_FORCE_MOCK` flag. |
| `399680e` | (back-fill) | K9 commit ref in `KNOWLEDGE_LAYER.md` + start-here |

This handoff: latest commit.

## What shipped (concrete)

### K8 — message embedding pipeline

* **`apps/conversations/tasks.py`** (new) —
  `embed_message(message_id, ...)` Celery task. Mirrors
  K3's `embed_document` shape: idempotent (wipes prior
  chunks on rerun), retries network-y exceptions,
  returns a telemetry dict with `chunks_created`,
  `total_cost_micros`, `cached_hits`, `status`.
* **`apps/conversations/signals.py`** (new) — post_save
  receiver on `ConversationMessage`. Fires on create
  only (no refire on update — embedding cost paid
  once). Skips `raw=True` fixture loads + empty content.
  Catches broker-unreachable failures so message
  creation can't 500 on a downed Celery.
* **`apps/conversations/apps.py`** — wires the signal
  via `AppConfig.ready()`.
* Conversation chunk size **500 / 0** locked (Q-k-1
  resolved). Doc-style 1000 / 200 would waste tokens on
  short chat turns.
* K0 contract rule 2 holds — only
  `apps.embeddings.retrieval` queries
  `ConversationEmbedding` on the read side; the new
  task is the sanctioned writer. Privacy isolation test
  ALLOWED_FILES extended with code-review notes.
* +11 backend tests covering short/long chunking, empty
  no-op, idempotency, signal per-role (USER +
  SPOKESPERSON), no-refire on update, broker
  resilience, end-to-end `retrieve_for_thread`
  integration, cross-thread isolation.

### K9 — conversation REST + SPA

#### Backend

* **`character_os/conversation_synthesis.py`** (new) —
  `synthesize_spokesperson_reply(thread, user_content)
  → ReplyResult`. Mirrors K6's
  `script_synthesis.build_render_brief` pattern:
  - Calls `retrieve_for_thread` for docs + history.
  - Builds a system prompt anchored on the
    spokesperson's tone + business brief.
  - Calls gpt-5-mini Responses API
    (`reasoning_effort=low`, `max_output_tokens=400`).
  - Graceful degradation on retrieval failure / missing
    `OPENAI_API_KEY` / API error.
  - `CONVERSATION_REPLY_FORCE_MOCK=1` env flag for dev
    determinism. Fourth force-mock alongside
    `RUNWAY_FORCE_MOCK`, `EMBEDDING_FORCE_MOCK`,
    `RENDER_SCRIPT_FORCE_MOCK`.

* **`apps/conversations/views.py`** — extended
  `ConversationThreadViewSet`:
  - `@action(detail=True, methods=["get", "post"],
    url_path="messages")` — list / send.
  - POST: creates user message inside a transaction →
    runs synthesis OUTSIDE the transaction (LLM is slow,
    don't hold a DB lock) → persists spokesperson
    reply inside a second transaction → bumps
    `thread.last_activity_at` (SPA list re-sort
    correctness).
  - Returns `{user_message, spokesperson_message,
    knowledge_chunk_ids}`.
  - Optional `?spokesperson=<id>` filter on the thread
    list.

* **`apps/conversations/serializers.py`** —
  `ConversationMessageSerializer` (new) +
  `ConversationThreadSerializer` grew
  `message_count` + `last_message_preview` (last 160
  chars of the most recent message).

* **+14 backend tests** in `test_k9_messages.py`:
  - Thread create + list (workspace-scoped + spokesperson
    filter)
  - Serializer surfaces `message_count` +
    `last_message_preview`
  - GET messages chronological order + cross-workspace
    rejection
  - POST messages happy path (both user + reply
    persisted, mock-mode reply has known prefix)
  - Empty / overlong content → 400
  - `last_activity_at` bumps after send
  - Cross-workspace send → 404
  - `knowledge_chunk_ids` field present in response
  - K8 ↔ K9 pipeline integration (sent messages produce
    ConversationEmbedding rows on both sides)
  - Unauthenticated → 401/403

#### Frontend

* **`web/src/lib/api/conversations.ts`** (new) — typed
  hooks:
  - `useThreads(options)` / `useThread(id)` —
    workspace-scoped, optional spokesperson filter.
  - `useCreateThread()` — invalidates the list cache on
    success.
  - `useMessages(threadId)` / `useSendMessage(threadId)`
    — send mutation **seeds the cache** with both new
    messages so the chat view renders the reply
    immediately, no refetch flash.

* **`web/src/routes/conversations/$id.tsx`** (new) —
  focused chat view. Message list (auto-scrolls on new
  messages) + composer with Cmd/Ctrl+Enter shortcut.
  Pending bubble shows during synthesis. Empty state
  for fresh threads suggests starter questions.

* **`web/src/routes/spokespeople/$id.tsx`** — new
  `ConversationsPanel` section after Knowledge. Lists
  threads with this spokesperson + a "Start a chat"
  button that creates the thread and navigates to
  `/conversations/<new_id>`.

* **`/conversations/:id` route** wired in `App.tsx`.

* **`web/e2e/conversations.spec.ts`** (new) — light e2e
  covering the not-found state. A fuller spec needs
  wizard interaction + backend force-mock; deferred to
  v1.1.

## Server restart incident (operator-flagged mid-session)

After committing K8, the operator hit a 502 on login.
Root cause: a stale `runway-hackathon/backend` uvicorn
(PID 42016, started Tuesday afternoon) was holding port
:8000. The new character-os Django couldn't bind, so the
SPA's auth POST hit the wrong server.

Resolution: killed the stale uvicorn + a stale Django
parent + the old Celery worker. Restarted Django on
:8000 and Celery (which picked up the new
`conversations.embed_message` task from K8). The
operator then hit a 409 on login — allauth's response
when the browser still has cookies tied to the old
Django session table. Resolved by clearing
`localhost:8000` cookies / incognito.

**Carry-forward**: when restarting Django, ensure
nothing else is bound to :8000 (lsof check), and remind
operators to clear cookies after a Django restart if
they see a 409 on login.

## Calibration moments

### 1. K8 was partly shipped during K2

K0 listed K8 as "ConversationMessage +
ConversationEmbedding models + retrieve_for_thread()".
On opening K8, the discovery: all three of those landed
during K2 in SESSION 138. What was actually missing was
the **ingestion side** — `embed_message` + a signal to
fire it. The K8 work this session shipped exactly that.

**Carry-forward**: before opening a scope-locked slice,
read the affected files first. The "schema only" framing
in the scope lock can mislead when partial work landed
in earlier slices.

### 2. The four `*_FORCE_MOCK` flags now form a family

K9 added `CONVERSATION_REPLY_FORCE_MOCK` as the fourth
member. The family:

| Flag | Mocks |
|---|---|
| `RUNWAY_FORCE_MOCK` | media-engine → Runway calls |
| `EMBEDDING_FORCE_MOCK` | OpenAI embeddings |
| `RENDER_SCRIPT_FORCE_MOCK` | K6 render-time brief synthesis |
| `CONVERSATION_REPLY_FORCE_MOCK` | K9 conversation reply synthesis |

For local dev without API keys, all four belong in the
environment. The settings-flag-beats-env pattern is
consistent across the family — set
`settings.<NAME>=True` in a test override or the env
var in shell.

### 3. The "Try it" patterns now span both arcs

Operator can drive an end-to-end flow that touches every
arc shipped:
1. Sign up → onboarding tour (F8) walks the path
2. Create a spokesperson (Phase 3 wizard)
3. Add knowledge (K3 / K4 / K7) — paste, PDF, URL,
   serper search
4. Render a video (V15 gallery, brief-mode helper from
   F4)
5. Composition status shows lineage (F5) + citations (F6)
6. From the spokesperson detail page, start a chat
   conversation (K9) that pulls the same workspace
   knowledge

The product feel is no longer "three islands" — it's
one workspace.

## Project memories saved this session

None new. The two SESSION 144 memories
(`project_workspace_fabric_merge.md`,
`project_youtube_ingest_silent_failure.md`) plus the
older ones (`feedback_cast_is_example_data.md`,
`feedback_openai_gpt5_responses_api.md`,
`project_hackathon_knowledge_leak.md`) carry through.

## What's next (SESSION 146)

The remaining queue has fewer big items than at SESSION
144 close. Knowledge arc done; fabric arc done; V-arc
done. Candidates:

### Option A — R1+ realtime avatar (recommended)

* **R1** — `RealtimeSession` + `RealtimeToolInvocation`
  schema. Schema-only mirror of V1.
* **R2** — media-engine `/internal/realtime_sessions/`
  + provider abstraction.
* **R3-R10** — broker, knowledge bridge, transcript
  persistence, memory, tools, SPA, cost governance.

This is the live two-way WebRTC arc. R0 scope-locked
SESSION 142. Qualitatively different surface from K9's
post-and-resolve chat — adds streaming audio, real-time
transcript, tool use during the call.

### Option B — K7.x YouTube ingest fix

Small slice. Two layers:
1. Detect-reject silent trafilatura failures
   (extracted content is just navigation shell).
2. Per-host YouTube transcript extractor using
   `youtube-transcript-api`.

Memory at `project_youtube_ingest_silent_failure.md`
has the investigation starting points.

### Option C — F8.1 K10 seed corpus

Blocked on operator-authored
`docs/seeds/character_os/*.md`. Once those land, F8.1
wires migration + signal + Celery task + tests in
~30-60 min.

### Option D — operator-authored corpus + F8.1 in
the same session

If the operator writes the seed markdown live,
F8.1 wiring can land same session. Fastest path to
"new operator workspaces come pre-stocked" feel.

### Recommendation

**R1** — the realtime arc is the only unshipped
top-level capability still scope-locked. R1 is a clean
schema slice that mirrors V1, so it sits well as a
first slice of a new arc. K7.x + F8.1 can each ride a
smaller session and don't block R-arc progress.

If the operator wants to author seed corpus right now,
**F8.1** is the next slice and lands fast.

## AI Notes

* **Slice count vs effort**: SESSION 145 shipped two
  slices but K9 is roughly the size of V15.0 + V15.1
  combined (new endpoint + new SPA route + spokesperson
  detail tab + LLM synthesis module). Session length
  matched that — K8 was ~30 minutes, K9 was ~2.5 hours.

* **The "ingestion was partly shipped" discovery on K8
  is the same pattern as F7's scope-lock optimism
  (SESSION 144)**: scope locks describe intent, but the
  actual implementation has to read what's already
  there first. Both times the calibration was
  "investigate before scoping."

* **The transaction-around-LLM choice in K9**: the
  user message creates inside a transaction so the K8
  signal can fire on commit; the spokesperson reply
  creates inside a *second* transaction because the
  synthesis call can take 1-3 seconds and we don't want
  the DB row lock held that long. The two transactions
  are intentional — splitting them costs nothing in
  consistency (the user message is persisted before
  synthesis starts; the reply lands as a follow-up
  row) and earns concurrency safety.

* **Why no streaming yet**: gpt-5-mini at
  `reasoning_effort=low` runs ~1-3s for the conversation
  reply shape. POST-and-resolve feels fine at that
  latency. SSE/streaming becomes worth it at >5s
  latency or when the operator wants to see token-by-
  token output. Q-k-3 left this open; v1 picks POST.

* **Force-mock family is now four flags** — worth
  noting that when operators run the stack locally
  without any provider keys, they need all four set.
  The CLAUDE.md "How to bring the stack up locally"
  block should probably surface this; deferred to a
  follow-up doc tweak.
