"""User + Workspace + Membership — the multi-tenant root.

A Workspace owns Spokespeople, Videos, and Conversations. Memberships
join Users to Workspaces with a role; v1 always has exactly one
owner-role membership, but the schema is multi-seat-ready for the
Agency tier (design doc §6.6).

The User model is **custom** (SESSION 119) — email as the primary
identifier, no username column. Replaces the SESSION 116
``WorkspaceAccountAdapter`` band-aid that papered over Django's
stock ``auth.User`` UNIQUE-constraint on the username column when
allauth signed everyone up with ``username=""``.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class UserManager(BaseUserManager["User"]):
    """Manager for the custom email-as-PK User model.

    ``use_in_migrations = True`` so Django's migration framework can
    refer back to the manager when generating user-touching
    migrations (e.g., ``createsuperuser``).
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user. Email is the primary identifier.

    No username column. ``allauth.headless`` signs users up with just
    email + password; the SESSION 116 band-aid populated ``username``
    from a hash of the email to satisfy Django's stock UNIQUE
    constraint. This model removes the column entirely so future
    signups don't carry the indirection.
    """

    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the admin site.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Set to False to disable the account without deleting it.",
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        """``allauth``'s default adapter calls this when serialising
        the user. Email is the most-stable identifier we have at v1;
        when a profile model lands, this overrides to ``f"{first} {last}"``.
        """
        return self.email

    def get_short_name(self) -> str:
        return self.email.split("@", 1)[0]


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


def default_workspace_for(user: User) -> Workspace | None:
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
