"""Dialogue-scene K6.4 verifier dispatcher.

SESSION 278 Q-278-4.2 — Slice 2 of the Q-278-4 cutover plan. Adopts
**Option A (dialogue-scene-only)** per the Q-278-4.2 pre-implementation
boundary challenge: `character_os/dialogue_synthesis.py` is the ONLY
call site rewired through this dispatcher. `script_synthesis.py` and
`conversation_synthesis.py` continue to call the legacy verifier
directly and remain unaffected.

The dispatcher exists so a future `CHARACTER_OS_K64_DIALOGUE_AUTHORITY=d_pos`
flip can move dialogue authority from legacy K6.4 to the D-POS Hybrid
NER classifier **without silently broadening blast radius** to Script,
ConversationMessage, or talking-head / long-form Composition surfaces
that have no shadow-evaluation evidence today.

Behavior contract:

* **Both classifiers ALWAYS run per dialogue turn.** The retired
  ``CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT`` flag is a no-op for the
  dialogue path after Slice 2.
* **Authority is resolved fresh per synthesis call.** No process-wide
  cache — the dispatcher reads the flag every call so mid-run env
  changes take effect on the next synthesis.
* **Defensive fallback (spaCy failure).** If authority=`d_pos` but the
  D-POS classifier cannot execute (spacy missing / model missing /
  exception), the dispatcher falls back to legacy for that call AND
  logs at ERROR. Prevents an install regression from silently
  converting "no unsupported claim ever flagged" into false confidence.
* **Legacy strict-mode semantics preserved exactly.** When the legacy
  verifier raises ``ClaimVerifierError``, the dispatcher re-raises so
  the existing per-turn strict-mode failure path (``turn.verification_status
  = "rejected"``; overall status rejected; composition FAILED) fires
  unchanged.
* **D-POS strict-mode behavior deliberately left as-is** — the shadow
  classifier never raises today. If a future slice moves dialogue
  authority to `d_pos` AND the operator also wants strict mode
  enforced on D-POS output, that combination is a separate scope-locked
  slice with its own audit. Slice 2 keeps warn/strict semantics
  identical to today by returning D-POS candidates as a warn-style list
  even when ``mode == "strict"``. See §"Strict mode + d_pos" below.

Non-scope in Slice 2:

* No adjacent-surface migration. Script + ConversationMessage keep
  calling ``claim_verifier.run_verifier`` directly.
* No default authority flip. `resolve_dialogue_authority()` defaults
  to ``"legacy"``; Slice 3 (Q-278-4.3, unopened) is the sole slice
  authorized to change that default.
* No stoplist cleanup, no strict-mode change, no SPA change.

Cross-references:

* `docs/design/SESSION_278_AUDIT.md` §Q-278-4 (three-slice plan) and
  §Q-278-4.2 pre-implementation boundary challenge (Option A rationale).
* `character_os/claim_verifier.py` (legacy) and
  `character_os/claim_verifier_ner.py` (D-POS Hybrid, Q-278-4.1-gated).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Iterable

from django.conf import settings

from character_os.claim_verifier import (
    ClaimVerifierError,
    UnsupportedClaim,
    run_verifier,
)
from character_os.claim_verifier_ner import run_shadow_verifier

logger = logging.getLogger(__name__)


_DIALOGUE_AUTHORITY_ENV = "CHARACTER_OS_K64_DIALOGUE_AUTHORITY"
_DIALOGUE_AUTHORITY_SETTING = "CHARACTER_OS_K64_DIALOGUE_AUTHORITY"

# Accepted authority values. Case-insensitive on input; whitespace-
# only reads as unset → default.
_VALID_AUTHORITIES: frozenset[str] = frozenset({"legacy", "d_pos"})
_DEFAULT_AUTHORITY: str = "legacy"


def resolve_dialogue_authority() -> str:
    """Resolve the dialogue-scene K6.4 authority.

    Precedence:

    1. ``settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY`` — Django-settings
       override.
    2. ``os.environ["CHARACTER_OS_K64_DIALOGUE_AUTHORITY"]`` — env-var
       override, so operators can toggle without editing settings.
    3. ``"legacy"`` — default.

    Whitespace-only values in either source are treated as unset. Any
    unrecognized value (i.e. neither ``"legacy"`` nor ``"d_pos"``)
    also falls back to the default and logs a WARNING so a
    misconfiguration surfaces loudly.
    """
    setting_value = getattr(settings, _DIALOGUE_AUTHORITY_SETTING, None)
    if isinstance(setting_value, str) and setting_value.strip():
        candidate = setting_value.strip().lower()
        if candidate in _VALID_AUTHORITIES:
            return candidate
        logger.warning(
            "K6.4 dispatcher: settings.%s=%r not in %s; using default %r",
            _DIALOGUE_AUTHORITY_SETTING, setting_value,
            sorted(_VALID_AUTHORITIES), _DEFAULT_AUTHORITY,
        )
        return _DEFAULT_AUTHORITY
    env_value = os.environ.get(_DIALOGUE_AUTHORITY_ENV, "").strip().lower()
    if env_value:
        if env_value in _VALID_AUTHORITIES:
            return env_value
        logger.warning(
            "K6.4 dispatcher: %s=%r not in %s; using default %r",
            _DIALOGUE_AUTHORITY_ENV, env_value,
            sorted(_VALID_AUTHORITIES), _DEFAULT_AUTHORITY,
        )
        return _DEFAULT_AUTHORITY
    return _DEFAULT_AUTHORITY


@dataclass(slots=True, frozen=True)
class DialogueVerifierResult:
    """Return payload from :func:`run_dialogue_verifier`.

    Consumers use this to populate the three persistence fields
    (``verification_warnings`` / ``verification_warnings_shadow`` /
    ``verification_warnings_legacy``) and to derive
    ``verification_status``.

    Fields:

    * ``authoritative`` — the list the caller should treat as
      authoritative. Either equals ``legacy`` or ``d_pos`` per
      :attr:`authority_used` below.
    * ``legacy`` — legacy classifier output, always populated (empty
      list on strict-mode raise is captured before the raise
      re-fires; see :func:`run_dialogue_verifier` for details).
    * ``d_pos`` — D-POS classifier output. Empty list when the D-POS
      classifier could not execute (spacy missing / model missing /
      exception); :attr:`d_pos_ok` records that distinction.
    * ``d_pos_ok`` — ``True`` if D-POS ran cleanly, ``False`` on any
      failure path. Load-bearing for the defensive-fallback branch.
    * ``authority_requested`` — ``"legacy"`` or ``"d_pos"`` per
      :func:`resolve_dialogue_authority` at call time.
    * ``authority_used`` — ``"legacy"`` or ``"d_pos"``. Equals
      ``authority_requested`` unless the requested authority was
      ``"d_pos"`` and ``d_pos_ok`` is ``False`` — then the dispatcher
      falls back to ``"legacy"`` and logs at ERROR.
    """
    authoritative: list[UnsupportedClaim]
    legacy: list[UnsupportedClaim]
    d_pos: list[UnsupportedClaim]
    d_pos_ok: bool
    authority_requested: str
    authority_used: str


def run_dialogue_verifier(
    text: str,
    *,
    factual_corpus: str,
    allowed_vocabulary: Iterable[str] = (),
    mode: str | None = None,
) -> DialogueVerifierResult:
    """Dialogue-scene-only dispatcher. Runs BOTH classifiers per call.

    Args:
        text: Synthesized turn text to verify.
        factual_corpus: Concatenated evidence for grounding (same
            shape :func:`claim_verifier.build_factual_corpus`
            produces).
        allowed_vocabulary: Whitelist entries (same shape
            :func:`claim_verifier.build_allowed_vocabulary` produces).
        mode: ``"warn" | "strict" | "off"``. Passed VERBATIM to the
            legacy verifier so its existing mode resolution
            (settings > env > default) applies. The D-POS side does
            not consume mode today (see class docstring
            §"Strict mode + d_pos").

    Returns:
        :class:`DialogueVerifierResult` with both classifier outputs +
        the dispatcher's authoritative choice + the requested-vs-used
        authority tag.

    Raises:
        :class:`character_os.claim_verifier.ClaimVerifierError`: when
            the legacy verifier raises under strict mode. The
            dispatcher preserves this legacy behavior verbatim so the
            existing per-turn strict-mode failure path in
            ``dialogue_synthesis.py`` fires unchanged.

    Strict mode + d_pos:

    Today ``run_shadow_verifier`` never raises. If ``mode == "strict"``
    and ``authority_requested == "d_pos"`` the dispatcher's D-POS
    branch will return a warn-style candidate list rather than raise.
    That combination is not yet an operator-facing configuration and
    is intentionally deferred to a future scope-locked slice. See
    module docstring.

    Defensive fallback:

    If the requested authority is ``"d_pos"`` but D-POS execution
    failed (``d_pos_ok = False``), the dispatcher logs at ERROR and
    substitutes legacy output for the authoritative choice. This
    guarantees an install regression cannot silently convert "no
    unsupported claim ever flagged" into false operator confidence.
    """
    authority_requested = resolve_dialogue_authority()

    # ---- Legacy classifier (may raise under strict) ----
    #
    # Capture legacy candidates BEFORE any potential raise so the
    # per-turn observability field can be populated even when the
    # raise bubbles up. Strict-mode raise carries the same
    # ``ClaimVerifierError`` shape callers already handle today.
    legacy_candidates: list[UnsupportedClaim] = []
    legacy_error: ClaimVerifierError | None = None
    try:
        legacy_candidates = run_verifier(
            text,
            factual_corpus=factual_corpus,
            allowed_vocabulary=allowed_vocabulary,
            mode=mode,
        )
    except ClaimVerifierError as exc:
        legacy_error = exc
        # Extract the unsupported list off the exception so shadow
        # observability still has something to persist even if we
        # re-raise below.
        legacy_candidates = list(exc.unsupported or [])

    # ---- D-POS classifier (never raises today) ----
    d_pos_ok = True
    d_pos_candidates: list[UnsupportedClaim] = []
    try:
        d_pos_candidates = run_shadow_verifier(
            text,
            factual_corpus=factual_corpus,
            allowed_vocabulary=allowed_vocabulary,
        )
    except Exception:  # noqa: BLE001 — dispatcher must never crash caller
        logger.exception(
            "K6.4 dispatcher: D-POS shadow verifier raised; "
            "recording d_pos_ok=False and continuing.",
        )
        d_pos_ok = False
        d_pos_candidates = []

    # ---- Authority resolution + defensive fallback ----
    authority_used = authority_requested
    if authority_requested == "d_pos" and not d_pos_ok:
        logger.error(
            "K6.4 dispatcher: authority=d_pos requested but D-POS "
            "classifier failed; falling back to legacy for this call. "
            "Investigate spacy/en_core_web_sm install.",
        )
        authority_used = "legacy"

    # If legacy raised under strict, we must re-raise BEFORE returning
    # so the existing per-turn dialogue_synthesis handler fires. The
    # legacy_candidates + d_pos_candidates observability payload
    # never reaches this branch's caller — the caller's exception
    # handler is responsible for persisting the failure row.
    if legacy_error is not None and authority_used == "legacy":
        # Preserve the exact strict-mode exception the legacy verifier
        # produced. The exception already carries the unsupported list
        # via ``exc.unsupported``.
        raise legacy_error

    # If authority is d_pos and legacy raised under strict, we do NOT
    # re-raise — legacy is not authoritative in that case. Log at
    # WARNING so audit trails can see legacy would have failed.
    if legacy_error is not None and authority_used == "d_pos":
        logger.warning(
            "K6.4 dispatcher: legacy verifier raised ClaimVerifierError "
            "under strict mode but authority=d_pos; suppressing raise. "
            "Legacy candidates captured for shadow observability.",
        )

    if authority_used == "d_pos":
        authoritative = d_pos_candidates
    else:
        authoritative = legacy_candidates

    return DialogueVerifierResult(
        authoritative=authoritative,
        legacy=legacy_candidates,
        d_pos=d_pos_candidates,
        d_pos_ok=d_pos_ok,
        authority_requested=authority_requested,
        authority_used=authority_used,
    )


__all__ = [
    "DialogueVerifierResult",
    "resolve_dialogue_authority",
    "run_dialogue_verifier",
]
