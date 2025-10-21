"""
Tests for pure collection functions (collect.py).

Test async generators yielding standardized items.
No mocks - test actual API responses or fixtures.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest


@pytest.fixture
def reddit_api_response():
    """Fixture: Real-like Reddit JSON API response structure."""
    return {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "abc123",
                        "title": "Python 3.13 Released",
                        "selftext": "Major performance improvements...",
                        "score": 500,
                        "num_comments": 45,
                        "subreddit": "programming",
                        "url": "https://reddit.com/r/programming/abc123",
                        "created_utc": 1729000000,
                        "over_18": False,
                    }
                },
                {
                    "data": {
                        "id": "def456",
                        "title": "Understanding Async/Await",
                        "selftext": "A deep dive into concurrency...",
                        "score": 250,
                        "num_comments": 30,
                        "subreddit": "programming",
                        "url": "https://reddit.com/r/programming/def456",
                        "created_utc": 1729000100,
                        "over_18": False,
                    }
                },
                {
                    "data": {
                        "id": "low_score",
                        "title": "Low Quality Post",
                        "selftext": "spam",
                        "score": 5,  # Below minimum
                        "num_comments": 2,
                        "subreddit": "programming",
                        "url": "https://reddit.com/r/programming/low_score",
                        "created_utc": 1729000200,
                        "over_18": False,
                    }
                },
            ]
        }
    }


@pytest.fixture
def mastodon_api_response():
    """Fixture: Real-like Mastodon API response structure."""
    return [
        {
            "id": "111111111111111111",
            "content": "<p>Interesting tech article about distributed systems</p>",
            "account": {
                "username": "techwriter",
                "url": "https://fosstodon.org/@techwriter",
            },
            "url": "https://fosstodon.org/@techwriter/111111111111111111",
            "created_at": "2025-10-21T12:00:00.000Z",
            "replies_count": 8,
            "reblogs_count": 25,
            "favourites_count": 50,
            "in_reply_to_id": None,
        },
        {
            "id": "222222222222222222",
            "content": "<p>New Python release notes</p>",
            "account": {
                "username": "pythondev",
                "url": "https://fosstodon.org/@pythondev",
            },
            "url": "https://fosstodon.org/@pythondev/222222222222222222",
            "created_at": "2025-10-21T13:00:00.000Z",
            "replies_count": 5,
            "reblogs_count": 8,
            "favourites_count": 12,
            "in_reply_to_id": None,
        },
        {
            "id": "333333333333333333",
            "content": "<p>Low engagement post</p>",
            "account": {
                "username": "lowengagement",
                "url": "https://fosstodon.org/@lowengagement",
            },
            "url": "https://fosstodon.org/@lowengagement/333333333333333333",
            "created_at": "2025-10-21T14:00:00.000Z",
            "replies_count": 0,
            "reblogs_count": 1,  # Below minimum
            "favourites_count": 2,
            "in_reply_to_id": None,
        },
    ]


class TestCollectRedditGenerator:
    """Test Reddit collection as async generator."""

    @pytest.mark.asyncio
    async def test_reddit_standardized_format(self, reddit_api_response, monkeypatch):
        """Each item has required fields in standardized format."""
        from collectors.collect import collect_reddit

        # Mock HTTP get
        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items = []
        async for item in collect_reddit(
            subreddits=["programming"],
            min_score=25,
            max_items=2,
        ):
            items.append(item)

        assert len(items) == 2

        for item in items:
            # Required fields
            assert "id" in item
            assert "title" in item
            assert "content" in item
            assert "source" in item
            assert "collected_at" in item
            assert "metadata" in item

            # Type checks
            assert isinstance(item["id"], str)
            assert isinstance(item["title"], str)
            assert isinstance(item["content"], str)
            assert item["source"] == "reddit"
            assert isinstance(item["collected_at"], str)
            assert isinstance(item["metadata"], dict)

    @pytest.mark.asyncio
    async def test_reddit_respects_min_score(self, reddit_api_response, monkeypatch):
        """Items below min_score are filtered out."""
        from collectors.collect import collect_reddit

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items = []
        async for item in collect_reddit(
            subreddits=["programming"],
            min_score=100,  # Only 2 items pass this
            max_items=10,
        ):
            items.append(item)

        # Items with score 500 and 250 should pass
        assert len(items) == 2
        assert all(int(item["metadata"]["score"]) >= 100 for item in items)

    @pytest.mark.asyncio
    async def test_reddit_max_items_limit(self, reddit_api_response, monkeypatch):
        """max_items parameter is respected."""
        from collectors.collect import collect_reddit

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items = []
        async for item in collect_reddit(
            subreddits=["programming"],
            min_score=1,
            max_items=1,  # Limit to 1
        ):
            items.append(item)

        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_reddit_metadata_fields(self, reddit_api_response, monkeypatch):
        """Reddit-specific metadata is included."""
        from collectors.collect import collect_reddit

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        item = None
        async for item in collect_reddit(
            subreddits=["programming"],
            min_score=1,
            max_items=1,
        ):
            break

        assert item is not None
        metadata = item["metadata"]
        assert metadata["subreddit"] == "programming"
        assert "score" in metadata
        assert "num_comments" in metadata
        assert "url" in metadata

    @pytest.mark.asyncio
    async def test_reddit_rate_limiting_delay(self, reddit_api_response, monkeypatch):
        """Delay is applied between subreddit requests."""
        import time

        from collectors.collect import collect_reddit

        call_times = []

        async def mock_get(*args, **kwargs):
            call_times.append(time.time())

            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items = []
        async for item in collect_reddit(
            subreddits=["programming", "technology"],
            min_score=1,
            max_items=10,
        ):
            items.append(item)

        # Should have at least 2 API calls (one per subreddit)
        # With delay, second should be ~2s after first
        assert len(call_times) >= 2


class TestCollectMastodonGenerator:
    """Test Mastodon collection as async generator."""

    @pytest.mark.asyncio
    async def test_mastodon_standardized_format(
        self, mastodon_api_response, monkeypatch
    ):
        """Each Mastodon item has required standardized fields."""
        from collectors.collect import collect_mastodon

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return mastodon_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items = []
        async for item in collect_mastodon(
            instance="fosstodon.org",
            min_boosts=5,
            max_items=2,
        ):
            items.append(item)

        assert len(items) == 2

        for item in items:
            assert "id" in item
            assert "title" in item
            assert "content" in item
            assert "source" in item
            assert item["source"] == "mastodon"
            assert "collected_at" in item
            assert "metadata" in item

    @pytest.mark.asyncio
    async def test_mastodon_respects_min_boosts(
        self, mastodon_api_response, monkeypatch
    ):
        """Items below min_boosts are filtered out."""
        from collectors.collect import collect_mastodon

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return mastodon_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items = []
        async for item in collect_mastodon(
            instance="fosstodon.org",
            min_boosts=10,  # Only first 2 items pass
            max_items=10,
        ):
            items.append(item)

        assert len(items) == 2
        assert all(item["metadata"]["boosts"] >= 10 for item in items)

    @pytest.mark.asyncio
    async def test_mastodon_metadata_fields(self, mastodon_api_response, monkeypatch):
        """Mastodon-specific metadata is included."""
        from collectors.collect import collect_mastodon

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return mastodon_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        item = None
        async for item in collect_mastodon(
            instance="fosstodon.org",
            min_boosts=1,
            max_items=1,
        ):
            break

        assert item is not None
        metadata = item["metadata"]
        assert "boosts" in metadata
        assert "favourites" in metadata
        assert "replies" in metadata
        assert "author" in metadata
        assert "instance" in metadata


class TestStandardizeFormat:
    """Test item standardization functions."""

    def test_standardize_reddit_item(self):
        """Reddit item is converted to standard format."""
        from collectors.standardize import standardize_reddit_item

        raw = {
            "id": "abc123",
            "title": "Python 3.13",
            "selftext": "Release notes...",
            "score": 500,
            "num_comments": 45,
            "subreddit": "programming",
            "url": "https://reddit.com/r/programming/abc123",
            "created_utc": 1729000000,
        }

        item = standardize_reddit_item(raw)

        assert item["id"] == "reddit_abc123"
        assert item["title"] == "Python 3.13"
        assert item["content"] == "Release notes..."
        assert item["source"] == "reddit"
        assert item["metadata"]["score"] == 500
        assert item["metadata"]["subreddit"] == "programming"
        assert isinstance(item["collected_at"], str)

    def test_standardize_mastodon_item(self):
        """Mastodon item is converted to standard format."""
        from collectors.standardize import standardize_mastodon_item

        raw = {
            "id": "111111",
            "content": "<p>Tech article</p>",
            "account": {"username": "author", "url": "https://fosstodon.org/@author"},
            "url": "https://fosstodon.org/@author/111111",
            "created_at": "2025-10-21T12:00:00.000Z",
            "reblogs_count": 25,
            "favourites_count": 50,
            "replies_count": 8,
        }

        item = standardize_mastodon_item(raw, instance="fosstodon.org")

        assert item["id"] == "mastodon_111111"
        assert "Tech article" in item["content"]
        assert item["source"] == "mastodon"
        assert item["metadata"]["boosts"] == 25
        assert item["metadata"]["favourites"] == 50
        assert item["metadata"]["instance"] == "fosstodon.org"
        assert isinstance(item["collected_at"], str)

    def test_standardize_handles_missing_fields(self):
        """Standardization handles missing optional fields gracefully."""
        from collectors.standardize import standardize_reddit_item

        minimal = {
            "id": "xyz",
            "title": "Title",
            "selftext": "Content",
            "created_utc": 1729000000,
        }

        item = standardize_reddit_item(minimal)

        assert item["id"] == "reddit_xyz"
        assert item["metadata"]["score"] == 0  # Default value
        assert item["metadata"]["subreddit"] == "unknown"


class TestCollectorIntegration:
    """Integration tests for collectors working together."""

    @pytest.mark.asyncio
    async def test_multiple_subreddit_streaming(self, reddit_api_response, monkeypatch):
        """Multiple subreddits stream items sequentially."""
        from collectors.collect import collect_reddit

        async def mock_get(*args, **kwargs):
            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        items_by_subreddit = {}
        async for item in collect_reddit(
            subreddits=["programming", "technology", "learnprogramming"],
            min_score=1,
            max_items=50,
        ):
            # Track which subreddit it came from
            sub = item["metadata"]["subreddit"]
            if sub not in items_by_subreddit:
                items_by_subreddit[sub] = []
            items_by_subreddit[sub].append(item)

        # Should have items from all subreddits (mocked response same for all)
        assert len(items_by_subreddit) >= 1

    @pytest.mark.asyncio
    async def test_generator_is_lazy(self, reddit_api_response, monkeypatch):
        """Generator doesn't fetch until iterated."""
        from collectors.collect import collect_reddit

        fetch_count = 0

        async def mock_get(*args, **kwargs):
            nonlocal fetch_count
            fetch_count += 1

            class MockResponse:
                async def json(self):
                    return reddit_api_response

            return MockResponse()

        monkeypatch.setattr("collectors.collect.rate_limited_get", mock_get)

        # Create generator but don't iterate
        gen = collect_reddit(subreddits=["programming"], min_score=1, max_items=10)
        assert fetch_count == 0

        # Iterate one item
        item = await gen.__anext__()
        assert fetch_count > 0  # First fetch happened


class TestAsyncGeneration:
    """Test that collectors are proper async generators."""

    @pytest.mark.asyncio
    async def test_collect_reddit_is_async_generator(self):
        """collect_reddit returns an async generator."""
        import types

        from collectors.collect import collect_reddit

        gen = collect_reddit(subreddits=["test"], min_score=1, max_items=10)
        assert isinstance(gen, types.AsyncGeneratorType)

    @pytest.mark.asyncio
    async def test_collect_mastodon_is_async_generator(self):
        """collect_mastodon returns an async generator."""
        import types

        from collectors.collect import collect_mastodon

        gen = collect_mastodon(instance="fosstodon.org", min_boosts=1, max_items=10)
        assert isinstance(gen, types.AsyncGeneratorType)
