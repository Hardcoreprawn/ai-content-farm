"""
Functional rate limiting for OpenAI API calls.

Uses aiolimiter library (proven, well-tested) instead of custom implementation.
All functions are pure with explicit dependencies.

Installation:
    pip install aiolimiter

Usage:
    from libs.openai_rate_limiter import create_rate_limiter, call_with_rate_limit

    # Create limiter at startup
    limiter = create_rate_limiter(max_requests_per_minute=60)

    # Use in processing
    result = await call_with_rate_limit(
        openai_client.chat.completions.create,
        limiter,
        model="gpt-4o",
        messages=[...]
    )
"""

from typing import Any, Callable, Dict

from aiolimiter import AsyncLimiter


def create_rate_limiter(
    max_requests_per_minute: int = 60,
    time_period_seconds: int = 60,
) -> AsyncLimiter:
    """
    Create a rate limiter instance.

    Pure function - returns configured limiter.

    Args:
        max_requests_per_minute: Maximum API calls per time period
        time_period_seconds: Time period in seconds (default 60 for per-minute)

    Returns:
        Configured AsyncLimiter instance

    Example:
        >>> limiter = create_rate_limiter(max_requests_per_minute=60)
        >>> # Use with call_with_rate_limit or async context manager
    """
    return AsyncLimiter(
        max_rate=max_requests_per_minute, time_period=time_period_seconds
    )


async def call_with_rate_limit(
    limiter: AsyncLimiter,
    func: Callable,
    *args,
    **kwargs,
) -> Any:
    """
    Execute async function with rate limiting.

    Pure function - wraps any async function with rate limiting.

    Args:
        limiter: AsyncLimiter instance from create_rate_limiter()
        func: Async function to call
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result from func

    Raises:
        Whatever func raises

    Example:
        >>> limiter = create_rate_limiter(60)
        >>> result = await call_with_rate_limit(
        ...     limiter,
        ...     openai_client.chat.completions.create,
        ...     model="gpt-4o",
        ...     messages=[{"role": "user", "content": "Hello"}]
        ... )
    """
    async with limiter:
        return await func(*args, **kwargs)


def get_limiter_stats(limiter: AsyncLimiter) -> Dict[str, Any]:
    """
    Get current rate limiter statistics.

    Pure function - reads limiter state without modification.

    Args:
        limiter: AsyncLimiter instance

    Returns:
        Dict with current stats (max_rate, time_period, has_capacity)

    Example:
        >>> limiter = create_rate_limiter(60)
        >>> stats = get_limiter_stats(limiter)
        >>> print(f"Has capacity: {stats['has_capacity']}")
    """
    return {
        "max_rate": limiter.max_rate,
        "time_period": limiter.time_period,
        "has_capacity": limiter.has_capacity(),
    }


def create_multi_region_limiters(regions: Dict[str, int]) -> Dict[str, AsyncLimiter]:
    """
    Create rate limiters for multiple OpenAI regions.

    Pure function - returns dict of configured limiters.

    Args:
        regions: Dict of {region_name: requests_per_minute}
                e.g., {"uksouth": 60, "westeurope": 60}

    Returns:
        Dict of {region_name: AsyncLimiter}

    Example:
        >>> limiters = create_multi_region_limiters({
        ...     "uksouth": 60,
        ...     "westeurope": 60
        ... })
        >>> uk_limiter = limiters["uksouth"]
    """
    return {
        region: create_rate_limiter(max_requests_per_minute=rpm)
        for region, rpm in regions.items()
    }


def get_best_region(limiters: Dict[str, AsyncLimiter]) -> str:
    """
    Get region with most available capacity.

    Pure function - finds best region based on current state.

    Args:
        limiters: Dict of {region_name: AsyncLimiter}

    Returns:
        Region name with most capacity

    Example:
        >>> limiters = create_multi_region_limiters({"uk": 60, "eu": 60})
        >>> best = get_best_region(limiters)
        >>> # Use limiters[best] for next request
    """
    # Find region with capacity, prefer first if multiple have capacity
    for region, limiter in limiters.items():
        if limiter.has_capacity():
            return region

    # If none have capacity, return first (will wait)
    return list(limiters.keys())[0]
