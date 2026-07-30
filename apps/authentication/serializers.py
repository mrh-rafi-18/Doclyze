"""Serializers for authentication flows."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extends the default JWT login serializer to include user profile in the response."""

    def validate(self, attrs: dict) -> dict:
        data = super().validate(attrs)
        # Add user profile data to the token response
        from apps.users.serializers import UserProfileSerializer

        data["user"] = UserProfileSerializer(self.user).data
        return data


class RegisterSerializer(serializers.ModelSerializer):
    """POST /api/auth/register/ — create a new user account."""

    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "display_name", "password", "confirm_password"]
        extra_kwargs = {
            "display_name": {"required": False},
        }

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data: dict) -> object:
        return User.objects.create_user(**validated_data)


class VerifyEmailSerializer(serializers.Serializer):
    """POST /api/auth/verify-email/ — verify email with token."""

    token = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    """POST /api/auth/forgot-password/ — request a password reset email."""

    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """POST /api/auth/reset-password/ — reset password with token."""

    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs
