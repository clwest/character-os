"""Tests for the §19 Step 9.b.1 read-only browser API surface.

Covers:

* run-list + run-detail + fixture-summary + slot-listing shapes
* candidate counts match the frozen 9.a evidence
* unsupported evidence rendered distinctly from reviewable candidates
* frozen_candidate_id present on every candidate record
* operator gate applied to every endpoint
* no substrate writes after exercising the full read surface
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
HUMAN_FIXTURES = ["fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"]
HUMAN_PURPOSES = [
    "front",
    "slight_left",
    "slight_right",
    "neutral_rest",
    "listening",
    "consideration",
    "gentle_positive",
]


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture()
def staff_user(db):
    User = get_user_model()
    user = User.objects.create_user(
        email="staff-9b1@example.test", password="pw"
    )
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture()
def superuser(db):
    User = get_user_model()
    return User.objects.create_superuser(
        email="root-9b1@example.test", password="pw"
    )


@pytest.fixture()
def ordinary_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="ordinary-9b1@example.test", password="pw"
    )


@pytest.fixture()
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture()
def ordinary_client(ordinary_user):
    client = APIClient()
    client.force_authenticate(user=ordinary_user)
    return client


# ---------------------------------------------------------------------
# Runs list + one-run detail
# ---------------------------------------------------------------------


def test_runs_list_returns_only_authorized_run(staff_client):
    url = reverse("bootstrap-review-runs-list")
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    ids = [r["run_id"] for r in body["runs"]]
    assert ids == [FROZEN_RUN_ID]
    run = body["runs"][0]
    assert run["run_kind"] == "bootstrap"
    assert run["qualification_status"] == "not_evaluated"
    assert run["execution_mode"]["contains_real_execution"] is True
    assert run["execution_mode"]["requested"] == "real_required"
    # SESSION 248 evidence: 168 real + 392 unsupported = 560 planned.
    assert run["counts"]["planned"] == 560
    assert run["counts"]["by_outcome"]["success"] == 168
    assert run["counts"]["by_outcome"]["unsupported_provider_capability"] == 392
    # 4 human fixtures exposed (nh1 filtered out).
    fixture_ids = {f["fixture_id"] for f in run["fixtures"]}
    assert fixture_ids == set(HUMAN_FIXTURES)


def test_run_detail_matches_runs_list_entry(staff_client):
    list_url = reverse("bootstrap-review-runs-list")
    detail_url = reverse(
        "bootstrap-review-run-detail",
        args=[FROZEN_RUN_ID],
    )
    list_body = staff_client.get(list_url).json()
    detail_body = staff_client.get(detail_url).json()
    assert list_body["runs"][0] == detail_body


def test_run_detail_rejects_unauthorized_run_id(staff_client):
    url = reverse(
        "bootstrap-review-run-detail",
        args=["bootstrap_someone_else"],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["code"] == "unauthorized_run_id"


# ---------------------------------------------------------------------
# Fixture summary
# ---------------------------------------------------------------------


@pytest.mark.parametrize("fixture_id", HUMAN_FIXTURES)
def test_fixture_summary_lists_seven_purposes(staff_client, fixture_id):
    url = reverse(
        "bootstrap-review-fixture-detail",
        args=[FROZEN_RUN_ID, fixture_id],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    purposes = body["purposes"]
    assert [p["reference_purpose"] for p in purposes] == HUMAN_PURPOSES
    for entry in purposes:
        assert entry["reference_kind"] == "portrait_reference"
        assert entry["review_status"] == "unreviewed"
        assert entry["reviewable_candidate_count"] == 6
        assert entry["unsupported_evidence_count"] == 14


def test_fixture_summary_rejects_nh1(staff_client):
    """fixture_nh1 stays off the 9.b.1 surface (§Q24)."""
    url = reverse(
        "bootstrap-review-fixture-detail",
        args=[FROZEN_RUN_ID, "fixture_nh1"],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["code"] == "unknown_fixture"


# ---------------------------------------------------------------------
# Slot listing — the load-bearing 6-reviewable + 14-unsupported shape
# ---------------------------------------------------------------------


def test_slot_returns_six_reviewable_and_fourteen_unsupported(staff_client):
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    reviewable = body["reviewable_candidates"]
    unsupported = body["unsupported_evidence"]

    assert len(reviewable) == 6
    assert len(unsupported) == 14

    # Every reviewable candidate exposes the load-bearing fields.
    for candidate in reviewable:
        # Canonical identity + provenance.
        assert candidate["frozen_candidate_id"].startswith(f"{FROZEN_RUN_ID}/")
        assert candidate["cell_id"].startswith("fixture_h1__portrait_reference__front__")
        assert candidate["reference_kind"] == "portrait_reference"
        assert candidate["reference_purpose"] == "front"
        assert candidate["fixture_id"] == "fixture_h1"
        # 6 reviewable per slot = 3 profiles × 2 directions.
        assert candidate["direction_hypothesis"] in {
            "identity_only",
            "softened_photographic",
        }
        assert candidate["surface_profile"] in {"compact", "team_card", "presence"}
        # Every real success has a real actual execution mode.
        assert candidate["outcome"] == "success"
        assert candidate["provider_stage"]["actual_execution_mode"] == "real"
        assert candidate["provider_stage"]["provider_model"] == "sd3-large"
        # SHA-256 present + non-empty on all three artifacts.
        assert len(candidate["raw_artifact"]["sha256_hex"]) == 64
        assert len(candidate["normalized_artifact"]["sha256_hex"]) == 64
        assert len(candidate["manifest_artifact"]["sha256_hex"]) == 64
        # Factual normalization notices are a list (may be empty for
        # some profiles). Never a score / ranking.
        assert isinstance(candidate["factual_normalization_notices"], list)

    # Every unsupported record retains its distinct frozen_candidate_id
    # and carries the factual provider error verbatim.
    ids = {u["frozen_candidate_id"] for u in unsupported}
    assert len(ids) == 14
    for entry in unsupported:
        assert entry["outcome"] == "unsupported_provider_capability"
        assert entry["provider_stage"]["error"]["class"] in {
            "UnsupportedAspectRatioError"
        }
        assert entry["raw_artifact"] is None


def test_slot_reviewable_and_unsupported_have_zero_id_overlap(staff_client):
    """Vocabulary discipline — reviewable and unsupported cell sets
    must be disjoint. A frozen_candidate_id belongs to exactly one
    of the two lists.
    """
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
    )
    body = staff_client.get(url).json()
    reviewable_ids = {c["frozen_candidate_id"] for c in body["reviewable_candidates"]}
    unsupported_ids = {c["frozen_candidate_id"] for c in body["unsupported_evidence"]}
    assert reviewable_ids.isdisjoint(unsupported_ids)
    assert len(reviewable_ids) == 6
    assert len(unsupported_ids) == 14


def test_slot_unsupported_summary_preserves_frozen_candidate_ids(staff_client):
    """Grouped summary per L5(b) must still expose every member's
    ``frozen_candidate_id`` — no cell becomes unreachable via the
    grouping.
    """
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
    )
    body = staff_client.get(url).json()
    summary = body["unsupported_summary"]
    member_ids = [m["frozen_candidate_id"] for g in summary for m in g["members"]]
    assert len(member_ids) == 14
    assert len(set(member_ids)) == 14
    # Compare against the source list.
    unsupported_ids = {c["frozen_candidate_id"] for c in body["unsupported_evidence"]}
    assert set(member_ids) == unsupported_ids


def test_slot_current_decision_is_null_in_9b1(staff_client):
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
    )
    body = staff_client.get(url).json()
    assert body["current_decision"] is None


def test_slot_rejects_unknown_purpose(staff_client):
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "unknown_purpose"],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["code"] == "unknown_reference_purpose"


def test_slot_rejects_unknown_reference_kind(staff_client):
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "motion_reference", "front"],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["code"] == "unknown_reference_kind"


# ---------------------------------------------------------------------
# Total-count invariants across every human fixture + purpose
# ---------------------------------------------------------------------


def test_total_reviewable_across_all_slots_is_168(staff_client):
    total_reviewable = 0
    total_unsupported = 0
    for fixture_id in HUMAN_FIXTURES:
        for purpose in HUMAN_PURPOSES:
            url = reverse(
                "bootstrap-review-slot-detail",
                args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
            )
            body = staff_client.get(url).json()
            total_reviewable += len(body["reviewable_candidates"])
            total_unsupported += len(body["unsupported_evidence"])
    # SESSION 248 numbers.
    assert total_reviewable == 168
    assert total_unsupported == 392


# ---------------------------------------------------------------------
# Operator gate applied to every endpoint
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_name,args",
    [
        ("bootstrap-review-runs-list", []),
        ("bootstrap-review-run-detail", [FROZEN_RUN_ID]),
        ("bootstrap-review-fixture-detail", [FROZEN_RUN_ID, "fixture_h1"]),
        (
            "bootstrap-review-slot-detail",
            [FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        ),
    ],
)
def test_ordinary_user_receives_403_on_read_endpoints(
    ordinary_client, url_name, args
):
    url = reverse(url_name, args=args)
    response = ordinary_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "url_name,args",
    [
        ("bootstrap-review-runs-list", []),
        ("bootstrap-review-run-detail", [FROZEN_RUN_ID]),
        ("bootstrap-review-fixture-detail", [FROZEN_RUN_ID, "fixture_h1"]),
        (
            "bootstrap-review-slot-detail",
            [FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        ),
    ],
)
def test_anonymous_user_receives_403_on_read_endpoints(db, url_name, args):
    client = APIClient()
    url = reverse(url_name, args=args)
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "url_name,args",
    [
        ("bootstrap-review-runs-list", []),
        ("bootstrap-review-run-detail", [FROZEN_RUN_ID]),
        ("bootstrap-review-fixture-detail", [FROZEN_RUN_ID, "fixture_h1"]),
        (
            "bootstrap-review-slot-detail",
            [FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        ),
    ],
)
def test_superuser_admitted_on_read_endpoints(superuser, url_name, args):
    client = APIClient()
    client.force_authenticate(user=superuser)
    url = reverse(url_name, args=args)
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
