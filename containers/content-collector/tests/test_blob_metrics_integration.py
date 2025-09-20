"""
Test Blob Metrics Storage Integration

Tests for persistent metrics storage integrated with adaptive collection.
Maps to: collectors/blob_metrics_storage.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from collectors.adaptive_strategy import CollectionMetrics, SourceHealth
from collectors.blob_metrics_storage import BlobMetricsStorage, get_metrics_storage

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "libs"))


@pytest.mark.unit
class TestBlobMetricsStorage:
    """Test blob metrics storage functionality."""

    @pytest.fixture
    def mock_blob_client(self):
        """Create mock blob storage client."""
        mock = MagicMock()
        mock.upload_json = AsyncMock(return_value=True)
        mock.download_json = AsyncMock(return_value={"test": "data"})
        mock.list_blobs = AsyncMock(return_value=[])
        mock.delete_blob = AsyncMock(return_value=True)
        mock.ensure_container = Mock()
        return mock

    @pytest.fixture
    def blob_storage(self, mock_blob_client):
        """Create BlobMetricsStorage instance with mocked client."""
        storage = BlobMetricsStorage()
        # Replace the blob_client after initialization with our mock
        storage.blob_client = mock_blob_client
        yield storage

    @pytest.fixture
    def sample_metrics(self):
        """Create sample metrics for testing."""
        return CollectionMetrics(
            source_name="test_source",
            timestamp=datetime(2023, 10, 22, 12, 0, 0),
            request_count=10,
            success_count=8,
            error_count=2,
            rate_limit_count=1,
            avg_response_time=2.5,
            current_rate_limit=60,
            rate_limit_reset=datetime(2023, 10, 22, 12, 15),
            health_status=SourceHealth.HEALTHY,
            adaptive_delay=1.5,
            success_rate=0.8,
        )

    @pytest.mark.asyncio
    async def test_save_strategy_metrics(
        self, blob_storage, mock_blob_client, sample_metrics
    ):
        """Test saving strategy metrics to blob storage."""
        strategy_key = "test_reddit_strategy"
        metrics_data = {
            "request_count": sample_metrics.request_count,
            "success_count": sample_metrics.success_count,
            "error_count": sample_metrics.error_count,
            "avg_response_time": sample_metrics.avg_response_time,
            "success_rate": sample_metrics.success_rate,
        }

        result = await blob_storage.save_strategy_metrics(strategy_key, metrics_data)

        assert result is True

        # Verify blob client was called correctly
        mock_blob_client.upload_json.assert_called()
        # Should be called twice (timestamped and latest)
        assert mock_blob_client.upload_json.call_count == 2

        # Check call arguments
        calls = mock_blob_client.upload_json.call_args_list
        assert len(calls) == 2

        # First call should be timestamped version
        container_name, blob_name, data = calls[0][0]
        assert container_name == "collection-metrics"
        assert "strategies/test_reddit_strategy/metrics/" in blob_name
        assert blob_name.endswith(".json")
        assert data["strategy_key"] == "test_reddit_strategy"
        assert data["metrics"]["request_count"] == 10

    @pytest.mark.asyncio
    async def test_load_strategy_metrics(self, blob_storage, mock_blob_client):
        """Test loading strategy metrics from blob storage."""
        # Setup mock response
        sample_data = {
            "strategy_key": "test_source",
            "timestamp": "2023-10-22T12:00:00",
            "metrics": {"request_count": 5, "success_count": 4, "success_rate": 0.8},
        }

        mock_blob_client.download_json.return_value = sample_data

        result = await blob_storage.load_strategy_metrics("test_source")

        assert result is not None
        assert result["strategy_key"] == "test_source"
        assert result["metrics"]["success_rate"] == 0.8

        # Verify correct blob was requested
        mock_blob_client.download_json.assert_called_once()
        call_args = mock_blob_client.download_json.call_args[0]
        container_name, blob_name = call_args
        assert container_name == "collection-metrics"
        assert blob_name == "strategies/test_source/latest.json"

    @pytest.mark.asyncio
    async def test_save_global_metrics(self, blob_storage, mock_blob_client):
        """Test saving global metrics."""
        global_data = {
            "total_requests": 100,
            "total_successes": 85,
            "total_errors": 15,
            "average_response_time": 2.3,
            "active_sources": ["reddit", "web", "rss"],
        }

        result = await blob_storage.save_global_metrics(global_data)

        assert result is True
        mock_blob_client.upload_json.assert_called_once()

        # Check call arguments
        container_name, blob_name, data = mock_blob_client.upload_json.call_args[0]
        assert container_name == "collection-metrics"
        assert blob_name == "global/metrics.json"
        assert data["total_requests"] == 100
        assert data["active_sources"] == ["reddit", "web", "rss"]

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics(self, blob_storage, mock_blob_client):
        """Test cleanup of old metrics."""
        # Mock old blobs
        old_blob = Mock()
        old_blob.name = "strategies/test/metrics/2023/09/01/120000.json"
        old_blob.last_modified = datetime.now() - timedelta(days=35)

        recent_blob = Mock()
        recent_blob.name = "strategies/test/metrics/2023/10/01/120000.json"
        recent_blob.last_modified = datetime.now() - timedelta(days=5)

        mock_blob_client.list_blobs.return_value = [old_blob, recent_blob]

        deleted_count = await blob_storage.cleanup_old_metrics(retention_days=30)

        assert deleted_count == 1
        mock_blob_client.delete_blob.assert_called_once()

        # Should delete the old blob
        deleted_blob_name = mock_blob_client.delete_blob.call_args[0][1]
        assert deleted_blob_name == old_blob.name

    def test_get_metrics_storage_singleton(self):
        """Test metrics storage singleton pattern."""
        storage1 = get_metrics_storage()
        storage2 = get_metrics_storage()

        # Should return the same instance
        assert storage1 is storage2
        assert isinstance(storage1, BlobMetricsStorage)


@pytest.mark.integration
class TestBlobMetricsIntegration:
    """Test blob metrics storage integration with adaptive strategies."""

    @pytest.fixture
    def mock_blob_client(self):
        """Mock blob client for integration tests."""
        mock = MagicMock()
        mock.upload_json = AsyncMock(return_value=True)
        mock.download_json = AsyncMock(return_value=None)
        mock.list_blobs = AsyncMock(return_value=[])
        mock.ensure_container = Mock()
        return mock

    @pytest.mark.asyncio
    async def test_adaptive_strategy_saves_metrics(self, mock_blob_client):
        """Test adaptive strategy automatically saves metrics."""
        from adaptive_strategy import AdaptiveCollectionStrategy

        # Mock the storage
        with patch("adaptive_strategy.get_metrics_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.save_strategy_metrics = AsyncMock(return_value=True)
            mock_storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            strategy = AdaptiveCollectionStrategy("test_integration")

            # Simulate a request
            await strategy.after_request(
                success=True, response_time=1.5, status_code=200
            )

            # Should have saved metrics
            mock_storage.save_strategy_metrics.assert_called()

            # Check the saved data
            call_args = mock_storage.save_strategy_metrics.call_args
            strategy_key, metrics_data = call_args[0]

            assert strategy_key == "test_integration"
            assert metrics_data["request_count"] == 1
            assert metrics_data["success_count"] == 1

    @pytest.mark.asyncio
    async def test_strategy_loads_previous_metrics(self, mock_blob_client):
        """Test strategy loads previous metrics on initialization."""
        from adaptive_strategy import AdaptiveCollectionStrategy

        # Mock previous metrics data
        previous_metrics = {
            "strategy_key": "test_load",
            "metrics": {
                "request_count": 50,
                "success_count": 45,
                "success_rate": 0.9,
                "avg_response_time": 1.2,
            },
            "strategy_params": {"current_delay": 1.8},
        }

        with patch("adaptive_strategy.get_metrics_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.load_strategy_metrics = AsyncMock(
                return_value=previous_metrics
            )
            mock_storage.save_strategy_metrics = AsyncMock(return_value=True)
            mock_get_storage.return_value = mock_storage

            strategy = AdaptiveCollectionStrategy("test_load")

            # Should have loaded previous metrics
            mock_storage.load_strategy_metrics.assert_called_with("test_load")

    @pytest.mark.asyncio
    async def test_collector_metrics_persistence(self, mock_blob_client):
        """Test collector with adaptive strategy persists metrics."""
        from collectors.web import WebCollector

        with patch("adaptive_strategy.get_metrics_storage") as mock_get_storage:
            mock_storage = MagicMock()
            mock_storage.save_strategy_metrics = AsyncMock(return_value=True)
            mock_storage.load_strategy_metrics = AsyncMock(return_value=None)
            mock_get_storage.return_value = mock_storage

            collector = WebCollector()

            # Mock web request
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.text = AsyncMock(
                    return_value="<html><body>Test</body></html>"
                )
                mock_get.return_value.__aenter__.return_value = mock_response

                # Perform collection
                await collector.collect_content_adaptive(
                    {"url": "https://example.com", "max_pages": 1}
                )

                # Should have persisted metrics
                mock_storage.save_strategy_metrics.assert_called()

                # Check metrics were saved with correct source name
                call_args = mock_storage.save_strategy_metrics.call_args
                strategy_key, metrics_data = call_args[0]
                assert strategy_key == "web"


@pytest.mark.performance
class TestBlobMetricsPerformance:
    """Test blob metrics storage performance characteristics."""

    @pytest.fixture
    def mock_blob_client(self):
        """Mock blob client for performance tests."""
        mock = MagicMock()
        mock.upload_json = AsyncMock(return_value=True)
        mock.download_json = AsyncMock(return_value=None)
        mock.ensure_container = Mock()
        return mock

    @pytest.mark.asyncio
    async def test_concurrent_metrics_saves(self, mock_blob_client):
        """Test concurrent metrics saves don't conflict."""
        import asyncio

        storage = BlobMetricsStorage()
        storage.blob_client = mock_blob_client

        # Create multiple concurrent save operations
        async def save_metrics(strategy_key, request_count):
            metrics_data = {
                "request_count": request_count,
                "success_count": request_count - 1,
                "success_rate": (request_count - 1) / request_count,
            }
            return await storage.save_strategy_metrics(strategy_key, metrics_data)

        # Run multiple saves concurrently
        tasks = [
            save_metrics("reddit", 10),
            save_metrics("web", 15),
            save_metrics("rss", 8),
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(results)

        # Should have made multiple upload calls
        assert mock_blob_client.upload_json.call_count >= 6  # 2 calls per strategy

    @pytest.mark.asyncio
    async def test_metrics_storage_error_handling(self, mock_blob_client):
        """Test error handling in metrics storage."""
        storage = BlobMetricsStorage()
        storage.blob_client = mock_blob_client

        # Mock upload failure
        mock_blob_client.upload_json.side_effect = Exception("Storage unavailable")

        # Should handle errors gracefully
        result = await storage.save_strategy_metrics("test", {"request_count": 1})

        assert result is False  # Should return False on error, not raise

    def test_health_check(self, mock_blob_client):
        """Test storage health check."""
        storage = BlobMetricsStorage()
        storage.blob_client = mock_blob_client

        health = storage.health_check()

        assert "status" in health
        assert "container_name" in health
        assert health["container_name"] == "collection-metrics"
