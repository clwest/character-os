"""3.b import-service tests — Step 3's exclusive write path.

Covers every ratified amendment from the SESSION 242 gate:

* Amendment A — empty teammates get ``nothing_to_import``.
* Amendment B — one legacy GenerationRecord per representation
  class; no shared record across classes.
* Amendment C — ApprovedRepresentationBundle only when at least
  one of voice / realtime lands.
* Amendment D — ``skipped_authored`` is defensible because
  per-teammate atomicity ensures Step 3 cannot leave a
  half-imported shape behind.
* Amendment E — provenance snapshot is scope-limited to the
  three legacy identity fields + identity-page text.
* Amendment F — classifier and importer agree; dry-run reports
  match real-run classification exactly.
* Amendment G — malformed values are refused as
  ``failed_incompatible``; no silent normalization beyond
  ``.strip()`` on trivial whitespace noise.

Also validates the write-path isolation ratified at session open:
``services.approve_version`` is never called during import.
"""
from __future__ import annotations

import uuid
from unittest import mock

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetRole, AssetType
from apps.identity import import_service, services
from apps.identity.models import (
    LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
    ApprovedRepresentationBundle,
    CanonicalRealtimeReference,
    CanonicalVoiceReference,
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    ImportProvenance,
    ReferenceState,
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


def _make_teammate(
    ws: Workspace,
    *,
    name: str = "Ruby",
    portrait_path: str = "",
    voice_id: str = "",
    runway_avatar_id: str = "",
    **identity_fields,
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        portrait_path=portrait_path,
        voice_id=voice_id,
        runway_avatar_id=runway_avatar_id,
        **identity_fields,
    )


# ---- Amendment A: empty teammates ---------------------------------


def test_empty_teammate_reports_nothing_to_import() -> None:
    ws = _make_workspace("empty@t")
    teammate = _make_teammate(ws)
    result = import_service.import_legacy_teammate(
        teammate, run_id=uuid.uuid4(),
    )
    assert result.action == "nothing_to_import"
    assert CharacterIdentity.objects.filter(teammate=teammate).count() == 0
    assert ImportProvenance.objects.count() == 0


def test_teammate_with_only_identity_page_text_is_still_nothing_to_import() -> None:
    """Identity-page text alone (business_brief, personality, etc.)
    is NOT enough to trigger an import. Only the three legacy
    identity fields qualify (Amendment A).
    """
    ws = _make_workspace("only-text@t")
    teammate = _make_teammate(
        ws,
        business_brief="coffee roaster in Boulder",
        personality="warm, energetic, direct",
        who_you_help="local coffee drinkers",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "nothing_to_import"
    assert CharacterIdentity.objects.count() == 0


def test_whitespace_only_legacy_fields_are_stripped_and_report_nothing() -> None:
    """``.strip()`` handles trivial whitespace noise (allowed per
    Amendment G); the resulting empty values trigger
    nothing_to_import.
    """
    ws = _make_workspace("whitespace@t")
    teammate = _make_teammate(
        ws,
        portrait_path="   ",
        voice_id="\n\t",
        runway_avatar_id="",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "nothing_to_import"


# ---- Happy paths — per-representation-class GenerationRecords (B) ---


def test_full_teammate_creates_three_generation_records() -> None:
    """Amendment B — one legacy GenerationRecord per representation
    class. Portrait, voice, realtime each get their own.
    """
    ws = _make_workspace("full@t")
    teammate = _make_teammate(
        ws,
        portrait_path="https://cdn.example.com/ruby.png",
        voice_id="voice_abc123",
        runway_avatar_id="avatar_xyz789",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "imported"

    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    records = list(version.generation_records.all())
    assert len(records) == 3
    kinds = {r.prompt_snapshot["legacy_kind"] for r in records}
    assert kinds == {"portrait", "voice", "realtime"}
    for r in records:
        assert r.provider == GenerationProvider.LEGACY_IMPORTED
        # §17.10.a Amendment 3 — legacy-import rows carry NULL
        # execution fields because no adapter ever ran through
        # the execution framework for them. The pairing invariant
        # on GenerationRecord.clean() enforces this shape.
        assert r.execution_mode is None
        assert r.execution_mode_actual is None
        assert r.provider_model == ""  # unknown; Amendment G


def test_full_teammate_creates_all_representation_rows() -> None:
    ws = _make_workspace("full-rows@t")
    teammate = _make_teammate(
        ws,
        portrait_path="https://cdn.example.com/ruby.png",
        voice_id="voice_abc123",
        runway_avatar_id="avatar_xyz789",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "imported"

    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    assert version.state == "approved"
    assert version.spec_schema_version == LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION
    assert version.is_legacy_imported is True
    assert version.is_canonical_schema_validated is False
    assert version.is_qualification_eligible is False

    assert version.references.count() == 1
    portrait_ref = version.references.first()
    assert portrait_ref.kind == "portrait_reference"
    assert portrait_ref.purpose == "front"
    assert portrait_ref.state == ReferenceState.APPROVED
    assert portrait_ref.asset.workspace_id == ws.id
    assert portrait_ref.asset.role == AssetRole.REFERENCE_IMAGE
    assert portrait_ref.asset.asset_type == AssetType.IMAGE
    assert portrait_ref.asset.file_path == "https://cdn.example.com/ruby.png"

    assert version.canonical_voice_references.count() == 1
    voice_ref = version.canonical_voice_references.first()
    assert voice_ref.state == ReferenceState.APPROVED

    assert version.canonical_realtime_references.count() == 1
    realtime_ref = version.canonical_realtime_references.first()
    assert realtime_ref.state == ReferenceState.APPROVED

    # Bundle exists with both voice + realtime approved.
    bundle = version.representation_bundles.first()
    assert bundle is not None
    assert bundle.state == ApprovedRepresentationBundle.State.APPROVED
    assert bundle.approved_voice_id == voice_ref.id
    assert bundle.approved_realtime_id == realtime_ref.id


# ---- Amendment C: bundle only when relevant refs land -------------


def test_portrait_only_teammate_creates_no_bundle() -> None:
    """Amendment C — bundle binds voice + realtime. A portrait-only
    import ships an IdentityReference but zero bundles.
    """
    ws = _make_workspace("portrait-only@t")
    teammate = _make_teammate(
        ws,
        portrait_path="https://cdn.example.com/x.png",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "imported"
    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    assert version.references.count() == 1
    assert version.representation_bundles.count() == 0
    assert version.canonical_voice_references.count() == 0
    assert version.canonical_realtime_references.count() == 0


def test_voice_only_teammate_creates_bundle_with_voice_and_no_realtime() -> None:
    ws = _make_workspace("voice-only@t")
    teammate = _make_teammate(ws, voice_id="voice_abc")
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "imported"
    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    bundle = version.representation_bundles.first()
    assert bundle is not None
    assert bundle.approved_voice_id is not None
    assert bundle.approved_realtime is None
    assert version.references.count() == 0


def test_realtime_only_teammate_creates_bundle_with_realtime_and_no_voice() -> None:
    ws = _make_workspace("realtime-only@t")
    teammate = _make_teammate(ws, runway_avatar_id="avatar_abc")
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "imported"
    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    bundle = version.representation_bundles.first()
    assert bundle is not None
    assert bundle.approved_voice is None
    assert bundle.approved_realtime_id is not None


# ---- Amendment D: idempotency + atomicity coverage -----------------


def test_second_import_reports_already_imported() -> None:
    ws = _make_workspace("idempotent@t")
    teammate = _make_teammate(ws, portrait_path="https://cdn.example.com/x.png")
    run_1 = uuid.uuid4()
    r1 = import_service.import_legacy_teammate(teammate, run_id=run_1)
    assert r1.action == "imported"
    before_counts = (
        CharacterIdentity.objects.count(),
        CharacterIdentityVersion.objects.count(),
        IdentityReference.objects.count(),
        GenerationRecord.objects.count(),
        Asset.objects.filter(role=AssetRole.REFERENCE_IMAGE).count(),
        ImportProvenance.objects.count(),
    )
    r2 = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert r2.action == "already_imported"
    after_counts = (
        CharacterIdentity.objects.count(),
        CharacterIdentityVersion.objects.count(),
        IdentityReference.objects.count(),
        GenerationRecord.objects.count(),
        Asset.objects.filter(role=AssetRole.REFERENCE_IMAGE).count(),
        ImportProvenance.objects.count(),
    )
    assert before_counts == after_counts
    # §17.10.a Amendment 3 regression — after the SESSION 242
    # correction, first-time imports produce NULL / NULL execution
    # fields on every legacy GenerationRecord, and a re-import
    # (idempotent "already_imported") leaves them untouched. The
    # SESSION 242 shape (execution_mode == LEGACY_HISTORICAL) must
    # no longer appear.
    for r in GenerationRecord.objects.filter(
        provider=GenerationProvider.LEGACY_IMPORTED,
    ):
        assert r.execution_mode is None
        assert r.execution_mode_actual is None


def test_pre_existing_authored_identity_reports_skipped_authored() -> None:
    """A CharacterIdentity that predates Step 3 (or was created via
    the Step 2 authoritative service) exists WITHOUT ImportProvenance.
    Step 3 must refuse to overwrite it and report the shape as
    authored.
    """
    ws = _make_workspace("authored@t")
    teammate = _make_teammate(ws, portrait_path="https://cdn.example.com/x.png")
    # Pretend this teammate already has an authored canonical identity.
    CharacterIdentity.objects.create(
        workspace=ws,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name=teammate.name,
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "skipped_authored"
    assert ImportProvenance.objects.count() == 0


def test_per_teammate_atomicity_prevents_partial_half_state() -> None:
    """Amendment D — the shape "CharacterIdentity exists without
    ImportProvenance" cannot be left behind by a failed Step 3
    import because the per-teammate transaction rolls back the
    identity itself if the provenance write fails.

    Simulated by patching ImportProvenance.objects.create to raise
    after the identity + version + refs have landed inside the
    same transaction.
    """
    ws = _make_workspace("atomic@t")
    teammate = _make_teammate(ws, voice_id="voice_abc")

    original_create = ImportProvenance.objects.create

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated provenance write failure")

    with mock.patch.object(ImportProvenance.objects, "create", side_effect=_boom):
        result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())

    assert result.action == "failed"
    assert "simulated provenance write failure" in result.detail
    # Full rollback: nothing survives.
    assert CharacterIdentity.objects.filter(teammate=teammate).count() == 0
    assert CharacterIdentityVersion.objects.count() == 0
    assert CanonicalVoiceReference.objects.count() == 0
    assert GenerationRecord.objects.count() == 0
    # ImportProvenance.objects.create is restored automatically by the mock.
    assert ImportProvenance.objects.create == original_create


def test_atomic_failure_on_one_teammate_does_not_block_others() -> None:
    """Two teammates. First fails on the provenance write.
    Second imports normally.
    """
    ws = _make_workspace("atomic-others@t")
    fail_teammate = _make_teammate(
        ws, name="Fail", voice_id="voice_fail",
    )
    ok_teammate = _make_teammate(
        ws, name="Ok", voice_id="voice_ok",
    )

    call_count = {"n": 0}
    original_create = ImportProvenance.objects.create

    def _flaky(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("first-teammate failure")
        return original_create(*args, **kwargs)

    with mock.patch.object(ImportProvenance.objects, "create", side_effect=_flaky):
        r1 = import_service.import_legacy_teammate(fail_teammate, run_id=uuid.uuid4())
        r2 = import_service.import_legacy_teammate(ok_teammate, run_id=uuid.uuid4())

    assert r1.action == "failed"
    assert r2.action == "imported"
    assert CharacterIdentity.objects.filter(teammate=fail_teammate).count() == 0
    assert CharacterIdentity.objects.filter(teammate=ok_teammate).count() == 1


# ---- Amendment E: provenance snapshot scope -----------------------


def test_provenance_snapshot_is_scope_limited() -> None:
    ws = _make_workspace("snapshot@t")
    teammate = _make_teammate(
        ws,
        portrait_path="https://cdn.example.com/x.png",
        voice_id="voice_abc",
        runway_avatar_id="avatar_xyz",
        business_brief="brief",
        personality="pers",
        who_you_help="help",
        what_you_sell="sell",
        always_emphasize="emp",
        never_say="never",
        desired_feeling="feel",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    prov = ImportProvenance.objects.get(pk=result.provenance_id)

    assert set(prov.legacy_snapshot.keys()) == {
        "runway_avatar_id",
        "portrait_path",
        "voice_id",
        "identity_page_fields",
    }
    # Identity-page-fields subset is explicitly enumerated — not
    # a dump of every Teammate column. Confirm the expected keys
    # are present and nothing surprising like ``created_at`` or
    # ``updated_at`` snuck in.
    page = prov.legacy_snapshot["identity_page_fields"]
    for k in ("business_brief", "personality", "who_you_help",
              "what_you_sell", "always_emphasize", "never_say",
              "desired_feeling", "visual_subject", "visual_template",
              "tone_archetype"):
        assert k in page
    for forbidden in ("created_at", "updated_at", "id", "workspace_id"):
        assert forbidden not in page


def test_provenance_snapshot_schema_version_is_recorded() -> None:
    ws = _make_workspace("snapshot-version@t")
    teammate = _make_teammate(ws, voice_id="voice_abc")
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    prov = ImportProvenance.objects.get(pk=result.provenance_id)
    assert prov.snapshot_schema_version == 1
    assert prov.migration_version == "identity.0002_step3_legacy_provenance"


# ---- Amendment F: dry-run matches classification ------------------


def test_classify_teammate_matches_import_result_action_across_all_paths() -> None:
    ws = _make_workspace("classify-match@t")
    empty = _make_teammate(ws, name="Empty")
    portrait_only = _make_teammate(
        ws, name="Portrait", portrait_path="https://cdn.example.com/x.png",
    )
    malformed = _make_teammate(
        ws, name="Bad", portrait_path="not a url",
    )
    already_imported = _make_teammate(
        ws, name="Done", voice_id="v",
    )
    import_service.import_legacy_teammate(already_imported, run_id=uuid.uuid4())

    for teammate, expected in (
        (empty, "nothing_to_import"),
        (portrait_only, "imported"),
        (malformed, "failed_incompatible"),
        (already_imported, "already_imported"),
    ):
        cls = import_service.classify_teammate(teammate)
        assert cls.action == expected, teammate.name


def test_dry_run_writes_nothing_and_matches_classification() -> None:
    ws = _make_workspace("dryrun@t")
    teammate = _make_teammate(
        ws,
        portrait_path="https://cdn.example.com/x.png",
        voice_id="v",
    )
    dry = import_service.import_legacy_teammate(
        teammate, run_id=uuid.uuid4(), dry_run=True,
    )
    assert dry.action == "imported"
    # Zero writes.
    assert CharacterIdentity.objects.count() == 0
    assert CharacterIdentityVersion.objects.count() == 0
    assert IdentityReference.objects.count() == 0
    assert CanonicalVoiceReference.objects.count() == 0
    assert GenerationRecord.objects.count() == 0
    assert ImportProvenance.objects.count() == 0

    # And the same classifier call returns the same action.
    cls = import_service.classify_teammate(teammate)
    assert cls.action == dry.action


# ---- Amendment G: malformed values refused ------------------------


def test_malformed_portrait_path_reports_failed_incompatible() -> None:
    ws = _make_workspace("malformed@t")
    teammate = _make_teammate(
        ws,
        portrait_path="/local/relative/path.png",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "failed_incompatible"
    assert "portrait_path" in result.detail
    # Zero substrate writes when the classification fails.
    assert CharacterIdentity.objects.count() == 0


def test_malformed_portrait_with_other_valid_fields_still_refused() -> None:
    """A malformed portrait_path fails the whole teammate — we do
    not silently drop the bad field and import the rest.
    Preserving history means refusing to guess.
    """
    ws = _make_workspace("mixed-malformed@t")
    teammate = _make_teammate(
        ws,
        portrait_path="just-some-string",
        voice_id="voice_abc",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "failed_incompatible"
    assert CanonicalVoiceReference.objects.count() == 0


def test_data_uri_portrait_path_accepted() -> None:
    """Mock-mode + some real client responses produce data URIs
    for portraits (per Teammate.portrait_path docstring). These
    must import cleanly.
    """
    ws = _make_workspace("data-uri@t")
    teammate = _make_teammate(
        ws,
        portrait_path="data:image/png;base64,iVBORw0KGgo=",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    assert result.action == "imported"


# ---- Isolation from Step 2 write path -----------------------------


def test_import_never_calls_approve_version() -> None:
    """The Step 3 import service is explicitly isolated from
    ``services.approve_version`` (operator ratification 4).
    Legacy imports bypass the branch-schema approval floor by
    going around the Step 2 write path entirely.
    """
    ws = _make_workspace("no-approve-call@t")
    teammate = _make_teammate(ws, voice_id="voice_abc")
    with mock.patch.object(services, "approve_version") as spy:
        result = import_service.import_legacy_teammate(
            teammate, run_id=uuid.uuid4(),
        )
    assert result.action == "imported"
    spy.assert_not_called()


def test_imported_version_never_ran_through_branch_schema_floor() -> None:
    """The identity has zero approved portrait_reference/front and
    portrait_reference/neutral_rest references (the human branch
    floor from the ratified schema). If the imported version were
    routed through ``approve_version``, that call would raise
    ``floor_not_satisfied``. Because import bypasses it, the
    version is imported successfully.
    """
    ws = _make_workspace("floor-bypass@t")
    teammate = _make_teammate(ws, voice_id="voice_abc")
    result = import_service.import_legacy_teammate(
        teammate, run_id=uuid.uuid4(),
    )
    assert result.action == "imported"
    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    assert version.state == "approved"
    # No approved portrait_reference/front — the floor was never
    # evaluated for this version.
    assert version.references.filter(
        state=ReferenceState.APPROVED,
    ).count() == 0


# ---- Provider-neutrality: legacy identifiers stay under refs -------


def test_bundle_carries_no_legacy_provider_identifiers_at_domain_boundary() -> None:
    """§17.4.a + §17.10.a — the bundle exposes canonical refs
    only. Provider-side runway_avatar_id / voice_id live inside
    the generation record's prompt_snapshot, not on the bundle
    or the canonical reference rows.
    """
    ws = _make_workspace("neutrality@t")
    teammate = _make_teammate(
        ws,
        voice_id="voice_secret",
        runway_avatar_id="runway_avatar_secret",
    )
    result = import_service.import_legacy_teammate(teammate, run_id=uuid.uuid4())
    version = CharacterIdentityVersion.objects.get(pk=result.version_id)
    bundle = version.representation_bundles.first()

    # Bundle field values are canonical references — not strings.
    voice_ref = bundle.approved_voice
    realtime_ref = bundle.approved_realtime
    assert isinstance(voice_ref, CanonicalVoiceReference)
    assert isinstance(realtime_ref, CanonicalRealtimeReference)

    # Bundle row does not carry the legacy identifiers directly.
    bundle_field_names = {f.name for f in ApprovedRepresentationBundle._meta.get_fields()}
    for forbidden in ("voice_id", "runway_avatar_id", "runway_voice_id"):
        assert forbidden not in bundle_field_names

    # The legacy identifiers ARE recorded — inside the generation
    # records' prompt_snapshots. That is where provider provenance
    # lives per §17.4.a.
    voice_record = voice_ref.generation_record
    realtime_record = realtime_ref.generation_record
    assert voice_record.prompt_snapshot["legacy_value"] == "voice_secret"
    assert realtime_record.prompt_snapshot["legacy_value"] == "runway_avatar_secret"


# ---- CharacterIdentity partial-unique interaction with import -----


def test_import_run_id_groups_multiple_teammates() -> None:
    ws = _make_workspace("run-group@t")
    t1 = _make_teammate(ws, name="A", voice_id="a")
    t2 = _make_teammate(ws, name="B", voice_id="b")
    run_id = uuid.uuid4()
    import_service.import_legacy_teammate(t1, run_id=run_id)
    import_service.import_legacy_teammate(t2, run_id=run_id)
    grouped = ImportProvenance.objects.filter(import_run_id=run_id).count()
    assert grouped == 2
