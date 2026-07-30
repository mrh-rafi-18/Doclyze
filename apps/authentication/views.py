"""Views for /api/auth/."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from apps.users.serializers import UserProfileSerializer
from core.responses import success_response, created_response

from .models import EmailToken, TokenPurpose
from .serializers import (
    CustomTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    VerifyEmailSerializer,
)
from .services import (
    create_session,
    get_client_ip,
    revoke_all_sessions,
    send_password_reset_email,
    send_verification_email,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class AuthThrottle(ScopedRateThrottle):
    scope = "auth"


# ── Register ──────────────────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class RegisterView(APIView):
    """POST /api/auth/register/"""

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Register a new user account",
        request=RegisterSerializer,
        responses={201: UserProfileSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email (non-blocking; failure is logged)
        send_verification_email(user)

        return created_response(
            UserProfileSerializer(user, context={"request": request}).data,
            "Account created. Please check your email to verify your address.",
        )


# ── Login ─────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class LoginView(APIView):
    """POST /api/auth/login/"""

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Obtain JWT token pair (login)",
        request=CustomTokenObtainPairSerializer,
        responses={200: OpenApiResponse(description="JWT access + refresh + user profile.")},
    )
    def post(self, request: Request) -> Response:
        serializer = CustomTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Track the session
        user = serializer.user
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        create_session(
            user=user,
            jti=str(refresh["jti"]),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            ip_address=get_client_ip(request),
        )

        data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserProfileSerializer(user, context={"request": request}).data,
        }
        return success_response(data, "Login successful.")


# ── Logout ────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    """POST /api/auth/logout/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout (blacklist refresh token)",
        responses={200: OpenApiResponse(description="Logged out.")},
    )
    def post(self, request: Request) -> Response:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken

                token = RefreshToken(refresh_token)
                token.blacklist()

                # Deactivate the matching session
                from .models import UserSession

                UserSession.objects.filter(
                    user=request.user, jti=str(token["jti"]), is_active=True
                ).update(is_active=False)

            except Exception:
                pass  # Token may already be blacklisted

        return success_response(message="Logged out successfully.")


# ── Logout All Sessions ──────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class LogoutAllView(APIView):
    """POST /api/auth/logout-all/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout from all devices",
        responses={200: OpenApiResponse(description="All sessions revoked.")},
    )
    def post(self, request: Request) -> Response:
        revoke_all_sessions(request.user)
        logger.info("User %s revoked all sessions.", request.user.pk)
        return success_response(message="All sessions have been revoked.")


# ── Token Refresh ─────────────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class TokenRefreshView(BaseTokenRefreshView):
    """POST /api/auth/token/refresh/"""

    pass


# ── Email Verification ───────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class VerifyEmailView(APIView):
    """POST /api/auth/verify-email/"""

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Verify email address with token",
        request=VerifyEmailSerializer,
        responses={200: OpenApiResponse(description="Email verified.")},
    )
    def post(self, request: Request) -> Response:
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = EmailToken.objects.get(
                token=serializer.validated_data["token"],
                purpose=TokenPurpose.EMAIL_VERIFICATION,
            )
        except EmailToken.DoesNotExist:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"token": "Invalid or expired verification token."})

        if not token_obj.is_valid:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"token": "This token has expired or has already been used."})

        token_obj.mark_used()
        user = token_obj.user
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        logger.info("User %s verified their email.", user.pk)
        return success_response(message="Email verified successfully.")


# ── Resend Verification ──────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class ResendVerificationView(APIView):
    """POST /api/auth/resend-verification/"""

    permission_classes = [IsAuthenticated]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Resend email verification link",
        responses={200: OpenApiResponse(description="Verification email sent.")},
    )
    def post(self, request: Request) -> Response:
        user = request.user
        if user.is_email_verified:
            return success_response(message="Email is already verified.")

        send_verification_email(user)
        return success_response(message="Verification email sent. Please check your inbox.")


# ── Forgot Password ──────────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class ForgotPasswordView(APIView):
    """POST /api/auth/forgot-password/"""

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Request a password reset email",
        request=ForgotPasswordSerializer,
        responses={200: OpenApiResponse(description="Reset email sent (if account exists).")},
    )
    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Always return success to prevent email enumeration
        try:
            user = User.objects.get(email=serializer.validated_data["email"])
            send_password_reset_email(user)
        except User.DoesNotExist:
            pass

        return success_response(
            message="If an account with that email exists, a password reset link has been sent."
        )


# ── Reset Password ───────────────────────────────────────────────────────────


@extend_schema(tags=["Authentication"])
class ResetPasswordView(APIView):
    """POST /api/auth/reset-password/"""

    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]

    @extend_schema(
        summary="Reset password with token",
        request=ResetPasswordSerializer,
        responses={200: OpenApiResponse(description="Password reset.")},
    )
    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token_obj = EmailToken.objects.get(
                token=serializer.validated_data["token"],
                purpose=TokenPurpose.PASSWORD_RESET,
            )
        except EmailToken.DoesNotExist:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"token": "Invalid or expired reset token."})

        if not token_obj.is_valid:
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"token": "This token has expired or has already been used."})

        token_obj.mark_used()
        user = token_obj.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Revoke all existing sessions for security
        revoke_all_sessions(user)

        logger.info("User %s reset their password.", user.pk)
        return success_response(message="Password has been reset successfully.")
