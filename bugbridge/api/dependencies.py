"""
FastAPI Dependencies

Shared dependencies for API endpoints, including authentication and authorization.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.api.routes.auth import get_current_user
from bugbridge.database.connection import get_session
from bugbridge.database.models import User as DBUser
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer()


async def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> DBUser:
    """
    Dependency to get the current authenticated user.
    
    This dependency requires a valid JWT token in the Authorization header.
    Use this for endpoints that require authentication.
    
    **Usage:**
    ```python
    @router.get("/protected")
    async def protected_endpoint(
        current_user: DBUser = Depends(get_authenticated_user),
    ):
        return {"user_id": current_user.id}
    ```
    
    Args:
        credentials: HTTP Bearer token credentials from Authorization header.
        session: Database session (injected by FastAPI).
        
    Returns:
        Current authenticated user database model.
        
    Raises:
        HTTPException: 401 if token is missing or invalid.
    """
    return await get_current_user(credentials, session)


async def get_optional_authenticated_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    session: AsyncSession = Depends(get_session),
) -> Optional[DBUser]:
    """
    Dependency to optionally get the current authenticated user.
    
    Returns None if no token is provided or token is invalid.
    Use this for endpoints that work with or without authentication.
    
    **Usage:**
    ```python
    @router.get("/optional")
    async def optional_endpoint(
        user: Optional[DBUser] = Depends(get_optional_authenticated_user),
    ):
        if user:
            return {"user_id": user.id, "authenticated": True}
        return {"authenticated": False}
    ```
    
    Args:
        credentials: Optional HTTP Bearer token credentials.
        session: Database session (injected by FastAPI).
        
    Returns:
        Current user if authenticated, None otherwise.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, session)
    except Exception as e:
        logger.debug(f"Optional authentication failed: {e}")
        return None


def require_role(*allowed_roles: str):
    """
    Dependency factory to require specific user roles.
    
    Creates a dependency that checks if the current user has one of the allowed roles.
    Raises 403 Forbidden if the user's role is not in the allowed list.
    
    **Usage:**
    ```python
    @router.get("/admin-only")
    async def admin_endpoint(
        current_user: DBUser = Depends(require_role("admin")),
    ):
        return {"message": "Admin access granted"}
    
    @router.get("/admin-or-manager")
    async def admin_or_manager_endpoint(
        current_user: DBUser = Depends(require_role("admin", "manager")),
    ):
        return {"message": "Access granted"}
    ```
    
    Args:
        *allowed_roles: One or more allowed role names (e.g., "admin", "viewer").
        
    Returns:
        Dependency function that checks user role.
        
    Raises:
        HTTPException: 403 if user role is not allowed.
    """
    async def role_checker(
        current_user: DBUser = Depends(get_authenticated_user),
    ) -> DBUser:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"User {current_user.username} (role: {current_user.role}) "
                f"attempted to access endpoint requiring roles: {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
            )
        return current_user
    
    return role_checker


def require_admin():
    """
    Convenience dependency for admin-only endpoints.
    
    Shorthand for `require_role("admin")`.
    
    **Usage:**
    ```python
    @router.delete("/resource/{id}")
    async def delete_resource(
        id: str,
        current_user: DBUser = Depends(require_admin),
    ):
        # Only admins can delete
        ...
    ```
    
    Returns:
        Dependency function that requires admin role.
    """
    return require_role("admin")


def require_viewer_or_admin():
    """
    Convenience dependency for endpoints accessible to both viewers and admins.
    
    Shorthand for `require_role("viewer", "admin")`.
    
    **Usage:**
    ```python
    @router.get("/data")
    async def get_data(
        current_user: DBUser = Depends(require_viewer_or_admin),
    ):
        # Both viewers and admins can access
        ...
    ```
    
    Returns:
        Dependency function that allows viewer or admin roles.
    """
    return require_role("viewer", "admin")


__all__ = [
    "get_authenticated_user",
    "get_optional_authenticated_user",
    "require_role",
    "require_admin",
    "require_viewer_or_admin",
    "security",
]
