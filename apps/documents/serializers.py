"""Serializers for the documents app."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from .models import Document


class DocumentUploadSerializer(serializers.Serializer):
    """POST /api/documents/ — upload a document for processing."""

    file = serializers.FileField()

    def validate_file(self, value: object) -> object:
        # Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_bytes:
            from core.exceptions import FileTooLargeError

            raise FileTooLargeError(
                f"File size ({value.size / 1024 / 1024:.1f} MB) exceeds "
                f"the maximum allowed size ({settings.MAX_UPLOAD_SIZE_MB} MB)."
            )

        # Validate file type
        if value.content_type not in settings.ALLOWED_DOCUMENT_TYPES:
            from core.exceptions import UnsupportedFileTypeError

            raise UnsupportedFileTypeError(
                f"File type '{value.content_type}' is not supported. "
                f"Allowed types: {', '.join(settings.ALLOWED_DOCUMENT_TYPES)}"
            )

        return value


class DocumentListSerializer(serializers.ModelSerializer):
    """GET /api/documents/ — list view with summary fields."""

    file_size_display = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "mime_type",
            "file_size",
            "file_size_display",
            "status",
            "pages",
            "created_at",
            "processed_at",
        ]
        read_only_fields = fields


class DocumentDetailSerializer(serializers.ModelSerializer):
    """GET /api/documents/{id}/ — full detail view."""

    file_size_display = serializers.CharField(read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_failed = serializers.BooleanField(read_only=True)
    download_urls = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "original_filename",
            "mime_type",
            "file_size",
            "file_size_display",
            "status",
            "pages",
            "error_message",
            "is_completed",
            "is_failed",
            "download_urls",
            "created_at",
            "updated_at",
            "processed_at",
        ]
        read_only_fields = fields

    def get_download_urls(self, obj: Document) -> dict:
        request = self.context.get("request")
        urls: dict = {}

        if obj.original_file_path:
            path = f"{settings.MEDIA_URL}{obj.original_file_path}"
            urls["original"] = request.build_absolute_uri(path) if request else path

        if obj.layout_pdf_path:
            path = f"{settings.MEDIA_URL}{obj.layout_pdf_path}"
            urls["layout_pdf"] = request.build_absolute_uri(path) if request else path

        if obj.markdown_path:
            path = f"{settings.MEDIA_URL}{obj.markdown_path}"
            urls["markdown"] = request.build_absolute_uri(path) if request else path

        return urls
