"""§19 Step 4.a — Canonical transition services + Postgres partial
unique constraints (ratified in §17.10.a Amendment 4, SESSION 243).

Scope discipline (per SESSION 243 4.a plan):

* Tests exercise ``approve_bundle`` / ``supersede_bundle`` /
  ``approve_reference`` / ``approve_prequalification_version`` and
  the ``PrequalificationProvenance`` model.
* No compatibility-mirror wiring; no
  ``record_prequalification_representation`` orchestration; no
  production call-site migration; no SPA / media-engine touches.
* Substrate correctness is provable **independently** of
  ``apps.identity.compat``. Bundle / reference / version
  transitions land here on their own merits so 4.b–4.c can layer
  compatibility behavior onto a sound substrate.

Ratified semantic under test throughout: ``state='approved'``
means **currently admitted for product use** (§5.6.a). It is not
shorthand for qualified.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity import services
from apps.identity.models import (
    PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
    ApprovedRepresentationBundle,
    CanonicalRealtimeReference,
    CanonicalVoiceReference,
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    ExecutionMode,
    ExecutionModeActual,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    ImportProvenance,
    PrequalificationProvenance,
    PrequalificationSourceCall,
    ReferenceState,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# =====================================================================
# Helpers
# =====================================================================


def _make_workspace(email: str):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_identity(ws: Workspace, *, name: str = "Ruby") -> CharacterIdentity:
    return CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name=name,
    )


def _make_draft_version(
    identity: CharacterIdentity,
    *,
    revision: int = 1,
    spec_schema_version: int = 0,
) -> CharacterIdentityVersion:
    """Create a raw draft version. Uses ``spec_schema_version=0``
    (legacy_unvalidated sentinel) because the Amendment 4 bypass
    paths do the same; the qualified draft-creation service refuses
    schema_version < 1.
    """
    return CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=revision,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=spec_schema_version,
    )


def _make_asset(ws: Workspace, *, file_path: str = "media/front.png") -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path=file_path,
    )


def _make_generation_record(
    version: CharacterIdentityVersion,
    *,
    provider: str = GenerationProvider.MOCK,
) -> GenerationRecord:
    """Real (non-legacy) generation record. Uses non-NULL execution
    fields per Amendment 3 pairing invariant. Legacy import records
    would carry ``provider=LEGACY_IMPORTED`` and NULL execution
    fields — that shape is exercised via ``ImportProvenance``
    fixtures below.
    """
    return GenerationRecord.objects.create(
        identity_version=version,
        provider=provider,
        provider_model="mock-1",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
    )


def _attach_portrait_ref(
    ws: Workspace,
    version: CharacterIdentityVersion,
    *,
    purpose: str = "front",
    state: str = ReferenceState.RAW,
    file_path: str = "media/front.png",
) -> IdentityReference:
    """Create a portrait reference directly via ORM (Step 4.a tests
    exercise ``approve_reference`` on rows created outside a
    reviewer workflow that will land in Steps 8-10).
    """
    return IdentityReference.objects.create(
        identity_version=version,
        asset=_make_asset(ws, file_path=file_path),
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose=purpose,
        state=state,
    )


def _make_prequalification_provenance(
    version: CharacterIdentityVersion,
    *,
    source_call: str = PrequalificationSourceCall.WIZARD_CREATE,
    author: object = None,
) -> PrequalificationProvenance:
    return PrequalificationProvenance.objects.create(
        identity_version=version,
        source_call=source_call,
        author=author,
        snapshot_schema_version=PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        provider_response_snapshot={"note": "test fixture"},
    )


def _make_import_provenance(
    version: CharacterIdentityVersion,
    *,
    import_run_id=None,
) -> ImportProvenance:
    import uuid as _uuid
    return ImportProvenance.objects.create(
        identity_version=version,
        source_teammate_id=_uuid.uuid4(),
        import_run_id=import_run_id or _uuid.uuid4(),
        migration_version="identity.0002_step3_legacy_provenance",
        snapshot_schema_version=1,
        legacy_snapshot={},
    )


# =====================================================================
# PrequalificationProvenance — model semantics
# =====================================================================


def test_prequalification_provenance_round_trip() -> None:
    ws, user = _make_workspace("prov-round@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    prov = _make_prequalification_provenance(
        version, source_call=PrequalificationSourceCall.CHANGE_VOICE, author=user,
    )
    reloaded = PrequalificationProvenance.objects.get(pk=prov.pk)
    assert reloaded.identity_version_id == version.id
    assert reloaded.source_call == "change_voice"
    assert reloaded.author_id == user.id
    assert reloaded.snapshot_schema_version == 1


def test_prequalification_provenance_is_append_only() -> None:
    ws, _ = _make_workspace("prov-append@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    prov = _make_prequalification_provenance(version)

    prov.source_call = PrequalificationSourceCall.WIZARD_REBAKE
    with pytest.raises(ValidationError, match="append-only"):
        prov.save()


def test_prequalification_provenance_mutual_exclusion_with_import_provenance() -> None:
    """§17.10.a Amendment 4 mutual exclusion — a version cannot carry
    both. clean() enforces at the model layer as a defensive second
    layer beneath the authoritative services.
    """
    ws, _ = _make_workspace("prov-mutex@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    _make_import_provenance(version)

    prov = PrequalificationProvenance(
        identity_version=version,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        snapshot_schema_version=1,
        provider_response_snapshot={},
    )
    with pytest.raises(ValidationError, match="mutually exclusive"):
        prov.full_clean()


def test_import_provenance_mutual_exclusion_with_prequalification_provenance() -> None:
    """Reverse direction: adding ImportProvenance after
    PrequalificationProvenance is refused by clean().
    """
    ws, _ = _make_workspace("import-mutex@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    _make_prequalification_provenance(version)

    import uuid as _uuid
    imp = ImportProvenance(
        identity_version=version,
        source_teammate_id=_uuid.uuid4(),
        import_run_id=_uuid.uuid4(),
        migration_version="identity.0002_step3_legacy_provenance",
        snapshot_schema_version=1,
        legacy_snapshot={},
    )
    with pytest.raises(ValidationError, match="mutually exclusive"):
        imp.full_clean()


# =====================================================================
# ReferenceState.SUPERSEDED — enum extension
# =====================================================================


def test_reference_state_enum_includes_superseded() -> None:
    values = {choice.value for choice in ReferenceState}
    assert "superseded" in values, (
        "ReferenceState must carry SUPERSEDED distinct from REJECTED "
        "(§17.10.a Amendment 4)."
    )
    # The full ratified enum shape:
    assert values == {
        "raw",
        "normalized",
        "provisional",
        "approved",
        "superseded",
        "rejected",
    }


# =====================================================================
# approve_reference
# =====================================================================


def test_approve_reference_promotes_raw_to_approved() -> None:
    ws, _ = _make_workspace("ar-basic@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    ref = _attach_portrait_ref(ws, version)

    approved = services.approve_reference(ref)
    approved.refresh_from_db()
    assert approved.state == ReferenceState.APPROVED


def test_approve_reference_is_idempotent_on_already_approved() -> None:
    ws, _ = _make_workspace("ar-idem@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    ref = _attach_portrait_ref(ws, version)
    services.approve_reference(ref)

    result = services.approve_reference(ref)
    assert result.state == ReferenceState.APPROVED


def test_approve_reference_supersedes_prior_occupant_of_same_slot() -> None:
    """The load-bearing SUPERSEDED-vs-REJECTED distinction: a prior
    approved reference at the same (identity_version, kind, purpose)
    slot must move to SUPERSEDED (not REJECTED) when replaced.
    """
    ws, _ = _make_workspace("ar-super@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    ref_a = _attach_portrait_ref(ws, version, file_path="media/a.png")
    services.approve_reference(ref_a)

    ref_b = _attach_portrait_ref(ws, version, file_path="media/b.png")
    services.approve_reference(ref_b)

    ref_a.refresh_from_db()
    ref_b.refresh_from_db()
    assert ref_a.state == ReferenceState.SUPERSEDED, (
        "Prior approved occupant must move to SUPERSEDED, not "
        "REJECTED (§17.10.a Amendment 4)."
    )
    assert ref_a.state != ReferenceState.REJECTED
    assert ref_b.state == ReferenceState.APPROVED


def test_approve_reference_does_not_supersede_different_purpose() -> None:
    """SUPERSEDED cascade is slot-scoped: approving
    portrait_reference/front does not touch portrait_reference/
    neutral_rest.
    """
    ws, _ = _make_workspace("ar-slot@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    ref_front = _attach_portrait_ref(
        ws, version, purpose="front", file_path="media/front.png",
    )
    ref_rest = _attach_portrait_ref(
        ws, version, purpose="neutral_rest", file_path="media/rest.png",
    )
    services.approve_reference(ref_front)
    services.approve_reference(ref_rest)

    ref_front.refresh_from_db()
    ref_rest.refresh_from_db()
    assert ref_front.state == ReferenceState.APPROVED
    assert ref_rest.state == ReferenceState.APPROVED


def test_approve_reference_refuses_superseded_state() -> None:
    ws, _ = _make_workspace("ar-terminal@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    ref_a = _attach_portrait_ref(ws, version, file_path="media/a.png")
    services.approve_reference(ref_a)
    ref_b = _attach_portrait_ref(ws, version, file_path="media/b.png")
    services.approve_reference(ref_b)
    ref_a.refresh_from_db()
    assert ref_a.state == ReferenceState.SUPERSEDED

    with pytest.raises(services.ReferenceApprovalError) as ei:
        services.approve_reference(ref_a)
    assert ei.value.code == "invalid_state_transition"


def test_approve_reference_refuses_rejected_state() -> None:
    ws, _ = _make_workspace("ar-reject@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    ref = _attach_portrait_ref(ws, version, state=ReferenceState.REJECTED)
    with pytest.raises(services.ReferenceApprovalError) as ei:
        services.approve_reference(ref)
    assert ei.value.code == "invalid_state_transition"


def test_reference_partial_unique_db_constraint_fires_on_bypass() -> None:
    """Direct-INSERT bypass around ``approve_reference`` triggers the
    Postgres partial unique. This proves the constraint is the final
    guard, not just service discipline.
    """
    ws, _ = _make_workspace("ar-db-unique@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    ref_a = _attach_portrait_ref(ws, version, file_path="media/a.png")
    services.approve_reference(ref_a)

    # Bypass the service — insert a second APPROVED reference at
    # the same (version, kind, purpose) slot. Postgres refuses.
    ref_b_asset = _make_asset(ws, file_path="media/b.png")
    with pytest.raises(IntegrityError, match="one_approved_reference_per_slot"):
        with transaction.atomic():
            IdentityReference.objects.create(
                identity_version=version,
                asset=ref_b_asset,
                kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
                purpose="front",
                state=ReferenceState.APPROVED,
            )


# =====================================================================
# approve_bundle
# =====================================================================


def _bundle_setup(email: str):
    ws, user = _make_workspace(email)
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    # Bundle-approval invariant requires an approved front portrait.
    portrait = _attach_portrait_ref(ws, version)
    services.approve_reference(portrait)
    return ws, user, identity, version


def test_approve_bundle_promotes_draft_to_approved() -> None:
    ws, user, _, version = _bundle_setup("ab-basic@t")
    bundle = services.create_draft_bundle(version)

    approved = services.approve_bundle(bundle, approver=user)
    approved.refresh_from_db()
    assert approved.state == ApprovedRepresentationBundle.State.APPROVED
    assert approved.approved_at is not None
    assert approved.approved_by_id == user.id


def test_approve_bundle_refuses_without_front_portrait() -> None:
    """§17.10.a Amendment 4 bundle-approval invariant."""
    ws, user = _make_workspace("ab-no-portrait@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    bundle = services.create_draft_bundle(version)

    with pytest.raises(services.BundleApprovalError) as ei:
        services.approve_bundle(bundle, approver=user)
    assert ei.value.code == "missing_front_portrait"


def test_approve_bundle_is_idempotent_on_already_approved() -> None:
    ws, user, _, version = _bundle_setup("ab-idem@t")
    bundle = services.create_draft_bundle(version)
    services.approve_bundle(bundle, approver=user)
    original_approved_at = ApprovedRepresentationBundle.objects.get(pk=bundle.pk).approved_at

    services.approve_bundle(bundle, approver=user)
    assert (
        ApprovedRepresentationBundle.objects.get(pk=bundle.pk).approved_at
        == original_approved_at
    )


def test_approve_bundle_transactionally_supersedes_prior_approved_bundle() -> None:
    ws, user, _, version = _bundle_setup("ab-super@t")
    b1 = services.create_draft_bundle(version)
    services.approve_bundle(b1, approver=user)

    b2 = services.create_draft_bundle(version)
    services.approve_bundle(b2, approver=user)

    b1.refresh_from_db()
    b2.refresh_from_db()
    assert b1.state == ApprovedRepresentationBundle.State.SUPERSEDED
    assert b2.state == ApprovedRepresentationBundle.State.APPROVED

    # Exactly one APPROVED bundle per version — enforced by DB.
    approved_count = ApprovedRepresentationBundle.objects.filter(
        identity_version=version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    ).count()
    assert approved_count == 1


def test_approve_bundle_refuses_non_draft_state() -> None:
    ws, user, _, version = _bundle_setup("ab-terminal@t")
    b1 = services.create_draft_bundle(version)
    services.approve_bundle(b1, approver=user)
    b2 = services.create_draft_bundle(version)
    services.approve_bundle(b2, approver=user)
    b1.refresh_from_db()
    assert b1.state == ApprovedRepresentationBundle.State.SUPERSEDED

    with pytest.raises(services.BundleApprovalError) as ei:
        services.approve_bundle(b1, approver=user)
    assert ei.value.code == "invalid_state_transition"


def test_approve_bundle_refuses_cross_identity_voice_reference() -> None:
    """A bundle FK to a canonical voice on a different identity
    version is refused. ``approve_bundle`` does the check in addition
    to ``create_draft_bundle``.
    """
    ws, user = _make_workspace("ab-cross@t")
    identity = _make_identity(ws)
    version_a = _make_draft_version(identity, revision=1)
    portrait_a = _attach_portrait_ref(ws, version_a)
    services.approve_reference(portrait_a)

    version_b = _make_draft_version(identity, revision=2)
    voice_on_b = CanonicalVoiceReference.objects.create(
        identity_version=version_b,
        generation_record=_make_generation_record(version_b),
        state=ReferenceState.APPROVED,
    )

    # Bypass ``create_draft_bundle`` and construct a bundle that FKs
    # across versions.
    bundle = ApprovedRepresentationBundle.objects.create(
        identity_version=version_a,
        approved_voice=voice_on_b,
        state=ApprovedRepresentationBundle.State.DRAFT,
    )
    with pytest.raises(services.BundleApprovalError) as ei:
        services.approve_bundle(bundle, approver=user)
    assert ei.value.code == "cross_identity_mismatch"


def test_bundle_partial_unique_db_constraint_fires_on_bypass() -> None:
    ws, user, _, version = _bundle_setup("ab-db-unique@t")
    b1 = services.create_draft_bundle(version)
    services.approve_bundle(b1, approver=user)

    # Direct-INSERT bypass: a second APPROVED bundle on the same
    # version. Postgres refuses.
    with pytest.raises(IntegrityError, match="one_approved_bundle_per_identity_version"):
        with transaction.atomic():
            ApprovedRepresentationBundle.objects.create(
                identity_version=version,
                state=ApprovedRepresentationBundle.State.APPROVED,
            )


# =====================================================================
# supersede_bundle
# =====================================================================


def test_supersede_bundle_moves_approved_to_superseded() -> None:
    ws, user, _, version = _bundle_setup("sb-basic@t")
    bundle = services.create_draft_bundle(version)
    approved = services.approve_bundle(bundle, approver=user)

    services.supersede_bundle(approved, reason="operator-directed")
    approved.refresh_from_db()
    assert approved.state == ApprovedRepresentationBundle.State.SUPERSEDED
    assert "operator-directed" in approved.reviewer_notes


def test_supersede_bundle_refuses_draft() -> None:
    ws, _, _, version = _bundle_setup("sb-draft@t")
    bundle = services.create_draft_bundle(version)
    with pytest.raises(services.BundleApprovalError) as ei:
        services.supersede_bundle(bundle)
    assert ei.value.code == "invalid_state_transition"


# =====================================================================
# approve_prequalification_version
# =====================================================================


def test_approve_prequalification_version_refuses_without_provenance() -> None:
    """§17.10.a Amendment 4: the schema-floor bypass path requires
    an explicitly-ratified bypass provenance
    (``PrequalificationProvenance`` or ``ImportProvenance``). A
    version with neither is refused; the caller should use the
    qualified ``approve_version`` instead.
    """
    ws, user = _make_workspace("apv-no-prov@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)

    with pytest.raises(services.PrequalificationVersionApprovalError) as ei:
        services.approve_prequalification_version(version, approver=user)
    assert ei.value.code == "missing_prequalification_provenance"


def test_approve_prequalification_version_accepts_prequalification_provenance() -> None:
    ws, user = _make_workspace("apv-prequal@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    _make_prequalification_provenance(version)

    approved = services.approve_prequalification_version(version, approver=user)
    approved.refresh_from_db()
    assert approved.state == CharacterIdentityVersion.State.APPROVED
    assert approved.approved_by_id == user.id


def test_approve_prequalification_version_accepts_import_provenance() -> None:
    """Amendment 4 permits the same bypass path for
    ImportProvenance too — legacy imports need the same floor bypass
    as prequalification-authored writes.
    """
    ws, user = _make_workspace("apv-import@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    _make_import_provenance(version)

    approved = services.approve_prequalification_version(version, approver=user)
    approved.refresh_from_db()
    assert approved.state == CharacterIdentityVersion.State.APPROVED


def test_approve_prequalification_version_is_idempotent() -> None:
    ws, user = _make_workspace("apv-idem@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    _make_prequalification_provenance(version)
    services.approve_prequalification_version(version, approver=user)
    original_approved_at = CharacterIdentityVersion.objects.get(pk=version.pk).approved_at

    services.approve_prequalification_version(version, approver=user)
    assert (
        CharacterIdentityVersion.objects.get(pk=version.pk).approved_at
        == original_approved_at
    )


def test_approve_prequalification_version_supersedes_prior_and_cascades_child_state() -> None:
    """Load-bearing test: when a version transitions APPROVED →
    SUPERSEDED, its APPROVED child rows (bundle, references, voice,
    realtime) must cascade to SUPERSEDED. §5.6.a mandates that
    child rows of a superseded version cannot be
    currently-admitted.
    """
    ws, user = _make_workspace("apv-cascade@t")
    identity = _make_identity(ws)

    # v1 with a full trio of approved children.
    v1 = _make_draft_version(identity, revision=1)
    _make_prequalification_provenance(v1)
    portrait_v1 = _attach_portrait_ref(ws, v1)
    services.approve_reference(portrait_v1)
    voice_v1 = CanonicalVoiceReference.objects.create(
        identity_version=v1,
        generation_record=_make_generation_record(v1),
        state=ReferenceState.APPROVED,
    )
    realtime_v1 = CanonicalRealtimeReference.objects.create(
        identity_version=v1,
        generation_record=_make_generation_record(v1),
        state=ReferenceState.APPROVED,
    )
    bundle_v1 = ApprovedRepresentationBundle.objects.create(
        identity_version=v1,
        approved_voice=voice_v1,
        approved_realtime=realtime_v1,
        state=ApprovedRepresentationBundle.State.DRAFT,
    )
    services.approve_bundle(bundle_v1, approver=user)
    services.approve_prequalification_version(v1, approver=user)

    # v2 supersedes v1.
    v2 = _make_draft_version(identity, revision=2)
    _make_prequalification_provenance(v2)
    services.approve_prequalification_version(v2, approver=user)

    v1.refresh_from_db()
    bundle_v1.refresh_from_db()
    portrait_v1.refresh_from_db()
    voice_v1.refresh_from_db()
    realtime_v1.refresh_from_db()

    assert v1.state == CharacterIdentityVersion.State.SUPERSEDED
    assert v1.superseded_at is not None
    assert bundle_v1.state == ApprovedRepresentationBundle.State.SUPERSEDED
    assert portrait_v1.state == ReferenceState.SUPERSEDED
    assert voice_v1.state == ReferenceState.SUPERSEDED
    assert realtime_v1.state == ReferenceState.SUPERSEDED


def test_approve_prequalification_version_refuses_non_draft_state() -> None:
    ws, user = _make_workspace("apv-terminal@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity)
    _make_prequalification_provenance(version)
    services.approve_prequalification_version(version, approver=user)

    # Now supersede via a new version.
    v2 = _make_draft_version(identity, revision=2)
    _make_prequalification_provenance(v2)
    services.approve_prequalification_version(v2, approver=user)

    version.refresh_from_db()
    assert version.state == CharacterIdentityVersion.State.SUPERSEDED
    with pytest.raises(services.PrequalificationVersionApprovalError) as ei:
        services.approve_prequalification_version(version, approver=user)
    assert ei.value.code == "invalid_state_transition"


def test_approve_prequalification_version_and_approve_version_are_not_mode_variants() -> None:
    """§17.10.a Amendment 4 discipline: the qualified path must not
    accept a mode-flag that bypasses the floor. This test verifies
    the two services remain distinct — no mode-switching signature
    on ``approve_version``.
    """
    import inspect
    sig = inspect.signature(services.approve_version)
    # Bypass-mode-flag hints we do not want on the qualified path.
    forbidden = {
        "bypass",
        "bypass_floor",
        "skip_floor",
        "force",
        "prequalification",
        "prequalification_authored",
    }
    leak = set(sig.parameters.keys()) & forbidden
    assert not leak, (
        f"services.approve_version must not accept bypass-mode "
        f"flags; leak: {leak}. Bypass belongs on "
        f"services.approve_prequalification_version (§17.10.a "
        f"Amendment 4)."
    )


# =====================================================================
# §5.6.a state semantics — APPROVED = currently admitted, not qualified
# =====================================================================


def test_prequalification_authored_version_is_not_qualification_eligible() -> None:
    """§5.6.a — state='approved' is not shorthand for qualified. A
    prequalification-authored version reaches ``state=approved``
    (currently admitted for product use) while ``is_qualification_
    eligible`` remains False.
    """
    ws, user = _make_workspace("state-sem-prequal@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity, spec_schema_version=0)
    _make_prequalification_provenance(version)
    services.approve_prequalification_version(version, approver=user)

    version.refresh_from_db()
    assert version.state == CharacterIdentityVersion.State.APPROVED
    assert version.is_canonical_schema_validated is False
    assert version.is_qualification_eligible is False


def test_import_provenance_version_is_admitted_but_not_qualified() -> None:
    """Same semantic for legacy-imported versions."""
    ws, user = _make_workspace("state-sem-import@t")
    identity = _make_identity(ws)
    version = _make_draft_version(identity, spec_schema_version=0)
    _make_import_provenance(version)
    services.approve_prequalification_version(version, approver=user)

    version.refresh_from_db()
    assert version.state == CharacterIdentityVersion.State.APPROVED
    assert version.is_legacy_imported is True
    assert version.is_qualification_eligible is False
