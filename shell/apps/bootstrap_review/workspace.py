"""§19 Step 9.b bootstrap-fixtures workspace identity (SESSION 249, 9.b.0).

Deterministic identity for the infrastructure workspace that owns
canonical-substrate rows for the portrait-qualification fixture set
(fixture_h1..h4). Not a customer workspace.

Design (SESSION 249 architecture plan L1 ratification):

* Deterministic UUIDv5 so the row is bit-identical across
  environments — fresh dev DB, staging, prod all end up with the
  same workspace ID + slug.
* No customer/user memberships. Access to bootstrap-review is
  authorized via ``IsOperator`` (staff/superuser flags), NOT
  ``IsWorkspaceMember``.
* A stable infrastructure ``User`` is created as the workspace
  ``owner`` because ``Workspace.owner`` is a required FK
  (``on_delete=PROTECT``). This user is ``is_active=False`` — it
  cannot log in — and is documented as bootstrap-infrastructure,
  not a customer account.
* Bootstrap fixture ``CharacterIdentity`` rows land in this
  workspace with ``teammate=NULL`` per §15.1 (permitted by the
  substrate; enforced by the partial unique
  ``one_character_identity_per_teammate WHERE teammate IS NOT NULL``).
  9.b.0 does NOT create those CharacterIdentity rows — that happens
  lazily on the first reviewer ``select`` decision at 9.b.3.
"""
from __future__ import annotations

import uuid

# Deterministic identifiers. UUIDv5 pins the workspace ID across
# environments so tests, docs, and inspection can all reference
# the same UUID literal without any per-environment lookup.
BOOTSTRAP_WORKSPACE_SLUG = "bootstrap-fixtures"
BOOTSTRAP_WORKSPACE_NAME = (
    "Bootstrap Fixtures (portrait qualification infrastructure)"
)
BOOTSTRAP_WORKSPACE_UUID = uuid.uuid5(
    uuid.NAMESPACE_DNS,
    "bootstrap-fixtures.character-os.internal",
)

# Deterministic infrastructure owner (never a customer). Email is
# unique in the accounts.User model, so ``get_or_create(email=...)``
# is idempotent. The address is under a non-routable ``.local``
# suffix so it can never accept mail; ``is_active=False`` ensures
# it cannot authenticate.
BOOTSTRAP_OWNER_EMAIL = "bootstrap-fixtures-owner+system@character-os.local"

__all__ = [
    "BOOTSTRAP_WORKSPACE_SLUG",
    "BOOTSTRAP_WORKSPACE_NAME",
    "BOOTSTRAP_WORKSPACE_UUID",
    "BOOTSTRAP_OWNER_EMAIL",
]
