"""
Tests for rate limiting (pipeline/rate_limit.py).

Token bucket with exponential backoff on rate limit errors.
Pure functions, defensive coding.
"""

import asyncio
import time

import pytest


class TestRateLimiter:
    """Test token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_token_bucket_basic_acquire(self):
        """Basic token acquisition works."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Should acquire immediately with tokens available
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        assert elapsed < 0.1  # Should be instant

    @pytest.mark.asyncio
    async def test_token_bucket_respects_limit(self):
        """Acquisition respects rate limit."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=6)  # 1 request per 10 seconds

        # First request immediate
        start = time.time()
        await limiter.acquire()
        first_time = time.time() - start

        # Second request should wait ~10 seconds
        start = time.time()
        await limiter.acquire()
        second_time = time.time() - start

        assert first_time < 0.1
        assert second_time > 8.0  # ~10 sec with tolerance

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_429(self):
        """Backoff increases exponentially on 429 errors."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, backoff_multiplier=2.0)

        # Initial backoff is 0
        assert limiter.current_delay == 0.0

        # After 429 error
        limiter.handle_429()
        assert limiter.current_delay == 2.0  # First backoff is 2.0

        # After another 429
        limiter.handle_429()
        assert limiter.current_delay == 4.0  # 2.0 * 2.0

        # After another 429
        limiter.handle_429()
        assert limiter.current_delay == 8.0

    @pytest.mark.asyncio
    async def test_backoff_respects_max(self):
        """Backoff respects maximum limit."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(
            requests_per_minute=60, backoff_multiplier=2.0, max_backoff=10.0
        )

        # Increase backoff multiple times
        for _ in range(10):
            limiter.handle_429()

        # Should not exceed max_backoff
        assert limiter.current_delay == 10.0

    @pytest.mark.asyncio
    async def test_backoff_with_retry_after(self):
        """Retry-After header is respected."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Retry-After of 30 seconds
        limiter.handle_429(retry_after=30)

        assert limiter.current_delay == 30

    @pytest.mark.asyncio
    async def test_backoff_resets_on_success(self):
        """Backoff resets after successful request."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Cause backoff
        limiter.handle_429()
        assert limiter.current_delay == 2.0

        # Reset on success
        limiter.reset_backoff()
        assert limiter.current_delay == 0.0

    @pytest.mark.asyncio
    async def test_multiple_limiters_independent(self):
        """Multiple limiter instances are independent."""
        from pipeline.rate_limit import RateLimiter

        limiter1 = RateLimiter(requests_per_minute=60)
        limiter2 = RateLimiter(requests_per_minute=120)

        limiter1.handle_429()
        limiter1.handle_429()

        # limiter2 should not be affected
        assert limiter1.current_delay == 4.0
        assert limiter2.current_delay == 0.0

    @pytest.mark.asyncio
    async def test_acquire_applies_backoff(self):
        """acquire() includes current backoff delay."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Cause 500ms backoff
        limiter.current_delay = 0.5

        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        # Should include backoff + token bucket delay
        assert elapsed >= 0.4  # Tolerance for timing

    @pytest.mark.asyncio
    async def test_initial_tokens_available(self):
        """Initial tokens equal requests_per_minute."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=30)

        assert limiter.tokens == 30

    @pytest.mark.asyncio
    async def test_refill_rate_calculation(self):
        """Refill rate is calculated correctly."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # 60 requests per minute = 1 per second
        assert limiter.refill_rate == pytest.approx(1.0, rel=0.01)

        limiter2 = RateLimiter(requests_per_minute=120)
        # 120 per minute = 2 per second
        assert limiter2.refill_rate == pytest.approx(2.0, rel=0.01)


class TestRedditRateLimiter:
    """Test Reddit-specific rate limiting settings."""

    @pytest.mark.asyncio
    async def test_reddit_limiter_config(self):
        """Reddit limiter configured appropriately."""
        from pipeline.rate_limit import create_reddit_limiter

        limiter = create_reddit_limiter()

        # Reddit-specific: 2 second delay between subreddit requests
        assert limiter is not None
        # Should have conservative settings for Reddit
        assert limiter.current_delay == 0.0

    @pytest.mark.asyncio
    async def test_mastodon_limiter_config(self):
        """Mastodon limiter configured appropriately."""
        from pipeline.rate_limit import create_mastodon_limiter

        limiter = create_mastodon_limiter()

        # Mastodon-specific: 1 second delay between requests
        assert limiter is not None
        assert limiter.current_delay == 0.0


class TestRateLimiterEdgeCases:
    """Test edge cases and defensive coding."""

    @pytest.mark.asyncio
    async def test_zero_requests_per_minute_safe(self):
        """Zero requests per minute doesn't crash."""
        from pipeline.rate_limit import RateLimiter

        # Should handle gracefully
        try:
            limiter = RateLimiter(requests_per_minute=0)
            # Attempting to acquire should not crash (might wait indefinitely)
        except Exception as e:
            pytest.fail(f"Should handle 0 rpm gracefully: {e}")

    @pytest.mark.asyncio
    async def test_negative_backoff_safe(self):
        """Negative values are handled safely."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Should not crash with invalid inputs
        limiter.handle_429(retry_after=-10)
        # Should be set to some reasonable value
        assert limiter.current_delay >= 0

    @pytest.mark.asyncio
    async def test_concurrent_acquires(self):
        """Multiple concurrent acquires work correctly."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Run multiple concurrent acquires
        tasks = [limiter.acquire() for _ in range(5)]
        start = time.time()
        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Should complete reasonably (not wait for all delays)
        assert elapsed < 10.0


class TestRateLimitContext:
    """Test rate limiter as context manager (optional feature)."""

    @pytest.mark.asyncio
    async def test_limiter_context_manager(self):
        """Rate limiter can be used as async context manager."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_minute=60)

        # Should work as context manager
        async with limiter:
            # Context manager body
            pass

        # After context, limiter should still be usable
        await limiter.acquire()
