"""Admin configuration for the documents app."""

from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "owner",
        "status",
        "file_size_display",
        "pages",
        "created_at",
        "processed_at",
    )
    list_filter = ("status", "mime_type", "created_at")
    search_fields = ("original_filename", "owner__email")
    readonly_fields = (
        "id",
        "file_size",
        "file_size_display",
        "original_file_path",
        "layout_pdf_path",
        "markdown_path",
        "created_at",
        "updated_at",
        "processed_at",
    )
    ordering = ("-created_at",)
    raw_id_fields = ("owner",)

    def file_size_display(self, obj: Document) -> str:
        return obj.file_size_display

    file_size_display.short_description = "Size"  # type: ignore[attr-defined]
