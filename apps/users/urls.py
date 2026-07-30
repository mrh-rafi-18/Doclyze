"""URL configuration for the users app."""

from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("me/", views.MeView.as_view(), name="me"),
    path("me/preferences/", views.MePreferencesView.as_view(), name="me-preferences"),
    path("me/avatar/", views.AvatarView.as_view(), name="me-avatar"),
    path("me/change-password/", views.ChangePasswordView.as_view(), name="me-change-password"),
    path("me/delete/", views.DeleteAccountView.as_view(), name="me-delete"),
]
