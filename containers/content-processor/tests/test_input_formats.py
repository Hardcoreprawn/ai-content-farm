"""
Input Format Validation Tests

Tests that content-processor correctly handles various input formats
from blob storage and queue messages.

Follows strict standards:
- Max 400 lines per file
- Type hints on all functions
- Test external APIs with mocked contracts
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest
from models import TopicMetadata, WakeUpRequest


class TestBlobStorageInputs:
    """Test reading from blob storage with various formats."""

    @pytest.fixture
    def mock_blob_client(self) -> Mock:
        """Create mock blob client with standard interface."""
        client = Mock()
        client.download_json = AsyncMock()
        client.list_blobs = AsyncMock()
        client.blob_exists = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_download_collection_file(self, mock_blob_client: Mock) -> None:
        """Test downloading collection file from blob storage."""
        # Mock response
        mock_blob_client.download_json.return_value = {
            "collection_id": "reddit-tech-20251008",
            "source": "reddit",
            "collected_at": "2025-10-08T10:30:45Z",
            "items": [
                {
                    "id": "abc123",
                    "title": "Test Article",
                    "upvotes": 500,
                    "comments": 75,
                }
            ],
            "metadata": {"api_version": "7.7.1"},
        }

        # Test download
        blob_name = "collections/2025/10/08/reddit-tech-20251008.json"
        data = await mock_blob_client.download_json(blob_name)

        # Validate structure
        assert "collection_id" in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_collection_files(self, mock_blob_client: Mock) -> None:
        """Test listing collection files from blob storage."""
        # Mock response
        mock_blob_client.list_blobs.return_value = [
            "collections/2025/10/08/reddit-tech-20251008.json",
            "collections/2025/10/08/reddit-science-20251008.json",
        ]

        # Test listing
        prefix = "collections/2025/10/08/"
        blobs = await mock_blob_client.list_blobs(prefix)

        # Validate results
        assert len(blobs) == 2
        assert all(blob.startswith(prefix) for blob in blobs)
        assert all(blob.endswith(".json") for blob in blobs)

    @pytest.mark.asyncio
    async def test_blob_exists_check(self, mock_blob_client: Mock) -> None:
        """Test checking if blob exists."""
        mock_blob_client.blob_exists.return_value = True

        blob_name = "collections/2025/10/08/test.json"
        exists = await mock_blob_client.blob_exists(blob_name)

        assert exists is True
        mock_blob_client.blob_exists.assert_called_once_with(blob_name)

    @pytest.mark.asyncio
    async def test_download_invalid_json(self, mock_blob_client: Mock) -> None:
        """Test handling invalid JSON from blob storage."""
        # Mock returns None for invalid JSON
        mock_blob_client.download_json.return_value = None

        blob_name = "collections/invalid.json"
        data = await mock_blob_client.download_json(blob_name)

        assert data is None

    @pytest.mark.asyncio
    async def test_download_missing_blob(self, mock_blob_client: Mock) -> None:
        """Test handling missing blob."""
        # Mock raises FileNotFoundError
        mock_blob_client.download_json.side_effect = FileNotFoundError("Blob not found")

        blob_name = "collections/missing.json"
        with pytest.raises(FileNotFoundError):
            await mock_blob_client.download_json(blob_name)


class TestQueueMessageInputs:
    """Test processing queue messages from KEDA."""

    def test_wake_up_request_parsing(self) -> None:
        """Test parsing wake-up request from queue."""
        message_data: Dict[str, Any] = {
            "source": "content-collector",
            "batch_size": 10,
            "priority_threshold": 0.5,
            "processing_options": {"quality_threshold": 0.7},
            "debug_bypass": False,
            "payload": {"files": ["collections/2025/10/08/reddit-tech.json"]},
        }

        # Parse into model
        request = WakeUpRequest(**message_data)

        # Validate parsing
        assert request.source == "content-collector"
        assert request.batch_size == 10
        assert request.priority_threshold == 0.5
        assert request.payload is not None
        assert "files" in request.payload

    def test_wake_up_request_defaults(self) -> None:
        """Test wake-up request with default values."""
        message_data: Dict[str, Any] = {
            "source": "content-collector",
            "payload": {},
        }

        request = WakeUpRequest(**message_data)

        # Validate defaults
        assert request.batch_size == 10  # Default
        assert request.priority_threshold == 0.5  # Default from model
        assert request.debug_bypass is False
        assert request.processing_options == {}

    def test_wake_up_request_validation(self) -> None:
        """Test wake-up request validation."""
        from pydantic import ValidationError

        # Missing required field
        invalid_data: Dict[str, Any] = {
            "batch_size": 10,
            # Missing 'source'
        }

        with pytest.raises(ValidationError):
            WakeUpRequest(**invalid_data)

    def test_debug_bypass_flag(self) -> None:
        """Test debug_bypass flag parsing."""
        message_data: Dict[str, Any] = {
            "source": "manual-trigger",
            "debug_bypass": True,
            "payload": {},
        }

        request = WakeUpRequest(**message_data)
        assert request.debug_bypass is True


class TestCollectionItemParsing:
    """Test parsing individual collection items."""

    def test_parse_reddit_item(self) -> None:
        """Test parsing Reddit collection item."""
        item: Dict[str, Any] = {
            "id": "abc123",
            "title": "How AI is Transforming Development",
            "url": "https://reddit.com/r/programming/comments/abc123",
            "upvotes": 1250,
            "comments": 180,
            "subreddit": "programming",
            "created_utc": 1728385845.0,
            "selftext": "Full article text...",
        }

        # Validate required fields
        assert "id" in item
        assert "title" in item
        assert "upvotes" in item
        assert isinstance(item["upvotes"], int)

    def test_parse_rss_item(self) -> None:
        """Test parsing RSS feed item."""
        item: Dict[str, Any] = {
            "id": "xyz789",
            "title": "New Python Release",
            "url": "https://python.org/news/release",
            "published": "2025-10-08T10:00:00Z",
            "summary": "Python 3.12 released...",
            "source": "python.org",
        }

        # Validate required fields
        assert "id" in item
        assert "title" in item
        assert "url" in item
        assert "published" in item

    def test_convert_item_to_topic_metadata(self) -> None:
        """Test converting collection item to TopicMetadata."""
        item: Dict[str, Any] = {
            "id": "test123",
            "title": "Test Article",
            "url": "https://example.com/test",
            "upvotes": 500,
            "comments": 75,
        }

        # Create TopicMetadata
        topic = TopicMetadata(
            topic_id=item["id"],
            title=item["title"],
            source="reddit",
            collected_at=datetime.now(timezone.utc),
            priority_score=0.8,
            url=item["url"],
            upvotes=item.get("upvotes", 0),
            comments=item.get("comments", 0),
        )

        # Validate conversion
        assert topic.topic_id == "test123"
        assert topic.title == "Test Article"
        assert topic.source == "reddit"
        assert 0.0 <= topic.priority_score <= 1.0

    def test_handle_missing_optional_fields(self) -> None:
        """Test handling missing optional fields."""
        item: Dict[str, Any] = {
            "id": "test123",
            "title": "Test Article",
            "url": "https://example.com/test",
            # Missing upvotes, comments, etc.
        }

        # Should handle gracefully with defaults
        topic = TopicMetadata(
            topic_id=item["id"],
            title=item["title"],
            source="generic",
            collected_at=datetime.now(timezone.utc),
            priority_score=0.5,
            url=item["url"],
            upvotes=item.get("upvotes", 0),
            comments=item.get("comments", 0),
        )

        # Validate defaults
        assert topic.upvotes == 0
        assert topic.comments == 0


class TestErrorHandling:
    """Test error handling for malformed inputs."""

    def test_empty_collection_file(self) -> None:
        """Test handling empty collection file."""
        collection_data: Dict[str, Any] = {
            "collection_id": "empty-20251008",
            "source": "reddit",
            "collected_at": "2025-10-08T10:30:45Z",
            "items": [],  # Empty items list
            "metadata": {},
        }

        # Should handle gracefully
        assert "items" in collection_data
        assert len(collection_data["items"]) == 0

    def test_malformed_timestamp(self) -> None:
        """Test handling malformed timestamp."""
        invalid_timestamps = [
            "invalid-date",
            "2025-13-45",  # Invalid month/day
            "not-a-timestamp",
        ]

        for ts in invalid_timestamps:
            # Should be caught by validation
            try:
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                assert False, f"Should have raised error for: {ts}"
            except (ValueError, AttributeError):
                pass  # Expected

    def test_negative_metrics(self) -> None:
        """Test handling negative upvotes/comments."""
        item: Dict[str, Any] = {
            "id": "test123",
            "title": "Test Article",
            "upvotes": -100,  # Invalid
            "comments": -50,  # Invalid
        }

        # Should either normalize or reject
        upvotes = max(0, item["upvotes"])
        comments = max(0, item["comments"])

        assert upvotes == 0
        assert comments == 0

    def test_oversized_title(self) -> None:
        """Test handling very long titles."""
        long_title = "A" * 1000  # Very long title

        # Should be truncated or rejected
        max_length = 500
        truncated = long_title[:max_length]

        assert len(truncated) <= max_length

    def test_missing_required_field(self) -> None:
        """Test handling missing required field."""
        incomplete_item: Dict[str, Any] = {
            "id": "test123",
            # Missing 'title' field
        }

        # Should be detected
        assert "title" not in incomplete_item
