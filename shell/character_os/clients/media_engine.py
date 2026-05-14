"""HTTP client for the FastAPI media engine.

The architectural boundary between the Django shell and the FastAPI
media engine (design doc §6.2). All cross-service calls go through
this client; Django code never imports from `media-engine/` directly,
never reaches into the media-engine's database, and never reads from
its filesystem.

v1 surface is minimal — just `health_check()` and a typed `request()`
helper. Real endpoint wrappers (create avatar, render video, etc.)
land in follow-up slices as the data model migration in Phase 2 settles
the API contract.

Error model — all transport / status / parsing failures normalize to a
single ``MediaEngineError`` so callers don't have to catch four
different exception types. Callers can inspect ``.status_code`` to
distinguish "service unreachable" (None) from "service returned an
error" (4xx/5xx).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def _as_float_or_none(value: Any) -> float | None:
    """Coerce JSON numbers (which may arrive as int or float) into a
    float, leaving None through. Reject everything else so a contract
    drift fails loud."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raise TypeError(f"expected number or None, got {type(value).__name__}")


class MediaEngineError(Exception):
    """Anything that can go wrong calling the media engine."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_text: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text

    def __repr__(self) -> str:
        return (
            f"MediaEngineError({self.args[0]!r}, status_code={self.status_code}, "
            f"response_text={self.response_text[:80]!r})"
        )


@dataclass
class HealthStatus:
    """Decoded response from the media engine's ``/health`` endpoint."""

    status: str
    service: str
    openai_mock: bool
    runway_mock: bool
    image_gen_mock: bool
    extras: dict[str, Any]

    @property
    def healthy(self) -> bool:
        return self.status == "ok"


@dataclass
class AvatarCreateResult:
    """Decoded response from ``POST /internal/avatars/``. Contract lives
    in ``docs/design/MEDIA_ENGINE_INTERNAL_API.md``."""

    avatar_id: str
    status: str  # "ready" | "mock" | "failed"
    thumbnail_url: str | None
    mock_mode: bool

    @property
    def ok(self) -> bool:
        return self.status in {"ready", "mock"}


@dataclass
class VoiceCloneResult:
    """Decoded response from ``POST /internal/voices/``. Contract lives
    in ``docs/design/MEDIA_ENGINE_INTERNAL_API.md``."""

    voice_id: str
    status: str  # "ready" | "mock" | "failed"
    preview_url: str | None
    mock_mode: bool

    @property
    def ok(self) -> bool:
        return self.status in {"ready", "mock"}


@dataclass
class PortraitCreateResult:
    """Decoded response from ``POST /internal/portrait/`` (SESSION 125 —
    wizard slice 2). Mock-mode returns a deterministic placeholder PNG;
    real-mode calls Runway gen4_image."""

    portrait_data_uri: str
    template: str
    prompt: str
    mock_mode: bool


@dataclass
class VideoCreateResult:
    """Decoded response from ``POST /internal/videos/`` — fire-then-poll.
    The status is always non-terminal here (``pending`` or
    ``rendering``); terminal state lives on the poll endpoint."""

    task_id: str
    status: str  # "pending" | "rendering"
    kind: str
    mock_mode: bool


@dataclass
class VideoPollResult:
    """Decoded response from ``GET /internal/videos/{task_id}/``."""

    task_id: str
    status: str  # "pending" | "rendering" | "ready" | "failed"
    progress: float | None
    output_url: str | None
    duration_seconds: float | None
    error: str | None
    failure_code: str | None
    mock_mode: bool

    @property
    def terminal(self) -> bool:
        return self.status in {"ready", "failed"}

    @property
    def succeeded(self) -> bool:
        return self.status == "ready"


class MediaEngineClient:
    """Thin wrapper around ``httpx.Client`` aimed at the FastAPI media
    engine. Stateless except for the underlying connection pool.

    Use as a short-lived per-request object, or as a long-lived
    application-wide singleton if you want connection reuse — both
    are safe because ``httpx.Client`` is thread-safe for concurrent
    request issuing.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.MEDIA_ENGINE_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def __enter__(self) -> "MediaEngineClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # ---- public API --------------------------------------------------

    def health_check(self) -> HealthStatus:
        """Hit ``GET /health`` and return the parsed status.

        Raises ``MediaEngineError`` if the service is unreachable, the
        response isn't 2xx, or the body isn't JSON-shaped as expected.
        """
        data = self.request("GET", "/health")
        try:
            return HealthStatus(
                status=str(data.get("status", "")),
                service=str(data.get("service", "")),
                openai_mock=bool(data.get("openai_mock", False)),
                runway_mock=bool(data.get("runway_mock", False)),
                image_gen_mock=bool(data.get("image_gen_mock", False)),
                extras={
                    k: v
                    for k, v in data.items()
                    if k not in {"status", "service", "openai_mock", "runway_mock", "image_gen_mock"}
                },
            )
        except (TypeError, AttributeError, ValueError) as exc:
            raise MediaEngineError(
                f"health response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def create_avatar(
        self,
        *,
        name: str,
        portrait_data_uri: str,
        voice_preset: str | None = None,
        personality: str | None = None,
    ) -> AvatarCreateResult:
        """Hit ``POST /internal/avatars/`` and return the parsed result.

        Raises ``MediaEngineError`` on transport failure, non-2xx, or
        unexpected body shape. Callers inspect ``result.ok`` for the
        ready/mock success path; the ``failed`` status is reserved for
        in-band failures the contract may surface in the future
        (today, real failures come back as 4xx/5xx and raise).
        """
        body: dict[str, Any] = {
            "name": name,
            "portrait_data_uri": portrait_data_uri,
        }
        if voice_preset is not None:
            body["voice_preset"] = voice_preset
        if personality is not None:
            body["personality"] = personality

        data = self.request("POST", "/internal/avatars/", json=body)
        try:
            return AvatarCreateResult(
                avatar_id=str(data["avatar_id"]),
                status=str(data["status"]),
                thumbnail_url=data.get("thumbnail_url"),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_avatar response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def create_video(
        self,
        *,
        kind: str,
        spokesperson_avatar_id: str,
        brief: str,
        ratio: str | None = None,
        duration: int | None = None,
        prompt_image: str | None = None,
    ) -> VideoCreateResult:
        """Hit ``POST /internal/videos/``. Returns immediately with a
        Runway task id; the caller polls ``poll_video(task_id)`` for
        terminal state. Raises ``MediaEngineError`` on transport or
        protocol failure."""
        body: dict[str, Any] = {
            "kind": kind,
            "spokesperson_avatar_id": spokesperson_avatar_id,
            "brief": brief,
        }
        if ratio is not None:
            body["ratio"] = ratio
        if duration is not None:
            body["duration"] = duration
        if prompt_image is not None:
            body["prompt_image"] = prompt_image

        data = self.request("POST", "/internal/videos/", json=body)
        try:
            return VideoCreateResult(
                task_id=str(data["task_id"]),
                status=str(data["status"]),
                kind=str(data["kind"]),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_video response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def poll_video(self, task_id: str) -> VideoPollResult:
        """Hit ``GET /internal/videos/{task_id}/``. Cheap and
        idempotent; safe to call on a tight loop from the Celery
        worker."""
        data = self.request("GET", f"/internal/videos/{task_id}/")
        try:
            return VideoPollResult(
                task_id=str(data["task_id"]),
                status=str(data["status"]),
                progress=_as_float_or_none(data.get("progress")),
                output_url=data.get("output_url"),
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                error=data.get("error"),
                failure_code=data.get("failure_code"),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"poll_video response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def create_portrait(
        self,
        *,
        template: str,
        subject: str | None = None,
        style: str | None = None,
    ) -> PortraitCreateResult:
        """Hit ``POST /internal/portrait/``. Synchronous — Runway
        gen4_image returns in ~10-20 s real mode, instant in mock.
        Templates must be one of the inherited PORTRAIT_TEMPLATES
        (mascot / founder / coach / local_guide).
        """
        body: dict[str, Any] = {"template": template}
        if subject is not None:
            body["subject"] = subject
        if style is not None:
            body["style"] = style

        data = self.request("POST", "/internal/portrait/", json=body)
        try:
            return PortraitCreateResult(
                portrait_data_uri=str(data["portrait_data_uri"]),
                template=str(data["template"]),
                prompt=str(data["prompt"]),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_portrait response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def clone_voice(
        self,
        *,
        audio_data_uri: str,
        name: str | None = None,
    ) -> VoiceCloneResult:
        """Hit ``POST /internal/voices/``. Inline / synchronous —
        Runway voice clones return in <10 s; no polling needed."""
        body: dict[str, Any] = {"audio_data_uri": audio_data_uri}
        if name is not None:
            body["name"] = name

        data = self.request("POST", "/internal/voices/", json=body)
        try:
            return VoiceCloneResult(
                voice_id=str(data["voice_id"]),
                status=str(data["status"]),
                preview_url=data.get("preview_url"),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"clone_voice response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
    ) -> dict:
        """Low-level wrapper. Returns parsed JSON; raises ``MediaEngineError``
        on any non-2xx response or transport error."""
        url = path if path.startswith("/") else f"/{path}"
        try:
            response = self._client.request(method, url, params=params, json=json)
        except httpx.TimeoutException as exc:
            logger.warning("media-engine timeout %s %s after %ss", method, url, self._timeout)
            raise MediaEngineError(
                f"timeout calling {method} {url}",
                status_code=None,
            ) from exc
        except httpx.ConnectError as exc:
            logger.warning("media-engine unreachable %s %s: %s", method, url, exc)
            raise MediaEngineError(
                f"unable to reach media engine at {self.base_url}",
                status_code=None,
            ) from exc
        except httpx.HTTPError as exc:
            raise MediaEngineError(
                f"http error calling {method} {url}: {exc!s}",
                status_code=None,
            ) from exc

        if response.status_code >= 400:
            raise MediaEngineError(
                f"{method} {url} returned {response.status_code}",
                status_code=response.status_code,
                response_text=response.text[:500],
            )

        try:
            return response.json()
        except ValueError as exc:
            raise MediaEngineError(
                f"non-JSON response from {method} {url}",
                status_code=response.status_code,
                response_text=response.text[:500],
            ) from exc
