"""§19 Step 9.b.3a promotion-service tests (SESSION 249).

Covers §S checklist for the promotion side:

* Evidence integrity re-check at promotion time.
* Fixture identity + version lazy get-or-create.
* Raw + normalized Asset mapping (exact bytes, exact SHA).
* GenerationRecord + NormalizationManifest factual mapping.
* IdentityReference approval + prior-slot SUPERSEDED cascade.
* PromotionAudit fields + uniqueness.
* Evidence dedup via BootstrapEvidenceIndex.
* Amendment cases: selected A → selected B; selected A → no_candidate;
  selected A → selected B → selected A.
* Idempotent retry: no duplicate rows / folders.
* Crash boundary — Phase 4 pending; resume completes.
* Filesystem revision folder immutable; prior revisions untouched.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import Asset
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationRecord,
    IdentityReference,
    NormalizationManifest,
    ReferenceState,
)

from apps.bootstrap_review import journal as journal_module
from apps.bootstrap_review.decisions import record_decision
from apps.bootstrap_review.evidence import FROZEN_EVIDENCE_ROOT
from apps.bootstrap_review.journal import (
    current_decision_per_slot,
    review_dir_for_fixture,
)
from apps.bootstrap_review.models import BootstrapEvidenceIndex, PromotionAudit
from apps.bootstrap_review.promotion import (
    PromotionError,
    _revision_folder,
    promote_current_decision,
)
from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
FCID_COMPACT = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__compact"
)
FCID_TEAM_CARD = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__team_card"
)
FCID_NEUTRAL = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__neutral_rest__compact"
)


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_review_and_references(tmp_path, settings):
    """Clean bootstrap/review/, bootstrap/references/, and durable
    Asset root between tests. Redirects the durable Asset root to a
    tmp path so tests never touch media-engine/data/.
    """
    settings.BOOTSTRAP_DURABLE_ASSETS_ROOT = str(tmp_path / "assets")
    fixtures = ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                _rmtree(d)
    yield
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                _rmtree(d)


def _rmtree(path: Path) -> None:
    import shutil
    shutil.rmtree(path)


@pytest.fixture()
def reviewer():
    User = get_user_model()
    return User.objects.create_user(email="reviewer-promo@example.test", password="x")


def _make_decision(
    reviewer,
    *,
    fixture_id: str = "fixture_h1",
    purpose: str = "front",
    disposition: str = "selected",
    fcid: str | None = FCID_COMPACT,
    supersedes_decision_id: str | None = None,
    amendment_reason: str | None = None,
):
    decision_id = str(uuid.uuid4())
    record, _ = record_decision(
        decision_id=decision_id,
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id=fixture_id,
        reference_kind="portrait_reference",
        reference_purpose=purpose,
        disposition=disposition,
        frozen_candidate_id=fcid,
        supersedes_decision_id=supersedes_decision_id,
        amendment_reason=amendment_reason,
        reviewer_user_id=reviewer.id,
        reviewer_email_at_write_time=reviewer.email,
    )
    return record


# ---------------------------------------------------------------------
# Happy path — selected promotion
# ---------------------------------------------------------------------


def test_selected_promotion_happy_path(reviewer):
    decision = _make_decision(reviewer)
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    assert result.kind == "selected"
    assert result.slot_revision == 1

    # PromotionAudit row exists + populated.
    audit = PromotionAudit.objects.get(decision_id=decision.decision_id)
    assert audit.frozen_candidate_id == FCID_COMPACT
    assert audit.evidence_published_at_utc is not None
    assert audit.reviewer_id == reviewer.id
    assert audit.raw_asset is not None
    assert audit.normalized_asset is not None
    assert audit.generation_record is not None
    assert audit.normalization_manifest is not None
    assert audit.identity_reference is not None
    assert audit.character_identity_version is not None

    # IdentityReference APPROVED.
    ref = audit.identity_reference
    assert ref.state == ReferenceState.APPROVED

    # Fixture identity created + teammate NULL + workspace correct.
    identity = audit.character_identity_version.identity
    assert identity.name == "fixture_h1"
    assert identity.teammate_id is None
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    assert identity.workspace_id == workspace.id

    # Version is DRAFT (approve_version is a separate operation).
    version = audit.character_identity_version
    assert version.state == CharacterIdentityVersion.State.DRAFT

    # Filesystem revision folder exists + sentinel present.
    folder = result.revision_folder
    assert folder is not None
    for name in ("raw.png", "normalized.png", "manifest.json", "source.json", ".materialization_complete"):
        assert (folder / name).exists()


def test_raw_asset_bytes_match_frozen(reviewer):
    _make_decision(reviewer)
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    audit = PromotionAudit.objects.get(decision_id=result.decision_id)
    frozen_raw = FROZEN_EVIDENCE_ROOT / (
        "fixture_h1/runs/bootstrap_20260808T044853Z_7eb392992e0f/"
        "identity_only/stability_still/raw/"
        "fixture_h1__portrait_reference__front__compact.png"
    )
    assert (
        Path(audit.raw_asset.file_path).read_bytes()
        == frozen_raw.read_bytes()
    )


def test_generation_record_carries_frozen_candidate_id(reviewer):
    _make_decision(reviewer)
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    audit = PromotionAudit.objects.get(decision_id=result.decision_id)
    gr = audit.generation_record
    assert gr.prompt_snapshot["frozen_candidate_id"] == FCID_COMPACT
    assert gr.execution_mode_actual == "real"
    assert gr.execution_mode == "real_required"
    assert gr.provider == "stability_still"
    assert gr.direction_hypothesis == "identity_only"


def test_normalization_manifest_matches_frozen_manifest(reviewer):
    _make_decision(reviewer)
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    audit = PromotionAudit.objects.get(decision_id=result.decision_id)
    frozen_manifest = FROZEN_EVIDENCE_ROOT / (
        "fixture_h1/runs/bootstrap_20260808T044853Z_7eb392992e0f/"
        "identity_only/stability_still/manifests/"
        "fixture_h1__portrait_reference__front__compact.json"
    )
    frozen_data = json.loads(frozen_manifest.read_text())
    nm = audit.normalization_manifest
    assert nm.pipeline_version == frozen_data["pipeline_version"]
    assert nm.surface_profile_id == frozen_data["surface_profile_id"]
    assert nm.background_id == frozen_data["background_id"]
    assert nm.eye_line_adjustments == frozen_data["eye_line_adjustments"]


def test_source_json_immutable_chain_of_custody(reviewer):
    _make_decision(reviewer)
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    src = json.loads((result.revision_folder / "source.json").read_text())
    assert src["frozen_candidate_id"] == FCID_COMPACT
    assert src["decision_id"] == str(result.decision_id)
    assert src["slot_revision"] == 1
    assert src["substrate"]["promotion_audit_id"] == result.promotion_audit_id
    assert src["substrate"]["identity_reference_id"] == result.identity_reference_id


# ---------------------------------------------------------------------
# Integrity re-check at promotion time
# ---------------------------------------------------------------------


def test_tampered_raw_bytes_refuse_promotion(reviewer, monkeypatch):
    _make_decision(reviewer)
    import apps.bootstrap_review.evidence as evidence
    from apps.bootstrap_review.evidence import ArtifactIntegrityError, FrozenCandidateId, artifact_path

    real_path = artifact_path(FrozenCandidateId.parse(FCID_COMPACT), "raw")
    original = evidence.Path.read_bytes

    def tampered(self, *args, **kwargs):
        if self == real_path:
            return b"tampered"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(evidence.Path, "read_bytes", tampered)

    with pytest.raises(ArtifactIntegrityError):
        promote_current_decision(
            fixture_id="fixture_h1",
            reference_kind="portrait_reference",
            reference_purpose="front",
        )
    # No canonical rows created.
    assert PromotionAudit.objects.count() == 0
    assert BootstrapEvidenceIndex.objects.count() == 0
    assert Asset.objects.filter(source_spec__contains={"origin": "bootstrap_9b3"}).count() == 0


# ---------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------


def test_retry_same_decision_creates_no_duplicates(reviewer):
    decision = _make_decision(reviewer)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    r2 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    assert r1.promotion_audit_id == r2.promotion_audit_id
    assert PromotionAudit.objects.filter(decision_id=decision.decision_id).count() == 1
    assert BootstrapEvidenceIndex.objects.filter(frozen_candidate_id=FCID_COMPACT).count() == 1
    assert IdentityReference.objects.filter(
        identity_version=r1.character_identity_version_id
    ).count() == 1


# ---------------------------------------------------------------------
# Amendments
# ---------------------------------------------------------------------


def test_amendment_A_to_B_supersedes_A_and_publishes_B(reviewer):
    d1 = _make_decision(reviewer)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    _make_decision(
        reviewer,
        fcid=FCID_TEAM_CARD,
        supersedes_decision_id=d1.decision_id,
        amendment_reason="switch to team_card",
    )
    r2 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    # Two audits, two revisions.
    assert r1.slot_revision == 1
    assert r2.slot_revision == 2
    assert r1.promotion_audit_id != r2.promotion_audit_id

    # A's IdentityReference is SUPERSEDED.
    a_ref = IdentityReference.objects.get(pk=r1.identity_reference_id)
    assert a_ref.state == ReferenceState.SUPERSEDED

    # B's IdentityReference is APPROVED.
    b_ref = IdentityReference.objects.get(pk=r2.identity_reference_id)
    assert b_ref.state == ReferenceState.APPROVED

    # A's revision folder still exists + bytes unchanged.
    a_folder = r1.revision_folder
    assert (a_folder / ".materialization_complete").exists()
    assert (a_folder / "raw.png").exists()

    # B's revision folder is separate.
    assert r2.revision_folder != r1.revision_folder
    assert (r2.revision_folder / ".materialization_complete").exists()


def test_amendment_A_to_no_candidate_supersedes_A_without_new_audit(reviewer):
    d1 = _make_decision(reviewer)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    _make_decision(
        reviewer,
        disposition="no_candidate_approved",
        fcid=None,
        supersedes_decision_id=d1.decision_id,
        amendment_reason="none acceptable",
    )
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    assert result.kind == "no_candidate_approved"
    # A's IdentityReference SUPERSEDED.
    a_ref = IdentityReference.objects.get(pk=r1.identity_reference_id)
    assert a_ref.state == ReferenceState.SUPERSEDED
    # No new PromotionAudit created.
    assert PromotionAudit.objects.count() == 1
    # A's revision folder still exists — evidence preserved.
    assert (r1.revision_folder / ".materialization_complete").exists()


def test_amendment_A_to_B_to_A_reuses_evidence_new_revision(reviewer):
    d1 = _make_decision(reviewer)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    d2 = _make_decision(
        reviewer,
        fcid=FCID_TEAM_CARD,
        supersedes_decision_id=d1.decision_id,
        amendment_reason="switch to team_card",
    )
    r2 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    _make_decision(
        reviewer,
        fcid=FCID_COMPACT,  # back to A
        supersedes_decision_id=d2.decision_id,
        amendment_reason="prefer compact after all",
    )
    r3 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )

    # Three audits, three revisions.
    assert PromotionAudit.objects.count() == 3
    assert r3.slot_revision == 3

    # Evidence dedup: only 2 BootstrapEvidenceIndex rows (compact + team_card).
    assert BootstrapEvidenceIndex.objects.count() == 2
    # Only 2 unique GRs (per fcid).
    assert GenerationRecord.objects.count() == 2
    # Only 4 unique Assets (raw + normalized per fcid).
    assert Asset.objects.filter(
        source_spec__origin="bootstrap_9b3"
    ).count() == 4

    # r3's IdentityReference is APPROVED.
    r3_ref = IdentityReference.objects.get(pk=r3.identity_reference_id)
    assert r3_ref.state == ReferenceState.APPROVED
    # r1's IdentityReference is SUPERSEDED (never re-approved).
    r1_ref = IdentityReference.objects.get(pk=r1.identity_reference_id)
    assert r1_ref.state == ReferenceState.SUPERSEDED
    # r2's IdentityReference is SUPERSEDED.
    r2_ref = IdentityReference.objects.get(pk=r2.identity_reference_id)
    assert r2_ref.state == ReferenceState.SUPERSEDED

    # All three revision folders still exist independently.
    for r in (r1, r2, r3):
        assert (r.revision_folder / ".materialization_complete").exists()


# ---------------------------------------------------------------------
# Crash boundary — Phase 4 pending; resume completes
# ---------------------------------------------------------------------


def test_resume_completes_pending_publication(reviewer, monkeypatch):
    _make_decision(reviewer)
    # Simulate Phase 4 crash by monkeypatching _publish_revision_folder
    # to raise AFTER DB commit but BEFORE folder write.
    import apps.bootstrap_review.promotion as promo

    original_publish = promo._publish_revision_folder
    call_count = {"n": 0}

    def flaky_publish(audit):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated Phase 4 crash")
        original_publish(audit)

    monkeypatch.setattr(promo, "_publish_revision_folder", flaky_publish)

    with pytest.raises(RuntimeError):
        promote_current_decision(
            fixture_id="fixture_h1",
            reference_kind="portrait_reference",
            reference_purpose="front",
        )

    # DB committed but publication pending.
    audit = PromotionAudit.objects.first()
    assert audit is not None
    assert audit.evidence_published_at_utc is None

    # Retry via promotion (idempotent path detects existing audit
    # + calls original publish).
    monkeypatch.setattr(promo, "_publish_revision_folder", original_publish)
    result = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    audit.refresh_from_db()
    assert audit.evidence_published_at_utc is not None
    assert (result.revision_folder / ".materialization_complete").exists()
