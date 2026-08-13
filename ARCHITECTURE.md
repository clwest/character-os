# Architecture

Character OS is a three-service monorepo backed by a shared
Postgres database.

```
┌───────────────────────────────────────────────────────────────┐
│                     React SPA (:5174)                          │
│                     Vite + TanStack Query                      │
│                     @runwayml/avatars-react (WebRTC)           │
└─────────────────┬─────────────────────────────────────────────┘
                  │ HTTPS (dev: /api proxy → :8010)
                  ▼
┌───────────────────────────────────────────────────────────────┐
│                Django DRF shell (:8010)                        │
│                                                                │
│   apps/            character_os/          identity substrate   │
│   ├─ accounts      ├─ script_synthesis    (canonical layer)    │
│   ├─ spokespeople  ├─ claim_verifier                           │
│   ├─ embeddings    ├─ realtime_memory                          │
│   ├─ compositions  ├─ teammate_ask                             │
│   ├─ realtime      └─ clients/media_engine.py                  │
│   ├─ scripts                                                   │
│   ├─ transcripts   Celery (async: composition steps,           │
│   ├─ campaigns             tool dispatch, transcript capture)  │
│   ├─ publish                                                   │
│   ├─ billing                                                   │
│   ├─ conversations                                             │
│   └─ identity                                                  │
└──────┬────────────────────────────────────────┬───────────────┘
       │ internal HTTP/JSON                     │
       ▼                                        ▼
┌────────────────────────────────┐   ┌───────────────────────────┐
│  FastAPI media-engine (:8001)  │   │  Postgres + pgvector      │
│                                 │   │  Redis (Celery + cache)   │
│  routers/                       │   │                           │
│  ├─ internal (36 routes)        │   │  ┌─────────────────────┐  │
│  ├─ characters (22 routes)      │   │  │ Vector: embeddings  │  │
│  ├─ campaigns (66 routes)       │   │  │ Cache: 30-day TTL   │  │
│  ├─ runway (8 routes)           │   │  │ Broker: celery queue│  │
│  └─ concepts + health           │   │  └─────────────────────┘  │
│                                 │   └───────────────────────────┘
│  services/                      │
│  ├─ runway_client              │            External providers
│  ├─ stability_ai_service       │─── HTTPS ─────► Runway
│  ├─ audio_client (ElevenLabs)  │                 OpenAI
│  ├─ realtime_avatar_client     │                 Stability
│  ├─ character_studio_client    │                 ElevenLabs
│  └─ …35+ service clients       │
└─────────────────────────────────┘
```

## Service boundaries

Cross-service calls are **always HTTP/JSON**. The SPA does not
import Django types; Django does not import media-engine Python
modules. This is deliberate — the monorepo exists to keep
migrations, features, and contracts in one commit-atomic place,
not to blur the wire.

The SPA never talks to the media engine directly. Django is the
single API surface; media-engine calls are proxied where
necessary.

## Domain model (canonical)

```
Workspace                       (accounts.Workspace — tenant anchor)
├── Teammate                    (spokespeople.Spokesperson — persistent identity)
│   ├── Composition             (compositions — video assembly, 20 recipes)
│   │   ├── CompositionStep     (23 primitive kinds, linear v1)
│   │   ├── Asset               (source_spec JSON provenance)
│   │   └── knowledge_chunk_ids (citation lineage → embeddings)
│   ├── RealtimeSession         (realtime — WebRTC avatar with tools)
│   │   ├── RealtimeToolInvocation (audit trail; approval state)
│   │   ├── knowledge_chunk_ids
│   │   └── transcript_asset    (Asset(TRANSCRIPT) FK)
│   ├── ConversationThread      (conversations — text + realtime bridge)
│   │   └── ConversationMessage
│   └── Script                  (scripts — pre-render draft/approval)
├── KnowledgeDocument           (embeddings — 4 doc types)
│   └── KnowledgeChunk          (retrieval unit; embedding cached)
├── Asset                       (canonical media unit — 12 role types)
├── PublishBundle               (publish — cross-platform variants)
├── PersonalizedCampaign        (campaigns — CSV batch)
├── EngineConnection            (realtime — per-workspace bridge config)
└── Subscription                (billing — tier + Stripe FKs)
```

Contract rules (per-arc) live in the design lock docs under
`docs/design/`.

## Tenancy enforcement

Defense in depth:

1. **Model layer** — every major model has a `workspace` FK;
   unique constraints scope by workspace.
2. **`Model.clean()`** — cross-workspace FK references raise
   `ValidationError`.
3. **Pre-save signals** — same guard, one layer down.
4. **Repo-grep tests** — `apps/*/tests/test_isolation.py` fails
   if any write path bypasses `clean()`.

## Cost governance

Three enforced layers:

- **Per-workspace monthly minutes budget** — Starter 30 / Pro
  120 / Agency unlimited. `shell/apps/billing/services.py::check_realtime_minutes_budget`.
- **Per-session length cap** — Runway enforces 5 minutes;
  SPA's `CostTicker` visualizes.
- **Per-tool approval threshold** — $0.05 default, configurable.
  Tools over threshold land in `AWAITING_APPROVAL` awaiting
  operator click. `shell/apps/realtime/dispatch.py`.

## State machines

- **RealtimeSession:** DRAFT → CREATING → NOT_READY → READY →
  ENDED / FAILED.
- **RealtimeToolInvocation:** INVOKED → AWAITING_APPROVAL /
  QUEUED → SUCCEEDED / FAILED / REJECTED.
- **Composition:** DRAFT → PLANNING → RUNNING →
  PARTIAL / COMPLETED / FAILED.
- **CompositionStep:** PENDING → RUNNING → SUCCEEDED / FAILED /
  SKIPPED.
- **PublishBundle:** DRAFT → LAUNCHING → IN_FLIGHT → COMPLETED /
  PARTIAL / FAILED.
- **PersonalizedCampaign:** same shape as PublishBundle.

## Provenance

Every generated `Asset` carries `source_spec` JSON:

```json
{
  "primitive": "generate_avatar_speech",
  "inputs": [{"slot": "voice", "asset_id": "<uuid>"}],
  "params": {"model": "gen4_turbo", "duration_ms": 8000}
}
```

Enables deterministic re-runs, audit, and lineage queries.

## Provider abstraction

Realtime, image, video, and voice providers all implement a
`Protocol` in Python. The AST-level drift verifier at
`media-engine/tests/test_r10_provider_drift.py` walks every
concrete provider class and asserts:

1. Every method in `PROTOCOL_METHODS` is defined.
2. No bare `raise NotImplementedError` stubs exist in
   ostensibly-implemented methods.
3. Registry parity — every module in the providers directory is
   accounted for in the known-modules set.

Adding a new provider forces a code-review event. Adding a new
protocol method forces stubs on every provider.

## Grounding

RAG output is grounded, not just retrieved:

1. `retrieve_for_teammate()` embeds the operator prompt and
   returns top-k chunks via pgvector cosine distance.
2. Chunks are injected into the K6 system prompt (GPT-5).
3. Post-synthesis, `claim_verifier.py` scans the output for
   claims that don't map back to the retrieved chunks.
4. Verifier mode is per-composition: `warn` records the warning;
   `strict` rejects the synthesis; `off` skips the check.
5. `Composition.knowledge_chunk_ids` persists the citation
   trail on the row.

## AI provider map

See [`docs/architecture/PROVIDER_MAP.md`](docs/architecture/PROVIDER_MAP.md).

## Known scars

See [`docs/architecture/GOD_FILES.md`](docs/architecture/GOD_FILES.md).
