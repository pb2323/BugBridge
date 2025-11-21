"""Retry logic with exponential backoff"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, Type, Tuple

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger_name: Optional[str] = None
):
    """Decorator for retry logic with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        exceptions: Tuple of exception types to catch and retry
        logger_name: Optional logger name for logging
    
    Usage:
        @retry_with_backoff(max_attempts=3, backoff_factor=2.0)
        async def my_function():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            _logger = logging.getLogger(logger_name or func.__module__)
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        _logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
                        raise
                    
                    wait_time = backoff_factor ** (attempt - 1)
                    _logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {str(e)}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
            
            return None
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            _logger = logging.getLogger(logger_name or func.__module__)
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        _logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
                        raise
                    
                    wait_time = backoff_factor ** (attempt - 1)
                    _logger.warning(
                        f"{func.__name__} attempt {attempt} failed: {str(e)}. "
                        f"Retrying in {wait_time}s..."
                    )
                    import time
                    time.sleep(wait_time)
            
            return None
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
