---
title: "Character OS — What It Actually Is"
status: populated
generated: 2026-05-13
last_revised: 2026-05-14 (SESSION 142)
companion_doc: CHARACTER_OS_INVENTORY.md
covers_sessions: "106-142"
---

# Character OS — What It Actually Is

> **Read-order note:** this doc is the conceptual companion to
> [`CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md). The
> inventory is runtime-derived and regenerable — it tells you *what
> exists right now*. This doc tells you *what it all is, why it
> exists, and how it fits together*. When a number disagrees
> between the two, INVENTORY wins.

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
`python manage.py inventory`). At time of writing (SESSION 132):
~40 `/api/*` routes in Django, ~94 user-defined routes in FastAPI
(~88 legacy + 5 `/internal/*` + health), 4 services + Redis (Django
+ FastAPI + React SPA + Celery), ~31K LOC across `shell/` +
`media-engine/` + `web/`. The 4-step create-spokesperson wizard
ships end-to-end after SESSION 132. Currently 1-developer /
0-customer; launch target is small-business operators (the
hackathon validated the product shape, this repo is the
productisation).

---

## The Core Idea

The hackathon product (`runway-hackathon/`) proved that "persistent
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
| Async task queue | Celery | Redis broker on :6381; `apps.videos.tasks.poll_video_until_terminal` is the first consumer |

Cross-app imports always work through model FK chains, never
direct module imports. The `IsWorkspaceMember` permission class
in `character_os/permissions.py` is the load-bearing multi-
tenant guarantee.

### Layer 2 — FastAPI media-engine (`media-engine/`)

The Runway façade. Imported wholesale from `runway-hackathon/` via
`git subtree` to preserve the proven Runway integration code,
then extended with a stateless `/internal/*` surface for Django.

| Component | Count | Purpose |
|---|---|---|
| Routes | inventory | ~88 legacy `/api/*` routes (consumed by the runway-hackathon SPA, still functional) + 4 new `/internal/*` routes (consumed by Django) + 1 health endpoint |
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
  it. See `TRUST_CALIBRATION.md` for the decision context.

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
- **W12 — Legacy form retirement**: now ungated since real-mode
  validation happened; queued for whenever.

---

## Phase 4 — three parallel arcs

After Phase 3 closed the wizard arc (W1-W11) and brought the
cast live in real-mode (SESSION 136), Phase 4 opened with
three arcs running in parallel. Each is scope-locked under
its own design doc, each has a slice plan, each adds
capability without forcing the others to advance in lockstep.

The three arcs share one architectural shape — workspace-
anchored data, structural cross-workspace rejection, mock-mode
at the right granularity, the Asset table from V1 as the
common persistence surface. The doc that captures the shape
across all three is the V0 scope lock
(`docs/design/VIDEO_COMPOSITION_V1.md` §"Contract rules") —
the contract rules there are a superset of what each arc
imposes.

### Arc 1 — Knowledge Layer (K0-K10)

**The cast can render videos. They have nothing to talk about.**

`business_brief` is a *style guide* for HOW each spokesperson
sounds — not a *knowledge base* for WHAT they know. Without a
knowledge layer, every render relies on the LLM hallucinating
product details from the prompt + the spokesperson's tone.

Scope-locked SESSION 137 (`docs/design/KNOWLEDGE_LAYER.md`).
**Seven slices shipped through SESSION 142:**

- **K1** Postgres + pgvector migration (the SQLite drift
  finally closed)
- **K2** `KnowledgeDocument` + `KnowledgeChunk` models, two
  named retrieval functions, repo-level isolation test
- **K3** Ingestion pipeline — paste + PDF upload, Celery
  embed task, content-hash dedup
- **K4** Workspace knowledge route (SPA + REST) +
  **K4.1** detail view + **K4.2** dedup-restore bug
- **K5** Spokesperson "Knowledge" tab — per-spokesperson
  visibility via M2M attach/detach
- **K6** Render flow integration — `build_render_brief`
  pipes RAG chunks into the script before media-engine
  fires; citations log on the Video row + **K6.2**
  pre-render portrait validation
- **K7** URL ingestion + serper discovery — `trafilatura`
  fetch + serper.dev search → same ingestion pipeline

Remaining: **K8** ConversationMessage + ConversationEmbedding
schema, **K9** conversation REST + SPA, **K10** onboarding
seed (operator-workspace only).

### Arc 2 — Video Composition (V0-V15)

**The hackathon shipped 15+ video kinds, all terminal endpoints.**

SESSION 142's runway-hackathon pipeline audit surfaced that
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
- **Step primitives** — 16 named operations (generate
  speech, generate visual, composite, mix audio, add
  captions, etc.). Adding capability = adding a primitive
  + a starter composition. Never an enum value.

**Three slices shipped SESSION 142:**

- **V0** scope lock — 9 contract rules, 16-slice plan
- **V1** schema — `apps.compositions` app, 13 model tests
- **V2** runtime — `execute_composition` Celery task,
  partial-failure resume, mock-primitive registry, 18
  runtime tests

**V5 promoted from V7 late-session.** No AI provider ships
single-call video longer than ~20 seconds; every long-form
AI video in the wild is stitched. Long-form
(`split_script` + `concat_clips` + `long_form_ad`) is
therefore not a v2 nice-to-have — it's the launch-
differentiating capability. Promoting it to the third
capability slice (right after V3 + V4) positions the
platform's distinctive selling point as early as possible.

New sequence: V3 (generate_avatar_speech, absorbs K6.5) →
V4 (generate_visual_clip) → V5 (long-form) → V6 (backwards-
compat shim) → V7 (talking_head_with_backdrop) → V8-V15.
**V3 is the next slice.**

### Arc 3 — Realtime Avatar (R0-R10)

**Operators (and eventually customers) need to *talk to* their
spokespeople, not just render them.**

The hackathon shipped a working WebRTC realtime flow against
Runway's `/v1/realtime_sessions` endpoint with
`@runwayml/avatars-react` handling the client-side handshake.
It worked for a single operator with no auth, no workspace
scoping, file-based Character storage, and a Runway-side
document corpus separate from the knowledge layer.

Scope-locked SESSION 142 (`docs/design/REALTIME_AVATAR_V1.md`)
under three constraints the hackathon didn't carry:

1. **Multi-tenant by construction.** Sessions workspace-scoped;
   the Runway API key never reaches the frontend
   (load-bearing privacy guarantee — contract rule 3).
2. **Knowledge layer integration.** Runway's per-session
   document corpus is *composed from* `KnowledgeDocument`
   rows via K2's `retrieve_for_spokesperson` surface.
   Operators don't curate two knowledge bases.
3. **Asset-shape persistence.** Transcripts persist as
   `Asset` rows of type TRANSCRIPT. Both arcs share one
   persistence model.

Two new tables (`RealtimeSession` + `RealtimeToolInvocation`),
six tools the avatar's LLM can invoke mid-conversation
(narrowed from hackathon's 9; expensive ones require
operator approval), three-layer cost governance (workspace
minutes budget + session length cap + tool approval
threshold), provider-abstraction registry (Runway is the v1
provider; adding Synthesia/HeyGen is a single-file change).

**R0 scope lock shipped SESSION 142.** R1 (schema) is the
next R-slice and is unblocked by V1.

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
two-doc anchor) to keep session-to-session cost low. Every session
ends with a handoff in `docs/handoffs/SESSION_NNN_*.md` and
overwrites `00-START-NEXT-SESSION.md` for the next session. AI
agents (this assistant) orient against `00-START-NEXT-SESSION.md`
first, then the runtime anchors. Inheritable across operators.

---

## Current State Honesty

### Working well (as of SESSION 142, 2026-05-14)

- Django shell + FastAPI media-engine speak the `/internal/*`
  contract for the five hackathon-imported verbs (avatars,
  voices, videos, portrait, polling) — though `/internal/videos/`
  currently routes to the wrong Runway endpoint (silent
  animated portrait instead of talking-head; closes in V3).
- Tier gating returns structured 402 payloads with upgrade
  hints.
- Multi-tenant isolation enforced three ways: `IsWorkspaceMember`
  queryset scoping (legacy + K + V), m2m_changed signals
  for cross-workspace M2M (K2 contract rule 3), pre_save
  signal for cross-workspace Asset references in
  CompositionStep inputs (V1 contract rule 3).
- Hermetic mock-mode for every pipeline: `RUNWAY_FORCE_MOCK`,
  `EMBEDDING_FORCE_MOCK`, `RENDER_SCRIPT_FORCE_MOCK`,
  `SERPER_FORCE_MOCK`. 133 backend tests + 46 prompts +
  38 e2e specs all green at SESSION 142 close.
- Knowledge layer K1-K7 shipped — operators can ingest
  paste / PDF / URL / serper-search results; renders are
  RAG-informed via gpt-5-mini synthesis + citation logging.
- Composition runtime V2 shipped — `execute_composition`
  walks ordered steps, persists outputs as Assets, supports
  partial-failure resume + retry_step. Mock-primitive
  registry exercises the runtime end-to-end without burning
  Runway credits. Adding a real primitive (V3+) is a
  registry-entry change.
- Postgres + pgvector running locally via
  `infra/docker-compose.yml`. SQLite drift closed (K1).

### Stale or drifting

- ~~**SQLite still in use**~~ — closed in K1 (SESSION 138).
- ~~**Numbered handoff gap `SESSION_053`**~~ — pre-migration
  cosmetic gap; still flagged by `context-kit orient` but
  the handoffs from runway-hackathon were spliced in and
  the numbering predates this project.
- **K6.5 talking-head endpoint not yet fixed** — SESSION 141
  audit identified `/v1/avatar_videos` as the correct
  endpoint; absorbed into V3 (next session). Cast members
  currently render as silent animated portraits, not
  speaking. Don't ship a real-mode demo until V3 lands.
- **The legacy `Video` model is going to be wrapped, not
  retired** — V5 (backwards-compat shim, formerly V6 before
  the SESSION 142 reorder) turns `Video.create` into a
  thin `talking_head` composition wrapper. The
  `/api/videos/` SPA surface stays stable; under the hood
  it'll route through the V2 runtime. V15 (recipe gallery)
  retires the legacy form UX.

### Known issues queued for follow-up

- **Stuck-row janitor** — Celery worker dying mid-poll leaves
  a Video row in `rendering` indefinitely. Same shape
  applies to `Composition.status='running'` after V2.
  Deferred until SPA load creates pressure.
- **Real Runway credentials smoke-tested partially.** The
  three "real API keys present" pre-K7 work confirmed
  Runway + OpenAI + Serper end-to-end, but the K6 render
  hits the wrong endpoint (covered above).
- **dj-stripe** + real Google OAuth + `allauth.headless` —
  all pending credentials / config from the operator.

---

## How to Navigate

### The docs to know

1. [`00-START-NEXT-SESSION.md`](../00-START-NEXT-SESSION.md) —
   what to do right now in this session.
2. [`docs/CHARACTER_OS_INVENTORY.md`](CHARACTER_OS_INVENTORY.md) —
   runtime truth (currently a stub — see drift above).
3. [`docs/CHARACTER_OS_WHAT_IT_IS.md`](CHARACTER_OS_WHAT_IT_IS.md) —
   this doc.
4. [`docs/CHARACTER_OS_PIPELINE.md`](CHARACTER_OS_PIPELINE.md) —
   runtime flow map (entry points, guards, retrieval, scrubs).
5. [`docs/CHARACTER_OS_BEHAVIOR_LAYER.md`](CHARACTER_OS_BEHAVIOR_LAYER.md) —
   voice / tone / source-of-truth contract.
6. [`docs/design/MEDIA_ENGINE_INTERNAL_API.md`](design/MEDIA_ENGINE_INTERNAL_API.md) —
   Django↔FastAPI contract.
6b. [`docs/design/SPA_ARCHITECTURE.md`](design/SPA_ARCHITECTURE.md) —
   Phase 3 SPA scope lock (stack, auth client, API client, first
   three screens).
6c. [`docs/design/BRAND_IDENTITY_V1.md`](design/BRAND_IDENTITY_V1.md) —
   v1 visual aesthetic (editorial-warm). Locked SESSION 117.
6d. [`docs/design/PROMPT_HELPERS.md`](design/PROMPT_HELPERS.md) —
   Tier 1 prompt helpers ported from unified-donkey-betz
   (SESSION 122). Public API of `character_os/prompts/`.
6e. [`docs/design/CREATE_SPOKESPERSON_WIZARD.md`](design/CREATE_SPOKESPERSON_WIZARD.md) —
   Wizard scope lock (SESSION 123). 4-step flow, two-axis
   archetypes (visual + tone), 3-mode voice input, hide-on-
   completion via setup-checklist.
7. [`docs/handoffs/`](handoffs/) — session-by-session build
   history. SESSION 106-110 cover the Phase 1 + Phase 2 work;
   111-123 cover Phase 3 + supporting work.
8. [`docs/TRUST_CALIBRATION.md`](TRUST_CALIBRATION.md) — append-
   only log of AI-vs-operator calibration events.
9. [`CLAUDE.md`](../CLAUDE.md) — AI session entry point + hard
   rules.

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
| **runway-hackathon** | The pre-launch repo. Frozen at `v-final-pre-migration`; read-only reference. |
| **Spokesperson** | A named on-camera identity belonging to a workspace. Has a Runway avatar + voice. Replaces the legacy `Character` model. |
| **Workspace** | Top-level multi-tenant root. Owns spokespeople, videos, conversations. |
| **Membership** | User ↔ Workspace join with a role (`owner` in v1; `admin` / `editor` reserved for the Agency tier). |
| **/internal/*** | The Phase 2 contract surface on the FastAPI media-engine. Pure JSON, stateless, consumed only by Django. |
| **/api/*** | The legacy hackathon surface on FastAPI. 102 routes. Consumed by the runway-hackathon SPA; still functional during transition. |
| **Mock mode** | The state of the media-engine when `RUNWAY_API_KEY` is unset. Every Runway-backed call short-circuits with deterministic stub responses. |
| **Tier** | One of `starter` / `pro` / `agency`. Defines spokesperson + video creation caps. Enforced via HTTP 402. |
| **Fire-then-poll** | The video generation shape: `POST /internal/videos/` returns immediately with a task id; a Celery worker polls until terminal. |
| **Context-kit** | The session-orientation framework this repo uses. See `docs/docs-pattern/`. |
| **Knowledge layer** | The K-arc data + retrieval surface. `KnowledgeDocument` + `KnowledgeChunk` in `apps.embeddings`, retrieval through two named functions. Scope lock: `docs/design/KNOWLEDGE_LAYER.md`. |
| **Asset** | V1 unit of generated artifact (clip / audio / image / transcript / voice). Workspace-anchored. Reusable across compositions. |
| **Composition** | V1 ordered sequence of `CompositionStep`s producing one final Asset. Replaces the "one endpoint per output kind" model from the hackathon. Scope lock: `docs/design/VIDEO_COMPOSITION_V1.md`. |
| **Step primitive** | A unit of work the composition runtime can dispatch to (`generate_avatar_speech`, `concat_clips`, `composite_video`, etc.). 16 named primitives in v1; adding capability = adding a primitive, never an enum value. |
| **Starter composition** | A predefined recipe of primitives (`talking_head`, `long_form_ad`, `talking_head_with_backdrop`, etc.). Operator picks a starter, fills inputs, runtime executes. |
| **Long-form** | Multi-minute video output produced by stitching N short clips. **No AI provider ships >20s single-call** — every long-form AI video in the wild is stitched. Lands as V5 (the platform's first launch differentiator). |
| **RealtimeSession** | R-arc model for a live WebRTC conversation with a spokesperson. Sessions are workspace-anchored; Runway API key never reaches the frontend (load-bearing privacy guarantee). Scope lock: `docs/design/REALTIME_AVATAR_V1.md`. |

---

*Last revised SESSION 142, 2026-05-14. When this doc drifts
from reality, regenerate `CHARACTER_OS_INVENTORY.md` first —
that's the runtime anchor and always authoritative.*
