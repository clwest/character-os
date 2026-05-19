"""The ``style_remix`` step primitive — Aleph visual transform.

SESSION 143 / V11. Ports the hackathon's aleph_client.py — Runway
``/v1/video_to_video`` via the ``gen4_aleph`` model. Production-
tested at the hackathon (operators used the presets live); V11
restores it under Asset+Composition shape.

### How chunking works (it does, transparently)

Aleph has a hard ~5s output cap regardless of source length.
Sources longer than ~5.5s get split + parallel-remixed +
concatenated server-side by the media-engine endpoint. The shell
primitive doesn't see the chunking — it just submits one
``clip_url`` and gets back one ``output_url`` covering the full
timeline. The ``source_spec`` records whether chunking ran +
the Runway task ids for audit.

### Params

* ``style_preset`` (str, required) — one of v1's 5 supported
  presets: ``noir`` | ``anime`` | ``chrome`` | ``watercolor`` |
  ``cyberpunk``. Hackathon-identical prompts; operators who
  used a preset in production get the same Aleph behavior.
* ``seed`` (int, optional) — Runway seed for reproducibility +
  cross-chunk style coherence. When omitted, media-engine picks
  one at request time (cached so retries still cache-hit).

### Inputs

Exactly one CLIP. Non-CLIP raises PrimitiveError.

### Output

One CLIP Asset. ``source_spec`` carries:
* ``style_preset`` — which preset ran
* ``chunked`` — whether the chunked path ran
* ``task_ids`` — Runway task ids (length 1 for single-fire, N
  for chunked)
* ``seed`` — the seed used (operator-supplied or random)
"""
from __future__ import annotations

import logging
from typing import Any

from apps.compositions.models import AssetRole, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Same five presets as the hackathon's STYLE_PRESETS + the
# media-engine's ALEPH_STYLE_PRESETS. Duplicated here so the
# primitive can fail-fast on unknown preset names before any
# RPC fires.
SUPPORTED_STYLE_PRESETS: frozenset[str] = frozenset({
    "noir", "anime", "chrome", "watercolor", "cyberpunk",
})


# Cost model — Aleph is more expensive than gen4_turbo
# (the chunked path can fire 5+ Aleph calls for a 25-second
# source). Conservative single-fire estimate ~$0.50;
# operator-visible total scales with composition step count
# rather than per-primitive.
_STYLE_REMIX_MICROS = 500_000


class StyleRemixPrimitive:
    """``style_remix`` step primitive — Aleph visual transform."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        preset = str(params.get("style_preset", "")).strip().lower()
        if not preset:
            raise PrimitiveError(
                "style_remix requires a style_preset param"
            )
        if preset not in SUPPORTED_STYLE_PRESETS:
            raise PrimitiveError(
                f"style_remix style_preset {preset!r} not supported. "
                f"Supported: {sorted(SUPPORTED_STYLE_PRESETS)}"
            )
        seed = params.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError):
                raise PrimitiveError("style_remix seed must be an integer")

        base = _expect_one_clip(resolved_inputs)

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(
                    str(step.id), f"-remix-{preset}.mp4",
                ),
                duration_ms=base.duration_ms,
                width=base.width,
                height=base.height,
                mime_type="video/mp4",
                size_bytes=base.size_bytes or 1024 * 1024,
                cost_micros=_STYLE_REMIX_MICROS,
                extra_source_spec={
                    "primitive_kind": "style_remix",
                    "mock": True,
                    "source_asset_id": str(base.id),
                    "style_preset": preset,
                    "seed": seed,
                    "chunked": False,
                },
                role=AssetRole.POLISH_OUTPUT.value,
            )

        if not base.file_path:
            raise PrimitiveError(
                "style_remix: base CLIP has empty file_path; cannot remix"
            )

        try:
            with MediaEngineClient() as client:
                result = client.style_remix(
                    clip_url=base.file_path,
                    style_preset=preset,
                    seed=seed,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine style_remix failed: {exc}"
            ) from exc

        logger.info(
            "style_remix step=%s preset=%s chunked=%s tasks=%d mock=%s",
            step.id, preset, result.chunked,
            len(result.task_ids), result.mock_mode,
        )

        duration_ms = base.duration_ms
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)

        extra: dict[str, Any] = {
            "primitive_kind": "style_remix",
            "source_asset_id": str(base.id),
            "style_preset": preset,
            "seed": seed,
            "chunked": result.chunked,
            "task_ids": result.task_ids,
            "media_engine_mock_mode": result.mock_mode,
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=base.width,
            height=base.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_STYLE_REMIX_MICROS,
            extra_source_spec=extra,
            role=AssetRole.POLISH_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _STYLE_REMIX_MICROS


def _expect_one_clip(resolved_inputs):
    """Pick the single CLIP asset from resolved_inputs."""
    clips = []
    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type != AssetType.CLIP:
            raise PrimitiveError(
                f"style_remix expects exactly one CLIP input; got "
                f"{asset.asset_type} in slot {entry.get('slot')!r}"
            )
        clips.append(asset)
    if len(clips) != 1:
        raise PrimitiveError(
            f"style_remix expects exactly one CLIP input; got {len(clips)}"
        )
    return clips[0]
