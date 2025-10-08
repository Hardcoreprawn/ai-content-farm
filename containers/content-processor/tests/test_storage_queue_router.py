"""
Tests for Storage Queue Router

Tests the storage_queue_router.py handlers for processing queue messages,
specifically the new process_topic handler for fanout pattern.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Import the router and models
from endpoints.storage_queue_router import ContentProcessorStorageQueueRouter

from libs.queue_client import QueueMessageModel


class TestProcessTopicHandler:
    """Tests for process_topic message handler (fanout pattern)."""

    @pytest.fixture
    def router(self):
        """Create router instance for testing."""
        return ContentProcessorStorageQueueRouter()

    @pytest.fixture
    def valid_topic_message(self):
        """Create valid process_topic queue message."""
        return QueueMessageModel(
            message_id="msg_123",
            operation="process_topic",
            service_name="content-collector",
            correlation_id="col_456_topic_789",
            payload={
                "topic_id": "reddit_abc123",
                "title": "Interesting Python Discussion",
                "source": "reddit",
                "subreddit": "python",
                "url": "https://reddit.com/r/python/comments/abc123",
                "upvotes": 1250,
                "comments": 45,
                "collected_at": "2025-10-08T10:00:00+00:00",
                "priority_score": 0.85,
                "collection_id": "col_456",
                "collection_blob": "collections/2025/10/08/col_456.json",
            },
        )

    @pytest.fixture
    def minimal_topic_message(self):
        """Create minimal process_topic queue message (only required fields)."""
        return QueueMessageModel(
            message_id="msg_456",
            operation="process_topic",
            service_name="content-collector",
            correlation_id="col_789_topic_xyz",
            payload={
                "topic_id": "rss_feed_123",
                "title": "Tech News Article",
                "source": "rss",
                # Optional fields omitted
            },
        )

    @pytest.mark.asyncio
    async def test_process_topic_with_complete_data(self, router, valid_topic_message):
        """Test processing topic message with complete data."""
        # Mock the processor
        mock_processor = Mock()
        mock_processor._process_topic_with_lease = AsyncMock(
            return_value=(True, 0.0542)  # success, cost
        )
        router.processor = mock_processor

        result = await router.process_storage_queue_message(valid_topic_message)

        # Verify result structure
        assert result["status"] == "success"
        assert result["operation"] == "topic_processed"
        assert result["result"]["topic_id"] == "reddit_abc123"
        assert result["result"]["title"] == "Interesting Python Discussion"
        assert result["result"]["success"] is True
        assert result["result"]["cost_usd"] == 0.0542
        assert result["message_id"] == "msg_123"

        # Verify processor was called with TopicMetadata
        assert mock_processor._process_topic_with_lease.called
        topic_arg = mock_processor._process_topic_with_lease.call_args[0][0]
        assert topic_arg.topic_id == "reddit_abc123"
        assert topic_arg.title == "Interesting Python Discussion"
        assert topic_arg.source == "reddit"
        assert topic_arg.subreddit == "python"
        assert topic_arg.upvotes == 1250
        assert topic_arg.comments == 45
        assert topic_arg.priority_score == 0.85

    @pytest.mark.asyncio
    async def test_process_topic_with_minimal_data(self, router, minimal_topic_message):
        """Test processing topic message with only required fields."""
        mock_processor = Mock()
        mock_processor._process_topic_with_lease = AsyncMock(
            return_value=(True, 0.0321)
        )
        router.processor = mock_processor

        result = await router.process_storage_queue_message(minimal_topic_message)

        assert result["status"] == "success"
        assert result["result"]["topic_id"] == "rss_feed_123"
        assert result["result"]["title"] == "Tech News Article"

        # Verify optional fields are None
        topic_arg = mock_processor._process_topic_with_lease.call_args[0][0]
        assert topic_arg.subreddit is None
        assert topic_arg.url is None
        assert topic_arg.upvotes is None
        assert topic_arg.comments is None
        assert topic_arg.priority_score == 0.5  # Default

    @pytest.mark.asyncio
    async def test_process_topic_missing_required_field(self, router):
        """Test that missing required fields returns error."""
        invalid_message = QueueMessageModel(
            message_id="msg_789",
            operation="process_topic",
            service_name="content-collector",
            correlation_id="test",
            payload={
                "topic_id": "test123",
                # Missing 'title' and 'source'
            },
        )

        result = await router.process_storage_queue_message(invalid_message)

        assert result["status"] == "error"
        assert "Missing required fields" in result["error"]
        assert result["message_id"] == "msg_789"

    @pytest.mark.asyncio
    async def test_process_topic_processing_failure(self, router, valid_topic_message):
        """Test handling of processing failure."""
        mock_processor = Mock()
        mock_processor._process_topic_with_lease = AsyncMock(
            return_value=(False, 0.0)  # Failure
        )
        router.processor = mock_processor

        result = await router.process_storage_queue_message(valid_topic_message)

        assert result["status"] == "error"
        assert result["result"]["success"] is False
        assert result["result"]["cost_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_process_topic_exception_handling(self, router, valid_topic_message):
        """Test handling of exceptions during processing."""
        mock_processor = Mock()
        mock_processor._process_topic_with_lease = AsyncMock(
            side_effect=Exception("Processing error")
        )
        router.processor = mock_processor

        result = await router.process_storage_queue_message(valid_topic_message)

        assert result["status"] == "error"
        assert "Processing error" in result["error"]

    @pytest.mark.asyncio
    async def test_process_topic_timestamp_parsing(self, router):
        """Test that collected_at timestamp is parsed correctly."""
        message = QueueMessageModel(
            message_id="msg_ts",
            operation="process_topic",
            service_name="content-collector",
            correlation_id="test",
            payload={
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                "collected_at": "2025-10-08T15:30:00+00:00",
            },
        )

        mock_processor = Mock()
        mock_processor._process_topic_with_lease = AsyncMock(return_value=(True, 0.01))
        router.processor = mock_processor

        await router.process_storage_queue_message(message)

        topic_arg = mock_processor._process_topic_with_lease.call_args[0][0]
        assert isinstance(topic_arg.collected_at, datetime)
        assert topic_arg.collected_at.year == 2025
        assert topic_arg.collected_at.month == 10
        assert topic_arg.collected_at.day == 8

    @pytest.mark.asyncio
    async def test_process_topic_missing_timestamp_uses_now(self, router):
        """Test that missing collected_at uses current time."""
        message = QueueMessageModel(
            message_id="msg_no_ts",
            operation="process_topic",
            service_name="content-collector",
            correlation_id="test",
            payload={
                "topic_id": "test123",
                "title": "Test",
                "source": "reddit",
                # No collected_at
            },
        )

        mock_processor = Mock()
        mock_processor._process_topic_with_lease = AsyncMock(return_value=(True, 0.01))
        router.processor = mock_processor

        before = datetime.now(timezone.utc)
        await router.process_storage_queue_message(message)
        after = datetime.now(timezone.utc)

        topic_arg = mock_processor._process_topic_with_lease.call_args[0][0]
        assert isinstance(topic_arg.collected_at, datetime)
        assert before <= topic_arg.collected_at <= after


class TestBackwardCompatibility:
    """Tests for backward compatibility with old 'process' message format."""

    @pytest.fixture
    def router(self):
        """Create router instance for testing."""
        return ContentProcessorStorageQueueRouter()

    @pytest.fixture
    def legacy_process_message(self):
        """Create legacy process message (batch processing)."""
        return QueueMessageModel(
            message_id="msg_legacy",
            operation="process",
            service_name="content-collector",
            correlation_id="legacy_col_123",
            payload={
                "blob_path": "collections/2025/10/08/col_123.json",
                "collection_id": "col_123",
            },
        )

    @pytest.mark.asyncio
    async def test_legacy_process_message_still_works(
        self, router, legacy_process_message
    ):
        """Test that old 'process' messages still work."""
        mock_processor = Mock()
        mock_result = Mock()
        mock_result.topics_processed = 5
        mock_result.articles_generated = 5
        mock_result.total_cost = 0.2734
        mock_result.processing_time = 45.2

        mock_processor.process_collection_file = AsyncMock(return_value=mock_result)
        router.processor = mock_processor

        result = await router.process_storage_queue_message(legacy_process_message)

        assert result["status"] == "success"
        assert result["operation"] == "processing_completed"
        assert result["result"]["topics_processed"] == 5
        assert result["result"]["articles_generated"] == 5
        assert result["message_id"] == "msg_legacy"

    @pytest.mark.asyncio
    async def test_legacy_process_missing_blob_path(self, router):
        """Test that legacy process message without blob_path returns error."""
        invalid_message = QueueMessageModel(
            message_id="msg_invalid",
            operation="process",
            service_name="content-collector",
            correlation_id="test",
            payload={
                # Missing blob_path
            },
        )

        result = await router.process_storage_queue_message(invalid_message)

        assert result["status"] == "error"
        assert "Missing required field: blob_path" in result["error"]


class TestUnknownOperations:
    """Tests for handling unknown operation types."""

    @pytest.fixture
    def router(self):
        """Create router instance for testing."""
        return ContentProcessorStorageQueueRouter()

    @pytest.mark.asyncio
    async def test_unknown_operation_returns_ignored(self, router):
        """Test that unknown operations return 'ignored' status."""
        unknown_message = QueueMessageModel(
            message_id="msg_unknown",
            operation="unknown_operation",
            service_name="some-service",
            correlation_id="test",
            payload={},
        )

        result = await router.process_storage_queue_message(unknown_message)

        assert result["status"] == "ignored"
        assert result["operation"] == "unknown_operation"
        assert "Unknown operation type" in result["reason"]
        assert result["message_id"] == "msg_unknown"


class TestWakeUpHandler:
    """Tests for wake_up message handler (legacy batch processing)."""

    @pytest.fixture
    def router(self):
        """Create router instance for testing."""
        return ContentProcessorStorageQueueRouter()

    @pytest.fixture
    def wake_up_message(self):
        """Create wake_up queue message."""
        return QueueMessageModel(
            message_id="msg_wakeup",
            operation="wake_up",
            service_name="scheduler",
            correlation_id="scheduled_run",
            payload={
                "batch_size": 10,
                "priority_threshold": 0.6,
                "debug_bypass": False,
            },
        )

    @pytest.mark.asyncio
    async def test_wake_up_message_triggers_batch_processing(
        self, router, wake_up_message
    ):
        """Test that wake_up messages trigger batch processing."""
        mock_processor = Mock()
        mock_result = Mock()
        mock_result.topics_processed = 15
        mock_result.articles_generated = 15
        mock_result.total_cost = 0.8234
        mock_result.processing_time = 120.5

        mock_processor.process_available_work = AsyncMock(return_value=mock_result)
        router.processor = mock_processor

        result = await router.process_storage_queue_message(wake_up_message)

        assert result["status"] == "success"
        assert result["operation"] == "wake_up_processed"
        assert result["result"]["topics_processed"] == 15
        assert result["result"]["batch_size"] == 10
        assert result["result"]["priority_threshold"] == 0.6

        # Verify process_available_work was called with correct params
        mock_processor.process_available_work.assert_called_once()
        call_kwargs = mock_processor.process_available_work.call_args[1]
        assert call_kwargs["batch_size"] == 10
        assert call_kwargs["priority_threshold"] == 0.6
        assert call_kwargs["debug_bypass"] is False
