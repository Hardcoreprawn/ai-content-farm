"""
Test Adaptive Collection Integration

Tests for adaptive collection framework integrated with existing collectors.
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, Mock, patch

import pytest
from collectors.adaptive_strategy import SourceHealth
from collectors.reddit import RedditPRAWCollector, RedditPublicCollector
from collectors.web import WebContentCollector

# Add the collectors directory to Python path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAdaptiveCollectionIntegration:
    """Test adaptive collection framework integration with collectors."""

    @pytest.fixture
    def reddit_public_collector(self):
        """Create Reddit public collector."""
        with patch("httpx.AsyncClient") as mock_httpx:
            # Mock HTTP client to prevent network calls
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"children": []}}
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            return RedditPublicCollector({"test": True})

    @pytest.fixture
    def reddit_praw_collector(self):
        """Create Reddit PRAW collector."""
        with (
            patch(
                "collectors.reddit.get_reddit_credentials_with_fallback"
            ) as mock_creds,
            patch("praw.Reddit") as mock_reddit,
            patch("httpx.AsyncClient") as mock_httpx,
        ):

            mock_creds.return_value = {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "user_agent": "test_agent",
            }

            # Mock network calls to prevent slow initialization
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "test_token",
                "token_type": "bearer",
            }
            mock_httpx.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            return RedditPRAWCollector({"test": True})

    @pytest.fixture
    def web_collector(self):
        """Create web content collector."""
        with patch("aiohttp.ClientSession") as mock_session:
            # Mock aiohttp to prevent network calls
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text.return_value = "<html>Test</html>"
            mock_response.headers = {"content-type": "text/html"}
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            return WebContentCollector({"test": True})

    def test_collector_initialization_with_adaptive_strategy(
        self, reddit_public_collector
    ):
        """Test that collectors are initialized with adaptive strategies."""
        assert reddit_public_collector.adaptive_strategy is not None
        assert reddit_public_collector.get_source_name() == "reddit_public"
        assert reddit_public_collector.get_health_status() == SourceHealth.HEALTHY
        assert reddit_public_collector.get_current_delay() > 0

    def test_different_source_strategies(self, reddit_public_collector, web_collector):
        """Test that different sources have different strategy parameters."""
        reddit_params = reddit_public_collector.adaptive_strategy.params
        web_params = web_collector.adaptive_strategy.params

        # Reddit should be more conservative
        assert reddit_params.base_delay > web_params.base_delay
        assert (
            reddit_params.max_requests_per_window < web_params.max_requests_per_window
        )
        assert reddit_params.rate_limit_buffer > web_params.rate_limit_buffer

    @pytest.mark.asyncio
    async def test_adaptive_collection_success_scenario(self, reddit_public_collector):
        """Test adaptive collection with successful requests."""
        # Mock the actual collect_content method
        with patch.object(
            reddit_public_collector, "collect_content", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = [{"title": "Test", "url": "http://test.com"}]

            # Perform adaptive collection
            result = await reddit_public_collector.collect_content_adaptive(
                {"limit": 10}
            )

            assert len(result) == 1
            assert result[0]["title"] == "Test"

            # Verify adaptive strategy was used
            assert (
                reddit_public_collector.adaptive_strategy.session_metrics.request_count
                == 1
            )
            assert (
                reddit_public_collector.adaptive_strategy.session_metrics.success_count
                == 1
            )

    @pytest.mark.asyncio
    async def test_adaptive_collection_error_scenario(self, web_collector):
        """Test adaptive collection with errors and rate limiting."""
        # Mock the actual collect_content method to raise an exception
        with patch.object(
            web_collector, "collect_content", new_callable=AsyncMock
        ) as mock_collect:
            # Simulate HTTP 429 rate limit error
            error = Exception("Rate limited")
            error.response = Mock()
            error.response.status_code = 429
            error.response.headers = {"retry-after": "60"}

            mock_collect.side_effect = error

            # Perform adaptive collection
            result = await web_collector.collect_content_adaptive(
                {"url": "http://test.com"}
            )

            assert result == []  # Empty result due to error

            # Verify adaptive strategy recorded the error
            assert web_collector.adaptive_strategy.session_metrics.request_count == 1
            assert web_collector.adaptive_strategy.session_metrics.error_count == 1
            assert (
                web_collector.get_current_delay()
                > web_collector.adaptive_strategy.params.base_delay
            )

    @pytest.mark.asyncio
    async def test_metrics_summary(self, reddit_public_collector):
        """Test metrics summary functionality."""
        # Mock successful collection
        with patch.object(
            reddit_public_collector, "collect_content", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = [{"test": "data"}]

            # Perform some collections
            await reddit_public_collector.collect_content_adaptive({"limit": 5})
            await reddit_public_collector.collect_content_adaptive({"limit": 5})

            # Get metrics summary
            summary = await reddit_public_collector.get_metrics_summary()

            assert summary["source_name"] == "reddit_public"
            assert summary["total_requests"] == 2
            assert summary["success_rate"] == 1.0
            assert "health_status" in summary
            assert "current_delay" in summary

    def test_source_name_identification(
        self, reddit_public_collector, reddit_praw_collector, web_collector
    ):
        """Test that different collectors have correct source names."""
        assert reddit_public_collector.get_source_name() == "reddit_public"
        assert reddit_praw_collector.get_source_name() == "reddit_praw"
        assert web_collector.get_source_name() == "web_content"

    @pytest.mark.asyncio
    async def test_concurrent_collection_independence(self):
        """Test that multiple collectors operate independently."""
        reddit_collector = RedditPublicCollector()
        web_collector = WebContentCollector()

        # Mock both collectors
        with patch.object(
            reddit_collector, "collect_content", new_callable=AsyncMock
        ) as mock_reddit:
            with patch.object(
                web_collector, "collect_content", new_callable=AsyncMock
            ) as mock_web:
                mock_reddit.return_value = [{"source": "reddit"}]
                mock_web.return_value = [{"source": "web"}]

                # Perform concurrent collections
                reddit_task = reddit_collector.collect_content_adaptive({"limit": 10})
                web_task = web_collector.collect_content_adaptive({"url": "test"})

                reddit_result, web_result = await asyncio.gather(reddit_task, web_task)

                # Verify independence
                assert reddit_result[0]["source"] == "reddit"
                assert web_result[0]["source"] == "web"

                # Verify separate metrics
                assert (
                    reddit_collector.adaptive_strategy.session_metrics.request_count
                    == 1
                )
                assert (
                    web_collector.adaptive_strategy.session_metrics.request_count == 1
                )

                # Different strategies should potentially have different delays
                reddit_delay = reddit_collector.get_current_delay()
                web_delay = web_collector.get_current_delay()

                # They should at least be positive
                assert reddit_delay > 0
                assert web_delay > 0
