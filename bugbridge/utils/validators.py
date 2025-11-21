"""Input validation utilities"""

from typing import Any, Dict, List, Optional
import re


def validate_email(email: str) -> bool:
    """Validate email address format
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_uuid(uuid_str: str) -> bool:
    """Validate UUID format
    
    Args:
        uuid_str: UUID string to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_str.lower()))


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize string input
    
    Args:
        text: Text to sanitize
        max_length: Optional maximum length
    
    Returns:
        Sanitized string
    """
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Strip whitespace
    text = text.strip()
    
    # Truncate if needed
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_priority_score(score: int) -> bool:
    """Validate priority score is in valid range
    
    Args:
        score: Priority score (1-100)
    
    Returns:
        True if valid, False otherwise
    """
    return 1 <= score <= 100


def validate_sentiment_score(score: float) -> bool:
    """Validate sentiment score is in valid range
    
    Args:
        score: Sentiment score (0.0-1.0)
    
    Returns:
        True if valid, False otherwise
    """
    return 0.0 <= score <= 1.0
