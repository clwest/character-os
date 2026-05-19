"""The ``generate_visual_clip`` step primitive.

SESSION 143 / V4 — silent visual clip generation via Runway's
``/v1/image_to_video`` (``gen4_turbo``) or ``/v1/text_to_video``
(``gen4.5``). The cinematic / backdrop / b-roll building block.

Same fire-then-poll shape as ``generate_avatar_speech`` (V3):
shell calls the media-engine endpoint, polls the generalised
``/internal/tasks/{task_id}/`` route until terminal, persists
the output as a CLIP Asset.

### Inputs

* **Slot ``reference_image``** (optional) — when supplied, the
  asset's ``file_path`` is sent to media-engine as
  ``prompt_image``. Lets V13's ``generate_image`` step feed
  its output into a visual clip step without the operator
  having to thread URLs by hand.

### Params

* ``prompt`` (str, required) — the operator's visual prompt.
* ``prompt_image`` (str, optional) — direct URL override. Takes
  precedence over the ``reference_image`` input slot if both
  are supplied.
* ``ratio`` (str, optional) — ``1280:720`` | ``720:1280`` |
  ``960:960``. Defaults to ``1280:720`` server-side.
* ``duration`` (int, optional) — seconds. ``gen4_turbo``
  accepts ``{5}``; ``gen4.5`` accepts ``{5, 8, 10}``. Defaults
  to 5 server-side.

### Failure paths

All raise ``PrimitiveError`` for the V2 runtime to translate
into a FAILED step:

* Empty / missing prompt
* Media-engine 400 (bad ratio/duration combo) or 502 (Runway
  upstream failure)
* Polling timeout (6-minute deadline)
* Terminal-FAILED Runway task
* Terminal-ready task with no ``output_url``
"""
from __future__ import annotations

import logging
import time
from typing import Any

from apps.compositions.models import AssetRole, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Polling cadence — same shape as V3. Visual-clip renders are
# roughly the same wall-clock cost as avatar_videos in real mode.
_POLL_INTERVAL_S = 2.0
_POLL_DEADLINE_S = 6 * 60


# Rough cost model — Runway's gen4_turbo / gen4.5 are billed at
# ~$0.05 / second of output. Use the requested duration as the
# multiplier with a floor at the 5-second minimum.
_VISUAL_CLIP_MICROS_PER_SECOND = 50_000
_VISUAL_CLIP_MIN_MICROS = 250_000


def _resolve_prompt_image(
    step,
    resolved_inputs: list[dict[str, Any]],
) -> str | None:
    """Pick the prompt_image URL. Order:

    1. Explicit ``prompt_image`` in params (operator override).
    2. ``reference_image`` slot input — use its asset's
       file_path (lets V13's generate_image feed this step).
    3. None (text-to-video path via gen4.5).
    """
    explicit = (step.params or {}).get("prompt_image")
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


class GenerateVisualClipPrimitive:
    """``generate_visual_clip`` step primitive."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        prompt = (step.params or {}).get("prompt", "").strip()
        if not prompt:
            raise PrimitiveError(
                "generate_visual_clip requires a non-empty prompt"
            )

        if mock_mode:
            duration_s = int((step.params or {}).get("duration", 5))
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-visual.mp4"),
                duration_ms=duration_s * 1000,
                width=1280,
                height=720,
                mime_type="video/mp4",
                size_bytes=1024 * 1024,
                cost_micros=GenerateVisualClipPrimitive.estimate_cost(step.params or {}),
                extra_source_spec={
                    "primitive_kind": "generate_visual_clip",
                    "mock": True,
                    "prompt_chars": len(prompt),
                },
                role=AssetRole.BACKDROP.value,
            )

        # ---- real-mode path -----------------------------------

        prompt_image = _resolve_prompt_image(step, resolved_inputs)
        ratio = (step.params or {}).get("ratio")
        duration = (step.params or {}).get("duration")

        try:
            with MediaEngineClient() as client:
                created = client.create_visual_clip(
                    prompt=prompt,
                    ratio=ratio,
                    duration=duration,
                    prompt_image=prompt_image,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine create_visual_clip failed: {exc}"
            ) from exc

        task_id = created.task_id
        logger.info(
            "generate_visual_clip step=%s task=%s mock=%s has_image=%s chars=%d",
            step.id, task_id, created.mock_mode, bool(prompt_image), len(prompt),
        )

        terminal = None
        deadline = time.monotonic() + _POLL_DEADLINE_S
        with MediaEngineClient() as client:
            while time.monotonic() < deadline:
                try:
                    poll = client.poll_task(task_id)
                except MediaEngineError as exc:
                    raise PrimitiveError(
                        f"media-engine poll_task failed: {exc}"
                    ) from exc
                if poll.terminal:
                    terminal = poll
                    break
                time.sleep(_POLL_INTERVAL_S)

        if terminal is None:
            raise PrimitiveError(
                f"visual_clip task {task_id} did not reach terminal state "
                f"within {_POLL_DEADLINE_S}s"
            )

        if not terminal.succeeded:
            raise PrimitiveError(
                f"visual_clip task {task_id} failed: "
                f"{terminal.error or terminal.failure_code or 'unknown'}"
            )

        if not terminal.output_url:
            raise PrimitiveError(
                f"visual_clip task {task_id} succeeded but produced no output_url"
            )

        extra: dict[str, Any] = {
            "primitive_kind": "generate_visual_clip",
            "task_id": task_id,
            "media_engine_mock_mode": terminal.mock_mode,
            "prompt_chars": len(prompt),
            "used_reference_image": bool(prompt_image),
        }
        if ratio:
            extra["ratio"] = ratio
        if duration:
            extra["duration"] = duration

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=terminal.output_url,
            duration_ms=(
                int(terminal.duration_seconds * 1000)
                if terminal.duration_seconds is not None
                else (int(duration) * 1000 if duration else None)
            ),
            mime_type="video/mp4",
            cost_micros=GenerateVisualClipPrimitive.estimate_cost(step.params or {}),
            extra_source_spec=extra,
            role=AssetRole.BACKDROP.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Estimate cost in micros based on requested duration.
        Operators see this in the pre-render forecast (V0
        contract rule 7)."""
        duration = (params or {}).get("duration") or 5
        try:
            duration_s = int(duration)
        except (TypeError, ValueError):
            duration_s = 5
        return max(
            _VISUAL_CLIP_MIN_MICROS,
            duration_s * _VISUAL_CLIP_MICROS_PER_SECOND,
        )
