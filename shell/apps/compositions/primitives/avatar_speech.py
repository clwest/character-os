"""The ``generate_avatar_speech`` step primitive.

SESSION 143 / V3 — the first real primitive in the composition
arc. Wraps Runway's talking-head endpoint (``/v1/avatar_videos``,
``gwm1_avatars``) via the media-engine's new
``/internal/clips/avatar_speech/`` route.

Closes the K6.5 audit finding from SESSION 141: the spokesperson
will now render *speaking* the synthesized script, not as a
silent animated portrait. K6.5 is dissolved into this slice per
the V0 scope lock — same Runway endpoint target, landing inside
the new Asset+Composition shape so it's reusable for every later
primitive.

### Behavior

* **Mock-mode**: short-circuits to a deterministic stub CLIP
  result. Cost zero, no media-engine call. Tests + local dev
  rely on this — same shape as the V2 ``mock_passthrough``.
* **Real-mode**: fires ``MediaEngineClient.create_avatar_speech``,
  polls via ``poll_task`` until terminal, returns a
  PrimitiveResult carrying the Runway-side output URL. Raises
  ``PrimitiveError`` on media-engine failure, polling timeout,
  or terminal-FAILED status.
* **Knowledge integration**: when ``params['use_knowledge']``
  is truthy, the script is run through K6's ``build_render_brief``
  first. The synthesized brief gets sent to media-engine; the
  retrieved chunk ids are recorded in the Asset's
  ``source_spec.knowledge_chunk_ids``.

### Params

* ``script`` (str, required) — the words the avatar should
  speak.
* ``spokesperson_avatar_id`` (str, optional) — overrides the
  composition spokesperson's bound avatar. Rarely useful;
  primary path takes it from the composition's spokesperson.
* ``use_knowledge`` (bool, default False) — pipe the script
  through K6 synthesis before sending.
* ``ratio`` (str, optional) — forwards-compat. Runway's
  avatar_videos endpoint controls aspect ratio server-side
  in v1.
* ``duration`` (int, optional) — forwards-compat. Same
  reason.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from apps.compositions.models import AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Polling cadence — mirrors apps/videos/tasks.poll_video_until_terminal.
# Avatar-video render takes ~30-180 s real-mode, instant in mock.
_POLL_INTERVAL_S = 2.0
_POLL_DEADLINE_S = 6 * 60  # 6-minute ceiling per hackathon precedent


# Rough cost model: Runway's avatar_videos is ~$0.05 / second of
# output. At ~150 chars/second of speech at conversational pace,
# that's ~$0.000333 / char ≈ 333 micros/char. Floor at the
# minimum-duration clip (5 seconds = ~$0.25 = 250k micros) so
# very short scripts still reflect the call-overhead. R&D should
# replace these constants with real telemetry once V8's
# cost-surface work lands.
_AVATAR_SPEECH_MICROS_PER_CHAR = 333
_AVATAR_SPEECH_MIN_MICROS = 250_000


def _resolve_avatar_id(step, composition) -> str:
    """Pick the avatar id from params (explicit) or fall back to
    the composition's spokesperson. Raises ``PrimitiveError`` if
    neither path produces an id."""
    explicit = (step.params or {}).get("spokesperson_avatar_id", "").strip()
    if explicit:
        return explicit
    spokesperson = composition.spokesperson
    if not spokesperson.runway_avatar_id:
        raise PrimitiveError(
            f"composition spokesperson {spokesperson.name!r} has no "
            f"runway_avatar_id; create the avatar before rendering"
        )
    return spokesperson.runway_avatar_id


def _maybe_synthesize_script(step, composition) -> tuple[str, list[str], list[dict]]:
    """Return ``(brief, chunk_ids, verification_warnings)``.

    When ``use_knowledge`` is truthy, the operator's script
    goes through K6's ``build_render_brief`` and we return the
    synthesized brief + citation ids + K6.4 verifier output.
    Otherwise the script is used verbatim, the citation list
    is empty, and verification is skipped (operator-typed
    scripts are trusted; the verifier exists to catch LLM
    invention, not operator typing).

    In Strict verifier mode, ``build_render_brief`` raises
    ``ClaimVerifierError`` before this function returns; the
    caller catches it and converts to ``PrimitiveError``.
    """
    raw_script = (step.params or {}).get("script", "").strip()
    if not raw_script:
        raise PrimitiveError("generate_avatar_speech requires a non-empty script")

    use_knowledge = bool((step.params or {}).get("use_knowledge"))
    if not use_knowledge:
        return raw_script, [], []

    # Lazy import — keep this primitive importable even if K6's
    # script_synthesis isn't wired yet (it is, but defensive).
    from character_os.claim_verifier import ClaimVerifierError
    from character_os.script_synthesis import build_render_brief

    try:
        result = build_render_brief(
            composition.spokesperson, raw_script,
        )
    except ClaimVerifierError as exc:
        # Strict mode — surface as a primitive failure so the
        # composition fails before Runway is asked to render
        # the bad script. K6.4.1: persist the synthesized text
        # + warning dicts onto the composition so the operator
        # can review what the LLM said and what got flagged.
        # Without this, the failure surface is just the error
        # message string and operators have no way to triage.
        composition.verification_warnings = [u.to_dict() for u in exc.unsupported]
        composition.rejected_synthesis = exc.synthesized_text or ""
        composition.save(
            update_fields=["verification_warnings", "rejected_synthesis"],
        )
        raise PrimitiveError(
            f"K6.4 claim verifier rejected the synthesized script "
            f"({len(exc.unsupported)} unsupported claim(s)): "
            + ", ".join(f"{u.claim!r}" for u in exc.unsupported)
        ) from exc
    return (
        result.brief,
        list(result.chunk_ids or []),
        list(result.verification_warnings or []),
    )


class GenerateAvatarSpeechPrimitive:
    """``generate_avatar_speech`` step primitive — Runway
    talking-head via ``/internal/clips/avatar_speech/``."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        composition = step.composition

        # Mock-mode short-circuit. Deterministic clip output —
        # tests assert against a stable file_path keyed off the
        # step id. Composition-level mock_mode overrides any
        # media-engine setting.
        if mock_mode:
            script = (step.params or {}).get("script", "").strip() or "[no script]"
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-avatar-speech.mp4"),
                duration_ms=5000,
                width=1280,
                height=720,
                mime_type="video/mp4",
                size_bytes=1024 * 1024,
                cost_micros=GenerateAvatarSpeechPrimitive.estimate_cost(step.params or {}),
                extra_source_spec={
                    "primitive_kind": "generate_avatar_speech",
                    "mock": True,
                    "script_chars": len(script),
                },
            )

        # ---- real-mode path -----------------------------------

        avatar_id = _resolve_avatar_id(step, composition)
        brief, chunk_ids, verification_warnings = _maybe_synthesize_script(step, composition)

        # K6.4 — persist Warn-mode verifier output onto the
        # composition. Strict mode would have raised in
        # _maybe_synthesize_script; Off mode returns an empty
        # list. Append rather than overwrite so a composition
        # with multiple knowledge-informed steps accumulates
        # warnings across all of them.
        if verification_warnings:
            existing = list(composition.verification_warnings or [])
            existing.extend(verification_warnings)
            composition.verification_warnings = existing
            composition.save(update_fields=["verification_warnings"])

        try:
            with MediaEngineClient() as client:
                created = client.create_avatar_speech(
                    spokesperson_avatar_id=avatar_id,
                    script=brief,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine create_avatar_speech failed: {exc}"
            ) from exc

        task_id = created.task_id
        logger.info(
            "generate_avatar_speech step=%s task=%s mock=%s avatar=%s chars=%d",
            step.id, task_id, created.mock_mode, avatar_id, len(brief),
        )

        # Poll until terminal. The media-engine's mock-mode returns
        # a deterministic task id that ``poll_task`` resolves
        # immediately; real-mode polls Runway through the same
        # endpoint. Either way, the loop exits on terminal status.
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
                f"avatar_speech task {task_id} did not reach terminal state "
                f"within {_POLL_DEADLINE_S}s"
            )

        if not terminal.succeeded:
            raise PrimitiveError(
                f"avatar_speech task {task_id} failed: "
                f"{terminal.error or terminal.failure_code or 'unknown'}"
            )

        if not terminal.output_url:
            raise PrimitiveError(
                f"avatar_speech task {task_id} succeeded but produced no output_url"
            )

        # Carry knowledge citations into the asset's source_spec
        # so the audit trail is intact for K6's citation contract.
        extra: dict[str, Any] = {
            "primitive_kind": "generate_avatar_speech",
            "task_id": task_id,
            "media_engine_mock_mode": terminal.mock_mode,
            "script_chars": len(brief),
        }
        if chunk_ids:
            extra["knowledge_chunk_ids"] = chunk_ids
            extra["used_knowledge"] = True
        else:
            extra["used_knowledge"] = False

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=terminal.output_url,
            duration_ms=(
                int(terminal.duration_seconds * 1000)
                if terminal.duration_seconds is not None
                else None
            ),
            mime_type="video/mp4",
            cost_micros=GenerateAvatarSpeechPrimitive.estimate_cost(step.params or {}),
            extra_source_spec=extra,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Estimate the Runway avatar_videos cost in micros from
        the script length. Conservative — better real-time
        estimation lands when V8's cost telemetry surfaces lay
        down. Used by ``estimate_composition_cost`` for the
        operator-facing pre-render cost forecast."""
        script = (params or {}).get("script", "")
        chars = len(str(script).strip())
        if chars == 0:
            return 0
        # Floor at minimum-clip cost; scale with script length.
        return max(_AVATAR_SPEECH_MIN_MICROS, chars * _AVATAR_SPEECH_MICROS_PER_CHAR)
