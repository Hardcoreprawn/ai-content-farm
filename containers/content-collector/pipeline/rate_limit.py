"""
Token bucket rate limiter with exponential backoff on 429 errors.

Pure functions, defensive coding, no state mutation.
"""

import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with exponential backoff.

    Tracks available tokens and enforces rate limits. On 429 (rate limit)
    errors, exponentially backs off until limit is reset.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 300.0,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Target rate limit (default 60 = 1 per second)
            backoff_multiplier: Multiplier for exponential backoff (default 2.0)
            max_backoff: Maximum backoff time in seconds (default 300 = 5 min)
        """
        self.capacity = requests_per_minute
        self.tokens = requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # tokens per second
        self.last_refill = time.time()

        self.backoff_multiplier = backoff_multiplier
        self.max_backoff = max_backoff
        self.current_delay = 0.0

        self._lock = asyncio.Lock()

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire a token for making a request, with optional timeout.

        Waits for token availability, includes current backoff delay.

        Args:
            timeout: Maximum time to wait in seconds. If None, waits indefinitely.

        Returns:
            True if token acquired, False on timeout
        """
        async with self._lock:
            start_time: Optional[float] = time.time() if timeout else None

            # Apply current backoff delay
            if self.current_delay > 0:
                if timeout is not None and start_time is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                    await asyncio.sleep(min(self.current_delay, timeout - elapsed))
                else:
                    await asyncio.sleep(self.current_delay)

            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            # Wait for token if needed
            while self.tokens < 1:
                if timeout is not None and start_time is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        return False
                    remaining_timeout = timeout - elapsed
                else:
                    remaining_timeout = float("inf")

                wait_time = (1 - self.tokens) / self.refill_rate

                if timeout is not None:
                    wait_time = min(wait_time, 0.1, remaining_timeout)
                else:
                    wait_time = min(wait_time, 0.1)

                await asyncio.sleep(wait_time)

                now = time.time()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.capacity, self.tokens + elapsed * self.refill_rate
                )
                self.last_refill = now

            # Consume token
            self.tokens -= 1
            return True

    def handle_429(self, retry_after: Optional[int] = None) -> None:
        """
        Handle 429 (rate limit) error with exponential backoff.

        Args:
            retry_after: Seconds to wait from Retry-After header (optional)
        """
        if retry_after:
            self.current_delay = retry_after
            logger.warning(f"Rate limited. Waiting {retry_after}s (from header)")
        else:
            # Exponential backoff starting at multiplier
            if self.current_delay == 0:
                self.current_delay = self.backoff_multiplier
            else:
                self.current_delay = min(
                    self.current_delay * self.backoff_multiplier, self.max_backoff
                )
            logger.warning(f"Rate limited. Backing off for {self.current_delay}s")

    def reset_backoff(self) -> None:
        """Reset backoff delay after successful request."""
        self.current_delay = 0.0

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


def create_reddit_limiter() -> RateLimiter:
    """
    Create rate limiter configured for Reddit API.

    Reddit recommends respectful rate limiting and user-agent headers.
    Conservative: 30 requests per minute = 2 second delay.
    """
    return RateLimiter(
        requests_per_minute=30, backoff_multiplier=2.5, max_backoff=600.0
    )


def create_mastodon_limiter() -> RateLimiter:
    """
    Create rate limiter configured for Mastodon instances.

    Mastodon public timeline: 300 requests per 5 minutes = 1 per second.
    Conservative: 60 requests per minute.
    """
    return RateLimiter(
        requests_per_minute=60, backoff_multiplier=2.0, max_backoff=300.0
    )
