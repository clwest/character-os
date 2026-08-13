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
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ---------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(ws: Workspace, name: str = "Marcus") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test spokesperson.",
    )


def _make_composition(ws: Workspace, sp: Teammate) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="test comp",
        template_kind="talking_head_polished",
    )


# ---- happy path -------------------------------------------------


def test_campaign_persists_with_realistic_fields() -> None:
    ws = _make_workspace("b32hp@test")
    sp = _make_teammate(ws)

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
    sp = _make_teammate(ws)
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
    sp_b = _make_teammate(ws_b)

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
    sp_b = _make_teammate(ws_b)

    c = PersonalizedCampaign(
        workspace=ws_a, spokesperson=sp_b,
        name="x", template="Hi {n}", placeholders=["n"],
    )
    with pytest.raises(ValidationError):
        c.save()


def test_same_workspace_save_succeeds() -> None:
    """Regression guard — same-ws saves work cleanly."""
    ws = _make_workspace("b32ok@test")
    sp = _make_teammate(ws)
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
    sp_a = _make_teammate(ws_a, name="A")
    sp_b = _make_teammate(ws_b, name="B")

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
    sp = _make_teammate(ws)
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


# ---- BC1 — source_script FK -------------------------------------


def _make_script(
    ws: Workspace, sp: Teammate, name: str = "Five Good Emperors",
):
    """BC1 fixture — a READY Script with non-empty draft_text
    in the same workspace as the supplied spokesperson."""
    from apps.scripts.models import Script

    return Script.objects.create(
        workspace=ws,
        spokesperson=sp,
        name=name,
        prompt="explain the five good emperors and the antonine peace",
        draft_text=(
            "Today we're tackling the Five Good Emperors and the "
            "Antonine peace..."
        ),
        knowledge_chunk_ids=["chunk-a", "chunk-b"],
        status="ready",
    )


def test_source_script_defaults_to_none() -> None:
    """BC1 — back-compat: existing C-arc create flow that
    doesn't pass source_script keeps working. The new field
    must default to None / nullable."""
    ws = _make_workspace("bc1null@test")
    sp = _make_teammate(ws)
    c = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="no-source", template="Hi {n}", placeholders=["n"],
    )
    assert c.source_script is None
    assert c.source_script_id is None


def test_source_script_persists_and_reverse_name_resolves() -> None:
    """BC1 — happy path: source_script FK round-trips +
    Script.derived_campaigns reverse manager surfaces the
    Campaign for the BC0 rule-1 query path."""
    ws = _make_workspace("bc1happy@test")
    sp = _make_teammate(ws)
    script = _make_script(ws, sp)
    c = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="from-script", template=script.draft_text,
        placeholders=[],
        source_script=script,
    )
    # FK persisted on the Campaign side.
    assert c.source_script_id == script.pk
    refetched = PersonalizedCampaign.objects.get(pk=c.pk)
    assert refetched.source_script_id == script.pk
    # Rule 1 — reverse query through related_name resolves
    # without back-reference on Script (Script schema unchanged).
    derived = list(script.derived_campaigns.all())
    assert derived == [refetched]


def test_cross_workspace_source_script_rejected_at_clean() -> None:
    """BC0 rule 3 — source_script.workspace MUST equal
    campaign.workspace. clean() catches the form path."""
    ws_a = _make_workspace("bc1xclean_a@test")
    ws_b = _make_workspace("bc1xclean_b@test")
    sp_a = _make_teammate(ws_a, name="MarcusA")
    sp_b = _make_teammate(ws_b, name="MarcusB")
    script_b = _make_script(ws_b, sp_b)

    c = PersonalizedCampaign(
        workspace=ws_a,
        spokesperson=sp_a,
        name="x", template="Hi {n}", placeholders=["n"],
        source_script=script_b,  # belongs to ws_b
    )
    with pytest.raises(ValidationError) as exc:
        c.full_clean()
    assert "source_script" in exc.value.message_dict
    assert "different workspace" in str(exc.value)


def test_cross_workspace_source_script_rejected_at_signal() -> None:
    """BC0 rule 3 — signal catches the raw .save() path that
    bypasses clean()."""
    ws_a = _make_workspace("bc1xsig_a@test")
    ws_b = _make_workspace("bc1xsig_b@test")
    sp_a = _make_teammate(ws_a, name="MarcusA")
    sp_b = _make_teammate(ws_b, name="MarcusB")
    script_b = _make_script(ws_b, sp_b)

    c = PersonalizedCampaign(
        workspace=ws_a,
        spokesperson=sp_a,
        name="x", template="Hi {n}", placeholders=["n"],
        source_script=script_b,
    )
    with pytest.raises(ValidationError):
        c.save()


def test_protect_on_delete_prevents_script_deletion_when_referenced() -> None:
    """BC0 rule 9 — on_delete=PROTECT prevents silent lineage
    orphaning. A Script referenced by any Campaign cannot be
    deleted until the referencing Campaign is removed first."""
    from django.db.models.deletion import ProtectedError

    ws = _make_workspace("bc1protect@test")
    sp = _make_teammate(ws)
    script = _make_script(ws, sp)
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp,
        name="protect-me", template=script.draft_text,
        placeholders=[],
        source_script=script,
    )

    # Direct Script.delete() must be blocked.
    with pytest.raises(ProtectedError):
        script.delete()

    # Script still exists.
    assert script.__class__.objects.filter(pk=script.pk).exists()

    # Cascade through Campaign removes the FK, then Script
    # delete succeeds.
    campaign.delete()
    script.delete()
    assert not script.__class__.objects.filter(pk=script.pk).exists()
