"""The ``transcribe`` step primitive.

SESSION 143 / V12. OpenAI Whisper transcription via the
media-engine's ``/internal/transcribe/`` endpoint. Accepts
either a CLIP or an AUDIO input — for CLIPs the media-engine
ffmpeg-extracts the audio track before sending to Whisper.

Outputs a TRANSCRIPT Asset whose ``inline_content`` is JSON
containing the segment list:

    [{"start_s": 0.0, "end_s": 2.5, "text": "Welcome to the demo."}, ...]

This is the same shape ``recut_teaser`` reads (via the
``transcription.fetch_transcript`` helper) at composition-
create time. Future compositions that want transcription as a
step (e.g. a "weekly-meeting summary" recipe that transcribes
then synthesizes a brief) use this primitive directly.

### Params

* ``extract_audio`` (bool, default True) — set False for AUDIO
  inputs to skip the ffmpeg extraction step. Default True
  works for both CLIP and AUDIO sources (extraction is a no-op
  on already-audio files but still runs ffmpeg — set False to
  save time when source is known-AUDIO).

### Cost

OpenAI Whisper is ~$0.006/min of audio. v1 uses a flat
50k-micro (~$0.05) estimate that covers most short-form ads
(<10 min). R&D will tighten this once V8/V9 cost telemetry
ships per-step duration probing.
"""
from __future__ import annotations

import json
import logging

from apps.compositions.models import Asset, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


_TRANSCRIBE_MICROS = 50_000  # ~$0.05 — Whisper at $0.006/min


class TranscribePrimitive:
    """``transcribe`` step primitive — Whisper-backed."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        source = _expect_one_av(resolved_inputs)
        params = step.params or {}
        # Auto-detect default: CLIPs need extraction, AUDIO doesn't.
        default_extract = source.asset_type == AssetType.CLIP
        extract_audio = bool(params.get("extract_audio", default_extract))

        if mock_mode:
            # Deterministic stub segments keyed off the step id
            # so re-runs produce the same shape.
            stub_segments = [
                {"start_s": 0.0, "end_s": 2.5, "text": f"Mock segment one ({str(step.id)[:8]})."},
                {"start_s": 2.5, "end_s": 6.0, "text": "This is the strongest line."},
                {"start_s": 6.0, "end_s": 9.0, "text": "Visit us today."},
            ]
            payload = {
                "segments": stub_segments,
                "duration_seconds": 9.0,
                "language": "en",
                "full_text": " ".join(s["text"] for s in stub_segments),
            }
            return PrimitiveResult(
                asset_type=AssetType.TRANSCRIPT,
                file_path=_deterministic_path(str(step.id), "-transcript.json"),
                inline_content=json.dumps(payload),
                mime_type="application/json",
                cost_micros=_TRANSCRIBE_MICROS,
                extra_source_spec={
                    "primitive_kind": "transcribe",
                    "mock": True,
                    "source_asset_id": str(source.id),
                    "source_asset_type": source.asset_type,
                    "segment_count": len(stub_segments),
                },
            )

        if not source.file_path:
            raise PrimitiveError(
                "transcribe: source asset has empty file_path; cannot transcribe"
            )

        try:
            with MediaEngineClient() as client:
                result = client.transcribe(
                    source_url=source.file_path,
                    extract_audio=extract_audio,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine transcribe failed: {exc}"
            ) from exc

        payload = {
            "segments": [
                {"start_s": s.start_s, "end_s": s.end_s, "text": s.text}
                for s in result.segments
            ],
            "duration_seconds": result.duration_seconds,
            "language": result.language,
            "full_text": result.full_text,
        }

        logger.info(
            "transcribe step=%s source=%s segments=%d lang=%s mock=%s",
            step.id, source.id, len(result.segments),
            result.language, result.mock_mode,
        )

        return PrimitiveResult(
            asset_type=AssetType.TRANSCRIPT,
            file_path="",
            inline_content=json.dumps(payload),
            mime_type="application/json",
            cost_micros=_TRANSCRIBE_MICROS,
            extra_source_spec={
                "primitive_kind": "transcribe",
                "source_asset_id": str(source.id),
                "source_asset_type": source.asset_type,
                "segment_count": len(result.segments),
                "language": result.language,
                "media_engine_mock_mode": result.mock_mode,
            },
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _TRANSCRIBE_MICROS


def _expect_one_av(resolved_inputs) -> Asset:
    """Pick the single CLIP or AUDIO asset from
    resolved_inputs. Raises PrimitiveError if zero, multiple,
    or a different type."""
    candidates = []
    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type not in (AssetType.CLIP, AssetType.AUDIO):
            raise PrimitiveError(
                f"transcribe expects CLIP or AUDIO input; got "
                f"{asset.asset_type} in slot {entry.get('slot')!r}"
            )
        candidates.append(asset)
    if len(candidates) != 1:
        raise PrimitiveError(
            f"transcribe expects exactly one CLIP or AUDIO input; got {len(candidates)}"
        )
    return candidates[0]
