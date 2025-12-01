"""
FastAPI Application Setup

Main FastAPI application for the BugBridge dashboard API.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError as PydanticValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from bugbridge.api.error_handlers import (
    api_exception_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from bugbridge.api.exceptions import APIException
from bugbridge.api.routes import (
    auth_router,
    config_router,
    feedback_router,
    jira_tickets_router,
    metrics_router,
    reports_router,
)
from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for FastAPI application.

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting BugBridge API server...")
    try:
        settings = get_settings()
        logger.info(
            "API server configuration",
            extra={
                "debug": settings.app.debug if hasattr(settings, "app") else False,
                "environment": settings.app.environment if hasattr(settings, "app") else "production",
            },
        )
    except Exception as e:
        logger.warning(f"Could not load settings during startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down BugBridge API server...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    # Try to get settings, but don't fail if configuration is incomplete
    try:
        settings = get_settings()
        cors_origins = getattr(settings.app, "cors_origins", ["*"]) if hasattr(settings, "app") else ["*"]
    except Exception:
        # Fallback for development/testing when .env is not fully configured
        cors_origins = ["*"]
        logger.warning("Could not load settings, using default CORS configuration")

    # Determine app title and description
    app_title = "BugBridge API"
    app_description = """
    BugBridge Platform API

    REST API for the BugBridge feedback management platform dashboard.

    ## Features

    * **Feedback Management**: View and manage feedback posts from Canny.io
    * **Metrics & Analytics**: Get aggregated metrics and statistics
    * **Reports**: Access historical reports and generate new ones
    * **Jira Integration**: View Jira tickets linked to feedback
    * **Configuration**: Manage platform settings

    ## Authentication

    All endpoints require JWT authentication except for `/api/auth/login`.
    Include the JWT token in the `Authorization` header: `Bearer <token>`
    """

    app = FastAPI(
        title=app_title,
        description=app_description,
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Authentication middleware
    from bugbridge.api.middleware.auth import authentication_middleware
    
    class AuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            return await authentication_middleware(request, call_next)
    
    app.add_middleware(AuthMiddleware)

    # Register routers
    app.include_router(auth_router)
    app.include_router(feedback_router)
    app.include_router(metrics_router)
    app.include_router(reports_router)
    app.include_router(config_router)
    app.include_router(jira_tickets_router)

    # Register exception handlers (order matters - most specific first)
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    return app


def get_app() -> FastAPI:
    """
    Get or create FastAPI application instance (singleton pattern).

    Returns:
        FastAPI application instance.
    """
    if not hasattr(get_app, "_app"):
        get_app._app = create_app()
    return get_app._app


__all__ = [
    "create_app",
    "get_app",
    "lifespan",
]

