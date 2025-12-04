"""
API Routes for Authentication

FastAPI endpoints for user authentication and session management.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
UTC = timezone.utc
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from bugbridge.api.exceptions import AuthenticationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bugbridge.config import get_settings
from bugbridge.database.connection import get_session
from bugbridge.database.models import User as DBUser
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_secret_key() -> str:
    """Get JWT secret key from settings or environment."""
    try:
        settings = get_settings()
        # TODO: Add JWT settings to config
        # For now, use environment variable or default
        import os
        return os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    except Exception:
        import os
        return os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")


class LoginRequest(BaseModel):
    """Request model for user login."""

    username: str = Field(..., min_length=1, max_length=255, description="Username or email")
    password: str = Field(..., min_length=1, max_length=255, description="User password")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        if not v.strip():
            raise ValueError("Username cannot be empty or whitespace only")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password is not empty."""
        if not v:
            raise ValueError("Password cannot be empty")
        return v


class LoginResponse(BaseModel):
    """Response model for successful login."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: "UserResponse" = Field(..., description="User information")


class UserResponse(BaseModel):
    """Response model for user information."""

    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="User email")
    role: str = Field(..., description="User role (admin or viewer)")
    created_at: datetime = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True


class LogoutResponse(BaseModel):
    """Response model for logout."""

    message: str = Field(..., description="Logout confirmation message")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password.
        hashed_password: Hashed password from database.

    Returns:
        True if password matches, False otherwise.
    """
    # Use bcrypt directly to avoid passlib compatibility issues
    import bcrypt
    # Ensure both are bytes
    if isinstance(plain_password, str):
        plain_password_bytes = plain_password.encode('utf-8')
    else:
        plain_password_bytes = plain_password
    if isinstance(hashed_password, str):
        hashed_password_bytes = hashed_password.encode('utf-8')
    else:
        hashed_password_bytes = hashed_password
    # Truncate password to 72 bytes max
    if len(plain_password_bytes) > 72:
        plain_password_bytes = plain_password_bytes[:72]
    try:
        return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Hashed password.
    """
    # Use bcrypt directly to avoid passlib compatibility issues
    import bcrypt
    # Ensure password is bytes
    if isinstance(password, str):
        password_bytes = password.encode('utf-8')
    else:
        password_bytes = password
    # Truncate to 72 bytes max (bcrypt limit)
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Data to encode in the token (typically user ID and role).
        expires_delta: Optional expiration time delta.

    Returns:
        Encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    secret_key = get_secret_key()
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> DBUser:
    """
    Dependency to get the current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials.
        session: Database session.

    Returns:
        Current user database model.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        secret_key = get_secret_key()
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Get user from database
    query = select(DBUser).where(DBUser.id == user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    """
    Authenticate user and return JWT access token.

    Accepts username/email and password, verifies credentials, and returns
    a JWT token for subsequent API requests.

    **Example Request:**
    ```json
    {
        "username": "admin",
        "password": "securepassword123"
    }
    ```

    **Example Response:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
        "user": {
            "id": "user-123",
            "username": "admin",
            "email": "admin@example.com",
            "role": "admin",
            "created_at": "2025-01-01T00:00:00Z"
        }
    }
    ```
    """
    # Find user by username or email
    query = select(DBUser).where(
        (DBUser.username == request.username) | (DBUser.email == request.username)
    )
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Login attempt with invalid username: {request.username}")
        raise AuthenticationError(
            message="Incorrect username or password",
            details={"field": "username"},
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        logger.warning(f"Login attempt with invalid password for user: {request.username}")
        raise AuthenticationError(
            message="Incorrect username or password",
            details={"field": "password"},
        )

    # Check if user is active
    if not user.is_active:
        raise AuthenticationError(
            message="User account is inactive",
            details={"user_id": str(user.id)},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role},
        expires_delta=access_token_expires,
    )

    logger.info(f"User logged in successfully: {user.username}")

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at,
        ),
    )


@router.post("/logout", response_model=LogoutResponse, status_code=status.HTTP_200_OK)
async def logout(
    current_user: DBUser = Depends(get_current_user),
) -> LogoutResponse:
    """
    Logout the current user.

    **Note**: In a stateless JWT implementation, logout is typically handled
    client-side by discarding the token. This endpoint provides a place for
    future token blacklisting or session invalidation if needed.

    Requires authentication via Bearer token.
    """
    logger.info(f"User logged out: {current_user.username}")

    # TODO: Implement token blacklisting if needed
    # For now, logout is handled client-side by discarding the token

    return LogoutResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: DBUser = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user information.

    Returns the user information for the authenticated user based on the
    JWT token in the Authorization header.

    Requires authentication via Bearer token.

    **Example Response:**
    ```json
    {
        "id": "user-123",
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "created_at": "2025-01-01T00:00:00Z"
    }
    ```
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
    )


__all__ = [
    "router",
    "LoginRequest",
    "LoginResponse",
    "UserResponse",
    "LogoutResponse",
    "get_current_user",
    "create_access_token",
    "verify_password",
    "get_password_hash",
]

