"""
API Response Models

Standardized response models for API success and error responses.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detail for a single validation error."""

    field: str = Field(..., description="Field name with error")
    message: str = Field(..., description="Error message for this field")
    code: Optional[str] = Field(None, description="Error code for this field")


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    
    All API errors should follow this structure for consistency.
    """

    error: bool = Field(True, description="Indicates this is an error response")
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    validation_errors: Optional[List[ErrorDetail]] = Field(
        None, description="Field-specific validation errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": True,
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {},
                "validation_errors": [
                    {
                        "field": "username",
                        "message": "Username cannot be empty",
                        "code": "REQUIRED",
                    }
                ],
            }
        }


class SuccessResponse(BaseModel):
    """
    Standard success response model.
    
    For endpoints that return simple success/failure status.
    """

    success: bool = Field(True, description="Indicates successful operation")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {},
            }
        }


class PaginatedResponse(BaseModel):
    """
    Base model for paginated responses.
    
    Extend this for endpoints that return paginated lists.
    """

    items: List[Any] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
            }
        }


__all__ = [
    "ErrorResponse",
    "ErrorDetail",
    "SuccessResponse",
    "PaginatedResponse",
]

