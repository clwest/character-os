---
title: "Realtime Avatar Architecture — scope lock"
status: active (scope-locked, no code yet)
generated: 2026-05-14 (SESSION 142)
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "MEDIA_ENGINE_INTERNAL_API.md"
  - "VIDEO_COMPOSITION_V1.md"
  - "KNOWLEDGE_LAYER.md"
  - "SPA_ARCHITECTURE.md"
phase: 4
---

# Realtime Avatar Architecture

> **Read first:** `VIDEO_COMPOSITION_V1.md` (the parallel arc;
> R1's data model layers on top of V1's Asset shape — both
> arcs must agree before R1 can ship), `KNOWLEDGE_LAYER.md`
> (Runway documents are composed FROM our existing
> `KnowledgeDocument` corpus, not the reverse), and the
> SESSION 142 runway-hackathon realtime pipeline map (what
> the hackathon shipped, what it didn't, what we have to
> add for SaaS).
>
> **Prior art:**
> `runway-hackathon/backend/app/services/realtime_avatar_client.py`
> (~800 lines, the broker that drives Runway's
> `/v1/realtime_sessions` endpoint with personality +
> document grounding + tool catalog + fallback cascade).
> `runway-hackathon/backend/app/services/documents_client.py`
> (the RAG-document client — separate corpus from
> Character OS's knowledge layer; this doc designs the
> bridge between them).
> `runway-hackathon/backend/app/routers/campaigns.py`
> (the realtime-related routes:
> `/spokesperson-session`, `/realtime-transcript`,
> `/realtime-document`).
> `runway-hackathon/frontend/src/components/RealtimeSpokesperson.jsx`
> (the WebRTC client surface — uses `@runwayml/avatars-react`'s
> `<AvatarCall>` SDK; no SDP negotiation lives in our code).
> `runway-hackathon/frontend/src/realtimeTools.js` (~650 lines,
> 9 tools the avatar's LLM can invoke during a live session —
> render an ad, recall knowledge, attach memory, hand off to
> another character).

---

## Purpose

The cast can already render *recorded* videos (today's Phase
4 work) and will soon compose multi-step renders (the V arc).
But the launch product also needs **live two-way conversations**
with each spokesperson — operators (and eventually their
customers) clicking a "Talk to Sasha" button and having a real
back-and-forth WebRTC call with a Runway-driven avatar that's
grounded in the same workspace knowledge their recorded videos
use.

The hackathon shipped a working WebRTC realtime flow against
Runway's `/v1/realtime_sessions` endpoint with `@runwayml/avatars-react`
handling the client-side handshake. It worked for a single
operator with no auth, no workspace scoping, file-based
Character storage, and a Runway-side document corpus separate
from the knowledge layer.

This arc ports that capability under three constraints the
hackathon didn't carry:

1. **Multi-tenant by construction.** Sessions are
   workspace-scoped; the Runway API key never reaches the
   frontend; tool invocations are workspace-scoped.
2. **Knowledge layer integration.** Runway's per-session
   document corpus is *composed from* the workspace's
   `KnowledgeDocument` rows. Operators don't curate two
   knowledge bases.
3. **Asset-shape persistence.** Transcripts, generated clips,
   and memory snapshots produced during a session land as
   `Asset` rows (V1's shape), addressable later by recorded-
   video compositions. The two arcs share one persistence
   model.

### Why scope-lock first

Realtime work touches more system surface area than any prior
arc:

- WebRTC infrastructure (provider-side; we don't run STUN/TURN
  but we orchestrate the handshake brokering).
- A new persistent session abstraction (lifecycle: create →
  poll-until-ready → live → tear-down → transcript-fetch →
  transcript-persist → memory-compose).
- Tool calling protocol over WebRTC data channels (the avatar's
  LLM invokes backend endpoints mid-conversation; operator sees
  toasts; some tools are fire-and-forget, others block on long
  renders).
- Cost governance (Runway bills per realtime minute — different
  cost model from per-render fixed-cost).
- Cross-session memory (each session's transcript composes into
  the next session's grounding document — the "returning
  operator" loop).
- A second knowledge-corpus shape (Runway's `/v1/documents`
  endpoint is a separate corpus we must keep in sync with our
  `KnowledgeDocument` rows).

A bad architectural decision here locks in either a security
gap (the API key in the frontend), a fork of the knowledge
layer (two corpora to maintain), or a cost cliff (no per-
workspace budget enforcement). Locking the surface before any
code lands matches the discipline of K0 and V0.

---

## Contract rules (load-bearing)

These bind every realtime slice the same way V0's rules bind
every composition slice.

1. **Every `RealtimeSession` has an explicit workspace anchor.**
   `RealtimeSession.workspace` is a required FK (DB-level
   NOT NULL). Workspace is never derivable through
   spokesperson reverse-lookup or inferred from the
   requesting user. Same shape as `Asset.workspace`,
   `Composition.workspace`, `KnowledgeDocument.workspace`.

2. **Every `RealtimeSession` has an explicit spokesperson
   anchor.** Required FK with `PROTECT` (mirrors
   `Composition.spokesperson`). Deleting a spokesperson with
   active or historical sessions requires explicit cleanup.

3. **The Runway API key never reaches the frontend.** All
   provider-side calls go through the media-engine's
   `/internal/realtime_sessions/` endpoint. The frontend
   receives only the per-session `(session_id, session_key)`
   pair — `session_key` is Runway's JWT-shaped token, opaque
   and safe for the browser. Different from typical SaaS
   patterns where API keys leak via env-based config; this
   is one of the highest-severity privacy guarantees in the
   arc.

4. **Transcripts persist as `Asset` rows (`TRANSCRIPT` type).**
   No `RealtimeTranscript` table. The V1 `Asset` shape is the
   one persistence model both arcs share. A session's
   transcript becomes one Asset whose `inline_content` is the
   transcript JSON (turns + speakers + timestamps), whose
   `source_spec` records the session id + provider + duration.

5. **Knowledge integration is one-way.** Runway documents are
   composed FROM `KnowledgeDocument` rows; the inverse never
   happens. The knowledge layer remains the system of record
   for workspace knowledge. The Runway-side document corpus is
   a derived projection refreshed at session-create time. If
   a `KnowledgeDocument` changes mid-session, the change does
   not propagate to the live session — it lands on the *next*
   session.

6. **Tool invocations are workspace-scoped.** When the avatar's
   LLM invokes a tool over the WebRTC data channel, the
   server-side handler validates that the requesting session's
   workspace owns the resource the tool touches. Cross-
   workspace tool invocations are rejected the same way
   cross-workspace asset references are.

7. **Cost ceilings are enforced before session-create.**
   Every workspace has a realtime-minutes budget (tier-
   dependent). The broker checks remaining budget before
   firing the Runway create call. Exhausted budget → 402
   Payment Required, same shape as recorded-video tier limit.
   Per-session length cap is the provider's maximum (5 minutes
   for Runway today) — operator extends by reconnecting, not
   by Runway-side keepalive.

8. **Provider abstraction is one named adapter.** The
   media-engine's realtime layer routes through
   `app/services/realtime_provider/` — a single registry of
   `(create_session, attach_documents, fetch_transcript,
   end_session)` adapters. Runway is the only provider in v1;
   adding a future provider (Synthesia, HeyGen) is a
   single-file addition. No conditional branching on provider
   name elsewhere in the codebase.

9. **Mock mode is a session-level concept.** Same shape as
   composition mock-mode (V0 contract rule 9). A session in
   mock-mode returns a deterministic stub `session_id` +
   `session_key`, runs no WebRTC handshake, and produces a
   canned transcript Asset on "end." Operators see this in the
   SPA via a "demo mode" pill.

10. **Conversation-thread continuity intersects with K8/K9.**
    A `RealtimeSession` references a `ConversationThread`
    (K8's model). Sessions on the same thread accrue context;
    transcripts written by realtime sessions are readable by
    `retrieve_for_thread()` once K8 lands. Until K8 lands, the
    `ConversationThread` FK is nullable — R sessions can run
    standalone. After K8, threading becomes mandatory.

---

## Framing corrections (carried from SESSION 142 conversation)

Three framings the SESSION 141 queue + earlier sessions used
that this doc supersedes:

- **"Real-time WebRTC is v2 nice-to-have" is wrong.**
  V0's first draft put it in "out of scope" alongside DaVinci
  Resolve; operator surfaced mid-session that it's a launch
  requirement. This arc shipped at hackathon and was
  load-bearing for the original product story (operators
  *talk to* their spokespeople, then ask them to render). It
  belongs in Phase 4 alongside the V arc, not in Phase 5+.

- **"Realtime is one big endpoint" is wrong.** The hackathon's
  monolithic `realtime_avatar_client.create_session` did
  personality composition + document grounding + tool catalog
  + fallback cascade in one ~150-line function. Under this
  arc, each concern is a separate composable slice — session
  creation (R2), workspace knowledge → Runway document bridge
  (R4), tool catalog (R7), cost governance (R9). Same
  composability discipline V0 applies to recorded video.

- **"WebRTC is the hard part" is wrong.** Runway provides
  `@runwayml/avatars-react`'s `<AvatarCall>` SDK; the entire
  client-side WebRTC handshake (SDP offer/answer, ICE
  negotiation, media tracks, data channels) is hidden behind
  one React component that takes `(sessionId, sessionKey)`.
  The hard parts are: provider-side key brokering (contract
  rule 3), knowledge composition (R4), cost governance (R9),
  cross-session memory (R6), and workspace-scoped tools
  (R7). Allocate the design effort accordingly.

---

## Data model

### `RealtimeSession`

```python
class RealtimeSession(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)

    # Required anchors — privacy + provenance
    workspace = ForeignKey(
        Workspace, on_delete=CASCADE,
        related_name='realtime_sessions',
    )
    spokesperson = ForeignKey(
        Spokesperson, on_delete=PROTECT,
        related_name='realtime_sessions',
    )

    # Conversation-thread linkage (K8 intersection).
    # Nullable in v1; required once K8 lands.
    thread = ForeignKey(
        'conversations.ConversationThread',
        on_delete=SET_NULL,
        null=True, blank=True,
        related_name='realtime_sessions',
    )

    # Provider abstraction (contract rule 8). Always 'runway'
    # in v1; the field exists so a future migration to a
    # second provider doesn't require a schema change.
    class Provider(TextChoices):
        RUNWAY = 'runway', 'Runway'

    provider = CharField(max_length=20, choices=Provider.choices,
                          default=Provider.RUNWAY)

    # Provider-side identifiers
    provider_session_id = CharField(max_length=200, blank=True, default='')
    # session_key is the JWT-shaped token the SDK uses. NEVER
    # logged. Stored encrypted-at-rest if we ever ship a v2
    # hardening — v1 stores plaintext, scoped by access via
    # workspace membership check on every read.
    provider_session_key = TextField(blank=True, default='')
    provider_document_id = CharField(max_length=200, blank=True, default='')

    # Runway-documents-side identity. Composed from
    # KnowledgeDocument rows + the spokesperson's
    # business_brief at session create time (R4).
    knowledge_chunk_ids = JSONField(default=list, blank=True)

    class Status(TextChoices):
        DRAFT = 'draft', 'Draft'
        CREATING = 'creating', 'Creating'
        NOT_READY = 'not_ready', 'Not Ready'
        READY = 'ready', 'Ready (live)'
        ENDED = 'ended', 'Ended'
        FAILED = 'failed', 'Failed'

    status = CharField(max_length=20, choices=Status.choices,
                        default=Status.DRAFT)
    error_message = TextField(blank=True, default='')

    # Lifecycle timestamps
    started_at = DateTimeField(null=True, blank=True)
    ready_at = DateTimeField(null=True, blank=True)
    ended_at = DateTimeField(null=True, blank=True)
    expires_at = DateTimeField(null=True, blank=True)

    # Cost governance (contract rule 7)
    cost_estimate_micros = PositiveIntegerField(default=0)
    cost_actual_micros = PositiveIntegerField(default=0)
    duration_seconds = PositiveIntegerField(default=0)

    # Mock-mode (contract rule 9)
    mock_mode = BooleanField(default=False)

    # Transcript Asset reference (contract rule 4). Null until
    # the post-session transcript fetch + persist completes.
    transcript_asset = ForeignKey(
        'compositions.Asset',
        on_delete=SET_NULL,
        null=True, blank=True,
        related_name='+',
    )

    created_by = ForeignKey(User, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            Index(fields=['workspace', 'status']),
            Index(fields=['spokesperson', 'created_at']),
            Index(fields=['thread']),
        ]
        ordering = ['-created_at']
```

### `RealtimeToolInvocation`

Audit trail for every tool the avatar invoked during a
session. Lets operators replay "what did the avatar do?"
and gives admins the cost-attribution surface (a tool that
triggered a long video render burns Runway credits; we
record the linkage).

```python
class RealtimeToolInvocation(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4)

    session = ForeignKey(
        RealtimeSession, on_delete=CASCADE,
        related_name='tool_invocations',
    )

    tool_name = CharField(max_length=80)  # e.g. 'recall_knowledge'
    args = JSONField(default=dict, blank=True)

    class Status(TextChoices):
        INVOKED = 'invoked', 'Invoked'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        REJECTED = 'rejected', 'Rejected (cross-workspace)'

    status = CharField(max_length=20, choices=Status.choices,
                        default=Status.INVOKED)
    error_message = TextField(blank=True, default='')

    # If the invocation triggered an Asset / Composition,
    # link it for audit + cost attribution.
    produced_asset = ForeignKey(
        'compositions.Asset',
        on_delete=SET_NULL, null=True, blank=True,
        related_name='+',
    )
    produced_composition = ForeignKey(
        'compositions.Composition',
        on_delete=SET_NULL, null=True, blank=True,
        related_name='+',
    )

    invoked_at = DateTimeField(auto_now_add=True)
    completed_at = DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            Index(fields=['session', 'invoked_at']),
            Index(fields=['tool_name']),
        ]
        ordering = ['session', 'invoked_at']
```

### Cross-arc relationships

```
Workspace
   ├── KnowledgeDocument  (K arc — system of record for knowledge)
   ├── Asset              (V arc — generated artifacts)
   ├── Composition        (V arc — recorded-video pipelines)
   ├── ConversationThread (K8 — text + realtime conversation thread)
   └── RealtimeSession    (R arc — live WebRTC sessions)
         ├── tool_invocations  → RealtimeToolInvocation rows
         ├── transcript_asset  → Asset (TRANSCRIPT type)
         └── thread            → ConversationThread (nullable in v1)
```

The V1 `Asset` shape is the persistence anchor for everything
that comes out of a session: transcripts (`TRANSCRIPT` type),
clips invoked via tools (`CLIP` type), composed memory
snapshots (`TRANSCRIPT` type with a `memory` source_spec
flag). No realtime-specific persistence tables beyond
`RealtimeSession` + `RealtimeToolInvocation`.

---

## Provider abstraction

Single named adapter per contract rule 8. The media-engine
exposes one interface; v1 has one implementation (Runway).

```python
# media-engine/app/services/realtime_provider/__init__.py
class RealtimeProvider(Protocol):
    def create_session(
        self,
        avatar_id: str,
        personality: str,
        start_script: str,
        document_ids: list[str],
        tools: list[ToolDef],
    ) -> SessionCreate: ...

    def poll_session(self, session_id: str) -> SessionState: ...

    def attach_documents(
        self, avatar_id: str, document_ids: list[str],
    ) -> None: ...

    def create_document(
        self, name: str, content: str,
    ) -> DocumentCreate: ...

    def fetch_transcript(
        self, session_id: str,
    ) -> TranscriptResult: ...

    def end_session(self, session_id: str) -> None: ...


# media-engine/app/services/realtime_provider/runway.py
class RunwayRealtimeProvider:
    # Implements every method on Protocol via Runway's
    # /v1/realtime_sessions + /v1/documents + 
    # /v1/avatar_conversations/{id} endpoints.
    ...
```

Adding a future provider (Synthesia, HeyGen, etc.) is one new
file + a registry entry. No code outside the registry should
branch on provider name.

---

## Knowledge integration (R4 — the bridge)

The single most architecturally significant slice. Runway's
`/v1/documents` corpus and our `KnowledgeDocument` corpus must
stay in sync without forking what operators think of as "their
spokesperson's knowledge."

### Flow at session-create time

1. Operator clicks "Talk to Sasha" in the SPA.
2. SPA POSTs `/api/realtime_sessions/` with `{spokesperson_id}`.
3. Django broker:
   a. Authz check (workspace membership, tier limits).
   b. Compose the Runway document body:
      - `Spokesperson.business_brief` (the static identity).
      - `retrieve_for_spokesperson(spokesperson, query="", top_k=30)`
        — pull the top 30 chunks visible to this
        spokesperson via the K2 retrieval surface. No query
        ranking needed at session-create; we hand the avatar
        a broad context window.
      - `realtime_transcript_history` — last N session
        transcripts, summarized via gpt-5-mini (R6).
      - Render to Markdown matching the hackathon's
        `documents_client.build_campaign_brief_markdown`
        shape.
   c. Cap at 40,000 chars (Runway's hard limit) — drop
      lowest-priority sections first (oldest transcripts,
      then knowledge chunks ranked by distance from the
      spokesperson's business_brief embedding).
   d. POST media-engine `/internal/realtime_sessions/` with
      `{avatar_id, personality, document_body, tools}`.
   e. Media-engine creates Runway document (`POST /v1/documents`),
      gets `document_id`.
   f. Media-engine creates Runway session
      (`POST /v1/realtime_sessions`) with
      `{document_ids: [document_id], tools, personality}`.
   g. Returns `{session_id, session_key, expires_at, document_id}`.
4. Django persists the RealtimeSession row with status=CREATING,
   `provider_document_id=document_id`,
   `knowledge_chunk_ids=[<the 30 chunks that fed the doc>]`.
5. SPA polls `/api/realtime_sessions/{id}/` until status=READY.
6. SPA mounts `<AvatarCall sessionId=... sessionKey=...>`.

### Why this shape

- `retrieve_for_spokesperson` is the K2 retrieval surface —
  we reuse it instead of writing a second retrieval path
  (contract rule 5).
- The Runway document is **derived** from `KnowledgeDocument`
  rows — never the reverse. K layer remains the system of
  record.
- Knowledge changes mid-session don't propagate; the doc is
  frozen at session-create. Next session re-composes from
  fresh knowledge.
- `knowledge_chunk_ids` on `RealtimeSession` is the citation
  trail — same shape as `Composition.knowledge_chunk_ids`
  from K6.

---

## Tools surface (R7)

The avatar's LLM invokes tools mid-conversation via WebRTC
data channel events. Each tool is workspace-scoped (contract
rule 6) and routed server-side through `RealtimeToolInvocation`
rows so the cost + audit trail persists.

### v1 tool catalog

Ported from the hackathon's 9-tool default, narrowed and
workspace-scoped:

| Tool name | Purpose | Sync/Async | Workspace gate |
|---|---|---|---|
| `recall_knowledge` | Filter spokesperson's knowledge docs by query; surface 1-3 matches to operator | Sync | Yes — only this spokesperson's visible docs |
| `render_video` | Operator approves a composition fork; fire a `talking_head` (or other starter) Composition via V arc | Async (~30-45s) | Yes — composition workspace must match session |
| `recall_recent_conversations` | Fetch prior transcript summaries for this spokesperson | Sync | Yes — only this workspace's RealtimeSession rows |
| `attach_memory` | Ingest current transcript → compose memory document → publish to Runway → attach to spokesperson for next session | Async (~10-20s) | Yes — workspace-scoped |
| `show_videos_tab` | UI-only nav event — flip operator's SPA to the spokesperson's videos page | Sync | N/A (UI) |
| `handoff_to_spokesperson` | End this session, suggest opening a session with a different spokesperson in the same workspace | Sync | Yes — cross-workspace handoff rejected |

Six tools in v1. Three hackathon tools dropped:
`render_spokesperson_ad` (replaced by the generic
`render_video` against a starter composition),
`auto_write_and_render_ad` (merged into `render_video` with an
`auto_draft=true` param), `auto_write_and_render_long_ad`
(same — long-form is a starter composition kind).

### Operator approval for expensive tools

Hackathon's `render_video` tool was fire-and-forget — the
avatar invoked it and the operator saw a toast. v1 changes
this: any tool whose cost estimate exceeds a workspace-
configurable threshold (default $0.05) requires explicit
operator approval via a modal that pops up in the SPA before
the tool actually fires. The avatar narrates "let me render
that for you, hang on" while the operator clicks Approve.
Cost governance applied to tools, not just sessions.

---

## Cost governance (R9)

Three independent governance layers:

1. **Per-workspace monthly minutes budget.** Tier-defined
   (e.g. Starter: 30 min/mo, Pro: 120 min/mo, Agency:
   unlimited). Enforced at session-create. Exhausted →
   402 Payment Required.

2. **Per-session length cap.** Provider maximum (5 min for
   Runway today). Hard cap; operator must reconnect after.

3. **Per-tool approval threshold.** Workspace-configurable
   (default $0.05). Any tool whose cost estimate exceeds
   threshold requires operator approval mid-session.

### Cost estimation primitives

Per-provider micros-per-second lookups, same shape as V's
per-primitive cost estimators (V Q-v-4). Live cost tracking
during the session updates `RealtimeSession.cost_actual_micros`
every N seconds (via a Celery beat task or on session-end).

---

## SPA integration

The hackathon's `RealtimeSpokesperson.jsx` is the reference;
the production version uses `@runwayml/avatars-react` SDK the
same way. Differences:

- Route lives at `/spokespeople/:id/talk` (a tab on the
  spokesperson detail page, not a global overlay).
- Session-create call gates on workspace membership +
  remaining minutes budget.
- Cost forecasting UI shows "~$0.42 for a 5-min session"
  before the operator clicks Start.
- Tool invocations that exceed approval threshold pop a
  modal: "Sasha wants to render a 30-second ad for you.
  Cost: ~$0.08. Approve / Reject."
- Active session shows live cost ticker.

### `@runwayml/avatars-react` SDK contract

Same as hackathon — we don't own the WebRTC handshake. The
SDK takes `(sessionId, sessionKey)`, opens audio + optional
video, exposes `onClientEvent` for tool invocations and
`onEnd` for session-end. No SDP / ICE / media-track code
lives in our SPA.

---

## Slice breakdown

Like the K and V arcs, R is a sequence of slices that can
land independently. Each slice is ~1-2 sessions.

| Slice | Deliverable | Depends on |
|---|---|---|
| **R0** | Scope lock (this doc) | V1 (Asset shape) |
| **R1** ✓ | `RealtimeSession` + `RealtimeToolInvocation` models + schema + isolation tests. Ships SESSION 146 (`9299dcf`). | V1 |
| **R2** ✓ | Media-engine `/internal/realtime_sessions/` endpoint — provider-abstraction layer + Runway implementation. POST creates session, GET polls. Ships SESSION 146 (`e8eb7d1`). | R1 |
| **R3** ✓ | Django broker: `/api/realtime_sessions/` (POST + GET + DELETE + POST `/end/`), workspace auth + new `check_realtime_session_limit` tier gate, session state machine, Runway provider `end_session` implemented. Ships SESSION 146 (`26378e9`). | R2 |
| **R4** ✓ | Knowledge → Runway document bridge: `compose_realtime_document` (uses K2's `retrieve_for_spokesperson` anchored on `business_brief`), media-engine `POST /internal/realtime_documents/`, Runway `create_document` + `attach_documents` implemented, broker create flow now composes → pushes → persists `provider_document_id` + `knowledge_chunk_ids` + passes `document_ids` into session create. Ships SESSION 146 (`6521451`). | R3, K1-K5 |
| **R5** ✓ | Transcript capture: Runway provider `fetch_transcript` impl, `GET /internal/realtime_sessions/<id>/transcript/`, `apps.realtime.tasks.fetch_transcript_for_session` Celery task fires on broker end, persists `Asset(TRANSCRIPT)` + wires `RealtimeSession.transcript_asset`. Idempotent (replaces stale Asset on rerun). Ships SESSION 146 (`885508d`). | R3 |
| **R6** ✓ | Cross-session memory: `character_os.realtime_memory.compose_session_memory` summarizes the last 3 ENDED sessions' `Asset(TRANSCRIPT)` rows via gpt-5-mini Responses API; injected as a `## Recent Conversations` section between `## About` and `## Knowledge` in the R4 document body; drops first under the 40k budget per scope-lock priority; sixth `*_FORCE_MOCK` flag (`REALTIME_MEMORY_FORCE_MOCK`). +14 tests. Ships SESSION 148 (`dbb22e0`). | R5, K8 (parallel) |
| **R7.0** ✓ | Tool catalog foundation: `apps/realtime/tools/` registry with `register_tool` decorator + `ToolSpec` shape, `apps/realtime/dispatch.py` (`dispatch_tool` + `approve_invocation` + `reject_invocation` + `DispatchResult`), `RealtimeToolInvocation.AWAITING_APPROVAL` status (migration `0002_r7_awaiting_approval_status`), `POST /api/realtime_sessions/<id>/invoke_tool/` action, new `RealtimeToolInvocationViewSet` (retrieve + list + approve + reject at `/api/realtime_tool_invocations/`), workspace property on the invocation model so shared permission resolver finds it, `REALTIME_TOOL_APPROVAL_THRESHOLD_MICROS=50_000` ($0.05) settings fallback. First tool — `show_videos_tab` (UI-only nav event, $0 cost). +22 tests. Ships SESSION 149 (`646c492`). | R3 |
| **R7.1** ✓ | Three sync tools: `recall_knowledge` (RAG against K2 via `retrieve_for_spokesperson`; starter tier; ~$0.001/call), `recall_recent_conversations` (read prior `Asset(TRANSCRIPT)` for this spokesperson, returns per-session previews; starter tier; $0), `handoff_to_spokesperson` (cross-spokesperson nav event with same-workspace gate; **pro tier** — Starter has spokespeople=1 so handoff is meaningless). Tier-aware filtering in `get_workspace_tools(workspace)` via new `tier_required` field on `ToolSpec` + new `apps.billing.services.get_workspace_tier` helper. Defense-in-depth tier check in the dispatcher (403 if workspace tier < tool tier). Resolves Q-r-4. +17 tests. Ships SESSION 150 (`611ae94`). | R7.0, K2, R5 |
| **R7.2** ✓ | Async tool dispatch + `render_video`: new `QUEUED` status (migration `0003_r7_2_queued_status`), generic `execute_tool_invocation` Celery task in `apps/realtime/tasks.py` (resolves invocation + spec, calls executor, links `produced_composition`/`produced_asset`), `dispatch_tool` async branch enqueues Celery (was a stub in R7.0), `approve_invocation` enqueues for async tools. **`render_video`** — fires a composition starter (default `talking_head`; configurable via `args.recipe`); $0.08 cost (over $0.05 threshold so exercises approval flow end-to-end); checks `check_video_limit` tier gate. Bonus — fixes the SESSION 147-deferred INVENTORY Celery undercount bug (call `celery_app.loader.import_default_modules()` in `_collect_celery_tasks`; count goes from 5 → 8). +14 tests. Ships SESSION 151 (`e8564f9`). | R7.0, V starters |
| **R7.3** ✓ | `attach_memory` async tool — Pro tier, ~$0.001/call. Fires `capture_transcript(session)` (shared helper extracted from R5's task body in the same slice; both R5's session-end task and R7.3's mid-session tool now go through one implementation). Returns `{event, asset_id, session_id, status, message}`; generic Celery wrapper links produced_asset to the invocation row. **R6.1** sibling change: `compose_session_memory` query widened to drop the `status=ENDED` filter — now picks up any session with a `transcript_asset` (so READY sessions with mid-session commits surface in next-session memory). Resolves Q-r-8 (cross-session tool side effects: idempotent + last-write-wins). +13 tests (1 net new R6 test from the split + 12 R7.3 tests). v1 tool catalog now complete: 6 tools. Ships SESSION 152. | R7.2 |
| **R8** | SPA `/spokespeople/:id/talk` route + `@runwayml/avatars-react` integration + cost forecasting UI + tool-approval modal | R3, R7 |
| **R9** | Cost governance: per-workspace minutes budget, tier-limit enforcement at session-create, live cost ticker | R2, billing |
| **R10** | Multi-provider abstraction hardening (no new providers shipped; just ensure the registry pattern holds — drift verifier test) | R2 |

Roughly 11 slices, ~10-14 sessions. R1-R3 is the "live
sessions work end-to-end with no knowledge / memory / tools"
arc. R4-R6 is the "knowledge + memory loop" arc. R7-R8 is
the "operator-grade UX" arc. R9 is the "production-safe
cost model" arc.

### Critical path

Two slices are load-bearing for the rest:

- **R2** establishes the provider-abstraction shape. Every
  later slice depends on it.
- **R3** establishes the broker pattern. R4-R8 all extend
  this surface.

R5-R10 parallelize once R3 lands.

---

## Out of scope (explicitly)

- **Operator-defined tools.** v1's tool catalog is fixed at
  6 tools in `apps/realtime/tools/`. Operators cannot define
  custom tools (e.g., "look up SKU in my inventory CSV") in
  v1. v2 may add this as a workspace-configurable surface;
  v1 keeps the catalog narrow for safety auditing.

- **Multi-spokesperson live conversations.** v1 sessions are
  single-spokesperson. The `handoff_to_spokesperson` tool
  ends the current session and proposes a new one; it does
  not bridge two avatars in one WebRTC call. Multi-
  spokesperson dialogue is the V arc's `dialogue_scene`
  composition (recorded), not realtime.

- **Customer-facing realtime sessions.** v1 sessions are
  operator-only — the workspace member talks to their own
  spokesperson. Embedding "talk to my spokesperson" on a
  customer-facing webpage (public chat widget) is Phase 5+
  agency-tier work.

- **Session recording.** v1 captures transcripts only. WebRTC
  media recording (saving the audio/video of the session as
  a clip Asset) is deferred. Runway's API may surface this
  on `/v1/avatar_conversations/{id}/recording` later — if so,
  it slots into R5's transcript persistence without breaking
  the schema.

- **Real-time provider-side memory.** Cross-session memory in
  v1 is *our* projection layer (R6) — we summarize
  transcripts and ship them as a fresh Runway document each
  session. Runway-side persistent memory ("avatar remembers
  prior conversations natively") is not a v1 capability we
  rely on.

- **Tool calling without operator approval.** All expensive
  tools (anything above the workspace's approval threshold)
  require operator approval. Fully autonomous avatar agents
  that fire renders / payments / external actions without
  operator confirmation is not v1 scope.

- **Encrypted-at-rest session keys.** `RealtimeSession.provider_session_key`
  is stored plaintext in v1. JWT-shaped tokens are
  short-lived (5-min expiry) which mitigates the exposure;
  full encryption-at-rest is a v2 hardening.

---

## Open questions (resolve in implementation slices)

- **Q-r-1 — Session-create authorization granularity.** Should
  workspace membership be enough, or do we need a separate
  per-spokesperson permission (e.g., "any member can render
  but only owners can talk live")? Resolve in R3 with the
  billing/tier surface.

- **Q-r-2 — Tool approval modal behavior on rejection.**
  Operator rejects a tool — does the avatar know
  (apologetically pivot)? Lean: yes, send a rejection event
  back over the data channel so the LLM can narrate "OK,
  let me skip that for now." Resolve in R7.

- **Q-r-3 — Document refresh during long sessions.** A 5-min
  session at hackathon never re-fetched documents. If we
  extend to longer sessions later (post-Runway limit raise),
  do we need mid-session document updates? Lean: no — keep
  documents frozen at session-create; mid-session refresh is
  v2 work.

- **Q-r-4 — Per-workspace tool catalog overrides.** A Pro-
  tier workspace gets all 6 tools; a Starter-tier workspace
  might get 3. Where does this gate live? Lean:
  `apps/realtime/tools/__init__.py` exposes a
  `get_workspace_tools(workspace)` function that filters by
  tier. Resolve in R7.

- **Q-r-5 — Transcript turn-level addressability.** A
  transcript Asset's `inline_content` is JSON; do we need
  individual turns to be addressable (e.g., for a future
  "render a clip of what Sasha said at 1:23")? Lean: yes —
  ship turn-level JSON shape now even if no v1 consumer
  uses it. Resolve in R5.

- **Q-r-6 — Memory composition LLM.** R6's transcript
  summarization needs an LLM. gpt-5-mini matches K6's choice
  (Responses API, low reasoning effort). Resolve in R6.

- **Q-r-7 — Returning-operator threshold.** Hackathon's
  "returning operator" cue fires after 1 prior session. Is
  that the right threshold? Operators may want to opt out
  (clean slate every time). Resolve in R6 with operator UX
  feedback.

- **Q-r-8 — Cross-session tool side effects.** If
  `attach_memory` runs at the end of session A, it modifies
  the document attached to session B. Race: session B
  created mid-session A's memory composition sees stale
  state. Lean: composition is idempotent + last-write-wins;
  rare in practice but document the race in R6.

- **Q-r-9 — WebRTC fallback.** If `@runwayml/avatars-react`
  fails to establish the connection (network conditions,
  firewall), what's the operator-facing fallback? Lean:
  show a clear error, suggest they fall back to recorded
  video. No text-chat fallback in v1.

---

## How to verify the realtime guarantees

Before R8 closes, six test cases must pass:

1. **`test_session_create_requires_workspace_membership`**:
   create a session against a spokesperson in workspace A
   while authenticated as a member of workspace B; assert
   403.

2. **`test_session_key_never_exposed_in_logs`**: capture all
   log output during a session create + end cycle; assert
   `provider_session_key` value never appears in any log
   line. Defensive — easy to leak via `repr()` or `logger.info(f"{session}")`.

3. **`test_runway_document_composed_from_knowledge_only`**:
   ingest a workspace knowledge doc, create a session; assert
   the document body sent to Runway contains chunk text from
   the ingested doc and *no* text from other workspaces'
   docs (mock Runway, capture the POST body).

4. **`test_tool_invocation_rejects_cross_workspace_resource`**:
   session in workspace A invokes `render_video` with a
   composition_id from workspace B; assert
   `RealtimeToolInvocation.status=REJECTED`,
   error_message identifies the workspace mismatch.

5. **`test_session_create_blocked_by_tier_limit`**: a workspace
   at its monthly minutes cap attempts session create; assert
   402 Payment Required with structured upgrade payload.

6. **`test_transcript_persists_as_asset`**: end a session;
   assert a new `Asset(asset_type=TRANSCRIPT, workspace=...)`
   exists, `RealtimeSession.transcript_asset` references it,
   `inline_content` is parseable JSON with turn structure.

The six tests are the contract. Implementation can vary; the
tests cannot fail.

---

## Change log

- 2026-05-14 (SESSION 142) — Initial scope lock. Triggered
  by SESSION 142 mid-session reframe: operator pulled
  real-time WebRTC from VIDEO_COMPOSITION_V1.md's "out of
  scope" list back into Phase 4 as a parallel arc. Locked
  10 contract rules, two-table data model (RealtimeSession
  + RealtimeToolInvocation) sharing V1's Asset persistence,
  provider-abstraction registry pattern, knowledge-layer
  one-way bridge (Runway documents composed from
  KnowledgeDocument rows), 6-tool catalog (down from
  hackathon's 9, narrowed for safety + scope), tier-aware
  cost governance with three independent layers (per-
  workspace budget + per-session length cap + per-tool
  approval). Six verification tests named. R0-R10 sequenced.
  R1 unblocked by V1 shipping in the same session
  (commit `68561fd`).

  Three framings the queue used that this lock supersedes:
  realtime is launch product (not v2), realtime is
  composable not monolithic (R2-R9 are independent slices),
  and WebRTC mechanics aren't the hard part (the SDK
  handles it) — the hard parts are key brokering,
  knowledge composition, cost governance, cross-session
  memory, and workspace-scoped tools.

- 2026-05-15 (SESSION 152) — **R7.3 SHIPPED + R6.1
  shipped + v1 tool catalog complete**. The realtime
  tool catalog reaches its v1 spec at six tools across
  starter + pro tiers. R6.1 (widening R6's memory
  query) lands as a sibling change in the same commit
  because `attach_memory`'s value depends on it.

  R6.1 (`character_os/realtime_memory.py`):

  * Dropped the `status=ENDED` filter from
    `compose_session_memory`'s query. Keeps the
    `transcript_asset__isnull=False` gate. Any session
    with a transcript snapshot surfaces in
    next-session memory, regardless of status. Edge
    case — a FAILED or crashed session that
    somehow has a transcript still surfaces — the
    operator-facing payoff is minor and architectural
    simplicity is worth it.
  * R6's prior test
    `test_non_ended_sessions_excluded` (asserted
    READY sessions are filtered out) rewritten to
    `test_non_ended_sessions_with_transcript_included`
    (asserts the opposite). New sibling test
    `test_sessions_without_transcript_still_excluded`
    confirms the asset gate still holds.

  Capture helper (`apps/realtime/tasks.py`):

  * New `capture_transcript(session) -> dict` helper.
    Extracted from R5's `fetch_transcript_for_session`
    Celery task body. Pulls the transcript snapshot
    from media-engine, persists as
    `Asset(asset_type=TRANSCRIPT)` in the session's
    workspace, wires `session.transcript_asset`.
    Idempotent — replaces stale Asset on rerun.
    Status return: `persisted | empty |
    upstream_error`. Never raises (MediaEngineError
    becomes a structured `upstream_error` payload).
  * R5's Celery task body is now a thin wrapper:
    resolve session row → call helper → honor retry
    signal for transient errors. Same external
    behavior; same idempotency guarantees.

  `attach_memory` tool (`apps/realtime/tools/attach_memory.py`):

  * `cost_micros=1_000` ($0.001) — under the $0.05
    approval threshold so executes inline.
  * `is_async=True` — goes through the generic
    Celery task. Network I/O (the media-engine
    fetch) shouldn't block the request handler in
    production.
  * `tier_required="pro"`. Mid-session memory commits
    are a power-user feature for long planning calls;
    Starter operators get end-of-session memory
    automatically via R5.
  * Returns `{event: "memory_committed", asset_id,
    session_id, status, message}`. The generic Celery
    wrapper sees `asset_id` and writes it to the
    invocation's `produced_asset` FK.
  * Operator-facing messages differentiated by
    upstream status: persisted → "I'll remember
    this", empty → "not enough yet", upstream_error
    → "I'll try again at session-end".

  13 new tests in
  `apps/realtime/tests/test_r7_3_attach_memory.py`
  covering `capture_transcript` helper directly (3),
  `attach_memory` tool through dispatch (7: happy path
  with produced_asset linkage, idempotency, empty
  upstream, upstream error, no provider id,
  Starter-blocked-403, cost-below-threshold sanity),
  R6.1 memory loop end-to-end (2: attach_memory →
  next-session R6 picks it up, no-transcript still
  filtered), REST integration (1). Plus 1 net new R6
  test from splitting the prior
  `test_non_ended_sessions_excluded` into two
  (included-with-transcript + excluded-without).

  One `ALLOWED_FILES` whitelist addition on
  `apps/realtime/tests/test_isolation.py`
  (`test_r7_3_attach_memory.py` — seeds sessions +
  creates invocations).

  Test totals: Django 627 → 641 (+14). No new
  migrations, no new Celery tasks, no new media-engine
  routes, no new force-mock flags.

  **v1 tool catalog (6 tools)**:
  * `show_videos_tab` — starter, $0, sync (R7.0)
  * `recall_knowledge` — starter, ~$0.001, sync (R7.1)
  * `recall_recent_conversations` — starter, $0, sync (R7.1)
  * `handoff_to_spokesperson` — pro, $0, sync (R7.1)
  * `render_video` — starter, $0.08, async (R7.2)
  * `attach_memory` — pro, ~$0.001, async (R7.3)

  Three Q-r questions resolved this slice:
  * **Q-r-8** (cross-session tool side effects) —
    `capture_transcript` is idempotent + last-write-
    wins; the race window is the standard media-
    engine fetch delay, not a multi-write merge
    problem.

  R-arc state after R7.3: **R1-R7 done**. R8 (SPA),
  R9 (cost governance), R10 (provider hardening)
  remain. R8 is the operator-visible moment — the
  backend is complete; the SPA wires up the SDK +
  cost forecasting + tool-approval modal against
  the full v1 catalog.

- 2026-05-15 (SESSION 151) — **R7.2 SHIPPED** + `attach_memory`
  deferred to R7.3 + INVENTORY Celery undercount fixed
  (SESSION 147 drift-prevention backlog item 5).

  Why split R7.2 in half: `attach_memory` as originally
  scoped ("ingest current transcript → compose memory
  document → publish to Runway → attach to spokesperson
  for next session") requires R6's query to widen. R6
  currently filters `RealtimeSession` rows by
  `status=ENDED`, which excludes the in-progress
  session `attach_memory` would commit. Wiring it
  end-to-end needs either R6 to accept any TRANSCRIPT
  Asset (not just ENDED-session ones) or a new
  `Asset(MEMORY_SNAPSHOT)` sub-type. Both are
  architectural changes that deserve their own slice
  (R6.1 + R7.3 together). R7.2 ships `render_video`
  only.

  Code changes:

  * `apps/realtime/models.py` — adds `QUEUED` choice to
    `RealtimeToolInvocation.Status`. Migration
    `0003_r7_2_queued_status` (TextChoices metadata only;
    no DDL).
  * `apps/realtime/tasks.py` — new
    `execute_tool_invocation` generic Celery task. One
    task for all async tools; resolves
    `RealtimeToolInvocation` → looks up the spec from
    the registry → calls executor → updates the row to
    SUCCEEDED with `produced_composition` /
    `produced_asset` linkage (read from the executor's
    return payload) or FAILED with the error message.
    Idempotent on terminal rows. Never raises.
  * `apps/realtime/dispatch.py` — async branch now
    actually enqueues Celery (R7.0 was a stub). New
    initial-status logic: `AWAITING_APPROVAL` if
    over threshold, `QUEUED` if async, `INVOKED` if
    sync. `approve_invocation` flips async to `QUEUED`
    and enqueues; sync stays inline. `_maybe_result`
    helper snapshots `produced_composition_id` /
    `produced_asset_id` into the SPA-facing
    `result` dict for SUCCEEDED async invocations.
    `_status_to_state` mapping extended for `QUEUED →
    "queued"`.
  * `apps/realtime/tools/render_video.py` — first
    real async tool. Fires `talking_head` by default;
    operator can override via `args.recipe`. Cost
    `80_000` micros ($0.08) — over the $0.05
    default threshold so the approval flow lands.
    Calls `check_video_limit(workspace)` for the
    per-month tier gate (10 / 30 / unlimited). Calls
    `recipe.starter(...)` to create the Composition
    + `execute_composition.delay(...)` to start the
    V-arc execution chain. Returns
    `{event: "render_video_queued", composition_id,
    recipe, message}`; the Celery task wrapper picks
    up the `composition_id` and writes it to the
    invocation row.
  * `apps/realtime/tools/__init__.py` — registers
    `render_video` (5th tool in the catalog).
  * `apps/accounts/management/commands/inventory.py`
    — `_collect_celery_tasks()` now calls
    `celery_app.loader.import_default_modules()`
    before reading `celery_app.tasks`. Fixes the
    SESSION 147-noted undercount (was 5 because of
    lazy autodiscovery; real count is 8 after R7.2's
    new task lands).

  Test count progression: 613 → 627 (+14). The 14 new
  tests cover the async dispatch path (3: under-
  threshold/over-threshold/approve), the generic Celery
  task (3: failure recording, tool de-registered race,
  terminal-state idempotency), `render_video` (6: happy
  path, missing script, unknown recipe, tier-limit
  exceeded, cost > threshold sanity, recipe override),
  end-to-end REST flow (1), and the inventory undercount
  fix (1).

  Two `ALLOWED_FILES` additions on
  `apps/realtime/tests/test_isolation.py`:
  `test_r7_2_async_tools.py` (seeds sessions + creates
  invocations) and `apps/realtime/tasks.py` (sanctioned
  Celery writer for invocation rows).

  Migrations: 50/50 → 51/51. Sixth Celery task added
  (`realtime.execute_tool_invocation`). One new force-
  mock dependency: tests use `CELERY_TASK_ALWAYS_EAGER`
  so the generic task runs synchronously and assertions
  on final state work without polling.

  Q-r-2 stays partly resolved (rejection narration —
  server-side done R7.0; SPA in R8). Q-r-3 (mid-session
  document refresh) not touched. Q-r-8 (cross-session
  tool side effects) deferred to R7.3 alongside
  `attach_memory`.

  R7.2 ships SESSION 151.

- 2026-05-15 (SESSION 150) — **R7.1 SHIPPED**. Three
  sync tools on top of R7.0's foundation, plus
  tier-aware filtering that resolves Q-r-4.

  Tools:

  * `recall_knowledge` (starter, ~$0.001/call) — RAG
    against K2 via `retrieve_for_spokesperson`.
    Returns `{query, count, matches: [{chunk_id,
    document_id, document_title, text}]}`. Empty
    query → `ValueError` caught by the dispatcher as
    a FAILED audit row. `EMBEDDING_FORCE_MOCK` is
    honored automatically (retrieval module checks
    internally).
  * `recall_recent_conversations` (starter, $0) —
    reads prior ENDED `RealtimeSession` rows with
    attached `Asset(TRANSCRIPT)` for this
    spokesperson. Distinct from R6's
    `compose_session_memory` (which composes a
    summarized projection at session-create time);
    this tool returns per-session previews so the
    avatar can quote a specific prior conversation.
    Excludes the current session by pk so the avatar
    doesn't quote its own in-progress conversation.
    Each preview is capped at 500 chars.
  * `handoff_to_spokesperson` (**pro**, $0) — returns
    a `{event, target_spokesperson_id,
    target_spokesperson_name, message}` nav payload
    the SPA dispatches on. Cross-workspace target →
    `ValueError("not in this workspace")` (message
    intentionally doesn't leak existence of
    other-workspace spokespeople). Same-spokesperson
    target → rejected. Pro-tier-only because Starter
    has `spokespeople=1` in TIER_LIMITS so handoff is
    structurally meaningless.

  Tier infrastructure (Q-r-4 resolution):

  * New `tier_required: str = 'starter'` field on
    `ToolSpec` + matching kwarg on `register_tool`.
  * New `_TIER_RANK` map (`starter=0`, `pro=1`,
    `agency=2`) + `_tier_rank(tier)` defensive
    lookup (unknown tier ranks below Starter so
    misconfigured workspaces can't accidentally
    unlock Pro/Agency tools).
  * `get_workspace_tools(workspace)` now filters by
    `_tier_rank(workspace_tier) >= _tier_rank(
    tool.tier_required)`. Starter sees 3 tools
    (`show_videos_tab`, `recall_knowledge`,
    `recall_recent_conversations`); Pro + Agency see
    4 (adds `handoff_to_spokesperson`). When R7.2
    lands, Starter+Pro both see `render_video` (a
    starter-tier tool gated by the per-month video
    cap, not catalog visibility); Pro+Agency add
    `attach_memory`.
  * Defense-in-depth tier check in
    `dispatch_tool` — even if a buggy SPA POSTs an
    over-tier tool name, the dispatcher rejects with
    `DispatchError(403)`. The catalog filter is the
    primary gate; the dispatcher check is the
    safety net.
  * New public helper `apps.billing.services.get_workspace_tier(
    workspace) -> str`. Lazily creates a Starter
    Subscription if one's missing, matching the rest
    of the billing contract.

  17 new tests in
  `apps/realtime/tests/test_r7_1_sync_tools.py`
  covering tier filtering (4: starter / pro / agency
  catalogs + default tier_required), dispatch tier
  gate (1), `recall_knowledge` (3: happy path,
  empty-query rejection, cross-workspace exclusion),
  `recall_recent_conversations` (4: prior sessions,
  current-session exclusion, ENDED-only filter,
  cross-workspace exclusion), `handoff_to_spokesperson`
  (4: happy path, missing target, same spokesperson,
  cross-workspace rejection), and REST integration
  (1: end-to-end through `POST /invoke_tool/` for
  `recall_knowledge`).

  Pre-existing R7.0 test
  `test_get_workspace_tools_returns_full_catalog`
  renamed to `..._for_agency` and updated to set
  the test workspace's tier to Agency explicitly —
  the original assertion ("catalog returns all
  registered tools unconditionally") no longer
  holds post-R7.1 filtering; Agency tier is the
  one that still sees the full catalog. Two
  `ALLOWED_FILES` additions on
  `apps/compositions/tests/test_isolation.py` +
  `apps/embeddings/tests/test_retrieval_privacy.py`
  (R7.1 tests seed Asset + KnowledgeChunk rows).

  Test totals: Django 596 → 613 (+17). No new
  migrations, no new Celery tasks, no new
  media-engine routes, no new force-mock flags.

  Q-r-4 resolved.

  R7.1 ships SESSION 150.

- 2026-05-15 (SESSION 149) — R7 split into three
  sub-slices and **R7.0 SHIPPED**. The original R7 row
  ("Tool catalog (6 tools, workspace-scoped) +
  RealtimeToolInvocation audit + approval-threshold
  modal") was too big for one session per the
  one-slice-per-session discipline calibrated in
  SESSION 148. Sub-slicing pattern matches V15.0-V15.4
  (foundation → sync tools → async tools). R7.0
  ships the foundation:

  * New `apps/realtime/tools/__init__.py` — registry
    with `register_tool(name, *, description,
    cost_micros, workspace_scoped, is_async)`
    decorator, `ToolSpec` frozen-slotted dataclass,
    `get_tool` / `list_tools` / `get_workspace_tools`
    accessors. The `get_workspace_tools(workspace)`
    function is the seam R7.1 will fill with
    tier-based filtering (Q-r-4).
  * New `apps/realtime/tools/show_videos_tab.py` —
    first tool. UI-only nav event, $0 cost,
    workspace_scoped=False. Returns
    `{event: "show_videos_tab", spokesperson_id: ...}`
    payload the SPA will dispatch on.
  * New `apps/realtime/dispatch.py` —
    `dispatch_tool(session, tool_name, args, *, user)`
    resolves from the registry, gates on workspace
    scope (per contract rule 6), compares cost
    against the v1 approval threshold, creates the
    `RealtimeToolInvocation` audit row, executes
    inline or returns `awaiting_approval`. Threshold
    reads via `getattr(settings,
    'REALTIME_TOOL_APPROVAL_THRESHOLD_MICROS',
    50_000)` so tests can `override_settings` it.
    Executor exceptions are caught + recorded as
    FAILED so the SPA never sees a 5xx from this
    surface.
  * `approve_invocation` + `reject_invocation` —
    operator approval gate. Idempotent on already-
    resolved invocations. Reject records the
    optional `reason` on `error_message` so the SPA
    can narrate it back via the WebRTC data channel
    (resolves Q-r-2 server-side; SPA wiring lands
    in R8).
  * `apps/realtime/models.py` — added
    `AWAITING_APPROVAL = "awaiting_approval"` to
    `RealtimeToolInvocation.Status`. Migration
    `0002_r7_awaiting_approval_status` (TextChoices
    metadata only; no DDL change). Migration count:
    49 → 50. Also added a `workspace` property to
    `RealtimeToolInvocation` so the shared
    `IsWorkspaceMember._workspace_of` resolver finds
    `session.workspace` without traversing an extra
    FK.
  * `apps/realtime/views.py` — new `invoke_tool`
    action on `RealtimeSessionViewSet` + new
    `RealtimeToolInvocationViewSet` with retrieve +
    list (filterable by `?session=<uuid>`) +
    approve + reject actions. Workspace-scoped via
    `session__workspace__memberships__user=user`
    queryset filter.
  * `apps/realtime/urls.py` — registers the
    invocation viewset at
    `/api/realtime_tool_invocations/`.
  * `_serialize_dispatch_result` helper translates
    `DispatchResult` → wire JSON; `result` /
    `error_message` / `reason` fields are
    conditionally omitted based on state.

  Contract rule alignment:

  * Rule 6 (workspace-scoped tools) — preserved:
    every workspace_scoped tool dispatches under
    the session's workspace anchor; cross-workspace
    tool invocations are structurally impossible at
    the view-layer (queryset filter on the session)
    + the audit row's `clean()` rejects
    cross-workspace `produced_asset` /
    `produced_composition` refs (existing R1 guard).
  * Rule 9 (mock mode) — preserved: tools call
    their respective `*_FORCE_MOCK` flags
    internally. The dispatcher is provider-agnostic.

  22 new tests in
  `apps/realtime/tests/test_r7_dispatch.py` covering
  registry (3), `get_workspace_tools` shape, dispatch
  Python-level paths (5: unknown tool, inline
  execute, above-threshold, executor failure, args
  persistence), approval flow (4: execute deferred,
  idempotent, after-deregister, reject + reason +
  idempotent), and REST surface (8: inline execute,
  above-threshold 202, unknown tool 400,
  cross-workspace 404, approve, reject, list-by-
  session, list workspace-scoped).

  Two `ALLOWED_FILES` whitelist additions on
  `apps/realtime/tests/test_isolation.py` — added
  `apps/realtime/tests/test_r7_dispatch.py` (tests
  seed sessions + create invocation rows) and
  `apps/realtime/dispatch.py` (sanctioned writer
  for the audit row — every `dispatch_tool` call
  creates one, workspace-anchored via the session
  FK).

  Test totals: Django 574 → 596 (+22). One new
  migration. Sixth `*_FORCE_MOCK` flag was added by
  R6; R7.0 doesn't add a seventh (no force-mock
  flag needed for dispatch — tools handle their own
  mock state).

  R7.0 ships SESSION 149.

- 2026-05-15 (SESSION 148) — R6 SHIPPED. New
  `shell/character_os/realtime_memory.py` implements
  `compose_session_memory(spokesperson, *, max_sessions=3)`
  — queries prior ENDED `RealtimeSession` rows with
  attached `Asset(TRANSCRIPT)` newest-first, summarizes
  via one `gpt-5-mini` Responses-API call
  (`reasoning_effort='low'`, `max_output_tokens=400`),
  returns `MemoryResult(body, session_ids, used_synthesis,
  model, tokens_*)`. Sixth `*_FORCE_MOCK` flag —
  `REALTIME_MEMORY_FORCE_MOCK` settings/env. Mirrors K6
  + K9 degradation pattern: empty memory on
  no-history / no-key / synthesis-failure (avatar opens
  cold, never crashes). `realtime_document.py` extended
  to inject a `## Recent Conversations` section between
  `## About` and `## Knowledge`; per scope-lock §R4
  priority order, memory drops FIRST under the 40k cap
  budget. `RealtimeDocumentResult` gains
  `memory_session_ids` for the broker's audit trail
  (already-persisted alongside `knowledge_chunk_ids` —
  no schema change). Contract rule alignment: rule 1
  preserved (workspace anchor flows via spokesperson),
  rule 4 preserved (reuses R5's `Asset(TRANSCRIPT)` —
  zero new persistence), rule 9 preserved (force-mock
  shape parity with the other five flags). Opens Q-r-7
  ("returning-operator threshold") with threshold=1 — any
  prior transcript triggers projection; no operator
  opt-out in v1 (deferred to R8 SPA settings). 14 new
  tests in `apps/realtime/tests/test_r6_session_memory.py`
  — full coverage on no-history, force-mock, real-mode
  synthesis, ordering, max_sessions cap,
  ENDED-without-transcript filter, non-ENDED filter,
  no-key degradation, synthesis-failure degradation,
  cross-workspace isolation, composer-injection,
  composer-skip-when-empty, budget-drop-memory-first,
  no-knowledge-with-memory. Three `ALLOWED_FILES`
  whitelist additions (realtime + compositions +
  embeddings isolation guards). Test totals: Django 560
  → 574 (+14). No new media-engine routes; no migrations;
  no new Celery tasks. R1-R6 done; R7-R10 remain.
