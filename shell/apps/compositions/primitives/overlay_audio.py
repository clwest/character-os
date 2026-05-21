"""The ``overlay_audio_at_offset`` step primitive.

SESSION 212 / VO.2. Second primitive in the voiceover arc. Takes a
base CLIP plus a voiceover AUDIO asset and splices the VO into the
base's audio track at ``offset_seconds``, ducking the base by
``duck_db`` during the VO window. ffmpeg-only — no Runway or
ElevenLabs call.

Pairs with ``synthesize_voiceover_audio`` (VO.1) to unlock the
``cta_swap`` (VO.3) and ``narrated_intro`` (VO.4) starters. Standalone
it's also the seam B-12 (SFX overlay) will plug into post-arc.

### Inputs

* Slot ``base`` — must be a CLIP asset. The video stream is preserved
  byte-for-byte by the media-engine route (rule 4); only audio is
  re-encoded.
* Slot ``voiceover`` — must be an AUDIO asset (typically a
  ``synthesize_voiceover_audio`` output, but any AUDIO Asset works).

### Params

* ``offset_seconds`` (float, required, ≥ 0) — when in the base's
  timeline the VO begins playing.
* ``duck_db`` (float, default -18, range [-60, 0]) — how far to
  attenuate the base audio under the VO window. ``0`` = no duck,
  ``-60`` = effectively silent.

### Output

One CLIP Asset whose ``file_path`` is the media-engine-served MP4 URL
and whose role is inherited from the base CLIP (e.g. a TALKING_HEAD
base produces a TALKING_HEAD output — VO swap doesn't change the
asset's semantic role per the VO.0 lock).

### Rules enforced shell-side

* **Rule 6 — offset + vo_duration must fit inside base.**
  ``offset_seconds + voiceover.duration_seconds > base.duration_seconds``
  raises ``PrimitiveError`` with an actionable message. The media-engine
  route re-checks via ffprobe (defense in depth).
* **Rule 5 — duck_db range gate.** ``[-60, 0]`` enforced before the
  HTTP roundtrip.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.compositions.asset_roles import PRIMITIVE_TO_ROLE
from apps.compositions.models import Asset, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Cost model — ffmpeg-only, no provider billing. Same floor as
# audio_extract; the operator is paying for the underlying base
# render (talking_head) + the VO synthesis separately.
_OVERLAY_AUDIO_MICROS = 100

_DEFAULT_DUCK_DB = -18.0
_MIN_DUCK_DB = -60.0
_MAX_DUCK_DB = 0.0


class OverlayAudioAtOffsetPrimitive:
    """``overlay_audio_at_offset`` step primitive — VO splice with
    window-only duck on the base. ffmpeg-only via the
    ``/internal/clips/overlay_audio/`` route."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        base_clip, voiceover = _expect_base_and_voiceover(resolved_inputs)

        params = step.params or {}
        offset_seconds = _coerce_offset(params.get("offset_seconds"))
        duck_db = _coerce_duck_db(params.get("duck_db"))

        # Rule 6 — shell-side primitive enforcement using the
        # persisted Asset.duration_ms. The media-engine route
        # ffprobes as a backstop, but failing here saves an
        # HTTP roundtrip and surfaces the operator-facing message
        # earlier.
        base_duration_s = (base_clip.duration_ms or 0) / 1000.0
        vo_duration_s = (voiceover.duration_ms or 0) / 1000.0
        if (
            base_duration_s > 0
            and vo_duration_s > 0
            and offset_seconds + vo_duration_s > base_duration_s + 0.05
        ):
            overflow = offset_seconds + vo_duration_s - base_duration_s
            raise PrimitiveError(
                f"VO would extend {overflow:.2f}s past base clip end "
                f"(offset={offset_seconds:.2f}s + "
                f"vo_duration={vo_duration_s:.2f}s > "
                f"base_duration={base_duration_s:.2f}s); "
                "shorten the VO text or extend the base render"
            )

        # Propagate base role (e.g. TALKING_HEAD stays TALKING_HEAD per
        # the VO.0 spec) when available; fall back to the static
        # primitive→role mapping otherwise.
        output_role = (
            getattr(base_clip.role, "value", None)
            or base_clip.role
            or PRIMITIVE_TO_ROLE["overlay_audio_at_offset"]
        )

        extra_base: dict[str, Any] = {
            "primitive_kind": "overlay_audio_at_offset",
            "base_asset_id": str(base_clip.id),
            "voiceover_asset_id": str(voiceover.id),
            "offset_seconds": offset_seconds,
            "duck_db": duck_db,
            "base_duration_seconds": base_duration_s or None,
            "vo_duration_seconds": vo_duration_s or None,
            "base_role": output_role,
        }

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-overlay.mp4"),
                duration_ms=base_clip.duration_ms,
                width=base_clip.width,
                height=base_clip.height,
                mime_type="video/mp4",
                size_bytes=base_clip.size_bytes or 1024 * 1024,
                cost_micros=_OVERLAY_AUDIO_MICROS,
                extra_source_spec={**extra_base, "mock": True},
                role=output_role,
            )

        if not base_clip.file_path:
            raise PrimitiveError(
                "overlay_audio_at_offset: base CLIP has empty file_path"
            )
        if not voiceover.file_path:
            raise PrimitiveError(
                "overlay_audio_at_offset: voiceover AUDIO has empty file_path"
            )

        try:
            with MediaEngineClient() as client:
                result = client.overlay_audio(
                    base_url=base_clip.file_path,
                    vo_url=voiceover.file_path,
                    offset_seconds=offset_seconds,
                    duck_db=duck_db,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine overlay_audio failed: {exc}"
            ) from exc

        # Duration follows the base — rule 4 says the video stream is
        # byte-identical, so length doesn't change. The media-engine
        # echoes a probed duration_seconds when it can; prefer that
        # over our cached base_clip.duration_ms when present.
        if result.duration_seconds is not None and result.duration_seconds > 0:
            duration_ms = int(result.duration_seconds * 1000)
        else:
            duration_ms = base_clip.duration_ms

        logger.info(
            "overlay_audio_at_offset step=%s base=%s vo=%s offset=%.2fs "
            "duck=%.1fdB output=%s mock=%s",
            step.id, base_clip.id, voiceover.id, offset_seconds, duck_db,
            result.output_url, result.mock_mode,
        )

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=base_clip.width,
            height=base_clip.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_OVERLAY_AUDIO_MICROS,
            extra_source_spec={
                **extra_base,
                "media_engine_mock_mode": result.mock_mode,
            },
            role=output_role,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _OVERLAY_AUDIO_MICROS


def _expect_base_and_voiceover(resolved_inputs) -> tuple[Asset, Asset]:
    """Resolve the two slots — ``base`` (CLIP) + ``voiceover`` (AUDIO).
    Both must be present and the asset_type must match the slot."""
    base_clip: Asset | None = None
    voiceover: Asset | None = None

    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        slot = (entry.get("slot") or "").lower()
        if slot == "base" or (
            slot == "" and base_clip is None and asset.asset_type == AssetType.CLIP
        ):
            if asset.asset_type != AssetType.CLIP:
                raise PrimitiveError(
                    f"overlay_audio_at_offset slot 'base' expects a CLIP "
                    f"asset; got {asset.asset_type}"
                )
            if base_clip is not None:
                raise PrimitiveError(
                    "overlay_audio_at_offset received a second CLIP for "
                    "slot 'base'"
                )
            base_clip = asset
        elif slot == "voiceover" or (
            slot == "" and voiceover is None and asset.asset_type == AssetType.AUDIO
        ):
            if asset.asset_type != AssetType.AUDIO:
                raise PrimitiveError(
                    f"overlay_audio_at_offset slot 'voiceover' expects an "
                    f"AUDIO asset; got {asset.asset_type}"
                )
            if voiceover is not None:
                raise PrimitiveError(
                    "overlay_audio_at_offset received a second AUDIO for "
                    "slot 'voiceover'"
                )
            voiceover = asset
        else:
            raise PrimitiveError(
                f"overlay_audio_at_offset got unexpected slot "
                f"{slot!r} with asset_type {asset.asset_type}; "
                "expected 'base' (CLIP) + 'voiceover' (AUDIO)"
            )

    if base_clip is None:
        raise PrimitiveError(
            "overlay_audio_at_offset requires a CLIP input in slot 'base'"
        )
    if voiceover is None:
        raise PrimitiveError(
            "overlay_audio_at_offset requires an AUDIO input in slot "
            "'voiceover'"
        )
    return base_clip, voiceover


def _coerce_offset(value) -> float:
    """Validate ``offset_seconds`` param. Required + ≥ 0."""
    if value is None:
        raise PrimitiveError(
            "overlay_audio_at_offset requires offset_seconds param"
        )
    try:
        offset = float(value)
    except (TypeError, ValueError) as exc:
        raise PrimitiveError(
            f"overlay_audio_at_offset.offset_seconds must be numeric; "
            f"got {value!r}"
        ) from exc
    if offset < 0:
        raise PrimitiveError(
            f"overlay_audio_at_offset.offset_seconds must be ≥ 0; "
            f"got {offset}"
        )
    return offset


def _coerce_duck_db(value) -> float:
    """Validate ``duck_db`` param — default -18, range [-60, 0]."""
    if value is None:
        return _DEFAULT_DUCK_DB
    try:
        duck = float(value)
    except (TypeError, ValueError) as exc:
        raise PrimitiveError(
            f"overlay_audio_at_offset.duck_db must be numeric; "
            f"got {value!r}"
        ) from exc
    if duck < _MIN_DUCK_DB or duck > _MAX_DUCK_DB:
        raise PrimitiveError(
            f"overlay_audio_at_offset.duck_db must be in "
            f"[{_MIN_DUCK_DB}, {_MAX_DUCK_DB}]; got {duck}"
        )
    return duck
