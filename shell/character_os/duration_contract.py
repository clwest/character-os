"""SESSION 253 — shared duration-driven synthesis contract.

Any recipe that wants K6 to write to a specific spoken duration
calls :func:`synthesize_with_duration_gate`. The helper delegates
to K6's ``build_render_brief`` under ``target_shape="long_form"``,
runs at most ONE bounded corrective pass, and raises
``DurationContractError`` if the corrected result is materially
outside the requested tolerance OR would exceed the provider-safe
character ceiling. Callers MUST NOT fire the Runway call after a
``DurationContractError``.

Extracted from ``apps.compositions.starters.long_form_ad``
(SESSION 251). Both ``long_form_ad`` and the SESSION 253 topic-
driven ``talking_head`` path now delegate here so there is one
duration-contract implementation.

Provider-safe ceiling
---------------------
No synthesis result passes acceptance if it exceeds the media-
engine's per-call script cap. :data:`AVATAR_SPEECH_SAFE_MAX_CHARS`
is 1900 chars = the media-engine 2000-char Pydantic cap
(``_AVATAR_SPEECH_MAX_SCRIPT_CHARS``) minus a 100-char safety
margin, matching the SESSION 253 calibration that ships ~172-
second single-call renders reliably. Anything above 1900 would
either bounce at media-engine (422) or waste the operator's
duration budget on a call that then rejects.

Acceptance gate has two conditions (both must hold):

1. ``actual_seconds`` inside ``[target * 0.8, target * 1.2]`` —
   the existing duration tolerance.
2. ``actual_chars <= effective_max_chars`` where
   ``effective_max_chars = min(duration_max_chars, max_script_chars)``.

For a 180-second target with the default 1900-char cap:

* Raw char budget from ``char_budget_for_duration`` = (1980, 1584, 2376).
* Effective budget after cap = (1850, 1584, 1900).
* Acceptance band = 1584-1900 chars ≈ 144-172 seconds. A 1900-
  char result (~172 s) is inside the ±20% seconds tolerance for
  180 s AND under the provider cap, so it accepts.

Duration incompatibility
------------------------
If the requested duration's minimum char budget itself exceeds the
provider cap (e.g. a 300-second target with the default 1900 cap:
min chars = 2640 > 1900), synthesis cannot possibly satisfy both.
Raises ``DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER``
up front, before any LLM call fires.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from character_os.script_synthesis import (
    ScriptResult,
    build_render_brief,
    char_budget_for_duration,
    word_budget_for_duration,
)

if TYPE_CHECKING:
    from apps.spokespeople.models import Teammate

logger = logging.getLogger(__name__)


# SESSION 253 — safe operating ceiling for a single Runway
# ``/v1/avatar_videos`` call. Media-engine's Pydantic cap is
# ``_AVATAR_SPEECH_MAX_SCRIPT_CHARS = 2000`` (see
# ``media-engine/app/routers/internal.py``); 1900 leaves a 100-
# char safety margin that absorbs K6 overshoot at the ±20 %
# tolerance band. Reused as the default ``max_script_chars`` in
# :func:`synthesize_with_duration_gate`.
AVATAR_SPEECH_SAFE_MAX_CHARS = 1900

# Buffer between the LLM's aim ("aim for ~X chars") and the
# hard acceptance ceiling. LLMs overshoot targets; aiming exactly
# at the ceiling pushes the acceptance gate into rejection more
# often than needed.
_IDEAL_SAFETY_BUFFER_CHARS = 50

# Same tolerance as the pre-extraction long_form_ad path. Kept
# here (not re-imported) so the shape of the contract is one
# read away for future maintainers.
_DURATION_TOLERANCE = 0.20


# SESSION 253 amendment B — LLM synthesis target multiplier.
#
# gpt-5 with the SESSION 253 Writing Contract systematically
# overshoots the OPERATOR-requested duration. Measured empirically
# in the SESSION 253 controlled 90-second dogfood against Penny
# (three ordinary operator briefs, single-topic each):
#
#   T1 beginner/reassurance:    first-pass 138.9 % of target
#   T2 experiential/observational: first-pass 114.4 %
#   T3 conservation/POV:         first-pass 131.1 %
#   mean first-pass:            128.1 %
#
# Full artifact at ``/tmp/dogfood_D_90s.json``. Multiplying the
# LLM-facing target by ``1 / 1.281 ≈ 0.78`` so the average
# expected LLM output lands at 100 % of the operator-requested
# duration.
#
# **This is a MODEL-CALIBRATION constant, not a provider constraint.**
# It only affects what K6 aims at internally. The
# operator-facing target, the acceptance band, error messages,
# and downstream audit trails all continue to reference the
# operator-requested duration.
#
# Recalibrate only from fresh dogfood evidence. If output
# systematically undershoots after this bias, do NOT
# auto-compensate: raise the multiplier from a new measurement.
K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER: float = 0.78

# Guardrail on the calibration: for requests short enough that
# ``target * multiplier`` rounds below this floor, the
# calibration is disabled and the LLM sees the requested target
# unchanged. The 0.78 multiplier was measured at 90s. Very
# short synthesis targets (say < 30s) are outside the calibrated
# range and applying the bias could underflow the acceptance
# min. Widening the calibration would require its own dogfood.
_SYNTHESIS_CALIBRATION_MIN_SECONDS: int = 30


def calibrated_synthesis_target(requested_target_seconds: int) -> int:
    """Return the LLM-facing synthesis target in seconds, biased
    downward per :data:`K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER`.

    Preserves the operator-visible target: the caller retains
    ``requested_target_seconds`` for acceptance/retry/error
    surfaces; this helper is only for what K6's prompt says.

    Guardrail: for very short requests (< 30 s) the calibration
    is skipped and the requested target is returned unchanged.
    """
    if requested_target_seconds < _SYNTHESIS_CALIBRATION_MIN_SECONDS:
        return requested_target_seconds
    return max(
        1,
        round(requested_target_seconds * K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER),
    )


class DurationContractError(Exception):
    """Raised when synthesis is materially outside the requested
    duration tolerance after one corrective pass, or would
    exceed the provider-safe character ceiling.

    Carries every field a caller needs to persist an audit row
    and surface an actionable error to the operator without
    firing the Runway call.

    Backward-compat alias: ``LongFormDurationError`` re-exports
    this class from :mod:`apps.compositions.starters` so
    existing catchers continue to work.
    """

    REASON_TOO_SHORT = "too_short"
    REASON_TOO_LONG = "too_long"
    REASON_OVER_PROVIDER_CAP = "over_provider_cap"
    REASON_INCOMPATIBLE_WITH_PROVIDER = "incompatible_with_provider_cap"

    def __init__(
        self,
        *,
        actual_chars: int,
        actual_words: int,
        actual_seconds: int,
        target_duration_seconds: int,
        min_seconds: int,
        max_seconds: int,
        effective_min_chars: int,
        effective_max_chars: int,
        synthesized_text: str,
        reason: str,
        # SESSION 253 amendment A — for correct classification of
        # duration-tolerance violations vs provider-ceiling
        # violations. ``effective_max_chars`` is ``min(duration_max,
        # provider_cap)``; when only ``duration_max`` is binding we
        # want to say "too long," not "over provider ceiling."
        duration_max_chars: int | None = None,
        provider_cap_chars: int | None = None,
    ) -> None:
        self.actual_chars = actual_chars
        self.actual_words = actual_words
        self.actual_seconds = actual_seconds
        self.target_duration_seconds = target_duration_seconds
        self.min_seconds = min_seconds
        self.max_seconds = max_seconds
        self.effective_min_chars = effective_min_chars
        self.effective_max_chars = effective_max_chars
        # Fall back to effective_max_chars when a caller doesn't
        # supply the more precise values (keeps existing tests +
        # LongFormDurationError wrapping working without touching
        # every call site).
        self.duration_max_chars = (
            duration_max_chars if duration_max_chars is not None
            else effective_max_chars
        )
        self.provider_cap_chars = provider_cap_chars
        self.synthesized_text = synthesized_text
        self.reason = reason
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        if self.reason == self.REASON_INCOMPATIBLE_WITH_PROVIDER:
            return (
                f"Duration contract failed ({self.reason}): "
                f"{self.target_duration_seconds}-second target requires "
                f"at least {self.effective_min_chars} chars, which exceeds "
                f"the provider-safe ceiling of {self.effective_max_chars}. "
                f"Reduce the target duration or split into multiple calls. "
                f"No Runway call fired."
            )
        if self.reason == self.REASON_OVER_PROVIDER_CAP:
            # True provider-ceiling violation: actual exceeds the
            # 1900-char (or caller-supplied) per-call cap. Message
            # names the provider cap explicitly and mentions the
            # media-engine boundary so the operator sees WHY.
            cap = self.provider_cap_chars or self.effective_max_chars
            return (
                f"Duration contract failed ({self.reason}): synthesized "
                f"{self.actual_chars} chars / {self.actual_words} words "
                f"(~{self.actual_seconds}s of speech), which exceeds the "
                f"{cap}-char per-call provider ceiling for a "
                f"{self.target_duration_seconds}-second target. "
                f"No Runway call fired."
            )
        if self.reason == self.REASON_TOO_LONG:
            # Duration-tolerance overshoot below the provider cap:
            # message names seconds first (operator-facing unit),
            # chars in parentheses.
            return (
                f"Duration contract failed ({self.reason}): generated "
                f"script is approximately {self.actual_seconds}s "
                f"({self.actual_chars} chars / {self.actual_words} words), "
                f"above the allowed {self.max_seconds}-second maximum for "
                f"a {self.target_duration_seconds}-second target "
                f"(accept band {self.min_seconds}-{self.max_seconds}s, "
                f"{self.effective_min_chars}-{self.duration_max_chars} chars). "
                f"No Runway call fired."
            )
        if self.reason == self.REASON_TOO_SHORT:
            return (
                f"Duration contract failed ({self.reason}): generated "
                f"script is approximately {self.actual_seconds}s "
                f"({self.actual_chars} chars / {self.actual_words} words), "
                f"below the allowed {self.min_seconds}-second minimum for "
                f"a {self.target_duration_seconds}-second target "
                f"(accept band {self.min_seconds}-{self.max_seconds}s, "
                f"{self.effective_min_chars}-{self.duration_max_chars} chars). "
                f"No Runway call fired."
            )
        # Fallback for any future reason code — generic shape.
        return (
            f"Duration contract failed ({self.reason}): synthesized "
            f"{self.actual_chars} chars / {self.actual_words} words "
            f"(~{self.actual_seconds}s of speech) for a "
            f"{self.target_duration_seconds}-second target. "
            f"No Runway call fired."
        )


# ---- helpers ------------------------------------------------------


def _measure(text: str) -> tuple[int, int, int]:
    """(chars, words, estimated_seconds) for a synthesized script.
    Delegates to the canonical estimator so this file and
    ``apps.compositions.starters`` stay on the same rate."""
    from apps.compositions.starters import _estimate_avatar_speech_seconds

    chars = len(text)
    words = len(text.split())
    seconds = _estimate_avatar_speech_seconds(chars)
    return chars, words, seconds


def compute_effective_budget(
    target_duration_seconds: int,
    max_script_chars: int,
) -> tuple[int, int, int]:
    """Return ``(effective_ideal, effective_min, effective_max)``
    where ``effective_max = min(duration_max, max_script_chars)``.

    Raises ``DurationContractError`` with
    ``REASON_INCOMPATIBLE_WITH_PROVIDER`` when the requested
    duration's min char budget itself exceeds the provider cap.
    """
    ideal, low, high = char_budget_for_duration(target_duration_seconds)
    effective_max = min(high, max_script_chars)
    if low > effective_max:
        min_s = max(1, int(round(target_duration_seconds * (1 - _DURATION_TOLERANCE))))
        max_s = max(min_s + 1, int(round(target_duration_seconds * (1 + _DURATION_TOLERANCE))))
        raise DurationContractError(
            actual_chars=0, actual_words=0, actual_seconds=0,
            target_duration_seconds=target_duration_seconds,
            min_seconds=min_s,
            max_seconds=max_s,
            effective_min_chars=low,
            effective_max_chars=effective_max,
            synthesized_text="",
            reason=DurationContractError.REASON_INCOMPATIBLE_WITH_PROVIDER,
        )
    effective_ideal = min(ideal, max(low, effective_max - _IDEAL_SAFETY_BUFFER_CHARS))
    return effective_ideal, low, effective_max


def _expansion_hint(
    *,
    actual_chars: int,
    actual_words: int,
    actual_seconds: int,
    target_duration_seconds: int,
    effective_ideal: int,
    effective_min: int,
    effective_max: int,
) -> str:
    """Concrete character-shortfall hint the LLM can act on.
    Mirrors the SESSION 251 long_form_ad expansion phrasing."""
    shortfall_chars = effective_min - actual_chars
    return (
        f"Your previous draft was {actual_chars} characters "
        f"({actual_words} words, estimated ~{actual_seconds}s of "
        f"speech). Target is {target_duration_seconds}s.\n"
        f"REWRITE THE SAME NARRATIVE ABOVE {effective_min} CHARACTERS "
        f"(aim for ~{effective_ideal}, do not exceed {effective_max}). "
        f"You currently need at least {shortfall_chars} more characters "
        f"to meet the minimum.\n"
        f"Preserve the central arc (opening → development → payoff → "
        f"single closing invitation), the narrator perspective, and "
        f"the factual grounding from the knowledge chunks. Expand "
        f"secondary detail from the knowledge chunks — describe more "
        f"of the sensory / emotional beats already implied. Do NOT "
        f"restart with a new opening. Do NOT add a second call to "
        f"action. Do NOT invent facts not present in the knowledge "
        f"chunks."
    )


def _compression_hint(
    *,
    actual_chars: int,
    actual_words: int,
    actual_seconds: int,
    target_duration_seconds: int,
    effective_ideal: int,
    effective_min: int,
    effective_max: int,
) -> str:
    """Concrete character-excess hint the LLM can act on. Mirrors
    the SESSION 251 long_form_ad compression phrasing."""
    excess_chars = actual_chars - effective_max
    return (
        f"Your previous draft was {actual_chars} characters "
        f"({actual_words} words, estimated ~{actual_seconds}s of "
        f"speech). Target is {target_duration_seconds}s.\n"
        f"REWRITE THE SAME NARRATIVE BELOW {effective_max} CHARACTERS "
        f"(aim for ~{effective_ideal}, do not fall below {effective_min}). "
        f"You currently have {excess_chars} characters more than the "
        f"maximum and must remove at least that much.\n"
        f"Preserve the central arc (opening → development → payoff → "
        f"single closing invitation), the narrator perspective, the "
        f"factual grounding, and the single closing CTA. "
        f"Preferentially remove secondary detail — decorative "
        f"adjectives, redundant beats, repeated framing — while "
        f"keeping the emotional progression intact. Do NOT drop the "
        f"closing call to action. Do NOT invent facts not present in "
        f"the knowledge chunks."
    )


# ---- public entry point ------------------------------------------


def synthesize_with_duration_gate(
    spokesperson: "Teammate",
    operator_prompt: str,
    *,
    target_duration_seconds: int,
    max_script_chars: int | None = None,
    verifier_mode: str | None = None,
    opener: str | None = None,
    mock_mode: bool = False,
) -> ScriptResult:
    """Duration-driven K6 synthesis with acceptance gate.

    Delegates to :func:`character_os.script_synthesis.build_render_brief`
    with ``target_shape="long_form"``. Runs at most ONE bounded
    corrective pass (expand OR compress) when the first synthesis
    is outside the tolerance band or over the provider ceiling.

    Args:
        spokesperson: passed through to K6.
        operator_prompt: the operator's topic / brief.
        target_duration_seconds: requested spoken duration.
        max_script_chars: hard provider-safe upper ceiling on the
            synthesized script. When ``None``, defaults to
            :data:`AVATAR_SPEECH_SAFE_MAX_CHARS` (1900). Set to
            ``None`` explicitly if the caller wants no ceiling
            (e.g. a caller that chunks the output — long_form_ad's
            legacy behavior).
        verifier_mode: K6.4 mode override.
        opener: optional pinned first sentence.
        mock_mode: skip corrective retry in mock mode
            (deterministic mock brief won't converge on a
            specific duration).

    Returns:
        ``ScriptResult`` on success.

    Raises:
        DurationContractError: still outside tolerance after one
            corrective pass, OR over the provider ceiling after
            one corrective pass, OR the duration is incompatible
            with the ceiling at all (min chars > ceiling).
            Caller MUST NOT fire the Runway call.
    """
    # ``None`` means "no provider cap — use raw duration tolerance"
    # (long_form_ad's chunked-output path). Represent that as a
    # very large integer for the min() math below without adding
    # branches everywhere. Callers who want the default single-call
    # cap pass ``AVATAR_SPEECH_SAFE_MAX_CHARS`` explicitly.
    effective_cap = max_script_chars if max_script_chars is not None else 10**9

    # SESSION 253 amendment B — two-target model.
    #
    #   requested target   → what the OPERATOR asked for.
    #                        Drives acceptance, retry decision,
    #                        rejection reasons, error messages,
    #                        and all operator-facing surfaces.
    #
    #   synthesis target   → what K6 is TOLD to write to. Biased
    #                        downward by the empirical
    #                        K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER
    #                        so K6's average overshoot lands at
    #                        the operator-requested duration.
    #                        Only appears in the K6 prompt +
    #                        corrective hints; NEVER surfaces to
    #                        the operator.
    #
    # Both derive their own char budgets from
    # ``char_budget_for_duration``.
    synth_target_seconds = calibrated_synthesis_target(target_duration_seconds)

    # LLM-facing budget derived from the synth target with the
    # provider cap threaded through. K6's prompt LENGTH block
    # and the corrective-retry hints use these numbers.
    synth_ideal, synth_min, synth_max = char_budget_for_duration(
        synth_target_seconds, max_script_chars=effective_cap,
    )

    # Acceptance / rejection bounds derive from the REQUESTED
    # target. Provider cap is threaded through here too so we
    # still raise ``REASON_INCOMPATIBLE_WITH_PROVIDER`` on
    # request/cap mismatch before any LLM call.
    compute_effective_budget(target_duration_seconds, effective_cap)
    raw_ideal, raw_min, raw_max = char_budget_for_duration(
        target_duration_seconds,
    )
    min_seconds = max(1, int(round(target_duration_seconds * (1 - _DURATION_TOLERANCE))))
    max_seconds = max(min_seconds + 1, int(round(target_duration_seconds * (1 + _DURATION_TOLERANCE))))

    def _synthesize(hint: str | None = None) -> ScriptResult:
        # K6 sees the SYNTH target — the LENGTH block, char
        # budget in the prompt, and word budget all derive from
        # this. Operator-facing target is preserved separately
        # for the acceptance surface and error messages below.
        return build_render_brief(
            spokesperson, operator_prompt,
            verifier_mode=verifier_mode,
            opener=opener,
            target_shape="long_form",
            target_duration_seconds=synth_target_seconds,
            max_script_chars=max_script_chars,
            corrective_hint=hint,
        )

    synth = _synthesize()
    actual_chars, actual_words, actual_seconds = _measure(synth.brief)
    logger.info(
        "synthesize_with_duration_gate first-pass sp=%s requested=%ds "
        "synth=%ds (accept %d-%ds, chars %d-%d) actual=%ds "
        "(%d chars / %d words) cap=%s",
        spokesperson.pk, target_duration_seconds, synth_target_seconds,
        min_seconds, max_seconds,
        raw_min, raw_max,
        actual_seconds, actual_chars, actual_words,
        max_script_chars if max_script_chars is not None else "none",
    )

    # Deterministic-mock path — skip retry (mock brief doesn't
    # converge on a specific duration) and skip acceptance
    # (test compositions render stubs, not real Runway).
    if mock_mode:
        return synth

    # ONE corrective pass. Retry decision uses the ACCEPTANCE
    # bounds (raw requested-target budget + provider cap) so we
    # only spend a second LLM call when the current result would
    # fail acceptance. Retry hints continue to reference the
    # SYNTH-target budget so K6 re-aims low (same calibration
    # bias on the retry).
    provider_cap_binds = (
        max_script_chars is not None and actual_chars > max_script_chars
    )
    acceptance_max_chars = (
        min(raw_max, max_script_chars) if max_script_chars is not None
        else raw_max
    )
    if actual_chars < raw_min:
        hint = _expansion_hint(
            actual_chars=actual_chars,
            actual_words=actual_words,
            actual_seconds=actual_seconds,
            target_duration_seconds=synth_target_seconds,
            effective_ideal=synth_ideal,
            effective_min=synth_min,
            effective_max=synth_max,
        )
        logger.info("synthesize_with_duration_gate expansion retry")
        synth = _synthesize(hint)
        actual_chars, actual_words, actual_seconds = _measure(synth.brief)
    elif actual_chars > acceptance_max_chars or provider_cap_binds:
        hint = _compression_hint(
            actual_chars=actual_chars,
            actual_words=actual_words,
            actual_seconds=actual_seconds,
            target_duration_seconds=synth_target_seconds,
            effective_ideal=synth_ideal,
            effective_min=synth_min,
            effective_max=synth_max,
        )
        logger.info("synthesize_with_duration_gate compression retry")
        synth = _synthesize(hint)
        actual_chars, actual_words, actual_seconds = _measure(synth.brief)

    # Acceptance gate — SESSION 253 amendment A. Classification:
    #
    # 1. Provider ceiling check first (highest severity, most
    #    actionable). Only fires when the caller supplied a cap
    #    AND the actual script exceeds it.
    # 2. Duration tolerance checks against the RAW REQUESTED-target
    #    budget (unclamped by provider cap) so a duration-overshoot
    #    below the provider cap is classified as TOO_LONG rather
    #    than OVER_PROVIDER_CAP.
    #
    # SESSION 253 amendment B — the ``effective_min_chars`` /
    # ``effective_max_chars`` fields on the exception surface the
    # OPERATOR-facing acceptance bounds (raw requested-target
    # budget, clamped to provider cap), NOT the synth-target
    # budget that K6 was actually told to hit. The synth budget
    # is an internal calibration detail; error messages must
    # reference the requested target.
    op_facing_max_chars = acceptance_max_chars  # clamped to cap
    op_facing_min_chars = raw_min
    if (
        max_script_chars is not None
        and actual_chars > max_script_chars
    ):
        raise DurationContractError(
            actual_chars=actual_chars,
            actual_words=actual_words,
            actual_seconds=actual_seconds,
            target_duration_seconds=target_duration_seconds,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            effective_min_chars=op_facing_min_chars,
            effective_max_chars=op_facing_max_chars,
            duration_max_chars=raw_max,
            provider_cap_chars=max_script_chars,
            synthesized_text=synth.brief,
            reason=DurationContractError.REASON_OVER_PROVIDER_CAP,
        )
    if actual_chars > raw_max:
        raise DurationContractError(
            actual_chars=actual_chars,
            actual_words=actual_words,
            actual_seconds=actual_seconds,
            target_duration_seconds=target_duration_seconds,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            effective_min_chars=op_facing_min_chars,
            effective_max_chars=op_facing_max_chars,
            duration_max_chars=raw_max,
            provider_cap_chars=max_script_chars,
            synthesized_text=synth.brief,
            reason=DurationContractError.REASON_TOO_LONG,
        )
    if actual_chars < raw_min:
        raise DurationContractError(
            actual_chars=actual_chars,
            actual_words=actual_words,
            actual_seconds=actual_seconds,
            target_duration_seconds=target_duration_seconds,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            effective_min_chars=op_facing_min_chars,
            effective_max_chars=op_facing_max_chars,
            duration_max_chars=raw_max,
            provider_cap_chars=max_script_chars,
            synthesized_text=synth.brief,
            reason=DurationContractError.REASON_TOO_SHORT,
        )

    return synth


__all__ = [
    "AVATAR_SPEECH_SAFE_MAX_CHARS",
    "K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER",
    "DurationContractError",
    "calibrated_synthesis_target",
    "compute_effective_budget",
    "synthesize_with_duration_gate",
]
