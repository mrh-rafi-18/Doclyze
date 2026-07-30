"""
Celery tasks for background document processing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def process_document_task(document_id: str) -> None:
    """
    Standalone function that can be called directly or via Celery.
    Designed to be safe to call from both sync and async contexts.
    """
    from .models import Document, ProcessingStatus
    from .analyzer import get_analyzer
    from core.exceptions import AnalyzerUnavailableError

    try:
        document = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error("Document %s not found for processing.", document_id)
        return

    if document.status == ProcessingStatus.COMPLETED:
        return

    document.status = ProcessingStatus.PROCESSING
    document.save(update_fields=["status"])

    try:
        analyzer = get_analyzer()
    except AnalyzerUnavailableError as exc:
        document.status = ProcessingStatus.FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message"])
        logger.error("Analyzer unavailable for doc %s: %s", document_id, exc)
        return

    # Per-document output directory keeps outputs organised
    output_dir = Path(settings.DOCUMENTS_OUTPUT_DIR) / str(document.owner_id) / str(document_id)

    try:
        result = analyzer.process_document(
            input_file=document.original_absolute,
            output_dir=output_dir,
        )

        media_root = Path(settings.MEDIA_ROOT)
        document.layout_pdf_path = str(result["layout_pdf"].relative_to(media_root))
        document.markdown_path = str(result["markdown"].relative_to(media_root))
        document.pages = result["pages"]
        document.status = ProcessingStatus.COMPLETED
        document.processed_at = timezone.now()
        document.save(update_fields=[
            "layout_pdf_path", "markdown_path", "pages",
            "status", "processed_at",
        ])
        logger.info("Document %s processed successfully (%d pages).", document_id, result["pages"])

    except FileNotFoundError as exc:
        document.status = ProcessingStatus.FAILED
        document.error_message = f"Source file not found: {exc}"
        document.save(update_fields=["status", "error_message"])
        logger.error("FileNotFoundError for doc %s: %s", document_id, exc)

    except Exception as exc:
        document.status = ProcessingStatus.FAILED
        document.error_message = str(exc)
        document.save(update_fields=["status", "error_message"])
        logger.exception("Unexpected error processing doc %s.", document_id)


# ── Celery task wrapper ───────────────────────────────────────────────────────

try:
    from config.celery import app as celery_app

    @celery_app.task(
        bind=True,
        name="documents.process_document",
        max_retries=2,
        default_retry_delay=30,
        acks_late=True,
    )
    def celery_process_document(self, document_id: str) -> None:  # type: ignore[misc]
        try:
            process_document_task(document_id)
        except Exception as exc:
            logger.exception("Celery task failed for doc %s: %s", document_id, exc)
            raise self.retry(exc=exc)

except ImportError:
    # Celery not configured; tasks run synchronously (useful in testing)
    celery_process_document = None  # type: ignore[assignment]
