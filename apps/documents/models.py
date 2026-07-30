"""Document model for the documents app."""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProcessingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Document(models.Model):
    """
    Represents an uploaded document and its processing results.

    Fields
    ------
    id                : UUID primary key.
    owner             : The user who uploaded the document.
    original_filename : Original name of the uploaded file.
    original_file_path: Relative path (from MEDIA_ROOT) to the stored upload.
    file_size         : Size in bytes.
    mime_type         : MIME type of the uploaded file.
    status            : Processing pipeline status.
    pages             : Number of pages detected (set after processing).
    layout_pdf_path   : Relative path to the layout-annotated PDF output.
    markdown_path     : Relative path to the Markdown transcription output.
    error_message     : Error details if processing failed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    # Upload metadata
    original_filename = models.CharField(max_length=255)
    original_file_path = models.CharField(max_length=512, help_text="Relative to MEDIA_ROOT")
    file_size = models.PositiveBigIntegerField(help_text="File size in bytes")
    mime_type = models.CharField(max_length=100)

    # Processing state
    status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        db_index=True,
    )
    pages = models.PositiveIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    # Output paths (relative to MEDIA_ROOT)
    layout_pdf_path = models.CharField(max_length=512, blank=True, default="")
    markdown_path = models.CharField(max_length=512, blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "documents"
        ordering = ["-created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.original_filename} ({self.status})"

    # ── Absolute path helpers ─────────────────────────────────────────────────

    @property
    def original_absolute(self) -> Path:
        return Path(settings.MEDIA_ROOT) / self.original_file_path

    @property
    def layout_absolute(self) -> Path | None:
        if self.layout_pdf_path:
            return Path(settings.MEDIA_ROOT) / self.layout_pdf_path
        return None

    @property
    def markdown_absolute(self) -> Path | None:
        if self.markdown_path:
            return Path(settings.MEDIA_ROOT) / self.markdown_path
        return None

    @property
    def is_completed(self) -> bool:
        return self.status == ProcessingStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.status == ProcessingStatus.FAILED

    @property
    def file_size_display(self) -> str:
        """Human-readable file size."""
        size = self.file_size
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
