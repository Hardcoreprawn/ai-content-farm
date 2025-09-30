"""
Retry utilities using Tenacity for robust error handling.

Provides standardized retry patterns for common operations in the site generator,
using the industry-standard tenacity library with proper integration to our
error handling and logging patterns.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable, Optional, Type, Union

from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from libs import SecureErrorHandler
from libs.site_generator_exceptions import SiteGeneratorError, StorageError

logger = logging.getLogger(__name__)
error_handler = SecureErrorHandler("retry-utilities")


# Standard retry configurations for common scenarios
def storage_retry(max_attempts: int = 5, min_wait: float = 1.0, max_wait: float = 30.0):
    """
    Retry configuration for storage operations.

    Retries on storage-related exceptions with exponential backoff.
    Suitable for blob storage operations, file uploads, etc.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Example:
        >>> @storage_retry(max_attempts=3)
        ... async def upload_file(path: str) -> bool:
        ...     return await blob_client.upload(path)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(
            (StorageError, ConnectionError, TimeoutError, OSError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.DEBUG),
    )


def network_retry(max_attempts: int = 3, min_wait: float = 0.5, max_wait: float = 10.0):
    """
    Retry configuration for network operations.

    Retries on network-related exceptions with shorter backoff times.
    Suitable for API calls, HTTP requests, etc.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Example:
        >>> @network_retry(max_attempts=2)
        ... async def fetch_data(url: str) -> dict:
        ...     return await http_client.get(url)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
        before_sleep=before_sleep_log(logger, logging.INFO),
        after=after_log(logger, logging.DEBUG),
    )


def quick_retry(max_attempts: int = 2, wait_time: float = 0.1):
    """
    Retry configuration for quick operations.

    Simple retry with fixed wait time for operations that should be fast.
    Suitable for local file operations, cache access, etc.

    Args:
        max_attempts: Maximum number of retry attempts
        wait_time: Fixed wait time between retries (seconds)

    Example:
        >>> @quick_retry(max_attempts=2)
        ... def read_cache(key: str) -> Optional[str]:
        ...     return cache.get(key)
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=wait_time, max=wait_time),
        retry=retry_if_exception_type((OSError, IOError)),
        before_sleep=before_sleep_log(logger, logging.DEBUG),
        after=after_log(logger, logging.DEBUG),
    )


def with_secure_retry(
    retry_config: Callable,
    *,
    operation_name: Optional[str] = None,
    error_context: Optional[dict] = None,
):
    """
    Decorator that combines Tenacity retry with SecureErrorHandler integration.

    Provides retry functionality with proper error sanitization and logging
    through our established SecureErrorHandler patterns.

    Args:
        retry_config: Tenacity retry configuration (e.g., storage_retry())
        operation_name: Name for logging (uses function name if None)
        error_context: Additional context for error handling

    Example:
        >>> @with_secure_retry(
        ...     storage_retry(max_attempts=3),
        ...     operation_name="upload_content",
        ...     error_context={"component": "content_processor"}
        ... )
        ... async def upload_content(data: bytes) -> str:
        ...     return await blob_client.upload(data)
    """

    def decorator(func: Callable) -> Callable:
        nonlocal operation_name
        if operation_name is None:
            operation_name = func.__name__

        # Apply the tenacity retry decorator
        retried_func = retry_config(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await retried_func(*args, **kwargs)
            except Exception as e:
                # Use SecureErrorHandler for final error processing
                sanitized_error = error_handler.handle_error(
                    error=e,
                    error_type="retry_exhausted",
                    context={
                        "operation": operation_name,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                        **(error_context or {}),
                    },
                )

                logger.error(
                    f"Operation {operation_name} failed after retries: {sanitized_error['message']}"
                )

                # Convert to our exception hierarchy if needed
                if not isinstance(e, SiteGeneratorError):
                    raise SiteGeneratorError(
                        f"Operation {operation_name} failed after retries",
                        details={"original_error": str(e)},
                    ) from e
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return retried_func(*args, **kwargs)
            except Exception as e:
                # Use SecureErrorHandler for final error processing
                sanitized_error = error_handler.handle_error(
                    error=e,
                    error_type="retry_exhausted",
                    context={
                        "operation": operation_name,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                        **(error_context or {}),
                    },
                )

                logger.error(
                    f"Operation {operation_name} failed after retries: {sanitized_error['message']}"
                )

                # Convert to our exception hierarchy if needed
                if not isinstance(e, SiteGeneratorError):
                    raise SiteGeneratorError(
                        f"Operation {operation_name} failed after retries",
                        details={"original_error": str(e)},
                    ) from e
                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
