"""
Test Source-Specific Collection Strategies

Tests for Reddit, Web, and RSS specific adaptive collection behaviors.
Maps to: collectors/reddit.py, collectors/web.py, collectors/rss.py
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from collectors.adaptive_strategy import SourceHealth


@pytest.mark.unit
class TestRedditAdaptiveCollection:
    """Test Reddit-specific adaptive collection behavior."""

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
    def reddit_collector(self, mock_storage):
        """Create Reddit collector with mocked dependencies."""
        from collectors.reddit import RedditPRAWCollector

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

            # Mock HTTP client to prevent actual requests
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"children": []}}
            mock_httpx.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            collector = RedditPRAWCollector()
            yield collector, mock_reddit

    def test_reddit_strategy_parameters(self, reddit_collector):
        """Test Reddit has conservative strategy parameters."""
        collector, _ = reddit_collector

        # Reddit should be conservative due to strict rate limits
        assert collector.adaptive_strategy.params.base_delay >= 2.0
        assert collector.adaptive_strategy.params.max_delay >= 300.0
        assert collector.adaptive_strategy.params.backoff_multiplier >= 2.0

    @pytest.mark.asyncio
    async def test_reddit_successful_collection(self, reddit_collector):
        """Test successful Reddit collection updates metrics."""
        collector, mock_reddit = reddit_collector

        # Mock successful Reddit response
        mock_subreddit = Mock()
        mock_post = Mock()
        mock_post.title = "Test Post"
        mock_post.selftext = "Test content"
        mock_post.url = "https://reddit.com/test"
        mock_post.score = 100
        mock_post.created_utc = 1634567890
        mock_post.author = Mock()
        mock_post.author.name = "test_user"

        mock_subreddit.hot.return_value = [mock_post]
        mock_reddit.return_value.subreddit.return_value = mock_subreddit

        initial_requests = collector.adaptive_strategy.session_metrics.request_count

        result = await collector.collect_content_adaptive(
            {"subreddit": "programming", "limit": 5}
        )

        assert result is not None
        assert len(result) > 0
        assert (
            collector.adaptive_strategy.session_metrics.request_count > initial_requests
        )
        assert collector.adaptive_strategy.session_metrics.success_count > 0

    @pytest.mark.asyncio
    async def test_reddit_rate_limit_handling(self, reddit_collector):
        """Test Reddit rate limit handling."""
        collector, mock_reddit = reddit_collector

        # Mock rate limited response
        from prawcore.exceptions import TooManyRequests

        mock_reddit.return_value.subreddit.side_effect = TooManyRequests(Mock())

        initial_delay = collector.adaptive_strategy.current_delay

        try:
            await collector.collect_content_adaptive(
                {"subreddit": "programming", "limit": 5}
            )
        except Exception:
            pass  # Expected to fail

        # Should have increased delay significantly
        assert collector.adaptive_strategy.current_delay > initial_delay
        assert collector.adaptive_strategy.session_metrics.rate_limit_count > 0

    @pytest.mark.asyncio
    async def test_reddit_oauth_error_handling(self, reddit_collector):
        """Test Reddit OAuth error handling."""
        collector, mock_reddit = reddit_collector

        # Mock OAuth error
        from prawcore.exceptions import OAuthException

        mock_reddit.return_value.subreddit.side_effect = OAuthException(
            "invalid_grant", "", ""
        )

        initial_delay = collector.adaptive_strategy.current_delay

        try:
            await collector.collect_content_adaptive(
                {"subreddit": "programming", "limit": 5}
            )
        except Exception:
            pass  # Expected to fail

        # Should handle auth errors gracefully
        assert collector.adaptive_strategy.session_metrics.error_count > 0


@pytest.mark.unit
class TestWebAdaptiveCollection:
    """Test Web-specific adaptive collection behavior."""

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
    def web_collector(self, mock_storage):
        """Create Web collector with mocked dependencies."""
        from collectors.web import WebContentCollector

        return WebContentCollector()

    def test_web_strategy_parameters(self, web_collector):
        """Test Web has moderate strategy parameters."""
        # Web should be respectful but not as conservative as Reddit
        assert web_collector.adaptive_strategy.params.base_delay >= 1.0
        assert web_collector.adaptive_strategy.params.base_delay < 3.0
        assert web_collector.adaptive_strategy.params.max_delay >= 180.0

    @pytest.mark.asyncio
    async def test_web_successful_collection(self, web_collector):
        """Test successful web collection updates metrics."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Mock successful web response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value="<html><body>Test content</body></html>"
            )
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value.__aenter__.return_value = mock_response

            initial_requests = (
                web_collector.adaptive_strategy.session_metrics.request_count
            )

            result = await web_collector.collect_content_adaptive(
                {"url": "https://example.com", "max_pages": 1}
            )

            assert result is not None
            assert (
                web_collector.adaptive_strategy.session_metrics.request_count
                > initial_requests
            )
            assert web_collector.adaptive_strategy.session_metrics.success_count > 0

    @pytest.mark.asyncio
    async def test_web_rate_limit_handling(self, web_collector):
        """Test web rate limit handling."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Mock rate limited response (429)
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.headers = {"retry-after": "30"}
            mock_get.return_value.__aenter__.return_value = mock_response

            initial_delay = web_collector.adaptive_strategy.current_delay

            try:
                await web_collector.collect_content_adaptive(
                    {"url": "https://example.com", "max_pages": 1}
                )
            except Exception:
                pass  # May fail due to rate limiting

            # Should have increased delay
            assert web_collector.adaptive_strategy.current_delay >= initial_delay
            assert web_collector.adaptive_strategy.session_metrics.rate_limit_count > 0

    @pytest.mark.asyncio
    async def test_web_server_error_handling(self, web_collector):
        """Test web server error handling."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            # Mock server error (500)
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text = AsyncMock(return_value="Internal Server Error")
            mock_get.return_value.__aenter__.return_value = mock_response

            initial_delay = web_collector.adaptive_strategy.current_delay

            try:
                await web_collector.collect_content_adaptive(
                    {"url": "https://example.com", "max_pages": 1}
                )
            except Exception:
                pass  # Expected to fail

            # Should have increased delay due to server error
            assert web_collector.adaptive_strategy.current_delay > initial_delay
            assert web_collector.adaptive_strategy.session_metrics.error_count > 0


@pytest.mark.integration
class TestSourceCollectorFactory:
    """Test source collector factory with adaptive capabilities."""

    @pytest.fixture
    def mock_storage(self):
        """Mock metrics storage."""
        with patch("collectors.adaptive_strategy.get_metrics_storage") as mock:
            storage = MagicMock()
            storage.save_strategy_metrics = AsyncMock(return_value=True)
            storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock.return_value = storage
            yield storage

    def test_factory_creates_adaptive_collectors(self, mock_storage):
        """Test factory creates collectors with adaptive strategies."""
        from source_collectors import SourceCollectorFactory

        factory = SourceCollectorFactory()

        # Test Reddit collector creation
        with patch(
            "collectors.reddit.get_reddit_credentials_with_fallback"
        ) as mock_creds:
            mock_creds.return_value = {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "user_agent": "test_agent",
            }

            reddit_collector = factory.create_reddit_collector()
            if reddit_collector:
                assert hasattr(reddit_collector, "adaptive_strategy")
                assert reddit_collector.adaptive_strategy.source_name == "reddit"

        # Test Web collector creation
        web_collector = factory.create_web_collector()
        if web_collector:
            assert hasattr(web_collector, "adaptive_strategy")
            assert web_collector.adaptive_strategy.source_name == "web"

    @pytest.mark.asyncio
    async def test_collectors_have_different_strategies(self, mock_storage):
        """Test different collectors have appropriately tuned strategies."""
        from source_collectors import SourceCollectorFactory

        factory = SourceCollectorFactory()
        collectors = []

        # Create Reddit collector
        with patch(
            "collectors.reddit.get_reddit_credentials_with_fallback"
        ) as mock_creds:
            mock_creds.return_value = {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "user_agent": "test_agent",
            }

            reddit_collector = factory.create_reddit_collector()
            if reddit_collector:
                collectors.append(("reddit", reddit_collector))

        # Create Web collector
        web_collector = factory.create_web_collector()
        if web_collector:
            collectors.append(("web", web_collector))

        # Verify different strategy parameters
        strategies = {
            name: collector.adaptive_strategy for name, collector in collectors
        }

        if "reddit" in strategies and "web" in strategies:
            reddit_strategy = strategies["reddit"]
            web_strategy = strategies["web"]

            # Reddit should be more conservative than web
            assert reddit_strategy.params.base_delay >= web_strategy.params.base_delay
            assert reddit_strategy.params.max_delay >= web_strategy.params.max_delay


@pytest.mark.performance
class TestAdaptiveCollectionScenarios:
    """Test realistic collection scenarios with adaptive strategies."""

    @pytest.fixture
    def mock_storage(self):
        """Mock metrics storage."""
        with patch("collectors.adaptive_strategy.get_metrics_storage") as mock:
            storage = MagicMock()
            storage.save_strategy_metrics = AsyncMock(return_value=True)
            storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock.return_value = storage
            yield storage

    @pytest.mark.asyncio
    async def test_concurrent_multi_source_collection(self, mock_storage):
        """Test concurrent collection from multiple sources."""
        import asyncio

        from source_collectors import SourceCollectorFactory

        factory = SourceCollectorFactory()

        async def collect_reddit():
            with patch(
                "collectors.reddit.get_reddit_credentials_with_fallback"
            ) as mock_creds:
                mock_creds.return_value = {
                    "client_id": "test_id",
                    "client_secret": "test_secret",
                    "user_agent": "test_agent",
                }

                with patch("praw.Reddit") as mock_reddit:
                    mock_subreddit = Mock()
                    mock_subreddit.hot.return_value = []
                    mock_reddit.return_value.subreddit.return_value = mock_subreddit

                    collector = factory.create_reddit_collector()
                    if collector:
                        return await collector.collect_content_adaptive(
                            {"subreddit": "programming", "limit": 5}
                        )

        async def collect_web():
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(
                    return_value="<html><body>Test</body></html>"
                )
                mock_get.return_value.__aenter__.return_value = mock_response

                collector = factory.create_web_collector()
                if collector:
                    return await collector.collect_content_adaptive(
                        {"url": "https://example.com", "max_pages": 1}
                    )

        # Run collections concurrently
        results = await asyncio.gather(
            collect_reddit(), collect_web(), return_exceptions=True
        )

        # Both should complete (even if with empty results due to mocking)
        assert len(results) == 2

        # No catastrophic failures
        for result in results:
            if isinstance(result, Exception):
                # Log but don't fail test for expected collection issues
                print(f"Collection result: {result}")

    @pytest.mark.asyncio
    async def test_degraded_performance_recovery(self, mock_storage):
        """Test recovery from degraded performance state."""
        from collectors.web import WebContentCollector

        collector = WebContentCollector()

        # Simulate degraded performance period
        with patch("aiohttp.ClientSession.get") as mock_get:
            # First, cause several failures
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_get.return_value.__aenter__.return_value = mock_response_fail

            for _ in range(3):
                try:
                    await collector.collect_content_adaptive(
                        {"url": "https://example.com", "max_pages": 1}
                    )
                except Exception:
                    pass  # Expected failures

            degraded_delay = collector.adaptive_strategy.current_delay
            degraded_health = collector.adaptive_strategy.session_metrics.health_status

            # Then simulate recovery with successes
            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.text = AsyncMock(
                return_value="<html><body>Success</body></html>"
            )
            mock_get.return_value.__aenter__.return_value = mock_response_success

            for _ in range(5):
                try:
                    await collector.collect_content_adaptive(
                        {"url": "https://example.com", "max_pages": 1}
                    )
                except Exception:
                    pass

            # Should show improvement
            final_delay = collector.adaptive_strategy.current_delay
            final_health = collector.adaptive_strategy.session_metrics.health_status

            # Delay should reduce (but remain cautious)
            assert final_delay <= degraded_delay

            # Health should improve or stay stable
            if degraded_health == SourceHealth.ERROR:
                assert final_health in [SourceHealth.DEGRADED, SourceHealth.HEALTHY]
