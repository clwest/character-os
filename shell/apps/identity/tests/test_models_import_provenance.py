"""3.a substrate additions — ImportProvenance model, LEGACY_IMPORTED
generation-provider enum value, CharacterIdentity.teammate partial
unique constraint, spec_schema_version=0 sentinel discipline, and
the three provenance helper properties on CharacterIdentityVersion.

These tests establish the invariants Step 3's import service will
rely on. The service itself and its concurrency / classification
behavior land in 3.b.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace
from apps.identity import services
from apps.identity.models import (
    IMPORT_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
    LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
    MIN_CANONICAL_SPEC_SCHEMA_VERSION,
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationProvider,
    ImportProvenance,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(ws: Workspace, *, name: str = "Ruby") -> Teammate:
    return Teammate.objects.create(workspace=ws, name=name)


def _make_identity(
    ws: Workspace,
    *,
    name: str = "Ruby",
    teammate: Teammate | None = None,
) -> CharacterIdentity:
    return CharacterIdentity.objects.create(
        workspace=ws,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name=name,
    )


def _make_legacy_version(identity: CharacterIdentity) -> CharacterIdentityVersion:
    return CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
        spec={},
        spec_schema_version=LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
    )


# ---- Sentinel + module constants -----------------------------------


def test_legacy_unvalidated_sentinel_is_zero() -> None:
    """The ratified sentinel value stays 0. Downstream code binds
    to the module constant, not the literal — this test locks the
    literal too so nobody quietly rebases the sentinel.
    """
    assert LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION == 0


def test_min_canonical_spec_schema_version_is_one() -> None:
    assert MIN_CANONICAL_SPEC_SCHEMA_VERSION == 1


def test_snapshot_schema_version_constant_exists() -> None:
    assert IMPORT_PROVENANCE_SNAPSHOT_SCHEMA_VERSION == 1


# ---- GenerationProvider.LEGACY_IMPORTED ----------------------------


def test_generation_provider_legacy_imported_present() -> None:
    """The enum value exists and carries a label that names it as
    historical / unqualified so any human reading admin or logs
    understands the discriminator.
    """
    assert GenerationProvider.LEGACY_IMPORTED == "legacy_imported"
    label = dict(GenerationProvider.choices)[GenerationProvider.LEGACY_IMPORTED]
    assert "legacy" in label.lower()
    assert "unqualified" in label.lower()


# ---- CharacterIdentity.teammate partial unique ---------------------


def test_one_character_identity_per_non_null_teammate() -> None:
    ws = _make_workspace("teammate-unique@t")
    teammate = _make_teammate(ws)
    _make_identity(ws, name="Alex-1", teammate=teammate)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _make_identity(ws, name="Alex-2", teammate=teammate)


def test_multiple_identities_with_null_teammate_allowed() -> None:
    """§15.1 — bootstrap fixture identities carry ``teammate=NULL``.
    The partial unique constraint must not block that shape.
    """
    ws = _make_workspace("teammate-null-ok@t")
    _make_identity(ws, name="Fixture-H1", teammate=None)
    _make_identity(ws, name="Fixture-H2", teammate=None)
    _make_identity(ws, name="Fixture-H3", teammate=None)
    null_ids = CharacterIdentity.objects.filter(teammate__isnull=True).count()
    assert null_ids == 3


# ---- services.create_draft_version schema-version gate -------------


def test_create_draft_version_rejects_schema_version_0() -> None:
    """The normal authoring write path must never accept the
    legacy-unvalidated sentinel — that value is Step 3's exclusive
    territory.
    """
    ws = _make_workspace("draft-zero@t")
    identity = _make_identity(ws)
    with pytest.raises(services.IdentityVersionSpecInvalid) as ei:
        services.create_draft_version(identity, {}, spec_schema_version=0)
    assert ei.value.code == "spec_invalid"
    assert "legacy_unvalidated" in str(ei.value).lower() or "0" in str(ei.value)


def test_update_draft_spec_rejects_schema_version_0() -> None:
    """Same gate on the update path so a caller cannot downgrade
    a valid canonical draft to the legacy sentinel.
    """
    ws = _make_workspace("update-zero@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(
        identity,
        _valid_human_spec(),
        spec_schema_version=1,
    )
    with pytest.raises(services.IdentityVersionSpecInvalid) as ei:
        services.update_draft_spec(version, {}, spec_schema_version=0)
    assert ei.value.code == "spec_invalid"


def test_dedicated_legacy_import_path_may_write_schema_version_0() -> None:
    """The DB does not forbid ``spec_schema_version=0`` — the gate
    lives in the service layer. Direct ORM writes (the Step 3
    legacy import service will use this path) can persist the
    sentinel value.
    """
    ws = _make_workspace("legacy-import-zero@t")
    identity = _make_identity(ws)
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
        spec={},
        spec_schema_version=LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
    )
    assert version.spec_schema_version == 0


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


# ---- ImportProvenance model ---------------------------------------


def test_import_provenance_round_trip() -> None:
    ws = _make_workspace("prov-round@t")
    teammate = _make_teammate(ws)
    identity = _make_identity(ws, teammate=teammate)
    version = _make_legacy_version(identity)

    run_id = uuid.uuid4()
    provenance = ImportProvenance.objects.create(
        identity_version=version,
        source_teammate_id=teammate.id,
        import_run_id=run_id,
        migration_version="identity.0002",
        snapshot_schema_version=IMPORT_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        legacy_snapshot={
            "runway_avatar_id": "avatar_abc",
            "portrait_path": "https://cdn.example/x.png",
            "voice_id": "voice_xyz",
            "identity_page_fields": {
                "business_brief": "coffee roaster",
            },
        },
    )

    reloaded = ImportProvenance.objects.get(pk=provenance.pk)
    assert reloaded.identity_version_id == version.id
    assert reloaded.source_teammate_id == teammate.id
    assert reloaded.import_run_id == run_id
    assert reloaded.migration_version == "identity.0002"
    assert reloaded.snapshot_schema_version == 1
    assert reloaded.legacy_snapshot["runway_avatar_id"] == "avatar_abc"
    assert reloaded.import_source == "apps.spokespeople.Teammate"
    assert reloaded.imported_at is not None


def test_import_provenance_one_to_one_enforced() -> None:
    ws = _make_workspace("prov-onetoone@t")
    teammate = _make_teammate(ws)
    identity = _make_identity(ws, teammate=teammate)
    version = _make_legacy_version(identity)
    ImportProvenance.objects.create(
        identity_version=version,
        import_run_id=uuid.uuid4(),
        migration_version="identity.0002",
        snapshot_schema_version=1,
        legacy_snapshot={},
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ImportProvenance.objects.create(
                identity_version=version,
                import_run_id=uuid.uuid4(),
                migration_version="identity.0002",
                snapshot_schema_version=1,
                legacy_snapshot={},
            )


def test_import_provenance_append_only_supported_path() -> None:
    ws = _make_workspace("prov-append@t")
    teammate = _make_teammate(ws)
    identity = _make_identity(ws, teammate=teammate)
    version = _make_legacy_version(identity)
    provenance = ImportProvenance.objects.create(
        identity_version=version,
        import_run_id=uuid.uuid4(),
        migration_version="identity.0002",
        snapshot_schema_version=1,
        legacy_snapshot={"runway_avatar_id": "old"},
    )
    provenance.legacy_snapshot = {"runway_avatar_id": "new"}
    with pytest.raises(ValidationError):
        provenance.save()


def test_import_provenance_survives_teammate_deletion() -> None:
    """source_teammate_id is a bare UUID snapshot — the row must
    survive Teammate deletion so historical audits remain
    answerable.
    """
    ws = _make_workspace("prov-survive@t")
    teammate = _make_teammate(ws)
    teammate_id = teammate.id
    identity = _make_identity(ws, teammate=teammate)
    version = _make_legacy_version(identity)
    provenance = ImportProvenance.objects.create(
        identity_version=version,
        source_teammate_id=teammate_id,
        import_run_id=uuid.uuid4(),
        migration_version="identity.0002",
        snapshot_schema_version=1,
        legacy_snapshot={"portrait_path": "..."},
    )
    # Delete the teammate; the identity's teammate FK goes NULL
    # (SET_NULL on the FK); the provenance snapshot survives.
    teammate.delete()
    identity.refresh_from_db()
    assert identity.teammate_id is None
    reloaded = ImportProvenance.objects.get(pk=provenance.pk)
    assert reloaded.source_teammate_id == teammate_id


# ---- Provenance helper properties ---------------------------------


def test_is_legacy_imported_false_without_provenance() -> None:
    ws = _make_workspace("prop-not-imported@t")
    identity = _make_identity(ws)
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=1,
    )
    assert version.is_legacy_imported is False


def test_is_legacy_imported_true_when_provenance_exists() -> None:
    ws = _make_workspace("prop-imported@t")
    teammate = _make_teammate(ws)
    identity = _make_identity(ws, teammate=teammate)
    version = _make_legacy_version(identity)
    ImportProvenance.objects.create(
        identity_version=version,
        import_run_id=uuid.uuid4(),
        migration_version="identity.0002",
        snapshot_schema_version=1,
        legacy_snapshot={},
    )
    version.refresh_from_db()
    assert version.is_legacy_imported is True


def test_is_canonical_schema_validated_true_for_positive_version() -> None:
    ws = _make_workspace("prop-schema-1@t")
    identity = _make_identity(ws)
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=1,
    )
    assert version.is_canonical_schema_validated is True


def test_is_canonical_schema_validated_false_for_legacy_sentinel() -> None:
    ws = _make_workspace("prop-schema-0@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)  # spec_schema_version=0
    assert version.is_canonical_schema_validated is False


def _make_generation_record(
    version: CharacterIdentityVersion,
    **overrides,
):
    """Default shape represents a legacy-imported record — provider
    LEGACY_IMPORTED with both execution fields NULL. Overrides let
    tests exercise the pairing invariant against every axis.
    """
    from apps.identity.models import (
        DirectionHypothesis,
        GenerationRecord,
    )
    defaults = dict(
        identity_version=version,
        provider=GenerationProvider.LEGACY_IMPORTED,
        provider_model="",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        execution_mode=None,
        execution_mode_actual=None,
    )
    defaults.update(overrides)
    return GenerationRecord.objects.create(**defaults)


# ---- Provider ↔ execution-field pairing invariant ------------------
# §17.10.a Amendment 3 (post-SESSION 242 correction). Execution-mode
# vocabulary describes execution-framework decisions (§9.4). Legacy
# imports never went through the framework, so the honest label is
# NULL / NULL. Origin is carried by GenerationProvider.LEGACY_IMPORTED
# + ImportProvenance + spec_schema_version=0.


def test_legacy_provider_with_null_execution_fields_accepted() -> None:
    """Regression case 1 — the shape the Step 3 import service
    always constructs (LEGACY_IMPORTED + NULL / NULL) is valid.
    """
    ws = _make_workspace("pair-happy@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    _make_generation_record(version)  # defaults are LEGACY + NULL/NULL


def test_legacy_provider_with_non_null_execution_mode_rejected() -> None:
    """Regression case 2a — a legacy_imported record must not claim
    an execution mode. Origin does not license execution semantics.
    """
    from apps.identity.models import ExecutionMode, ExecutionModeActual
    ws = _make_workspace("pair-legacy-real-mode@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    with pytest.raises(ValidationError):
        _make_generation_record(
            version,
            provider=GenerationProvider.LEGACY_IMPORTED,
            execution_mode=ExecutionMode.REAL_REQUIRED,
            execution_mode_actual=ExecutionModeActual.REAL,
        )


def test_legacy_provider_with_non_null_execution_actual_rejected() -> None:
    """Regression case 2b — same guard when only execution_actual
    is populated on a legacy row.
    """
    from apps.identity.models import ExecutionMode, ExecutionModeActual
    ws = _make_workspace("pair-legacy-real-actual@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    with pytest.raises(ValidationError):
        _make_generation_record(
            version,
            provider=GenerationProvider.LEGACY_IMPORTED,
            execution_mode=ExecutionMode.FORCED_MOCK,
            execution_mode_actual=ExecutionModeActual.MOCK,
        )


def test_non_legacy_provider_with_null_execution_fields_rejected() -> None:
    """Regression case 3 — an executable provider record with NULL
    execution fields is invalid. NULL is specific to non-execution
    origin; it must not silently degrade a malformed provider record.
    """
    ws = _make_workspace("pair-real-null@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    with pytest.raises(ValidationError):
        _make_generation_record(
            version,
            provider=GenerationProvider.RUNWAY_AVATAR,
            execution_mode=None,
            execution_mode_actual=None,
        )


def test_half_null_execution_fields_rejected_mode_null_only() -> None:
    """Regression case 4a — one NULL / one non-NULL has no defined
    semantics. Refused regardless of provider.
    """
    from apps.identity.models import ExecutionModeActual
    ws = _make_workspace("pair-half-null-a@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    with pytest.raises(ValidationError):
        _make_generation_record(
            version,
            provider=GenerationProvider.STABILITY_STILL,
            execution_mode=None,
            execution_mode_actual=ExecutionModeActual.REAL,
        )


def test_half_null_execution_fields_rejected_actual_null_only() -> None:
    """Regression case 4b — symmetric to 4a."""
    from apps.identity.models import ExecutionMode
    ws = _make_workspace("pair-half-null-b@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    with pytest.raises(ValidationError):
        _make_generation_record(
            version,
            provider=GenerationProvider.MOCK,
            execution_mode=ExecutionMode.FORCED_MOCK,
            execution_mode_actual=None,
        )


def test_normal_provider_pair_still_accepted() -> None:
    """A non-legacy provider paired with real / mock execution
    fields is the standard case — the invariant adds no friction
    to Step 2's authoritative write path.
    """
    from apps.identity.models import ExecutionMode, ExecutionModeActual
    ws = _make_workspace("pair-normal@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)
    _make_generation_record(
        version,
        provider=GenerationProvider.MOCK,
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
    )


def test_unavailable_execution_mode_is_distinct_from_null() -> None:
    """Regression case 5 — ``UNAVAILABLE`` is an execution-framework
    decision recorded from an attempted call; NULL is the absence
    of any such attempt. A non-legacy provider may honestly claim
    UNAVAILABLE (with a mock_fallback or real actual, per §9.4)
    while a legacy_imported row must remain NULL / NULL.

    This test explicitly locks the semantic distinction:

    * ``UNAVAILABLE + MOCK_FALLBACK`` on a real provider → valid.
    * ``LEGACY_IMPORTED + UNAVAILABLE + MOCK_FALLBACK`` → invalid
      (misrepresents a non-execution as a failed real execution).
    """
    from apps.identity.models import ExecutionMode, ExecutionModeActual
    ws = _make_workspace("pair-unavailable-distinct@t")
    identity = _make_identity(ws)
    version = _make_legacy_version(identity)

    # UNAVAILABLE on a real provider is a valid non-null execution
    # decision — the request went through the framework and the
    # provider could not serve it.
    _make_generation_record(
        version,
        provider=GenerationProvider.RUNWAY_AVATAR,
        execution_mode=ExecutionMode.UNAVAILABLE,
        execution_mode_actual=ExecutionModeActual.MOCK_FALLBACK,
    )

    # Same UNAVAILABLE / MOCK_FALLBACK pair is refused on a
    # legacy_imported row — origin says "no request was ever made,"
    # so no execution-framework decision (including UNAVAILABLE)
    # applies.
    with pytest.raises(ValidationError):
        _make_generation_record(
            version,
            provider=GenerationProvider.LEGACY_IMPORTED,
            execution_mode=ExecutionMode.UNAVAILABLE,
            execution_mode_actual=ExecutionModeActual.MOCK_FALLBACK,
        )


def test_is_qualification_eligible_matrix() -> None:
    """Composite semantics: eligible iff schema-validated AND not
    legacy-imported.
    """
    ws = _make_workspace("prop-qual@t")
    teammate_a = _make_teammate(ws, name="A")
    teammate_b = _make_teammate(ws, name="B")

    # 1. Legacy import (schema_version=0, provenance present) -> not eligible.
    identity_legacy = _make_identity(ws, name="ident-legacy", teammate=teammate_a)
    v_legacy = _make_legacy_version(identity_legacy)
    ImportProvenance.objects.create(
        identity_version=v_legacy,
        import_run_id=uuid.uuid4(),
        migration_version="identity.0002",
        snapshot_schema_version=1,
        legacy_snapshot={},
    )
    v_legacy.refresh_from_db()
    assert v_legacy.is_qualification_eligible is False

    # 2. Schema-validated authored version (no provenance) -> eligible.
    identity_authored = _make_identity(ws, name="ident-authored", teammate=teammate_b)
    v_authored = CharacterIdentityVersion.objects.create(
        identity=identity_authored,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=1,
    )
    assert v_authored.is_qualification_eligible is True

    # 3. Sentinel spec_schema_version without provenance (a degenerate
    #    state that shouldn't occur in practice but the property must
    #    still refuse) -> not eligible.
    identity_edge = _make_identity(ws, name="ident-edge")
    v_edge = CharacterIdentityVersion.objects.create(
        identity=identity_edge,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    assert v_edge.is_qualification_eligible is False
