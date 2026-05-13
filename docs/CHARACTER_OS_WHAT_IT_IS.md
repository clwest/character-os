---
title: "Character OS — What It Actually Is"
status: populated
generated: 2026-05-13
last_revised: 2026-05-13 (SESSION 115)
companion_doc: CHARACTER_OS_INVENTORY.md
covers_sessions: "106-115"
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
`python manage.py inventory`). At time of writing (SESSION 112):
~35 `/api/*` routes in Django, ~93 user-defined routes in FastAPI
(~88 legacy + 4 `/internal/*` + health), 3 services + Redis,
~30K LOC across `shell/` + `media-engine/`. Currently 1-developer /
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

Currently empty scaffold (`.gitkeep` only). **Phase 3 in
progress.** Scope locked in `docs/design/SPA_ARCHITECTURE.md`
(SESSION 115): Vite + React + TypeScript + shadcn/ui + Tailwind,
session-cookie auth via `/_allauth/browser/v1/*`, TanStack Query
data layer, React Router routing, Playwright smoke tests.

First three slices land starting SESSION 116:

1. Sign-up + sign-in (S-03, S-04 of design lock).
2. Workspace dashboard (S-09).
3. Spokesperson detail (S-10).

See `SPA_ARCHITECTURE.md` for the full scope lock + folder
structure + out-of-scope list.

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

Three verbs ship as of SESSION 110:

| Endpoint | Shape | Latency | Persistence |
|---|---|---|---|
| `POST /internal/avatars/` | Sync | ~20 s real / <1 s mock | `Spokesperson.runway_avatar_id` |
| `POST /internal/voices/` | Sync | ~10 s real / <1 s mock | `Spokesperson.voice_id` |
| `POST /internal/videos/` + `GET .../{task_id}/` | Fire-then-poll via Celery | 60-120 s real / ~12 s mock | `Video.media_engine_task_id` + `output_path` |

Full contract: `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.

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

### Working well (as of SESSION 110, 2026-05-13)

- Django shell + FastAPI media-engine speak the new internal
  contract for all three core verbs.
- Tier gating returns structured 402 payloads with upgrade hints.
- Multi-tenant isolation enforced by `IsWorkspaceMember` +
  queryset scoping.
- Hermetic mock-mode smoke tests for all three pipelines.
- Celery worker polls happily; ~13 s end-to-end video render in
  mock mode.

### Stale or drifting

- ~~**`docs/design/UI_REDESIGN_V2.md` doesn't exist**~~ — closed
  in SESSION 113. The 845-line design lock had been left in
  `runway-hackathon/docs/design/` during the SESSION 106
  scaffold; SESSION 113 copied it across with a provenance
  preamble. Phase status reconciled in CLAUDE.md the same
  session.
- ~~**`CHARACTER_OS_INVENTORY.md`** is still the stub~~ — closed
  in SESSION 112. `python manage.py inventory` regenerates it
  from runtime introspection. Re-run after any model / route /
  task change.
- **SQLite still in use.** Phase 2 was supposed to switch to
  Postgres + pgvector "when the media data model migrates."
  The data model migrated; the DB swap didn't.
- **Numbered handoff gap.** `SESSION_053` is missing from
  `docs/handoffs/`. Cosmetic; flagged by `context-kit orient`.

### Known issues queued for follow-up

- **Stuck-row janitor** — Celery worker dying mid-poll leaves a
  Video row in `rendering` indefinitely. Easy fix via
  `celery beat`; deferred until SPA load creates pressure.
- **Real Runway credentials never smoke-tested.** Mock mode is
  fully wired; real mode is theoretically wired but untested
  against the new `/internal/*` shape.
- **dj-stripe** + real Google OAuth + `allauth.headless` — all
  pending credentials / config from the operator.

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
7. [`docs/handoffs/`](handoffs/) — session-by-session build
   history. SESSION 106-110 cover the Phase 1 + Phase 2 work.
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

---

*Last revised SESSION 111, 2026-05-13. When this doc drifts from
reality, regenerate `CHARACTER_OS_INVENTORY.md` first — that's
always authoritative (or will be, once the generator lands).*
