"""Admin configuration for the users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("email", "display_name", "is_email_verified", "is_active", "is_staff", "date_joined")
    list_filter = ("is_active", "is_staff", "is_email_verified", "theme", "date_joined")
    search_fields = ("email", "display_name")
    ordering = ("-date_joined",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "avatar", "theme")}),
        ("Status", {"fields": ("is_email_verified", "is_active", "is_staff", "is_superuser")}),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
        ("Timestamps", {"fields": ("date_joined", "updated_at", "last_login")}),
    )
    readonly_fields = ("date_joined", "updated_at", "last_login")

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "display_name", "is_active", "is_staff"),
        }),
    )
