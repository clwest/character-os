"""The ``remove_avatar_background`` step primitive.

SESSION 179 / V16. Matt the avatar out of its Runway-baked white
square so downstream ``composite_video`` (kind=backdrop) can lay
the avatar over any scene without the picture-frame look. The
media-engine pipeline is ffmpeg-decode -> rembg(u2net_human_seg)
-> ffmpeg-encode (VP9 with yuva420p alpha) and is heavy
(~2.4 min for a 22s 24fps clip on M-series CPU). Caller is
already async via Celery, so wall-clock latency lands on the
Composition row, not on a request.

### Inputs

Exactly one CLIP input (typically the output of
``generate_avatar_speech``). The single-input restriction is
deliberate — chained matting passes are an anti-pattern (each
pass loses edge detail).

### Params

* ``model`` (str, optional) — rembg model id. Defaults to
  ``u2net_human_seg``. The v1 catalog only ships this one.

### Output

One CLIP Asset whose ``file_path`` is the cached WebM URL on the
media-engine. ``duration_ms`` carries through from the input
(the matter doesn't change duration). ``mime_type`` is
``video/webm`` so the SPA player tags it correctly.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.compositions.models import Asset, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# CPU-bound work on the media-engine side (no API spend). Set to
# 200 micros so estimate_composition_cost surfaces it as non-zero
# (it shows up on the cost preview) without overstating the
# dollar cost — the real cost here is wall-clock time, not money.
_REMOVE_BG_MICROS = 200

# Single-source-of-truth list of supported rembg model ids. Must
# stay in sync with media-engine's ``_REMOVE_BACKGROUND_MODELS``.
_VALID_MODELS = {"u2net_human_seg"}


class RemoveAvatarBackgroundPrimitive:
    """``remove_avatar_background`` step primitive — rembg portrait
    matting via the media-engine."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        model = (params.get("model") or "u2net_human_seg").strip()
        if model not in _VALID_MODELS:
            raise PrimitiveError(
                f"remove_avatar_background model must be one of "
                f"{sorted(_VALID_MODELS)}; got {model!r}"
            )

        clips: list[Asset] = []
        for entry in resolved_inputs or []:
            asset = entry.get("asset")
            if asset is None:
                continue
            if asset.asset_type != AssetType.CLIP:
                raise PrimitiveError(
                    f"remove_avatar_background expects a CLIP input; "
                    f"got {asset.asset_type} in slot "
                    f"{entry.get('slot')!r}"
                )
            clips.append(asset)

        if len(clips) != 1:
            raise PrimitiveError(
                f"remove_avatar_background requires exactly one CLIP "
                f"input; got {len(clips)}"
            )
        source = clips[0]

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(
                    str(step.id), "-matted.webm",
                ),
                duration_ms=source.duration_ms,
                width=source.width,
                height=source.height,
                mime_type="video/webm",
                size_bytes=1024 * 1024,
                cost_micros=_REMOVE_BG_MICROS,
                extra_source_spec={
                    "primitive_kind": "remove_avatar_background",
                    "mock": True,
                    "model": model,
                    "source_asset_id": str(source.id),
                },
            )

        # ---- real-mode path -----------------------------------

        if not source.file_path:
            raise PrimitiveError(
                "remove_avatar_background: source clip has empty "
                "file_path; cannot mat"
            )

        try:
            with MediaEngineClient() as client:
                result = client.remove_avatar_background(
                    clip_url=source.file_path,
                    model=model,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine remove_avatar_background failed: {exc}"
            ) from exc

        logger.info(
            "remove_avatar_background step=%s model=%s output=%s mock=%s",
            step.id, model, result.output_url, result.mock_mode,
        )

        # The matter doesn't change duration. Prefer media-engine's
        # number if surfaced; else fall through from the source.
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)
        else:
            duration_ms = source.duration_ms

        extra: dict[str, Any] = {
            "primitive_kind": "remove_avatar_background",
            "model": model,
            "source_asset_id": str(source.id),
            "media_engine_mock_mode": result.mock_mode,
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=source.width,
            height=source.height,
            mime_type="video/webm",
            size_bytes=result.size_bytes,
            cost_micros=_REMOVE_BG_MICROS,
            extra_source_spec=extra,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _REMOVE_BG_MICROS
