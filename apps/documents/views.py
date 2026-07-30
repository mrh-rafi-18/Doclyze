"""Views for /api/documents/."""

from __future__ import annotations

import logging
import uuid

from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.responses import success_response, created_response, no_content_response

from .models import Document, ProcessingStatus
from .serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
    DocumentUploadSerializer,
)
from .storage import save_uploaded_document, delete_document_files

logger = logging.getLogger(__name__)


# ── Upload ────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Documents"])
class DocumentUploadView(APIView):
    """POST /api/documents/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Upload a document for processing",
        request=DocumentUploadSerializer,
        responses={201: DocumentDetailSerializer},
    )
    def post(self, request: Request) -> Response:
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]

        doc_id = str(uuid.uuid4())
        relative_path, final_filename = save_uploaded_document(
            document_id=doc_id,
            owner_id=str(request.user.pk),
            uploaded_file=uploaded_file,
        )

        document = Document.objects.create(
            id=doc_id,
            owner=request.user,
            original_filename=final_filename,
            original_file_path=relative_path,
            file_size=uploaded_file.size,
            mime_type=uploaded_file.content_type or "application/octet-stream",
            status=ProcessingStatus.PENDING,
        )

        # Dispatch background processing
        self._dispatch_processing(str(document.id))

        logger.info(
            "User %s uploaded document %s (%s, %d bytes).",
            request.user.pk,
            document.id,
            final_filename,
            uploaded_file.size,
        )

        return created_response(
            DocumentDetailSerializer(document, context={"request": request}).data,
            "Document uploaded successfully. Processing has started.",
        )

    @staticmethod
    def _dispatch_processing(document_id: str) -> None:
        """Try Celery first; fall back to sync processing."""
        from .tasks import celery_process_document, process_document_task

        if celery_process_document is not None:
            try:
                celery_process_document.delay(document_id)
                return
            except Exception:
                pass

        process_document_task(document_id)


# ── List ──────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Documents"])
@extend_schema_view(
    get=extend_schema(summary="List user's documents"),
)
class DocumentListView(ListAPIView):
    """GET /api/documents/"""

    permission_classes = [IsAuthenticated]
    serializer_class = DocumentListSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "mime_type"]
    search_fields = ["original_filename"]
    ordering_fields = ["created_at", "file_size", "original_filename", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


# ── Detail ────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Documents"])
class DocumentDetailView(APIView):
    """GET /api/documents/{id}/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get document details",
        responses={200: DocumentDetailSerializer},
    )
    def get(self, request: Request, document_id: str) -> Response:
        document = get_object_or_404(
            Document, id=document_id, owner=request.user
        )
        serializer = DocumentDetailSerializer(document, context={"request": request})
        return success_response(serializer.data)


# ── Delete ────────────────────────────────────────────────────────────────────


@extend_schema(tags=["Documents"])
class DocumentDeleteView(APIView):
    """DELETE /api/documents/{id}/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete a document and its files",
        responses={204: OpenApiResponse(description="Document deleted.")},
    )
    def delete(self, request: Request, document_id: str) -> Response:
        document = get_object_or_404(
            Document, id=document_id, owner=request.user
        )

        logger.info("User %s deleting document %s.", request.user.pk, document.id)
        delete_document_files(document)
        document.delete()

        return no_content_response()


# ── Retry Processing ─────────────────────────────────────────────────────────


@extend_schema(tags=["Documents"])
class DocumentRetryView(APIView):
    """POST /api/documents/{id}/retry/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Retry processing a failed document",
        responses={200: DocumentDetailSerializer},
    )
    def post(self, request: Request, document_id: str) -> Response:
        document = get_object_or_404(
            Document, id=document_id, owner=request.user
        )

        if document.status != ProcessingStatus.FAILED:
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                {"status": "Only failed documents can be retried."}
            )

        document.status = ProcessingStatus.PENDING
        document.error_message = ""
        document.save(update_fields=["status", "error_message"])

        DocumentUploadView._dispatch_processing(str(document.id))

        logger.info("User %s retrying document %s.", request.user.pk, document.id)
        return success_response(
            DocumentDetailSerializer(document, context={"request": request}).data,
            "Document reprocessing has started.",
        )
