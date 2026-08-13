"""Brand Voice Studio + Multilingual Dub Pack (PR H).

Two visible phases (mirroring the Brand Spokesperson Avatar pattern):

    1. ``design_brand_voice(campaign, settings, ...)``
       Designs a custom Runway voice from a templated text description
       via ``POST /v1/voices`` (model ``eleven_multilingual_ttv_v2``),
       polls to READY, downloads Runway's ``previewUrl`` MP3 to local
       cache, persists the voice id + cached preview URL on the campaign
       record.

    2. ``dub_brand_voice(campaign, settings, target_lang)``
       Sends the cached preview MP3 (or whatever audio we picked as the
       dub source) to ``POST /v1/voice_dubbing`` (model
       ``eleven_voice_dubbing``), polls the resulting task, downloads
       the dubbed MP3 to local cache, persists per-language URLs +
       statuses on the campaign record.

Direct TTS narration of arbitrary campaign script (`/v1/text_to_speech`)
is **deferred to a future phase** — the ``voice.type`` discriminator
is gated by Runway and could not be unlocked via probing. See
``docs/research/RUNWAY_API_CAPABILITY_MAP.md`` Appendix C.

Mock mode synthesizes an MP3 placeholder via ffmpeg ``lavfi`` for
every external surface — same dependency we already require for the
Campaign Pack and Avatar Host Clip.

Never raises in normal operation — both phases return structured
result dataclasses and the routers map them to HTTP responses.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from ..config import Settings
from ..models import Campaign

logger = logging.getLogger(__name__)

_VOICE_DESIGN_MODEL = "eleven_multilingual_ttv_v2"
_DUB_MODEL = "eleven_voice_dubbing"
_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB cap per audio artefact

# Validator-dumped enum from the dub schema probe (29 documented).
SUPPORTED_DUB_LANGS: tuple[str, ...] = (
    "en", "hi", "pt", "zh", "es", "fr", "de", "ja", "ar", "ru",
    "ko", "id", "it", "nl", "tr", "pl", "sv", "fil", "ms", "ro",
    "uk", "el", "cs", "da", "fi", "bg", "hr", "sk", "ta",
)


@dataclass
class BrandVoiceResult:
    status: str  # "ready" | "failed" | "mock"
    voice_id: Optional[str] = None
    preview_url: Optional[str] = None  # local /api/... URL
    error: Optional[str] = None
    mock_mode: bool = False


@dataclass
class DubResult:
    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    task_id: Optional[str] = None
    error: Optional[str] = None
    mock_mode: bool = False


class AudioError(RuntimeError):
    """Internal — caught by the public entry points."""


# ---- shared helpers --------------------------------------------------

def is_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _runway_headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }


def _audio_dir(settings: Settings) -> Path:
    d = settings.data_path / "audio"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _voice_preview_path(settings: Settings, campaign_id: str) -> Path:
    return _audio_dir(settings) / f"{campaign_id}-voice-preview.mp3"


def _dub_path(settings: Settings, campaign_id: str, lang: str) -> Path:
    return _audio_dir(settings) / f"{campaign_id}-dub-{lang}.mp3"


def path_for_audio(settings: Settings, campaign_id: str, kind: str) -> Optional[Path]:
    """Resolve an audio artefact path. ``kind`` ∈ {voice-preview, dub-<lang>}.

    Returns None for unknown kinds — the route maps that to 404.
    """
    if kind == "voice-preview":
        return _voice_preview_path(settings, campaign_id)
    if kind.startswith("dub-"):
        lang = kind[len("dub-"):]
        if lang not in SUPPORTED_DUB_LANGS:
            return None
        return _dub_path(settings, campaign_id, lang)
    return None


def build_voice_description(campaign: Campaign, override: Optional[str] = None) -> str:
    """Deterministic local templating for the Brand Voice text-design
    prompt. Runway requires ≥20 characters.
    """
    if override and override.strip():
        return override.strip()[:600]
    tone = campaign.tone or "warm"
    audience = campaign.audience or "modern audiences"
    biz = campaign.business or "the brand"
    return (
        f"A {tone} mid-range American spokesperson voice for {biz}, "
        f"speaking to {audience}. Confident yet inviting, mid-30s, "
        "natural cadence."
    )[:600]


def _download(url: str, target: Path, *, accept_prefix: str = "audio/", timeout: float = 60.0) -> int:
    tmp = target.with_suffix(target.suffix + ".tmp")
    size = 0
    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as resp:
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            if not ctype.startswith(accept_prefix):
                raise AudioError(f"unexpected content-type: {ctype or '(missing)'}")
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > _MAX_AUDIO_BYTES:
                        raise AudioError(
                            f"audio exceeds cap ({_MAX_AUDIO_BYTES} bytes)"
                        )
                    fh.write(chunk)
        tmp.replace(target)
        return size
    except AudioError:
        tmp.unlink(missing_ok=True)
        raise
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        raise AudioError(f"download error: {exc!s}"[:300]) from exc


# ---- mock placeholder generation ------------------------------------

def _ffmpeg_silent_mp3(target: Path, duration_s: int = 4) -> bool:
    """Generate a silent MP3 via ffmpeg lavfi. Returns True on success.

    Stays mock-safe — same dependency we already require for the
    Campaign Pack pipeline.
    """
    if not is_ffmpeg_available():
        return False
    tmp = target.with_suffix(target.suffix + ".tmp")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={duration_s}",
        "-c:a", "libmp3lame", "-b:a", "96k",
        "-f", "mp3",
        str(tmp),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return False
    if result.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        return False
    tmp.replace(target)
    return True


# ---- phase 1: design brand voice -----------------------------------

# §19 Step 6.b (SESSION 245) — this is the reusable transport
# boundary the Runway ``VoiceDesignProvider`` adapter wraps for the
# design operation. Renamed from ``_design_voice_real`` in 6.b so
# the name stops lying about its scope: it is not private to
# ``audio_client``; it is the shared Runway ``POST /v1/voices``
# (``from.type=text``) + poll primitive. Renaming was mechanically
# tiny (single internal caller inside ``design_brand_voice`` below).
def runway_design_voice_transport(
    description: str,
    name: str,
    settings: Settings,
) -> tuple[str, str]:
    """Returns (voice_id, preview_url_from_runway). Raises AudioError."""
    body = {
        "name": name,
        "from": {
            "type": "text",
            "prompt": description,
            "model": _VOICE_DESIGN_MODEL,
        },
    }
    create_url = f"{settings.runway_api_base}/v1/voices"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(create_url, headers=_runway_headers(settings), json=body)
        if resp.status_code != 200:
            raise AudioError(
                f"voice create failed: {resp.status_code} {resp.text[:300]}"
            )
        created = resp.json()
    voice_id = created.get("id")
    if not voice_id:
        raise AudioError(f"voice create missing id: {created}")

    detail_url = f"{settings.runway_api_base}/v1/voices/{voice_id}"
    deadline = time.time() + 90
    final_status = (created.get("status") or "").upper()
    payload = created
    with httpx.Client(timeout=20.0) as client:
        while time.time() < deadline and final_status not in {"READY", "FAILED"}:
            time.sleep(3)
            r = client.get(detail_url, headers=_runway_headers(settings))
            r.raise_for_status()
            payload = r.json()
            final_status = (payload.get("status") or "").upper()
    if final_status == "FAILED":
        raise AudioError("Runway rejected the voice design request.")
    if final_status != "READY":
        raise AudioError(f"voice did not reach READY (final: {final_status})")
    preview = payload.get("previewUrl")
    if not preview:
        raise AudioError("voice READY but no previewUrl")
    return voice_id, preview


def design_brand_voice(
    campaign: Campaign,
    settings: Settings,
    *,
    description_override: Optional[str] = None,
    force_recreate: bool = False,
) -> BrandVoiceResult:
    """Phase 1 — Design Brand Voice. Idempotent unless ``force_recreate``."""
    # Reuse path
    if (
        not force_recreate
        and campaign.brand_voice_id
        and campaign.brand_voice_status in {"ready", "mock"}
    ):
        return BrandVoiceResult(
            status=campaign.brand_voice_status or "ready",
            voice_id=campaign.brand_voice_id,
            preview_url=campaign.brand_voice_preview_url,
            mock_mode=campaign.brand_voice_status == "mock",
        )

    description = build_voice_description(campaign, description_override)
    name = f"Character OS — {(campaign.business or 'campaign')[:40]}"
    target = _voice_preview_path(settings, campaign.id)

    if settings.runway_mock:
        ok = _ffmpeg_silent_mp3(target, duration_s=3)
        if not ok:
            return BrandVoiceResult(
                status="failed",
                error="ffmpeg unavailable for mock voice preview",
                mock_mode=True,
            )
        return BrandVoiceResult(
            status="mock",
            voice_id=f"mock_voice_{uuid.uuid4().hex[:10]}",
            preview_url=f"/api/campaigns/{campaign.id}/audio/voice-preview",
            mock_mode=True,
        )

    try:
        voice_id, preview_url = runway_design_voice_transport(description, name, settings)
        size = _download(preview_url, target, accept_prefix="audio/")
        logger.info(
            "brand voice ready campaign=%s voice=%s preview_bytes=%d",
            campaign.id, voice_id, size,
        )
        return BrandVoiceResult(
            status="ready",
            voice_id=voice_id,
            preview_url=f"/api/campaigns/{campaign.id}/audio/voice-preview",
            mock_mode=False,
        )
    except AudioError as exc:
        logger.warning("brand voice failed campaign=%s: %s", campaign.id, exc)
        return BrandVoiceResult(status="failed", error=str(exc)[:300])
    except httpx.HTTPError as exc:
        logger.warning("brand voice http error: %s", exc)
        return BrandVoiceResult(status="failed", error=f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("brand voice unexpected")
        return BrandVoiceResult(status="failed", error=f"unexpected: {exc!s}"[:300])


# ---- phase 2: multilingual dub --------------------------------------

def _public_preview_url_for(campaign: Campaign, settings: Settings) -> Optional[str]:
    """Resolve a Runway-fetchable URL for the source audio.

    Phase H V1 dubs the Brand Voice preview MP3. We can't hand Runway
    our local /api/... URL (it's not publicly reachable from
    Runway's servers), so we read the file and embed as a data URI.
    """
    target = _voice_preview_path(settings, campaign.id)
    if not target.exists():
        return None
    data = target.read_bytes()
    if len(data) > 4 * 1024 * 1024:  # data-URI sanity cap
        return None
    import base64
    return "data:audio/mpeg;base64," + base64.b64encode(data).decode("ascii")


def _dub_real(
    audio_uri: str, target_lang: str, settings: Settings
) -> tuple[str, str]:
    """Returns (task_id, output_url). Raises AudioError on failure."""
    body = {
        "model": _DUB_MODEL,
        "audioUri": audio_uri,
        "targetLang": target_lang,
    }
    url = f"{settings.runway_api_base}/v1/voice_dubbing"
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, headers=_runway_headers(settings), json=body)
        if resp.status_code != 200:
            raise AudioError(
                f"dub create failed: {resp.status_code} {resp.text[:300]}"
            )
        created = resp.json()
    task_id = created.get("id")
    if not task_id:
        raise AudioError(f"dub create missing task id: {created}")

    deadline = time.time() + 240
    final = None
    with httpx.Client(timeout=20.0) as client:
        while time.time() < deadline:
            r = client.get(
                f"{settings.runway_api_base}/v1/tasks/{task_id}",
                headers=_runway_headers(settings),
            )
            r.raise_for_status()
            payload = r.json()
            status = (payload.get("status") or "").upper()
            if status == "SUCCEEDED":
                final = payload
                break
            if status in {"FAILED", "CANCELED"}:
                reason = payload.get("failure") or payload.get("error") or status
                raise AudioError(f"dub task {status}: {reason}")
            time.sleep(5)
    if not final:
        raise AudioError(f"dub task {task_id} timed out after 4 min")

    output = final.get("output")
    out_url: Optional[str] = None
    if isinstance(output, list):
        for v in output:
            if isinstance(v, str):
                out_url = v
                break
    if not out_url:
        raise AudioError(f"dub task {task_id} produced no output url")
    return task_id, out_url


def dub_brand_voice(
    campaign: Campaign,
    settings: Settings,
    target_lang: str,
) -> DubResult:
    """Phase 2 — Multilingual Dub. Dubs the cached Brand Voice preview
    MP3 into ``target_lang``.  Requires Phase 1 to have run.
    """
    if target_lang not in SUPPORTED_DUB_LANGS:
        return DubResult(
            status="failed",
            error=(
                f"unsupported target_lang '{target_lang}'. supported: "
                f"{sorted(SUPPORTED_DUB_LANGS)}"
            ),
            mock_mode=settings.runway_mock,
        )
    if (
        not campaign.brand_voice_id
        or campaign.brand_voice_status not in {"ready", "mock"}
    ):
        return DubResult(
            status="failed",
            error=(
                "Brand Voice must be designed first. "
                "POST /api/campaigns/{id}/brand-voice."
            ),
            mock_mode=settings.runway_mock,
        )

    target = _dub_path(settings, campaign.id, target_lang)

    if settings.runway_mock:
        ok = _ffmpeg_silent_mp3(target, duration_s=3)
        if not ok:
            return DubResult(
                status="failed",
                error="ffmpeg unavailable for mock dub",
                mock_mode=True,
            )
        return DubResult(
            status="ok",
            output_path=target,
            task_id=f"mock_dub_{uuid.uuid4().hex[:8]}",
            mock_mode=True,
        )

    audio_uri = _public_preview_url_for(campaign, settings)
    if not audio_uri:
        return DubResult(
            status="failed",
            error="cached voice preview missing or too large for dub source",
            mock_mode=False,
        )

    try:
        task_id, out_url = _dub_real(audio_uri, target_lang, settings)
        size = _download(out_url, target, accept_prefix="audio/")
        logger.info(
            "dub ok campaign=%s lang=%s task=%s bytes=%d",
            campaign.id, target_lang, task_id, size,
        )
        return DubResult(
            status="ok",
            output_path=target,
            task_id=task_id,
            mock_mode=False,
        )
    except AudioError as exc:
        logger.warning("dub failed campaign=%s lang=%s: %s", campaign.id, target_lang, exc)
        return DubResult(status="failed", error=str(exc)[:300])
    except httpx.HTTPError as exc:
        logger.warning("dub http error: %s", exc)
        return DubResult(status="failed", error=f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("dub unexpected")
        return DubResult(status="failed", error=f"unexpected: {exc!s}"[:300])


# ---- PR EY — voice_dubbing applied to an existing Spokesperson Ad ----
#
# Pipeline:
#   1. Resolve the source MP4 from the OutputRecord
#   2. ffmpeg-extract its audio track → MP3 (mono 128k, fits the 4MB
#      data URI cap for typical 30-60s ads)
#   3. base64-encode → POST /v1/voice_dubbing (existing `_dub_real`)
#   4. Download the dubbed audio MP3
#   5. ffmpeg-mux: replace the original audio stream with the dubbed
#      MP3 while keeping the video stream intact ("-c:v copy" so we
#      don't re-encode video)
#   6. Save to data/finished/<campaign>-dubbed-<lang>-<output>-<ts>.mp4
#
# Known limitation (documented for the operator + future sessions):
# lip-sync will NOT match the new language because the original video
# stream still has the avatar's mouth moving to English phonemes.
# True lip-synced localization needs LLM-translate the script + re-
# render via avatar_videos — a separate Path B slice.


@dataclass
class DubbedAdResult:
    """Returned from `dub_output_ad`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    task_id: Optional[str] = None
    error: Optional[str] = None
    mock_mode: bool = False


def dub_output_ad(
    *,
    source_video_path: Path,
    campaign_id: str,
    output_id: str,
    target_lang: str,
    settings: Settings,
) -> DubbedAdResult:
    """Dub the audio of an existing rendered ad into ``target_lang``,
    muxing the dubbed audio back into the original video stream.

    Caller is responsible for: validating the OutputRecord exists,
    confirming the source MP4 lives at ``source_video_path``, and
    appending the resulting OutputRecord to the campaign.
    """
    if target_lang not in SUPPORTED_DUB_LANGS:
        return DubbedAdResult(
            status="failed",
            error=(
                f"unsupported target_lang '{target_lang}'. supported: "
                f"{sorted(SUPPORTED_DUB_LANGS)}"
            ),
            mock_mode=settings.runway_mock,
        )

    if not source_video_path.exists():
        return DubbedAdResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
            mock_mode=settings.runway_mock,
        )

    if not is_ffmpeg_available():
        return DubbedAdResult(
            status="failed",
            error="ffmpeg unavailable",
            mock_mode=settings.runway_mock,
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-dubbed-{target_lang}-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Mock mode: produce a deterministic copy of the source so the UI
    # flow exercises end-to-end (gallery + tile + playback) without
    # hitting Runway. The "dubbed" file is just the original — no
    # language transform, but the OutputRecord pathing is real.
    if settings.runway_mock:
        try:
            shutil.copyfile(source_video_path, output_path)
        except Exception as exc:
            return DubbedAdResult(
                status="failed",
                error=f"mock copy failed: {exc!s}"[:300],
                mock_mode=True,
            )
        return DubbedAdResult(
            status="ok",
            output_path=output_path,
            cache_filename=cache_filename,
            duration_s=_ffprobe_duration(source_video_path),
            task_id=f"mock_dub_ad_{uuid.uuid4().hex[:8]}",
            mock_mode=True,
        )

    # Real mode: extract → dub → mux.
    extracted_audio: Optional[Path] = None
    dubbed_audio: Optional[Path] = None
    try:
        # 1. Extract audio from source MP4 → MP3 (mono 128k).
        extracted_audio = (
            finished_dir / f"{campaign_id}-extract-{output_id}-{timestamp}.mp3"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(source_video_path),
                "-vn",                  # no video
                "-ac", "1",             # mono
                "-ar", "44100",
                "-b:a", "128k",
                str(extracted_audio),
            ],
            check=True, capture_output=True, text=True, timeout=60,
        )
        audio_bytes = extracted_audio.read_bytes()
        if len(audio_bytes) > 4 * 1024 * 1024:
            return DubbedAdResult(
                status="failed",
                error=(
                    f"extracted audio {len(audio_bytes):,} bytes exceeds "
                    f"the 4MB data URI cap. Try a shorter ad or lower bitrate."
                ),
            )
        import base64 as _b64
        audio_uri = (
            "data:audio/mpeg;base64,"
            + _b64.b64encode(audio_bytes).decode("ascii")
        )

        # 2. Fire Runway voice_dubbing.
        task_id, out_url = _dub_real(audio_uri, target_lang, settings)

        # 3. Download the dubbed audio.
        dubbed_audio = (
            finished_dir / f"{campaign_id}-dubbed-audio-{output_id}-{timestamp}.mp3"
        )
        _download(out_url, dubbed_audio, accept_prefix="audio/")

        # 4. Mux dubbed audio + original video. `-c:v copy` keeps the
        #    video stream untouched (no re-encode). `-shortest` so
        #    the output truncates if the audio is slightly off the
        #    video duration. AAC re-encode of the dubbed audio for
        #    MP4 container compatibility.
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(source_video_path),
                "-i", str(dubbed_audio),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                "-movflags", "+faststart",
                str(output_path),
            ],
            check=True, capture_output=True, text=True, timeout=120,
        )
        duration = _ffprobe_duration(output_path)
        logger.info(
            "dub-ad ok campaign=%s lang=%s output=%s bytes=%d duration=%.2f task=%s",
            campaign_id, target_lang, output_id,
            output_path.stat().st_size, duration or 0.0, task_id,
        )
        return DubbedAdResult(
            status="ok",
            output_path=output_path,
            cache_filename=cache_filename,
            duration_s=duration,
            task_id=task_id,
        )
    except AudioError as exc:
        logger.warning(
            "dub-ad failed campaign=%s lang=%s: %s",
            campaign_id, target_lang, exc,
        )
        return DubbedAdResult(status="failed", error=str(exc)[:300])
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()[:300] if exc.stderr else ""
        logger.warning(
            "dub-ad ffmpeg failed campaign=%s lang=%s err=%s",
            campaign_id, target_lang, stderr,
        )
        return DubbedAdResult(
            status="failed",
            error=f"ffmpeg failed: {stderr}"[:300],
        )
    except httpx.HTTPError as exc:
        logger.warning("dub-ad http error: %s", exc)
        return DubbedAdResult(status="failed", error=f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("dub-ad unexpected")
        return DubbedAdResult(status="failed", error=f"unexpected: {exc!s}"[:300])
    finally:
        # Cleanup intermediate files (extracted source audio + dubbed
        # audio). Best-effort.
        for p in (extracted_audio, dubbed_audio):
            try:
                if p is not None and p.exists():
                    p.unlink()
            except Exception:
                pass


def _ffprobe_duration(path: Path) -> Optional[float]:
    """Best-effort duration extraction; returns None on failure."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True, capture_output=True, text=True, timeout=10,
        )
        return float(out.stdout.strip() or 0.0)
    except Exception:
        return None
