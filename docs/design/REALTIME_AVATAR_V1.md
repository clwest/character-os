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
| **R1** | `RealtimeSession` + `RealtimeToolInvocation` models + schema + isolation tests | V1 |
| **R2** | Media-engine `/internal/realtime_sessions/` endpoint — provider-abstraction layer + Runway implementation. POST creates session, GET polls. | R1 |
| **R3** | Django broker: `/api/realtime_sessions/` (POST + GET + DELETE), workspace auth + tier-limit gate, session state machine | R2 |
| **R4** | Knowledge → Runway document bridge: `compose_realtime_document` (uses K2's `retrieve_for_spokesperson`), media-engine document endpoint, document attached on session-create | R3, K1-K5 (shipped) |
| **R5** | Transcript capture: post-session fetch + persist as `Asset(TRANSCRIPT)`, wire to `RealtimeSession.transcript_asset` | R3 |
| **R6** | Cross-session memory: transcript summarization (gpt-5-mini), `realtime_transcript_history` projection into the next session's document, returning-operator personality cue | R5, K8 (parallel) |
| **R7** | Tool catalog (6 tools, workspace-scoped) + `RealtimeToolInvocation` audit trail + approval-threshold modal | R3, V (for `render_video`) |
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
