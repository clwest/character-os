"""Provider-status inspection helper — P1 slice 2.2.

Consolidates media-engine ``/health`` plus shell-side provider
configuration + engine-bridge resolution into a single truthful
snapshot for the ``GET /api/health/providers/`` endpoint.

**Truthfulness contract** (documented on the endpoint's runbook
entry — ``docs/production-readiness/REAL_MODE_PROVIDER_RUNBOOK.md``):

* ``configured=True`` means required configuration appears
  present. It does NOT mean a call has succeeded and it does
  not expose the value, length, or prefix of any secret.
* ``mode="real"`` means resolution would pick the real adapter.
  It does NOT mean a paid call was made or verified.
* ``mode="mock"`` means resolution would pick the mock adapter.
* ``mode="unavailable"`` means resolution would refuse (e.g.
  Serper with no key and no ``SERPER_FORCE_MOCK``). A call would
  error.
* ``mode="unknown"`` means we could not determine the mode
  because the underlying probe is unavailable (typically
  ``media_engine`` unreachable).
* ``reachable=True`` on a provider row requires that provider to
  have received its own safe, provider-specific probe during this
  request (or the underlying probe response to have carried
  provider-specific reachability evidence). A successful media-
  engine ``/health`` call proves the media-engine PROCESS is
  reachable — it does NOT prove Runway, OpenAI, image gen, or the
  realtime provider is reachable. Media-engine ``/health`` today
  reports configuration flags + adapter selection + mock state; it
  does not perform outbound provider probes. Therefore every
  provider row currently returns ``reachable=None``.
* ``reachable=False`` on a provider row means a provider-specific
  probe was attempted and failed. No provider-specific probes are
  implemented yet, so this value is not currently reachable in
  code — reserved for future provider probes.
* ``reachable=None`` means no provider-specific probe was
  attempted (the default for every provider row in v1).

Process-level reachability lives in the top-level
``media_engine.reachable`` field. Only that field flips
``true``/``false`` today.

No paid provider calls are made from this module. Every real-mode
determination is derived from configuration presence + adapter
selection logic, not from an outbound call.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


Mode = Literal["mock", "real", "unavailable", "unknown"]
Source = Literal[
    "media_engine_health",
    "shell_env",
    "engine_connection_row",
    "env_fallback",
    "none",
]
TopStatus = Literal["ok", "degraded", "unavailable"]


@dataclass(frozen=True)
class ProviderStatus:
    """One row of the ``providers`` map. Field semantics documented
    at module top."""

    configured: bool
    mode: Mode
    reachable: Optional[bool]  # tri-state: True / False / None
    source: Source
    detail: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "mode": self.mode,
            "reachable": self.reachable,
            "source": self.source,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class MediaEngineStatus:
    """Media-engine-side sub-object.

    ``base_url`` is captured internally so server-side logs and
    administrative diagnostics can identify which media-engine
    was probed, but it is NOT included in the serialized response
    — the API consumer only needs ``reachable`` + ``detail``.
    Suppressing the URL avoids unnecessary infrastructure
    disclosure to authenticated clients.
    """

    base_url: str
    reachable: bool
    detail: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        # ``payload`` + ``base_url`` are NOT included in the
        # serialized response — they exist as an inspection aid
        # for internal callers.
        return {
            "reachable": self.reachable,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class ProviderReport:
    """Aggregate snapshot returned by ``build_provider_report``."""

    status: TopStatus
    generated_at: str
    media_engine: MediaEngineStatus
    providers: dict[str, ProviderStatus]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "generated_at": self.generated_at,
            "media_engine": self.media_engine.to_dict(),
            "providers": {
                name: status.to_dict()
                for name, status in self.providers.items()
            },
        }


# ---- Env-presence helpers (never read the value) --------------------


def _env_present(name: str) -> bool:
    """True if ``os.environ[name]`` is set and non-empty after strip."""
    return bool(os.environ.get(name, "").strip())


def _force_mock_flag(name: str) -> bool:
    """Match the shell-family ``*_FORCE_MOCK`` semantics.

    Settings beats env; env accepts 1/true/yes/on (case-insensitive).
    """
    settings_flag = getattr(settings, name, None)
    if settings_flag is not None:
        return bool(settings_flag)
    env_val = os.environ.get(name, "").strip().lower()
    return env_val in {"1", "true", "yes", "on"}


# ---- Media-engine probe ---------------------------------------------


def _probe_media_engine(*, timeout_seconds: float = 3.0) -> MediaEngineStatus:
    """Hit media-engine ``/health``. Never exposes exception bodies
    verbatim — surfaces only a short, secret-safe reason string."""

    from character_os.clients.media_engine import (
        MediaEngineClient,
        MediaEngineError,
    )

    base_url = getattr(settings, "MEDIA_ENGINE_BASE_URL", "")

    try:
        with MediaEngineClient(timeout=timeout_seconds) as client:
            health = client.health_check()
    except MediaEngineError as exc:
        # ``exc`` may carry ``response_text`` which could contain a
        # provider error body. We surface only ``exc.args[0]`` (the
        # short message) capped to 200 chars — never response_text
        # or status_code detail beyond a code number.
        short = str(exc.args[0]) if exc.args else "media-engine unreachable"
        detail = short[:200]
        return MediaEngineStatus(
            base_url=base_url,
            reachable=False,
            detail=detail,
            payload={},
        )
    except Exception as exc:  # defence-in-depth
        logger.warning("provider-status: unexpected media-engine probe error: %r", exc)
        return MediaEngineStatus(
            base_url=base_url,
            reachable=False,
            detail="unexpected probe error",
            payload={},
        )

    payload: dict[str, Any] = {
        "openai_mock": health.openai_mock,
        "runway_mock": health.runway_mock,
        "image_gen_mock": health.image_gen_mock,
        **{k: v for k, v in health.extras.items()},
    }
    return MediaEngineStatus(
        base_url=base_url,
        reachable=health.healthy,
        detail=None if health.healthy else f"unexpected status {health.status!r}",
        payload=payload,
    )


# ---- Per-provider row builders --------------------------------------


# All media-engine-derived provider rows return ``reachable=None``:
# media-engine ``/health`` reports configuration + adapter selection
# + mock state, not provider-specific reachability. A ``true`` here
# would falsely imply Runway/OpenAI/etc. is reachable when we only
# know the media-engine process itself is.

_MEDIA_ENGINE_OBSERVED_DETAIL = (
    "media-engine reachable; provider configuration observed; "
    "provider not probed"
)


def _runway_row(engine: MediaEngineStatus) -> ProviderStatus:
    if not engine.reachable:
        return ProviderStatus(
            configured=False,
            mode="unknown",
            reachable=None,
            source="none",
            detail="media-engine unreachable",
        )
    runway_mock = bool(engine.payload.get("runway_mock", True))
    return ProviderStatus(
        configured=(not runway_mock),
        mode="mock" if runway_mock else "real",
        reachable=None,
        source="media_engine_health",
        detail=_MEDIA_ENGINE_OBSERVED_DETAIL,
    )


def _image_gen_row(engine: MediaEngineStatus) -> ProviderStatus:
    if not engine.reachable:
        return ProviderStatus(
            configured=False,
            mode="unknown",
            reachable=None,
            source="none",
            detail="media-engine unreachable",
        )
    # image_gen currently rides on runway_mock (main.py:63). Preserve
    # that derivation explicitly rather than fabricate an independent
    # flag.
    image_gen_mock = bool(engine.payload.get("image_gen_mock", True))
    runway_mock = bool(engine.payload.get("runway_mock", True))
    derivation = (
        "derives from runway_mock; independent split queued "
        "(P1 2.2 follow-up)"
    )
    if image_gen_mock != runway_mock:
        derivation = (
            "image_gen_mock diverges from runway_mock — media-engine "
            "may have shipped the independent split"
        )
    return ProviderStatus(
        configured=(not image_gen_mock),
        mode="mock" if image_gen_mock else "real",
        reachable=None,
        source="media_engine_health",
        detail=f"{_MEDIA_ENGINE_OBSERVED_DETAIL}; {derivation}",
    )


def _llm_provider_row(engine: MediaEngineStatus) -> ProviderStatus:
    if not engine.reachable:
        return ProviderStatus(
            configured=False,
            mode="unknown",
            reachable=None,
            source="none",
            detail="media-engine unreachable",
        )
    llm_provider = str(engine.payload.get("llm_provider", "openai")).lower()
    llm_model = engine.payload.get("llm_model")
    if llm_provider == "ollama":
        # Ollama is opt-in; media-engine's ``openai_mock`` is False when
        # ollama is selected regardless of OpenAI key state (config.py:83-84).
        return ProviderStatus(
            configured=True,
            mode="real",
            reachable=None,
            source="media_engine_health",
            detail=(
                f"{_MEDIA_ENGINE_OBSERVED_DETAIL}; provider=ollama "
                f"model={llm_model!r}"
            ),
        )
    # openai path
    openai_mock = bool(engine.payload.get("openai_mock", True))
    return ProviderStatus(
        configured=(not openai_mock),
        mode="mock" if openai_mock else "real",
        reachable=None,
        source="media_engine_health",
        detail=(
            f"{_MEDIA_ENGINE_OBSERVED_DETAIL}; provider=openai "
            f"model={llm_model!r}"
        ),
    )


def _realtime_row(engine: MediaEngineStatus) -> ProviderStatus:
    if not engine.reachable:
        return ProviderStatus(
            configured=False,
            mode="unknown",
            reachable=None,
            source="none",
            detail="media-engine unreachable",
        )
    # realtime_provider/__init__.py:145 selects Mock when runway_mock,
    # else Runway. Contract rule 8: single provider abstraction.
    runway_mock = bool(engine.payload.get("runway_mock", True))
    return ProviderStatus(
        configured=(not runway_mock),
        mode="mock" if runway_mock else "real",
        reachable=None,
        source="media_engine_health",
        detail=(
            f"{_MEDIA_ENGINE_OBSERVED_DETAIL}; realtime adapter selected "
            "via settings.runway_mock"
        ),
    )


def _openai_shell_row() -> ProviderStatus:
    """Shell-side OPENAI_API_KEY usage: embeddings, script/conversation/
    transcript/memory synthesis. Each service has its own force-mock
    flag; we report a summary."""
    key_present = _env_present("OPENAI_API_KEY")
    embedding_mock = _force_mock_flag("EMBEDDING_FORCE_MOCK")
    render_mock = _force_mock_flag("RENDER_SCRIPT_FORCE_MOCK")
    convo_mock = _force_mock_flag("CONVERSATION_REPLY_FORCE_MOCK")
    memory_mock = _force_mock_flag("REALTIME_MEMORY_FORCE_MOCK")
    miner_mock = _force_mock_flag("TRANSCRIPT_MINER_FORCE_MOCK")

    any_mock_forced = (
        embedding_mock or render_mock or convo_mock or memory_mock or miner_mock
    )
    all_mock_forced = (
        embedding_mock and render_mock and convo_mock and memory_mock and miner_mock
    )

    if not key_present and not all_mock_forced:
        # embedding_service raises RuntimeError here; other services
        # degrade to empty results. Surface as ``unavailable`` because
        # a real-mode call to any of those services would fail or
        # silently degrade.
        return ProviderStatus(
            configured=False,
            mode="unavailable",
            reachable=None,
            source="shell_env",
            detail=(
                "OPENAI_API_KEY unset; not all shell force-mock flags are on "
                "(embeddings would raise RuntimeError; synth services degrade)"
            ),
        )
    if all_mock_forced:
        return ProviderStatus(
            configured=key_present,
            mode="mock",
            reachable=None,
            source="shell_env",
            detail="all shell *_FORCE_MOCK flags enabled",
        )
    if any_mock_forced:
        return ProviderStatus(
            configured=key_present,
            mode="mock" if not key_present else "real",
            reachable=None,
            source="shell_env",
            detail=(
                "partial force-mock: "
                f"embedding={embedding_mock} script={render_mock} "
                f"conversation={convo_mock} memory={memory_mock} "
                f"transcript_miner={miner_mock}"
            ),
        )
    return ProviderStatus(
        configured=True,
        mode="real",
        reachable=None,
        source="shell_env",
        detail=None,
    )


def _stability_row(engine: MediaEngineStatus) -> ProviderStatus:
    """Stability AI is not on ``/health``; we can derive
    ``stability_mock`` from the media-engine's ``Settings``
    only by inspecting env (media-engine reads the same root
    ``.env``). We treat env presence as configuration; mode is
    ``real`` iff configured."""
    key_present = _env_present("STABILITY_API_KEY")
    if not engine.reachable:
        # media-engine consumes STABILITY_API_KEY; without it, we can't
        # be sure our env view matches the running process.
        return ProviderStatus(
            configured=key_present,
            mode="unknown",
            reachable=None,
            source="shell_env",
            detail="media-engine unreachable; shell view of env only",
        )
    return ProviderStatus(
        configured=key_present,
        mode="real" if key_present else "mock",
        reachable=None,
        source="shell_env",
        detail=(
            "not surfaced on /health; shell reads root .env directly"
        ),
    )


def _elevenlabs_row(engine: MediaEngineStatus) -> ProviderStatus:
    """ElevenLabs is not on ``/health``; derive from env + VO flags."""
    key_present = _env_present("ELEVENLABS_API_KEY")
    force_mock = _force_mock_flag("VOICEOVER_TTS_FORCE_MOCK")
    default_provider = (
        os.environ.get("VOICEOVER_TTS_DEFAULT_PROVIDER", "auto").strip().lower()
        or "auto"
    )

    if force_mock:
        return ProviderStatus(
            configured=key_present,
            mode="mock",
            reachable=None,
            source="shell_env",
            detail=(
                f"VOICEOVER_TTS_FORCE_MOCK=1; default_provider={default_provider!r}"
            ),
        )
    if default_provider == "mock":
        return ProviderStatus(
            configured=key_present,
            mode="mock",
            reachable=None,
            source="shell_env",
            detail="VOICEOVER_TTS_DEFAULT_PROVIDER=mock",
        )
    if default_provider == "elevenlabs" and not key_present:
        return ProviderStatus(
            configured=False,
            mode="unavailable",
            reachable=None,
            source="shell_env",
            detail=(
                "explicit provider=elevenlabs but ELEVENLABS_API_KEY unset"
            ),
        )
    if not engine.reachable:
        return ProviderStatus(
            configured=key_present,
            mode="unknown",
            reachable=None,
            source="shell_env",
            detail="media-engine unreachable; shell view of env only",
        )
    return ProviderStatus(
        configured=key_present,
        mode="real" if key_present else "mock",
        reachable=None,
        source="shell_env",
        detail=(
            f"default_provider={default_provider!r}; "
            "auto chain: runway -> elevenlabs -> mock"
        ),
    )


def _serper_row() -> ProviderStatus:
    key_present = _env_present("SERPER_API_KEY")
    force_mock = _force_mock_flag("SERPER_FORCE_MOCK")
    if force_mock:
        return ProviderStatus(
            configured=key_present,
            mode="mock",
            reachable=None,
            source="shell_env",
            detail="SERPER_FORCE_MOCK enabled",
        )
    if not key_present:
        return ProviderStatus(
            configured=False,
            mode="unavailable",
            reachable=None,
            source="shell_env",
            detail=(
                "SERPER_API_KEY unset and SERPER_FORCE_MOCK not set — a real "
                "K7 URL ingest would raise SerperError"
            ),
        )
    return ProviderStatus(
        configured=True,
        mode="real",
        reachable=None,
        source="shell_env",
        detail=None,
    )


def _celery_worker_row() -> ProviderStatus:
    """SESSION 224 F-07 — Celery worker liveness probe.

    Motivation: F-07 originated when the operator's char-OS Celery
    worker had died silently overnight; two compositions sat at
    ``status=draft`` forever because nothing consumed the queue,
    but ``/api/health/providers/`` reported the platform healthy.
    From a user perspective "video spinning forever" is
    indistinguishable from "generation genuinely running." This row
    surfaces the difference.

    Probe: ``celery.app.control.ping(timeout=<short>)`` — a broker
    round-trip that returns a list like
    ``[{'celery@host': {'ok': 'pong'}}]`` when workers respond.
    Empty list / None means broker is up but no workers responded
    within the timeout. Any exception (typically kombu / redis
    connection errors) means the broker itself is unreachable.
    All three states below are user-observable defects.

    Never queues a task. Never blocks longer than ``timeout``.
    """
    try:
        from character_os.celery import app as celery_app
    except Exception as exc:  # pragma: no cover — defensive
        return ProviderStatus(
            configured=False,
            mode="unknown",
            reachable=None,
            source="none",
            detail=f"celery app import failed: {type(exc).__name__}",
        )

    try:
        pong = celery_app.control.ping(timeout=1.0)
    except Exception as exc:
        return ProviderStatus(
            configured=True,
            mode="unavailable",
            reachable=False,
            source="shell_env",
            detail=(
                f"celery broker unreachable ({type(exc).__name__}) — "
                "compositions will queue but never execute"
            ),
        )

    if not pong:
        return ProviderStatus(
            configured=True,
            mode="unavailable",
            reachable=False,
            source="shell_env",
            detail=(
                "broker reachable but no workers responded within 1 s — "
                "compositions will not execute until a worker starts "
                "(cd shell && celery -A character_os worker --loglevel=info)"
            ),
        )

    hostnames = sorted({name for reply in pong for name in reply.keys()})
    return ProviderStatus(
        configured=True,
        mode="real",
        reachable=True,
        source="shell_env",
        detail=(
            f"{len(hostnames)} worker(s) responding: {', '.join(hostnames)}"
        ),
    )


def _engine_bridge_row(workspace: Any | None) -> ProviderStatus:
    """Engine-bridge resolver dry-run. Never calls the sibling project.

    When ``workspace`` is provided (and caller is a member — the view
    enforces that), the resolver is exercised against that workspace's
    row + env fallback.

    When ``workspace`` is None, we can only report env-fallback
    presence.
    """
    if workspace is None:
        env_token_present = _env_present("UDB_PA_API_TOKEN")
        if env_token_present:
            return ProviderStatus(
                configured=True,
                mode="real",
                reachable=None,
                source="env_fallback",
                detail=(
                    "workspace not specified; reporting env-fallback state "
                    "only. Per-workspace EngineConnection rows are not "
                    "considered without ?workspace=<id>."
                ),
            )
        return ProviderStatus(
            configured=False,
            mode="unavailable",
            reachable=None,
            source="none",
            detail=(
                "workspace not specified; env fallback (UDB_PA_API_TOKEN) "
                "absent. Per-workspace EngineConnection rows not considered."
            ),
        )

    # Workspace supplied — use the resolver dry-run.
    from apps.realtime.engine_bridge import resolve_engine_connection

    resolved = resolve_engine_connection(workspace)
    if resolved is None:
        return ProviderStatus(
            configured=False,
            mode="unavailable",
            reachable=None,
            source="none",
            detail=(
                "resolver returned None — workspace tier is below Pro, "
                "no enabled EngineConnection row, and no env fallback"
            ),
        )
    return ProviderStatus(
        configured=True,
        mode="real",
        reachable=None,
        source=(
            "engine_connection_row" if resolved.source == "db" else "env_fallback"
        ),
        detail=(
            "resolver dry-run only; test_ping NOT invoked from this endpoint"
        ),
    )


# ---- Aggregator -----------------------------------------------------


def build_provider_report(
    workspace: Any | None = None,
    *,
    media_engine_timeout: float = 3.0,
) -> ProviderReport:
    """Assemble the full provider-status report.

    ``workspace`` is optional and only affects the ``engine_bridge``
    row (per contract §3.2 in the runbook). The view is responsible
    for verifying that the requester is a member before passing a
    workspace here.
    """
    engine = _probe_media_engine(timeout_seconds=media_engine_timeout)

    providers: dict[str, ProviderStatus] = {
        "runway": _runway_row(engine),
        "image_gen": _image_gen_row(engine),
        "llm_provider": _llm_provider_row(engine),
        "realtime": _realtime_row(engine),
        "openai_shell": _openai_shell_row(),
        "stability": _stability_row(engine),
        "elevenlabs": _elevenlabs_row(engine),
        "serper": _serper_row(),
        "engine_bridge": _engine_bridge_row(workspace),
        # SESSION 224 F-07 — Celery liveness. Placed last so that a
        # dead worker degrades the top-level status without hiding
        # other provider signal.
        "celery_worker": _celery_worker_row(),
    }

    # Top-level status derivation.
    #
    #   ok          -- media-engine reachable AND no provider row is
    #                  in an unavailable state.
    #   degraded    -- report was constructed but at least one of:
    #                    * media-engine unreachable (media-engine-
    #                      derived rows are `unknown`, but shell-side
    #                      + bridge rows remain truthful);
    #                    * one or more providers report
    #                      `mode="unavailable"`;
    #                    * one or more providers report
    #                      `mode="unknown"`.
    #   unavailable -- reserved for cases where the report itself
    #                  cannot be meaningfully constructed. Not
    #                  currently reachable in v1 code.
    #
    # Rationale: even with media-engine down, this endpoint can still
    # report shell-side providers, engine-bridge env-fallback state,
    # and per-workspace resolver output. That's a partial-but-useful
    # report, so ``degraded`` is more truthful than ``unavailable``.
    if engine.reachable and all(
        p.mode not in ("unavailable", "unknown")
        for p in providers.values()
    ):
        top: TopStatus = "ok"
    else:
        top = "degraded"

    return ProviderReport(
        status=top,
        generated_at=datetime.now(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
        media_engine=engine,
        providers=providers,
    )
