"""
Unit Tests for Blob Metrics Storage

Tests for Azure Blob Storage integration and persistence functionality.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from urllib.parse import urlparse

import pytest
from collectors.adaptive_strategy import CollectionMetrics, SourceHealth
from collectors.blob_metrics_storage import BlobMetricsStorage

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "containers", "content-collector")
)


class TestBlobMetricsStorage:
    """Test the blob storage persistence layer."""

    def _validate_test_url(self, url: str) -> str:
        """Validate test URLs for security."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
        if not parsed.netloc:
            raise ValueError("URL must have a valid domain")
        return url

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
            current_rate_limit=100,
            rate_limit_reset=datetime(2023, 10, 22, 12, 15, 0),
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
            "source_name": "test_source",
            "timestamp": "2023-10-22T12:00:00",
            "request_count": 5,
            "success_count": 4,
            "error_count": 1,
            "rate_limit_count": 0,
            "avg_response_time": 1.8,
            "current_rate_limit": 60,
            "rate_limit_reset": None,
            "health_status": "healthy",
            "adaptive_delay": 2.0,
            "success_rate": 0.8,
        }
        mock_blob_client.download_text.return_value = json.dumps(sample_data)

        result = await blob_storage.load_strategy_metrics("test_source")

        assert result is not None
        assert isinstance(result, CollectionMetrics)
        assert result.source_name == "test_source"
        assert result.request_count == 5
        assert result.health_status == SourceHealth.HEALTHY

    @pytest.mark.asyncio
    async def test_load_strategy_metrics_not_found(
        self, blob_storage, mock_blob_storage
    ):
        """Test loading metrics when file doesn't exist."""
        mock_blob_storage.download_text.side_effect = Exception("Blob not found")

        result = await blob_storage.load_strategy_metrics("nonexistent_source")

        assert result is None

    @pytest.mark.asyncio
    async def test_save_subreddit_cooldowns(self, blob_storage, mock_blob_storage):
        """Test saving subreddit cooldowns."""
        cooldowns = {
            "programming": datetime(2023, 10, 22, 12, 30, 0),
            "python": datetime(2023, 10, 22, 11, 45, 0),
        }

        result = await blob_storage.save_subreddit_cooldowns(cooldowns)

        assert result is True
        mock_blob_storage.upload_text.assert_called_once()

        # Check content
        call_args = mock_blob_storage.upload_text.call_args
        content = call_args[0][0]
        blob_name = call_args[0][1]

        assert blob_name == "metrics/reddit/subreddit_cooldowns.json"

        data = json.loads(content)
        assert "programming" in data
        assert "python" in data

    @pytest.mark.asyncio
    async def test_load_subreddit_cooldowns(self, blob_storage, mock_blob_storage):
        """Test loading subreddit cooldowns."""
        sample_data = {
            "programming": "2023-10-22T12:30:00",
            "python": "2023-10-22T11:45:00",
        }
        mock_blob_storage.download_text.return_value = json.dumps(sample_data)

        result = await blob_storage.load_subreddit_cooldowns()

        assert len(result) == 2
        assert "programming" in result
        assert isinstance(result["programming"], datetime)

    @pytest.mark.asyncio
    async def test_save_etag_cache(self, blob_storage, mock_blob_storage):
        """Test saving RSS ETag cache."""
        test_url = self._validate_test_url("https://example.com/feed.xml")
        etag_cache = {
            test_url: {
                "etag": '"12345"',
                "last_modified": "Wed, 21 Oct 2023 07:28:00 GMT",
                "timestamp": datetime(2023, 10, 22, 12, 0, 0),
            }
        }

        result = await blob_storage.save_etag_cache(etag_cache)

        assert result is True
        mock_blob_storage.upload_text.assert_called_once()

        # Check content
        call_args = mock_blob_storage.upload_text.call_args
        blob_name = call_args[0][1]
        assert blob_name == "metrics/rss/etag_cache.json"

    @pytest.mark.asyncio
    async def test_load_etag_cache(self, blob_storage, mock_blob_storage):
        """Test loading RSS ETag cache."""
        test_url = self._validate_test_url("https://example.com/feed.xml")
        sample_data = {
            test_url: {
                "etag": '"12345"',
                "last_modified": "Wed, 21 Oct 2023 07:28:00 GMT",
                "timestamp": "2023-10-22T12:00:00",
            }
        }
        mock_blob_storage.download_text.return_value = json.dumps(sample_data)

        result = await blob_storage.load_etag_cache()

        assert len(result) == 1
        assert test_url in result
        cache_entry = result[test_url]
        assert cache_entry["etag"] == '"12345"'
        assert isinstance(cache_entry["timestamp"], datetime)

    @pytest.mark.asyncio
    async def test_save_robots_cache(self, blob_storage, mock_blob_storage):
        """Test saving web robots.txt cache."""
        test_url = self._validate_test_url("https://example.com")
        robots_cache = {
            test_url: {
                "crawl_delay": 2.0,
                "allowed_paths": ["/api/", "/public/"],
                "disallowed_paths": ["/private/"],
                "timestamp": datetime(2023, 10, 22, 12, 0, 0),
            }
        }

        result = await blob_storage.save_robots_cache(robots_cache)

        assert result is True
        mock_blob_storage.upload_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_robots_cache(self, blob_storage, mock_blob_storage):
        """Test loading web robots.txt cache."""
        test_url = self._validate_test_url("https://example.com")
        sample_data = {
            test_url: {
                "crawl_delay": 2.0,
                "allowed_paths": ["/api/", "/public/"],
                "disallowed_paths": ["/private/"],
                "timestamp": "2023-10-22T12:00:00",
            }
        }
        mock_blob_storage.download_text.return_value = json.dumps(sample_data)

        result = await blob_storage.load_robots_cache()

        assert len(result) == 1
        assert test_url in result
        cache_entry = result["https://example.com"]
        assert cache_entry["crawl_delay"] == 2.0
        assert isinstance(cache_entry["timestamp"], datetime)

    @pytest.mark.asyncio
    async def test_get_metrics_history(self, blob_storage, mock_blob_storage):
        """Test retrieving metrics history for a source."""

        # Mock blob listing
        class MockBlob:
            def __init__(self, name, timestamp):
                self.name = name
                self.last_modified = timestamp

        mock_blobs = [
            MockBlob(
                "metrics/strategy/test_source/2023-10-22_12-00-00.json",
                datetime(2023, 10, 22, 12, 0, 0),
            ),
            MockBlob(
                "metrics/strategy/test_source/2023-10-22_13-00-00.json",
                datetime(2023, 10, 22, 13, 0, 0),
            ),
        ]
        mock_blob_storage.list_blobs.return_value = mock_blobs

        # Mock blob content
        sample_metrics = {
            "source_name": "test_source",
            "timestamp": "2023-10-22T12:00:00",
            "request_count": 10,
            "success_rate": 0.8,
            "health_status": "healthy",
        }
        mock_blob_storage.download_text.return_value = json.dumps(sample_metrics)

        result = await blob_storage.get_metrics_history("test_source", hours=24)

        assert len(result) == 2
        assert all(isinstance(m, CollectionMetrics) for m in result)

        # Should call list_blobs with correct prefix
        mock_blob_storage.list_blobs.assert_called_once()
        call_args = mock_blob_storage.list_blobs.call_args
        assert call_args[1]["name_starts_with"] == "metrics/strategy/test_source/"

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics(self, blob_storage, mock_blob_storage):
        """Test cleanup of old metrics."""

        # Mock old blobs
        class MockBlob:
            def __init__(self, name, timestamp):
                self.name = name
                self.last_modified = timestamp

        old_time = datetime.now() - timedelta(days=8)
        recent_time = datetime.now() - timedelta(days=2)

        mock_blobs = [
            MockBlob("metrics/strategy/test_source/old_file.json", old_time),
            MockBlob("metrics/strategy/test_source/recent_file.json", recent_time),
        ]
        mock_blob_storage.list_blobs.return_value = mock_blobs

        result = await blob_storage.cleanup_old_metrics(days=7)

        # Should delete only the old blob
        mock_blob_storage.delete_blob.assert_called_once_with(
            "metrics/strategy/test_source/old_file.json"
        )
        assert result == 1  # One blob deleted

    @pytest.mark.asyncio
    async def test_get_storage_stats(self, blob_storage, mock_blob_storage):
        """Test getting storage statistics."""

        # Mock blob listing
        class MockBlob:
            def __init__(self, name, size, timestamp):
                self.name = name
                self.size = size
                self.last_modified = timestamp

        mock_blobs = [
            MockBlob("metrics/strategy/reddit/file1.json", 1024, datetime.now()),
            MockBlob("metrics/strategy/rss/file2.json", 2048, datetime.now()),
            MockBlob("metrics/reddit/subreddit_cooldowns.json", 512, datetime.now()),
        ]
        mock_blob_storage.list_blobs.return_value = mock_blobs

        stats = await blob_storage.get_storage_stats()

        assert stats["total_files"] == 3
        assert stats["total_size"] == 3584  # 1024 + 2048 + 512
        assert stats["by_source"]["reddit"] == 1
        assert stats["by_source"]["rss"] == 1
        assert stats["by_type"]["strategy"] == 2
        assert stats["by_type"]["cooldowns"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_upload_failure(
        self, blob_storage, mock_blob_storage, sample_metrics
    ):
        """Test error handling when upload fails."""
        mock_blob_storage.upload_text.side_effect = Exception("Upload failed")

        result = await blob_storage.save_strategy_metrics(sample_metrics)

        assert result is False

    @pytest.mark.asyncio
    async def test_error_handling_malformed_json(self, blob_storage, mock_blob_storage):
        """Test error handling when downloaded JSON is malformed."""
        mock_blob_storage.download_text.return_value = "invalid json{"

        result = await blob_storage.load_strategy_metrics("test_source")

        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self, blob_storage, mock_blob_storage, sample_metrics
    ):
        """Test concurrent save/load operations."""
        # Simulate concurrent saves
        tasks = []
        for i in range(5):
            metrics = CollectionMetrics(
                source_name=f"source_{i}",
                timestamp=datetime.now(),
                request_count=i + 1,
                success_count=i,
                error_count=1,
                rate_limit_count=0,
                avg_response_time=1.0,
                health_status=SourceHealth.HEALTHY,
                adaptive_delay=1.0,
                success_rate=float(i) / (i + 1) if i > 0 else 0.0,
            )
            tasks.append(blob_storage.save_strategy_metrics(metrics))

        results = await asyncio.gather(*tasks)

        # All saves should succeed
        assert all(results)
        assert mock_blob_storage.upload_text.call_count == 5


@pytest.mark.asyncio
class TestBlobStorageIntegration:
    """Test integration scenarios for blob storage."""

    @pytest.fixture
    def mock_blob_storage(self):
        """Create mock blob storage client."""
        with patch("collectors.blob_metrics_storage.get_blob_storage_client") as mock:
            client = MagicMock()
            client.upload_text = AsyncMock(return_value=True)
            client.download_text = AsyncMock(return_value="{}")
            client.list_blobs = AsyncMock(return_value=[])
            client.delete_blob = AsyncMock(return_value=True)
            mock.return_value = client
            yield client

    async def test_full_lifecycle_scenario(self, mock_blob_storage):
        """Test full lifecycle of metrics storage and retrieval."""
        blob_storage = BlobMetricsStorage()

        # Save metrics for multiple sources
        sources = ["reddit", "rss", "web"]
        for source in sources:
            metrics = CollectionMetrics(
                source_name=source,
                timestamp=datetime.now(),
                request_count=10,
                success_count=8,
                error_count=2,
                rate_limit_count=0,
                avg_response_time=2.0,
                health_status=SourceHealth.HEALTHY,
                adaptive_delay=1.5,
                success_rate=0.8,
            )
            result = await blob_storage.save_strategy_metrics(metrics)
            assert result is True

        # Save source-specific data
        await blob_storage.save_subreddit_cooldowns({"programming": datetime.now()})
        await blob_storage.save_etag_cache(
            {"https://example.com/feed": {"etag": '"123"'}}
        )
        await blob_storage.save_robots_cache(
            {"https://example.com": {"crawl_delay": 1.0}}
        )

        # Verify all data was saved
        assert mock_blob_storage.upload_text.call_count == 6  # 3 metrics + 3 caches

    async def test_storage_resilience(self, mock_blob_storage):
        """Test storage resilience to failures."""
        blob_storage = BlobMetricsStorage()

        # Simulate intermittent failures
        call_count = 0

        def upload_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Fail every other call
                raise Exception("Intermittent failure")
            return True

        mock_blob_storage.upload_text.side_effect = upload_side_effect

        # Try to save multiple metrics
        results = []
        for i in range(4):
            metrics = CollectionMetrics(
                source_name=f"source_{i}",
                timestamp=datetime.now(),
                request_count=1,
                success_count=1,
                error_count=0,
                rate_limit_count=0,
                avg_response_time=1.0,
                health_status=SourceHealth.HEALTHY,
                adaptive_delay=1.0,
                success_rate=1.0,
            )
            result = await blob_storage.save_strategy_metrics(metrics)
            results.append(result)

        # Should have mixed results
        assert True in results  # Some saves succeeded
        assert False in results  # Some saves failed


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
