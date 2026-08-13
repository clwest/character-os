"""Tests for the §19 Step 9.b.0 bootstrap-fixtures workspace seed
data migration (SESSION 249).

Verifies the discipline ratified in L1:

* Deterministic identity — UUID + slug + name are byte-stable
  across environments.
* Idempotent — running the migration twice (via
  ``call_command("migrate")``) produces exactly one workspace and
  one owner user.
* No customer / user memberships are manufactured.
* No CharacterIdentity, no CharacterIdentityVersion, no
  IdentityReference, no GenerationRecord, no NormalizationManifest,
  and no Teammate rows are created.
* The infrastructure owner is ``is_active=False`` and NOT staff /
  superuser — it is a placeholder, not a customer.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Membership, Workspace
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationRecord,
    IdentityReference,
    NormalizationManifest,
)
from apps.spokespeople.models import Teammate

from apps.bootstrap_review.workspace import (
    BOOTSTRAP_OWNER_EMAIL,
    BOOTSTRAP_WORKSPACE_NAME,
    BOOTSTRAP_WORKSPACE_SLUG,
    BOOTSTRAP_WORKSPACE_UUID,
)


@pytest.fixture()
def bootstrap_workspace(db) -> Workspace:
    """Returns the workspace already seeded by
    ``0001_bootstrap_fixtures_workspace``. Every test in this
    module depends on the migration having run — pytest's Django
    plugin runs migrations before test collection, so the row is
    already present.
    """
    return Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)


def test_workspace_identity_is_deterministic(bootstrap_workspace):
    assert bootstrap_workspace.id == BOOTSTRAP_WORKSPACE_UUID
    assert bootstrap_workspace.slug == BOOTSTRAP_WORKSPACE_SLUG
    assert bootstrap_workspace.name == BOOTSTRAP_WORKSPACE_NAME


def test_infrastructure_owner_is_placeholder(bootstrap_workspace):
    User = get_user_model()
    owner = User.objects.get(email=BOOTSTRAP_OWNER_EMAIL)
    assert bootstrap_workspace.owner_id == owner.id
    # L1 discipline — placeholder, not a customer.
    assert owner.is_active is False
    assert owner.is_staff is False
    assert owner.is_superuser is False


def test_no_memberships_are_manufactured(bootstrap_workspace):
    """§L1 — the workspace has no members. Do not create any."""
    assert bootstrap_workspace.memberships.count() == 0
    assert bootstrap_workspace.members.count() == 0

    # Also assert the owner user has no memberships attaching them
    # to this or any workspace. Owner is an FK, not a Membership.
    User = get_user_model()
    owner = User.objects.get(email=BOOTSTRAP_OWNER_EMAIL)
    assert Membership.objects.filter(user=owner).count() == 0


def test_no_teammate_rows_created(db):
    """§L1 — bootstrap fixtures are infrastructure, not Teammates.
    The migration must not create any Teammate row. This test's
    baseline is a fresh test DB where Teammates only exist if a
    prior fixture created them — the 9.b.0 migration itself must
    not.
    """
    # In the fresh migrated state, no Teammate rows belong to the
    # bootstrap-fixtures workspace.
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    assert Teammate.objects.filter(workspace=workspace).count() == 0


def test_no_character_identity_rows_created(db):
    """§Q15 — fixture CharacterIdentity rows are created LAZILY on
    the first reviewer ``select`` decision at 9.b.3. The 9.b.0
    migration must not create any.
    """
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    assert CharacterIdentity.objects.filter(workspace=workspace).count() == 0


def test_no_substrate_evidence_rows_created(db):
    """No CharacterIdentityVersion, IdentityReference, GenerationRecord,
    or NormalizationManifest rows may be created by 9.b.0. Those all
    require an owning CharacterIdentity anchored to this workspace;
    since the identity rows must not exist yet, neither may these.
    """
    # Across the fresh test DB, no substrate rows anchored to the
    # bootstrap-fixtures workspace exist.
    workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
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


def test_migration_is_idempotent(db):
    """Running the seed function a second time produces exactly one
    workspace + one owner (no duplicates, no ``IntegrityError``).

    Directly invokes the seed function via the historical apps
    registry the migration uses. This mirrors the failure mode a
    re-run of ``manage.py migrate`` would exercise if migration
    frameworks ever double-applied the RunPython step.
    """
    import importlib

    from django.apps import apps as global_apps

    # Migration modules start with a digit; use importlib to bypass
    # Python's identifier rules for ``from ... import`` syntax.
    migration_module = importlib.import_module(
        "apps.bootstrap_review.migrations.0001_bootstrap_fixtures_workspace"
    )
    User = get_user_model()

    # Pre-count.
    workspace_before = Workspace.objects.filter(slug=BOOTSTRAP_WORKSPACE_SLUG).count()
    owner_before = User.objects.filter(email=BOOTSTRAP_OWNER_EMAIL).count()
    assert workspace_before == 1
    assert owner_before == 1

    # Re-run.
    migration_module._seed_bootstrap_fixtures_workspace(global_apps, schema_editor=None)

    # Post-count identical.
    assert Workspace.objects.filter(slug=BOOTSTRAP_WORKSPACE_SLUG).count() == 1
    assert User.objects.filter(email=BOOTSTRAP_OWNER_EMAIL).count() == 1
