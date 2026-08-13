"""Tests for the §19 Step 9.b.1 artifact-streaming endpoints.

Covers:

* raw / normalized / manifest / candidate.json all streamable for
  reviewable candidates
* absent artifacts on unsupported cells return a stable
  ``artifact_absent`` code (not a 500 or manufactured payload)
* SHA-256 verification: on-disk bytes must match candidate.json
* tampered evidence is refused loudly with
  ``artifact_integrity_mismatch``
* path traversal via malformed identifiers refused
* unauthorized run IDs refused (never leak filesystem contents)
* operator gate applied identically to artifact endpoints
"""
from __future__ import annotations

import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.bootstrap_review.evidence import (
    FROZEN_EVIDENCE_ROOT,
    FrozenCandidateId,
)

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"

# A known-successful candidate from the frozen 9.a evidence.
GOOD_FCID = FrozenCandidateId.build(
    run_id=FROZEN_RUN_ID,
    direction="identity_only",
    provider="stability_still",
    cell_id="fixture_h1__portrait_reference__front__compact",
)

# A known-unsupported candidate (Runway declined 1:1).
UNSUPPORTED_FCID = FrozenCandidateId.build(
    run_id=FROZEN_RUN_ID,
    direction="identity_only",
    provider="runway_still_portrait",
    cell_id="fixture_h1__portrait_reference__front__compact",
)


@pytest.fixture()
def staff_user(db):
    User = get_user_model()
    user = User.objects.create_user(email="staff-art@example.test", password="pw")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture()
def ordinary_user(db):
    User = get_user_model()
    return User.objects.create_user(email="ordinary-art@example.test", password="pw")


@pytest.fixture()
def staff_client(staff_user):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


def _artifact_url(url_name: str, fcid: FrozenCandidateId) -> str:
    return reverse(
        url_name,
        args=[fcid.run_id, fcid.direction, fcid.provider, fcid.cell_id],
    )


# ---------------------------------------------------------------------
# Happy path — every artifact type streamable + hashes match
# ---------------------------------------------------------------------


def test_raw_artifact_streams_for_reviewable_candidate(staff_client):
    response = staff_client.get(_artifact_url("bootstrap-review-artifact-raw", GOOD_FCID))
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "image/png"
    payload = b"".join(response.streaming_content)
    # Payload matches the recorded sha256 on candidate.json.
    from apps.bootstrap_review.evidence import load_candidate_json

    candidate = load_candidate_json(GOOD_FCID)
    expected_sha = candidate["raw_artifact"]["sha256_hex"]
    assert hashlib.sha256(payload).hexdigest() == expected_sha


def test_normalized_artifact_streams_for_reviewable_candidate(staff_client):
    response = staff_client.get(
        _artifact_url("bootstrap-review-artifact-normalized", GOOD_FCID)
    )
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "image/png"
    payload = b"".join(response.streaming_content)
    from apps.bootstrap_review.evidence import load_candidate_json

    candidate = load_candidate_json(GOOD_FCID)
    expected_sha = candidate["normalization_stage"]["normalized_artifact"]["sha256_hex"]
    assert hashlib.sha256(payload).hexdigest() == expected_sha


def test_manifest_artifact_streams_for_reviewable_candidate(staff_client):
    response = staff_client.get(
        _artifact_url("bootstrap-review-artifact-manifest", GOOD_FCID)
    )
    assert response.status_code == status.HTTP_200_OK
    assert response["Content-Type"] == "application/json"
    payload = b"".join(response.streaming_content)
    from apps.bootstrap_review.evidence import load_candidate_json

    candidate = load_candidate_json(GOOD_FCID)
    expected_sha = candidate["normalization_stage"]["manifest_artifact"]["sha256_hex"]
    assert hashlib.sha256(payload).hexdigest() == expected_sha


def test_candidate_json_endpoint_returns_full_record(staff_client):
    response = staff_client.get(
        _artifact_url("bootstrap-review-artifact-candidate", GOOD_FCID)
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    # Full candidate.json fields present.
    assert body["outcome"] == "success"
    assert body["cell"]["cell_id"] == GOOD_FCID.cell_id
    assert body["provider_stage"]["actual_execution_mode"] == "real"


def test_etag_header_is_the_sha256(staff_client):
    response = staff_client.get(_artifact_url("bootstrap-review-artifact-raw", GOOD_FCID))
    payload = b"".join(response.streaming_content)
    assert response["ETag"] == f'"{hashlib.sha256(payload).hexdigest()}"'


# ---------------------------------------------------------------------
# Absent artifacts on unsupported cells — honest reporting
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_name", ["bootstrap-review-artifact-raw", "bootstrap-review-artifact-normalized"]
)
def test_absent_artifact_returns_stable_code(staff_client, url_name):
    response = staff_client.get(_artifact_url(url_name, UNSUPPORTED_FCID))
    assert response.status_code == status.HTTP_404_NOT_FOUND
    body = response.json()
    assert body["code"] == "artifact_absent"


def test_candidate_json_available_for_unsupported_cell(staff_client):
    """Even though the raw/normalized bytes don't exist, the frozen
    candidate.json DOES exist and carries the factual provider
    refusal record — must be inspectable.
    """
    response = staff_client.get(
        _artifact_url("bootstrap-review-artifact-candidate", UNSUPPORTED_FCID)
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["outcome"] == "unsupported_provider_capability"
    assert body["provider_stage"]["error"]["class"] == "UnsupportedAspectRatioError"


# ---------------------------------------------------------------------
# SHA-256 integrity — loud failure on tampered evidence
# ---------------------------------------------------------------------


def test_tampered_raw_bytes_refuse_to_stream(staff_client, tmp_path, monkeypatch):
    """Simulate on-disk tampering by monkeypatching read_bytes to
    return tampered content. The view must return the stable
    integrity error and NEVER stream the altered bytes.
    """
    import apps.bootstrap_review.evidence as evidence

    original_read_bytes = evidence.Path.read_bytes
    real_path = evidence.artifact_path(GOOD_FCID, "raw")

    def tampered_read_bytes(self, *args, **kwargs):
        if self == real_path:
            return b"tampered-bytes"
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(evidence.Path, "read_bytes", tampered_read_bytes)

    response = staff_client.get(_artifact_url("bootstrap-review-artifact-raw", GOOD_FCID))
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    body = response.json()
    assert body["code"] == "artifact_integrity_mismatch"
    assert "SHA-256 mismatch" in body["detail"]


def test_tampered_manifest_bytes_refuse_to_stream(staff_client, monkeypatch):
    import apps.bootstrap_review.evidence as evidence

    original_read_bytes = evidence.Path.read_bytes
    real_path = evidence.artifact_path(GOOD_FCID, "manifest")

    def tampered_read_bytes(self, *args, **kwargs):
        if self == real_path:
            return b'{"tampered": true}'
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(evidence.Path, "read_bytes", tampered_read_bytes)

    response = staff_client.get(
        _artifact_url("bootstrap-review-artifact-manifest", GOOD_FCID)
    )
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert response.json()["code"] == "artifact_integrity_mismatch"


# ---------------------------------------------------------------------
# Path traversal + unauthorized run_id refusals
# ---------------------------------------------------------------------


def test_unauthorized_run_id_in_artifact_url_refused(staff_client):
    url = reverse(
        "bootstrap-review-artifact-raw",
        args=[
            "bootstrap_someone_else",
            "identity_only",
            "stability_still",
            "fixture_h1__portrait_reference__front__compact",
        ],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["code"] == "unauthorized_run_id"


def test_traversal_via_double_dot_direction_refused(staff_client):
    """The URL router accepts ``<str:direction>`` so a client could
    submit ``..``; the view MUST reject at vocabulary validation
    before touching the filesystem.
    """
    url = reverse(
        "bootstrap-review-artifact-raw",
        args=[
            FROZEN_RUN_ID,
            "..",  # attempted traversal
            "stability_still",
            "fixture_h1__portrait_reference__front__compact",
        ],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_frozen_candidate_id"


def test_traversal_via_cell_id_refused(staff_client):
    """Construct the URL by hand — django's ``reverse`` refuses to
    build a URL where a ``<str:>`` segment contains ``/``, which is
    itself a safeguard, but we exercise the raw HTTP surface to
    prove the view refuses even when the URL router matched.
    """
    # Any traversal-flavored cell_id containing '/' would be split by
    # the URL router into extra segments and NOT reach our view. A
    # legitimate-looking cell_id that violates the pattern (e.g. one
    # containing '..') exercises the view-layer guard directly.
    url = (
        f"/api/bootstrap-review/artifacts/{FROZEN_RUN_ID}/"
        f"identity_only/stability_still/"
        f"..__portrait_reference__front__compact/raw.png"
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["code"] == "invalid_frozen_candidate_id"


def test_traversal_via_url_slash_refused_by_router(staff_client):
    """A cell_id literally containing ``/`` cannot even be built into
    a URL by the router — Django refuses to match. We exercise the
    raw HTTP surface to prove the request 404s before reaching our
    view.
    """
    url = (
        f"/api/bootstrap-review/artifacts/{FROZEN_RUN_ID}/"
        f"identity_only/stability_still/"
        f"../../etc/passwd/raw.png"
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_provider_not_in_vocabulary_refused(staff_client):
    url = reverse(
        "bootstrap-review-artifact-raw",
        args=[
            FROZEN_RUN_ID,
            "identity_only",
            "elevenlabs_tts",  # not a portrait provider
            "fixture_h1__portrait_reference__front__compact",
        ],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_fixture_nh1_artifact_refused(staff_client):
    """fixture_nh1 stays off the 9.b.1 surface (§Q24)."""
    url = reverse(
        "bootstrap-review-artifact-raw",
        args=[
            FROZEN_RUN_ID,
            "identity_only",
            "stability_still",
            "fixture_nh1__canonical_reference__front__compact",
        ],
    )
    response = staff_client.get(url)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------
# Filesystem paths never leak into responses
# ---------------------------------------------------------------------


def test_slot_response_does_not_leak_filesystem_paths(staff_client):
    """The slot listing must not expose any absolute filesystem path
    or MEDIA_ROOT-relative path — clients look artifacts up via
    ``frozen_candidate_id``.
    """
    url = reverse(
        "bootstrap-review-slot-detail",
        args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
    )
    body = staff_client.get(url).json()
    serialized = str(body)
    assert str(FROZEN_EVIDENCE_ROOT) not in serialized
    assert "/Users/" not in serialized
    assert "media-engine/data" not in serialized


# ---------------------------------------------------------------------
# Operator gate — every artifact endpoint is protected
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_name",
    [
        "bootstrap-review-artifact-raw",
        "bootstrap-review-artifact-normalized",
        "bootstrap-review-artifact-manifest",
        "bootstrap-review-artifact-candidate",
    ],
)
def test_ordinary_user_refused_on_artifact_endpoints(ordinary_user, url_name):
    client = APIClient()
    client.force_authenticate(user=ordinary_user)
    response = client.get(_artifact_url(url_name, GOOD_FCID))
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(
    "url_name",
    [
        "bootstrap-review-artifact-raw",
        "bootstrap-review-artifact-normalized",
        "bootstrap-review-artifact-manifest",
        "bootstrap-review-artifact-candidate",
    ],
)
def test_anonymous_refused_on_artifact_endpoints(db, url_name):
    client = APIClient()
    response = client.get(_artifact_url(url_name, GOOD_FCID))
    assert response.status_code == status.HTTP_403_FORBIDDEN
