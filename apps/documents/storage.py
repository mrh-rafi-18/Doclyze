"""
Centralised storage helpers for document files.
All paths returned are RELATIVE to MEDIA_ROOT so they can be stored in the DB.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

if TYPE_CHECKING:
    from .models import Document

logger = logging.getLogger(__name__)


def save_uploaded_document(document_id: str, owner_id: str, uploaded_file: UploadedFile) -> tuple[str, str]:
    """
    Persist *uploaded_file* to the local filesystem.

    Returns
    -------
    (relative_path, filename)
        relative_path is relative to MEDIA_ROOT and safe to store in the DB.
    """
    filename = uploaded_file.name or "document"
    # Sanitise filename
    filename = os.path.basename(filename)

    dest_dir = Path(settings.DOCUMENTS_UPLOAD_DIR) / owner_id / document_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_path = dest_dir / filename
    # Handle name collisions
    counter = 1
    while dest_path.exists():
        stem, ext = os.path.splitext(filename)
        dest_path = dest_dir / f"{stem}_{counter}{ext}"
        counter += 1

    with open(dest_path, "wb") as dest:
        for chunk in uploaded_file.chunks():
            dest.write(chunk)

    relative = str(dest_path.relative_to(Path(settings.MEDIA_ROOT)))
    return relative, dest_path.name


def delete_document_files(document: "Document") -> None:
    """Remove all files associated with a Document instance."""
    paths_to_delete: list[Path] = []

    if document.original_file_path:
        paths_to_delete.append(document.original_absolute)
    if document.layout_pdf_path:
        p = document.layout_absolute
        if p:
            paths_to_delete.append(p)
    if document.markdown_path:
        p = document.markdown_absolute
        if p:
            paths_to_delete.append(p)

    for path in paths_to_delete:
        try:
            if path.exists():
                path.unlink()
        except OSError as exc:
            logger.warning("Could not delete %s: %s", path, exc)

    # Remove empty directories
    for path in paths_to_delete:
        try:
            d = path.parent
            if d.exists() and not any(d.iterdir()):
                d.rmdir()
        except OSError:
            pass
