"""K6.4 dialogue-scene dispatcher regression tests.

SESSION 278 Q-278-4.2 — Slice 2 of the Q-278-4 cutover plan; updated
in Q-278-4.3 (Slice 3) after the default authority flip from
``"legacy"`` to ``"d_pos"``. Locks the dispatcher's contract:

* both classifiers ALWAYS run per call;
* authority defaults to ``"d_pos"`` (Q-278-4.3 flip); explicit
  ``"legacy"`` forces rollback to the legacy classifier;
* legacy ``ClaimVerifierError`` under strict mode re-raises when
  legacy is authoritative (explicit rollback OR defensive-fallback
  path); suppressed with WARNING when d_pos is authoritative;
* defensive fallback (``d_pos`` requested but D-POS execution
  failed) substitutes legacy and logs at ERROR;
* invalid flag values fall back to the default;
* dialogue-scene scope is enforced by call-site — script + conversation
  synthesis paths never touch this module.

Pure-function tests over ``(text, corpus, vocab, flag)``; no ORM
writes; no Composition rows constructed; test_isolation.py allow-list
untouched. Skips cleanly if spaCy or the model are absent.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

spacy = pytest.importorskip("spacy")
try:
    _NLP = spacy.load("en_core_web_sm")
except OSError:
    pytest.skip(
        "en_core_web_sm not installed; K6.4 dispatcher tests skipped.",
        allow_module_level=True,
    )

from character_os.claim_verifier import ClaimVerifierError  # noqa: E402
from character_os.claim_verifier_dispatch import (  # noqa: E402
    resolve_dialogue_authority,
    run_dialogue_verifier,
)


_CORPUS = (
    "Fox and Flour is a neighborhood artisan bakery. "
    "Fox and Flour is closed on Christmas Day."
)
_VOCAB = ["Ruby", "Tyson", "Character OS"]


# ---- resolve_dialogue_authority --------------------------------------


def test_resolve_default_authority_is_d_pos_q278_4_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Q-278-4.3 default flip: no env + no settings override → d_pos.
    Slice-3 acceptance signal — this is the load-bearing assertion
    that the dialogue-scene default is now the D-POS Hybrid
    classifier rather than the legacy K6.4 verifier."""
    monkeypatch.delenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", raising=False)
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = None
        assert resolve_dialogue_authority() == "d_pos"


def test_resolve_explicit_legacy_env_rollback_q278_4_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Q-278-4.3 rollback path: explicit ``legacy`` env override
    forces legacy authority even after the default flip. This is
    the primary operator rollback mechanism.
    Preserves the Q-278-4 §6 invariant that rollback is a single
    env-var flip, no code revert required."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "legacy")
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = None
        assert resolve_dialogue_authority() == "legacy"


def test_resolve_explicit_legacy_settings_rollback_q278_4_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Django settings override also forces legacy — same rollback
    mechanism via a different precedence path (settings > env >
    default). Locks that either configuration route can restore
    legacy authority."""
    monkeypatch.delenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", raising=False)
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = "legacy"
        assert resolve_dialogue_authority() == "legacy"


def test_resolve_explicit_env_d_pos_still_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit ``d_pos`` env still resolves to d_pos even after the
    default flip. The resolver treats explicit values identically
    regardless of whether they match the default."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "d_pos")
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = None
        assert resolve_dialogue_authority() == "d_pos"


def test_resolve_settings_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Precedence: settings > env. Now demonstrated in the rollback
    direction: env=d_pos + settings=legacy → legacy (rollback via
    settings wins over an env-var claim of d_pos)."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "d_pos")
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = "legacy"
        assert resolve_dialogue_authority() == "legacy"


def test_resolve_whitespace_only_env_reads_as_unset_q278_4_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whitespace-only env-var reads as unset → default (now d_pos
    post Q-278-4.3)."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "   ")
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = None
        assert resolve_dialogue_authority() == "d_pos"


@pytest.mark.parametrize("invalid", ["yes", "on", "true", "d-pos", "random"])
def test_resolve_invalid_env_falls_back_to_default_q278_4_3(
    invalid: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any unrecognized value falls back to default (d_pos after
    Q-278-4.3) + WARNING. Prevents an operator typo or misconfiguration
    from silently rolling back to legacy — the safer default post-flip
    is the current authoritative classifier, and the WARNING makes the
    invalid value visible in logs."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", invalid)
    with patch("character_os.claim_verifier_dispatch.settings") as fake_settings:
        fake_settings.CHARACTER_OS_K64_DIALOGUE_AUTHORITY = None
        assert resolve_dialogue_authority() == "d_pos"


# ---- run_dialogue_verifier basics ------------------------------------


def _clear_authority_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset to the Slice-3 default (``d_pos``) so a test starts from
    a known state. Post Q-278-4.3 the resolver returns ``d_pos`` when
    both env and settings are unset."""
    monkeypatch.delenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", raising=False)


def _force_legacy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicitly force legacy authority via env override. Used by
    tests that need to exercise the pre-flip / rollback code path."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "legacy")


def test_dispatcher_runs_both_classifiers_default_d_pos_authority_q278_4_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post Q-278-4.3: under the DEFAULT authority (d_pos) the
    dispatcher runs both classifiers, produces D-POS output as
    authoritative, and silences the Q-278-1 class on the operator-
    facing column while still capturing the legacy warning on
    ``result.legacy`` for shadow observability."""
    _clear_authority_env(monkeypatch)
    result = run_dialogue_verifier(
        "Fair enough.",
        factual_corpus=_CORPUS,
        allowed_vocabulary=_VOCAB,
    )
    assert result.authority_requested == "d_pos"
    assert result.authority_used == "d_pos"
    assert result.d_pos_ok is True
    # Under d_pos authority, authoritative mirrors D-POS.
    assert result.authoritative == result.d_pos
    # Legacy shadow still captures the Q-278-1 flag for post-flip evidence.
    legacy_claims = {w.claim for w in result.legacy}
    d_pos_claims = {w.claim for w in result.d_pos}
    assert "Fair" in legacy_claims
    assert "Fair" not in d_pos_claims
    # And the Q-278-1 false positive is gone from the operator-facing
    # column since d_pos is authoritative.
    auth_claims = {w.claim for w in result.authoritative}
    assert "Fair" not in auth_claims


def test_dispatcher_explicit_legacy_rollback_authority_q278_4_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit ``legacy`` env override forces the rollback path
    post Q-278-4.3. Under legacy authority the dispatcher's
    ``authoritative`` mirrors ``legacy``, restoring the pre-flip
    behavior for the affected synthesis call."""
    _force_legacy_env(monkeypatch)
    result = run_dialogue_verifier(
        "Fair enough.",
        factual_corpus=_CORPUS,
        allowed_vocabulary=_VOCAB,
    )
    assert result.authority_requested == "legacy"
    assert result.authority_used == "legacy"
    # Under explicit legacy rollback, authoritative == legacy.
    assert result.authoritative == result.legacy
    # Legacy still flags Fair; D-POS shadow still silences it.
    auth_claims = {w.claim for w in result.authoritative}
    assert "Fair" in auth_claims


def test_dispatcher_preserves_real_unsupported_entity_under_both_authorities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The founding hallucination invariant survives both authorities:
    an unsupported named entity flags whether legacy or D-POS is
    authoritative."""
    text = "Antoninus reigned peacefully."
    for authority in ("legacy", "d_pos"):
        monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", authority)
        result = run_dialogue_verifier(
            text, factual_corpus=_CORPUS, allowed_vocabulary=_VOCAB,
        )
        auth_claims = {w.claim for w in result.authoritative}
        assert "Antoninus" in auth_claims, (
            f"authority={authority}: Antoninus should flag; got {auth_claims}"
        )


# ---- Strict-mode preservation ----------------------------------------


def test_dispatcher_reraises_legacy_strict_error_under_legacy_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict-mode legacy raise MUST re-fire when legacy is the
    authoritative classifier so the existing
    ``dialogue_synthesis.py`` per-turn strict handler runs. Post
    Q-278-4.3 legacy authority requires an explicit env override —
    the default is now d_pos, under which the raise is suppressed
    (see the companion test below)."""
    _force_legacy_env(monkeypatch)
    with pytest.raises(ClaimVerifierError):
        run_dialogue_verifier(
            "Antoninus reigned peacefully.",
            factual_corpus="",  # empty → nothing supports the entity
            allowed_vocabulary=[],
            mode="strict",
        )


def test_dispatcher_suppresses_legacy_strict_error_under_d_pos_authority(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    """When authority=d_pos and legacy would raise under strict, the
    dispatcher does NOT re-raise (legacy is not authoritative). Legacy
    candidates are still captured for shadow observability; a WARNING
    is emitted so audits can see the suppression."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "d_pos")
    result = run_dialogue_verifier(
        "Antoninus reigned peacefully.",
        factual_corpus="",
        allowed_vocabulary=[],
        mode="strict",
    )
    # authoritative reflects D-POS output (Antoninus still flags —
    # PROPN pass catches it).
    assert any(w.claim == "Antoninus" for w in result.authoritative)
    # legacy candidates preserved for shadow observability.
    assert any(w.claim == "Antoninus" for w in result.legacy)
    # WARNING emitted about the suppression.
    assert any(
        "authority=d_pos" in rec.message and "suppressing raise" in rec.message
        for rec in caplog.records
    )


# ---- Defensive fallback (Q-278-4 §6) ---------------------------------


def test_dispatcher_falls_back_to_legacy_when_d_pos_fails(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    """If authority=d_pos but D-POS execution raises, dispatcher
    substitutes legacy AND logs at ERROR. This is the load-bearing
    guarantee against spaCy install regression silently producing
    ``verification_warnings = []`` false confidence."""
    monkeypatch.setenv("CHARACTER_OS_K64_DIALOGUE_AUTHORITY", "d_pos")

    # Force run_shadow_verifier to raise.
    def _raise(*_a, **_kw):
        raise RuntimeError("simulated spaCy failure")

    with patch(
        "character_os.claim_verifier_dispatch.run_shadow_verifier",
        side_effect=_raise,
    ):
        result = run_dialogue_verifier(
            "Fair enough.",
            factual_corpus=_CORPUS,
            allowed_vocabulary=_VOCAB,
        )

    # Requested d_pos, but fell back to legacy.
    assert result.authority_requested == "d_pos"
    assert result.authority_used == "legacy"
    assert result.d_pos_ok is False
    # authoritative == legacy on the fallback.
    assert result.authoritative == result.legacy
    # ERROR was logged so the operator can see the degradation.
    assert any(
        "falling back to legacy" in rec.message and rec.levelname == "ERROR"
        for rec in caplog.records
    )


# ---- Q-278-3.1 / Q-278-4.1 continuity — Fair/Come/Unless on 26c62b4b shape ---


@pytest.mark.parametrize("text", [
    "Fair enough.",
    "Come inside.",
    "Unless you disagree.",
    "Please sit down.",
    "Always check first.",
])
def test_dispatcher_records_q278_1_class_delta_under_legacy_rollback(
    text: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under explicit legacy rollback authority, for every Q-278-1
    sentence-initial ordinary-language token: legacy non-empty
    (flagged), d_pos empty (silenced), authoritative mirrors legacy.
    This is the LEGACY_ONLY diff shape the shadow-window relied on;
    it must still be reproducible on-demand after Q-278-4.3 for
    rollback-shape verification + `k64_shadow_diff` semantics."""
    _force_legacy_env(monkeypatch)
    result = run_dialogue_verifier(
        text, factual_corpus=_CORPUS, allowed_vocabulary=_VOCAB,
    )
    assert result.legacy, f"expected legacy warnings on {text!r}"
    assert result.d_pos == [], f"expected no d_pos warnings on {text!r}"
    # Under explicit legacy rollback, authoritative should equal legacy.
    assert result.authoritative == result.legacy


@pytest.mark.parametrize("text", [
    "Fair enough.",
    "Come inside.",
    "Unless you disagree.",
    "Please sit down.",
    "Always check first.",
])
def test_dispatcher_q278_1_class_silent_under_default_d_pos_authority_q278_4_3(
    text: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post Q-278-4.3: under the DEFAULT d_pos authority, the Q-278-1
    sentence-initial class is silent on ``result.authoritative`` while
    ``result.legacy`` still captures the (now non-authoritative) legacy
    warning for post-flip shadow-diff evidence. Load-bearing acceptance
    signal for the Slice-3 default flip."""
    _clear_authority_env(monkeypatch)
    result = run_dialogue_verifier(
        text, factual_corpus=_CORPUS, allowed_vocabulary=_VOCAB,
    )
    # authoritative = D-POS output — Q-278-1 class silenced.
    assert result.authoritative == result.d_pos
    assert result.authoritative == []
    # legacy shadow still captures the false positive for post-flip
    # diff evidence (Slice-3 evidence trail preservation).
    assert result.legacy, f"expected legacy shadow warnings on {text!r}"


# ---- Dialogue-scene scope-lock guard --------------------------------


def test_script_synthesis_does_not_import_dispatcher() -> None:
    """Q-278-4.2 Option A scope-lock: script_synthesis.py MUST NOT
    call the dialogue dispatcher. Verified by source-text inspection
    rather than by execution — a runtime import via the wrong path
    would violate the boundary invariant."""
    from pathlib import Path
    script_syn_source = Path(
        "character_os/script_synthesis.py"
    ).read_text()
    assert "claim_verifier_dispatch" not in script_syn_source, (
        "script_synthesis.py must NOT import the dialogue dispatcher; "
        "adjacent-surface migration is out of scope for Q-278-4.2"
    )


def test_conversation_synthesis_does_not_import_dispatcher() -> None:
    """Q-278-4.2 Option A scope-lock: conversation_synthesis.py MUST
    NOT call the dialogue dispatcher either. Same invariant, same
    check shape."""
    from pathlib import Path
    conv_syn_source = Path(
        "character_os/conversation_synthesis.py"
    ).read_text()
    assert "claim_verifier_dispatch" not in conv_syn_source, (
        "conversation_synthesis.py must NOT import the dialogue "
        "dispatcher; adjacent-surface migration is out of scope for "
        "Q-278-4.2"
    )


# ---- Dual-write invariant (starters.py flattener parity) -------------


def test_flattener_dual_write_invariant_under_legacy_authority() -> None:
    """Load-bearing invariant that pinned the Q-278-4.2 Slice-3
    acceptance gate:
    under LEGACY authority (default pre-Q-278-4.3; still reachable
    post-flip via explicit rollback), the persisted
    ``verification_warnings`` and ``verification_warnings_legacy``
    columns MUST equal each other on every dialogue-scene row.

    Proven at the flattener level: since
    ``turn.verification_warnings`` and
    ``turn.verification_warnings_legacy`` are both mirrors of the
    dispatcher's legacy output under legacy authority, and the two
    flatteners
    (:func:`apps.compositions.starters._dialogue_ai_flattened_warnings` and
    :func:`apps.compositions.starters._dialogue_ai_flattened_legacy_warnings`)
    apply identical speaker/line enrichment, the persisted columns
    must be structurally equal.

    This assertion drove Slice-3 acceptance on the 3/3 dual-write
    dogfood window; post-flip it remains a load-bearing rollback
    invariant.
    """
    from apps.compositions.starters import (
        _dialogue_ai_flattened_warnings,
        _dialogue_ai_flattened_legacy_warnings,
    )
    from types import SimpleNamespace

    # Simulate the exact shape ``dialogue_synthesis.py`` produces
    # under legacy authority: ``verification_warnings`` and
    # ``verification_warnings_legacy`` are identical per-turn lists.
    warn = {"kind": "proper_noun", "claim": "Fair", "position": 0}
    turn = SimpleNamespace(
        line_index=5,
        speaker_alias="tyson",
        speaker_teammate=SimpleNamespace(name="Tyson"),
        verification_warnings=[warn],
        verification_warnings_legacy=[warn],
        verification_warnings_shadow=[],
    )
    result = SimpleNamespace(turns=[turn])

    auth_flat = _dialogue_ai_flattened_warnings(result)
    legacy_flat = _dialogue_ai_flattened_legacy_warnings(result)

    assert auth_flat == legacy_flat
    # Enrichment applied on both.
    assert auth_flat[0]["speaker_name"] == "Tyson"
    assert legacy_flat[0]["speaker_name"] == "Tyson"


def test_flattener_dual_write_invariant_under_d_pos_authority() -> None:
    """Post-Q-278-4.3 invariant (default authority state):
    under ``d_pos`` authority the ``verification_warnings`` column
    equals the ``verification_warnings_shadow`` column (both mirror
    D-POS output), while ``verification_warnings_legacy`` may carry a
    DIFFERENT list — the post-flip legacy shadow.

    This test locks the SHAPE of the current default post Q-278-4.3.
    """
    from apps.compositions.starters import (
        _dialogue_ai_flattened_warnings,
        _dialogue_ai_flattened_shadow_warnings,
        _dialogue_ai_flattened_legacy_warnings,
    )
    from types import SimpleNamespace

    legacy_warn = {"kind": "proper_noun", "claim": "Fair", "position": 0}
    turn = SimpleNamespace(
        line_index=3,
        speaker_alias="rivet",
        speaker_teammate=SimpleNamespace(name="Rivet"),
        # Under d_pos authority, ``verification_warnings`` mirrors
        # D-POS (empty here after Q-278-4.1 gate); shadow mirrors
        # the same; legacy carries the pre-cutover legacy shadow.
        verification_warnings=[],
        verification_warnings_shadow=[],
        verification_warnings_legacy=[legacy_warn],
    )
    result = SimpleNamespace(turns=[turn])

    auth_flat = _dialogue_ai_flattened_warnings(result)
    shadow_flat = _dialogue_ai_flattened_shadow_warnings(result)
    legacy_flat = _dialogue_ai_flattened_legacy_warnings(result)

    assert auth_flat == shadow_flat  # both empty (d_pos silenced Fair)
    assert auth_flat != legacy_flat  # legacy DIFFERS (still flags Fair)
    assert legacy_flat[0]["claim"] == "Fair"
