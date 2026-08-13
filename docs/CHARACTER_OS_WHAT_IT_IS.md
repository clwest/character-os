---
title: "Character OS — What It Actually Is"
status: populated
generated: 2026-05-13
last_revised: 2026-07-21 (SESSION 218 P0 — object map + engine-bridge product framing codified atop SESSION 217 EB.0-EB.3 backend; workspace-provisioning narrative corrected; recipe count 18 → 20)
companion_doc: CHARACTER_OS_INVENTORY.md
covers_sessions: "106-218"
---

# Character OS — What It Actually Is

> **Read-order note:** this doc is the conceptual companion to
> [`CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md). The
> inventory is runtime-derived and regenerable — it tells you *what
> exists right now*. This doc tells you *what it all is, why it
> exists, and how it fits together*. When a number disagrees
> between the two, INVENTORY wins.
>
> **Customer journey lock:** the story a first-time small business
> owner lives through — from Discover to Grow the Team — is
> scope-locked in
> [`design/CUSTOMER_JOURNEY_V1.md`](design/CUSTOMER_JOURNEY_V1.md)
> (SESSION 229). That doc sits **above** the feature arcs (K, V,
> R, F, EB, VO) and constrains them: when a feature arc's design
> conflicts with the customer journey, the customer journey wins.
> Chapters 3–5 are designed at story-level altitude; Chapters 0–2
> and 6–7 are higher-level maps pending their own design sessions.

---

## TL;DR — One Sentence

**Character OS** is post-hackathon SaaS infrastructure for
**persistent AI spokespeople** — small businesses create reusable
on-camera identities (powered by Runway's avatar API) that star
across video ads, conversational sessions, and finishing-layer
composites; the launch product is a Django+FastAPI+React stack
with tier-based billing, replacing the single-tenant hackathon
demo it inherited the media engine from.

**Scale:** see [`CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md)
for the canonical numbers (regenerated via
`python manage.py inventory`). Headline shape at SESSION 217:
14 Django apps + 23 models, 173 `/api/*` routes, 124 routes on
the media-engine, 70 migrations, 4 services + Redis (Django +
FastAPI + React SPA + Celery). The 4-step create-spokesperson
wizard ships end-to-end (SESSION 132); the knowledge arc
(K1-K9) gives spokespeople grounded retrieval; the video
composition arc (V0-V18) gives them a 20-recipe composition
pipeline (18 V-arc + `auto_script` from B-2 + `cinematic_visual_extended`
alongside V17.1); the realtime arc (R0-R10 + R6.1) gives them live
two-way WebRTC sessions with persisted transcripts, six
operator-side tools, and a tool-approval-gate UI; the
workspace fabric arc (F0-F10) merges Spokespeople / Knowledge
/ Recipes into one shell; the brand identity arc (V3.0-V3.9)
gives them editorial dark-luxe theming; the engine-bridge arc
(EB.0-EB.3 backend, SESSION 217) lets each customer wire their
own external AI engine to their spokespeople via a per-
workspace `EngineConnection`. Numbers move per slice — always
trust INVENTORY over any quote here. Currently 1-developer /
0-customer; launch target is small-business operators (the
hackathon validated the product shape, this repo is the
productisation).

---

## The Core Idea

The hackathon product (`an earlier hackathon prototype/`) proved that "persistent
spokesperson" is a meaningfully different shape than "one-shot ad
generator" — operators want to define a brand identity once
(portrait + voice + brief) and reuse it across all video output.
Character OS is the launch productisation of that shape: a
**Django shell** that owns customer / billing / workspace state,
a **FastAPI media-engine** that wraps Runway's avatar / video /
voice APIs, and an **eventual SPA** (Phase 3) for the operator UI.

What makes this launch product different from "wrap Runway in a
SaaS":

- **Spokespeople are the unit of work**, not campaigns. The
  hackathon's Campaign → Character → OutputRecord hierarchy was
  refactored to Workspace → Spokesperson → Video (design doc §4)
  because the operator's mental model is "I run brand X, here is
  my spokesperson, render me ads featuring them" — not "I'm
  starting a new campaign from scratch."
- **The media-engine is stateless on the Django side.** Phase 2
  closed the original architectural debt: the FastAPI service no
  longer owns customer-shaped state. Django is the system of
  record; the media-engine is a stateless façade over Runway.
- **Pricing tiers are built in, not bolted on.** Phase 1 shipped
  a Subscription model with HTTP 402 gating on spokesperson +
  video creation. Starter (10 videos / 1 spokesperson), Pro
  (30/3), Agency (unlimited). dj-stripe wiring is queued for when
  the operator has Stripe credentials.

---

## Product object map

Canonical graph (audit
`docs/audit-2026-07-21/10_final_report.md` §4). This is what a
returning reader should see without opening the audit:

```
Workspace                                    ← auto-provisioned at signup
 ├─ Subscription (starter | pro | agency)    ← tier gating everywhere
 ├─ EngineConnection (0 or 1 per engine_kind) ← per-workspace external engine (SESSION 217 EB.0-EB.3)
 ├─ Spokesperson                             ← user-visible root; unit of brand identity
 │   ├─ Composition ← Recipe (template)      ← 20 registered recipes
 │   │   └─ CompositionStep (20 primitives + 3 mocks)
 │   │       └─ output_asset → Asset
 │   ├─ RealtimeSession → RealtimeToolInvocation
 │   │                   → transcript_asset → Asset(TRANSCRIPT)
 │   ├─ ConversationThread → ConversationMessage → ConversationEmbedding
 │   ├─ Video (legacy V6 shim; syncs from Composition.final_asset)
 │   ├─ Script (K6-drafted, approval-gated)
 │   └─ PersonalizedCampaign → PersonalizedRecipient → Composition
 ├─ Asset (workspace-scoped; role: talking_head / broll / transcript / …)
 │   └─ TranscriptHighlight (from Asset(TRANSCRIPT)) → Composition
 ├─ KnowledgeDocument → KnowledgeChunk (pgvector HNSW; retrieval-monopoly)
 └─ PublishBundle → PublishVariant → Composition
```

Load-bearing distinctions:

- **Workspace is a provisioning atom, never a user-visible
  entity.** Users don't "create a workspace"; a workspace is
  minted at signup by `accounts.models.User.post_save`. Any doc
  narrative that implies a manual workspace-creation step is
  stale (audit finding D6).
- **Spokesperson is the closest thing the product has to a
  user-visible root.** Every UI journey starts from either a
  Spokesperson or the Dashboard.
- **EngineConnection is workspace-scoped, not spokesperson-scoped.**
  A single EngineConnection per `engine_kind` per Workspace routes
  every bridge tool invocation from every spokesperson in that
  workspace (SESSION 217 EB.2 resolver).
- **Recipe / Composition / Video overlap by design.** The V6
  shim keeps the legacy `Video` model synced from
  `Composition.final_asset` so the two surfaces coexist while
  the SPA migrates.
- **Script → Campaign** and **PublishBundle → Variant** are the
  two batch-fan-out patterns.
- **Asset is the universal downstream artefact.** It is used
  and produced by almost everything. Follow the R5
  `Asset(TRANSCRIPT)` precedent when adding new roles rather
  than inventing a new persistence model.
- **KnowledgeChunk and ConversationEmbedding live in physically
  separate tables** with a retrieval-module monopoly to prevent
  conversation content leaking into knowledge retrieval.
- **RealtimeToolInvocation is the audit surface for every tool
  call** (native + bridge). It links to `produced_asset` and
  `produced_composition` for native tools; those FKs are
  **always NULL** for bridge tools today. Bridge answer text
  itself is not persisted as of SESSION 217 — durable
  persistence is queued as production-readiness Phase P3.

---

## Engine-bridge product pattern

Character OS is not "marketing-avatar SaaS." It's **the face for
any business's entire AI stack.** SESSION 216 reframed the
bridge tools (`consult_engine`, `query_spider_data`,
`agent_consult`) as the v1 instance of an engine-bridge product
pattern; SESSION 217's EB.0–EB.3 backend arc then turned that
framing into runnable per-workspace configuration:

- The customer already has a brain — agents, spiders,
  knowledge, decision systems — living in their own engine.
- Character OS provides the **face**: a persistent, on-camera
  spokesperson that can hold a live conversation.
- Bridge tools call the customer's external engine mid-conversation
  and surface answers via `BridgeAnswerPanel` on the SPA. The
  avatar is the human anchor; the panel is the data surface.
  Panel-first narration is **intended UX**, not a workaround.
- 24/7 Global AI is the first customer; `a sibling private project`
  is what 24/7's engine side looks like; Rigby is the first
  spokesperson instance of the hookup pattern.

State on this branch (post-SESSION-217 EB.0–EB.3 integration):

| Layer | State |
|---|---|
| Bridge tool implementations exist in code | Yes — 3 tools (`consult_engine`, `query_spider_data`, `agent_consult`) |
| Callable via LLM dispatch during a realtime session | Yes |
| Per-workspace connection config (backend) | **SHIPPED SESSION 217 EB.0-EB.3** — `EngineConnection` model + `resolve_engine_connection()` + `/api/engine_connections/` viewset + `test_ping` action + Pro-tier gate |
| Per-workspace connection config (customer-facing UX) | **Not shipped** — SPA settings panel is EB.4 (queued) |
| Visible to users outside a live session | **No** — tool catalog surface queued as production-readiness Phase P3 item 4.4 |
| Bridge answer creates durable Character OS state | **No** — answer text still not persisted; queued as Phase P3 item 4.2 (target: `Asset(role=BRIDGE_ANSWER)`) |
| Non-realtime bridge invocation | **No** — queued as Phase P3 item 4.5 |
| Tier gating | Bridge tools all at Starter tier today; per-workspace `EngineConnection` requires Pro+. Post-launch item 7.2 revisits bridge-tool tier when a real customer onboards. |

The launch roadmap treats the bridge as **backend-integrated
via EB.0-EB.3 but not yet product-complete for customers**. The
internal production-readiness queue tracks the remaining ship
gates for Phase P3; the queue itself is preserved privately.

Reframe rationale and backend arc detail are captured in the
internal session handoff history (SESSION 216 reframe;
SESSION 217 backend arc; SESSION 218 anchor-doc codification).
The handoffs are preserved privately.

---

## The Layered Architecture

### Layer 1 — Django shell (`shell/`)

The customer-facing service. Owns multi-tenant state, auth,
billing, and the public REST API.

| Component | Count | Purpose |
|---|---|---|
| Django apps | 8 | accounts, spokespeople, videos, conversations, memory, billing, agents, embeddings (last four empty scaffold post-SESSION 112; see inventory for live counts) |
| Models (project-owned) | inventory | Workspace, Membership, Spokesperson, Video, ConversationThread, Subscription |
| REST endpoints | inventory | Workspace / Membership / Spokesperson / Video / ConversationThread CRUD + `/spokespeople/{id}/clone-voice/` action + `/me/` + `/billing/*` |
| Auth backends | 2 | django-allauth (email/password + Google OAuth scaffold) + Django default |
| Tier gating | 3 tiers | Starter / Pro / Agency, enforced via `apps.billing.services` returning HTTP 402 |
| Async task queue | Celery | Redis broker on :6381; `apps.videos.tasks.poll_video_until_terminal` is the first consumer; **Celery Beat** runs `apps.compositions.tasks.sweep_expired_assets` hourly at :07 (SESSION 210) |

Cross-app imports always work through model FK chains, never
direct module imports. The `IsWorkspaceMember` permission class
in `character_os/permissions.py` is the load-bearing multi-
tenant guarantee.

### Layer 2 — FastAPI media-engine (`media-engine/`)

The Runway façade. Imported wholesale from `an earlier hackathon prototype/` via
`git subtree` to preserve the proven Runway integration code,
then extended with a stateless `/internal/*` surface for Django.

| Component | Count | Purpose |
|---|---|---|
| Routes | inventory | ~88 legacy `/api/*` routes (consumed by the an earlier hackathon prototype SPA, still functional) + 4 new `/internal/*` routes (consumed by Django) + 1 health endpoint |
| Services | ~25 | Avatar, voice, image, video, dialogue, memory, polish, broll, music — wrap Runway endpoints with consistent error vocabulary |
| Storage | filesystem only | `media-engine/data/*` — gitignored, regenerable artefacts; legacy state lives here too |
| Mock mode | first-class | Every Runway-backed call short-circuits deterministically when `RUNWAY_API_KEY` is unset |

The legacy `/api/*` surface stays untouched during Phase 2 — the
two consumers (old SPA, new Django) coexist. The legacy routes
can be retired in Phase 3 chunks as the new SPA replaces the
old one.

### Layer 3 — SPA (`web/`)

**Operational after SESSION 132.** Vite + React + TypeScript +
shadcn/ui + Tailwind, session-cookie auth via
`/_allauth/browser/v1/*`, TanStack Query data layer, React Router
routing, Playwright smoke tests (25 specs as of SESSION 132).
Scope locked in `docs/design/SPA_ARCHITECTURE.md` (SESSION 115);
detailed wizard scope in `docs/design/CREATE_SPOKESPERSON_WIZARD.md`
(SESSION 123).

What ships:

| Surface | Status | Source |
|---|---|---|
| Sign-up / sign-in | DONE (SESSION 116) | `routes/sign-{up,in}.tsx` |
| Workspace dashboard (S-09) | DONE (SESSION 118) | `routes/dashboard.tsx` |
| Spokesperson detail (S-10) | DONE (SESSION 118) | `routes/spokespeople/$id.tsx` |
| Create spokesperson — legacy single-form (S-06) | DONE (SESSION 121); behind `?legacy=1` escape hatch after SESSION 132 | `routes/spokespeople/new.tsx::LegacyCreateForm` |
| Make-a-video flow (S-11/S-12) | DONE (SESSION 121) | `routes/spokespeople/$id/render.tsx` + `routes/videos/$id.tsx` |
| Voice-clone affordance on detail page | DONE (SESSION 126) | `components/voice-capture.tsx` |
| **4-step Create-Spokesperson Wizard** | **DONE (SESSIONS 124-132)** — the default at `/spokespeople/new` | `components/spokesperson-wizard.tsx` (see next section) |
| Template tile picker on Step 1 | Pending (W10) | — |
| Hide-on-completion detail page rework | Foundations landed in SESSION 126; full rework pending (W11) | — |

See `SPA_ARCHITECTURE.md` for folder structure + out-of-scope list.

### Infrastructure

- **PostgreSQL** — planned for Phase 2 later slices; SQLite still
  in use for the scaffold (`shell/db.sqlite3`).
- **Redis** — broker (db=0) + Celery result backend (db=1), host
  port 6381 in `infra/docker-compose.yml` (port-shifted to dodge
  other dev Redis instances).
- **Celery** — pulled in early (SESSION 109, originally planned
  for Phase 4) because fire-then-poll video generation requires
  it. Decision context is captured in the internal calibration
  ledger (preserved privately).

---

## The Internal Contract (Django ↔ FastAPI)

The Phase 2 deliverable. The boundary between the two services is
load-bearing — these rules bind every new endpoint:

1. **Pure JSON in, pure JSON out.** Binary payloads (portraits,
   audio) ride as `data:` URIs inside the JSON body.
2. **Stateless across calls.** The media-engine holds no
   customer-shaped state between requests.
3. **Errors normalise to `{error, code}`.**
4. **Mock mode is a first-class output** — every response carries
   `mock_mode: bool`.
5. **Idempotent in mock mode** so smoke tests stay deterministic.

Five verbs ship as of SESSION 125:

| Endpoint | Shape | Latency | Persistence |
|---|---|---|---|
| `POST /internal/avatars/` | Sync | ~20 s real / <1 s mock | `Spokesperson.runway_avatar_id` |
| `POST /internal/voices/` | Sync | ~10 s real / <1 s mock | `Spokesperson.voice_id` |
| `POST /internal/videos/` + `GET .../{task_id}/` | Fire-then-poll via Celery | 60-120 s real / ~12 s mock | `Video.media_engine_task_id` + `output_path` |
| `POST /internal/portrait/` | Sync | ~10-20 s real / <1 s mock | Wizard accumulates client-side (no row until Confirm) |

Full contract: `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.

---

## The Create-Spokesperson Wizard (W1-W9, SESSIONS 124-132)

The central UX of the launch product. Replaces the single-form
operator flow with a 4-step wizard so new operators don't face a
blank Brief textarea + unclear portrait/voice setup. Default at
`/spokespeople/new` after the SESSION 132 flip.

### Step shape

| Step | Component | Inputs | Foundation |
|---|---|---|---|
| 1 — Identity | `Step1Identity` | `name` + `business_brief` (≥8 chars) + `tone_archetype` (5 choices, default `expert`). Inline tone suggestion fires on briefs ≥30 chars via `GET /api/prompts/suggest-tone/`. | W4 (`tone_archetype` field), W6 (form body) |
| 2 — Portrait | `WizardPortraitStep` | Three-mode tabs: Upload (file picker), Camera (`getUserMedia`), Generate (`/api/spokespeople/generate-portrait/` → 4 visual templates × free-text `visual_subject`). | W1 (camera), W2 (`/internal/portrait/`), W3.5 (`visual_subject` field), W7 (composition) |
| 3 — Voice | `<VoiceCapture>` (reused from detail page) | Three-mode tabs: Preset (Runway voice from `voice-presets/`), Upload (audio file), Record (`MediaRecorder`). Optional — "Skip" affordance pre-fills `vincent`. | W3 (voice-capture + clone-voice preset path), W8 (wizard wiring) |
| 4 — Confirm | `Step4Confirm` | Read-only review panel: portrait thumbnail + identity summary + voice summary. Fires the atomic submit: `POST /api/spokespeople/` (with `voice_preset` if applicable) followed by `POST /clone-voice/` if voice mode is upload/record. Tier-limit 402 surfaces as upgrade callout; row creates regardless of clone-voice success (detail-page setup checklist catches partial state). | W9 (submit orchestration + wizard-as-default flip) |

### Reducer shape

`WizardState` matches the eventual create payload, not the UI
grouping:

```ts
interface WizardState {
  step: 1 | 2 | 3 | 4;
  identity: { name; business_brief; visual_subject; tone_archetype }
  portrait: { dataUri; fileName; mime; bytes }
  voice:    { mode; preset; dataUri; fileName; mime; bytes; durationMs }
}
```

Step 2's UI surfaces `visual_subject` next to the portrait picker
even though it lives in the `identity` bag — UI grouping and
backend grouping diverge by design. The Confirm step reads from
one consistent bag.

### Atomicity is at the UX level, not the API level

The submit fires up to two API calls (create + optional
clone-voice). A failed clone-voice doesn't roll back the row — the
operator lands on the detail page with a "Set up voice" affordance
(SESSION 126) waiting for them. A half-created spokesperson with a
missing voice is still useful.

### Mirrored constants

Three SPA-side constants mirror Django + media-engine values
(cross-service imports forbidden per CLAUDE.md):

| Constant | Django | Media-engine | SPA |
|---|---|---|---|
| `TONE_ARCHETYPES` (5) | `Spokesperson.Tone` + `character_os/prompts/brand.py` | — | `web/src/lib/api/spokespeople.ts` |
| `SUPPORTED_VOICE_PRESETS` (30) | `apps/spokespeople/views.py` | `character_host_client.py` (authoritative) | Loaded via `voice-presets/` endpoint |
| `SUPPORTED_PORTRAIT_TEMPLATES` (4) | `apps/spokespeople/views.py` | `character_studio_client.PORTRAIT_TEMPLATES` (authoritative) | `web/src/lib/api/spokespeople.ts` |

Queued #12 in the START doc tracks a `verify_doc_claims --only-drift`
verifier that could keep all three in sync automatically.

### What ships *with* the wizard

- `Spokesperson.visual_subject` field (W3.5, SESSION 127)
- `Spokesperson.tone_archetype` field (W4, SESSION 127)
- `suggest_tone_from_brief()` keyword helper (SESSION 127)
- Camera-capture readyState bug fix (SESSION 126 side-quest)
- Allauth rate-limit DEBUG override (SESSION 131 side-quest)

### What's still ahead

- **W10/W11 — DONE** (SESSIONS 133-134). The wizard arc closed
  with templates + hide-on-completion. The cast went live in
  real-mode in SESSION 136 (all four animal characters bound to
  real Runway avatars in admin@mail.com's workspace).
- **W11.1 + W11.2 — DONE** (SESSIONS 169-170). The
  spokesperson-editing loop closed: persona-fields edit modal,
  voice swap (PATCH live Runway avatar), full avatar rebake.
- **W11.6 — DONE** (SESSIONS 172-173). The workspace-wide
  image generation surface — every operator can produce
  scene / b-roll / product / ad imagery via Stability AI from
  the `/images` route. Two providers, one operator-facing
  surface (`POST /api/images/`): Runway gen4_image for avatars
  (existing wizard path, unchanged); Stability AI for non-
  avatar purposes with 42 ported style presets across 8
  categories. 5th nav item; full library grid with filters,
  detail modal with Regenerate + Delete. See
  `docs/design/MEDIA_GENERATION_V1.md` for the scope-lock.
- **W11.6.5 — DONE** (SESSION 174). Recipe inline image-
  picker. `cinematic_visual` recipe gains an optional
  reference-image field that browses the workspace image
  library; resolver extracts the data URI for IMAGE-type
  assets so the starter's existing `prompt_image: str` param
  works unchanged. Closes the W11.6 arc.
- **W11.6.5.1 / W11.6.5.3 — DONE** (SESSION 174). Asset
  picker labels are human-readable. Asset gains an optional
  `title` CharField; ImageViewSet auto-derives from subject;
  composition runtime auto-derives from composition.name.
  Dropdowns read "Talking-head — Marcus" instead of
  `5cf5ab4e-…mp4?_jwt=eyJh…`.
- **W11.x voice telemetry — DONE** (SESSION 174). Edit
  modal surfaces the `voice_patch: {status, error}` envelope
  from the change-voice action. Operators see whether
  Runway accepted the live PATCH; modal stays open on
  failure with the error message.
- **K7.1 cost telemetry — DONE** (SESSION 174). Workspace
  dashboard's cost panel surfaces per-surface MTD + all-
  time spend (compositions / images / realtime). Three-band
  dollar formatter handles sub-cent → multi-dollar
  precision automatically.
- **K6.4 v2.1 — DONE** (SESSION 174). Sentence-opener
  verifier false-positives ("Today" / "Think Antoninus")
  closed via stoplist additions + multi-word leader
  demotion when the leader is sentence-initial and
  stoplisted.
- **K7.x YouTube ingest reject — DONE** (SESSION 174).
  YouTube URLs + boilerplate-extraction patterns rejected
  up-front with operator-actionable error.
- **K7.x v2 YouTube transcript extractor — DONE**
  (SESSION 175). Replaces v1's rejection with actual
  ingestion via youtube-transcript-api. URLs land as
  knowledge docs with cleaned transcript text; pure music
  / applause markers stripped; per-mode operator-actionable
  errors for TranscriptsDisabled / NoTranscriptFound /
  VideoUnavailable / AgeRestricted / IpBlocked /
  PoTokenRequired. K7.x v3 (oEmbed for real video titles)
  queued.
- **K6.4 v2.2 — DONE** (SESSION 175). Sentence-opener
  stoplist expansion (respect / protect / prepare /
  maintain / include / ensure / verify / etc.) +
  parametrized test. Closes Donny K6 dogfood's
  "Respect HTML" false-positive.
- **W11.x.1 voice swap auto-close fix — DONE**
  (SESSION 175). SESSION 174 voice-telemetry banners
  unmounted in the same React tick they rendered;
  operators saw nothing. Modal now stays open for any
  voice change.
- **W11.x.2 voice preview surface — DONE** (SESSION 175).
  Runway's clone-voice preview_url now plays inline in
  the wizard's final step. Operators hear the cloned
  voice before committing instead of after a $0.25+
  talking-head render.
- **W11.y personality / business_brief split — DONE**
  (SESSION 175). Operator insight: HOW the spokesperson
  speaks should be independently swappable from WHAT
  the business does. New ``personality`` field on
  Spokesperson; K6 + K6.5 + Runway avatar + R-arc
  realtime document all updated to use personality for
  voice + business_brief for facts. Backfill copies
  business_brief → personality for existing rows so
  pre-W11.y renders stay identical until operator splits.
- **W12 — Legacy form retirement**: now ungated since real-mode
  validation happened; queued for whenever.

---

## Phase 4 — four parallel arcs (all complete) + Asset Library v1 (complete)

After Phase 3 closed the wizard arc (W1-W11) and brought the
cast live in real-mode (SESSION 136), Phase 4 opened with
three arcs in parallel and added a fourth (workspace fabric)
mid-flight. Each is scope-locked under its own design doc,
each has a slice plan, each adds capability without forcing
the others to advance in lockstep.

**State as of SESSION 192**: all four Phase 4 arcs complete +
first end-to-end real-Runway marketing video shipped +
**Asset Library v1 arc complete** (9 slices across SESSIONS
185-192, layered atop the four Phase 4 arcs).

| Arc | Status | Scope lock |
|---|---|---|
| Knowledge layer (K0-K10) | K1-K9 done; K10 → F8.1 queued | `docs/design/KNOWLEDGE_LAYER.md` |
| Video composition (V0-V15 + V16/V17/V18 post-closes) | **COMPLETE** (SESSIONS 142-144) + **18/18 recipes REAL-MODE VALIDATED (SESSION 197)** | `docs/design/VIDEO_COMPOSITION_V1.md` |
| Workspace fabric (F0-F10) | **COMPLETE** (SESSION 144) | `docs/design/WORKSPACE_FABRIC_V1.md` |
| Realtime avatar (R0-R10) | **COMPLETE** (SESSIONS 146-157); first marketing video shipped against real Runway SESSION 158 | `docs/design/REALTIME_AVATAR_V1.md` |
| **Asset Library v1 (A0-A8)** | **COMPLETE** (SESSIONS 185-192) — 10-role taxonomy + emit-time stamping + storage-health classifier + paginated browse endpoint + SPA list / detail / role-filtered picker / composition cross-link | `docs/design/ASSET_LIBRARY_V1.md` |

All four arcs share one architectural shape — workspace-
anchored data, structural cross-workspace rejection, mock-mode
at the right granularity, the Asset table from V1 as the
common persistence surface. The doc that captures the shape
across all three is the V0 scope lock
(`docs/design/VIDEO_COMPOSITION_V1.md` §"Contract rules") —
the contract rules there are a superset of what each arc
imposes.

> **Canonical runtime state lives in
> [`docs/CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md).
> The sections below describe each arc's shape + key shipped
> capabilities.**

### Arc 1 — Knowledge Layer (K0-K10)

**The cast can render videos. They have nothing to talk about.**

`business_brief` is a *style guide* for HOW each spokesperson
sounds — not a *knowledge base* for WHAT they know. Without a
knowledge layer, every render relies on the LLM hallucinating
product details from the prompt + the spokesperson's tone.

Scope-locked SESSION 137 (`docs/design/KNOWLEDGE_LAYER.md`).
**K1-K9 shipped** plus an architectural refinement (R6.1)
in SESSION 152:

- **K1-K7** (SESSIONS 138-142) — Postgres + pgvector,
  KnowledgeDocument + KnowledgeChunk schema, ingestion
  (paste / PDF / URL / serper search), workspace +
  spokesperson visibility surfaces, render-flow RAG
  integration (`build_render_brief`).
- **K8** (SESSION 145) — `embed_message` Celery task +
  post-save signal that backfills
  `ConversationEmbedding` rows.
- **K9** (SESSION 145) — `POST /api/conversations/<id>/messages/`
  with server-synchronous LLM synthesis +
  `character_os/conversation_synthesis.py` mirroring K6
  + SPA chat route at `/conversations/<id>` +
  "Conversations" panel on the spokesperson detail page.

K-arc state: 9 of 10 slices done; **K10 → F8.1**
(onboarding seed corpus) queued, blocked on
operator-authored markdown. K7.x YouTube ingest fix
queued.

### Arc 2 — Video Composition (V0-V15)

**The hackathon shipped 15+ video kinds, all terminal endpoints.**

SESSION 142's an earlier hackathon prototype pipeline audit surfaced that
every hackathon endpoint is a leaf operation — input goes in,
finished MP4 comes out. There's no notion of one clip being
an *input* to a larger composition. Operators can't ask for
"talking-head + cinematic backdrop + music bed + captions"
because combination isn't a concept the data model holds.

Scope-locked SESSION 142
(`docs/design/VIDEO_COMPOSITION_V1.md`). The architecture:

- **`Asset`** — a generated artifact (clip / audio / image /
  transcript / voice). Workspace-anchored. Reusable.
- **`Composition`** — an ordered sequence of steps producing
  one final Asset. Carries workspace + spokesperson FK.
- **`CompositionStep`** — one step invoking one step
  primitive. Linear ordering (DAG is v2). Partial-failure
  resume per contract rule 6.
- **Step primitives** — named operations (generate speech,
  generate visual, composite, mix audio, add captions,
  etc.). Adding capability = adding a primitive + a starter
  composition. Never an enum value.

**V-arc COMPLETE.** All 16 slices (V0-V15) shipped across
SESSIONS 142-144. The arc closed at:

* **13 step primitives** — `generate_avatar_speech`,
  `generate_visual_clip`, `split_script`,
  `concat_clips`, `composite_video`, `mix_audio`,
  `add_captions`, `add_intro_outro`, `trim_clip`,
  `reformat_clip`, `design_voice`, `dub_audio`,
  `style_remix`, `transcribe`, `generate_image`,
  `audio_extract` (16 listed; the runtime registry
  filters the V2 mock primitives).
* **18 starter compositions** — `talking_head`,
  `cinematic_visual`, `long_form_ad` (launch
  differentiator), 5 layout-modifier starters
  (`pip_layout` / `backdrop_layout` /
  `cohost_layout` / `broll_splice` /
  `music_bed_pass`), `talking_head_with_backdrop`,
  `talking_head_polished`, `reels_format`,
  `voice_design`, `multi_lang_dub` (restores
  hackathon's 29-language dubbing),
  `style_remix_pass`, `recut_teaser` (first
  net-new beyond hackathon), `storyboard_ad`,
  `dialogue_scene`, `storyboard_voiced`.
* **SPA recipe gallery** (V15) at `/recipes` —
  metadata-driven forms; legacy single-form
  CTA retired in F9 while V6 backward-compat shim
  preserves the `Video` model.

**Net-new vs. hackathon-shipped**: V5 (long_form
stitching — no AI provider ships single-call >20s
video), V6 (Video shim), V8 (talking_head_with_backdrop
recipe combines V3+V4+V7), V12 (Whisper — first
non-Runway provider in the media engine).

Two mid-arc reorders (V5 from V7, V9 to V7) both
surfaced the same pattern — latent dependencies
between slices that the original sequence missed.
The discipline became "check the dependency graph of
every prior slice's data shape before locking the
next slice's scope, not just the immediate
predecessor."

### Arc 3 — Workspace Fabric (F0-F10) — COMPLETE

**The platform had three SPA islands (Spokespeople,
Knowledge, Recipes) that didn't talk to each other.**

Scope-locked + shipped SESSION 144
(`docs/design/WORKSPACE_FABRIC_V1.md`). All 10 slices
landed in one extended session. **Zero new persistence**
— the arc consolidates existing surfaces into one
workspace experience.

The shipped shape:
* **Persistent nav rail** (Dashboard / Spokespeople /
  Knowledge / Recipes) replaces the previous
  per-island navigation.
* **Cross-cut dashboard** (`/api/workspace/overview/`)
  surfaces activity feed + knowledge corpus stats +
  spokesperson badges.
* **Knowledge ↔ composition bidirectional graph** —
  `/api/compositions/<id>/lineage/` (asset producers
  + consumers) +
  `/api/knowledge/<id>/compositions/` (reverse-lookup
  of compositions that used a knowledge doc).
* **Brief-mode helper** on recipe forms surfaces K6's
  LLM synthesis output before render.
* **Onboarding walkthrough** (tour banner).
* **Legacy single-form retirement** — the
  `/spokespeople/<id>/render` route was deleted;
  operators now flow through the recipe gallery.

F8.1 (K10 seed corpus) queued — blocked on
operator-authored markdown.

### Arc 4 — Realtime Avatar (R0-R10) — operator-visible product complete

**Operators need to *talk to* their spokespeople, not
just render them.**

The hackathon shipped a working WebRTC realtime flow
against Runway's `/v1/realtime_sessions` endpoint with
`@runwayml/avatars-react` handling the client-side
handshake. Worked for a single operator with no auth,
no workspace scoping, file-based Character storage, and
a Runway-side document corpus separate from the
knowledge layer.

Scope-locked SESSION 142
(`docs/design/REALTIME_AVATAR_V1.md`) under three
constraints the hackathon didn't carry:

1. **Multi-tenant by construction.** Sessions
   workspace-scoped; the Runway API key never reaches
   the frontend (contract rule 3).
2. **Knowledge layer integration.** Runway's
   per-session document corpus is *composed from*
   `KnowledgeDocument` rows via K2's
   `retrieve_for_spokesperson` surface.
3. **Asset-shape persistence.** Transcripts persist
   as `Asset` rows of type TRANSCRIPT. Realtime and
   recorded arcs share one persistence model.

**R1-R8 shipped across SESSIONS 146-155** —
operator-visible product complete. The shipped shape:

* **R1-R5** (SESSION 146) — `RealtimeSession` +
  `RealtimeToolInvocation` schema, media-engine
  provider abstraction, Django broker
  (`/api/realtime_sessions/`) with tier-limit gate,
  knowledge → Runway document bridge
  (`compose_realtime_document`), Celery transcript
  capture (`Asset(TRANSCRIPT)`).
* **R6 + R6.1** (SESSIONS 148, 152) —
  `compose_session_memory` summarizes prior
  transcripts via gpt-5-mini into a
  `## Recent Conversations` section in the
  Runway document body. R6.1 widened the query
  to include mid-session memory snapshots.
* **R7.0-R7.3** (SESSIONS 149-152) — tool dispatch
  foundation + 6-tool catalog. Tools:
  `show_videos_tab` (starter), `recall_knowledge`
  (starter, ~$0.001), `recall_recent_conversations`
  (starter, $0), `handoff_to_spokesperson` (pro,
  $0), `render_video` (starter, $0.08 — over
  $0.05 threshold, exercises the approval flow
  end-to-end), `attach_memory` (pro, ~$0.001,
  mid-session memory commit).
* **R8.0-R8.2** (SESSIONS 153-155) — SPA
  realtime UX. `/spokespeople/:id/talk` route +
  `@runwayml/avatars-react` SDK mount + tool-
  approval modal + cost forecasting + live cost
  ticker + WebRTC fallback messaging. Mock-mode
  UX is a first-class surface so the demo runs
  end-to-end without real Runway creds.

**Q-r-2 partial v1 resolution**: Runway's SDK doesn't
expose a `sendClientEvent` for server-pushed
narration. v1 narration is operator-mediated — modal
decision → operator verbally continues. Audit row's
`error_message` captures the operator's reason for
retrospective review.

**R9 + R10 shipped SESSIONS 156-157** — R-arc closes.
R9 wired the cost governance backend (per-provider
rate table + per-workspace minutes budget alongside
R3's session-count gate + cost_estimate/actual stamps
on session create + end). R10 shipped a 9-test
multi-provider drift verifier — AST analysis catches
bare `raise NotImplementedError` stubs across the
provider registry; package-directory enumeration
catches unregistered new providers.

**SESSION 158 — first real-Runway marketing video**.
Operator-mediated validation: exercised the full
Phase 4 stack end-to-end (K2 retrieval → K6
synthesis → V3 talking_head → V2 Celery → Runway
`/v1/avatar_videos` → Asset persistence). Two renders,
$0.50 total Runway spend, one publishable cut
(Sasha + `clara` voice). Operational calibration
landed: avatar voice × lip-sync quality is a real
operator-visible axis — `drew` voice produced dental
artifacts on Donny's avatar bake; `clara` voice on
Sasha's bake rendered clean. R9's hardcoded
$0.08/min placeholder confirmed accurate within
~5x of real spend.

---

## Phase 5 — strategic-axis arcs (SESSIONS 185-205)

After Phase 4 closed all four parallel arcs, the
codebase had primitives + recipes but not yet the
operator-visible **workflows** that turn primitives
into compounding value. Phase 5 added strategic axes
on top:

* **Asset Library (A-arc, SESSIONS 185-192).**
  `Asset.role` taxonomy + role-filtered SPA browse
  surface + cross-link between Compositions and Assets.
  Operators can now find every clip / image / audio /
  transcript / portrait their workspace has produced
  and filter by intended use (backdrop, talking_head,
  composite_output, etc.).
* **Transcript Miner (B-1, SESSION 202).** R-arc
  transcripts → gpt-5-mini segment selection → operator
  approval gate → re-baked `talking_head_polished`
  per highlight. The realtime sessions that operators
  already paid for now produce 3-5 shareable clips at
  ~$0.001 LLM + standard talking-head cost per clip.
* **Personalized Video (B-3, SESSION 203).** Template
  + CSV → N personalized renders. The B2B sales /
  lifecycle email category at scale; per-workspace
  avatars make this structurally necessary in a way
  generic-LLM-video tools can't deliver.
* **`videos_per_month` cap migration (SESSION 204).**
  Cleanup between strategic arcs — `get_usage()` had
  been reading the legacy V6 Video shim while the
  V/B/C arcs all created Compositions directly. Cap
  was effectively disabled for modern callers (dev
  workspace probe: 2 vs actual 72). Single-function
  fix + 8 pinning tests + the new
  `template_kind="publish_variant"` exclusion seam
  (SESSION 205 D-arc dependency).
* **Publish Bundle (B-14, SESSION 205).** One source
  CLIP → N platform-ready variants
  (Reels/Shorts/TikTok/X/LinkedIn) via the existing
  `reformat_clip` + `trim_clip` primitives. Pure
  ffmpeg, **$0 incremental cost** per variant. The
  distribution-stickiness axis: every B2B customer
  ships to ≥3 platforms.
* **Auto-Scripting (B-2, SESSION 206).** Lifts K6's
  in-primitive script synthesis into a first-class
  persistent artifact — operator types a topic → K2
  retrieves → gpt-5 drafts → K6.4 verifier runs →
  operator reviews citations + flags → operator
  approves → operator fires the render. **Renders
  cannot fire without an approved Script.** Backend
  + SPA shipped one extended session (B2.0-B2.5, six
  commits); the B2.6 dogfood was pulled to its own
  session to preserve real-mode validation quality.
  New `apps.scripts` Django app + `Script` model with
  4-state machine (DRAFT/READY/RENDERED/ARCHIVED) +
  `apps.scripts.synthesis.draft_script` adapter over
  the existing K6 pipeline (zero K6 regressions per
  the adapter-wraps-callable pattern) +
  `auto_script` Composition starter (`use_knowledge=False`;
  the draft is already synthesized at draft-time) +
  20th recipe in the gallery with a new `script_picker`
  field type + `/workspace/scripts` SPA surface. New
  `drafts_per_month` tier gate (Starter=10, Pro=100,
  Agency=∞). The "blank page" friction is now removable.

The five strategic-axis arcs **proved the scope-lock
cadence at 5-for-5** (A/B/C/D/E all opened + landed
their implementation slices in single-session blocks;
B2.6 will close the E-arc dogfood). The full strategic-
axis quartet — B-1 (mine) + B-2 (auto-script) + B-3
(personalize) + B-14 (distribute) — is now operator-
visible and SPA-driven. Composition between arcs (B-2
Script becomes B-3 PersonalizedCampaign template; B-3
launch auto-fires B-14 bundles per recipient) is the
next leverage frontier; the v2 hooks are documented in
each arc's scope-lock doc.

---

## The Unique Stuff

What makes Character OS distinctive vs. "wrap a Runway API key in
Stripe Checkout":

### 1. The media-engine isn't a stub

It carries ten finishing-layer compositors (PR FB → FI in the
hackathon), a working agentic loop (avatar takes spoken commands
and produces the ad), Ollama-based local LLM support, and a real
voice clone pipeline with drift detection. The launch product
inherits all of it via the legacy `/api/*` surface; Phase 2's
internal contract just adds the customer-managed wrapper.

### 2. Stateless service boundary

Most "SaaS that wraps a creative API" implementations end up with
two systems both owning customer state and a slow integration
nightmare. Character OS's Phase 2 deliberately makes the FastAPI
side hold zero customer state — the cost is JSON data URIs for
binary payloads, the reward is that Phase 3 deploy story collapses
to "Django + Postgres + Celery in one place, FastAPI behind it as
a stateless transformer."

### 3. Mock mode end-to-end

Every Runway-backed service degrades cleanly when there's no API
key — the launch product can demo, smoke-test, and develop with
zero Runway spend. The `mock_mode: bool` carries all the way up
through the response chain to the eventual SPA, which can render
a "demo mode" pill.

### 4. Tier-aware from day one

The Subscription model + 402 gating shipped in Phase 1, before any
real customers exist, because gating after launch is a customer-
visible regression. Operators on the trial Starter tier can hit
the cap and the SPA can render a structured upgrade prompt.

### 5. Hermetic smoke tests

Three management commands (`smoke_avatar`, `smoke_voice`,
`smoke_video`) drive each `/internal/*` verb end-to-end with
zero fixture files. Hermetic because they construct their own
in-line WAV / 1×1 PNG payloads.

### 6. Context-kit pattern

The repo uses the `context-kit` framework (orient + handoffs +
two-doc anchor) to keep session-to-session cost low. The full
session-handoff chain is preserved privately; the seven public
case studies under `docs/case-studies/` distill the strongest
engineering-evolution evidence.

---

## Current State Honesty

### Working well (as of SESSION 143, 2026-05-14)

- Django shell + FastAPI media-engine speak the `/internal/*`
  contract across 14 V-arc routes (avatar_speech, visual,
  images, composite, audio mix, captions, intro_outro, trim,
  reformat, concat, style_remix, transcribe, voices/design,
  audio/dub) + the 5 hackathon-imported verbs + the
  generalised `/internal/tasks/{id}/` poll.
- Tier gating returns structured 402 payloads with upgrade
  hints.
- Multi-tenant isolation enforced three ways: `IsWorkspaceMember`
  queryset scoping (legacy + K + V), m2m_changed signals
  for cross-workspace M2M (K2 contract rule 3), pre_save
  signal for cross-workspace Asset references in
  CompositionStep inputs (V1 contract rule 3).
- Hermetic mock-mode for every pipeline: `RUNWAY_FORCE_MOCK`,
  `EMBEDDING_FORCE_MOCK`, `RENDER_SCRIPT_FORCE_MOCK`,
  `SERPER_FORCE_MOCK`. **339 backend tests** + 46 prompts +
  38 e2e specs all green at SESSION 143 close.
- Knowledge layer K1-K7 shipped — operators can ingest
  paste / PDF / URL / serper-search results; renders are
  RAG-informed via gpt-5-mini synthesis + citation logging.
- Video composition arc V0-V13 shipped — 12 step primitives
  registered, 12 starter compositions live, partial-failure
  resume + retry_step + Asset audit trail. Legacy `Video`
  model wraps a `talking_head` composition under the hood
  (V6 shim); SPA contract unchanged.
- Postgres + pgvector running locally via
  `infra/docker-compose.yml`. SQLite drift closed (K1).
- K6.5 closed via V3 — cast members render *speaking* via
  Runway's `/v1/avatar_videos` (`gwm1_avatars`) end-to-end
  in real mode.

### Stale or drifting

- ~~**SQLite still in use**~~ — closed in K1 (SESSION 138).
- ~~**Numbered handoff gap `SESSION_053`**~~ — pre-migration
  cosmetic gap; still flagged by `context-kit orient` but
  the handoffs from an earlier hackathon prototype were spliced in and
  the numbering predates this project.
- ~~**K6.5 talking-head endpoint not yet fixed**~~ — closed
  via V3 (SESSION 143).
- ~~**The legacy `Video` model needs wrapping**~~ — closed
  via V6 (SESSION 143). `Video.create` now creates a
  `talking_head` composition; the Composition→Video
  post_save signal syncs terminal state back to the row.
- **`storyboard_voiced` deferred** — V13 shipped
  `storyboard_ad` but not the voiced variant; needs an
  `audio_extract` primitive (CLIP → AUDIO via ffmpeg `-vn`)
  scheduled for V14+.

### Known issues queued for follow-up

- **Stuck-row janitor** — Celery worker dying mid-poll leaves
  a Video row in `rendering` indefinitely. Same shape
  applies to `Composition.status='running'` after V2.
  Deferred until SPA load creates pressure.
- **Real Runway credentials smoke-tested partially.** The
  three "real API keys present" pre-K7 work confirmed
  Runway + OpenAI + Serper end-to-end. After V3-V13, the
  same keys cover every new `/internal/*` endpoint —
  real-mode end-to-end smoke for the full V-arc is
  pending operator-time.
- **dj-stripe** + real Google OAuth + `allauth.headless` —
  all pending credentials / config from the operator.
- **SPA recipe gallery not yet built** — V15 surfaces the
  composition arc to operators via a card-style picker;
  until then operators drive compositions via admin / CLI /
  the legacy `/api/videos/` shim.

---

## How to Navigate

### The docs to know

Repo-root public docs:

- [`README.md`](../README.md) — 30-second orientation + three
  canonical flows.
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — service boundaries,
  domain model, tenancy, cost governance, state machines,
  provenance.
- [`AI_ASSISTED_DEVELOPMENT.md`](../AI_ASSISTED_DEVELOPMENT.md) —
  honest disclosure of the Chris ÷ Claude Code split.

Runtime-truth anchors (regenerable):

- [`docs/CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md) —
  runtime truth.
- [`docs/CHARACTER_OS_PIPELINE.md`](CHARACTER_OS_PIPELINE.md) —
  runtime flow map.
- [`docs/CHARACTER_OS_BEHAVIOR_LAYER.md`](CHARACTER_OS_BEHAVIOR_LAYER.md) —
  voice / tone / source-of-truth contract.

Design locks (arc contracts referenced from code):

- [`docs/design/MEDIA_ENGINE_INTERNAL_API.md`](design/MEDIA_ENGINE_INTERNAL_API.md) —
  Django↔FastAPI contract.
- [`docs/design/SPA_ARCHITECTURE.md`](design/SPA_ARCHITECTURE.md) —
  SPA scope lock.
- [`docs/design/BRAND_IDENTITY_V1.md`](design/BRAND_IDENTITY_V1.md) —
  v1 visual aesthetic (editorial-warm). Locked SESSION 117.
- [`docs/design/PROMPT_HELPERS.md`](design/PROMPT_HELPERS.md) —
  Tier 1 prompt helpers (Public API of `character_os/prompts/`).
- [`docs/design/CREATE_SPOKESPERSON_WIZARD.md`](design/CREATE_SPOKESPERSON_WIZARD.md) —
  Wizard scope lock (SESSION 123).

Public case studies:

- [`docs/case-studies/`](case-studies/) — seven engineering-
  evolution write-ups distilled from the private handoff history.

(The internal session-handoff chain, the trust-calibration
ledger, and the AI pair-programming rules are preserved
privately and not shipped in this public distribution.)

### Commands to remember

```bash
# Bring up the stack
cd infra && docker compose up -d                           # Redis :6381
cd media-engine && uvicorn app.main:app --port 8001        # FastAPI
cd shell && python manage.py runserver                     # Django :8000
cd shell && celery -A character_os worker --pool=solo      # video pipeline

# Smoke checks
cd shell && python manage.py smoke_avatar
cd shell && python manage.py smoke_voice
cd shell && python manage.py smoke_video

# Health probe
cd shell && python manage.py ping_media_engine
```

### Inventory regeneration

```bash
cd shell && source .venv/bin/activate
python manage.py inventory          # → docs/CHARACTER_OS_INVENTORY.md
python manage.py inventory --dry-run   # preview without writing
python manage.py inventory --json      # machine-readable
```

Probes the live media-engine for FastAPI routes; falls back to a
"unreachable" marker if the FastAPI service isn't running, so the
inventory always regenerates cleanly.

---

## Glossary

| Term | Meaning |
|---|---|
| **Character OS** | The launch product. SaaS for persistent AI spokespeople. |
| **an earlier hackathon prototype** | The pre-launch repo. Frozen at `v-final-pre-migration`; read-only reference. |
| **Spokesperson** | A named on-camera identity belonging to a workspace. Has a Runway avatar + voice. Replaces the legacy `Character` model. **User-visible root** — every SPA journey starts from a Spokesperson or the Dashboard. |
| **Workspace** | Top-level multi-tenant root. Owns spokespeople, videos, conversations, and one `EngineConnection` per engine kind. **Auto-provisioned at signup** via `accounts.models.User.post_save`; never a user-visible creation step. |
| **Membership** | User ↔ Workspace join with a role (`owner` in v1; `admin` / `editor` reserved for the Agency tier). |
| **EngineConnection** | Per-workspace record (unique on `(workspace, engine_kind)`) storing the URL + token that bridge tools use to reach a customer's external engine. Shipped SESSION 217 EB.1 (`apps.realtime.models`); resolved by `apps.realtime.engine_bridge.resolve_engine_connection(workspace)` with an env-var fallback for the legacy hardcode. Pro-tier-gated. Answer persistence + non-realtime UI still queued (production-readiness P3). |
| **Engine-bridge pattern** | The v1 hookup pattern (SESSION 216 reframe; SESSION 217 backend) — a Character OS spokesperson calls a customer's external engine (agents/spiders/knowledge) via HTTP tools; the SPA `BridgeAnswerPanel` renders the structured answer while the avatar acts as the human anchor. See §"Engine-bridge product pattern" above. |
| **/internal/*** | The Phase 2 contract surface on the FastAPI media-engine. Pure JSON, stateless, consumed only by Django. |
| **/api/*** | The legacy hackathon surface on FastAPI. 102 routes. Consumed by the an earlier hackathon prototype SPA; still functional during transition. |
| **Mock mode** | The state of the media-engine when `RUNWAY_API_KEY` is unset. Every Runway-backed call short-circuits with deterministic stub responses. |
| **Tier** | One of `starter` / `pro` / `agency`. Defines spokesperson + video creation caps. Enforced via HTTP 402. |
| **Fire-then-poll** | The video generation shape: `POST /internal/videos/` returns immediately with a task id; a Celery worker polls until terminal. |
| **Context-kit** | The session-orientation framework this repo uses (internal-only; not shipped in the public distribution). |
| **Knowledge layer** | The K-arc data + retrieval surface. `KnowledgeDocument` + `KnowledgeChunk` in `apps.embeddings`, retrieval through two named functions. Scope lock: `docs/design/KNOWLEDGE_LAYER.md`. |
| **Asset** | V1 unit of generated artifact (clip / audio / image / transcript / voice). Workspace-anchored. Reusable across compositions. |
| **Composition** | V1 ordered sequence of `CompositionStep`s producing one final Asset. Replaces the "one endpoint per output kind" model from the hackathon. Scope lock: `docs/design/VIDEO_COMPOSITION_V1.md`. |
| **Step primitive** | A unit of work the composition runtime can dispatch to (`generate_avatar_speech`, `concat_clips`, `composite_video`, etc.). 16 named primitives in v1; adding capability = adding a primitive, never an enum value. |
| **Starter composition** | A predefined recipe of primitives (`talking_head`, `long_form_ad`, `talking_head_with_backdrop`, etc.). Operator picks a starter, fills inputs, runtime executes. |
| **Long-form** | Multi-minute video output produced by stitching N short clips. **No AI provider ships >20s single-call** — every long-form AI video in the wild is stitched. Lands as V5 (the platform's first launch differentiator). |
| **RealtimeSession** | R-arc model for a live WebRTC conversation with a spokesperson. Sessions are workspace-anchored; Runway API key never reaches the frontend (load-bearing privacy guarantee). Scope lock: `docs/design/REALTIME_AVATAR_V1.md`. |
| **Step primitive registry** | The single source of truth for what step types V2's runtime can dispatch to. Maps a string name (`"generate_avatar_speech"`) to a primitive class. Adding capability = registering a new class. Never an enum value. |
| **Chunked path** | V11 pattern for Aleph's hard ~5s output cap. Source CLIPs >5.5s are server-side split into 5s chunks, parallel-remixed (same seed for coherence), then concat'd. Invisible to the primitive — just one CLIP input + one CLIP output from the runtime's view. |
| **Pre-computation pattern** | V5/V12 starter trick: synchronous LLM work happens at composition-create time (Whisper, sentence-pick, script-split) so the runtime sees a deterministic step plan rather than dynamic step expansion. Honors V0 contract rule 5 (linear ordering only). |
| **Net-new capability** | A composition feature that doesn't restore something the hackathon shipped. V5 (long-form via stitching), V8 (multi-recipe combo), V12 (Whisper transcription + AI editorial cuts) are net-new. Everything else through V13 is restoration under the new architecture. |

---

*Last revised SESSION 143, 2026-05-14. When this doc drifts
from reality, regenerate `CHARACTER_OS_INVENTORY.md` first —
that's the runtime anchor and always authoritative.*
