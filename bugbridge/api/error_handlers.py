"""
API Error Handlers

FastAPI exception handlers for consistent error response formatting.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from bugbridge.api.exceptions import APIException
from bugbridge.api.responses import ErrorDetail, ErrorResponse
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle custom API exceptions.

    Args:
        request: FastAPI request object.
        exc: API exception instance.

    Returns:
        JSON response with error details.
    """
    logger.warning(
        f"API exception: {exc.error_code} - {exc.message}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
        },
    )

    error_response = ErrorResponse(
        error=True,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Converts Pydantic validation errors into structured error responses
    with field-specific error details.

    Args:
        request: FastAPI request object.
        exc: Pydantic validation error.

    Returns:
        JSON response with validation error details.
    """
    validation_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        validation_errors.append(
            ErrorDetail(
                field=field_path,
                message=error["msg"],
                code=error.get("type"),
            )
        )

    logger.warning(
        f"Validation error: {len(validation_errors)} field(s) failed",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "validation_errors": [e.model_dump() for e in validation_errors],
        },
    )

    error_response = ErrorResponse(
        error=True,
        error_code="VALIDATION_ERROR",
        message="Request validation failed",
        details={},
        validation_errors=validation_errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    """
    Handle FastAPI HTTPException.

    Converts FastAPI HTTPException into structured error responses.

    Args:
        request: FastAPI request object.
        exc: HTTPException instance.

    Returns:
        JSON response with error details.
    """
    # Extract error details from HTTPException
    if hasattr(exc, "detail"):
        detail = exc.detail
        if isinstance(detail, dict):
            message = detail.get("detail", "An error occurred")
            error_code = detail.get("error", "HTTP_ERROR")
            error_details = {k: v for k, v in detail.items() if k not in ["detail", "error"]}
        else:
            message = str(detail)
            error_code = "HTTP_ERROR"
            error_details = {}
    else:
        message = "An error occurred"
        error_code = "HTTP_ERROR"
        error_details = {}

    status_code = exc.status_code if hasattr(exc, "status_code") else 500

    logger.warning(
        f"HTTP exception: {status_code} - {message}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "status_code": status_code,
        },
    )

    error_response = ErrorResponse(
        error=True,
        error_code=error_code,
        message=message,
        details=error_details,
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unhandled exceptions.

    Catches all unhandled exceptions and returns a generic error response.
    Logs the full exception for debugging.

    Args:
        request: FastAPI request object.
        exc: Exception instance.

    Returns:
        JSON response with generic error message.
    """
    logger.error(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__,
        },
    )

    error_response = ErrorResponse(
        error=True,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details={},
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True),
    )


__all__ = [
    "api_exception_handler",
    "validation_exception_handler",
    "http_exception_handler",
    "general_exception_handler",
]

