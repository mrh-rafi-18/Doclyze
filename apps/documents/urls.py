"""URL configuration for the documents app."""

from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.DocumentUploadView.as_view(), name="upload"),
    path("list/", views.DocumentListView.as_view(), name="list"),
    path("<uuid:document_id>/", views.DocumentDetailView.as_view(), name="detail"),
    path("<uuid:document_id>/delete/", views.DocumentDeleteView.as_view(), name="delete"),
    path("<uuid:document_id>/retry/", views.DocumentRetryView.as_view(), name="retry"),
]
