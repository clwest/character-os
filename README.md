# Character OS

**A multimodal AI creator platform.** Character OS gives a persistent
AI teammate a stable identity, voice, knowledge base, and media-
generation pipeline. It combines grounded LLM generation, image /
video / voice providers, composition recipes, realtime avatar
sessions, and cost-governed tool execution.

Solo-authored, pre-launch, AI-assisted. See
[`AI_ASSISTED_DEVELOPMENT.md`](AI_ASSISTED_DEVELOPMENT.md).

## What it does

Three canonical flows exercise the whole stack. Each one is real
runtime behavior — not stubs.

### 1. Grounded content generation

Knowledge ingest → pgvector retrieval → LLM synthesis → claim
verification → citation lineage on the output row.

Entry points:
- `shell/apps/embeddings/` — ingest, chunk, embed (OpenAI
  `text-embedding-3-small`, cached, pgvector HNSW).
- `shell/character_os/script_synthesis.py` — retrieves top-k for
  the teammate and injects into a GPT-5 system prompt.
- `shell/character_os/claim_verifier.py` — post-synthesis check;
  warn / strict / off modes; results persisted on the
  `Composition`.
- `shell/apps/compositions/models.py` — `Composition.knowledge_chunk_ids`
  is the citation trail.

### 2. Multimodal media generation

Portrait / identity → avatar bake → script → voice → composited
video, with `Asset.source_spec` recording the provenance of every
output.

Entry points:
- `shell/apps/spokespeople/` — the `Teammate` (persistent identity).
- `media-engine/app/services/` — Runway (`gen4_image`, `gen4_turbo`,
  avatar), Stability (SD3), ElevenLabs. See
  [`docs/architecture/PROVIDER_MAP.md`](docs/architecture/PROVIDER_MAP.md).
- `shell/apps/compositions/recipes.py` — 20 registered recipes.
- `shell/apps/compositions/primitives/` — 23 registered step
  primitives.
- `shell/apps/compositions/models.py` — `Asset.source_spec`
  provenance JSON.

### 3. Realtime avatar session

Browser WebRTC ↔ Runway realtime avatar → server-side tool
dispatch → tier + cost approval → sync inline or async Celery
execution → transcript capture → cross-session memory in the next
session.

Entry points:
- `web/src/routes/spokespeople/talk.tsx` — SPA lifecycle.
- `web/src/components/avatar-session-inner.tsx` — SDK data channel
  → tool invocation callback.
- `shell/apps/realtime/dispatch.py` — server-side gate.
- `shell/apps/realtime/tools/` — 9 registered tools (recall
  knowledge, render video, handoff, attach memory, etc.).
- `shell/apps/realtime/cost.py` — per-tool $0.05 approval
  threshold; per-workspace monthly minutes budget.

## Architecture

Django DRF shell + FastAPI media engine + React SPA, sharing a
Postgres + pgvector database.

| Service | Language | Purpose | Port |
|---------|----------|---------|------|
| `shell/` | Django 5 + DRF | auth, persistence, orchestration, DRF API | 8010 |
| `media-engine/` | FastAPI | media pipeline (Runway/Stability/ElevenLabs), 139 routes | 8001 |
| `web/` | React 19 + Vite | operator SPA, WebRTC realtime avatar | 5174 |

Cross-service calls are HTTP/JSON only; the SPA proxies through
Django. Full breakdown in
[`ARCHITECTURE.md`](ARCHITECTURE.md).

## Provider map

- **LLM:** OpenAI `gpt-5`, `gpt-5-mini`, `text-embedding-3-small`.
  Ollama shim wired.
- **Image:** Runway `gen4_image`, Stability SD3, `rembg` (ONNX
  u2net) for background removal.
- **Video:** Runway `gen4_turbo`, `gen4.5`, avatar bake, extend
  chain, `aleph`, `act_two`.
- **Voice:** Runway voice design / dubbing, ElevenLabs, 30-voice
  preset library.
- **Realtime:** Runway `gwm1_avatars` via `@runwayml/avatars-react`.

Every provider ships with a mock mode. Real ↔ mock parity is
guarded structurally by an AST-level drift test at
`media-engine/tests/test_r10_provider_drift.py`.

## Cost governance

Three layers, all real, all tested:

1. **Per-workspace monthly minutes budget** — starter 30, pro
   120, agency unlimited (`shell/apps/billing/services.py`).
2. **Per-session length cap** — Runway 5-minute provider ceiling.
3. **Per-tool approval threshold** — $0.05; tools above the
   threshold land in `AWAITING_APPROVAL` and require an operator
   click (`shell/apps/realtime/dispatch.py`).

## Tenancy

Defense in depth. Every major model has a `workspace` FK.
Cross-workspace references are rejected at three layers:
`Model.clean()`, pre-save signals, and repo-grep tests at
`shell/apps/*/tests/test_isolation.py` that fail if writes bypass
the sanctioned code paths.

## Testing

Real, empirical counts:

- Django (shell): **2,090 tests collected**
- FastAPI (media-engine): **901 tests collected**
- Vitest (SPA): **38 test files**
- Playwright (SPA): **21 spec files**

Strongest tests (start here to see the invariants):

- `shell/apps/compositions/tests/test_isolation.py` — repo-grep
  workspace-isolation enforcement.
- `shell/apps/realtime/tests/test_isolation.py` — same for the
  realtime surface.
- `media-engine/tests/test_r10_provider_drift.py` — AST parity
  verifier for every concrete provider.
- `shell/apps/realtime/tests/test_broker.py` — tier limits, cost
  estimation, `AWAITING_APPROVAL` gate.

CI: see [`.github/workflows/`](.github/workflows/) — Django
check + migration drift + backend/media-engine test collection
+ SPA typecheck + build + Vitest run on every PR to `main`.

## How to run

**Canonical local stack — one script, four processes.**

Prerequisites (first-time setup only):

```bash
# Root venv covers both Django (shell/) and FastAPI (media-engine/).
python -m venv .venv && source .venv/bin/activate
pip install -e shell && pip install -r media-engine/requirements.txt

# SPA deps.
cd web && pnpm install && cd ..

# Populate .env at repo root with provider keys (real mode).
```

Then, from repo root:

```bash
bash scripts/start-local-real.sh    # real providers — Runway / OpenAI / etc.
```

That script brings up Postgres + Redis via `infra/docker-compose.yml`
(if not already running), then starts **all four processes required
for composition generation to complete end-to-end**:

| Process | Port | Purpose |
|---|---|---|
| Django shell | 8010 | auth, REST API, orchestration |
| FastAPI media-engine | 8001 | Runway / Stability / ElevenLabs |
| **Celery worker** | — | consumes composition renders, transcript captures, tool dispatch |
| Vite SPA | 5174 | operator UI |

The script health-probes each service and runs `celery inspect ping`
so the worker's broker connection is proven before returning.
**Omitting the Celery worker is what caused the SESSION 251 "stuck
DRAFT" incident** — every `POST /api/compositions/` enqueued a task
that nothing consumed. Do not run any subset of these processes by
hand for functional testing; use the script.

Mock mode (no real-provider spend, safe for CI / smoke):

```bash
bash scripts/start-local-mock.sh
```

Stop everything (docker infra stays up so restarts are fast):

```bash
bash scripts/stop-local.sh
```

Logs live at `/tmp/character-os-{django,media,celery,web}.log`.

## Known limitations

Character OS is pre-launch. Publishing this repo is a portfolio
decision, not a launch announcement.

- No real customer traffic; no production hardening (rate limits,
  observability, secrets manager, etc.) beyond development
  scaffolding.
- Social platform publishing (YouTube, TikTok, IG) is scaffolded
  (`shell/apps/publish/`, `platform_catalog`) but the dispatch
  adapters are not implemented.
- The `agents` and `memory` Django apps are empty scaffolds — the
  realtime tool catalog is the closest to an "agent" concept
  that's actually shipping.
- Some `RealtimeProvider` protocol methods on non-Runway providers
  remain stubs guarded by the R10 drift verifier — Runway is the
  only realtime provider that fully implements the protocol.
- Ollama LLM fallback is wired but exercised only lightly.
- No Kubernetes / deployment manifests; only local dev via
  `docker compose` for Postgres + Redis.

## Case studies

Seven engineering-evolution case studies in
[`docs/case-studies/`](docs/case-studies/) — each follows the
shape: problem → evidence → decision → change → verification →
lasting rule.

## Architectural scars

Honestly documented in
[`docs/architecture/GOD_FILES.md`](docs/architecture/GOD_FILES.md):
four large files (1.5k-3k LOC), the Teammate/Spokesperson naming
compatibility debt, the legacy `Video` model shim, and the two
empty `agents/` + `memory/` app placeholders.

## License

MIT. See [`LICENSE`](LICENSE).

## AI-assisted development

Chris West defined product philosophy, architecture, scope locks,
acceptance criteria, and dogfood verification. Claude Code
performed most of the implementation under that direction. Full
disclosure with concrete examples in
[`AI_ASSISTED_DEVELOPMENT.md`](AI_ASSISTED_DEVELOPMENT.md).
