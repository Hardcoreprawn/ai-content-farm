"""
Content Collection Tests for Content Collector

Tests for the main content collection and storage functionality.
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
from test_fixtures import MockBlobStorageClient, sample_collection_data

sys.path.append(os.path.dirname(__file__))

# Add the shared libs folder to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "libs"))


@pytest.mark.unit
class TestContentCollection:
    """Test content collection and storage functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance with mock storage."""
        mock_storage = MockBlobStorageClient()
        return ContentCollectorService(storage_client=mock_storage)

    @pytest.fixture
    def sample_sources(self):
        """Sample sources configuration for testing."""
        return [
            {
                "type": "reddit",
                "name": "technology",
                "config": {
                    "subreddit": "technology",
                    "sort": "hot",
                    "limit": 25,
                },
                "criteria": {
                    "min_score": 50,
                    "max_age_hours": 24,
                },
            }
        ]

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    @patch("libs.queue_client.send_wake_up_message")
    async def test_collect_and_store_content_success(
        self, mock_wake_up, mock_collect, service, sample_sources
    ):
        """Test successful content collection and storage."""
        # Mock content collection
        mock_collect.return_value = {
            "collected_items": [
                {"id": "item1", "title": "Test 1", "score": 100},
                {"id": "item2", "title": "Test 2", "score": 200},
            ],
            "metadata": {"source_count": 1},
        }

        # Mock wake-up message
        mock_wake_up.return_value = {"message_id": "test_123"}

        result = await service.collect_and_store_content(
            sources_data=sample_sources, deduplicate=True, save_to_storage=True
        )

        # Verify collection result
        assert result["collection_id"].startswith("collection_")
        assert len(result["collected_items"]) == 2
        assert result["metadata"]["total_items"] == 2
        assert result["metadata"]["deduplication"]["enabled"] is True
        assert result["storage_location"] is not None

        # Verify stats updated
        assert service.stats["total_collections"] == 1
        assert service.stats["successful_collections"] == 1
        assert service.stats["failed_collections"] == 0

        # Verify wake-up message sent
        mock_wake_up.assert_called_once()

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    async def test_collect_and_store_content_no_save(
        self, mock_collect, service, sample_sources
    ):
        """Test content collection without saving to storage."""
        # Mock content collection
        mock_collect.return_value = {
            "collected_items": [{"id": "item1", "title": "Test"}],
            "metadata": {"source_count": 1},
        }

        result = await service.collect_and_store_content(
            sources_data=sample_sources, save_to_storage=False
        )

        # Should still have collection data
        assert result["collection_id"].startswith("collection_")
        assert len(result["collected_items"]) == 1
        assert result["storage_location"] is None

        # Stats should still be updated
        assert service.stats["successful_collections"] == 1

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    @patch("service_logic.deduplicate_content")
    async def test_collect_and_store_content_with_deduplication(
        self, mock_dedupe, mock_collect, service, sample_sources
    ):
        """Test content collection with deduplication."""
        # Mock content collection
        original_items = [
            {"id": "item1", "title": "Test 1"},
            {"id": "item2", "title": "Test 1"},  # Duplicate
            {"id": "item3", "title": "Test 2"},
        ]
        mock_collect.return_value = {
            "collected_items": original_items,
            "metadata": {"source_count": 1},
        }

        # Mock deduplication (removes 1 duplicate)
        deduplicated_items = [
            {"id": "item1", "title": "Test 1"},
            {"id": "item3", "title": "Test 2"},
        ]
        mock_dedupe.return_value = deduplicated_items

        result = await service.collect_and_store_content(
            sources_data=sample_sources,
            deduplicate=True,
            similarity_threshold=0.9,
            save_to_storage=False,
        )

        # Verify deduplication was applied
        assert len(result["collected_items"]) == 2
        assert result["metadata"]["deduplication"]["enabled"] is True
        assert result["metadata"]["deduplication"]["original_count"] == 3
        assert result["metadata"]["deduplication"]["deduplicated_count"] == 2
        assert result["metadata"]["deduplication"]["removed_count"] == 1
        assert result["metadata"]["deduplication"]["similarity_threshold"] == 0.9

        mock_dedupe.assert_called_once_with(original_items, 0.9)

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    async def test_collect_and_store_content_no_deduplication(
        self, mock_collect, service, sample_sources
    ):
        """Test content collection without deduplication."""
        # Mock content collection
        mock_collect.return_value = {
            "collected_items": [{"id": "item1"}, {"id": "item2"}],
            "metadata": {"source_count": 1},
        }

        result = await service.collect_and_store_content(
            sources_data=sample_sources, deduplicate=False, save_to_storage=False
        )

        # Verify deduplication was not applied
        assert result["metadata"]["deduplication"]["enabled"] is False
        assert "original_count" not in result["metadata"]["deduplication"]

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    async def test_collect_and_store_content_empty_results(
        self, mock_collect, service, sample_sources
    ):
        """Test content collection with empty results."""
        # Mock empty collection
        mock_collect.return_value = {
            "collected_items": [],
            "metadata": {"source_count": 1},
        }

        result = await service.collect_and_store_content(
            sources_data=sample_sources, save_to_storage=True
        )

        # Should still create collection record
        assert result["collection_id"].startswith("collection_")
        assert len(result["collected_items"]) == 0
        assert result["metadata"]["total_items"] == 0
        # Should still save empty collections
        assert result["storage_location"] is not None

    @pytest.mark.asyncio
    @patch("service_logic.collect_content_batch")
    async def test_collect_and_store_content_collection_failure(
        self, mock_collect, service, sample_sources
    ):
        """Test handling of content collection failures."""
        # Mock collection failure
        mock_collect.side_effect = Exception("Collection failed")

        with pytest.raises(Exception, match="Collection failed"):
            await service.collect_and_store_content(
                sources_data=sample_sources, save_to_storage=False
            )

        # Stats should reflect failure
        assert service.stats["total_collections"] == 1
        assert service.stats["successful_collections"] == 0
        assert service.stats["failed_collections"] == 1

    @pytest.mark.asyncio
    async def test_save_to_storage_success(self, service):
        """Test successful storage save operation."""
        collection_id = "test_collection_20231215_120000"
        collected_items = [{"id": "item1", "title": "Test"}]
        metadata = {"total_items": 1, "timestamp": "2023-12-15T12:00:00Z"}

        storage_location = await service._save_to_storage(
            collection_id, collected_items, metadata
        )

        # Verify storage location format
        assert storage_location.startswith("collected-content/collections/")
        assert collection_id in storage_location
        assert storage_location.endswith(".json")

        # Verify content was stored
        blob_name = storage_location.replace("collected-content/", "")
        stored_key = f"collected-content/{blob_name}"
        assert stored_key in service.storage.uploaded_files

        # Verify stored structure
        stored_content = service.storage.uploaded_files[stored_key]["content"]
        stored_data = json.loads(stored_content)
        assert stored_data["collection_id"] == collection_id
        assert stored_data["items"] == collected_items
        assert stored_data["metadata"] == metadata
        assert stored_data["format_version"] == "1.0"
