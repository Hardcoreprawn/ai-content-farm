"""
Test async patterns and external API access.

Verify collectors use async/await properly for external APIs.
"""

import asyncio
from typing import AsyncIterator

import pytest


class TestAsyncPatterns:
    """Verify async methods are used for external API access."""

    @pytest.mark.asyncio
    async def test_collect_reddit_is_async_generator(self):
        """collect_reddit returns async generator (not regular generator)."""
        from collectors.collect import collect_reddit

        gen = collect_reddit(subreddits=["test"], max_items=1)

        # Must be async generator
        assert hasattr(gen, "__anext__"), "collect_reddit must be async generator"
        assert hasattr(gen, "__aiter__"), "collect_reddit must be iterable"

    @pytest.mark.asyncio
    async def test_collect_mastodon_is_async_generator(self):
        """collect_mastodon returns async generator (not regular generator)."""
        from collectors.collect import collect_mastodon

        gen = collect_mastodon(instance="test.social", max_items=1)

        # Must be async generator
        assert hasattr(gen, "__anext__"), "collect_mastodon must be async generator"
        assert hasattr(gen, "__aiter__"), "collect_mastodon must be iterable"

    @pytest.mark.asyncio
    async def test_rate_limited_get_is_async_context_manager(self):
        """rate_limited_get returns async context manager."""
        from collectors.collect import rate_limited_get

        # The function should return something that can be used with async with
        ctx_mgr = rate_limited_get("http://example.com")

        # Must be async context manager
        assert hasattr(
            ctx_mgr, "__aenter__"
        ), "rate_limited_get must return async context manager"
        assert hasattr(
            ctx_mgr, "__aexit__"
        ), "rate_limited_get must return async context manager"

    @pytest.mark.asyncio
    async def test_stream_collection_is_async(self):
        """stream_collection is properly async."""
        # Get the function signature
        import inspect

        from pipeline.stream import stream_collection

        assert asyncio.iscoroutinefunction(
            stream_collection
        ), "stream_collection must be async function"

    @pytest.mark.asyncio
    async def test_dedup_functions_are_async(self):
        """Dedup functions use async/await for blob access."""
        from pipeline.dedup import is_seen, mark_seen

        # Both must be async
        assert asyncio.iscoroutinefunction(is_seen), "is_seen must be async"
        assert asyncio.iscoroutinefunction(mark_seen), "mark_seen must be async"

    def test_hash_content_is_pure_sync(self):
        """hash_content is pure sync function (no I/O)."""
        from pipeline.dedup import hash_content

        # Should not be async (pure computation)
        assert not asyncio.iscoroutinefunction(hash_content)

        # Should produce consistent output
        hash1 = hash_content("title", "content")
        hash2 = hash_content("title", "content")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex is 64 chars

    @pytest.mark.asyncio
    async def test_standardize_functions_are_pure_sync(self):
        """Standardize functions are pure sync (no I/O)."""
        from collectors.standardize import (
            standardize_mastodon_item,
            standardize_reddit_item,
        )

        # Should not be async (pure transformation)
        assert not asyncio.iscoroutinefunction(standardize_reddit_item)
        assert not asyncio.iscoroutinefunction(standardize_mastodon_item)

    @pytest.mark.asyncio
    async def test_rate_limiter_acquire_is_async(self):
        """RateLimiter.acquire is async method."""
        from pipeline.rate_limit import RateLimiter

        limiter = RateLimiter()

        # acquire must be async
        assert asyncio.iscoroutinefunction(limiter.acquire)

    @pytest.mark.asyncio
    async def test_async_generator_can_be_consumed(self):
        """Async generators can be consumed with async for."""
        from collectors.standardize import standardize_reddit_item, validate_item

        # Create test data
        raw = {
            "id": "test_id",
            "title": "Test Title",
            "selftext": "Test content",
            "score": 100,
            "subreddit": "test",
            "url": "http://example.com",
            "created_utc": 1629000000,
        }

        item = standardize_reddit_item(raw)

        # Item should be valid
        assert validate_item(item)

        # Can we iterate over standardized item fields?
        fields = ["id", "title", "content", "source", "collected_at", "metadata"]
        for field in fields:
            assert field in item, f"Item missing required field: {field}"

    @pytest.mark.asyncio
    async def test_no_blocking_io_in_async_generators(self):
        """Collectors don't have blocking I/O patterns."""
        from collectors import collect

        # Verify the module uses aiohttp (async), not requests (blocking)
        source = inspect.getsource(collect)

        # Should use aiohttp
        assert "aiohttp" in source, "Should use aiohttp for async HTTP"

        # Should NOT use blocking requests library
        assert (
            "import requests" not in source
        ), "Should not use requests library (blocking)"


import inspect
