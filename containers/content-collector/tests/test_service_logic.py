"""
Service Logic Tests for Content Collector

Tests for the ContentCollectorService class and its core methods.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from service_logic import ContentCollectorService, MockBlobStorageClient

from libs.blob_storage import BlobContainers
from libs.service_bus_client import ServiceBusClient, ServiceBusConfig

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
        assert service.service_bus_client is None
        assert service.stats["total_collections"] == 0
        assert service.stats["successful_collections"] == 0
        assert service.stats["failed_collections"] == 0

    @patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "test"})
    def test_init_in_pytest_environment(self):
        """Test initialization in pytest environment uses mock storage."""
        service = ContentCollectorService()

        assert isinstance(service.storage, MockBlobStorageClient)

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
class TestServiceBusIntegration:
    """Test Service Bus client integration."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock storage."""
        return ContentCollectorService(storage_client=Mock())

    @pytest.mark.asyncio
    @patch("service_logic.ServiceBusClient")
    @patch("service_logic.ServiceBusConfig")
    async def test_get_service_bus_client_success(
        self, mock_config, mock_client_class, service
    ):
        """Test successful Service Bus client creation."""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await service._get_service_bus_client()

        assert result == mock_client
        assert service.service_bus_client == mock_client
        mock_config.assert_called_once()
        mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("service_logic.ServiceBusClient")
    async def test_get_service_bus_client_failure(self, mock_client_class, service):
        """Test Service Bus client creation failure."""
        mock_client_class.side_effect = Exception("Connection failed")

        result = await service._get_service_bus_client()

        assert result is None
        assert service.service_bus_client is None

    @pytest.mark.asyncio
    async def test_get_service_bus_client_cached(self, service):
        """Test that Service Bus client is cached after first creation."""
        mock_client = AsyncMock()
        service.service_bus_client = mock_client

        result = await service._get_service_bus_client()

        assert result == mock_client
        # Should not attempt to create new client

    @pytest.mark.asyncio
    async def test_send_processing_request_success(self, service):
        """Test successful wake-up message sending."""
        mock_service_bus = AsyncMock()
        mock_service_bus.send_message.return_value = True
        service.service_bus_client = mock_service_bus

        collection_result = {
            "collection_id": "test_collection",
            "storage_location": "container/path/file.json",
            "collected_items": [{"id": 1}, {"id": 2}],
            "metadata": {"test": "data"},
        }

        result = await service._send_processing_request(collection_result)

        assert result is True
        # Should send one wake-up message per collection (not per item)
        assert mock_service_bus.send_message.call_count == 1

        # Verify wake-up message structure
        wake_up_call = mock_service_bus.send_message.call_args_list[0][0][0]
        assert wake_up_call.service_name == "content-collector"
        assert wake_up_call.operation == "wake_up"
        assert wake_up_call.payload["collection_id"] == "test_collection"
        assert wake_up_call.payload["items_count"] == 2
        assert wake_up_call.payload["trigger_reason"] == "new_collection"
        assert wake_up_call.metadata["content_type"] == "wake_up_signal"
        assert wake_up_call.metadata["target_service"] == "content-processor"

    @pytest.mark.asyncio
    async def test_send_processing_request_no_service_bus(self, service):
        """Test processing request when Service Bus unavailable."""
        with patch.object(service, "_get_service_bus_client", return_value=None):
            result = await service._send_processing_request({"collection_id": "test"})

            assert result is False

    @pytest.mark.asyncio
    async def test_send_processing_request_send_failure(self, service):
        """Test processing request when wake-up message send fails."""
        mock_service_bus = AsyncMock()
        # Wake-up message fails
        mock_service_bus.send_message.return_value = False
        service.service_bus_client = mock_service_bus

        collection_result = {
            "collection_id": "test",
            "collected_items": [{"id": 1}, {"id": 2}],
            "metadata": {},
            "storage_location": "test/path",
        }

        result = await service._send_processing_request(collection_result)

        # Should return False because wake-up message failed
        assert result is False
        assert mock_service_bus.send_message.call_count == 1

    @pytest.mark.asyncio
    async def test_send_processing_request_all_failures(self, service):
        """Test processing request when all sends fail."""
        mock_service_bus = AsyncMock()
        mock_service_bus.send_message.return_value = False
        service.service_bus_client = mock_service_bus

        collection_result = {
            "collection_id": "test",
            "collected_items": [{"id": 1}],
            "metadata": {},
            "storage_location": "test/path",
        }

        result = await service._send_processing_request(collection_result)

        # Should return False when all messages fail to send
        assert result is False

    @pytest.mark.asyncio
    async def test_send_processing_request_empty_items(self, service):
        """Test processing request with no items to process."""
        mock_service_bus = AsyncMock()
        mock_service_bus.send_message.return_value = True
        service.service_bus_client = mock_service_bus

        result = await service._send_processing_request(
            {"collection_id": "test", "collected_items": []}
        )

        # Should return True and send wake-up message even for empty collections
        assert result is True
        # Should send one wake-up message even for empty collections
        assert mock_service_bus.send_message.call_count == 1


@pytest.mark.unit
class TestStorageOperations:
    """Test blob storage operations."""

    @pytest.fixture
    def service(self):
        """Create service with mock storage."""
        mock_storage = AsyncMock()
        return ContentCollectorService(storage_client=mock_storage)

    @pytest.mark.asyncio
    async def test_save_to_storage_success(self, service):
        """Test successful content saving to storage."""
        collection_id = "test_collection_123"
        collected_items = [{"title": "Test Item", "content": "Test content"}]
        metadata = {"source": "test", "timestamp": "2023-01-01T00:00:00Z"}

        service.storage.upload_text.return_value = "mock://blob/path"

        result = await service._save_to_storage(
            collection_id, collected_items, metadata
        )

        # Verify storage path format
        assert result.startswith(f"{BlobContainers.COLLECTED_CONTENT}/collections/")
        assert result.endswith(f"{collection_id}.json")

        # Verify upload was called correctly
        service.storage.upload_text.assert_called_once()
        call_args = service.storage.upload_text.call_args

        assert call_args.kwargs["container_name"] == BlobContainers.COLLECTED_CONTENT
        assert call_args.kwargs["content_type"] == "application/json"

        # Verify content structure
        uploaded_content = json.loads(call_args.kwargs["content"])
        assert uploaded_content["collection_id"] == collection_id
        assert uploaded_content["items"] == collected_items
        assert uploaded_content["metadata"] == metadata
        assert uploaded_content["format_version"] == "1.0"

    @pytest.mark.asyncio
    async def test_save_to_storage_empty_items(self, service):
        """Test saving with empty items list."""
        result = await service._save_to_storage("test_id", [], {"test": "metadata"})

        assert result is not None
        service.storage.upload_text.assert_called_once()

    def test_get_recent_collections_success(self, service):
        """Test getting recent collections from storage."""
        # Mock blob listing
        mock_blobs = [
            {"name": "collections/2023/01/15/collection_20230115_120000.json"},
            {"name": "collections/2023/01/14/collection_20230114_110000.json"},
            {"name": "collections/2023/01/13/collection_20230113_100000.json"},
        ]
        # Set up the mock properly
        service.storage = Mock()
        service.storage.list_blobs.return_value = mock_blobs

        result = service.get_recent_collections(limit=2)

        assert len(result) == 2
        assert result[0]["collection_id"] == "collection_20230115_120000"
        assert result[0]["date"] == "2023-01-15"
        assert result[1]["collection_id"] == "collection_20230114_110000"

        service.storage.list_blobs.assert_called_once_with(
            container_name=BlobContainers.COLLECTED_CONTENT, prefix="collections/"
        )

    def test_get_recent_collections_storage_error(self, service):
        """Test handling of storage errors when getting collections."""
        service.storage.list_blobs.side_effect = Exception("Storage error")

        result = service.get_recent_collections()

        assert result == []

    def test_get_collection_by_id_success(self, service):
        """Test retrieving specific collection by ID."""
        collection_data = {
            "collection_id": "test_collection",
            "items": [{"title": "Test"}],
            "metadata": {"source": "test"},
        }

        # Set up the mock properly
        service.storage = Mock()
        service.storage.list_blobs.return_value = [
            {"name": "collections/2023/01/15/test_collection.json"}
        ]
        service.storage.download_text.return_value = json.dumps(collection_data)

        result = service.get_collection_by_id("test_collection")

        assert result == collection_data
        service.storage.download_text.assert_called_once()

    def test_get_collection_by_id_not_found(self, service):
        """Test retrieving non-existent collection."""
        service.storage.list_blobs.return_value = []

        result = service.get_collection_by_id("nonexistent")

        assert result is None

    def test_get_collection_by_id_storage_error(self, service):
        """Test handling of storage errors when getting collection."""
        service.storage.list_blobs.side_effect = Exception("Storage error")

        result = service.get_collection_by_id("test_collection")

        assert result is None


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
    async def test_collect_and_store_content_no_deduplication(
        self, mock_collect, service
    ):
        """Test collection without deduplication."""
        mock_collect.return_value = {
            "collected_items": [{"title": "Item 1"}],
            "metadata": {"source": "reddit"},
        }

        service.storage.upload_text.return_value = "mock://blob/path"

        result = await service.collect_and_store_content(
            [{"type": "reddit"}], deduplicate=False
        )

        assert result["metadata"]["deduplication"]["enabled"] is False

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


@pytest.mark.unit
class TestMockBlobStorageClient:
    """Test the MockBlobStorageClient functionality."""

    def test_mock_blob_storage_client_is_async(self):
        """Test that MockBlobStorageClient methods are async."""
        import inspect

        client = MockBlobStorageClient()

        # Check that upload methods are async
        assert inspect.iscoroutinefunction(client.upload_text)
        assert inspect.iscoroutinefunction(client.upload_json)

    @pytest.mark.asyncio
    async def test_mock_upload_text(self):
        """Test mock upload_text method."""
        client = MockBlobStorageClient()

        result = await client.upload_text(
            container_name="test-container",
            blob_name="test-blob.txt",
            content="test content",
            content_type="text/plain",
        )

        assert result == "mock://blob/test-blob.txt"

    @pytest.mark.asyncio
    async def test_mock_upload_json(self):
        """Test mock upload_json method."""
        client = MockBlobStorageClient()

        result = await client.upload_json(
            container_name="test-container",
            blob_name="test-blob.json",
            data={"test": "data"},
        )

        assert result == "mock://blob/test-blob.json"

    def test_mock_download_text(self):
        """Test mock download_text method."""
        client = MockBlobStorageClient()

        result = client.download_text("container", "blob")

        assert result == '{"mock": "data"}'

    def test_mock_list_blobs(self):
        """Test mock list_blobs method."""
        client = MockBlobStorageClient()

        result = client.list_blobs("container", "prefix")

        assert result == []
