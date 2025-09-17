"""
Service Logic Tests for Content Collector

Tests for the ContentCollectorService class and its core methods.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the service under test
from service_logic import ContentCollectorService

# Add libs path for other imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))

# Handle imports that may not be available in test environment
try:
    from blob_storage import BlobContainers
except ImportError:
    # Create mock BlobContainers for testing
    class BlobContainers:
        COLLECTED_CONTENT = "collected-content"


# Mock class for testing
class MockBlobStorageClient:
    def __init__(self):
        self.uploads = []

    async def upload_text(self, container: str, blob_name: str, content: str) -> str:
        self.uploads.append(
            {"container": container, "blob_name": blob_name, "content": content}
        )
        return f"mock://{container}/{blob_name}"

    async def upload_json(self, container: str, blob_name: str, data: Any) -> str:
        self.uploads.append(
            {"container": container, "blob_name": blob_name, "data": data}
        )
        return f"mock://{container}/{blob_name}"

    async def download_text(self, container: str, blob_name: str) -> str:
        return f"Mock content for {blob_name}"

    async def list_blobs(self, container: str, prefix: str = "") -> List[str]:
        return [f"mock_blob_{i}.json" for i in range(3)]

    async def test_connection(self) -> bool:
        return True


# Test fixtures for this module
@pytest.fixture
def mock_storage():
    """Provide a mock blob storage client."""
    return MockBlobStorageClient()


@pytest.fixture
def sample_collection_data():
    """Provide sample collection data for testing."""
    return {
        "collection_id": "test_collection_20230815_120000",
        "metadata": {
            "timestamp": "2023-08-15T12:00:00Z",
            "total_items": 2,
            "processing_time_seconds": 1.5,
            "source": "reddit",
        },
        "collected_items": [
            {
                "title": "Test Article 1",
                "url": "https://example.com/article1",
                "source": "reddit",
                "content": "Sample content for article 1",
            },
            {
                "title": "Test Article 2",
                "url": "https://example.com/article2",
                "source": "reddit",
                "content": "Sample content for article 2",
            },
        ],
    }


# Add the shared libs folder to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))


@pytest.mark.unit
class TestContentCollectorService:
    """Test ContentCollectorService initialization and basic functionality."""

    def test_init_with_storage_client(self):
        """Test initialization with provided storage client."""
        mock_storage = Mock()
        service = ContentCollectorService(storage_client=mock_storage)

        assert service.storage == mock_storage
        assert service.queue_client is None
        assert service.stats["total_collections"] == 0
        assert service.stats["successful_collections"] == 0
        assert service.stats["failed_collections"] == 0

    @patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"})
    def test_init_in_pytest_environment(self):
        """Test initialization in pytest environment uses mock storage."""
        service = ContentCollectorService()

        # Verify it's using a mock storage, not real BlobStorageClient
        # Mock characteristic
        assert hasattr(service.storage, "uploaded_files")
        # Mock characteristic
        assert hasattr(service.storage, "call_history")

    @patch.dict(os.environ, {}, clear=True)
    @patch("service_logic.BlobStorageClient")
    def test_init_production_environment(self, mock_blob_client):
        """Test initialization in production uses real storage client."""
        mock_blob_instance = Mock()
        mock_blob_client.return_value = mock_blob_instance

        service = ContentCollectorService()

        assert service.storage == mock_blob_instance
        mock_blob_client.assert_called_once()

    def test_get_service_stats(self):
        """Test getting service statistics."""
        service = ContentCollectorService()
        stats = service.get_service_stats()

        # Should return a copy, not the original
        assert stats == service.stats
        assert stats is not service.stats

        # Verify structure
        expected_keys = [
            "total_collections",
            "successful_collections",
            "failed_collections",
            "last_collection",
        ]
        assert all(key in stats for key in expected_keys)


@pytest.mark.unit
class TestStorageQueueIntegration:
    """Test Azure Storage Queue integration for wake-up messages."""

    @pytest.fixture
    def service(self, mock_storage):
        """Create service instance with mock storage."""
        return ContentCollectorService(storage_client=mock_storage)

    @pytest.mark.asyncio
    @patch("libs.queue_client.send_wake_up_message")
    async def test_send_processing_request_success(self, mock_send_wake_up, service):
        """Test successful wake-up message sending to Storage Queue."""
        mock_send_wake_up.return_value = {"message_id": "test-id", "status": "sent"}

        collection_result = {
            "collection_id": "test_collection",
            "storage_location": "container/path/file.json",
            "collected_items": [{"id": 1}, {"id": 2}],
            "metadata": {"test": "data"},
        }

        result = await service._send_processing_request(collection_result)

        assert result is True
        # Verify wake-up message was sent
        mock_send_wake_up.assert_called_once()

        # Check call arguments
        call_args = mock_send_wake_up.call_args
        assert call_args[1]["queue_name"] == "content-processing-requests"
        assert call_args[1]["service_name"] == "content-collector"

        payload = call_args[1]["payload"]
        assert payload["collection_id"] == "test_collection"
        assert payload["items_count"] == 2
        assert payload["trigger_reason"] == "new_collection"
        assert payload["storage_location"] == "container/path/file.json"

    @pytest.mark.asyncio
    @patch("libs.queue_client.send_wake_up_message")
    async def test_send_processing_request_queue_failure(
        self, mock_send_wake_up, service
    ):
        """Test processing request when Storage Queue send fails."""
        mock_send_wake_up.side_effect = Exception("Queue unavailable")

        collection_result = {
            "collection_id": "test_collection",
            "collected_items": [{"id": 1}, {"id": 2}],
            "storage_location": "test/path/file.json",
        }

        result = await service._send_processing_request(collection_result)

        assert result is False
        mock_send_wake_up.assert_called_once()

    @pytest.mark.asyncio
    @patch("libs.queue_client.send_wake_up_message")
    async def test_send_processing_request_empty_items(
        self, mock_send_wake_up, service
    ):
        """Test processing request with no items to process."""
        mock_send_wake_up.return_value = {"message_id": "test-id", "status": "sent"}

        collection_result = {
            "collection_id": "test_empty",
            "collected_items": [],
            "storage_location": "test/path/empty.json",
        }

        result = await service._send_processing_request(collection_result)

        # Should still send wake-up message even for empty collections
        assert result is True
        mock_send_wake_up.assert_called_once()

        # Check payload for empty collection
        payload = mock_send_wake_up.call_args[1]["payload"]
        assert payload["items_count"] == 0
        assert payload["collection_id"] == "test_empty"

    @pytest.mark.asyncio
    @patch("libs.queue_client.send_wake_up_message")
    async def test_send_processing_request_message_format(
        self, mock_send_wake_up, service
    ):
        """Test that wake-up message has correct format."""
        mock_send_wake_up.return_value = {"message_id": "test-id", "status": "sent"}

        collection_result = {
            "collection_id": "test_format_20231215_120000",
            "collected_items": [{"id": 1}, {"id": 2}, {"id": 3}],
            "storage_location": "raw-content/collections/2023/12/15/test_format_20231215_120000.json",
        }

        await service._send_processing_request(collection_result)

        # Get the payload that was sent
        payload = mock_send_wake_up.call_args[1]["payload"]

        # Verify all required fields
        assert "trigger_reason" in payload
        assert "collection_id" in payload
        assert "items_count" in payload
        assert "storage_location" in payload
        assert "message" in payload

        # Verify values
        assert payload["trigger_reason"] == "new_collection"
        assert payload["collection_id"] == "test_format_20231215_120000"
        assert payload["items_count"] == 3
        assert (
            payload["storage_location"]
            == "raw-content/collections/2023/12/15/test_format_20231215_120000.json"
        )
        assert "Content collected for test_format_20231215_120000" in payload["message"]
        assert "processor should scan storage" in payload["message"]

    @pytest.mark.asyncio
    @patch("libs.queue_client.send_wake_up_message")
    async def test_send_processing_request_logging(self, mock_send_wake_up, service):
        """Test that processing request logs appropriately."""
        mock_send_wake_up.return_value = {"message_id": "test-id", "status": "sent"}

        collection_result = {
            "collection_id": "test_logging",
            "collected_items": [{"id": 1}],
            "storage_location": "test/path/logging.json",
        }

        with patch("logging.getLogger") as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance

            await service._send_processing_request(collection_result)

            # Verify logging calls
            assert logger_instance.info.call_count >= 1

            # Check that collection info is logged
            log_calls = [call[0][0] for call in logger_instance.info.call_args_list]
            assert any("test_logging" in call for call in log_calls)
            assert any("1 items collected" in call for call in log_calls)


@pytest.mark.unit
class TestContentCollectionWorkflow:
    """Test the main content collection workflow."""

    @pytest.fixture
    def service(self):
        """Create service with all necessary mocks."""
        mock_storage = AsyncMock()
        service = ContentCollectorService(storage_client=mock_storage)
        return service

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    @patch("service_logic.deduplicate_content")
    async def test_collect_and_store_content_success(
        self, mock_dedupe, mock_collect, service
    ):
        """Test successful content collection and storage."""
        # Mock content collection
        mock_collect.return_value = {
            "collected_items": [
                {"title": "Item 1", "content": "Content 1"},
                {"title": "Item 2", "content": "Content 2"},
            ],
            "metadata": {"source": "reddit", "subreddit": "test"},
        }

        # Mock deduplication (no duplicates found)
        mock_dedupe.return_value = mock_collect.return_value["collected_items"]

        # Mock storage
        service.storage.upload_text.return_value = "mock://blob/path"

        # Mock Service Bus
        with patch.object(service, "_send_processing_request", return_value=True):
            sources_data = [{"type": "reddit", "subreddits": ["test"]}]

            result = await service.collect_and_store_content(sources_data)

        # Verify result structure
        assert "collection_id" in result
        assert result["collected_items"] == mock_collect.return_value["collected_items"]
        assert result["storage_location"] is not None
        assert "timestamp" in result

        # Verify stats updated
        assert service.stats["total_collections"] == 1
        assert service.stats["successful_collections"] == 1
        assert service.stats["failed_collections"] == 0

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    @patch("service_logic.deduplicate_content")
    async def test_collect_and_store_content_no_deduplication(
        self, mock_dedupe, mock_collect, service
    ):
        """Test collection without deduplication."""
        mock_collect.return_value = {
            "collected_items": [{"title": "Item 1"}],
            "metadata": {"source": "reddit"},
        }
        # Mock deduplication - should not be called when deduplicate=False
        mock_dedupe.return_value = mock_collect.return_value["collected_items"]

        service.storage.upload_text.return_value = "mock://blob/path"

        # Mock the processing request to avoid Azure calls
        with patch.object(service, "_send_processing_request", return_value=True):
            result = await service.collect_and_store_content(
                [{"type": "reddit"}], deduplicate=False
            )

        assert result["metadata"]["deduplication"]["enabled"] is False
        # Verify deduplication was not called
        mock_dedupe.assert_not_called()

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    async def test_collect_and_store_content_no_storage(self, mock_collect, service):
        """Test collection without saving to storage."""
        mock_collect.return_value = {
            "collected_items": [{"title": "Item 1"}],
            "metadata": {"source": "reddit"},
        }

        result = await service.collect_and_store_content(
            [{"type": "reddit"}], save_to_storage=False
        )

        assert result["storage_location"] is None
        service.storage.upload_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    async def test_collect_and_store_content_failure(self, mock_collect, service):
        """Test handling of collection failures."""
        mock_collect.side_effect = Exception("Collection failed")

        with pytest.raises(Exception, match="Collection failed"):
            await service.collect_and_store_content([{"type": "reddit"}])

        # Stats should reflect the failure
        assert service.stats["total_collections"] == 1
        assert service.stats["successful_collections"] == 0
        assert service.stats["failed_collections"] == 1

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    @patch("service_logic.deduplicate_content")
    async def test_collect_and_store_content_with_deduplication(
        self, mock_dedupe, mock_collect, service
    ):
        """Test collection with deduplication removing items."""
        original_items = [
            {"title": "Item 1", "content": "Content 1"},
            {"title": "Item 2", "content": "Content 2"},
            {"title": "Item 1 duplicate", "content": "Content 1"},
        ]
        deduplicated_items = original_items[:2]  # Remove one duplicate

        mock_collect.return_value = {
            "collected_items": original_items,
            "metadata": {"source": "reddit"},
        }
        mock_dedupe.return_value = deduplicated_items

        service.storage.upload_text.return_value = "mock://blob/path"

        # Mock the processing request to avoid Azure calls
        with patch.object(service, "_send_processing_request", return_value=True):
            result = await service.collect_and_store_content(
                [{"type": "reddit"}], deduplicate=True, similarity_threshold=0.9
            )

        # Verify deduplication metadata
        dedup_metadata = result["metadata"]["deduplication"]
        assert dedup_metadata["enabled"] is True
        assert dedup_metadata["original_count"] == 3
        assert dedup_metadata["deduplicated_count"] == 2
        assert dedup_metadata["removed_count"] == 1
        assert dedup_metadata["similarity_threshold"] == 0.9
