"""
Additional Tests to Improve Coverage on Critical Areas - ACTIVE

CURRENT ARCHITECTURE: Coverage-focused tests for simplified collectors
Status: ACTIVE - Ensures comprehensive test coverage

Additional tests to improve coverage on critical areas.
Focuses on edge cases, error handling, and health checks.

Test Coverage:
- Health check functionality for all collectors
- HTTP error handling (401, 500, 400, etc.)
- Edge cases (empty responses, malformed data)
- Factory configuration handling
- Base collector functionality
- Error scenarios and retry logic

Additional tests to improve coverage on critical areas.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from collectors.factory import CollectorFactory
from collectors.simple_base import CollectorError, HTTPCollector, RateLimitError
from collectors.simple_mastodon import SimpleMastodonCollector
from collectors.simple_reddit import SimpleRedditCollector


class TestHealthChecks:
    """Test health check functionality that was missing coverage."""

    @pytest.mark.asyncio
    async def test_reddit_health_check_success(self):
        """Test Reddit health check when API is accessible."""
        collector = SimpleRedditCollector()

        mock_response = {"data": {"children": [{"data": {"id": "test"}}]}}

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                is_healthy, message = await collector.health_check()

            assert is_healthy is True
            assert "Reddit API accessible" in message

    @pytest.mark.asyncio
    async def test_reddit_health_check_failure(self):
        """Test Reddit health check when API fails."""
        collector = SimpleRedditCollector()

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            async with collector:
                is_healthy, message = await collector.health_check()

            assert is_healthy is False
            assert "health check failed" in message

    @pytest.mark.asyncio
    async def test_mastodon_health_check_success(self):
        """Test Mastodon health check when instance is accessible."""
        collector = SimpleMastodonCollector()

        mock_response = {"title": "Test Instance"}

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                is_healthy, message = await collector.health_check()

            assert is_healthy is True
            assert "accessible" in message

    @pytest.mark.asyncio
    async def test_mastodon_health_check_failure(self):
        """Test Mastodon health check when instance fails."""
        collector = SimpleMastodonCollector()

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Instance down")

            async with collector:
                is_healthy, message = await collector.health_check()

            assert is_healthy is False
            assert "health check failed" in message


class TestHTTPErrorHandling:
    """Test HTTP error handling that was missing coverage."""

    @pytest.mark.asyncio
    async def test_http_401_error(self):
        """Test handling of 401 authentication errors."""
        collector = SimpleRedditCollector()

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch.object(collector.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                with pytest.raises(CollectorError) as exc_info:
                    await collector.get_json("https://test.com")

                assert exc_info.value.retryable is False
                assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_500_error(self):
        """Test handling of 500 server errors (retryable)."""
        collector = SimpleRedditCollector()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(collector.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                with pytest.raises(CollectorError) as exc_info:
                    await collector.get_json("https://test.com")

                assert exc_info.value.retryable is True
                assert "HTTP 500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_400_error(self):
        """Test handling of 400 client errors (non-retryable)."""
        collector = SimpleRedditCollector()

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch.object(collector.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                with pytest.raises(CollectorError) as exc_info:
                    await collector.get_json("https://test.com")

                assert exc_info.value.retryable is False
                assert "HTTP 400" in str(exc_info.value)


class TestEdgeCases:
    """Test edge cases that were missing coverage."""

    @pytest.mark.asyncio
    async def test_reddit_empty_response(self):
        """Test Reddit collector with empty response."""
        collector = SimpleRedditCollector()

        mock_response = {"data": {"children": []}}

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                items = await collector.collect_batch()

            assert items == []

    @pytest.mark.asyncio
    async def test_mastodon_empty_response(self):
        """Test Mastodon collector with empty response."""
        collector = SimpleMastodonCollector()

        mock_response = []

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                items = await collector.collect_batch()

            assert items == []

    @pytest.mark.asyncio
    async def test_reddit_malformed_response(self):
        """Test Reddit collector with malformed response."""
        collector = SimpleRedditCollector()

        mock_response = {"invalid": "structure"}

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                # Should return empty list but continue gracefully
                items = await collector.collect_batch()
                assert items == []

    @pytest.mark.asyncio
    async def test_mastodon_malformed_response(self):
        """Test Mastodon collector with malformed response."""
        collector = SimpleMastodonCollector()

        mock_response = {"not": "a list"}

        with patch.object(collector, "get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            async with collector:
                # Should return empty list but continue gracefully
                items = await collector.collect_batch()
                assert items == []

    def test_factory_create_collectors_from_config(self):
        """Test factory creating collectors from config (missing coverage)."""
        config = {
            "sources": [
                {"type": "reddit", "subreddits": ["programming"]},
                {"type": "mastodon", "instances": ["mastodon.social"]},
                {"type": "invalid_type"},  # Should be skipped
                {},  # Missing type, should be skipped
            ]
        }

        collectors = CollectorFactory.create_collectors_from_config(config)

        # Should create 2 collectors (reddit and mastodon), skip invalid ones
        assert len(collectors) == 2
        assert any(c.get_source_name() == "reddit" for c in collectors)
        assert any(c.get_source_name() == "mastodon" for c in collectors)


class TestBaseCollectorFunctionality:
    """Test base collector functionality that was missing coverage."""

    @pytest.mark.asyncio
    async def test_base_health_check_default(self):
        """Test default health check implementation."""
        from collectors.simple_base import SimpleCollector

        class TestCollector(SimpleCollector):
            def get_source_name(self):
                return "test"

            async def collect_batch(self, **kwargs):
                return [{"test": "item"}]

        collector = TestCollector()
        is_healthy, message = await collector.health_check()

        assert is_healthy is True
        assert "test is accessible" in message

    @pytest.mark.asyncio
    async def test_standardize_item_default(self):
        """Test default item standardization."""
        from collectors.simple_base import SimpleCollector

        class TestCollector(SimpleCollector):
            def get_source_name(self):
                return "test"

            async def collect_batch(self, **kwargs):
                return []

        collector = TestCollector()
        raw_item = {
            "id": "test123",
            "title": "Test Title",
            "content": "Test Content",
            "author": "Test Author",
        }

        standardized = collector.standardize_item(raw_item)

        assert standardized["id"] == "test123"
        assert standardized["title"] == "Test Title"
        assert standardized["source"] == "test"
        assert "created_at" in standardized
        assert "metadata" in standardized
