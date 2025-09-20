"""
Test Adaptive Collection Framework Integration

Tests the adaptive collection functionality integrated into the collector classes.
Maps to: collectors/adaptive_strategy.py, individual collector strategy classes
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from collectors.adaptive_strategy import (
    AdaptiveCollectionStrategy,
    CollectionMetrics,
    SourceHealth,
    StrategyParameters,
)
from collectors.reddit import RedditCollectionStrategy
from collectors.web import WebCollectionStrategy
from source_collectors import SourceCollectorFactory

# Add paths for container testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))

# Alias RSS strategy to WebCollectionStrategy since RSS is web content
RSSCollectionStrategy = WebCollectionStrategy


# Test concrete implementation of abstract base class
class TestConcreteStrategy(AdaptiveCollectionStrategy):
    """Concrete test implementation for testing base strategy functionality."""

    def get_collection_parameters(self):
        """Return test parameters for base strategy testing."""
        return {"max_items": 50, "depth": 2, "test_param": "test_value"}


@pytest.fixture
def mock_blob_storage():
    """Mock blob storage for testing."""
    mock = MagicMock()
    mock.save_strategy_metrics = AsyncMock(return_value=True)
    mock.load_strategy_metrics = AsyncMock(return_value=None)
    return mock


@pytest.mark.unit
class TestAdaptiveStrategy:
    """Test core adaptive collection strategy functionality."""

    @pytest.fixture
    def adaptive_strategy(self, mock_blob_storage):
        """Create adaptive strategy with mocked storage."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_blob_storage,
        ):
            # Use concrete Reddit strategy for testing base functionality
            strategy = RedditCollectionStrategy()
            strategy.blob_storage = mock_blob_storage
            return strategy

    @pytest.mark.asyncio
    async def test_strategy_initialization(self, adaptive_strategy):
        """Test strategy initializes with correct defaults."""
        assert adaptive_strategy.source_name == "reddit"
        assert adaptive_strategy.current_delay == adaptive_strategy.params.base_delay
        assert adaptive_strategy.session_metrics.request_count == 0

    @pytest.mark.asyncio
    async def test_successful_request_tracking(self, adaptive_strategy):
        """Test successful request tracking."""
        await adaptive_strategy.after_request(
            success=True, response_time=1.0, status_code=200
        )

        metrics = adaptive_strategy.session_metrics
        assert metrics.request_count == 1
        assert metrics.success_count == 1
        assert metrics.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_rate_limit_detection(self, adaptive_strategy):
        """Test rate limit detection and handling."""
        await adaptive_strategy.after_request(
            success=False,
            response_time=2.0,
            status_code=429,
            headers={"retry-after": "300"},
        )

        metrics = adaptive_strategy.session_metrics
        assert metrics.rate_limit_count == 1
        assert adaptive_strategy.current_delay > adaptive_strategy.params.base_delay

    @pytest.mark.asyncio
    async def test_delay_adaptation(self, adaptive_strategy):
        """Test delay adaptation based on performance."""
        # Multiple successful requests should reduce delay
        for _ in range(5):
            await adaptive_strategy.after_request(
                success=True, response_time=0.5, status_code=200
            )

        assert adaptive_strategy.current_delay < adaptive_strategy.params.base_delay

    @pytest.mark.asyncio
    async def test_health_assessment(self, adaptive_strategy):
        """Test health status assessment."""
        # Simulate degraded performance (60% success rate)
        for i in range(10):
            success = i < 6  # 60% success rate
            await adaptive_strategy.after_request(
                success=success, response_time=2.0, status_code=200 if success else 500
            )

        adaptive_strategy._assess_health()
        assert adaptive_strategy.session_metrics.health_status == SourceHealth.DEGRADED


@pytest.mark.unit
class TestSourceStrategies:
    """Test source-specific strategy implementations."""

    @pytest.fixture
    def mock_storage(self):
        """Mock storage for source strategies."""
        mock = MagicMock()
        mock.save_strategy_metrics = AsyncMock(return_value=True)
        mock.load_strategy_metrics = AsyncMock(return_value=None)
        return mock

    def test_reddit_strategy_initialization(self, mock_storage):
        """Test Reddit strategy has conservative parameters."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            strategy = RedditCollectionStrategy()
            assert strategy.source_name == "reddit"
            assert strategy.params.base_delay >= 2.0  # Conservative for Reddit

    def test_rss_strategy_initialization(self, mock_storage):
        """Test RSS strategy has moderate parameters."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            strategy = RSSCollectionStrategy()
            assert strategy.source_name == "rss"
            assert strategy.params.base_delay <= 1.0  # More aggressive for RSS

    def test_web_strategy_initialization(self, mock_storage):
        """Test Web strategy has balanced parameters."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            strategy = WebCollectionStrategy()
            assert strategy.source_name == "web"
            assert 1.0 <= strategy.params.base_delay <= 3.0  # Balanced

    @pytest.mark.asyncio
    async def test_reddit_rate_limit_handling(self, mock_storage):
        """Test Reddit-specific rate limit handling."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            strategy = RedditCollectionStrategy()

            await strategy.after_request(
                success=False,
                response_time=2.0,
                status_code=429,
                headers={"retry-after": "600"},
            )

            # Reddit should be very conservative with rate limits
            assert strategy.current_delay >= 600

    @pytest.mark.asyncio
    async def test_source_specific_parameters(self, mock_storage):
        """Test each source has appropriate collection parameters."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            reddit = RedditCollectionStrategy()
            rss = RSSCollectionStrategy()
            web = WebCollectionStrategy()

            reddit_params = await reddit.get_collection_parameters()
            rss_params = await rss.get_collection_parameters()
            web_params = await web.get_collection_parameters()

            # Each should have request_delay
            assert "request_delay" in reddit_params
            assert "request_delay" in rss_params
            assert "request_delay" in web_params

            # Reddit should be most conservative
            assert reddit_params["request_delay"] >= rss_params["request_delay"]


@pytest.mark.integration
class TestAdaptiveCollectorIntegration:
    """Test adaptive collection integration with existing collectors."""

    @pytest.fixture
    def mock_storage(self):
        """Mock storage for integration tests."""
        mock = MagicMock()
        mock.save_strategy_metrics = AsyncMock(return_value=True)
        mock.load_strategy_metrics = AsyncMock(return_value=None)
        return mock

    @pytest.mark.asyncio
    async def test_multiple_source_adaptation(self, mock_storage):
        """Test multiple sources adapt independently."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            reddit = RedditCollectionStrategy()
            rss = RSSCollectionStrategy()

            # Simulate different performance for each source
            await reddit.after_request(
                success=False, response_time=5.0, status_code=429
            )
            await rss.after_request(success=True, response_time=0.5, status_code=200)

            reddit_params = await reddit.get_collection_parameters()
            rss_params = await rss.get_collection_parameters()

            # Reddit should have higher delay due to rate limit
            assert reddit_params["request_delay"] > rss_params["request_delay"]

    @pytest.mark.asyncio
    async def test_metrics_persistence(self, mock_storage):
        """Test metrics are saved for persistence."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            strategy = RedditCollectionStrategy()

            await strategy.after_request(
                success=True, response_time=1.0, status_code=200
            )

            # Verify save was called
            mock_storage.save_strategy_metrics.assert_called()

    @pytest.mark.asyncio
    async def test_adaptive_collection_workflow(self, mock_storage):
        """Test complete adaptive collection workflow."""
        with patch(
            "collectors.blob_metrics_storage.get_metrics_storage",
            return_value=mock_storage,
        ):
            strategy = RedditCollectionStrategy()

            # 1. Get initial parameters
            initial_params = await strategy.get_collection_parameters()
            initial_delay = initial_params["request_delay"]

            # 2. Apply delay before request
            await strategy.before_request()

            # 3. Process successful request
            await strategy.after_request(
                success=True, response_time=1.0, status_code=200
            )

            # 4. Get updated parameters
            updated_params = await strategy.get_collection_parameters()

            # Delay should have been reduced slightly after success
            assert updated_params["request_delay"] <= initial_delay


@pytest.mark.unit
class TestCollectionMetrics:
    """Test collection metrics data structure."""

    def test_metrics_serialization(self):
        """Test metrics can be serialized/deserialized."""
        metrics = CollectionMetrics(
            source_name="test",
            timestamp=datetime.now(),
            request_count=10,
            success_count=8,
            error_count=2,
            rate_limit_count=1,
            avg_response_time=1.5,
            current_rate_limit=None,
            rate_limit_reset=None,
            health_status=SourceHealth.HEALTHY,
            adaptive_delay=2.0,
            success_rate=0.8,
        )

        data = metrics.to_dict()
        assert isinstance(data["timestamp"], str)
        assert data["health_status"] == "healthy"

        restored = CollectionMetrics.from_dict(data)
        assert restored.source_name == metrics.source_name
        assert restored.success_rate == metrics.success_rate


@pytest.mark.unit
class TestStrategyParameters:
    """Test strategy parameter configuration."""

    def test_default_parameters(self):
        """Test default strategy parameters."""
        params = StrategyParameters()
        assert params.base_delay > 0
        assert params.min_delay >= 0
        assert params.max_delay > params.base_delay
        assert 0 < params.backoff_multiplier <= 10

    def test_custom_parameters(self):
        """Test custom strategy parameters."""
        params = StrategyParameters(
            base_delay=5.0, max_delay=300.0, backoff_multiplier=3.0
        )
        assert params.base_delay == 5.0
        assert params.max_delay == 300.0
        assert params.backoff_multiplier == 3.0


# Import collector components


@pytest.mark.unit
class TestAdaptiveCollectionStrategy:
    """Test core adaptive collection strategy framework."""

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
    def strategy(self, mock_storage):
        """Create test strategy instance."""
        return TestConcreteStrategy("test_source")

    def test_strategy_initialization(self, strategy):
        """Test strategy initializes with correct defaults."""
        assert strategy.source_name == "test_source"
        assert strategy.current_delay == strategy.params.base_delay
        assert strategy.session_metrics.request_count == 0
        assert strategy.session_metrics.success_count == 0

    @pytest.mark.asyncio
    async def test_before_request_applies_delay(self, strategy):
        """Test before_request applies adaptive delay."""
        strategy.current_delay = 3.0

        # Mock asyncio.sleep to avoid actual delays in tests
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await strategy.before_request()

            # Verify sleep was called with the correct delay
            mock_sleep.assert_called_with(3.0)

    @pytest.mark.asyncio
    async def test_successful_request_reduces_delay(self, strategy):
        """Test successful requests gradually reduce delay."""
        initial_delay = strategy.current_delay

        # Simulate multiple successful requests
        for _ in range(3):
            await strategy.after_request(
                success=True, response_time=1.0, status_code=200
            )

        # Delay should be reduced but not below minimum
        assert strategy.current_delay <= initial_delay
        assert strategy.current_delay >= strategy.params.min_delay

    @pytest.mark.asyncio
    async def test_failed_request_increases_delay(self, strategy):
        """Test failed requests increase delay after multiple consecutive errors."""
        initial_delay = strategy.current_delay

        # First error - no delay increase yet
        await strategy.after_request(success=False, response_time=5.0, status_code=500)
        assert strategy.current_delay == initial_delay  # No change yet

        # Second consecutive error - now delay should increase
        await strategy.after_request(success=False, response_time=5.0, status_code=500)

        # Delay should be increased after 2 consecutive errors
        assert strategy.current_delay > initial_delay

    @pytest.mark.asyncio
    async def test_rate_limit_detection(self, strategy):
        """Test rate limit detection and handling."""
        await strategy.after_request(
            success=False,
            response_time=1.0,
            status_code=429,
            headers={"retry-after": "300"},
        )

        # Should increase rate limit count and adaptive delay
        assert strategy.session_metrics.rate_limit_count == 1
        # Should be 305 (300 + 5 second buffer)
        assert strategy.current_delay >= 300

    def test_health_status_assessment(self, strategy):
        """Test health status assessment based on metrics."""
        # High success rate = healthy
        strategy.session_metrics.request_count = 10
        strategy.session_metrics.success_count = 9
        strategy.session_metrics.success_rate = 0.9

        strategy._assess_health()
        assert strategy.session_metrics.health_status == SourceHealth.HEALTHY

        # Low success rate = error state
        strategy.session_metrics.success_count = 3
        strategy.session_metrics.success_rate = 0.3

        strategy._assess_health()
        assert strategy.session_metrics.health_status == SourceHealth.ERROR

    @pytest.mark.asyncio
    async def test_metrics_persistence(self, strategy, mock_storage):
        """Test metrics are persisted after multiple requests."""
        # Make 10 requests to trigger persistence (metrics saved every 10 requests)
        for i in range(10):
            await strategy.after_request(
                success=True, response_time=2.0, status_code=200
            )

        # Should save metrics after 10 requests
        mock_storage.save_strategy_metrics.assert_called()


@pytest.mark.unit
class TestCollectionMetrics:
    """Test collection metrics data structure."""

    def test_metrics_creation(self):
        """Test metrics can be created and updated."""
        metrics = CollectionMetrics(
            source_name="test",
            timestamp=datetime.now(),
            request_count=5,
            success_count=4,
            error_count=1,
            rate_limit_count=0,
            avg_response_time=1.5,
            current_rate_limit=None,
            rate_limit_reset=None,
            health_status=SourceHealth.HEALTHY,
            adaptive_delay=2.0,
            success_rate=0.8,
        )

        assert metrics.source_name == "test"
        assert metrics.success_rate == 0.8
        assert metrics.health_status == SourceHealth.HEALTHY

    def test_metrics_serialization(self):
        """Test metrics can be serialized to dict."""
        metrics = CollectionMetrics(
            source_name="test",
            timestamp=datetime(2023, 10, 22, 12, 0, 0),
            request_count=5,
            success_count=4,
            error_count=1,
            rate_limit_count=0,
            avg_response_time=1.5,
            current_rate_limit=None,
            rate_limit_reset=None,
            health_status=SourceHealth.HEALTHY,
            adaptive_delay=2.0,
            success_rate=0.8,
        )

        data = metrics.to_dict()
        assert data["source_name"] == "test"
        assert data["success_rate"] == 0.8
        assert data["health_status"] == "healthy"
        assert data["timestamp"] == "2023-10-22T12:00:00"


@pytest.mark.integration
class TestAdaptiveCollectorIntegration:
    """Test adaptive collection integrated with real collectors."""

    @pytest.fixture
    def mock_storage(self):
        """Mock metrics storage for integration tests."""
        with patch("collectors.adaptive_strategy.get_metrics_storage") as mock:
            storage = MagicMock()
            storage.save_strategy_metrics = AsyncMock(return_value=True)
            storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock.return_value = storage
            yield storage

    @pytest.mark.asyncio
    async def test_reddit_collector_with_adaptive_strategy(self, mock_storage):
        """Test Reddit collector has adaptive strategy configured."""
        from collectors.reddit import RedditPRAWCollector

        # Mock Reddit API to avoid authentication
        with patch(
            "collectors.reddit.get_reddit_credentials_with_fallback"
        ) as mock_creds:
            mock_creds.return_value = {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "user_agent": "test_agent",
            }

            with patch("praw.Reddit") as mock_reddit:
                collector = RedditPRAWCollector()

                # Should have adaptive strategy configured
                assert hasattr(collector, "adaptive_strategy")
                assert collector.adaptive_strategy is not None
                assert collector.adaptive_strategy.source_name == "reddit_praw"

                # Strategy should be Reddit-specific
                assert isinstance(collector.adaptive_strategy, RedditCollectionStrategy)

    @pytest.mark.asyncio
    async def test_web_collector_with_adaptive_strategy(self, mock_storage):
        """Test Web collector uses adaptive collection."""
        from collectors.web import WebContentCollector

        with (
            patch("aiohttp.ClientSession.get") as mock_get,
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            # Mock successful web response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value="<html><body>Test content</body></html>"
            )
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value.__aenter__.return_value = mock_response

            collector = WebContentCollector()

            # Test adaptive collection
            result = await collector.collect_content_adaptive(
                {"url": "https://example.com", "max_pages": 1}
            )

            assert result is not None

            # Strategy should have been used
            assert hasattr(collector, "adaptive_strategy")
            assert collector.adaptive_strategy.session_metrics.request_count > 0

    @pytest.mark.asyncio
    async def test_multi_source_adaptive_collection(self, mock_storage):
        """Test adaptive collection across multiple sources."""
        from collectors.reddit import RedditPRAWCollector
        from collectors.web import WebContentCollector

        collectors = []

        # Mock Reddit collector
        with patch(
            "collectors.reddit.get_reddit_credentials_with_fallback"
        ) as mock_creds:
            mock_creds.return_value = {
                "client_id": "test_id",
                "client_secret": "test_secret",
                "user_agent": "test_agent",
            }

            with patch("praw.Reddit"):
                reddit_collector = RedditPRAWCollector()
                collectors.append(("reddit_praw", reddit_collector))

        # Create Web collector
        web_collector = WebContentCollector()
        collectors.append(("web_content", web_collector))

        # Test that each has independent adaptive strategies
        for expected_source, collector in collectors:
            assert hasattr(collector, "adaptive_strategy")
            assert collector.adaptive_strategy.source_name == expected_source

            # Each should have appropriate strategy parameters
            if expected_source == "reddit_praw":
                # Reddit should be more conservative
                assert collector.adaptive_strategy.params.base_delay >= 2.0
            elif expected_source == "web_content":
                # Web should be moderate
                assert collector.adaptive_strategy.params.base_delay >= 1.0


@pytest.mark.performance
class TestAdaptivePerformance:
    """Test adaptive collection performance scenarios."""

    @pytest.fixture
    def mock_storage(self):
        """Mock storage for performance tests."""
        with patch("collectors.adaptive_strategy.get_metrics_storage") as mock:
            storage = MagicMock()
            storage.save_strategy_metrics = AsyncMock(return_value=True)
            storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock.return_value = storage
            yield storage

    @pytest.mark.asyncio
    async def test_rate_limiting_scenario(self, mock_storage):
        """Test adaptive behavior under rate limiting."""
        strategy = TestConcreteStrategy("test_rate_limit")

        # Simulate rate limiting scenario
        initial_delay = strategy.current_delay

        # First few requests succeed
        for _ in range(3):
            await strategy.after_request(
                success=True, response_time=1.0, status_code=200
            )

        # Then hit rate limit
        await strategy.after_request(
            success=False,
            response_time=1.0,
            status_code=429,
            headers={"retry-after": "60"},
        )

        # Delay should increase significantly
        assert strategy.current_delay > initial_delay * 2
        assert strategy.session_metrics.rate_limit_count == 1

    @pytest.mark.asyncio
    async def test_gradual_recovery_scenario(self, mock_storage):
        """Test gradual recovery from degraded state."""
        strategy = TestConcreteStrategy("test_recovery")

        # Start with some failures to degrade performance
        for _ in range(3):
            await strategy.after_request(
                success=False, response_time=5.0, status_code=500
            )

        degraded_delay = strategy.current_delay

        # Then gradually recover with successes
        for _ in range(5):
            await strategy.after_request(
                success=True, response_time=1.0, status_code=200
            )

        # Delay should reduce but remain cautious
        assert strategy.current_delay < degraded_delay
        assert strategy.current_delay >= strategy.params.min_delay

        # Health should improve
        assert strategy.session_metrics.success_rate > 0.5
