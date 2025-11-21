"""
Application configuration powered by Pydantic settings.

This module centralizes how BugBridge loads and validates environment variables
across the platform. It relies on `python-dotenv` to populate values from a
local `.env` file during development while still favoring real environment
variables in higher environments.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, SecretStr, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file early so BaseSettings can pick up default values during
# instantiation in local development environments.
load_dotenv()


def _split_comma_separated(value: Optional[str]) -> List[str]:
    """Utility to parse comma-separated environment variables into lists."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class CannySettings(BaseModel):
    """Configuration for the Canny.io integration."""

    api_key: SecretStr = Field(..., description="Canny.io API token")
    subdomain: str = Field(..., description="Canny.io company subdomain")
    board_id: str = Field(..., description="Default board ID to sync feedback from")
    sync_interval_minutes: int = Field(
        5,
        description="Polling interval for syncing feedback posts",
        ge=1,
        le=1440,
    )

    @property
    def base_url(self) -> str:
        """Convenience helper for constructing API URLs."""
        return f"https://{self.subdomain}.canny.io"


class JiraSettings(BaseModel):
    """Configuration for the Jira MCP integration."""

    server_url: HttpUrl = Field(..., description="Base URL of the Jira MCP server")
    project_key: str = Field(..., description="Default Jira project key")
    resolution_done_statuses: List[str] = Field(
        default_factory=lambda: ["Done", "Resolved", "Closed"],
        description="Statuses that indicate an issue is resolved",
    )

    @validator("resolution_done_statuses", each_item=True)
    def _strip_status(cls, status: str) -> str:  # noqa: D401
        """Ensure statuses are normalized without surrounding whitespace."""
        cleaned = status.strip()
        if not cleaned:
            raise ValueError("Resolution status entries cannot be blank")
        return cleaned


class XAISettings(BaseModel):
    """Settings for interacting with the XAI (Grok) API."""

    api_key: SecretStr = Field(..., description="XAI API key")
    model: Literal["grok-beta", "grok-2"] = Field(
        "grok-2",
        description="Primary Grok model to use for deterministic agents",
    )
    temperature: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Temperature for deterministic outputs",
    )
    max_output_tokens: int = Field(
        2048,
        ge=256,
        le=4096,
        description="Upper bound for response tokens to control costs",
    )


class DatabaseSettings(BaseModel):
    """Settings for BugBridge's PostgreSQL database."""

    url: str = Field(..., description="SQLAlchemy connection string (asyncpg driver)")
    echo: bool = Field(False, description="Enable SQL echo logging for debugging")
    pool_size: int = Field(10, ge=1, description="Default async connection pool size")
    pool_timeout: int = Field(30, ge=1, description="Pool acquire timeout in seconds")

    @validator("url")
    def _validate_url(cls, value: str) -> str:
        """Ensure the database URL uses asyncpg so SQLAlchemy can run async."""
        if "asyncpg" not in value:
            raise ValueError("DATABASE_URL must use the asyncpg driver")
        return value


class ReportingSettings(BaseModel):
    """Settings for scheduled reporting and digest emails."""

    enabled: bool = Field(True, description="Toggle automated reporting jobs")
    schedule_cron: str = Field(
        "0 9 * * *",
        description="Cron expression for scheduled report generation",
    )
    recipients: List[str] = Field(
        default_factory=list,
        description="List of email recipients for reports",
    )

    @validator("recipients", pre=True)
    def _parse_recipients(cls, value):  # noqa: D401, ANN001
        """Allow comma separated strings in environment variables."""
        if isinstance(value, list):
            return value
        return _split_comma_separated(value)


class AgentSettings(BaseModel):
    """Global controls for AI agent execution."""

    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry attempts")
    retry_backoff_seconds: float = Field(
        2.0, ge=0.0, description="Base backoff used between retries"
    )
    timeout_seconds: int = Field(
        60, ge=1, description="Default timeout for agent operations"
    )
    deterministic: bool = Field(
        True,
        description="Ensure all agents run with deterministic settings (temperature=0)",
    )


class Settings(BaseSettings):
    """Top-level application settings container."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["local", "dev", "staging", "production"] = Field(
        "local", description="Deployment environment identifier"
    )
    debug: bool = Field(False, description="Enable verbose debug logging")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO",
        description="Logging level applied across the stack",
    )

    canny: CannySettings
    jira: JiraSettings
    xai: XAISettings
    database: DatabaseSettings
    reporting: ReportingSettings = Field(
        default_factory=ReportingSettings,
        description="Reporting/digest configuration",
    )
    agents: AgentSettings = Field(
        default_factory=AgentSettings,
        description="Global agent execution parameters",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance for reuse across the app."""
    return Settings()


__all__ = [
    "AgentSettings",
    "CannySettings",
    "DatabaseSettings",
    "JiraSettings",
    "ReportingSettings",
    "Settings",
    "XAISettings",
    "get_settings",
]

