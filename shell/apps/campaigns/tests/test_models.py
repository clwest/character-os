"""B3.2 — PersonalizedCampaign + PersonalizedRecipient model tests.

Six concerns:

1. Happy-path saves with realistic FK shape.
2. Status enum values match the scope-lock state machine.
3. Cross-workspace spokesperson rejected (clean + signal).
4. Cross-workspace produced_composition on recipient rejected.
5. Recipient.workspace property surfaces campaign.workspace
   (for IsWorkspaceMember permission resolver).
6. Tier limit table carries personalized_batch_max for all
   three tiers (Q-c-1 lock).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Workspace
from apps.billing.models import TIER_LIMITS, tier_limit
from apps.campaigns.models import (
    PersonalizedCampaign,
    PersonalizedRecipient,
)
from apps.compositions.models import Composition
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ---------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_spokesperson(ws: Workspace, name: str = "Marcus") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test spokesperson.",
    )


def _make_composition(ws: Workspace, sp: Spokesperson) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="test comp",
        template_kind="talking_head_polished",
    )


# ---- happy path -------------------------------------------------


def test_campaign_persists_with_realistic_fields() -> None:
    ws = _make_workspace("b32hp@test")
    sp = _make_spokesperson(ws)

    c = PersonalizedCampaign.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="Q3 outreach",
        template="Hi {first_name}, saw {company} just hit {milestone}!",
        placeholders=["first_name", "company", "milestone"],
    )
    assert c.id is not None
    assert c.status == PersonalizedCampaign.Status.DRAFT
    assert c.launched_at is None
    assert c.completed_at is None
    assert c.placeholders == ["first_name", "company", "milestone"]


def test_recipient_persists_with_realistic_fields() -> None:
    ws = _make_workspace("b32hpr@test")
    sp = _make_spokesperson(ws)
    c = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp, name="x", template="Hi {name}",
        placeholders=["name"],
    )

    r = PersonalizedRecipient.objects.create(
        campaign=c,
        variables={"name": "Bob"},
        label="Bob",
        position=0,
    )
    assert r.id is not None
    assert r.status == PersonalizedRecipient.Status.PENDING
    assert r.workspace == ws  # property surface
    assert r.rendered_script == ""
    assert r.produced_composition is None


# ---- enum coverage ---------------------------------------------


def test_campaign_status_enum_matches_scope_lock() -> None:
    """v1 ships exactly six campaign statuses per the state
    machine in PERSONALIZED_VIDEO_V1.md."""
    expected = {
        "draft", "launching", "in_flight",
        "completed", "partial", "failed",
    }
    actual = {choice for choice, _ in PersonalizedCampaign.Status.choices}
    assert actual == expected


def test_recipient_status_enum_matches_scope_lock() -> None:
    """v1 ships exactly five recipient statuses per the
    state machine."""
    expected = {"pending", "queued", "running", "completed", "failed"}
    actual = {choice for choice, _ in PersonalizedRecipient.Status.choices}
    assert actual == expected


# ---- workspace isolation ---------------------------------------


def test_cross_workspace_spokesperson_rejected_at_clean() -> None:
    """Rule 3 — campaign.spokesperson must live in
    campaign.workspace."""
    ws_a = _make_workspace("b32iso_a@test")
    ws_b = _make_workspace("b32iso_b@test")
    sp_b = _make_spokesperson(ws_b)

    c = PersonalizedCampaign(
        workspace=ws_a,
        spokesperson=sp_b,
        name="x", template="Hi {name}",
        placeholders=["name"],
    )
    with pytest.raises(ValidationError) as exc:
        c.full_clean()
    assert "different workspace" in str(exc.value)


def test_cross_workspace_spokesperson_rejected_at_signal() -> None:
    """Rule 3 — signal catches the raw .save() path too."""
    ws_a = _make_workspace("b32sig_a@test")
    ws_b = _make_workspace("b32sig_b@test")
    sp_b = _make_spokesperson(ws_b)

    c = PersonalizedCampaign(
        workspace=ws_a, spokesperson=sp_b,
        name="x", template="Hi {n}", placeholders=["n"],
    )
    with pytest.raises(ValidationError):
        c.save()


def test_same_workspace_save_succeeds() -> None:
    """Regression guard — same-ws saves work cleanly."""
    ws = _make_workspace("b32ok@test")
    sp = _make_spokesperson(ws)
    c = PersonalizedCampaign(
        workspace=ws, spokesperson=sp,
        name="x", template="Hi {n}", placeholders=["n"],
    )
    c.full_clean()
    c.save()
    assert c.pk is not None


def test_cross_workspace_produced_composition_rejected_on_recipient() -> None:
    """Rule 3 — recipient.produced_composition must live in
    the same workspace as the campaign (which inherits from
    its own workspace FK)."""
    ws_a = _make_workspace("b32ra@test")
    ws_b = _make_workspace("b32rb@test")
    sp_a = _make_spokesperson(ws_a, name="A")
    sp_b = _make_spokesperson(ws_b, name="B")

    campaign_a = PersonalizedCampaign.objects.create(
        workspace=ws_a, spokesperson=sp_a,
        name="x", template="Hi {n}", placeholders=["n"],
    )
    comp_b = _make_composition(ws_b, sp_b)

    r = PersonalizedRecipient(
        campaign=campaign_a,
        variables={"n": "x"}, label="x", position=0,
        produced_composition=comp_b,
        status=PersonalizedRecipient.Status.QUEUED,
    )
    with pytest.raises(ValidationError) as exc:
        r.full_clean()
    assert "different workspace" in str(exc.value)


def test_recipient_workspace_property_resolves_to_campaign_workspace() -> None:
    """The .workspace property is what
    character_os.permissions._workspace_of() reads to enforce
    IsWorkspaceMember on detail routes."""
    ws = _make_workspace("b32wsprop@test")
    sp = _make_spokesperson(ws)
    c = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="x", template="Hi {n}", placeholders=["n"],
    )
    r = PersonalizedRecipient.objects.create(
        campaign=c, variables={"n": "Bob"}, label="Bob", position=0,
    )
    assert r.workspace == ws


# ---- TIER_LIMITS — Q-c-1 lock -----------------------------------


def test_personalized_batch_max_present_for_all_tiers() -> None:
    """Q-c-1: Starter=5, Pro=30, Agency=200."""
    assert TIER_LIMITS["starter"]["personalized_batch_max"] == 5
    assert TIER_LIMITS["pro"]["personalized_batch_max"] == 30
    assert TIER_LIMITS["agency"]["personalized_batch_max"] == 200


def test_tier_limit_helper_returns_per_batch_cap() -> None:
    """The shared tier_limit() helper works for the new
    field too (same shape as videos_per_month)."""
    assert tier_limit("starter", "personalized_batch_max") == 5
    assert tier_limit("pro", "personalized_batch_max") == 30
    assert tier_limit("agency", "personalized_batch_max") == 200
