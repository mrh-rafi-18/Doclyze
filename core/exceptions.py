"""
Centralised DRF exception handler.
All API errors are returned as a consistent JSON envelope:

    {
        "success": false,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Human-readable summary",
            "details": { ... }   # field-level errors or extra context
        }
    }
"""

from __future__ import annotations

import logging
from typing import Any

from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAcceptable,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied as DRFPermissionDenied,
    Throttled,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ── Mapping: exception type → (error_code, http_status) ──────────────────────

_STATUS_MAP: dict[type, tuple[str, int]] = {
    ValidationError: ("VALIDATION_ERROR", status.HTTP_400_BAD_REQUEST),
    ParseError: ("PARSE_ERROR", status.HTTP_400_BAD_REQUEST),
    NotAuthenticated: ("NOT_AUTHENTICATED", status.HTTP_401_UNAUTHORIZED),
    AuthenticationFailed: ("AUTHENTICATION_FAILED", status.HTTP_401_UNAUTHORIZED),
    DRFPermissionDenied: ("FORBIDDEN", status.HTTP_403_FORBIDDEN),
    NotFound: ("NOT_FOUND", status.HTTP_404_NOT_FOUND),
    MethodNotAllowed: ("METHOD_NOT_ALLOWED", status.HTTP_405_METHOD_NOT_ALLOWED),
    NotAcceptable: ("NOT_ACCEPTABLE", status.HTTP_406_NOT_ACCEPTABLE),
    UnsupportedMediaType: ("UNSUPPORTED_MEDIA_TYPE", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    Throttled: ("THROTTLED", status.HTTP_429_TOO_MANY_REQUESTS),
}


def _error_payload(code: str, message: str, details: Any = None) -> dict:
    payload: dict = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details
    return payload


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """Drop-in replacement for DRF's default exception_handler."""

    # Let DRF normalise Django's built-in exceptions first
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = DRFPermissionDenied()

    response = exception_handler(exc, context)

    if response is None:
        # Unhandled server error – log it and return 500
        logger.exception("Unhandled exception in view: %s", exc)
        return Response(
            _error_payload(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred. Please try again later.",
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Look up the exception type in our map; for custom APIException subclasses
    # that aren't in the map, fall back to their own default_code and status_code.
    mapped = _STATUS_MAP.get(type(exc))
    if mapped:
        code, http_status = mapped
    elif isinstance(exc, APIException):
        code = getattr(exc, "default_code", "API_ERROR")
        http_status = exc.status_code
    else:
        code = "API_ERROR"
        http_status = response.status_code

    # For ValidationError the detail may be a dict of field errors
    if isinstance(exc, ValidationError):
        details = response.data
        message = "Request validation failed. Please check the provided data."
    else:
        details = None
        raw = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
        message = str(raw)

    response.data = _error_payload(code, message, details)
    response.status_code = http_status
    return response


# ── Custom application exceptions ─────────────────────────────────────────────

class DocumentProcessingError(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "DOCUMENT_PROCESSING_ERROR"
    default_detail = "Document processing failed."


class AnalyzerUnavailableError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "ANALYZER_UNAVAILABLE"
    default_detail = "The document analysis engine is currently unavailable."


class FileTooLargeError(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_code = "FILE_TOO_LARGE"
    default_detail = "The uploaded file exceeds the maximum allowed size."


class UnsupportedFileTypeError(APIException):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_code = "UNSUPPORTED_FILE_TYPE"
    default_detail = "The uploaded file type is not supported."


class EmailNotVerifiedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "EMAIL_NOT_VERIFIED"
    default_detail = "Please verify your email address before proceeding."
