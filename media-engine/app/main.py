import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .routers.campaigns import router as campaigns_router
from .routers.characters import router as characters_router
from .routers.concepts import router as concepts_router
from .routers.internal import router as internal_router
from .routers.runway import router as runway_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="Character OS API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(concepts_router)
app.include_router(runway_router)
app.include_router(campaigns_router)
app.include_router(characters_router)
app.include_router(internal_router)

# Serve media artifacts from `data/` over HTTP so the SPA can play
# locally-generated assets (long_form_ad concats, composite videos,
# audio mixes, etc.) whose Asset.file_path is a `/data/_internal/...`
# disk path. Without this mount the SPA's
# `<video src="/data/_internal/concats/<hash>.mp4">` 404s — the
# concat file exists on the media-engine filesystem but no HTTP
# route exposes it.
#
# Dev: Vite's `/data` proxy in `web/vite.config.ts` forwards
# `localhost:5174/data/*` to `localhost:8001/data/*`. Production:
# add a reverse-proxy entry (or a Django streaming proxy view) so
# `<spa-origin>/data/*` resolves to the media-engine filesystem.
app.mount(
    "/data",
    StaticFiles(directory=settings.data_path, check_dir=False),
    name="data",
)


@app.get("/health")
def health(s: Settings = Depends(get_settings)) -> dict:
    # image_gen rides on the same Runway API key as video, so it inherits the
    # runway mock flag today. Surfaced as its own field so the frontend banner
    # can show a separate pill, and so a future split (e.g. an OSS image model
    # behind its own key) is a backend-only change.
    return {
        "status": "ok",
        "service": "adspark-studio",
        "openai_mock": s.openai_mock,
        "runway_mock": s.runway_mock,
        "image_gen_mock": s.runway_mock,
        "any_mock": s.openai_mock or s.runway_mock,
        # PR EH — surface which LLM the concept service is talking to
        # so the frontend Mode banner can show "🦙 Ollama (local)"
        # when the operator runs the demo without an OpenAI key.
        "llm_provider": (s.llm_provider or "openai").strip().lower(),
        "llm_model": (
            s.ollama_model
            if (s.llm_provider or "").strip().lower() == "ollama"
            else s.openai_model
        ),
    }
