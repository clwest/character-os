"""§19 Step 9.b.3a promotion service (SESSION 249).

Materializes an already-recorded reviewer decision into canonical
substrate + immutable bootstrap-reference filesystem revision.

Load-bearing invariants (all asserted by tests):

* The current terminal decision in the append-only journal is the
  ONLY authority. Callers pass ``(fixture_id, reference_kind,
  reference_purpose)`` — the service reads the current decision
  itself. Never accepts arbitrary provider/profile/path metadata.
* Only ``disposition == 'selected'`` produces canonical rows.
  ``no_candidate_approved`` is DB-only: transitions any prior
  APPROVED reference to SUPERSEDED via
  ``services.supersede_reference_at_slot``. Journal remains the
  durable record.
* Integrity re-check at PROMOTION time — SHA-256 verification of
  raw + normalized + manifest against ``candidate.json``. Failure
  raises loudly; no substrate rows, no filesystem revision.
* Evidence dedup by ``frozen_candidate_id`` via
  :class:`BootstrapEvidenceIndex` (Finding 8). Race-safe under
  concurrent inserts; single retry on ``IntegrityError``.
* PromotionAudit ``unique(decision_id)`` is the retry idempotency
  key (Finding 7).
* Filesystem revision folder ``bootstrap/references/<kind>/
  <purpose>/<NNN>/`` is immutable after publication (temp sibling
  + atomic rename); prior revisions are never touched.
* No FS+DB atomicity pretense. Phase 3 (DB) commits first, Phase 4
  (FS publish) runs post-commit. If Phase 4 crashes,
  ``evidence_published_at_utc`` stays NULL and the resume command
  finishes publication idempotently.
* Zero provider generation. Zero normalization pipeline execution.
  Zero rembg / Pillow / opencv imports (enforced by 9.b.0's AST
  boundary test which walks every ``*.py`` under this app).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings as django_settings
from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetRole, AssetType
from apps.identity import services as identity_services
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    ExecutionMode,
    ExecutionModeActual,
    GenerationApprovalState,
    GenerationProvider,
    IdentityReference,
    IdentityReferenceKind,
    ReferenceState,
)

from .evidence import (
    FROZEN_EVIDENCE_ROOT,
    ArtifactAbsent,
    ArtifactIntegrityError,
    EvidenceError,
    FrozenCandidateId,
    load_candidate_json,
    read_artifact_bytes,
)
from .journal import (
    DecisionRecord,
    current_decision_per_slot,
)
from .models import BootstrapEvidenceIndex, PromotionAudit
from .workspace import BOOTSTRAP_WORKSPACE_SLUG


# ---------------------------------------------------------------------
# Exceptions — stable domain vocabulary
# ---------------------------------------------------------------------


class PromotionError(Exception):
    code: str = "promotion_error"


class NoCurrentDecision(PromotionError):
    code = "no_current_decision"


class DecisionNotPromotable(PromotionError):
    """Raised when the current decision has a shape 9.b.3a cannot
    promote (e.g. missing fcid on a supposedly-selected decision)."""

    code = "decision_not_promotable"


class DurableAssetsRoot(PromotionError):
    """Raised when the durable Asset directory cannot be created."""

    code = "durable_assets_root_missing"


# ---------------------------------------------------------------------
# Filesystem paths — durable Assets + bootstrap references
# ---------------------------------------------------------------------


def _durable_assets_root() -> Path:
    """Root under which promoted Asset files live.

    Uses ``BOOTSTRAP_DURABLE_ASSETS_ROOT`` from settings if set;
    otherwise defaults to ``<repo>/media-engine/data/_assets/
    bootstrap/``. Both callers exercise this path via
    :func:`~apps.bootstrap_review.evidence.FROZEN_EVIDENCE_ROOT`'s
    grandparent so tests can point it elsewhere if needed.
    """
    override = getattr(django_settings, "BOOTSTRAP_DURABLE_ASSETS_ROOT", None)
    if override:
        return Path(override).resolve()
    return (
        Path(django_settings.BASE_DIR).parent
        / "media-engine"
        / "data"
        / "_assets"
        / "bootstrap"
    ).resolve()


def _bootstrap_references_dir(fixture_id: str, kind: str, purpose: str) -> Path:
    return (
        FROZEN_EVIDENCE_ROOT
        / fixture_id
        / "bootstrap"
        / "references"
        / kind
        / purpose
    )


def _revision_folder(
    fixture_id: str, kind: str, purpose: str, slot_revision: int
) -> Path:
    return _bootstrap_references_dir(fixture_id, kind, purpose) / (
        f"{slot_revision:03d}"
    )


# ---------------------------------------------------------------------
# Public service surface
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class PromotionResult:
    kind: str  # "selected" | "no_candidate_approved" | "noop_current_decision_matches_prior_state"
    decision_id: str
    promotion_audit_id: str | None = None
    character_identity_version_id: str | None = None
    identity_reference_id: str | None = None
    superseded_identity_reference_id: str | None = None
    slot_revision: int | None = None
    revision_folder: Path | None = None


def promote_current_decision(
    *,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> PromotionResult:
    """Materialize the current terminal decision at
    ``(fixture_id, reference_kind, reference_purpose)`` into
    canonical substrate + filesystem revision.

    Reads the current decision from the append-only journal. Refuses
    if the slot has no current decision (``NoCurrentDecision``).
    Dispatches by disposition:

    * ``selected`` → full Phase 1–5 materialization.
    * ``no_candidate_approved`` → DB-only supersede via
      :func:`identity_services.supersede_reference_at_slot`.

    Idempotent: retry with the same current decision (same
    ``decision_id``) returns the stored ``PromotionAudit`` without
    duplicating rows or filesystem revisions. Retry after a Phase 4
    crash completes only the pending publication.
    """
    current = current_decision_per_slot(fixture_id).get(
        (reference_kind, reference_purpose)
    )
    if current is None:
        raise NoCurrentDecision(
            f"slot ({fixture_id!r}, {reference_kind!r}, "
            f"{reference_purpose!r}) has no current decision"
        )

    decision_id = current["decision_id"]
    disposition = current["disposition"]

    if disposition == "selected":
        return _promote_selected(current)
    if disposition == "no_candidate_approved":
        return _promote_no_candidate_approved(current)
    raise DecisionNotPromotable(
        f"decision_id={decision_id!r} carries unsupported disposition "
        f"{disposition!r}"
    )


# ---------------------------------------------------------------------
# Selected promotion — Phase 1–4
# ---------------------------------------------------------------------


def _promote_selected(current: dict) -> PromotionResult:
    """Materialize a ``selected`` decision.

    Phase 1 — decision validation + integrity re-check.
    Phase 2 — copy raw + normalized bytes to durable Asset paths.
    Phase 3 — DB transaction: fixture identity + version + Assets +
              GR + NM + IdentityReference + PromotionAudit.
    Phase 4 — Publish immutable revision folder + mark
              ``evidence_published_at_utc``.
    """
    decision_id = current["decision_id"]
    frozen_candidate_id = current["frozen_candidate_id"]
    fixture_id = current["fixture_id"]
    reference_kind = current["reference_kind"]
    reference_purpose = current["reference_purpose"]
    reviewer_user_id = current["reviewer_user_id"]

    if not frozen_candidate_id:
        raise DecisionNotPromotable(
            f"decision_id={decision_id!r} disposition='selected' but "
            "frozen_candidate_id is null"
        )

    # --- Idempotent short-circuit ---------------------------------------
    existing_audit = PromotionAudit.objects.filter(decision_id=decision_id).first()
    if existing_audit is not None:
        if existing_audit.evidence_published_at_utc is None:
            # Phase 4 pending — resume publication.
            _publish_revision_folder(existing_audit)
        return _result_from_audit(existing_audit)

    # --- Phase 1: full integrity re-check ------------------------------
    fcid = FrozenCandidateId.parse(frozen_candidate_id)
    if fcid.fixture_id != fixture_id:
        raise DecisionNotPromotable(
            f"fcid.fixture_id={fcid.fixture_id!r} != slot.fixture_id={fixture_id!r}"
        )
    if fcid.reference_kind != reference_kind:
        raise DecisionNotPromotable(
            f"fcid.reference_kind={fcid.reference_kind!r} != slot={reference_kind!r}"
        )
    if fcid.reference_purpose != reference_purpose:
        raise DecisionNotPromotable(
            f"fcid.reference_purpose={fcid.reference_purpose!r} != slot={reference_purpose!r}"
        )
    candidate = load_candidate_json(fcid)
    if candidate.get("outcome") != "success":
        raise DecisionNotPromotable(
            f"candidate outcome={candidate.get('outcome')!r} not 'success'"
        )
    provider_stage = candidate.get("provider_stage") or {}
    if provider_stage.get("actual_execution_mode") != "real":
        raise DecisionNotPromotable(
            f"candidate execution not real: "
            f"{provider_stage.get('actual_execution_mode')!r}"
        )
    norm_stage = candidate.get("normalization_stage") or {}
    if norm_stage.get("outcome") != "success":
        raise DecisionNotPromotable(
            f"normalization outcome={norm_stage.get('outcome')!r} not 'success'"
        )
    # SHA-256 re-verify all three artifacts. Raises loudly.
    raw_bytes = read_artifact_bytes(fcid, "raw")
    normalized_bytes = read_artifact_bytes(fcid, "normalized")
    manifest_bytes = read_artifact_bytes(fcid, "manifest")

    # --- Phase 2: durable Asset materialization -------------------------
    reviewer_uuid = uuid.uuid4()
    durable_dir = _durable_assets_root() / decision_id
    durable_dir.mkdir(parents=True, exist_ok=True)
    raw_path = durable_dir / f"{reviewer_uuid}-raw.png"
    normalized_path = durable_dir / f"{reviewer_uuid}-normalized.png"
    raw_path.write_bytes(raw_bytes)
    normalized_path.write_bytes(normalized_bytes)
    _verify_sha256(raw_path, provider_stage_sha=candidate["raw_artifact"]["sha256_hex"])
    _verify_sha256(
        normalized_path,
        provider_stage_sha=norm_stage["normalized_artifact"]["sha256_hex"],
    )

    # --- Phase 3: DB transaction (retry once on evidence-index race) ----
    audit: PromotionAudit | None = None
    last_exc: IntegrityError | None = None
    for attempt in range(2):
        try:
            audit = _phase_3_db_transaction(
                current=current,
                fcid=fcid,
                candidate=candidate,
                raw_bytes_sha=hashlib.sha256(raw_bytes).hexdigest(),
                normalized_bytes_sha=hashlib.sha256(normalized_bytes).hexdigest(),
                raw_path=raw_path,
                normalized_path=normalized_path,
                reviewer_user_id=reviewer_user_id,
            )
            break
        except IntegrityError as exc:
            last_exc = exc
            if attempt == 0 and "frozen_candidate_id" in str(exc):
                # Race: another writer created the BootstrapEvidenceIndex
                # row between our read and write. Retry — the second
                # attempt sees the winner's row and reuses it.
                continue
            raise
    if audit is None:
        # Loop exhausted without success (shouldn't reach here given
        # the raise inside the except, but Pyright wants the guard).
        raise last_exc or PromotionError("Phase 3 exhausted retries")

    # --- Phase 4: publish immutable revision folder ---------------------
    _publish_revision_folder(audit)
    return _result_from_audit(audit)


def _phase_3_db_transaction(
    *,
    current: dict,
    fcid: FrozenCandidateId,
    candidate: dict,
    raw_bytes_sha: str,
    normalized_bytes_sha: str,
    raw_path: Path,
    normalized_path: Path,
    reviewer_user_id: int,
) -> PromotionAudit:
    with transaction.atomic():
        workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
        identity = _get_or_create_fixture_identity(workspace, fcid.fixture_id)
        version = _get_or_create_draft_version(identity, fcid.fixture_id)

        # Evidence dedup by fcid.
        index = BootstrapEvidenceIndex.objects.filter(
            frozen_candidate_id=fcid.value
        ).first()
        if index is not None:
            raw_asset = index.raw_asset
            normalized_asset = index.normalized_asset
            gr = index.generation_record
            nm = index.normalization_manifest
        else:
            raw_asset = _create_asset(
                workspace=workspace,
                fcid=fcid,
                file_path=raw_path,
                sha256_hex=raw_bytes_sha,
                role_in_pair="raw",
                reviewer_user_id=reviewer_user_id,
            )
            normalized_asset = _create_asset(
                workspace=workspace,
                fcid=fcid,
                file_path=normalized_path,
                sha256_hex=normalized_bytes_sha,
                role_in_pair="normalized",
                reviewer_user_id=reviewer_user_id,
            )
            gr = _create_generation_record(
                version=version,
                fcid=fcid,
                candidate=candidate,
                raw_asset=raw_asset,
                normalized_asset=normalized_asset,
                current=current,
            )
            nm = _create_normalization_manifest(
                gr=gr,
                candidate=candidate,
                raw_asset=raw_asset,
                normalized_asset=normalized_asset,
            )
            BootstrapEvidenceIndex.objects.create(
                frozen_candidate_id=fcid.value,
                raw_asset=raw_asset,
                normalized_asset=normalized_asset,
                generation_record=gr,
                normalization_manifest=nm,
            )

        # IdentityReference: new row per promotion; existing approve
        # cascade transitions any prior APPROVED reference at the
        # same slot to SUPERSEDED.
        ref = identity_services.attach_reference(
            version,
            asset=raw_asset,
            kind=fcid.reference_kind,
            purpose=fcid.reference_purpose,
            state=ReferenceState.RAW,
            generation_record=gr,
        )
        identity_services.approve_reference(ref)
        ref.refresh_from_db()

        # Compute slot_revision — one higher than max existing on
        # this (version, kind, purpose) tuple.
        max_rev = (
            PromotionAudit.objects.filter(
                character_identity_version=version,
                reference_kind=fcid.reference_kind,
                reference_purpose=fcid.reference_purpose,
            )
            .order_by("-slot_revision")
            .values_list("slot_revision", flat=True)
            .first()
        )
        slot_revision = (max_rev or 0) + 1

        audit = PromotionAudit.objects.create(
            decision_id=current["decision_id"],
            frozen_candidate_id=fcid.value,
            bootstrap_run_id=fcid.run_id,
            fixture_id=fcid.fixture_id,
            direction=fcid.direction,
            provider=fcid.provider,
            cell_id=fcid.cell_id,
            reference_kind=fcid.reference_kind,
            reference_purpose=fcid.reference_purpose,
            surface_profile=fcid.surface_profile,
            slot_revision=slot_revision,
            reviewer_id=reviewer_user_id,
            raw_asset=raw_asset,
            normalized_asset=normalized_asset,
            generation_record=gr,
            normalization_manifest=nm,
            identity_reference=ref,
            character_identity_version=version,
            substrate_committed_at_utc=datetime.now(timezone.utc),
        )
    return audit


# ---------------------------------------------------------------------
# no_candidate_approved promotion — DB-only supersede
# ---------------------------------------------------------------------


def _promote_no_candidate_approved(current: dict) -> PromotionResult:
    """Handle a ``no_candidate_approved`` current decision.

    Journal-driven per Finding 9. Creates no PromotionAudit row.
    Transitions the current APPROVED IdentityReference at the slot
    (if any) to SUPERSEDED via
    :func:`identity_services.supersede_reference_at_slot`.
    Idempotent — repeated calls are no-ops.
    """
    fixture_id = current["fixture_id"]
    reference_kind = current["reference_kind"]
    reference_purpose = current["reference_purpose"]

    workspace = Workspace.objects.filter(slug=BOOTSTRAP_WORKSPACE_SLUG).first()
    if workspace is None:
        # No workspace → no possible prior reference. No-op.
        return PromotionResult(
            kind="noop_current_decision_matches_prior_state",
            decision_id=current["decision_id"],
        )
    identity = CharacterIdentity.objects.filter(
        workspace=workspace, name=fixture_id
    ).first()
    if identity is None:
        # No identity → nothing to supersede.
        return PromotionResult(
            kind="noop_current_decision_matches_prior_state",
            decision_id=current["decision_id"],
        )
    version = (
        CharacterIdentityVersion.objects.filter(identity=identity)
        .order_by("-revision")
        .first()
    )
    if version is None:
        return PromotionResult(
            kind="noop_current_decision_matches_prior_state",
            decision_id=current["decision_id"],
        )

    superseded = identity_services.supersede_reference_at_slot(
        version,
        kind=reference_kind,
        purpose=reference_purpose,
        reason=(
            f"no_candidate_approved decision_id={current['decision_id']}"
        ),
    )
    return PromotionResult(
        kind="no_candidate_approved",
        decision_id=current["decision_id"],
        character_identity_version_id=str(version.id),
        superseded_identity_reference_id=(
            str(superseded.id) if superseded else None
        ),
    )


# ---------------------------------------------------------------------
# Phase 4 — filesystem revision publication
# ---------------------------------------------------------------------


def _publish_revision_folder(audit: PromotionAudit) -> None:
    """Publish the immutable revision folder for a committed
    PromotionAudit. Idempotent — safe to call multiple times.

    Uses a temp sibling directory + atomic ``os.rename``. The
    ``.materialization_complete`` sentinel inside the folder is the
    "publication succeeded" marker; its presence blocks re-publication.
    """
    target = _revision_folder(
        audit.fixture_id,
        audit.reference_kind,
        audit.reference_purpose,
        audit.slot_revision,
    )
    sentinel = target / ".materialization_complete"
    if sentinel.exists():
        # Already published; idempotent no-op. Still stamp the
        # timestamp if it's NULL (recovery after a race where the
        # sentinel landed but the timestamp update didn't).
        if audit.evidence_published_at_utc is None:
            PromotionAudit.objects.filter(pk=audit.pk).update(
                evidence_published_at_utc=datetime.now(timezone.utc)
            )
            audit.refresh_from_db()
        return

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)

    tmp = Path(
        tempfile.mkdtemp(
            prefix=f".{audit.slot_revision:03d}.",
            suffix=".tmp",
            dir=str(parent),
        )
    )
    try:
        # Copy from durable Asset paths — those are the canonical
        # bytes referenced by the DB row.
        shutil.copyfile(audit.raw_asset.file_path, tmp / "raw.png")
        shutil.copyfile(
            audit.normalized_asset.file_path, tmp / "normalized.png"
        )
        # Manifest bytes: reconstruct canonical from the frozen manifest
        # file. This byte-perfectly reproduces the Step 9.a evidence.
        fcid = FrozenCandidateId.parse(audit.frozen_candidate_id)
        manifest_source = FROZEN_EVIDENCE_ROOT / (
            f"{fcid.fixture_id}/runs/{fcid.run_id}/{fcid.direction}/"
            f"{fcid.provider}/manifests/{fcid.cell_id}.json"
        )
        shutil.copyfile(manifest_source, tmp / "manifest.json")
        # source.json — immutable per-revision chain-of-custody.
        source_json = {
            "promoted_at_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_candidate_id": audit.frozen_candidate_id,
            "bootstrap_run_id": audit.bootstrap_run_id,
            "fixture_id": audit.fixture_id,
            "direction": audit.direction,
            "provider": audit.provider,
            "cell_id": audit.cell_id,
            "reference_kind": audit.reference_kind,
            "reference_purpose": audit.reference_purpose,
            "surface_profile": audit.surface_profile,
            "slot_revision": audit.slot_revision,
            "decision_id": str(audit.decision_id),
            "reviewer_user_id": audit.reviewer_id,
            "raw_sha256": audit.raw_asset.source_spec.get("sha256"),
            "normalized_sha256": audit.normalized_asset.source_spec.get(
                "sha256"
            ),
            "substrate": {
                "promotion_audit_id": str(audit.id),
                "character_identity_version_id": str(
                    audit.character_identity_version_id
                ),
                "identity_reference_id": str(audit.identity_reference_id),
                "generation_record_id": str(audit.generation_record_id),
                "normalization_manifest_id": str(
                    audit.normalization_manifest_id
                ),
                "raw_asset_id": str(audit.raw_asset_id),
                "normalized_asset_id": str(audit.normalized_asset_id),
            },
        }
        (tmp / "source.json").write_text(
            json.dumps(source_json, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        # Sentinel LAST — its presence means the revision is complete.
        (tmp / ".materialization_complete").write_text(
            datetime.now(timezone.utc).isoformat(), encoding="utf-8"
        )
        # Atomic rename into final target. If target already exists
        # from a partial prior attempt, rmtree it first — that folder
        # never got a sentinel so is definitionally incomplete.
        if target.exists():
            shutil.rmtree(target)
        tmp.rename(target)
    except Exception:
        # Clean up temp on any failure.
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        raise

    # Mark PromotionAudit.evidence_published_at_utc.
    PromotionAudit.objects.filter(pk=audit.pk).update(
        evidence_published_at_utc=datetime.now(timezone.utc)
    )
    audit.refresh_from_db()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _verify_sha256(path: Path, provider_stage_sha: str) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != provider_stage_sha:
        raise ArtifactIntegrityError(
            f"copied file {path.name} sha256 mismatch: "
            f"expected {provider_stage_sha}, got {actual}"
        )


def _get_or_create_fixture_identity(
    workspace: Workspace, fixture_id: str
) -> CharacterIdentity:
    identity, _ = CharacterIdentity.objects.get_or_create(
        workspace=workspace,
        name=fixture_id,
        defaults={
            "kind": CharacterIdentity.Kind.HUMAN,
        },
    )
    return identity


def _get_or_create_draft_version(
    identity: CharacterIdentity, fixture_id: str
) -> CharacterIdentityVersion:
    """Lazy get-or-create the draft bootstrap version for a fixture.

    First call parses the fixture's ``identity.yaml`` + calls
    ``services.create_draft_version`` (which validates the spec
    against the human branch schema). Subsequent calls reuse the
    existing draft.
    """
    existing = (
        CharacterIdentityVersion.objects.filter(
            identity=identity,
            state=CharacterIdentityVersion.State.DRAFT,
        )
        .order_by("-revision")
        .first()
    )
    if existing is not None:
        return existing
    # No draft yet — read fixture spec + create.
    spec = _load_fixture_spec(fixture_id)
    return identity_services.create_draft_version(
        identity,
        spec=spec,
        spec_schema_version=int(spec.get("spec_schema_version", 1)),
    )


def _load_fixture_spec(fixture_id: str) -> dict:
    path = FROZEN_EVIDENCE_ROOT / fixture_id / "identity.yaml"
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    # identity.yaml has a top-level spec section; the schema validates
    # the spec payload, not the wrapper. Handle either shape honestly.
    if isinstance(raw, dict) and "spec" in raw and isinstance(raw["spec"], dict):
        return raw["spec"]
    return raw


def _create_asset(
    *,
    workspace: Workspace,
    fcid: FrozenCandidateId,
    file_path: Path,
    sha256_hex: str,
    role_in_pair: str,
    reviewer_user_id: int,
) -> Asset:
    return Asset.objects.create(
        workspace=workspace,
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE,
        file_path=str(file_path),
        mime_type="image/png",
        size_bytes=file_path.stat().st_size,
        source_spec={
            "origin": "bootstrap_9b3",
            "frozen_candidate_id": fcid.value,
            "sha256": sha256_hex,
            "role_in_pair": role_in_pair,
        },
        created_by_id=reviewer_user_id,
    )


def _create_generation_record(
    *,
    version: CharacterIdentityVersion,
    fcid: FrozenCandidateId,
    candidate: dict,
    raw_asset: Asset,
    normalized_asset: Asset,
    current: dict,
) -> Any:
    provider_stage = candidate["provider_stage"]
    prompt_snapshot: dict = dict(provider_stage.get("prompt_snapshot") or {})
    prompt_snapshot["frozen_candidate_id"] = fcid.value
    seed = provider_stage.get("deterministic_seed")
    return identity_services.record_generation(
        version=version,
        provider=fcid.provider,
        provider_model=provider_stage.get("provider_model") or "",
        direction_hypothesis=fcid.direction,
        prompt_snapshot=prompt_snapshot,
        seed_or_reproduction_data={"seed": seed} if seed else None,
        raw_output_asset=raw_asset,
        normalized_output_asset=normalized_asset,
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        elapsed_ms=provider_stage.get("elapsed_ms"),
        approval_state=GenerationApprovalState.ADMITTED_TO_BUNDLE,
        reviewer_notes={
            "decision_id": current["decision_id"],
            "reason": current.get("amendment_reason") or "",
        },
    )


def _create_normalization_manifest(
    *,
    gr: Any,
    candidate: dict,
    raw_asset: Asset,
    normalized_asset: Asset,
) -> Any:
    payload = candidate["normalization_stage"]["manifest_payload"]
    return identity_services.record_normalization_manifest(
        generation_record=gr,
        raw_output_asset=raw_asset,
        normalized_output_asset=normalized_asset,
        pipeline_version=payload["pipeline_version"],
        surface_profile_id=payload["surface_profile_id"],
        surface_profile_version=payload["surface_profile_version"],
        background_id=payload["background_id"],
        stages_executed=payload.get("stages_executed") or [],
        stages_skipped=payload.get("stages_skipped") or [],
        eye_line_adjustments=payload.get("eye_line_adjustments") or {},
        crop_metadata=payload.get("crop_metadata") or {},
        execution_duration_ms=int(payload.get("execution_duration_ms") or 0),
    )


def _result_from_audit(audit: PromotionAudit) -> PromotionResult:
    return PromotionResult(
        kind="selected",
        decision_id=str(audit.decision_id),
        promotion_audit_id=str(audit.id),
        character_identity_version_id=str(audit.character_identity_version_id),
        identity_reference_id=str(audit.identity_reference_id),
        slot_revision=audit.slot_revision,
        revision_folder=_revision_folder(
            audit.fixture_id,
            audit.reference_kind,
            audit.reference_purpose,
            audit.slot_revision,
        ),
    )
