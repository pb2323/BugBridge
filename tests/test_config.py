"""
Unit Tests for Configuration Module

Tests for configuration loading, validation, and environment variable handling.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from bugbridge.config import (
    AgentSettings,
    CannySettings,
    DatabaseSettings,
    JiraSettings,
    ReportingSettings,
    Settings,
    XAISettings,
    get_settings,
)
from bugbridge.utils.validators import (
    ValidationError as ValidatorError,
    validate_board_id,
    validate_confidence_score,
    validate_email,
    validate_jira_key,
    validate_list_not_empty,
    validate_non_empty_string,
    validate_post_id,
    validate_priority_score,
    validate_project_key,
    validate_url,
)


class TestCannySettings:
    """Tests for CannySettings configuration."""

    def test_canny_settings_creation(self):
        """Test creating valid CannySettings."""
        settings = CannySettings(
            api_key="test_api_key",
            subdomain="test-subdomain",
            board_id="board123",
            sync_interval_minutes=5,
        )

        assert settings.api_key.get_secret_value() == "test_api_key"
        assert settings.subdomain == "test-subdomain"
        assert settings.board_id == "board123"
        assert settings.sync_interval_minutes == 5
        assert settings.base_url == "https://test-subdomain.canny.io"

    def test_canny_settings_defaults(self):
        """Test CannySettings with default values."""
        settings = CannySettings(
            api_key="test_key",
            subdomain="test",
            board_id="board1",
        )

        assert settings.sync_interval_minutes == 5  # Default

    def test_canny_settings_sync_interval_validation(self):
        """Test sync interval validation."""
        # Valid range
        CannySettings(
            api_key="key",
            subdomain="test",
            board_id="board1",
            sync_interval_minutes=1,
        )

        CannySettings(
            api_key="key",
            subdomain="test",
            board_id="board1",
            sync_interval_minutes=1440,  # Max
        )

        # Invalid - too low
        with pytest.raises(ValidationError):
            CannySettings(
                api_key="key",
                subdomain="test",
                board_id="board1",
                sync_interval_minutes=0,
            )

        # Invalid - too high
        with pytest.raises(ValidationError):
            CannySettings(
                api_key="key",
                subdomain="test",
                board_id="board1",
                sync_interval_minutes=1441,
            )


class TestJiraSettings:
    """Tests for JiraSettings configuration."""

    def test_jira_settings_creation(self):
        """Test creating valid JiraSettings."""
        settings = JiraSettings(
            server_url="https://jira.example.com",
            project_key="PROJ",
            resolution_done_statuses=["Done", "Resolved", "Closed"],
        )

        # HttpUrl may add trailing slash, so check contains
        assert "https://jira.example.com" in str(settings.server_url)
        assert settings.project_key == "PROJ"
        assert "Done" in settings.resolution_done_statuses

    def test_jira_settings_default_statuses(self):
        """Test JiraSettings with default resolution statuses."""
        settings = JiraSettings(
            server_url="https://jira.example.com",
            project_key="PROJ",
        )

        assert "Done" in settings.resolution_done_statuses
        assert "Resolved" in settings.resolution_done_statuses
        assert "Closed" in settings.resolution_done_statuses

    def test_jira_settings_status_validation(self):
        """Test resolution status validation."""
        # Valid - strips whitespace
        settings = JiraSettings(
            server_url="https://jira.example.com",
            project_key="PROJ",
            resolution_done_statuses=["  Done  ", " Resolved "],
        )
        assert "Done" in settings.resolution_done_statuses
        assert "Resolved" in settings.resolution_done_statuses

        # Invalid - empty status
        with pytest.raises(ValidationError):
            JiraSettings(
                server_url="https://jira.example.com",
                project_key="PROJ",
                resolution_done_statuses=["Done", ""],
            )


class TestXAISettings:
    """Tests for XAISettings configuration."""

    def test_xai_settings_creation(self):
        """Test creating valid XAISettings."""
        settings = XAISettings(
            api_key="test_xai_key",
            model="grok-2",
            temperature=0.0,
            max_output_tokens=2048,
        )

        assert settings.api_key.get_secret_value() == "test_xai_key"
        assert settings.model == "grok-2"
        assert settings.temperature == 0.0
        assert settings.max_output_tokens == 2048

    def test_xai_settings_defaults(self):
        """Test XAISettings with default values."""
        settings = XAISettings(api_key="test_key")

        assert settings.model == "grok-2"  # Default
        assert settings.temperature == 0.0  # Default
        assert settings.max_output_tokens == 2048  # Default

    def test_xai_settings_temperature_validation(self):
        """Test temperature range validation."""
        # Valid range
        XAISettings(api_key="key", temperature=0.0)
        XAISettings(api_key="key", temperature=1.0)

        # Invalid - too low
        with pytest.raises(ValidationError):
            XAISettings(api_key="key", temperature=-0.1)

        # Invalid - too high
        with pytest.raises(ValidationError):
            XAISettings(api_key="key", temperature=1.1)

    def test_xai_settings_model_validation(self):
        """Test model selection validation."""
        # Valid models
        XAISettings(api_key="key", model="grok-beta")
        XAISettings(api_key="key", model="grok-2")

        # Invalid model
        with pytest.raises(ValidationError):
            XAISettings(api_key="key", model="invalid-model")


class TestDatabaseSettings:
    """Tests for DatabaseSettings configuration."""

    def test_database_settings_creation(self):
        """Test creating valid DatabaseSettings."""
        settings = DatabaseSettings(
            url="postgresql+asyncpg://user:pass@localhost/db",
            echo=False,
            pool_size=10,
            pool_timeout=30,
        )

        assert "asyncpg" in settings.url
        assert settings.echo is False
        assert settings.pool_size == 10

    def test_database_settings_defaults(self):
        """Test DatabaseSettings with default values."""
        settings = DatabaseSettings(url="postgresql+asyncpg://localhost/db")

        assert settings.echo is False  # Default
        assert settings.pool_size == 10  # Default
        assert settings.pool_timeout == 30  # Default

    def test_database_settings_url_validation(self):
        """Test database URL validation for asyncpg driver."""
        # Valid - contains asyncpg
        DatabaseSettings(url="postgresql+asyncpg://localhost/db")

        # Invalid - missing asyncpg
        with pytest.raises(ValidationError):
            DatabaseSettings(url="postgresql://localhost/db")


class TestReportingSettings:
    """Tests for ReportingSettings configuration."""

    def test_reporting_settings_creation(self):
        """Test creating valid ReportingSettings."""
        settings = ReportingSettings(
            enabled=True,
            schedule_cron="0 9 * * *",
            recipients=["admin@example.com", "pm@example.com"],
        )

        assert settings.enabled is True
        assert settings.schedule_cron == "0 9 * * *"
        assert len(settings.recipients) == 2

    def test_reporting_settings_defaults(self):
        """Test ReportingSettings with default values."""
        settings = ReportingSettings()

        assert settings.enabled is True  # Default
        assert settings.schedule_cron == "0 9 * * *"  # Default
        assert settings.recipients == []  # Default


class TestAgentSettings:
    """Tests for AgentSettings configuration."""

    def test_agent_settings_creation(self):
        """Test creating valid AgentSettings."""
        settings = AgentSettings(
            max_retries=5,
            retry_backoff_seconds=3.0,
            timeout_seconds=120,
            deterministic=True,
        )

        assert settings.max_retries == 5
        assert settings.retry_backoff_seconds == 3.0
        assert settings.timeout_seconds == 120
        assert settings.deterministic is True

    def test_agent_settings_defaults(self):
        """Test AgentSettings with default values."""
        settings = AgentSettings()

        assert settings.max_retries == 3  # Default
        assert settings.retry_backoff_seconds == 2.0  # Default
        assert settings.timeout_seconds == 60  # Default
        assert settings.deterministic is True  # Default


class TestSettings:
    """Tests for top-level Settings class."""

    @patch.dict(
        os.environ,
        {
            "CANNY__API_KEY": "test_canny_key",
            "CANNY__SUBDOMAIN": "test-subdomain",
            "CANNY__BOARD_ID": "board123",
            "JIRA__SERVER_URL": "https://jira.example.com",
            "JIRA__PROJECT_KEY": "PROJ",
            "XAI__API_KEY": "test_xai_key",
            "DATABASE__URL": "postgresql+asyncpg://localhost/db",
        },
    )
    def test_settings_from_env(self):
        """Test loading Settings from environment variables."""
        # Clear cache to force reload
        get_settings.cache_clear()

        settings = get_settings()

        assert settings.canny.api_key.get_secret_value() == "test_canny_key"
        assert settings.canny.subdomain == "test-subdomain"
        assert settings.jira.project_key == "PROJ"
        assert settings.xai.api_key.get_secret_value() == "test_xai_key"
        assert "asyncpg" in settings.database.url

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "CANNY__API_KEY": "test_canny_key",
            "CANNY__SUBDOMAIN": "test-subdomain",
            "CANNY__BOARD_ID": "board123",
            "JIRA__SERVER_URL": "https://jira.example.com",
            "JIRA__PROJECT_KEY": "PROJ",
            "XAI__API_KEY": "test_xai_key",
            "DATABASE__URL": "postgresql+asyncpg://localhost/db",
        },
    )
    def test_settings_environment_fields(self):
        """Test Settings environment and debug fields."""
        get_settings.cache_clear()

        settings = get_settings()

        assert settings.environment == "production"
        assert settings.debug is True
        assert settings.log_level == "DEBUG"


class TestValidators:
    """Tests for validation utilities."""

    def test_validate_post_id(self):
        """Test post ID validation."""
        assert validate_post_id("post123") == "post123"
        assert validate_post_id("post-123-abc") == "post-123-abc"
        assert validate_post_id("  post123  ") == "post123"  # Strips whitespace

        with pytest.raises(ValidatorError):
            validate_post_id("")  # Empty

        with pytest.raises(ValidatorError):
            validate_post_id("post@123")  # Invalid character

    def test_validate_board_id(self):
        """Test board ID validation."""
        assert validate_board_id("board123") == "board123"
        assert validate_board_id("  board123  ") == "board123"

        with pytest.raises(ValidatorError):
            validate_board_id("")  # Empty

    def test_validate_jira_key(self):
        """Test Jira key validation."""
        assert validate_jira_key("PROJ-123") == "PROJ-123"
        assert validate_jira_key("TEST-456") == "TEST-456"
        assert validate_jira_key("  PROJ-123  ") == "PROJ-123"  # Strips and uppercases

        with pytest.raises(ValidatorError):
            validate_jira_key("proj-123")  # Invalid format

        with pytest.raises(ValidatorError):
            validate_jira_key("PROJ")  # Missing number

        with pytest.raises(ValidatorError):
            validate_jira_key("PROJ-ABC")  # Non-numeric suffix

    def test_validate_project_key(self):
        """Test project key validation."""
        assert validate_project_key("PROJ") == "PROJ"
        assert validate_project_key("TEST") == "TEST"
        assert validate_project_key("  proj  ") == "PROJ"  # Strips and uppercases

        with pytest.raises(ValidatorError):
            validate_project_key("P")  # Too short

        with pytest.raises(ValidatorError):
            validate_project_key("")  # Empty

    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://example.com") == "https://example.com"
        assert validate_url("http://localhost:8000") == "http://localhost:8000"

        with pytest.raises(ValidatorError):
            validate_url("invalid-url")  # Missing scheme

        with pytest.raises(ValidatorError):
            validate_url("ftp://example.com")  # Disallowed scheme

    def test_validate_email(self):
        """Test email validation."""
        assert validate_email("test@example.com") == "test@example.com"
        assert validate_email("user.name@example.co.uk") == "user.name@example.co.uk"

        with pytest.raises(ValidatorError):
            validate_email("invalid-email")  # Invalid format

        with pytest.raises(ValidatorError):
            validate_email("@example.com")  # Missing local part

    def test_validate_priority_score(self):
        """Test priority score validation."""
        assert validate_priority_score(1) == 1
        assert validate_priority_score(50) == 50
        assert validate_priority_score(100) == 100

        with pytest.raises(ValidatorError):
            validate_priority_score(0)  # Too low

        with pytest.raises(ValidatorError):
            validate_priority_score(101)  # Too high

        with pytest.raises(ValidatorError):
            validate_priority_score(50.5)  # Not integer

    def test_validate_confidence_score(self):
        """Test confidence score validation."""
        assert validate_confidence_score(0.0) == 0.0
        assert validate_confidence_score(0.5) == 0.5
        assert validate_confidence_score(1.0) == 1.0

        with pytest.raises(ValidatorError):
            validate_confidence_score(-0.1)  # Too low

        with pytest.raises(ValidatorError):
            validate_confidence_score(1.1)  # Too high

    def test_validate_non_empty_string(self):
        """Test non-empty string validation."""
        assert validate_non_empty_string("test") == "test"
        assert validate_non_empty_string("  test  ") == "test"  # Strips

        with pytest.raises(ValidatorError):
            validate_non_empty_string("")  # Empty

        with pytest.raises(ValidatorError):
            validate_non_empty_string(123)  # Not string

    def test_validate_list_not_empty(self):
        """Test list validation."""
        assert validate_list_not_empty([1, 2, 3]) == [1, 2, 3]
        assert validate_list_not_empty(["a"]) == ["a"]

        with pytest.raises(ValidatorError):
            validate_list_not_empty([])  # Empty

        with pytest.raises(ValidatorError):
            validate_list_not_empty([1], min_length=2)  # Too short

        with pytest.raises(ValidatorError):
            validate_list_not_empty("not a list")  # Not a list

