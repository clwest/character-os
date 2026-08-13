"""Canonical Identity substrate — reference / generation / manifest
model shape tests (2.b slice).

Covers ``IdentityReference``, ``GenerationRecord``, and
``NormalizationManifest``. Cross-workspace isolation per §7.5 is
verified through both ``clean()`` and the ``pre_save`` signal so
the raw ``.save()`` path is covered too.

Append-only guards on ``GenerationRecord`` and
``NormalizationManifest`` are tested only along the supported ORM
path (instance-level ``.save()`` on a persisted row). The contract
explicitly does not claim ``QuerySet.update()`` / raw SQL are
prevented — the substrate does not introduce DB triggers for this.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    ExecutionMode,
    ExecutionModeActual,
    GenerationApprovalState,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    NormalizationManifest,
    ReferenceState,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_identity_and_version(ws: Workspace, *, name: str = "Ruby"):
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name=name,
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={"spec_schema_version": 1},
        spec_schema_version=1,
    )
    return identity, version


def _make_asset(ws: Workspace, *, path: str = "media/portrait.png") -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path=path,
    )


def _make_generation_record(version: CharacterIdentityVersion, **overrides) -> GenerationRecord:
    defaults = dict(
        identity_version=version,
        provider=GenerationProvider.MOCK,
        provider_model="mock-1",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={"prompt": "test"},
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
    )
    defaults.update(overrides)
    return GenerationRecord.objects.create(**defaults)


# ---- IdentityReference ---------------------------------------------


def test_identity_reference_round_trip() -> None:
    ws = _make_workspace("iref-round@t")
    _, version = _make_identity_and_version(ws)
    asset = _make_asset(ws)

    ref = IdentityReference.objects.create(
        identity_version=version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.RAW,
    )

    reloaded = IdentityReference.objects.get(pk=ref.pk)
    assert reloaded.kind == "portrait_reference"
    assert reloaded.purpose == "front"
    assert reloaded.state == "raw"
    assert reloaded.generation_record is None
    assert reloaded.created_at is not None


def test_identity_reference_purpose_is_free_text() -> None:
    """§17.5.a — purpose is validated by the branch schema at the
    write-path service, not by DB-level choices. The column is a
    plain CharField so adding a purpose value does not require a
    Django migration.
    """
    ws = _make_workspace("iref-purpose@t")
    _, version = _make_identity_and_version(ws)
    asset = _make_asset(ws)
    # A purpose value that is not in the current human schema
    # persists successfully — the substrate is deliberately
    # neutral. Rejection happens in the write-path service (2.d).
    ref = IdentityReference.objects.create(
        identity_version=version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="entirely_new_purpose_value",
        state=ReferenceState.RAW,
    )
    assert ref.purpose == "entirely_new_purpose_value"


def test_identity_reference_cross_workspace_asset_rejected_via_clean() -> None:
    ws_a = _make_workspace("iref-clean-a@t")
    ws_b = _make_workspace("iref-clean-b@t")
    _, version_a = _make_identity_and_version(ws_a)
    asset_b = _make_asset(ws_b, path="media/wrong-ws.png")

    ref = IdentityReference(
        identity_version=version_a,
        asset=asset_b,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.RAW,
    )
    with pytest.raises(ValidationError):
        ref.full_clean()


def test_identity_reference_cross_workspace_asset_rejected_via_signal() -> None:
    """The raw ``.save()`` path (which does not call ``clean()``)
    must also refuse cross-workspace references — the ``pre_save``
    signal delegates to ``clean()`` (§7.5 defense in depth).
    """
    ws_a = _make_workspace("iref-sig-a@t")
    ws_b = _make_workspace("iref-sig-b@t")
    _, version_a = _make_identity_and_version(ws_a)
    asset_b = _make_asset(ws_b, path="media/wrong-ws-signal.png")

    with pytest.raises(ValidationError):
        IdentityReference.objects.create(
            identity_version=version_a,
            asset=asset_b,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose="front",
            state=ReferenceState.RAW,
        )


# ---- GenerationRecord ----------------------------------------------


def test_generation_record_round_trip() -> None:
    ws = _make_workspace("gen-round@t")
    _, version = _make_identity_and_version(ws)
    raw_asset = _make_asset(ws, path="media/raw.png")

    record = _make_generation_record(
        version,
        raw_output_asset=raw_asset,
        elapsed_ms=1250,
    )

    reloaded = GenerationRecord.objects.get(pk=record.pk)
    assert reloaded.provider == "mock"
    assert reloaded.provider_model == "mock-1"
    assert reloaded.direction_hypothesis == "identity_only"
    assert reloaded.execution_mode == "forced_mock"
    assert reloaded.execution_mode_actual == "mock"
    assert reloaded.approval_state == "pending"
    assert reloaded.raw_output_asset_id == raw_asset.id
    assert reloaded.normalized_output_asset is None
    assert reloaded.elapsed_ms == 1250
    assert reloaded.reviewer_notes == {}


def test_generation_record_input_assets_m2m() -> None:
    ws = _make_workspace("gen-inputs@t")
    _, version = _make_identity_and_version(ws)
    input_a = _make_asset(ws, path="media/in-a.png")
    input_b = _make_asset(ws, path="media/in-b.png")

    record = _make_generation_record(version)
    record.input_reference_assets.add(input_a, input_b)

    inputs = list(record.input_reference_assets.order_by("file_path"))
    assert {a.pk for a in inputs} == {input_a.pk, input_b.pk}


def test_generation_record_cross_workspace_raw_asset_rejected() -> None:
    ws_a = _make_workspace("gen-cross-a@t")
    ws_b = _make_workspace("gen-cross-b@t")
    _, version_a = _make_identity_and_version(ws_a)
    wrong_asset = _make_asset(ws_b, path="media/wrong.png")

    with pytest.raises(ValidationError):
        _make_generation_record(version_a, raw_output_asset=wrong_asset)


def test_generation_record_append_only_supported_path() -> None:
    """§8.2 — the supported write path creates records; instance-
    level mutation of a persisted row is defensively rejected.

    This does not claim ``QuerySet.update()`` is impossible; it
    covers the supported ORM path only.
    """
    ws = _make_workspace("gen-append@t")
    _, version = _make_identity_and_version(ws)
    record = _make_generation_record(version)

    record.approval_state = GenerationApprovalState.REJECTED
    with pytest.raises(ValidationError):
        record.save()


# ---- NormalizationManifest -----------------------------------------


def test_normalization_manifest_round_trip() -> None:
    ws = _make_workspace("nm-round@t")
    _, version = _make_identity_and_version(ws)
    raw = _make_asset(ws, path="media/raw.png")
    normalized = _make_asset(ws, path="media/normalized.png")
    record = _make_generation_record(
        version,
        raw_output_asset=raw,
        normalized_output_asset=normalized,
    )

    manifest = NormalizationManifest.objects.create(
        generation_record=record,
        raw_output_asset=raw,
        normalized_output_asset=normalized,
        pipeline_version="crop-1|framing-1|eyeline-1|bg-1",
        surface_profile_id="presence",
        surface_profile_version=1,
        background_id="studio_seamless_warm",
        stages_executed=[{"stage": "crop", "version": 1}],
        stages_skipped=[{"stage": "tonal", "reason": "deferred round-one"}],
        eye_line_adjustments={"pitch_deg": 0.5},
        crop_metadata={"aspect": "3:4"},
        execution_duration_ms=845,
    )

    reloaded = NormalizationManifest.objects.get(pk=manifest.pk)
    assert reloaded.pipeline_version == "crop-1|framing-1|eyeline-1|bg-1"
    assert reloaded.surface_profile_id == "presence"
    assert reloaded.surface_profile_version == 1
    assert reloaded.background_id == "studio_seamless_warm"
    assert reloaded.stages_executed == [{"stage": "crop", "version": 1}]
    assert reloaded.execution_duration_ms == 845


def test_normalization_manifest_one_per_generation() -> None:
    """§10.6 — one manifest per generation. The FK is OneToOne, so
    a second manifest against the same record must be rejected.
    """
    ws = _make_workspace("nm-one@t")
    _, version = _make_identity_and_version(ws)
    raw = _make_asset(ws, path="media/raw2.png")
    normalized = _make_asset(ws, path="media/normalized2.png")
    record = _make_generation_record(version, raw_output_asset=raw)

    NormalizationManifest.objects.create(
        generation_record=record,
        raw_output_asset=raw,
        normalized_output_asset=normalized,
        pipeline_version="v1",
        surface_profile_id="presence",
        surface_profile_version=1,
        background_id="studio_seamless_warm",
        execution_duration_ms=100,
    )
    from django.db import IntegrityError, transaction
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            NormalizationManifest.objects.create(
                generation_record=record,
                raw_output_asset=raw,
                normalized_output_asset=normalized,
                pipeline_version="v1",
                surface_profile_id="presence",
                surface_profile_version=1,
                background_id="studio_seamless_warm",
                execution_duration_ms=100,
            )


def test_normalization_manifest_cross_workspace_asset_rejected() -> None:
    ws_a = _make_workspace("nm-cross-a@t")
    ws_b = _make_workspace("nm-cross-b@t")
    _, version_a = _make_identity_and_version(ws_a)
    raw_a = _make_asset(ws_a, path="media/raw-a.png")
    wrong_asset = _make_asset(ws_b, path="media/wrong-ws.png")
    record = _make_generation_record(version_a, raw_output_asset=raw_a)

    with pytest.raises(ValidationError):
        NormalizationManifest.objects.create(
            generation_record=record,
            raw_output_asset=raw_a,
            normalized_output_asset=wrong_asset,
            pipeline_version="v1",
            surface_profile_id="presence",
            surface_profile_version=1,
            background_id="studio_seamless_warm",
            execution_duration_ms=100,
        )


def test_normalization_manifest_append_only_supported_path() -> None:
    ws = _make_workspace("nm-append@t")
    _, version = _make_identity_and_version(ws)
    raw = _make_asset(ws, path="media/raw-append.png")
    normalized = _make_asset(ws, path="media/norm-append.png")
    record = _make_generation_record(version, raw_output_asset=raw)

    manifest = NormalizationManifest.objects.create(
        generation_record=record,
        raw_output_asset=raw,
        normalized_output_asset=normalized,
        pipeline_version="v1",
        surface_profile_id="presence",
        surface_profile_version=1,
        background_id="studio_seamless_warm",
        execution_duration_ms=100,
    )

    manifest.execution_duration_ms = 999
    with pytest.raises(ValidationError):
        manifest.save()
