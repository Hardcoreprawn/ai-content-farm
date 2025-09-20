"""
Test Mastodon Collector

Tests for Mastodon content collection with adaptive strategy.
Maps to: collectors/mastodon.py
"""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from collectors.mastodon import MastodonCollectionStrategy, MastodonCollector

# Add paths for container testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@pytest.mark.unit
class TestMastodonCollector:
    """Test Mastodon collector functionality."""

    @pytest.fixture
    def mock_storage(self):
        """Mock metrics storage."""
        with patch("collectors.adaptive_strategy.get_metrics_storage") as mock:
            storage = MagicMock()
            storage.save_strategy_metrics = AsyncMock(return_value=True)
            storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock.return_value = storage
            yield storage

    @pytest.fixture
    def mastodon_collector(self, mock_storage):
        """Create Mastodon collector with mocked dependencies."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock HTTP client to prevent network calls
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "title": "Test Instance",
                "version": "4.0.0",
            }
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            collector = MastodonCollector()
            yield collector

    def test_mastodon_strategy_initialization(self, mastodon_collector):
        """Test Mastodon collector initializes with correct strategy."""
        assert mastodon_collector.get_source_name() == "mastodon"
        assert isinstance(
            mastodon_collector.adaptive_strategy, MastodonCollectionStrategy
        )
        assert mastodon_collector.adaptive_strategy.source_name == "mastodon"

        # Check Mastodon-specific parameters
        params = mastodon_collector.adaptive_strategy.params
        assert params.base_delay == 1.5  # More lenient than Reddit
        assert params.max_requests_per_window == 100  # More generous
        assert params.window_duration == 300  # 5-minute windows

    @pytest.mark.asyncio
    async def test_mastodon_public_timeline_collection(self, mastodon_collector):
        """Test collecting from Mastodon public timeline."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock successful Mastodon response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": "123",
                    "content": "This is a test post from Mastodon with interesting content",
                    "url": "https://mastodon.social/@user/123",
                    "created_at": "2025-09-20T12:00:00Z",
                    "account": {
                        "username": "testuser",
                        "display_name": "Test User",
                        "url": "https://mastodon.social/@testuser",
                        "followers_count": 100,
                    },
                    "replies_count": 5,
                    "reblogs_count": 10,
                    "favourites_count": 15,
                    "tags": [{"name": "technology"}],
                    "media_attachments": [],
                    "visibility": "public",
                }
            ]
            mock_response.raise_for_status = Mock()
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await mastodon_collector.collect_content_adaptive(
                {"type": "public_timeline", "limit": 5}
            )

            assert result is not None
            assert len(result) > 0

            post = result[0]
            assert post["source"] == "mastodon"
            assert (
                post["content"]
                == "This is a test post from Mastodon with interesting content"
            )
            assert post["author"]["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_mastodon_hashtag_collection(self, mastodon_collector):
        """Test collecting from Mastodon hashtags."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock successful hashtag response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": "456",
                    "content": "Great discussion about #technology and #programming in the fediverse",
                    "url": "https://mastodon.social/@dev/456",
                    "created_at": "2025-09-20T12:30:00Z",
                    "account": {
                        "username": "developer",
                        "display_name": "Tech Developer",
                        "url": "https://mastodon.social/@developer",
                    },
                    "tags": [{"name": "technology"}, {"name": "programming"}],
                    "media_attachments": [],
                    "visibility": "public",
                }
            ]
            mock_response.raise_for_status = Mock()
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await mastodon_collector.collect_content_adaptive(
                {"type": "hashtags", "hashtags": ["technology"], "limit": 5}
            )

            assert result is not None
            assert len(result) > 0

            post = result[0]
            assert post["source"] == "mastodon"
            assert "technology" in post["content"]
            assert post["source_hashtag"] == "technology"

    @pytest.mark.asyncio
    async def test_mastodon_trends_collection(self, mastodon_collector):
        """Test collecting trending topics from Mastodon."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock successful trends response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "name": "OpenSource",
                    "url": "https://mastodon.social/tags/opensource",
                    "history": [{"day": "1695168000", "uses": "42", "accounts": "25"}],
                },
                {
                    "name": "Privacy",
                    "url": "https://mastodon.social/tags/privacy",
                    "history": [{"day": "1695168000", "uses": "38", "accounts": "22"}],
                },
            ]
            mock_response.raise_for_status = Mock()
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await mastodon_collector.collect_content_adaptive(
                {"type": "trends"}
            )

            assert result is not None
            assert len(result) == 2

            trend = result[0]
            assert trend["type"] == "trend"
            assert trend["name"] == "OpenSource"
            assert trend["source"] == "mastodon"

    @pytest.mark.asyncio
    async def test_mastodon_connectivity_check(self, mastodon_collector):
        """Test Mastodon instance connectivity check."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock successful instance info response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "title": "Mastodon.social",
                "version": "4.2.0",
                "description": "The original server operated by the Mastodon gGmbH non-profit",
            }
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            is_connected, message = await mastodon_collector.check_connectivity()

            assert is_connected is True
            assert "Mastodon.social" in message

    @pytest.mark.asyncio
    async def test_mastodon_strategy_parameters(self, mastodon_collector):
        """Test that Mastodon has appropriate strategy parameters."""
        strategy = mastodon_collector.adaptive_strategy
        params = strategy.params

        # Mastodon should be more lenient than Reddit but not too aggressive
        assert params.base_delay == 1.5
        assert params.min_delay == 1.0
        assert params.max_delay == 300.0
        assert params.max_requests_per_window == 100  # More generous than Reddit
        assert params.window_duration == 300  # 5-minute windows

        # Check collection parameters
        collection_params = await strategy.get_collection_parameters()
        assert collection_params["max_items"] == 40  # Mastodon API limit
        assert "hashtags" in collection_params
        assert "technology" in collection_params["hashtags"]


@pytest.mark.unit
class TestMastodonCollectionStrategy:
    """Test Mastodon-specific adaptive strategy."""

    @pytest.mark.asyncio
    async def test_mastodon_strategy_creation(self):
        """Test creating Mastodon strategy."""
        strategy = MastodonCollectionStrategy()

        assert strategy.source_name == "mastodon"
        assert strategy.params.base_delay == 1.5
        assert strategy.params.max_requests_per_window == 100

        # Test collection parameters
        params = await strategy.get_collection_parameters()
        assert params["max_items"] == 40
        assert "types" in params
        assert "public_timeline" in params["types"]

    def test_mastodon_strategy_with_custom_source_name(self):
        """Test creating Mastodon strategy with custom source name."""
        strategy = MastodonCollectionStrategy(source_name="mastodon_custom")

        assert strategy.source_name == "mastodon_custom"
        # Should still have Mastodon parameters
        assert strategy.params.base_delay == 1.5


@pytest.mark.integration
class TestMastodonAdaptiveIntegration:
    """Test Mastodon collector integration with adaptive collection."""

    @pytest.fixture
    def mock_storage(self):
        """Mock storage for integration tests."""
        with patch("collectors.adaptive_strategy.get_metrics_storage") as mock:
            storage = MagicMock()
            storage.save_strategy_metrics = AsyncMock(return_value=True)
            storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock.return_value = storage
            yield storage

    @pytest.mark.asyncio
    async def test_mastodon_adaptive_collection_workflow(self, mock_storage):
        """Test complete adaptive collection workflow with Mastodon."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock successful responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    "id": "test123",
                    "content": "Mastodon is great for decentralized social media discussions",
                    "url": "https://mastodon.social/@user/test123",
                    "created_at": "2025-09-20T12:00:00Z",
                    "account": {"username": "testuser", "display_name": "Test User"},
                    "tags": [],
                    "media_attachments": [],
                    "visibility": "public",
                }
            ]
            mock_response.raise_for_status = Mock()
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            collector = MastodonCollector()

            # Test that strategy is properly configured
            assert isinstance(collector.adaptive_strategy, MastodonCollectionStrategy)

            # Test adaptive collection
            result = await collector.collect_content_adaptive(
                {"type": "public_timeline", "limit": 1}
            )

            assert result is not None
            assert len(result) > 0

            # Verify metrics were updated
            metrics = collector.adaptive_strategy.session_metrics
            assert metrics.request_count > 0
            assert metrics.source_name == "mastodon"
