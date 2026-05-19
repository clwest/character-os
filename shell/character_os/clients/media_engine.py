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


def _parse_processed_clip(data: dict, op_name: str) -> "ProcessedClipResult":
    """Shared parser for the V9 polish endpoints. They all return
    the same shape; this helper keeps the per-method bodies tiny."""
    try:
        return ProcessedClipResult(
            output_url=str(data["output_url"]),
            duration_seconds=_as_float_or_none(data.get("duration_seconds")),
            size_bytes=(
                int(data["size_bytes"]) if data.get("size_bytes") is not None
                else None
            ),
            mock_mode=bool(data.get("mock_mode", False)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MediaEngineError(
            f"{op_name} response not in expected shape: {data!r}",
            response_text=str(data),
        ) from exc


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
class ConcatClipsResult:
    """Decoded response from ``POST /internal/clips/concat/``.

    Synchronous endpoint — there's no polling. The output URL
    points at a cached MP4 the media-engine produced from the
    operator-supplied inputs."""

    output_url: str
    duration_seconds: float | None
    size_bytes: int | None
    mock_mode: bool


@dataclass
class CompositeResult:
    """Decoded response from ``POST /internal/clips/composite/``.
    Same shape as ConcatClipsResult — synchronous ffmpeg with
    a cached MP4 output."""

    output_url: str
    duration_seconds: float | None
    size_bytes: int | None
    mock_mode: bool


@dataclass
class AudioMixResult:
    """Decoded response from ``POST /internal/audio/mix/``.
    Same shape — synchronous ffmpeg audio mix with a cached
    MP4 output (video stream copied through, audio re-encoded)."""

    output_url: str
    duration_seconds: float | None
    size_bytes: int | None
    mock_mode: bool


@dataclass
class ProcessedClipResult:
    """Generic response shape for V9's four polish endpoints —
    captions, intro_outro, trim, reformat. Same fields as the
    earlier per-operation results; consolidated here because
    all four primitives produce CLIPs with no operation-specific
    metadata beyond the output URL."""

    output_url: str
    duration_seconds: float | None
    size_bytes: int | None
    mock_mode: bool


@dataclass
class VoiceDesignResult:
    """Decoded response from ``POST /internal/voices/design/``."""

    voice_id: str
    preview_url: str | None
    mock_mode: bool


@dataclass
class AudioDubResult:
    """Decoded response from ``POST /internal/audio/dub/``."""

    output_url: str
    duration_seconds: float | None
    size_bytes: int | None
    target_language: str
    mock_mode: bool


@dataclass
class RealtimeSessionResult:
    """Result of `realtime_session_create`. session_key is the
    JWT-shaped SDK token — passed to the SPA ONCE in the
    create response, persisted on RealtimeSession.provider_session_key,
    never returned in subsequent retrieves."""

    session_id: str
    session_key: str
    status: str
    expires_at: str | None
    avatar_id: str | None
    mock_mode: bool


@dataclass
class RealtimeDocumentResult:
    """Result of `realtime_document_create`. R4 — the broker
    persists `document_id` on
    `RealtimeSession.provider_document_id`."""

    document_id: str
    mock_mode: bool


@dataclass
class RealtimeTranscriptResult:
    """Result of `realtime_session_fetch_transcript`. R5 — the
    broker persists `text` as the inline content of an
    Asset(TRANSCRIPT) row and wires it to
    RealtimeSession.transcript_asset."""

    session_id: str
    text: str
    segments: list[dict]
    mock_mode: bool


@dataclass
class RealtimeSessionPollResult:
    """Result of `realtime_session_poll`. No session_key — the
    SDK already holds it from the create response."""

    session_id: str
    status: str
    expires_at: str | None
    error_message: str
    mock_mode: bool


@dataclass
class TranscriptSegment:
    """One sentence-level segment from Whisper's verbose_json
    response. Timing is in seconds (Whisper convention)."""

    start_s: float
    end_s: float
    text: str


@dataclass
class TranscribeResult:
    """Decoded response from ``POST /internal/transcribe/``."""

    segments: list[TranscriptSegment]
    duration_seconds: float | None
    language: str | None
    full_text: str
    mock_mode: bool


@dataclass
class GenerateImageResult:
    """Decoded response from ``POST /internal/images/``."""

    image_url: str
    width: int | None
    height: int | None
    seed: int | None
    mock_mode: bool


@dataclass
class StabilityImageResult:
    """Decoded response from ``POST /internal/image_stability/``
    (W11.6.1). Bytes are returned inline as a base64 data URI
    rather than a URL because the media-engine cache layout for
    Stability images is not yet exposed through ``/data/`` static
    serving (and may move to S3 in production)."""

    image_data_uri: str
    prompt: str
    mime_type: str
    cost_credits: float
    model: str
    purpose: str
    style_preset: str | None
    aspect_ratio: str
    mock_mode: bool


@dataclass
class StyleRemixResult:
    """Decoded response from ``POST /internal/clips/style_remix/``.

    Carries the chunked-path flag + Runway task ids so audit trails
    can reconstruct which Aleph fires produced the output (single-fire
    vs N-chunk fires)."""

    output_url: str
    duration_seconds: float | None
    size_bytes: int | None
    style_preset: str
    chunked: bool
    task_ids: list[str]
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
        timeout: float = 60.0,
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

    def refresh_avatar_thumbnail(
        self,
        *,
        avatar_id: str,
    ) -> str | None:
        """SESSION 169 follow-up — hit
        ``POST /internal/avatars/<id>/refresh/`` to get a fresh
        JWT-signed thumbnail URL for an existing avatar. Returns
        ``None`` in mock mode or on Runway-side failure (caller
        decides what to do — usually leave portrait_path alone).
        """
        data = self.request(
            "POST", f"/internal/avatars/{avatar_id}/refresh/",
            json={},
        )
        return data.get("thumbnail_url") or None

    def change_avatar_voice(
        self,
        *,
        avatar_id: str,
        voice_id: str,
        voice_kind: str = "preset",
    ) -> dict:
        """W11.2 (SESSION 170) — PATCH the Runway avatar's voice
        block without re-baking. Returns the parsed JSON response
        ``{avatar_id, status, error, mock_mode}``. Raises
        ``MediaEngineError`` only on transport / non-2xx; Runway-
        side failures come back as ``status="failed"`` with
        ``error`` set so the caller can persist + surface.
        """
        return self.request(
            "POST", f"/internal/avatars/{avatar_id}/change-voice/",
            json={"voice_id": voice_id, "voice_kind": voice_kind},
        )

    def change_avatar_personality(
        self,
        *,
        avatar_id: str,
        personality: str,
    ) -> dict:
        """PATCH the Runway avatar's personality text without
        re-baking. Sibling of `change_avatar_voice`. Same return
        shape + best-effort semantics. The local
        Spokesperson.personality is the source of truth; this
        method pushes the latest value to Runway's avatar
        resource so non-session-create surfaces (recipes that
        call avatar_videos directly, etc.) inherit it.
        """
        return self.request(
            "POST", f"/internal/avatars/{avatar_id}/change-personality/",
            json={"personality": personality},
        )

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

    def create_avatar_speech(
        self,
        *,
        spokesperson_avatar_id: str,
        script: str,
        ratio: str | None = None,
        duration: int | None = None,
    ) -> VideoCreateResult:
        """Hit ``POST /internal/clips/avatar_speech/`` — Runway's
        talking-head endpoint (``/v1/avatar_videos`` / ``gwm1_avatars``).
        Returns immediately with a Runway task id; the caller polls
        ``poll_task(task_id)`` for terminal state.

        Same fire-then-poll shape as ``create_video``, same Runway
        task ID space — the V3 endpoint that fixes K6.5's
        wrong-endpoint bug. Cast members will render speaking,
        not as silent animated portraits.
        """
        body: dict[str, Any] = {
            "spokesperson_avatar_id": spokesperson_avatar_id,
            "script": script,
        }
        if ratio is not None:
            body["ratio"] = ratio
        if duration is not None:
            body["duration"] = duration

        data = self.request("POST", "/internal/clips/avatar_speech/", json=body)
        try:
            return VideoCreateResult(
                task_id=str(data["task_id"]),
                status=str(data["status"]),
                kind=str(data.get("kind", "avatar_speech")),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_avatar_speech response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def create_visual_clip(
        self,
        *,
        prompt: str,
        ratio: str | None = None,
        duration: int | None = None,
        prompt_image: str | None = None,
    ) -> VideoCreateResult:
        """Hit ``POST /internal/clips/visual/`` — Runway's silent
        visual pipeline. Routes through ``gen4_turbo`` (image-to-
        video) when ``prompt_image`` is supplied, ``gen4.5``
        (text-to-video) otherwise.

        Returns immediately with a Runway task id; caller polls
        ``poll_task(task_id)`` for terminal state. Same shape as
        ``create_avatar_speech`` — both endpoints share the
        generalised poll route.
        """
        body: dict[str, Any] = {"prompt": prompt}
        if ratio is not None:
            body["ratio"] = ratio
        if duration is not None:
            body["duration"] = duration
        if prompt_image is not None:
            body["prompt_image"] = prompt_image

        data = self.request("POST", "/internal/clips/visual/", json=body)
        try:
            return VideoCreateResult(
                task_id=str(data["task_id"]),
                status=str(data["status"]),
                kind=str(data.get("kind", "visual_clip")),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_visual_clip response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def concat_clips(
        self,
        *,
        clip_urls: list[str],
        reencode: bool = False,
    ) -> "ConcatClipsResult":
        """Hit ``POST /internal/clips/concat/`` — synchronous
        ffmpeg stitch. Returns the cached output URL + size.

        Inputs may be external URLs (Runway-hosted) or local
        paths the media-engine can reach (``/data/_internal/...``).
        The endpoint downloads externals on the fly, then runs
        ``ffmpeg -f concat -c copy`` by default. ``reencode=True``
        forces filter_complex normalization for heterogeneous
        inputs.
        """
        body: dict[str, Any] = {
            "clip_urls": clip_urls,
            "reencode": reencode,
        }
        data = self.request("POST", "/internal/clips/concat/", json=body)
        try:
            return ConcatClipsResult(
                output_url=str(data["output_url"]),
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                size_bytes=(
                    int(data["size_bytes"]) if data.get("size_bytes") is not None
                    else None
                ),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"concat_clips response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def create_composite(
        self,
        *,
        clip_urls: list[str],
        layout_spec: dict,
    ) -> "CompositeResult":
        """Hit ``POST /internal/clips/composite/`` — synchronous
        ffmpeg filter_complex overlay according to
        ``layout_spec.kind``. v1 supports ``pip``, ``backdrop``,
        ``cohost``, ``broll``."""
        body: dict[str, Any] = {
            "clip_urls": clip_urls,
            "layout_spec": layout_spec,
        }
        data = self.request("POST", "/internal/clips/composite/", json=body)
        try:
            return CompositeResult(
                output_url=str(data["output_url"]),
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                size_bytes=(
                    int(data["size_bytes"]) if data.get("size_bytes") is not None
                    else None
                ),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_composite response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def mix_audio(
        self,
        *,
        base_clip_url: str,
        audio_urls: list[str],
        mix_spec: dict | None = None,
    ) -> "AudioMixResult":
        """Hit ``POST /internal/audio/mix/`` — synchronous
        ffmpeg audio mix. v1 ships the music_bed pattern (one
        base clip + one music track at ``mix_spec.music_gain_db``
        gain). The API accepts a list for forwards-compat with
        multi-track mixing."""
        body: dict[str, Any] = {
            "base_clip_url": base_clip_url,
            "audio_urls": audio_urls,
            "mix_spec": mix_spec or {},
        }
        data = self.request("POST", "/internal/audio/mix/", json=body)
        try:
            return AudioMixResult(
                output_url=str(data["output_url"]),
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                size_bytes=(
                    int(data["size_bytes"]) if data.get("size_bytes") is not None
                    else None
                ),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"mix_audio response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def add_captions(
        self,
        *,
        clip_url: str,
        captions: list[dict],
    ) -> "ProcessedClipResult":
        """Hit ``POST /internal/clips/captions/`` — burn-in
        subtitles. ``captions`` is a list of
        ``{"start_s", "end_s", "text"}`` entries."""
        data = self.request(
            "POST", "/internal/clips/captions/",
            json={"clip_url": clip_url, "captions": captions},
        )
        return _parse_processed_clip(data, "add_captions")

    def add_intro_outro(
        self,
        *,
        clip_url: str,
        intro: dict | None = None,
        outro: dict | None = None,
    ) -> "ProcessedClipResult":
        """Hit ``POST /internal/clips/intro_outro/`` — prepend
        and/or append title cards. At least one of ``intro`` /
        ``outro`` must be supplied."""
        body: dict[str, Any] = {"clip_url": clip_url}
        if intro is not None:
            body["intro"] = intro
        if outro is not None:
            body["outro"] = outro
        data = self.request("POST", "/internal/clips/intro_outro/", json=body)
        return _parse_processed_clip(data, "add_intro_outro")

    def trim_clip(
        self,
        *,
        clip_url: str,
        start_ms: int,
        end_ms: int,
    ) -> "ProcessedClipResult":
        """Hit ``POST /internal/clips/trim/`` — stream-copy trim."""
        data = self.request(
            "POST", "/internal/clips/trim/",
            json={"clip_url": clip_url, "start_ms": start_ms, "end_ms": end_ms},
        )
        return _parse_processed_clip(data, "trim_clip")

    def reformat_clip(
        self,
        *,
        clip_url: str,
        target_ratio: str,
    ) -> "ProcessedClipResult":
        """Hit ``POST /internal/clips/reformat/`` — scale + crop
        to ``target_ratio`` (e.g., ``720:1280`` for Reels)."""
        data = self.request(
            "POST", "/internal/clips/reformat/",
            json={"clip_url": clip_url, "target_ratio": target_ratio},
        )
        return _parse_processed_clip(data, "reformat_clip")

    def remove_avatar_background(
        self,
        *,
        clip_url: str,
        model: str = "u2net_human_seg",
        # The pipeline runs frame-by-frame through rembg on CPU
        # (~3-4 fps on M-series); a 22s 24fps clip needs ~2.4 min.
        # Default timeout covers a generous 60s clip.
        timeout: float = 900.0,
    ) -> "ProcessedClipResult":
        """Hit ``POST /internal/clips/remove_background/`` — mat
        the avatar out of its Runway-baked white background so a
        downstream ``composite_video`` can layer it over a real
        scene. Returns a WebM with alpha (VP9 / yuva420p)."""
        data = self.request(
            "POST", "/internal/clips/remove_background/",
            json={"clip_url": clip_url, "model": model},
            timeout=timeout,
        )
        return _parse_processed_clip(data, "remove_avatar_background")

    def design_voice(
        self,
        *,
        description: str,
        name: str | None = None,
    ) -> "VoiceDesignResult":
        """Hit ``POST /internal/voices/design/`` — generate a
        custom Runway voice from a text description. Synchronous;
        Runway voice design typically completes in 10-30s."""
        body: dict[str, Any] = {"description": description}
        if name is not None:
            body["name"] = name
        data = self.request("POST", "/internal/voices/design/", json=body)
        try:
            return VoiceDesignResult(
                voice_id=str(data["voice_id"]),
                preview_url=data.get("preview_url"),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"design_voice response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def dub_audio(
        self,
        *,
        audio_url: str,
        target_language: str,
    ) -> "AudioDubResult":
        """Hit ``POST /internal/audio/dub/`` — multilingual voice
        dub. 29 supported languages (ported from the hackathon's
        audio_client). Synchronous; Runway dub typically
        completes in 30-240s."""
        body = {"audio_url": audio_url, "target_language": target_language}
        data = self.request("POST", "/internal/audio/dub/", json=body)
        try:
            return AudioDubResult(
                output_url=str(data["output_url"]),
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                size_bytes=(
                    int(data["size_bytes"]) if data.get("size_bytes") is not None
                    else None
                ),
                target_language=str(data.get("target_language", target_language)),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"dub_audio response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def style_remix(
        self,
        *,
        clip_url: str,
        style_preset: str,
        seed: int | None = None,
        # Aleph is slow — chunked + parallel for clips >5.5s,
        # each chunk a separate Runway gen4_aleph call running
        # ~30-60s. A 10s clip = 2 chunks ~ 2-3 min wall-clock;
        # longer clips can easily hit 8+ min. The default 60s
        # client timeout fired the SESSION 181 dogfood failure
        # before Aleph could even respond. Same shape as V16's
        # remove_avatar_background timeout override (SESSION
        # 179) — long-running endpoints need their own ceiling.
        timeout: float = 900.0,
    ) -> "StyleRemixResult":
        """Hit ``POST /internal/clips/style_remix/`` — Runway
        Aleph (gen4_aleph) via /v1/video_to_video. Synchronous;
        media-engine handles the chunked path internally for
        sources >5.5s. v1 supports 5 presets: noir, anime, chrome,
        watercolor, cyberpunk."""
        body: dict[str, Any] = {
            "clip_url": clip_url,
            "style_preset": style_preset,
        }
        if seed is not None:
            body["seed"] = seed
        data = self.request(
            "POST", "/internal/clips/style_remix/",
            json=body, timeout=timeout,
        )
        try:
            return StyleRemixResult(
                output_url=str(data["output_url"]),
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                size_bytes=(
                    int(data["size_bytes"]) if data.get("size_bytes") is not None
                    else None
                ),
                style_preset=str(data.get("style_preset", style_preset)),
                chunked=bool(data.get("chunked", False)),
                task_ids=list(data.get("task_ids") or []),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"style_remix response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def generate_image(
        self,
        *,
        prompt: str,
        ratio: str = "1280:720",
        seed: int | None = None,
        reference_image_url: str | None = None,
    ) -> "GenerateImageResult":
        """Hit ``POST /internal/images/`` — gen4_image text-to-image.
        Synchronous; polls Runway internally. v1 supports the same
        three aspect ratios as visual_clip (1280:720, 720:1280,
        1024:1024). Reference image is optional; gen4_image's
        hard requirement is satisfied server-side with a neutral
        seed when the operator doesn't supply one."""
        body: dict[str, Any] = {"prompt": prompt, "ratio": ratio}
        if seed is not None:
            body["seed"] = seed
        if reference_image_url is not None:
            body["reference_image_url"] = reference_image_url
        data = self.request("POST", "/internal/images/", json=body)
        try:
            return GenerateImageResult(
                image_url=str(data["image_url"]),
                width=(int(data["width"]) if data.get("width") is not None else None),
                height=(int(data["height"]) if data.get("height") is not None else None),
                seed=(int(data["seed"]) if data.get("seed") is not None else None),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"generate_image response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def list_styles(self) -> dict:
        """W11.6.2 — hit ``GET /internal/styles/``.

        Returns the categorized 42-preset style library snapshot.
        Pure data (no Stability call). Caller is responsible for
        caching — the library is a code-level constant on the
        media-engine.
        """
        return self.request("GET", "/internal/styles/")

    def create_stability_image(
        self,
        *,
        purpose: str,
        subject: str,
        model: str = "sd3-large",
        style_preset: str | None = None,
        aspect_ratio: str = "16:9",
        negative_prompt_override: str | None = None,
        template: str | None = None,
    ) -> "StabilityImageResult":
        """W11.6.1 — hit ``POST /internal/image_stability/``.

        Synchronous; the media-engine handles Stability's retry
        logic internally (sd3-large completes in ~10s real-mode,
        instant in mock). The result carries the base64 data URI
        of the image plus the composed prompt + credit cost so
        the Django side can persist a complete Asset row in one
        request.
        """
        body: dict[str, Any] = {
            "purpose": purpose,
            "subject": subject,
            "model": model,
            "aspect_ratio": aspect_ratio,
        }
        if style_preset is not None:
            body["style_preset"] = style_preset
        if negative_prompt_override is not None:
            body["negative_prompt_override"] = negative_prompt_override
        if template is not None:
            body["template"] = template

        data = self.request("POST", "/internal/image_stability/", json=body)
        try:
            return StabilityImageResult(
                image_data_uri=str(data["image_data_uri"]),
                prompt=str(data.get("prompt") or ""),
                mime_type=str(data.get("mime_type") or "image/png"),
                cost_credits=float(data.get("cost_credits") or 0.0),
                model=str(data.get("model") or model),
                purpose=str(data.get("purpose") or purpose),
                style_preset=data.get("style_preset"),
                aspect_ratio=str(data.get("aspect_ratio") or aspect_ratio),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"create_stability_image response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def audio_extract(
        self,
        *,
        clip_url: str,
        format: str = "mp3",
    ) -> "ProcessedClipResult":
        """Hit ``POST /internal/audio/extract/`` — pull the audio
        track from a CLIP. Synchronous; returns a cached audio
        file URL. v1 supports mp3, aac, wav."""
        data = self.request(
            "POST", "/internal/audio/extract/",
            json={"clip_url": clip_url, "format": format},
        )
        return _parse_processed_clip(data, "audio_extract")

    def transcribe(
        self,
        *,
        source_url: str,
        extract_audio: bool = True,
    ) -> "TranscribeResult":
        """Hit ``POST /internal/transcribe/`` — OpenAI Whisper
        transcription. For CLIP sources set ``extract_audio=True``
        (default) so the media-engine ffmpeg-extracts the audio
        track first; for AUDIO sources set False to skip
        extraction."""
        body = {"source_url": source_url, "extract_audio": extract_audio}
        data = self.request("POST", "/internal/transcribe/", json=body)
        try:
            segments = [
                TranscriptSegment(
                    start_s=float(s["start_s"]),
                    end_s=float(s["end_s"]),
                    text=str(s["text"]),
                )
                for s in (data.get("segments") or [])
            ]
            return TranscribeResult(
                segments=segments,
                duration_seconds=_as_float_or_none(data.get("duration_seconds")),
                language=data.get("language"),
                full_text=str(data.get("full_text", "")),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"transcribe response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def poll_task(self, task_id: str) -> VideoPollResult:
        """Hit ``GET /internal/tasks/{task_id}/`` — the generalised
        poll for every async primitive in the V0+ composition arc.
        Same Runway task ID space + identical response shape as
        ``poll_video``; ``poll_video`` stays for backwards-compat
        with the legacy ``Video`` model until V5/V15 retire it.
        """
        data = self.request("GET", f"/internal/tasks/{task_id}/")
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
                f"poll_task response not in expected shape: {data!r}",
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

    # ---- realtime (R3 — workspace fabric realtime arc) -----------

    def realtime_document_create(
        self,
        *,
        name: str,
        content: str,
        provider: str = "runway",
    ) -> "RealtimeDocumentResult":
        """Hit ``POST /internal/realtime_documents/``. R4 — the broker
        calls this with the composed Markdown body (built shell-side
        from K2 retrieval) before ``realtime_session_create`` so the
        returned ``document_id`` can ride in the session payload's
        ``document_ids`` array."""
        body: dict[str, Any] = {
            "name": name,
            "content": content,
            "provider": provider,
        }
        data = self.request("POST", "/internal/realtime_documents/", json=body)
        try:
            return RealtimeDocumentResult(
                document_id=str(data["document_id"]),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"realtime_document_create response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def realtime_session_create(
        self,
        *,
        avatar_id: str,
        personality: str = "",
        start_script: str = "",
        document_ids: list[str] | None = None,
        tools: list[dict] | None = None,
        provider: str = "runway",
    ) -> "RealtimeSessionResult":
        """Hit ``POST /internal/realtime_sessions/``. Synchronous —
        the media-engine handler creates the upstream session and
        returns the SDK-safe payload. The broker persists session_id
        + session_key on RealtimeSession."""
        body: dict[str, Any] = {
            "avatar_id": avatar_id,
            "personality": personality,
            "start_script": start_script,
            "document_ids": list(document_ids or []),
            "tools": list(tools or []),
            "provider": provider,
        }
        data = self.request("POST", "/internal/realtime_sessions/", json=body)
        try:
            return RealtimeSessionResult(
                session_id=str(data["session_id"]),
                session_key=str(data["session_key"]),
                status=str(data["status"]),
                expires_at=data.get("expires_at"),
                avatar_id=data.get("avatar_id"),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"realtime_session_create response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def realtime_session_poll(
        self,
        session_id: str,
        *,
        provider: str = "runway",
    ) -> "RealtimeSessionPollResult":
        """Hit ``GET /internal/realtime_sessions/<id>/``. Returns the
        upstream session state for the broker's state machine."""
        params = {"provider": provider} if provider != "runway" else None
        data = self.request(
            "GET", f"/internal/realtime_sessions/{session_id}/",
            params=params,
        )
        try:
            return RealtimeSessionPollResult(
                session_id=str(data["session_id"]),
                status=str(data["status"]),
                expires_at=data.get("expires_at"),
                error_message=str(data.get("error_message") or ""),
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"realtime_session_poll response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def realtime_session_fetch_transcript(
        self,
        session_id: str,
        *,
        provider: str = "runway",
    ) -> "RealtimeTranscriptResult":
        """Hit ``GET /internal/realtime_sessions/<id>/transcript/``.
        R5 — broker calls this post-end to persist the transcript
        as a TRANSCRIPT Asset on the workspace.

        Empty transcripts ("conversation not recorded yet") return
        a result with empty text + segments; the caller decides
        whether to retry or accept the empty shape."""
        params = {"provider": provider} if provider != "runway" else None
        data = self.request(
            "GET",
            f"/internal/realtime_sessions/{session_id}/transcript/",
            params=params,
        )
        try:
            segments = list(data.get("segments") or [])
            return RealtimeTranscriptResult(
                session_id=str(data["session_id"]),
                text=str(data.get("text") or ""),
                segments=segments,
                mock_mode=bool(data.get("mock_mode", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MediaEngineError(
                f"realtime_session_fetch_transcript response not in expected shape: {data!r}",
                response_text=str(data),
            ) from exc

    def realtime_session_end(
        self,
        session_id: str,
        *,
        provider: str = "runway",
    ) -> None:
        """Hit ``DELETE /internal/realtime_sessions/<id>/``. Best-effort
        teardown — the broker marks the session ENDED regardless of
        whether the upstream call succeeds."""
        params = {"provider": provider} if provider != "runway" else None
        self.request(
            "DELETE", f"/internal/realtime_sessions/{session_id}/",
            params=params,
        )

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
        timeout: float | None = None,
    ) -> dict:
        """Low-level wrapper. Returns parsed JSON; raises ``MediaEngineError``
        on any non-2xx response or transport error. ``timeout`` overrides
        the client-level default for one call — used by long-running
        endpoints like ``remove_avatar_background`` (rembg pipeline takes
        minutes, not seconds)."""
        url = path if path.startswith("/") else f"/{path}"
        effective_timeout = (
            timeout if timeout is not None else self._timeout
        )
        try:
            response = self._client.request(
                method, url, params=params, json=json,
                timeout=effective_timeout,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "media-engine timeout %s %s after %ss",
                method, url, effective_timeout,
            )
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
