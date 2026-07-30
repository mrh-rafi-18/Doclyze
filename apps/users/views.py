"""Views for /api/users/."""

from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.responses import success_response, no_content_response
from .serializers import (
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    UpdatePreferencesSerializer,
    UpdateProfileSerializer,
    UserProfileSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@extend_schema(tags=["Users"])
class MeView(APIView):
    """GET / PATCH /api/users/me"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        responses={200: UserProfileSerializer},
    )
    def get(self, request: Request) -> Response:
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return success_response(serializer.data)

    @extend_schema(
        summary="Update user profile (display name)",
        request=UpdateProfileSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request: Request) -> Response:
        serializer = UpdateProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            UserProfileSerializer(request.user, context={"request": request}).data,
            "Profile updated successfully.",
        )


@extend_schema(tags=["Users"])
class MePreferencesView(APIView):
    """PATCH /api/users/me/preferences"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update user preferences (theme)",
        request=UpdatePreferencesSerializer,
        responses={200: UserProfileSerializer},
    )
    def patch(self, request: Request) -> Response:
        serializer = UpdatePreferencesSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            UserProfileSerializer(request.user, context={"request": request}).data,
            "Preferences updated successfully.",
        )


@extend_schema(tags=["Users"])
class AvatarView(APIView):
    """POST / DELETE /api/users/me/avatar"""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload user avatar",
        request=AvatarUploadSerializer,
        responses={200: UserProfileSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = AvatarUploadSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        # Remove old avatar file if it exists
        old_avatar = request.user.avatar
        if old_avatar:
            try:
                old_avatar.delete(save=False)
            except Exception:
                pass
        serializer.save()
        return success_response(
            UserProfileSerializer(request.user, context={"request": request}).data,
            "Avatar uploaded successfully.",
        )

    @extend_schema(
        summary="Delete user avatar",
        responses={200: OpenApiResponse(description="Avatar removed.")},
    )
    def delete(self, request: Request) -> Response:
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=["avatar"])
        return success_response(message="Avatar removed successfully.")


@extend_schema(tags=["Users"])
class ChangePasswordView(APIView):
    """POST /api/users/me/change-password"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password (requires current password)",
        request=ChangePasswordSerializer,
        responses={200: OpenApiResponse(description="Password changed.")},
    )
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["current_password"]):
            from rest_framework.exceptions import ValidationError

            raise ValidationError({"current_password": "Current password is incorrect."})

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        logger.info("User %s changed their password.", user.pk)
        return success_response(message="Password changed successfully.")


@extend_schema(tags=["Users"])
class DeleteAccountView(APIView):
    """DELETE /api/users/me"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Permanently delete user account",
        responses={204: OpenApiResponse(description="Account deleted.")},
    )
    def delete(self, request: Request) -> Response:
        user = request.user
        logger.warning("Deleting account for user %s.", user.pk)
        # Delete avatar file
        if user.avatar:
            try:
                user.avatar.delete(save=False)
            except Exception:
                pass
        user.delete()
        return no_content_response()
