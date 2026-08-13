"""Identity-version write-path service — draft authoring, spec
validation, reference attachment, generation / manifest records.

Concurrency + approval semantics live in ``test_services_approval``
and ``test_services_concurrency``.
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
    DirectionHypothesis,
    ExecutionMode,
    ExecutionModeActual,
    GenerationProvider,
    IdentityReferenceKind,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_identity(ws: Workspace, *, name: str = "Ruby") -> CharacterIdentity:
    return CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name=name,
    )


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


def _make_asset(ws: Workspace, path: str) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path=path,
    )


# ---- create_draft_version -----------------------------------------


def test_create_draft_version_happy_path() -> None:
    ws = _make_workspace("draft-create@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(
        identity, _valid_human_spec(), spec_schema_version=1,
    )
    assert version.state == "draft"
    assert version.revision == 1
    assert version.spec_schema_version == 1


def test_create_draft_version_assigns_monotonic_revisions() -> None:
    ws = _make_workspace("draft-monotonic@t")
    identity = _make_identity(ws)
    v1 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    v2 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    v3 = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    assert (v1.revision, v2.revision, v3.revision) == (1, 2, 3)


def test_create_draft_version_rejects_invalid_spec() -> None:
    ws = _make_workspace("draft-invalid@t")
    identity = _make_identity(ws)
    bad_spec = _valid_human_spec()
    del bad_spec["hair"]  # required field
    with pytest.raises(services.IdentityVersionSpecInvalid) as ei:
        services.create_draft_version(identity, bad_spec, spec_schema_version=1)
    assert ei.value.code == "spec_invalid"


def test_create_draft_version_rejects_provider_leakage_in_spec() -> None:
    """§17.3.a — the human schema forbids additional properties,
    so provider-namespaced fields cannot sneak into the spec.
    """
    ws = _make_workspace("draft-leak@t")
    identity = _make_identity(ws)
    spec = _valid_human_spec()
    spec["runway_avatar_id"] = "runway_abc"
    with pytest.raises(services.IdentityVersionSpecInvalid):
        services.create_draft_version(identity, spec, spec_schema_version=1)


# ---- update_draft_spec --------------------------------------------


def test_update_draft_spec_happy_path() -> None:
    ws = _make_workspace("update-happy@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    new_spec = _valid_human_spec()
    new_spec["hair"]["color"] = "silver"
    services.update_draft_spec(version, new_spec, spec_schema_version=1)
    version.refresh_from_db()
    assert version.spec["hair"]["color"] == "silver"


def test_update_draft_spec_rejects_non_draft_state() -> None:
    ws = _make_workspace("update-nondraft@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    version.state = CharacterIdentityVersion.State.REJECTED
    version.save(update_fields=["state"])
    with pytest.raises(services.IdentityVersionError) as ei:
        services.update_draft_spec(version, _valid_human_spec(), spec_schema_version=1)
    assert ei.value.code == "invalid_state_transition"


# ---- attach_reference ---------------------------------------------


def test_attach_reference_happy_path() -> None:
    ws = _make_workspace("attach-happy@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    asset = _make_asset(ws, "media/front.png")
    ref = services.attach_reference(
        version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
    )
    assert ref.kind == "portrait_reference"
    assert ref.purpose == "front"


def test_attach_reference_rejects_unknown_purpose() -> None:
    ws = _make_workspace("attach-purpose@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    asset = _make_asset(ws, "media/front.png")
    with pytest.raises(services.IdentityReferenceError) as ei:
        services.attach_reference(
            version,
            asset=asset,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose="something_not_in_the_schema",
        )
    assert ei.value.code == "reference_invalid"


def test_attach_reference_rejects_unknown_kind() -> None:
    ws = _make_workspace("attach-kind@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    asset = _make_asset(ws, "media/front.png")
    with pytest.raises(services.IdentityReferenceError) as ei:
        services.attach_reference(
            version,
            asset=asset,
            kind="not_a_kind",
            purpose="front",
        )
    assert ei.value.code == "reference_invalid"


def test_attach_reference_rejects_cross_workspace_asset() -> None:
    ws_a = _make_workspace("attach-cross-a@t")
    ws_b = _make_workspace("attach-cross-b@t")
    identity = _make_identity(ws_a)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    wrong_asset = _make_asset(ws_b, "media/wrong.png")
    with pytest.raises(services.IdentityReferenceError) as ei:
        services.attach_reference(
            version,
            asset=wrong_asset,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose="front",
        )
    assert ei.value.code == "reference_invalid"


# ---- record_generation / record_normalization_manifest -------------


def test_record_generation_happy_path() -> None:
    ws = _make_workspace("gen-service@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    raw = _make_asset(ws, "media/raw.png")
    record = services.record_generation(
        version,
        provider=GenerationProvider.MOCK,
        provider_model="mock-1",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"prompt": "test"},
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
        raw_output_asset=raw,
    )
    assert record.provider == "mock"
    assert record.raw_output_asset_id == raw.id


def test_record_generation_rejects_cross_workspace_asset() -> None:
    ws_a = _make_workspace("gen-cross-a@t")
    ws_b = _make_workspace("gen-cross-b@t")
    identity = _make_identity(ws_a)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    wrong = _make_asset(ws_b, "media/wrong.png")
    with pytest.raises(services.IdentityVersionError):
        services.record_generation(
            version,
            provider=GenerationProvider.MOCK,
            provider_model="mock-1",
            direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
            prompt_snapshot={},
            execution_mode=ExecutionMode.FORCED_MOCK,
            execution_mode_actual=ExecutionModeActual.MOCK,
            raw_output_asset=wrong,
        )


def test_record_normalization_manifest_happy_path() -> None:
    ws = _make_workspace("nm-service@t")
    identity = _make_identity(ws)
    version = services.create_draft_version(identity, _valid_human_spec(), spec_schema_version=1)
    raw = _make_asset(ws, "media/raw.png")
    normalized = _make_asset(ws, "media/norm.png")
    record = services.record_generation(
        version,
        provider=GenerationProvider.MOCK,
        provider_model="mock-1",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
        raw_output_asset=raw,
        normalized_output_asset=normalized,
    )
    manifest = services.record_normalization_manifest(
        record,
        raw_output_asset=raw,
        normalized_output_asset=normalized,
        pipeline_version="v1",
        surface_profile_id="presence",
        surface_profile_version=1,
        background_id="studio_seamless_warm",
        execution_duration_ms=100,
    )
    assert manifest.pipeline_version == "v1"
