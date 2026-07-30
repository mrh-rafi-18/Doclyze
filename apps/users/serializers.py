"""Serializers for the users app."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Read-only profile returned after auth or GET /api/users/me."""

    has_avatar = serializers.BooleanField(read_only=True)
    initials = serializers.CharField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "theme",
            "is_email_verified",
            "has_avatar",
            "avatar_url",
            "initials",
            "date_joined",
            "updated_at",
        ]
        read_only_fields = fields

    def get_avatar_url(self, obj: object) -> str | None:
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class UpdateProfileSerializer(serializers.ModelSerializer):
    """PATCH /api/users/me — update display_name."""

    class Meta:
        model = User
        fields = ["display_name"]

    def validate_display_name(self, value: str) -> str:
        value = value.strip()
        if len(value) > 150:
            raise serializers.ValidationError("Display name must be 150 characters or fewer.")
        return value


class UpdatePreferencesSerializer(serializers.ModelSerializer):
    """PATCH /api/users/me/preferences — update theme."""

    class Meta:
        model = User
        fields = ["theme"]


class AvatarUploadSerializer(serializers.ModelSerializer):
    """POST /api/users/me/avatar."""

    class Meta:
        model = User
        fields = ["avatar"]

    def validate_avatar(self, value: object) -> object:
        max_size = 5 * 1024 * 1024  # 5 MB
        if hasattr(value, "size") and value.size > max_size:
            raise serializers.ValidationError("Avatar file must be under 5 MB.")
        allowed = ["image/jpeg", "image/png", "image/webp"]
        if hasattr(value, "content_type") and value.content_type not in allowed:
            raise serializers.ValidationError("Only JPEG, PNG and WebP images are allowed.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """POST /api/users/me/change-password."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from current password."}
            )
        return attrs
