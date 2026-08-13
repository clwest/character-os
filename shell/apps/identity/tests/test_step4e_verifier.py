"""§19 Step 4.e — Compatibility-consistency verifier.

Read-only verifier ratified by §17.10.a Amendment 4. Detects drift
between the three ``Teammate`` compatibility mirror fields and the
values derivable from the canonical substrate. Never mutates state;
never manufactures canonical state to make a comparison succeed.

Semantic coverage in this module walks the ratified taxonomy:

* Clean Step 3 legacy imports verify clean.
* Clean Step 4.d prequalification-authored teammates verify clean.
* No CharacterIdentity + blank mirrors → per-field N/A.
* No CharacterIdentity + populated mirrors → per-field drift with
  ``canonical_identity_required``.
* Approved canonical value differs from mirror → drift.
* Canonical absence + populated mirror → drift.
* Canonical absence + blank mirror → match.
* Whitespace normalization at the comparison boundary.
* Deliberate ORM bypass creates drift the verifier detects.
* Aggregate report counts + workspace filter + operational
  ``canonical_backfill_required_count`` signal.

Read-only guarantees are enforced in ``test_step4e_read_only.py``.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity import compat, services
from apps.identity.compat import (
    IdentityClass,
    MirrorReason,
    MirrorStatus,
)
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


def _seed_legacy_imported(
    teammate: Teammate,
    *,
    portrait_path: str = "https://legacy/portrait.png",
    voice_id: str = "vincent",
    runway_avatar_id: str = "avatar_legacy",
) -> CharacterIdentityVersion:
    """Hand-construct the shape ``import_service`` produces for a
    legacy-imported teammate. Bypasses ``import_service`` so tests
    can precisely control the shape.
    """
    ws = teammate.workspace
    # Set the pre-substrate mirror values first — this is what Step 3
    # would read.
    teammate.portrait_path = portrait_path
    teammate.voice_id = voice_id
    teammate.runway_avatar_id = runway_avatar_id
    teammate.save(
        update_fields=["portrait_path", "voice_id", "runway_avatar_id"],
    )

    identity = CharacterIdentity.objects.create(
        workspace=ws, teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN, name=teammate.name,
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity, revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
        spec={}, spec_schema_version=0,
        approved_at=timezone.now(),
    )
    import uuid as _uuid

    ImportProvenance.objects.create(
        identity_version=version,
        source_teammate_id=teammate.id,
        import_run_id=_uuid.uuid4(),
        migration_version="identity.0002_step3_legacy_provenance",
        snapshot_schema_version=1,
        legacy_snapshot={
            "portrait_path": portrait_path,
            "voice_id": voice_id,
            "runway_avatar_id": runway_avatar_id,
        },
    )
    # Portrait Asset + IdentityReference.
    portrait_asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE, file_path=portrait_path,
    )
    portrait_gen = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.LEGACY_IMPORTED,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"legacy_value": portrait_path},
        execution_mode=None, execution_mode_actual=None,
    )
    IdentityReference.objects.create(
        identity_version=version, asset=portrait_asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE, purpose="front",
        state=ReferenceState.APPROVED, generation_record=portrait_gen,
    )
    # Voice + realtime canonical references.
    voice_gen = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.LEGACY_IMPORTED,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"legacy_value": voice_id},
        execution_mode=None, execution_mode_actual=None,
    )
    voice_ref = CanonicalVoiceReference.objects.create(
        identity_version=version, generation_record=voice_gen,
        state=ReferenceState.APPROVED,
    )
    realtime_gen = GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.LEGACY_IMPORTED,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"legacy_value": runway_avatar_id},
        execution_mode=None, execution_mode_actual=None,
    )
    realtime_ref = CanonicalRealtimeReference.objects.create(
        identity_version=version, generation_record=realtime_gen,
        state=ReferenceState.APPROVED,
    )
    ApprovedRepresentationBundle.objects.create(
        identity_version=version,
        approved_voice=voice_ref, approved_realtime=realtime_ref,
        state=ApprovedRepresentationBundle.State.APPROVED,
        approved_at=timezone.now(),
    )
    return version


def _seed_prequalification_authored(
    teammate: Teammate, user,
) -> CharacterIdentityVersion:
    return services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(uri="https://prov/portrait.png"),
        voice=_voice(voice_id="vincent"),
        realtime=_realtime(realtime_id="avatar_v1"),
    )


# =====================================================================
# No CharacterIdentity
# =====================================================================


def test_no_identity_with_all_blank_mirrors_reports_na() -> None:
    teammate, _ = _make_teammate("no-id-blank@t")
    result = compat.verify_teammate_mirrors(teammate)

    assert result.identity_class == IdentityClass.NO_IDENTITY
    assert not result.has_drift
    assert not result.canonical_backfill_required
    for f in result.fields:
        assert f.status == MirrorStatus.NOT_APPLICABLE
        assert f.reason == MirrorReason.NO_IDENTITY_AUTHORED
        assert f.mirror_value == ""
        assert f.canonical_value is None


def test_no_identity_with_populated_portrait_reports_drift() -> None:
    teammate, _ = _make_teammate("no-id-portrait@t")
    teammate.portrait_path = "https://stale/portrait.png"
    teammate.save(update_fields=["portrait_path"])

    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.NO_IDENTITY
    assert result.portrait_path.status == MirrorStatus.DRIFT
    assert result.portrait_path.reason == MirrorReason.CANONICAL_IDENTITY_REQUIRED
    assert result.voice_id.status == MirrorStatus.NOT_APPLICABLE
    assert result.runway_avatar_id.status == MirrorStatus.NOT_APPLICABLE
    assert result.canonical_backfill_required is True


def test_no_identity_with_populated_voice_reports_drift() -> None:
    teammate, _ = _make_teammate("no-id-voice@t")
    teammate.voice_id = "vincent"
    teammate.save(update_fields=["voice_id"])

    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.NO_IDENTITY
    assert result.voice_id.status == MirrorStatus.DRIFT
    assert result.voice_id.reason == MirrorReason.CANONICAL_IDENTITY_REQUIRED
    assert result.canonical_backfill_required is True


def test_no_identity_with_populated_realtime_reports_drift() -> None:
    teammate, _ = _make_teammate("no-id-rt@t")
    teammate.runway_avatar_id = "avatar_stale"
    teammate.save(update_fields=["runway_avatar_id"])

    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.NO_IDENTITY
    assert result.runway_avatar_id.status == MirrorStatus.DRIFT
    assert result.runway_avatar_id.reason == MirrorReason.CANONICAL_IDENTITY_REQUIRED
    assert result.canonical_backfill_required is True


# =====================================================================
# Legacy-imported (Step 3) clean state
# =====================================================================


def test_legacy_imported_teammate_verifies_clean() -> None:
    teammate, _ = _make_teammate("legacy-clean@t")
    _seed_legacy_imported(
        teammate,
        portrait_path="https://legacy/p.png",
        voice_id="vincent",
        runway_avatar_id="avatar_legacy_1",
    )
    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.LEGACY_IMPORTED
    assert not result.has_drift
    for f in result.fields:
        assert f.status == MirrorStatus.MATCH
        assert f.reason == MirrorReason.MATCH


# =====================================================================
# Prequalification-authored (Step 4.b/4.d) clean state
# =====================================================================


def test_prequalification_authored_teammate_verifies_clean() -> None:
    teammate, user = _make_teammate("prequal-clean@t")
    _seed_prequalification_authored(teammate, user)
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.PREQUALIFICATION_AUTHORED
    assert not result.has_drift
    for f in result.fields:
        assert f.status == MirrorStatus.MATCH


# =====================================================================
# Canonical vs mirror mismatches — every drift class
# =====================================================================


def test_canonical_portrait_differs_from_mirror_reports_value_mismatch() -> None:
    teammate, user = _make_teammate("mismatch-portrait@t")
    _seed_prequalification_authored(teammate, user)
    teammate.refresh_from_db()

    # ORM-bypass drift injection.
    Teammate.objects.filter(pk=teammate.pk).update(
        portrait_path="https://stale/wrong.png",
    )
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    assert result.portrait_path.status == MirrorStatus.DRIFT
    assert result.portrait_path.reason == MirrorReason.VALUE_MISMATCH
    # Canonical still wins conceptually; verifier reports the true
    # canonical value, not the stale mirror.
    assert result.portrait_path.canonical_value == "https://prov/portrait.png"
    assert result.portrait_path.mirror_value == "https://stale/wrong.png"


def test_canonical_voice_differs_from_mirror_reports_value_mismatch() -> None:
    teammate, user = _make_teammate("mismatch-voice@t")
    _seed_prequalification_authored(teammate, user)
    Teammate.objects.filter(pk=teammate.pk).update(voice_id="wrong_voice")
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    assert result.voice_id.status == MirrorStatus.DRIFT
    assert result.voice_id.reason == MirrorReason.VALUE_MISMATCH


def test_canonical_realtime_differs_from_mirror_reports_value_mismatch() -> None:
    teammate, user = _make_teammate("mismatch-rt@t")
    _seed_prequalification_authored(teammate, user)
    Teammate.objects.filter(pk=teammate.pk).update(
        runway_avatar_id="wrong_realtime",
    )
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    assert result.runway_avatar_id.status == MirrorStatus.DRIFT
    assert result.runway_avatar_id.reason == MirrorReason.VALUE_MISMATCH


def test_canonical_absent_with_populated_mirror_reports_stale_drift() -> None:
    """CharacterIdentity exists with no approved version; the mirror
    should have been cleared but wasn't. Verifier catches it.
    """
    teammate, _ = _make_teammate("stale@t")
    # Identity exists but no approved version.
    CharacterIdentity.objects.create(
        workspace=teammate.workspace, teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN, name=teammate.name,
    )
    Teammate.objects.filter(pk=teammate.pk).update(
        portrait_path="https://stale/still-here.png",
    )
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.NO_APPROVED_VERSION
    assert result.portrait_path.status == MirrorStatus.DRIFT
    assert result.portrait_path.reason == MirrorReason.STALE_AFTER_CANONICAL_ABSENT
    # Voice + realtime are blank → match against canonical absence.
    assert result.voice_id.status == MirrorStatus.MATCH
    assert result.runway_avatar_id.status == MirrorStatus.MATCH


def test_canonical_absent_with_blank_mirror_reports_match() -> None:
    teammate, _ = _make_teammate("absent-blank@t")
    CharacterIdentity.objects.create(
        workspace=teammate.workspace, teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN, name=teammate.name,
    )
    result = compat.verify_teammate_mirrors(teammate)
    assert result.identity_class == IdentityClass.NO_APPROVED_VERSION
    for f in result.fields:
        assert f.status == MirrorStatus.MATCH


def test_canonical_voice_absent_with_blank_mirror_reports_match() -> None:
    """Approved version + approved portrait but no bundle
    (voice/realtime canonical values return None). Blank mirrors on
    those two fields must report match.
    """
    teammate, user = _make_teammate("voice-absent-blank@t")
    # Seed a prequal authoring with portrait only.
    services.record_prequalification_representation(
        teammate,
        source_call=PrequalificationSourceCall.WIZARD_CREATE,
        author=user,
        portrait=_portrait(),
    )
    teammate.refresh_from_db()
    # Portrait matches; voice + realtime blank on both sides.
    result = compat.verify_teammate_mirrors(teammate)
    assert result.portrait_path.status == MirrorStatus.MATCH
    assert result.voice_id.status == MirrorStatus.MATCH
    assert result.voice_id.reason == MirrorReason.MATCH
    assert result.runway_avatar_id.status == MirrorStatus.MATCH
    assert result.runway_avatar_id.reason == MirrorReason.MATCH


def test_mirror_blank_but_canonical_present_reports_drift() -> None:
    teammate, user = _make_teammate("blank-vs-present@t")
    _seed_prequalification_authored(teammate, user)
    # Blank out mirrors via ORM-bypass — canonical values still exist.
    Teammate.objects.filter(pk=teammate.pk).update(
        portrait_path="", voice_id="", runway_avatar_id="",
    )
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    for f in result.fields:
        assert f.status == MirrorStatus.DRIFT
        assert f.reason == MirrorReason.MIRROR_BLANK_BUT_CANONICAL_PRESENT


# =====================================================================
# Whitespace normalization
# =====================================================================


def test_whitespace_normalized_at_comparison_boundary() -> None:
    teammate, user = _make_teammate("ws-norm@t")
    _seed_prequalification_authored(teammate, user)
    # Add trailing whitespace via ORM bypass. Canonical is bare
    # "vincent"; mirror now has "vincent  ".
    Teammate.objects.filter(pk=teammate.pk).update(voice_id="vincent   ")
    teammate.refresh_from_db()

    result = compat.verify_teammate_mirrors(teammate)
    assert result.voice_id.status == MirrorStatus.MATCH, (
        "Trailing whitespace difference must be normalized at the "
        "comparison boundary and NOT report as drift."
    )
    # Reported values preserve what was actually persisted — audit
    # output must not lie about the raw content.
    assert result.voice_id.mirror_value == "vincent   "
    assert result.voice_id.canonical_value == "vincent"


# =====================================================================
# Aggregate report — verify_all_mirrors
# =====================================================================


def test_verify_all_mirrors_counts_all_categories() -> None:
    # Clean prequalification teammate.
    tm_clean, u_clean = _make_teammate("agg-clean@t")
    _seed_prequalification_authored(tm_clean, u_clean)

    # Clean legacy import.
    tm_legacy, _ = _make_teammate("agg-legacy@t")
    _seed_legacy_imported(tm_legacy)

    # No-identity + all mirrors blank.
    tm_empty, _ = _make_teammate("agg-empty@t")

    # No-identity + populated mirrors (canonical_backfill_required).
    tm_debt, _ = _make_teammate("agg-debt@t")
    tm_debt.portrait_path = "https://debt/p.png"
    tm_debt.voice_id = "vincent"
    tm_debt.save(update_fields=["portrait_path", "voice_id"])

    # Drift via ORM bypass on the clean prequal teammate.
    Teammate.objects.filter(pk=tm_clean.pk).update(
        portrait_path="https://drifted/wrong.png",
    )

    report = compat.verify_all_mirrors()
    assert report.total_inspected == 4
    assert report.identity_class_counts[IdentityClass.NO_IDENTITY] == 2
    assert (
        report.identity_class_counts[IdentityClass.PREQUALIFICATION_AUTHORED]
        == 1
    )
    assert report.identity_class_counts[IdentityClass.LEGACY_IMPORTED] == 1

    # tm_empty is fully N/A → not counted as clean_match.
    # tm_legacy is clean match.
    # tm_debt has drift.
    # tm_clean now has drift.
    assert report.clean_match_count == 1
    assert report.drift_count == 2
    assert report.canonical_backfill_required_count == 1

    assert report.drift_by_field["portrait_path"] == 2  # tm_clean + tm_debt
    assert report.drift_by_field["voice_id"] == 1       # tm_debt
    assert report.drift_by_field["runway_avatar_id"] == 0

    assert report.drift_by_reason[MirrorReason.CANONICAL_IDENTITY_REQUIRED] == 2
    assert report.drift_by_reason[MirrorReason.VALUE_MISMATCH] == 1

    assert report.na_by_reason[MirrorReason.NO_IDENTITY_AUTHORED] == 4  # tm_empty's 3 + tm_debt's 1 blank


def test_verify_all_mirrors_workspace_filter() -> None:
    tm_a, _ = _make_teammate("agg-a@t", name="A")
    tm_b, _ = _make_teammate("agg-b@t", name="B")

    report_a = compat.verify_all_mirrors(workspace_id=tm_a.workspace_id)
    assert report_a.total_inspected == 1
    assert report_a.per_teammate[0].teammate_id == tm_a.id

    report_b = compat.verify_all_mirrors(workspace_id=tm_b.workspace_id)
    assert report_b.total_inspected == 1
    assert report_b.per_teammate[0].teammate_id == tm_b.id
