"""SESSION 249 §19 Step 9.b.3a Finding 10 regression.

Proves ``NormalizationManifest.pipeline_version`` can round-trip
the actual frozen Step 9.a pipeline_version encoding (110 chars)
byte-for-byte after the CharField(64) → TextField widening in
migration ``0009_normalization_pipeline_version_text``.

Uses a real frozen value, not an invented long test string, so the
test remains meaningful across future encoding changes.
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
    NormalizationManifest,
)

# Verbatim from the frozen Step 9.a evidence at
# fixtures/fixture_h1/runs/bootstrap_20260808T044853Z_7eb392992e0f/
# identity_only/stability_still/manifests/
# fixture_h1__portrait_reference__front__compact.json — 110 chars.
FROZEN_PIPELINE_VERSION = (
    "pipeline_v1:crop@2|framing@1|background_replacement@1|"
    "profile:compact@1:cbb1eb67c47d|bg_family:v1:801f375021f4"
)

User = get_user_model()
pytestmark = pytest.mark.django_db


def _make_ws() -> Workspace:
    user = User.objects.create_user(email="nm-pipe@example.test", password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_asset(ws: Workspace) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE,
        file_path="/tmp/nothing.png",
    )


def test_frozen_step9a_pipeline_version_round_trips_byte_for_byte():
    """The 110-char frozen encoding survives full_clean + save
    + refresh_from_db without truncation or transformation.
    """
    ws = _make_ws()
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name="fixture_h1",
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    raw = _make_asset(ws)
    norm = _make_asset(ws)
    gr = services.record_generation(
        version=version,
        provider=GenerationProvider.STABILITY_STILL,
        provider_model="sd3-large",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        raw_output_asset=raw,
        normalized_output_asset=norm,
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        elapsed_ms=1000,
    )
    nm = services.record_normalization_manifest(
        generation_record=gr,
        raw_output_asset=raw,
        normalized_output_asset=norm,
        pipeline_version=FROZEN_PIPELINE_VERSION,
        surface_profile_id="compact",
        surface_profile_version=1,
        background_id="neutral_warm_studio",
        stages_executed=[],
        stages_skipped=[],
        eye_line_adjustments={},
        crop_metadata={},
        execution_duration_ms=1500,
    )
    nm.refresh_from_db()
    assert nm.pipeline_version == FROZEN_PIPELINE_VERSION
    assert len(nm.pipeline_version) == 110


def test_pipeline_version_accepts_longer_future_encodings():
    """Guard against re-introducing a length cap. TextField has no
    length constraint; any future encoding change ships without a
    substrate migration.
    """
    ws = _make_ws()
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name="fixture_h_future",
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    raw = _make_asset(ws)
    norm = _make_asset(ws)
    gr = services.record_generation(
        version=version,
        provider=GenerationProvider.STABILITY_STILL,
        provider_model="sd3-large",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        raw_output_asset=raw,
        normalized_output_asset=norm,
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        elapsed_ms=1000,
    )
    long_encoding = FROZEN_PIPELINE_VERSION + "|" + "extra_stage@1:" + "a" * 500
    nm = services.record_normalization_manifest(
        generation_record=gr,
        raw_output_asset=raw,
        normalized_output_asset=norm,
        pipeline_version=long_encoding,
        surface_profile_id="compact",
        surface_profile_version=1,
        background_id="neutral_warm_studio",
        stages_executed=[],
        stages_skipped=[],
        eye_line_adjustments={},
        crop_metadata={},
        execution_duration_ms=1500,
    )
    nm.refresh_from_db()
    assert nm.pipeline_version == long_encoding
    assert len(nm.pipeline_version) > 500


def test_other_manifest_fields_still_validated():
    """Widening pipeline_version must not have loosened any other
    field's validation. surface_profile_id is CharField(max_length=64)
    (unchanged); prove it still rejects overflow.
    """
    ws = _make_ws()
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name="fixture_h_validate",
    )
    version = CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={},
        spec_schema_version=0,
    )
    raw = _make_asset(ws)
    norm = _make_asset(ws)
    gr = services.record_generation(
        version=version,
        provider=GenerationProvider.STABILITY_STILL,
        provider_model="sd3-large",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        raw_output_asset=raw,
        normalized_output_asset=norm,
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        elapsed_ms=1000,
    )
    with pytest.raises(services.IdentityVersionError) as exc_info:
        services.record_normalization_manifest(
            generation_record=gr,
            raw_output_asset=raw,
            normalized_output_asset=norm,
            pipeline_version=FROZEN_PIPELINE_VERSION,
            surface_profile_id="x" * 100,  # overflow CharField(64)
            surface_profile_version=1,
            background_id="neutral_warm_studio",
            stages_executed=[],
            stages_skipped=[],
            eye_line_adjustments={},
            crop_metadata={},
            execution_duration_ms=1500,
        )
    assert "surface_profile_id" in str(exc_info.value)
