# Provider Map

Every AI provider Character OS integrates with. Each entry lists
the SDK, hardcoded model IDs, the env-var gate, whether a mock
path exists, and where the code lives.

## LLM

### OpenAI (primary)

- **SDK:** `openai>=2.0`
- **Models:** `gpt-5` (K6 script synthesis, teammate ask),
  `gpt-5-mini` (structured output).
- **API:** Responses API — `client.responses.create(...)`.
- **Env:** `OPENAI_API_KEY`.
- **Mock gate:** `RENDER_SCRIPT_FORCE_MOCK`, `EMBEDDING_FORCE_MOCK`.
- **Code:** `shell/character_os/script_synthesis.py`,
  `shell/character_os/teammate_ask.py`,
  `shell/apps/embeddings/embedding_service.py`.

### Ollama (fallback, lightly exercised)

- **Config:** `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL`,
  `OLLAMA_MODEL`.
- **Code:** `media-engine/app/config.py:85-87`,
  `media-engine/app/services/concept_service.py`.
- **Status:** Wired for the concept endpoint; not integrated with
  the main K6 flow.

## Embeddings

### OpenAI

- **Model:** `text-embedding-3-small` (1536-d).
- **Cache:** Redis, 30-day TTL, key = SHA256(text).
- **Mock:** `_deterministic_mock_vector()` — hash-based
  pseudo-vector; NOT semantically meaningful (mock tests
  verify wiring, not retrieval quality).
- **Code:** `shell/apps/embeddings/embedding_service.py`.

## Retrieval

### pgvector

- **Extension:** `pgvector` on the shared Postgres.
- **Index:** HNSW, `m=16`, `ef_construction=64`.
- **Search:** cosine distance via Django ORM.
- **Code:** `shell/apps/embeddings/retrieval.py`.

## Image

### Runway `gen4_image`

- **Endpoint:** `POST /v1/generate/gen4_image`.
- **Use:** Avatar portrait generation (canonical portrait
  source since SESSION 171).
- **Env:** `RUNWAY_API_KEY`.
- **Mock gate:** `RUNWAY_FORCE_MOCK`.
- **Code:** `media-engine/app/services/runway_client.py`,
  `character_studio_client.py`.

### Stability AI SD3

- **Endpoint:** `https://api.stability.ai/v2beta/`.
- **Use:** Scenes, b-roll, product images. NOT portraits
  (see SESSION 171 case study).
- **Env:** `STABILITY_API_KEY`.
- **Code:** `media-engine/app/services/stability_ai_service.py`,
  `stability_portrait.py`.

### rembg (local ONNX)

- **Model:** u2net (176 MB on first call, cached).
- **Use:** Background removal for avatar backdrops (V16).
- **Code:** invoked from `apps/compositions/primitives/remove_avatar_background.py`.

## Video

### Runway (primary and only)

- **Endpoints:**
  - `POST /v1/text_to_video` (gen4.5)
  - `POST /v1/image_to_video` (gen4_turbo)
  - `POST /v1/avatars/` (avatar bake)
  - `POST /v1/text_to_video/{id}/extend` (extend chain)
  - `POST /v1/character_performance/` (act_two)
  - `POST /v1/scene/aleph/` (aleph)
- **Env:** `RUNWAY_API_KEY`.
- **Mock:** `_MockRunwayStore` — in-memory task tracker.
- **Code:** `media-engine/app/services/runway_client.py`.

## Voice / TTS

### Runway voice

- **Endpoints:** `POST /v1/voices` (design),
  `POST /v1/voice_dubbing` (dub).
- **Models:** `eleven_multilingual_ttv_v2`,
  `eleven_voice_dubbing`.
- **Code:** `media-engine/app/services/audio_client.py`.

### ElevenLabs (fallback)

- **Env:** `ELEVENLABS_API_KEY`,
  `VOICEOVER_TTS_DEFAULT_PROVIDER`.
- **Code:** `media-engine/app/services/tts_provider/elevenlabs.py`.

### Voice presets

- **Library:** 30 Runway-hosted voice presets, mirrored in
  `shell/apps/spokespeople/views.py:54-60`.
- **Preview:** static MP3 samples in
  `web/public/voice-samples/`.

## Realtime

### Runway realtime avatars

- **Model:** `gwm1_avatars`.
- **Endpoint:** `POST /v1/realtime_sessions/`.
- **SDK (frontend):** `@runwayml/avatars-react@0.16.0`,
  bundling LiveKit React + JS clients.
- **Transport:** WebRTC bidirectional audio + data channel.
- **Session cap:** 5 minutes provider-enforced.
- **Mock:** `MockRealtimeProvider` — returns
  `status=not_ready` indefinitely; SPA branches to demo mode
  UI.
- **Code:** `media-engine/app/services/realtime_avatar_client.py`,
  `shell/apps/realtime/`,
  `web/src/routes/spokespeople/talk.tsx`,
  `web/src/components/avatar-session-inner.tsx`.

## Transcription

### Runway realtime transcript

- **Endpoint:** `GET /v1/realtime_sessions/{id}/transcript/`.
- **Trigger:** Post-session Celery task via broker `end`.
- **Persistence:** `Asset(role=TRANSCRIPT)` linked to
  `RealtimeSession.transcript_asset`.
- **Code:** `shell/apps/realtime/tasks.py::capture_transcript`,
  `media-engine/app/services/realtime_avatar_client.py::fetch_transcript`.

## Web search (K7)

### Serper

- **Env:** `SERPER_API_KEY`.
- **Use:** Knowledge discovery — operator supplies a query,
  Serper returns top URLs, `trafilatura` ingests them.
- **Code:** `shell/apps/embeddings/serper.py`.

## Content extraction

### trafilatura

- **Use:** HTML text extraction for URL-based knowledge ingest.
- **Silent-failure fix:** SESSION 175 added a per-host
  extractor layer that detects YouTube URLs and routes them to
  `youtube-transcript-api` instead of trafilatura (which
  returns empty on YouTube pages).
- **Code:** `shell/apps/embeddings/ingestion.py`.

### youtube-transcript-api

- **Use:** YouTube transcript ingest (SESSION 175 first-class
  knowledge source).
- **Fallback:** captions-fetch when transcript unavailable.

### pdfminer.six

- **Use:** PDF text extraction.

## Cost table (per-provider, hardcoded)

| Provider | Rate | Location |
|----------|------|----------|
| Runway realtime | 80,000 micros/min ($0.08/min) | `shell/apps/realtime/cost.py::_PROVIDER_RATES` |
| Runway realtime session cap | 5 min | same file, `PROVIDER_MAX_SESSION_MINUTES` |
| OpenAI embeddings | $0.02/1M tokens | measured via API |
| Runway avatar bake | ~$0.08/render | operator-measured SESSION 158 |
| Tool approval threshold | $0.05 (50,000 micros) | `dispatch.py`, configurable via `settings.REALTIME_TOOL_APPROVAL_THRESHOLD_MICROS` |

## Drift protection

Every provider class ships with a mock counterpart. Parity is
verified by AST inspection at
`media-engine/tests/test_r10_provider_drift.py`, which:

1. Enumerates every module in the providers directory.
2. Asserts every module is in the known-modules set (registry
   drift).
3. Walks each concrete provider class and checks every method
   in `PROTOCOL_METHODS` is defined (protocol drift).
4. Rejects bare `raise NotImplementedError` stubs in
   ostensibly-implemented methods.

Adding a provider or a protocol method forces a code-review
event.
