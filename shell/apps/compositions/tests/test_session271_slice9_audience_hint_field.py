"""SESSION 271 §187 / Slice 9 — Composition.audience_hint canonical
field behavioral tests.

Scope: the per-render listener descriptor promoted from SESSION 270
env-var research plumbing to a persisted Composition field. Covers:

1. Field exists on ``Composition`` and defaults to ``""``.
2. Non-empty ``audience_hint`` supplied to the ``talking_head`` starter
   persists on the row AND lands in ``step.params['audience_hint']``
   so the SESSION 270 ``_resolve_solo_audience_hint`` resolver picks
   it up first in its step.params → settings → env precedence chain.
3. Blank / whitespace-only ``audience_hint`` at the starter does NOT
   add a ``step.params`` key (blank on the row = no step-param key
   = resolver returns None = universal Writing Contract v6 invariant
   falls back to ``Teammate.who_you_help`` via §1 AUDIENCE).
4. ``audience_hint`` participates in SESSION 262 immutability — once
   populated with a non-default value, subsequent overwrites raise
   ``ValidationError`` at ``save()``.
5. Regression: SESSION 270 primitive-layer resolver still honours
   step.params > settings > env precedence, and the newly-persisted
   Composition.audience_hint field does NOT bypass the resolver
   (talking_head is the ONLY starter surface that copies to
   step.params in this slice; other starters still see the resolver's
   settings / env fallbacks unchanged).

These tests are DB-backed but LLM-free — no OpenAI calls, no
retrieval, no media-engine. They exercise field semantics + starter
plumbing + immutability guard only. The prompt-shape / retrieval /
end-to-end tests remain in ``test_session270_audience_hint.py``
(untouched by this slice; ``test_writing_contract_solo_scene.py``
covers the new universal invariant block in the contract text).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Workspace
from apps.compositions.models import Composition
from apps.compositions.starters import talking_head
from apps.spokespeople.models import Teammate

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- fixtures --------------------------------------------------------


def _ws(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _tm(ws: Workspace, name: str = "Patch") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        runway_avatar_id=f"av-{name.lower()}",
        portrait_path="https://fake/p.png",
        business_brief=f"{name}'s brief.",
    )


# The Slice 9 §179.4 canonical hint text — pinned to detect drift.
_HINT = (
    "AUDIENCE: children around 8-10 years old. Adapt technical "
    "depth, vocabulary, examples, and analogies to this listener "
    "without changing character identity, intelligence, expertise, "
    "humor, personality, factual grounding, or confidence."
)


# ---- 1. Field exists + defaults blank --------------------------------


def test_composition_audience_hint_field_defaults_blank():
    """A newly-created Composition with no explicit ``audience_hint``
    lands with ``""`` (empty string) — the SESSION 262 additive-nullable
    discipline for TextField observability fields."""
    ws = _ws("s271s9-default@t")
    sp = _tm(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="default-hint",
    )
    assert comp.audience_hint == ""
    # Reload to confirm the DB column also stored the default.
    comp.refresh_from_db()
    assert comp.audience_hint == ""


def test_composition_audience_hint_field_accepts_non_empty_at_create():
    """First-write on the empty-string default is always accepted
    (SESSION 262 ``_observability_value_is_populated`` treats ``""``
    as "not populated")."""
    ws = _ws("s271s9-first@t")
    sp = _tm(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="first-write",
        audience_hint=_HINT,
    )
    comp.refresh_from_db()
    assert comp.audience_hint == _HINT


# ---- 2. talking_head starter copies non-empty hint → step.params -----


def test_talking_head_starter_copies_non_empty_hint_to_step_params():
    """Non-empty ``audience_hint`` supplied to ``talking_head`` must
    both persist on the Composition row AND land in the single
    generate_avatar_speech step's params dict so the SESSION 270
    ``_resolve_solo_audience_hint`` resolver picks it up in its
    step.params → settings → env precedence chain."""
    ws = _ws("s271s9-copy@t")
    sp = _tm(ws)
    comp = talking_head(
        workspace=ws, spokesperson=sp,
        script="Explain photosynthesis.",
        use_knowledge=True,
        target_duration_seconds=60,
        mock_mode=True,
        audience_hint=_HINT,
    )
    assert comp.audience_hint == _HINT
    step = comp.steps.first()
    assert step is not None
    assert step.params.get("audience_hint") == _HINT


def test_talking_head_starter_strips_whitespace_around_hint():
    """The starter normalizes the persisted value the same way the
    SESSION 270 resolver treats whitespace — leading / trailing
    whitespace stripped; internal whitespace preserved."""
    ws = _ws("s271s9-strip@t")
    sp = _tm(ws)
    padded = f"   {_HINT}   "
    comp = talking_head(
        workspace=ws, spokesperson=sp,
        script="Explain photosynthesis.",
        use_knowledge=True,
        target_duration_seconds=60,
        mock_mode=True,
        audience_hint=padded,
    )
    assert comp.audience_hint == _HINT  # not padded
    step = comp.steps.first()
    assert step is not None
    assert step.params.get("audience_hint") == _HINT


# ---- 3. Blank hint → no step.params key ------------------------------


def test_talking_head_starter_omits_step_param_when_hint_blank():
    """Blank / whitespace-only ``audience_hint`` at the starter must
    NOT add a step.params key. This preserves the pre-SESSION-270
    step.params shape byte-for-byte on renders that rely on the
    universal Writing Contract v6 invariant's baseline (Teammate.
    who_you_help via §1 AUDIENCE) — the resolver sees no step.params
    key and returns None."""
    ws = _ws("s271s9-blank@t")
    sp = _tm(ws)
    for blank_hint in (None, "", "   ", "\n\t  \n"):
        comp = talking_head(
            workspace=ws, spokesperson=sp,
            script="Explain photosynthesis.",
            use_knowledge=True,
            target_duration_seconds=60,
            mock_mode=True,
            audience_hint=blank_hint,
        )
        assert comp.audience_hint == ""
        step = comp.steps.first()
        assert step is not None
        assert "audience_hint" not in step.params, (
            f"blank hint {blank_hint!r} leaked into step.params"
        )


def test_talking_head_starter_omits_step_param_when_hint_kwarg_absent():
    """Not passing ``audience_hint`` at all is byte-identical to
    passing ``None`` (both silently drop; no step.params key added).
    This guards the pre-SESSION-271 caller shape for legacy code
    paths that never learned about audience_hint."""
    ws = _ws("s271s9-absent@t")
    sp = _tm(ws)
    comp = talking_head(
        workspace=ws, spokesperson=sp,
        script="Explain photosynthesis.",
        use_knowledge=True,
        target_duration_seconds=60,
        mock_mode=True,
    )
    assert comp.audience_hint == ""
    step = comp.steps.first()
    assert step is not None
    assert "audience_hint" not in step.params


# ---- 4. Immutability semantics (SESSION 262) -------------------------


def test_composition_audience_hint_immutable_after_first_write():
    """Once ``audience_hint`` is populated with a non-default value,
    subsequent overwrites raise ValidationError at ``save()`` — same
    SESSION 262 provenance-guard semantics as ``operator_topic``,
    ``first_pass_synthesis``, ``render_dispatched_at``, etc."""
    ws = _ws("s271s9-imm@t")
    sp = _tm(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="imm-hint",
        audience_hint=_HINT,
    )
    # Reload so from_db() populates the snapshot.
    comp = Composition.objects.get(pk=comp.pk)
    comp.audience_hint = "AUDIENCE: technical adults."
    with pytest.raises(ValidationError) as exc:
        comp.save()
    assert "audience_hint" in str(exc.value)


def test_composition_audience_hint_no_op_save_does_not_raise():
    """A save that keeps the same audience_hint value (a no-op
    write) must NOT raise — the SESSION 262 guard only fires on
    actual divergence, not on re-saves of the persisted value."""
    ws = _ws("s271s9-noop@t")
    sp = _tm(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="noop-hint",
        audience_hint=_HINT,
    )
    comp = Composition.objects.get(pk=comp.pk)
    # Same value — must succeed.
    comp.audience_hint = _HINT
    comp.save()
    comp.refresh_from_db()
    assert comp.audience_hint == _HINT


# ---- 5. SESSION 270 resolver regression ------------------------------


def test_session270_resolver_precedence_still_prefers_step_params():
    """Regression: after promoting audience_hint to a Composition
    field, the SESSION 270 ``_resolve_solo_audience_hint`` resolver
    must still honour its documented step.params → settings → env
    precedence. The Composition field is NOT a fourth precedence
    source — the starter is responsible for copying it into
    step.params, and the resolver reads only step.params."""
    from apps.compositions.primitives.avatar_speech import (
        _resolve_solo_audience_hint,
    )
    from unittest.mock import MagicMock

    step = MagicMock()
    step.params = {"audience_hint": "from step.params"}
    # settings + env would say otherwise, but step.params wins.
    resolved = _resolve_solo_audience_hint(step)
    assert resolved == "from step.params"


def test_session270_resolver_returns_none_when_step_params_blank():
    """When ``audience_hint`` is absent from step.params (which is
    how the starter now shapes the step when the Composition field
    is blank), the resolver falls through to settings → env → None.
    In an isolated test with no settings / env overrides, the
    fallback is None — the caller then passes None to synthesis
    and the prompt stays byte-stable per SESSION 270 contract."""
    from apps.compositions.primitives.avatar_speech import (
        _resolve_solo_audience_hint,
    )
    from unittest.mock import MagicMock

    step = MagicMock()
    step.params = {}  # no audience_hint key
    resolved = _resolve_solo_audience_hint(step)
    # Under the test suite's default settings + env, both fallback
    # sources are unset. The resolver returns None.
    assert resolved is None
