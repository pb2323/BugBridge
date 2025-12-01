"""
API Exception Classes

Custom exception classes for API error handling with structured error responses.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class APIException(Exception):
    """
    Base exception class for API errors.
    
    All API exceptions should inherit from this class to ensure consistent
    error handling and response formatting.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize API exception.

        Args:
            message: Human-readable error message.
            status_code: HTTP status code.
            error_code: Machine-readable error code.
            details: Additional error details.
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIException):
    """Exception for request validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationError(APIException):
    """Exception for authentication errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationError(APIException):
    """Exception for authorization errors."""

    def __init__(
        self,
        message: str = "Access denied",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class NotFoundError(APIException):
    """Exception for resource not found errors."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class ConflictError(APIException):
    """Exception for resource conflict errors."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class RateLimitError(APIException):
    """Exception for rate limiting errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class InternalServerError(APIException):
    """Exception for internal server errors."""

    def __init__(
        self,
        message: str = "Internal server error",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code="INTERNAL_SERVER_ERROR",
            details=details,
        )


class ServiceUnavailableError(APIException):
    """Exception for service unavailable errors."""

    def __init__(
        self,
        message: str = "Service unavailable",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=503,
            error_code="SERVICE_UNAVAILABLE",
            details=details,
        )


__all__ = [
    "APIException",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "InternalServerError",
    "ServiceUnavailableError",
]

