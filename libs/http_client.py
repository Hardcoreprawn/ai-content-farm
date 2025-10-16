"""
Shared HTTP Client Management

Provides centralized HTTP client lifecycle management with connection pooling,
proper cleanup, and consistent configuration across all containers.

Benefits:
- Single session per application (connection pooling)
- Automatic cleanup on shutdown (no resource leaks)
- Consistent timeouts and retry behavior
- DRY principle - don't create sessions everywhere
"""

import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

# Global session for connection pooling and proper cleanup
_http_session: Optional[aiohttp.ClientSession] = None


async def get_http_session(
    timeout: Optional[float] = 30.0,
    connector_limit: int = 100,
) -> aiohttp.ClientSession:
    """
    Get or create the shared HTTP session for connection pooling.

    Creates a single session per application lifecycle, reusing connections
    and preventing resource leaks from creating multiple ClientSession instances.

    Args:
        timeout: Request timeout in seconds (default: 30s)
        connector_limit: Maximum simultaneous connections (default: 100)

    Returns:
        Shared aiohttp ClientSession instance

    Example:
        >>> session = await get_http_session()
        >>> async with session.get("https://api.example.com/data") as resp:
        ...     data = await resp.json()
    """
    global _http_session

    if _http_session is None or _http_session.closed:
        # Configure connection pooling and timeouts
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        connector = aiohttp.TCPConnector(
            limit=connector_limit,
            limit_per_host=30,  # Max connections per host
            ttl_dns_cache=300,  # DNS cache TTL (5 minutes)
        )

        _http_session = aiohttp.ClientSession(
            timeout=timeout_config,
            connector=connector,
            # Add common headers if needed
            headers={
                "User-Agent": "ai-content-farm/1.0",
            },
        )
        logger.info(
            f"Created shared HTTP session (timeout={timeout}s, "
            f"max_connections={connector_limit})"
        )

    return _http_session


async def close_http_session() -> None:
    """
    Close the shared HTTP session.

    Should be called during application shutdown to ensure proper cleanup
    and prevent 'Unclosed client session' warnings.

    Example:
        >>> # In FastAPI lifespan or container shutdown
        >>> await close_http_session()
    """
    global _http_session

    if _http_session is not None and not _http_session.closed:
        await _http_session.close()
        _http_session = None
        logger.info("Closed shared HTTP session")


async def reset_http_session() -> None:
    """
    Force close and reset the shared HTTP session.

    Useful for testing or when connection state becomes invalid.
    Next call to get_http_session() will create a new session.

    Example:
        >>> # In test teardown or error recovery
        >>> await reset_http_session()
    """
    await close_http_session()
    logger.debug("Reset shared HTTP session")
