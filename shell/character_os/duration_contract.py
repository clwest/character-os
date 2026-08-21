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
import os
from typing import TYPE_CHECKING, Sequence

from character_os.script_synthesis import (
    ScriptResult,
    build_render_brief,
    char_budget_for_duration,
    word_budget_for_duration,
)

if TYPE_CHECKING:
    from apps.memory.models import NarrativeMemory
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


# SESSION 253 amendment B / SESSION 254 recalibration — LLM
# synthesis target multiplier.
#
# gpt-5 with the SESSION 253 Writing Contract overshoots the
# OPERATOR-requested duration. The initial SESSION 253 dogfood
# measured a mean 128.1 % first-pass overshoot in a cps=11
# estimator environment and set the multiplier to
# ``1 / 1.281 ≈ 0.78`` to compensate:
#
#   T1 beginner/reassurance:    first-pass 138.9 % of target
#   T2 experiential/observational: first-pass 114.4 %
#   T3 conservation/POV:         first-pass 131.1 %
#   mean first-pass:            128.1 %
#
# SESSION 254 recalibration — post-Stage-3 (cps 11 → 15) the 0.78
# was over-correcting. Real-Runway 90 s Penny dogfood on the exact
# SESSION 253 kayak-beginner topic produced a first-pass K6 output
# of 1196 chars (114 % of the biased K6 ideal of 1050 chars),
# measured MP4 = 72.73 s = 80.8 % of the 90 s request — hugging the
# −20 % failure floor by 0.73 s. Decomposition attributed −19.8 s
# of the −17.3 s total deficit to the 0.78 bias itself, with a
# +9.5 s partial recovery from K6's 14 % overshoot vs its biased
# aim and a further −7.0 s from Runway delivering at 16.44 cps vs
# the 15 cps estimator.
#
# The 0.78 correction was calibrated in a cps=11 world where K6's
# char budget for a 70 s synth target was 770 chars (ideal). Under
# cps=15 the same synth target yields a 1050-char budget — K6 now
# has more room to write to and its residual overshoot is
# empirically smaller (+14 % here vs +28 % at the original
# calibration). Compound bias → predictable undershoot.
#
# Recalibrated to 0.90 as the smallest evidence-supported move
# toward centering first-pass output on the operator-requested
# duration without immediately reintroducing too_long rejections.
# Validation: SESSION 254 three-topic 90 s + one 120 s controlled
# real-Runway dogfood (kayak beginners / Colorado lake shoreline /
# river-lake stewardship at 90 s; paddling attention at 120 s).
# See the SESSION 254 handoff for measurements + verdict.
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
K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER: float = 0.90

# Guardrail on the calibration: for requests short enough that
# ``target * multiplier`` rounds below this floor, the
# calibration is disabled and the LLM sees the requested target
# unchanged. The 0.78 multiplier was measured at 90s. Very
# short synthesis targets (say < 30s) are outside the calibrated
# range and applying the bias could underflow the acceptance
# min. Widening the calibration would require its own dogfood.
_SYNTHESIS_CALIBRATION_MIN_SECONDS: int = 30


# SESSION 271 Q-270-15c — transient corrective-revision experiment.
#
# When this env var is set truthy, the EXPANSION corrective retry
# inside :func:`synthesize_with_duration_gate` passes the first-pass
# script text back to the LLM as ``previous_draft`` and swaps the
# canonical :func:`_expansion_hint` for the compact
# :func:`_experimental_expansion_revision_hint`, which instructs
# the model to REVISE the previous draft rather than regenerate
# from substrate.
#
# Scope guardrails (deliberate):
#
# * First pass is byte-behavior-equivalent to canonical production
#   regardless of this flag — Draft A only reaches the RETRY.
# * EXPANSION path only. The compression path stays canonical even
#   when the flag is set; a log line records the fallback.
# * Non-duration path (build_render_brief single-pass callers) is
#   NOT touched — Q-270-15c is a corrective-retry experiment.
# * Dialogue synthesis (:mod:`character_os.dialogue_synthesis`) is
#   NOT touched — Q-270-15c scopes to solo/long-form only.
# * Default OFF. Env unset or whitespace-only ⇒ canonical behaviour.
#
# Removal plan: once Q-270-15c produces a verdict, either promote
# the mechanism deliberately (its own architectural slice) or
# delete this constant + the branch + the experimental hint. Do
# NOT let this drift into permanent architecture.
_CORRECTIVE_REVISION_ENV = "CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT"


def _corrective_revision_experiment_active() -> bool:
    """Return True when the SESSION 271 Q-270-15c corrective-
    revision experiment is currently activated via env var.
    Whitespace-only values count as inactive so operators can
    unset by ``export CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT=``
    without a stale-value trap."""
    return bool(os.environ.get(_CORRECTIVE_REVISION_ENV, "").strip())


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

    SESSION 262 — additional per-attempt provenance fields
    (``first_pass_synthesis``, ``corrective_hint``,
    ``corrective_pass_synthesis``, ``attempt_count``,
    ``predicted_seconds``) are optional; callers that don't plumb
    them default to the pre-SESSION-262 shape.
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
        # SESSION 262 — per-attempt provenance for Composition
        # observability. All optional. See class docstring.
        first_pass_synthesis: str = "",
        corrective_hint: str = "",
        corrective_pass_synthesis: str = "",
        attempt_count: int = 0,
        predicted_seconds: float | None = None,
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
        # SESSION 262 — Composition observability per-attempt provenance.
        self.first_pass_synthesis = first_pass_synthesis
        self.corrective_hint = corrective_hint
        self.corrective_pass_synthesis = corrective_pass_synthesis
        self.attempt_count = attempt_count
        self.predicted_seconds = predicted_seconds
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
    Mirrors the SESSION 251 long_form_ad expansion phrasing.

    SESSION 272 Slice F (§20) — the opening anchor changed from
    ``REWRITE THE SAME NARRATIVE ABOVE`` to ``EXPAND YOUR SCRIPT``.
    The original phrase referred to a Draft-A "narrative above" that
    only exists when Q-270-15c is active (``previous_draft`` supplied
    to build_render_brief). In default operation Q-270-15c is OFF
    and no prior draft appears above §5 — the phrase pointed at
    §1 Factual Basis (KNOWLEDGE CHUNKS) instead, driving verbatim /
    near-canonical reappearance of retrieved knowledge wording in
    the corrective pass. See SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md
    §19 for the n=5 three-condition ablation evidence: the single-phrase
    swap reduced the strongest-attractor family from 4/5 to 1/5 (−75%)
    with no measurable harm to factual grounding, verification, or
    total canonical density. All other hint wording — factual-grounding
    reference, no-restart, no-second-CTA, no-invent-facts, "expand
    secondary detail from the knowledge chunks" — is preserved
    byte-for-byte."""
    shortfall_chars = effective_min - actual_chars
    return (
        f"Your previous draft was {actual_chars} characters "
        f"({actual_words} words, estimated ~{actual_seconds}s of "
        f"speech). Target is {target_duration_seconds}s.\n"
        f"EXPAND YOUR SCRIPT TO AT LEAST {effective_min} CHARACTERS "
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


def _experimental_expansion_revision_hint(
    *,
    actual_chars: int,
    actual_words: int,
    actual_seconds: int,
    target_duration_seconds: int,
    effective_ideal: int,
    effective_min: int,
    effective_max: int,
) -> str:
    """SESSION 271 Q-270-15c — expansion corrective hint used ONLY
    when the corrective-revision experiment is active. Paired with
    ``previous_draft`` (Draft A) being passed to build_render_brief
    so the LLM sees the prior attempt verbatim inside §5 as
    PREVIOUS DRAFT TO REVISE.

    Deliberately compact — the variable under test is that Draft A
    is now visible. Do NOT coach the answer with vocabulary /
    metaphor / joke preservation checklists; the point is to test
    whether the draft itself supplies the preservation signal.
    """
    shortfall_chars = effective_min - actual_chars
    return (
        f"Your previous draft was {actual_chars} characters "
        f"({actual_words} words, estimated ~{actual_seconds}s of "
        f"speech). Target is {target_duration_seconds}s.\n"
        f"REVISE THE PREVIOUS DRAFT (above, labelled PREVIOUS DRAFT "
        f"TO REVISE) to reach at least {effective_min} characters "
        f"(aim for ~{effective_ideal}, do not exceed {effective_max}). "
        f"You currently need at least {shortfall_chars} more "
        f"characters to meet the minimum.\n"
        f"Preserve the previous draft's meaning, voice, audience "
        f"fit, arc, and factual grounding. Change only what is "
        f"necessary to meet the length target. Add supporting "
        f"detail from the knowledge chunks where needed to expand; "
        f"do not replace successful wording that already works. "
        f"Factual Basis still governs truth — do not preserve any "
        f"claim in the previous draft that conflicts with the "
        f"Factual Basis. Do not add a second closing invitation. "
        f"Do not invent facts not present in the knowledge chunks."
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
    memory_rows: "Sequence[NarrativeMemory] | None" = None,
    target_shape: str = "long_form",
    audience_hint: str | None = None,
    communication_policy_hint: str | None = None,
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
        audience_hint: SESSION 270 — optional transient research
            directive forwarded verbatim to
            :func:`build_render_brief`. Emitted as a §5 Task HARD
            CONSTRAINT when non-empty; ``None`` leaves the prompt
            byte-stable versus pre-SESSION-270 behaviour. Both
            first-pass and corrective retry receive the same
            directive so the audience contract is stable across
            attempts.
        communication_policy_hint: SESSION 271 Slice 7 /
            E-KNOWLEDGE-1 — optional transient research plumbing
            carrying a character-invariant communication rule.
            Forwarded verbatim to :func:`build_render_brief` on
            BOTH first pass and corrective retry so the rule is
            always present regardless of substrate. ``None`` /
            empty leaves the prompt byte-stable. Caller
            (avatar_speech primitive) resolves the value via
            env-var + spokesperson-identity gating; this function
            merely threads the string through without inspecting it.

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

    def _synthesize(
        hint: str | None = None,
        *,
        previous_draft: str | None = None,
    ) -> ScriptResult:
        # K6 sees the SYNTH target — the LENGTH block, char
        # budget in the prompt, and word budget all derive from
        # this. Operator-facing target is preserved separately
        # for the acceptance surface and error messages below.
        #
        # SESSION 269 §15 — ``target_shape`` is caller-supplied
        # (defaults to ``"long_form"`` for legacy standalone
        # talking_head + long_form_ad callers). Episode-attached
        # talking_head renders pass ``"solo_scene"``; other shape
        # branches in WritingContract.for_shape are chosen by the
        # avatar_speech primitive.
        #
        # SESSION 271 Q-270-15c — ``previous_draft`` is defaulted
        # None so first-pass invocations remain byte-behavior-
        # equivalent to canonical production. Only the expansion
        # corrective retry, under the experiment flag, passes a
        # non-None value; every other invocation stays canonical.
        return build_render_brief(
            spokesperson, operator_prompt,
            verifier_mode=verifier_mode,
            opener=opener,
            target_shape=target_shape,
            target_duration_seconds=synth_target_seconds,
            max_script_chars=max_script_chars,
            corrective_hint=hint,
            memory_rows=memory_rows,
            audience_hint=audience_hint,
            previous_draft=previous_draft,
            communication_policy_hint=communication_policy_hint,
        )

    synth = _synthesize()
    actual_chars, actual_words, actual_seconds = _measure(synth.brief)
    # SESSION 262 — freeze first-pass output verbatim for Composition
    # observability. `synth.brief` may be reassigned by the retry
    # below; `first_pass_brief` never is.
    first_pass_brief = synth.brief
    corrective_hint_used = ""
    corrective_pass_brief = ""
    attempt_count = 1
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
        # SESSION 262 — carry per-attempt provenance so callers can
        # persist Composition observability even in mock renders.
        synth.first_pass_brief = first_pass_brief  # type: ignore[attr-defined]
        synth.corrective_hint_used = corrective_hint_used  # type: ignore[attr-defined]
        synth.corrective_pass_brief = corrective_pass_brief  # type: ignore[attr-defined]
        synth.attempt_count = attempt_count  # type: ignore[attr-defined]
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
    # SESSION 271 Q-270-15c — corrective-revision experiment gate.
    # Resolved ONCE here so both branches (expansion / compression)
    # observe the same value even if the env changes mid-render.
    _q270_15c_active = _corrective_revision_experiment_active()

    if actual_chars < raw_min:
        # SESSION 273 §25 — corrective expansion targets the RAW
        # acceptance floor, not the calibrated first-pass floor.
        # SESSION 254's 0.90 first-pass multiplier compensates for
        # gpt-5's habitual overshoot on the operator-requested target;
        # applying the same downward bias to the corrective hint
        # means telling the LLM to expand to a minimum BELOW the
        # acceptance minimum. Fresh / minimally-authored characters
        # (Ruby SESSION 273 Slice β — 4/4 90s attempts clustered at
        # 893 / 1032 / 1031 / 1008 chars; 3/4 cleared synth_min=972
        # but 0/4 cleared render_min=1080) expose the gap. Saturated
        # characters (Patch/Rivet — 15/15 90s attempts landed
        # 1163-1599 chars) hid it by systematically overshooting the
        # hint minimum. Corrective hint now uses the operator target's
        # char budget clamped to the provider cap so the LLM's stated
        # "at least" floor equals the actual acceptance floor.
        # First-pass calibration and compression retry are unchanged.
        exp_ideal, exp_min, exp_max = char_budget_for_duration(
            target_duration_seconds, max_script_chars=effective_cap,
        )
        # SESSION 271 Q-270-15c — expansion path. When the
        # experiment is active, swap the canonical expansion hint
        # for the compact revision hint AND pass Draft A back to
        # the LLM as previous_draft. Every other invocation of
        # _synthesize (first pass; compression retry) remains
        # byte-behavior-equivalent to canonical production because
        # previous_draft defaults to None.
        if _q270_15c_active:
            hint = _experimental_expansion_revision_hint(
                actual_chars=actual_chars,
                actual_words=actual_words,
                actual_seconds=actual_seconds,
                target_duration_seconds=target_duration_seconds,
                effective_ideal=exp_ideal,
                effective_min=exp_min,
                effective_max=exp_max,
            )
            logger.info(
                "synthesize_with_duration_gate SESSION 271 Q-270-15c "
                "expansion revision retry (experiment ACTIVE) sp=%s "
                "previous_draft_chars=%d — this is transient research "
                "plumbing; unset CHARACTER_OS_CORRECTIVE_REVISION_EXPERIMENT "
                "to restore canonical fresh-regeneration behaviour",
                spokesperson.pk, actual_chars,
            )
            corrective_hint_used = hint
            attempt_count = 2
            synth = _synthesize(hint, previous_draft=first_pass_brief)
        else:
            hint = _expansion_hint(
                actual_chars=actual_chars,
                actual_words=actual_words,
                actual_seconds=actual_seconds,
                target_duration_seconds=target_duration_seconds,
                effective_ideal=exp_ideal,
                effective_min=exp_min,
                effective_max=exp_max,
            )
            logger.info(
                "synthesize_with_duration_gate expansion retry sp=%s "
                "requested=%ds hint_min=%d hint_ideal=%d hint_max=%d "
                "(SESSION 273 §25 raw-target hint)",
                spokesperson.pk, target_duration_seconds,
                exp_min, exp_ideal, exp_max,
            )
            corrective_hint_used = hint
            attempt_count = 2
            synth = _synthesize(hint)
        corrective_pass_brief = synth.brief
        actual_chars, actual_words, actual_seconds = _measure(synth.brief)
    elif actual_chars > acceptance_max_chars or provider_cap_binds:
        # SESSION 271 Q-270-15c — compression path stays canonical
        # even when the experiment flag is set. Q-270-15c scopes to
        # expansion only (SESSION 271 §32.3); compression semantics
        # are a separate open question (SESSION 263 §6.5). Record
        # the intentional fallback for observability.
        if _q270_15c_active:
            logger.info(
                "synthesize_with_duration_gate SESSION 271 Q-270-15c "
                "compression retry — experiment flag is set but "
                "compression path stays canonical (expansion-only "
                "scope); running fresh-regeneration corrective pass"
            )
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
        corrective_hint_used = hint
        attempt_count = 2
        synth = _synthesize(hint)
        corrective_pass_brief = synth.brief
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
    # SESSION 262 — Composition observability: bundle per-attempt
    # provenance into every DurationContractError raise so the view /
    # primitive layer can persist ``first_pass_synthesis`` /
    # ``corrective_hint`` / ``corrective_pass_synthesis`` /
    # ``synthesis_attempt_count`` / ``synthesis_predicted_seconds`` on
    # the FAILED composition without reconstructing from logs.
    def _observability_kwargs() -> dict:
        return {
            "first_pass_synthesis": first_pass_brief,
            "corrective_hint": corrective_hint_used,
            "corrective_pass_synthesis": corrective_pass_brief,
            "attempt_count": attempt_count,
            "predicted_seconds": float(actual_seconds),
        }
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
            **_observability_kwargs(),
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
            **_observability_kwargs(),
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
            **_observability_kwargs(),
        )

    # SESSION 262 — attach per-attempt provenance to the returned
    # ScriptResult so callers (long_form_ad starter, avatar_speech
    # primitive) can persist observability fields on the accepted
    # Composition. Attribute-style attachment avoids widening
    # ScriptResult's dataclass signature and touching every existing
    # caller that constructs one.
    synth.first_pass_brief = first_pass_brief  # type: ignore[attr-defined]
    synth.corrective_hint_used = corrective_hint_used  # type: ignore[attr-defined]
    synth.corrective_pass_brief = corrective_pass_brief  # type: ignore[attr-defined]
    synth.attempt_count = attempt_count  # type: ignore[attr-defined]
    synth.predicted_seconds = float(actual_seconds)  # type: ignore[attr-defined]
    return synth


__all__ = [
    "AVATAR_SPEECH_SAFE_MAX_CHARS",
    "K6_DURATION_SYNTHESIS_TARGET_MULTIPLIER",
    "DurationContractError",
    "calibrated_synthesis_target",
    "compute_effective_budget",
    "synthesize_with_duration_gate",
    # SESSION 271 Q-270-15c — transient corrective-revision
    # experiment surface. Exported so tests can address them
    # without importing private helpers.
    "_CORRECTIVE_REVISION_ENV",
    "_corrective_revision_experiment_active",
]
