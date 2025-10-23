"""
Test rate limiter handles 429 responses with exponential backoff.
"""

import asyncio
from unittest.mock import Mock

import pytest
from pipeline.rate_limit import RateLimiter


class TestRateLimiter429Handling:
    """Verify exponential backoff on rate limit responses."""

    @pytest.mark.asyncio
    async def test_429_triggers_exponential_backoff(self):
        """When 429 seen, delay increases exponentially."""
        limiter = RateLimiter(
            requests_per_minute=60, backoff_multiplier=2.0, max_backoff=300.0
        )

        # Initial delay is 0
        assert limiter.current_delay == 0.0

        # First 429
        limiter.handle_429()
        assert limiter.current_delay == 2.0  # 1 * 2.0

        # Second 429
        limiter.handle_429()
        assert limiter.current_delay == 4.0  # 2.0 * 2.0

        # Third 429
        limiter.handle_429()
        assert limiter.current_delay == 8.0  # 4.0 * 2.0

    @pytest.mark.asyncio
    async def test_429_respects_max_backoff(self):
        """Exponential backoff doesn't exceed max_backoff."""
        limiter = RateLimiter(
            requests_per_minute=60, backoff_multiplier=2.0, max_backoff=10.0
        )

        # Trigger many 429s
        for _ in range(10):
            limiter.handle_429()

        # Should be capped at max_backoff
        assert limiter.current_delay <= 10.0

    @pytest.mark.asyncio
    async def test_retry_after_header_sets_delay(self):
        """Retry-After header value is used if provided."""
        limiter = RateLimiter(
            requests_per_minute=60, backoff_multiplier=2.0, max_backoff=300.0
        )

        # Handle 429 with Retry-After: 45
        limiter.handle_429(retry_after=45)

        assert limiter.current_delay == 45  # Exact value from header

    @pytest.mark.asyncio
    async def test_reset_backoff_clears_delay(self):
        """After success, backoff resets to 0."""
        limiter = RateLimiter(
            requests_per_minute=60, backoff_multiplier=2.0, max_backoff=300.0
        )

        # Trigger 429s
        limiter.handle_429()
        limiter.handle_429()
        assert limiter.current_delay == 4.0

        # Reset after success
        limiter.reset_backoff()
        assert limiter.current_delay == 0.0

    @pytest.mark.asyncio
    async def test_acquire_includes_backoff_delay(self):
        """Token acquisition waits for backoff delay."""
        limiter = RateLimiter(
            requests_per_minute=60, backoff_multiplier=2.0, max_backoff=300.0
        )

        # Set backoff
        limiter.current_delay = 0.1

        # Acquire should wait
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have waited ~0.1 seconds
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_reddit_limiter_config(self):
        """Reddit limiter has correct rate limit config."""
        from pipeline.rate_limit import create_reddit_limiter

        limiter = create_reddit_limiter()

        # 30 rpm = 2 req/sec = 0.5 sec per request
        assert limiter.capacity == 30
        assert limiter.backoff_multiplier == 2.5
        assert limiter.max_backoff == 600.0  # 10 minutes max

    @pytest.mark.asyncio
    async def test_mastodon_limiter_config(self):
        """Mastodon limiter has correct rate limit config."""
        from pipeline.rate_limit import create_mastodon_limiter

        limiter = create_mastodon_limiter()

        # 60 rpm = 1 req/sec
        assert limiter.capacity == 60
        assert limiter.backoff_multiplier == 2.0
        assert limiter.max_backoff == 300.0  # 5 minutes max
