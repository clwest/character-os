"""Tests for the §19 Step 9.b IsOperator permission + gate wiring
(SESSION 249, 9.b.0).

Verifies the four admission classes required by the operator
ratification of L2:

* anonymous / unauthenticated → 403
* ordinary authenticated user (staff=False, superuser=False) → 403
* staff user (is_staff=True, superuser=False) → 200
* superuser (is_staff=False, superuser=True) → 200

Also verifies:

* No workspace membership is required for operator access — the
  operator's admission is by staff/superuser flag, not by
  ``IsWorkspaceMember`` (L2 ratification).
* The placeholder endpoint returns the seeded bootstrap-fixtures
  workspace's identity when the gate admits the caller — proves
  the migration ran + views can read the row.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace

from apps.bootstrap_review.workspace import (
    BOOTSTRAP_WORKSPACE_SLUG,
    BOOTSTRAP_WORKSPACE_UUID,
)

HEALTH_URL_NAME = "bootstrap-review-health"


@pytest.fixture()
def anonymous_client() -> APIClient:
    return APIClient()


@pytest.fixture()
def ordinary_user(db):
    User = get_user_model()
    return User.objects.create_user(
        email="ordinary@example.test",
        password="ordinary-password-123",
    )


@pytest.fixture()
def staff_user(db):
    User = get_user_model()
    user = User.objects.create_user(
        email="staff@example.test",
        password="staff-password-123",
    )
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture()
def super_user(db):
    User = get_user_model()
    return User.objects.create_superuser(
        email="root@example.test",
        password="root-password-123",
    )


@pytest.fixture()
def auth_client_factory():
    def _make(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    return _make


def test_anonymous_is_rejected(anonymous_client, db):
    """§L2 — unauthenticated requests never reach the surface."""
    url = reverse(HEALTH_URL_NAME)
    response = anonymous_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_ordinary_authenticated_user_is_rejected(auth_client_factory, ordinary_user):
    """§L2 — staff/superuser flag is required; plain login is not enough."""
    client = auth_client_factory(ordinary_user)
    url = reverse(HEALTH_URL_NAME)
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_staff_user_is_admitted(auth_client_factory, staff_user):
    """§L2 — is_staff admits the caller."""
    client = auth_client_factory(staff_user)
    url = reverse(HEALTH_URL_NAME)
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "ok"
    assert body["bootstrap_fixtures_workspace"]["slug"] == BOOTSTRAP_WORKSPACE_SLUG


def test_superuser_is_admitted(auth_client_factory, super_user):
    """§L2 — is_superuser admits the caller."""
    client = auth_client_factory(super_user)
    url = reverse(HEALTH_URL_NAME)
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "ok"


def test_operator_admission_requires_no_bootstrap_workspace_membership(
    auth_client_factory, staff_user
):
    """§L2 — the bootstrap-fixtures workspace has zero memberships
    by design; operator admission must NOT depend on membership in
    that workspace.

    Note: signup auto-provisions a personal workspace for every new
    User via ``accounts.models.User.post_save`` (see CLAUDE.md
    "Product object shape"), so ``staff_user`` legitimately owns
    their own personal workspace. What must remain true is that
    they hold NO membership in the bootstrap-fixtures workspace
    yet still gain access to its API surface via IsOperator alone.
    """
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)

    # Assert: bootstrap-fixtures workspace has no memberships at all.
    assert workspace.memberships.count() == 0

    # Assert: staff_user has NO membership in the bootstrap-fixtures
    # workspace specifically (they may have other memberships from
    # signup auto-provisioning).
    assert Membership.objects.filter(
        user=staff_user, workspace=workspace
    ).count() == 0

    # Access still succeeds via IsOperator.
    client = auth_client_factory(staff_user)
    url = reverse(HEALTH_URL_NAME)
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK


def test_health_endpoint_returns_seeded_workspace_identity(
    auth_client_factory, staff_user, db
):
    """Proves the 9.b.0 migration ran + the view can locate the row."""
    client = auth_client_factory(staff_user)
    url = reverse(HEALTH_URL_NAME)
    response = client.get(url)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    workspace = body["bootstrap_fixtures_workspace"]
    assert workspace["id"] == str(BOOTSTRAP_WORKSPACE_UUID)
    assert workspace["slug"] == BOOTSTRAP_WORKSPACE_SLUG
    assert workspace["name"].startswith("Bootstrap Fixtures")


def test_admission_is_by_staff_flag_not_by_email_identity(
    auth_client_factory, ordinary_user
):
    """Defense in depth: admission is decided by is_staff/is_superuser,
    NOT by email match against the infrastructure owner.

    Even if a customer had an email that happened to sort near the
    infrastructure owner's, they would still be denied unless staff
    or superuser. The permission code has no email-comparison branch.
    """
    # ordinary_user is not staff/superuser by construction. Confirm
    # they cannot access even though authenticated.
    assert ordinary_user.is_staff is False
    assert ordinary_user.is_superuser is False
    client = auth_client_factory(ordinary_user)
    url = reverse(HEALTH_URL_NAME)
    response = client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN
