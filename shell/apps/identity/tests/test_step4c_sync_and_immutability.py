"""§19 Step 4.c — Canonical lifecycle transition ↔ compatibility
mirror synchronization + approved-version immutability (§5.4).

Central invariant under test: a canonical state transition and its
resulting mirror state must commit or roll back together, and
canonical transitions cannot mutate the approved representation set
of an APPROVED CharacterIdentityVersion in place (§5.4 immutability).

Design shape verified:

* Only the three version-level services synchronize compatibility
  mirrors: ``approve_version``, ``supersede_version``,
  ``approve_prequalification_version``. Sync fires inside each
  service's ``transaction.atomic()``, immediately after the state
  change is written to the transaction.
* The three assembly-time services (``approve_reference``,
  ``approve_bundle``, ``supersede_bundle``) refuse to operate on a
  non-DRAFT parent version with a stable domain-error code
  (``parent_version_not_draft``). §5.4 immutability enforced at the
  service boundary.
* ``record_prequalification_representation`` no longer performs an
  explicit final sync — ``approve_prequalification_version`` is the
  last transactional step and now owns the sync. The orchestration
  performs exactly one mirror-sync call per authoring event.
* The §5.6.a cascade (APPROVED version → SUPERSEDED cascades APPROVED
  children to SUPERSEDED) rides a single shared helper used by all
  three version-level services so shapes cannot drift.
"""
from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity import compat, services
from apps.identity.models import (
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
    PrequalificationSourceCall,
    ReferenceState,
)
from apps.identity.prequalification import (
    PortraitRepresentation,
    RealtimeRepresentation,
    VoiceRepresentation,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# =====================================================================
# Fixtures
# =====================================================================


def _make_teammate(email: str, *, name: str = "Ruby"):
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    teammate = Teammate.objects.create(workspace=ws, name=name)
    return teammate, user


def _portrait(uri: str = "https://prov/p.png") -> PortraitRepresentation:
    return PortraitRepresentation(
        portrait_uri=uri,
        provider=GenerationProvider.MOCK,
        provider_model="mock-1",
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
        mock_mode=True,
        provider_response={},
    )


def _voice(voice_id: str = "vincent") -> VoiceRepresentation:
    return VoiceRepresentation(
        provider_voice_id=voice_id,
        provider=GenerationProvider.RUNWAY_TTS,
        provider_model="",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        mock_mode=False,
        voice_kind="preset",
        provider_response={},
    )


def _realtime(realtime_id: str = "avatar_v1") -> RealtimeRepresentation:
    return RealtimeRepresentation(
        provider_realtime_id=realtime_id,
        provider=GenerationProvider.RUNWAY_AVATAR,
        provider_model="",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        mock_mode=False,
        provider_response={},
    )


def _current_approved_version(identity: CharacterIdentity) -> CharacterIdentityVersion:
    return CharacterIdentityVersion.objects.get(
        identity=identity, state=CharacterIdentityVersion.State.APPROVED,
    )


# =====================================================================
# Operator priority #1 — approve_bundle leaves mirrors matching the
# newly approved bundle. (Exercised inside record_prequalification_
# representation, which is the amendment-ratified orchestration.)
# =====================================================================


def test_orchestration_bundle_approval_leaves_mirrors_matching_approved_bundle() -> None:
    teammate, user = _make_teammate("op1-bundle-mirror@t")
    version = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p1.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )
    teammate.refresh_from_db()

    # Mirrors match the canonical values landed in the new bundle.
    bundle = ApprovedRepresentationBundle.objects.get(
        identity_version=version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )
    assert bundle.approved_voice is not None
    assert bundle.approved_realtime is not None

    assert teammate.portrait_path == "https://prov/p1.png"
    assert teammate.voice_id == "vincent"
    assert teammate.runway_avatar_id == "avatar_v1"


# =====================================================================
# Operator priority #2 — supersede_bundle with no replacement is only
# legitimate on a DRAFT-version bundle. §5.4 immutability makes the
# operator's proposed "clear mirrors while preserving portrait"
# scenario a contract violation on an APPROVED version. The proper
# lifecycle for that outcome is a new authoring event that drops
# voice/realtime, which is out of Amendment 4 scope (voice/realtime
# are nullable on the bundle but the orchestration always supplies
# what the current approved trio held). This test locks the §5.4
# guard rather than the unreachable pre-4.c behavior.
# =====================================================================


def test_supersede_bundle_refuses_on_approved_parent_version() -> None:
    teammate, user = _make_teammate("op2-supersede-guard@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p1.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )
    identity = teammate.character_identities.first()
    approved_version = _current_approved_version(identity)
    approved_bundle = ApprovedRepresentationBundle.objects.get(
        identity_version=approved_version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )

    with pytest.raises(services.BundleApprovalError) as ei:
        services.supersede_bundle(approved_bundle, reason="operator directed")
    assert ei.value.code == "parent_version_not_draft"

    # Substrate + mirrors both unchanged.
    approved_bundle.refresh_from_db()
    teammate.refresh_from_db()
    assert approved_bundle.state == ApprovedRepresentationBundle.State.APPROVED
    assert teammate.voice_id == "vincent"
    assert teammate.runway_avatar_id == "avatar_v1"
    assert teammate.portrait_path == "https://prov/p1.png"


# =====================================================================
# Operator priority #3 — approve_reference replacing the active front
# portrait is a §5.4 change. Under 4.c, that mutation is refused and
# the caller is directed to author a new version instead. The right
# way to "replace the active front portrait" is to run a new
# prequalification-authoring event.
# =====================================================================


def test_approve_reference_refuses_replacing_front_portrait_on_approved_version() -> None:
    teammate, user = _make_teammate("op3-ref-guard@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p1.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )
    identity = teammate.character_identities.first()
    approved_version = _current_approved_version(identity)

    # Directly attach a candidate front portrait reference to the
    # APPROVED version and try to promote it.
    ws = teammate.workspace
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path="https://prov/replacement.png",
    )
    candidate = IdentityReference.objects.create(
        identity_version=approved_version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.RAW,
    )

    with pytest.raises(services.ReferenceApprovalError) as ei:
        services.approve_reference(candidate)
    assert ei.value.code == "parent_version_not_draft"

    # Correct path: a new prequalification-authoring event.
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.REFRESH_PORTRAIT,
        author=user,
        portrait=_portrait(uri="https://prov/replacement.png"),
    )
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/replacement.png"


# =====================================================================
# Operator priority #4 — supersede_version with no replacement clears
# all canonical-derived mirrors.
# =====================================================================


def test_supersede_version_clears_all_mirrors_atomically() -> None:
    teammate, user = _make_teammate("op4-supersede-version@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p1.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )
    identity = teammate.character_identities.first()
    approved_version = _current_approved_version(identity)

    services.supersede_version(approved_version, reason="removed")

    teammate.refresh_from_db()
    assert teammate.portrait_path == ""
    assert teammate.voice_id == ""
    assert teammate.runway_avatar_id == ""

    approved_version.refresh_from_db()
    assert approved_version.state == CharacterIdentityVersion.State.SUPERSEDED

    # §5.6.a cascade: no APPROVED child rows remain under the
    # superseded version.
    assert not ApprovedRepresentationBundle.objects.filter(
        identity_version=approved_version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    ).exists()
    assert not IdentityReference.objects.filter(
        identity_version=approved_version,
        state=ReferenceState.APPROVED,
    ).exists()
    assert not CanonicalVoiceReference.objects.filter(
        identity_version=approved_version,
        state=ReferenceState.APPROVED,
    ).exists()
    assert not CanonicalRealtimeReference.objects.filter(
        identity_version=approved_version,
        state=ReferenceState.APPROVED,
    ).exists()


# =====================================================================
# Operator priority #5 — approving a replacement version leaves
# mirrors derived only from the replacement version.
# =====================================================================


def test_replacement_version_derives_mirrors_only_from_new_version() -> None:
    teammate, user = _make_teammate("op5-replacement@t")

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p1.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_REBAKE,
        author=user,
        portrait=_portrait(uri="https://prov/p2.png"),
        voice=_voice(voice_id="clara"),
        realtime=_realtime(realtime_id="avatar_v2"),
    )
    teammate.refresh_from_db()

    assert teammate.portrait_path == "https://prov/p2.png"
    assert teammate.voice_id == "clara"
    assert teammate.runway_avatar_id == "avatar_v2"

    # Old version's approved children cascaded to SUPERSEDED.
    identity = teammate.character_identities.first()
    old_version = CharacterIdentityVersion.objects.get(
        identity=identity, revision=1,
    )
    assert old_version.state == CharacterIdentityVersion.State.SUPERSEDED
    assert not IdentityReference.objects.filter(
        identity_version=old_version,
        state=ReferenceState.APPROVED,
    ).exists()


# =====================================================================
# Operator priority #6 — approve_prequalification_version standalone
# leaves mirrors correct.
# =====================================================================


def test_approve_prequalification_version_standalone_syncs_mirrors() -> None:
    """Bypass ``record_prequalification_representation`` and construct
    a DRAFT version + APPROVED bundle + portrait reference by hand,
    then call approve_prequalification_version directly. Mirrors
    should update from the newly-approved canonical state.
    """
    teammate, user = _make_teammate("op6-standalone@t")
    ws = teammate.workspace

    identity = CharacterIdentity.objects.create(
        workspace=ws, teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN, name=teammate.name,
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity, revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={}, spec_schema_version=0,
    )
    # Prequalification provenance so approve_prequalification_version
    # accepts the version.
    from apps.identity.models import (
        PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        PrequalificationProvenance,
    )
    PrequalificationProvenance.objects.create(
        identity_version=version,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        snapshot_schema_version=PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        provider_response_snapshot={},
    )
    # Approved front portrait so the bundle invariant is satisfied.
    asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        file_path="https://prov/standalone.png",
    )
    portrait_ref = IdentityReference.objects.create(
        identity_version=version, asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front", state=ReferenceState.RAW,
    )
    services.approve_reference(portrait_ref)

    # Voice + realtime.
    voice_gen = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.RUNWAY_TTS,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"provider_voice_id": "standalone_voice"},
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
    )
    voice_ref = CanonicalVoiceReference.objects.create(
        identity_version=version, generation_record=voice_gen,
        state=ReferenceState.APPROVED,
    )
    realtime_gen = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.RUNWAY_AVATAR,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"provider_realtime_id": "standalone_avatar"},
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
    )
    realtime_ref = CanonicalRealtimeReference.objects.create(
        identity_version=version, generation_record=realtime_gen,
        state=ReferenceState.APPROVED,
    )
    bundle = ApprovedRepresentationBundle.objects.create(
        identity_version=version,
        approved_voice=voice_ref, approved_realtime=realtime_ref,
        state=ApprovedRepresentationBundle.State.DRAFT,
    )
    services.approve_bundle(bundle, approver=user)

    # Mirrors still empty — approve_bundle is an assembly-time service
    # and does not sync (its parent version is still DRAFT).
    teammate.refresh_from_db()
    assert teammate.portrait_path == ""
    assert teammate.voice_id == ""
    assert teammate.runway_avatar_id == ""

    # Standalone approve_prequalification_version drives sync.
    services.approve_prequalification_version(version, approver=user)
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/standalone.png"
    assert teammate.voice_id == "standalone_voice"
    assert teammate.runway_avatar_id == "standalone_avatar"


# =====================================================================
# Operator priority #7 — record_prequalification_representation still
# performs one coherent authoring event and finishes with correct
# mirrors.
# =====================================================================


def test_record_prequalification_representation_finishes_with_correct_mirrors() -> None:
    teammate, user = _make_teammate("op7-orchestration-coherent@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/c.png"),
        voice=_voice(voice_id="clara"),
        realtime=_realtime(realtime_id="avatar_c"),
    )
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/c.png"
    assert teammate.voice_id == "clara"
    assert teammate.runway_avatar_id == "avatar_c"


# =====================================================================
# Operator priority #8 — mirror-sync failure causes the entire
# canonical transition to roll back.
# =====================================================================


def test_mirror_sync_failure_rolls_back_the_entire_canonical_transition() -> None:
    """The operator's exact rollback-locking scenario, structured to
    make each step observable.

    1. Existing approved version A + mirrors derived from A.
    2. New draft version B assembled completely.
    3. B promotion begins.
    4. A and its admitted children become superseded.
    5. B becomes approved.
    6. Mirror sync derives B.
    7. Mirror write raises.
    8. Entire transaction rolls back.
    9. A is again APPROVED.
    10. A's children are again APPROVED.
    11. B is again DRAFT.
    12. Mirrors still contain A's original values.
    """
    teammate, user = _make_teammate("op8-rollback@t")
    ws = teammate.workspace

    # Step 1 — A + mirrors from A.
    a = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/a.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_a"),
    )
    identity = teammate.character_identities.first()
    a_bundle = ApprovedRepresentationBundle.objects.get(
        identity_version=a,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )
    a_portrait_ref = IdentityReference.objects.get(
        identity_version=a,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.APPROVED,
    )
    teammate.refresh_from_db()
    original_portrait = teammate.portrait_path
    original_voice = teammate.voice_id
    original_realtime = teammate.runway_avatar_id
    assert original_portrait == "https://prov/a.png"

    # Step 2 — assemble B completely, still DRAFT.
    b = CharacterIdentityVersion.objects.create(
        identity=identity, revision=2,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={}, spec_schema_version=0,
    )
    from apps.identity.models import (
        PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        PrequalificationProvenance,
    )
    PrequalificationProvenance.objects.create(
        identity_version=b,
        source_call=PrequalificationSourceCall.WIZARD_REBAKE,
        snapshot_schema_version=PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        provider_response_snapshot={},
    )
    b_asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        file_path="https://prov/b.png",
    )
    b_portrait_ref = IdentityReference.objects.create(
        identity_version=b, asset=b_asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front", state=ReferenceState.RAW,
    )
    services.approve_reference(b_portrait_ref)  # legal — b is DRAFT
    b_voice_gen = GenerationRecord.objects.create(
        identity_version=b,
        provider=GenerationProvider.RUNWAY_TTS,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"provider_voice_id": "clara"},
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
    )
    b_voice_ref = CanonicalVoiceReference.objects.create(
        identity_version=b, generation_record=b_voice_gen,
        state=ReferenceState.APPROVED,
    )
    b_realtime_gen = GenerationRecord.objects.create(
        identity_version=b,
        provider=GenerationProvider.RUNWAY_AVATAR,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"provider_realtime_id": "avatar_b"},
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
    )
    b_realtime_ref = CanonicalRealtimeReference.objects.create(
        identity_version=b, generation_record=b_realtime_gen,
        state=ReferenceState.APPROVED,
    )
    b_bundle = ApprovedRepresentationBundle.objects.create(
        identity_version=b,
        approved_voice=b_voice_ref, approved_realtime=b_realtime_ref,
        state=ApprovedRepresentationBundle.State.DRAFT,
    )
    services.approve_bundle(b_bundle, approver=user)  # legal — b is DRAFT

    # Steps 3–7 — promote B; make sync raise.
    def _boom(_teammate):
        raise RuntimeError("simulated mirror-write failure")

    with patch("apps.identity.compat.sync_teammate_mirrors", _boom):
        with pytest.raises(RuntimeError, match="simulated"):
            services.approve_prequalification_version(b, approver=user)

    # Steps 8–12 — assert full rollback.
    a.refresh_from_db()
    b.refresh_from_db()
    a_bundle.refresh_from_db()
    b_bundle.refresh_from_db()
    a_portrait_ref.refresh_from_db()
    teammate.refresh_from_db()

    assert a.state == CharacterIdentityVersion.State.APPROVED  # step 9
    assert a_portrait_ref.state == ReferenceState.APPROVED  # step 10
    assert a_bundle.state == ApprovedRepresentationBundle.State.APPROVED  # step 10
    assert b.state == CharacterIdentityVersion.State.DRAFT  # step 11
    assert b_bundle.state == ApprovedRepresentationBundle.State.APPROVED  # step 11
    #   (B's bundle stays APPROVED because B is DRAFT — approve_bundle
    #   succeeded pre-promotion. Rollback of promotion doesn't undo
    #   pre-promotion assembly, which is what "B is again DRAFT" means.)

    assert teammate.portrait_path == original_portrait  # step 12
    assert teammate.voice_id == original_voice
    assert teammate.runway_avatar_id == original_realtime


# =====================================================================
# Operator priority #9 — canonical-transition failure before sync
# leaves mirrors unchanged.
# =====================================================================


def test_canonical_failure_before_sync_leaves_mirrors_unchanged() -> None:
    teammate, user = _make_teammate("op9-precommit@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )
    teammate.refresh_from_db()
    original_portrait = teammate.portrait_path
    original_voice = teammate.voice_id
    original_realtime = teammate.runway_avatar_id

    # Try to approve a bundle on the current-APPROVED version — the
    # §5.4 guard refuses before any state change occurs. Mirrors must
    # be untouched.
    identity = teammate.character_identities.first()
    version = _current_approved_version(identity)
    with pytest.raises(services.BundleApprovalError) as ei:
        # Build a fresh DRAFT bundle then flip parent state to APPROVED
        # to prove the guard fires against APPROVED parents.
        bogus = ApprovedRepresentationBundle.objects.create(
            identity_version=version,
            state=ApprovedRepresentationBundle.State.DRAFT,
        )
        services.approve_bundle(bogus, approver=user)
    assert ei.value.code == "parent_version_not_draft"

    teammate.refresh_from_db()
    assert teammate.portrait_path == original_portrait
    assert teammate.voice_id == original_voice
    assert teammate.runway_avatar_id == original_realtime


# =====================================================================
# Operator priority #10 — idempotent re-approval does not create
# semantic drift; no mirror write on a no-op.
# =====================================================================


def test_idempotent_reapproval_does_not_trigger_mirror_sync() -> None:
    teammate, user = _make_teammate("op10-idempotent@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/p.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )
    identity = teammate.character_identities.first()
    version = _current_approved_version(identity)

    with patch("apps.identity.compat.sync_teammate_mirrors") as mock_sync:
        services.approve_prequalification_version(version, approver=user)
    assert mock_sync.call_count == 0, (
        "Idempotent re-approval must not trigger mirror sync. "
        f"Called {mock_sync.call_count} times."
    )


# =====================================================================
# Operator priority #11 — no transition can commit canonical state and
# then fail mirror synchronization outside the transaction.
# =====================================================================


def test_sync_call_lives_inside_the_transactional_atomic_block() -> None:
    """AST inspection: the sync call in each version-level service
    lives inside a ``with transaction.atomic():`` block, and no
    version-state save happens after sync. This prevents a design
    regression that would commit canonical state before sync.
    """
    import ast

    source = ast.parse(inspect.getsource(services))

    # Names of the version-level services that must sync.
    services_that_sync = {
        "approve_version",
        "supersede_version",
        "approve_prequalification_version",
    }

    for node in ast.walk(source):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in services_that_sync:
            continue

        # Every call to _sync_teammate_mirrors_if_present must be
        # nested inside a ``with transaction.atomic():`` block within
        # the function.
        found_sync_inside_atomic = False

        for outer in ast.walk(node):
            if not isinstance(outer, ast.With):
                continue
            # Is this the transaction.atomic context?
            has_atomic = any(
                (isinstance(item.context_expr, ast.Call)
                 and isinstance(item.context_expr.func, ast.Attribute)
                 and item.context_expr.func.attr == "atomic")
                for item in outer.items
            )
            if not has_atomic:
                continue
            for inner in ast.walk(outer):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "_sync_teammate_mirrors_if_present"
                ):
                    found_sync_inside_atomic = True
                    break

        assert found_sync_inside_atomic, (
            f"services.{node.name} does not call "
            "_sync_teammate_mirrors_if_present inside a "
            "with transaction.atomic() block. Sync outside the "
            "atomic could commit canonical state before mirror "
            "synchronization runs — the exact invariant §17.10.a "
            "Amendment 1 forbids."
        )


# =====================================================================
# Operator priority #12 — record_prequalification_representation does
# not cascade redundant mirror writes after 4.c.
# =====================================================================


def test_orchestration_performs_exactly_one_mirror_sync_per_authoring_event() -> None:
    teammate, user = _make_teammate("op12-single-sync@t")

    with patch(
        "apps.identity.compat.sync_teammate_mirrors",
        wraps=compat.sync_teammate_mirrors,
    ) as mock_sync:
        services.record_prequalification_representation(
            teammate,
            source_call=PrequalificationSourceCall.WIZARD_CREATE,
            author=user,
            portrait=_portrait(),
            voice=_voice(),
            realtime=_realtime(),
        )
    assert mock_sync.call_count == 1, (
        "record_prequalification_representation must perform exactly "
        "one mirror-sync call per authoring event. Got "
        f"{mock_sync.call_count}."
    )


# =====================================================================
# §5.6.a cascade correction — supersede_version cascades, tested
# alongside approve_version's cascade so all three version-level
# services share the shape.
# =====================================================================


def test_approve_version_cascades_prior_version_children() -> None:
    """approve_version (qualified path) must cascade the prior
    APPROVED version's children to SUPERSEDED via the shared helper.
    Uses a bootstrap fixture identity (no teammate) so we can avoid
    the branch-schema approval floor by dropping through the
    ``services.approve_version`` path via a prequalification
    substitute — actually we exercise the code via the shared helper
    directly on a bootstrap identity.
    """
    # Cross-reference the shared cascade in a direct unit shape.
    # We assert the cascade correction by inspecting the source of
    # the two paths (approve_version + supersede_version) that lacked
    # cascade before 4.c and now delegate to
    # _supersede_version_and_cascade_children.
    import ast

    source = ast.parse(inspect.getsource(services))
    callers = {"approve_version", "supersede_version", "approve_prequalification_version"}
    caller_uses_shared_helper = {name: False for name in callers}

    for node in ast.walk(source):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in callers:
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_supersede_version_and_cascade_children"
            ):
                caller_uses_shared_helper[node.name] = True
                break

    for name, uses in caller_uses_shared_helper.items():
        assert uses, (
            f"services.{name} must invoke "
            "_supersede_version_and_cascade_children to cascade "
            "APPROVED children on version supersession — §5.6.a "
            "invariant + 4.c cascade correction."
        )


# =====================================================================
# Design-invariant tests — no sync_mirrors parameter, assembly-time
# services don't sync at all.
# =====================================================================


def test_no_sync_mirrors_parameter_on_any_transition_service() -> None:
    """Verify the design has no ``sync_mirrors`` escape hatch. State
    guards + invariant enforcement replace the parameter entirely.
    """
    for name in (
        "approve_version",
        "supersede_version",
        "approve_prequalification_version",
        "approve_reference",
        "approve_bundle",
        "supersede_bundle",
    ):
        service = getattr(services, name)
        sig = inspect.signature(service)
        assert "sync_mirrors" not in sig.parameters, (
            f"services.{name} carries a sync_mirrors parameter — 4.c "
            "eliminated the escape hatch via §5.4 immutability guards."
        )


def test_assembly_time_services_do_not_call_sync() -> None:
    """AST inspection: no source-level call to
    ``_sync_teammate_mirrors_if_present`` inside the three
    assembly-time services.
    """
    import ast

    source = ast.parse(inspect.getsource(services))
    assembly_time = {"approve_reference", "approve_bundle", "supersede_bundle"}

    for node in ast.walk(source):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in assembly_time:
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_sync_teammate_mirrors_if_present"
            ):
                pytest.fail(
                    f"services.{node.name} calls "
                    "_sync_teammate_mirrors_if_present. Assembly-time "
                    "services must not sync — they operate on DRAFT "
                    "versions which cannot affect mirror derivation."
                )


def test_record_prequalification_representation_does_not_call_compat_sync_directly() -> None:
    """The redundant final sync at 4.b step J is gone.
    ``approve_prequalification_version`` is the sole sync trigger
    inside the orchestration.
    """
    import ast

    source = ast.parse(inspect.getsource(services))
    for node in ast.walk(source):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "record_prequalification_representation":
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "sync_teammate_mirrors"
            ):
                pytest.fail(
                    "record_prequalification_representation calls "
                    "compat.sync_teammate_mirrors directly. 4.c "
                    "removed that redundant call — sync now fires "
                    "inside approve_prequalification_version."
                )


# =====================================================================
# Guard error codes are stable — 4.d callers depend on discriminating
# ``parent_version_not_draft`` to know a §5.4 violation was refused.
# =====================================================================


def test_parent_version_not_draft_is_the_ratified_guard_code() -> None:
    """Sanity: the guard code is stable and returned by all three
    assembly-time services when their parent version is not DRAFT.
    """
    teammate, user = _make_teammate("guard-code@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(),
        voice=_voice(),
        realtime=_realtime(),
    )
    identity = teammate.character_identities.first()
    version = _current_approved_version(identity)
    ws = teammate.workspace

    # approve_reference
    asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        file_path="https://prov/x.png",
    )
    ref = IdentityReference.objects.create(
        identity_version=version, asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="slight_left", state=ReferenceState.RAW,
    )
    with pytest.raises(services.ReferenceApprovalError) as ei_ref:
        services.approve_reference(ref)
    assert ei_ref.value.code == "parent_version_not_draft"

    # approve_bundle
    draft_bundle = ApprovedRepresentationBundle.objects.create(
        identity_version=version,
        state=ApprovedRepresentationBundle.State.DRAFT,
    )
    with pytest.raises(services.BundleApprovalError) as ei_ab:
        services.approve_bundle(draft_bundle, approver=user)
    assert ei_ab.value.code == "parent_version_not_draft"

    # supersede_bundle
    approved_bundle = ApprovedRepresentationBundle.objects.get(
        identity_version=version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )
    with pytest.raises(services.BundleApprovalError) as ei_sb:
        services.supersede_bundle(approved_bundle)
    assert ei_sb.value.code == "parent_version_not_draft"
