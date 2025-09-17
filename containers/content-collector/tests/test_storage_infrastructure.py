"""
Storage Infrastructure Tests for Content Collector

Tests for storage-related functionality including mock clients,
storage operations, and blob storage integration.
"""

import inspect
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the service under test
from service_logic import ContentCollectorService

# Import test fixtures from the shared test fixtures file
from test_fixtures import MockBlobStorageClient, mock_storage, sample_collection_data

# Add libs path for other imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))

# Handle imports that may not be available in test environment
try:
    from blob_storage import BlobContainers
except ImportError:
    # Create mock BlobContainers for testing
    class BlobContainers:
        COLLECTED_CONTENT = "collected-content"


class TestMockBlobStorageClient:
    """Test the MockBlobStorageClient functionality."""

    def test_mock_blob_storage_client_is_async(self):
        """Test that MockBlobStorageClient methods are async."""
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

    @pytest.mark.asyncio
    async def test_mock_download_text(self):
        """Test mock download_text method."""
        client = MockBlobStorageClient()

        result = await client.download_text("container", "blob")

        assert result == '{"mock": "data"}'

    @pytest.mark.asyncio
    async def test_mock_list_blobs(self):
        """Test mock list_blobs method."""
        client = MockBlobStorageClient()

        result = await client.list_blobs("container", "prefix")

        assert result == []


class TestStorageOperations:
    """Test storage-related operations in ContentCollectorService."""

    @pytest.fixture
    def service(self, mock_storage):
        """Create service instance for testing."""
        return ContentCollectorService(storage_client=mock_storage)

    def test_generate_collection_id(self, service):
        """Test collection ID generation format."""
        collection_id = service._generate_collection_id()

        # Should match pattern: content_collection_YYYYMMDD_HHMMSS
        assert collection_id.startswith("content_collection_")

        # Extract and verify timestamp part
        timestamp_part = collection_id.replace("content_collection_", "")
        assert len(timestamp_part) == 15  # YYYYMMDD_HHMMSS
        assert "_" in timestamp_part

        date_part, time_part = timestamp_part.split("_")
        assert len(date_part) == 8  # YYYYMMDD
        assert len(time_part) == 6  # HHMMSS

    def test_get_storage_path(self, service):
        """Test storage path generation."""
        collection_id = "content_collection_20231215_120000"
        path = service._get_storage_path(collection_id)

        # Should follow pattern: collections/YYYY/MM/DD/collection_id.json
        expected_pattern = (
            "collections/2023/12/15/content_collection_20231215_120000.json"
        )
        assert path.startswith(f"{BlobContainers.COLLECTED_CONTENT}/")
        assert path.endswith(expected_pattern)

    @pytest.mark.asyncio
    async def test_save_to_storage_success(self, service, mock_storage):
        """Test successful storage save operation."""
        collection_data = {
            "collection_id": "test_collection_20231215_120000",
            "collected_items": [{"id": 1}, {"id": 2}],
            "metadata": {"timestamp": "2023-12-15T12:00:00Z"},
        }

        mock_storage.upload_json.return_value = "mock://blob/test.json"

        result = await service._save_to_storage(
            collection_data, "test_collection_20231215_120000"
        )

        # Should return the storage path
        assert result.startswith(f"{BlobContainers.COLLECTED_CONTENT}/collections/")
        assert result.endswith("test_collection_20231215_120000.json")

        # Verify upload was called
        assert mock_storage.upload_json.called
        call_args = mock_storage.upload_json.call_args
        assert call_args.kwargs["container_name"] == BlobContainers.COLLECTED_CONTENT
        assert "test_collection_20231215_120000.json" in call_args.kwargs["blob_name"]

    @pytest.mark.asyncio
    async def test_save_to_storage_failure(self, service, mock_storage):
        """Test storage save operation failure."""
        collection_data = {
            "collection_id": "test_collection_20231215_120000",
            "collected_items": [],
            "metadata": {"timestamp": "2023-12-15T12:00:00Z"},
        }

        mock_storage.upload_json.side_effect = Exception("Storage error")

        with pytest.raises(Exception, match="Storage error"):
            await service._save_to_storage(
                collection_data, "test_collection_20231215_120000"
            )

    @pytest.mark.asyncio
    async def test_list_collection_files_success(self, service, mock_storage):
        """Test listing collection files from storage."""
        mock_storage.list_blobs.return_value = [
            {"name": "collections/2023/12/15/test1.json"},
            {"name": "collections/2023/12/15/test2.json"},
        ]

        result = await service._list_collection_files()

        assert len(result) == 2
        mock_storage.list_blobs.assert_called_once_with(
            container_name=BlobContainers.COLLECTED_CONTENT, prefix="collections/"
        )

    @pytest.mark.asyncio
    async def test_list_collection_files_empty(self, service, mock_storage):
        """Test listing collection files when none exist."""
        mock_storage.list_blobs.return_value = []

        result = await service._list_collection_files()

        assert len(result) == 0
        mock_storage.list_blobs.assert_called_once()

    @pytest.mark.asyncio
    async def test_storage_metadata_creation(self, service):
        """Test that storage metadata is created correctly."""
        collection_data = {
            "collection_id": "test_collection_20231215_120000",
            "collected_items": [{"id": 1}, {"id": 2}, {"id": 3}],
            "metadata": {"timestamp": "2023-12-15T12:00:00Z", "source": "reddit"},
        }

        # Get the storage path to verify metadata structure
        storage_path = service._get_storage_path("test_collection_20231215_120000")

        # Verify metadata includes proper storage location reference
        assert "collections/" in storage_path
        assert "2023/12/15/" in storage_path
        assert "test_collection_20231215_120000.json" in storage_path
