"""Models for authentication: email tokens and user sessions."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class TokenPurpose(models.TextChoices):
    EMAIL_VERIFICATION = "email_verification", "Email Verification"
    PASSWORD_RESET = "password_reset", "Password Reset"


class EmailToken(models.Model):
    """Single-use token for email verification and password reset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_tokens",
    )
    token = models.CharField(max_length=128, unique=True, db_index=True)
    purpose = models.CharField(max_length=30, choices=TokenPurpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token", "purpose"]),
        ]

    def __str__(self) -> str:
        return f"{self.purpose} token for {self.user}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_expired and self.used_at is None

    def mark_used(self) -> None:
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])


class UserSession(models.Model):
    """Tracks active JWT sessions per user for session management."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    jti = models.CharField(max_length=255, unique=True, db_index=True, help_text="JWT ID (jti) claim")
    user_agent = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self) -> str:
        status = "active" if self.is_active else "revoked"
        return f"Session {self.jti[:8]}… ({status}) for {self.user}"
