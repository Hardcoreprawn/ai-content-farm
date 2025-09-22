"""
Tests for Simplified Collectors - ACTIVE

CURRENT ARCHITECTURE: Unit tests for simplified collector components
Status: ACTIVE - Core test suite for the new simplified architecture

Clean, simple tests for the new collector architecture.
Tests Reddit and Mastodon collectors, factory patterns, and error handling.

Test Coverage:
- SimpleRedditCollector initialization and collection
- SimpleMastodonCollector initialization and collection
- CollectorFactory creation and management
- Error handling and retry logic
- Content standardization
- Mock-based testing patterns

Clean, simple tests for the new collector architecture.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from collectors.factory import CollectorFactory, collect_from_sources
from collectors.simple_base import CollectorError, RateLimitError
from collectors.simple_mastodon import SimpleMastodonCollector
from collectors.simple_reddit import SimpleRedditCollector


class TestSimpleRedditCollector:
    """Test the simplified Reddit collector."""

    def test_initialization(self):
        """Test collector initialization."""
        config = {
            "subreddits": ["programming", "technology"],
            "max_items": 20,
            "base_delay": 0.1,
        }
        collector = SimpleRedditCollector(config)

        assert collector.get_source_name() == "reddit"
        assert collector.subreddits == ["programming", "technology"]
        assert collector.max_items == 20
        assert collector.base_delay == 0.1

    @pytest.mark.asyncio
    async def test_successful_collection(self, sample_reddit_data):
        """Test successful content collection."""
        collector = SimpleRedditCollector(
            {"subreddits": ["programming"], "max_items": 5, "base_delay": 0.1}
        )

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_reddit_data

            async with collector:
                items = await collector.collect_batch()

            assert len(items) == 2  # Based on sample data

            # Check first item
            item = items[0]
            assert item["id"] == "reddit_test123"
            assert item["title"] == "Test Post"
            assert item["content"] == "This is a test post content"
            assert item["source"] == "reddit"
            assert item["metadata"]["subreddit"] == "programming"
            assert item["metadata"]["score"] == 100

    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self):
        """Test rate limit handling."""
        collector = SimpleRedditCollector(
            # Only one subreddit
            {"subreddits": ["programming"], "base_delay": 0.1}
        )

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = RateLimitError(
                "Rate limited", retry_after=1, source="reddit"
            )

            async with collector:
                # Should return empty list since all requests fail
                items = await collector.collect_batch()
                assert items == []

    def test_standardize_reddit_post(self):
        """Test Reddit post standardization."""
        collector = SimpleRedditCollector()

        reddit_post = {
            "id": "abc123",
            "title": "Test Post Title",
            "selftext": "Post content here",
            "author": "testuser",
            "created_utc": 1640995200,
            "permalink": "/r/programming/comments/abc123/test_post/",
            "url": "https://example.com/external",  # Added missing url field
            "score": 42,
            "num_comments": 5,
            "upvote_ratio": 0.8,
            "over_18": False,
            "spoiler": True,
            "link_flair_text": "Discussion",
        }

        standardized = collector.standardize_reddit_post(reddit_post, "programming")

        assert standardized["id"] == "reddit_abc123"
        assert standardized["title"] == "Test Post Title"
        assert standardized["content"] == "Post content here"
        assert standardized["author"] == "testuser"
        assert standardized["source"] == "reddit"
        assert standardized["metadata"]["subreddit"] == "programming"
        assert standardized["metadata"]["score"] == 42
        assert standardized["metadata"]["spoiler"] is True


class TestSimpleMastodonCollector:
    """Test the simplified Mastodon collector."""

    def test_initialization(self):
        """Test collector initialization."""
        config = {
            "instances": ["mastodon.social"],
            "hashtags": ["technology"],
            "max_items": 15,
            "base_delay": 0.2,
        }
        collector = SimpleMastodonCollector(config)

        assert collector.get_source_name() == "mastodon"
        assert collector.instances == ["mastodon.social"]
        assert collector.hashtags == ["technology"]
        assert collector.max_items == 15
        assert collector.base_delay == 0.2

    @pytest.mark.asyncio
    async def test_successful_collection(self, sample_mastodon_data):
        """Test successful Mastodon content collection."""
        collector = SimpleMastodonCollector(
            {
                "instances": ["mastodon.social"],
                "hashtags": ["technology"],
                "max_items": 5,
                "base_delay": 0.1,
            }
        )

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_mastodon_data

            async with collector:
                items = await collector.collect_batch()

            assert len(items) == 1  # Based on sample data

            # Check item
            item = items[0]
            assert item["id"] == "mastodon_mastodon.social_post123"
            assert item["content"] == "This is a test post about #technology"
            assert item["source"] == "mastodon"
            assert item["metadata"]["instance"] == "mastodon.social"

    def test_html_stripping(self):
        """Test HTML content stripping."""
        collector = SimpleMastodonCollector()

        html_content = '<p>This is <strong>bold</strong> text with a <a href="https://example.com">link</a>.</p>'
        stripped = collector._strip_html(html_content)

        assert stripped == "This is bold text with a link."

    def test_standardize_mastodon_post(self):
        """Test Mastodon post standardization."""
        collector = SimpleMastodonCollector()

        mastodon_post = {
            "id": "post456",
            "content": "<p>Hello <strong>world</strong>!</p>",
            "created_at": "2022-01-01T12:00:00Z",
            "url": "https://mastodon.social/@user/post456",
            "account": {
                "username": "testuser",
                "display_name": "Test User",
                "url": "https://mastodon.social/@testuser",
            },
            "favourites_count": 10,
            "reblogs_count": 5,
            "replies_count": 2,
            "tags": [{"name": "test"}],
            "sensitive": False,
            "visibility": "public",
        }

        standardized = collector.standardize_mastodon_post(
            mastodon_post, "mastodon.social", "#test"
        )

        assert standardized["id"] == "mastodon_mastodon.social_post456"
        assert standardized["content"] == "Hello world!"
        assert standardized["author"] == "Test User"
        assert standardized["source"] == "mastodon"
        assert standardized["metadata"]["instance"] == "mastodon.social"
        assert standardized["metadata"]["username"] == "testuser"


class TestCollectorFactory:
    """Test the collector factory."""

    def test_create_reddit_collector(self):
        """Test creating Reddit collector."""
        collector = CollectorFactory.create_collector("reddit")
        assert isinstance(collector, SimpleRedditCollector)
        assert collector.get_source_name() == "reddit"

    def test_create_mastodon_collector(self):
        """Test creating Mastodon collector."""
        collector = CollectorFactory.create_collector("mastodon")
        assert isinstance(collector, SimpleMastodonCollector)
        assert collector.get_source_name() == "mastodon"

    def test_invalid_collector_type(self):
        """Test error on invalid collector type."""
        with pytest.raises(ValueError, match="Unknown collector type"):
            CollectorFactory.create_collector("invalid_type")

    def test_get_available_sources(self):
        """Test getting available source types."""
        sources = CollectorFactory.get_available_sources()
        assert "reddit" in sources
        assert "mastodon" in sources

    @pytest.mark.asyncio
    async def test_collect_from_sources(self):
        """Test collecting from multiple sources."""

        with patch("collectors.factory.create_collector") as mock_create:
            # Mock collectors
            reddit_collector = Mock()
            reddit_collector.__aenter__ = AsyncMock(return_value=reddit_collector)
            reddit_collector.__aexit__ = AsyncMock(return_value=None)
            reddit_collector.collect_with_retry = AsyncMock(
                return_value=[{"id": "reddit_1", "title": "Reddit Post"}]
            )

            mastodon_collector = Mock()
            mastodon_collector.__aenter__ = AsyncMock(return_value=mastodon_collector)
            mastodon_collector.__aexit__ = AsyncMock(return_value=None)
            mastodon_collector.collect_with_retry = AsyncMock(
                return_value=[{"id": "mastodon_1", "title": "Mastodon Post"}]
            )

            mock_create.side_effect = [reddit_collector, mastodon_collector]

            results = await collect_from_sources(["reddit", "mastodon"])

            assert "reddit" in results
            assert "mastodon" in results
            assert len(results["reddit"]) == 1
            assert len(results["mastodon"]) == 1
            assert results["reddit"][0]["id"] == "reddit_1"
            assert results["mastodon"][0]["id"] == "mastodon_1"


class TestErrorHandling:
    """Test error handling in collectors."""

    @pytest.mark.asyncio
    async def test_collector_error_handling(self):
        """Test generic collector error handling."""
        collector = SimpleRedditCollector(
            {
                "subreddits": ["programming"],  # Only one subreddit
                "max_retries": 1,
                "base_delay": 0.1,
            }
        )

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = CollectorError(
                "Generic error", source="reddit", retryable=False
            )

            async with collector:
                # Should return empty list since all requests fail
                items = await collector.collect_batch()
                assert items == []

    @pytest.mark.asyncio
    async def test_retry_logic(self):
        """Test retry logic with temporary failures."""
        collector = SimpleRedditCollector({"max_retries": 2, "base_delay": 0.1})

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            # First call fails, second succeeds
            mock_get.side_effect = [
                CollectorError("Temporary error", source="reddit", retryable=True),
                {"data": {"children": []}},
            ]

            async with collector:
                items = await collector.collect_batch()
                assert items == []  # Empty but successful
                assert mock_get.call_count == 2  # Retried once
