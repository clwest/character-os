"""The ``generate_image`` step primitive.

SESSION 143 / V13. Runway gen4_image text-to-image via the
media-engine's ``/internal/images/`` route. Sibling to V4's
``generate_visual_clip`` — produces a still IMAGE Asset
(typically used as a reference frame for subsequent
``generate_visual_clip`` steps in storyboard compositions).

### Inputs

Optional ``reference_image`` slot — when supplied, the
operator's reference image guides Runway's generation
(consistent character appearance across shots, brand color
palette, etc.). When omitted, the media-engine seeds with a
neutral 1x1 grey image (gen4_image requires at least one
reference image; the neutral seed is a transparent no-op).

### Params

* ``prompt`` (str, required) — visual prompt for Runway.
* ``ratio`` (str, optional) — ``1280:720`` (default) |
  ``720:1280`` | ``1024:1024``.
* ``seed`` (int, optional) — Runway seed for reproducibility.

### Output

One IMAGE Asset whose ``file_path`` is the local cached PNG
URL. ``width``/``height`` populated from the ratio.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.compositions.models import Asset, AssetRole, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Cost model: gen4_image is ~$0.04 per image. Most storyboards
# need 3 images; v1 uses a flat 40k-micro estimate.
_GENERATE_IMAGE_MICROS = 40_000


SUPPORTED_IMAGE_RATIOS: frozenset[str] = frozenset({
    "1280:720", "720:1280", "1024:1024",
})


class GenerateImagePrimitive:
    """``generate_image`` step primitive."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        prompt = str(params.get("prompt", "")).strip()
        if len(prompt) < 4:
            raise PrimitiveError(
                "generate_image requires a prompt of at least 4 characters"
            )
        ratio = str(params.get("ratio", "1280:720")).strip()
        if ratio not in SUPPORTED_IMAGE_RATIOS:
            raise PrimitiveError(
                f"generate_image ratio {ratio!r} not supported. "
                f"Supported: {sorted(SUPPORTED_IMAGE_RATIOS)}"
            )
        seed = params.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError):
                raise PrimitiveError("generate_image seed must be an integer")

        ref_url = _resolve_reference_image_url(resolved_inputs, params)

        # Dims from ratio.
        w, _, h = ratio.partition(":")
        try:
            width, height = int(w), int(h)
        except ValueError:
            width, height = 1280, 720

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.IMAGE,
                file_path=_deterministic_path(str(step.id), "-image.png"),
                width=width,
                height=height,
                mime_type="image/png",
                size_bytes=1024,
                cost_micros=_GENERATE_IMAGE_MICROS,
                extra_source_spec={
                    "primitive_kind": "generate_image",
                    "mock": True,
                    "prompt_chars": len(prompt),
                    "ratio": ratio,
                    "seed": seed,
                    "used_reference_image": bool(ref_url),
                },
                role=AssetRole.REFERENCE_IMAGE.value,
            )

        try:
            with MediaEngineClient() as client:
                result = client.generate_image(
                    prompt=prompt,
                    ratio=ratio,
                    seed=seed,
                    reference_image_url=ref_url,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine generate_image failed: {exc}"
            ) from exc

        logger.info(
            "generate_image step=%s ratio=%s prompt_chars=%d ref=%s mock=%s",
            step.id, ratio, len(prompt), bool(ref_url), result.mock_mode,
        )

        return PrimitiveResult(
            asset_type=AssetType.IMAGE,
            file_path=result.image_url,
            width=result.width or width,
            height=result.height or height,
            mime_type="image/png",
            cost_micros=_GENERATE_IMAGE_MICROS,
            extra_source_spec={
                "primitive_kind": "generate_image",
                "prompt_chars": len(prompt),
                "ratio": ratio,
                "seed": result.seed,
                "used_reference_image": bool(ref_url),
                "media_engine_mock_mode": result.mock_mode,
            },
            role=AssetRole.REFERENCE_IMAGE.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _GENERATE_IMAGE_MICROS


def _resolve_reference_image_url(
    resolved_inputs,
    params: dict,
) -> str | None:
    """Pick the reference image URL.

    Order:
      1. Explicit ``reference_image_url`` in params.
      2. ``reference_image`` slot input pointing at an IMAGE
         asset — use its file_path.
      3. None (media-engine seeds with neutral 1x1 grey).
    """
    explicit = (params or {}).get("reference_image_url")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    for entry in resolved_inputs or []:
        if entry.get("slot") != "reference_image":
            continue
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type != AssetType.IMAGE:
            raise PrimitiveError(
                f"reference_image slot expects an IMAGE asset, "
                f"got {asset.asset_type}"
            )
        if asset.file_path:
            return asset.file_path

    return None
