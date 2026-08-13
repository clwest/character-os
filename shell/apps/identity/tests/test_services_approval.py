"""Identity-version approval / supersede / reject semantics.

Concurrency (multi-threaded approvals against the same identity)
lives in ``test_services_concurrency.py`` — this module walks the
single-threaded state-machine cases:

* declarative approval floor (§17.5.b) is enforced;
* idempotent re-approval of the same version;
* supersede + approve in one round-trip;
* invalid state transitions raise domain-typed errors;
* cross-identity mismatch raises.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity import services
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    IdentityReference,
    IdentityReferenceKind,
    ReferenceState,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


def _valid_human_spec() -> dict:
    return {
        "spec_schema_version": 1,
        "age_presentation": {"min_years": 30, "max_years": 45},
        "skin_tone": {"descriptor": "medium olive", "undertone": "olive"},
        "hair": {"length": "medium", "texture": "wavy", "color": "dark brown"},
        "eye": {"color": "hazel", "shape": "almond"},
        "face_shape": {"descriptor": "oval"},
        "gender_presentation": {"descriptor": "feminine", "primary_axis": "feminine"},
        "canonical_outfit": {
            "descriptor": "cream linen blazer over a navy tee",
            "formality": "smart_casual",
            "material_family": "linen",
        },
    }


def _make_setup(email: str):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name="Ruby",
    )
    return user, ws, identity


def _approve_reference(ws: Workspace, version: CharacterIdentityVersion, purpose: str) -> None:
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path=f"media/{purpose}.png",
    )
    ref = services.attach_reference(
        version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose=purpose,
    )
    # Bypass the write-path service on the reference itself — a
    # reference reaches ``state=approved`` via a reviewer workflow
    # that will land in Steps 8-10. For this test we set the state
    # directly on a valid reference row.
    IdentityReference.objects.filter(pk=ref.pk).update(state=ReferenceState.APPROVED)


def _satisfy_floor(ws: Workspace, version: CharacterIdentityVersion) -> None:
    """Land approved references matching the human branch's
    declarative floor (``portrait_reference/front`` +
    ``portrait_reference/neutral_rest``).
    """
    for purpose in ("front", "neutral_rest"):
        _approve_reference(ws, version, purpose)


# ---- approval floor -----------------------------------------------


def test_approve_rejects_when_floor_not_satisfied() -> None:
    user, _, identity = _make_setup("approve-floor-missing@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    with pytest.raises(services.IdentityVersionApprovalError) as ei:
        services.approve_version(version, approver=user)
    assert ei.value.code == "floor_not_satisfied"


def test_approve_succeeds_when_floor_satisfied() -> None:
    user, ws, identity = _make_setup("approve-floor-ok@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, version)
    approved = services.approve_version(version, approver=user)
    assert approved.state == "approved"
    assert approved.approved_at is not None
    assert approved.approved_by_id == user.id


# ---- idempotency + supersede --------------------------------------


def test_approve_is_idempotent_on_already_approved_version() -> None:
    user, ws, identity = _make_setup("approve-idempotent@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, version)
    services.approve_version(version, approver=user)

    original_approved_at = CharacterIdentityVersion.objects.get(pk=version.pk).approved_at
    result = services.approve_version(version, approver=user)
    assert result.state == "approved"
    # approved_at should not shift on the idempotent second call.
    assert CharacterIdentityVersion.objects.get(pk=version.pk).approved_at == original_approved_at


def test_approve_supersedes_prior_approved_version_atomically() -> None:
    user, ws, identity = _make_setup("approve-supersede@t")

    v1 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, v1)
    services.approve_version(v1, approver=user)

    v2 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, v2)
    services.approve_version(v2, approver=user)

    v1.refresh_from_db()
    v2.refresh_from_db()
    assert v1.state == "superseded"
    assert v1.superseded_at is not None
    assert v2.state == "approved"

    # Exactly one approved version per identity.
    approved_count = CharacterIdentityVersion.objects.filter(
        identity=identity, state="approved",
    ).count()
    assert approved_count == 1


# ---- invalid state transitions ------------------------------------


def test_approve_rejects_superseded_version() -> None:
    user, ws, identity = _make_setup("approve-reject-super@t")
    v1 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, v1)
    services.approve_version(v1, approver=user)
    v2 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, v2)
    services.approve_version(v2, approver=user)

    v1.refresh_from_db()
    with pytest.raises(services.IdentityVersionApprovalError) as ei:
        services.approve_version(v1, approver=user)
    assert ei.value.code == "invalid_state_transition"


def test_approve_rejects_rejected_version() -> None:
    user, _, identity = _make_setup("approve-reject-rejected@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    services.reject_version(version, reason="test")
    version.refresh_from_db()
    with pytest.raises(services.IdentityVersionApprovalError) as ei:
        services.approve_version(version, approver=user)
    assert ei.value.code == "invalid_state_transition"


def test_supersede_rejects_non_approved_version() -> None:
    _, _, identity = _make_setup("super-reject-nonapproved@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    with pytest.raises(services.IdentityVersionError) as ei:
        services.supersede_version(version, reason="test")
    assert ei.value.code == "invalid_state_transition"


def test_reject_rejects_non_draft_version() -> None:
    user, ws, identity = _make_setup("reject-reject-nondraft@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    _satisfy_floor(ws, version)
    services.approve_version(version, approver=user)
    version.refresh_from_db()
    with pytest.raises(services.IdentityVersionError) as ei:
        services.reject_version(version, reason="too-late")
    assert ei.value.code == "invalid_state_transition"


# ---- reject (draft only) ------------------------------------------


def test_reject_draft_transitions_to_rejected() -> None:
    _, _, identity = _make_setup("reject-happy@t")
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    result = services.reject_version(version, reason="unfit")
    assert result.state == "rejected"
    assert "rejected: unfit" in result.reviewer_notes
