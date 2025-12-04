"""
API Routes for Configuration Management

FastAPI endpoints for getting and updating configuration settings.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from bugbridge.api.dependencies import get_authenticated_user, require_admin
from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger
from pydantic_settings.exceptions import SettingsError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigResponse(BaseModel):
    """Response model for configuration settings."""

    canny: Dict[str, Any] = Field(..., description="Canny.io configuration")
    jira: Dict[str, Any] = Field(..., description="Jira configuration")
    xai: Dict[str, Any] = Field(..., description="XAI/Grok configuration")
    database: Dict[str, Any] = Field(..., description="Database configuration")
    reporting: Dict[str, Any] = Field(..., description="Reporting configuration")
    agent: Dict[str, Any] = Field(..., description="Agent configuration")


class ConfigUpdateRequest(BaseModel):
    """Request model for updating configuration."""

    canny: Optional[Dict[str, Any]] = Field(None, description="Canny.io configuration updates")
    jira: Optional[Dict[str, Any]] = Field(None, description="Jira configuration updates")
    reporting: Optional[Dict[str, Any]] = Field(None, description="Reporting configuration updates")
    agent: Optional[Dict[str, Any]] = Field(None, description="Agent configuration updates")

    @model_validator(mode="after")
    def validate_at_least_one_update(self) -> "ConfigUpdateRequest":
        """Ensure at least one configuration section is provided for update."""
        if not any([self.canny, self.jira, self.reporting, self.agent]):
            raise ValueError("At least one configuration section must be provided for update")
        return self


@router.get("", response_model=ConfigResponse, status_code=status.HTTP_200_OK)
async def get_config(
    current_user = Depends(get_authenticated_user),
) -> ConfigResponse:
    """
    Get current configuration settings.

    Returns sanitized configuration (sensitive values like API keys are masked).
    """
    # Build response with sanitized values
    def sanitize_secret(value: Any) -> Any:
        """Mask sensitive values."""
        if isinstance(value, str) and ("key" in str(value).lower() or "password" in str(value).lower()):
            return "***"
        return value

    def to_dict(obj: Any) -> Dict[str, Any]:
        """Convert Pydantic model to dict with sanitization."""
        if obj is None:
            return {}
        if hasattr(obj, "model_dump"):
            try:
                data = obj.model_dump()
                return {k: sanitize_secret(v) for k, v in data.items()}
            except Exception:
                return {}
        return {}

    try:
        settings = get_settings()
        
        return ConfigResponse(
            canny=to_dict(getattr(settings, "canny", None)),
            jira=to_dict(getattr(settings, "jira", None)),
            xai=to_dict(getattr(settings, "xai", None)),
            database=to_dict(getattr(settings, "database", None)),
            reporting=to_dict(getattr(settings, "reporting", None)),
            agent=to_dict(getattr(settings, "agent", None)),
        )
    except SettingsError as e:
        logger.warning(
            f"SettingsError loading configuration: {str(e)}. "
            "This usually indicates a malformed environment variable. "
            "Returning fallback configuration with error messages.",
            exc_info=False
        )
        # Return fallback configuration when settings fail to load
        # Extract the field name from the error message if possible
        error_message = str(e)
        if "jira" in error_message.lower():
            jira_error = {
                "error": "Failed to load Jira configuration. Check your .env file - ensure JIRA__SERVER_URL and JIRA__PROJECT_KEY are set correctly. Complex nested values (like dictionaries) must be valid JSON or omitted.",
                "hint": "For Jira settings, use format: JIRA__SERVER_URL=http://... and JIRA__PROJECT_KEY=PROJ"
            }
        else:
            jira_error = {"error": "Configuration loading failed. Please check your .env file."}
        
        return ConfigResponse(
            canny={},
            jira=jira_error,
            xai={},
            database={},
            reporting={},
            agent={},
        )
    except Exception as e:
        logger.error(f"Failed to get configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}",
        ) from e


@router.put("", response_model=ConfigResponse, status_code=status.HTTP_200_OK)
async def update_config(
    request: ConfigUpdateRequest,
    current_user = Depends(require_admin),
) -> ConfigResponse:
    """
    Update configuration settings.

    **Note**: This endpoint is a placeholder. Actual configuration updates should
    be persisted to environment variables or a configuration file. This implementation
    only returns the current configuration as updating settings at runtime requires
    careful handling of environment variables and application restart.

    For production use, consider:
    - Storing configuration in a database
    - Using a configuration management service
    - Implementing proper validation and persistence logic
    """
    try:
        # Log the update request (in production, this would persist to config storage)
        logger.info(
            "Configuration update requested",
            extra={
                "has_canny_updates": request.canny is not None,
                "has_jira_updates": request.jira is not None,
                "has_reporting_updates": request.reporting is not None,
                "has_agent_updates": request.agent is not None,
            },
        )

        # TODO: Implement actual configuration persistence
        # For now, return current configuration
        # In production, this should:
        # 1. Validate the update request
        # 2. Persist changes to configuration storage
        # 3. Reload settings if needed
        # 4. Return updated configuration

        return await get_config()

    except Exception as e:
        logger.error(f"Failed to update configuration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}",
        ) from e


__all__ = [
    "router",
    "ConfigResponse",
    "ConfigUpdateRequest",
]

