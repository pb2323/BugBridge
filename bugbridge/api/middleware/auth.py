"""
Authentication Middleware

JWT-based authentication middleware for FastAPI endpoints.
"""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


async def authentication_middleware(request: Request, call_next):
    """
    Middleware to validate authentication for protected endpoints.
    
    This middleware checks if the request path requires authentication
    (excludes /api/auth/login and /api/docs, /api/openapi.json, etc.)
    and ensures a valid Bearer token is present.
    
    Note: Actual token validation is done by the get_current_user dependency
    in route handlers. This middleware just ensures a token is present for
    protected endpoints.
    
    Args:
        request: FastAPI request object.
        call_next: Next middleware/endpoint handler.
        
    Returns:
        Response from next handler or 401 if authentication required but missing.
    """
    # Public endpoints that don't require authentication
    public_paths = [
        "/api/auth/login",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/",
        "/health",
        "/api/health",
    ]
    
    # Check if this is a public endpoint
    path = request.url.path
    is_public = any(path.startswith(public_path) for public_path in public_paths)
    
    if is_public:
        return await call_next(request)
    
    # For protected endpoints, check for authentication header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        logger.warning(f"Unauthenticated request to protected endpoint: {path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Authentication required",
                "error": "missing_authorization_header",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate Bearer token format
    if not auth_header.startswith("Bearer "):
        logger.warning(f"Invalid authorization header format: {path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": "Invalid authorization header format. Expected 'Bearer <token>'",
                "error": "invalid_authorization_format",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token validation will be done by the get_current_user dependency
    # This middleware just ensures a token is present
    return await call_next(request)


__all__ = [
    "authentication_middleware",
]

