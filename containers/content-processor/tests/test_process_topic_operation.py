"""
Tests for process_topic operation (single-topic processing).

This validates the contract alignment between content-collector and content-processor
for the new single-topic processing architecture.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.queue_client import QueueMessageModel


@pytest.mark.asyncio
class TestProcessTopicOperation:
    """Test single-topic processing operation."""

    async def test_process_topic_with_valid_payload(self):
        """Test processing a single topic with valid collector payload."""
        # This is the exact format that content-collector sends
        message = QueueMessageModel(
            operation="process_topic",
            service_name="content-collector",
            payload={
                "topic_id": "rss_737279",
                "title": "The AI Industry's Scaling Obsession",
                "source": "rss",
                "collected_at": "2025-10-15T18:00:00+00:00",
                "priority_score": 0.5,
                "collection_id": "collection_20251015_214949",
                "collection_blob": "collected-content/collections/2025/10/15/collection_20251015_214949.json",
                "url": "https://www.wired.com/story/example/",
            },
        )

        # Mock the processor context and operations
        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch("core.processor_operations._process_single_topic") as mock_process,
        ):

            # Mock successful processing
            mock_process.return_value = {
                "article_id": "article_123",
                "cost": 0.05,
                "tokens_used": 500,
            }

            from endpoints.storage_queue_router import process_storage_queue_message

            result = await process_storage_queue_message(message)

            # Verify the result
            assert result["status"] == "success"
            assert result["operation"] == "topic_processed"
            assert result["result"]["article_id"] == "article_123"
            assert mock_process.called

    async def test_process_topic_missing_required_fields(self):
        """Test that missing required fields returns error."""
        message = QueueMessageModel(
            operation="process_topic",
            service_name="content-collector",
            payload={
                # Missing topic_id and title
                "source": "rss",
            },
        )

        from endpoints.storage_queue_router import process_storage_queue_message

        result = await process_storage_queue_message(message)

        assert result["status"] == "error"
        assert "topic_id and title" in result["error"]

    async def test_process_topic_already_processed(self):
        """Test that already-processed topics are skipped."""
        message = QueueMessageModel(
            operation="process_topic",
            service_name="content-collector",
            payload={
                "topic_id": "rss_123456",
                "title": "Already Processed Topic",
                "source": "rss",
                "collected_at": "2025-10-15T18:00:00+00:00",
                "priority_score": 0.5,
            },
        )

        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch("core.processor_operations._process_single_topic") as mock_process,
        ):

            # Mock that topic was already processed (returns None)
            mock_process.return_value = None

            from endpoints.storage_queue_router import process_storage_queue_message

            result = await process_storage_queue_message(message)

            assert result["status"] == "skipped"
            assert result["operation"] == "topic_already_processed"

    async def test_process_topic_with_reddit_metadata(self):
        """Test processing Reddit topic with full metadata."""
        message = QueueMessageModel(
            operation="process_topic",
            service_name="content-collector",
            payload={
                "topic_id": "reddit_abc123",
                "title": "Cool Technology Discussion",
                "source": "reddit",
                "subreddit": "technology",
                "upvotes": 1234,
                "comments": 56,
                "url": "https://reddit.com/r/technology/comments/abc123",
                "collected_at": "2025-10-15T20:00:00+00:00",
                "priority_score": 0.8,
                "collection_id": "collection_20251015_214949",
                "collection_blob": "collected-content/collections/2025/10/15/collection_20251015_214949.json",
            },
        )

        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch("core.processor_operations._process_single_topic") as mock_process,
        ):

            mock_process.return_value = {
                "article_id": "article_456",
                "cost": 0.08,
            }

            from endpoints.storage_queue_router import process_storage_queue_message

            result = await process_storage_queue_message(message)

            assert result["status"] == "success"
            assert result["operation"] == "topic_processed"

            # Verify that TopicMetadata was created with all fields
            call_args = mock_process.call_args
            topic_metadata = call_args[0][1]  # Second argument
            assert topic_metadata.topic_id == "reddit_abc123"
            assert topic_metadata.subreddit == "technology"
            assert topic_metadata.upvotes == 1234
            assert topic_metadata.comments == 56

    async def test_process_topic_datetime_parsing(self):
        """Test that collected_at timestamp is parsed correctly."""
        message = QueueMessageModel(
            operation="process_topic",
            service_name="content-collector",
            payload={
                "topic_id": "rss_test",
                "title": "Test Article",
                "source": "rss",
                "collected_at": "2025-10-15T18:30:45.123Z",  # ISO format with Z suffix
                "priority_score": 0.5,
            },
        )

        with (
            patch(
                "endpoints.storage_queue_router.get_processor_context"
            ) as mock_context,
            patch("core.processor_operations._process_single_topic") as mock_process,
        ):

            mock_process.return_value = {"article_id": "test_123"}

            from endpoints.storage_queue_router import process_storage_queue_message

            result = await process_storage_queue_message(message)

            assert result["status"] == "success"

            # Verify timestamp was parsed
            call_args = mock_process.call_args
            topic_metadata = call_args[0][1]
            assert isinstance(topic_metadata.collected_at, datetime)
