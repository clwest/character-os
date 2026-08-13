"""§19 Step 9.b.0 — data migration provisioning the bootstrap-fixtures workspace.

Ratified in SESSION 249 (L1). Creates a dedicated infrastructure
workspace that owns canonical-substrate rows for the portrait-
qualification fixture set (fixture_h1..h4). Not a customer workspace.

Discipline (L1):

* Deterministic identity — UUIDv5 for the workspace; stable email
  for the placeholder infrastructure owner. Same DB state across
  every environment.
* No customer/user memberships are created here. Access to the
  bootstrap-review surface is gated by ``IsOperator`` (staff /
  superuser flags), not by ``IsWorkspaceMember``.
* No CharacterIdentity, no CharacterIdentityVersion, no Teammate
  rows are manufactured. Those land later, lazily, at 9.b.3 (on
  first reviewer ``select`` decision) — see the SESSION 249
  architecture plan §Q15.
* Idempotent — ``get_or_create`` on both the User and the
  Workspace. Reverse migration removes the workspace + owner
  ONLY when nothing depends on them (defensive PROTECT-check).

Cannot use ``apps.accounts.models.Workspace.save()`` here because
that override auto-generates a slug from the name and rides on the
non-historical model. Historical migrations must set every column
explicitly.
"""
from __future__ import annotations

import uuid

from django.db import migrations


# Duplicated intentionally from ``apps.bootstrap_review.workspace``
# because migrations must not import runtime app modules
# (the runtime module might drift; the historical migration must
# hold its state permanently).
BOOTSTRAP_WORKSPACE_SLUG = "bootstrap-fixtures"
BOOTSTRAP_WORKSPACE_NAME = (
    "Bootstrap Fixtures (portrait qualification infrastructure)"
)
BOOTSTRAP_WORKSPACE_UUID = uuid.uuid5(
    uuid.NAMESPACE_DNS,
    "bootstrap-fixtures.character-os.internal",
)
BOOTSTRAP_OWNER_EMAIL = "bootstrap-fixtures-owner+system@character-os.local"


def _seed_bootstrap_fixtures_workspace(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Workspace = apps.get_model("accounts", "Workspace")

    owner, _owner_created = User.objects.get_or_create(
        email=BOOTSTRAP_OWNER_EMAIL,
        defaults={
            # Placeholder — cannot log in. Password never set.
            "is_active": False,
            "is_staff": False,
            "is_superuser": False,
        },
    )
    # Owner exists; do NOT flip is_active or promote to staff on
    # subsequent migration runs — that would silently upgrade
    # historical data.

    Workspace.objects.get_or_create(
        slug=BOOTSTRAP_WORKSPACE_SLUG,
        defaults={
            "id": BOOTSTRAP_WORKSPACE_UUID,
            "name": BOOTSTRAP_WORKSPACE_NAME,
            "owner": owner,
        },
    )
    # No Membership rows are created. No CharacterIdentity rows are
    # created. No Teammate rows are created. All of these are
    # verified by the 9.b.0 test suite in ``tests/test_workspace_seed.py``.


def _remove_bootstrap_fixtures_workspace(apps, schema_editor):
    """Reverse migration.

    Removes the workspace + owner only when nothing depends on them
    (defensive PROTECT-check). If any downstream row (a
    CharacterIdentity, an Asset, a Membership) has been attached
    since the forward migration ran, the reverse aborts to prevent
    silent data loss.
    """
    Workspace = apps.get_model("accounts", "Workspace")
    User = apps.get_model("accounts", "User")

    workspace = Workspace.objects.filter(slug=BOOTSTRAP_WORKSPACE_SLUG).first()
    if workspace is not None:
        # Any dependency at all → abort.
        related_counts = {
            rel.get_accessor_name(): getattr(workspace, rel.get_accessor_name()).count()
            for rel in workspace._meta.related_objects
            if rel.get_accessor_name()
        }
        blockers = {k: v for k, v in related_counts.items() if v > 0}
        if blockers:
            raise RuntimeError(
                "Refusing to reverse 9.b.0 workspace seed — dependent rows exist: "
                f"{blockers}. Remove them manually before reversing."
            )
        workspace.delete()

    User.objects.filter(email=BOOTSTRAP_OWNER_EMAIL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            _seed_bootstrap_fixtures_workspace,
            reverse_code=_remove_bootstrap_fixtures_workspace,
        ),
    ]
