"""
Business logic for authentication flows.
Keeps views thin and testable.
"""

from __future__ import annotations

import logging
import secrets
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .models import EmailToken, TokenPurpose, UserSession

if TYPE_CHECKING:
    from apps.users.models import User
    from rest_framework.request import Request

logger = logging.getLogger(__name__)


# ── Token helpers ─────────────────────────────────────────────────────────────

def generate_email_token(user: "User", purpose: str) -> EmailToken:
    """Create a fresh single-use token, invalidating any existing ones."""
    EmailToken.objects.filter(
        user=user, purpose=purpose, used_at__isnull=True
    ).update(used_at=timezone.now())

    raw_token = secrets.token_urlsafe(48)
    return EmailToken.objects.create(user=user, token=raw_token, purpose=purpose)


def send_verification_email(user: "User") -> None:
    token_obj = generate_email_token(user, TokenPurpose.EMAIL_VERIFICATION)
    try:
        send_mail(
            subject="Verify your Doclyze email address",
            message=(
                f"Hi {user.display_name or user.email},\n\n"
                f"Click the link below to verify your email:\n{verify_url}\n\n"
                "This link expires in 24 hours."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", user.email, exc)


def send_password_reset_email(user: "User") -> None:
    token_obj = generate_email_token(user, TokenPurpose.PASSWORD_RESET)
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token_obj.token}"
    try:
        send_mail(
            subject="Reset your Doclyze password",
            message=(
                f"Hi {user.display_name or user.email},\n\n"
                f"Click the link below to reset your password:\n{reset_url}\n\n"
                "This link expires in 24 hours. If you did not request this, ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error("Failed to send password reset email to %s: %s", user.email, exc)


# ── Session management ────────────────────────────────────────────────────────

def create_session(user: "User", jti: str, user_agent: str, ip_address: str | None) -> UserSession:
    return UserSession.objects.create(
        user=user,
        jti=jti,
        user_agent=user_agent,
        ip_address=ip_address,
    )


def _blacklist_jti(jti: str) -> None:
    """Add a refresh token JTI to simplejwt's blacklist."""
    try:
        outstanding = OutstandingToken.objects.get(jti=jti)
        BlacklistedToken.objects.get_or_create(token=outstanding)
    except OutstandingToken.DoesNotExist:
        logger.warning("Outstanding token with JTI %s not found; skipping blacklist.", jti)


def revoke_session(session: UserSession) -> None:
    _blacklist_jti(session.jti)
    session.is_active = False
    session.save(update_fields=["is_active"])


def revoke_all_sessions(user: "User") -> None:
    active_sessions = UserSession.objects.filter(user=user, is_active=True)
    for session in active_sessions:
        _blacklist_jti(session.jti)
    active_sessions.update(is_active=False)


def get_client_ip(request: "Request") -> str | None:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
