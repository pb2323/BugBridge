"""
Input validation utilities for BugBridge.

This module provides validation functions for various inputs to ensure
data integrity and prevent errors before processing.
"""

from __future__ import annotations

import re
from typing import Any, Callable, List, Optional, Pattern
from urllib.parse import urlparse

from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationError(ValueError):
    """Raised when validation fails."""

    pass


def validate_post_id(post_id: str) -> str:
    """
    Validate Canny.io post ID format.

    Args:
        post_id: Post ID to validate.

    Returns:
        Validated post ID.

    Raises:
        ValidationError: If post ID is invalid.
    """
    if not post_id or not isinstance(post_id, str):
        raise ValidationError("Post ID must be a non-empty string")

    # Strip whitespace first
    post_id = post_id.strip()

    if not post_id:
        raise ValidationError("Post ID cannot be empty or whitespace only")

    # Canny.io post IDs are typically alphanumeric with hyphens
    if not re.match(r"^[a-zA-Z0-9_-]+$", post_id):
        raise ValidationError(
            f"Post ID '{post_id}' contains invalid characters. "
            "Must be alphanumeric with hyphens or underscores only."
        )

    return post_id


def validate_board_id(board_id: str) -> str:
    """
    Validate Canny.io board ID format.

    Args:
        board_id: Board ID to validate.

    Returns:
        Validated board ID.

    Raises:
        ValidationError: If board ID is invalid.
    """
    if not board_id or not isinstance(board_id, str):
        raise ValidationError("Board ID must be a non-empty string")

    # Strip whitespace first
    board_id = board_id.strip()

    if not board_id:
        raise ValidationError("Board ID cannot be empty or whitespace only")

    # Board IDs are typically alphanumeric
    if not re.match(r"^[a-zA-Z0-9_-]+$", board_id):
        raise ValidationError(
            f"Board ID '{board_id}' contains invalid characters. "
            "Must be alphanumeric with hyphens or underscores only."
        )

    return board_id


def validate_jira_key(jira_key: str) -> str:
    """
    Validate Jira issue key format (e.g., "PROJ-123").

    Args:
        jira_key: Jira key to validate.

    Returns:
        Validated Jira key.

    Raises:
        ValidationError: If Jira key is invalid.
    """
    if not jira_key or not isinstance(jira_key, str):
        raise ValidationError("Jira key must be a non-empty string")

    if not jira_key.strip():
        raise ValidationError("Jira key cannot be empty or whitespace only")

    # Jira keys format: PROJECT-KEY-123
    pattern = r"^[A-Z][A-Z0-9_]*-\d+$"
    if not re.match(pattern, jira_key.strip()):
        raise ValidationError(
            f"Jira key '{jira_key}' is invalid. "
            "Must match format: PROJECT-KEY-123"
        )

    return jira_key.strip().upper()


def validate_project_key(project_key: str) -> str:
    """
    Validate Jira project key format (e.g., "PROJ").

    Args:
        project_key: Project key to validate.

    Returns:
        Validated project key.

    Raises:
        ValidationError: If project key is invalid.
    """
    if not project_key or not isinstance(project_key, str):
        raise ValidationError("Project key must be a non-empty string")

    if not project_key.strip():
        raise ValidationError("Project key cannot be empty or whitespace only")

    project_key = project_key.strip().upper()

    # Jira project keys are typically 2-10 uppercase alphanumeric characters
    if not re.match(r"^[A-Z][A-Z0-9_]{1,9}$", project_key):
        raise ValidationError(
            f"Project key '{project_key}' is invalid. "
            "Must be 2-10 uppercase alphanumeric characters starting with a letter."
        )

    return project_key


def validate_url(url: str, schemes: Optional[List[str]] = None) -> str:
    """
    Validate URL format.

    Args:
        url: URL to validate.
        schemes: Allowed URL schemes (default: ["http", "https"]).

    Returns:
        Validated URL.

    Raises:
        ValidationError: If URL is invalid.
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL must be a non-empty string")

    if not url.strip():
        raise ValidationError("URL cannot be empty or whitespace only")

    url = url.strip()

    # Default allowed schemes
    if schemes is None:
        schemes = ["http", "https"]

    try:
        parsed = urlparse(url)
    except Exception as e:
        raise ValidationError(f"Invalid URL format: {str(e)}") from e

    if not parsed.scheme:
        raise ValidationError(f"URL '{url}' is missing a scheme")

    if parsed.scheme not in schemes:
        raise ValidationError(
            f"URL '{url}' uses disallowed scheme '{parsed.scheme}'. "
            f"Allowed schemes: {', '.join(schemes)}"
        )

    if not parsed.netloc:
        raise ValidationError(f"URL '{url}' is missing a network location (host)")

    return url


def validate_email(email: str) -> str:
    """
    Validate email address format.

    Args:
        email: Email address to validate.

    Returns:
        Validated email address.

    Raises:
        ValidationError: If email is invalid.
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email must be a non-empty string")

    if not email.strip():
        raise ValidationError("Email cannot be empty or whitespace only")

    email = email.strip().lower()

    # Basic email regex pattern
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        raise ValidationError(f"Email '{email}' has invalid format")

    return email


def validate_priority_score(score: int) -> int:
    """
    Validate priority score range (1-100).

    Args:
        score: Priority score to validate.

    Returns:
        Validated priority score.

    Raises:
        ValidationError: If score is out of range.
    """
    if not isinstance(score, int):
        raise ValidationError(f"Priority score must be an integer, got {type(score).__name__}")

    if score < 1 or score > 100:
        raise ValidationError(f"Priority score must be between 1 and 100, got {score}")

    return score


def validate_confidence_score(score: float) -> float:
    """
    Validate confidence score range (0.0-1.0).

    Args:
        score: Confidence score to validate.

    Returns:
        Validated confidence score.

    Raises:
        ValidationError: If score is out of range.
    """
    if not isinstance(score, (int, float)):
        raise ValidationError(
            f"Confidence score must be a number, got {type(score).__name__}"
        )

    score = float(score)

    if score < 0.0 or score > 1.0:
        raise ValidationError(f"Confidence score must be between 0.0 and 1.0, got {score}")

    return score


def validate_non_empty_string(value: str, field_name: str = "value") -> str:
    """
    Validate that a string is non-empty.

    Args:
        value: String to validate.
        field_name: Name of the field for error messages.

    Returns:
        Validated string (stripped).

    Raises:
        ValidationError: If string is empty.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")

    if not value.strip():
        raise ValidationError(f"{field_name} cannot be empty or whitespace only")

    return value.strip()


def validate_list_not_empty(
    value: List[Any],
    field_name: str = "list",
    min_length: int = 1,
) -> List[Any]:
    """
    Validate that a list is not empty (and optionally meets minimum length).

    Args:
        value: List to validate.
        field_name: Name of the field for error messages.
        min_length: Minimum required length (default: 1).

    Returns:
        Validated list.

    Raises:
        ValidationError: If list is empty or too short.
    """
    if not isinstance(value, list):
        raise ValidationError(f"{field_name} must be a list, got {type(value).__name__}")

    if len(value) < min_length:
        raise ValidationError(
            f"{field_name} must have at least {min_length} item(s), got {len(value)}"
        )

    return value


def validate_regex_pattern(
    value: str,
    pattern: Pattern[str],
    field_name: str = "value",
    error_message: Optional[str] = None,
) -> str:
    """
    Validate that a string matches a regex pattern.

    Args:
        value: String to validate.
        pattern: Compiled regex pattern to match against.
        field_name: Name of the field for error messages.
        error_message: Custom error message (optional).

    Returns:
        Validated string.

    Raises:
        ValidationError: If string doesn't match pattern.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string, got {type(value).__name__}")

    if not pattern.match(value):
        message = (
            error_message
            if error_message
            else f"{field_name} '{value}' does not match required pattern"
        )
        raise ValidationError(message)

    return value


__all__ = [
    "ValidationError",
    "validate_post_id",
    "validate_board_id",
    "validate_jira_key",
    "validate_project_key",
    "validate_url",
    "validate_email",
    "validate_priority_score",
    "validate_confidence_score",
    "validate_non_empty_string",
    "validate_list_not_empty",
    "validate_regex_pattern",
]

