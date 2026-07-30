"""Utility helpers that wrap DRF Response in a standard envelope."""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response


def success_response(
    data: Any = None,
    message: str = "Success",
    http_status: int = status.HTTP_200_OK,
) -> Response:
    payload: dict = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return Response(payload, status=http_status)


def created_response(data: Any, message: str = "Resource created successfully.") -> Response:
    return success_response(data, message, status.HTTP_201_CREATED)


def no_content_response() -> Response:
    """Return a proper 204 No Content response (empty body)."""
    return Response(status=status.HTTP_204_NO_CONTENT)
