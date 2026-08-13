"""Canonical Identity substrate — canonical voice / realtime
references + approved representation bundle (2.c slice).

The load-bearing property tested here is the ratified
provider-neutrality boundary from §17.4.a — the bundle exposes
canonical approved representations only; provider details stay on
the generation record beneath the reference. This test module
walks a bundle end-to-end without ever touching a Runway /
ElevenLabs / Stability identifier.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
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


def _make_version(ws: Workspace, *, name: str = "Ruby") -> CharacterIdentityVersion:
    identity = CharacterIdentity.objects.create(
        workspace=ws,
        kind=CharacterIdentity.Kind.HUMAN,
        name=name,
    )
    return CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.DRAFT,
        spec={"spec_schema_version": 1},
        spec_schema_version=1,
    )


def _make_generation_record(version: CharacterIdentityVersion) -> GenerationRecord:
    return GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.MOCK,
        provider_model="mock-1",
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={},
        execution_mode=ExecutionMode.FORCED_MOCK,
        execution_mode_actual=ExecutionModeActual.MOCK,
    )


# ---- CanonicalVoiceReference ---------------------------------------


def test_canonical_voice_reference_round_trip() -> None:
    ws = _make_workspace("cvr-round@t")
    version = _make_version(ws)
    record = _make_generation_record(version)

    ref = CanonicalVoiceReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.PROVISIONAL,
    )

    reloaded = CanonicalVoiceReference.objects.get(pk=ref.pk)
    assert reloaded.identity_version_id == version.id
    assert reloaded.generation_record_id == record.id
    assert reloaded.state == "provisional"
    assert reloaded.approved_at is None


def test_canonical_voice_reference_domain_contract_is_provider_neutral() -> None:
    """§17.4.a — the CanonicalVoiceReference row itself carries no
    provider-namespaced fields. Provider details must live on the
    referenced GenerationRecord (its ``provider``,
    ``provider_model``, ``prompt_snapshot``,
    ``seed_or_reproduction_data``).

    This test asserts the row's public shape does not carry any
    provider-identifier-flavored attribute — a mechanical guard
    against regressing to a Runway voice_id on the reference row.
    """
    fields = {f.name for f in CanonicalVoiceReference._meta.get_fields()}
    forbidden_hints = {
        "voice_id",
        "runway_voice_id",
        "elevenlabs_voice_id",
        "provider",
        "provider_id",
        "external_voice_id",
    }
    leak = fields & forbidden_hints
    assert not leak, (
        f"CanonicalVoiceReference exposes provider-namespaced "
        f"fields at its domain boundary: {leak}. Provider details "
        f"belong on GenerationRecord (§17.4.a)."
    )


# ---- CanonicalRealtimeReference ------------------------------------


def test_canonical_realtime_reference_round_trip() -> None:
    ws = _make_workspace("crr-round@t")
    version = _make_version(ws)
    record = _make_generation_record(version)

    ref = CanonicalRealtimeReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.RAW,
    )
    reloaded = CanonicalRealtimeReference.objects.get(pk=ref.pk)
    assert reloaded.state == "raw"


def test_canonical_realtime_reference_domain_contract_is_provider_neutral() -> None:
    """§17.10.a explicitly bars ``runway_avatar_id`` from the
    permanent canonical schema. The reference row must not carry a
    provider-namespaced avatar / realtime identifier at its domain
    boundary.
    """
    fields = {f.name for f in CanonicalRealtimeReference._meta.get_fields()}
    forbidden_hints = {
        "runway_avatar_id",
        "avatar_id",
        "provider",
        "provider_id",
        "external_avatar_id",
        "external_realtime_id",
    }
    leak = fields & forbidden_hints
    assert not leak, (
        f"CanonicalRealtimeReference exposes provider-namespaced "
        f"fields at its domain boundary: {leak}. Provider details "
        f"belong on GenerationRecord (§17.4.a, §17.10.a)."
    )


# ---- ApprovedRepresentationBundle ----------------------------------


def test_bundle_round_trip_draft() -> None:
    ws = _make_workspace("bundle-draft@t")
    version = _make_version(ws)

    bundle = ApprovedRepresentationBundle.objects.create(
        identity_version=version,
    )
    reloaded = ApprovedRepresentationBundle.objects.get(pk=bundle.pk)
    assert reloaded.state == "draft"
    assert reloaded.approved_voice is None
    assert reloaded.approved_realtime is None
    assert reloaded.approved_at is None
    assert reloaded.approved_by is None


def test_bundle_binds_canonical_refs_not_provider_ids() -> None:
    """§6, §17.4.a — the bundle field shape references canonical
    reference rows, not provider IDs or asset paths. Callers ask
    for ``approved_voice`` and receive a CanonicalVoiceReference;
    provider resolution happens under the reference at the
    adapter boundary.
    """
    ws = _make_workspace("bundle-neutral@t")
    version = _make_version(ws)
    record = _make_generation_record(version)
    voice = CanonicalVoiceReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.APPROVED,
    )
    realtime = CanonicalRealtimeReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.APPROVED,
    )

    bundle = ApprovedRepresentationBundle.objects.create(
        identity_version=version,
        approved_voice=voice,
        approved_realtime=realtime,
        state=ApprovedRepresentationBundle.State.APPROVED,
    )

    # The domain-facing accessors return canonical references — not
    # strings, ints, or provider identifiers.
    assert isinstance(bundle.approved_voice, CanonicalVoiceReference)
    assert isinstance(bundle.approved_realtime, CanonicalRealtimeReference)

    # Bundle shape does not carry any provider-namespaced field.
    bundle_fields = {f.name for f in ApprovedRepresentationBundle._meta.get_fields()}
    forbidden_hints = {
        "voice_id",
        "runway_voice_id",
        "runway_avatar_id",
        "avatar_id",
        "portrait_path",
        "provider",
        "provider_id",
    }
    leak = bundle_fields & forbidden_hints
    assert not leak, (
        f"ApprovedRepresentationBundle exposes provider-namespaced "
        f"fields at its domain boundary: {leak}. Provider details "
        f"belong on GenerationRecord under the canonical reference "
        f"(§17.4.a)."
    )


def test_bundle_does_not_carry_normalization_profile_field() -> None:
    """§15.6 / operator directive — ``NormalizationProfile`` is
    deferred from Step 2. The bundle must not carry a placeholder
    FK to a nonexistent table. Re-introducing the concept requires
    a contract amendment per §19.5.
    """
    bundle_fields = {f.name for f in ApprovedRepresentationBundle._meta.get_fields()}
    assert "normalization_profile" not in bundle_fields
