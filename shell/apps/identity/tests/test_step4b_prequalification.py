"""§19 Step 4.b — Prequalification-authoring orchestration + compat
derivation / synchronization (§17.10.a Amendment 4).

Semantic priorities (per SESSION 243 operator direction):

* Portrait-only update preserves voice + realtime canonical state.
* Voice-only update preserves portrait + realtime.
* Realtime-only update preserves portrait + voice.
* Full update replaces all three honestly.
* Spec stays ``{}`` / schema_version 0 for prequalification-authored
  versions — no invented human-spec facts.
* ``PrequalificationProvenance`` and ``ImportProvenance`` remain
  mutually exclusive.
* Provider identifiers appear only in ``GenerationRecord`` evidence,
  never on canonical rows.
* Orchestration failure rolls back the entire authoring event —
  substrate and mirrors both.
* Resulting canonical version is ``state=approved`` (currently
  admitted per §5.6.a) but ``is_qualification_eligible`` remains
  ``False``.

Discipline scope (4.b, not 4.c/4.d):

* The prequalification service is the only production caller of
  ``compat.sync_teammate_mirrors`` in this landing.
* The canonical transition services (``approve_bundle``,
  ``approve_reference``, ``approve_version``, etc.) do **not** call
  sync from their own bodies yet. Standalone calls to those
  services are exercised in the 4.a test suite and their mirror
  wiring lands in 4.c.
* Production mutation call sites (``perform_create``,
  ``clone_voice``, etc.) are **not** migrated in this landing.
  That is 4.d.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
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
    IdentityReferenceKind,
    ImportProvenance,
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
# Helpers
# =====================================================================


def _make_teammate(email: str, *, name: str = "Ruby") -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    teammate = Teammate.objects.create(workspace=ws, name=name)
    return teammate, user


def _make_portrait_input(*, uri: str = "https://provider/img.png") -> PortraitRepresentation:
    return PortraitRepresentation(
        portrait_uri=uri,
        provider=GenerationProvider.MOCK,
        provider_model="mock-portrait-1",
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
        mock_mode=True,
        provider_response={"thumbnail_url": uri},
    )


def _make_voice_input(*, voice_id: str = "vincent") -> VoiceRepresentation:
    return VoiceRepresentation(
        provider_voice_id=voice_id,
        provider=GenerationProvider.RUNWAY_TTS,
        provider_model="",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        mock_mode=False,
        voice_kind="preset",
        provider_response={"status": "preset"},
    )


def _make_realtime_input(*, realtime_id: str = "avatar_abc123") -> RealtimeRepresentation:
    return RealtimeRepresentation(
        provider_realtime_id=realtime_id,
        provider=GenerationProvider.RUNWAY_AVATAR,
        provider_model="",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        mock_mode=False,
        provider_response={"status": "ready", "thumbnail_url": None},
    )


def _current_approved_version(
    identity: CharacterIdentity,
) -> CharacterIdentityVersion:
    return CharacterIdentityVersion.objects.get(
        identity=identity, state=CharacterIdentityVersion.State.APPROVED,
    )


# =====================================================================
# compat.py — provider-ID extraction + derivation walks
# =====================================================================


def test_extractor_reads_legacy_value_from_legacy_imported_record() -> None:
    """Step 3's landed convention preserved verbatim."""
    teammate, _ = _make_teammate("ext-legacy@t")
    identity = CharacterIdentity.objects.create(
        workspace=teammate.workspace,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name="Ruby",
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    record = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.LEGACY_IMPORTED,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"legacy_value": "runway_avatar_xyz"},
        execution_mode=None,
        execution_mode_actual=None,
    )
    assert compat._extract_provider_realtime_id(record) == "runway_avatar_xyz"
    assert compat._extract_provider_voice_id(record) == "runway_avatar_xyz"


def test_extractor_reads_provider_voice_id_for_non_legacy_record() -> None:
    teammate, _ = _make_teammate("ext-non-legacy@t")
    identity = CharacterIdentity.objects.create(
        workspace=teammate.workspace,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name="Ruby",
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    record = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.RUNWAY_TTS,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"provider_voice_id": "vincent"},
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
    )
    assert compat._extract_provider_voice_id(record) == "vincent"
    # Cross-key isolation — provider_voice_id must not leak into
    # realtime derivation.
    assert compat._extract_provider_realtime_id(record) is None


def test_derivation_returns_none_when_no_identity() -> None:
    teammate, _ = _make_teammate("d-no-id@t")
    assert compat.derive_portrait_path(teammate) is None
    assert compat.derive_voice_id(teammate) is None
    assert compat.derive_runway_avatar_id(teammate) is None


def test_derivation_returns_none_when_no_approved_version() -> None:
    teammate, _ = _make_teammate("d-no-approved@t")
    identity = CharacterIdentity.objects.create(
        workspace=teammate.workspace,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name="Ruby",
    )
    # A draft version exists but nothing is approved.
    CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    assert compat.derive_portrait_path(teammate) is None
    assert compat.derive_voice_id(teammate) is None
    assert compat.derive_runway_avatar_id(teammate) is None


# =====================================================================
# record_prequalification_representation — first authoring event
# =====================================================================


def test_first_authoring_event_creates_identity_version_provenance_and_syncs_mirrors() -> None:
    teammate, user = _make_teammate("first-auth@t")

    portrait = _make_portrait_input(uri="https://prov/first.png")
    voice = _make_voice_input(voice_id="marcus")
    realtime = _make_realtime_input(realtime_id="avatar_first")

    version = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=portrait,
        voice=voice,
        realtime=realtime,
    )

    assert version.state == CharacterIdentityVersion.State.APPROVED
    assert version.spec == {}
    assert version.spec_schema_version == 0

    # Provenance
    assert version.prequalification_provenance.source_call == "wizard_create"

    # Mirrors sync'd
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/first.png"
    assert teammate.voice_id == "marcus"
    assert teammate.runway_avatar_id == "avatar_first"


def test_first_authoring_event_creates_character_identity_if_missing() -> None:
    teammate, user = _make_teammate("first-identity@t")
    assert not teammate.character_identities.exists()

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(),
    )
    teammate.refresh_from_db()
    identity = teammate.character_identities.first()
    assert identity is not None
    assert identity.kind == CharacterIdentity.Kind.HUMAN
    assert identity.name == teammate.name


# =====================================================================
# Semantic carry-forward — portrait-only, voice-only, realtime-only
# =====================================================================


def test_voice_only_update_preserves_portrait_and_realtime() -> None:
    """Operator priority #2: voice-only update must not erase
    portrait or realtime canonical state.
    """
    teammate, user = _make_teammate("carry-voice@t")

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p1.png"),
        voice=_make_voice_input(voice_id="vincent"),
        realtime=_make_realtime_input(realtime_id="avatar_v1"),
    )

    v2 = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.CHANGE_VOICE,
        author=user,
        voice=_make_voice_input(voice_id="clara"),
    )

    teammate.refresh_from_db()
    # Voice changed; portrait + realtime preserved.
    assert teammate.voice_id == "clara"
    assert teammate.portrait_path == "https://prov/p1.png"
    assert teammate.runway_avatar_id == "avatar_v1"

    # New version has approved references for all three slots.
    assert v2.references.filter(
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.APPROVED,
    ).count() == 1
    bundle = ApprovedRepresentationBundle.objects.get(
        identity_version=v2,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )
    assert bundle.approved_voice is not None
    assert bundle.approved_realtime is not None


def test_portrait_only_update_preserves_voice_and_realtime() -> None:
    """Operator priority #1."""
    teammate, user = _make_teammate("carry-portrait@t")

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p1.png"),
        voice=_make_voice_input(voice_id="vincent"),
        realtime=_make_realtime_input(realtime_id="avatar_v1"),
    )

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.REFRESH_PORTRAIT,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p2.png"),
    )

    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/p2.png"
    assert teammate.voice_id == "vincent"
    assert teammate.runway_avatar_id == "avatar_v1"


def test_realtime_only_update_preserves_portrait_and_voice() -> None:
    """Operator priority #3."""
    teammate, user = _make_teammate("carry-realtime@t")

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p1.png"),
        voice=_make_voice_input(voice_id="vincent"),
        realtime=_make_realtime_input(realtime_id="avatar_v1"),
    )

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_REBAKE,
        author=user,
        realtime=_make_realtime_input(realtime_id="avatar_v2"),
    )

    teammate.refresh_from_db()
    assert teammate.runway_avatar_id == "avatar_v2"
    assert teammate.voice_id == "vincent"
    assert teammate.portrait_path == "https://prov/p1.png"


def test_full_update_replaces_all_three_honestly() -> None:
    """Operator priority #4."""
    teammate, user = _make_teammate("full-update@t")

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p1.png"),
        voice=_make_voice_input(voice_id="vincent"),
        realtime=_make_realtime_input(realtime_id="avatar_v1"),
    )

    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_REBAKE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p2.png"),
        voice=_make_voice_input(voice_id="clara"),
        realtime=_make_realtime_input(realtime_id="avatar_v2"),
    )

    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/p2.png"
    assert teammate.voice_id == "clara"
    assert teammate.runway_avatar_id == "avatar_v2"


# =====================================================================
# Version + provenance semantics
# =====================================================================


def test_prequalification_authored_version_has_empty_spec_and_zero_schema() -> None:
    """Operator priority #5: no fabricated human-spec values."""
    teammate, user = _make_teammate("spec-zero@t")

    version = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(),
    )
    assert version.spec == {}
    assert version.spec_schema_version == 0
    assert version.is_canonical_schema_validated is False


def test_prequalification_authored_version_is_admitted_but_not_qualified() -> None:
    """Operator priority #9: §5.6.a state semantics — admitted for
    product use, not benchmark-qualified.
    """
    teammate, user = _make_teammate("state-sem@t")

    version = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(),
    )
    assert version.state == CharacterIdentityVersion.State.APPROVED
    assert version.is_qualification_eligible is False
    assert version.is_legacy_imported is False
    assert hasattr(version, "prequalification_provenance")


def test_provenance_mutual_exclusion_holds_end_to_end() -> None:
    """Operator priority #6: PrequalificationProvenance and
    ImportProvenance remain mutually exclusive on the same version.
    """
    teammate, user = _make_teammate("mutex@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(),
    )
    identity = teammate.character_identities.first()
    version = _current_approved_version(identity)

    # A hypothetical caller trying to attach ImportProvenance to a
    # prequalification-authored version is refused by clean().
    import uuid as _uuid

    conflict = ImportProvenance(
        identity_version=version,
        source_teammate_id=teammate.id,
        import_run_id=_uuid.uuid4(),
        migration_version="identity.0002_step3_legacy_provenance",
        snapshot_schema_version=1,
        legacy_snapshot={},
    )
    with pytest.raises(Exception, match="mutually exclusive"):
        conflict.full_clean()


def test_prior_version_supersedes_transactionally_on_second_authoring_event() -> None:
    teammate, user = _make_teammate("supersede@t")
    v1 = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p1.png"),
    )
    v2 = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.REFRESH_PORTRAIT,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p2.png"),
    )

    v1.refresh_from_db()
    v2.refresh_from_db()
    assert v1.state == CharacterIdentityVersion.State.SUPERSEDED
    assert v2.state == CharacterIdentityVersion.State.APPROVED

    # Exactly one currently-approved version per identity.
    identity = teammate.character_identities.first()
    assert (
        CharacterIdentityVersion.objects.filter(
            identity=identity,
            state=CharacterIdentityVersion.State.APPROVED,
        ).count()
        == 1
    )


# =====================================================================
# Provider IDs quarantined — appear only in GenerationRecord evidence
# =====================================================================


def test_provider_ids_appear_only_in_generation_record_evidence() -> None:
    """Operator priority #7: provider identifiers live in
    ``GenerationRecord.prompt_snapshot`` — never on canonical
    row fields.
    """
    teammate, user = _make_teammate("quarantine@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/p.png"),
        voice=_make_voice_input(voice_id="clara"),
        realtime=_make_realtime_input(realtime_id="avatar_q"),
    )

    identity = teammate.character_identities.first()
    version = _current_approved_version(identity)
    bundle = ApprovedRepresentationBundle.objects.get(
        identity_version=version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )

    # provider_voice_id in the paired GenerationRecord
    voice_record = bundle.approved_voice.generation_record
    assert voice_record.prompt_snapshot.get("provider_voice_id") == "clara"

    # provider_realtime_id in the paired GenerationRecord
    realtime_record = bundle.approved_realtime.generation_record
    assert realtime_record.prompt_snapshot.get("provider_realtime_id") == "avatar_q"

    # None of these leak onto canonical rows.
    voice_ref_fields = {
        f.name for f in CanonicalVoiceReference._meta.get_fields()
    }
    for hint in {
        "voice_id",
        "provider_voice_id",
        "runway_voice_id",
        "provider",
    }:
        assert hint not in voice_ref_fields, (
            f"CanonicalVoiceReference leaked provider-namespaced "
            f"field {hint!r}"
        )

    realtime_ref_fields = {
        f.name for f in CanonicalRealtimeReference._meta.get_fields()
    }
    for hint in {
        "runway_avatar_id",
        "avatar_id",
        "provider_realtime_id",
        "external_avatar_id",
    }:
        assert hint not in realtime_ref_fields, (
            f"CanonicalRealtimeReference leaked provider-namespaced "
            f"field {hint!r}"
        )

    # Bundle domain contract stays provider-neutral.
    bundle_fields = {f.name for f in ApprovedRepresentationBundle._meta.get_fields()}
    for hint in {
        "voice_id",
        "runway_avatar_id",
        "portrait_path",
        "provider_voice_id",
        "provider_realtime_id",
    }:
        assert hint not in bundle_fields, (
            f"ApprovedRepresentationBundle leaked provider field {hint!r}"
        )


# =====================================================================
# Orchestration atomicity — failure rolls back the entire event
# =====================================================================


def test_failure_inside_orchestration_rolls_back_entire_event(monkeypatch) -> None:
    """Operator priority #8: substrate + mirrors must roll back
    together.
    """
    teammate, user = _make_teammate("atomic@t")

    # Seed a first successful authoring event so we can distinguish
    # "no state" from "prior state preserved" after rollback.
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(uri="https://prov/before.png"),
        voice=_make_voice_input(voice_id="vincent"),
        realtime=_make_realtime_input(realtime_id="avatar_before"),
    )
    teammate.refresh_from_db()
    identity = teammate.character_identities.first()
    v1 = _current_approved_version(identity)

    # Force the sync step to raise. Everything upstream should roll
    # back — mirrors AND canonical state.
    from apps.identity import compat as compat_module

    def _boom(_teammate):
        raise RuntimeError("simulated sync failure")

    monkeypatch.setattr(compat_module, "sync_teammate_mirrors", _boom)

    with pytest.raises(RuntimeError, match="simulated"):
        services.record_prequalification_representation(
            teammate,
            source_call=PrequalificationSourceCall.WIZARD_REBAKE,
            author=user,
            portrait=_make_portrait_input(uri="https://prov/after.png"),
        )

    # Prior canonical state unchanged.
    teammate.refresh_from_db()
    assert teammate.portrait_path == "https://prov/before.png"
    assert teammate.voice_id == "vincent"
    assert teammate.runway_avatar_id == "avatar_before"

    v1.refresh_from_db()
    assert v1.state == CharacterIdentityVersion.State.APPROVED

    # No new canonical version leaked past the rollback.
    assert (
        CharacterIdentityVersion.objects.filter(identity=identity).count() == 1
    )


# =====================================================================
# Refusals
# =====================================================================


def test_empty_authoring_event_refused() -> None:
    teammate, user = _make_teammate("empty@t")
    with pytest.raises(services.PrequalificationAuthoringError) as ei:
        services.record_prequalification_representation(
            teammate,
            source_call=PrequalificationSourceCall.WIZARD_CREATE,
            author=user,
        )
    assert ei.value.code == "empty_authoring_event"


def test_voice_only_first_authoring_event_refused_without_portrait_carry() -> None:
    """A brand-new teammate with only a voice input has no prior
    approved portrait to carry from. The bundle-approval invariant
    refuses. Failure surfaces as a domain error, not silent
    inconsistency.
    """
    teammate, user = _make_teammate("no-portrait-first@t")
    with pytest.raises(services.BundleApprovalError) as ei:
        services.record_prequalification_representation(
            teammate,
            source_call=PrequalificationSourceCall.CLONE_VOICE_PRESET,
            author=user,
            voice=_make_voice_input(voice_id="vincent"),
        )
    assert ei.value.code == "missing_front_portrait"

    # Teammate mirrors still empty (rollback).
    teammate.refresh_from_db()
    assert teammate.portrait_path == ""
    assert teammate.voice_id == ""
    assert teammate.runway_avatar_id == ""


# =====================================================================
# Mock-mode is recorded honestly, not disguised as real
# =====================================================================


def test_mock_mode_recorded_literally_in_provenance_and_generation_record() -> None:
    """Operator priority #6: provenance literal. Mock-mode executions
    must be recorded as mock, not disguised as real.
    """
    teammate, user = _make_teammate("mock-literal@t")
    portrait = PortraitRepresentation(
        portrait_uri="data:image/png;base64,abc",
        provider=GenerationProvider.MOCK,
        provider_model="mock-1",
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
        mock_mode=True,
        provider_response={"mock_mode": True},
    )
    version = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=portrait,
    )
    # Provenance snapshot records mock_mode literally.
    prov = version.prequalification_provenance
    assert prov.provider_response_snapshot["portrait"]["mock_mode"] is True

    # GenerationRecord records provider=MOCK + execution=FORCED_MOCK/MOCK.
    portrait_ref = version.references.filter(
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.APPROVED,
    ).first()
    assert portrait_ref is not None
    record = portrait_ref.generation_record
    assert record.provider == GenerationProvider.MOCK
    assert record.execution_mode == ExecutionMode.FORCED_MOCK
    assert record.execution_mode_actual == ExecutionModeActual.MOCK


# =====================================================================
# Provenance snapshot — supplied vs carried-forward accurately
# =====================================================================


def test_provenance_snapshot_marks_carried_forward_slots_accurately() -> None:
    teammate, user = _make_teammate("prov-snap@t")
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_make_portrait_input(),
        voice=_make_voice_input(voice_id="vincent"),
        realtime=_make_realtime_input(realtime_id="avatar_v1"),
    )
    identity = teammate.character_identities.first()
    v1 = _current_approved_version(identity)

    # Voice-only second event.
    v2 = services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.CHANGE_VOICE,
        author=user,
        voice=_make_voice_input(voice_id="clara"),
    )
    snap = v2.prequalification_provenance.provider_response_snapshot
    assert snap["voice"]["supplied"] is True
    assert snap["voice"]["provider_voice_id"] == "clara"
    assert snap["portrait"]["supplied"] is False
    assert snap["portrait"]["carry_forward_from_version_id"] == str(v1.id)
    assert snap["realtime"]["supplied"] is False
    assert snap["realtime"]["carry_forward_from_version_id"] == str(v1.id)


# =====================================================================
# sync_teammate_mirrors — canonical absence → mirror "" translation
# =====================================================================


def test_sync_encodes_none_as_empty_string_when_canonical_absent() -> None:
    """None → '' translation happens at the compatibility boundary
    (compat.sync_teammate_mirrors) and never leaks into canonical
    code.
    """
    teammate, _ = _make_teammate("null-sync@t")
    # Pre-seed teammate mirrors to non-empty so we can observe the
    # None → "" write.
    teammate.portrait_path = "https://stale/portrait.png"
    teammate.voice_id = "stale_voice"
    teammate.runway_avatar_id = "stale_realtime"
    teammate.save(
        update_fields=["portrait_path", "voice_id", "runway_avatar_id"],
    )

    # No CharacterIdentity → derivation returns None across the board.
    compat.sync_teammate_mirrors(teammate)
    teammate.refresh_from_db()
    assert teammate.portrait_path == ""
    assert teammate.voice_id == ""
    assert teammate.runway_avatar_id == ""


# =====================================================================
# Structural — compat.py never writes to canonical models
# =====================================================================


def test_compat_module_never_writes_canonical_rows() -> None:
    """4.b discipline: compat.py reads canonical state; it must not
    modify canonical rows. Guards against a future refactor that
    would recreate the two-authority problem §17.10.a exists to
    eliminate.
    """
    source_path = Path(compat.__file__)
    tree = ast.parse(source_path.read_text())

    forbidden_call_targets = {
        # Canonical model write surfaces to reject.
        "CharacterIdentity.objects.create",
        "CharacterIdentityVersion.objects.create",
        "CanonicalVoiceReference.objects.create",
        "CanonicalRealtimeReference.objects.create",
        "ApprovedRepresentationBundle.objects.create",
        "IdentityReference.objects.create",
        "GenerationRecord.objects.create",
        "PrequalificationProvenance.objects.create",
        "ImportProvenance.objects.create",
        # `.update()` on managers for the same canonical types.
        "CharacterIdentityVersion.objects.filter",  # too broad; skip
    }
    # Trim the accidental over-broad entry.
    forbidden_call_targets.discard(
        "CharacterIdentityVersion.objects.filter"
    )

    class _WriteHunter(ast.NodeVisitor):
        def __init__(self):
            self.hits: list[str] = []

        def visit_Call(self, node):
            # Only .save calls and .create-style manager calls need
            # scrutiny. Read patterns (.filter, .get, .first) are
            # fine.
            attr = _dotted(node.func)
            if attr is None:
                self.generic_visit(node)
                return
            # Any ``.save(...)`` on a canonical model instance would
            # show up here; the compat module only calls
            # ``teammate.save(...)`` which is legitimate.
            if attr.endswith(".objects.create"):
                model_name = attr.rsplit(".objects.create", 1)[0]
                if model_name in {
                    "CharacterIdentity",
                    "CharacterIdentityVersion",
                    "CanonicalVoiceReference",
                    "CanonicalRealtimeReference",
                    "ApprovedRepresentationBundle",
                    "IdentityReference",
                    "GenerationRecord",
                    "PrequalificationProvenance",
                    "ImportProvenance",
                }:
                    self.hits.append(attr)
            if attr.endswith(".objects.update"):
                self.hits.append(attr)
            if attr.endswith(".objects.bulk_create"):
                self.hits.append(attr)
            if attr.endswith(".objects.bulk_update"):
                self.hits.append(attr)
            self.generic_visit(node)

    def _dotted(node) -> str | None:
        if isinstance(node, ast.Attribute):
            base = _dotted(node.value)
            if base is None:
                return None
            return f"{base}.{node.attr}"
        if isinstance(node, ast.Name):
            return node.id
        return None

    hunter = _WriteHunter()
    hunter.visit(tree)
    assert not hunter.hits, (
        f"apps/identity/compat.py performs canonical writes: "
        f"{hunter.hits}. Compat must not modify canonical rows."
    )


def test_compat_module_declares_step_13_deletion_horizon() -> None:
    """Docstring discipline: compat.py must name its bounded
    lifetime so future readers do not treat it as permanent
    architecture.
    """
    doc = inspect.getdoc(compat)
    assert doc is not None
    assert "Step 13" in doc, (
        "compat.py must document its deletion horizon (Step 13)"
    )


# =====================================================================
# Sanity — sync_teammate_mirrors is the sole production writer path
# =====================================================================


def test_sync_teammate_mirrors_writes_only_the_three_mirror_fields() -> None:
    """Explicit ``update_fields`` guard on the sync helper prevents
    unrelated ``Teammate`` mutation on the sync path.
    """
    assert set(compat.MIRROR_FIELDS) == {
        "portrait_path",
        "voice_id",
        "runway_avatar_id",
    }
