"""§19 Step 9.b.3b end-to-end closure test.

Walks every human fixture through the complete review → promote →
admit-version pipeline via the SPA-facing REST API. Proves the
9.b.3b integration is honest: SPA calls only, backend does the
work, frozen 9.a evidence is untouched, all four fixtures become
Step-10 ready by close.

If this test passes, Step 9.b is fully complete and Step 10 can
open.
"""
from __future__ import annotations

import json
import uuid
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    IdentityReference,
    ReferenceState,
)

from apps.bootstrap_review.evidence import (
    AUTHORIZED_FIXTURE_IDS,
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    FROZEN_EVIDENCE_ROOT,
)
from apps.bootstrap_review.models import PromotionAudit
from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
HUMAN_FIXTURES = ["fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"]

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_state(tmp_path, settings):
    settings.BOOTSTRAP_DURABLE_ASSETS_ROOT = str(tmp_path / "assets")
    fixtures = ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                import shutil
                shutil.rmtree(d)
    yield
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                import shutil
                shutil.rmtree(d)


@pytest.fixture()
def operator():
    User = get_user_model()
    user = User.objects.create_user(email="operator-e2e@example.test", password="x")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture()
def client(operator):
    c = APIClient()
    c.force_authenticate(user=operator)
    return c


def _fcid(fixture_id, purpose):
    return (
        f"{FROZEN_RUN_ID}/identity_only/stability_still/"
        f"{fixture_id}__portrait_reference__{purpose}__compact"
    )


def _decide_url(fixture_id, purpose):
    return reverse(
        "bootstrap-review-slot-decisions",
        args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
    )


def _promote_url(fixture_id, purpose):
    return reverse(
        "bootstrap-review-slot-promote",
        args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
    )


def _approve_url(fixture_id):
    return reverse(
        "bootstrap-review-fixture-approve-version",
        args=[FROZEN_RUN_ID, fixture_id],
    )


def _post_decision(client, fixture_id, purpose, disposition, fcid):
    body = {
        "decision_id": str(uuid.uuid4()),
        "disposition": disposition,
        "frozen_candidate_id": fcid if disposition == "selected" else None,
        "supersedes_decision_id": None,
        "amendment_reason": None,
    }
    r = client.post(_decide_url(fixture_id, purpose), body, format="json")
    assert r.status_code == status.HTTP_201_CREATED, r.content


def _walk_fixture(client, fixture_id):
    """Full review → promote → admit-version pipeline for one fixture."""
    # Two required purposes: select + promote.
    for purpose in ("front", "neutral_rest"):
        _post_decision(
            client, fixture_id, purpose, "selected", _fcid(fixture_id, purpose)
        )
        r = client.post(_promote_url(fixture_id, purpose))
        assert r.status_code == status.HTTP_200_OK, r.content
        assert r.json()["kind"] == "selected"

    # Five optional purposes: no_candidate_approved.
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if purpose in ("front", "neutral_rest"):
            continue
        _post_decision(client, fixture_id, purpose, "no_candidate_approved", None)

    # Admit fixture identity for product use.
    r = client.post(_approve_url(fixture_id))
    assert r.status_code == status.HTTP_200_OK, r.content
    assert r.json()["state"] == "approved"


def test_full_pipeline_all_four_fixtures_become_step10_ready(client):
    """The load-bearing 9.b.3b closure test.

    Walks every human fixture through review → promote → admit via
    the HTTP surface. Asserts canonical substrate, PromotionAudit
    rows, filesystem revision folders, and the readiness command
    all agree.
    """
    from apps.accounts.models import Workspace

    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)

    for fixture_id in HUMAN_FIXTURES:
        _walk_fixture(client, fixture_id)

    # -- Canonical substrate: one CharacterIdentity + one APPROVED
    #    version per fixture; two APPROVED IdentityReferences per
    #    version (front + neutral_rest).
    for fixture_id in HUMAN_FIXTURES:
        identity = CharacterIdentity.objects.get(
            workspace=workspace, name=fixture_id
        )
        assert identity.teammate_id is None
        version = CharacterIdentityVersion.objects.get(
            identity=identity,
            state=CharacterIdentityVersion.State.APPROVED,
        )
        approved_refs = IdentityReference.objects.filter(
            identity_version=version, state=ReferenceState.APPROVED
        )
        approved_pairs = {(r.kind, r.purpose) for r in approved_refs}
        assert approved_pairs == {
            ("portrait_reference", "front"),
            ("portrait_reference", "neutral_rest"),
        }

    # -- PromotionAudit: 2 rows per fixture = 8 total.
    assert PromotionAudit.objects.count() == 8

    # -- Every promotion has evidence_published_at_utc set.
    assert PromotionAudit.objects.filter(
        evidence_published_at_utc__isnull=True
    ).count() == 0

    # -- Filesystem revision folder + sentinel present per promotion.
    for audit in PromotionAudit.objects.all():
        folder = (
            FROZEN_EVIDENCE_ROOT
            / audit.fixture_id
            / "bootstrap"
            / "references"
            / audit.reference_kind
            / audit.reference_purpose
            / f"{audit.slot_revision:03d}"
        )
        assert folder.exists()
        assert (folder / ".materialization_complete").exists()
        for artifact in ("raw.png", "normalized.png", "manifest.json", "source.json"):
            assert (folder / artifact).exists()

    # -- fixture_nh1 excluded — no CharacterIdentity in the workspace.
    assert not CharacterIdentity.objects.filter(
        workspace=workspace, name="fixture_nh1"
    ).exists()

    # -- Readiness helper (backend) — all four ready.
    from apps.bootstrap_review.readiness import derive_step10_readiness

    for fixture_id in HUMAN_FIXTURES:
        readiness = derive_step10_readiness(fixture_id)
        assert readiness.ready, (
            f"{fixture_id} not Step-10 ready: failures={readiness.failures}"
        )

    # -- CLI command exits 0 across all fixtures.
    out = StringIO()
    call_command("bootstrap_review_gate", "--all-fixtures", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["all_ready"] is True
    assert len(payload["reports"]) == 4


def test_gate_command_reports_all_authorized_fixture_ids(client):
    from apps.bootstrap_review.readiness import derive_step10_readiness

    out = StringIO()
    with pytest.raises(SystemExit):
        call_command("bootstrap_review_gate", "--all-fixtures", stdout=out)
    payload = json.loads(out.getvalue())
    ids = sorted(r["fixture_id"] for r in payload["reports"])
    assert ids == sorted(AUTHORIZED_FIXTURE_IDS)


def test_frozen_9a_evidence_still_untouched_after_full_pipeline(client):
    """After the entire E2E walk, `git status --porcelain` on the
    frozen 9.a subtree (runs/, _runs/, identity.yaml, rationale.md)
    reports empty. Only bootstrap/review/ + bootstrap/references/
    have new writes.
    """
    import subprocess

    for fixture_id in HUMAN_FIXTURES:
        _walk_fixture(client, fixture_id)

    from django.conf import settings

    repo_root = Path(settings.BASE_DIR).parent
    frozen_paths = [
        "docs/design/visual/portrait_qualification/fixtures/_runs/",
    ]
    for fixture_id in HUMAN_FIXTURES + ["fixture_nh1"]:
        frozen_paths.extend(
            [
                f"docs/design/visual/portrait_qualification/fixtures/{fixture_id}/runs/",
                f"docs/design/visual/portrait_qualification/fixtures/{fixture_id}/identity.yaml",
                f"docs/design/visual/portrait_qualification/fixtures/{fixture_id}/rationale.md",
            ]
        )
    result = subprocess.run(
        ["git", "status", "--porcelain", *frozen_paths],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"git not available: {result.stderr}")
    assert result.stdout == "", (
        f"Frozen 9.a subtree not clean after E2E walk: {result.stdout}"
    )
