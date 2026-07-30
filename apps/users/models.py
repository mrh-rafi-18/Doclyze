"""Custom User model with email-based authentication."""

from __future__ import annotations

import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    def create_user(self, email: str, password: str | None = None, **extra: object) -> "User":
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        user: User = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra: object) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("is_email_verified", True)

        if extra.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra)


class ThemeChoice(models.TextChoices):
    LIGHT = "light", "Light"
    DARK = "dark", "Dark"
    SYSTEM = "system", "System"


def avatar_upload_path(instance: "User", filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1]
    return f"avatars/{instance.pk}.{ext}"


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model.

    Fields
    ------
    id          : UUID primary key.
    email       : Unique login identifier.
    display_name: Optional human-friendly name.
    avatar      : Optional profile picture.
    theme       : UI preference (light / dark / system).
    is_email_verified: Whether the user completed email verification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=150, blank=True, default="")
    avatar = models.ImageField(upload_to=avatar_upload_path, null=True, blank=True)

    # Preferences
    theme = models.CharField(
        max_length=10,
        choices=ThemeChoice.choices,
        default=ThemeChoice.SYSTEM,
    )

    # Status flags
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects: UserManager = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email

    @property
    def has_avatar(self) -> bool:
        return bool(self.avatar)

    @property
    def initials(self) -> str:
        if self.display_name:
            parts = self.display_name.split()
            return "".join(p[0].upper() for p in parts[:2])
        return self.email[0].upper()
