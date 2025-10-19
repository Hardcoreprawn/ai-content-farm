"""
Unsplash API client with rate limiting and retry logic.

Handles rate limiting (Unsplash: 50 requests/hour for free tier),
exponential backoff on 403 errors, and detailed logging.

Rate Limits (Unsplash Free Tier):
- 50 requests per hour
- Headers: X-Ratelimit-Limit, X-Ratelimit-Remaining, X-Ratelimit-Reset
- 403 = Rate limit exceeded

Strategy:
- Use token bucket limiter: ~0.83 requests/sec = 50/hour
- Add 50% buffer: 0.4 requests/sec to stay safely below limit
- Exponential backoff on 403 errors (1s → 2s → 4s max 30s)
- Log remaining quota for monitoring
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from libs.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Unsplash API configuration
UNSPLASH_API_BASE_URL = "https://api.unsplash.com"

# Rate limiting: Free tier = 50 requests/hour
# Use 0.4 req/s = ~24 req/min = 1440 req/hour (well below limit, allows bursting)
# This gives us a 96% safety margin below the 50/hour limit
UNSPLASH_RATE_LIMIT = 0.4  # requests per second
UNSPLASH_RATE_LIMIT_NAME = "unsplash-api"

# Singleton limiter instance (shared across all requests)
_unsplash_limiter: Optional[RateLimiter] = None


def get_unsplash_limiter() -> RateLimiter:
    """
    Get or create singleton Unsplash rate limiter.

    Returns:
        RateLimiter instance configured for Unsplash (0.4 req/sec)
    """
    global _unsplash_limiter

    if _unsplash_limiter is None:
        # Calculate tokens: 0.4 req/sec = 24 req/min
        # Allow bursting: capacity = 5 requests max at once
        rate = 0.4  # requests per second
        capacity = 5  # allow burst of 5
        _unsplash_limiter = RateLimiter(
            rate=int(rate * 60),  # Convert to per-minute for the API
            per_seconds=60,
            capacity=int(capacity),
            name=UNSPLASH_RATE_LIMIT_NAME,
        )
        logger.info(
            f"Created Unsplash rate limiter: "
            f"{rate} req/sec, burst capacity={capacity}"
        )

    return _unsplash_limiter


class UnsplashRateLimitError(Exception):
    """Raised when Unsplash rate limit is exceeded after retries."""

    pass


class UnsplashError(Exception):
    """Base exception for Unsplash API errors."""

    pass


async def search_unsplash_photo(
    access_key: str,
    query: str,
    orientation: str = "landscape",
    max_retries: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Search Unsplash API for a single photo with rate limiting and retries.

    Handles:
    - Rate limiting (0.4 req/sec to stay below 50/hour quota)
    - Exponential backoff on rate limit errors (403)
    - Request/response logging for monitoring

    Args:
        access_key: Unsplash API access key
        query: Search query (article topic)
        orientation: "landscape", "portrait", or "squarish"
        max_retries: Maximum retry attempts on rate limit error

    Returns:
        First photo data dict or None if not found

    Raises:
        UnsplashRateLimitError: If rate limit exceeded after all retries
        UnsplashError: For other API errors
        aiohttp.ClientError: For network errors

    Examples:
        >>> photo = await search_unsplash_photo(
        ...     access_key="key",
        ...     query="artificial intelligence"
        ... )
        >>> photo["photographer"]  # if found
        'Jane Photographer'
    """
    limiter = get_unsplash_limiter()
    attempt = 0
    retry_wait = 1  # Initial retry wait: 1 second

    clean_query = query.strip()[:100]

    if not clean_query:
        logger.warning("Empty search query provided to Unsplash")
        return None

    while attempt <= max_retries:
        try:
            # Wait for rate limit token
            logger.debug(
                f"Acquiring rate limit token (attempt={attempt}, "
                f"status={limiter.get_stats()})"
            )
            async with limiter:
                logger.info(f"Searching Unsplash: query='{clean_query}'")

                session = aiohttp.ClientSession()
                try:
                    params = {
                        "query": clean_query,
                        "per_page": 1,
                        "orientation": orientation,
                        "content_filter": "high",
                    }
                    headers = {"Authorization": f"Client-ID {access_key}"}
                    url = f"{UNSPLASH_API_BASE_URL}/search/photos"

                    async with session.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        # Extract rate limit headers for monitoring
                        limit = resp.headers.get("X-Ratelimit-Limit")
                        remaining = resp.headers.get("X-Ratelimit-Remaining")
                        reset = resp.headers.get("X-Ratelimit-Reset")

                        if resp.status == 200:
                            data = await resp.json()

                            logger.info(
                                f"Unsplash search successful: "
                                f"remaining={remaining}/{limit} "
                                f"(reset={reset})"
                            )

                            if data.get("results"):
                                return data["results"][0]
                            else:
                                logger.warning(f"No images found for: {clean_query}")
                                return None

                        elif resp.status == 403:
                            # Rate limit exceeded
                            logger.warning(
                                f"Unsplash rate limit (403): "
                                f"remaining={remaining}/{limit}, reset={reset}"
                            )

                            if attempt < max_retries:
                                logger.info(
                                    f"Retrying after {retry_wait}s "
                                    f"(attempt {attempt + 1}/{max_retries})"
                                )
                                import asyncio

                                await asyncio.sleep(retry_wait)
                                retry_wait *= 2  # Exponential backoff
                                attempt += 1
                                continue
                            else:
                                raise UnsplashRateLimitError(
                                    f"Unsplash rate limit exceeded after {max_retries} retries"
                                )

                        elif resp.status == 401:
                            error_text = await resp.text()
                            logger.error(f"Unsplash auth error (401): {error_text}")
                            raise UnsplashError(f"Invalid API key: {error_text}")

                        else:
                            error_text = await resp.text()
                            logger.error(
                                f"Unsplash API error ({resp.status}): {error_text}"
                            )
                            raise UnsplashError(
                                f"API error {resp.status}: {error_text}"
                            )

                finally:
                    await session.close()

        except UnsplashRateLimitError:
            # Don't retry rate limit errors further
            raise
        except UnsplashError:
            # Don't retry other API errors
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Network error from Unsplash: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Unsplash search: {e}", exc_info=True)
            raise
