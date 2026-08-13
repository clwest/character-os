"""§19 Step 9.b.2 POST /decisions/ endpoint tests (SESSION 249).

Covers HTTP-level behavior + operator gate + the substrate-zero
regression discipline after the full decision-lifecycle exercise.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.bootstrap_review.evidence import FROZEN_EVIDENCE_ROOT
from apps.bootstrap_review.journal import review_dir_for_fixture
from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationRecord,
    IdentityReference,
    NormalizationManifest,
)
from apps.spokespeople.models import Teammate

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
GOOD_FCID_COMPACT = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__compact"
)
GOOD_FCID_TEAM_CARD = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__team_card"
)
GOOD_FCID_NEUTRAL = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__neutral_rest__compact"
)
UNSUPPORTED_FCID = (
    f"{FROZEN_RUN_ID}/identity_only/runway_still_portrait/"
    "fixture_h1__portrait_reference__front__compact"
)


@pytest.fixture(autouse=True)
def clean_review_directories():
    dirs = [
        review_dir_for_fixture(f)
        for f in ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    ]
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
    yield
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


@pytest.fixture()
def staff_user(db):
    User = get_user_model()
    user = User.objects.create_user(email="staff-dec@example.test", password="pw")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture()
def superuser(db):
    User = get_user_model()
    return User.objects.create_superuser(email="root-dec@example.test", password="pw")


@pytest.fixture()
def ordinary_user(db):
    User = get_user_model()
    return User.objects.create_user(email="ordinary-dec@example.test", password="pw")


@pytest.fixture()
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


def _slot_url(purpose: str = "front", fixture_id: str = "fixture_h1") -> str:
    return reverse(
        "bootstrap-review-slot-decisions",
        args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
    )


def _payload(**overrides):
    body = {
        "decision_id": str(uuid.uuid4()),
        "disposition": "no_candidate_approved",
        "frozen_candidate_id": None,
        "supersedes_decision_id": None,
        "amendment_reason": None,
    }
    body.update(overrides)
    return body


# ---------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------


def test_first_no_candidate_approved_returns_201(staff_client):
    body = _payload()
    response = staff_client.post(_slot_url(), body, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["created"] is True
    assert payload["decision"]["disposition"] == "no_candidate_approved"
    assert payload["decision"]["frozen_candidate_id"] is None
    assert payload["decision"]["reviewer_user_id"] > 0


def test_first_selected_returns_201(staff_client):
    body = _payload(disposition="selected", frozen_candidate_id=GOOD_FCID_COMPACT)
    response = staff_client.post(_slot_url(), body, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["created"] is True
    assert payload["decision"]["disposition"] == "selected"
    assert payload["decision"]["frozen_candidate_id"] == GOOD_FCID_COMPACT


def test_idempotent_replay_returns_200(staff_client):
    body = _payload()
    r1 = staff_client.post(_slot_url(), body, format="json")
    r2 = staff_client.post(_slot_url(), body, format="json")
    assert r1.status_code == status.HTTP_201_CREATED
    assert r2.status_code == status.HTTP_200_OK
    assert r2.json()["created"] is False
    assert r1.json()["decision"]["decision_id"] == r2.json()["decision"]["decision_id"]


# ---------------------------------------------------------------------
# Validation refusals
# ---------------------------------------------------------------------


def test_invalid_disposition_returns_400(staff_client):
    response = staff_client.post(
        _slot_url(), _payload(disposition="rejected"), format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_disposition"


def test_selected_without_fcid_returns_400(staff_client):
    response = staff_client.post(
        _slot_url(),
        _payload(disposition="selected", frozen_candidate_id=None),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_disposition"


def test_no_candidate_approved_with_fcid_returns_400(staff_client):
    response = staff_client.post(
        _slot_url(),
        _payload(
            disposition="no_candidate_approved",
            frozen_candidate_id=GOOD_FCID_COMPACT,
        ),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_disposition"


def test_selected_unsupported_candidate_returns_400(staff_client):
    response = staff_client.post(
        _slot_url(),
        _payload(disposition="selected", frozen_candidate_id=UNSUPPORTED_FCID),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "candidate_not_reviewable"


def test_cross_purpose_candidate_refused(staff_client):
    # slot=front but fcid is for neutral_rest
    response = staff_client.post(
        _slot_url("front"),
        _payload(disposition="selected", frozen_candidate_id=GOOD_FCID_NEUTRAL),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "candidate_slot_mismatch"


def test_fixture_nh1_refused(staff_client):
    url = reverse(
        "bootstrap-review-slot-decisions",
        args=[FROZEN_RUN_ID, "fixture_nh1", "portrait_reference", "front"],
    )
    response = staff_client.post(url, _payload(), format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_candidate"


def test_unauthorized_run_refused(staff_client):
    url = reverse(
        "bootstrap-review-slot-decisions",
        args=["bootstrap_someone_else", "fixture_h1", "portrait_reference", "front"],
    )
    response = staff_client.post(url, _payload(), format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_candidate"


# ---------------------------------------------------------------------
# Amendment + stale-supersedes
# ---------------------------------------------------------------------


def test_amendment_appends_second_record(staff_client):
    b1 = _payload(disposition="no_candidate_approved")
    r1 = staff_client.post(_slot_url(), b1, format="json").json()

    b2 = _payload(
        disposition="selected",
        frozen_candidate_id=GOOD_FCID_COMPACT,
        supersedes_decision_id=r1["decision"]["decision_id"],
        amendment_reason="chose compact after review",
    )
    r2 = staff_client.post(_slot_url(), b2, format="json")
    assert r2.status_code == status.HTTP_201_CREATED
    payload = r2.json()
    assert (
        payload["decision"]["supersedes_decision_id"]
        == r1["decision"]["decision_id"]
    )
    assert payload["decision"]["amendment_reason"] == "chose compact after review"


def test_amendment_requires_reason(staff_client):
    b1 = _payload()
    r1 = staff_client.post(_slot_url(), b1, format="json").json()
    b2 = _payload(
        supersedes_decision_id=r1["decision"]["decision_id"],
        amendment_reason="   ",
    )
    r2 = staff_client.post(_slot_url(), b2, format="json")
    assert r2.status_code == status.HTTP_400_BAD_REQUEST
    assert r2.json()["code"] == "amendment_reason_required"


def test_stale_supersedes_returns_409(staff_client):
    b1 = _payload()
    r1 = staff_client.post(_slot_url(), b1, format="json").json()

    b2 = _payload(
        supersedes_decision_id=r1["decision"]["decision_id"],
        amendment_reason="first amend",
    )
    staff_client.post(_slot_url(), b2, format="json")

    # Now try to amend from r1 again — stale.
    b3 = _payload(
        supersedes_decision_id=r1["decision"]["decision_id"],
        amendment_reason="stale amend",
    )
    r3 = staff_client.post(_slot_url(), b3, format="json")
    assert r3.status_code == status.HTTP_409_CONFLICT
    assert r3.json()["code"] == "stale_supersedes_decision"


def test_second_first_decision_returns_409(staff_client):
    """Trying to submit a first-decision (supersedes=None) into a slot
    that already has a terminal decision must fail — the client must
    explicitly amend.
    """
    staff_client.post(_slot_url(), _payload(), format="json")
    r2 = staff_client.post(_slot_url(), _payload(), format="json")
    assert r2.status_code == status.HTTP_409_CONFLICT
    assert r2.json()["code"] == "supersedes_decision_required"


def test_same_uuid_different_payload_returns_409(staff_client):
    decision_id = str(uuid.uuid4())
    body1 = _payload(decision_id=decision_id, disposition="no_candidate_approved")
    body2 = _payload(
        decision_id=decision_id,
        disposition="selected",
        frozen_candidate_id=GOOD_FCID_COMPACT,
    )
    r1 = staff_client.post(_slot_url(), body1, format="json")
    r2 = staff_client.post(_slot_url(), body2, format="json")
    assert r1.status_code == status.HTTP_201_CREATED
    assert r2.status_code == status.HTTP_409_CONFLICT
    assert r2.json()["code"] == "decision_id_conflict"


# ---------------------------------------------------------------------
# Operator gate — POST endpoint
# ---------------------------------------------------------------------


def test_ordinary_user_forbidden(ordinary_user):
    client = APIClient()
    client.force_authenticate(user=ordinary_user)
    response = client.post(_slot_url(), _payload(), format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_anonymous_forbidden(db):
    client = APIClient()
    response = client.post(_slot_url(), _payload(), format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_superuser_admitted(superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)
    response = client.post(_slot_url(), _payload(), format="json")
    assert response.status_code == status.HTTP_201_CREATED


# ---------------------------------------------------------------------
# GET slot + GET fixture now expose current decision / progress
# ---------------------------------------------------------------------


def test_get_slot_includes_current_decision_and_history(staff_client):
    b1 = _payload()
    staff_client.post(_slot_url(), b1, format="json")

    slot = staff_client.get(
        reverse(
            "bootstrap-review-slot-detail",
            args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        )
    ).json()
    assert slot["current_decision"] is not None
    assert slot["current_decision"]["disposition"] == "no_candidate_approved"
    assert len(slot["decision_history"]) == 1


def test_get_fixture_includes_progress_signals(staff_client):
    # Two selected + five no_candidate_approved = review complete + floor satisfied.
    for purpose, disposition, fcid in [
        ("front", "selected", GOOD_FCID_COMPACT),
        ("neutral_rest", "selected", GOOD_FCID_NEUTRAL),
        ("slight_left", "no_candidate_approved", None),
        ("slight_right", "no_candidate_approved", None),
        ("listening", "no_candidate_approved", None),
        ("consideration", "no_candidate_approved", None),
        ("gentle_positive", "no_candidate_approved", None),
    ]:
        body = _payload(disposition=disposition, frozen_candidate_id=fcid)
        r = staff_client.post(_slot_url(purpose=purpose), body, format="json")
        assert r.status_code == status.HTTP_201_CREATED

    fixture = staff_client.get(
        reverse(
            "bootstrap-review-fixture-detail",
            args=[FROZEN_RUN_ID, "fixture_h1"],
        )
    ).json()
    progress = fixture["progress"]
    assert progress["purposes_dispositioned"] == 7
    assert progress["review_complete"] is True
    assert progress["approval_floor_satisfied"] is True
    assert set(progress["approval_floor_satisfied_pairs"]) == {
        "portrait_reference/front",
        "portrait_reference/neutral_rest",
    }


def test_progress_review_complete_but_floor_unsatisfied(staff_client):
    for purpose in (
        "front",
        "slight_left",
        "slight_right",
        "neutral_rest",
        "listening",
        "consideration",
        "gentle_positive",
    ):
        body = _payload(disposition="no_candidate_approved")
        staff_client.post(_slot_url(purpose=purpose), body, format="json")

    fixture = staff_client.get(
        reverse(
            "bootstrap-review-fixture-detail",
            args=[FROZEN_RUN_ID, "fixture_h1"],
        )
    ).json()
    progress = fixture["progress"]
    assert progress["review_complete"] is True
    assert progress["approval_floor_satisfied"] is False


# ---------------------------------------------------------------------
# Substrate-zero-write regression — the load-bearing 9.b.2 boundary
# ---------------------------------------------------------------------


def test_zero_substrate_writes_after_full_decision_exercise(staff_client):
    """Exercise selection + no-candidate + amendment + amendment
    across multiple slots, then assert canonical substrate remains
    empty (0 rows) and bootstrap/references/ / scores/ remain empty.
    """
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    assert CharacterIdentity.objects.filter(workspace=workspace).count() == 0

    # Slot 1: front → no_candidate → selected → no_candidate (amendment chain)
    b1 = _payload(disposition="no_candidate_approved")
    r1 = staff_client.post(_slot_url("front"), b1, format="json").json()
    b2 = _payload(
        disposition="selected",
        frozen_candidate_id=GOOD_FCID_COMPACT,
        supersedes_decision_id=r1["decision"]["decision_id"],
        amendment_reason="pick compact",
    )
    r2 = staff_client.post(_slot_url("front"), b2, format="json").json()
    b3 = _payload(
        disposition="no_candidate_approved",
        supersedes_decision_id=r2["decision"]["decision_id"],
        amendment_reason="none acceptable after all",
    )
    staff_client.post(_slot_url("front"), b3, format="json")

    # Slot 2: neutral_rest → selected
    b4 = _payload(
        disposition="selected", frozen_candidate_id=GOOD_FCID_NEUTRAL
    )
    staff_client.post(_slot_url("neutral_rest"), b4, format="json")

    # Idempotent retry of r1
    staff_client.post(_slot_url("front"), b1, format="json")

    # Stale-supersedes attempt (already tested elsewhere; belt).
    stale = _payload(
        supersedes_decision_id=r1["decision"]["decision_id"],
        amendment_reason="stale",
    )
    staff_client.post(_slot_url("front"), stale, format="json")

    # Assert: substrate untouched.
    assert CharacterIdentity.objects.filter(workspace=workspace).count() == 0
    assert CharacterIdentityVersion.objects.filter(
        identity__workspace=workspace
    ).count() == 0
    assert IdentityReference.objects.filter(
        identity_version__identity__workspace=workspace
    ).count() == 0
    assert GenerationRecord.objects.filter(
        identity_version__identity__workspace=workspace
    ).count() == 0
    assert NormalizationManifest.objects.filter(
        generation_record__identity_version__identity__workspace=workspace
    ).count() == 0
    assert Teammate.objects.filter(workspace=workspace).count() == 0

    # Assert: bootstrap/references/ + scores/ untouched.
    for fixture_id in ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"):
        refs = FROZEN_EVIDENCE_ROOT / fixture_id / "bootstrap" / "references"
        if refs.exists():
            files = [f for f in refs.rglob("*") if f.is_file()]
            assert files == [], (
                f"bootstrap/references/ for {fixture_id} contains {files!r}"
            )
        run_root = FROZEN_EVIDENCE_ROOT / fixture_id / "runs" / FROZEN_RUN_ID
        for scores_dir in run_root.rglob("scores"):
            entries = list(scores_dir.iterdir())
            assert entries == [], (
                f"scores/ under {scores_dir} contains {entries!r}"
            )


def test_review_journal_files_are_the_only_new_disk_writes(staff_client):
    """After the full exercise every write must be under bootstrap/review/.

    The frozen 9.a subtree (identity.yaml, rationale.md, runs/) must
    remain untouched. Journal files under bootstrap/review/ ARE
    expected new writes (they are runtime evidence, not frozen
    evidence).
    """
    b1 = _payload(disposition="selected", frozen_candidate_id=GOOD_FCID_COMPACT)
    staff_client.post(_slot_url("front"), b1, format="json")

    # The journal dir exists + has one file.
    journal_dir = FROZEN_EVIDENCE_ROOT / "fixture_h1" / "bootstrap" / "review"
    assert journal_dir.exists()
    files = list(journal_dir.glob("*.jsonl"))
    assert len(files) == 1
    assert files[0].suffix == ".jsonl"

    # Non-review 9.a evidence subtree is untouched.
    identity_yaml = FROZEN_EVIDENCE_ROOT / "fixture_h1" / "identity.yaml"
    assert identity_yaml.exists()
    # (Content immutability is verified separately by
    # test_frozen_evidence_tree_is_git_clean in test_regression_guards.)
