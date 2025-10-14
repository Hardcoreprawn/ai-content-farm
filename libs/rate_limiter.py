"""
Rate Limiter with Token Bucket Algorithm

Prevents hitting Azure OpenAI rate limits (429 errors) by throttling requests.
Implements token bucket algorithm with async support.

Usage:
    from libs.rate_limiter import RateLimiter

    # 60 requests per minute
    limiter = RateLimiter(rate=60, per_seconds=60)

    async with limiter:
        # Make API call - will wait if rate limit exceeded
        response = await client.make_request()
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for async operations.

    Allows burst traffic up to capacity, then enforces steady rate.
    Thread-safe for async operations.
    """

    def __init__(
        self,
        rate: int,
        per_seconds: int = 60,
        capacity: Optional[int] = None,
        name: str = "default",
    ):
        """
        Initialize rate limiter.

        Args:
            rate: Number of requests allowed per time period
            per_seconds: Time period in seconds (default 60 for per-minute)
            capacity: Bucket capacity (default = rate, allows bursting)
            name: Name for logging
        """
        self.rate = rate
        self.per_seconds = per_seconds
        self.capacity = capacity or rate
        self.name = name

        # Token bucket state
        self.tokens = float(self.capacity)
        self.last_update = time.monotonic()

        # Asyncio lock for thread safety
        self._lock = asyncio.Lock()

        # Statistics
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.throttled_requests = 0

        logger.info(
            f"🚦 RateLimiter '{name}' initialized: {rate}/{per_seconds}s "
            f"(capacity: {self.capacity})"
        )

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update

        # Calculate tokens to add based on rate
        tokens_to_add = elapsed * (self.rate / self.per_seconds)

        # Add tokens but don't exceed capacity
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now

    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default 1)

        Returns:
            Wait time in seconds (0 if no wait needed)
        """
        async with self._lock:
            self._refill_tokens()

            # If we have enough tokens, consume and return
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.total_requests += 1
                return 0.0

            # Calculate wait time for tokens to refill
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / (self.rate / self.per_seconds)

            self.total_wait_time += wait_time
            self.throttled_requests += 1

            logger.warning(
                f"⏳ RateLimiter '{self.name}' throttling: "
                f"waiting {wait_time:.2f}s for {tokens} tokens"
            )

        # Wait outside the lock so other requests can check
        await asyncio.sleep(wait_time)

        # Acquire again after waiting
        async with self._lock:
            self._refill_tokens()
            self.tokens -= tokens
            self.total_requests += 1
            return wait_time

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "name": self.name,
            "rate": self.rate,
            "per_seconds": self.per_seconds,
            "capacity": self.capacity,
            "current_tokens": self.tokens,
            "total_requests": self.total_requests,
            "throttled_requests": self.throttled_requests,
            "total_wait_time_seconds": self.total_wait_time,
            "throttle_percentage": (
                100 * self.throttled_requests / self.total_requests
                if self.total_requests > 0
                else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset statistics (not token bucket)."""
        self.total_requests = 0
        self.total_wait_time = 0.0
        self.throttled_requests = 0


class MultiRegionRateLimiter:
    """
    Rate limiter pool for multiple OpenAI regions.

    Tracks separate rate limits per region and provides
    automatic region selection based on availability.
    """

    def __init__(self, regions: dict[str, tuple[int, int]]):
        """
        Initialize multi-region rate limiter.

        Args:
            regions: Dict of {region_name: (rate, per_seconds)}
                    e.g., {"uksouth": (60, 60), "westeurope": (60, 60)}
        """
        self.limiters = {
            region: RateLimiter(rate=rate, per_seconds=per, name=region)
            for region, (rate, per) in regions.items()
        }
        self.current_region = list(self.limiters.keys())[0] if self.limiters else None

    async def acquire(
        self, region: Optional[str] = None, tokens: int = 1
    ) -> tuple[str, float]:
        """
        Acquire tokens from specified or best available region.

        Args:
            region: Preferred region (None = auto-select)
            tokens: Number of tokens to acquire

        Returns:
            Tuple of (region_used, wait_time)
        """
        if region and region in self.limiters:
            wait_time = await self.limiters[region].acquire(tokens)
            return region, wait_time

        # Auto-select region with most available tokens
        async with asyncio.Lock():  # Prevent race conditions
            best_region = max(
                self.limiters.keys(), key=lambda r: self.limiters[r].tokens
            )

        wait_time = await self.limiters[best_region].acquire(tokens)
        return best_region, wait_time

    @asynccontextmanager
    async def use_region(self, region: Optional[str] = None):
        """
        Async context manager for region-specific rate limiting.

        Usage:
            async with rate_limiter.use_region("uksouth") as selected_region:
                # Make API call to selected_region
                pass
        """
        selected_region, wait_time = await self.acquire(region)
        try:
            yield selected_region
        finally:
            pass

    def get_all_stats(self) -> dict[str, dict]:
        """Get statistics for all regions."""
        return {
            region: limiter.get_stats() for region, limiter in self.limiters.items()
        }

    def get_healthiest_region(self) -> str:
        """Get region with best availability."""
        return max(
            self.limiters.keys(),
            key=lambda r: (
                self.limiters[r].tokens,
                -self.limiters[r].throttled_requests,
            ),
        )


# Global rate limiter instances (initialized by containers)
_openai_limiter: Optional[MultiRegionRateLimiter] = None


def get_openai_rate_limiter() -> MultiRegionRateLimiter:
    """Get global OpenAI rate limiter instance."""
    global _openai_limiter

    if _openai_limiter is None:
        # Default configuration - should be overridden by container
        _openai_limiter = MultiRegionRateLimiter(
            {
                "uksouth": (60, 60),  # 60 RPM
                "westeurope": (60, 60),  # 60 RPM
            }
        )

    return _openai_limiter


def initialize_openai_rate_limiter(regions: dict[str, tuple[int, int]]) -> None:
    """
    Initialize global OpenAI rate limiter with specific configuration.

    Call this from container startup with actual rate limits from config.

    Args:
        regions: Dict of {region_name: (rate_per_minute, period_seconds)}
    """
    global _openai_limiter
    _openai_limiter = MultiRegionRateLimiter(regions)
    logger.info(
        f"🚦 Initialized OpenAI rate limiter for regions: {list(regions.keys())}"
    )
