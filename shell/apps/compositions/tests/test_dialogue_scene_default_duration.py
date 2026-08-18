"""SESSION 264 post-Terra-dogfood — Episode / Dialogue Scene
default duration raised from 60 s to 90 s.

Scope-locked tests for the four operator-brief invariants:

1. Episode / Dialogue Scene AI Topic defaults to 90 s when
   ``target_duration_seconds`` is omitted from the resolver
   input. (Both entry paths: recipe registry schema default +
   resolver fallback.)
2. Explicit 60-second selection still produces a 60-second
   target — the backend must not silently override an operator
   value.
3. Unrelated recipes retain their existing defaults —
   talking-head, spokesperson (talking-head-polished),
   long-form-ad, storyboard-voiced, etc.
4. The change is scoped to Dialogue Scene AI Topic mode only;
   manual-mode dialogue_scene resolution is unaffected (there
   is no target_duration_seconds in manual mode).

Zero provider calls; the resolver + registry are pure Python.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.recipes import (
    RECIPES,
    _dialogue_resolver,
    get_recipe,
)
from apps.spokespeople.models import Teammate

User = get_user_model()
pytestmark = pytest.mark.django_db


def _ws(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _cast(ws: Workspace) -> tuple[Teammate, Teammate]:
    patch = Teammate.objects.create(
        workspace=ws, name="Patch",
        runway_avatar_id="av-p",
        portrait_path="https://fake/p.png",
        business_brief="Patch",
    )
    rivet = Teammate.objects.create(
        workspace=ws, name="Rivet",
        runway_avatar_id="av-r",
        portrait_path="https://fake/r.png",
        business_brief="Rivet",
    )
    return patch, rivet


# ============================================================
# 1. Registry-schema default
# ============================================================


def test_dialogue_scene_target_duration_field_default_is_90():
    """The recipe registry advertises the target_duration_seconds
    default the SPA form uses as its initial value. Was "60" before
    the SESSION 264 post-Terra dogfood change; now "90"."""
    recipe = get_recipe("dialogue_scene")
    field = next(
        (f for f in recipe.fields if f.name == "target_duration_seconds"),
        None,
    )
    assert field is not None, "target_duration_seconds field missing from dialogue_scene recipe"
    assert field.default == "90"


def test_dialogue_scene_target_duration_choices_unchanged():
    """The set of selectable durations is unchanged; only the
    default moved. Guards against a rollout that trimmed 60 s off
    the choice list — 60 must remain an operator-selectable value."""
    recipe = get_recipe("dialogue_scene")
    field = next(
        f for f in recipe.fields if f.name == "target_duration_seconds"
    )
    choice_values = {c["value"] for c in field.choices}
    assert choice_values == {"30", "60", "90", "120"}


# ============================================================
# 2. Resolver fallback (when SPA omits the field entirely)
# ============================================================


def test_dialogue_resolver_defaults_target_duration_to_90():
    """The resolver's fallback for a missing ``target_duration_seconds``
    kwarg. Moved from 60 to 90 per operator brief (§11.3 of the
    migration doc)."""
    ws = _ws("dur-def@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "dialogue_mode": "ai_topic",
            "primary_spokesperson_id": str(p.pk),
            "secondary_spokesperson_id": str(r.pk),
            "topic": "The agent is acting weird again",
            # NOTE: target_duration_seconds intentionally omitted.
        },
        created_by=None,
    )
    assert kwargs["target_duration_seconds"] == 90


# ============================================================
# 3. Explicit operator value is not silently overridden
# ============================================================


@pytest.mark.parametrize("explicit", [30, 60, 90, 120])
def test_dialogue_resolver_honors_explicit_target_duration(explicit):
    """Regression guard against a change that accidentally overrides
    the operator's explicit choice with the new 90 s default. Every
    supported value round-trips unchanged."""
    ws = _ws(f"dur-{explicit}@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "dialogue_mode": "ai_topic",
            "primary_spokesperson_id": str(p.pk),
            "secondary_spokesperson_id": str(r.pk),
            "topic": "explicit-duration test",
            "target_duration_seconds": explicit,
        },
        created_by=None,
    )
    assert kwargs["target_duration_seconds"] == explicit


def test_dialogue_resolver_honors_explicit_60_even_after_default_moved():
    """The specific case the operator brief names: 60-second
    selection still produces a 60-second target after the default
    moved to 90."""
    ws = _ws("explicit-60@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "dialogue_mode": "ai_topic",
            "primary_spokesperson_id": str(p.pk),
            "secondary_spokesperson_id": str(r.pk),
            "topic": "explicit 60 s test",
            "target_duration_seconds": 60,
        },
        created_by=None,
    )
    assert kwargs["target_duration_seconds"] == 60


def test_dialogue_resolver_honors_explicit_60_as_string():
    """The SPA select emits strings; the resolver coerces via
    ``int()``. Regression guard on string→int coercion for the
    now-non-default value."""
    ws = _ws("explicit-60str@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "dialogue_mode": "ai_topic",
            "primary_spokesperson_id": str(p.pk),
            "secondary_spokesperson_id": str(r.pk),
            "topic": "string-int coercion test",
            "target_duration_seconds": "60",
        },
        created_by=None,
    )
    assert kwargs["target_duration_seconds"] == 60


# ============================================================
# 4. Scope lock — unrelated recipes unaffected
# ============================================================


def _get_field(recipe, name: str):
    return next((f for f in recipe.fields if f.name == name), None)


def test_unrelated_recipe_defaults_unchanged():
    """Every recipe that has a ``target_duration_seconds`` field
    outside dialogue_scene must retain its pre-SESSION-264 default.
    The operator brief explicitly names talking-head, spokesperson
    videos, long-form ads, and other recipes as out of scope for
    this change.

    Frozen values below are the actual pre-SESSION-264 state
    (captured from ``git show HEAD~1:shell/apps/compositions/recipes.py``
    when this test file was added). If any of these drift under a
    dialogue-scene default-change commit, the change scope was
    wrong."""
    frozen_expected: dict[str, dict[str, object]] = {
        # talking_head's ``target_duration_seconds`` default was
        # "" (empty string = "use spokesperson-shape defaults per
        # SESSION 253 Stage 1 recalibration"). MUST stay empty;
        # SESSION 264 must NOT set talking_head to any explicit
        # duration.
        "talking_head": {"target_duration_seconds": ""},
        # long_form_ad had a target_duration_seconds default of
        # "90" LONG BEFORE SESSION 264 (SESSION 251 duration-driven
        # synthesis). It must STAY at "90"; the SESSION 264 change
        # coincidentally landed on the same number, but the two
        # defaults have different origin stories and are governed
        # by different scopes.
        "long_form_ad": {"target_duration_seconds": "90"},
    }
    for kind, expected_fields in frozen_expected.items():
        recipe = RECIPES.get(kind)
        assert recipe is not None, f"recipe {kind!r} not registered"
        for field_name, expected_default in expected_fields.items():
            field = _get_field(recipe, field_name)
            assert field is not None, (
                f"{kind}.{field_name} missing — cannot verify "
                "unrelated-recipe scope lock"
            )
            assert field.default == expected_default, (
                f"{kind}.{field_name} default drifted from "
                f"{expected_default!r} to {field.default!r} — "
                "SESSION 264 duration change should be scoped to "
                "dialogue_scene only"
            )




def test_dialogue_scene_manual_mode_unaffected_by_default_change():
    """Manual-mode dialogue_scene has no target_duration_seconds
    in its kwargs — the field is AI-Topic-only. This test guards
    against a change that accidentally started injecting the new
    90 s default into manual-mode resolutions."""
    ws = _ws("dur-manual@t")
    p, r = _cast(ws)
    kwargs = _dialogue_resolver(
        workspace=ws,
        params={
            "dialogue_mode": "manual",
            "primary_spokesperson_id": str(p.pk),
            "lines": [
                {"spokesperson_id": str(p.pk), "text": "one"},
                {"spokesperson_id": str(r.pk), "text": "two"},
            ],
        },
        created_by=None,
    )
    assert kwargs["dialogue_mode"] == "manual"
    # Manual mode does NOT inject target_duration_seconds — the
    # starter's manual path renders exactly the lines the operator
    # provided.
    assert "target_duration_seconds" not in kwargs
