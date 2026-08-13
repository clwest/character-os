"""Tests for ``services.supersede_reference_at_slot`` — SESSION 249 9.b.3a.

Load-bearing behavior covered:

* Transitions the current APPROVED reference at (version, kind, purpose)
  to SUPERSEDED without admitting a replacement.
* Idempotent no-op when no APPROVED occupant exists.
* Refuses to operate on a non-DRAFT parent version per §5.4.
* Does not touch evidence rows (Assets, GenerationRecord,
  NormalizationManifest).
* Records ``reason`` into ``reviewer_notes`` when supplied.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetRole, AssetType
from apps.identity import services
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    ExecutionMode,
    ExecutionModeActual,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    ReferenceState,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _make_workspace(email: str):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_identity(ws: Workspace) -> CharacterIdentity:
    return CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name="Bootstrap fixture",
    )


def _make_draft_version(identity: CharacterIdentity) -> CharacterIdentityVersion:
    return CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )


def _make_asset(ws: Workspace) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE,
        file_path="/tmp/nothing.png",
    )


def _make_gr(version: CharacterIdentityVersion, raw: Asset) -> GenerationRecord:
    return services.record_generation(
        version=version,
        provider=GenerationProvider.STABILITY_STILL,
        provider_model="sd3-large",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        raw_output_asset=raw,
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        elapsed_ms=1000,
    )


def _make_and_approve_reference(
    version: CharacterIdentityVersion, ws: Workspace
) -> IdentityReference:
    raw = _make_asset(ws)
    gr = _make_gr(version, raw)
    ref = services.attach_reference(
        version,
        asset=raw,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.RAW,
        generation_record=gr,
    )
    services.approve_reference(ref)
    ref.refresh_from_db()
    assert ref.state == ReferenceState.APPROVED
    return ref


# ---------------------------------------------------------------------
# Behavior
# ---------------------------------------------------------------------


def test_supersedes_current_approved_reference():
    ws, _user = _make_workspace("s1@example.test")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    ref = _make_and_approve_reference(version, ws)

    result = services.supersede_reference_at_slot(
        version, kind=ref.kind, purpose=ref.purpose, reason="reviewer withdrew"
    )
    assert result is not None
    assert result.pk == ref.pk

    ref.refresh_from_db()
    assert ref.state == ReferenceState.SUPERSEDED
    assert "reviewer withdrew" in (ref.reviewer_notes or "")


def test_idempotent_when_no_approved_occupant():
    ws, _ = _make_workspace("s2@example.test")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    result = services.supersede_reference_at_slot(
        version,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        reason="",
    )
    assert result is None


def test_second_call_is_no_op():
    ws, _ = _make_workspace("s3@example.test")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    ref = _make_and_approve_reference(version, ws)

    first = services.supersede_reference_at_slot(
        version, kind=ref.kind, purpose=ref.purpose
    )
    assert first is not None
    second = services.supersede_reference_at_slot(
        version, kind=ref.kind, purpose=ref.purpose
    )
    assert second is None


def test_refuses_non_draft_parent_version():
    ws, user = _make_workspace("s4@example.test")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    ref = _make_and_approve_reference(version, ws)
    # Add a second required reference so approve_version's floor
    # is satisfied for the human branch (front + neutral_rest).
    raw2 = _make_asset(ws)
    gr2 = _make_gr(version, raw2)
    ref2 = services.attach_reference(
        version,
        asset=raw2,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="neutral_rest",
        state=ReferenceState.RAW,
        generation_record=gr2,
    )
    services.approve_reference(ref2)

    services.approve_version(version, approver=user)
    version.refresh_from_db()
    assert version.state == CharacterIdentityVersion.State.APPROVED

    with pytest.raises(services.IdentityReferenceError) as exc_info:
        services.supersede_reference_at_slot(
            version, kind=ref.kind, purpose=ref.purpose, reason="try"
        )
    assert exc_info.value.code == "parent_version_not_draft"


def test_does_not_touch_evidence_rows():
    ws, _ = _make_workspace("s5@example.test")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    ref = _make_and_approve_reference(version, ws)

    raw_before = ref.asset
    gr_before = ref.generation_record

    services.supersede_reference_at_slot(
        version, kind=ref.kind, purpose=ref.purpose
    )

    raw_before.refresh_from_db()
    gr_before.refresh_from_db()
    assert raw_before.pk is not None  # still exists
    assert gr_before.pk is not None
    # GR is immutable — approval_state stays where it was set.
    assert gr_before.approval_state == "pending"
