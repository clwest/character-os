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

from apps.compositions.models import AssetRole, AssetType
from character_os.claim_verifier import ClaimVerifierError
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.duration_contract import (
    AVATAR_SPEECH_SAFE_MAX_CHARS,
    DurationContractError,
    synthesize_with_duration_gate,
)
from character_os.script_synthesis import build_render_brief
from character_os.writing_contract import WRITING_CONTRACT_VERSION

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Polling cadence — mirrors apps/videos/tasks.poll_video_until_terminal.
# Avatar-video render takes ~30-180 s real-mode, instant in mock.
_POLL_INTERVAL_S = 2.0
_POLL_DEADLINE_S = 6 * 60  # 6-minute ceiling per hackathon precedent


# Rough cost model: Runway's avatar_videos is ~$0.05 / second of
# output. At ~150 chars/second of speech at conversational pace,
# that's ~$0.000333 / char ≈ 333 micros/char. Floor at the
# SESSION 257 — flat 2-credits-per-call cost, empirically
# verified against 15 sampled real-Runway ``/v1/avatar_videos``
# tasks spanning 1.81 s → 179.64 s durations (mined from real
# workspace Assets, queried via ``GET /v1/tasks/{id}``, all
# reported ``cost.credits == 2``, mean 2.00, stdev 0). Runway
# credit economics: 1000 credits = $10 → 1 credit = $0.01 =
# 10_000 micros. Flat-billed regardless of script length or
# render duration in the observed range.
#
# Pre-SESSION-257 constants were an inferred ``max($0.25 floor,
# 333 micros/char)`` estimator that ran 12.5× hot at the floor
# (implied 25 credits/call vs actual 2). Never grounded in
# provider telemetry; the SESSION 143 header comment flagged
# them as R&D placeholders. Now retired.
#
# Runtime path: ``execute`` prefers the media-engine's
# ``cost_credits`` from the task poll (SESSION 257 wired
# through ``InternalTaskPollResponse``) and uses this constant
# only as fallback (mock mode, or Runway occasionally omitting
# the field). The pre-render forecast in ``estimate_cost``
# always uses the constant — provider truth isn't available
# until the render completes.
_AVATAR_SPEECH_MICROS_PER_CALL = 20_000
_RUNWAY_CREDITS_TO_MICROS = 10_000


# Pre-render delivery-rate estimator for K6-generated Runway
# avatar renders. Used ONLY:
#
#   * pre-render: to translate the operator's target duration
#     into a character budget (via
#     ``script_synthesis.char_budget_for_duration`` — reads this
#     constant from ``starters._AVATAR_SPEECH_CHARS_PER_SECOND``,
#     which is the peer copy that MUST move together with this
#     one), and
#   * post-render fallback: to fabricate ``duration_ms`` when the
#     media-engine ffprobe on the returned MP4 URL fails (missing
#     binary, non-zero rc, network timeout). The successful
#     ffprobe path (``duration_source="media_probe"``, SESSION 253
#     Stage 2) is authoritative and does NOT touch this constant.
#
# SESSION 253 Stage 1 CALIBRATION — value moved 11 → 15.
# Empirically measured against five controlled real-Runway
# ``/v1/avatar_videos`` renders driven by the production
# ``synthesize_with_duration_gate`` path (K6 + Character Voice
# contract, target=90 s, Penny + variants):
#
#   1002 chars / 63.69 s = 15.732 cps
#    964 chars / 65.69 s = 14.675 cps
#   1016 chars / 64.29 s = 15.803 cps
#    880 chars / 56.97 s = 15.446 cps
#    965 chars / 62.89 s = 15.344 cps
#
#   mean 15.40  median 15.446  stddev 0.448  CV 2.9 %
#
# Rounded down to 15 (conservative + integer — the ±20 % duration
# tolerance already absorbs the 0.4 rounding error, and using
# 15 avoids false precision).
#
# The two SESSION 253 calibration constants solve DIFFERENT
# problems and must not be confused:
#
#   * ``_AVATAR_SPEECH_CHARS_PER_SECOND`` = 15 (this file):
#     how quickly the Runway avatar SPEAKS a finished script.
#     Governs the pre-render acceptance/gating budget and the
#     post-render fallback estimate. Recalibrate from fresh
#     dogfood if Runway avatar behavior materially changes
#     (new avatar family, new gwm* version, per-avatar
#     personas that vary in delivery pace).
#
#   * ``duration_contract.K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER``
#     = 0.90 (SESSION 254; was 0.78 in SESSION 253): how much GPT
#     overshoots a requested character target. Applied only to
#     what K6 is told to aim at internally; does NOT change the
#     operator-facing acceptance band. Independent from the
#     delivery rate — the 0.78 originally rode on top of a
#     cps=11 estimator and became double-biasing after Stage 3
#     recalibrated cps to 15. Recalibrate separately from cps.
#
# See docs/handoffs SESSION 253 for the calibration methodology
# and the full 30/60/90/120/180-second duration-budget table.
_AVATAR_SPEECH_CHARS_PER_SECOND = 15
_AVATAR_SPEECH_MIN_DURATION_MS = 5_000


def _estimate_duration_ms_from_script(chars: int) -> int:
    """Conservative estimate of speech duration in milliseconds
    from synthesized-brief character count. Used only as a
    fallback when the media-engine poll response lacks
    ``duration_seconds``."""
    chars = max(0, chars)
    if chars == 0:
        return _AVATAR_SPEECH_MIN_DURATION_MS
    seconds = chars / _AVATAR_SPEECH_CHARS_PER_SECOND
    return max(_AVATAR_SPEECH_MIN_DURATION_MS, int(seconds * 1000))


# SESSION 257 AI-D5 cleanup — verification_status precedence rule.
#
# Ranked strongest → weakest:
#   rejected           (4) — strict K6.4 blocked the render.
#   verified           (3) — K6/K6.4/AI Topic synthesis ran + verified.
#   skipped            (2) — LLM synthesized; verifier was explicitly off.
#   trusted_passthrough (1) — no LLM ran, no verifier ran.
#   ""                 (0) — unset.
#
# The load-bearing invariant: a step must NEVER downgrade the
# composition's verification state. Most importantly, a subsequent
# generate_avatar_speech in passthrough mode (use_knowledge=False)
# must not overwrite an AI Topic dialogue synthesis's ``verified``
# state — AI-D3 stamps ``verified`` at composition-create time,
# then each speech step's per-turn ``trusted_passthrough`` write
# would have downgraded the composition (observed on the AI-D5
# real dogfood, `5e74323f...` composition ended with
# verification_status="trusted_passthrough" despite 8 K6.4-
# verified generated turns).
#
# The rule is generic — not dialogue-specific. It preserves K6-
# derived states on any multi-step composition. Talking-head +
# manual dialogue paths are unchanged because their FIRST step's
# stamp is always weaker or equal to their subsequent steps'.
_VERIFICATION_STATUS_RANK: dict[str, int] = {
    "": 0,
    "trusted_passthrough": 1,
    "skipped": 2,
    "verified": 3,
    "rejected": 4,
}


def _should_stamp_verification_status(current: str, incoming: str) -> bool:
    """True iff ``incoming`` is strictly stronger than ``current``.

    Same-status → False (no-op, avoids pointless save cycles).
    Unset incoming → False (empty string carries no signal).

    Used by :func:`GenerateAvatarSpeechPrimitive.execute` at the
    composition-level status stamp site to prevent downgrades.
    """
    if not incoming:
        return False
    if current == incoming:
        return False
    return (
        _VERIFICATION_STATUS_RANK.get(incoming, 0)
        > _VERIFICATION_STATUS_RANK.get(current, 0)
    )


def _apply_composition_status_and_warnings(
    composition,
    *,
    incoming_status: str = "",
    incoming_warnings: list[dict] | None = None,
    incoming_brief: str = "",
    incoming_contract_version: int = 0,
) -> None:
    """SESSION 258 P1.2 + P1.3 — race-safe Composition
    verification-state update under Postgres row-level lock.

    Prior write path (four separate reads on the in-memory
    composition + one save) was subject to two races the
    parallel-execution audit flagged as blockers:

    * verification_status downgrade race — two workers both
      reading ``composition.verification_status`` from stale
      in-memory state, each independently passing the
      no-downgrade precedence check, but the second writer
      overwriting the first regardless (last-writer-wins on
      a bare ``.save()``).
    * verification_warnings append race — two workers both
      reading the current warnings list, both appending their
      own, both writing; JSONField has no atomic-append
      operation so one worker's warnings are lost.

    Fix: open ``transaction.atomic()``, acquire
    ``select_for_update()`` on the composition row, read the
    CURRENT database values under the lock (not the caller's
    stale in-memory copy), apply the precedence + append
    semantics against the locked read, save once with all
    changed fields. Concurrent callers serialize on the
    composition row's UPDATE lock; each sees the previous
    worker's committed state before deciding what to write.

    Sequential semantics unchanged — a single caller in the
    absence of contention behaves exactly like the prior
    inline block.

    Also syncs the caller's in-memory ``composition`` instance
    to the persisted state so downstream code that reads any
    of these fields sees the same values the row holds. This
    matches the prior contract where the inline block wrote
    directly to the caller's object.

    Empty inputs → no-op (avoids opening a transaction for
    nothing).
    """
    if not (
        incoming_status
        or incoming_warnings
        or incoming_brief
        or incoming_contract_version
    ):
        return

    from django.db import transaction

    from apps.compositions.models import Composition

    with transaction.atomic():
        locked = Composition.objects.select_for_update().get(pk=composition.pk)
        update_fields: list[str] = []

        if incoming_warnings:
            existing = list(locked.verification_warnings or [])
            existing.extend(incoming_warnings)
            locked.verification_warnings = existing
            update_fields.append("verification_warnings")

        # SESSION 257 AI-D5 no-downgrade rule, now applied
        # against the FRESH row-locked read (not stale in-memory).
        if _should_stamp_verification_status(
            locked.verification_status, incoming_status,
        ):
            locked.verification_status = incoming_status
            update_fields.append("verification_status")

        # K6.6: synthesized brief persistence. Only for K6
        # actually-synthesized statuses; the trusted_passthrough
        # path never has a brief worth persisting (operator
        # prompt verbatim).
        if incoming_brief and incoming_status in ("verified", "skipped"):
            locked.synthesized_brief = incoming_brief
            update_fields.append("synthesized_brief")

        # SESSION 253 — stamp the contract version if this K6
        # pass applied one. 0 (passthrough) leaves it alone.
        if incoming_contract_version and (
            locked.writing_contract_version != incoming_contract_version
        ):
            locked.writing_contract_version = incoming_contract_version
            update_fields.append("writing_contract_version")

        if update_fields:
            locked.save(update_fields=update_fields)

        # Sync caller's in-memory instance to the persisted
        # state. Downstream code that reads these fields off
        # ``composition`` sees the row's authoritative values.
        composition.verification_warnings = locked.verification_warnings
        composition.verification_status = locked.verification_status
        composition.synthesized_brief = locked.synthesized_brief
        composition.writing_contract_version = locked.writing_contract_version


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


def _maybe_synthesize_script(
    step, composition,
) -> tuple[str, list[str], list[dict], str, int]:
    """Return ``(brief, chunk_ids, verification_warnings,
    verification_status, writing_contract_version)``.

    When ``use_knowledge`` is truthy, the operator's script
    goes through K6's ``build_render_brief`` and we return the
    synthesized brief + citation ids + K6.4 verifier output +
    K6.4 v1.2 ``verification_status`` + the SESSION 253
    ``writing_contract_version`` stamp. Otherwise the script
    is used verbatim, the citation list is empty, verification
    is skipped (operator-typed scripts are trusted), the status
    is ``trusted_passthrough``, and the contract version is 0
    (no contract was applied because no K6 pass ran).
    """
    raw_script = (step.params or {}).get("script", "").strip()
    if not raw_script:
        raise PrimitiveError("generate_avatar_speech requires a non-empty script")

    use_knowledge = bool((step.params or {}).get("use_knowledge"))
    if not use_knowledge:
        return raw_script, [], [], "trusted_passthrough", 0

    # K6.4 v1.1 — per-render verifier mode. Picked up from
    # ``step.params['verifier_mode']`` if the caller (starter /
    # API view) set it; otherwise falls back to
    # ``settings.K6_CLAIM_VERIFIER_MODE``.
    verifier_mode = (step.params or {}).get("verifier_mode") or None

    # K6.6 (SESSION 168) — per-render opener override. When the
    # operator sets a non-empty opener via the recipe form, K6
    # uses it verbatim as the script's first sentence. None
    # falls back to the model-chosen opener under the system
    # prompt's standalone-video framing.
    opener = (step.params or {}).get("opener") or None

    # SESSION 253 — duration-driven synthesis. When the step
    # carries ``target_duration_seconds`` (talking_head with
    # AI-topic mode and a selected duration), route through
    # the shared duration-contract helper so a script that
    # doesn't hit the requested length fails BEFORE the
    # Runway call. Absence of the field preserves the pre-
    # SESSION-253 short-standalone behavior (no acceptance
    # gate, model picks length).
    target_duration_seconds = (step.params or {}).get(
        "target_duration_seconds",
    )
    if target_duration_seconds:
        try:
            target_duration_seconds = int(target_duration_seconds)
        except (TypeError, ValueError) as exc:
            raise PrimitiveError(
                f"generate_avatar_speech target_duration_seconds must be "
                f"an integer; got {target_duration_seconds!r}"
            ) from exc

    try:
        if target_duration_seconds:
            # Duration-driven synthesis + acceptance gate. Uses
            # AVATAR_SPEECH_SAFE_MAX_CHARS as the provider ceiling
            # because this primitive fires exactly one
            # ``/v1/avatar_videos`` call — the synthesized script
            # goes to Runway verbatim, unlike long_form_ad which
            # chunks first.
            result = synthesize_with_duration_gate(
                composition.spokesperson, raw_script,
                target_duration_seconds=target_duration_seconds,
                max_script_chars=AVATAR_SPEECH_SAFE_MAX_CHARS,
                verifier_mode=verifier_mode,
                opener=opener,
                mock_mode=False,
            )
        else:
            result = build_render_brief(
                composition.spokesperson, raw_script,
                verifier_mode=verifier_mode,
                opener=opener,
            )
    except ClaimVerifierError as exc:
        # Strict mode — surface as a primitive failure so the
        # composition fails before Runway is asked to render
        # the bad script. K6.4.1: persist the synthesized text
        # + warning dicts onto the composition so the operator
        # can review what the LLM said and what got flagged.
        # K6.4 v1.2: stamp verification_status="rejected" so
        # the audit trail is explicit (status=failed +
        # verification_status=rejected together distinguish
        # K6.4 rejections from other primitive failures).
        composition.verification_warnings = [u.to_dict() for u in exc.unsupported]
        composition.rejected_synthesis = exc.synthesized_text or ""
        composition.verification_status = "rejected"
        # SESSION 253 — stamp the contract version even on rejection;
        # the contract WAS applied (K6 ran under it and got rejected).
        composition.writing_contract_version = WRITING_CONTRACT_VERSION
        # SESSION 262 — Composition observability. Stamp the
        # per-attempt provenance for the K6.4-rejected talking-head
        # path so audits can reconstruct without terminal logs.
        # operator_topic + target_duration_seconds were already
        # persisted at composition-create time by the talking_head
        # starter (immutability guards prevent overwrite here).
        composition.first_pass_synthesis = exc.synthesized_text or ""
        composition.synthesis_attempt_count = 1
        composition.validation_failure_reason = (
            f"k6_4_strict:{len(exc.unsupported)}_unsupported_claims"
        )[:500]
        composition.save(
            update_fields=[
                "verification_warnings",
                "rejected_synthesis",
                "verification_status",
                "writing_contract_version",
                "first_pass_synthesis",
                "synthesis_attempt_count",
                "validation_failure_reason",
            ],
        )
        raise PrimitiveError(
            f"K6.4 claim verifier rejected the synthesized script "
            f"({len(exc.unsupported)} unsupported claim(s)): "
            + ", ".join(f"{u.claim!r}" for u in exc.unsupported)
        ) from exc
    except DurationContractError as exc:
        # SESSION 253 — duration-driven synthesis failed
        # acceptance after one bounded corrective pass. Persist
        # the rejected draft + reason onto the composition
        # (mirrors K6.4 rejection persistence pattern) and raise
        # PrimitiveError so the composition transitions to FAILED
        # BEFORE the media-engine / Runway call. Economic invariant:
        # zero Runway credits spent on a duration-mismatched script.
        composition.rejected_synthesis = exc.synthesized_text or ""
        composition.verification_status = "rejected"
        composition.writing_contract_version = WRITING_CONTRACT_VERSION
        composition.error_message = str(exc)
        # SESSION 262 — Composition observability. Duration-contract
        # rejection carries the full per-attempt log; persist it so
        # the FAILED talking-head row surfaces first-pass/corrective
        # provenance identical to the long-form/dialogue paths.
        composition.first_pass_synthesis = exc.first_pass_synthesis
        composition.corrective_hint = exc.corrective_hint
        composition.corrective_pass_synthesis = exc.corrective_pass_synthesis
        composition.synthesis_attempt_count = exc.attempt_count
        composition.synthesis_predicted_seconds = exc.predicted_seconds
        composition.validation_failure_reason = (
            f"duration_contract:{exc.reason}"[:500]
        )
        composition.save(
            update_fields=[
                "rejected_synthesis",
                "verification_status",
                "writing_contract_version",
                "error_message",
                "first_pass_synthesis",
                "corrective_hint",
                "corrective_pass_synthesis",
                "synthesis_attempt_count",
                "synthesis_predicted_seconds",
                "validation_failure_reason",
            ],
        )
        raise PrimitiveError(str(exc)) from exc
    # SESSION 262 — Composition observability on the accepted
    # talking-head duration-driven path. Attempt provenance flows
    # through the ScriptResult attributes attached by
    # duration_contract.synthesize_with_duration_gate.
    # `operator_topic` + `target_duration_seconds` were already
    # persisted at composition-create time by the talking_head
    # starter. Non-duration path (build_render_brief alone) also
    # writes attempt_count=1 + first_pass_brief=result.brief since
    # build_render_brief is a single-pass helper.
    _first_pass = getattr(result, "first_pass_brief", "") or result.brief
    _attempt = getattr(result, "attempt_count", 0) or 1
    _corrective_hint = getattr(result, "corrective_hint_used", "")
    _corrective_pass = getattr(result, "corrective_pass_brief", "")
    _predicted = getattr(result, "predicted_seconds", None)
    _obs_fields_dirty: list[str] = []
    if not composition.first_pass_synthesis and _first_pass:
        composition.first_pass_synthesis = _first_pass
        _obs_fields_dirty.append("first_pass_synthesis")
    if not composition.corrective_hint and _corrective_hint:
        composition.corrective_hint = _corrective_hint
        _obs_fields_dirty.append("corrective_hint")
    if not composition.corrective_pass_synthesis and _corrective_pass:
        composition.corrective_pass_synthesis = _corrective_pass
        _obs_fields_dirty.append("corrective_pass_synthesis")
    if composition.synthesis_attempt_count == 0 and _attempt:
        composition.synthesis_attempt_count = _attempt
        _obs_fields_dirty.append("synthesis_attempt_count")
    if composition.synthesis_predicted_seconds is None and _predicted is not None:
        composition.synthesis_predicted_seconds = _predicted
        _obs_fields_dirty.append("synthesis_predicted_seconds")
    if _obs_fields_dirty:
        composition.save(update_fields=_obs_fields_dirty + ["updated_at"])
    return (
        result.brief,
        list(result.chunk_ids or []),
        list(result.verification_warnings or []),
        result.verification_status or "",
        getattr(result, "writing_contract_version", 0),
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
            # SESSION 262 — the runtime dispatched a render primitive.
            # Mock mode counts (it exercises the same dispatch path;
            # the "not mock" distinction is captured elsewhere by
            # `composition.mock_mode`). Idempotent per-composition.
            composition.mark_render_dispatched()
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
                    # SESSION 257 — mock never touches the provider;
                    # persist the same cost provenance shape as the
                    # real-mode fallback so downstream analytics
                    # filters are uniform.
                    "cost_source": "estimated",
                },
                role=AssetRole.TALKING_HEAD.value,
            )

        # ---- real-mode path -----------------------------------

        avatar_id = _resolve_avatar_id(step, composition)
        (
            brief,
            chunk_ids,
            verification_warnings,
            verification_status,
            writing_contract_version,
        ) = _maybe_synthesize_script(step, composition)

        # K6.4 — persist Warn-mode verifier output onto the
        # composition. Strict mode would have raised in
        # _maybe_synthesize_script; Off mode returns an empty
        # list. Append rather than overwrite so a composition
        # with multiple knowledge-informed steps accumulates
        # warnings across all of them. K6.4 v1.2: stamp the
        # composition-level verification_status from the
        # step's outcome (last writer wins for multi-step
        # compositions; the final step's status dominates).
        # K6.6: persist the synthesized brief itself when K6
        # actually ran (verification_status of "verified" or
        # "skipped" both mean the LLM synthesized).
        # SESSION 258 P1.2 + P1.3 — race-safe composition
        # verification-state + warnings update. Under a future
        # fan-out scheduler, multiple avatar_speech steps may
        # complete concurrently; the helper acquires a row-level
        # lock on the composition row and reads current values
        # under lock before applying precedence + append. The
        # AI-D5 no-downgrade rule (SESSION 257 e3d3765) is
        # preserved and now operates against the fresh DB read
        # rather than stale in-memory state.
        _apply_composition_status_and_warnings(
            composition,
            incoming_status=verification_status,
            incoming_warnings=verification_warnings,
            incoming_brief=brief,
            incoming_contract_version=writing_contract_version,
        )

        # SESSION 262 — the runtime is about to dispatch to Runway
        # via the media-engine. Mark the composition NOW so audits can
        # distinguish "synthesis-rejected pre-dispatch" (NULL) from
        # "provider called; failed" (populated). Placed AFTER
        # `_maybe_synthesize_script` so a K6/duration/verifier
        # rejection that raised above correctly leaves the mark NULL.
        composition.mark_render_dispatched()
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

        # Duration resolution — SESSION 253 Stage 2 provenance.
        #
        # Three cases:
        #
        #   * ``duration_seconds`` populated AND ``duration_source``
        #     supplied → real measurement (media-engine ffprobed
        #     the output URL, provenance flows through).
        #   * ``duration_seconds`` populated, no source given →
        #     provider-reported (kept for forward-compat if a
        #     future endpoint returns duration from its own
        #     payload without ffprobing).
        #   * ``duration_seconds is None`` → media-engine could
        #     neither ffprobe nor read from the provider. Fall back
        #     to the shell-side script-length estimator and mark
        #     ``duration_source="estimated"`` so downstream analytics
        #     never confuse a fabricated number for a measurement.
        #
        # ``duration_estimated`` is kept as a boolean mirror for
        # backward-compat with any consumer that reads that flag.
        if terminal.duration_seconds is not None:
            duration_ms = int(terminal.duration_seconds * 1000)
            extra["duration_estimated"] = False
            extra["duration_source"] = (
                terminal.duration_source or "provider_reported"
            )
        else:
            duration_ms = _estimate_duration_ms_from_script(len(brief))
            extra["duration_estimated"] = True
            extra["duration_source"] = "estimated"
            logger.warning(
                "generate_avatar_speech step=%s task=%s: media-engine "
                "did not return a measured duration; persisting "
                "estimator fallback (%d ms from %d chars @ %d cps)",
                step.id, task_id, duration_ms, len(brief),
                _AVATAR_SPEECH_CHARS_PER_SECOND,
            )

        # SESSION 257 — cost resolution. Prefer provider truth
        # when the media-engine surfaced ``cost.credits`` from
        # Runway's ``/v1/tasks/{id}`` terminal poll. Fall back to
        # the pre-render estimator only when unavailable (mock
        # mode, or occasional Runway omission). Provenance is
        # stamped on the asset's ``source_spec`` so downstream
        # analytics can distinguish billed-truth rows from
        # estimator rows without another API round-trip.
        if terminal.cost_credits is not None:
            cost_micros = int(
                round(terminal.cost_credits * _RUNWAY_CREDITS_TO_MICROS)
            )
            extra["cost_source"] = "provider_reported"
            extra["cost_provider_credits"] = terminal.cost_credits
        else:
            cost_micros = GenerateAvatarSpeechPrimitive.estimate_cost(
                step.params or {}
            )
            extra["cost_source"] = "estimated"

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=terminal.output_url,
            duration_ms=duration_ms,
            mime_type="video/mp4",
            cost_micros=cost_micros,
            extra_source_spec=extra,
            role=AssetRole.TALKING_HEAD.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Pre-render cost forecast in micros.

        SESSION 257 — flat per-call estimate matching Runway's
        empirically-verified billing shape (2 credits = $0.02 per
        completed ``/v1/avatar_videos`` task, duration-independent
        across our observed 1.81 s → 179.64 s range).

        Empty script → 0 micros (no call will fire).

        This is the pre-render forecast that operators see before
        clicking render (via ``estimate_composition_cost``). The
        run-time actual is provider-reported when Runway surfaces
        ``cost.credits`` on the terminal poll; see ``execute``.
        """
        script = (params or {}).get("script", "")
        if not str(script).strip():
            return 0
        return _AVATAR_SPEECH_MICROS_PER_CALL
