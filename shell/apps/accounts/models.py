"""Workspace + Membership — the multi-tenant root.

A Workspace owns Spokespeople, Videos, and Conversations. Memberships
join Users to Workspaces with a role; v1 always has exactly one
owner-role membership, but the schema is multi-seat-ready for the
Agency tier (design doc §6.6).
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Workspace(models.Model):
    """Top-level multi-tenant root. Spokespeople and Videos FK here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_workspaces",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Membership",
        related_name="workspaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "workspace"
            candidate = base
            n = 2
            while Workspace.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base}-{n}"
                n += 1
            self.slug = candidate
        super().save(*args, **kwargs)


class Membership(models.Model):
    """User ↔ Workspace join with a role. v1 only uses ``owner``;
    the other roles exist for the Agency tier (design doc §6.6)."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.OWNER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "workspace")]
        ordering = ["workspace", "created_at"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.workspace} ({self.role})"


def default_workspace_for(user) -> Workspace | None:
    """Return the user's primary workspace.

    v1 model: every user has one workspace they own. This helper picks
    the owned workspace first, then falls back to the oldest membership
    if the user is a member but not an owner. Returns None for users
    with no workspace yet (e.g., fresh signup pre-onboarding).
    """
    owned = user.owned_workspaces.order_by("created_at").first()
    if owned is not None:
        return owned
    membership = user.memberships.select_related("workspace").order_by("created_at").first()
    return membership.workspace if membership else None
