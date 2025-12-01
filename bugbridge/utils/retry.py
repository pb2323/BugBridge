"""
Retry utilities with exponential backoff for resilient API calls.

This module provides decorators and utilities for implementing retry logic
with exponential backoff, essential for handling rate-limited APIs and
transient failures.
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from typing import Any, Callable, Optional, TypeVar, Union

from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class RetryError(Exception):
    """Raised when retry attempts are exhausted."""

    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        """Initialize retry error with message and last exception."""
        super().__init__(message)
        self.last_exception = last_exception


def exponential_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float = 300.0,
    jitter: bool = True,
) -> float:
    """
    Calculate exponential backoff delay for retry attempts.

    Args:
        attempt: Current attempt number (0-indexed).
        base_delay: Base delay in seconds (doubled each attempt).
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter to prevent thundering herd.

    Returns:
        Delay in seconds before next retry attempt.
    """
    delay = base_delay * (2**attempt)

    # Cap at maximum delay
    if delay > max_delay:
        delay = max_delay

    # Add jitter to prevent synchronized retries
    if jitter:
        jitter_amount = delay * 0.1  # 10% jitter
        delay += random.uniform(-jitter_amount, jitter_amount)

    return max(0, delay)


def retry_with_backoff(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: float = 300.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying function calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (defaults to config value).
        base_delay: Base delay in seconds (defaults to config value).
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter.
        exceptions: Tuple of exception types to catch and retry.
        on_retry: Optional callback function(attempt, exception) called before retry.

    Returns:
        Decorated function with retry logic.

    Example:
        @retry_with_backoff(max_retries=3, base_delay=2.0)
        def fetch_data():
            # Function that might fail
            pass
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Get default values from config if not provided
        settings = None
        try:
            settings = get_settings()
            default_max_retries = max_retries if max_retries is not None else settings.agents.max_retries
            default_base_delay = base_delay if base_delay is not None else settings.agents.retry_backoff_seconds
        except Exception:
            # Config not available, use provided or hardcoded defaults
            default_max_retries = max_retries if max_retries is not None else 3
            default_base_delay = base_delay if base_delay is not None else 2.0

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(default_max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Check if exception is non-retryable (has is_retryable attribute set to False)
                    is_retryable = getattr(e, "is_retryable", True)
                    if not is_retryable:
                        logger.debug(
                            f"Exception is non-retryable for {func.__name__}: {type(e).__name__}",
                            extra={
                                "function": func.__name__,
                                "exception_type": type(e).__name__,
                            },
                        )
                        raise

                    if attempt < default_max_retries:
                        delay = exponential_backoff_delay(
                            attempt,
                            default_base_delay,
                            max_delay,
                            jitter,
                        )

                        logger.warning(
                            f"Retry attempt {attempt + 1}/{default_max_retries} "
                            f"for {func.__name__} after {delay:.2f}s: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": default_max_retries,
                                "delay": delay,
                                "exception_type": type(e).__name__,
                            },
                        )

                        # Call retry callback if provided
                        if on_retry:
                            on_retry(attempt + 1, e)

                        time.sleep(delay)
                    else:
                        # Final attempt failed
                        logger.error(
                            f"All {default_max_retries + 1} attempts exhausted "
                            f"for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": default_max_retries + 1,
                                "exception_type": type(last_exception).__name__
                                if last_exception
                                else None,
                            },
                            exc_info=last_exception,
                        )
                        raise RetryError(
                            f"Failed after {default_max_retries + 1} attempts: {str(last_exception)}",
                            last_exception,
                        ) from last_exception

            # Should never reach here, but for type safety
            raise RetryError(
                f"Failed after {default_max_retries + 1} attempts",
                last_exception,
            )

        return wrapper

    return decorator


def async_retry_with_backoff(
    max_retries: Optional[int] = None,
    base_delay: Optional[float] = None,
    max_delay: float = 300.0,
    jitter: bool = True,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying async function calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (defaults to config value).
        base_delay: Base delay in seconds (defaults to config value).
        max_delay: Maximum delay cap in seconds.
        jitter: Whether to add random jitter.
        exceptions: Tuple of exception types to catch and retry.
        on_retry: Optional callback function(attempt, exception) called before retry.

    Returns:
        Decorated async function with retry logic.

    Example:
        @async_retry_with_backoff(max_retries=3, base_delay=2.0)
        async def fetch_data_async():
            # Async function that might fail
            pass
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Get default values from config if not provided
        settings = None
        try:
            settings = get_settings()
            default_max_retries = max_retries if max_retries is not None else settings.agents.max_retries
            default_base_delay = base_delay if base_delay is not None else settings.agents.retry_backoff_seconds
        except Exception:
            # Config not available, use provided or hardcoded defaults
            default_max_retries = max_retries if max_retries is not None else 3
            default_base_delay = base_delay if base_delay is not None else 2.0

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None

            for attempt in range(default_max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    # Check if exception is non-retryable (has is_retryable attribute set to False)
                    is_retryable = getattr(e, "is_retryable", True)
                    if not is_retryable:
                        logger.debug(
                            f"Exception is non-retryable for {func.__name__}: {type(e).__name__}",
                            extra={
                                "function": func.__name__,
                                "exception_type": type(e).__name__,
                            },
                        )
                        raise

                    if attempt < default_max_retries:
                        delay = exponential_backoff_delay(
                            attempt,
                            default_base_delay,
                            max_delay,
                            jitter,
                        )

                        logger.warning(
                            f"Retry attempt {attempt + 1}/{default_max_retries} "
                            f"for {func.__name__} after {delay:.2f}s: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": default_max_retries,
                                "delay": delay,
                                "exception_type": type(e).__name__,
                            },
                        )

                        # Call retry callback if provided
                        if on_retry:
                            on_retry(attempt + 1, e)

                        await asyncio.sleep(delay)
                    else:
                        # Final attempt failed
                        logger.error(
                            f"All {default_max_retries + 1} attempts exhausted "
                            f"for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": default_max_retries + 1,
                                "exception_type": type(last_exception).__name__
                                if last_exception
                                else None,
                            },
                            exc_info=last_exception,
                        )
                        raise RetryError(
                            f"Failed after {default_max_retries + 1} attempts: {str(last_exception)}",
                            last_exception,
                        ) from last_exception

            # Should never reach here, but for type safety
            raise RetryError(
                f"Failed after {default_max_retries + 1} attempts",
                last_exception,
            )

        return wrapper

    return decorator


__all__ = [
    "RetryError",
    "exponential_backoff_delay",
    "retry_with_backoff",
    "async_retry_with_backoff",
]

