"""
Core Service Logic Tests for Content Collector

Tests for the ContentCollectorService class initialization, statistics,
and core business logic methods.
"""

import json
import os

# Import test fixtures
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from service_logic import ContentCollectorService
from test_fixtures import MockBlobStorageClient, MockQueueClient

sys.path.append(os.path.dirname(__file__))

# Add the shared libs folder to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))


@pytest.mark.unit
class TestContentCollectorServiceInit:
    """Test ContentCollectorService initialization and configuration."""

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
class TestContentCollectorServiceStats:
    """Test service statistics and monitoring functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock storage."""
        return ContentCollectorService(storage_client=MockBlobStorageClient())

    def test_initial_stats(self, service):
        """Test initial statistics values."""
        stats = service.get_service_stats()

        assert stats["total_collections"] == 0
        assert stats["successful_collections"] == 0
        assert stats["failed_collections"] == 0
        assert stats["last_collection"] is None

    def test_stats_update_after_success(self, service):
        """Test statistics update after successful collection."""
        # Simulate successful collection
        service.stats["total_collections"] += 1
        service.stats["successful_collections"] += 1
        service.stats["last_collection"] = "2023-12-15T12:00:00Z"

        stats = service.get_service_stats()
        assert stats["total_collections"] == 1
        assert stats["successful_collections"] == 1
        assert stats["failed_collections"] == 0
        assert stats["last_collection"] == "2023-12-15T12:00:00Z"

    def test_stats_update_after_failure(self, service):
        """Test statistics update after failed collection."""
        # Simulate failed collection
        service.stats["total_collections"] += 1
        service.stats["failed_collections"] += 1

        stats = service.get_service_stats()
        assert stats["total_collections"] == 1
        assert stats["successful_collections"] == 0
        assert stats["failed_collections"] == 1


@pytest.mark.unit
class TestContentCollectorServiceStorage:
    """Test storage-related functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock storage."""
        return ContentCollectorService(storage_client=MockBlobStorageClient())

    @pytest.mark.asyncio
    async def test_get_recent_collections_success(self, service):
        """Test getting recent collections from storage."""
        # Mock blob listing
        mock_blobs = [
            {"name": "collections/2023/01/15/collection_20230115_120000.json"},
            {"name": "collections/2023/01/14/collection_20230114_110000.json"},
            {"name": "collections/2023/01/13/collection_20230113_100000.json"},
        ]
        service.storage.list_blobs = AsyncMock(return_value=mock_blobs)

        result = await service.get_recent_collections(limit=2)

        assert len(result) == 2
        assert result[0]["collection_id"] == "collection_20230115_120000"
        assert result[0]["date"] == "2023-01-15"
        assert result[1]["collection_id"] == "collection_20230114_110000"
        assert result[1]["date"] == "2023-01-14"

    @pytest.mark.asyncio
    async def test_get_recent_collections_storage_error(self, service):
        """Test handling of storage errors when getting collections."""
        service.storage.list_blobs = AsyncMock(side_effect=Exception("Storage error"))

        result = await service.get_recent_collections()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_collection_by_id_success(self, service):
        """Test retrieving specific collection by ID."""
        collection_data = {
            "collection_id": "test_collection",
            "items": [{"title": "Test"}],
            "metadata": {"source": "test"},
        }

        service.storage.list_blobs = AsyncMock(
            return_value=[{"name": "collections/2023/01/15/test_collection.json"}]
        )
        service.storage.download_text = AsyncMock(
            return_value=json.dumps(collection_data)
        )

        result = await service.get_collection_by_id("test_collection")

        assert result == collection_data

    @pytest.mark.asyncio
    async def test_get_collection_by_id_not_found(self, service):
        """Test retrieving non-existent collection."""
        service.storage.list_blobs = AsyncMock(return_value=[])

        result = await service.get_collection_by_id("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_collection_by_id_storage_error(self, service):
        """Test handling of storage errors when getting collection."""
        service.storage.list_blobs = AsyncMock(side_effect=Exception("Storage error"))

        result = await service.get_collection_by_id("test_collection")

        assert result is None
