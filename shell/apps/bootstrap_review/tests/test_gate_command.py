"""Tests for the ``bootstrap_review_gate`` management command."""
from __future__ import annotations

import json
import uuid
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from apps.identity import services as identity_services
from apps.identity.models import CharacterIdentityVersion

from apps.bootstrap_review.decisions import record_decision
from apps.bootstrap_review.evidence import (
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    FROZEN_EVIDENCE_ROOT,
)
from apps.bootstrap_review.promotion import promote_current_decision

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
FCID_FRONT = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__compact"
)
FCID_NEUTRAL = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__neutral_rest__compact"
)

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
def reviewer():
    User = get_user_model()
    return User.objects.create_user(email="gate@example.test", password="x")


def _promote_all_purposes(reviewer, fixture_id):
    """Full happy-path promotion for one fixture."""
    for purpose, fcid in (
        ("front", FCID_FRONT.replace("fixture_h1", fixture_id)),
        ("neutral_rest", FCID_NEUTRAL.replace("fixture_h1", fixture_id)),
    ):
        record_decision(
            decision_id=str(uuid.uuid4()),
            bootstrap_run_id=FROZEN_RUN_ID,
            fixture_id=fixture_id,
            reference_kind="portrait_reference",
            reference_purpose=purpose,
            disposition="selected",
            frozen_candidate_id=fcid,
            supersedes_decision_id=None,
            amendment_reason=None,
            reviewer_user_id=reviewer.id,
            reviewer_email_at_write_time=reviewer.email,
        )
        promote_current_decision(
            fixture_id=fixture_id,
            reference_kind="portrait_reference",
            reference_purpose=purpose,
        )
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if purpose in ("front", "neutral_rest"):
            continue
        record_decision(
            decision_id=str(uuid.uuid4()),
            bootstrap_run_id=FROZEN_RUN_ID,
            fixture_id=fixture_id,
            reference_kind="portrait_reference",
            reference_purpose=purpose,
            disposition="no_candidate_approved",
            frozen_candidate_id=None,
            supersedes_decision_id=None,
            amendment_reason=None,
            reviewer_user_id=reviewer.id,
            reviewer_email_at_write_time=reviewer.email,
        )
    # Approve the version.
    from apps.accounts.models import Workspace
    from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG
    from apps.identity.models import CharacterIdentity

    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    identity = CharacterIdentity.objects.get(workspace=workspace, name=fixture_id)
    version = CharacterIdentityVersion.objects.get(
        identity=identity, state=CharacterIdentityVersion.State.DRAFT
    )
    identity_services.approve_version(version, approver=reviewer)


# ---------------------------------------------------------------------
# Argument handling
# ---------------------------------------------------------------------


def test_requires_fixture_or_all_flag():
    with pytest.raises(CommandError):
        call_command("bootstrap_review_gate")


def test_rejects_both_fixture_and_all():
    with pytest.raises(CommandError):
        call_command(
            "bootstrap_review_gate", "fixture_h1", "--all-fixtures"
        )


# ---------------------------------------------------------------------
# Single-fixture output
# ---------------------------------------------------------------------


def test_single_fixture_not_ready_exits_1(reviewer):
    out = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        call_command("bootstrap_review_gate", "fixture_h1", stdout=out)
    assert exc_info.value.code == 1
    payload = json.loads(out.getvalue())
    report = payload["reports"][0]
    assert report["fixture_id"] == "fixture_h1"
    assert report["ready"] is False
    assert "review_incomplete" in report["failures"]


def test_single_fixture_ready_exits_0(reviewer):
    _promote_all_purposes(reviewer, "fixture_h1")
    out = StringIO()
    call_command("bootstrap_review_gate", "fixture_h1", stdout=out)
    payload = json.loads(out.getvalue())
    report = payload["reports"][0]
    assert report["ready"] is True
    assert report["failures"] == []


def test_fixture_nh1_not_ready():
    out = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        call_command("bootstrap_review_gate", "fixture_nh1", stdout=out)
    assert exc_info.value.code == 1
    report = json.loads(out.getvalue())["reports"][0]
    assert report["fixture_authorized"] is False


# ---------------------------------------------------------------------
# --all-fixtures
# ---------------------------------------------------------------------


def test_all_fixtures_reports_every_authorized_fixture():
    out = StringIO()
    with pytest.raises(SystemExit) as exc_info:
        call_command("bootstrap_review_gate", "--all-fixtures", stdout=out)
    assert exc_info.value.code == 1
    payload = json.loads(out.getvalue())
    fixture_ids = sorted(r["fixture_id"] for r in payload["reports"])
    assert fixture_ids == ["fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"]
    assert payload["all_ready"] is False


def test_all_fixtures_all_ready_exits_0(reviewer):
    for fixture_id in ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"):
        _promote_all_purposes(reviewer, fixture_id)
    out = StringIO()
    call_command("bootstrap_review_gate", "--all-fixtures", stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["all_ready"] is True
    assert all(r["ready"] for r in payload["reports"])
